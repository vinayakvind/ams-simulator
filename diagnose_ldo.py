"""Diagnostic script to find exact LDO simulation failure."""
import sys, traceback
import numpy as np

sys.path.insert(0, ".")

from simulator.engine.analog_engine import AnalogEngine, TransientAnalysis, DCAnalysis

netlist = open("examples/analog_blocks/ldo_regulator.spice").read()
engine = AnalogEngine()
engine.load_netlist(netlist)

# Check if models were loaded
print("Models in engine:")
for name, m in engine._models.items():
    mtype = m.get("type", "?")
    print(f"  {name}: type={mtype}")

# Check what model each MOSFET gets
print("\nMOSFET model resolution:")
for elem in engine._elements:
    if elem.name[0].upper() == "M":
        model_name = elem.model or "NMOS_DEFAULT"
        found = engine._models.get(model_name,
                    engine._models.get(model_name.upper(),
                        engine._models.get("NMOS_DEFAULT")))
        mtype = found.get("type", "?") if found else "MISSING"
        print(f"  {elem.name}: model_ref='{model_name}' -> resolved type='{mtype}'")

# Try DC OP first
print("\n=== Running DC Operating Point ===")
try:
    dc = DCAnalysis(engine)
    results = dc.run({"type": "op"})
    if results:
        for k, v in results.items():
            if isinstance(v, (float, int, np.floating)):
                print(f"  {k} = {v:.6f}")
            elif isinstance(v, np.ndarray) and v.size == 1:
                print(f"  {k} = {float(v):.6f}")
    else:
        print("  DC OP returned None/empty")
except Exception as ex:
    print(f"DC OP failed: {ex}")
    traceback.print_exc()

# Try transient
print("\n=== Running Transient ===")
try:
    engine2 = AnalogEngine()
    engine2.load_netlist(netlist)
    tran = TransientAnalysis(engine2)
    results = tran.run({"tstep": 1e-6, "tstop": 50e-6, "tstart": 0})
    if results:
        print(f"  Result keys: {list(results.keys())}")
        for k, v in results.items():
            if isinstance(v, np.ndarray):
                print(f"  {k}: min={np.min(v):.4f} max={np.max(v):.4f} final={v[-1]:.4f}")
    else:
        print("  Transient returned None/empty")
except Exception as ex:
    print(f"Transient failed: {ex}")
    traceback.print_exc()
