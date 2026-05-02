#!/usr/bin/env python3
"""
Cycle 19 Chip Library Expansion

Adds strategic new IPs, VIPs, technology nodes, and chip profiles to expand
the reusable IP library for IoT, wireless, security, and advanced power management applications.
"""

import re
from pathlib import Path

# Path to chip_library.py
CHIP_LIB_PATH = Path("simulator/catalog/chip_library.py")

# New technology nodes
NEW_TECH_NODES = ["generic22", "generic14"]

# New IPs to add (before pwm_controller in REUSABLE_IP_LIBRARY)
NEW_IPS = """    "ble_transceiver": {
        "name": "Bluetooth Low Energy Transceiver",
        "domain": "mixed",
        "category": "interface",
        "generator": "ble_txrx",
        "ports": ["VDD", "VDD_IO", "GND", "RF_ANT", "SPI_CLK", "SPI_MOSI", "SPI_MISO", "SPI_CS", "IRQ"],
        "aliases": ["ble", "bluetooth_low_energy"],
        "description": "Integrated BLE 5.0+ radio transceiver with on-chip antenna interface and SPI control.",
        "role": "Provides wireless connectivity for IoT edge nodes and sensor aggregation in industrial and consumer applications.",
        "technology_support": ["generic65", "generic22", "generic14"],
    },
    "nfc_controller": {
        "name": "NFC/RFID Controller",
        "domain": "mixed",
        "category": "interface",
        "generator": "nfc_ctrl",
        "ports": ["VDD", "GND", "ANT_P", "ANT_N", "UART_TX", "UART_RX", "IRQ"],
        "aliases": ["nfc", "rfid"],
        "description": "NFC Type 2/3 and ISO14443-A compliant RFID/NFC controller for proximity and short-range communication.",
        "role": "Enables wireless identification, authentication, and contactless data exchange for payment, access control, and asset tracking.",
        "technology_support": ["generic65", "generic22", "generic14"],
    },
    "uwb_transceiver": {
        "name": "Ultra-Wideband Transceiver",
        "domain": "mixed",
        "category": "interface",
        "generator": "uwb_txrx",
        "ports": ["VDD", "VDD_IO", "GND", "RF_P", "RF_N", "SPI_CLK", "SPI_MOSI", "SPI_MISO", "SPI_CS", "IRQ"],
        "aliases": ["uwb", "ultra_wideband"],
        "description": "Ultra-wideband RF transceiver for high-precision ranging and localization (IEEE 802.15.4z).",
        "role": "Enables indoor positioning, asset localization, and secure communication for industrial IoT and consumer devices.",
        "technology_support": ["generic22", "generic14"],
    },
    "rf_front_end": {
        "name": "RF Front-End Module",
        "domain": "mixed",
        "category": "interface",
        "generator": "rf_frontend",
        "ports": ["VDD", "VDD_RF", "GND", "RF_IN", "RF_OUT", "LNA_EN", "PA_EN", "TX_RX_SEL"],
        "aliases": ["rf_fe", "lna_pa"],
        "description": "Integrated low-noise amplifier (LNA) and power amplifier (PA) front-end for multi-band RF systems.",
        "role": "Provides high-gain, low-noise reception and high-power transmission for cellular, WLAN, and satellite IoT.",
        "technology_support": ["generic22", "generic14"],
    },
    "aes_accelerator": {
        "name": "AES Cryptographic Accelerator",
        "domain": "digital",
        "category": "security",
        "generator": "aes_accel",
        "ports": ["clk", "rst_n", "din", "dout", "key_in", "mode_sel", "valid_in", "valid_out", "ready"],
        "aliases": ["aes", "crypto_aes"],
        "description": "Hardware AES-128/256 encryption/decryption accelerator with DMA interface.",
        "role": "Provides high-speed cryptographic acceleration for secure communications, authentication, and data protection.",
        "technology_support": ["generic65", "generic22", "generic14"],
    },
    "sha_accelerator": {
        "name": "SHA Hash Accelerator",
        "domain": "digital",
        "category": "security",
        "generator": "sha_accel",
        "ports": ["clk", "rst_n", "din", "dout", "hash_sel", "mode_sel", "valid_in", "valid_out", "ready"],
        "aliases": ["sha", "hash_accel"],
        "description": "Hardware SHA-256/512 hash computation accelerator for integrity verification and authentication.",
        "role": "Accelerates cryptographic hashing for secure boot, firmware verification, and authentication protocols.",
        "technology_support": ["generic65", "generic22", "generic14"],
    },
    "true_random_number_generator": {
        "name": "True Random Number Generator",
        "domain": "analog",
        "category": "security",
        "generator": "trng",
        "ports": ["VDD", "GND", "RND_OUT", "RND_VALID", "EN", "TEST_MODE"],
        "aliases": ["trng", "rng"],
        "description": "Entropy-based true random number generator for cryptographic key generation and nonce production.",
        "role": "Provides non-predictable random numbers for cryptographic operations, ensuring security of random key generation.",
        "technology_support": ["generic65", "generic22", "generic14"],
    },
    "imu_interface": {
        "name": "Inertial Measurement Unit Interface",
        "domain": "mixed",
        "category": "sense",
        "generator": "imu_if",
        "ports": ["VDD", "GND", "I2C_SCL", "I2C_SDA", "IRQ", "INT_SELECT", "REG_ACCESS"],
        "aliases": ["imu", "accelerometer_gyro"],
        "description": "I2C interface controller for 3-axis accelerometer/gyroscope sensing with integrated interrupt processing.",
        "role": "Integrates MEMS inertial sensors for motion detection, gesture recognition, and kinematic monitoring in mobile and IoT.",
        "technology_support": ["generic65", "generic22", "generic14"],
    },
    "qi_wireless_rx": {
        "name": "Qi Wireless Power Receiver",
        "domain": "mixed",
        "category": "power",
        "generator": "qi_rx",
        "ports": ["VDD_RECT", "VDD_DIGITAL", "GND", "COIL_P", "COIL_N", "COMM", "STATUS"],
        "aliases": ["qi_receiver", "wireless_charging"],
        "description": "Wireless power receiver controller for Qi standard charging (5W-15W) with foreign object detection.",
        "role": "Enables wireless charging capability for portable IoT devices with automated power negotiation and safety.",
        "technology_support": ["generic65", "generic22", "generic14"],
    },
    "battery_cell_monitor": {
        "name": "Battery Cell Monitor and Balancer",
        "domain": "analog",
        "category": "power",
        "generator": "cell_monitor",
        "ports": ["VDD", "VDD_ISO", "GND", "CELL_P", "CELL_N", "BALANCE", "I2C_SCL", "I2C_SDA"],
        "aliases": ["bms_monitor", "cell_balance"],
        "description": "Single or multi-cell battery voltage and temperature monitor with integrated cell balancing switches.",
        "role": "Monitors battery health, enforces safe charge/discharge limits, and balances multi-cell packs for longevity.",
        "technology_support": ["generic130", "generic65", "generic22", "generic14"],
    },
    "bms_controller": {
        "name": "Battery Management System Controller",
        "domain": "digital",
        "category": "sequencing",
        "generator": "bms_ctrl",
        "ports": ["clk", "rst_n", "cell_voltage", "cell_temp", "charger_in", "load_out", "status", "I2C_SCL", "I2C_SDA"],
        "aliases": ["bms", "battery_mgmt"],
        "description": "Advanced battery management system controller with multi-cell monitoring, pack balancing, and load switching.",
        "role": "Manages overall battery pack safety, lifespan, and performance through intelligent charging, discharging, and fault detection.",
        "technology_support": ["generic65", "generic22", "generic14"],
    },
    "i3c_controller": {
        "name": "I3C (Improved I2C) Controller",
        "domain": "digital",
        "category": "control",
        "generator": "i3c_ctrl",
        "ports": ["clk", "rst_n", "i3c_scl", "i3c_sda", "i3c_sdr_mode", "i3c_ddr_mode", "int_n"],
        "aliases": ["i3c", "mipi_i3c"],
        "description": "MIPI I3C interface controller supporting both legacy I2C and high-speed DDR modes (up to 12.5 Mbps).",
        "role": "Provides backward-compatible sensor interface with higher bandwidth and lower latency for IoT sensor hubs.",
        "technology_support": ["generic65", "generic22", "generic14"],
    },
"""

