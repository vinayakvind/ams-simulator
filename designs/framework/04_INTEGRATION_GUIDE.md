# 04 - Integration Guide

## Integrating Blocks into Top-Level

### Integration Steps

1. **Verify each block standalone** — All blocks must pass their individual specs
2. **Create top-level netlist** — Instantiate all subcircuits with proper connectivity
3. **Add pad ring** — Model I/O pads and ESD structures
4. **Power sequencing** — Verify supply ramp order
5. **Signal integrity** — Check analog/digital coupling
6. **Full-chip simulation** — Run top-level transient

### Top-Level Netlist Structure

```spice
* Top-Level: LIN ASIC
* ====================

* Include all block subcircuits
.include blocks/bandgap/bandgap.spice
.include blocks/ldo_analog/ldo_analog.spice
.include blocks/ldo_digital/ldo_digital.spice
.include blocks/ldo_lin/ldo_lin.spice
.include blocks/lin_transceiver/lin_transceiver.spice

* Technology models
.MODEL NMOS_3P3 NMOS (VTO=0.5 KP=120u LAMBDA=0.01)
.MODEL PMOS_3P3 PMOS (VTO=-0.5 KP=40u LAMBDA=0.01)
.MODEL PMOS_HV PMOS (VTO=-0.8 KP=20u LAMBDA=0.005)
.MODEL NPN_VERT NPN (IS=1e-15 BF=100)

* External supplies
V_VBAT VBAT 0 DC 12.0
V_EN_GLOBAL EN_GLOBAL 0 PULSE(0 3.3 1u 100n 100n 100u 200u)

* Block instances
X_BG      VDD_IO VREF GND EN_GLOBAL  BANDGAP_REF
X_LDO_ANA VBAT   VDD_IO GND VREF EN_GLOBAL  LDO_ANALOG
X_LDO_DIG VDD_IO VDD_CORE GND VREF EN_GLOBAL LDO_DIGITAL
X_LDO_LIN VBAT   VDD_LIN GND VREF EN_GLOBAL  LDO_LIN

* Test loads
R_LOAD_IO   VDD_IO   0  200
R_LOAD_CORE VDD_CORE 0  100
R_LOAD_LIN  VDD_LIN  0  500

.end
```

### Mixed-Signal Integration

For chips with both analog and digital:

```python
from simulator.engine.mixed_signal_engine import MixedSignalEngine

ms_engine = MixedSignalEngine()

# Load analog partition
ms_engine.load_analog_netlist(analog_netlist)

# Load digital partition
ms_engine.load_digital_module(verilog_code)

# Define connect modules (A/D, D/A boundaries)
ms_engine.add_connect_module("adc_interface", analog_node="v_sense", 
                              digital_signal="d_sense", threshold=1.65)
ms_engine.add_connect_module("dac_interface", digital_signal="d_ctrl",
                              analog_node="v_ctrl", v_high=3.3, v_low=0.0)

# Run mixed-signal simulation
results = ms_engine.run(tstop=100e-6, tstep=10e-9)
```

### Integration Checklist

- [ ] All blocks pass standalone verification
- [ ] Supply connectivity verified (power tree)
- [ ] Ground connections verified (single ground or split)
- [ ] Signal naming consistent across blocks
- [ ] No floating nodes
- [ ] Decoupling capacitors on each supply domain
- [ ] ESD structures on all I/O pads
- [ ] Power sequencing order correct
- [ ] Clock distribution verified
- [ ] Reset propagation verified
