#!/usr/bin/env python3
"""
Schematic Round-Trip Test
=========================

Tests netlist → schematic → netlist conversion for buck converter.
Validates that the schematic generation is correct and lossless.
"""

import sys
import json
from pathlib import Path

# Add simulator to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from simulator.gui.schematic_editor import SchematicEditor
from simulator.engine.analog_engine import AnalogEngine, TransientAnalysis
import numpy as np


def test_roundtrip():
    """Test complete round-trip: netlist → schematic → netlist → simulate."""
    
    print("="*70)
    print("SCHEMATIC ROUND-TRIP TEST")
    print("="*70)
    
    netlist_path = Path(__file__).parent.parent / 'examples' / 'standard_circuits' / 'buck_converter.spice'
    
    # Step 1: Load original netlist
    print("\n[Step 1] Loading original netlist...")
    with open(netlist_path, 'r', encoding='utf-8') as f:
        original_netlist = f.read()
    print(f"  ✓ Loaded {len(original_netlist)} characters")
    
    # Step 2: Simulate original
    print("\n[Step 2] Simulating original netlist...")
    engine1 = AnalogEngine()
    engine1.load_netlist(original_netlist)
    ta1 = TransientAnalysis(engine1)
    results1 = ta1.run({'tstop': 500e-6, 'tstep': 100e-9})
    
    time1 = np.array(results1['time'])
    vout1 = np.array(results1.get('V(output)', []))
    ss_mask = (time1 >= 400e-6) & (time1 <= 500e-6)
    vout1_avg = float(np.mean(vout1[ss_mask]))
    print(f"  ✓ Original Vout avg: {vout1_avg:.3f}V")
    
    # Step 3: Convert to schematic
    print("\n[Step 3] Converting netlist → schematic...")
    try:
        from PyQt6.QtWidgets import QApplication
        import sys as qtsys
        
        # Create minimal QApplication for SchematicEditor
        app = QApplication.instance()
        if app is None:
            app = QApplication(qtsys.argv)
        
        editor = SchematicEditor()
        editor.load_from_netlist(str(netlist_path))
        
        num_components = len(editor._components)
        num_wires = len(editor._wires)
        print(f"  ✓ Generated schematic: {num_components} components, {num_wires} wires")
        
        # Save schematic
        schematic_path = Path(__file__).parent.parent / 'reports' / 'buck_schematic.json'
        schematic_path.parent.mkdir(exist_ok=True)
        editor.save_schematic(str(schematic_path))
        print(f"  ✓ Saved: {schematic_path}")
        
        # Step 4: Generate netlist from schematic
        print("\n[Step 4] Converting schematic → netlist...")
        regenerated_netlist = editor.generate_netlist()
        print(f"  ✓ Regenerated {len(regenerated_netlist)} characters")
        
        # Save regenerated netlist
        regen_path = Path(__file__).parent.parent / 'reports' / 'buck_regenerated.spice'
        with open(regen_path, 'w', encoding='utf-8') as f:
            f.write(regenerated_netlist)
        print(f"  ✓ Saved: {regen_path}")
        
        # Step 5: Simulate regenerated netlist
        print("\n[Step 5] Simulating regenerated netlist...")
        engine2 = AnalogEngine()
        engine2.load_netlist(regenerated_netlist)
        ta2 = TransientAnalysis(engine2)
        results2 = ta2.run({'tstop': 500e-6, 'tstep': 100e-9})
        
        time2 = np.array(results2['time'])
        vout2 = np.array(results2.get('V(output)', []))
        ss_mask2 = (time2 >= 400e-6) & (time2 <= 500e-6)
        vout2_avg = float(np.mean(vout2[ss_mask2]))
        print(f"  ✓ Regenerated Vout avg: {vout2_avg:.3f}V")
        
        # Step 6: Compare results
        print("\n[Step 6] Comparing results...")
        vout_diff = abs(vout1_avg - vout2_avg)
        vout_diff_pct = (vout_diff / vout1_avg) * 100
        
        print(f"  • Original:    {vout1_avg:.4f}V")
        print(f"  • Regenerated: {vout2_avg:.4f}V")
        print(f"  • Difference:  {vout_diff:.4f}V ({vout_diff_pct:.2f}%)")
        
        # Success criteria: < 5% difference
        tolerance_pct = 5.0
        passed = vout_diff_pct < tolerance_pct
        
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        if passed:
            print(f"✓ ROUND-TRIP TEST PASSED (error {vout_diff_pct:.2f}% < {tolerance_pct}%)")
        else:
            print(f"✗ ROUND-TRIP TEST FAILED (error {vout_diff_pct:.2f}% >= {tolerance_pct}%)")
        
        return {
            'success': passed,
            'original_vout': vout1_avg,
            'regenerated_vout': vout2_avg,
            'error_percent': vout_diff_pct,
            'schematic_path': str(schematic_path),
            'regen_netlist_path': str(regen_path)
        }
        
    except Exception as e:
        import traceback
        print(f"\n✗ Round-trip test failed: {e}")
        print(traceback.format_exc())
        return {'success': False, 'error': str(e)}


def main():
    """Main entry point."""
    results = test_roundtrip()
    return 0 if results.get('success') else 1


if __name__ == '__main__':
    sys.exit(main())