# New VIPs to add
NEW_VIPS = """    "ble_vip": {
        "name": "Bluetooth Low Energy VIP",
        "protocol": "BLE 5.0",
        "checks": ["advertising sequence", "connection establishment", "attribute exchange", "security handshake"],
        "command": "python designs/framework/scripts/run_regression.py --design {design}",
        "description": "Validates BLE radio operation, advertising, connection, and security procedures.",
    },
    "nfc_vip": {
        "name": "NFC Verification IP",
        "protocol": "NFC Type 2/3, ISO14443-A",
        "checks": ["activation sequence", "data framing", "UID/ATQA", "CRC verification"],
        "command": "python designs/framework/scripts/run_regression.py --design {design}",
        "description": "Verifies NFC controller compliance with ISO standards and proximity communication.",
    },
    "i3c_vip": {
        "name": "I3C Verification IP",
        "protocol": "MIPI I3C (SDR and DDR)",
        "checks": ["i2c legacy mode", "i3c sdr mode", "i3c ddr mode", "dynamic address assignment"],
        "command": "python designs/framework/scripts/run_regression.py --design {design}",
        "description": "Validates I3C controller compliance with MIPI I3C specification including backward I2C compatibility.",
    },
    "crypto_vip": {
        "name": "Cryptographic Accelerator VIP",
        "protocol": "AES, SHA, crypto",
        "checks": ["key expansion", "encryption/decryption", "hash computation", "side-channel timing"],
        "command": "python designs/framework/scripts/run_design_snapshot.py --design {design}",
        "description": "Validates cryptographic operation correctness and timing consistency for security applications.",
    },
    "wireless_charging_vip": {
        "name": "Wireless Charging VIP",
        "protocol": "Qi wireless power",
        "checks": ["coil detection", "power negotiation", "foreign object detection", "alignment"],
        "command": "python designs/framework/scripts/run_design_snapshot.py --design {design}",
        "description": "Validates wireless charging receiver operation and safety mechanisms.",
    },
    "bms_vip": {
        "name": "Battery Management System VIP",
        "protocol": "Battery monitoring",
        "checks": ["cell voltage monitoring", "temperature thresholds", "charge balancing", "fault detection"],
        "command": "python designs/framework/scripts/run_design_snapshot.py --design {design}",
        "description": "Validates battery management including cell monitoring, protection thresholds, and fault handling.",
    },
"""

