# Sigma-Delta ADC - Design Index

## Overview
Indexed design folder for a reusable Sigma-Delta ADC reference design.
This folder wraps the converter into the same architecture capture, results normalization, and presentation flow used across the AMS design workspace.

## Source Implementation
- Imported source: examples/standard_circuits/sigma_delta_adc.spice
- Design focus: top-level modulator and filtered-output behavior
- Technology intent: generic180 baseline, portable through TechMapper wrappers

## Quick Commands
```bash
python designs/framework/scripts/run_design_snapshot.py --design sigma_delta_adc --block sigma_delta_adc_top
python designs/framework/scripts/generate_design_reference.py --input designs/sigma_delta_adc/design_reference.json --output reports/sigma_delta_adc_design_reference.html
```

## Deliverables
- architecture.yaml: machine-readable design intent and verification settings
- 01_ARCHITECTURE.md: human-readable architecture summary
- design_reference.json: indexed methodology and debug reference
- blocks/sigma_delta_adc_top/spec.yaml: top-level verification contract