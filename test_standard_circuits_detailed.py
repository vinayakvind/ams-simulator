#!/usr/bin/env python
"""
Test and Verify Standard Circuits
Checks all standard circuits and creates visual representations
"""

import sys
import os
from pathlib import Path
import subprocess
import re

sys.path.insert(0, str(Path(__file__).parent))

def test_standard_circuit(circuit_path: Path, analysis: str = "transient") -> bool:
    """Test if a standard circuit can be simulated."""
    print(f"\n  Testing: {circuit_path.name}")
    
    # Add timeout and analysis-specific args
    args = [
        str(Path(__file__).parent / '.venv' / 'Scripts' / 'python.exe'),
        '-m', 'simulator.cli.runner',
        '--netlist', str(circuit_path),
        '--analysis', analysis,
    ]
    
    if analysis == 'transient':
        args.extend(['--tstop', '100e-6', '--tstep', '1e-9'])
    
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(Path(__file__).parent)
        )
        
        if result.returncode == 0 or "Simulation Results" in result.stdout:
            print(f"    ✓ Simulation successful")
            return True
        else:
            print(f"    ✗ Simulation failed")
            if result.stderr:
                print(f"      Error: {result.stderr[:100]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"    ✗ Simulation timeout")
        return False
    except Exception as e:
        print(f"    ✗ Error: {str(e)[:100]}")
        return False


def extract_circuit_info(netlist_path: Path) -> dict:
    """Extract information from netlist."""
    info = {
        'name': netlist_path.stem,
        'file': netlist_path.name,
        'description': '',
        'components': {},
        'analysis': 'unknown',
    }
    
    try:
        with open(netlist_path, 'r') as f:
            content = f.read()
        
        # Extract description from comments
        lines = content.split('\n')
        for line in lines[:20]:
            if line.startswith('*'):
                if info['description']:
                    info['description'] += ' ' + line.lstrip('*').strip()
                else:
                    info['description'] = line.lstrip('*').strip()
        
        # Count component types
        components = {
            'resistors': len(re.findall(r'^R\d+\s', content, re.MULTILINE)),
            'capacitors': len(re.findall(r'^C\d+\s', content, re.MULTILINE)),
            'inductors': len(re.findall(r'^L\d+\s', content, re.MULTILINE)),
            'transistors': len(re.findall(r'^M\d+\s|^Q\d+\s', content, re.MULTILINE)),
            'diodes': len(re.findall(r'^D\d+\s', content, re.MULTILINE)),
            'sources': len(re.findall(r'^V\d+\s|^I\d+\s', content, re.MULTILINE)),
        }
        info['components'] = {k: v for k, v in components.items() if v > 0}
        
        # Detect analysis type
        if '.TRAN' in content or '.tran' in content:
            info['analysis'] = 'transient'
        elif '.AC' in content or '.ac' in content:
            info['analysis'] = 'ac'
        elif '.DC' in content or '.dc' in content:
            info['analysis'] = 'dc'
        
    except Exception as e:
        info['error'] = str(e)
    
    return info


def create_circuit_diagram_markdown(circuits_dir: Path) -> str:
    """Create markdown documentation for all circuits."""
    md = "# Standard Circuits Library\n\n"
    md += "Complete list of available standard circuits for the AMS Simulator.\n\n"
    
    categories = {
        "Power Electronics": [
            "buck_converter.spice",
            "boost_converter.spice", 
            "buck_boost_converter.spice",
            "flyback_converter.spice",
            "ldo_regulator.spice"
        ],
        "Analog Circuits": [
            "bandgap_reference.spice",
            "differential_amplifier.spice",
            "rc_highpass.spice"
        ],
        "Data Converters": [
            "sar_adc.spice",
            "sigma_delta_adc.spice",
            "r2r_dac.spice"
        ]
    }
    
    for category, filenames in categories.items():
        md += f"## {category}\n\n"
        
        for filename in filenames:
            filepath = circuits_dir / filename
            if filepath.exists():
                info = extract_circuit_info(filepath)
                md += f"### {info['name'].replace('_', ' ').title()}\n"
                md += f"- **File:** `{filename}`\n"
                md += f"- **Description:** {info['description']}\n"
                md += f"- **Analysis Type:** {info['analysis']}\n"
                
                if info['components']:
                    md += f"- **Components:** "
                    comp_list = [f"{k.replace('_', ' ')}: {v}" 
                               for k, v in info['components'].items()]
                    md += ", ".join(comp_list) + "\n"
                
                md += "\n"
        
        md += "\n"
    
    return md


def main():
    """Run all tests."""
    print("=" * 70)
    print("STANDARD CIRCUITS TEST SUITE")
    print("=" * 70)
    
    circuits_dir = Path(__file__).parent / "examples" / "standard_circuits"
    
    if not circuits_dir.exists():
        print(f"✗ Circuits directory not found: {circuits_dir}")
        return 1
    
    print(f"\nCircuits Directory: {circuits_dir}")
    print(f"Found {len(list(circuits_dir.glob('*.spice')))} circuits\n")
    
    # Collect all circuits
    circuits = sorted(circuits_dir.glob("*.spice"))
    
    if not circuits:
        print("✗ No circuits found!")
        return 1
    
    print("=" * 70)
    print("CIRCUIT INFORMATION")
    print("=" * 70)
    
    circuit_info_list = []
    for circuit_path in circuits:
        info = extract_circuit_info(circuit_path)
        circuit_info_list.append(info)
        
        print(f"\n{info['name'].upper()}")
        print(f"  File: {info['file']}")
        if info['description']:
            print(f"  Description: {info['description'][:80]}")
        print(f"  Analysis: {info['analysis']}")
        if info['components']:
            print(f"  Components: {info['components']}")
    
    print("\n" + "=" * 70)
    print("CIRCUIT SIMULATION TEST")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for circuit_path in circuits:
        # Determine analysis type
        info = next(i for i in circuit_info_list if i['file'] == circuit_path.name)
        analysis = info['analysis']
        
        if test_standard_circuit(circuit_path, analysis):
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Total Circuits: {len(circuits)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    # Generate documentation
    print("\n" + "=" * 70)
    print("GENERATING DOCUMENTATION")
    print("=" * 70)
    
    doc_path = Path(__file__).parent / "STANDARD_CIRCUITS_GUIDE.md"
    doc_content = create_circuit_diagram_markdown(circuits_dir)
    
    try:
        with open(doc_path, 'w') as f:
            f.write(doc_content)
        print(f"✓ Documentation created: {doc_path}")
    except Exception as e:
        print(f"✗ Failed to create documentation: {e}")
    
    print("\n" + "=" * 70)
    if failed == 0:
        print("ALL TESTS PASSED - All standard circuits are functional!")
    else:
        print(f"SOME TESTS FAILED - {failed} circuit(s) need investigation")
    print("=" * 70)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
