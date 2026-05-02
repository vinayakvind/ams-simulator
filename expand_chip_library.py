#!/usr/bin/env python
"""
Expand the chip library with new IPs, VIPs, subsystems, and chip profiles.
This script adds concrete improvements to expand reusable component coverage.
"""

import sys
from pathlib import Path

# Add repo to path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

from simulator.catalog.chip_library import (
    REUSABLE_IP_LIBRARY,
    VERIFICATION_IP_LIBRARY,
    DIGITAL_SUBSYSTEM_LIBRARY,
    CHIP_PROFILE_LIBRARY,
)

# New Reusable IPs to add
NEW_REUSABLE_IPS = {
    "gpio_controller": {
        "name": "GPIO Controller",
        "domain": "digital",
        "category": "interface",
        "generator": "gpio_controller",
        "ports": ["clk", "rst_n", "gpio_pad", "gpio_out", "gpio_in", "gpio_oe"],
        "aliases": ["gpio", "port_controller", "io_mux"],
        "description": "General-purpose I/O interface with configurable direction, pull-ups, and interrupt support.",
        "role": "Provides flexible digital I/O for auxiliary control, status monitoring, and application-specific signals.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "i2s_audio_controller": {
        "name": "I2S Audio Controller",
        "domain": "digital",
        "category": "protocol",
        "generator": "i2s_controller",
        "ports": ["clk", "rst_n", "i2s_sclk", "i2s_lrck", "i2s_dout", "i2s_din"],
        "aliases": ["i2s", "pcm_interface", "audio_interface"],
        "description": "I2S/PCM digital audio interface for audio codecs and digital audio processing.",
        "role": "Handles I2S protocol timing and data synchronization for audio streaming.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
}

# New Verification IPs to add
NEW_VERIFICATION_IPS = {
    "i2s_audio_vip": {
        "name": "I2S Audio VIP",
        "protocol": "I2S",
        "checks": ["frame synchronization", "clock gating", "data alignment", "channel separation"],
        "command": "python designs/framework/scripts/run_regression.py --design {design}",
        "description": "Validates I2S protocol timing, frame boundaries, and stereo channel integrity.",
    },
}

# New Digital Subsystems to add
NEW_DIGITAL_SUBSYSTEMS = {
    "sensor_aggregation_plane": {
        "name": "Sensor Aggregation Plane",
        "blocks": ["i2c_controller", "spi_controller", "register_file", "interrupt_controller", "control_logic"],
        "description": "Multi-protocol sensor interface plane for coordinating I2C and SPI peripherals.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
    "clock_distribution_plane": {
        "name": "Clock Distribution Plane",
        "blocks": ["pll", "clock_divider", "control_logic"],
        "description": "Advanced clock generation, distribution, and gating for power-efficient multi-domain designs.",
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
}

# New Chip Profiles to add
NEW_CHIP_PROFILES = {
    "audio_codec_asic": {
        "name": "Audio Codec ASIC",
        "summary": "Digital audio interface chip combining stereo ADC/DAC, I2S, and signal conditioning.",
        "headline": "Integrated audio codec platform with I2S interface and precision analog front-end.",
        "narrative": "This profile assembles a complete audio-in/audio-out codec chip from precision analog infrastructure (references, op-amps, filters, ADC/DAC) and digital I2S interface for consumer and automotive audio applications.",
        "standard": "I2S 3.0, internal audio codec architecture",
        "tags": ["audio", "codec", "i2s", "dac", "adc", "mixed-signal"],
        "blocks": ["bandgap", "precision_voltage_reference", "operational_amplifier", "low_pass_filter", 
                   "dac_r2r_4bit" if "dac_r2r_4bit" in REUSABLE_IP_LIBRARY else "sar_adc_top",
                   "sar_adc_top", "i2s_audio_controller", "spi_controller", "register_file", "control_logic"],
        "vips": ["i2s_audio_vip", "adc_transient_vip", "analog_snapshot_vip", "spi_vip"],
        "digital_subsystems": ["sensor_aggregation_plane"],
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
}


def expand_library():
    """Add new entries to the chip library catalogs."""
    
    # Add new reusable IPs
    print(f"Adding {len(NEW_REUSABLE_IPS)} new Reusable IPs...")
    for key, entry in NEW_REUSABLE_IPS.items():
        REUSABLE_IP_LIBRARY[key] = entry
        print(f"  ✓ {entry['name']}")
    
    # Add new verification IPs
    print(f"\nAdding {len(NEW_VERIFICATION_IPS)} new Verification IPs...")
    for key, entry in NEW_VERIFICATION_IPS.items():
        VERIFICATION_IP_LIBRARY[key] = entry
        print(f"  ✓ {entry['name']}")
    
    # Add new digital subsystems
    print(f"\nAdding {len(NEW_DIGITAL_SUBSYSTEMS)} new Digital Subsystems...")
    for key, entry in NEW_DIGITAL_SUBSYSTEMS.items():
        DIGITAL_SUBSYSTEM_LIBRARY[key] = entry
        print(f"  ✓ {entry['name']}")
    
    # Add new chip profiles
    print(f"\nAdding {len(NEW_CHIP_PROFILES)} new Chip Profiles...")
    for key, entry in NEW_CHIP_PROFILES.items():
        CHIP_PROFILE_LIBRARY[key] = entry
        print(f"  ✓ {entry['name']}")
    
    # Print summary
    print("\n" + "=" * 70)
    print("Library Expansion Summary:")
    print(f"  Reusable IPs:      {len(REUSABLE_IP_LIBRARY):2d} (was 39, +{len(NEW_REUSABLE_IPS)})")
    print(f"  Verification IPs:  {len(VERIFICATION_IP_LIBRARY):2d} (was 17, +{len(NEW_VERIFICATION_IPS)})")
    print(f"  Digital Subsystems: {len(DIGITAL_SUBSYSTEM_LIBRARY):2d} (was 7, +{len(NEW_DIGITAL_SUBSYSTEMS)})")
    print(f"  Chip Profiles:     {len(CHIP_PROFILE_LIBRARY):2d} (was 10, +{len(NEW_CHIP_PROFILES)})")
    print("=" * 70)


if __name__ == "__main__":
    try:
        expand_library()
        print("\n✓ Library expansion completed successfully!")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error expanding library: {e}", file=sys.stderr)
        sys.exit(1)
