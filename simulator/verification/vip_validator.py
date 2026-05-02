"""VIP and Subsystem Integration Validator.

Validates reusable IPs, VIPs, digital subsystems, and chip profiles
against integration rules and validation scenarios.
"""

from __future__ import annotations

from typing import Any
from dataclasses import dataclass

from simulator.catalog.chip_library import (
    get_reusable_ip,
    get_verification_ip,
    get_digital_subsystem,
    get_chip_profile,
)


@dataclass
class ValidationResult:
    """Result of a validation check."""

    name: str
    category: str
    passed: bool
    message: str
    details: dict[str, Any] | None = None


class VIPValidator:
    """Validates VIP, subsystem, and profile definitions."""

    def __init__(self):
        self.results: list[ValidationResult] = []

    def validate_reusable_ip(self, ip_name: str) -> ValidationResult:
        """Validate a reusable IP definition."""
        try:
            ip_def = get_reusable_ip(ip_name)
            if not ip_def:
                return ValidationResult(
                    name=ip_name,
                    category="Reusable IP",
                    passed=False,
                    message=f"IP '{ip_name}' not found in library",
                )

            # Check required fields
            required_fields = ["name", "domain", "category", "description", "technology_support"]
            missing = [f for f in required_fields if f not in ip_def]
            if missing:
                return ValidationResult(
                    name=ip_name,
                    category="Reusable IP",
                    passed=False,
                    message=f"Missing required fields: {missing}",
                    details={"missing_fields": missing},
                )

            # Validate specs if present
            if "specs" in ip_def:
                specs_detail = f"Found {len(ip_def['specs'])} specification entries"
            else:
                specs_detail = "No specifications defined"

            return ValidationResult(
                name=ip_name,
                category="Reusable IP",
                passed=True,
                message=f"✓ Valid IP definition with {len(ip_def.get('ports', []))} ports",
                details={
                    "domain": ip_def.get("domain"),
                    "category": ip_def.get("category"),
                    "technology_support": ip_def.get("technology_support"),
                    "specs": specs_detail,
                    "ports": len(ip_def.get("ports", [])),
                },
            )

        except Exception as e:
            return ValidationResult(
                name=ip_name,
                category="Reusable IP",
                passed=False,
                message=f"Error during validation: {str(e)}",
            )

    def validate_verification_ip(self, vip_name: str) -> ValidationResult:
        """Validate a Verification IP definition."""
        try:
            vip_def = get_verification_ip(vip_name)
            if not vip_def:
                return ValidationResult(
                    name=vip_name,
                    category="Verification IP",
                    passed=False,
                    message=f"VIP '{vip_name}' not found in library",
                )

            # Check required fields
            required_fields = ["name", "protocol", "checks", "description"]
            missing = [f for f in required_fields if f not in vip_def]
            if missing:
                return ValidationResult(
                    name=vip_name,
                    category="Verification IP",
                    passed=False,
                    message=f"Missing required fields: {missing}",
                    details={"missing_fields": missing},
                )

            # Count validation coverage items
            coverage_count = sum(
                len(vip_def.get(key, []))
                for key in ["checks", "design_scenarios", "enhanced_scenarios", "validation_coverage"]
            )

            return ValidationResult(
                name=vip_name,
                category="Verification IP",
                passed=True,
                message=f"✓ Valid VIP with {coverage_count} validation coverage items",
                details={
                    "protocol": vip_def.get("protocol"),
                    "checks_count": len(vip_def.get("checks", [])),
                    "design_scenarios": len(vip_def.get("design_scenarios", [])),
                    "enhanced_scenarios": len(vip_def.get("enhanced_scenarios", [])),
                    "validation_coverage_count": len(vip_def.get("validation_coverage", [])),
                    "mixed_signal_regressions": len(vip_def.get("mixed_signal_regressions", [])),
                },
            )

        except Exception as e:
            return ValidationResult(
                name=vip_name,
                category="Verification IP",
                passed=False,
                message=f"Error during validation: {str(e)}",
            )

    def validate_digital_subsystem(self, subsys_name: str) -> ValidationResult:
        """Validate a digital subsystem definition."""
        try:
            subsys_def = get_digital_subsystem(subsys_name)
            if not subsys_def:
                return ValidationResult(
                    name=subsys_name,
                    category="Digital Subsystem",
                    passed=False,
                    message=f"Subsystem '{subsys_name}' not found in library",
                )

            # Check required fields
            required_fields = ["name", "blocks", "description", "technology_support"]
            missing = [f for f in required_fields if f not in subsys_def]
            if missing:
                return ValidationResult(
                    name=subsys_name,
                    category="Digital Subsystem",
                    passed=False,
                    message=f"Missing required fields: {missing}",
                    details={"missing_fields": missing},
                )

            # Count integration rules and validation scenarios
            rules_count = len(subsys_def.get("integration_rules", []))
            scenarios_count = len(subsys_def.get("validation_scenarios", []))
            patterns_count = len(subsys_def.get("design_patterns", []))

            return ValidationResult(
                name=subsys_name,
                category="Digital Subsystem",
                passed=True,
                message=f"✓ Valid subsystem with {rules_count} integration rules and {scenarios_count} validation scenarios",
                details={
                    "blocks_count": len(subsys_def.get("blocks", [])),
                    "integration_rules": rules_count,
                    "validation_scenarios": scenarios_count,
                    "design_patterns": patterns_count,
                    "design_assembly_rules": len(subsys_def.get("design_assembly_rules", [])),
                    "technology_support": subsys_def.get("technology_support"),
                },
            )

        except Exception as e:
            return ValidationResult(
                name=subsys_name,
                category="Digital Subsystem",
                passed=False,
                message=f"Error during validation: {str(e)}",
            )

    def validate_chip_profile(self, profile_name: str) -> ValidationResult:
        """Validate a chip profile definition."""
        try:
            profile_def = get_chip_profile(profile_name)
            if not profile_def:
                return ValidationResult(
                    name=profile_name,
                    category="Chip Profile",
                    passed=False,
                    message=f"Profile '{profile_name}' not found in library",
                )

            # Check required fields
            required_fields = ["name", "headline", "blocks", "vips", "digital_subsystems"]
            missing = [f for f in required_fields if f not in profile_def]
            if missing:
                return ValidationResult(
                    name=profile_name,
                    category="Chip Profile",
                    passed=False,
                    message=f"Missing required fields: {missing}",
                    details={"missing_fields": missing},
                )

            # Count design collateral and automation coverage
            collateral_count = len(profile_def.get("design_collateral", []))
            automation_count = len(profile_def.get("automation_coverage", []))
            rules_count = len(profile_def.get("integration_rules", []))

            return ValidationResult(
                name=profile_name,
                category="Chip Profile",
                passed=True,
                message=f"✓ Valid profile with {collateral_count} design artifacts and {automation_count} automation items",
                details={
                    "blocks_count": len(profile_def.get("blocks", [])),
                    "vips_count": len(profile_def.get("vips", [])),
                    "digital_subsystems": len(profile_def.get("digital_subsystems", [])),
                    "integration_rules": rules_count,
                    "design_collateral": collateral_count,
                    "automation_coverage": automation_count,
                    "technology_support": profile_def.get("technology_support"),
                },
            )

        except Exception as e:
            return ValidationResult(
                name=profile_name,
                category="Chip Profile",
                passed=False,
                message=f"Error during validation: {str(e)}",
            )

    def validate_priority_items(self) -> list[ValidationResult]:
        """Validate all priority items from the handshake prompt."""
        # Priority reusable IPs
        reusable_ips = [
            "high_speed_comparator",
            "differential_amplifier",
            "buffered_precision_dac",
            "lvds_receiver",
            "ethernet_phy",
            "profibus_transceiver",
            "canopen_controller",
            "isolated_gate_driver",
        ]

        # Priority VIPs
        vips = [
            "ethernet_vip",
            "profibus_vip",
            "canopen_vip",
            "clock_gating_vip",
            "precision_dac_vip",
            "high_speed_signal_vip",
        ]

        # Priority digital subsystems
        subsystems = [
            "clock_gating_plane",
            "ethernet_control_plane",
            "safety_monitor_plane",
            "infotainment_control_plane",
            "power_conversion_plane",
        ]

        # Priority chip profiles
        profiles = [
            "automotive_infotainment_soc",
            "industrial_iot_gateway",
            "isolated_power_supply_controller",
            "ethernet_sensor_hub",
        ]

        results = []

        print("Validating Priority Reusable IPs...")
        for ip_name in reusable_ips:
            result = self.validate_reusable_ip(ip_name)
            results.append(result)
            print(f"  {ip_name}: {'✓ PASS' if result.passed else '✗ FAIL'}")

        print("\nValidating Priority Verification IPs...")
        for vip_name in vips:
            result = self.validate_verification_ip(vip_name)
            results.append(result)
            print(f"  {vip_name}: {'✓ PASS' if result.passed else '✗ FAIL'}")

        print("\nValidating Priority Digital Subsystems...")
        for subsys_name in subsystems:
            result = self.validate_digital_subsystem(subsys_name)
            results.append(result)
            print(f"  {subsys_name}: {'✓ PASS' if result.passed else '✗ FAIL'}")

        print("\nValidating Priority Chip Profiles...")
        for profile_name in profiles:
            result = self.validate_chip_profile(profile_name)
            results.append(result)
            print(f"  {profile_name}: {'✓ PASS' if result.passed else '✗ FAIL'}")

        self.results = results
        return results

    def summary(self) -> dict[str, Any]:
        """Generate validation summary."""
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)

        by_category = {}
        for result in self.results:
            if result.category not in by_category:
                by_category[result.category] = {"passed": 0, "failed": 0}
            if result.passed:
                by_category[result.category]["passed"] += 1
            else:
                by_category[result.category]["failed"] += 1

        return {
            "total": len(self.results),
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{100*passed/len(self.results):.1f}%" if self.results else "N/A",
            "by_category": by_category,
        }


def main():
    """Run validation of priority items."""
    validator = VIPValidator()
    results = validator.validate_priority_items()

    summary = validator.summary()
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Total: {summary['total']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Pass Rate: {summary['pass_rate']}")
    print("\nBy Category:")
    for category, counts in summary["by_category"].items():
        print(f"  {category}: {counts['passed']} passed, {counts['failed']} failed")

    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    exit(main())
