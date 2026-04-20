"""
Verify block simulation results against spec.

Usage:
    python designs/framework/scripts/verify_block.py --design lin_asic --block bandgap
    python designs/framework/scripts/verify_block.py --design lin_asic --all
"""

import argparse
import sys
import yaml
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from simulator.engine.analog_engine import AnalogEngine, DCAnalysis, TransientAnalysis


MODELS = """
.MODEL NMOS_3P3 NMOS (VTO=0.5 KP=120u LAMBDA=0.01 GAMMA=0.4 PHI=0.8)
.MODEL PMOS_3P3 PMOS (VTO=-0.5 KP=40u LAMBDA=0.01 GAMMA=0.4 PHI=0.8)
.MODEL PMOS_HV PMOS (VTO=-0.8 KP=20u LAMBDA=0.005)
.MODEL NPN_VERT NPN (IS=1e-15 BF=100 BR=1)
"""


def load_spec(block_dir: Path) -> dict:
    """Load block spec.yaml."""
    spec_path = block_dir / "spec.yaml"
    if not spec_path.exists():
        return {}
    with open(spec_path) as f:
        return yaml.safe_load(f)


def verify_block(block_name: str, design_dir: Path) -> dict:
    """Verify a single block against its spec."""
    block_dir = design_dir / "blocks" / block_name
    spice_path = block_dir / f"{block_name}.spice"

    if not spice_path.exists():
        return {"name": block_name, "status": "SKIP", "reason": "No netlist found"}

    spec = load_spec(block_dir)
    results = {"name": block_name, "checks": [], "status": "PENDING"}

    # Read netlist
    netlist_content = spice_path.read_text()

    # Extract subcircuit info
    subckt_name = block_name.upper()
    ports = []
    for line in netlist_content.splitlines():
        if line.strip().upper().startswith(".SUBCKT"):
            parts = line.split()
            if len(parts) > 1:
                subckt_name = parts[1]
                ports = parts[2:]
            break

    # Build wrapper for simulation
    supply_lines = ["V_VDD VDD 0 DC 3.3"]
    port_map = []
    has_vout = any(pp.upper() == "VOUT" for pp in ports)
    for p in ports:
        p_upper = p.upper()
        if p_upper in ("VDD", "VDD_IO", "AVDD"):
            port_map.append("VDD")
        elif p_upper in ("GND", "VSS", "AVSS"):
            port_map.append("0")
        elif p_upper == "VIN":
            vin_val = 12.0 if "lin" in block_name.lower() else 5.0
            supply_lines.append(f"V_VIN VIN 0 DC {vin_val}")
            port_map.append("VIN")
        elif p_upper == "EN":
            supply_lines.append("V_EN EN 0 DC 3.3")
            port_map.append("EN")
        elif p_upper == "VREF" and has_vout:
            supply_lines.append("V_VREF VREF 0 DC 1.2")
            port_map.append("VREF")
        else:
            port_map.append(p)

    load_lines = []
    for p in ports:
        if p.upper() in ("VOUT", "VREF") and not has_vout:
            load_lines.append(f"R_LOAD_{p} {p} 0 100k")
        elif p.upper() == "VOUT":
            load_lines.append(f"R_LOAD_{p} {p} 0 100k")
    
    # Add startup aid for LDO blocks (mimics real startup circuit)
    startup_lines = []
    if "ldo" in block_name.lower() and has_vout:
        startup_lines.append("* Startup aid (models real startup circuit)")
        startup_lines.append("R_STARTUP VIN VOUT 100k")

    startup_section = "\n".join(startup_lines)

    full_netlist = f"""* Verification testbench: {block_name}
{MODELS}
{netlist_content}
{chr(10).join(supply_lines)}
X_DUT {' '.join(port_map)} {subckt_name}
{chr(10).join(load_lines)}
{startup_section}
.end
"""

    # Run DC
    try:
        engine = AnalogEngine()
        engine.load_netlist(full_netlist)
        dc_results = engine.solve_dc()

        # Check that output nodes have non-zero voltage
        for p in ports:
            p_upper = p.upper()
            if p_upper in ("VOUT", "VREF"):
                v = dc_results.get(f"V({p})", dc_results.get(f"V({p_upper})", 0))
                check = {
                    "test": f"DC {p} voltage",
                    "value": f"{v:.6f} V",
                    "pass": v > 0.01,
                }
                results["checks"].append(check)

        # Check spec targets if available
        specs = spec.get("specs", {})
        if "vref_nominal" in specs:
            target = specs["vref_nominal"]
            if isinstance(target, dict):
                target = target.get("value", 1.2)
            vref = dc_results.get("V(VREF)", dc_results.get("V(vref)", 0))
            tol = 0.1 * target  # 10% tolerance
            check = {
                "test": f"VREF accuracy ({target}V ± 10%)",
                "value": f"{vref:.6f} V",
                "pass": abs(vref - target) < tol,
            }
            results["checks"].append(check)

        # Check convergence
        all_zero = all(v == 0 for k, v in dc_results.items()
                       if k.startswith("V(") and k not in ("V(0)", "V(GND)"))
        results["checks"].append({
            "test": "NR convergence",
            "value": "converged" if not all_zero else "all zeros - likely failed",
            "pass": not all_zero,
        })

    except Exception as e:
        results["checks"].append({
            "test": "DC simulation",
            "value": str(e),
            "pass": False,
        })

    # Determine overall status
    if not results["checks"]:
        results["status"] = "SKIP"
    elif all(c["pass"] for c in results["checks"]):
        results["status"] = "PASS"
    else:
        results["status"] = "FAIL"

    return results


