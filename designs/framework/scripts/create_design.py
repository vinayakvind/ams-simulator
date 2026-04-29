"""
Create a new design directory structure from architecture spec.

Usage:
    python designs/framework/scripts/create_design.py --name lin_asic --tech generic180
    python designs/framework/scripts/create_design.py --name lin_asic --arch architecture.yaml
"""

import argparse
import json
import os
import sys
import yaml
from pathlib import Path
from typing import Any

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from simulator.catalog import (
    compose_chip_profile,
    list_chip_profiles,
    list_digital_subsystems,
    list_reusable_ips,
    list_supported_technologies,
    list_verification_ips,
)


DEFAULT_BLOCKS = {
    "bandgap": {
        "type": "analog",
        "generator": "bandgap_ref",
        "ports": ["VDD", "VREF", "GND", "EN"],
    },
    "ldo_analog": {
        "type": "analog",
        "generator": "ldo_analog",
        "ports": ["VIN", "VOUT", "GND", "VREF", "EN"],
    },
    "ldo_digital": {
        "type": "analog",
        "generator": "ldo_digital",
        "ports": ["VIN", "VOUT", "GND", "VREF", "EN"],
    },
}

MODELS = {
    "generic180": {
        "NMOS_3P3": ".MODEL NMOS_3P3 NMOS (VTO=0.5 KP=120u LAMBDA=0.01 GAMMA=0.4 PHI=0.8)",
        "PMOS_3P3": ".MODEL PMOS_3P3 PMOS (VTO=-0.5 KP=40u LAMBDA=0.01 GAMMA=0.4 PHI=0.8)",
        "PMOS_HV": ".MODEL PMOS_HV PMOS (VTO=-0.8 KP=20u LAMBDA=0.005)",
        "NPN_VERT": ".MODEL NPN_VERT NPN (IS=1e-15 BF=100 BR=1)",
    },
}


