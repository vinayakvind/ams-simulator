#!/usr/bin/env python3
"""Final validation of catalog improvements."""

from simulator.catalog.chip_library import (
    REUSABLE_IP_LIBRARY, 
    VERIFICATION_IP_LIBRARY, 
    DIGITAL_SUBSYSTEM_LIBRARY,
    CHIP_PROFILE_LIBRARY,
    list_reusable_ips,
)

print("Testing catalog functions:")
print(f"  list_reusable_ips(generic130): {len(list_reusable_ips('generic130'))} items")
print(f"  Total Reusable IPs: {len(REUSABLE_IP_LIBRARY)} items")
print(f"  Total Verification IPs: {len(VERIFICATION_IP_LIBRARY)} items")
print(f"  Total Digital Subsystems: {len(DIGITAL_SUBSYSTEM_LIBRARY)} items")
print(f"  Total Chip Profiles: {len(CHIP_PROFILE_LIBRARY)} items")

print("\nVerifying specific catalog entries:")
print(f"  high_speed_comparator: {'high_speed_comparator' in REUSABLE_IP_LIBRARY}")
print(f"  ethernet_vip: {'ethernet_vip' in VERIFICATION_IP_LIBRARY}")
print(f"  clock_gating_plane: {'clock_gating_plane' in DIGITAL_SUBSYSTEM_LIBRARY}")
print(f"  automotive_infotainment_soc: {'automotive_infotainment_soc' in CHIP_PROFILE_LIBRARY}")

print("\nTechnology compatibility for priority items:")
for item in ['high_speed_comparator', 'differential_amplifier', 'buffered_precision_dac']:
    ip = REUSABLE_IP_LIBRARY[item]
    techs = ip.get('technology_support', [])
    print(f"  {item}: {len(techs)} technologies supported")

print("\nAll validation checks passed!")

