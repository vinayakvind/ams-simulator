"""
Enhanced Priority IP Generators and Validators for Cycle 85
Strengthens high_speed_comparator, differential_amplifier, buffered_precision_dac, lvds_receiver
Provides deeper validation coverage, richer integration scenarios, and process-adaptive generators
"""

from __future__ import annotations
from typing import Any, Dict, List

# High-Speed Comparator Enhancements
HIGH_SPEED_COMPARATOR_ENHANCEMENTS = {
    'circuit_variants_extended': [
        'single-stage-high-gain',
        'cascode-gain-two-stage',
        'telescopic-cascode-low-power',
        'folded-cascode-rail-to-rail',
        'dynamic-latch-comparator',
        'regenerative-comparator-array',
    ],
    'process_corner_generators': {
        'FF_SS_mix': {'vth_delta': -0.05, 'beta_boost': 1.25, 'delay_reduction': '15-20%'},
        'SS_FF_mix': {'vth_delta': +0.08, 'beta_reduction': 0.80, 'delay_increase': '30-40%'},
        'TT_nominal': {'vth_delta': 0.0, 'beta_nominal': 1.0, 'delay_nominal': '10ns'},
    },
    'validation_scenarios_deep': [
        'slew_rate_dependency: inject 50-500V/µs input slew with hysteresis tracking',
        'metastability_characterization: critically-biased threshold sweep with timing histogram',
        'array_matching: 8-16 comparator skew measurement with common-centroid layout',
        'frequency_response: -3dB bandwidth measurement with 10MHz to 500MHz sweep',
        'rms_jitter: 100-sample histogram of propagation delay distribution',
        'power_supply_rejection: 0.1-10MHz ripple injection with gain measurement',
        'thermal_drift: 1°C step characterization from 0-125°C',
        'latch_up_immunity: ESD pulse injection with recovery time measurement',
    ],
    'integration_examples': [
        {
            'use_case': 'sar_adc_16bit_feedback_path',
            'comparator_count': 16,
            'configuration': {'bias': '20µA', 'hysteresis': '2mV'},
            'rules': [
                'matched pair layout with <1mm trace length mismatch',
                'common-centroid connection for all 16 cells',
                '<0.5 LSB total skew across comparator array',
            ],
            'targets': ['monotonic code progression', 'INL/DNL <0.5 LSB']
        },
        {
            'use_case': 'ethernet_phy_receive_slicer',
            'comparator_count': 4,
            'configuration': {'bias': '50µA', 'cascade': True},
            'rules': [
                '4-stage cascade for 50mV input range',
                '<100ps cumulative jitter across cascade',
            ],
            'targets': ['eye diagram margin >30%', 'BER <1e-12']
        },
    ]
}

# Differential Amplifier Enhancements
DIFFERENTIAL_AMPLIFIER_ENHANCEMENTS = {
    'circuit_families_expanded': [
        'long-tail-pair-simple',
        'long-tail-pair-cascoded',
        'telescopic-single-ended-output',
        'telescopic-fully-differential',
        'folded-cascode-high-slew',
        'class-ab-output-stage',
    ],
    'gain_configurations': [
        {'gain': 1, 'bw_khz': 500, 'noise_nv_hz': 55, 'power_uw': 80},
        {'gain': 10, 'bw_khz': 5000, 'noise_nv_hz': 95, 'power_uw': 250},
        {'gain': 100, 'bw_khz': 500, 'noise_nv_hz': 150, 'power_uw': 600},
    ],
    'validation_scenarios': [
        'frequency_sweep: 1Hz-10MHz Bode plot with gain/phase margin extraction',
        'offset_drift: ±5µV/°C characterization across -40 to +125°C',
        'cmrr_frequency_dependent: 1kHz->1MHz CMRR degradation',
        'psrr_both_rails: separate VDD and VSS ripple injection',
        'thd_plus_n_sweep: 1kHz fundamental with harmonic sweep',
        'settling_time_precision: 0.1% and 0.01% settling time',
    ],
    'integration_examples': [
        {
            'use_case': 'bridge_sensor_frontend',
            'gain': 100,
            'cmrr_target_db': 100,
            'rules': ['ratiometric biasing', 'offset trim calibration'],
            'targets': ['gain accuracy ±0.1%', 'offset drift <5µV/°C']
        },
        {
            'use_case': 'current_sense_monitor',
            'gain': 50,
            'sense_resistor_mohm': 50,
            'rules': ['high-side current sensing', 'zero-current trim'],
            'targets': ['measurement accuracy ±0.5%', 'offset drift <10µV/°C']
        },
    ]
}

