# Chip Assembly Catalog Report

Generated: 2026-05-02T18:46:51.920461
Technology filter: all

## Summary

- Technologies: 4
- Reusable IPs: 49
- Verification IPs: 23
- Digital subsystems: 17
- Chip profiles: 15
- Compatible IPs: 0
- Compatible digital subsystems: 0
- Compatible chip profiles: 0

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
| analog_signal_conditioner | no | Mixed-signal front-end combining precision references, filters, multiplexers, and ADCs. |
| audio_codec_asic | no | Digital audio interface chip combining stereo ADC/DAC, I2S, and signal conditioning. |
| automotive_hvdc_pmic | no | Automotive multi-output PMIC with boost converter, buck converter, and integrated protection. |
| can_automotive_node | no | CAN-enabled automotive controller with transceiver, messaging, and thermal protection. |
| debug_console_interface | no | UART-based debug and telemetry interface with register access and event logging. |
| high_voltage_power_supply | no | Automotive high-voltage supply combining buck converter, LDO, charge pump, and protection. |
| isolated_rs485_gateway | no | Galvanically isolated RS-485 interface combining transceiver, isolation, and protocol handling. |
| lin_node_asic | no | Automotive LIN node with integrated analog rails, transceiver, and digital control plane. |
| mixed_signal_sensor_hub | no | Sensor/control chip scaffold combining references, rails, multiple converter macros, and shared digital control. |
| multi_sensor_hub | no | I2C-based sensor aggregation platform with dual data converters and temperature monitoring. |
| power_management_unit | no | PMU-oriented chip scaffold combining references, regulators, switching conversion, and control-plane logic. |
| precision_analog_frontend | no | Lab instrumentation front-end with programmable gain, multi-threshold detection, and precision references. |
| real_time_motor_controller | no | Three-phase motor control ASIC with PWM generation, current sensing, and thermal protection. |
| sar_adc_macro | no | Converter-oriented chip scaffold centered on a reusable SAR ADC macro and digital control hooks. |
| sigma_delta_macro | no | Oversampled converter scaffold centered on a reusable sigma-delta ADC macro and its control plane. |

## Reusable IPs

| IP | Domain | Category | Compatible | Technology Support |
|----|--------|----------|------------|--------------------|
| analog_multiplexer | analog | interface | no | generic180, generic130, generic65, bcd180 |
| bandgap | analog | reference | no | generic180, generic130, generic65, bcd180 |
| bias_generator | analog | bias | no | generic180, generic130, generic65, bcd180 |
| boost_converter | analog | power | no | generic180, generic130, generic65, bcd180 |
| buck_converter | analog | power | no | generic180, generic130, generic65, bcd180 |
| can_controller | digital | protocol | no | generic180, generic130, generic65, bcd180 |
| can_transceiver | mixed | interface | no | generic180, generic130, generic65, bcd180 |
| charge_pump | analog | power | no | generic180, generic130, generic65, bcd180 |
| clock_divider | digital | sequencing | no | generic180, generic130, generic65, bcd180 |
| comparator_array | analog | sense | no | generic180, generic130, generic65, bcd180 |
| comparator_cmos | analog | sense | no | generic180, generic130, generic65, bcd180 |
| control_logic | digital | sequencing | no | generic180, generic130, generic65, bcd180 |
| current_mirror | analog | bias | no | generic180, generic130, generic65, bcd180 |
| current_reference | analog | reference | no | generic180, generic130, generic65, bcd180 |
| dac_r2r_4bit | analog | converter | no | generic180, generic130, generic65, bcd180 |
| esd_protection | analog | interface | no | generic180, generic130, generic65, bcd180 |
| flash_memory | digital | storage | no | generic180, generic130, generic65, bcd180 |
| frequency_detector | mixed | sense | no | generic180, generic130, generic65, bcd180 |
| gpio_controller | digital | interface | no | generic180, generic130, generic65, bcd180 |
| i2c_controller | digital | protocol | no | generic180, generic130, generic65, bcd180 |
| i2s_audio_controller | digital | protocol | no | generic180, generic130, generic65, bcd180 |
| interrupt_controller | digital | sequencing | no | generic180, generic130, generic65, bcd180 |
| ldo_analog | analog | power | no | generic180, generic130, generic65, bcd180 |
| ldo_digital | analog | power | no | generic180, generic130, generic65, bcd180 |
| ldo_lin | analog | power | no | generic180, generic130, generic65, bcd180 |
| lin_controller | digital | protocol | no | generic180, generic130, generic65, bcd180 |
| lin_transceiver | mixed | interface | no | generic180, generic130, generic65, bcd180 |
| low_pass_filter | analog | filter | no | generic180, generic130, generic65, bcd180 |
| lvds_driver | mixed | interface | no | generic180, generic130, generic65, bcd180 |
| memory_compiler | digital | storage | no | generic180, generic130, generic65, bcd180 |
| operational_amplifier | analog | sense | no | generic180, generic130, generic65, bcd180 |
| pll | mixed | sequencing | no | generic180, generic130, generic65, bcd180 |
| precision_voltage_reference | analog | reference | no | generic180, generic130, generic65, bcd180 |
| programmable_gain_amplifier | analog | sense | no | generic180, generic130, generic65, bcd180 |
| pwm_controller | digital | sequencing | no | generic180, generic130, generic65, bcd180 |
| register_file | digital | control | no | generic180, generic130, generic65, bcd180 |
| reset_generator | digital | sequencing | no | generic180, generic130, generic65, bcd180 |
| ring_oscillator | analog | sequencing | no | generic180, generic130, generic65, bcd180 |
| rs485_transceiver | mixed | interface | no | generic180, generic130, generic65, bcd180 |
| sample_hold_frontend | analog | converter | no | generic180, generic130, generic65, bcd180 |
| sar_adc_top | mixed | converter | no | generic180, generic130, generic65, bcd180 |
| sigma_delta_adc_top | mixed | converter | no | generic180, generic130, generic65, bcd180 |
| slew_rate_limiter | analog | interface | no | generic180, generic130, generic65, bcd180 |
| spi_controller | digital | control | no | generic180, generic130, generic65, bcd180 |
| temperature_sensor | analog | sense | no | generic180, generic130, generic65, bcd180 |
| trim_circuit | analog | bias | no | generic180, generic130, generic65, bcd180 |
| uart_controller | digital | protocol | no | generic180, generic130, generic65, bcd180 |
| voltage_ladder_dac | analog | converter | no | generic180, generic130, generic65, bcd180 |
| watchdog_timer | digital | sequencing | no | generic180, generic130, generic65, bcd180 |

