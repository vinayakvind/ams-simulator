#!/usr/bin/env python3
"""
Schematic-to-Simulation Validation
==================================

Tests complete workflow: Schematic → Generate Netlist → Simulate → Validate
This ensures schematic generation produces correct, simulatable netlists.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from simulator.gui.schematic_editor import SchematicEditor
from simulator.engine.analog_engine import AnalogEngine, TransientAnalysis
from simulator.components.base import Component
import numpy as np


class SchematicNetlistValidator:
    """Validates schematic → netlist → simulation pipeline."""
    
    def __init__(self):
        self.results = {
            'steps': {},
            'validation': {}
        }
    
    def step1_create_buck_schematic(self) -> Dict[str, Any]:
        """Create buck converter schematic programmatically."""
        print("\n[Step 1] Creating Buck Converter Schematic...")
        
        try:
            from PyQt6.QtWidgets import QApplication
            import sys as qtsys
            
            app = QApplication.instance()
            if app is None:
                app = QApplication(qtsys.argv)
            
            editor = SchematicEditor()
            
            # Component positions (grid-based for clarity)
            positions = {
                'Vin': (100, 200),
                'M1': (300, 150),
                'Vgate': (200, 100),
                'D1': (400, 250),
                'L1': (450, 150),
                'C1': (600, 250),
                'Rload': (650, 250),
                'GND1': (150, 300),
                'GND2': (400, 300),
                'GND3': (650, 300)
            }
            
            # Create components
            from simulator.components.sources import VoltageSource, PulseSource
            from simulator.components.transistors import PMOS
            from simulator.components.diodes import Diode
            from simulator.components.passive import Inductor, Capacitor, Resistor
            
            # Input voltage source
            vin = VoltageSource()
            vin.reference = 'Vin'
            vin.set_property('voltage', 12.0)
            vin.x, vin.y = positions['Vin']
            vin.id = 'Vin_1'
            editor._components[vin.id] = vin
            
            # PMOS high-side switch
            m1 = PMOS()
            m1.reference = 'M1'
            m1.set_property('model', 'PMOS_BUCK')
            m1.set_property('w', 20e-6)
            m1.set_property('l', 0.18e-6)
            m1.x, m1.y = positions['M1']
            m1.id = 'M1_1'
            editor._components[m1.id] = m1
            
            # Gate drive (PWM)
            vgate = PulseSource()
            vgate.reference = 'Vgate'
            vgate.set_property('v_low', 0)
            vgate.set_property('v_high', 16)
            vgate.set_property('delay', 0)
            vgate.set_property('rise_time', 10e-9)
            vgate.set_property('fall_time', 10e-9)
            vgate.set_property('pulse_width', 3.274e-6)
            vgate.set_property('period', 10e-6)
            vgate.x, vgate.y = positions['Vgate']
            vgate.id = 'Vgate_1'
            editor._components[vgate.id] = vgate
            
            # Freewheeling diode
            d1 = Diode()
            d1.reference = 'D1'
            d1.set_property('model', 'DFAST')
            d1.x, d1.y = positions['D1']
            d1.id = 'D1_1'
            editor._components[d1.id] = d1
            
            # Output inductor
            l1 = Inductor()
            l1.reference = 'L1'
            l1.set_property('inductance', 100e-6)
            l1.set_property('initial_current', 0.5)
            l1.x, l1.y = positions['L1']
            l1.id = 'L1_1'
            editor._components[l1.id] = l1
            
            # Output capacitor
            c1 = Capacitor()
            c1.reference = 'C1'
            c1.set_property('capacitance', 100e-6)
            c1.set_property('initial_voltage', 5.0)
            c1.x, c1.y = positions['C1']
            c1.id = 'C1_1'
            editor._components[c1.id] = c1
            
            # Load resistor
            rload = Resistor()
            rload.reference = 'Rload'
            rload.set_property('resistance', 5.0)
            rload.x, rload.y = positions['Rload']
            rload.id = 'Rload_1'
            editor._components[rload.id] = rload
            
            print(f"  ✓ Created {len(editor._components)} components")
            
            # Set pin connections (connected_net attribute)
            # Buck topology:
            # Vin+ → M1.S (input node)
            # Vin- → GND
            # M1.D → sw_node → D1.anode → L1+
            # M1.G → Vgate+
            # Vgate- → GND
            # D1.cathode → GND
            # L1- → C1+ → Rload+ (output node)
            # C1- → Rload- → GND
            # M1.B → GND (bulk)
            
            # Define node connections
            # PMOS pins: G=gate, D=drain, S=source, B=bulk
            # Diode pins: 0=anode (+), 1=cathode (-)
            # Two-terminal: 0=+, 1=-
            
            # Node: input (12V rail)
            vin._pins[0].connected_net = 'input'  # Vin+
            m1._pins[2].connected_net = 'input'   # M1 source (PMOS source = input)
            m1._pins[3].connected_net = 'input'   # M1 bulk (tie to source for PMOS)
            
            # Node: sw_node (switching node)
            m1._pins[1].connected_net = 'sw_node'  # M1 drain
            d1._pins[0].connected_net = 'sw_node'  # D1 anode
            l1._pins[0].connected_net = 'sw_node'  # L1+
            
            # Node: gate
            vgate._pins[0].connected_net = 'gate'  # Vgate+
            m1._pins[0].connected_net = 'gate'     # M1 gate
            
            # Node: output
            l1._pins[1].connected_net = 'output'    # L1-
            c1._pins[0].connected_net = 'output'    # C1+
            rload._pins[0].connected_net = 'output' # Rload+
            
            # Node: 0 (ground)
            vin._pins[1].connected_net = '0'     # Vin-
            vgate._pins[1].connected_net = '0'   # Vgate-
            d1._pins[1].connected_net = '0'      # D1 cathode
            c1._pins[1].connected_net = '0'      # C1-
            rload._pins[1].connected_net = '0'   # Rload-
            
            print(f"  ✓ Connected all pins to nodes")
            
            # Save schematic
            schematic_path = Path(__file__).parent.parent / 'reports' / 'buck_from_schematic.json'
            schematic_path.parent.mkdir(exist_ok=True)
            editor.save_to_file(str(schematic_path))
            print(f"  ✓ Saved schematic: {schematic_path}")
            
            return {
                'success': True,
                'num_components': len(editor._components),
                'num_wires': len(editor._wires),
                'schematic_path': str(schematic_path),
                'editor': editor
            }
            
        except Exception as e:
            import traceback
            print(f"  ✗ Failed: {e}")
            print(traceback.format_exc())
            return {'success': False, 'error': str(e)}
    
    def step2_generate_netlist(self, editor: SchematicEditor) -> Dict[str, Any]:
        """Generate SPICE netlist from schematic."""
        print("\n[Step 2] Generating Netlist from Schematic...")
        
        try:
            netlist = editor.generate_netlist()
            
            # Count elements
            lines = netlist.splitlines()
            element_counts = {}
            for line in lines:
                line = line.strip()
                if line and not line.startswith('*') and not line.startswith('.'):
                    prefix = line[0].upper()
                    element_counts[prefix] = element_counts.get(prefix, 0) + 1
            
            print(f"  ✓ Generated netlist ({len(netlist)} chars)")
            print(f"  • Elements: {element_counts}")
            
            # Save netlist
            netlist_path = Path(__file__).parent.parent / 'reports' / 'buck_from_schematic.spice'
            with open(netlist_path, 'w', encoding='utf-8') as f:
                f.write(netlist)
            print(f"  ✓ Saved netlist: {netlist_path}")
            
            # Show key lines
            print("\n  Key netlist lines:")
            for line in lines[:20]:
                if line.strip() and not line.startswith('*'):
                    print(f"    {line}")
            
            return {
                'success': True,
                'netlist': netlist,
                'netlist_path': str(netlist_path),
                'size': len(netlist),
                'element_counts': element_counts
            }
            
        except Exception as e:
            import traceback
            print(f"  ✗ Failed: {e}")
            print(traceback.format_exc())
            return {'success': False, 'error': str(e)}
    
    def step3_simulate_generated_netlist(self, netlist: str) -> Dict[str, Any]:
        """Run transient simulation with generated netlist."""
        print("\n[Step 3] Simulating Generated Netlist...")
        
        try:
            engine = AnalogEngine()
            engine.load_netlist(netlist)
            
            print(f"  • Loaded: {engine._num_nodes} nodes, {len(engine._elements)} elements")
            
            ta = TransientAnalysis(engine)
            results = ta.run({
                'tstop': 500e-6,
                'tstep': 100e-9,
                'tstart': 0,
                'uic': False
            })
            
            time = np.array(results['time'])
            vout = np.array(results.get('V(output)', []))
            vin = np.array(results.get('V(input)', []))
            
            if len(vout) == 0:
                # Try alternative node names
                for key in results.keys():
                    if 'out' in key.lower() and key.startswith('V('):
                        vout = np.array(results[key])
                        print(f"  • Using node: {key}")
                        break
            
            if len(vout) > 0:
                ss_mask = (time >= 400e-6) & (time <= 500e-6)
                
                metrics = {
                    'vin_avg': float(np.mean(vin)) if len(vin) > 0 else 0,
                    'vout_final': float(vout[-1]),
                    'vout_avg_steady': float(np.mean(vout[ss_mask])),
                    'vout_ripple_mv': float((np.max(vout[ss_mask]) - np.min(vout[ss_mask])) * 1000)
                }
                
                print(f"  ✓ Simulation completed")
                print(f"  • Vin avg: {metrics['vin_avg']:.3f}V")
                print(f"  • Vout avg (400-500µs): {metrics['vout_avg_steady']:.3f}V")
                print(f"  • Vout ripple: {metrics['vout_ripple_mv']:.2f}mV")
                
                return {
                    'success': True,
                    'metrics': metrics,
                    'num_points': len(time)
                }
            else:
                print(f"  ✗ No output voltage data found")
                print(f"  Available nodes: {[k for k in results.keys() if k.startswith('V(')]}")
                return {
                    'success': False,
                    'error': 'No V(output) in results',
                    'available_nodes': [k for k in results.keys() if k.startswith('V(')]
                }
            
        except Exception as e:
            import traceback
            print(f"  ✗ Simulation failed: {e}")
            print(traceback.format_exc())
            return {'success': False, 'error': str(e)}
    
    def step4_compare_with_reference(self, generated_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Compare generated netlist results with reference netlist."""
        print("\n[Step 4] Comparing with Reference Netlist...")
        
        try:
            # Load and simulate reference netlist
            ref_path = Path(__file__).parent.parent / 'examples' / 'standard_circuits' / 'buck_converter.spice'
            with open(ref_path, 'r', encoding='utf-8') as f:
                ref_netlist = f.read()
            
            engine = AnalogEngine()
            engine.load_netlist(ref_netlist)
            
            ta = TransientAnalysis(engine)
            results = ta.run({'tstop': 500e-6, 'tstep': 100e-9})
            
            time = np.array(results['time'])
            vout = np.array(results.get('V(output)', []))
            vin = np.array(results.get('V(input)', []))
            ss_mask = (time >= 400e-6) & (time <= 500e-6)
            
            ref_metrics = {
                'vin_avg': float(np.mean(vin)),
                'vout_avg_steady': float(np.mean(vout[ss_mask])),
                'vout_ripple_mv': float((np.max(vout[ss_mask]) - np.min(vout[ss_mask])) * 1000)
            }
            
            print(f"  Reference netlist:")
            print(f"    • Vout avg: {ref_metrics['vout_avg_steady']:.3f}V")
            print(f"    • Vout ripple: {ref_metrics['vout_ripple_mv']:.2f}mV")
            
            print(f"\n  Generated netlist:")
            print(f"    • Vout avg: {generated_metrics['vout_avg_steady']:.3f}V")
            print(f"    • Vout ripple: {generated_metrics['vout_ripple_mv']:.2f}mV")
            
            # Calculate differences
            vout_diff = abs(generated_metrics['vout_avg_steady'] - ref_metrics['vout_avg_steady'])
            vout_diff_pct = (vout_diff / ref_metrics['vout_avg_steady']) * 100
            
            ripple_diff = abs(generated_metrics['vout_ripple_mv'] - ref_metrics['vout_ripple_mv'])
            
            print(f"\n  Differences:")
            print(f"    • Vout: {vout_diff:.4f}V ({vout_diff_pct:.2f}%)")
            print(f"    • Ripple: {ripple_diff:.2f}mV")
            
            # Validation
            tolerance_pct = 10.0
            passed = vout_diff_pct < tolerance_pct
            
            return {
                'success': passed,
                'reference': ref_metrics,
                'generated': generated_metrics,
                'vout_error_pct': vout_diff_pct,
                'ripple_error_mv': ripple_diff,
                'tolerance_pct': tolerance_pct
            }
            
        except Exception as e:
            print(f"  ✗ Comparison failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def run_full_validation(self) -> Dict[str, Any]:
        """Execute complete schematic-to-simulation validation."""
        print("="*70)
        print("SCHEMATIC → NETLIST → SIMULATION VALIDATION")
        print("="*70)
        
        # Step 1: Create schematic
        result = self.step1_create_buck_schematic()
        self.results['steps']['step1_schematic'] = result
        if not result['success']:
            print("\n✗ VALIDATION FAILED: Could not create schematic")
            return self.results
        
        editor = result['editor']
        
        # Step 2: Generate netlist
        result = self.step2_generate_netlist(editor)
        self.results['steps']['step2_netlist'] = result
        if not result['success']:
            print("\n✗ VALIDATION FAILED: Could not generate netlist")
            return self.results
        
        netlist = result['netlist']
        
        # Step 3: Simulate
        result = self.step3_simulate_generated_netlist(netlist)
        self.results['steps']['step3_simulation'] = result
        if not result['success']:
            print("\n✗ VALIDATION FAILED: Simulation failed")
            return self.results
        
        metrics = result['metrics']
        
        # Step 4: Compare
        result = self.step4_compare_with_reference(metrics)
        self.results['steps']['step4_comparison'] = result
        
        # Summary
        print("\n" + "="*70)
        print("VALIDATION SUMMARY")
        print("="*70)
        
        if result['success']:
            print(f"✅ SCHEMATIC → NETLIST → SIMULATION PIPELINE VALIDATED")
            print(f"   Error: {result['vout_error_pct']:.2f}% (< {result['tolerance_pct']:.1f}% tolerance)")
        else:
            if 'vout_error_pct' in result:
                print(f"❌ VALIDATION FAILED")
                print(f"   Error: {result['vout_error_pct']:.2f}% (>= {result['tolerance_pct']:.1f}% tolerance)")
            else:
                print(f"❌ VALIDATION FAILED: {result.get('error', 'Unknown error')}")
        
        self.results['validation'] = result
        return self.results


def main():
    """Main entry point."""
    validator = SchematicNetlistValidator()
    results = validator.run_full_validation()
    
    # Save results
    report_path = Path(__file__).parent.parent / 'reports' / 'schematic_validation_report.json'
    report_path.parent.mkdir(exist_ok=True)
    
    # Convert for JSON
    def convert(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, SchematicEditor):
            return '<SchematicEditor object>'
        elif hasattr(obj, '__dict__'):
            return str(obj)
        return obj
    
    serializable = json.loads(json.dumps(results, default=convert))
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(serializable, f, indent=2)
    
    print(f"\n📄 Report saved: {report_path}")
    
    validation = results.get('validation', {})
    return 0 if validation.get('success') else 1


if __name__ == '__main__':
    sys.exit(main())