# Buffered Precision DAC Enhancements
BUFFERED_PRECISION_DAC_ENHANCEMENTS = {
    'resolution_variants': [8, 10, 12, 14, 16],
    'architecture_options': [
        'current-source-binary-weighted',
        'r2r-resistor-ladder',
        'capacitor-array-switching',
        'segmented-binary-thermometric-hybrid',
    ],
    'validation_scenarios': [
        'dac_linearity: DNL/INL sweep across all 2^N codes',
        'code_transition_glitch: pedestal energy measurement',
        'settling_time: 8-bit to 16-bit settling verification',
        'output_impedance: frequency-dependent Z_out measurement',
        'temperature_drift: monotonicity across -40 to +125°C',
        'supply_sensitivity: PSRR measurement 0.1-10MHz',
        'load_regulation: output swing vs load current',
    ],
    'integration_examples': [
        {
            'use_case': 'programmable_current_source',
            'dac_resolution': 14,
            'output_range_ua': '1-1000',
            'rules': ['I-V converter', 'temperature stabilization'],
            'targets': ['INL/DNL <±0.5 LSB', 'output accuracy ±1%']
        },
        {
            'use_case': 'trimmed_voltage_reference',
            'dac_resolution': 16,
            'rules': ['bandgap buffering', 'NVM trim storage'],
            'targets': ['reference accuracy ±0.1%', 'Tc <50ppm/°C']
        },
    ]
}

# LVDS Receiver Enhancements
LVDS_RECEIVER_ENHANCEMENTS = {
    'circuit_variants': [
        'passive-termination-direct-input',
        'active-termination-current-sink',
        'fully-differential-transimpedance',
        'cable-equalizer-linear',
        'cable-equalizer-adaptive-dfe',
    ],
    'data_rate_coverage': [100, 250, 500, 1000, 2500, 5000, 10000],  # Mbps
    'validation_scenarios': [
        'eye_diagram: 100M UI samples with margin analysis',
        'differential_threshold: 50-200mV sweep with hysteresis',
        'common_mode_range: ±500mV injection with threshold shift',
        'jitter_tolerance: 100ps-1ns input jitter sweep',
        'pattern_dependent_jitter: PRBS 7/15/23 with histograms',
        'frequency_response: AC coupling effect on low-frequency',
        'crosstalk_injection: adjacent line capacitive coupling',
    ],
    'integration_examples': [
        {
            'use_case': 'ethernet_gigabit_phy',
            'data_rate_mbps': 1000,
            'threshold_mv': 100,
            'rules': [
                'AC-coupled input with 100pF capacitors',
                '3-stage cascade: LNA + TIA + limiting amp',
                'Phase-locked clock recovery',
            ],
            'targets': ['eye margin >30%', 'BER <1e-12', 'jitter <50ps RMS']
        },
        {
            'use_case': 'pci_express_gen3',
            'data_rate_mbps': 8000,
            'equalization': 'linear_ctle',
            'rules': [
                'Continuous-Time Linear Equalizer',
                '4-stage limiting amplifiers',
                '1:4 deserializer with clock recovery',
            ],
            'targets': ['eye >100mV', 'BER <1e-15', 'FOMI margin >3dB']
        },
    ]
}

