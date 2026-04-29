# LIN_ASIC - Design Index

## Architecture Overview
LIN protocol mixed-signal ASIC with dedicated analog regulators, a bandgap reference,
LIN physical layer, and a digital control plane.

## Block Status

| # | Block | Type | Status |
|---|-------|------|--------|
| 1 | bandgap | analog | PENDING |
| 2 | ldo_analog | analog | PENDING |
| 3 | ldo_digital | analog | PENDING |
| 4 | ldo_lin | analog | PENDING |
| 5 | lin_transceiver | mixed | PENDING |
| 6 | spi_controller | digital | PENDING |
| 7 | register_file | digital | PENDING |
| 8 | lin_controller | digital | PENDING |
| 9 | control_logic | digital | PENDING |

## Directory Structure
```
lin_asic/
  00_INDEX.md          ← This file
  architecture.yaml    ← Architecture definition
  design_reference.json← Indexed design methodology and debug reference
  blocks/              ← Individual block designs
    <block_name>/
      spec.yaml        ← Block specification
      <block>.spice    ← Block netlist
      testbench.spice  ← Testbench
      simulate.py      ← Simulation script
      REPORT.md        ← Results report
  rtl/                 ← Digital RTL files
  top/                 ← Top-level integration
  VERIFICATION_STATUS.md
```

## Quick Commands
```bash
# Query the design-reference index
python designs/framework/scripts/query_design_reference.py \
  --input designs/lin_asic/design_reference.json --list-blocks

# Generate the standalone methodology webpage
python designs/framework/scripts/generate_design_reference.py \
  --input designs/lin_asic/design_reference.json \
  --output reports/lin_asic_design_reference.html

# Simulate a specific block
python designs/lin_asic/blocks/<block>/simulate.py

# Run full regression
python designs/framework/scripts/run_regression.py --design lin_asic
```
