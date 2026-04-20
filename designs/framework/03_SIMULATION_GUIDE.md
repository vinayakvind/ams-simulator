# 03 - Simulation Guide

## Simulating and Verifying Blocks

### Supported Analysis Types

| Analysis | Engine | Purpose |
|----------|--------|---------|
| DC OP | AnalogEngine | Operating point, bias verification |
| DC Sweep | AnalogEngine | Line/load regulation, transfer curves |
| AC | AnalogEngine | Frequency response, PSRR, gain |
| Transient | AnalogEngine | Startup, load steps, time-domain |
| Digital | DigitalEngine | Logic verification, timing |
| Mixed-Signal | MixedSignalEngine | A/D interface, full chip |

### Simulation Script Usage

```bash
# DC operating point
python designs/framework/scripts/simulate_block.py \
    --design lin_asic --block bandgap --analysis dc

# AC analysis
python designs/framework/scripts/simulate_block.py \
    --design lin_asic --block bandgap --analysis ac \
    --fstart 1 --fstop 1e9 --points 100

# Transient
python designs/framework/scripts/simulate_block.py \
    --design lin_asic --block bandgap --analysis tran \
    --tstop 50e-6 --tstep 10e-9
```

### Building a Testbench

Every block needs a testbench that wraps the subcircuit with:

1. **Supply voltages** - VDD, GND, and any references
2. **Model declarations** - `.MODEL` for all device types
3. **Stimulus** - Input signals (PULSE, SIN, DC)
4. **Load** - Realistic output loading
5. **Analysis commands** - `.DC`, `.AC`, `.TRAN`

Example testbench for bandgap:

```spice
* Bandgap Reference Testbench
.include bandgap.spice

* Models
.MODEL NMOS_3P3 NMOS (VTO=0.5 KP=120u LAMBDA=0.01 GAMMA=0.4 PHI=0.8)
.MODEL PMOS_3P3 PMOS (VTO=-0.5 KP=40u LAMBDA=0.01 GAMMA=0.4 PHI=0.8)
.MODEL NPN_VERT NPN (IS=1e-15 BF=100 BR=1)

* Supply
V_VDD VDD 0 DC 3.3
V_EN EN 0 DC 3.3

* DUT
X1 VDD VREF 0 EN BANDGAP_REF

* Load
R_LOAD VREF 0 100k

* Analysis
.OP
.DC V_VDD 1.8 5.5 0.1
.AC DEC 50 1 1G
.TRAN 10n 50u

.end
```

### Engine Capabilities and Limitations

**AnalogEngine supports:**
- R, C, L, V, I (DC, PULSE, SIN sources)
- MOSFET Level-1 (NMOS, PMOS) with body effect
- BJT Ebers-Moll (NPN, PNP)
- Diode exponential model
- VCVS (E), VCCS (G)
- Coupled inductors (K)
- Newton-Raphson with source stepping for convergence

**Best practices for convergence:**
- Keep circuits to < 20 active devices per analysis
- Use explicit `.MODEL` declarations
- Provide reasonable W/L ratios (not extreme)
- For PMOS: ensure gate can be pulled below VDD - |Vtp| at startup
- For feedback loops: add startup paths or test open-loop first
- Use source stepping (automatic in engine) for multi-transistor circuits

**DigitalEngine supports:**
- Gate-level Verilog: and, or, nand, nor, xor, xnor, not, buf
- 4-state logic: 0, 1, X, Z
- Event-driven simulation with propagation delay
- Waveform recording

### Result Verification

After simulation, verify results against spec:

```python
from simulator.engine.analog_engine import AnalogEngine, DCAnalysis

engine = AnalogEngine()
engine.load_netlist(netlist)
results = engine.solve_dc()

# Check specs
vref = results.get('V(VREF)', 0)
assert 1.17 < vref < 1.23, f"VREF={vref} out of spec (1.2V ± 2%)"
```

### Automated verification via script:

```bash
python designs/framework/scripts/verify_block.py \
    --design lin_asic --block bandgap
```

This reads `spec.yaml`, runs simulations, and generates `REPORT.md`.