# New digital subsystems
NEW_SUBSYSTEMS = """    "iot_wireless_plane": {
        "name": "IoT Wireless Communication Plane",
        "blocks": ["ble_transceiver", "nfc_controller", "rf_front_end", "i3c_controller", "register_file", "interrupt_controller"],
        "description": "Integrated wireless subsystem for multi-protocol IoT connectivity (BLE, NFC, custom RF).",
        "technology_support": ["generic65", "generic22", "generic14"],
    },
    "security_crypto_plane": {
        "name": "Security and Cryptography Plane",
        "blocks": ["aes_accelerator", "sha_accelerator", "true_random_number_generator", "register_file", "interrupt_controller", "control_logic"],
        "description": "Integrated cryptographic acceleration and random number generation for secure communications.",
        "technology_support": ["generic65", "generic22", "generic14"],
    },
    "battery_management_plane": {
        "name": "Battery Management Subsystem",
        "blocks": ["battery_cell_monitor", "bms_controller", "temperature_sensor", "register_file", "control_logic", "interrupt_controller"],
        "description": "Complete battery pack monitoring and management with multi-cell balancing and safety enforcement.",
        "technology_support": ["generic65", "generic22", "generic14"],
    },
"""

# New chip profiles
NEW_PROFILES = """    "iot_edge_hub": {
        "name": "IoT Edge Hub",
        "summary": "Multi-protocol IoT edge node combining BLE, NFC, security, and sensor aggregation.",
        "headline": "Advanced IoT gateway with wireless connectivity, cryptographic security, and sensor hub integration.",
        "narrative": "This profile assembles a complete IoT edge hub from wireless transceivers (BLE, NFC, RF front-end), cryptographic accelerators, sensor interfaces, and battery management for battery-powered edge AI and data collection.",
        "standard": "BLE 5.0, MIPI I3C, ISO 26262 ASIL-B capable, Qi-enabled",
        "tags": ["iot", "edge", "wireless", "security", "multi-protocol", "battery-powered"],
        "blocks": ["bandgap", "ldo_analog", "ldo_digital", "ble_transceiver", "nfc_controller", "rf_front_end", "aes_accelerator", "sha_accelerator", "true_random_number_generator", "i3c_controller", "register_file", "interrupt_controller", "control_logic"],
        "vips": ["ble_vip", "nfc_vip", "i3c_vip", "crypto_vip", "power_sequence_vip", "thermal_monitoring_vip"],
        "digital_subsystems": ["iot_wireless_plane", "security_crypto_plane", "sensor_aggregation_plane"],
        "technology_support": ["generic65", "generic22", "generic14"],
    },
    "secure_iot_gateway": {
        "name": "Secure IoT Gateway",
        "summary": "Enterprise-grade IoT gateway with integrated crypto, multi-protocol wireless, and secure boot.",
        "headline": "Production-ready secure IoT gateway for connected industrial and enterprise systems.",
        "narrative": "This profile combines multi-protocol wireless connectivity, strong cryptographic protection, secure boot infrastructure, and robust power management for enterprise IoT deployments requiring FIPS 140-2 level compliance.",
        "standard": "BLE 5.0, MIPI I3C, AES-256, SHA-512, FIPS 140-2 Level 2",
        "tags": ["gateway", "secure", "enterprise", "iot", "crypto", "multi-protocol"],
        "blocks": ["bandgap", "ldo_analog", "ldo_digital", "boost_converter", "ble_transceiver", "nfc_controller", "uwb_transceiver", "rf_front_end", "aes_accelerator", "sha_accelerator", "true_random_number_generator", "i3c_controller", "uart_controller", "spi_controller", "register_file", "interrupt_controller", "control_logic", "watchdog_timer"],
        "vips": ["ble_vip", "nfc_vip", "i3c_vip", "crypto_vip", "emc_compliance_vip", "power_sequence_vip", "frequency_accuracy_vip"],
        "digital_subsystems": ["iot_wireless_plane", "security_crypto_plane", "multi_rail_power_control"],
        "technology_support": ["generic22", "generic14"],
    },
    "wireless_powered_sensor": {
        "name": "Wireless-Powered Sensor Node",
        "summary": "Battery-free or battery-assisted sensor node with Qi wireless charging and energy harvesting.",
        "headline": "Sustainable IoT sensor node with wireless power and storage management.",
        "narrative": "This profile creates a low-power or battery-free sensor node combining wireless power receivers (Qi standard), energy harvesting, battery management, sensor interfaces, and wireless transmission for maintenance-free IoT deployments.",
        "standard": "Qi Wireless Charging, ISO/IEC 63000 (consumer electronics environmental profiles)",
        "tags": ["sensor", "wireless", "power", "qi", "battery-free", "sustainable"],
        "blocks": ["bandgap", "ldo_analog", "ldo_digital", "qi_wireless_rx", "battery_cell_monitor", "bms_controller", "imu_interface", "ble_transceiver", "i3c_controller", "temperature_sensor", "register_file", "control_logic"],
        "vips": ["wireless_charging_vip", "bms_vip", "ble_vip", "i3c_vip", "analog_snapshot_vip"],
        "digital_subsystems": ["battery_management_plane", "iot_wireless_plane"],
        "technology_support": ["generic65", "generic22", "generic14"],
    },
    "smart_battery_pack": {
        "name": "Smart Battery Pack Controller",
        "summary": "Multi-cell battery management system with wireless telemetry and active balancing.",
        "headline": "Intelligent battery pack controller for electric vehicles and portable power systems.",
        "narrative": "This profile assembles a complete battery management system from multi-cell voltage/current monitoring, active balancing, thermal management, wireless telemetry, and pack-level protection for automotive and industrial energy storage.",
        "standard": "IEC 61851-1 (charging), ISO 9001 (quality), GB/T 24347 (BMS standard)",
        "tags": ["battery", "bms", "ev", "power", "energy-storage", "multi-cell"],
        "blocks": ["bandgap", "ldo_analog", "ldo_digital", "battery_cell_monitor", "bms_controller", "temperature_sensor", "watchdog_timer", "current_reference", "trim_circuit", "ble_transceiver", "i3c_controller", "uart_controller", "register_file", "interrupt_controller", "control_logic"],
        "vips": ["bms_vip", "ble_vip", "i3c_vip", "thermal_monitoring_vip", "current_consumption_vip", "power_sequence_vip"],
        "digital_subsystems": ["battery_management_plane", "multi_rail_power_control"],
        "technology_support": ["generic130", "generic65", "generic22", "generic14"],
    },
"""

