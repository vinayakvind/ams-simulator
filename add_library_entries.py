#!/usr/bin/env python
"""
Add library expansion entries to chip_library.py.
This reads the file, inserts new entries before the closing braces of each dictionary, and writes it back.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent
CHIP_LIB = REPO_ROOT / "simulator" / "catalog" / "chip_library.py"

# Read the entire file
content = CHIP_LIB.read_text()

# Define new entries to add (as Python code text)
NEW_IP_ENTRIES = '''    "gpio_controller": {
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
'''

NEW_VIP_ENTRIES = '''    "i2s_audio_vip": {
        "name": "I2S Audio VIP",
        "protocol": "I2S",
        "checks": ["frame synchronization", "clock gating", "data alignment", "channel separation"],
        "command": "python designs/framework/scripts/run_regression.py --design {design}",
        "description": "Validates I2S protocol timing, frame boundaries, and stereo channel integrity.",
    },
'''

NEW_SUBSYSTEM_ENTRIES = '''    "sensor_aggregation_plane": {
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
'''

NEW_PROFILE_ENTRIES = '''    "audio_codec_asic": {
        "name": "Audio Codec ASIC",
        "summary": "Digital audio interface chip combining stereo ADC/DAC, I2S, and signal conditioning.",
        "headline": "Integrated audio codec platform with I2S interface and precision analog front-end.",
        "narrative": "This profile assembles a complete audio-in/audio-out codec chip from precision analog infrastructure (references, op-amps, filters, ADC/DAC) and digital I2S interface for consumer and automotive audio applications.",
        "standard": "I2S 3.0, internal audio codec architecture",
        "tags": ["audio", "codec", "i2s", "dac", "adc", "mixed-signal"],
        "blocks": ["bandgap", "precision_voltage_reference", "operational_amplifier", "low_pass_filter", "dac_r2r_4bit", "sar_adc_top", "i2s_audio_controller", "spi_controller", "register_file", "control_logic"],
        "vips": ["i2s_audio_vip", "adc_transient_vip", "analog_snapshot_vip", "spi_vip"],
        "digital_subsystems": ["sensor_aggregation_plane"],
        "technology_support": ["generic180", "generic130", "generic65", "bcd180"],
    },
'''

def add_entries_before_closing_brace(text: str, entries: str, marker: str) -> str:
    """Insert entries before the closing brace of a dictionary."""
    # Find the pattern: last entry (usually ending with ],) followed by }
    # We need to replace: "    }," with the new entries + "    },"
    # This is tricky because we need to add a comma to the last existing entry
    
    # Find the position to insert - just before the final closing brace
    # Strategy: Find the last closing brace for the dictionary, and insert before it
    
    # For REUSABLE_IP_LIBRARY
    if marker == "REUSABLE_IP":
        # Find the line "VERIFICATION_IP_LIBRARY" and work backwards
        vip_pos = text.find("VERIFICATION_IP_LIBRARY:")
        # Find the closing } before that
        section = text[:vip_pos]
        last_brace = section.rfind("}")
        # Insert before that brace
        return text[:last_brace] + entries + "    " + text[last_brace:]
    
    elif marker == "VERIFICATION_IP":
        # Find DIGITAL_SUBSYSTEM_LIBRARY and work backwards
        ds_pos = text.find("DIGITAL_SUBSYSTEM_LIBRARY:")
        section = text[:ds_pos]
        last_brace = section.rfind("}")
        return text[:last_brace] + entries + "    " + text[last_brace:]
    
    elif marker == "DIGITAL_SUBSYSTEM":
        # Find CHIP_PROFILE_LIBRARY and work backwards
        cp_pos = text.find("CHIP_PROFILE_LIBRARY:")
        section = text[:cp_pos]
        last_brace = section.rfind("}")
        return text[:last_brace] + entries + "    " + text[last_brace:]
    
    elif marker == "CHIP_PROFILE":
        # Find the function definitions (def _ordered_unique) and work backwards
        func_pos = text.find("def _ordered_unique")
        section = text[:func_pos]
        last_brace = section.rfind("}")
        return text[:last_brace] + entries + "    " + text[last_brace:]
    
    return text

try:
    print("Expanding chip library with new entries...")
    
    # Add new IPs
    print("  Adding GPIO Controller and I2S Audio Controller IPs...")
    content = add_entries_before_closing_brace(content, NEW_IP_ENTRIES, "REUSABLE_IP")
    
    # Add new VIPs
    print("  Adding I2S Audio VIP...")
    content = add_entries_before_closing_brace(content, NEW_VIP_ENTRIES, "VERIFICATION_IP")
    
    # Add new subsystems
    print("  Adding Sensor Aggregation and Clock Distribution Subsystems...")
    content = add_entries_before_closing_brace(content, NEW_SUBSYSTEM_ENTRIES, "DIGITAL_SUBSYSTEM")
    
    # Add new profiles
    print("  Adding Audio Codec ASIC Profile...")
    content = add_entries_before_closing_brace(content, NEW_PROFILE_ENTRIES, "CHIP_PROFILE")
    
    # Write back
    CHIP_LIB.write_text(content)
    print("\n✓ Library successfully expanded and written to chip_library.py")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
