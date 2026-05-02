"""
Priority Enhancement Validator for Cycle 85
Validates reusable IPs, VIPs, digital subsystems, and chip profiles
"""

from __future__ import annotations
from typing import Any, Dict, List, Tuple
import json


class PriorityEnhancementValidator:
    """Validates priority catalog items against cycle 85 enhancement requirements."""

    def __init__(self, chip_library: Dict[str, Any]):
        self.chip_library = chip_library
        self.validation_results = {
            'reusable_ips': {},
            'vips': {},
            'digital_subsystems': {},
            'chip_profiles': {},
            'summary': {}
        }

    def validate_reusable_ips(self) -> Dict[str, Any]:
        """Validate priority reusable IPs for enhanced generators and validation coverage."""
        priority_ips = [
            'high_speed_comparator',
            'differential_amplifier',
            'buffered_precision_dac',
            'lvds_receiver'
        ]
        
        results = {}
        for ip_name in priority_ips:
            ip_entry = self.chip_library.get('REUSABLE_IP_LIBRARY', {}).get(ip_name, {})
            
            checks = {
                'exists': ip_name in self.chip_library.get('REUSABLE_IP_LIBRARY', {}),
                'has_validation_coverage': 'validation_coverage' in ip_entry,
                'has_generator_params': 'generator_params' in ip_entry,
                'has_example_config': 'example_config' in ip_entry,
                'has_integration_example': 'integration_example' in ip_entry,
                'technology_support_count': len(ip_entry.get('technology_support', [])),
            }
            
            validation_count = len(ip_entry.get('validation_coverage', []))
            config_count = len(ip_entry.get('example_config', {}))
            integration_count = len(ip_entry.get('integration_example', {}))
            
            results[ip_name] = {
                'checks': checks,
                'enhancement_metrics': {
                    'validation_scenarios': validation_count,
                    'example_configs': config_count,
                    'integration_examples': integration_count,
                    'total_enhancements': validation_count + config_count + integration_count,
                },
                'status': 'enhanced' if all(checks.values()) and validation_count > 5 else 'partial'
            }
        
        self.validation_results['reusable_ips'] = results
        return results

    def validate_vips(self) -> Dict[str, Any]:
        """Validate priority VIPs for protocol scenarios and mixed-signal regressions."""
        priority_vips = [
            'ethernet_vip',
            'profibus_vip',
            'canopen_vip',
            'clock_gating_vip'
        ]
        
        results = {}
        for vip_name in priority_vips:
            vip_entry = self.chip_library.get('VERIFICATION_IP_LIBRARY', {}).get(vip_name, {})
            
            checks = {
                'exists': vip_name in self.chip_library.get('VERIFICATION_IP_LIBRARY', {}),
                'has_protocol': 'protocol' in vip_entry,
                'has_checks': 'checks' in vip_entry,
                'has_design_scenarios': 'design_scenarios' in vip_entry,
                'has_enhanced_scenarios': 'enhanced_scenarios' in vip_entry,
                'has_mixed_signal_regressions': 'mixed_signal_regressions' in vip_entry,
            }
            
            checks_count = len(vip_entry.get('checks', []))
            scenarios_count = len(vip_entry.get('design_scenarios', []))
            enhanced_count = len(vip_entry.get('enhanced_scenarios', []))
            ms_regressions = len(vip_entry.get('mixed_signal_regressions', []))
            
            results[vip_name] = {
                'checks': checks,
                'scenario_metrics': {
                    'protocol_checks': checks_count,
                    'design_scenarios': scenarios_count,
                    'enhanced_scenarios': enhanced_count,
                    'mixed_signal_regressions': ms_regressions,
                    'total_scenarios': scenarios_count + enhanced_count + ms_regressions,
                },
                'status': 'enhanced' if all(checks.values()) and ms_regressions > 3 else 'partial'
            }
        
        self.validation_results['vips'] = results
        return results

    def validate_digital_subsystems(self) -> Dict[str, Any]:
        """Validate priority digital subsystems for integration rules and validation coverage."""
        priority_subsystems = [
            'clock_gating_plane',
            'ethernet_control_plane',
            'safety_monitor_plane',
            'infotainment_control_plane',
            'power_conversion_plane'
        ]
        
        results = {}
        for subsys_name in priority_subsystems:
            subsys_entry = self.chip_library.get('DIGITAL_SUBSYSTEM_LIBRARY', {}).get(subsys_name, {})
            
            checks = {
                'exists': subsys_name in self.chip_library.get('DIGITAL_SUBSYSTEM_LIBRARY', {}),
                'has_blocks': 'blocks' in subsys_entry,
                'has_integration_rules': 'integration_rules' in subsys_entry,
                'has_validation_scenarios': 'validation_scenarios' in subsys_entry,
                'has_design_patterns': 'design_patterns' in subsys_entry,
                'has_technology_support': 'technology_support' in subsys_entry,
            }
            
            blocks_count = len(subsys_entry.get('blocks', []))
            rules_count = len(subsys_entry.get('integration_rules', []))
            scenarios_count = len(subsys_entry.get('validation_scenarios', []))
            patterns_count = len(subsys_entry.get('design_patterns', []))
            
            results[subsys_name] = {
                'checks': checks,
                'detail_metrics': {
                    'block_count': blocks_count,
                    'integration_rules': rules_count,
                    'validation_scenarios': scenarios_count,
                    'design_patterns': patterns_count,
                    'total_details': blocks_count + rules_count + scenarios_count + patterns_count,
                },
                'status': 'enhanced' if all(checks.values()) and rules_count > 5 else 'partial'
            }
        
        self.validation_results['digital_subsystems'] = results
        return results

    def validate_chip_profiles(self) -> Dict[str, Any]:
        """Validate priority chip profiles for top-level references and automation."""
        priority_profiles = [
            'automotive_infotainment_soc',
            'industrial_iot_gateway',
            'isolated_power_supply_controller',
            'ethernet_sensor_hub',
            'safe_motor_drive_controller'
        ]
        
        results = {}
        for profile_name in priority_profiles:
            profile_entry = self.chip_library.get('CHIP_PROFILE_LIBRARY', {}).get(profile_name, {})
            
            checks = {
                'exists': profile_name in self.chip_library.get('CHIP_PROFILE_LIBRARY', {}),
                'has_blocks': 'blocks' in profile_entry,
                'has_vips': 'vips' in profile_entry,
                'has_digital_subsystems': 'digital_subsystems' in profile_entry,
                'has_power_domains': 'power_domains' in profile_entry,
                'has_integration_rules': 'integration_rules' in profile_entry,
                'has_automation_steps': 'automation_steps' in profile_entry,
                'has_design_reference': 'design_reference' in profile_entry,
            }
            
            blocks = len(profile_entry.get('blocks', []))
            vips = len(profile_entry.get('vips', []))
            subsystems = len(profile_entry.get('digital_subsystems', []))
            power_domains = len(profile_entry.get('power_domains', {}))
            rules = len(profile_entry.get('integration_rules', []))
            automation = len(profile_entry.get('automation_steps', []))
            
            results[profile_name] = {
                'checks': checks,
                'assembly_metrics': {
                    'block_count': blocks,
                    'vip_count': vips,
                    'subsystem_count': subsystems,
                    'power_domain_count': power_domains,
                    'integration_rules': rules,
                    'automation_steps': automation,
                    'total_components': blocks + vips + subsystems,
                },
                'status': 'complete' if all(checks.values()) and blocks > 5 else 'partial'
            }
        
        self.validation_results['chip_profiles'] = results
        return results

    def generate_summary(self) -> Dict[str, Any]:
        """Generate summary of validation results."""
        total_checks = 0
        passed_checks = 0
        
        for section_name, section_results in self.validation_results.items():
            if section_name != 'summary':
                for item_name, item_result in section_results.items():
                    if isinstance(item_result, dict) and 'checks' in item_result:
                        total_checks += len(item_result['checks'])
                        passed_checks += sum(1 for v in item_result['checks'].values() if v)
        
        pass_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        
        summary = {
            'total_items_validated': len([r for r in self.validation_results.values() 
                                         if isinstance(r, dict) and 'checks' in next(iter(r.values()), {})]),
            'total_checks': total_checks,
            'passed_checks': passed_checks,
            'pass_rate_percent': pass_rate,
            'overall_status': 'PASS' if pass_rate >= 80 else 'PARTIAL' if pass_rate >= 60 else 'NEEDS_WORK'
        }
        
        self.validation_results['summary'] = summary
        return summary

    def validate_all(self) -> Dict[str, Any]:
        """Run all validations."""
        self.validate_reusable_ips()
        self.validate_vips()
        self.validate_digital_subsystems()
        self.validate_chip_profiles()
        self.generate_summary()
        return self.validation_results

    def export_results_json(self, output_path: str) -> None:
        """Export validation results to JSON."""
        with open(output_path, 'w') as f:
            json.dump(self.validation_results, f, indent=2)

    def export_results_markdown(self, output_path: str) -> None:
        """Export validation results to Markdown."""
        lines = [
            "# Priority Enhancement Validation - Cycle 85\n",
            f"## Summary\n",
            f"- Overall Status: {self.validation_results['summary']['overall_status']}\n",
            f"- Pass Rate: {self.validation_results['summary']['pass_rate_percent']:.1f}%\n",
            f"- Total Checks: {self.validation_results['summary']['total_checks']}\n",
            f"- Passed: {self.validation_results['summary']['passed_checks']}\n\n",
        ]
        
        # Reusable IPs
        lines.append("## Reusable IPs\n")
        for ip_name, result in self.validation_results['reusable_ips'].items():
            status = result['status']
            metrics = result['enhancement_metrics']
            lines.append(f"### {ip_name} - {status.upper()}\n")
            lines.append(f"- Validation Scenarios: {metrics['validation_scenarios']}\n")
            lines.append(f"- Example Configs: {metrics['example_configs']}\n")
            lines.append(f"- Integration Examples: {metrics['integration_examples']}\n")
            lines.append(f"- Total Enhancements: {metrics['total_enhancements']}\n\n")
        
        # VIPs
        lines.append("## Verification IPs\n")
        for vip_name, result in self.validation_results['vips'].items():
            status = result['status']
            metrics = result['scenario_metrics']
            lines.append(f"### {vip_name} - {status.upper()}\n")
            lines.append(f"- Protocol Checks: {metrics['protocol_checks']}\n")
            lines.append(f"- Design Scenarios: {metrics['design_scenarios']}\n")
            lines.append(f"- Enhanced Scenarios: {metrics['enhanced_scenarios']}\n")
            lines.append(f"- Mixed-Signal Regressions: {metrics['mixed_signal_regressions']}\n\n")
        
        # Digital Subsystems
        lines.append("## Digital Subsystems\n")
        for subsys_name, result in self.validation_results['digital_subsystems'].items():
            status = result['status']
            metrics = result['detail_metrics']
            lines.append(f"### {subsys_name} - {status.upper()}\n")
            lines.append(f"- Blocks: {metrics['block_count']}\n")
            lines.append(f"- Integration Rules: {metrics['integration_rules']}\n")
            lines.append(f"- Validation Scenarios: {metrics['validation_scenarios']}\n\n")
        
        # Chip Profiles
        lines.append("## Chip Profiles\n")
        for profile_name, result in self.validation_results['chip_profiles'].items():
            status = result['status']
            metrics = result['assembly_metrics']
            lines.append(f"### {profile_name} - {status.upper()}\n")
            lines.append(f"- Blocks: {metrics['block_count']}\n")
            lines.append(f"- VIPs: {metrics['vip_count']}\n")
            lines.append(f"- Subsystems: {metrics['subsystem_count']}\n")
            lines.append(f"- Automation Steps: {metrics['automation_steps']}\n\n")
        
        with open(output_path, 'w') as f:
            f.writelines(lines)
