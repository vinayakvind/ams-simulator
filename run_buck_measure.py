from simulator.engine.analog_engine import AnalogEngine, TransientAnalysis
import numpy as np
p='examples/standard_circuits/buck_converter.spice'
with open(p,'r',encoding='utf-8') as f:
    net=f.read()
eng=AnalogEngine()
eng.load_netlist(net)
ta=TransientAnalysis(eng)
res=ta.run({'tstop':500e-6,'tstep':100e-9})

time=np.array(res['time'])
vout=np.array(res['V(output)'])
mask=(time>=400e-6)&(time<=500e-6)
print('Vout final:', vout[-1])
print('Vout avg 400-500us:', np.mean(vout[mask]))
print('Vout min/max:', vout.min(), vout.max())
