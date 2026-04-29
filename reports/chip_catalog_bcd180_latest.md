# Chip Assembly Catalog Report

Generated: 2026-04-30T01:20:34.432974
Technology filter: bcd180

## Summary

- Technologies: 4
- Reusable IPs: 30
- Verification IPs: 13
- Digital subsystems: 7
- Chip profiles: 10
- Compatible IPs: 30
- Compatible digital subsystems: 7
- Compatible chip profiles: 10

## Technologies

| Name | Node | VDD | Description |
|------|------|-----|-------------|
| generic180 | 180nm | 1.8 | Generic 180nm CMOS with HV options (automotive) |
| generic130 | 130nm | 1.2 | Generic 130nm CMOS |
| generic65 | 65nm | 1.0 | Generic 65nm CMOS (low-power) |
| bcd180 | 180nm | 1.8 | BCD 180nm - Bipolar/CMOS/DMOS for automotive HV |

## Chip Profiles

| Profile | Compatible | Summary |
|---------|------------|---------|
| analog_signal_conditioner | yes | Mixed-signal front-end combining precision references, filters, multiplexers, and ADCs. |
| can_automotive_node | yes | CAN-enabled automotive controller with transceiver, messaging, and thermal protection. |
| debug_console_interface | yes | UART-based debug and telemetry interface with register access and event logging. |
| high_voltage_power_supply | yes | Automotive high-voltage supply combining buck converter, LDO, charge pump, and protection. |
| lin_node_asic | yes | Automotive LIN node with integrated analog rails, transceiver, and digital control plane. |
| mixed_signal_sensor_hub | yes | Sensor/control chip scaffold combining references, rails, multiple converter macros, and shared digital control. |
| multi_sensor_hub | yes | I2C-based sensor aggregation platform with dual data converters and temperature monitoring. |
| power_management_unit | yes | PMU-oriented chip scaffold combining references, regulators, switching conversion, and control-plane logic. |
| sar_adc_macro | yes | Converter-oriented chip scaffold centered on a reusable SAR ADC macro and digital control hooks. |
| sigma_delta_macro | yes | Oversampled converter scaffold centered on a reusable sigma-delta ADC macro and its control plane. |

## Reusable IPs

| IP | Domain | Category | Compatible | Technology Support |
|----|--------|----------|------------|--------------------|
| analog_multiplexer | analog | interface | yes | generic180, generic130, generic65, bcd180 |
| bandgap | analog | reference | yes | generic180, generic130, generic65, bcd180 |
| buck_converter | analog | power | yes | generic180, generic130, generic65, bcd180 |
| can_controller | digital | protocol | yes | generic180, generic130, generic65, bcd180 |
| can_transceiver | mixed | interface | yes | generic180, generic130, generic65, bcd180 |
| charge_pump | analog | power | yes | generic180, generic130, generic65, bcd180 |
| clock_divider | digital | sequencing | yes | generic180, generic130, generic65, bcd180 |
| comparator_cmos | analog | sense | yes | generic180, generic130, generic65, bcd180 |
| control_logic | digital | sequencing | yes | generic180, generic130, generic65, bcd180 |
| current_mirror | analog | bias | yes | generic180, generic130, generic65, bcd180 |
| dac_r2r_4bit | analog | converter | yes | generic180, generic130, generic65, bcd180 |
| i2c_controller | digital | protocol | yes | generic180, generic130, generic65, bcd180 |
| interrupt_controller | digital | sequencing | yes | generic180, generic130, generic65, bcd180 |
| ldo_analog | analog | power | yes | generic180, generic130, generic65, bcd180 |
| ldo_digital | analog | power | yes | generic180, generic130, generic65, bcd180 |
| ldo_lin | analog | power | yes | generic180, generic130, generic65, bcd180 |
| lin_controller | digital | protocol | yes | generic180, generic130, generic65, bcd180 |
| lin_transceiver | mixed | interface | yes | generic180, generic130, generic65, bcd180 |
| low_pass_filter | analog | filter | yes | generic180, generic130, generic65, bcd180 |
| memory_compiler | digital | storage | yes | generic180, generic130, generic65, bcd180 |
| operational_amplifier | analog | sense | yes | generic180, generic130, generic65, bcd180 |
| precision_voltage_reference | analog | reference | yes | generic180, generic130, generic65, bcd180 |
| register_file | digital | control | yes | generic180, generic130, generic65, bcd180 |
| sample_hold_frontend | analog | converter | yes | generic180, generic130, generic65, bcd180 |
| sar_adc_top | mixed | converter | yes | generic180, generic130, generic65, bcd180 |
| sigma_delta_adc_top | mixed | converter | yes | generic180, generic130, generic65, bcd180 |
| spi_controller | digital | control | yes | generic180, generic130, generic65, bcd180 |
| temperature_sensor | analog | sense | yes | generic180, generic130, generic65, bcd180 |
| uart_controller | digital | protocol | yes | generic180, generic130, generic65, bcd180 |
| watchdog_timer | digital | sequencing | yes | generic180, generic130, generic65, bcd180 |

## Verification IPs

| VIP | Protocol | Checks |
|-----|----------|--------|
| adc_transient_vip | Converter transient | input stimulus, internal decision nodes, bitstream or DAC activity |
| analog_snapshot_vip | Analog snapshot | waveform presence, minimum sample count, tracked node visibility |
| can_vip | CAN | arbitration, frame format, bit stuffing, CRC validation, acknowledgment |
| clock_monitoring_vip | Clock/Oscillator | frequency accuracy, phase continuity, jitter metrics, duty cycle |
| current_consumption_vip | Power monitoring | quiescent current, dynamic current, power sequencing, inrush limiting |
| digital_subsystem_vip | Digital verification | timing compliance, reset sequencing, state machine coverage, functional correctness |
| i2c_vip | I2C | start and stop conditions, acknowledge handshake, data framing, clock stretching |
| lin_vip | LIN | break and sync, frame timing, TX/RX thresholding |
| mixed_signal_bridge_vip | Mixed-signal interface | digital-to-analog drive, analog-to-digital thresholding, interface closure |
| power_sequence_vip | Power-up sequencing | rail order, enable staging, reset release |
| spi_vip | SPI | transaction decode, register access, reset defaults |
| thermal_monitoring_vip | Temperature monitoring | temp sensor accuracy, shutdown threshold, hysteresis, rise time |
| uart_vip | UART | frame formation, baud rate accuracy, parity checking, flow control |

## Digital Subsystems

| Subsystem | Compatible | Blocks |
|-----------|------------|--------|
| can_node_control_plane | yes | can_controller, spi_controller, register_file, interrupt_controller, control_logic |
| converter_control_plane | yes | spi_controller, register_file, control_logic |
| i2c_sensor_interface | yes | i2c_controller, register_file, interrupt_controller, control_logic |
| lin_node_control_plane | yes | spi_controller, register_file, lin_controller, control_logic |
| sensor_hub_control_plane | yes | spi_controller, register_file, control_logic |
| thermal_management_plane | yes | temperature_sensor, watchdog_timer, interrupt_controller, control_logic |
| uart_debug_interface | yes | uart_controller, register_file, control_logic |
