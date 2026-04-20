"""
Simulate a single block from a design.

Usage:
    python designs/framework/scripts/simulate_block.py --design lin_asic --block bandgap --analysis dc
    python designs/framework/scripts/simulate_block.py --design lin_asic --block bandgap --analysis tran --tstop 50e-6
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from simulator.engine.analog_engine import AnalogEngine, DCAnalysis, ACAnalysis, TransientAnalysis


MODELS = """
.MODEL NMOS_3P3 NMOS (VTO=0.5 KP=120u LAMBDA=0.01 GAMMA=0.4 PHI=0.8)
.MODEL PMOS_3P3 PMOS (VTO=-0.5 KP=40u LAMBDA=0.01 GAMMA=0.4 PHI=0.8)
.MODEL PMOS_HV PMOS (VTO=-0.8 KP=20u LAMBDA=0.005)
.MODEL NPN_VERT NPN (IS=1e-15 BF=100 BR=1)
.MODEL D_CLAMP D (IS=1e-14 N=1.0)
"""


def build_netlist_with_wrapper(block_name: str, design_dir: Path, analysis: str,
                                tstop: float = 1e-6, tstep: float = 10e-9) -> str:
    """Build a complete netlist by wrapping the block with models and supplies."""
    block_dir = design_dir / "blocks" / block_name
    block_spice = block_dir / f"{block_name}.spice"

    if not block_spice.exists():
        # Try to generate via BlockBuilder
        try:
            from simulator.agents.block_builder import BlockBuilder
            builder = BlockBuilder()
            result = builder.build_block(block_name)
            block_content = result.get("netlist", "")
        except Exception:
            raise FileNotFoundError(f"Block netlist not found: {block_spice}")
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
    supply_lines = ["V_VDD VDD 0 DC 3.3", "V_GND_REF GND_REF 0 DC 0"]
    port_connections = []
    has_vout = any(pp.upper() == "VOUT" for pp in ports)
    for p in ports:
        p_upper = p.upper()
        if p_upper in ("VDD", "VDD_IO"):
            port_connections.append("VDD")
        elif p_upper in ("GND", "VSS", "AVSS"):
            port_connections.append("0")
        elif p_upper == "VIN":
            vin_val = 12.0 if "lin" in block_name.lower() else 5.0
            supply_lines.append(f"V_VIN VIN 0 DC {vin_val}")
            port_connections.append("VIN")
        elif p_upper == "EN":
            supply_lines.append("V_EN EN 0 DC 3.3")
            port_connections.append("EN")
        elif p_upper == "VREF" and has_vout:
            supply_lines.append("V_VREF VREF 0 DC 1.2")
            port_connections.append("VREF")
        elif p_upper.startswith("V"):
            port_connections.append(p)
        else:
            port_connections.append(p)

    supply_section = "\n".join(supply_lines)
    instance = f"X_DUT {' '.join(port_connections)} {subckt_name}"

    # Add load on output nodes
    load_lines = []
    for p in ports:
        p_upper = p.upper()
        if p_upper in ("VOUT", "VREF") and p in port_connections:
            load_lines.append(f"R_LOAD_{p} {p} 0 100k")

    load_section = "\n".join(load_lines)

    netlist = f"""* Testbench: {block_name} ({analysis} analysis)
{MODELS}

{block_content}

* Supplies
{supply_section}

* DUT
{instance}

* Loads
{load_section}

.end
"""
    return netlist


def run_dc(engine: AnalogEngine) -> dict:
    """Run DC operating point."""
    results = engine.solve_dc()
    print("\nDC Operating Point Results")
    print("=" * 40)
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
    print("\nAC Analysis Results")
    print("=" * 40)
    for k in sorted(results.keys()):
        if k.startswith("mag("):
            vals = results[k]
            if vals:
                print(f"  {k}: min={min(vals):.4f}, max={max(vals):.4f}")
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
    parser.add_argument("--analysis", default="dc", choices=["dc", "ac", "tran"],
                        help="Analysis type")
    parser.add_argument("--tstop", type=float, default=1e-6, help="Transient stop time")
    parser.add_argument("--tstep", type=float, default=10e-9, help="Transient time step")
    parser.add_argument("--fstart", type=float, default=1.0, help="AC start frequency")
    parser.add_argument("--fstop", type=float, default=1e9, help="AC stop frequency")
    parser.add_argument("--points", type=int, default=50, help="AC frequency points")
    parser.add_argument("--output", help="Output JSON file for results")
    args = parser.parse_args()

    design_dir = PROJECT_ROOT / "designs" / args.design

    print(f"Simulating {args.block} from {args.design} ({args.analysis} analysis)")

    # Build netlist
    netlist = build_netlist_with_wrapper(
        args.block, design_dir, args.analysis, args.tstop, args.tstep
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

    # Save results if requested
    if args.output:
        # Convert numpy arrays to lists for JSON serialization
        serializable = {}
        for k, v in results.items():
            if hasattr(v, "tolist"):
                serializable[k] = v.tolist()
            elif isinstance(v, list):
                serializable[k] = v
            else:
                serializable[k] = float(v) if isinstance(v, (int, float)) else str(v)

        with open(args.output, "w") as f:
            json.dump(serializable, f, indent=2)
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
