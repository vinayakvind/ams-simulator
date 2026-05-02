# Chip Assembly Catalog Report

Generated: 2026-05-03T01:13:32.489170
Technology filter: generic130

## Summary

- Technologies: 4
- Reusable IPs: 69
- Verification IPs: 35
- Digital subsystems: 25
- Chip profiles: 24
- Compatible IPs: 69
- Compatible digital subsystems: 25
- Compatible chip profiles: 24

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
| audio_codec_asic | yes | Digital audio interface chip combining stereo ADC/DAC, I2S, and signal conditioning. |
| automotive_hvdc_pmic | yes | Automotive multi-output PMIC with boost converter, buck converter, and integrated protection. |
| automotive_infotainment_soc | yes | Advanced in-vehicle infotainment system with multi-protocol connectivity, audio interface, and safety monitoring. |
| can_automotive_node | yes | CAN-enabled automotive controller with transceiver, messaging, and thermal protection. |
| debug_console_interface | yes | UART-based debug and telemetry interface with register access and event logging. |
| ethernet_sensor_hub | yes | Networked sensor aggregation node with Ethernet PHY, multi-channel I2C/SPI, and precision analog. |
| high_voltage_power_supply | yes | Automotive high-voltage supply combining buck converter, LDO, charge pump, and protection. |
| industrial_iot_gateway | yes | Multi-protocol industrial gateway with PROFIBUS, CANopen, Ethernet, and security acceleration. |
| iot_edge_hub | yes | Multi-protocol IoT edge node combining BLE, NFC, security, and sensor aggregation. |
| isolated_power_supply_controller | yes | Isolated PMIC with multiple isolated rails, boost/buck converters, and high-side gate drivers. |
| isolated_rs485_gateway | yes | Galvanically isolated RS-485 interface combining transceiver, isolation, and protocol handling. |
| lin_node_asic | yes | Automotive LIN node with integrated analog rails, transceiver, and digital control plane. |
| mixed_signal_sensor_hub | yes | Sensor/control chip scaffold combining references, rails, multiple converter macros, and shared digital control. |
| multi_sensor_hub | yes | I2C-based sensor aggregation platform with dual data converters and temperature monitoring. |
| power_management_unit | yes | PMU-oriented chip scaffold combining references, regulators, switching conversion, and control-plane logic. |
| precision_analog_frontend | yes | Lab instrumentation front-end with programmable gain, multi-threshold detection, and precision references. |
| real_time_motor_controller | yes | Three-phase motor control ASIC with PWM generation, current sensing, and thermal protection. |
| safe_motor_drive_controller | yes | Functional safety-compliant three-phase motor drive with integrated diagnostics and SIL monitoring. |
| sar_adc_macro | yes | Converter-oriented chip scaffold centered on a reusable SAR ADC macro and digital control hooks. |
| secure_iot_gateway | yes | Enterprise-grade IoT gateway with integrated crypto, multi-protocol wireless, and secure boot. |
| sigma_delta_macro | yes | Oversampled converter scaffold centered on a reusable sigma-delta ADC macro and its control plane. |
| smart_battery_pack | yes | Multi-cell battery management system with wireless telemetry and active balancing. |
| wireless_powered_sensor | yes | Battery-free or battery-assisted sensor node with Qi wireless charging and energy harvesting. |

## Reusable IPs

