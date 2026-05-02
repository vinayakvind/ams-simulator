"""Enhanced VIP regression scenarios with mixed-signal protocol coupling.

Comprehensive protocol-to-analog coupling scenarios for Ethernet, PROFIBUS,
CANopen, and clock gating VIPs to validate real-world interactions between
digital protocols and analog power/signal integrity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class MixedSignalScenario:
    """Protocol mixed-signal regression test scenario."""
    name: str
    vip: str
    description: str
    
    # Protocol stimulus
    protocol_traffic: dict[str, Any] = field(default_factory=dict)
    
    # Analog stimulus
    analog_coupling: dict[str, Any] = field(default_factory=dict)
    
    # Validation checks
    validation_rules: list[str] = field(default_factory=list)
    
    # Expected outcomes
    expected_behavior: dict[str, Any] = field(default_factory=dict)


# ════════════════════════════════════════════════════════════════════════════
# ETHERNET VIP - Mixed Signal Regressions
# ════════════════════════════════════════════════════════════════════════════

ETHERNET_PHY_SUPPLY_NOISE = MixedSignalScenario(
    name="ethernet_phy_supply_noise_coupling",
    vip="ethernet_vip",
    description="Ethernet PHY resilience to power supply noise and crosstalk",
    
    protocol_traffic={
        "frame_pattern": "64-byte minimum frames",
        "line_rate": "100 Mbps",
        "frame_count": 10000,
        "frame_spacing": "back-to-back (96 ns minimum IFG)",
        "traffic_type": "bidirectional with 50% collision rate",
    },
    
    analog_coupling={
        "supply_noise": {
            "frequency_ranges": ["100 kHz", "10 MHz", "50 MHz"],
            "amplitude_vpp": [0.1, 0.2, 0.5],  # volts
            "injection_point": "VDD_PHY and VDD_IO rails",
            "effect": "Threshold shift, timing jitter",
        },
        "substrate_coupling": {
            "description": "Simultaneous TX and RX with crosstalk",
            "tx_power": "100 mW peak",
            "rx_sensitivity": "-10 dBm (95 dB signal margin)",
            "coupling_percentage": "2-5% signal corruption",
        },
        "temperature_sweep": {
            "range": "-40°C to +125°C",
            "ramp_rate": "1°C/second",
            "effect": "Propagation delay drift, threshold shift",
        },
    },
    
    validation_rules=[
        "Frame reception: <1% BER with supply noise injection",
        "Collision detection: Latency <1µs under supply transients",
        "Auto-negotiation: Link-up within 2 seconds with noise present",
        "Jitter transfer: Phase margin >60° with 200mV supply ripple",
        "Threshold margin: >25% eye opening maintained throughout sweep",
    ],
    
    expected_behavior={
        "pass_rate": ">99%",
        "error_types": ["bit_slip", "threshold_violation", "false_collision"],
        "max_latency_impact": "+50 ns",
        "recovery_time": "<100 µs",
    }
)


ETHERNET_SIMULTANEOUS_TX_RX = MixedSignalScenario(
    name="ethernet_simultaneous_tx_rx_collision",
    vip="ethernet_vip",
    description="True collision handling with simultaneous transmit and receive",
    
    protocol_traffic={
        "tx_pattern": "Continuous frame transmission",
        "rx_pattern": "Continuous frame reception",
        "collision_point": "0.5ms from TX start",
        "collision_duration": "4µs",
        "jam_signal": "32-bit pattern (0x55555555 Manchester)",
    },
    
    analog_coupling={
        "differential_short": {
            "duration_us": 4,
            "impedance_mismatch": "±20Ω",
            "effect": "Signal reflection and timing skew",
        },
        "common_mode_transient": {
            "amplitude": "±2V",
            "slew_rate": "50 V/µs",
            "effect": "Common-mode offset and jitter",
        },
    },
    
    validation_rules=[
        "Collision detection: Jam signal asserted within 400ns",
        "Backoff timing: Binary exponential backoff (1-1023 slots) ±5%",
        "CRC recalculation: Correct FCS after successful retransmit",
        "Signal recovery: Eye diagram margins restored <10µs post-collision",
    ],
    
    expected_behavior={
        "collision_success_rate": "100%",
        "retry_count": "0-5 (exponential backoff)",
        "frame_loss": "0%",
    }
)


# ════════════════════════════════════════════════════════════════════════════
# PROFIBUS VIP - Mixed Signal Regressions
# ════════════════════════════════════════════════════════════════════════════

PROFIBUS_NOISE_MARGIN = MixedSignalScenario(
    name="profibus_noise_immunity_field_conditions",
    vip="profibus_vip",
    description="PROFIBUS resilience to industrial EMI and signal degradation",
    
    protocol_traffic={
        "token_passing": "12 Mbps token-ring protocol",
        "node_count": 8,
        "message_length": "64 bytes maximum",
        "failsafe_biasing": "680Ω mid-supply pull (±900-1200 mV)",
    },
    
    analog_coupling={
        "conducted_emc": {
            "frequency": "50/60 Hz, 100 kHz-1 MHz",
            "amplitude": "100 mV RMS",
            "coupling": "Common-mode on bus",
            "effect": "Threshold shift, false bit detection",
        },
        "radiated_emc": {
            "frequency": "10 MHz - 1 GHz",
            "field_strength": "10 V/m",
            "coupling": "Differential pair pickup",
            "effect": "Jitter, timing skew",
        },
        "amplitude_degradation": {
            "description": "50% signal amplitude reduction",
            "scenario": "Worst-case cable loss over 100m",
            "effect": "Threshold margin reduced to ±100mV",
        },
    },
    
    validation_rules=[
        "Token passing: Zero lost tokens over 1000 cycles",
        "Noise margin: >50% amplitude reduction still detectable",
        "Bit error rate: <1e-9 with EMI present",
        "CCITT-16 CRC: 100% error detection with fault injection",
        "Failsafe state: <100mV hysteresis, no meta-stability",
    ],
    
    expected_behavior={
        "frame_success": ">99.9%",
        "token_loss": "0",
        "recovery_latency": "<100 µs",
    }
)


PROFIBUS_CLOCK_RECOVERY = MixedSignalScenario(
    name="profibus_clock_recovery_with_jitter",
    vip="profibus_vip",
    description="Clock recovery under varying baud rates with jitter injection",
    
    protocol_traffic={
        "baud_rates": [9.6e3, 19.2e3, 93.75e3, 187.5e3, 500e3, 1.5e6, 3e6, 6e6, 12e6],
        "frame_format": "Start bit + 8 data + stop bit + CRC",
        "frame_count_per_rate": 1000,
    },
    
    analog_coupling={
        "tx_jitter": {
            "rms_ps": [50, 100, 200],  # picoseconds
            "jitter_type": "random, periodic, bounded",
            "effect": "Clock recovery loop tracking error",
        },
        "receiver_common_mode_offset": {
            "range": "±200 mV",
            "rate_of_change": "100 mV/µs",
            "effect": "Threshold centering error",
        },
    },
    
    validation_rules=[
        "Symbol alignment: ±50ns tolerance at symbol boundaries",
        "Bit slip detection: Zero undetected slips over 1M bits",
        "Clock phase recovery: Lock time <100ms at each baud rate",
        "Jitter tracking: Clock loop bandwidth 1-10 kHz",
    ],
    
    expected_behavior={
        "successful_recovery": "100% at all baud rates",
        "phase_error": "<±50 ns steady-state",
        "lock_time": "<100 ms per rate change",
    }
)


# ════════════════════════════════════════════════════════════════════════════
# CANopen VIP - Mixed Signal Regressions
# ════════════════════════════════════════════════════════════════════════════

CANOPEN_BUS_ARBITRATION = MixedSignalScenario(
    name="canopen_multilevel_arbitration_with_crosstalk",
    vip="canopen_vip",
    description="CAN bus arbitration with signal integrity degradation",
    
    protocol_traffic={
        "can_id_distribution": ["11-bit (CAN 2.0A)", "29-bit (CAN 2.0B)"],
        "priority_levels": 8,
        "simultaneous_transmitters": 4,
        "arbitration_window": "First 6 bits of CAN ID",
    },
    
    analog_coupling={
        "differential_pair_crosstalk": {
            "coupling_percentage": [5, 10, 15],  # percent
            "near_end_crosstalk": "NEXT_dB at symbol rate",
            "far_end_crosstalk": "FEXT_dB at symbol rate",
            "effect": "Timing skew between CAN_H and CAN_L",
        },
        "termination_impedance_mismatch": {
            "characteristic_impedance": "120Ω ±5%",
            "mismatch_effect": "Ringing and reflection",
            "amplitude_overshoot": "±100 mV",
        },
        "supply_dependent_threshold": {
            "threshold_vdd_sensitivity": "0.1 V/V",
            "supply_ripple": "±100 mV at 100 kHz",
            "effect": "Dynamic threshold variation",
        },
    },
    
    validation_rules=[
        "Arbitration loss: Highest priority frame always wins",
        "Bit timing: Recessive to dominant transition <100ns",
        "Dominant timeout: Dominant level held for ≥6 bits",
        "Stuff bits: Maximum 5 consecutive bits of same polarity",
        "CRC polynomial: 15-bit CRC catches 99.9% of errors",
    ],
    
    expected_behavior={
        "arbitration_success": "100%",
        "frame_loss": "0% (errors handled by retry)",
        "bit_errors": "<1e-9 with worst-case coupling",
    }
)


CANOPEN_REMOTE_FRAME_RESPONSE = MixedSignalScenario(
    name="canopen_rtr_response_latency_under_noise",
    vip="canopen_vip",
    description="Remote transmit request with response timing under noise",
    
    protocol_traffic={
        "rtr_pattern": "Request data from multiple nodes",
        "response_latency_max_us": [100, 500, 1000],
        "node_count": 16,
        "simultaneous_responses": "Bit-by-bit arbitration",
    },
    
    analog_coupling={
        "phase_noise": {
            "spectral_density": "-100 dBc/Hz at 100 kHz offset",
            "integrated_jitter": "<1 ns RMS",
            "effect": "Bit timing phase error",
        },
        "common_mode_current_injection": {
            "amplitude_ma": [10, 50, 100],
            "frequency": "10 MHz - 100 MHz",
            "coupling": "Substrate and ground plane",
            "effect": "Timing skew and threshold shift",
        },
    },
    
    validation_rules=[
        "Response timing: Within specified latency budget",
        "Arbitration: Correct node responds (ID-based priority)",
        "Data integrity: CRC validation on response frame",
        "Retry logic: Automatic retry on timeout <100ms",
    ],
    
    expected_behavior={
        "response_success": ">99.9%",
        "latency_distribution": "Normal distribution around nominal +50%",
        "timeout_rate": "<0.1%",
    }
)


# ════════════════════════════════════════════════════════════════════════════
# CLOCK GATING VIP - Mixed Signal Regressions
# ════════════════════════════════════════════════════════════════════════════

CLOCK_GATING_METASTABILITY = MixedSignalScenario(
    name="clock_gating_enable_metastability_injection",
    vip="clock_gating_vip",
    description="Clock gating with CDC enable signal crossing metastability zone",
    
    protocol_traffic={
        "clock_frequency": [1e6, 100e6, 500e6, 1e9],  # 1 MHz to 1 GHz
        "enable_signal_domain": "Crossing clock domains",
        "gate_stages": [1, 2, 4],  # Cascaded gating levels
    },
    
    analog_coupling={
        "enable_timing_violation": {
            "setup_time": "2 ns",
            "hold_time": "1 ns",
            "violation_magnitude": "±500 ps",
            "effect": "Metastability in latch, unpredictable settling time",
        },
        "power_supply_droop": {
            "magnitude": "±200 mV",
            "slew_rate": "100 V/µs",
            "timing_sensitivity": "±10 ps per 100mV",
            "effect": "Delay variation across gates",
        },
        "temperature_gradient": {
            "rate": "10°C/µs across die",
            "effect": "Differential skew accumulation",
            "skew_per_stage": "±50 ps",
        },
    },
    
    validation_rules=[
        "Glitch-free guarantee: No spurious edges on gated clock output",
        "CDC synchronization: 2-stage minimum latch chain",
        "Duty cycle preservation: ±5% across all gate stages",
        "Frequency capping: Output frequency ≤ input frequency",
        "Enable setup/hold: Timing closure verified with worst-case margins",
    ],
    
    expected_behavior={
        "metastability_occurrence": "Predictable and contained",
        "settling_time": "<500 ps max (MTBF >100 years)",
        "glitch_detection": "0 glitches over 1M clock cycles",
        "duty_cycle_deviation": "<2.5% at each level",
    }
)


CLOCK_GATING_POWER_GATING_INTERACTION = MixedSignalScenario(
    name="clock_gating_power_domain_isolation",
    vip="clock_gating_vip",
    description="Clock gating interaction with power gating control signals",
    
    protocol_traffic={
        "power_domain_states": ["ON", "IDLE", "OFF"],
        "state_transitions": "Continuous power cycling at 1 Hz",
        "gating_stages": 4,
        "duration_cycles": 10000,
    },
    
    analog_coupling={
        "power_rail_discharge": {
            "initial_voltage": 1.8,
            "discharge_target": 0.0,
            "discharge_time": "10 µs",
            "effect": "Clock frequency ramp-down",
        },
        "substrate_transient": {
            "bulk_voltage_overshoot": "±300 mV",
            "dV/dt": "1000 V/s",
            "effect": "Threshold variation, timing uncertainty",
        },
        "power_good_signal": {
            "threshold": "1.6 V",
            "hysteresis": "100 mV",
            "propagation_delay": "<100 ns",
        },
    },
    
    validation_rules=[
        "Gate disable sequencing: Power-off gates held inactive",
        "No spurious clock edges: 100% glitch-free during power transitions",
        "Clean gate re-enable: No metastability on power restoration",
        "Power sequencing: Correct enable/disable order maintained",
    ],
    
    expected_behavior={
        "successful_transitions": "100%",
        "glitch_free_guarantee": "Yes",
        "transition_time": "<10 µs",
        "recovery_time": "<50 µs",
    }
)


# Registry of all VIP regression scenarios
VIP_REGRESSION_SCENARIOS = {
    "ethernet_phy_supply_noise_coupling": ETHERNET_PHY_SUPPLY_NOISE,
    "ethernet_simultaneous_tx_rx_collision": ETHERNET_SIMULTANEOUS_TX_RX,
    "profibus_noise_immunity_field_conditions": PROFIBUS_NOISE_MARGIN,
    "profibus_clock_recovery_with_jitter": PROFIBUS_CLOCK_RECOVERY,
    "canopen_multilevel_arbitration_with_crosstalk": CANOPEN_BUS_ARBITRATION,
    "canopen_rtr_response_latency_under_noise": CANOPEN_REMOTE_FRAME_RESPONSE,
    "clock_gating_enable_metastability_injection": CLOCK_GATING_METASTABILITY,
    "clock_gating_power_domain_isolation": CLOCK_GATING_POWER_GATING_INTERACTION,
}


def get_vip_regression_scenario(scenario_name: str) -> MixedSignalScenario | None:
    """Retrieve a VIP regression scenario by name."""
    return VIP_REGRESSION_SCENARIOS.get(scenario_name)


def list_vip_regression_scenarios(vip_name: str | None = None) -> list[str]:
    """List VIP regression scenarios, optionally filtered by VIP."""
    if vip_name is None:
        return sorted(VIP_REGRESSION_SCENARIOS.keys())
    return sorted([k for k, v in VIP_REGRESSION_SCENARIOS.items() if v.vip == vip_name])


def get_scenarios_by_vip(vip_name: str) -> list[MixedSignalScenario]:
    """Get all regression scenarios for a specific VIP."""
    return [v for v in VIP_REGRESSION_SCENARIOS.values() if v.vip == vip_name]
