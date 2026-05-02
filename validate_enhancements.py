#!/usr/bin/env python3
"""Validate chip library enhancements for cycle 89."""
import json

from simulator.catalog.chip_library import (
    REUSABLE_IP_LIBRARY,
    VERIFICATION_IP_LIBRARY,
    DIGITAL_SUBSYSTEM_LIBRARY,
    CHIP_PROFILE_LIBRARY,
)

# Check priority backlog items
priority_items = {
    "reusable_ips": [
        "high_speed_comparator",
        "differential_amplifier",
        "buffered_precision_dac",
        "lvds_receiver",
    ],
    "vips": [
        "ethernet_vip",
        "profibus_vip",
        "canopen_vip",
        "clock_gating_vip",
    ],
    "subsystems": [
        "clock_gating_plane",
        "ethernet_control_plane",
        "safety_monitor_plane",
    ],
    "profiles": [
        "automotive_infotainment_soc",
        "industrial_iot_gateway",
        "isolated_power_supply_controller",
    ],
}

print("=" * 70)
print("CHIP CATALOG VALIDATION - CYCLE 89")
print("=" * 70)

print("\n1. REUSABLE IP LIBRARY")
print(f"   Total IPs: {len(REUSABLE_IP_LIBRARY)}")
for ip in priority_items["reusable_ips"]:
    if ip in REUSABLE_IP_LIBRARY:
        ip_data = REUSABLE_IP_LIBRARY[ip]
        has_enhanced = (
            "process_corner_generators" in ip_data.get("generator_params", {})
            or "circuit_variants_extended" in ip_data.get("generator_params", {})
            or len(ip_data.get("validation_coverage", [])) > 5
        )
        status = "✓ ENHANCED" if has_enhanced else "⚠ BASIC"
        print(f"   - {ip}: {status}")
    else:
        print(f"   - {ip}: ✗ MISSING")

print("\n2. VERIFICATION IP LIBRARY")
print(f"   Total VIPs: {len(VERIFICATION_IP_LIBRARY)}")
for vip in priority_items["vips"]:
    if vip in VERIFICATION_IP_LIBRARY:
        vip_data = VERIFICATION_IP_LIBRARY[vip]
        has_mixed_signal = "mixed_signal_regressions" in vip_data
        status = "✓ WITH MIXED-SIGNAL" if has_mixed_signal else "⚠ BASIC"
        print(f"   - {vip}: {status}")
    else:
        print(f"   - {vip}: ✗ MISSING")

print("\n3. DIGITAL SUBSYSTEM LIBRARY")
print(f"   Total Subsystems: {len(DIGITAL_SUBSYSTEM_LIBRARY)}")
for subsys in priority_items["subsystems"]:
    if subsys in DIGITAL_SUBSYSTEM_LIBRARY:
        subsys_data = DIGITAL_SUBSYSTEM_LIBRARY[subsys]
        has_rules = "integration_rules" in subsys_data
        status = "✓ WITH RULES" if has_rules else "⚠ BASIC"
        print(f"   - {subsys}: {status}")
    else:
        print(f"   - {subsys}: ✗ MISSING")

print("\n4. CHIP PROFILE LIBRARY")
print(f"   Total Profiles: {len(CHIP_PROFILE_LIBRARY)}")
for profile in priority_items["profiles"]:
    if profile in CHIP_PROFILE_LIBRARY:
        profile_data = CHIP_PROFILE_LIBRARY[profile]
        has_collateral = "design_collateral" in profile_data
        has_automation = "automation_coverage" in profile_data
        status = "✓ COMPLETE" if (has_collateral and has_automation) else "⚠ PARTIAL"
        print(f"   - {profile}: {status}")
    else:
        print(f"   - {profile}: ✗ MISSING")

print("\n" + "=" * 70)
print("VALIDATION COMPLETE")
print("=" * 70)
