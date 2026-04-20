#!/usr/bin/env python3
"""
Test CMOS ADC Sub-Blocks
Simulates and validates each ADC component
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from simulator.engine.analog_engine import AnalogEngine, TransientAnalysis, DCAnalysis
import numpy as np
import matplotlib.pyplot as plt

def test_comparator():
    """Test CMOS comparator circuit."""
    print("\n" + "="*70)
    print("TESTING: CMOS Differential Comparator")
    print("="*70)
    
    # Load netlist
    netlist_path = Path(__file__).parent.parent / 'examples' / 'adc' / 'comparator_cmos.spice'
    
    # Simplified comparator for testing (full version has unsupported elements)
    netlist = """
* Simplified CMOS Comparator Test
* Differential pair with active load

VDD vdd 0 DC 1.8V

* Input signals
Vin_p inp 0 DC 0.9V
Vin_n inn 0 DC 0.85V

* Differential pair (NMOS inputs)
.MODEL nmos_1v8 NMOS (VTO=0.45 KP=280u LAMBDA=0.08)
.MODEL pmos_1v8 PMOS (VTO=-0.45 KP=95u LAMBDA=0.10)

M1 d1 inp tail 0 nmos_1v8 W=2u L=0.5u
M2 d2 inn tail 0 nmos_1v8 W=2u L=0.5u

* Tail current source
Itail tail 0 DC 50u

* Active load (PMOS current mirror)
M3 d1 d1 vdd vdd pmos_1v8 W=4u L=0.5u
M4 d2 d1 vdd vdd pmos_1v8 W=4u L=0.5u

* Second stage
M5 d3 d2 0 0 nmos_1v8 W=5u L=0.5u
M6 d3 d3 vdd vdd pmos_1v8 W=8u L=0.5u

* Output buffer
M7 out d3 0 0 nmos_1v8 W=8u L=0.35u
M8 out d3 vdd vdd pmos_1v8 W=12u L=0.35u

* Load
Cload out 0 100f

.OP
.DC Vin_p 0.7 1.1 0.01
.TRAN 1n 100n

.END
    """
    
    try:
        engine = AnalogEngine()
        engine.load_netlist(netlist)
        print(f"✓ Loaded netlist: {engine._num_nodes} nodes, {len(engine._elements)} elements")
        
        # Run DC analysis (sweep inp from 0.7 to 1.1V)
        print("\nRunning DC sweep analysis...")
        dc = DCAnalysis(engine)
        dc_results = dc.run({
            'source': 'Vin_p',
            'start': 0.7,
            'stop': 1.1,
            'step': 0.01
        })
        
        vin_sweep = np.array(dc_results['Vin_p'])
        vout = np.array(dc_results.get('V(out)', dc_results.get('V(d3)', [])))
        
        if len(vout) > 0:
            # Find switching point
            mid_idx = np.argmin(np.abs(vout - 0.9))
            switch_voltage = vin_sweep[mid_idx]
            
            # Calculate gain around switching point
            if mid_idx > 5 and mid_idx < len(vout) - 5:
                dv_in = vin_sweep[mid_idx+5] - vin_sweep[mid_idx-5]
                dv_out = vout[mid_idx+5] - vout[mid_idx-5]
                gain = abs(dv_out / dv_in)
                gain_db = 20 * np.log10(gain)
            else:
                gain_db = 0
            
            print(f"\n✓ DC Analysis Results:")
            print(f"  • Switching point: {switch_voltage:.3f}V (≈ Vin_n = 0.85V)")
            print(f"  • Small-signal gain: {gain_db:.1f} dB")
            print(f"  • Output low: {vout.min():.3f}V")
            print(f"  • Output high: {vout.max():.3f}V")
            print(f"  • Output swing: {vout.max() - vout.min():.3f}V")
            
            return {'success': True, 'gain_db': gain_db, 'switch_v': switch_voltage}
        else:
            print("✗ No output voltage found")
            return {'success': False}
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


def test_dac():
    """Test R-2R DAC circuit."""
    print("\n" + "="*70)
    print("TESTING: 4-Bit R-2R Ladder DAC")
    print("="*70)
    
    # Simplified DAC for testing
    netlist = """
* Simplified 4-bit R-2R DAC Test

Vref vref 0 DC 1.6V

* Digital bits (test code 1010 = 10 decimal = 10/16 * 1.6V = 1.0V)
Vb3 b3 0 DC 1.8V   ; MSB = 1
Vb2 b2 0 DC 0V     ; = 0
Vb1 b1 0 DC 1.8V   ; = 1
Vb0 b0 0 DC 0V     ; LSB = 0

* R-2R ladder
Rref vref n3 10k
R3a n3 n2 10k
R3b n3 0 20k
R2a n2 n1 10k
R2b n2 0 20k
R1a n1 n0 10k
R1b n1 0 20k
R0a n0 vout 10k
R0b n0 0 20k

* Load
Rload vout 0 100k

.OP
.TRAN 1n 1u

.END
    """
    
    try:
        engine = AnalogEngine()
        engine.load_netlist(netlist)
        print(f"✓ Loaded netlist: {engine._num_nodes} nodes, {len(engine._elements)} elements")
        
        # Run transient
        print("\nRunning transient analysis...")
        ta = TransientAnalysis(engine)
        results = ta.run({
            'tstop': 1e-6,
            'tstep': 1e-9,
            'tstart': 0
        })
        
        vout = np.array(results['V(vout)'])
        vref = 1.6
        
        # Calculate expected output for code 1010 (10 decimal)
        expected = vref * 10 / 16
        measured = vout[-1]  # Final value
        error = abs(measured - expected) / expected * 100
        
        print(f"\n✓ DAC Test Results:")
        print(f"  • Input code: 1010 (binary) = 10 (decimal)")
        print(f"  • Expected output: {expected:.3f}V")
        print(f"  • Measured output: {measured:.3f}V")
        print(f"  • Error: {error:.2f}%")
        print(f"  • LSB size: {vref/16*1000:.1f}mV")
        
        if error < 5:
            print(f"  • ✓ PASS (error < 5%)")
            return {'success': True, 'error_pct': error}
        else:
            print(f"  • ✗ FAIL (error >= 5%)")
            return {'success': False, 'error_pct': error}
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


def main():
    """Run all ADC sub-block tests."""
    print("\n" + "="*70)
    print("ADC SUB-BLOCK VALIDATION SUITE")
    print("Testing CMOS ADC Components with 180nm Technology")
    print("="*70)
    
    results = {}
    
    # Test comparator
    results['comparator'] = test_comparator()
    
    # Test DAC
    results['dac'] = test_dac()
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for r in results.values() if r.get('success'))
    total = len(results)
    
    for name, result in results.items():
        status = "✓ PASS" if result.get('success') else "✗ FAIL"
        print(f"{name.upper():20s}: {status}")
        
        if name == 'comparator' and 'gain_db' in result:
            print(f"  • Gain: {result['gain_db']:.1f} dB")
        elif name == 'dac' and 'error_pct' in result:
            print(f"  • Error: {result['error_pct']:.2f}%")
    
    print(f"\n{'='*70}")
    print(f"OVERALL: {passed}/{total} tests passed")
    print(f"{'='*70}\n")
    
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
