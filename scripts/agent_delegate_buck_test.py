#!/usr/bin/env python3
"""
Agent Delegation Script - Buck Converter Testing
================================================

Simple task-based workflow for buck converter validation.
Each task is atomic and can be executed independently by simple agents.
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any

# Add simulator to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class BuckAgentTasks:
    """Atomic tasks for buck converter validation."""
    
    def __init__(self, netlist_path: str = None):
        self.netlist_path = netlist_path or str(
            Path(__file__).parent.parent / 'examples' / 'standard_circuits' / 'buck_converter.spice'
        )
        self.results = {}
    
    # ========== LEVEL 1: BASIC FILE OPERATIONS ==========
    
    def task_check_file(self) -> Dict[str, Any]:
        """Task 1.1: Check if buck netlist file exists."""
        path = Path(self.netlist_path)
        return {
            'task': 'check_file',
            'success': path.exists(),
            'path': str(path),
            'size_bytes': path.stat().st_size if path.exists() else 0
        }
    
    def task_read_netlist(self) -> Dict[str, Any]:
        """Task 1.2: Read netlist content."""
        try:
            with open(self.netlist_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {
                'task': 'read_netlist',
                'success': True,
                'lines': len(content.splitlines()),
                'characters': len(content),
                'has_models': '.MODEL' in content.upper()
            }
        except Exception as e:
            return {'task': 'read_netlist', 'success': False, 'error': str(e)}
    
    def task_count_elements(self) -> Dict[str, Any]:
        """Task 1.3: Count circuit elements."""
        try:
            with open(self.netlist_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            counts = {'R': 0, 'C': 0, 'L': 0, 'M': 0, 'D': 0, 'V': 0, 'I': 0}
            for line in lines:
                line = line.strip()
                if line and not line.startswith('*') and not line.startswith('.'):
                    prefix = line[0].upper()
                    if prefix in counts:
                        counts[prefix] += 1
            
            return {
                'task': 'count_elements',
                'success': True,
                'element_counts': counts,
                'total': sum(counts.values())
            }
        except Exception as e:
            return {'task': 'count_elements', 'success': False, 'error': str(e)}
    
    # ========== LEVEL 2: SIMULATION SETUP ==========
    
    def task_load_engine(self) -> Dict[str, Any]:
        """Task 2.1: Load netlist into AnalogEngine."""
        try:
            from simulator.engine.analog_engine import AnalogEngine
            
            with open(self.netlist_path, 'r', encoding='utf-8') as f:
                netlist = f.read()
            
            engine = AnalogEngine()
            engine.load_netlist(netlist)
            
            return {
                'task': 'load_engine',
                'success': True,
                'num_nodes': engine._num_nodes,
                'num_elements': len(engine._elements),
                'num_models': len(engine._models)
            }
        except Exception as e:
            return {'task': 'load_engine', 'success': False, 'error': str(e)}
    
    def task_dc_analysis(self) -> Dict[str, Any]:
        """Task 2.2: Run DC operating point analysis."""
        try:
            from simulator.engine.analog_engine import AnalogEngine, DCAnalysis
            
            with open(self.netlist_path, 'r', encoding='utf-8') as f:
                netlist = f.read()
            
            engine = AnalogEngine()
            engine.load_netlist(netlist)
            
            dc = DCAnalysis(engine)
            results = dc.run({})
            
            return {
                'task': 'dc_analysis',
                'success': True,
                'V_input': results.get('V(input)', 0),
                'V_output': results.get('V(output)', 0),
                'num_nodes': len([k for k in results.keys() if k.startswith('V(')])
            }
        except Exception as e:
            return {'task': 'dc_analysis', 'success': False, 'error': str(e)}
    
    def task_check_models(self) -> Dict[str, Any]:
        """Task 2.3: Verify device models are defined."""
        try:
            from simulator.engine.analog_engine import AnalogEngine
            
            with open(self.netlist_path, 'r', encoding='utf-8') as f:
                netlist = f.read()
            
            engine = AnalogEngine()
            engine.load_netlist(netlist)
            
            models = list(engine._models.keys())
            return {
                'task': 'check_models',
                'success': True,
                'models': models,
                'has_pmos': 'PMOS' in ' '.join(models).upper(),
                'has_nmos': 'NMOS' in ' '.join(models).upper(),
                'has_diode': any('D' in m.upper() for m in models)
            }
        except Exception as e:
            return {'task': 'check_models', 'success': False, 'error': str(e)}
    
    # ========== LEVEL 3: FULL SIMULATION & VALIDATION ==========
    
    def task_run_transient(self) -> Dict[str, Any]:
        """Task 3.1: Run full transient analysis."""
        try:
            from simulator.engine.analog_engine import AnalogEngine, TransientAnalysis
            import numpy as np
            
            with open(self.netlist_path, 'r', encoding='utf-8') as f:
                netlist = f.read()
            
            engine = AnalogEngine()
            engine.load_netlist(netlist)
            
            ta = TransientAnalysis(engine)
            results = ta.run({'tstop': 500e-6, 'tstep': 100e-9})
            
            time = np.array(results['time'])
            vout = np.array(results.get('V(output)', []))
            
            return {
                'task': 'run_transient',
                'success': True,
                'num_points': len(time),
                'time_final': float(time[-1]) if len(time) > 0 else 0,
                'vout_final': float(vout[-1]) if len(vout) > 0 else 0,
                'vout_min': float(vout.min()) if len(vout) > 0 else 0,
                'vout_max': float(vout.max()) if len(vout) > 0 else 0
            }
        except Exception as e:
            import traceback
            return {
                'task': 'run_transient',
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def task_compute_metrics(self) -> Dict[str, Any]:
        """Task 3.2: Compute steady-state metrics (400-500µs)."""
        try:
            from simulator.engine.analog_engine import AnalogEngine, TransientAnalysis
            import numpy as np
            
            with open(self.netlist_path, 'r', encoding='utf-8') as f:
                netlist = f.read()
            
            engine = AnalogEngine()
            engine.load_netlist(netlist)
            
            ta = TransientAnalysis(engine)
            results = ta.run({'tstop': 500e-6, 'tstep': 100e-9})
            
            time = np.array(results['time'])
            vout = np.array(results.get('V(output)', []))
            vin = np.array(results.get('V(input)', []))
            
            # Steady-state window
            ss_mask = (time >= 400e-6) & (time <= 500e-6)
            
            return {
                'task': 'compute_metrics',
                'success': True,
                'vin_avg': float(np.mean(vin)),
                'vout_final': float(vout[-1]),
                'vout_avg_steady': float(np.mean(vout[ss_mask])),
                'vout_ripple_mv': float((np.max(vout[ss_mask]) - np.min(vout[ss_mask])) * 1000),
                'duty_cycle_inferred': float(np.mean(vout[ss_mask]) / np.mean(vin))
            }
        except Exception as e:
            return {'task': 'compute_metrics', 'success': False, 'error': str(e)}
    
    def task_validate_specs(self) -> Dict[str, Any]:
        """Task 3.3: Validate against target specifications."""
        try:
            from simulator.engine.analog_engine import AnalogEngine, TransientAnalysis
            import numpy as np
            
            with open(self.netlist_path, 'r', encoding='utf-8') as f:
                netlist = f.read()
            
            engine = AnalogEngine()
            engine.load_netlist(netlist)
            
            ta = TransientAnalysis(engine)
            results = ta.run({'tstop': 500e-6, 'tstep': 100e-9})
            
            time = np.array(results['time'])
            vout = np.array(results.get('V(output)', []))
            vin = np.array(results.get('V(input)', []))
            
            ss_mask = (time >= 400e-6) & (time <= 500e-6)
            
            # Target specs
            vin_target = 12.0
            vout_target = 5.0
            ripple_max_mv = 500.0
            
            # Measured values
            vin_avg = float(np.mean(vin))
            vout_avg = float(np.mean(vout[ss_mask]))
            ripple_mv = float((np.max(vout[ss_mask]) - np.min(vout[ss_mask])) * 1000)
            
            # Checks
            checks = {
                'vin_stable': abs(vin_avg - vin_target) < 0.5,
                'vout_in_range': abs(vout_avg - vout_target) < 1.0,
                'ripple_acceptable': ripple_mv < ripple_max_mv
            }
            
            return {
                'task': 'validate_specs',
                'success': all(checks.values()),
                'checks': checks,
                'measured': {
                    'vin_avg': vin_avg,
                    'vout_avg': vout_avg,
                    'ripple_mv': ripple_mv
                },
                'targets': {
                    'vin': vin_target,
                    'vout': vout_target,
                    'ripple_max_mv': ripple_max_mv
                },
                'pass_count': sum(checks.values()),
                'total_checks': len(checks)
            }
        except Exception as e:
            return {'task': 'validate_specs', 'success': False, 'error': str(e)}
    
    # ========== TASK ROUTER ==========
    
    def run_task(self, task_name: str) -> Dict[str, Any]:
        """Execute a specific task by name."""
        task_map = {
            # Level 1
            'check_file': self.task_check_file,
            'read_netlist': self.task_read_netlist,
            'count_elements': self.task_count_elements,
            # Level 2
            'load_engine': self.task_load_engine,
            'dc_analysis': self.task_dc_analysis,
            'check_models': self.task_check_models,
            # Level 3
            'run_transient': self.task_run_transient,
            'compute_metrics': self.task_compute_metrics,
            'validate_specs': self.task_validate_specs
        }
        
        if task_name not in task_map:
            return {
                'task': task_name,
                'success': False,
                'error': f'Unknown task: {task_name}',
                'available_tasks': list(task_map.keys())
            }
        
        return task_map[task_name]()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Buck Converter Agent Tasks')
    parser.add_argument('--task', required=True, help='Task name to execute')
    parser.add_argument('--netlist', help='Path to buck netlist file')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    agent = BuckAgentTasks(args.netlist)
    result = agent.run_task(args.task)
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"Task: {result.get('task', 'unknown')}")
        print(f"Status: {'✓ SUCCESS' if result.get('success') else '✗ FAILED'}")
        print(f"{'='*60}")
        
        for key, value in result.items():
            if key not in ['task', 'success']:
                print(f"  {key}: {value}")
    
    return 0 if result.get('success') else 1


if __name__ == '__main__':
    sys.exit(main())