def _merge_unique_strings(*groups: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for item in group:
            if item and item not in seen:
                seen.add(item)
                merged.append(item)
    return merged


def _print_catalog(entries: list[dict[str, Any]], fields: list[tuple[str, str]]) -> None:
    for entry in entries:
        values = [f"{label}={entry.get(key, '')}" for label, key in fields]
        print(" | ".join(values))


def _normalize_block_type(block_info: dict) -> str:
    return str(block_info.get("type", "analog")).strip().lower()


def _resolve_source_path(source: str, design_dir: Path) -> Path:
    candidate = Path(source)
    if candidate.is_absolute():
        return candidate

    search_roots = [PROJECT_ROOT, design_dir, design_dir.parent, Path.cwd()]
    for root in search_roots:
        resolved = (root / candidate).resolve()
        if resolved.exists():
            return resolved
    return (PROJECT_ROOT / candidate).resolve()


def _load_model_cards(technology: str) -> str:
    try:
        from simulator.agents.tech_mapper import TechMapper

        return TechMapper(technology).get_model_cards()
    except Exception:
        models = MODELS.get(technology, MODELS["generic180"])
        return "\n".join(models.values())


def _digital_stub_module(block_name: str, ports: list[str]) -> str:
    port_comment = ", ".join(ports) if ports else "(none recorded)"
    return (
        f"// Auto-generated RTL stub for {block_name}\n"
        f"// Expected ports: {port_comment}\n"
        f"module {block_name}();\n"
        "endmodule\n"
    )


def _format_block_title(block_name: str) -> str:
    acronyms = {"adc", "dac", "ldo", "lin", "pll", "por", "psrr", "rtl", "spi", "uart"}
    parts = []
    for token in block_name.split("_"):
        parts.append(token.upper() if token.lower() in acronyms else token.capitalize())
    return " ".join(parts)


def _default_analysis_steps(design_name: str, block_name: str, block_type: str) -> list[dict]:
    normalized_type = (block_type or "mixed").lower()
    if normalized_type == "analog":
        return [
            {
                "type": "dc",
                "name": "DC operating point",
                "purpose": "Confirm the bias points and closed-loop target before higher-order analysis.",
                "command": f"python designs/framework/scripts/simulate_block.py --design {design_name} --block {block_name} --analysis dc",
                "pass_criteria": "All intended operating nodes settle in their nominal ranges.",
                "debug_focus": "Bias current, reference level, divider ratio, and pass-device headroom.",
            },
            {
                "type": "ac",
                "name": "AC small-signal inspection",
                "purpose": "Measure gain shape, pole placement, and loop-strength margins.",
                "command": f"python designs/framework/scripts/simulate_block.py --design {design_name} --block {block_name} --analysis ac --fstart 10 --fstop 1e7 --points 60",
                "pass_criteria": "Dominant-pole behavior is controlled and no unstable peaking appears.",
                "debug_focus": "Compensation network, amplifier gm, and loading.",
            },
            {
                "type": "psrr",
                "name": "PSRR extraction",
                "purpose": "Inject supply ripple and quantify how much leaks into the regulated or reference node.",
                "command": f"python designs/framework/scripts/simulate_block.py --design {design_name} --block {block_name} --analysis psrr --fstart 10 --fstop 1e7 --points 60",
                "pass_criteria": "Rejection stays above the design target at the key frequencies.",
                "debug_focus": "Loop gain, feedthrough paths, and local decoupling.",
            },
            {
                "type": "corner",
                "name": "Corner closure sweep",
                "purpose": "Repeat the core checks across process, voltage, and temperature movement.",
                "command": f"python designs/framework/scripts/simulate_block.py --design {design_name} --block {block_name} --analysis dc --corner FF --temperature 125",
                "pass_criteria": "Required specs remain inside limits across the intended PVT matrix.",
                "debug_focus": "One dominant tuning knob per failure mode, recorded explicitly.",
            },
        ]

    if normalized_type == "digital":
        return [
            {
                "type": "functional",
                "name": "Digital control-path check",
                "purpose": "Verify reset state, register or interface behavior, and state reachability.",
                "command": f"python designs/framework/scripts/run_regression.py --design {design_name}",
                "pass_criteria": "Reset defaults and primary transactions behave as documented.",
                "debug_focus": "Reset order, decode logic, interface timing, and state transitions.",
            }
        ]

    return [
        {
            "type": "dc",
            "name": "Static threshold and bias check",
            "purpose": "Confirm static node placement before exercising dynamic behavior.",
            "command": f"python designs/framework/scripts/simulate_block.py --design {design_name} --block {block_name} --analysis dc",
            "pass_criteria": "Threshold-defining nodes and supplies settle to intended values.",
            "debug_focus": "Bias network, thresholds, and supply headroom.",
        },
        {
            "type": "tran",
            "name": "Dynamic interface check",
            "purpose": "Exercise the real interface behavior in time domain.",
            "command": f"python designs/framework/scripts/simulate_block.py --design {design_name} --block {block_name} --analysis tran --tstop 50e-6 --tstep 20e-9",
            "pass_criteria": "Edges, thresholds, or transitions remain inside the intended interface budget.",
            "debug_focus": "Slew control, timing constants, and interface biasing.",
        },
        {
            "type": "corner",
            "name": "Corner robustness",
            "purpose": "Check the mixed-signal path over process and temperature movement.",
            "command": f"python designs/framework/scripts/simulate_block.py --design {design_name} --block {block_name} --analysis dc --corner SS --temperature 125",
            "pass_criteria": "Thresholds and interface behavior remain valid across the matrix.",
            "debug_focus": "One failure signature and one corrective knob at a time.",
        },
    ]


def _default_block_files(design_name: str, block_name: str, block_type: str) -> list[dict]:
    files = [
        {"path": f"designs/{design_name}/blocks/{block_name}/spec.yaml", "role": "Block specification"},
    ]
    normalized_type = (block_type or "mixed").lower()
    if normalized_type in {"analog", "mixed"}:
        files.extend([
            {"path": f"designs/{design_name}/blocks/{block_name}/{block_name}.spice", "role": "Block netlist or subcircuit"},
            {"path": f"designs/{design_name}/blocks/{block_name}/testbench.spice", "role": "Standalone testbench"},
            {"path": f"designs/{design_name}/blocks/{block_name}/simulate.py", "role": "Block-level simulation entrypoint"},
            {"path": f"designs/{design_name}/blocks/{block_name}/REPORT.md", "role": "Recorded block results"},
        ])
    else:
        files.extend([
            {"path": f"designs/{design_name}/rtl/{block_name}.sv", "role": "Planned RTL implementation"},
            {"path": f"designs/{design_name}/blocks/{block_name}/REPORT.md", "role": "Recorded verification notes"},
        ])
    return files


def create_block_spec(block_name: str, block_info: dict, design_dir: Path, technology: str):
    """Create spec.yaml for a block."""
    block_dir = design_dir / "blocks" / block_name
    block_dir.mkdir(parents=True, exist_ok=True)

    source = block_info.get("source", "")
    spec = {
        "block": {
            "name": block_name,
            "type": block_info.get("type", "analog"),
            "generator": block_info.get("generator", ""),
            "description": block_info.get("description", f"{block_name} block"),
            "technology": technology,
            "source": source,
            "category": block_info.get("category", ""),
            "aliases": block_info.get("aliases", []),
            "technology_support": block_info.get("technology_support", []),
        },
        "ports": [
            {"name": p, "direction": "inout"} for p in block_info.get("ports", [])
        ],
        "specs": {},
        "verification": block_info.get("verification", {}),
    }

    if _normalize_block_type(block_info) in {"analog", "mixed"}:
        spec["testbench"] = {
            "dc_op": {"description": "DC operating point", "pass_criteria": "TBD"},
        }

    with open(block_dir / "spec.yaml", "w") as f:
        yaml.dump(spec, f, default_flow_style=False, sort_keys=False)


def create_block_netlist(block_name: str, block_info: dict, design_dir: Path, technology: str) -> tuple[str, bool]:
    """Generate or import the implementation for a block.

    Returns:
        Tuple of (content, supports_subckt_testbench)
    """
    block_dir = design_dir / "blocks" / block_name
    block_dir.mkdir(parents=True, exist_ok=True)
    block_type = _normalize_block_type(block_info)
    source = str(block_info.get("source", "")).strip()

    if source:
        source_path = _resolve_source_path(source, design_dir)
        if not source_path.exists():
            raise FileNotFoundError(f"Source implementation not found: {source}")

        content = source_path.read_text(encoding="utf-8")
        if block_type == "digital":
            rtl_dir = design_dir / "rtl"
            rtl_dir.mkdir(parents=True, exist_ok=True)
            suffix = source_path.suffix.lower() if source_path.suffix.lower() in {".v", ".sv"} else ".sv"
            output_path = rtl_dir / f"{block_name}{suffix}"
        else:
            output_path = block_dir / f"{block_name}.spice"
        output_path.write_text(content, encoding="utf-8")
        return content, ".SUBCKT" in content.upper()

    if block_type == "digital":
        rtl_dir = design_dir / "rtl"
        rtl_dir.mkdir(parents=True, exist_ok=True)
        rtl = _digital_stub_module(block_name, block_info.get("ports", []))
        (rtl_dir / f"{block_name}.sv").write_text(rtl, encoding="utf-8")
        return rtl, False

    generator = block_info.get("generator", "")
    params = block_info.get("params", {})

    try:
        from simulator.agents.block_builder import BlockBuilder
        builder = BlockBuilder(technology)
        result = builder.build_block(generator, **params)
        netlist = result.get("netlist", "")
    except Exception:
        ports = " ".join(block_info.get("ports", ["VDD", "GND"]))
        netlist = f"* Stub: {block_name}\n.SUBCKT {block_name.upper()} {ports}\n.ENDS {block_name.upper()}\n"

    with open(block_dir / f"{block_name}.spice", "w") as f:
        f.write(netlist)

    return netlist, ".SUBCKT" in netlist.upper()


def create_testbench(block_name: str, block_info: dict, design_dir: Path, technology: str):
    """Create testbench SPICE file for a block."""
    block_dir = design_dir / "blocks" / block_name
    model_lines = _load_model_cards(technology)
    ports = block_info.get("ports", ["VDD", "GND"])

    tb = f"""* Testbench: {block_name}
* Auto-generated by AMS Design Framework

.include {block_name}.spice

* Technology models
{model_lines}

* Supplies
V_VDD VDD 0 DC 3.3
V_GND_REF GND_REF 0 DC 0

* Enable
V_EN EN 0 DC 3.3

* DUT instantiation
X_DUT {' '.join(ports)} {block_name.upper()}

* Analysis
.OP

.end
"""
    with open(block_dir / "testbench.spice", "w") as f:
        f.write(tb)


def create_simulate_script(block_name: str, design_dir: Path):
    """Create per-block simulation script."""
    block_dir = design_dir / "blocks" / block_name

    script = f'''"""Simulate {block_name} block."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT))

from simulator.engine.analog_engine import AnalogEngine, DCAnalysis, TransientAnalysis

def run_dc():
    """Run DC operating point analysis."""
    engine = AnalogEngine()
    tb_path = Path(__file__).parent / "testbench.spice"
    
    # Load testbench (inline for simplicity)
    block_path = Path(__file__).parent / "{block_name}.spice"
    with open(block_path) as f:
        block_netlist = f.read()
    
    engine.load_netlist(block_netlist)
    results = engine.solve_dc()
    
    print(f"DC Operating Point - {block_name}")
    print("=" * 40)
    for k, v in sorted(results.items()):
        if "V(" in k:
            print(f"  {{k}} = {{v:.6f}} V")
    
    return results

if __name__ == "__main__":
    run_dc()
'''
    with open(block_dir / "simulate.py", "w") as f:
        f.write(script)


def create_report_template(block_name: str, design_dir: Path):
    """Create REPORT.md template."""
    block_dir = design_dir / "blocks" / block_name

    report = f"""# Block Report: {block_name}

## Status: PENDING

## DC Operating Point
| Node | Voltage | Expected | Pass |
|------|---------|----------|------|
| | | | |

## Specs Verification
| Spec | Target | Measured | Pass |
|------|--------|----------|------|
| | | | |

## Notes
- Generated by AMS Design Framework
"""
    with open(block_dir / "REPORT.md", "w") as f:
        f.write(report)


def create_design_index(design_name: str, blocks: dict, design_dir: Path):
    """Create design-level index file."""
    block_list = "\n".join(
        f"| {i+1} | {name} | {info.get('type', 'unknown')} | PENDING |"
        for i, (name, info) in enumerate(blocks.items())
    )

    index = (
        f"# {design_name.upper()} - Design Index\n\n"
        "## Architecture Overview\n"
        f"Auto-generated design with {len(blocks)} blocks.\n\n"
        "## Block Status\n\n"
        "| # | Block | Type | Status |\n"
        "|---|-------|------|--------|\n"
        f"{block_list}\n\n"
        "## Directory Structure\n"
        "```\n"
        f"{design_name}/\n"
        "  00_INDEX.md          ← This file\n"
        "  architecture.yaml    ← Architecture definition\n"
        "  design_reference.json← Indexed design methodology and debug reference\n"
        "  blocks/              ← Individual block designs\n"
        "    <block_name>/\n"
        "      spec.yaml        ← Block specification\n"
        "      <block>.spice    ← Block netlist or imported source mirror\n"
        "      testbench.spice  ← Optional testbench for subcircuit-style analog blocks\n"
        "      simulate.py      ← Optional block simulation script\n"
        "      REPORT.md        ← Results report\n"
        "  rtl/                 ← Digital RTL files\n"
        "  top/                 ← Top-level integration\n"
        "  VERIFICATION_STATUS.md\n"
        "```\n\n"
        "## Quick Commands\n"
        "```bash\n"
        "# Query the design-reference index\n"
        f"python designs/framework/scripts/query_design_reference.py --input designs/{design_name}/design_reference.json --list-blocks\n\n"
        "# Generate the standalone methodology webpage\n"
        f"python designs/framework/scripts/generate_design_reference.py --input designs/{design_name}/design_reference.json --output reports/{design_name}_design_reference.html\n\n"
        "# Simulate a specific block\n"
        f"python designs/{design_name}/blocks/<block>/simulate.py\n\n"
        "# Run full regression\n"
        f"python designs/framework/scripts/run_regression.py --design {design_name}\n"
        "```\n"
    )
    with open(design_dir / "00_INDEX.md", "w", encoding="utf-8") as f:
        f.write(index)


def create_design_reference_template(
    design_name: str,
    blocks: dict,
    design_dir: Path,
    technology: str,
    library_context: dict[str, Any] | None = None,
):
    """Create a reusable indexed design-reference scaffold for the design."""
    ordered_blocks = list(blocks.items())
    example_block = ordered_blocks[0][0] if ordered_blocks else "block_a"
    library_context = library_context or {}

    manifest_blocks = []
    for block_name, block_info in ordered_blocks:
        block_type = block_info.get("type", "mixed")
        manifest_blocks.append({
            "block_key": block_name,
            "name": _format_block_title(block_name),
            "domain": block_type,
            "aliases": _merge_unique_strings([block_name], block_info.get("aliases", [])),
            "role": block_info.get("role", f"Document the role of {block_name} inside the {design_name} architecture."),
            "architecture": block_info.get("description", "TBD - capture the chosen topology and why it satisfies the block contract."),
            "implementation_steps": [
                {
                    "title": "Capture architecture intent",
                    "description": "Record why this topology was chosen and what assumptions it makes about surrounding blocks.",
                },
                {
                    "title": "Record sizing or logic equations",
                    "description": "Add the first-order sizing formulas, state equations, or protocol equations that control behavior.",
                },
                {
                    "title": "Close verification and debug flow",
                    "description": "Capture the DC, AC, PSRR, transient, corner, or functional checks plus the primary tuning knobs.",
                },
            ],
            "primary_specs": [],
            "sizing_formulas": [],
            "dc_operating_points": [],
            "analysis_steps": _default_analysis_steps(design_name, block_name, block_type),
            "corner_focus": [],
            "tuning_knobs": [],
            "files": _default_block_files(design_name, block_name, block_type),
            "category": block_info.get("category", ""),
            "technology_support": block_info.get("technology_support", []),
        })

    manifest = {
        "design": {
            "id": design_name,
            "title": f"{design_name.upper()} Indexed Design Reference",
            "headline": "One indexed playbook for architecture, formulas, corners, and debug.",
            "summary": f"Structured design-reference scaffold for {design_name} so future work keeps architecture, operating points, analysis flow, and debug knowledge in one scriptable place.",
            "narrative": "Fill this manifest as the design matures. The goal is to preserve not only what the block is, but also how it was sized, how DC operating points were chosen, how AC or PSRR was checked, what failed at corners, and which knob closed the failure.",
            "standard": "TBD",
            "technology": technology,
            "signoff_boundary": "Replace generic placeholder assumptions with foundry PDK models, extracted parasitics, and production signoff criteria before tapeout.",
            "tags": ["indexed methodology", "reuse", "corner closure", "debug"],
        },
        "flow_summary": "Use the same indexed flow for every design so architecture, implementation, verification, and debug artifacts remain aligned.",
        "analysis_summary": "Analog blocks should record DC operating points first, then AC shape, PSRR, transient behavior, and PVT closure. Digital blocks should record reset behavior, interface transactions, and state reachability.",
        "script_summary": "The manifest is the source of truth. Query it from the CLI and render it to HTML so the methodology can be reused across designs.",
        "architecture": {
            "summary": "Describe the chip-level partitioning, power tree, control path, and external interfaces here.",
            "power_tree_summary": "TBD",
            "domains": [],
            "power_sequence": [],
            "control_path": [],
        },
        "indexed_flow": [
            {
                "index": "01",
                "title": "Freeze architecture and interfaces",
                "description": "Lock the block list, domain boundaries, interfaces, and design assumptions before detailed sizing begins.",
                "outputs": ["architecture.yaml", "00_INDEX.md"],
            },
            {
                "index": "02",
                "title": "Design and size each block",
                "description": "Capture the chosen topology, first-order formulas, and assumptions that control each block implementation.",
                "outputs": ["blocks/<block>/spec.yaml", "blocks/<block>/<block>.spice or rtl/<block>.sv"],
            },
            {
                "index": "03",
                "title": "Record operating points and analysis flow",
                "description": "Write down DC targets, AC or functional checks, PSRR if relevant, and the required debug sequence.",
                "outputs": ["design_reference.json"],
            },
            {
                "index": "04",
                "title": "Close corners and publish knowledge",
                "description": "Attach the corner matrix, failure signatures, corrective knobs, and generate the HTML reference page.",
                "outputs": [f"reports/{design_name}_design_reference.html"],
            },
        ],
        "analysis_playbook": _default_analysis_steps(design_name, example_block, blocks.get(example_block, {}).get("type", "mixed")),
        "corner_closure": {
            "summary": "Record the process, voltage, and temperature matrix plus the order in which corner failures were closed.",
            "matrix": {
                "process": "TT, FF, SS, FS, SF",
                "voltage": "domain-specific min / nominal / max",
                "temperature_c": "-40, 27, 125",
            },
            "closure_order": [
                "Fix DC operating-point errors before AC, PSRR, or transient tuning.",
                "Tune one dominant knob at a time and record why it worked.",
                "Promote recurring lessons into the manifest so the next design starts from a known playbook.",
            ],
            "pass_rule": "A block is closed only when its required specs stay inside limits across the intended matrix or when a narrower assumption is explicitly documented.",
            "model_note": "Generic corner wrappers are for early sensitivity exploration only; production signoff should use PDK corner decks.",
        },
        "script_index": [
            {
                "name": "Query all recorded blocks",
                "purpose": "List the indexed blocks in this design reference.",
                "command": f"python designs/framework/scripts/query_design_reference.py --input designs/{design_name}/design_reference.json --list-blocks",
            },
            {
                "name": "Query one block summary",
                "purpose": "Retrieve one block section from the manifest.",
                "command": f"python designs/framework/scripts/query_design_reference.py --input designs/{design_name}/design_reference.json --block {example_block} --section summary",
            },
            {
                "name": "Generate the HTML reference",
                "purpose": "Render the manifest into a standalone webpage.",
                "command": f"python designs/framework/scripts/generate_design_reference.py --input designs/{design_name}/design_reference.json --output reports/{design_name}_design_reference.html",
            },
        ],
        "debug_playbook": [
            {
                "title": "Start with the first failing physical assumption",
                "description": "Fix reference level, bias, thresholds, or reset state before tuning second-order behavior.",
            },
            {
                "title": "Record one knob per failure",
                "description": "Tie every corner or protocol failure to one primary knob so the lesson is reusable.",
            },
        ],
        "future_design_reuse": [
            {
                "title": "Reuse this manifest structure",
                "description": "Copy the same indexed sections into the next design so architecture and debug stay comparable.",
            },
            {
                "title": "Keep the HTML page generated",
                "description": "The webpage is the fastest review surface, but the JSON manifest stays the source of truth.",
            },
        ],
        "blocks": manifest_blocks,
    }

    design_manifest = library_context.get("design_manifest", {})
    for key, value in design_manifest.items():
        if key == "tags":
            manifest["design"]["tags"] = _merge_unique_strings(manifest["design"].get("tags", []), value)
        elif value:
            manifest["design"][key] = value

    if library_context.get("chip_profile"):
        manifest["chip_profile"] = library_context["chip_profile"]
    if library_context.get("reusable_ips"):
        manifest["reusable_ips"] = library_context["reusable_ips"]
    if library_context.get("verification_ips"):
        manifest["verification_ips"] = library_context["verification_ips"]
    if library_context.get("digital_subsystems"):
        manifest["digital_subsystems"] = library_context["digital_subsystems"]

    manifest_path = design_dir / "design_reference.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    try:
        from simulator.reporting import render_design_reference_html

        reports_dir = PROJECT_ROOT / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        html_path = reports_dir / f"{design_name}_design_reference.html"
        html_path.write_text(render_design_reference_html({**manifest, "source_path": str(manifest_path)}), encoding="utf-8")
    except Exception:
        pass


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Create a new ASIC design")
    parser.add_argument("--name", help="Design name")
    parser.add_argument("--tech", default="generic180", help="Technology node")
    parser.add_argument("--arch", help="Architecture YAML file")
    parser.add_argument("--profile", help="Reusable chip profile from the integrated IP/VIP catalog")
    parser.add_argument("--blocks", nargs="*", help="Block names to include")
    parser.add_argument("--include-ip", action="append", default=[], help="Additional reusable IP key to include")
    parser.add_argument("--exclude-ip", action="append", default=[], help="Reusable IP key to remove from the selected profile")
    parser.add_argument("--list-profiles", action="store_true", help="List available chip profiles and exit")
    parser.add_argument("--list-ips", action="store_true", help="List available reusable IP blocks and exit")
    parser.add_argument("--list-vips", action="store_true", help="List available verification IP entries and exit")
    parser.add_argument("--list-subsystems", action="store_true", help="List available integrated digital subsystems and exit")
    parser.add_argument("--list-technologies", action="store_true", help="List supported technology mappings and exit")
    args = parser.parse_args(argv)

    if args.list_technologies:
        _print_catalog(list_supported_technologies(), [("name", "name"), ("node", "node"), ("vdd", "vdd"), ("description", "description")])
        return 0
    if args.list_profiles:
        _print_catalog(list_chip_profiles(), [("key", "key"), ("name", "name"), ("summary", "summary")])
        return 0
    if args.list_ips:
        _print_catalog(list_reusable_ips(), [("key", "key"), ("domain", "domain"), ("category", "category"), ("name", "name")])
        return 0
    if args.list_vips:
        _print_catalog(list_verification_ips(), [("key", "key"), ("protocol", "protocol"), ("name", "name")])
        return 0
    if args.list_subsystems:
        _print_catalog(list_digital_subsystems(), [("key", "key"), ("name", "name"), ("description", "description")])
        return 0

    if not args.name:
        parser.error("--name is required unless a list option is used")
    if args.arch and args.profile:
        parser.error("Use either --arch or --profile, not both in the same command")

    designs_dir = PROJECT_ROOT / "designs"
    design_dir = designs_dir / args.name
    design_dir.mkdir(parents=True, exist_ok=True)
    library_context: dict[str, Any] = {}

    # Parse architecture or use defaults
    if args.arch and os.path.exists(args.arch):
        with open(args.arch) as f:
            arch = yaml.safe_load(f)
        blocks = {b["name"]: b for b in arch.get("blocks", [])}
        technology = arch.get("chip", {}).get("technology", args.tech)
        library_context = {
            "chip_profile": arch.get("chip_profile", {}),
            "reusable_ips": arch.get("reusable_ips", []),
            "verification_ips": arch.get("verification_ips", []),
            "digital_subsystems": arch.get("digital_subsystems", []),
        }
        if arch.get("chip", {}).get("profile"):
            library_context["chip_profile"] = {
                "key": arch["chip"].get("profile"),
                "name": arch["chip"].get("profile"),
                "summary": arch["chip"].get("profile_summary", ""),
                "technology_support": arch["chip"].get("technology_support", []),
            }
        if arch.get("design_manifest"):
            library_context["design_manifest"] = arch["design_manifest"]
    elif args.profile:
        technology = args.tech
        library_context = compose_chip_profile(
            profile_key=args.profile,
            design_name=args.name,
            technology=technology,
            include_ips=args.include_ip,
            exclude_ips=args.exclude_ip,
        )
        blocks = library_context["blocks"]
    else:
        technology = args.tech
        if args.blocks:
            blocks = {name: DEFAULT_BLOCKS.get(name, {"type": "analog", "ports": ["VDD", "GND"]})
                      for name in args.blocks}
        else:
            blocks = DEFAULT_BLOCKS

    print(f"Creating design '{args.name}' with {len(blocks)} blocks...")
    print(f"Technology: {technology}")

    # Create directories
    (design_dir / "blocks").mkdir(exist_ok=True)
    (design_dir / "rtl").mkdir(exist_ok=True)
    (design_dir / "top").mkdir(exist_ok=True)

    # Generate each block
    for block_name, block_info in blocks.items():
        print(f"  Generating block: {block_name}")
        block_type = _normalize_block_type(block_info)
        create_block_spec(block_name, block_info, design_dir, technology)
        _content, supports_subckt_testbench = create_block_netlist(block_name, block_info, design_dir, technology)
        if block_type in {"analog", "mixed"} and supports_subckt_testbench:
            create_testbench(block_name, block_info, design_dir, technology)
            create_simulate_script(block_name, design_dir)
        create_report_template(block_name, design_dir)

    # Create design index
    create_design_index(args.name, blocks, design_dir)

    # Create architecture.yaml
    arch_data = {
        "chip": {
            "name": args.name.upper(),
            "technology": technology,
            "profile": library_context.get("chip_profile", {}).get("key", ""),
            "profile_summary": library_context.get("chip_profile", {}).get("summary", ""),
            "technology_support": library_context.get("chip_profile", {}).get("technology_support", []),
        },
        "chip_profile": library_context.get("chip_profile", {}),
        "reusable_ips": library_context.get("reusable_ips", []),
        "verification_ips": library_context.get("verification_ips", []),
        "digital_subsystems": library_context.get("digital_subsystems", []),
        "design_manifest": library_context.get("design_manifest", {}),
        "blocks": [{"name": n, **info} for n, info in blocks.items()],
    }
    with open(design_dir / "architecture.yaml", "w") as f:
        yaml.dump(arch_data, f, default_flow_style=False, sort_keys=False)

    create_design_reference_template(args.name, blocks, design_dir, technology, library_context=library_context)

    print(f"\nDesign created at: {design_dir}")
    print(f"See {design_dir / '00_INDEX.md'} for navigation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