## Verification IPs

| VIP | Protocol | Checks |
|-----|----------|--------|
| adc_linearity_vip | Converter linearity | INL/DNL analysis, code histogram, missing codes, monotonicity |
| adc_transient_vip | Converter transient | input stimulus, internal decision nodes, bitstream or DAC activity |
| analog_snapshot_vip | Analog snapshot | waveform presence, minimum sample count, tracked node visibility |
| can_vip | CAN | arbitration, frame format, bit stuffing, CRC validation, acknowledgment |
| clock_monitoring_vip | Clock/Oscillator | frequency accuracy, phase continuity, jitter metrics, duty cycle |
| current_consumption_vip | Power monitoring | quiescent current, dynamic current, power sequencing, inrush limiting |
| digital_subsystem_vip | Digital verification | timing compliance, reset sequencing, state machine coverage, functional correctness |
| emc_compliance_vip | Electromagnetic compatibility | EMI immunity, conducted emissions, radiated immunity, ESD margin |
| frequency_accuracy_vip | Oscillator/Clock accuracy | frequency tolerance, temperature drift, supply sensitivity, long-term stability |
| i2c_vip | I2C | start and stop conditions, acknowledge handshake, data framing, clock stretching |
| i2s_audio_vip | I2S | frame synchronization, clock gating, data alignment, channel separation |
| io_electrical_vip | I/O interface | output drive strength, input threshold margin, leakage current, output impedance |
| lin_vip | LIN | break and sync, frame timing, TX/RX thresholding |
| mixed_signal_bridge_vip | Mixed-signal interface | digital-to-analog drive, analog-to-digital thresholding, interface closure |
| noise_performance_vip | Signal integrity | SNR calculation, THD analysis, SFDR measurement, noise floor |
| power_domain_isolation_vip | Analog/Digital isolation | cross-domain leakage, isolation boundary integrity, handshake synchronization, metastability |
| power_sequence_vip | Power-up sequencing | rail order, enable staging, reset release |
| power_supply_vip | Power supply quality | ripple and noise, PSRR, transient response, regulation accuracy, ramp rate |
| spi_vip | SPI | transaction decode, register access, reset defaults |
| temperature_corner_vip | Temperature characterization | cold corner performance, hot corner performance, gradient effects, thermal coupling |
| thermal_monitoring_vip | Temperature monitoring | temp sensor accuracy, shutdown threshold, hysteresis, rise time |
| uart_vip | UART | frame formation, baud rate accuracy, parity checking, flow control |
| voltage_regulation_vip | Power supply regulation | DC regulation accuracy, load transient response, line regulation, soft-start behavior |

## Digital Subsystems

| Subsystem | Compatible | Blocks |
|-----------|------------|--------|
| analog_conditioning_plane | no | programmable_gain_amplifier, low_pass_filter, comparator_array, register_file, control_logic |
| can_node_control_plane | no | can_controller, spi_controller, register_file, interrupt_controller, control_logic |
| clock_distribution_plane | no | pll, clock_divider, control_logic |
| converter_control_plane | no | spi_controller, register_file, control_logic |
| frequency_monitoring_plane | no | frequency_detector, control_logic, register_file, interrupt_controller |
| i2c_sensor_interface | no | i2c_controller, register_file, interrupt_controller, control_logic |
| lin_node_control_plane | no | spi_controller, register_file, lin_controller, control_logic |
| multi_rail_power_control | no | control_logic, reset_generator, register_file, interrupt_controller, temperature_sensor |
| power_sequencer | no | control_logic, reset_generator, interrupt_controller, register_file |
| pwm_motor_control_plane | no | pwm_controller, register_file, control_logic, interrupt_controller |
| rs485_interface_plane | no | rs485_transceiver, uart_controller, register_file, control_logic |
| sensor_aggregation_plane | no | i2c_controller, spi_controller, register_file, interrupt_controller, control_logic |
| sensor_hub_control_plane | no | spi_controller, register_file, control_logic |
| test_control_plane | no | uart_controller, spi_controller, register_file, control_logic, interrupt_controller |
| thermal_management_plane | no | temperature_sensor, watchdog_timer, interrupt_controller, control_logic |
| trim_engine | no | trim_circuit, voltage_ladder_dac, register_file, control_logic |
| uart_debug_interface | no | uart_controller, register_file, control_logic |
