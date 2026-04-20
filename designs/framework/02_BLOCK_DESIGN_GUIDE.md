# 02 - Block Design Guide

## Designing Individual Blocks

### Analog Block Design Flow

```
1. Define spec in block_spec.yaml
2. Generate netlist via BlockBuilder OR write custom SPICE
3. Create testbench with supplies and stimuli
4. Run DC operating point → verify bias conditions
5. Run AC analysis → verify gain, bandwidth, PSRR
6. Run Transient → verify startup, load transients
7. Record results in REPORT.md
```

### Using the BlockBuilder Agent

```python
from simulator.agents.block_builder import BlockBuilder

builder = BlockBuilder("generic180")

# List available generators
print(builder.list_block_types())
# ['bandgap', 'bandgap_ref', 'bandgap_reference', 'control_logic', 
#  'lin_controller', 'lin_transceiver', 'ldo_analog', 'ldo_digital', 
#  'ldo_lin', 'register_file', 'spi_controller', ...]

# Build a block
block = builder.build_block("bandgap_ref", supply_voltage=3.3)
print(block['netlist'])       # SPICE subcircuit
print(block['ports'])         # Port list
print(block['specs'])         # Spec dict
print(block['transistor_count'])
```

### Custom SPICE Block

When BlockBuilder doesn't have your block, write a custom subcircuit:

```spice
* Custom comparator block
.SUBCKT COMPARATOR INP INN OUT VDD GND

.MODEL NMOS_3P3 NMOS (VTO=0.5 KP=120u LAMBDA=0.01)
.MODEL PMOS_3P3 PMOS (VTO=-0.5 KP=40u LAMBDA=0.01)

* Diff pair
M1 n_d1 INP n_tail GND NMOS_3P3 W=10u L=1u
M2 n_d2 INN n_tail GND NMOS_3P3 W=10u L=1u

* Load
M3 n_d1 n_d1 VDD VDD PMOS_3P3 W=20u L=1u
M4 n_d2 n_d1 VDD VDD PMOS_3P3 W=20u L=1u

* Tail current
R_TAIL n_tail GND 50k

* Output
R_OUT n_d2 OUT 1k

.ENDS COMPARATOR
```

### Block Specification Format

Every block has a `spec.yaml`:

```yaml
block:
  name: bandgap_ref
  type: analog
  description: "Bandgap voltage reference, Brokaw topology"

ports:
  - {name: VDD, direction: input, type: power}
  - {name: VREF, direction: output, type: analog}
  - {name: GND, direction: input, type: ground}
  - {name: EN, direction: input, type: digital}

specs:
  vref_nominal: {value: 1.2, unit: V, tolerance: 2%}
  tempco: {value: 50, unit: ppm/C, condition: "max"}
  psrr: {value: 60, unit: dB, condition: "min @ 1kHz"}
  supply_current: {value: 50, unit: uA, condition: "typical"}
  startup_time: {value: 10, unit: us, condition: "max"}
  supply_range: {min: 1.8, max: 5.5, unit: V}

testbench:
  dc_op:
    description: "Verify output voltage and bias currents"
    pass_criteria: "1.17V < VREF < 1.23V"
  ac_analysis:
    description: "PSRR measurement"
    pass_criteria: "PSRR > 60dB @ 1kHz"
  transient:
    description: "Startup from EN assertion"
    pass_criteria: "VREF settles within 10us"
```

### Digital Block Design

For digital blocks, provide Verilog RTL:

```verilog
module spi_slave (
    input wire clk,
    input wire rst_n,
    input wire sclk,
    input wire mosi,
    output reg miso,
    input wire cs_n,
    output reg [7:0] addr,
    output reg [7:0] wdata,
    input wire [7:0] rdata,
    output reg wen,
    output reg ren
);
// ... RTL implementation
endmodule
```

Digital blocks are simulated via the DigitalEngine with gate-level Verilog.

### Design Rules

1. Every subcircuit MUST include `.MODEL` declarations or reference the technology
2. Every port must have a clear direction (input/output/inout)
3. All node names must be unique within the subcircuit
4. Use standard naming: VDD, GND, VIN, VOUT, EN, etc.
5. Include bypass capacitors on supply pins in testbenches
