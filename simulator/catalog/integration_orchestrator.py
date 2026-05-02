"""Integration orchestrator for chip library, profiles, and VIP scenarios.

This module provides the central coordination point for:
- Resolving chip profile specifications from the catalog
- Assembling design collateral from reference designs
- Generating comprehensive regression test plans
- Validating technology support and compatibility
"""

from __future__ import annotations

from typing import Any, Optional
import json

from simulator.catalog.chip_library import (
    REUSABLE_IP_LIBRARY,
    VERIFICATION_IP_LIBRARY,
    DIGITAL_SUBSYSTEM_LIBRARY,
    CHIP_PROFILE_LIBRARY,
)
from simulator.catalog.profile_reference_designs import (
    get_reference_design,
    list_reference_designs,
    ReferenceDesign,
)
from simulator.catalog.vip_regression_scenarios import (
    get_vip_regression_scenario,
    get_scenarios_by_vip,
    list_vip_regression_scenarios,
)


class ChipCatalogIntegrator:
    """Central orchestrator for chip design catalog and integration."""
    
    def __init__(self):
        """Initialize the integrator with library data."""
        self.reusable_ips = REUSABLE_IP_LIBRARY
        self.vips = VERIFICATION_IP_LIBRARY
        self.digital_subsystems = DIGITAL_SUBSYSTEM_LIBRARY
        self.chip_profiles = CHIP_PROFILE_LIBRARY
        self._cache: dict[str, Any] = {}
    
    def get_profile_full_design(self, profile_name: str) -> dict[str, Any]:
        """Get complete design assembly for a chip profile.
        
        Returns profile definition, reference design, and regression test plan.
        """
        # Get profile from catalog
        profile = self.chip_profiles.get(profile_name)
        if not profile:
            raise ValueError(f"Profile not found: {profile_name}")
        
        # Get reference design
        ref_design = get_reference_design(profile_name)
        if not ref_design:
            ref_design = None  # May not have one for all profiles
        
        # Collect regression scenarios for VIPs
        vip_scenarios = {}
        for vip_name in profile.get("vips", []):
            scenarios = get_scenarios_by_vip(vip_name)
            if scenarios:
                vip_scenarios[vip_name] = [s.name for s in scenarios]
        
        return {
            "profile": profile,
            "reference_design": ref_design,
            "vip_regression_scenarios": vip_scenarios,
            "assembly_rules": ref_design.integration_rules if ref_design else [],
            "design_patterns": ref_design.design_patterns if ref_design else [],
            "power_domains": ref_design.power_domains if ref_design else {},
        }
    
    def validate_technology_support(self, profile_name: str, technology: str) -> bool:
        """Check if a profile supports a specific technology node."""
        profile = self.chip_profiles.get(profile_name)
        if not profile:
            return False
        
        return technology in profile.get("technology_support", [])
    
    def get_all_supported_technologies(self) -> set[str]:
        """Get union of all supported technology nodes across all profiles."""
        techs = set()
        for profile in self.chip_profiles.values():
            techs.update(profile.get("technology_support", []))
        return techs
    
    def get_profiles_for_technology(self, technology: str) -> list[str]:
        """Get all profiles that support a specific technology."""
        profiles = []
        for name, profile in self.chip_profiles.items():
            if technology in profile.get("technology_support", []):
                profiles.append(name)
        return sorted(profiles)
    
    def get_block_dependencies(self, profile_name: str) -> dict[str, list[str]]:
        """Get all block dependencies for a profile.
        
        Returns map of block -> list of required blocks.
        """
        profile = self.chip_profiles.get(profile_name)
        if not profile:
            raise ValueError(f"Profile not found: {profile_name}")
        
        dependencies = {}
        
        # Collect from blocks
        for block_name in profile.get("blocks", []):
            block = self.reusable_ips.get(block_name, {})
            dependencies[block_name] = []  # Blocks don't depend on each other typically
        
        # Collect from VIPs
        for vip_name in profile.get("vips", []):
            vip = self.vips.get(vip_name, {})
            dependencies[vip_name] = vip.get("requires", [])
        
        # Collect from digital subsystems
        for subsys_name in profile.get("digital_subsystems", []):
            subsys = self.digital_subsystems.get(subsys_name, {})
            dependencies[subsys_name] = subsys.get("blocks", [])
        
        return dependencies
    
    def get_comprehensive_regression_plan(self, profile_name: str) -> dict[str, Any]:
        """Generate comprehensive regression test plan for a profile."""
        profile = self.chip_profiles.get(profile_name)
        if not profile:
            raise ValueError(f"Profile not found: {profile_name}")
        
        ref_design = get_reference_design(profile_name)
        
        plan = {
            "profile": profile_name,
            "test_scenarios": [],
            "vip_regressions": {},
            "design_patterns": [],
            "validation_checkpoints": [],
        }
        
        # Add reference design test scenarios
        if ref_design:
            plan["test_scenarios"] = [
                {
                    "name": s["name"],
                    "description": s.get("description", ""),
                    "duration_sec": s.get("duration_sec", 60),
                    "validation": s.get("validation", []),
                }
                for s in ref_design.test_scenarios
            ]
            plan["design_patterns"] = ref_design.design_patterns
        
        # Add VIP regression scenarios
        for vip_name in profile.get("vips", []):
            scenarios = get_scenarios_by_vip(vip_name)
            plan["vip_regressions"][vip_name] = [
                {
                    "name": s.name,
                    "description": s.description,
                    "validation": s.validation_rules,
                }
                for s in scenarios
            ]
        
        # Add design validation checkpoints
        plan["validation_checkpoints"] = [
            "Technology compatibility verified",
            "Power domain isolation confirmed",
            "Clock tree timing closed",
            "Reset sequencing validated",
            "Thermal margins verified",
            "Safety requirements met",
            "EMC/EMI compliance confirmed",
        ]
        
        return plan
    
    def export_profile_manifest(self, profile_name: str, output_format: str = "json") -> str:
        """Export complete profile manifest for documentation/automation.
        
        Args:
            profile_name: Name of chip profile
            output_format: "json" or "markdown"
        
        Returns:
            Formatted manifest string
        """
        design = self.get_profile_full_design(profile_name)
        regression = self.get_comprehensive_regression_plan(profile_name)
        
        if output_format == "json":
            manifest = {
                "profile_name": profile_name,
                "profile_data": design["profile"],
                "reference_design": design["reference_design"].__dict__ if design["reference_design"] else None,
                "power_domains": design["power_domains"],
                "integration_rules": design["assembly_rules"],
                "design_patterns": design["design_patterns"],
                "regression_plan": regression,
            }
            return json.dumps(manifest, indent=2, default=str)
        
        elif output_format == "markdown":
            md = f"# {profile_name.replace('_', ' ').title()}\n\n"
            
            profile = design["profile"]
            md += f"**Summary:** {profile.get('summary', '')}\n\n"
            md += f"**Headline:** {profile.get('headline', '')}\n\n"
            
            if design["reference_design"]:
                ref = design["reference_design"]
                md += f"## Reference Design\n\n"
                md += f"- **Die Size:** {ref.die_size_mm2} mm²\n"
                md += f"- **Power Domains:** {len(ref.power_domains)}\n\n"
            
            md += f"## Blocks ({len(profile.get('blocks', []))})\n\n"
            for block in profile.get("blocks", []):
                md += f"- `{block}`\n"
            md += "\n"
            
            md += f"## Technology Support\n\n"
            for tech in profile.get("technology_support", []):
                md += f"- {tech}\n"
            md += "\n"
            
            if design["assembly_rules"]:
                md += f"## Integration Rules\n\n"
                for rule in design["assembly_rules"]:
                    md += f"- {rule}\n"
                md += "\n"
            
            return md
        
        else:
            raise ValueError(f"Unknown output format: {output_format}")


# Global integrator instance
_integrator: Optional[ChipCatalogIntegrator] = None


def get_integrator() -> ChipCatalogIntegrator:
    """Get or create the global chip catalog integrator."""
    global _integrator
    if _integrator is None:
        _integrator = ChipCatalogIntegrator()
    return _integrator


def resolve_profile(profile_name: str) -> dict[str, Any]:
    """Convenience function to resolve a profile with full design data."""
    return get_integrator().get_profile_full_design(profile_name)


def get_regression_plan(profile_name: str) -> dict[str, Any]:
    """Convenience function to get regression test plan for a profile."""
    return get_integrator().get_comprehensive_regression_plan(profile_name)
