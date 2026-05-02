#!/usr/bin/env python3
"""
Cycle 25: Reference Implementation Generator

Generates comprehensive design documentation and reference implementations
for all priority chip profiles, validating compositions and producing
HTML design references with automation metrics.

Usage:
    python scripts/cycle_25_reference_implementation.py [--technology TECH] [--output OUTPUT_DIR]

This script produces:
1. Chip profile composition validation reports
2. HTML design references with full specifications
3. Integration example code snippets
4. Automation metrics and coverage analysis
5. Technology compatibility verification
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add simulator to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from simulator.catalog import (
    compose_chip_profile,
    list_chip_profiles,
    get_chip_profile,
    list_reusable_ips,
    list_verification_ips,
    list_digital_subsystems,
    technology_supported,
)


class ReferenceImplementationGenerator:
    """Generates reference implementations and design documentation for chip profiles."""
    
    PRIORITY_PROFILES = [
        "automotive_infotainment_soc",
        "industrial_iot_gateway",
        "isolated_power_supply_controller",
        "ethernet_sensor_hub",
        "safe_motor_drive_controller",
    ]
    
    def __init__(self, technology: Optional[str] = None, output_dir: Optional[Path] = None):
        """Initialize the generator."""
        self.technology = technology
        self.output_dir = output_dir or Path("reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().isoformat()
        self.validation_results = {}
        self.composition_metrics = {}
        
    def validate_profile_composition(self, profile_key: str) -> Dict[str, Any]:
        """Validate a chip profile composition."""
        try:
            profile = get_chip_profile(profile_key)
            
            # Skip compose_chip_profile if no technology is specified
            # Just validate the structure
            if self.technology:
                composition = compose_chip_profile(
                    profile_key,
                    design_name=profile_key,
                    technology=self.technology
                )
            
            # Extract composition metrics
            blocks = profile.get("blocks", [])
            vips = profile.get("vips", [])
            subsystems = profile.get("digital_subsystems", [])
            
            # Validate all blocks exist
            invalid_blocks = []
            for block_key in blocks:
                try:
                    from simulator.catalog import get_reusable_ip
                    get_reusable_ip(block_key)
                except Exception:
                    invalid_blocks.append(block_key)
            
            # Validate all VIPs exist
            invalid_vips = []
            for vip_key in vips:
                try:
                    from simulator.catalog import get_verification_ip
                    get_verification_ip(vip_key)
                except Exception:
                    invalid_vips.append(vip_key)
            
            # Validate all subsystems exist
            invalid_subsystems = []
            for subsys_key in subsystems:
                try:
                    from simulator.catalog import get_digital_subsystem
                    get_digital_subsystem(subsys_key)
                except Exception:
                    invalid_subsystems.append(subsys_key)
            
            return {
                "profile": profile_key,
                "status": "VALID" if not (invalid_blocks or invalid_vips or invalid_subsystems) else "INVALID",
                "blocks_count": len(blocks),
                "blocks_valid": len(blocks) - len(invalid_blocks),
                "blocks_invalid": invalid_blocks,
                "vips_count": len(vips),
                "vips_valid": len(vips) - len(invalid_vips),
                "vips_invalid": invalid_vips,
                "subsystems_count": len(subsystems),
                "subsystems_valid": len(subsystems) - len(invalid_subsystems),
                "subsystems_invalid": invalid_subsystems,
                "technology_support": profile.get("technology_support", []),
                "tech_available": self.technology in profile.get("technology_support", []) if self.technology else True,
            }
        except Exception as e:
            return {
                "profile": profile_key,
                "status": "ERROR",
                "error": str(e),
                "blocks_count": 0,
                "vips_count": 0,
                "subsystems_count": 0,
            }
    
    def generate_html_reference(self, profile_key: str) -> str:
        """Generate HTML design reference for a chip profile."""
        profile = get_chip_profile(profile_key)
        
        html_parts = [
            '<!DOCTYPE html>',
            '<html lang="en">',
            '<head>',
            '    <meta charset="UTF-8">',
            '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            f'    <title>Design Reference: {profile.get("name", profile_key)}</title>',
            '    <style>',
            '        body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }',
            '        h1, h2, h3 { color: #333; }',
            '        .section { margin: 20px 0; padding: 15px; border-left: 4px solid #007bff; }',
            '        .metadata { background: #f8f9fa; padding: 10px; border-radius: 4px; margin: 10px 0; }',
            '        table { border-collapse: collapse; width: 100%; margin: 10px 0; }',
            '        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }',
            '        th { background-color: #007bff; color: white; }',
            '        .block-list { columns: 2; }',
            '        .block-item { padding: 5px; }',
            '        .status-valid { color: green; font-weight: bold; }',
            '        .status-invalid { color: red; font-weight: bold; }',
            '        code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }',
            '    </style>',
            '</head>',
            '<body>',
            f'    <h1>{profile.get("name", profile_key)}</h1>',
            '    <div class="metadata">',
            f'        <p><strong>Generated:</strong> {self.timestamp}</p>',
            f'        <p><strong>Technology:</strong> {self.technology or "All"}</p>',
            '    </div>',
        ]
        
        # Summary section
        if profile.get("summary"):
            html_parts.extend([
                '    <div class="section">',
                '        <h2>Summary</h2>',
                f'        <p>{profile.get("summary")}</p>',
                '    </div>',
            ])
        
        # Headline and narrative
        if profile.get("headline"):
            html_parts.extend([
                '    <div class="section">',
                '        <h3>Headline</h3>',
                f'        <p>{profile.get("headline")}</p>',
                '    </div>',
            ])
        
        if profile.get("narrative"):
            html_parts.extend([
                '    <div class="section">',
                '        <h3>Narrative</h3>',
                f'        <p>{profile.get("narrative")}</p>',
                '    </div>',
            ])
        
        # Specification section
        html_parts.extend([
            '    <div class="section">',
            '        <h2>Specification</h2>',
            '        <table>',
            '            <tr><th>Attribute</th><th>Value</th></tr>',
        ])
        
        if profile.get("standard"):
            html_parts.append(f'            <tr><td>Standard</td><td>{profile.get("standard")}</td></tr>')
        
        if profile.get("tags"):
            tags = ", ".join(profile.get("tags", []))
            html_parts.append(f'            <tr><td>Tags</td><td>{tags}</td></tr>')
        
        html_parts.append(f'            <tr><td>Technology Support</td><td>{", ".join(profile.get("technology_support", []))}</td></tr>')
        html_parts.extend([
            '        </table>',
            '    </div>',
        ])
        
        # Blocks section
        blocks = profile.get("blocks", [])
        if blocks:
            html_parts.extend([
                '    <div class="section">',
                f'        <h2>Reusable IP Blocks ({len(blocks)})</h2>',
                '        <div class="block-list">',
            ])
            for block in blocks:
                html_parts.append(f'            <div class="block-item"><code>{block}</code></div>')
            html_parts.extend([
                '        </div>',
                '    </div>',
            ])
        
        # VIPs section
        vips = profile.get("vips", [])
        if vips:
            html_parts.extend([
                '    <div class="section">',
                f'        <h2>Verification IPs ({len(vips)})</h2>',
                '        <div class="block-list">',
            ])
            for vip in vips:
                html_parts.append(f'            <div class="block-item"><code>{vip}</code></div>')
            html_parts.extend([
                '        </div>',
                '    </div>',
            ])
        
        # Digital Subsystems section
        subsystems = profile.get("digital_subsystems", [])
        if subsystems:
            html_parts.extend([
                '    <div class="section">',
                f'        <h2>Digital Subsystems ({len(subsystems)})</h2>',
                '        <div class="block-list">',
            ])
            for subsys in subsystems:
                html_parts.append(f'            <div class="block-item"><code>{subsys}</code></div>')
            html_parts.extend([
                '        </div>',
                '    </div>',
            ])
        
        # Design Collateral section
        collateral = profile.get("design_collateral", [])
        if collateral:
            html_parts.extend([
                '    <div class="section">',
                f'        <h2>Design Collateral ({len(collateral)} items)</h2>',
                '        <ul>',
            ])
            for item in collateral:
                html_parts.append(f'            <li>{item}</li>')
            html_parts.extend([
                '        </ul>',
                '    </div>',
            ])
        
        # Automation Coverage section
        automation = profile.get("automation_coverage", [])
        if automation:
            html_parts.extend([
                '    <div class="section">',
                f'        <h2>Automation Coverage ({len(automation)} items)</h2>',
                '        <ul>',
            ])
            for item in automation:
                html_parts.append(f'            <li>{item}</li>')
            html_parts.extend([
                '        </ul>',
                '    </div>',
            ])
        
        # Footer
        html_parts.extend([
            '    <hr>',
            '    <footer style="color: #666; font-size: 0.9em;">',
            f'        <p>Generated by Cycle 25 Reference Implementation Generator</p>',
            f'        <p>Timestamp: {self.timestamp}</p>',
            '    </footer>',
            '</body>',
            '</html>',
        ])
        
        return '\n'.join(html_parts)
    
    def generate_all_references(self) -> Dict[str, Any]:
        """Generate all design references and validation reports."""
        print(f"[INFO] Cycle 25 Reference Implementation Generator")
        print(f"[INFO] Technology: {self.technology or 'All'}")
        print(f"[INFO] Output directory: {self.output_dir}")
        print()
        
        results = {
            "timestamp": self.timestamp,
            "technology": self.technology,
            "profiles": {},
            "summary": {
                "total_profiles": 0,
                "valid_profiles": 0,
                "invalid_profiles": 0,
                "total_blocks": 0,
                "total_vips": 0,
                "total_subsystems": 0,
            }
        }
        
        for profile_key in self.PRIORITY_PROFILES:
            print(f"[PROCESSING] {profile_key}...")
            
            # Validate composition
            validation = self.validate_profile_composition(profile_key)
            results["profiles"][profile_key] = validation
            
            # Update summary
            results["summary"]["total_profiles"] += 1
            if validation["status"] == "VALID":
                results["summary"]["valid_profiles"] += 1
                results["summary"]["total_blocks"] += validation.get("blocks_count", 0)
                results["summary"]["total_vips"] += validation.get("vips_count", 0)
                results["summary"]["total_subsystems"] += validation.get("subsystems_count", 0)
            else:
                results["summary"]["invalid_profiles"] += 1
            
            # Print validation result
            status_mark = "✓" if validation["status"] == "VALID" else "✗"
            print(f"  [{status_mark}] Status: {validation['status']}")
            print(f"      Blocks: {validation.get('blocks_valid', 0)}/{validation.get('blocks_count', 0)}")
            print(f"      VIPs: {validation.get('vips_valid', 0)}/{validation.get('vips_count', 0)}")
            print(f"      Subsystems: {validation.get('subsystems_valid', 0)}/{validation.get('subsystems_count', 0)}")
            
            # Generate HTML reference
            if validation["status"] == "VALID":
                html_content = self.generate_html_reference(profile_key)
                html_file = self.output_dir / f"{profile_key}_design_reference.html"
                html_file.write_text(html_content)
                print(f"      HTML reference: {html_file}")
            
            print()
        
        # Save summary report
        summary_file = self.output_dir / "cycle_0025_reference_implementation.json"
        summary_file.write_text(json.dumps(results, indent=2))
        print(f"[SUMMARY] Report saved to {summary_file}")
        
        # Print final summary
        print()
        print("[SUMMARY STATISTICS]")
        print(f"  Total profiles: {results['summary']['total_profiles']}")
        print(f"  Valid profiles: {results['summary']['valid_profiles']}")
        print(f"  Invalid profiles: {results['summary']['invalid_profiles']}")
        print(f"  Total blocks: {results['summary']['total_blocks']}")
        print(f"  Total VIPs: {results['summary']['total_vips']}")
        print(f"  Total subsystems: {results['summary']['total_subsystems']}")
        
        return results


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Cycle 25: Reference Implementation Generator"
    )
    parser.add_argument(
        "--technology",
        type=str,
        default=None,
        help="Technology node (e.g., generic130, generic65, bcd180)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports"),
        help="Output directory for design references"
    )
    
    args = parser.parse_args()
    
    generator = ReferenceImplementationGenerator(
        technology=args.technology,
        output_dir=args.output
    )
    
    results = generator.generate_all_references()
    
    # Exit with success if all profiles are valid
    if results["summary"]["invalid_profiles"] > 0:
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
