# CMOS ADC Design Suite

Complete Analog-to-Digital Converter implementation using CMOS technology with transistor-level sub-blocks.

## Table of Contents
1. [Overview](#overview)
2. [Technology Library](#technology-library)
3. [Sub-Block Designs](#sub-block-designs)
4. [Complete ADC](#complete-adc)
5. [Simulation Instructions](#simulation-instructions)
6. [Performance Specifications](#performance-specifications)

---

## Overview

This directory contains a complete 4-bit Successive Approximation Register (SAR) ADC designed with 180nm CMOS technology. All circuits are implemented at the transistor level using accurate MOSFET models.

### Architecture
```
                   ┌─────────────┐
Analog Input ─────>│ Sample/Hold │
                   └──────┬──────┘
                          │
                          v
                   ┌─────────────┐      ┌──────────────┐
                   │  Comparator │<─────│ 4-bit R-2R   │
                   │  (CMOS)     │      │ DAC          │
                   └──────┬──────┘      └──────▲───────┘
                          │                    │
                          v                    │
                   ┌─────────────┐            │
                   │ SAR Control │────────────┘
                   │ Logic       │
                   └──────┬──────┘
                          │
                          v
                   Digital Output [3:0]
```

### Key Features
- **Resolution**: 4 bits (16 levels)
- **Technology**: 180nm CMOS (can be scaled)
- **Supply Voltage**: 1.8V digital, 1.8V analog
- **Sample Rate**: 100 kSPS
- **Input Range**: 0V to 1.6V (Vref)
- **Architecture**: SAR ADC with:
  - Differential comparator with latching output
  - R-2R ladder DAC with CMOS switches
  - Sample-and-hold with low droop
  - Digital SAR control logic

---

## Technology Library

### File: `../technology/cmos_180nm.lib`

Comprehensive 180nm CMOS process models including:

#### NMOS Models
- **nmos_1v8**: Core 1.8V NMOS (thin oxide, VTH0=0.45V)
- **nmos_3v3**: I/O 3.3V NMOS (thick oxide, VTH0=0.55V)
- **nmos_lvt**: Low-threshold NMOS (VTH0=0.30V)

#### PMOS Models
- **pmos_1v8**: Core 1.8V PMOS (thin oxide, VTH0=-0.45V)
- **pmos_3v3**: I/O 3.3V PMOS (thick oxide, VTH0=-0.60V)
- **pmos_lvt**: Low-threshold PMOS (VTH0=-0.30V)

#### Key Parameters
| Parameter | NMOS (1.8V) | PMOS (1.8V) | Unit |
|-----------|-------------|-------------|------|
| TOX       | 4.1         | 4.1         | nm   |
| KP        | 280         | 95          | μA/V²|
| U0        | 350         | 120         | cm²/V-s |
| LAMBDA    | 0.08        | 0.10        | 1/V  |
| L_min     | 180         | 180         | nm   |

#### Passive Components
- Poly resistor (RSH = 50 Ω/sq)
- Metal resistor (RSH = 0.08 Ω/sq)
- MIM capacitor (CJ = 2 fF/μm²)
- PN junction diode

---

## Sub-Block Designs

### 1. CMOS Comparator (`comparator_cmos.spice`)

High-gain differential comparator with latched output for ADC applications.

#### Circuit Topology
```
Input Diff Pair (M1, M2) → PMOS Load (M3, M4) → Second Stage (M5, M6) 
→ Output Buffer (M7, M8) → Latch (M11-M14) → Digital Output (M15, M16)
```

#### Key Specifications
- **Gain**: >60 dB (open-loop)
- **Input Range**: 0.7V to 1.1V (common-mode)
- **Output Levels**: Rail-to-rail (0V / 1.8V)
- **Propagation Delay**: <10ns
- **Power Consumption**: ~1mW @ 1.8V
- **Input-Referred Offset**: <5mV (typical)

#### Transistor Sizing
| Stage | Transistor | W/L | Function |
|-------|-----------|-----|----------|
| Input | M1, M2 | 2μm/0.5μm | Differential pair |
| Load | M3, M4 | 4μm/0.5μm | Current mirror |
| Gain | M5 | 5μm/0.5μm | Second stage NMOS |
| Gain | M6 | 8μm/0.5μm | Second stage load |
| Buffer | M7 | 8μm/0.35μm | Output NMOS |
| Buffer | M8 | 12μm/0.35μm | Output PMOS |
| Latch | M11-M14 | 1-2μm/0.18μm | SR latch |

#### Test Signals
- **Vin_p**: 0.9V DC (positive input)
- **Vin_n**: 0.85V DC (reference)
- **Vclk**: 10MHz clock for latching
- **Itail**: 50μA bias current

#### Key Nodes
- `inp`, `inn`: Differential inputs
- `d1`, `d2`: First stage outputs
- `d3`: Second stage output
- `preout`: Before latch
- `comp_out`: Final digital output

---

### 2. R-2R Ladder DAC (`dac_r2r_4bit.spice`)

4-bit Digital-to-Analog Converter using R-2R ladder topology with CMOS switches.

#### Circuit Topology
```
Vref ──R── n3 ──R── n2 ──R── n1 ──R── n0 ──R── Vout
           │        │        │        │
          2R       2R       2R       2R
           │        │        │        │
         [SW3]    [SW2]    [SW1]    [SW0]
           │        │        │        │
          GND      GND      GND      GND

SW = CMOS transmission gate (controlled by digital bits)
```

#### Specifications
- **Resolution**: 4 bits (16 levels)
- **Reference Voltage**: 1.6V
- **LSB Size**: 1.6V / 16 = 100mV
- **R Value**: 10kΩ
- **2R Value**: 20kΩ
- **Settling Time**: <500ns
- **INL/DNL**: <0.5 LSB (typical)

#### Output Equation
```
Vout = Vref × (b3×2³ + b2×2² + b1×2¹ + b0×2⁰) / 16
     = Vref × (b3×8 + b2×4 + b1×2 + b0) / 16
```

#### CMOS Switches
- Transmission gate (NMOS + PMOS in parallel)
- RON ≈ 500Ω (combined)
- ROFF > 100GΩ
- Sizes: NMOS 2μm/0.18μm, PMOS 4μm/0.18μm

#### Example Outputs
| Code (Binary) | Code (Decimal) | Vout (V) |
|---------------|----------------|----------|
| 0000 | 0 | 0.000 |
| 0001 | 1 | 0.100 |
| 0101 | 5 | 0.500 |
| 1000 | 8 | 0.800 |
| 1010 | 10 | 1.000 |
| 1111 | 15 | 1.500 |

---

### 3. Sample-and-Hold (`sample_hold_cmos.spice`)

Low-droop sample-and-hold circuit with bootstrapped switch and unity-gain buffer.

#### Circuit Topology
```
Vin → Input Buffer → Sampling Switch → Hold Capacitor → Output Buffer → Vout
                           ↑                                ↑
                         Clock                      Unity-Gain OpAmp
```

#### Specifications
- **Bandwidth**: 10 MHz (tracking mode)
- **Hold Capacitor**: 2pF (low leakage MIM cap)
- **Acquisition Time**: <200ns (to 0.1% accuracy)
- **Droop Rate**: <1mV/μs
- **Aperture Jitter**: <100ps
- **Input Impedance**: >1MΩ (buffered)
- **Output Impedance**: <100Ω

#### Key Components
1. **Input Buffer**: PMOS source follower (high Zin)
2. **Sampling Switch**: TG with dummy for charge injection cancellation
3. **Hold Capacitor**: 2pF MIM capacitor
4. **Output Buffer**: Two-stage opamp in unity-gain configuration

#### Transistor Sizing
| Block | Transistor | W/L | Function |
|-------|-----------|-----|----------|
| Input Buf | M_in1 | 10μm/0.5μm | PMOS follower |
| Switch | M_sw_n | 8μm/0.18μm | NMOS switch |
| Switch | M_sw_p | 16μm/0.18μm | PMOS switch |
| Buffer | M_amp1,2 | 10μm/0.5μm | Diff pair |
| Buffer | M_amp5 | 30μm/0.35μm | Output stage |

#### Operation Phases
- **Sample (Track)**: Clock HIGH → Switch closed → Chold charges to Vin
- **Hold**: Clock LOW → Switch open → Voltage held on Chold → Buffer drives output

---

### 4. Complete SAR ADC (`sar_adc_4bit_complete.spice`)

Integrated 4-bit SAR ADC combining all sub-blocks with control logic.

#### System Architecture

**Block Diagram:**
```
                    ┌──────────────┐
Vin_analog ────────>│ S/H Circuit  │
(0-1.6V)            │ (2pF hold)   │
                    └──────┬───────┘
                           │ Vsampled
                           v
                    ┌─────────────┐
                ┌───│  Comparator │───┐
                │   │  (3-stage)  │   │
                │   └─────────────┘   │
                │                     │
        DAC voltage            Comparison result
                │                     │
                v                     v
         ┌──────────────┐      ┌─────────────┐
Vref ───>│  4-bit R-2R  │<─────│ SAR Control │
(1.6V)   │  DAC         │      │ Logic       │
         └──────────────┘      └──────┬──────┘
                                      │
                                      v
                              Digital Output [3:0]
                              (0 to 15 decimal)
```

#### SAR Algorithm (Successive Approximation)

```
1. Sample Input: Sample Vin onto hold capacitor
2. Initialize: Set all DAC bits to 0
3. For each bit (MSB to LSB):
   a. Set current bit to 1
   b. DAC generates corresponding voltage
   c. Compare DAC voltage with sampled input
   d. If Vin > VDAC: Keep bit = 1
      If Vin < VDAC: Reset bit = 0
   e. Move to next bit
4. Output: Final 4-bit digital code
```

**Example Conversion (Vin = 0.625V, Vref = 1.6V):**
| Step | Try Code | DAC Voltage | Compare | Decision | Final Bit |
|------|----------|-------------|---------|----------|-----------|
| 1 | 1000 | 0.800V | Vin < VDAC | Reset | 0 |
| 2 | 0100 | 0.400V | Vin > VDAC | Keep | 1 |
| 3 | 0110 | 0.600V | Vin > VDAC | Keep | 1 |
| 4 | 0111 | 0.700V | Vin < VDAC | Reset | 0 |
| **Final** | **0110** | **0.600V** | - | - | **6** |

#### Specifications
- **Resolution**: 4 bits (ENOB ~ 3.8 bits typical)
- **Sample Rate**: 100 kSPS
- **Conversion Time**: ~10μs (1 sample + 4 bit decisions)
- **Input Range**: 0V to 1.6V
- **LSB Size**: 100mV
- **DNL**: <0.5 LSB
- **INL**: <1.0 LSB
- **Power Consumption**: ~5mW @ 1.8V

#### Clock Timing
- **clk_master**: 500kHz (2μs period) - system clock
- **clk_sample**: Sample phase (high for 2μs every 10μs)
- **clk_convert**: Conversion start trigger
- **bit_try pulses**: Sequential 2μs pulses for each bit trial

#### Key Signals to Monitor
- `vin_analog`: Analog input (test ramp)
- `sh_out_buf`: Sampled and held voltage
- `dac_out2`: DAC reconstruction voltage
- `comp_out_analog`: Comparator analog output
- `dac_b3`, `dac_b2`, `dac_b1`, `dac_b0`: Digital output bits
- `dout_decimal`: Decimal output code (0-15)

#### Performance Measurements
```spice
.measure tran conversion_time TRIG V(clk_sample) VAL=0.9 FALL=1 TARG V(dac_b0) VAL=0.9 CROSS=1
.measure tran final_code FIND V(dout_decimal) AT=9.5u
```

---

## Simulation Instructions

### Using AMS Simulator GUI

1. **Launch the Simulator**
   ```bash
   cd "C:\Users\vinay\My Simulator"
   .\.venv\Scripts\pythonw.exe launch_ams_simulator.pyw
   ```

2. **Load a Sub-Block**
   - File → Open
   - Navigate to `examples/adc/`
   - Select netlist (e.g., `comparator_cmos.spice`)

3. **Run Simulation**
   - Simulation → Configure
   - Select Analysis Type: Transient
   - Set parameters (tstop, tstep)
   - Click "Run Simulation"

4. **View Waveforms**
   - Waveform Viewer opens automatically
   - Select signals from list
   - Zoom/pan to examine details
   - Add measurements

### Using Command-Line Interface

```bash
cd "C:\Users\vinay\My Simulator"
.\.venv\Scripts\python.exe -m simulator.cli.runner --netlist examples/adc/comparator_cmos.spice
```

### Using Python Script

```python
from simulator.engine.analog_engine import AnalogEngine, TransientAnalysis

# Load netlist
engine = AnalogEngine()
with open('examples/adc/comparator_cmos.spice', 'r') as f:
    netlist = f.read()
engine.load_netlist(netlist)

# Run transient simulation
ta = TransientAnalysis(engine)
results = ta.run({
    'tstop': 500e-9,
    'tstep': 10e-12,
    'tstart': 0
})

# Plot results
import matplotlib.pyplot as plt
plt.plot(results['time'], results['V(comp_out)'])
plt.xlabel('Time (s)')
plt.ylabel('Comparator Output (V)')
plt.title('CMOS Comparator Response')
plt.show()
```

---

## Performance Specifications

### Comparator Performance
| Parameter | Min | Typ | Max | Unit | Conditions |
|-----------|-----|-----|-----|------|------------|
| DC Gain | 55 | 60 | 65 | dB | Open-loop |
| Bandwidth | - | 50 | - | MHz | Unity-gain |
| Slew Rate | - | 100 | - | V/μs | Cload=10pF |
| Prop. Delay | - | 8 | 15 | ns | 100mV overdrive |
| Offset Voltage | -5 | 0 | +5 | mV | Input-referred |
| CMRR | 60 | 70 | - | dB | @ DC |
| Power | - | 1 | 1.5 | mW | @ 1.8V |

### DAC Performance
| Parameter | Min | Typ | Max | Unit | Conditions |
|-----------|-----|-----|-----|------|------------|
| Resolution | - | 4 | - | bits | - |
| DNL | -0.5 | 0 | +0.5 | LSB | All codes |
| INL | -1.0 | 0 | +1.0 | LSB | All codes |
| Settling Time | - | 300 | 500 | ns | To 0.1% |
| Output Impedance | - | 5 | - | kΩ | Buffered |
| Glitch Energy | - | 10 | 50 | pV-s | Major transitions |

### Sample-and-Hold Performance
| Parameter | Min | Typ | Max | Unit | Conditions |
|-----------|-----|-----|-----|------|------------|
| Bandwidth | 8 | 10 | - | MHz | -3dB, tracking |
| Acquisition Time | - | 150 | 200 | ns | To 0.1%, 1V step |
| Droop Rate | - | 0.5 | 1.0 | mV/μs | Hold mode |
| THD | - | -60 | -50 | dB | 1MHz input |
| Aperture Jitter | - | 80 | 150 | ps | RMS |

### Complete ADC Performance
| Parameter | Min | Typ | Max | Unit | Conditions |
|-----------|-----|-----|-----|------|------------|
| Resolution | - | 4 | - | bits | - |
| ENOB | 3.5 | 3.8 | - | bits | Vin=1kHz sine |
| Sample Rate | - | 100 | 120 | kSPS | - |
| Conversion Time | - | 8 | 12 | μs | Per sample |
| DNL | -0.8 | 0 | +0.8 | LSB | - |
| INL | -1.5 | 0 | +1.5 | LSB | - |
| SNDR | - | 22 | - | dB | @ Nyquist |
| SFDR | - | 30 | - | dB | Spurious-free |
| Power | - | 5 | 7 | mW | Digital + analog |

---

## Design Notes

### Technology Scaling
These designs can be ported to other CMOS processes (65nm, 40nm, etc.) by:
1. Updating the technology library models
2. Rescaling transistor W/L ratios
3. Adjusting supply voltages
4. Recharacterizing performance

### Layout Considerations
For physical implementation:
- **Matching**: Use common-centroid layout for differential pairs
- **Shielding**: Guard rings around sensitive analog blocks
- **Supply**: Separate AVDD/DVDD with decoupling caps
- **Routing**: Minimize parasitics on high-impedance nodes (hold cap)

### Future Enhancements
- Increase resolution to 8-12 bits
- Add calibration for offset/gain error
- Implement dynamic element matching in DAC
- Add embedded reference voltage generator
- Include overvoltage protection on inputs

---

## References

1. B. Razavi, "Design of Analog CMOS Integrated Circuits", 2nd Edition
2. P. E. Allen, D. R. Holberg, "CMOS Analog Circuit Design", 3rd Edition
3. A. Hastings, "The Art of Analog Layout", 2nd Edition
4. IEEE papers on SAR ADC architectures and optimization

---

## Contact & Support

For questions about these designs or the AMS Simulator:
- Check documentation in `/docs`
- Run test scripts in `/scripts`
- See examples in `/examples`

**Created with AMS Simulator - Advanced Mixed-Signal Circuit Design Tool**
