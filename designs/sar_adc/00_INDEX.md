# SAR ADC - Design Index

## Overview
Indexed design folder for a reusable SAR ADC reference design.
This folder wraps an existing converter implementation into the same architecture, reporting, and presentation flow used by the LIN ASIC work.

## Source Implementation
- Imported source: examples/standard_circuits/sar_adc.spice
- Design focus: top-level sampled-data conversion behavior
- Technology intent: generic180 baseline, portable through TechMapper wrappers

## Quick Commands
```bash
python designs/framework/scripts/run_design_snapshot.py --design sar_adc --block sar_adc_top
python designs/framework/scripts/generate_design_reference.py --input designs/sar_adc/design_reference.json --output reports/sar_adc_design_reference.html
```

## Deliverables
- architecture.yaml: machine-readable design intent and verification settings
- 01_ARCHITECTURE.md: human-readable architecture summary
- design_reference.json: indexed methodology and debug reference
- blocks/sar_adc_top/spec.yaml: top-level verification contract