# SAR ADC - Architecture Definition

## Intent
This design captures a reusable successive-approximation ADC reference under the indexed AMS design flow.
The goal is to keep converter architecture, top-level verification settings, and presentation artifacts aligned with the same reporting flow used by mixed-signal ASIC projects.

## Architecture
The converter follows the classical SAR partition:

1. Sample and hold captures the analog input.
2. Comparator determines whether the DAC trial code is above or below the held sample.
3. Binary-weighted DAC reconstructs the trial voltage.
4. SAR control logic performs the bit-by-bit binary search.
5. Output register exposes the final digital code.

## Electrical Intent
- Resolution: 8-bit behavioral reference
- Input range: 0 V to 2.5 V
- Conversion style: sampled-data, transient-oriented validation
- Baseline supply: 3.3 V analog environment

## Technology Adaptation
The imported source is a generic reference netlist rather than a foundry-specific block.
Framework portability comes from:

1. Technology-aware model cards provided by TechMapper.
2. Indexed manifests that separate architecture intent from one specific implementation file.
3. Snapshot-based verification settings stored in spec.yaml so the same flow can wrap a different SAR ADC implementation later.

## Verification Strategy
Current validation is a top-level transient snapshot.
The snapshot checks that the imported design produces waveform data for the analog input and internal conversion nodes and that the run generates a meaningful number of samples.

## Current Boundary
This is a reusable architecture and reporting reference, not a silicon-signoff SAR ADC.
Future work should replace the imported top-level example with block-level subcircuits and PDK-specific verification.