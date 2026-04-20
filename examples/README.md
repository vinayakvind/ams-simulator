# Example Circuits

This folder contains example circuits to test the AMS Simulator.

## Usage

### From Terminal (in GUI or command line)
```bash
# Test voltage divider
ams-sim --netlist examples/voltage_divider.spice --analysis dc --verbose

# Test RC low-pass filter
ams-sim --netlist examples/rc_lowpass.spice --analysis ac --fstart 1 --fstop 1e6

# Test transient response
ams-sim --netlist examples/rc_transient.spice --analysis transient --tstop 200e-6 --tstep 1e-6

# Test digital circuit
ams-sim --netlist examples/and_gate_test.v --analysis digital --max-time 100
```

### Batch Process All Examples
```bash
ams-batch --dir examples --analysis dc
```

## Circuit Descriptions

### voltage_divider.spice
- **Type**: Analog DC
- **Description**: Simple resistive voltage divider
- **Expected**: V(out) = 2.5V with 5V input

### rc_lowpass.spice
- **Type**: Analog AC
- **Description**: RC low-pass filter (cutoff ~159 Hz)
- **Expected**: -3dB at cutoff frequency

### rc_transient.spice
- **Type**: Analog Transient
- **Description**: RC charging/discharging with pulse source
- **Expected**: Exponential rise/fall with time constant τ = RC = 1ms

### and_gate_test.v
- **Type**: Digital
- **Description**: Simple AND gate with test inputs
- **Expected**: Output follows AND logic

## Try Your Own

Create new netlists following these examples and run them through the simulator!