| IP | Domain | Category | Compatible | Technology Support |
|----|--------|----------|------------|--------------------|
| aes_accelerator | digital | security | yes | generic130, generic65, bcd180, generic22, generic14 |
| analog_multiplexer | analog | interface | yes | generic180, generic130, generic65, bcd180 |
| bandgap | analog | reference | yes | generic180, generic130, generic65, bcd180 |
| battery_cell_monitor | analog | power | yes | generic130, generic65, bcd180, generic22, generic14 |
| bias_generator | analog | bias | yes | generic180, generic130, generic65, bcd180 |
| ble_transceiver | mixed | interface | yes | generic130, generic65, bcd180, generic22, generic14 |
| bms_controller | digital | sequencing | yes | generic130, generic65, bcd180, generic22, generic14 |
| boost_converter | analog | power | yes | generic180, generic130, generic65, bcd180 |
| buck_converter | analog | power | yes | generic180, generic130, generic65, bcd180 |
| buffered_precision_dac | analog | converter | yes | generic180, generic130, generic65, bcd180 |
| can_controller | digital | protocol | yes | generic180, generic130, generic65, bcd180 |
| can_transceiver | mixed | interface | yes | generic180, generic130, generic65, bcd180 |
| canopen_controller | digital | protocol | yes | generic130, generic65, bcd180, generic22 |
| charge_pump | analog | power | yes | generic180, generic130, generic65, bcd180 |
| clock_divider | digital | sequencing | yes | generic180, generic130, generic65, bcd180 |
| comparator_array | analog | sense | yes | generic180, generic130, generic65, bcd180 |
| comparator_cmos | analog | sense | yes | generic180, generic130, generic65, bcd180 |
| control_logic | digital | sequencing | yes | generic180, generic130, generic65, bcd180 |
| current_mirror | analog | bias | yes | generic180, generic130, generic65, bcd180 |
| current_reference | analog | reference | yes | generic180, generic130, generic65, bcd180 |
| dac_r2r_4bit | analog | converter | yes | generic180, generic130, generic65, bcd180 |
| differential_amplifier | analog | sense | yes | generic180, generic130, generic65, bcd180 |
| esd_protection | analog | interface | yes | generic180, generic130, generic65, bcd180 |
| ethernet_phy | mixed | interface | yes | generic130, generic65, bcd180, generic22 |
| flash_memory | digital | storage | yes | generic180, generic130, generic65, bcd180 |
| frequency_detector | mixed | sense | yes | generic180, generic130, generic65, bcd180 |
| gpio_controller | digital | interface | yes | generic180, generic130, generic65, bcd180 |
| high_speed_comparator | analog | sense | yes | generic180, generic130, generic65, bcd180 |
| i2c_controller | digital | protocol | yes | generic180, generic130, generic65, bcd180 |
| i2s_audio_controller | digital | protocol | yes | generic180, generic130, generic65, bcd180 |
| i3c_controller | digital | control | yes | generic130, generic65, bcd180, generic22, generic14 |
| imu_interface | mixed | sense | yes | generic130, generic65, bcd180, generic22, generic14 |
| interrupt_controller | digital | sequencing | yes | generic180, generic130, generic65, bcd180 |
| isolated_gate_driver | mixed | interface | yes | generic130, generic65, bcd180 |
| ldo_analog | analog | power | yes | generic180, generic130, generic65, bcd180 |
| ldo_digital | analog | power | yes | generic180, generic130, generic65, bcd180 |
| ldo_lin | analog | power | yes | generic180, generic130, generic65, bcd180 |
| lin_controller | digital | protocol | yes | generic180, generic130, generic65, bcd180 |
| lin_transceiver | mixed | interface | yes | generic180, generic130, generic65, bcd180 |
| low_pass_filter | analog | filter | yes | generic180, generic130, generic65, bcd180 |
| lvds_driver | mixed | interface | yes | generic180, generic130, generic65, bcd180 |
| lvds_receiver | mixed | interface | yes | generic180, generic130, generic65, bcd180 |
| memory_compiler | digital | storage | yes | generic180, generic130, generic65, bcd180 |
| nfc_controller | mixed | interface | yes | generic130, generic65, bcd180, generic22, generic14 |
| operational_amplifier | analog | sense | yes | generic180, generic130, generic65, bcd180 |
| pll | mixed | sequencing | yes | generic180, generic130, generic65, bcd180 |
| precision_voltage_reference | analog | reference | yes | generic180, generic130, generic65, bcd180 |
| profibus_transceiver | mixed | interface | yes | generic130, generic65, bcd180 |
| programmable_gain_amplifier | analog | sense | yes | generic180, generic130, generic65, bcd180 |
| pwm_controller | digital | sequencing | yes | generic180, generic130, generic65, bcd180 |
| qi_wireless_rx | mixed | power | yes | generic130, generic65, bcd180, generic22, generic14 |
| register_file | digital | control | yes | generic180, generic130, generic65, bcd180 |
| reset_generator | digital | sequencing | yes | generic180, generic130, generic65, bcd180 |
| rf_front_end | mixed | interface | yes | generic130, generic65, bcd180, generic22, generic14 |
| ring_oscillator | analog | sequencing | yes | generic180, generic130, generic65, bcd180 |
| rs485_transceiver | mixed | interface | yes | generic180, generic130, generic65, bcd180 |
| sample_hold_frontend | analog | converter | yes | generic180, generic130, generic65, bcd180 |
| sar_adc_top | mixed | converter | yes | generic180, generic130, generic65, bcd180 |
| sha_accelerator | digital | security | yes | generic130, generic65, bcd180, generic22, generic14 |
| sigma_delta_adc_top | mixed | converter | yes | generic180, generic130, generic65, bcd180 |
| slew_rate_limiter | analog | interface | yes | generic180, generic130, generic65, bcd180 |
| spi_controller | digital | control | yes | generic180, generic130, generic65, bcd180 |
| temperature_sensor | analog | sense | yes | generic180, generic130, generic65, bcd180 |
| trim_circuit | analog | bias | yes | generic180, generic130, generic65, bcd180 |
| true_random_number_generator | analog | security | yes | generic130, generic65, bcd180, generic22, generic14 |
| uart_controller | digital | protocol | yes | generic180, generic130, generic65, bcd180 |
| uwb_transceiver | mixed | interface | yes | generic130, generic65, bcd180, generic22, generic14 |
| voltage_ladder_dac | analog | converter | yes | generic180, generic130, generic65, bcd180 |
| watchdog_timer | digital | sequencing | yes | generic180, generic130, generic65, bcd180 |