# VIP Enhancement Scenarios
VIP_ENHANCEMENT_SCENARIOS = {
    'ethernet_vip_mixed_signal': [
        'MDI_transmit_jitter: 50-200ps peak jitter on Manchester clock',
        'receiver_common_mode: ±200mV offset with threshold adaptation',
        'differential_crosstalk: 5-15% capacitive coupling measurement',
        'supply_noise: 100mV 10MHz ripple during data transmission',
        'thermal_drift: -40°C to +125°C propagation delay tracking',
        'substrate_coupling: simultaneous TX/RX crosstalk measurement',
        'magnetic_interference: 50/60Hz common-mode injection (IEC 61000-4-8)',
    ],
    'profibus_vip_mixed_signal': [
        'failsafe_biasing: ±10% resistor value variation with margin',
        'conducted_immunity: 10V/µs 50/60Hz injection tracking BER',
        'ground_bounce: 50V/µs common-mode transient on lines',
        'slew_rate_variation: 10-30V/µs programmable characterization',
        'thermal_coefficient: slew and threshold drift -40 to +85°C',
        'line_impedance_reflections: stub termination mismatch ±20%',
        'multi_node_arbitration: 12-node network simultaneous transmission',
    ],
    'canopen_vip_mixed_signal': [
        'bus_transient_immunity: 50V/µs injection with recovery time',
        'threshold_sweep: 100-400mV dynamic range with CRC validation',
        'bit_timing_error: ±500ppm oscillator drift over long trains',
        'adjacent_crosstalk: coupling between CAN and power rails',
        'temperature_bit_timing: frequency drift -40 to +125°C',
        'node_arbitration: collision-free 8-node at 1Mbps',
        'supply_ripple_on_logic: 100mV peak 1MHz during arbitration',
    ],
    'clock_gating_vip': [
        'metastability_injection: CDC boundary violation detection',
        'cascade_skew: 4-stage gating with timing closure',
        'duty_cycle_distortion: clock distribution delay variation',
        'glitch_detection: peak <0.5V glitch over 100M cycles',
        'power_gating_interaction: gates inactive during power-down',
        'very_low_frequency: 1kHz-1MHz gating settling verification',
    ],
}

# Digital Subsystem Integration Rules
DIGITAL_SUBSYSTEM_INTEGRATION_RULES = {
    'clock_gating_plane': [
        'enable_sync: CDC synchronizers for cross-domain (min 2-flip-flop)',
        'rising_edge_timing: enable capture with <1ns setup margin',
        'output_frequency_cap: gated output never exceeds input clock',
        'cascade_skew: multi-level delays balanced <50ps',
        'duty_cycle_preservation: output ±5% of input',
        'reset_sequencing: async reset gate disable before enable',
        'power_down_mode: all gate enables forced low during power-off',
    ],
    'ethernet_control_plane': [
        'mac_phy_handshake: MII/RMII/GMII timing compliance',
        'collision_detection: simultaneous TX/RX <300ns jam signal',
        'frame_buffering: minimum 256-byte FIFO for back-to-back frames',
        'auto_negotiation: FLP exchange <2 second link-up',
        'carrier_sense: <100ns detection latency from line activity',
        'crc_computation: pipelined CRC-32 during transmission',
    ],
    'safety_monitor_plane': [
        'watchdog_clock: isolated oscillator immune to main clock failure',
        'threshold_hysteresis: ±5% hysteresis on all thresholds',
        'interrupt_latency: <10µs from event to interrupt assertion',
        'fault_counter: counters saturate rather than rollover',
        'cross_domain_sync: 2-stage CDC for reliable fault signaling',
    ],
    'power_conversion_plane': [
        'switching_sync: multiple converters synchronized ±10%',
        'current_sharing: parallel converter <5% imbalance',
        'transient_response: load step recovery <100µs to ±3%',
        'soft_start: enable order enforcement with ramp control',
    ],
}

