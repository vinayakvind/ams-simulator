"""
Standard Circuit Test Suite
Tests all standard circuits and verifies results match expected specifications.
"""

import sys
import os
from pathlib import Path
import numpy as np
from typing import Dict, List, Tuple

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from simulator.engine.analog_engine import AnalogEngine


class CircuitTest:
    """Test specification for a standard circuit."""
    
    def __init__(self, filename: str, name: str, 
                 expected_results: Dict[str, Tuple[float, float]],
                 analysis_type: str = "transient"):
        self.filename = filename
        self.name = name
        self.expected_results = expected_results  # {signal_name: (expected_value, tolerance)}
        self.analysis_type = analysis_type
        self.passed = False
        self.actual_results = {}
        self.errors = []


# Define test specifications for each circuit
CIRCUIT_TESTS = [
    CircuitTest(
        "buck_converter.spice",
        "Buck Converter (12V to 5V)",
        {
            "output": (5.0, 0.5),  # 5V ± 0.5V
        },
        "transient"
    ),
    CircuitTest(
        "boost_converter.spice",
        "Boost Converter (5V to 12V)",
        {
            "output": (12.0, 1.0),  # 12V ± 1V
        },
        "transient"
    ),
    CircuitTest(
        "buck_boost_converter.spice",
        "Buck-Boost Converter",
        {
            "output": (-12.0, 1.5),  # -12V ± 1.5V (inverted)
        },
        "transient"
    ),
    CircuitTest(
        "ldo_regulator.spice",
        "LDO Regulator (3.3V)",
        {
            "output": (3.3, 0.1),  # 3.3V ± 0.1V
        },
        "dc"
    ),
    CircuitTest(
        "bandgap_reference.spice",
        "Bandgap Reference (1.25V)",
        {
            "output": (1.25, 0.1),  # 1.25V ± 0.1V
        },
        "dc"
    ),
    CircuitTest(
        "differential_amplifier.spice",
        "Differential Amplifier",
        {
            "output": (0.0, 0.5),  # DC bias near 0V
        },
        "transient"
    ),
    CircuitTest(
        "rc_highpass.spice",
        "RC High-Pass Filter",
        {
            "output": (0.0, 0.1),  # DC blocked
        },
        "transient"
    ),
]


