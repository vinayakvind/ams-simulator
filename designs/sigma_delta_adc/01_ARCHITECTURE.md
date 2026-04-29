# Sigma-Delta ADC - Architecture Definition

## Intent
This design captures a reusable Sigma-Delta ADC reference under the indexed AMS design flow.
The objective is to keep architecture intent, top-level verification settings, and portfolio reporting aligned for oversampled converter designs.

## Architecture
The converter follows the classical first-order Sigma-Delta partition:

1. Analog input is summed against the feedback DAC output.
2. Integrator accumulates the input error.
3. One-bit quantizer produces the high-rate bitstream.
4. One-bit feedback DAC closes the noise-shaping loop.
5. Decimation filter produces the lower-rate filtered output.

## Electrical Intent
- Modulator order: first order
- Oversampling ratio: 64x reference behavior
- Input style: sinusoidal analog stimulus
- Baseline supply: 3.3 V environment

## Technology Adaptation
This wrapper treats the current netlist as a reusable architecture source.
Technology portability comes from:

1. TechMapper model-card support for retargeted environments.
2. Indexed manifests that preserve architecture and verification rules even when the implementation changes.
3. Snapshot settings stored beside the block spec so a future Sigma-Delta design can be dropped in with the same reporting contract.

## Verification Strategy
Current validation is a top-level transient snapshot that checks for analog input, bitstream activity, filtered output visibility, and sufficient sample depth.

## Current Boundary
This is a reusable reference for architecture and reporting.
Future work should introduce explicit integrator, quantizer, DAC, and decimator sub-block implementations with technology-specific closure.