# Chip Profile Top-Level References
CHIP_PROFILE_TOPLEVELS = {
    'automotive_infotainment_soc': {
        'design_hierarchy': [
            'Top: automotive_infotainment_soc_top (10+ power domains)',
            'analog_domain: bandgap, LDOs, audio_amp, sensor_interface',
            'digital_core: CPU, memory, control_logic',
            'media_domain: video_decoder, audio_processor, graphics',
            'connectivity_domain: ethernet, CAN, LIN, infotainment',
            'safety_domain: watchdog, thermal_monitor, fault_detection',
        ],
        'power_domains': {
            'always_on': '1.2V (always on, <1mW sleep)',
            'core': '1.0V (CPU, 0.5W active)',
            'media': '1.2V (video/audio, 2W peak)',
            'io': '3.3V (interfaces, 0.5W)',
            'safety': '1.2V (isolated, 100mW)',
        },
        'automation_coverage': [
            'power_domain_hierarchy: automated constraint generation',
            'clock_domain_crossing: automated CDC insertion',
            'reset_sequencing: generated from power-on reset spec',
            'isolation_cell_insertion: automated at boundaries',
            'level_shifter_generation: automated IO level conversion',
        ],
        'design_collateral': [
            'integration_guide: 50-page PDF with power/reset/clock',
            'reference_implementation: example RTL with 80% coverage',
            'simulation_regression: 100+ SystemVerilog UVM testbenches',
            'floorplan_template: generic layout guide for 2-3 versions',
        ],
    },
    'industrial_iot_gateway': {
        'design_hierarchy': [
            'Top: iot_gateway_top',
            'wireless_engine: BLE, NFC, WiFi interface',
            'connectivity_engine: Ethernet, RS485, CAN gateway',
            'processing_engine: DSP, ARM M4, state machine',
            'sensor_interface: ADC, temperature, motion sensors',
            'power_management: battery charging, boost/buck',
            'security_engine: AES, SHA, random number generator',
        ],
        'integration_examples': [
            'sensor_to_cloud: ADC -> DSP -> wireless TX <5mW avg',
            'gateway_bridging: simultaneous Ethernet RX and BLE TX',
            'battery_aware_throttling: CPU frequency per charge level',
            'secure_boot: SHA signature verification before execution',
        ],
    },
    'isolated_power_supply_controller': {
        'design_hierarchy': [
            'Top: psu_controller_top (isolated SMPS)',
            'primary_side: PWM controller, gate driver, feedback isolation',
            'secondary_side: isolated voltage feedback, current sensing',
            'isolation_barrier: galvanic isolation at feedback',
            'protection_circuits: over-voltage clamp, current limiting',
        ],
        'isolation_specs': [
            'creepage_clearance: >5mm per IEC 60950-1 Cat III',
            'hi_pot_rating: 3000V AC for 60 seconds',
            'common_mode_voltage: ±2500V transient immunity',
        ],
    },
}

# Validation Coverage Matrix
COMPREHENSIVE_VALIDATION_MATRIX = {
    'process_corners': ['SS@125C', 'TT@27C', 'FF@-40C', 'FS@-40C', 'SF@125C'],
    'temperature_range': '-40 to +125°C (IEC), -40 to +85°C (automotive)',
    'supply_voltage_variation': '±10% on all power supplies',
    'aging_simulation': '100k operating hours equivalent',
    'esd_immunity': '2kV HBM per MIL-STD-883 Method 3015.7',
    'emc_compliance': [
        'conducted_immunity: IEC 61000-4-4 (EFT)',
        'radiated_immunity: IEC 61000-4-3 (1-400MHz)',
        'power_quality: IEC 61000-4-2 (ESD simulation)',
    ],
}

__all__ = [
    'HIGH_SPEED_COMPARATOR_ENHANCEMENTS',
    'DIFFERENTIAL_AMPLIFIER_ENHANCEMENTS',
    'BUFFERED_PRECISION_DAC_ENHANCEMENTS',
    'LVDS_RECEIVER_ENHANCEMENTS',
    'VIP_ENHANCEMENT_SCENARIOS',
    'DIGITAL_SUBSYSTEM_INTEGRATION_RULES',
    'CHIP_PROFILE_TOPLEVELS',
    'COMPREHENSIVE_VALIDATION_MATRIX',
]
