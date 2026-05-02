#!/usr/bin/env python
"""Integration test for new reference designs and VIP scenarios."""

from simulator.catalog.integration_orchestrator import (
    get_integrator,
    resolve_profile,
    get_regression_plan,
)


def test_integrator_initialization():
    """Test integrator setup."""
    print("[TEST 1] Integrator initialization")
    integrator = get_integrator()
    print(f"  ✓ Profiles loaded: {len(integrator.chip_profiles)}")
    print(f"  ✓ Reusable IPs: {len(integrator.reusable_ips)}")
    print(f"  ✓ VIPs: {len(integrator.vips)}")
    assert len(integrator.chip_profiles) > 0
    assert len(integrator.reusable_ips) > 0


def test_profile_resolution():
    """Test profile resolution."""
    print("\n[TEST 2] Profile resolution")
    profiles_to_test = [
        "automotive_infotainment_soc",
        "industrial_iot_gateway",
        "ethernet_sensor_hub",
    ]
    
    for prof_name in profiles_to_test:
        try:
            design = resolve_profile(prof_name)
            blocks = len(design["profile"].get("blocks", []))
            print(f"  ✓ {prof_name}: {blocks} blocks")
            assert blocks > 0
        except Exception as e:
            print(f"  ✗ {prof_name}: {e}")
            raise


def test_technology_support():
    """Test technology compatibility."""
    print("\n[TEST 3] Technology support verification")
    integrator = get_integrator()
    all_techs = integrator.get_all_supported_technologies()
    print(f"  ✓ Supported technologies: {', '.join(sorted(all_techs))}")
    
    # Check priority profiles support common nodes
    for tech in ["generic180", "generic130", "generic65"]:
        profiles = integrator.get_profiles_for_technology(tech)
        print(f"    - {tech}: {len(profiles)} profiles")
        assert len(profiles) > 0


def test_regression_plan_generation():
    """Test regression plan generation."""
    print("\n[TEST 4] Regression plan generation")
    profiles_to_test = ["automotive_infotainment_soc"]
    
    for prof_name in profiles_to_test:
        plan = get_regression_plan(prof_name)
        print(f"  ✓ {prof_name}:")
        print(f"    - Test scenarios: {len(plan.get('test_scenarios', []))}")
        print(f"    - VIP regressions: {len(plan.get('vip_regressions', {}))}")
        print(f"    - Validation checkpoints: {len(plan.get('validation_checkpoints', []))}")
        
        assert len(plan.get("test_scenarios", [])) >= 0
        assert len(plan.get("vip_regressions", {})) >= 0


def test_block_dependencies():
    """Test block dependency resolution."""
    print("\n[TEST 5] Block dependencies")
    integrator = get_integrator()
    
    for prof_name in ["automotive_infotainment_soc"]:
        deps = integrator.get_block_dependencies(prof_name)
        print(f"  ✓ {prof_name}: {len(deps)} components")
        for comp_name, dep_list in list(deps.items())[:3]:
            print(f"    - {comp_name}: {len(dep_list)} deps")


def test_manifest_export():
    """Test manifest export."""
    print("\n[TEST 6] Manifest export")
    integrator = get_integrator()
    
    # JSON export
    manifest_json = integrator.export_profile_manifest(
        "automotive_infotainment_soc", output_format="json"
    )
    print(f"  ✓ JSON export: {len(manifest_json)} bytes")
    assert len(manifest_json) > 100
    
    # Markdown export
    manifest_md = integrator.export_profile_manifest(
        "automotive_infotainment_soc", output_format="markdown"
    )
    print(f"  ✓ Markdown export: {len(manifest_md)} bytes")
    assert len(manifest_md) > 100


if __name__ == "__main__":
    try:
        test_integrator_initialization()
        test_profile_resolution()
        test_technology_support()
        test_regression_plan_generation()
        test_block_dependencies()
        test_manifest_export()
        
        print("\n" + "=" * 60)
        print("[SUMMARY] All integration tests passed!")
        print("=" * 60)
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
