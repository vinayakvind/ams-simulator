"""Mixed-signal regression test generator for protocol and interface verification.

Generates comprehensive test scenarios combining analog and digital validation
for priority VIP and reusable IP items.
"""

from __future__ import annotations

from typing import Any
from dataclasses import dataclass


@dataclass
class RegressionScenario:
    """A single mixed-signal regression test scenario."""

    name: str
    description: str
    analog_stimulus: dict[str, Any]
    digital_stimulus: dict[str, Any]
    validation_metrics: list[str]
    pass_fail_criteria: dict[str, Any]


class MixedSignalRegressionGenerator:
    """Generates mixed-signal regression scenarios for VIP validation."""

    def generate_ethernet_phy_regressions(self) -> list[RegressionScenario]:
        """Generate comprehensive Ethernet PHY mixed-signal test scenarios."""
        scenarios = []

        # Jitter and timing margin tests
        scenarios.append(
            RegressionScenario(
                name="eth_phy_transmit_jitter_margin",
                description="Transmit jitter sweep 0-150ps RMS with receiver sensitivity analysis",
                analog_stimulus={
                    "jitter_type": "gaussian_rms",
                    "jitter_amount_range": [0, 50, 100, 150],
                    "target_signal": "MDI_transmit",
                    "frequency": "100Mbps",
                    "duration_frames": 1000,
                },
                digital_stimulus={
                    "frame_sequence": "back_to_back_64byte_minimum",
                    "frame_count": 1000,
                    "inter_frame_gap": "96_bittime",
                    "error_injection": None,
                },
                validation_metrics=[
                    "bit_error_rate",
                    "frame_loss_count",
                    "receiver_lock_time",
                    "clock_recovery_phase_margin",
                ],
                pass_fail_criteria={
                    "bit_error_rate": {"max": 1e-9},
                    "frame_loss_count": {"max": 0},
                    "receiver_lock_time": {"max": "10µs"},
                    "clock_recovery_phase_margin": {"min": 45},  # degrees
                },
            )
        )

        # Common-mode offset and threshold margin
        scenarios.append(
            RegressionScenario(
                name="eth_phy_receiver_common_mode_immunity",
                description="Receiver threshold margin with ±300mV common-mode offset variation",
                analog_stimulus={
                    "common_mode_offset": [-300, -200, -100, 0, 100, 200, 300],
                    "offset_unit": "mV",
                    "target_signal": "MDI_differential_pair",
                    "sweep_rate": "1mV/µs",
                    "hold_duration": "100ms",
                },
                digital_stimulus={
                    "frame_sequence": "manchester_pattern_test",
                    "patterns": ["0x0000", "0xFFFF", "0xAAAA", "0x5555"],
                    "pattern_repeat": 100,
                },
                validation_metrics=[
                    "threshold_margin_percent",
                    "bit_error_rate",
                    "hysteresis_measurement",
                ],
                pass_fail_criteria={
                    "threshold_margin_percent": {"min": 25},
                    "bit_error_rate": {"max": 1e-9},
                    "hysteresis_measurement": {"max": "50mV"},
                },
            )
        )

        # Noise and crosstalk immunity
        scenarios.append(
            RegressionScenario(
                name="eth_phy_noise_immunity_stress",
                description="AWGN injection with SNR sweep 10-30dB and cross-coupling stress",
                analog_stimulus={
                    "noise_type": "awgn",
                    "snr_range": [10, 15, 20, 25, 30],
                    "crosstalk_coupling": ["0%", "5%", "10%"],
                    "coupled_signals": ["MDI_clock", "power_rail_noise"],
                    "duration": "1s",
                },
                digital_stimulus={
                    "frame_sequence": "continuous_traffic",
                    "frame_rate": "100Mbps",
                    "payload_pattern": "random",
                    "frame_count": 100000,
                },
                validation_metrics=[
                    "bit_error_rate",
                    "frame_error_rate",
                    "timing_jitter_accumulation",
                ],
                pass_fail_criteria={
                    "bit_error_rate": {"max": 1e-6},
                    "frame_error_rate": {"max": 1e-4},
                    "timing_jitter_accumulation": {"max": "200ps"},
                },
            )
        )

        # Transient response and recovery
        scenarios.append(
            RegressionScenario(
                name="eth_phy_collision_transient_recovery",
                description="Collision event with dual transmitter activation and recovery timing",
                analog_stimulus={
                    "collision_event_type": "dual_transmitter_simultaneous",
                    "collision_duration": "10µs",
                    "jam_signal_pattern": "0x32",  # 32-bit jam pattern
                    "transient_slew_rate": "100V/µs",
                },
                digital_stimulus={
                    "tx_enable_timing": ["simultaneous", "offset_100ns"],
                    "backoff_slots": [0, 1, 2, 4, 8, 16],
                    "recovery_frame_sequence": "single_frame",
                },
                validation_metrics=[
                    "collision_detection_latency",
                    "jam_signal_pattern_match",
                    "receiver_recovery_time",
                    "first_recovery_frame_valid",
                ],
                pass_fail_criteria={
                    "collision_detection_latency": {"max": "400ns"},
                    "jam_signal_pattern_match": {"min": 95},  # percent
                    "receiver_recovery_time": {"max": "1µs"},
                    "first_recovery_frame_valid": {"min": 95},  # percent
                },
            )
        )

        # Temperature coefficient analysis
        scenarios.append(
            RegressionScenario(
                name="eth_phy_temperature_coefficient_drift",
                description="Propagation delay and jitter drift across -40°C to +125°C",
                analog_stimulus={
                    "temperature_profile": "corner_sweep",
                    "temperature_corners": [-40, 0, 27, 85, 125],
                    "corner_units": "celsius",
                    "soak_time_per_corner": "100ms",
                    "ramp_rate": "5°C/ms",
                },
                digital_stimulus={
                    "frame_sequence": "repeating_64byte_frames",
                    "frame_rate": "100Mbps",
                    "frame_count": 10000,
                },
                validation_metrics=[
                    "propagation_delay_drift",
                    "threshold_shift",
                    "jitter_temperature_coefficient",
                ],
                pass_fail_criteria={
                    "propagation_delay_drift": {"max": "100ps"},
                    "threshold_shift": {"max": "30mV"},
                    "jitter_temperature_coefficient": {"max": "2ps/°C"},
                },
            )
        )

        return scenarios

    def generate_isolated_gate_driver_regressions(self) -> list[RegressionScenario]:
        """Generate mixed-signal regression scenarios for isolated gate driver."""
        scenarios = []

        # Isolation voltage stress
        scenarios.append(
            RegressionScenario(
                name="gate_driver_isolation_voltage_margin",
                description="Primary-to-secondary isolation with 3.5kV DC stress and transient immunity",
                analog_stimulus={
                    "isolation_dc_voltage": 3500,  # 3.5kV nominal
                    "voltage_stress_range": [0, 1750, 3500, 5250],
                    "transient_overstress": {"peak": 4200, "duration": "1µs"},
                    "test_duration": "10s",
                },
                digital_stimulus={
                    "gate_drive_signal": "PWM",
                    "duty_cycle_range": [10, 50, 90],
                    "frequency_list": [1, 10, 100, 500],  # kHz
                    "frequency_unit": "kHz",
                },
                validation_metrics=[
                    "isolation_breakdown_voltage",
                    "leakage_current",
                    "signal_transmission_error_rate",
                    "propagation_delay_stability",
                ],
                pass_fail_criteria={
                    "isolation_breakdown_voltage": {"min": 3500},
                    "leakage_current": {"max": "1µA"},
                    "signal_transmission_error_rate": {"max": 0},
                    "propagation_delay_stability": {"max": "50ns_variation"},
                },
            )
        )

        # EMI immunity with conducted noise
        scenarios.append(
            RegressionScenario(
                name="gate_driver_emi_immunity_conducted",
                description="Conducted EMI injection on primary and secondary sides with sensitivity analysis",
                analog_stimulus={
                    "emi_source": "conducted_noise",
                    "noise_frequency_range": [1, 100],  # MHz
                    "noise_amplitude_range": [0, 50, 100, 200],  # mV
                    "injection_node": ["primary_vcc", "secondary_vcc", "gnd_plane"],
                    "duration_per_frequency": "10ms",
                },
                digital_stimulus={
                    "gate_output_frequency": [10, 100, 500],  # kHz
                    "duty_cycle": 50,
                    "test_pattern": "continuous_switching",
                },
                validation_metrics=[
                    "bit_error_rate",
                    "gate_timing_error",
                    "false_transition_count",
                ],
                pass_fail_criteria={
                    "bit_error_rate": {"max": 0},
                    "gate_timing_error": {"max": "10ns"},
                    "false_transition_count": {"max": 0},
                },
            )
        )

        # Dead-time accuracy and cross-conduction prevention
        scenarios.append(
            RegressionScenario(
                name="gate_driver_deadtime_cross_conduction",
                description="Dead-time accuracy sweep 0-2µs with overlapping gate detection",
                analog_stimulus={
                    "deadtime_setting": ["100ns", "200ns", "500ns", "1µs", "2µs"],
                    "gate_a_drive": "5V_logic_drive",
                    "gate_b_drive": "5V_logic_drive",
                },
                digital_stimulus={
                    "input_pwm_frequency": 100,  # kHz
                    "duty_cycle_range": [20, 50, 80],
                    "deadtime_program_value": [1, 2, 5, 10, 20],  # units of 100ns
                    "test_duration_per_setting": "100ms",
                },
                validation_metrics=[
                    "gate_a_off_to_gate_b_on_delay",
                    "gate_b_off_to_gate_a_on_delay",
                    "cross_conduction_time",
                    "output_short_energy_dissipation",
                ],
                pass_fail_criteria={
                    "gate_a_off_to_gate_b_on_delay": {"equals": "programmed_deadtime"},
                    "gate_b_off_to_gate_a_on_delay": {"equals": "programmed_deadtime"},
                    "cross_conduction_time": {"max": "50ns"},
                    "output_short_energy_dissipation": {"max": "100µJ"},
                },
            )
        )

        # Bootstrap capacitor charging and sustaining
        scenarios.append(
            RegressionScenario(
                name="gate_driver_bootstrap_sustainability",
                description="Bootstrap capacitor charging, sustaining, and leakage characterization",
                analog_stimulus={
                    "bootstrap_capacitor_value": ["10µF", "47µF", "100µF"],
                    "low_side_gate_frequency": [1, 10, 100],  # kHz
                    "low_side_on_time": "100µs",
                    "temperature": [-40, 85, 125],  # °C
                },
                digital_stimulus={
                    "gate_sequence": "low_side_switching_boost_charge",
                    "boost_charge_cycles": 1000,
                    "charge_period": "50µs",
                    "sustain_period": "1s",
                },
                validation_metrics=[
                    "bootstrap_voltage_rise_time",
                    "bootstrap_voltage_final_value",
                    "leakage_current_quiescent",
                    "bootstrap_discharge_time",
                ],
                pass_fail_criteria={
                    "bootstrap_voltage_rise_time": {"max": "10µs"},
                    "bootstrap_voltage_final_value": {"min": "9V"},
                    "leakage_current_quiescent": {"max": "100nA"},
                    "bootstrap_discharge_time": {"min": "10s"},
                },
            )
        )

        # Fault tolerance and soft-error immunity
        scenarios.append(
            RegressionScenario(
                name="gate_driver_fault_tolerance_soft_errors",
                description="Single-bit upset (SBU) and transient fault injection with recovery",
                analog_stimulus={
                    "fault_injection_type": "single_bit_transient",
                    "fault_duration": ["100ps", "1ns", "10ns"],
                    "fault_location": ["state_machine", "DAC_trim", "delay_line"],
                    "fault_injection_count": 10000,
                },
                digital_stimulus={
                    "gate_drive_pattern": "continuous_1kHz_switching",
                    "monitoring_duration": "1s",
                },
                validation_metrics=[
                    "fault_detection_latency",
                    "functional_recovery_time",
                    "gate_output_anomaly_count",
                ],
                pass_fail_criteria={
                    "fault_detection_latency": {"max": "1µs"},
                    "functional_recovery_time": {"max": "100ns"},
                    "gate_output_anomaly_count": {"max": 0},
                },
            )
        )

        return scenarios

    def generate_precision_dac_regressions(self) -> list[RegressionScenario]:
        """Generate mixed-signal regression scenarios for precision DAC."""
        scenarios = []

        # Monotonicity verification across all codes
        scenarios.append(
            RegressionScenario(
                name="precision_dac_monotonicity_full_sweep",
                description="Complete DAC code sweep with monotonicity verification and DNL/INL analysis",
                analog_stimulus={
                    "dac_settling_time": "1µs",
                    "output_filter": "first_order_rc",
                    "filter_cutoff": "100kHz",
                    "measurement_settling": "2µs",
                },
                digital_stimulus={
                    "code_sequence": "full_monotonic_sweep",
                    "code_range": ["0", "2^resolution - 1"],
                    "step_direction": ["ascending", "descending"],
                    "dwell_time_per_code": "5µs",
                },
                validation_metrics=[
                    "monotonicity_violations",
                    "inl_max_deviation",
                    "dnl_max_deviation",
                    "integral_nonlinearity_curve",
                    "differential_nonlinearity_histogram",
                ],
                pass_fail_criteria={
                    "monotonicity_violations": {"max": 0},
                    "inl_max_deviation": {"max": "2LSB"},
                    "dnl_max_deviation": {"max": "1LSB"},
                },
            )
        )

        # Settling time and glitch measurement
        scenarios.append(
            RegressionScenario(
                name="precision_dac_settling_glitch_analysis",
                description="Settling time measurement with glitch energy quantification at code transitions",
                analog_stimulus={
                    "measurement_resolution": "1mV",
                    "sampling_rate": "100Msps",
                    "settling_definition": "within_0.5LSB_final_value",
                    "glitch_detection_threshold": "1mV",
                },
                digital_stimulus={
                    "code_transitions": ["single_bit_changes", "maximum_transitions"],
                    "transition_patterns": ["0_to_full_scale", "mid_scale_to_mid_scale"],
                    "repetition_count": 1000,
                },
                validation_metrics=[
                    "settling_time_90_percent",
                    "settling_time_99_percent",
                    "glitch_energy",
                    "glitch_peak_voltage",
                    "glitch_duration",
                ],
                pass_fail_criteria={
                    "settling_time_90_percent": {"max": "1µs"},
                    "settling_time_99_percent": {"max": "3µs"},
                    "glitch_energy": {"max": "10nV·s"},
                    "glitch_peak_voltage": {"max": "10LSB"},
                },
            )
        )

        # Temperature and supply coefficient analysis
        scenarios.append(
            RegressionScenario(
                name="precision_dac_temperature_supply_coefficient",
                description="Temperature and supply variation effects on gain, offset, and linearity",
                analog_stimulus={
                    "temperature_range": [-40, 0, 27, 85, 125],
                    "supply_voltage_sweep": [4.75, 5.0, 5.25],  # 5V ±5%
                    "soak_time_per_condition": "50ms",
                },
                digital_stimulus={
                    "code_sequence": "linearity_test_points",
                    "test_codes": [0, 128, 256, 512, 1024, 2048, 4095],
                    "repetitions_per_code": 100,
                },
                validation_metrics=[
                    "gain_variation_vs_temp",
                    "offset_variation_vs_temp",
                    "gain_variation_vs_supply",
                    "offset_variation_vs_supply",
                    "inl_variation_vs_temp",
                ],
                pass_fail_criteria={
                    "gain_variation_vs_temp": {"max": "50ppm/°C"},
                    "offset_variation_vs_temp": {"max": "2µV/°C"},
                    "gain_variation_vs_supply": {"max": "0.05%/V"},
                    "offset_variation_vs_supply": {"max": "1mV/V"},
                    "inl_variation_vs_temp": {"max": "2LSB_across_range"},
                },
            )
        )

        # Load and slew-rate dependent behavior
        scenarios.append(
            RegressionScenario(
                name="precision_dac_load_slew_dependency",
                description="DAC performance with varying load capacitance and slew-rate constraints",
                analog_stimulus={
                    "load_capacitance": [1, 10, 100, 1000],  # pF
                    "load_resistance": [1, 10, 100],  # kΩ
                    "slew_rate_limit": ["unlimited", "1V/µs", "10V/µs"],
                    "settling_tolerance": "0.5LSB",
                },
                digital_stimulus={
                    "code_transitions": "maximum_step_changes",
                    "transition_count": 1000,
                },
                validation_metrics=[
                    "settling_time_vs_load",
                    "slew_rate_achieved",
                    "linearity_vs_load",
                    "power_supply_rejection_ratio",
                ],
                pass_fail_criteria={
                    "settling_time_vs_load": {"max": "10µs"},
                    "linearity_vs_load": {"inl_change": {"max": "2LSB"}},
                    "power_supply_rejection_ratio": {"min": "60dB"},
                },
            )
        )

        return scenarios

    def generate_all_regression_scenarios(self) -> dict[str, list[RegressionScenario]]:
        """Generate all regression scenarios for cycle 88 priority items."""
        return {
            "ethernet_phy": self.generate_ethernet_phy_regressions(),
            "isolated_gate_driver": self.generate_isolated_gate_driver_regressions(),
            "precision_dac": self.generate_precision_dac_regressions(),
        }

    def export_regression_summary(self) -> dict[str, Any]:
        """Export summary of generated regression scenarios."""
        all_scenarios = self.generate_all_regression_scenarios()

        summary = {}
        for component, scenarios in all_scenarios.items():
            summary[component] = {
                "scenario_count": len(scenarios),
                "scenarios": [
                    {
                        "name": s.name,
                        "description": s.description,
                        "validation_metrics": s.validation_metrics,
                    }
                    for s in scenarios
                ],
            }

        return {
            "cycle": 88,
            "generated_at": "2026-05-03",
            "total_scenarios": sum(len(s) for s in all_scenarios.values()),
            "by_component": summary,
        }
