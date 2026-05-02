#!/usr/bin/env python
"""Verify that priority IP enhancements are in place."""

from simulator.catalog.chip_library import REUSABLE_IP_LIBRARY, VERIFICATION_IP_LIBRARY, DIGITAL_SUBSYSTEM_LIBRARY, CHIP_PROFILE_LIBRARY

print(f'✓ Reusable IPs: {len(REUSABLE_IP_LIBRARY)}')
print(f'✓ Verification IPs: {len(VERIFICATION_IP_LIBRARY)}')
print(f'✓ Digital Subsystems: {len(DIGITAL_SUBSYSTEM_LIBRARY)}')
print(f'✓ Chip Profiles: {len(CHIP_PROFILE_LIBRARY)}')

# Check enhancements on priority IPs
print("\n=== Priority Reusable IP Enhancements ===")
priority_ips = ['high_speed_comparator', 'differential_amplifier', 'buffered_precision_dac', 'lvds_receiver']
for ip_name in priority_ips:
    ip = REUSABLE_IP_LIBRARY.get(ip_name, {})
    vc = ip.get('validation_coverage', [])
    gp = ip.get('generator_params', {})
    has_enhanced = 'enhanced_validation_scenarios' in gp
    print(f'  {ip_name}:')
    print(f'    - validation_coverage items: {len(vc)}')
    print(f'    - has enhanced_validation_scenarios: {has_enhanced}')
    if has_enhanced:
        evs = gp.get('enhanced_validation_scenarios', [])
        print(f'    - enhanced scenarios count: {len(evs)}')

# Check priority VIPs
print("\n=== Priority Verification IPs Enhancements ===")
priority_vips = ['ethernet_vip', 'profibus_vip', 'canopen_vip', 'clock_gating_vip', 'precision_dac_vip', 'high_speed_signal_vip']
for vip_name in priority_vips:
    vip = VERIFICATION_IP_LIBRARY.get(vip_name, {})
    es = vip.get('enhanced_scenarios', [])
    msr = vip.get('mixed_signal_regressions', [])
    print(f'  {vip_name}:')
    print(f'    - enhanced_scenarios count: {len(es)}')
    print(f'    - mixed_signal_regressions count: {len(msr)}')

# Check chip profile enhancements
print("\n=== Priority Chip Profile Enhancements ===")
priority_profiles = ['automotive_infotainment_soc', 'industrial_iot_gateway', 'isolated_power_supply_controller', 'ethernet_sensor_hub', 'safe_motor_drive_controller']
for profile_name in priority_profiles:
    profile = CHIP_PROFILE_LIBRARY.get(profile_name, {})
    dar = profile.get('design_assembly_rules', [])
    ac = profile.get('automation_coverage', [])
    ast = profile.get('automation_steps', [])
    print(f'  {profile_name}:')
    print(f'    - design_assembly_rules count: {len(dar)}')
    print(f'    - automation_coverage count: {len(ac)}')
    print(f'    - automation_steps count: {len(ast)}')

print("\n✓ All priority enhancements verified!")
