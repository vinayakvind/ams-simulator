"""Simulate ldo_analog block."""
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
    block_path = Path(__file__).parent / "ldo_analog.spice"
    with open(block_path) as f:
        block_netlist = f.read()
    
    engine.load_netlist(block_netlist)
    results = engine.solve_dc()
    
    print(f"DC Operating Point - ldo_analog")
    print("=" * 40)
    for k, v in sorted(results.items()):
        if "V(" in k:
            print(f"  {k} = {v:.6f} V")
    
    return results

if __name__ == "__main__":
    run_dc()
