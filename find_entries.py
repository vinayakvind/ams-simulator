#!/usr/bin/env python3
import re

with open('simulator/catalog/chip_library.py', 'r') as f:
    content = f.read()
    lines = content.split('\n')

# Find all REUSABLE_IP entries
ip_pattern = r'^    "(\w+)": \{'
target_ips = ['high_speed_comparator', 'differential_amplifier', 'buffered_precision_dac', 'lvds_receiver']
target_vips = ['ethernet_vip', 'profibus_vip', 'canopen_vip', 'clock_gating_vip']
target_subsystems = ['clock_gating_plane', 'ethernet_control_plane', 'safety_monitor_plane']
target_profiles = ['automotive_infotainment_soc', 'industrial_iot_gateway', 'isolated_power_supply_controller']

print("Searching for REUSABLE IPs...")
for i, line in enumerate(lines, start=1):
    match = re.match(ip_pattern, line)
    if match:
        ip_name = match.group(1)
        if ip_name in target_ips:
            print(f"Line {i}: {ip_name}")

print("\nSearching for VIPs...")
for i, line in enumerate(lines, start=1):
    for vip in target_vips:
        if f'"{vip}":' in line:
            print(f"Line {i}: {vip}")
            
print("\nSearching for Digital Subsystems...")
for i, line in enumerate(lines, start=1):
    for subsys in target_subsystems:
        if f'"{subsys}":' in line:
            print(f"Line {i}: {subsys}")

print("\nSearching for Chip Profiles...")
for i, line in enumerate(lines, start=1):
    for profile in target_profiles:
        if f'"{profile}":' in line:
            print(f"Line {i}: {profile}")