## Verification IPs

| VIP | Protocol | Checks |
|-----|----------|--------|
| adc_linearity_vip | Converter linearity | INL/DNL analysis, code histogram, missing codes, monotonicity |
| adc_transient_vip | Converter transient | input stimulus, internal decision nodes, bitstream or DAC activity |
| analog_snapshot_vip | Analog snapshot | waveform presence, minimum sample count, tracked node visibility |
| ble_vip | BLE 5.0 | advertising sequence, connection establishment, attribute exchange, security handshake |
| bms_vip | Battery monitoring | cell voltage monitoring, temperature thresholds, charge balancing, fault detection |
| can_vip | CAN | arbitration, frame format, bit stuffing, CRC validation, acknowledgment |
| canopen_vip | CANopen | CAN frame structure (CAN 2.0A/2.0B), SDO transfer sequence (download/upload, expedited/segmented), PDO mapping and triggering, NMT state machine (BOOT -> OPERATIONAL -> STOPPED), heartbeat producer/consumer timing, emergency (EMCY) message generation, synchronization (SYNC) frame handling, arbitration field collision resolution, transceiver differential signaling integrity, error frame detection and transmission |
| clock_gating_vip | Clock gating control | gating latency from enable to clock shutdown (<2ns typ), enable signal synchronization to clock edge, glitch immunity (no spurious clock edges), clock tree propagation delay matching, setup/hold time verification at gating point, enable signal timing margin analysis, multi-level gating cascade verification, power gating interaction with clock gating, enable signal metastability analysis, duty cycle preservation through gating |
| clock_monitoring_vip | Clock/Oscillator | frequency accuracy, phase continuity, jitter metrics, duty cycle |
| crypto_vip | AES, SHA, crypto | key expansion, encryption/decryption, hash computation, side-channel timing |
| current_consumption_vip | Power monitoring | quiescent current, dynamic current, power sequencing, inrush limiting |
| digital_subsystem_vip | Digital verification | timing compliance, reset sequencing, state machine coverage, functional correctness |
| emc_compliance_vip | Electromagnetic compatibility | EMI immunity, conducted emissions, radiated immunity, ESD margin |
| ethernet_vip | Ethernet 10/100 Base-T | frame format validation (destination, source, type, data, FCS), CRC validation for frame integrity, link detection and auto-negotiation (10/100 Mbps), collision detection and backoff timing, MDI signaling (Manchester encoding), interframe gap (IFG) compliance, jitter and timing margin analysis, transmit/receive signal integrity at PHY interface, power consumption during active transmission |
| frequency_accuracy_vip | Oscillator/Clock accuracy | frequency tolerance, temperature drift, supply sensitivity, long-term stability |
| high_speed_signal_vip | High-speed signaling | rise/fall time, overshoot/undershoot, jitter analysis, crosstalk immunity, impedance matching |
| i2c_vip | I2C | start and stop conditions, acknowledge handshake, data framing, clock stretching |
| i2s_audio_vip | I2S | frame synchronization, clock gating, data alignment, channel separation |
| i3c_vip | MIPI I3C (SDR and DDR) | i2c legacy mode, i3c sdr mode, i3c ddr mode, dynamic address assignment |
| io_electrical_vip | I/O interface | output drive strength, input threshold margin, leakage current, output impedance |
| lin_vip | LIN | break and sync, frame timing, TX/RX thresholding |
| mixed_signal_bridge_vip | Mixed-signal interface | digital-to-analog drive, analog-to-digital thresholding, interface closure |
| nfc_vip | NFC Type 2/3, ISO14443-A | activation sequence, data framing, UID/ATQA, CRC verification |
| noise_performance_vip | Signal integrity | SNR calculation, THD analysis, SFDR measurement, noise floor |
| power_domain_isolation_vip | Analog/Digital isolation | cross-domain leakage, isolation boundary integrity, handshake synchronization, metastability |
| power_sequence_vip | Power-up sequencing | rail order, enable staging, reset release |
| power_supply_vip | Power supply quality | ripple and noise, PSRR, transient response, regulation accuracy, ramp rate |
| precision_dac_vip | DAC conversion | DNL/INL analysis, settling time, output impedance, linearity, code transition |
| profibus_vip | PROFIBUS PA/DP | bit timing and baud rate accuracy (9.6 kbps - 12 Mbps), frame format (start, address, data length, data, CRC, end), slave address and collision handling, CRC validation (CCITT-16), collision detection and resolution (CSMA/CD-like), idle line detection and silence detection, transceiver failsafe biasing, electromagnetic immunity (conducted and radiated), power consumption in different operational modes |
| spi_vip | SPI | transaction decode, register access, reset defaults |
| temperature_corner_vip | Temperature characterization | cold corner performance, hot corner performance, gradient effects, thermal coupling |
| thermal_monitoring_vip | Temperature monitoring | temp sensor accuracy, shutdown threshold, hysteresis, rise time |
| uart_vip | UART | frame formation, baud rate accuracy, parity checking, flow control |
| voltage_regulation_vip | Power supply regulation | DC regulation accuracy, load transient response, line regulation, soft-start behavior |
| wireless_charging_vip | Qi wireless power | coil detection, power negotiation, foreign object detection, alignment |

