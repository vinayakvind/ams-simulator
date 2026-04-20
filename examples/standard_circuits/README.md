# Standard Circuit Library

This directory contains verified standard circuits for common analog and mixed-signal applications.

## Power Electronics
- **buck_converter.spice** - Buck (step-down) DC-DC converter
- **boost_converter.spice** - Boost (step-up) DC-DC converter
- **buck_boost_converter.spice** - Buck-Boost DC-DC converter
- **flyback_converter.spice** - Flyback isolated converter
- **ldo_regulator.spice** - Low Dropout Regulator

## Analog Circuits
- **bandgap_reference.spice** - Bandgap voltage reference
- **rc_lowpass.spice** - RC low-pass filter
- **rc_highpass.spice** - RC high-pass filter
- **differential_amplifier.spice** - Differential amplifier

## Data Converters
- **sar_adc.spice** - Successive Approximation Register ADC
- **sigma_delta_adc.spice** - Sigma-Delta ADC
- **r2r_dac.spice** - R-2R Ladder DAC

## Using These Circuits
1. Open in AMS Simulator GUI via File > Open Standard Circuit
2. Run simulation to see verified waveforms
3. Modify parameters to explore behavior

All circuits have been verified and include expected simulation results.
