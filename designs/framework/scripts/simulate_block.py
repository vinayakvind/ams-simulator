"""
Simulate a single block from a design.

Usage:
    python designs/framework/scripts/simulate_block.py --design lin_asic --block bandgap --analysis dc
    python designs/framework/scripts/simulate_block.py --design lin_asic --block bandgap --analysis tran --tstop 50e-6
"""

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from simulator.engine.analog_engine import AnalogEngine, ACAnalysis, TransientAnalysis


BASE_MODELS = {
    "NMOS_3P3": {"kind": "NMOS", "VTO": 0.50, "KP": 120e-6, "LAMBDA": 0.01, "GAMMA": 0.4, "PHI": 0.8},
    "PMOS_3P3": {"kind": "PMOS", "VTO": -0.50, "KP": 40e-6, "LAMBDA": 0.01, "GAMMA": 0.4, "PHI": 0.8},
    "PMOS_HV": {"kind": "PMOS", "VTO": -0.80, "KP": 20e-6, "LAMBDA": 0.005, "GAMMA": 0.35, "PHI": 0.8},
    "NPN_VERT": {"kind": "NPN", "IS": 1e-15, "BF": 100, "BR": 1},
    "D_CLAMP": {"kind": "D", "IS": 1e-14, "N": 1.0},
}

CORNER_PROFILES = {
    "TT": {"nmos_speed": 1.00, "pmos_speed": 1.00, "nmos_vth_shift": 0.00, "pmos_vth_shift": 0.00, "lambda_scale": 1.00},
    "FF": {"nmos_speed": 1.18, "pmos_speed": 1.18, "nmos_vth_shift": -0.04, "pmos_vth_shift": -0.04, "lambda_scale": 0.92},
    "SS": {"nmos_speed": 0.84, "pmos_speed": 0.84, "nmos_vth_shift": 0.04, "pmos_vth_shift": 0.04, "lambda_scale": 1.08},
    "FS": {"nmos_speed": 1.18, "pmos_speed": 0.84, "nmos_vth_shift": -0.04, "pmos_vth_shift": 0.04, "lambda_scale": 1.00},
    "SF": {"nmos_speed": 0.84, "pmos_speed": 1.18, "nmos_vth_shift": 0.04, "pmos_vth_shift": -0.04, "lambda_scale": 1.00},
}

_VALUE_RE = re.compile(r"^([+-]?\d*\.?\d+(?:[eE][+-]?\d+)?)([a-zA-Z]+)?$")
_SUFFIXES = {
    "t": 1e12,
    "g": 1e9,
    "meg": 1e6,
    "k": 1e3,
    "m": 1e-3,
    "u": 1e-6,
    "n": 1e-9,
    "p": 1e-12,
    "f": 1e-15,
}


def _format_spice_number(value: float) -> str:
    return f"{value:.6g}"


def _parse_spice_value(token: str) -> float:
    match = _VALUE_RE.match(token.strip())
    if not match:
        raise ValueError(f"Unsupported SPICE value: {token}")
    number = float(match.group(1))
    suffix = (match.group(2) or "").lower()
    if not suffix:
        return number
    if suffix in _SUFFIXES:
        return number * _SUFFIXES[suffix]
    if suffix[:1] in _SUFFIXES:
        return number * _SUFFIXES[suffix[:1]]
    return number