## Digital Subsystems

| Subsystem | Compatible | Blocks |
|-----------|------------|--------|
| analog_conditioning_plane | yes | programmable_gain_amplifier, low_pass_filter, comparator_array, register_file, control_logic |
| battery_management_plane | yes | battery_cell_monitor, bms_controller, temperature_sensor, register_file, control_logic, interrupt_controller |
| can_node_control_plane | yes | can_controller, spi_controller, register_file, interrupt_controller, control_logic |
| clock_distribution_plane | yes | pll, clock_divider, control_logic |
| clock_gating_plane | yes | control_logic, register_file, clock_divider, interrupt_controller |
| converter_control_plane | yes | spi_controller, register_file, control_logic |
| ethernet_control_plane | yes | ethernet_phy, uart_controller, spi_controller, register_file, interrupt_controller, control_logic |
| frequency_monitoring_plane | yes | frequency_detector, control_logic, register_file, interrupt_controller |
| i2c_sensor_interface | yes | i2c_controller, register_file, interrupt_controller, control_logic |
| infotainment_control_plane | yes | i2s_audio_controller, i2c_controller, uart_controller, register_file, interrupt_controller, control_logic |
| iot_wireless_plane | yes | ble_transceiver, nfc_controller, rf_front_end, i3c_controller, register_file, interrupt_controller |
| lin_node_control_plane | yes | spi_controller, register_file, lin_controller, control_logic |
| multi_rail_power_control | yes | control_logic, reset_generator, register_file, interrupt_controller, temperature_sensor |
| power_conversion_plane | yes | boost_converter, buck_converter, pwm_controller, frequency_detector, control_logic, register_file |
| power_sequencer | yes | control_logic, reset_generator, interrupt_controller, register_file |
| pwm_motor_control_plane | yes | pwm_controller, register_file, control_logic, interrupt_controller |
| rs485_interface_plane | yes | rs485_transceiver, uart_controller, register_file, control_logic |
| safety_monitor_plane | yes | watchdog_timer, temperature_sensor, interrupt_controller, control_logic, reset_generator |
| security_crypto_plane | yes | aes_accelerator, sha_accelerator, true_random_number_generator, register_file, interrupt_controller, control_logic |
| sensor_aggregation_plane | yes | i2c_controller, spi_controller, register_file, interrupt_controller, control_logic |
| sensor_hub_control_plane | yes | spi_controller, register_file, control_logic |
| test_control_plane | yes | uart_controller, spi_controller, register_file, control_logic, interrupt_controller |
| thermal_management_plane | yes | temperature_sensor, watchdog_timer, interrupt_controller, control_logic |
| trim_engine | yes | trim_circuit, voltage_ladder_dac, register_file, control_logic |
| uart_debug_interface | yes | uart_controller, register_file, control_logic |
