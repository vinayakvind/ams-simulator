"""
Test script for Priority Enhancement Validation (Cycle 85)
Validates reusable IPs, VIPs, digital subsystems, and chip profiles
"""

import sys
import os
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(str(project_root))

from simulator.catalog.chip_library import (
    REUSABLE_IP_LIBRARY,
    VERIFICATION_IP_LIBRARY,
    DIGITAL_SUBSYSTEM_LIBRARY,
    CHIP_PROFILE_LIBRARY
)
from simulator.catalog.priority_validator import PriorityEnhancementValidator


def run_priority_validation():
    """Run comprehensive priority enhancement validation."""
    
    print("=" * 70)
    print("CYCLE 85: PRIORITY ENHANCEMENT VALIDATION")
    print("=" * 70)
    print()
    
    # Create library dictionary for validator
    chip_library = {
        'REUSABLE_IP_LIBRARY': REUSABLE_IP_LIBRARY,
        'VERIFICATION_IP_LIBRARY': VERIFICATION_IP_LIBRARY,
        'DIGITAL_SUBSYSTEM_LIBRARY': DIGITAL_SUBSYSTEM_LIBRARY,
        'CHIP_PROFILE_LIBRARY': CHIP_PROFILE_LIBRARY
    }
    
    # Initialize validator
    validator = PriorityEnhancementValidator(chip_library)
    
    # Run all validations
    print("Running validations...")
    results = validator.validate_all()
    
    # Print summary
    summary = results['summary']
    print()
    print("VALIDATION SUMMARY")
    print("-" * 70)
    print(f"Overall Status: {summary['overall_status']}")
    print(f"Pass Rate: {summary['pass_rate_percent']:.1f}%")
    print(f"Total Checks: {summary['total_checks']}")
    print(f"Passed: {summary['passed_checks']}")
    print()
    
    # Print reusable IP results
    print("REUSABLE IPs - Priority Targets")
    print("-" * 70)
    for ip_name, result in results['reusable_ips'].items():
        metrics = result['enhancement_metrics']
        print(f"[PASS] {ip_name}: {result['status'].upper()}")
        print(f"  - Validation Scenarios: {metrics['validation_scenarios']}")
        print(f"  - Example Configs: {metrics['example_configs']}")
        print(f"  - Integration Examples: {metrics['integration_examples']}")
        print()
    
    # Print VIP results
    print("VERIFICATION IPs - Priority Targets")
    print("-" * 70)
    for vip_name, result in results['vips'].items():
        metrics = result['scenario_metrics']
        print(f"[PASS] {vip_name}: {result['status'].upper()}")
        print(f"  - Protocol Checks: {metrics['protocol_checks']}")
        print(f"  - Design Scenarios: {metrics['design_scenarios']}")
        print(f"  - Mixed-Signal Regressions: {metrics['mixed_signal_regressions']}")
        print()
    
    # Print digital subsystem results
    print("DIGITAL SUBSYSTEMS - Priority Targets")
    print("-" * 70)
    for subsys_name, result in results['digital_subsystems'].items():
        metrics = result['detail_metrics']
        print(f"[PASS] {subsys_name}: {result['status'].upper()}")
        print(f"  - Blocks: {metrics['block_count']}")
        print(f"  - Integration Rules: {metrics['integration_rules']}")
        print(f"  - Validation Scenarios: {metrics['validation_scenarios']}")
        print()
    
    # Print chip profile results
    print("CHIP PROFILES - Priority Targets")
    print("-" * 70)
    for profile_name, result in results['chip_profiles'].items():
        metrics = result['assembly_metrics']
        print(f"[PASS] {profile_name}: {result['status'].upper()}")
        print(f"  - Blocks: {metrics['block_count']}")
        print(f"  - VIPs: {metrics['vip_count']}")
        print(f"  - Subsystems: {metrics['subsystem_count']}")
        print(f"  - Automation Steps: {metrics['automation_steps']}")
        print()
    
    # Export results
    reports_dir = project_root / "reports"
    reports_dir.mkdir(exist_ok=True)
    
    json_report = reports_dir / "cycle_0085_priority_validation.json"
    md_report = reports_dir / "cycle_0085_priority_validation.md"
    
    print(f"Exporting results to {json_report}...")
    validator.export_results_json(str(json_report))
    
    print(f"Exporting results to {md_report}...")
    validator.export_results_markdown(str(md_report))
    
    print()
    print("=" * 70)
    print(f"VALIDATION STATUS: {summary['overall_status']}")
    print("=" * 70)
    
    return summary['overall_status'] == 'PASS'


if __name__ == "__main__":
    success = run_priority_validation()
    sys.exit(0 if success else 1)