def run_circuit_test(test: CircuitTest, base_path: Path) -> bool:
    """Run a single circuit test."""
    print(f"\n{'='*70}")
    print(f"Testing: {test.name}")
    print(f"File: {test.filename}")
    print(f"Analysis: {test.analysis_type}")
    print(f"{'='*70}")
    
    circuit_path = base_path / test.filename
    if not circuit_path.exists():
        test.errors.append(f"Circuit file not found: {circuit_path}")
        print(f"[X] FAILED: File not found")
        return False
    
    try:
        # Read netlist
        netlist = circuit_path.read_text()
        
        # Create engine and load netlist
        engine = AnalogEngine()
        engine.load_netlist(netlist)
        
        # Run simulation
        print(f"Running {test.analysis_type} analysis...")
        results = None
        
        if test.analysis_type == "dc":
            from simulator.engine.analog_engine import DCAnalysis
            analysis = DCAnalysis(engine)
            # DC settings - operating point if no sweep specified
            settings = {}
            results = analysis.run(settings)
        elif test.analysis_type == "ac":
            from simulator.engine.analog_engine import ACAnalysis
            analysis = ACAnalysis(engine)
            # AC settings - decade sweep from 1 Hz to 1 MHz
            settings = {
                'variation': 'decade',
                'points': 10,
                'fstart': 1,
                'fstop': 1e6
            }
            results = analysis.run(settings)
        else:  # transient
            from simulator.engine.analog_engine import TransientAnalysis
            analysis = TransientAnalysis(engine)
            # Transient settings - auto-detect from netlist or use defaults
            settings = {
                'tstop': 1e-3,  # 1ms default
                'tstep': 1e-6,  # 1us default
                'tstart': 0
            }
            results = analysis.run(settings)
        
        if not results:
            test.errors.append("Simulation returned no results")
            print(f"[X] FAILED: No results")
            return False
        
        # Analyze results
        print(f"\nResults Summary:")
        
        # Get signals from results - they're stored as 'V(nodename)' keys directly in dict
        signal_keys = [k for k in results.keys() if k.startswith('V(') or k.startswith('I(')]
        print(f"  Signals: {len(signal_keys)}")
        print(f"  Time Points: {len(results.get('time', []))}")
        
        # Debug: print all available signals
        if signal_keys:
            print(f"  Available signals: {', '.join(signal_keys[:10])}")  # First 10
        else:
            print(f"  WARNING: No signals in results!")
        
        # Check expected values
        all_passed = True
        for signal_name, (expected, tolerance) in test.expected_results.items():
            # Find signal in results - look for V(signal_name) or just signal_name
            signal_data = None
            matched_name = None
            
            # Try different name variations
            variations = [
                f'V({signal_name})',
                signal_name,
                signal_name.upper(),
                f'V({signal_name.upper()})'
            ]
            
            for sig_name in results.keys():
                if any(var.lower() in sig_name.lower() for var in variations):
                    signal_data = results[sig_name]
                    matched_name = sig_name
                    break
            
            if signal_data is None:
                test.errors.append(f"Signal '{signal_name}' not found in results")
                print(f"  [!] Signal '{signal_name}': NOT FOUND")
                all_passed = False
                continue
            
            # Calculate average value (for transient) or use value (for DC)
            try:
                # Handle both array and scalar results
                if hasattr(signal_data, '__len__') and not isinstance(signal_data, (str, bytes)):
                    # Array result (transient/AC)
                    if len(signal_data) > 0:
                        if test.analysis_type == "transient":
                            # Use last 20% of data for steady-state average
                            start_idx = max(0, int(len(signal_data) * 0.8))
                            actual_value = np.mean(signal_data[start_idx:])
                        else:
                            actual_value = signal_data[-1]
                    else:
                        actual_value = float('nan')
                else:
                    # Scalar result (DC operating point)
                    actual_value = float(signal_data)
                
                # Skip if NaN
                if np.isnan(actual_value):
                    test.errors.append(f"{signal_name}: NaN result (simulation failed)")
                    print(f"  [X] {matched_name}: NaN (expected {expected:.3f} +/- {tolerance:.3f}) - SIMULATION FAILED")
                    all_passed = False
                    continue
                
                test.actual_results[signal_name] = actual_value
                
                # Check if within tolerance
                error = abs(actual_value - expected)
                passed = error <= tolerance
                
                if passed:
                    print(f"  [OK] {matched_name}: {actual_value:.3f} (expected {expected:.3f} +/- {tolerance:.3f})")
                else:
                    print(f"  [X] {matched_name}: {actual_value:.3f} (expected {expected:.3f} +/- {tolerance:.3f}, error: {error:.3f})")
                    test.errors.append(f"{signal_name}: {actual_value:.3f} vs expected {expected:.3f}")
                    all_passed = False
                    
            except Exception as e:
                test.errors.append(f"{signal_name}: Error processing signal - {str(e)}")
                print(f"  [X] {matched_name}: ERROR - {str(e)}")
                all_passed = False
        
        test.passed = all_passed
        
        if all_passed:
            print(f"\n[PASSED]")
        else:
            print(f"\n[FAILED]")
            print(f"Errors: {', '.join(test.errors)}")
        
        return all_passed
        
    except Exception as e:
        test.errors.append(f"Exception: {str(e)}")
        print(f"[X] FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all circuit tests."""
    print("="*70)
    print(" "*10 + "AMS Simulator - Standard Circuit Test Suite")
    print("="*70)
    
    base_path = Path(__file__).parent / "examples" / "standard_circuits"
    
    results = []
    passed_count = 0
    failed_count = 0
    
    for test in CIRCUIT_TESTS:
        success = run_circuit_test(test, base_path)
        results.append(test)
        if success:
            passed_count += 1
        else:
            failed_count += 1
    
    # Summary report
    print("\n" + "="*70)
    print("FINAL SUMMARY")
    print("="*70)
    
    for test in results:
        status = "[PASS]" if test.passed else "[FAIL]"
        print(f"{status:8} {test.name:40} ({test.filename})")
        if not test.passed and test.errors:
            for error in test.errors:
                print(f"         -> {error}")
    
    print("\n" + "="*70)
    print(f"Total Tests: {len(results)}")
    print(f"Passed:      {passed_count} ({passed_count/len(results)*100:.1f}%)")
    print(f"Failed:      {failed_count} ({failed_count/len(results)*100:.1f}%)")
    print("="*70)
    
    # Generate report file
    report_path = Path(__file__).parent / "CIRCUIT_TEST_REPORT.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Standard Circuit Test Report\n\n")
        f.write(f"**Date:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## Summary\n\n")
        f.write(f"- **Total Tests:** {len(results)}\n")
        f.write(f"- **Passed:** {passed_count} ({passed_count/len(results)*100:.1f}%)\n")
        f.write(f"- **Failed:** {failed_count} ({failed_count/len(results)*100:.1f}%)\n\n")
        f.write(f"## Test Results\n\n")
        
        for test in results:
            status_mark = "PASS" if test.passed else "FAIL"
            f.write(f"### [{status_mark}] {test.name}\n\n")
            f.write(f"- **File:** `{test.filename}`\n")
            f.write(f"- **Analysis:** {test.analysis_type}\n")
            f.write(f"- **Status:** {'PASSED' if test.passed else 'FAILED'}\n\n")
            
            if test.expected_results:
                f.write(f"**Expected Results:**\n\n")
                for sig, (val, tol) in test.expected_results.items():
                    actual = test.actual_results.get(sig, "N/A")
                    if isinstance(actual, float):
                        f.write(f"- `{sig}`: {actual:.3f} V (expected {val:.3f} ± {tol:.3f} V)\n")
                    else:
                        f.write(f"- `{sig}`: {actual} (expected {val:.3f} ± {tol:.3f} V)\n")
                f.write("\n")
            
            if test.errors:
                f.write(f"**Errors:**\n\n")
                for error in test.errors:
                    f.write(f"- {error}\n")
                f.write("\n")
    
    print(f"\nDetailed report saved to: {report_path}")
    
    # Return exit code
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
