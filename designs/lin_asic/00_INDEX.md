# LIN_ASIC - Design Index

## Architecture Overview
Auto-generated design with 4 blocks.

## Block Status

| # | Block | Type | Status |
|---|-------|------|--------|
| 1 | bandgap | analog | PENDING |
| 2 | ldo_analog | analog | PENDING |
| 3 | ldo_digital | analog | PENDING |
| 4 | ldo_lin | analog | PENDING |

## Directory Structure
```
lin_asic/
  00_INDEX.md          ← This file
  architecture.yaml    ← Architecture definition
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
# Simulate a specific block
python designs/lin_asic/blocks/<block>/simulate.py

# Run full regression
python designs/framework/scripts/run_regression.py --design lin_asic
```
