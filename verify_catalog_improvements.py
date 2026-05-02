#!/usr/bin/env python3
"""Verify catalog improvements are in place."""

from simulator.catalog.chip_library import (
    get_reusable_ip,
    get_digital_subsystem,
    get_chip_profile,
    REUSABLE_IP_LIBRARY,
    VERIFICATION_IP_LIBRARY,
    DIGITAL_SUBSYSTEM_LIBRARY,
    CHIP_PROFILE_LIBRARY,
)

def main():
    print("=" * 70)
    print("CATALOG IMPROVEMENT VERIFICATION")
    print("=" * 70)

    # Verify reusable IP improvements
    print("\n1. REUSABLE IP IMPROVEMENTS")
    print("-" * 70)
    
    ip_targets = ["high_speed_comparator", "differential_amplifier", "buffered_precision_dac", "lvds_receiver"]
    for ip_name in ip_targets:
        ip = get_reusable_ip(ip_name)
        val_cov = len(ip.get("validation_coverage", []))
        gen_params = len(ip.get("generator_params", {}))
        int_examples = len(ip.get("integration_example", {}))
        print(f"  {ip_name}:")
        print(f"    - Validation Coverage: {val_cov} items")
        print(f"    - Generator Params: {gen_params} items")
        print(f"    - Integration Examples: {int_examples} items")

    # Verify VIPs
    print("\n2. VERIFICATION IP (VIP) IMPROVEMENTS")
    print("-" * 70)
    
    vip_targets = ["ethernet_vip", "profibus_vip", "canopen_vip", "clock_gating_vip"]
    for vip_name in vip_targets:
        if vip_name in VERIFICATION_IP_LIBRARY:
            vip = VERIFICATION_IP_LIBRARY[vip_name]
            checks = len(vip.get("checks", []))
            scenarios = len(vip.get("design_scenarios", [])) + len(vip.get("enhanced_scenarios", []))
            print(f"  {vip_name}:")
            print(f"    - Checks: {checks} items")
            print(f"    - Test Scenarios: {scenarios} items")
        else:
            print(f"  {vip_name}: NOT FOUND")

    # Verify digital subsystems
    print("\n3. DIGITAL SUBSYSTEM IMPROVEMENTS")
    print("-" * 70)
    
    ds_targets = ["clock_gating_plane", "ethernet_control_plane", "safety_monitor_plane", "infotainment_control_plane"]
    for ds_name in ds_targets:
        try:
            ds = get_digital_subsystem(ds_name)
            blocks = len(ds.get("blocks", []))
            rules = len(ds.get("integration_rules", []))
            scenarios = len(ds.get("validation_scenarios", []))
            print(f"  {ds_name}:")
            print(f"    - Blocks: {blocks} components")
            print(f"    - Integration Rules: {rules} rules")
            print(f"    - Validation Scenarios: {scenarios} scenarios")
        except Exception as e:
            print(f"  {ds_name}: ERROR - {e}")

    # Verify chip profiles
    print("\n4. CHIP PROFILE IMPROVEMENTS")
    print("-" * 70)
    
    profile_targets = ["automotive_infotainment_soc", "industrial_iot_gateway", "isolated_power_supply_controller", "ethernet_sensor_hub"]
    for profile_name in profile_targets:
        try:
            profile = get_chip_profile(profile_name)
            blocks = len(profile.get("blocks", []))
            vips = len(profile.get("vips", []))
            subsystems = len(profile.get("digital_subsystems", []))
            collateral = len(profile.get("design_collateral", []))
            automation = len(profile.get("automation_coverage", []))
            print(f"  {profile_name}:")
            print(f"    - Blocks: {blocks} components")
            print(f"    - VIPs: {vips} verification IPs")
            print(f"    - Digital Subsystems: {subsystems}")
            print(f"    - Design Collateral: {collateral} items")
            print(f"    - Automation Coverage: {automation} items")
        except Exception as e:
            print(f"  {profile_name}: ERROR - {e}")

    # Summary statistics
    print("\n5. CATALOG STATISTICS")
    print("-" * 70)
    print(f"  Total Reusable IPs: {len(REUSABLE_IP_LIBRARY)}")
    print(f"  Total VIPs: {len(VERIFICATION_IP_LIBRARY)}")
    print(f"  Total Digital Subsystems: {len(DIGITAL_SUBSYSTEM_LIBRARY)}")
    print(f"  Total Chip Profiles: {len(CHIP_PROFILE_LIBRARY)}")

    print("\n" + "=" * 70)
    print("VERIFICATION COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    main()