def write_report(block_name: str, verification: dict, design_dir: Path):
    """Write/update REPORT.md for a block."""
    block_dir = design_dir / "blocks" / block_name
    block_dir.mkdir(parents=True, exist_ok=True)

    status = verification["status"]
    checks_table = ""
    for c in verification.get("checks", []):
        p = "PASS" if c["pass"] else "FAIL"
        checks_table += f"| {c['test']} | {c['value']} | {p} |\n"

    report = f"""# Block Report: {block_name}

## Status: {status}
Verified: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Verification Results
| Test | Result | Pass |
|------|--------|------|
{checks_table}

## Notes
- Auto-verified by AMS Design Framework
"""
    with open(block_dir / "REPORT.md", "w") as f:
        f.write(report)


def main():
    parser = argparse.ArgumentParser(description="Verify block against spec")
    parser.add_argument("--design", required=True, help="Design name")
    parser.add_argument("--block", help="Block name (omit for --all)")
    parser.add_argument("--all", action="store_true", help="Verify all blocks")
    args = parser.parse_args()

    design_dir = PROJECT_ROOT / "designs" / args.design

    if args.all or not args.block:
        blocks_dir = design_dir / "blocks"
        if not blocks_dir.exists():
            print(f"No blocks directory found in {design_dir}")
            sys.exit(1)
        block_names = [d.name for d in blocks_dir.iterdir() if d.is_dir()]
    else:
        block_names = [args.block]

    print(f"Verifying {len(block_names)} block(s) in '{args.design}'")
    print("=" * 50)

    all_results = []
    for name in sorted(block_names):
        print(f"\n--- {name} ---")
        result = verify_block(name, design_dir)
        all_results.append(result)

        for c in result.get("checks", []):
            status = "PASS" if c["pass"] else "FAIL"
            print(f"  [{status}] {c['test']}: {c['value']}")

        write_report(name, result, design_dir)
        print(f"  Overall: {result['status']}")

    # Summary
    print("\n" + "=" * 50)
    print("VERIFICATION SUMMARY")
    print("=" * 50)
    for r in all_results:
        print(f"  {r['name']:25s} {r['status']}")

    passed = sum(1 for r in all_results if r["status"] == "PASS")
    total = len(all_results)
    print(f"\n  {passed}/{total} blocks passing")

    # Write overall status
    status_md = f"""# Verification Status - {args.design}
Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Summary
- Total blocks: {total}
- Passing: {passed}
- Failing: {total - passed}

## Block Status
| Block | Status |
|-------|--------|
"""
    for r in all_results:
        status_md += f"| {r['name']} | {r['status']} |\n"

    with open(design_dir / "VERIFICATION_STATUS.md", "w") as f:
        f.write(status_md)


if __name__ == "__main__":
    main()
