#!/usr/bin/env python3
"""
API Workflow Scripts for Buck Converter
=======================================

Complete API-driven workflow for circuit simulation and validation.
All operations executable via HTTP REST API.
"""

import requests
import json
import time
from typing import Dict, Any, Optional
from pathlib import Path


class SimulatorAPI:
    """API client for AMS Simulator."""
    
    def __init__(self, base_url: str = "http://localhost:5198"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def check_status(self) -> Dict[str, Any]:
        """Check API server status."""
        response = self.session.get(f"{self.base_url}/api/status")
        response.raise_for_status()
        return response.json()
    
    def list_circuits(self) -> Dict[str, Any]:
        """List available standard circuits."""
        response = self.session.get(f"{self.base_url}/api/circuits")
        response.raise_for_status()
        return response.json()
    
    def load_circuit(self, circuit_name: str) -> Dict[str, Any]:
        """Load a standard circuit by name."""
        response = self.session.post(
            f"{self.base_url}/api/circuits/load",
            json={'name': circuit_name}
        )
        response.raise_for_status()
        return response.json()
    
    def simulate(self, netlist: str, analysis: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Run simulation via API."""
        payload = {
            'netlist': netlist,
            'analysis': analysis,
            'settings': settings
        }
        response = self.session.post(
            f"{self.base_url}/api/simulate",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def get_results(self) -> Dict[str, Any]:
        """Get last simulation results."""
        response = self.session.get(f"{self.base_url}/api/results")
        response.raise_for_status()
        return response.json()


class BuckAPIWorkflow:
    """Complete buck converter workflow via API."""
    
    def __init__(self, api_url: str = "http://localhost:5198"):
        self.api = SimulatorAPI(api_url)
        self.netlist_path = Path(__file__).parent.parent / 'examples' / 'standard_circuits' / 'buck_converter.spice'
    
    def workflow_01_check_server(self) -> Dict[str, Any]:
        """Step 1: Verify API server is running."""
        print("\n[Step 1] Checking API server...")
        try:
            status = self.api.check_status()
            print(f"  ✓ Server status: {status.get('status')}")
            return {'success': True, 'status': status}
        except Exception as e:
            print(f"  ✗ Server not available: {e}")
            return {'success': False, 'error': str(e)}
    
    def workflow_02_load_netlist(self) -> Dict[str, Any]:
        """Step 2: Load buck converter netlist."""
        print("\n[Step 2] Loading netlist...")
        try:
            with open(self.netlist_path, 'r', encoding='utf-8') as f:
                netlist = f.read()
            print(f"  ✓ Loaded {len(netlist)} characters")
            return {'success': True, 'netlist': netlist, 'size': len(netlist)}
        except Exception as e:
            print(f"  ✗ Failed to load: {e}")
            return {'success': False, 'error': str(e)}
    
    def workflow_03_run_transient(self, netlist: str) -> Dict[str, Any]:
        """Step 3: Run transient analysis via API."""
        print("\n[Step 3] Running transient analysis...")
        try:
            start_time = time.time()
            results = self.api.simulate(
                netlist=netlist,
                analysis='transient',
                settings={
                    'tstop': 500e-6,
                    'tstep': 100e-9
                }
            )
            elapsed = time.time() - start_time
            
            num_points = len(results.get('time', []))
            print(f"  ✓ Simulation completed in {elapsed:.2f}s")
            print(f"  • Data points: {num_points}")
            
            return {'success': True, 'results': results, 'elapsed': elapsed}
        except Exception as e:
            print(f"  ✗ Simulation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def workflow_04_extract_metrics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Step 4: Extract key metrics from results."""
        print("\n[Step 4] Extracting metrics...")
        try:
            import numpy as np
            
            time_arr = np.array(results.get('time', []))
            vout = np.array(results.get('V(output)', []))
            vin = np.array(results.get('V(input)', []))
            
            # Steady-state (400-500µs)
            ss_mask = (time_arr >= 400e-6) & (time_arr <= 500e-6)
            
            metrics = {
                'vin_avg': float(np.mean(vin)),
                'vout_final': float(vout[-1]),
                'vout_avg_steady': float(np.mean(vout[ss_mask])),
                'vout_ripple_mv': float((np.max(vout[ss_mask]) - np.min(vout[ss_mask])) * 1000)
            }
            
            print(f"  • Vin avg: {metrics['vin_avg']:.3f}V")
            print(f"  • Vout avg (400-500µs): {metrics['vout_avg_steady']:.3f}V")
            print(f"  • Vout ripple: {metrics['vout_ripple_mv']:.2f}mV")
            
            return {'success': True, 'metrics': metrics}
        except Exception as e:
            print(f"  ✗ Metric extraction failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def workflow_05_validate(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Step 5: Validate against specs."""
        print("\n[Step 5] Validating specs...")
        
        targets = {
            'vin': 12.0,
            'vout': 5.0,
            'ripple_max_mv': 500.0
        }
        
        checks = {
            'vin_stable': abs(metrics['vin_avg'] - targets['vin']) < 0.5,
            'vout_in_range': abs(metrics['vout_avg_steady'] - targets['vout']) < 1.0,
            'ripple_acceptable': metrics['vout_ripple_mv'] < targets['ripple_max_mv']
        }
        
        for name, passed in checks.items():
            status = '✓' if passed else '✗'
            print(f"  {status} {name}")
        
        all_passed = all(checks.values())
        return {
            'success': all_passed,
            'checks': checks,
            'pass_count': sum(checks.values()),
            'total': len(checks)
        }
    
    def run_full_workflow(self) -> Dict[str, Any]:
        """Execute complete workflow end-to-end."""
        print("="*70)
        print("BUCK CONVERTER API WORKFLOW")
        print("="*70)
        
        workflow_results = {}
        
        # Step 1: Check server
        result = self.workflow_01_check_server()
        workflow_results['step1_server'] = result
        if not result['success']:
            print("\n✗ Workflow aborted: Server not available")
            return workflow_results
        
        # Step 2: Load netlist
        result = self.workflow_02_load_netlist()
        workflow_results['step2_netlist'] = result
        if not result['success']:
            print("\n✗ Workflow aborted: Netlist load failed")
            return workflow_results
        
        netlist = result['netlist']
        
        # Step 3: Run simulation
        result = self.workflow_03_run_transient(netlist)
        workflow_results['step3_simulation'] = result
        if not result['success']:
            print("\n✗ Workflow aborted: Simulation failed")
            return workflow_results
        
        sim_results = result['results']
        
        # Step 4: Extract metrics
        result = self.workflow_04_extract_metrics(sim_results)
        workflow_results['step4_metrics'] = result
        if not result['success']:
            print("\n✗ Workflow aborted: Metric extraction failed")
            return workflow_results
        
        metrics = result['metrics']
        
        # Step 5: Validate
        result = self.workflow_05_validate(metrics)
        workflow_results['step5_validation'] = result
        
        # Summary
        print("\n" + "="*70)
        print("WORKFLOW SUMMARY")
        print("="*70)
        if result['success']:
            print(f"✓ All checks passed ({result['pass_count']}/{result['total']})")
        else:
            print(f"✗ Some checks failed ({result['pass_count']}/{result['total']})")
        
        return workflow_results


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Buck Converter API Workflow')
    parser.add_argument('--url', default='http://localhost:5198', help='API base URL')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    workflow = BuckAPIWorkflow(args.url)
    results = workflow.run_full_workflow()
    
    if args.json:
        # Convert numpy types for JSON
        def convert(obj):
            if hasattr(obj, 'tolist'):
                return obj.tolist()
            elif hasattr(obj, '__dict__'):
                return obj.__dict__
            return obj
        
        print(json.dumps(results, default=convert, indent=2))
    
    # Exit code based on final validation
    final_validation = results.get('step5_validation', {})
    return 0 if final_validation.get('success') else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
