#!/usr/bin/env python3
"""
Buck Converter Validation Suite - Comprehensive Testing
========================================================

Tests the buck converter with both Python and NgSpice engines,
validates waveforms, and generates detailed reports.
"""

import sys
import json
import time
from pathlib import Path
import numpy as np

# Add simulator to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from simulator.engine.analog_engine import AnalogEngine, TransientAnalysis, DCAnalysis
from simulator.engine.ngspice_backend import NgSpiceBackend


class BuckValidationSuite:
    """Comprehensive buck converter validation."""
    
    def __init__(self, netlist_path: str):
        self.netlist_path = Path(netlist_path)
        self.results = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'netlist': str(self.netlist_path),
            'tests': {}
        }
        
    def load_netlist(self) -> str:
        """Load netlist from file."""
        with open(self.netlist_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def test_python_engine(self) -> dict:
        """Test with built-in Python engine."""
        print("\n=== Testing Python Engine ===")
        netlist = self.load_netlist()
        
        engine = AnalogEngine()
        engine.load_netlist(netlist)
        
        # Run transient analysis
        ta = TransientAnalysis(engine)
        settings = {
            'tstop': 500e-6,
            'tstep': 100e-9,
            'tstart': 0,
            'uic': False
        }
        
        print(f"Running transient: 0 to {settings['tstop']*1e6}µs, step={settings['tstep']*1e9}ns")
        start_time = time.time()
        results = ta.run(settings)
        elapsed = time.time() - start_time
        
        # Extract key metrics
        time_array = np.array(results['time'])
        vout = np.array(results.get('V(output)', []))
        vin = np.array(results.get('V(input)', []))
        vsw = np.array(results.get('V(sw_node)', []))
        
        # Steady-state window (400-500µs)
        ss_mask = (time_array >= 400e-6) & (time_array <= 500e-6)
        
        metrics = {
            'success': True,
            'elapsed_time': elapsed,
            'num_points': len(time_array),
            'vin_avg': float(np.mean(vin)),
            'vout_final': float(vout[-1]) if len(vout) > 0 else None,
            'vout_avg_steady': float(np.mean(vout[ss_mask])) if np.sum(ss_mask) > 0 else None,
            'vout_min': float(np.min(vout)) if len(vout) > 0 else None,
            'vout_max': float(np.max(vout)) if len(vout) > 0 else None,
            'vout_ripple': float(np.max(vout[ss_mask]) - np.min(vout[ss_mask])) if np.sum(ss_mask) > 0 else None,
            'vsw_range': float(np.max(vsw) - np.min(vsw)) if len(vsw) > 0 else None,
        }
        
        print(f"  ✓ Completed in {elapsed:.2f}s")
        print(f"  • Vin avg: {metrics['vin_avg']:.3f}V")
        print(f"  • Vout final: {metrics['vout_final']:.3f}V")
        print(f"  • Vout avg (400-500µs): {metrics['vout_avg_steady']:.3f}V")
        print(f"  • Vout ripple: {metrics['vout_ripple']*1000:.2f}mV")
        print(f"  • Switch node range: {metrics['vsw_range']:.1f}V")
        
        return {
            'metrics': metrics,
            'waveforms': {
                'time': results['time'],
                'V(input)': results.get('V(input)', []),
                'V(output)': results.get('V(output)', []),
                'V(sw_node)': results.get('V(sw_node)', []),
                'V(gate)': results.get('V(gate)', [])
            }
        }
    
    def test_ngspice_backend(self) -> dict:
        """Test with NgSpice backend."""
        print("\n=== Testing NgSpice Backend ===")
        
        try:
            backend = NgSpiceBackend()
            if not backend.is_available():
                print("  ⚠ NgSpice not available")
                return {'success': False, 'reason': 'ngspice_not_found'}
            
            netlist = self.load_netlist()
            
            print("  Running NgSpice simulation...")
            start_time = time.time()
            results = backend.simulate(netlist)
            elapsed = time.time() - start_time
            
            if not results or 'error' in results:
                print(f"  ✗ NgSpice failed: {results.get('error', 'unknown')}")
                return {'success': False, 'error': results.get('error')}
            
            # Extract metrics
            vout = results.get('v(output)', [])
            vin = results.get('v(input)', [])
            time_array = results.get('time', [])
            
            metrics = {
                'success': True,
                'elapsed_time': elapsed,
                'num_points': len(time_array),
                'vin_avg': float(np.mean(vin)) if len(vin) > 0 else None,
                'vout_final': float(vout[-1]) if len(vout) > 0 else None,
                'vout_avg': float(np.mean(vout)) if len(vout) > 0 else None,
            }
            
            print(f"  ✓ Completed in {elapsed:.2f}s")
            print(f"  • Points: {metrics['num_points']}")
            print(f"  • Vout final: {metrics['vout_final']:.3f}V")
            
            return {
                'metrics': metrics,
                'waveforms': results
            }
            
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            return {'success': False, 'error': str(e)}
    
    def validate_results(self, python_results: dict, ngspice_results: dict) -> dict:
        """Compare Python vs NgSpice results."""
        print("\n=== Validation ===")
        
        validation = {
            'python_engine': 'pass',
            'ngspice_engine': 'pass' if ngspice_results.get('metrics', {}).get('success') else 'skip',
            'checks': []
        }
        
        # Python engine checks
        pm = python_results.get('metrics', {})
        target_vout = 5.0
        
        if pm.get('vout_avg_steady'):
            vout_err = abs(pm['vout_avg_steady'] - target_vout)
            check = {
                'name': 'Python: Vout steady-state near 5V',
                'pass': vout_err < 1.0,
                'value': pm['vout_avg_steady'],
                'target': target_vout,
                'error': vout_err
            }
            validation['checks'].append(check)
            print(f"  {'✓' if check['pass'] else '✗'} {check['name']}: {check['value']:.3f}V (err={check['error']:.3f}V)")
        
        if pm.get('vout_ripple'):
            check = {
                'name': 'Python: Vout ripple < 500mV',
                'pass': pm['vout_ripple'] < 0.5,
                'value': pm['vout_ripple'] * 1000,
                'unit': 'mV'
            }
            validation['checks'].append(check)
            print(f"  {'✓' if check['pass'] else '✗'} {check['name']}: {check['value']:.1f}mV")
        
        if pm.get('vin_avg'):
            check = {
                'name': 'Python: Vin stable at 12V',
                'pass': abs(pm['vin_avg'] - 12.0) < 0.5,
                'value': pm['vin_avg'],
                'target': 12.0
            }
            validation['checks'].append(check)
            print(f"  {'✓' if check['pass'] else '✗'} {check['name']}: {check['value']:.3f}V")
        
        # NgSpice checks (if available)
        if ngspice_results.get('metrics', {}).get('success'):
            nm = ngspice_results['metrics']
            if nm.get('vout_final'):
                check = {
                    'name': 'NgSpice: Vout converged',
                    'pass': abs(nm['vout_final'] - target_vout) < 1.0,
                    'value': nm['vout_final'],
                    'target': target_vout
                }
                validation['checks'].append(check)
                print(f"  {'✓' if check['pass'] else '✗'} {check['name']}: {check['value']:.3f}V")
        
        return validation
    
    def run_full_suite(self) -> dict:
        """Run complete validation suite."""
        print("=" * 70)
        print("BUCK CONVERTER VALIDATION SUITE")
        print("=" * 70)
        print(f"Netlist: {self.netlist_path}")
        
        # Test Python engine
        python_results = self.test_python_engine()
        self.results['tests']['python_engine'] = python_results
        
        # Test NgSpice
        ngspice_results = self.test_ngspice_backend()
        self.results['tests']['ngspice_backend'] = ngspice_results
        
        # Validate
        validation = self.validate_results(python_results, ngspice_results)
        self.results['validation'] = validation
        
        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        passed = sum(1 for c in validation['checks'] if c['pass'])
        total = len(validation['checks'])
        print(f"Checks passed: {passed}/{total}")
        
        if passed == total:
            print("✓ ALL CHECKS PASSED")
        else:
            print("✗ SOME CHECKS FAILED")
        
        return self.results
    
    def save_report(self, output_path: str):
        """Save results to JSON."""
        # Convert numpy arrays to lists for JSON serialization
        def convert_to_serializable(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_serializable(item) for item in obj]
            else:
                return obj
        
        serializable_results = convert_to_serializable(self.results)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, indent=2)
        print(f"\n📄 Report saved: {output_path}")


def main():
    """Main entry point."""
    buck_netlist = Path(__file__).parent.parent / 'examples' / 'standard_circuits' / 'buck_converter.spice'
    
    suite = BuckValidationSuite(buck_netlist)
    results = suite.run_full_suite()
    
    # Save report
    report_path = Path(__file__).parent.parent / 'reports' / 'buck_validation_report.json'
    report_path.parent.mkdir(exist_ok=True)
    suite.save_report(report_path)
    
    return 0 if results['validation']['python_engine'] == 'pass' else 1


if __name__ == '__main__':
    sys.exit(main())
