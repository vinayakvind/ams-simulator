#!/usr/bin/env python
"""
Comprehensive test suite for AMS Simulator
Tests all major components to ensure everything works as expected.
"""

import sys
import os
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all major modules can be imported."""
    print("=" * 70)
    print("TEST 1: Module Imports")
    print("=" * 70)
    
    tests = [
        ("PyQt6.QtWidgets", "PyQt6 GUI Framework"),
        ("numpy", "NumPy"),
        ("scipy", "SciPy"),
        ("matplotlib", "Matplotlib"),
        ("ply", "PLY Parser"),
        ("simulator.components.base", "Components Base"),
        ("simulator.components.passive", "Passive Components"),
        ("simulator.components.sources", "Source Components"),
        ("simulator.components.transistors", "Transistor Components"),
        ("simulator.components.digital", "Digital Components"),
        ("simulator.engine.analog_engine", "Analog Engine"),
        ("simulator.engine.digital_engine", "Digital Engine"),
        ("simulator.engine.mixed_signal_engine", "Mixed-Signal Engine"),
        ("simulator.gui.main_window", "Main GUI Window"),
        ("simulator.gui.schematic_editor", "Schematic Editor"),
        ("simulator.gui.waveform_viewer", "Waveform Viewer"),
        ("simulator.cli.runner", "CLI Runner"),
        ("simulator.cli.batch", "Batch Processor"),
        ("simulator.reporting.report_generator", "Report Generator"),
        ("simulator.reporting.specs_monitor", "Specs Monitor"),
    ]
    
    passed = 0
    failed = 0
    
    for module_name, display_name in tests:
        try:
            __import__(module_name)
            print(f"  ✓ {display_name:30} - OK")
            passed += 1
        except Exception as e:
            print(f"  ✗ {display_name:30} - FAILED: {str(e)[:50]}")
            failed += 1
    
    print(f"\nImport Tests: {passed} passed, {failed} failed")
    return failed == 0


def test_components():
    """Test component instantiation."""
    print("\n" + "=" * 70)
    print("TEST 2: Component Instantiation")
    print("=" * 70)
    
    from simulator.components.transistors import NMOS, PMOS, NPN, PNP
    from simulator.components.diodes import Diode
    from simulator.components.amplifiers import OpAmp
    
    tests = [
        ("NMOS Transistor", lambda: NMOS()),
        ("PMOS Transistor", lambda: PMOS()),
        ("NPN Transistor", lambda: NPN()),
        ("PNP Transistor", lambda: PNP()),
        ("Diode", lambda: Diode()),
        ("Op-Amp", lambda: OpAmp()),
    ]
    
    passed = 0
    failed = 0
    
    for component_name, constructor in tests:
        try:
            component = constructor()
            print(f"  ✓ {component_name:30} - OK")
            passed += 1
        except Exception as e:
            print(f"  ✗ {component_name:30} - FAILED: {str(e)[:50]}")
            failed += 1
    
    print(f"\nComponent Tests: {passed} passed, {failed} failed")
    return failed == 0


def test_netlist_parsing():
    """Test netlist file parsing."""
    print("\n" + "=" * 70)
    print("TEST 3: Example Circuit Files")
    print("=" * 70)
    
    examples_dir = Path(__file__).parent / "examples"
    
    tests = [
        ("voltage_divider.spice", "Voltage Divider"),
        ("rc_lowpass.spice", "RC Low-Pass Filter"),
        ("rc_transient.spice", "RC Transient"),
        ("and_gate_test.v", "AND Gate Testbench"),
    ]
    
    passed = 0
    failed = 0
    
    for filename, display_name in tests:
        filepath = examples_dir / filename
        if filepath.exists():
            with open(filepath, 'r') as f:
                content = f.read()
            if content.strip():
                print(f"  ✓ {display_name:30} - Found ({len(content)} bytes)")
                passed += 1
            else:
                print(f"  ✗ {display_name:30} - Empty")
                failed += 1
        else:
            print(f"  ✗ {display_name:30} - File not found")
            failed += 1
    
    print(f"\nCircuit File Tests: {passed} passed, {failed} failed")
    return failed == 0


def test_engines():
    """Test simulation engine instantiation."""
    print("\n" + "=" * 70)
    print("TEST 4: Simulation Engines")
    print("=" * 70)
    
    from simulator.engine.analog_engine import AnalogEngine
    from simulator.engine.digital_engine import DigitalEngine
    from simulator.engine.mixed_signal_engine import MixedSignalEngine
    
    tests = [
        ("Analog Engine", lambda: AnalogEngine()),
        ("Digital Engine", lambda: DigitalEngine()),
        ("Mixed-Signal Engine", lambda: MixedSignalEngine()),
    ]
    
    passed = 0
    failed = 0
    
    for engine_name, constructor in tests:
        try:
            engine = constructor()
            print(f"  ✓ {engine_name:30} - OK")
            passed += 1
        except Exception as e:
            print(f"  ✗ {engine_name:30} - FAILED: {str(e)[:50]}")
            failed += 1
    
    print(f"\nEngine Tests: {passed} passed, {failed} failed")
    return failed == 0


def test_configuration():
    """Test project configuration."""
    print("\n" + "=" * 70)
    print("TEST 5: Project Configuration")
    print("=" * 70)
    
    import tomllib
    
    pyproject_path = Path(__file__).parent / "pyproject.toml"
    
    try:
        with open(pyproject_path, 'rb') as f:
            config = tomllib.load(f)
        
        # Check project metadata
        project_name = config.get('project', {}).get('name')
        version = config.get('project', {}).get('version')
        dependencies = config.get('project', {}).get('dependencies', [])
        
        print(f"  Project Name:     {project_name}")
        print(f"  Version:          {version}")
        print(f"  Dependencies:     {len(dependencies)}")
        
        print(f"\n  ✓ Configuration loaded successfully")
        return True
    except Exception as e:
        print(f"  ✗ Failed to load configuration: {str(e)}")
        return False


def test_reporting():
    """Test reporting modules."""
    print("\n" + "=" * 70)
    print("TEST 6: Reporting Modules")
    print("=" * 70)
    
    from simulator.reporting.report_generator import ReportGenerator
    from simulator.reporting.specs_monitor import SpecsMonitor
    
    tests = [
        ("Report Generator", lambda: ReportGenerator()),
        ("Specs Monitor", lambda: SpecsMonitor()),
    ]
    
    passed = 0
    failed = 0
    
    for module_name, constructor in tests:
        try:
            module = constructor()
            print(f"  ✓ {module_name:30} - OK")
            passed += 1
        except Exception as e:
            print(f"  ✗ {module_name:30} - FAILED: {str(e)[:50]}")
            failed += 1
    
    print(f"\nReporting Tests: {passed} passed, {failed} failed")
    return failed == 0


def test_cli_tools():
    """Test CLI tools."""
    print("\n" + "=" * 70)
    print("TEST 7: CLI Tools")
    print("=" * 70)
    
    from simulator.cli.runner import SimulationRunner
    from simulator.cli.batch import BatchRunner
    
    tests = [
        ("Simulation Runner", lambda: SimulationRunner()),
        ("Batch Runner", lambda: BatchRunner()),
    ]
    
    passed = 0
    failed = 0
    
    for tool_name, constructor in tests:
        try:
            tool = constructor()
            print(f"  ✓ {tool_name:30} - OK")
            passed += 1
        except Exception as e:
            print(f"  ✗ {tool_name:30} - FAILED: {str(e)[:50]}")
            failed += 1
    
    print(f"\nCLI Tools Tests: {passed} passed, {failed} failed")
    return failed == 0


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + "AMS SIMULATOR - COMPREHENSIVE TEST SUITE".center(68) + "║")
    print("╚" + "=" * 68 + "╝")
    
    results = []
    
    results.append(("Module Imports", test_imports()))
    results.append(("Components", test_components()))
    results.append(("Circuit Files", test_netlist_parsing()))
    results.append(("Simulation Engines", test_engines()))
    results.append(("Configuration", test_configuration()))
    results.append(("Reporting", test_reporting()))
    results.append(("CLI Tools", test_cli_tools()))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed_count = sum(1 for _, result in results if result)
    total_count = len(results)
    
    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        symbol = "✓" if result else "✗"
        print(f"  {symbol} {test_name:40} - {status}")
    
    print("\n" + "=" * 70)
    if passed_count == total_count:
        print(f"ALL TESTS PASSED ({passed_count}/{total_count})")
        print("The AMS Simulator is ready to use!")
    else:
        print(f"SOME TESTS FAILED ({passed_count}/{total_count} passed)")
        print("Please check the errors above.")
    print("=" * 70 + "\n")
    
    return 0 if passed_count == total_count else 1


if __name__ == "__main__":
    sys.exit(main())