def _build_model_cards(corner: str = "TT", temperature_c: float = 27.0) -> str:
    profile = CORNER_PROFILES[corner.upper()]
    temp_delta = temperature_c - 27.0
    mobility_scale = max(0.55, 1.0 - 0.0025 * temp_delta)

    lines = [f"* Generic corner wrapper: {corner.upper()} @ {temperature_c:.1f}C"]
    for model_name, spec in BASE_MODELS.items():
        kind = spec["kind"]
        if kind in {"NMOS", "PMOS"}:
            speed_key = "nmos_speed" if kind == "NMOS" else "pmos_speed"
            shift_key = "nmos_vth_shift" if kind == "NMOS" else "pmos_vth_shift"
            kp = spec["KP"] * profile[speed_key] * mobility_scale
            vth_mag = abs(spec["VTO"]) + profile[shift_key] - 0.001 * temp_delta
            vth_mag = max(0.15, vth_mag)
            vto = vth_mag if kind == "NMOS" else -vth_mag
            lambda_value = spec["LAMBDA"] * profile["lambda_scale"]
            lines.append(
                f".MODEL {model_name} {kind} (VTO={_format_spice_number(vto)} "
                f"KP={_format_spice_number(kp)} LAMBDA={_format_spice_number(lambda_value)} "
                f"GAMMA={_format_spice_number(spec['GAMMA'])} PHI={_format_spice_number(spec['PHI'])})"
            )
        elif kind == "NPN":
            bf = spec["BF"] * max(0.8, min(1.2, mobility_scale))
            lines.append(
                f".MODEL {model_name} NPN (IS={_format_spice_number(spec['IS'])} BF={_format_spice_number(bf)} BR={_format_spice_number(spec['BR'])})"
            )
        else:
            lines.append(
                f".MODEL {model_name} D (IS={_format_spice_number(spec['IS'])} N={_format_spice_number(spec['N'])})"
            )
    return "\n".join(lines)


def _scale_passives(netlist: str, temperature_c: float) -> str:
    temp_delta = temperature_c - 27.0
    resistor_scale = max(0.85, 1.0 + 0.001 * temp_delta)
    capacitor_scale = max(0.90, 1.0 + 0.0002 * temp_delta)
    scaled_lines: list[str] = []
    for line in netlist.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("*", ".", "+")):
            scaled_lines.append(line)
            continue
        parts = stripped.split()
        if len(parts) >= 4 and parts[0][0].upper() in {"R", "C"}:
            scale = resistor_scale if parts[0][0].upper() == "R" else capacitor_scale
            try:
                parts[3] = _format_spice_number(_parse_spice_value(parts[3]) * scale)
                prefix = line[: len(line) - len(stripped)]
                line = prefix + " ".join(parts)
            except ValueError:
                pass
        scaled_lines.append(line)
    return "\n".join(scaled_lines)


