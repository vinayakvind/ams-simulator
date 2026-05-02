"""Priority IP Integration Examples for Cycle 91

Demonstrates real-world usage patterns, design rules, and validation approaches
for high_speed_comparator, differential_amplifier, buffered_precision_dac, and
lvds_receiver in system-level applications.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class IPIntegrationExample:
    """Integration example for a priority reusable IP."""
    
    ip_name: str
    use_case: str
    description: str
    ip_count: int = 1
    
    # Circuit configuration
    configuration: Dict[str, Any] = field(default_factory=dict)
    
    # Integration rules
    integration_rules: List[str] = field(default_factory=list)
    
    # Design considerations
    design_considerations: List[str] = field(default_factory=list)
    
    # Validation targets
    validation_targets: Dict[str, Any] = field(default_factory=dict)
    
    # Power and performance
    power_budget_uw: float = 0.0
    area_um2: float = 0.0
    
    # Technology support
    technology_nodes: List[str] = field(default_factory=lambda: ["generic180", "generic130", "generic65", "bcd180"])


# ════════════════════════════════════════════════════════════════════════════
# HIGH-SPEED COMPARATOR Integration Examples
# ════════════════════════════════════════════════════════════════════════════

HSC_SAR_ADC_FEEDBACK = IPIntegrationExample(
    ip_name="high_speed_comparator",
    use_case="16-bit SAR ADC Feedback Path",
    description="Array of matched comparators for successive approximation ADC feedback",
    ip_count=16,
    
    configuration={
        "circuit_topology": "cascode-gain with regenerative latch",
        "gain": "60 V/V",
        "propagation_delay": "<0.8 ns at TT@27C",
        "offset_trim_dac_bits": 10,
        "hysteresis_range": "0-5 mV programmable",
        "bias_current_ua": 20,
        "array_architecture": "common-centroid with matching",
    },
    
    integration_rules=[
        "Match all 16 comparators within <1% gain variation",
        "Trace length matching <1 mm for differential pairs",
        "Common-centroid layout with interdigitated fingers",
        "Each comparator isolated in separate n-well",
        "Bias current source shared with current mirror network",
        "Offset trim DAC routed to center with equalized lengths",
        "<0.5 LSB total skew across array (16-bit SAR)",
        "Latch reset driven from single phase generator",
    ],
    
    design_considerations=[
        "Temperature coefficient tracking <2 ppm/°C for INL preservation",
        "Supply noise coupling: >65 dB PSRR at SAR clock frequency",
        "Latch-up immunity >100 mA hold current",
        "Metastability MTBF calculation for 16-bit resolution",
        "Glitch-free guarantee at 1-8 MHz SAR clock rates",
        "Output buffer rise/fall time matching <100 ps",
    ],
    
    validation_targets={
        "sar_monotonicity": "Guaranteed across all PVT",
        "sar_inl_dnl": "INL/DNL <0.5 LSB",
        "comparator_skew": "<0.5 LSB total array",
        "conversion_time": "<500 ns for 16-bit",
        "power_consumption": "<5 mW per bit",
    },
    
    power_budget_uw=80.0,  # 16 × 5 µW each
    area_um2=2500.0,  # ~2500 µm² per comparator
)

HSC_ETHERNET_RECEIVER_SLICER = IPIntegrationExample(
    ip_name="high_speed_comparator",
    use_case="Ethernet 100Base-TX Receiver Slicer",
    description="4-stage cascaded comparator for eye diagram slicing at 125 MHz",
    ip_count=4,
    
    configuration={
        "circuit_topology": "cascaded dynamic-latch-comparator",
        "gain_per_stage": "8 V/V (32 V/V total)",
        "propagation_delay": "<1 ns per stage",
        "input_range": "50 mV differential (single stage), 6.4 mV total cascade",
        "bias_current_ua": 50,
        "cascade_feedback": "AC-coupled positive feedback",
    },
    
    integration_rules=[
        "Stage 1: 100 mV input threshold detection",
        "Stages 2-4: Gain boosting with <100 ps accumulated jitter",
        "Clock distribution: Single phase to all 4 latch stages",
        "Output buffer: Rail-to-rail CMOS inverter 50-200 µA",
        "Power supply: Separate analog and digital rails <50 mV ripple",
        "Input AC coupling: 10 MHz high-pass with 1% tolerance caps",
    ],
    
    design_considerations=[
        "Hysteresis tuning: 2-5 mV for noise margin vs frequency",
        "Temperature-dependent sensitivity: Trim range ±10% across -40 to +125°C",
        "Jitter accumulation <100 ps across 4-stage cascade",
        "Clock-to-output skew matching <50 ps between stages",
        "No ringing on output: Load capacitance <50 pF per stage",
    ],
    
    validation_targets={
        "eye_margin": ">30% at 125 Mbps",
        "ber_performance": "<1e-12 over 1 hour",
        "jitter_accumulation": "<100 ps RMS",
        "threshold_accuracy": "±5 mV across PVT",
    },
    
    power_budget_uw=200.0,
    area_um2=1200.0,
)


# ════════════════════════════════════════════════════════════════════════════
# DIFFERENTIAL AMPLIFIER Integration Examples
# ════════════════════════════════════════════════════════════════════════════

DA_INSTRUMENTATION_CHANNEL = IPIntegrationExample(
    ip_name="differential_amplifier",
    use_case="Instrumentation Amplifier for Sensor Signal Path",
    description="Single-channel 100x gain with 12-bit ADC interface",
    ip_count=1,
    
    configuration={
        "gain": 100,
        "input_impedance": ">1 MΩ single-ended",
        "gain_accuracy": "±1% across PVT",
        "input_referred_noise": "<100 nV/√Hz",
        "bandwidth": "500 kHz at 100x gain",
        "offset_voltage": "±5 mV trim range (±1mV post-trim)",
        "slew_rate": ">0.05 V/µs at 100x gain",
        "settling_time_to_0_01pct": "<5 µs",
    },
    
    integration_rules=[
        "Gain resistors: 1% tolerance metal-film pair (R_in and R_fb)",
        "Input stage: Buffer each sensor line with 100kΩ resistor",
        "AC coupling: 1 µF ceramic capacitor on input (>1.6V), high ESR acceptable",
        "Output buffer: Directly drives 12-bit SAR ADC (1 MΩ || 5 pF)",
        "Power supply bypassing: 100 nF ceramic + 10 µF tantalum on each rail",
        "Offset trim DAC: Driven by on-chip 10-bit register (SPI accessible)",
    ],
    
    design_considerations=[
        "Gain resistor tolerances: ±1% → ±1% gain accuracy",
        "Temperature coefficient tracking: Both resistors <50 ppm/°C",
        "Sensor bridge excitation: Separate LDO for stable VREF (1.2 V)",
        "EMI/RFI filtering: 10 nF differential mode filter on input",
        "PSRR across supply ripple: >70 dB at 10 kHz supply noise",
    ],
    
    validation_targets={
        "gain_accuracy": "±1%",
        "offset_post_trim": "±0.5 mV",
        "noise_floor": "<10 µV RMS",
        "settling_time": "<5 µs to 0.01%",
        "linearity_thd": "<0.5%",
    },
    
    power_budget_uw=250.0,
    area_um2=800.0,
)

DA_AUDIO_PREAMPLIFIER = IPIntegrationExample(
    ip_name="differential_amplifier",
    use_case="Microphone Preamplifier (MEMS Audio)",
    description="Low-noise 10x preamplifier for MEMS microphone integration",
    ip_count=2,  # Stereo left/right channels
    
    configuration={
        "gain": 10,
        "input_impedance": "100 kΩ differential",
        "gain_bandwidth": "50 kHz at 10x gain",
        "input_referred_noise": "<50 nV/√Hz (20 Hz - 20 kHz)",
        "offset_voltage": "±5 mV trim",
        "slew_rate": ">1 V/µs at 10x gain",
        "settling_time_to_0_1pct": "<1 µs",
        "cmrr": ">80 dB at 1 kHz",
    },
    
    integration_rules=[
        "Microphone source impedance: 1-10 kΩ (MEMS PDM or analog output)",
        "Input coupling: AC coupled 10 µF ceramic for DC blocking",
        "Gain resistors: 1% tolerance, temperature-matched pair",
        "Output buffer: Direct connection to 16-bit ADC (delta-sigma type)",
        "Power supply: Separate analog and digital ground planes (star grounding)",
        "Digital feedthrough: >60 dB isolation between digital and analog clocks",
    ],
    
    design_considerations=[
        "Microphone bias current: <1 µA typical (MEMS input bias)",
        "AC coupling corner frequency: 100 Hz -3dB point (speech optimization)",
        "Frequency response flatness: ±1 dB from 100 Hz - 20 kHz",
        "Noise spectral density: <50 nV/√Hz in speech band (300 Hz - 3 kHz)",
        "THD+N: <1% at typical speech levels (-30 dBFS to 0 dBFS)",
    ],
    
    validation_targets={
        "snr": ">90 dB at 1 kHz",
        "thd_plus_n": "<1%",
        "frequency_response": "±1 dB from 100 Hz - 20 kHz",
        "input_referred_noise": "<50 nV/√Hz",
    },
    
    power_budget_uw=500.0,  # 2 channels × 250 µW each
    area_um2=1600.0,  # 2 channels × 800 µm²
)


# ════════════════════════════════════════════════════════════════════════════
# BUFFERED PRECISION DAC Integration Examples
# ════════════════════════════════════════════════════════════════════════════

BPDA_PROGRAMMABLE_SETPOINT = IPIntegrationExample(
    ip_name="buffered_precision_dac",
    use_case="Programmable Analog Setpoint Generator",
    description="12-bit DAC for LDO feedback reference and threshold tuning",
    ip_count=1,
    
    configuration={
        "resolution": 12,
        "settling_time_0_1pct": "<500 ns",
        "settling_time_0_01pct": "<2 µs",
        "dac_architecture": "R-2R-ladder with charge-redistribution",
        "output_impedance": "<50 Ω",
        "glitch_impulse_energy": "<100 pJ per LSB",
        "monotonicity": "Guaranteed",
        "dnl": "<±0.5 LSB",
        "inl": "<±1 LSB",
    },
    
    integration_rules=[
        "VREF input: Bandgap 1.2 V ±5% stable reference",
        "Output load: 10 kΩ minimum (feedback network input)",
        "Update rate: SPI programmable, 1 kHz to 1 MHz",
        "Startup: <1 µs to final value after power-on or enable",
        "Glitch-free latch: Transparent mode for <2µs settling path",
        "Register access: 16-bit SPI frame (4-bit address + 12-bit data)",
    ],
    
    design_considerations=[
        "Settling time trade-off: 0.1% (500 ns) vs 0.01% (2 µs) modes",
        "Glitch energy injection: <100 pJ limits coupling to sensitive nodes",
        "Code transition linearity: No jump at 0x7FF to 0x800 (binary transitions)",
        "Temperature coefficient: <50 ppm/°C on full-scale value",
        "Supply sensitivity: >60 dB PSRR at 100 kHz ripple frequency",
    ],
    
    validation_targets={
        "setpoint_accuracy": "±0.5% at 25°C",
        "temperature_drift": "<50 ppm/°C",
        "settling_time": "<500 ns to 0.1%",
        "glitch_energy": "<100 pJ",
        "output_impedance": "<50 Ω",
    },
    
    power_budget_uw=150.0,
    area_um2=450.0,
)

BPDA_BIAS_CURRENT_GENERATOR = IPIntegrationExample(
    ip_name="buffered_precision_dac",
    use_case="Bias Current Generator for Analog Macros",
    description="14-bit DAC as programmable current source for bandgap, LDO, and comparator trim",
    ip_count=1,
    
    configuration={
        "resolution": 14,
        "settling_time_0_01pct": "<5 µs",
        "dac_architecture": "Segmented binary + R-2R for MSBs + LSBs",
        "output_impedance": "<100 Ω high-impedance current source",
        "monotonicity": "Guaranteed",
        "dnl": "<±0.8 LSB",
        "inl": "<±1 LSB",
        "current_range": "1 µA - 100 µA programmable",
    },
    
    integration_rules=[
        "Reference voltage: Bandgap 1.2 V ± 5% through 10 kΩ sense resistor",
        "Output feedback: Connected via current-mirror copy to bandgap bias",
        "Trim resolution: 100 µA / 16384 codes ≈ 6 nA per LSB",
        "Supply independence: >70 dB PSRR ensures stable bias across PVT",
        "Digital interface: 16-bit SPI for bias word programming",
        "Temperature compensation: Included in bandgap (no DAC trim needed)",
    ],
    
    design_considerations=[
        "Bias point stability: Feedback network ensures monotonic current increase",
        "Process corner tuning: trim codes different for FF vs SS vs TT corners",
        "Frequency response: >1 MHz bandwidth for fast settling",
        "Noise coupling: Low-impedance sense resistor minimizes bias jitter",
        "Multi-corner support: Separate trim codes for generic130, generic65, bcd180",
    ],
    
    validation_targets={
        "bias_accuracy": "±5% across PVT",
        "settling_time": "<5 µs",
        "current_range": "1 µA - 100 µA",
        "monotonicity": "Guaranteed",
        "psrr": ">70 dB",
    },
    
    power_budget_uw=100.0,
    area_um2=500.0,
)


# ════════════════════════════════════════════════════════════════════════════
# LVDS RECEIVER Integration Examples
# ════════════════════════════════════════════════════════════════════════════

LVDS_HIGH_SPEED_BACKPLANE = IPIntegrationExample(
    ip_name="lvds_receiver",
    use_case="High-Speed Backplane Link (3.2 Gbps)",
    description="8-lane LVDS receiver array for parallel backplane communication",
    ip_count=8,
    
    configuration={
        "data_rate": "3.2 Gbps",
        "receiver_architecture": "regenerative-latch with AC coupling",
        "threshold_setting": "Fixed 100 mV",
        "jitter_tolerance": "<200 ps RMS",
        "propagation_delay": "<2 ns matched across 8 lanes",
        "common_mode_range": "-0.5V to +3.5V",
        "differential_impedance": "100 Ω nominal",
    },
    
    integration_rules=[
        "AC coupling on input: 100 nF high-quality capacitors (low ESR)",
        "Termination: 100 Ω series at transmitter or parallel at receiver endpoint",
        "Trace routing: Differential pair length matching <100 mils",
        "Common mode inductance: <5 nH per pair (controlled loop area)",
        "Bias network: 100 Ω pull-down resistor to mid-supply (1.65V for 3.3V)",
        "Simultaneous switching noise: Guard traces between LVDS lanes",
    ],
    
    design_considerations=[
        "Eye margin closure: >30% at 3.2 Gbps with all PVT corners combined",
        "Jitter budget: <200 ps accumulated across parallel lanes",
        "Crosstalk immunity: NEXT/FEXT < -30 dB at 3.2 GHz",
        "Phase alignment: <50 ps skew across 8 parallel lanes",
        "Clock recovery: PLL jitter transfer <0.3 at data clock frequency",
    ],
    
    validation_targets={
        "data_rate": "3.2 Gbps",
        "ber": "<1e-12",
        "eye_margin": ">30%",
        "lane_skew": "<50 ps",
        "crosstalk_rejection": ">-30 dB",
    },
    
    power_budget_uw=800.0,  # 8 lanes × 100 µW each
    area_um2=2400.0,  # 8 lanes × 300 µm²
)

LVDS_SENSOR_INTERFACE = IPIntegrationExample(
    ip_name="lvds_receiver",
    use_case="Differential Sensor Data Interface (250 Mbps)",
    description="Single-lane LVDS receiver for low-power sensor link",
    ip_count=1,
    
    configuration={
        "data_rate": "250 Mbps",
        "receiver_architecture": "latch-based with programmable threshold",
        "threshold_setting": "Programmable 50-400 mV",
        "jitter_tolerance": "<300 ps RMS",
        "propagation_delay": "<1.5 ns",
        "common_mode_range": "-0.5V to +3.5V",
        "input_coupling": "AC-coupled or DC-coupled (selectable)",
    },
    
    integration_rules=[
        "AC coupling capacitor: 1 µF ceramic for <10 MHz cutoff (slow sensor)",
        "Threshold trim: Digital DAC for hysteresis adjustment 50-400 mV",
        "Output buffer: Low-swing LVDS driver to reduce power",
        "Termination: Optional series termination at source (low power mode)",
        "Ground return: Coplanar traces with return path directly under differential pair",
    ],
    
    design_considerations=[
        "Sensor excitation timing: Separate supply domain for sensor bias",
        "Temperature compensation: Threshold adjustment via on-chip DAC trim",
        "Low-frequency operation: Supports rates from 100 kbps to 250 Mbps",
        "Power efficiency: <50 µW static + <10 µW per bit",
        "Mode selection: AC vs DC coupling switch for sensor type flexibility",
    ],
    
    validation_targets={
        "data_rate": "250 Mbps",
        "ber": "<1e-9",
        "sensitivity": "<100 mV differential",
        "throughput": ">99% link utilization",
        "power_consumption": "<50 µW at idle",
    },
    
    power_budget_uw=100.0,
    area_um2=300.0,
)


# Priority IP Integration Registry
IP_INTEGRATION_EXAMPLES = {
    # High-Speed Comparator examples
    "hsc_sar_adc_feedback": HSC_SAR_ADC_FEEDBACK,
    "hsc_ethernet_slicer": HSC_ETHERNET_RECEIVER_SLICER,
    
    # Differential Amplifier examples
    "da_instrumentation_channel": DA_INSTRUMENTATION_CHANNEL,
    "da_audio_preamplifier": DA_AUDIO_PREAMPLIFIER,
    
    # Buffered Precision DAC examples
    "bpda_programmable_setpoint": BPDA_PROGRAMMABLE_SETPOINT,
    "bpda_bias_current_generator": BPDA_BIAS_CURRENT_GENERATOR,
    
    # LVDS Receiver examples
    "lvds_high_speed_backplane": LVDS_HIGH_SPEED_BACKPLANE,
    "lvds_sensor_interface": LVDS_SENSOR_INTERFACE,
}


def get_ip_integration_examples(ip_name: str) -> list[IPIntegrationExample]:
    """Get all integration examples for a specific priority IP."""
    return [v for v in IP_INTEGRATION_EXAMPLES.values() if v.ip_name == ip_name]


def list_integration_examples() -> list[str]:
    """List all available integration examples."""
    return sorted(IP_INTEGRATION_EXAMPLES.keys())


def get_integration_example(example_name: str) -> IPIntegrationExample | None:
    """Get a specific integration example by name."""
    return IP_INTEGRATION_EXAMPLES.get(example_name)
