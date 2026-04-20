# Standard Circuits Library

Complete list of available standard circuits for the AMS Simulator.

## Power Electronics

### Buck Converter
- **File:** `buck_converter.spice`
- **Description:** Buck Converter - Step-Down DC-DC Converter Converts 12V input to 5V output Switching frequency: 100kHz Output power: up to 10W Power Supply MOSFET Switch (simplified as voltage-controlled switch) In real simulation, use NMOS model Gate drive signal (PWM at 100kHz, 42% duty cycle for 5V output) Freewheeling diode Output inductor (100uH)
- **Analysis Type:** transient
- **Components:** capacitors: 1, inductors: 1, transistors: 1, diodes: 1

### Boost Converter
- **File:** `boost_converter.spice`
- **Description:** Boost Converter - Step-Up DC-DC Converter Converts 5V input to 12V output Switching frequency: 100kHz Output power: up to 6W Power Supply Input capacitor Boost inductor (47uH) MOSFET Switch Gate drive signal (PWM at 100kHz, 58% duty cycle for 12V output) D = 1 - Vin/Vout = 1 - 5/12 = 0.583
- **Analysis Type:** transient
- **Components:** inductors: 1, transistors: 1, diodes: 1

### Buck Boost Converter
- **File:** `buck_boost_converter.spice`
- **Description:** Buck-Boost Converter - Inverting DC-DC Converter Converts 12V input to -12V output (inverted) Can also produce |Vout| > Vin or |Vout| < Vin Switching frequency: 100kHz Power Supply Input capacitor MOSFET Switch (connects input to inductor during ON) Gate drive signal (50% duty cycle for |Vout| = Vin) Inductor (100uH)
- **Analysis Type:** transient
- **Components:** inductors: 1, transistors: 1, diodes: 1

### Flyback Converter
- **File:** `flyback_converter.spice`
- **Description:** Flyback Converter - Isolated DC-DC Converter Converts 48V input to isolated 12V output Uses transformer for isolation Switching frequency: 100kHz Primary Side Power Supply Input capacitor (primary side) Primary MOSFET Switch Gate drive signal (25% duty cycle) For flyback: Vout = Vin * (N2/N1) * D/(1-D) With N2/N1=0.25, D=0.25: Vout = 48 * 0.25 * 0.25/0.75 = 4V Adjusted for 12V output
- **Analysis Type:** transient
- **Components:** transistors: 1

### Ldo Regulator
- **File:** `ldo_regulator.spice`
- **Description:** LDO - Low Dropout Regulator Converts 5V input to regulated 3.3V output Uses PMOS pass transistor for low dropout Dropout voltage: ~200mV Power Supply (5V input with some noise/ripple) Reference voltage (1.25V bandgap reference) Error Amplifier (simplified op-amp model) Non-inverting input: feedback from output Inverting input: reference voltage Output drives PMOS gate PMOS Pass Transistor Large W/L for low RDS(on)
- **Analysis Type:** transient


## Analog Circuits

### Bandgap Reference
- **File:** `bandgap_reference.spice`
- **Description:** Bandgap Voltage Reference Produces temperature-stable 1.25V reference Uses PTAT and CTAT currents for compensation Classic Brokaw bandgap topology Power Supply Bias Current Source Current Mirror (PMOS) BJT Pair (different areas for delta-Vbe) Q1: 1x area, Q2: 8x area
- **Analysis Type:** ac
- **Components:** resistors: 3, transistors: 2

### Differential Amplifier
- **File:** `differential_amplifier.spice`
- **Description:** Differential Amplifier - Classic Long-Tail Pair Gain: ~40dB (100 V/V) Bandwidth: ~1MHz CMRR: >60dB Power Supplies Differential input signals Tail current source (1mA) Input differential pair (NPN)
- **Analysis Type:** transient
- **Components:** transistors: 2

### Rc Highpass
- **File:** `rc_highpass.spice`
- **Description:** RC High-Pass Filter Cutoff frequency: 1kHz First order filter: 20dB/decade rolloff Input signal - pulse for transient analysis High-pass RC filter fc = 1/(2*pi*R*C) For fc = 1kHz: RC = 1/(2*pi*1000) = 159.15us Choose C = 100nF, R = 1.59k Load (high impedance) DC Analysis
- **Analysis Type:** transient
- **Components:** resistors: 1, capacitors: 1


## Data Converters

### Sar Adc
- **File:** `sar_adc.spice`
- **Description:** SAR ADC - 8-bit Successive Approximation Register ADC Conversion time: 8 clock cycles Sample rate: up to 1 MSPS Input range: 0 to Vref (2.5V) Power Supplies Analog input signal (100Hz sine wave, 0-2.5V range) Sample and Hold capacitor Sample control signal (sample for 100ns, then hold)
- **Analysis Type:** transient

### Sigma Delta Adc
- **File:** `sigma_delta_adc.spice`
- **Description:** Sigma-Delta ADC - First Order Modulator Oversampling ratio: 64x Signal bandwidth: 20kHz Sample rate: 2.56 MHz (64 * 2 * 20kHz) Power Supplies Analog input signal (1kHz sine wave) Sampling clock (2.56 MHz) ============================================ First-Order Sigma-Delta Modulator ============================================
- **Analysis Type:** transient

### R2R Dac
- **File:** `r2r_dac.spice`
- **Description:** R-2R Ladder DAC - 8-bit Digital to Analog Converter Reference voltage: 2.5V Output range: 0 to 2.5V * (255/256) Reference voltage Digital inputs (binary weighted) Example: input code = 10101010 (170 decimal = 1.66V) R-2R Ladder Network Each bit contributes: Vbit * 2^(bit_position) / 256
- **Analysis Type:** transient


