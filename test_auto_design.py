"""
End-to-end test for the auto-design system.

Tests:
1. LDO auto-design (analytical mode)
2. OTA auto-design
3. Current mirror auto-design
4. Ready-config LDO netlist generation
5. Component registration check
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from simulator.engine.auto_designer import AutoDesigner
from simulator.components.analog_blocks import (
    LDORegulator, BandgapReference, CurrentMirror, OTA,
    VoltageBuffer, LevelShifter, generate_ldo_subcircuit
)


def test_ldo_auto_design():
    """Test LDO auto-design converges to target Vout."""
    print("=" * 60)
    print("TEST 1: LDO Auto-Design")
    print("=" * 60)

    designer = AutoDesigner(max_iterations=20, verbose=True)
    result = designer.design_ldo({
        'vout': 1.2,
        'vin': 3.3,
        'dropout': 0.2,
        'iout_max': 0.1,
        'loop_gain': 60,
        'bandwidth': 1e6,
    })

    print(f"\nResult: {result.message}")
    print(f"Success: {result.success}")
    print(f"Iterations: {len(result.iterations)}")
    print(f"Final measurements:")
    for k, v in result.final_measurements.items():
        print(f"  {k}: {v:.4g}")
    print(f"Design variables:")
    for k, v in result.variables.items():
        print(f"  {k}: {v:.4g}")
    print(f"\nNetlist length: {len(result.netlist)} chars")
    assert result.success, "LDO design should converge"
    assert abs(result.final_measurements.get('vout', 0) - 1.2) < 0.05, \
        f"Vout should be ~1.2V, got {result.final_measurements.get('vout', 0):.4f}"
    print("✓ PASSED\n")
    return True


def test_ota_auto_design():
    """Test OTA auto-design converges to target gain/BW."""
    print("=" * 60)
    print("TEST 2: OTA Auto-Design")
    print("=" * 60)

    designer = AutoDesigner(max_iterations=20, verbose=False)
    result = designer.design_ota({
        'gain': 70,
        'bandwidth': 10e6,
        'ibias': 50e-6,
        'vdd': 1.8,
        'cl': 2e-12,
    })

    print(f"Result: {result.message}")
    print(f"Success: {result.success}")
    print(f"Final: gain={result.final_measurements.get('gain', 0):.1f}dB, "
          f"BW={result.final_measurements.get('bandwidth', 0)/1e6:.1f}MHz")
    assert result.netlist, "Should generate OTA netlist"
    print("✓ PASSED\n")
    return True


def test_current_mirror():
    """Test current mirror auto-design."""
    print("=" * 60)
    print("TEST 3: Current Mirror Auto-Design")
    print("=" * 60)

    designer = AutoDesigner()
    result = designer.design_current_mirror({
        'iref': 10e-6,
        'ratio': 2.0,
        'type': 'nmos',
    })

    print(f"Result: {result.message}")
    print(f"Final: Iout={result.final_measurements.get('iout', 0)*1e6:.1f}uA, "
          f"Rout={result.final_measurements.get('rout', 0)/1e6:.1f}MΩ")
    assert result.success, "Current mirror should always succeed"
    assert abs(result.final_measurements.get('iout', 0) - 20e-6) < 1e-6, \
        "Iout should be 20uA (ratio=2, Iref=10uA)"
    print("✓ PASSED\n")
    return True


def test_ready_config_netlist():
    """Test that the ready-config LDO netlist exists and is valid."""
    print("=" * 60)
    print("TEST 4: Ready-Config LDO Netlist")
    print("=" * 60)

    ldo_path = os.path.join(
        os.path.dirname(__file__),
        "examples", "analog_blocks", "ldo_regulator.spice"
    )
    assert os.path.exists(ldo_path), f"LDO netlist not found at {ldo_path}"

    with open(ldo_path) as f:
        netlist = f.read()

    assert ".MODEL nmos_1v8" in netlist, "Should contain NMOS model"
    assert ".MODEL pmos_1v8" in netlist, "Should contain PMOS model"
    assert "Mpass" in netlist, "Should contain pass transistor"
    assert ".TRAN" in netlist, "Should contain transient analysis"
    assert "R1 vout vfb" in netlist, "Should contain feedback divider"
    print(f"Netlist: {len(netlist)} chars, {netlist.count(chr(10))} lines")
    print("✓ PASSED\n")
    return True


def test_component_classes():
    """Test that all analog block components can be instantiated."""
    print("=" * 60)
    print("TEST 5: Component Class Instantiation")
    print("=" * 60)

    components = [
        (LDORegulator, "LDO Regulator", 4),
        (BandgapReference, "Bandgap Reference", 3),
        (CurrentMirror, "Current Mirror", 4),
        (OTA, "OTA", 5),
        (VoltageBuffer, "Voltage Buffer", 4),
        (LevelShifter, "Level Shifter", 4),
    ]

    for cls, expected_name, expected_pins in components:
        comp = cls()
        assert comp.display_name == expected_name, \
            f"Expected '{expected_name}', got '{comp.display_name}'"
        assert len(comp._pins) == expected_pins, \
            f"{expected_name}: expected {expected_pins} pins, got {len(comp._pins)}"
        assert comp.symbol_path, f"{expected_name}: should have symbol"

        # Set pin nets and test spice model generation
        for pin in comp._pins:
            pin.connected_net = f"net_{pin.name.lower()}"
        spice = comp.get_spice_model()
        assert spice, f"{expected_name}: should generate SPICE model"
        print(f"  ✓ {expected_name}: {len(comp._pins)} pins, "
              f"SPICE: {spice[:60]}...")

    print("✓ PASSED\n")
    return True


def test_subcircuit_generation():
    """Test LDO subcircuit generation from component properties."""
    print("=" * 60)
    print("TEST 6: LDO Subcircuit Generation")
    print("=" * 60)

    ldo = LDORegulator()
    subckt = ldo.generate_subcircuit()
    assert "CMOS LDO Regulator" in subckt
    assert ".MODEL nmos_ldo" in subckt
    assert ".MODEL pmos_ldo" in subckt
    assert "Mpass" in subckt
    assert "R1 vout vfb" in subckt
    print(f"Generated subcircuit: {len(subckt)} chars")
    print("✓ PASSED\n")
    return True


def test_component_registry():
    """Test that analog blocks are registered in the component library."""
    print("=" * 60)
    print("TEST 7: Component Library Registration")
    print("=" * 60)

    from simulator.gui.component_library import COMPONENT_REGISTRY, COMPONENT_CATEGORIES

    expected = [
        'LDORegulator', 'BandgapReference', 'CurrentMirror',
        'OTA', 'VoltageBuffer', 'LevelShifter',
    ]

    for name in expected:
        assert name in COMPONENT_REGISTRY, \
            f"{name} not in COMPONENT_REGISTRY"
        print(f"  ✓ {name} registered")

    assert 'Analog Blocks' in COMPONENT_CATEGORIES, \
        "Analog Blocks category missing"
    ab_names = [name for name, _ in COMPONENT_CATEGORIES['Analog Blocks']]
    assert len(ab_names) == 6, f"Expected 6 analog blocks, got {len(ab_names)}"
    print(f"  ✓ Analog Blocks category: {ab_names}")
    print("✓ PASSED\n")
    return True


def test_generic_design_dispatch():
    """Test the generic design() dispatcher."""
    print("=" * 60)
    print("TEST 8: Generic Design Dispatch")
    print("=" * 60)

    designer = AutoDesigner(max_iterations=5, verbose=False)

    # Valid type
    result = designer.design('ldo', {'vout': 1.5, 'vin': 3.3})
    assert result.netlist, "LDO dispatch should return netlist"
    print(f"  ✓ LDO dispatch: {len(result.netlist)} chars")

    # Invalid type
    result = designer.design('unknown_block', {})
    assert not result.success, "Unknown block should fail"
    assert 'Unknown block type' in result.message
    print(f"  ✓ Unknown block: {result.message}")

    print("✓ PASSED\n")
    return True


def main():
    print("\n" + "=" * 60)
    print("  AMS Simulator — Auto-Design End-to-End Test Suite")
    print("=" * 60 + "\n")

    tests = [
        test_ldo_auto_design,
        test_ota_auto_design,
        test_current_mirror,
        test_ready_config_netlist,
        test_component_classes,
        test_subcircuit_generation,
        test_component_registry,
        test_generic_design_dispatch,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ FAILED: {test.__name__}: {e}\n")
            failed += 1

    print("=" * 60)
    print(f"  Results: {passed} passed, {failed} failed out of {len(tests)}")
    print("=" * 60)
    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
