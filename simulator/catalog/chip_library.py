"""Catalog of reusable IPs, VIPs, and chip assembly profiles."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from simulator.agents.tech_mapper import TechMapper


REUSABLE_IP_LIBRARY: dict[str, dict[str, Any]] = {
    "bandgap": {
        "name": "Bandgap Reference",
        "domain": "analog",
        "category": "reference",
        "generator": "bandgap_ref",
        "ports": ["VDD", "VREF", "GND", "EN"],
        "aliases": ["bandgap_ref", "bandgap_reference"],
        "description": "Master 1.2 V reference for mixed-signal chips.",
        "role": "Provides a stable reference for regulators, comparators, and analog bias paths.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "ldo_analog": {
        "name": "Analog LDO",
        "domain": "analog",
        "category": "power",
        "generator": "ldo_analog",
        "ports": ["VIN", "VOUT", "GND", "VREF", "EN"],
        "aliases": ["ldo_ana"],
        "description": "Regulated analog rail generator for sensor, reference, and interface domains.",
        "role": "Creates a quiet analog rail from a higher-voltage source.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "ldo_digital": {
        "name": "Digital LDO",
        "domain": "analog",
        "category": "power",
        "generator": "ldo_digital",
        "ports": ["VIN", "VOUT", "GND", "VREF", "EN"],
        "aliases": ["ldo_dig"],
        "description": "Low-noise regulator for digital core and control logic domains.",
        "role": "Generates the digital core supply from the parent analog rail.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "ldo_lin": {
        "name": "LIN Rail LDO",
        "domain": "analog",
        "category": "power",
        "generator": "ldo_lin",
        "ports": ["VIN", "VOUT", "GND", "VREF", "EN"],
        "aliases": ["ldo_lin_driver"],
        "description": "Automotive-facing regulator for LIN bus driver domains.",
        "role": "Creates the LIN transceiver supply from VBAT or another HV source.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "lin_transceiver": {
        "name": "LIN Transceiver",
        "domain": "mixed",
        "category": "interface",
        "generator": "lin_transceiver",
        "ports": ["VBAT", "VDD5", "VDDIO", "GND", "TXD", "RXD", "LIN", "EN"],
        "aliases": ["lin_tx_rx", "lin_txrx"],
        "description": "Mixed-signal LIN physical interface with driver and receiver paths.",
        "role": "Bridges digital control signals to the automotive LIN bus and back.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "spi_controller": {
        "name": "SPI Controller",
        "domain": "digital",
        "category": "control",
        "generator": "spi_controller",
        "ports": ["clk", "rst_n", "sclk", "mosi", "miso", "cs_n"],
        "aliases": ["spi"],
        "description": "Register access path for software-programmable mixed-signal chips.",
        "role": "Provides serial register access into the chip control plane.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "register_file": {
        "name": "Register File",
        "domain": "digital",
        "category": "control",
        "generator": "register_file",
        "ports": ["clk", "rst_n", "wr_en", "addr", "wdata", "rdata"],
        "aliases": ["registers", "reg_file"],
        "description": "Central register bank for configuration, status, and trim control.",
        "role": "Holds chip configuration state and status visibility.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "lin_controller": {
        "name": "LIN Controller",
        "domain": "digital",
        "category": "protocol",
        "generator": "lin_controller",
        "ports": ["clk", "rst_n", "tx_req", "rx_valid", "baud_div"],
        "aliases": ["lin_protocol"],
        "description": "Protocol state machine for LIN framing, timing, and control.",
        "role": "Owns the LIN protocol engine and timing behavior.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "control_logic": {
        "name": "Control Logic",
        "domain": "digital",
        "category": "sequencing",
        "generator": "control_logic",
        "ports": ["clk", "rst_n", "en_bgr", "en_ana", "en_dig", "en_if"],
        "aliases": ["ctrl_logic"],
        "description": "Chip-level sequencing and enable orchestration logic.",
        "role": "Coordinates power-up order, mode transitions, and safety gating.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "sar_adc_top": {
        "name": "SAR ADC Top",
        "domain": "mixed",
        "category": "converter",
        "source": "examples/standard_circuits/sar_adc.spice",
        "ports": [],
        "aliases": ["sar_adc"],
        "description": "Top-level successive-approximation ADC reference implementation.",
        "role": "Provides a reusable sampled-data converter macro for sensor or monitor chips.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
        "verification": {
            "case_id": "TOP-SAR-ADC",
            "category": "Top",
            "standard": "Internal ADC architecture spec",
            "description": "Top-level transient snapshot for the imported SAR ADC reference design.",
            "analysis": "transient",
            "settings": {"tstop": 100e-6, "tstep": 100e-9},
            "checks": [
                {"type": "has_key", "key": "V(analog_in)", "description": "Analog input waveform captured"},
                {"type": "has_any_key", "keys": ["V(dac_out)", "V(sh_out)", "V(comp_out)"], "description": "Internal SAR conversion nodes are present"},
                {"type": "min_length", "key": "time", "min": 100, "description": "Transient simulation produced enough samples"},
            ],
        },
    },
    "sigma_delta_adc_top": {
        "name": "Sigma-Delta ADC Top",
        "domain": "mixed",
        "category": "converter",
        "source": "examples/standard_circuits/sigma_delta_adc.spice",
        "ports": [],
        "aliases": ["sigma_delta_adc"],
        "description": "Top-level sigma-delta ADC reference implementation.",
        "role": "Provides an oversampled converter macro for sensing and monitoring chips.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
        "verification": {
            "case_id": "TOP-SIGMA-DELTA-ADC",
            "category": "Top",
            "standard": "Internal ADC architecture spec",
            "description": "Top-level transient snapshot for the imported Sigma-Delta ADC reference design.",
            "analysis": "transient",
            "settings": {"tstop": 2e-3, "tstep": 100e-9},
            "checks": [
                {"type": "has_key", "key": "V(analog_in)", "description": "Analog input waveform captured"},
                {"type": "has_key", "key": "V(bitstream)", "description": "Modulator bitstream is present"},
                {"type": "has_any_key", "keys": ["V(dec_filt)", "V(fb_dac)", "V(int_out)"], "description": "Internal sigma-delta nodes are present"},
                {"type": "min_length", "key": "time", "min": 1000, "description": "Transient simulation produced enough samples"},
            ],
        },
    },
    "sample_hold_frontend": {
        "name": "Sample and Hold Frontend",
        "domain": "analog",
        "category": "converter",
        "source": "examples/adc/sample_hold_cmos.spice",
        "ports": [],
        "aliases": ["sample_hold"],
        "description": "Reusable sample-and-hold front-end stage for ADC assembly.",
        "role": "Captures the analog input and holds it stable for conversion.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "dac_r2r_4bit": {
        "name": "R-2R DAC 4-bit",
        "domain": "analog",
        "category": "converter",
        "source": "examples/adc/dac_r2r_4bit.spice",
        "ports": [],
        "aliases": ["r2r_dac"],
        "description": "Reusable DAC building block for converter and mixed-signal control designs.",
        "role": "Converts digital control words into analog voltage levels.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "comparator_cmos": {
        "name": "CMOS Comparator",
        "domain": "analog",
        "category": "sense",
        "source": "examples/adc/comparator_cmos.spice",
        "ports": [],
        "aliases": ["comparator"],
        "description": "Reusable comparator for converter and monitor macros.",
        "role": "Compares analog levels for thresholding and bit decisions.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "buck_converter": {
        "name": "Buck Converter",
        "domain": "analog",
        "category": "power",
        "source": "examples/standard_circuits/buck_converter.spice",
        "ports": [],
        "aliases": ["buck"],
        "description": "Switching regulator reference for PMIC and power-management chip assembly.",
        "role": "Generates efficient lower-voltage rails from higher-voltage sources.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "temperature_sensor": {
        "name": "Temperature Sensor",
        "domain": "analog",
        "category": "sense",
        "generator": "temperature_sensor",
        "ports": ["VDD", "GND", "TEMP_OUT", "EN"],
        "aliases": ["temp_sensor", "temp_mon"],
        "description": "On-die temperature sensor for thermal monitoring and protection.",
        "role": "Provides die temperature feedback for power sequencing and thermal shutdown.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "current_mirror": {
        "name": "Current Mirror",
        "domain": "analog",
        "category": "bias",
        "generator": "current_mirror",
        "ports": ["VDD", "GND", "I_IN", "I_OUT"],
        "aliases": ["current_source", "bias_cell"],
        "description": "Precision current steering circuit for analog bias and reference generation.",
        "role": "Duplicates reference currents for distributed bias across analog blocks.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "operational_amplifier": {
        "name": "Operational Amplifier",
        "domain": "analog",
        "category": "sense",
        "generator": "opamp",
        "ports": ["VDD", "VSS", "VIN_P", "VIN_N", "VOUT", "VBIAS"],
        "aliases": ["opamp", "op_amp"],
        "description": "Reusable operational amplifier macro for instrumentation and filtering.",
        "role": "Provides high-gain analog signal processing for sensor conditioning.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "precision_voltage_reference": {
        "name": "Precision Voltage Reference",
        "domain": "analog",
        "category": "reference",
        "generator": "precision_vref",
        "ports": ["VDD", "GND", "VREF", "EN"],
        "aliases": ["vref", "precision_ref"],
        "description": "High-accuracy voltage reference for data converters and comparators.",
        "role": "Provides calibrated reference voltage for precision analog circuits.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "charge_pump": {
        "name": "Charge Pump",
        "domain": "analog",
        "category": "power",
        "generator": "charge_pump",
        "ports": ["VDD", "GND", "VOUT", "CLK", "EN"],
        "aliases": ["pump", "voltage_multiplier"],
        "description": "Switched-capacitor voltage converter for high-voltage generation.",
        "role": "Creates higher-voltage rails or negative voltages from single-supply sources.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "low_pass_filter": {
        "name": "Low-Pass Filter",
        "domain": "analog",
        "category": "filter",
        "generator": "lpf_rc",
        "ports": ["VIN", "VOUT", "GND"],
        "aliases": ["lpf", "rc_filter"],
        "description": "RC low-pass filter for noise rejection and anti-aliasing.",
        "role": "Attenuates high-frequency noise before ADC input or sensitive analog nodes.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "analog_multiplexer": {
        "name": "Analog Multiplexer",
        "domain": "analog",
        "category": "interface",
        "generator": "analog_mux",
        "ports": ["VDD", "GND", "SEL", "IN", "OUT"],
        "aliases": ["mux", "analog_switch"],
        "description": "High-speed analog switch matrix for channel selection.",
        "role": "Routes multiple analog signals to a single converter or processing path.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "i2c_controller": {
        "name": "I2C Controller",
        "domain": "digital",
        "category": "protocol",
        "generator": "i2c_controller",
        "ports": ["clk", "rst_n", "scl", "sda", "int_n"],
        "aliases": ["i2c", "iic"],
        "description": "I2C master/slave interface for sensor and peripheral communication.",
        "role": "Provides inter-chip communication for multi-device sensor platforms.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "uart_controller": {
        "name": "UART Controller",
        "domain": "digital",
        "category": "protocol",
        "generator": "uart_controller",
        "ports": ["clk", "rst_n", "tx", "rx", "cts_n", "rts_n"],
        "aliases": ["uart", "serial"],
        "description": "UART/serial interface for host communication.",
        "role": "Provides serial debug and data port to external host or console.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "watchdog_timer": {
        "name": "Watchdog Timer",
        "domain": "digital",
        "category": "sequencing",
        "generator": "watchdog_timer",
        "ports": ["clk", "rst_n", "wd_en", "wd_kick", "wd_rst_n"],
        "aliases": ["watchdog", "wdt"],
        "description": "System watchdog for fault detection and recovery.",
        "role": "Monitors system health and forces reset on timeout for robustness.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "interrupt_controller": {
        "name": "Interrupt Controller",
        "domain": "digital",
        "category": "sequencing",
        "generator": "interrupt_controller",
        "ports": ["clk", "rst_n", "int_req", "int_mask", "int_stat", "int_prio"],
        "aliases": ["intc", "irq_controller"],
        "description": "Prioritized interrupt dispatcher for multi-source event handling.",
        "role": "Arbitrates and prioritizes multiple interrupt sources to CPU.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "can_transceiver": {
        "name": "CAN Transceiver",
        "domain": "mixed",
        "category": "interface",
        "generator": "can_transceiver",
        "ports": ["VDD", "GND", "TXD", "RXD", "CANH", "CANL", "EN"],
        "aliases": ["can_txrx", "can_phy"],
        "description": "CAN bus physical layer interface for automotive networking.",
        "role": "Bridges digital CAN protocol signals to automotive CAN bus.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "can_controller": {
        "name": "CAN Controller",
        "domain": "digital",
        "category": "protocol",
        "generator": "can_controller",
        "ports": ["clk", "rst_n", "txd", "rxd", "int_n"],
        "aliases": ["can"],
        "description": "CAN protocol engine for automotive messaging.",
        "role": "Implements CAN 2.0A/B protocol state machine and frame handling.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "memory_compiler": {
        "name": "Memory Compiler",
        "domain": "digital",
        "category": "storage",
        "generator": "memory_compiler",
        "ports": ["clk", "rst_n", "addr", "din", "dout", "wr_en", "rd_en"],
        "aliases": ["sram", "memory"],
        "description": "Embedded SRAM macro for configuration and data storage.",
        "role": "Provides local storage for register settings, calibration, and runtime state.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "clock_divider": {
        "name": "Clock Divider",
        "domain": "digital",
        "category": "sequencing",
        "generator": "clock_divider",
        "ports": ["clk_in", "rst_n", "div_ratio", "clk_out"],
        "aliases": ["clkdiv"],
        "description": "Programmable clock frequency divider for multi-rate systems.",
        "role": "Generates slower clock domains for power-efficient processing.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
}


VERIFICATION_IP_LIBRARY: dict[str, dict[str, Any]] = {
    "spi_vip": {
        "name": "SPI Verification IP",
        "protocol": "SPI",
        "checks": ["transaction decode", "register access", "reset defaults"],
        "command": "python designs/framework/scripts/run_regression.py --design {design}",
        "description": "Exercises the serial programming path and register map visibility.",
    },
    "lin_vip": {
        "name": "LIN Verification IP",
        "protocol": "LIN",
        "checks": ["break and sync", "frame timing", "TX/RX thresholding"],
        "command": "python designs/framework/scripts/run_regression.py --design {design}",
        "description": "Covers LIN protocol and mixed-signal bus behavior.",
    },
    "power_sequence_vip": {
        "name": "Power Sequence VIP",
        "protocol": "Power-up sequencing",
        "checks": ["rail order", "enable staging", "reset release"],
        "command": "python designs/framework/scripts/run_regression.py --design {design}",
        "description": "Checks rail bring-up order and control-logic sequencing assumptions.",
    },
    "analog_snapshot_vip": {
        "name": "Analog Snapshot VIP",
        "protocol": "Analog snapshot",
        "checks": ["waveform presence", "minimum sample count", "tracked node visibility"],
        "command": "python designs/framework/scripts/run_design_snapshot.py --design {design}",
        "description": "Turns a block verification spec into a normalized regression artifact.",
    },
    "adc_transient_vip": {
        "name": "ADC Transient VIP",
        "protocol": "Converter transient",
        "checks": ["input stimulus", "internal decision nodes", "bitstream or DAC activity"],
        "command": "python designs/framework/scripts/run_design_snapshot.py --design {design}",
        "description": "Validates converter activity over a sampled-data transient window.",
    },
    "mixed_signal_bridge_vip": {
        "name": "Mixed-Signal Bridge VIP",
        "protocol": "Mixed-signal interface",
        "checks": ["digital-to-analog drive", "analog-to-digital thresholding", "interface closure"],
        "command": "python designs/framework/scripts/run_regression.py --design {design}",
        "description": "Checks top-level mixed-signal bridge behavior between digital logic and analog interfaces.",
    },
    "i2c_vip": {
        "name": "I2C Verification IP",
        "protocol": "I2C",
        "checks": ["start and stop conditions", "acknowledge handshake", "data framing", "clock stretching"],
        "command": "python designs/framework/scripts/run_regression.py --design {design}",
        "description": "Validates I2C master/slave protocol compliance and timing.",
    },
    "uart_vip": {
        "name": "UART Verification IP",
        "protocol": "UART",
        "checks": ["frame formation", "baud rate accuracy", "parity checking", "flow control"],
        "command": "python designs/framework/scripts/run_regression.py --design {design}",
        "description": "Exercises serial communication framing, timing, and error handling.",
    },
    "can_vip": {
        "name": "CAN Verification IP",
        "protocol": "CAN",
        "checks": ["arbitration", "frame format", "bit stuffing", "CRC validation", "acknowledgment"],
        "command": "python designs/framework/scripts/run_regression.py --design {design}",
        "description": "Validates CAN 2.0 protocol compliance, messaging, and bus arbitration.",
    },
    "clock_monitoring_vip": {
        "name": "Clock Monitoring VIP",
        "protocol": "Clock/Oscillator",
        "checks": ["frequency accuracy", "phase continuity", "jitter metrics", "duty cycle"],
        "command": "python designs/framework/scripts/run_design_snapshot.py --design {design}",
        "description": "Monitors oscillator and clock divider performance across corners.",
    },
    "thermal_monitoring_vip": {
        "name": "Thermal Monitoring VIP",
        "protocol": "Temperature monitoring",
        "checks": ["temp sensor accuracy", "shutdown threshold", "hysteresis", "rise time"],
        "command": "python designs/framework/scripts/run_design_snapshot.py --design {design}",
        "description": "Validates temperature sensor linearity and thermal shutdown protection.",
    },
    "current_consumption_vip": {
        "name": "Current Consumption VIP",
        "protocol": "Power monitoring",
        "checks": ["quiescent current", "dynamic current", "power sequencing", "inrush limiting"],
        "command": "python designs/framework/scripts/run_design_snapshot.py --design {design}",
        "description": "Measures steady-state and transient current consumption across all rails.",
    },
    "digital_subsystem_vip": {
        "name": "Digital Subsystem VIP",
        "protocol": "Digital verification",
        "checks": ["timing compliance", "reset sequencing", "state machine coverage", "functional correctness"],
        "command": "python designs/framework/scripts/run_regression.py --design {design}",
        "description": "Validates digital logic timing, sequencing, and functional behavior.",
    },
}


DIGITAL_SUBSYSTEM_LIBRARY: dict[str, dict[str, Any]] = {
    "lin_node_control_plane": {
        "name": "LIN Node Control Plane",
        "blocks": ["spi_controller", "register_file", "lin_controller", "control_logic"],
        "description": "Integrated digital subsystem for protocol control, configuration, and sequencing.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "converter_control_plane": {
        "name": "Converter Control Plane",
        "blocks": ["spi_controller", "register_file", "control_logic"],
        "description": "Digital control subsystem for sampling cadence, trim, and observability.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "sensor_hub_control_plane": {
        "name": "Sensor Hub Control Plane",
        "blocks": ["spi_controller", "register_file", "control_logic"],
        "description": "Shared digital control and telemetry plane for mixed-signal sensor chips.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
}


CHIP_PROFILE_LIBRARY: dict[str, dict[str, Any]] = {
    "lin_node_asic": {
        "name": "LIN Node ASIC",
        "summary": "Automotive LIN node with integrated analog rails, transceiver, and digital control plane.",
        "headline": "Integrated LIN chip assembly from reusable power, interface, and digital IP.",
        "narrative": "This profile combines the reusable bandgap, regulator, LIN interface, and control-plane IP blocks into an automotive-oriented mixed-signal chip scaffold.",
        "standard": "ISO 17987 / LIN 2.2A",
        "tags": ["automotive", "lin", "mixed-signal", "ip library", "vip"],
        "blocks": ["bandgap", "ldo_analog", "ldo_digital", "ldo_lin", "lin_transceiver", "spi_controller", "register_file", "lin_controller", "control_logic"],
        "vips": ["spi_vip", "lin_vip", "power_sequence_vip", "mixed_signal_bridge_vip"],
        "digital_subsystems": ["lin_node_control_plane"],
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "sar_adc_macro": {
        "name": "SAR ADC Macro",
        "summary": "Converter-oriented chip scaffold centered on a reusable SAR ADC macro and digital control hooks.",
        "headline": "Reusable SAR ADC chip assembly with verification hooks baked in.",
        "narrative": "This profile packages the available SAR ADC macro and supporting control/VIP pieces into a reusable converter design scaffold.",
        "standard": "Internal ADC architecture reference",
        "tags": ["adc", "sar", "data converter", "ip library", "vip"],
        "blocks": ["sar_adc_top", "spi_controller", "register_file", "control_logic"],
        "vips": ["adc_transient_vip", "analog_snapshot_vip", "spi_vip"],
        "digital_subsystems": ["converter_control_plane"],
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "sigma_delta_macro": {
        "name": "Sigma-Delta ADC Macro",
        "summary": "Oversampled converter scaffold centered on a reusable sigma-delta ADC macro and its control plane.",
        "headline": "Reusable sigma-delta converter chip assembly with integrated validation flow.",
        "narrative": "This profile packages the available sigma-delta ADC macro and the reusable digital control path for monitoring and sensing designs.",
        "standard": "Internal ADC architecture reference",
        "tags": ["adc", "sigma-delta", "data converter", "ip library", "vip"],
        "blocks": ["sigma_delta_adc_top", "spi_controller", "register_file", "control_logic"],
        "vips": ["adc_transient_vip", "analog_snapshot_vip", "spi_vip"],
        "digital_subsystems": ["converter_control_plane"],
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "mixed_signal_sensor_hub": {
        "name": "Mixed-Signal Sensor Hub",
        "summary": "Sensor/control chip scaffold combining references, rails, multiple converter macros, and shared digital control.",
        "headline": "Sensor-hub chip assembly from reusable analog, converter, and digital subsystem IP.",
        "narrative": "This profile combines power/reference infrastructure with multiple converter macros and a shared digital control plane so new monitor or sensor chips start from integrated building blocks instead of a blank architecture.",
        "standard": "Internal sensor and monitor architecture reference",
        "tags": ["sensor hub", "mixed-signal", "adc", "control plane", "vip"],
        "blocks": ["bandgap", "ldo_analog", "ldo_digital", "sar_adc_top", "sigma_delta_adc_top", "spi_controller", "register_file", "control_logic"],
        "vips": ["spi_vip", "power_sequence_vip", "adc_transient_vip", "analog_snapshot_vip"],
        "digital_subsystems": ["sensor_hub_control_plane"],
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "power_management_unit": {
        "name": "Power Management Unit",
        "summary": "PMU-oriented chip scaffold combining references, regulators, switching conversion, and control-plane logic.",
        "headline": "Reusable PMU chip assembly with analog power IP and digital control integration.",
        "narrative": "This profile starts a power-management chip from reusable bandgap, regulator, switching, and digital-control assets already in the repository.",
        "standard": "Internal PMU architecture reference",
        "tags": ["pmu", "power", "ldo", "buck", "vip"],
        "blocks": ["bandgap", "ldo_analog", "ldo_digital", "buck_converter", "spi_controller", "register_file", "control_logic"],
        "vips": ["power_sequence_vip", "spi_vip", "analog_snapshot_vip"],
        "digital_subsystems": ["sensor_hub_control_plane"],
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
}


def _ordered_unique(items: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def technology_supported(entry: dict[str, Any], technology: str) -> bool:
    """Return whether one catalog entry supports the requested technology."""
    supported = entry.get("technology_support", [])
    if not supported:
        return True
    return technology in supported


def list_supported_technologies() -> list[dict[str, Any]]:
    """Return all known technology mappings."""
    return TechMapper.list_technologies()


def _list_catalog_entries(
    catalog: dict[str, dict[str, Any]],
    technology: str | None = None,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for key, value in sorted(catalog.items()):
        payload = deepcopy(value)
        payload["key"] = key
        if technology is not None:
            payload["compatible"] = technology_supported(payload, technology)
        entries.append(payload)
    return entries


def list_reusable_ips(technology: str | None = None) -> list[dict[str, Any]]:
    """List reusable IP blocks, optionally marking technology compatibility."""
    return _list_catalog_entries(REUSABLE_IP_LIBRARY, technology=technology)


def list_verification_ips() -> list[dict[str, Any]]:
    """List reusable verification IP entries."""
    return _list_catalog_entries(VERIFICATION_IP_LIBRARY)


def list_digital_subsystems(technology: str | None = None) -> list[dict[str, Any]]:
    """List reusable digital subsystem groupings."""
    return _list_catalog_entries(DIGITAL_SUBSYSTEM_LIBRARY, technology=technology)


def list_chip_profiles(technology: str | None = None) -> list[dict[str, Any]]:
    """List reusable chip assembly profiles."""
    return _list_catalog_entries(CHIP_PROFILE_LIBRARY, technology=technology)


def _get_catalog_entry(catalog: dict[str, dict[str, Any]], key: str, entry_type: str) -> dict[str, Any]:
    try:
        return deepcopy(catalog[key])
    except KeyError as exc:
        raise KeyError(f"Unknown {entry_type}: {key}") from exc


def get_reusable_ip(key: str) -> dict[str, Any]:
    """Return one reusable IP entry."""
    return _get_catalog_entry(REUSABLE_IP_LIBRARY, key, "IP")


def get_verification_ip(key: str) -> dict[str, Any]:
    """Return one verification IP entry."""
    return _get_catalog_entry(VERIFICATION_IP_LIBRARY, key, "VIP")


def get_digital_subsystem(key: str) -> dict[str, Any]:
    """Return one digital subsystem entry."""
    return _get_catalog_entry(DIGITAL_SUBSYSTEM_LIBRARY, key, "digital subsystem")


def get_chip_profile(key: str) -> dict[str, Any]:
    """Return one chip assembly profile."""
    return _get_catalog_entry(CHIP_PROFILE_LIBRARY, key, "chip profile")


def compose_chip_profile(
    profile_key: str,
    design_name: str,
    technology: str,
    include_ips: list[str] | None = None,
    exclude_ips: list[str] | None = None,
) -> dict[str, Any]:
    """Compose a reusable chip profile into create_design-compatible metadata."""
    profile = get_chip_profile(profile_key)
    if not technology_supported(profile, technology):
        raise ValueError(f"Chip profile '{profile_key}' is not supported on technology '{technology}'")

    selected_keys = _ordered_unique(list(profile.get("blocks", [])) + list(include_ips or []))
    selected_keys = [key for key in selected_keys if key not in set(exclude_ips or [])]

    blocks: dict[str, dict[str, Any]] = {}
    reusable_ips: list[dict[str, Any]] = []
    for ip_key in selected_keys:
        ip = get_reusable_ip(ip_key)
        if not technology_supported(ip, technology):
            raise ValueError(f"Reusable IP '{ip_key}' is not supported on technology '{technology}'")

        blocks[ip_key] = {
            "type": ip.get("domain", "mixed"),
            "generator": ip.get("generator", ""),
            "source": ip.get("source", ""),
            "ports": deepcopy(ip.get("ports", [])),
            "description": ip.get("description", ""),
            "role": ip.get("role", ""),
            "aliases": deepcopy(ip.get("aliases", [])),
            "category": ip.get("category", ""),
            "technology_support": deepcopy(ip.get("technology_support", [])),
            "verification": deepcopy(ip.get("verification", {})),
            "params": deepcopy(ip.get("params", {})),
        }
        reusable_ips.append(
            {
                "key": ip_key,
                "name": ip.get("name", ip_key),
                "domain": ip.get("domain", "mixed"),
                "category": ip.get("category", ""),
                "technology_support": deepcopy(ip.get("technology_support", [])),
                "description": ip.get("description", ""),
            }
        )

    verification_ips: list[dict[str, Any]] = []
    for vip_key in profile.get("vips", []):
        vip = get_verification_ip(vip_key)
        verification_ips.append(
            {
                "key": vip_key,
                "name": vip.get("name", vip_key),
                "protocol": vip.get("protocol", ""),
                "checks": deepcopy(vip.get("checks", [])),
                "command": str(vip.get("command", "")).format(design=design_name),
                "description": vip.get("description", ""),
            }
        )

    digital_subsystems: list[dict[str, Any]] = []
    for subsystem_key in profile.get("digital_subsystems", []):
        subsystem = get_digital_subsystem(subsystem_key)
        if not technology_supported(subsystem, technology):
            raise ValueError(f"Digital subsystem '{subsystem_key}' is not supported on technology '{technology}'")
        digital_subsystems.append(
            {
                "key": subsystem_key,
                "name": subsystem.get("name", subsystem_key),
                "blocks": deepcopy(subsystem.get("blocks", [])),
                "description": subsystem.get("description", ""),
                "technology_support": deepcopy(subsystem.get("technology_support", [])),
            }
        )

    design_manifest = {
        "headline": profile.get("headline", ""),
        "summary": profile.get("summary", ""),
        "narrative": profile.get("narrative", ""),
        "standard": profile.get("standard", ""),
        "tags": _ordered_unique(list(profile.get("tags", [])) + ["reusable chip assembly", technology]),
    }

    return {
        "blocks": blocks,
        "chip_profile": {
            "key": profile_key,
            "name": profile.get("name", profile_key),
            "summary": profile.get("summary", ""),
            "technology_support": deepcopy(profile.get("technology_support", [])),
        },
        "reusable_ips": reusable_ips,
        "verification_ips": verification_ips,
        "digital_subsystems": digital_subsystems,
        "design_manifest": design_manifest,
    }


__all__ = [
    "compose_chip_profile",
    "get_chip_profile",
    "get_digital_subsystem",
    "get_reusable_ip",
    "get_verification_ip",
    "list_chip_profiles",
    "list_digital_subsystems",
    "list_reusable_ips",
    "list_supported_technologies",
    "list_verification_ips",
    "technology_supported",
]