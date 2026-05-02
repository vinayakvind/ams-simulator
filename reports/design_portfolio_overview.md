# Design Portfolio Overview

Generated: 2026-05-02T19:05:51.867997

## Supported Technologies

- generic180 (180nm): Generic 180nm CMOS with HV options (automotive)
- generic130 (130nm): Generic 130nm CMOS
- generic65 (65nm): Generic 65nm CMOS (low-power)
- bcd180 (180nm): BCD 180nm - Bipolar/CMOS/DMOS for automotive HV

## Design Summary

| Design | Technology | Blocks | Latest Overall |
|--------|------------|--------|----------------|
| LIN ASIC Indexed Design Reference | BCD 180nm for target architecture, generic180 for current simulation framework | 9 | PASS |
| SAR ADC Indexed Design Reference | generic180 baseline with portability to generic130, generic65, and bcd180 through TechMapper wrappers | 1 | PASS |
| Sigma-Delta ADC Indexed Design Reference | generic180 baseline with portability to generic130, generic65, and bcd180 through TechMapper wrappers | 1 | PASS |

## LIN ASIC Indexed Design Reference

VBAT feeds the high-voltage LIN rail and the analog rail. The 3.3V analog rail feeds the bandgap and becomes the source for the 1.8V digital rail. Digital configuration arrives through SPI, lands in the register file, then fans into the control logic and LIN controller.


## SAR ADC Indexed Design Reference

Analog input is sampled, compared against a DAC trial voltage, and resolved bit by bit by SAR logic until the digital code converges. The indexed wrapper keeps this architecture reusable even when the underlying implementation file changes.

### Top Results

| Case | Block | Status | Details |
|------|-------|--------|---------|
| TOP-SAR-ADC | sar_adc_top | PASS | Top-level transient snapshot for the imported SAR ADC reference design.; time_points=3887; signals=33 |


## Sigma-Delta ADC Indexed Design Reference

Analog input is integrated against a one-bit feedback DAC, quantized into a bitstream, and then low-pass filtered or decimated to reconstruct the in-band signal. The indexed wrapper keeps that architecture reusable across future implementations and technologies.

### Top Results

| Case | Block | Status | Details |
|------|-------|--------|---------|
| TOP-SIGMA-DELTA-ADC | sigma_delta_adc_top | PASS | Top-level transient snapshot for the imported Sigma-Delta ADC reference design.; time_points=103092; signals=28 |