def _load_design_architecture(design_dir: Path) -> dict[str, Any]:
    architecture_path = design_dir / f"{design_dir.name}_architecture.json"
    if not architecture_path.exists():
        return {}
    try:
        return json.loads(architecture_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _architecture_supplies(design_dir: Path) -> dict[str, float]:
    architecture = _load_design_architecture(design_dir)
    raw_supplies = architecture.get("supplies", {})

    def _as_float(value: Any, fallback: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    return {
        "vbat_input": _as_float(raw_supplies.get("vbat_input"), 12.0),
        "vdd_lin": _as_float(raw_supplies.get("vdd_lin"), 5.0),
        "vdd_analog": _as_float(raw_supplies.get("vdd_analog"), 3.3),
        "vdd_digital": _as_float(raw_supplies.get("vdd_digital"), 1.8),
        "vref": 1.2,
    }


def _default_vin_voltage(block_name: str, supplies: dict[str, float]) -> float:
    block_name = block_name.lower()
    if block_name == "ldo_analog":
        return supplies["vbat_input"]
    if block_name == "ldo_digital":
        return supplies["vdd_analog"]
    if block_name == "ldo_lin":
        return supplies["vbat_input"]
    if "lin" in block_name:
        return supplies["vbat_input"]
    return supplies["vdd_lin"]


def _default_output_load_resistance(block_name: str, supplies: dict[str, float]) -> Optional[float]:
    del block_name
    del supplies
    return 100_000.0


def build_netlist_with_wrapper(block_name: str, design_dir: Path, analysis: str,
                                tstop: float = 1e-6, tstep: float = 10e-9,
                                corner: str = "TT", temperature_c: float = 27.0) -> tuple[str, list[str]]:
    """Build a complete netlist by wrapping the block with models and supplies."""
    block_path_candidates = {
        "bandgap": [
            design_dir / "blocks" / "bandgap_ref.spice",
            design_dir / "blocks" / "bandgap" / "bandgap.spice",
        ],
        "ldo_analog": [
            design_dir / "blocks" / "ldo_analog.spice",
            design_dir / "blocks" / "ldo_analog" / "ldo_analog.spice",
        ],
        "ldo_digital": [
            design_dir / "blocks" / "ldo_digital.spice",
            design_dir / "blocks" / "ldo_digital" / "ldo_digital.spice",
        ],
        "ldo_lin": [
            design_dir / "blocks" / "ldo_lin.spice",
            design_dir / "blocks" / "ldo_lin" / "ldo_lin.spice",
        ],
        "lin_transceiver": [
            design_dir / "blocks" / "lin_transceiver.spice",
            design_dir / "blocks" / "lin_transceiver" / "lin_transceiver.spice",
        ],
    }
    default_candidates = [
        design_dir / "blocks" / f"{block_name}.spice",
        design_dir / "blocks" / block_name / f"{block_name}.spice",
    ]
    block_spice = None
    for candidate in block_path_candidates.get(block_name, default_candidates):
        if candidate.exists():
            block_spice = candidate
            break
    supplies = _architecture_supplies(design_dir)

    if block_spice is None:
        # Try to generate via BlockBuilder
        try:
            from simulator.agents.block_builder import BlockBuilder
            builder = BlockBuilder()
            result = builder.build_block(block_name)
            block_content = result.get("netlist", "")
        except Exception:
            raise FileNotFoundError(f"Block netlist not found for {block_name}")
    else:
        block_content = block_spice.read_text()

    # Extract subcircuit name and ports from the block
    subckt_name = block_name.upper()
    ports = []
    for line in block_content.splitlines():
        if line.strip().upper().startswith(".SUBCKT"):
            parts = line.split()
            if len(parts) > 1:
                subckt_name = parts[1]
                ports = parts[2:]
            break

    # Build supply connections
    supply_lines: list[str] = []
    port_connections = []
    has_vout = any(pp.upper() == "VOUT" for pp in ports)
    for p in ports:
        p_upper = p.upper()
        if p_upper in ("VDD", "VDD_IO"):
            if analysis == "psrr":
                supply_lines.append(f"V_VDD VDD 0 DC {supplies['vdd_analog']} AC 1")
            else:
                supply_lines.append(f"V_VDD VDD 0 DC {supplies['vdd_analog']}")
            port_connections.append("VDD")
        elif p_upper == "VBAT":
            if analysis == "psrr":
                supply_lines.append(f"V_VBAT VBAT 0 DC {supplies['vbat_input']} AC 1")
            else:
                supply_lines.append(f"V_VBAT VBAT 0 DC {supplies['vbat_input']}")
            port_connections.append("VBAT")
        elif p_upper in ("GND", "VSS", "AVSS"):
            port_connections.append("0")
        elif p_upper == "VIN":
            vin_val = _default_vin_voltage(block_name, supplies)
            if analysis == "psrr":
                supply_lines.append(f"V_VIN VIN 0 DC {vin_val} AC 1")
            else:
                supply_lines.append(f"V_VIN VIN 0 DC {vin_val}")
            port_connections.append("VIN")
        elif p_upper == "EN":
            supply_lines.append("V_EN EN 0 DC 3.3")
            port_connections.append("EN")
        elif p_upper == "SLP_N":
            supply_lines.append("V_SLP SLP_N 0 DC 3.3")
            port_connections.append("SLP_N")
        elif p_upper == "TXD":
            supply_lines.append("V_TXD TXD 0 DC 3.3")
            port_connections.append("TXD")
        elif p_upper == "VREF" and has_vout:
            supply_lines.append(f"V_VREF VREF 0 DC {supplies['vref']}")
            port_connections.append("VREF")
        elif p_upper.startswith("V"):
            port_connections.append(p)
        else:
            port_connections.append(p)

    supply_section = "\n".join(supply_lines)
    instance = f"X_DUT {' '.join(port_connections)} {subckt_name}"

    # Add load on output nodes
    load_lines = []
    vout_load_resistance = _default_output_load_resistance(block_name, supplies)
    for p in ports:
        p_upper = p.upper()
        if p_upper == "VOUT" and p in port_connections and vout_load_resistance is not None:
            load_lines.append(f"R_LOAD_{p} {p} 0 {_format_spice_number(vout_load_resistance)}")
        elif p_upper == "VREF" and p in port_connections:
            load_lines.append(f"R_LOAD_{p} {p} 0 100k")

    load_section = "\n".join(load_lines)

    netlist = f"""* Testbench: {block_name} ({analysis} analysis)
{_build_model_cards(corner=corner, temperature_c=temperature_c)}

{block_content}

* Supplies
{supply_section}

* DUT
{instance}

* Loads
{load_section}

.end
"""
    return _scale_passives(netlist, temperature_c), ports


def run_dc(engine: AnalogEngine) -> dict:
    """Run DC operating point."""
    results = engine.solve_dc()
    results["dc_converged"] = bool(getattr(engine, "_last_dc_converged", True))
    print("\nDC Operating Point Results")
    print("=" * 40)
    print(f"  converged:           {results['dc_converged']}")
    for k, v in sorted(results.items()):
        if "V(" in k:
            print(f"  {k:20s} = {v:12.6f} V")
    return results


def run_ac(engine: AnalogEngine, fstart: float, fstop: float, points: int) -> dict:
    """Run AC analysis."""
    ac = ACAnalysis(engine)
    results = ac.run({
        "fstart": fstart,
        "fstop": fstop,
        "points": points,
    })
    results["dc_converged"] = bool(getattr(engine, "_last_dc_converged", True))
    print("\nAC Analysis Results")
    print("=" * 40)
    print(f"  dc_converged:        {results['dc_converged']}")
    for k in sorted(results.keys()):
        if k.startswith("mag("):
            vals = results[k]
            if vals:
                print(f"  {k}: min={min(vals):.4f}, max={max(vals):.4f}")
    return results


def _resolve_output_node(results: dict, candidates: list[str]) -> str:
    lower_map = {key.lower(): key for key in results.keys()}
    for candidate in candidates:
        key = f"mag({candidate})".lower()
        if key in lower_map:
            return lower_map[key][4:-1]
    raise KeyError(f"Could not find output node in AC results for candidates: {', '.join(candidates)}")


def _sample_by_frequency(frequencies: list[float], values: list[float], target: float) -> float:
    index = min(range(len(frequencies)), key=lambda i: abs(frequencies[i] - target))
    return float(values[index])


def _make_json_safe(value: Any) -> Any:
    """Convert simulation results into JSON-safe nested data."""
    if hasattr(value, "tolist"):
        return _make_json_safe(value.tolist())
    if isinstance(value, dict):
        return {str(key): _make_json_safe(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_make_json_safe(item) for item in value]
    if isinstance(value, (str, bool)) or value is None:
        return value
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return str(value)
        return float(value) if isinstance(value, float) else int(value)
    return str(value)


def run_psrr(engine: AnalogEngine, fstart: float, fstop: float, points: int, output_candidates: list[str]) -> dict:
    """Run PSRR analysis by injecting 1V AC ripple on the block supply source."""
    ac = ACAnalysis(engine)
    results = ac.run({
        "fstart": fstart,
        "fstop": fstop,
        "points": points,
    })
    results["dc_converged"] = bool(getattr(engine, "_last_dc_converged", True))
    results["analysis_valid"] = results["dc_converged"]

    output_node = _resolve_output_node(results, output_candidates)
    magnitude_key = f"mag({output_node})"
    frequencies = results.get("frequency", [])
    output_mag = results.get(magnitude_key, [])
    psrr_db = [-20.0 * math.log10(max(value, 1e-18)) for value in output_mag]
    results["psrr_output_node"] = output_node
    results["psrr_db"] = psrr_db
    if frequencies and psrr_db:
        summary = {}
        for target in (10.0, 1e2, 1e3, 1e4, 1e5, 1e6):
            if frequencies[0] <= target <= frequencies[-1]:
                label = str(int(target)) if target < 1000 else f"{int(target / 1000)}k"
                summary[f"psrr_at_{label}_db"] = _sample_by_frequency(frequencies, psrr_db, target)
        results["psrr_summary"] = summary

    print("\nPSRR Analysis Results")
    print("=" * 40)
    print(f"  dc_converged:        {results['dc_converged']}")
    print(f"  Output node: {output_node}")
    if results.get("psrr_summary"):
        for name, value in sorted(results["psrr_summary"].items()):
            print(f"  {name:20s} = {value:8.2f} dB")
    return results


def run_tran(engine: AnalogEngine, tstop: float, tstep: float) -> dict:
    """Run transient analysis."""
    tran = TransientAnalysis(engine)
    results = tran.run({
        "tstop": tstop,
        "tstep": tstep,
    })
    print("\nTransient Analysis Results")
    print("=" * 40)
    print(f"  Time points: {len(results.get('time', []))}")
    for k, v in sorted(results.items()):
        if k.startswith("V(") and isinstance(v, list) and v:
            print(f"  {k:20s}: min={min(v):10.6f}, max={max(v):10.6f}")
    return results


def main():
    parser = argparse.ArgumentParser(description="Simulate a block")
    parser.add_argument("--design", required=True, help="Design name")
    parser.add_argument("--block", required=True, help="Block name")
    parser.add_argument("--analysis", default="dc", choices=["dc", "ac", "tran", "psrr"],
                        help="Analysis type")
    parser.add_argument("--tstop", type=float, default=1e-6, help="Transient stop time")
    parser.add_argument("--tstep", type=float, default=10e-9, help="Transient time step")
    parser.add_argument("--fstart", type=float, default=1.0, help="AC start frequency")
    parser.add_argument("--fstop", type=float, default=1e9, help="AC stop frequency")
    parser.add_argument("--points", type=int, default=50, help="AC frequency points")
    parser.add_argument("--corner", default="TT", choices=sorted(CORNER_PROFILES.keys()), help="Generic process corner wrapper")
    parser.add_argument("--temperature", type=float, default=27.0, help="Temperature for passive and model scaling")
    parser.add_argument("--output-node", help="Override output node for PSRR analysis")
    parser.add_argument("--output", help="Output JSON file for results")
    args = parser.parse_args()

    design_dir = PROJECT_ROOT / "designs" / args.design

    print(f"Simulating {args.block} from {args.design} ({args.analysis} analysis)")

    # Build netlist
    netlist, ports = build_netlist_with_wrapper(
        args.block,
        design_dir,
        args.analysis,
        args.tstop,
        args.tstep,
        corner=args.corner,
        temperature_c=args.temperature,
    )

    # Create engine and load
    engine = AnalogEngine()
    engine.load_netlist(netlist)

    # Run analysis
    if args.analysis == "dc":
        results = run_dc(engine)
    elif args.analysis == "ac":
        results = run_ac(engine, args.fstart, args.fstop, args.points)
    elif args.analysis == "tran":
        results = run_tran(engine, args.tstop, args.tstep)
    elif args.analysis == "psrr":
        output_candidates = [args.output_node] if args.output_node else []
        for candidate in ("VOUT", "VREF", "RXD"):
            if candidate in ports and candidate not in output_candidates:
                output_candidates.append(candidate)
        results = run_psrr(engine, args.fstart, args.fstop, args.points, output_candidates)

    results["context"] = {
        "design": args.design,
        "block": args.block,
        "analysis": args.analysis,
        "corner": args.corner,
        "temperature_c": args.temperature,
    }

    # Save results if requested
    if args.output:
        serializable = _make_json_safe(results)

        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=2)
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
