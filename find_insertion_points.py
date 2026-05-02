#!/usr/bin/env python3
"""Direct chip library expansion without complex parsing."""

from pathlib import Path

CHIP_LIB_PATH = Path("simulator/catalog/chip_library.py")

# Read the file
with open(CHIP_LIB_PATH, 'r') as f:
    lines = f.readlines()

# Find key line numbers
pwm_controller_line = None
last_vip_closing = None
last_subsys_closing = None
last_profile_before_hvdc = None
chip_profile_def = None

for i, line in enumerate(lines):
    if '"pwm_controller": {' in line:
        pwm_controller_line = i
    if '"temperature_corner_vip": {' in line:
        temp_corner_line = i
    if '"rs485_interface_plane": {' in line:
        rs485_subsys_line = i
    if 'CHIP_PROFILE_LIBRARY: dict' in line:
        chip_profile_def = i
    if '"automotive_hvdc_pmic": {' in line:
        hvdc_profile_line = i

print(f"Found key lines:")
print(f"  pwm_controller: {pwm_controller_line}")
print(f"  chip_profile_def: {chip_profile_def}")
print(f"  hvdc_profile_line: {hvdc_profile_line}")

# Now find exact insertion points
# 1. For IPs: insert before pwm_controller
if pwm_controller_line:
    ip_insert_line = pwm_controller_line
    print(f"✓ Will insert new IPs at line {ip_insert_line}")

# 2. For VIPs: find the closing brace before DIGITAL_SUBSYSTEM_LIBRARY
vip_insert_line = None
for i in range(chip_profile_def - 1, -1, -1):
    if i + 2 < len(lines) and 'DIGITAL_SUBSYSTEM_LIBRARY' in lines[i+2]:
        # Found it, this is the closing brace
        vip_insert_line = i
        print(f"✓ Will insert new VIPs at line {vip_insert_line}")
        break

# 3. For subsystems: find the closing before CHIP_PROFILE_LIBRARY
subsys_insert_line = None
for i in range(chip_profile_def - 1, -1, -1):
    if i + 1 < len(lines) and 'CHIP_PROFILE_LIBRARY' in lines[i+2]:
        # Found it
        subsys_insert_line = i
        print(f"✓ Will insert new subsystems at line {subsys_insert_line}")
        break

# 4. For profiles: insert before hvdc
if hvdc_profile_line:
    profile_insert_line = hvdc_profile_line
    print(f"✓ Will insert new profiles at line {profile_insert_line}")

print()
print("Insertion strategy:")
print(f"  1. Insert IPs before line {ip_insert_line} (pwm_controller)")
print(f"  2. Insert VIPs before line {vip_insert_line} (last VIP closing)")
if subsys_insert_line:
    print(f"  3. Insert subsystems before line {subsys_insert_line} (subsystem dict closing)")
else:
    print(f"  3. Insert subsystems - SEARCH FAILED")
print(f"  4. Insert profiles before line {profile_insert_line} (automotive_hvdc_pmic)")
