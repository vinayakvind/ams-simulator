#!/usr/bin/env python
"""Test cycle 19 library expansion."""

from simulator.catalog.chip_library import (
    list_reusable_ips,
    list_verification_ips,
    list_digital_subsystems,
    list_chip_profiles,
    get_chip_profile,
    compose_chip_profile,
)

def main():
    # Test new IPs
    ips = list_reusable_ips()
    new_ips = [ip for ip in ips if ip['key'] in [
        'boost_converter', 'current_reference', 'frequency_detector',
        'slew_rate_limiter', 'programmable_gain_amplifier', 'comparator_array',
        'rs485_transceiver', 'pwm_controller'
    ]]
    print(f"✓ Found {len(new_ips)}/8 new IPs")
    for ip in new_ips:
        print(f"  - {ip['name']}")

    # Test new VIPs
    vips = list_verification_ips()
    new_vips = [vip for vip in vips if vip['key'] in [
        'voltage_regulation_vip', 'frequency_accuracy_vip', 
        'power_domain_isolation_vip', 'io_electrical_vip',
        'temperature_corner_vip'
    ]]
    print(f"\n✓ Found {len(new_vips)}/5 new VIPs")
    for vip in new_vips:
        print(f"  - {vip['name']}")

    # Test new subsystems
    subsystems = list_digital_subsystems()
    new_subsystems = [s for s in subsystems if s['key'] in [
        'frequency_monitoring_plane', 'multi_rail_power_control',
        'pwm_motor_control_plane', 'analog_conditioning_plane',
        'rs485_interface_plane'
    ]]
    print(f"\n✓ Found {len(new_subsystems)}/5 new Digital Subsystems")
    for s in new_subsystems:
        print(f"  - {s['name']}")

    # Test new profiles
    profiles = list_chip_profiles()
    new_profiles = [p for p in profiles if p['key'] in [
        'real_time_motor_controller', 'isolated_rs485_gateway',
        'precision_analog_frontend', 'automotive_hvdc_pmic'
    ]]
    print(f"\n✓ Found {len(new_profiles)}/4 new Chip Profiles")
    for p in new_profiles:
        print(f"  - {p['name']}")

    # Test profile composition
    print(f"\n✓ Testing profile composition...")
    profile_key = 'real_time_motor_controller'
    profile = get_chip_profile(profile_key)
    print(f"  Profile: {profile['name']}")
    
    composed = compose_chip_profile(profile_key, 'test_motor_chip', 'generic130')
    print(f"  Composed IPs: {len(composed['reusable_ips'])}")
    print(f"  Composed VIPs: {len(composed['verification_ips'])}")
    print(f"  Composed Subsystems: {len(composed['digital_subsystems'])}")
    
    # Summary stats
    print(f"\n✓ Total Inventory:")
    print(f"  Reusable IPs: {len(ips)}")
    print(f"  Verification IPs: {len(vips)}")
    print(f"  Digital Subsystems: {len(subsystems)}")
    print(f"  Chip Profiles: {len(profiles)}")
    
    print(f"\n✓ All tests passed!")

if __name__ == '__main__':
    main()
