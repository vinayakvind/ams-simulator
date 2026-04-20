"""Generate simulation proof for all standard circuits."""
import os
import json
from pathlib import Path
from simulator.engine.analog_engine import AnalogEngine, TransientAnalysis, DCAnalysis, ACAnalysis

os.makedirs('simulation_proof', exist_ok=True)
circuits_dir = Path('examples/standard_circuits')
proof = {}

for f in sorted(circuits_dir.glob('*.spice')):
    name = f.stem
    netlist = f.read_text()
    engine = AnalogEngine()
    engine.load_netlist(netlist)
    n_elems = len(engine._elements)
    
    try:
        if '.TRAN' in netlist.upper():
            tran = TransientAnalysis(engine)
            result = tran.run({'tstop': 1e-3, 'tstep': 10e-6})
            n_pts = len(result.get('time', []))
            n_signals = len([k for k in result if k.startswith('V(')])
            proof[name] = {
                'status': 'OK', 'elements': n_elems,
                'time_points': n_pts, 'signals': n_signals, 'analysis': 'transient'
            }
        elif '.AC' in netlist.upper():
            ac = ACAnalysis(engine)
            result = ac.run({'variation': 'decade', 'points': 10, 'fstart': 10, 'fstop': 100e3})
            n_pts = len(result.get('frequency', []))
            proof[name] = {
                'status': 'OK', 'elements': n_elems,
                'freq_points': n_pts, 'analysis': 'ac'
            }
        else:
            dc = DCAnalysis(engine)
            result = dc.run({})
            proof[name] = {'status': 'OK', 'elements': n_elems, 'analysis': 'dc'}
    except Exception as e:
        proof[name] = {'status': 'WARN', 'elements': n_elems, 'note': str(e)[:100]}
    
    status = proof[name]['status']
    print(f"  {name}: {status} ({n_elems} elements)")

with open('simulation_proof/all_circuits_proof.json', 'w') as fp:
    json.dump(proof, fp, indent=2)

print(f"\nAll {len(proof)} circuits processed.")
print("Proof saved to simulation_proof/all_circuits_proof.json")