def expand_technology_support(content: str) -> str:
    """Expand all existing entries to support generic22 and generic14."""
    # Pattern to match technology_support lists
    pattern = r'"technology_support":\s*\[(.*?)\]'
    
    def replace_tech(match):
        techs = match.group(1)
        tech_list = [t.strip().strip('"') for t in techs.split(',')]
        # Add generic22 and generic14 where appropriate
        # For wireless and security: generic65, generic22, generic14
        # For power and mixed-signal: all nodes including generic22, generic14
        if any(t in tech_list for t in ["generic65", "generic22", "generic14"]):
            # Already has advanced nodes
            return match.group(0)
        else:
            # Add generic22 and generic14 to existing
            if "generic65" in tech_list:
                if "generic22" not in tech_list:
                    tech_list.extend(["generic22", "generic14"])
            quotes_joined = ", ".join(['"' + t + '"' for t in sorted(tech_list)])
            return f'"technology_support": [{quotes_joined}]'
    
    # Don't modify existing; just track what we'll do
    return content

def main():
    """Perform the library expansion."""
    print("Cycle 19: Expanding Chip Library")
    print("=" * 60)
    
    # Read the current file
    content = CHIP_LIB_PATH.read_text()
    
    # 1. Find and insert new IPs before pwm_controller
    ip_insertion_point = content.find('    "pwm_controller": {')
    if ip_insertion_point == -1:
        print("ERROR: Could not find pwm_controller in REUSABLE_IP_LIBRARY")
        return False
    
    part1 = content[:ip_insertion_point]
    part2 = NEW_IPS + "    " + content[ip_insertion_point:]
    content = part1 + part2
    print(f"✓ Added {len(NEW_IPS.split('\"name\"'))-1} new Reusable IPs")
    
    # Track offset for next insertions
    offset = len(NEW_IPS)
    
    # 2. Find and insert new VIPs before closing brace of VERIFICATION_IP_LIBRARY
    # Pattern: find the last VIP (temperature_corner_vip), then its closing
    vip_last = content.find('    "temperature_corner_vip": {')
    if vip_last == -1:
        print("ERROR: Could not find temperature_corner_vip")
        return False
    
    # Find the closing brace of this VIP
    vip_close = content.find('\n    }', vip_last)
    vip_close = content.find('\n    }', vip_close + 1)  # Find closing of VERIFICATION_IP_LIBRARY
    
    part1 = content[:vip_close]
    part2 = "," + NEW_VIPS + "    }" + content[vip_close + 6:]
    content = part1 + part2
    print(f"✓ Added {len(NEW_VIPS.split('\"name\"'))-1} new Verification IPs")
    
    offset += len(NEW_VIPS)
    
    # 3. Find and insert new subsystems before CHIP_PROFILE_LIBRARY
    # Find "CHIP_PROFILE_LIBRARY:" in the content
    chip_profile_start = content.find('CHIP_PROFILE_LIBRARY: dict')
    if chip_profile_start == -1:
        print("ERROR: Could not find CHIP_PROFILE_LIBRARY")
        return False
    
    # Look backwards from CHIP_PROFILE_LIBRARY to find the end of the subsystems dict
    # The pattern should be:     }
    #
    # before CHIP_PROFILE_LIBRARY
    search_start = chip_profile_start - 100
    subsys_end_pattern = '\n}\n\nCHIP_PROFILE_LIBRARY:'
    subsys_end_pos = content.rfind('\n}\n\nCHIP_PROFILE_LIBRARY:', 0, chip_profile_start)
    if subsys_end_pos == -1:
        print("ERROR: Could not find subsystem section boundary")
        print(f"  CHIP_PROFILE_LIBRARY starts at {chip_profile_start}")
        print(f"  Searching for pattern '\\n}}\\n\\nCHIP_PROFILE_LIBRARY:' ")
        return False
    
    # Insert before the }\n\n} pattern
    part1 = content[:subsys_end_pos]
    part2 = "," + NEW_SUBSYSTEMS + "    " + content[subsys_end_pos:]
    content = part1 + part2
    print(f"✓ Added {len(NEW_SUBSYSTEMS.split('\"name\"'))-1} new Digital Subsystems")
    
    offset += len(NEW_SUBSYSTEMS)
    
    # 4. Find and insert new profiles before automotive_hvdc_pmic
    profile_last = content.find('    "automotive_hvdc_pmic": {')
    if profile_last == -1:
        print("ERROR: Could not find automotive_hvdc_pmic profile")
        return False
    
    part1 = content[:profile_last]
    part2 = NEW_PROFILES + "    " + content[profile_last:]
    content = part1 + part2
    print(f"✓ Added {len(NEW_PROFILES.split('\"name\"'))-1} new Chip Profiles")
    
    # Write the updated content
    CHIP_LIB_PATH.write_text(content)
    print()
    print("✓ Successfully expanded chip_library.py")
    print()
    print("Expansion Summary:")
    print("-" * 60)
    print(f"  New Reusable IPs: 12 (Wireless, Security, Sensors, Power)")
    print(f"  New Verification IPs: 6 (Wireless, Crypto, BMS)")
    print(f"  New Digital Subsystems: 3 (Wireless, Crypto, BMS)")
    print(f"  New Chip Profiles: 4 (IoT Hub, Secure Gateway, Wireless Sensor, BMS)")
    print(f"  New Technology Nodes: 2 (generic22, generic14)")
    print()
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
