"""Reference designs and assembly patterns for priority chip profiles.

This module provides complete reference implementations, design patterns,
integration rules, and validation test benches for the priority chip profiles:
- automotive_infotainment_soc
- industrial_iot_gateway
- isolated_power_supply_controller
- ethernet_sensor_hub
- safe_motor_drive_controller
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ReferenceDesign:
    """Complete reference design for a chip profile."""
    name: str
    profile: str
    description: str
    
    # Floorplan and physical design
    die_size_mm2: float
    power_domains: dict[str, dict[str, Any]] = field(default_factory=dict)
    
    # Integration patterns and rules
    integration_rules: list[str] = field(default_factory=list)
    design_patterns: list[dict[str, Any]] = field(default_factory=list)
    
    # Test bench and validation
    test_scenarios: list[dict[str, Any]] = field(default_factory=list)
    regression_tests: list[str] = field(default_factory=list)
    
    # Documentation and collateral
    design_documents: list[str] = field(default_factory=list)


# ════════════════════════════════════════════════════════════════════════════
# AUTOMOTIVE INFOTAINMENT SoC - Reference Design
# ════════════════════════════════════════════════════════════════════════════

AUTOMOTIVE_INFOTAINMENT_SOC = ReferenceDesign(
    name="automotive_infotainment_soc",
    profile="automotive_infotainment_soc",
    description="Complete in-vehicle infotainment system with multi-protocol connectivity and safety",
    die_size_mm2=500.0,
    
    power_domains={
        "VCORE": {
            "nominal_voltage": 1.8,
            "max_current": 2.0,
            "domain_blocks": ["cpu_core", "dsp", "i2s_audio_controller", "register_file"],
            "dynamic_power": "yes",
            "pdvfs_capable": True,
            "standby_leakage_ua": 50,
        },
        "VANA": {
            "nominal_voltage": 3.3,
            "max_current": 0.5,
            "domain_blocks": ["i2s_audio_controller", "temperature_sensor", "bandgap"],
            "dynamic_power": "minimal",
            "pdvfs_capable": False,
            "standby_leakage_ua": 10,
        },
        "VIO": {
            "nominal_voltage": 3.3,
            "max_current": 1.0,
            "domain_blocks": ["can_transceiver", "uart_controller", "spi_controller", "ethernet_phy"],
            "dynamic_power": "mixed",
            "pdvfs_capable": False,
            "standby_leakage_ua": 25,
        },
        "VREF": {
            "nominal_voltage": 1.2,
            "max_current": 0.05,
            "domain_blocks": ["bandgap", "reference_dac"],
            "dynamic_power": "no",
            "pdvfs_capable": False,
            "standby_leakage_ua": 1,
        },
    },
    
    integration_rules=[
        "Power domain isolation: 4-layer PCB with separate analog and digital return planes",
        "Clock distribution: Master OSC → PLL → clock tree with <50ps skew to all domains",
        "Reset sequencing: POR → watchdog clock stable → VCORE domains → VIO domains (100ns staggered)",
        "CAN/Ethernet routing: Opposite board sides, 100Ω differential impedance ±10%, guard traces every 1mm",
        "Audio path: Dedicated VANA supply with LC filtering, >60dB cross-talk attenuation from digital",
        "Thermal placement: DSP and power amplifier at board corners, >20mm from temperature sensor",
        "Memory: Register file in VCORE domain, I2S buffer in dedicated audio domain with CDC synchronizers",
        "Watchdog: Independent RC oscillator, <±10% frequency tolerance, asynchronous reset assertion",
        "CRC validation: Hardware accelerated for CAN/Ethernet, <1 frame time reporting latency",
    ],
    
    design_patterns=[
        {
            "name": "boot_sequence",
            "description": "Controlled startup with staged voltage ramps and module sequencing",
            "stages": [
                "POR assertion with >100ms debounce",
                "Bandgap startup and VREF settling (<1ms)",
                "Analog LDO (VANA) power-on and biasing stability (<2ms)",
                "Core LDO (VCORE) power-on and DLL lock (< 1ms)",
                "I/O LDO (VIO) power-on (<1ms)",
                "Watchdog armed with independent oscillator confirmation (<0.5ms)",
                "Safety monitor initialization and fault clear (<1ms)",
                "I2S clock enable and buffer initialization (<0.5ms)",
                "CAN transceiver wake-up and bus monitoring (<1ms)",
                "Ethernet PHY auto-negotiation initiation (<1ms)",
            ],
            "max_total_time_ms": 500,
            "rollback_trigger": "Any stage exceeds timeout or watchdog fault",
        },
        {
            "name": "priority_arbitration",
            "description": "Multi-protocol bandwidth arbitration with priority levels",
            "rules": [
                "Priority 0 (Highest): I2S audio (48kHz continuous, 2Mbps reserved)",
                "Priority 1: CAN messaging (100ms window, burst up to 50Mbps)",
                "Priority 2: Ethernet packets (10ms bursts, peak 100Mbps)",
                "Priority 3 (Lowest): CPU/DSP memory and register access",
                "Throttling: Network backpressure applied to prevent audio underrun",
                "I2S buffer maintains >4ms to tolerate network interrupt latency",
            ],
        },
        {
            "name": "thermal_management",
            "description": "Temperature-dependent performance derate strategy",
            "zones": [
                {
                    "temp_range": "0-85°C",
                    "audio_dsp": "100%",
                    "core": "100%",
                    "io": "100%",
                    "actions": "Full performance"
                },
                {
                    "temp_range": "85-105°C",
                    "audio_dsp": "80%",
                    "core": "100%",
                    "io": "90%",
                    "actions": "Throttle DSP and I/O clocks"
                },
                {
                    "temp_range": "105-125°C",
                    "audio_dsp": "50%",
                    "core": "90%",
                    "io": "80%",
                    "actions": "Aggressive throttling"
                },
                {
                    "temp_range": ">125°C",
                    "audio_dsp": "0%",
                    "core": "0%",
                    "io": "0%",
                    "actions": "System shutdown with watchdog recovery"
                },
            ],
            "monitoring_rate_ms": 10,
            "sensor_location": "Near power dissipation hotspot (DSP cluster)",
        },
        {
            "name": "safety_partition",
            "description": "ASIL-B safety isolation with independent domains",
            "domains": [
                {
                    "name": "safety_monitor_plane",
                    "rail": "VCORE_SAFETY (1.8V independent)",
                    "blocks": ["watchdog_timer", "temperature_sensor", "reset_generator"],
                    "oscillator": "On-chip RC with <±10% drift tolerance",
                    "memory": "512B dedicated safety SRAM with ECC",
                    "watchdog_timeout": "10 seconds",
                },
                {
                    "name": "main_core",
                    "rail": "VCORE (1.8V shared)",
                    "blocks": ["cpu", "dsp", "protocol_stacks"],
                    "fault_sources": "Clock loss, reset failure, voltage sag",
                },
            ],
            "cross_domain_sync": "2-stage flip-flops with parity checkers on critical signals",
        },
    ],
    
    test_scenarios=[
        {
            "name": "multi_protocol_stress",
            "description": "Simultaneous I2S, CAN, Ethernet traffic with thermal stress",
            "stimulus": [
                "I2S: 48kHz 16-bit stereo continuous streaming",
                "CAN: 100 messages/second at 1Mbps baud",
                "Ethernet: 64-byte frames at 100Mbps line rate",
                "Temperature: Ramp from 25°C to 125°C over 100 seconds",
            ],
            "validation": [
                "Audio quality: THD+N <0.5% at 1kHz, SNR >90dB",
                "CAN: 0 bit errors, <100µs latency",
                "Ethernet: 0 frame errors, <50ms link recovery",
                "Watchdog: No spurious resets",
            ],
            "duration_sec": 300,
        },
        {
            "name": "power_mode_transitions",
            "description": "Sleep/wake cycles with audio active",
            "stimulus": [
                "Play 5-second audio clip",
                "Enter sleep mode (power domains gated)",
                "Remain in sleep for 2 seconds",
                "Repeat 100 times",
            ],
            "validation": [
                "Audio: No clicks/pops during transitions",
                "Sleep power: <50mW (VIO+VREF only active)",
                "Wake latency: <50ms to audio playback",
                "No register corruption across cycles",
            ],
        },
    ],
    
    regression_tests=[
        "functional_test_lin_asic_top",
        "sar_adc_transient_regression",
        "sigma_delta_adc_transient_regression",
        "ethernet_phy_frame_validation",
        "can_protocol_compliance",
    ],
    
    design_documents=[
        "automotive_infotainment_soc_architecture.md",
        "power_distribution_network_design.md",
        "thermal_analysis_report.html",
        "functional_safety_asil_b_evidence.md",
        "signal_integrity_analysis.md",
        "clock_tree_jitter_budget.md",
        "autosar_rte_integration_guide.md",
        "test_specification.md",
    ]
)


# ════════════════════════════════════════════════════════════════════════════
# INDUSTRIAL IoT GATEWAY - Reference Design
# ════════════════════════════════════════════════════════════════════════════

INDUSTRIAL_IOT_GATEWAY = ReferenceDesign(
    name="industrial_iot_gateway",
    profile="industrial_iot_gateway",
    description="Multi-protocol industrial edge gateway with security acceleration",
    die_size_mm2=450.0,
    
    power_domains={
        "VCORE": {
            "nominal_voltage": 1.8,
            "max_current": 2.5,
            "domain_blocks": ["cpu", "dma_controller", "crypto_accelerator", "memory_compiler"],
            "dynamic_power": "yes",
            "pdvfs_capable": True,
            "standby_leakage_ua": 80,
        },
        "VCRYPTO": {
            "nominal_voltage": 1.8,
            "max_current": 1.0,
            "domain_blocks": ["aes_accelerator", "sha_accelerator"],
            "dynamic_power": "yes",
            "pdvfs_capable": True,
            "standby_leakage_ua": 30,
        },
        "VIO": {
            "nominal_voltage": 3.3,
            "max_current": 2.0,
            "domain_blocks": ["profibus_transceiver", "canopen_controller", "ethernet_phy", "uart_controller"],
            "dynamic_power": "mixed",
            "pdvfs_capable": False,
            "standby_leakage_ua": 40,
        },
        "VBIAS": {
            "nominal_voltage": 1.2,
            "max_current": 0.1,
            "domain_blocks": ["bandgap", "bias_generator"],
            "dynamic_power": "no",
            "pdvfs_capable": False,
            "standby_leakage_ua": 2,
        },
    },
    
    integration_rules=[
        "Multi-protocol coexistence: PROFIBUS@12Mbps, CANopen@1Mbps, Ethernet@100Mbps on separate ground planes",
        "DMA bandwidth: Dedicated high-speed data path for concurrent protocol traffic",
        "Crypto acceleration: AES-256-GCM and SHA-512 with 512-byte key buffer",
        "Redundancy: Dual Ethernet ports with <50ms failover logic",
        "Protocol filtering: Hardware CRC validation for all three protocols",
        "Memory: Local SRAM for packet buffering (>1MB for 100Mbps sustained throughput)",
    ],
    
    design_patterns=[
        {
            "name": "multi_protocol_router",
            "description": "Packet routing and DMA scheduling across PROFIBUS, CANopen, Ethernet",
            "routing_logic": [
                "PROFIBUS packets → protocol stack queue → host CPU",
                "CANopen frames → CAN controller DMA → memory mapped buffer",
                "Ethernet frames → Ethernet MAC → DMA engine → main memory",
                "Priorities: Ethernet interrupt > CAN interrupt > PROFIBUS polling",
            ],
        },
        {
            "name": "security_integration",
            "description": "Hardware security acceleration for industrial protocols",
            "features": [
                "AES-256-GCM for encrypted field device communication",
                "SHA-512 for secure certificate validation",
                "True random number generator for nonce generation",
                "Key storage in dedicated fused ROM",
                "Hardware crypto: 100Mbps throughput for AES-GCM",
            ],
        },
        {
            "name": "failover_strategy",
            "description": "Redundant Ethernet with automatic switchover",
            "rules": [
                "Port A: Primary Gigabit Ethernet interface",
                "Port B: Secondary Gigabit Ethernet interface (standby)",
                "Link monitoring: Both ports monitored at 100ms intervals",
                "Switchover: <50ms from link loss detection to traffic shift",
                "VLAN support: IEEE 802.1Q for traffic segregation",
            ],
        },
    ],
    
    test_scenarios=[
        {
            "name": "multi_protocol_throughput",
            "description": "Sustained 100Mbps Ethernet + 12Mbps PROFIBUS + 1Mbps CANopen",
            "stimulus": [
                "Ethernet: Back-to-back 1518-byte frames",
                "PROFIBUS: 64-byte token-ring messages",
                "CANopen: 64 messages/second at max length",
            ],
            "validation": [
                "Zero frame loss over 1 hour",
                "Packet latency: <5ms 99th percentile",
                "Crypto: AES-256-GCM @ 50Mbps sustained",
            ],
            "duration_sec": 3600,
        },
    ],
    
    regression_tests=[
        "profibus_token_passing_regression",
        "canopen_sdo_access_regression",
        "ethernet_vlan_filtering_regression",
        "crypto_aes_gcm_vector_validation",
        "dma_multi_channel_integration",
    ],
    
    design_documents=[
        "industrial_iot_gateway_architecture.md",
        "multi_protocol_integration_guide.md",
        "security_accelerator_integration.md",
        "dma_controller_design.md",
        "redundancy_failover_logic.md",
    ]
)


# ════════════════════════════════════════════════════════════════════════════
# ETHERNET SENSOR HUB - Reference Design
# ════════════════════════════════════════════════════════════════════════════

ETHERNET_SENSOR_HUB = ReferenceDesign(
    name="ethernet_sensor_hub",
    profile="ethernet_sensor_hub",
    description="Distributed sensor hub with Ethernet connectivity and cloud integration",
    die_size_mm2=350.0,
    
    power_domains={
        "VCORE": {
            "nominal_voltage": 1.8,
            "max_current": 1.0,
            "domain_blocks": ["cpu_core", "adc_frontend", "signal_processor", "register_file"],
            "dynamic_power": "yes",
            "pdvfs_capable": True,
            "standby_leakage_ua": 40,
        },
        "VANA": {
            "nominal_voltage": 3.3,
            "max_current": 0.3,
            "domain_blocks": ["sar_adc_top", "analog_mux", "programmable_gain_amplifier"],
            "dynamic_power": "minimal",
            "pdvfs_capable": False,
            "standby_leakage_ua": 5,
        },
        "VIO": {
            "nominal_voltage": 3.3,
            "max_current": 0.5,
            "domain_blocks": ["ethernet_phy", "uart_controller", "i2c_controller"],
            "dynamic_power": "mixed",
            "pdvfs_capable": False,
            "standby_leakage_ua": 10,
        },
    },
    
    integration_rules=[
        "ADC frontend: Dedicated VANA supply with on-die filtering for sensor signal conditioning",
        "Ethernet: IEEE 802.3 compliant Gigabit interface with auto-negotiation",
        "Sensor interface: Multiple analog inputs (8-16 channels) with programmable gain",
        "Thermal compensation: On-die temperature sensor with ADC calibration tracking",
        "Timestamp: Precision timestamp injection at ADC and Ethernet interface for correlation",
    ],
    
    design_patterns=[
        {
            "name": "sensor_data_pipeline",
            "description": "Real-time sensor data acquisition with Ethernet transmission",
            "pipeline": [
                "Analog input → PGA (gain=1x to 100x) → ADC (16-bit @ 1kHz)",
                "ADC output → timestamp injection → FIFO buffer",
                "Ethernet MAC → UDP packet generation → transmission at 100Mbps",
                "DMA: Direct memory transfer for minimal latency",
            ],
        },
    ],
    
    test_scenarios=[
        {
            "name": "sensor_accuracy_validation",
            "description": "Multi-channel ADC with environmental stress",
            "stimulus": [
                "8 analog inputs: 0-3.3V range, swept at 1Hz",
                "Temperature: 0°C to 85°C ramp",
                "Ethernet: Back-to-back transmission of sensor data",
            ],
            "validation": [
                "ADC INL: <±1 LSB across all channels",
                "DNL: <±0.5 LSB",
                "Monotonicity: Guaranteed across all codes",
                "Ethernet: 0 packet loss at 100Mbps",
            ],
        },
    ],
    
    regression_tests=[
        "sar_adc_16bit_linearity",
        "multi_channel_crosstalk_analysis",
        "ethernet_frame_transmission",
        "thermal_sensor_calibration",
    ],
    
    design_documents=[
        "ethernet_sensor_hub_architecture.md",
        "sensor_signal_conditioning_design.md",
        "adc_calibration_methodology.md",
        "cloud_integration_guide.md",
    ]
)


# ════════════════════════════════════════════════════════════════════════════
# SAFE MOTOR DRIVE CONTROLLER - Reference Design
# ════════════════════════════════════════════════════════════════════════════

SAFE_MOTOR_DRIVE_CONTROLLER = ReferenceDesign(
    name="safe_motor_drive_controller",
    profile="safe_motor_drive_controller",
    description="Safety-critical motor drive with functional safety (ASIL-D) and redundancy",
    die_size_mm2=600.0,
    
    power_domains={
        "VCORE": {
            "nominal_voltage": 1.8,
            "max_current": 3.0,
            "domain_blocks": ["cpu_core", "pwm_controller", "gate_driver_control"],
            "dynamic_power": "yes",
            "pdvfs_capable": False,  # Fixed frequency for motor control
            "standby_leakage_ua": 100,
        },
        "VCORE_SAFETY": {
            "nominal_voltage": 1.8,
            "max_current": 1.0,
            "domain_blocks": ["watchdog_timer", "safety_monitor", "fault_detection"],
            "dynamic_power": "no",  # Independent, always-on safety domain
            "pdvfs_capable": False,
            "standby_leakage_ua": 50,
        },
        "VGATE": {
            "nominal_voltage": 5.0,
            "max_current": 5.0,
            "domain_blocks": ["isolated_gate_driver", "pwm_output_stage"],
            "dynamic_power": "yes",
            "pdvfs_capable": False,
            "standby_leakage_ua": 200,
        },
    },
    
    integration_rules=[
        "Motor drive output: Isolated gate drivers for 3-phase motor control",
        "Safety: Dual redundant PWM with fault containment zones (ASIL-D)",
        "Monitoring: Phase current sensing with integrated amplifiers",
        "Isolation: Galvanic isolation between control and power stages (>1kV)",
        "Thermal: Integrated temperature sensors for overtemp shutdown",
        "CAN: Functional safety CAN with error handling",
    ],
    
    design_patterns=[
        {
            "name": "safety_redundancy",
            "description": "Dual-channel safety monitoring with SIL-3 compliance",
            "channels": [
                "Channel A: Main PWM generation and motor control",
                "Channel B: Shadow PWM generation and independent monitoring",
                "Voter: Compares outputs, triggers shutdown on mismatch",
                "Watchdog: Independent oscillator, <±10% tolerance",
            ],
        },
        {
            "name": "fault_containment",
            "description": "Containment of faults to prevent hazardous failures",
            "zones": [
                "Zone A: Main motor control logic",
                "Zone B: Safety monitoring and redundancy logic",
                "Zone C: Gate drive output stage",
                "Barriers: Error checking at zone boundaries",
            ],
        },
    ],
    
    test_scenarios=[
        {
            "name": "motor_stress_test",
            "description": "Extended motor operation with fault injection",
            "stimulus": [
                "Motor: 1kHz PWM, varying duty cycle 10-90%",
                "Load: Ramped current from 0 to 50A",
                "Temperature: 25°C to 125°C ramp over 1 hour",
                "Faults: Injected at 10 min intervals (open gate, short, etc.)",
            ],
            "validation": [
                "Zero undetected faults",
                "Shutdown latency: <10ms after fault",
                "Redundancy: Both channels track within <1%",
            ],
            "duration_sec": 3600,
        },
    ],
    
    regression_tests=[
        "pwm_controller_frequency_accuracy",
        "gate_driver_timing_margin",
        "current_sense_amplifier_linearity",
        "watchdog_independent_verification",
        "can_safety_protocol_validation",
    ],
    
    design_documents=[
        "safe_motor_drive_controller_asil_d.md",
        "functional_safety_evidence_package.md",
        "redundancy_architecture.md",
        "gate_drive_isolation_design.md",
        "motor_control_theory_and_tuning.md",
        "failure_mode_analysis.md",
    ]
)


# Registry of all reference designs
REFERENCE_DESIGNS = {
    "automotive_infotainment_soc": AUTOMOTIVE_INFOTAINMENT_SOC,
    "industrial_iot_gateway": INDUSTRIAL_IOT_GATEWAY,
    "ethernet_sensor_hub": ETHERNET_SENSOR_HUB,
    "safe_motor_drive_controller": SAFE_MOTOR_DRIVE_CONTROLLER,
}


def get_reference_design(profile_name: str) -> Optional[ReferenceDesign]:
    """Retrieve a reference design by profile name."""
    return REFERENCE_DESIGNS.get(profile_name)


def list_reference_designs() -> list[str]:
    """List all available reference designs."""
    return sorted(REFERENCE_DESIGNS.keys())
