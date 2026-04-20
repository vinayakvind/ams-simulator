"""
Comprehensive Test Suite for AMS Simulator.

Tests all features: imports, components, netlist parsing, schematic loading,
simulation engines, waveform output, toolbar actions, and API server.

Usage:
    python test_all_features.py
"""

import sys
import os
import traceback
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

PASS = "\033[92m✓ PASS\033[0m"
FAIL = "\033[91m✗ FAIL\033[0m"
SKIP = "\033[93m⊘ SKIP\033[0m"

results = {"passed": 0, "failed": 0, "skipped": 0, "details": []}


def test(name: str):
    """Decorator to register a test function."""
    def decorator(func):
        def wrapper():
            try:
                func()
                results["passed"] += 1
                results["details"].append((name, "PASS", ""))
                print(f"  {PASS}  {name}")
            except AssertionError as e:
                results["failed"] += 1
                results["details"].append((name, "FAIL", str(e)))
                print(f"  {FAIL}  {name}: {e}")
            except Exception as e:
                results["failed"] += 1
                tb = traceback.format_exc()
                results["details"].append((name, "FAIL", f"{e}\n{tb}"))
                print(f"  {FAIL}  {name}: {e}")
        wrapper.__test_name__ = name
        return wrapper
    return decorator


# ============================================================
# 1. IMPORT TESTS
# ============================================================
print("\n" + "="*70)
print("1. IMPORT TESTS")
print("="*70)


@test("Import simulator package")
def test_import_simulator():
    import simulator
    assert simulator is not None


@test("Import all component modules")
def test_import_components():
    from simulator.components.passive import Resistor, Capacitor, Inductor, PolarizedCapacitor
    from simulator.components.transistors import NMOS, PMOS, NPN, PNP
    from simulator.components.diodes import Diode, Zener, LED, SchottkyDiode
    from simulator.components.sources import (
        VoltageSource, CurrentSource, PulseSource, SineSource, PWLSource,
        VoltageProbe, CurrentProbe, Ground, VDD
    )
    from simulator.components.amplifiers import OpAmp, Comparator, InstrumentationAmplifier
    from simulator.components.digital import (
        ANDGate, ORGate, NOTGate, NANDGate, NORGate, XORGate, XNORGate,
        Buffer, DFlipFlop, SRLatch, Mux2to1
    )
    assert Resistor is not None


@test("Import engine modules")
def test_import_engines():
    from simulator.engine.analog_engine import AnalogEngine, DCAnalysis, ACAnalysis, TransientAnalysis
    from simulator.engine.digital_engine import DigitalEngine
    from simulator.engine.mixed_signal_engine import MixedSignalEngine
    assert AnalogEngine is not None


@test("Import GUI modules")
def test_import_gui():
    from simulator.gui.main_window import MainWindow, CircuitLibraryDialog
    from simulator.gui.schematic_editor import SchematicEditor, ComponentGraphicsItem, WireGraphicsItem
    from simulator.gui.component_library import ComponentLibrary, COMPONENT_REGISTRY
    from simulator.gui.waveform_viewer import WaveformViewer
    from simulator.gui.simulation_dialog import SimulationDialog
    from simulator.gui.netlist_viewer import NetlistViewer
    from simulator.gui.terminal_widget import TerminalWidget
    from simulator.gui.property_editor import PropertyEditor
    assert MainWindow is not None


@test("Import API server")
def test_import_api():
    from simulator.api.server import SimulatorAPIHandler, start_api_server
    assert start_api_server is not None


@test("Import CLI modules")
def test_import_cli():
    from simulator.cli.runner import main as runner_main
    from simulator.cli.batch import BatchRunner
    assert BatchRunner is not None


test_import_simulator()
test_import_components()
test_import_engines()
test_import_gui()
test_import_api()
test_import_cli()


# ============================================================
# 2. COMPONENT TESTS
# ============================================================
print("\n" + "="*70)
print("2. COMPONENT TESTS")
print("="*70)


@test("Create all passive components")
def test_passive_components():
    from simulator.components.passive import Resistor, Capacitor, Inductor, PolarizedCapacitor
    from simulator.components.base import Component
    Component.reset_counters()
    
    r = Resistor()
    assert r.reference.startswith("R"), f"Resistor ref = {r.reference}"
    assert len(r.pins) == 2
    assert 'resistance' in r.properties
    assert r.get_spice_model() is not None
    
    c = Capacitor()
    assert c.reference.startswith("C"), f"Capacitor ref = {c.reference}"
    assert len(c.pins) == 2
    
    l = Inductor()
    assert l.reference.startswith("L"), f"Inductor ref = {l.reference}"
    assert len(l.pins) == 2
    
    pc = PolarizedCapacitor()
    assert pc.reference.startswith("C"), f"PolarizedCapacitor ref = {pc.reference}"


@test("Create all transistor components")
def test_transistor_components():
    from simulator.components.transistors import NMOS, PMOS, NPN, PNP
    from simulator.components.base import Component
    Component.reset_counters()
    
    n = NMOS()
    assert n.reference.startswith("M"), f"NMOS ref = {n.reference}"
    assert len(n.pins) == 4  # G, D, S, B
    
    p = PMOS()
    assert p.reference.startswith("M"), f"PMOS ref = {p.reference}"
    
    npn = NPN()
    assert npn.reference.startswith("Q"), f"NPN ref = {npn.reference}"
    assert len(npn.pins) == 3  # C, B, E
    
    pnp = PNP()
    assert pnp.reference.startswith("Q"), f"PNP ref = {pnp.reference}"


@test("Create all diode components")
def test_diode_components():
    from simulator.components.diodes import Diode, Zener, LED, SchottkyDiode
    from simulator.components.base import Component
    Component.reset_counters()
    
    d = Diode()
    assert d.reference.startswith("D"), f"Diode ref = {d.reference}"
    assert len(d.pins) == 2  # A, K
    
    z = Zener()
    led = LED()
    sd = SchottkyDiode()
    assert all(x is not None for x in [z, led, sd])


@test("Create all source components")
def test_source_components():
    from simulator.components.sources import (
        VoltageSource, CurrentSource, PulseSource, SineSource, PWLSource,
        Ground, VDD, VoltageProbe, CurrentProbe
    )
    from simulator.components.base import Component
    Component.reset_counters()
    
    vs = VoltageSource()
    assert vs.reference.startswith("V"), f"VoltageSource ref = {vs.reference}"
    assert len(vs.pins) == 2
    
    cs = CurrentSource()
    assert cs.reference.startswith("I"), f"CurrentSource ref = {cs.reference}"
    
    ps = PulseSource()
    ss = SineSource()
    gnd = Ground()
    vdd = VDD()
    vp = VoltageProbe()
    cp = CurrentProbe()
    assert all(x is not None for x in [ps, ss, gnd, vdd, vp, cp])


@test("Create all digital components")
def test_digital_components():
    from simulator.components.digital import (
        ANDGate, ORGate, NOTGate, NANDGate, NORGate, XORGate, XNORGate,
        Buffer, DFlipFlop, SRLatch, Mux2to1
    )
    
    gates = [ANDGate(), ORGate(), NOTGate(), NANDGate(), NORGate(),
             XORGate(), XNORGate(), Buffer(), DFlipFlop(), SRLatch(), Mux2to1()]
    assert len(gates) == 11


@test("Create amplifier components")
def test_amplifier_components():
    from simulator.components.amplifiers import OpAmp, Comparator, InstrumentationAmplifier
    
    op = OpAmp()
    comp = Comparator()
    ia = InstrumentationAmplifier()
    assert all(x is not None for x in [op, comp, ia])


@test("Component serialization round-trip")
def test_component_serialization():
    from simulator.components.passive import Resistor
    
    r = Resistor()
    r.x = 100
    r.y = 200
    r.set_property('resistance', 4700.0)
    r.pins[0].connect('net1')
    r.pins[1].connect('net2')
    
    data = r.to_dict()
    assert data['type'] == 'Resistor'
    assert data['x'] == 100
    assert data['y'] == 200
    
    # Deserialize
    r2 = Resistor.from_dict(data)
    assert r2.x == 100
    assert r2.y == 200
    assert r2.properties['resistance'].value == 4700.0


@test("Component SPICE model output")
def test_spice_model_output():
    from simulator.components.passive import Resistor, Capacitor, Inductor
    from simulator.components.sources import VoltageSource
    
    r = Resistor()
    r.pins[0].connect('in')
    r.pins[1].connect('out')
    spice = r.get_spice_model()
    assert 'in' in spice
    assert 'out' in spice
    
    vs = VoltageSource()
    vs.pins[0].connect('vcc')
    vs.pins[1].connect('0')
    spice = vs.get_spice_model()
    assert 'vcc' in spice


@test("Component property validation")
def test_property_validation():
    from simulator.components.passive import Resistor
    
    r = Resistor()
    ok, msg = r.set_property('resistance', 1000.0)
    assert ok, f"Should accept valid value, got: {msg}"
    
    ok, msg = r.set_property('nonexistent', 0)
    assert not ok, "Should reject unknown property"


@test("Component registry completeness")
def test_component_registry():
    from simulator.gui.component_library import COMPONENT_REGISTRY
    
    expected = [
        'Resistor', 'Capacitor', 'Inductor', 'NMOS', 'PMOS', 'NPN', 'PNP',
        'VoltageSource', 'CurrentSource', 'Diode', 'Ground', 'VDD',
        'OpAmp', 'ANDGate', 'ORGate', 'NOTGate',
    ]
    for name in expected:
        assert name in COMPONENT_REGISTRY, f"{name} not in COMPONENT_REGISTRY"


test_passive_components()
test_transistor_components()
test_diode_components()
test_source_components()
test_digital_components()
test_amplifier_components()
test_component_serialization()
test_spice_model_output()
test_property_validation()
test_component_registry()


# ============================================================
# 3. ENGINE TESTS
# ============================================================
print("\n" + "="*70)
print("3. ENGINE TESTS")
print("="*70)


@test("Analog engine: load RC netlist")
def test_engine_load_netlist():
    from simulator.engine.analog_engine import AnalogEngine
    
    netlist = """
    * RC Test Circuit
    V1 in 0 DC 5
    R1 in out 1k
    C1 out 0 100n
    .END
    """
    engine = AnalogEngine()
    engine.load_netlist(netlist)
    assert len(engine._elements) >= 3


@test("DC Operating Point analysis")
def test_dc_analysis():
    from simulator.engine.analog_engine import AnalogEngine, DCAnalysis
    
    netlist = """
    * Voltage divider
    V1 in 0 DC 10
    R1 in mid 1k
    R2 mid 0 1k
    .END
    """
    engine = AnalogEngine()
    engine.load_netlist(netlist)
    
    dc = DCAnalysis(engine)
    result = dc.run({})
    
    # V(mid) should be ~5V
    assert 'V(mid)' in result, f"Expected V(mid) in results, got: {list(result.keys())}"
    v_mid = result['V(mid)']
    assert abs(v_mid - 5.0) < 0.5, f"V(mid) = {v_mid}, expected ~5.0"


@test("Transient analysis - RC circuit")
def test_transient_analysis():
    from simulator.engine.analog_engine import AnalogEngine, TransientAnalysis
    
    netlist = """
    * RC charging
    V1 in 0 DC 5
    R1 in out 1k
    C1 out 0 1u
    .END
    """
    engine = AnalogEngine()
    engine.load_netlist(netlist)
    
    tran = TransientAnalysis(engine)
    result = tran.run({'tstop': 5e-3, 'tstep': 10e-6})
    
    assert 'time' in result
    assert len(result['time']) > 10
    # Check that some voltage output exists
    voltage_keys = [k for k in result.keys() if k.startswith('V(')]
    assert len(voltage_keys) > 0, f"No voltage results. Keys: {list(result.keys())}"


@test("AC Analysis - frequency response")
def test_ac_analysis():
    from simulator.engine.analog_engine import AnalogEngine, ACAnalysis
    
    netlist = """
    * RC lowpass
    V1 in 0 DC 0 AC 1 0
    R1 in out 1k
    C1 out 0 100n
    .END
    """
    engine = AnalogEngine()
    engine.load_netlist(netlist)
    
    ac = ACAnalysis(engine)
    result = ac.run({
        'variation': 'decade',
        'points': 10,
        'fstart': 10,
        'fstop': 1e6,
    })
    
    assert 'frequency' in result
    assert len(result['frequency']) > 5


@test("Engine with MOSFET netlist")
def test_mosfet_netlist():
    from simulator.engine.analog_engine import AnalogEngine
    
    netlist = """
    * NMOS test
    Vdd vdd 0 DC 5
    Vgs gate 0 DC 2
    M1 vdd gate 0 0 NMOS W=10u L=0.18u
    .MODEL NMOS NMOS (VTO=0.7 KP=110u)
    .END
    """
    engine = AnalogEngine()
    engine.load_netlist(netlist)
    assert len(engine._elements) >= 3


@test("Engine with diode netlist")
def test_diode_netlist():
    from simulator.engine.analog_engine import AnalogEngine
    
    netlist = """
    * Diode circuit
    V1 in 0 DC 5
    R1 in out 1k
    D1 out 0 D1N4148
    .MODEL D1N4148 D (IS=1e-14 RS=0.05)
    .END
    """
    engine = AnalogEngine()
    engine.load_netlist(netlist)
    assert len(engine._elements) >= 3


test_engine_load_netlist()
test_dc_analysis()
test_transient_analysis()
test_ac_analysis()
test_mosfet_netlist()
test_diode_netlist()


# ============================================================
# 4. STANDARD CIRCUITS TESTS
# ============================================================
print("\n" + "="*70)
print("4. STANDARD CIRCUITS TESTS")
print("="*70)

STANDARD_CIRCUITS_DIR = Path(__file__).parent / "examples" / "standard_circuits"


@test("All 11 standard circuits exist")
def test_standard_circuits_exist():
    expected = [
        'buck_converter.spice', 'boost_converter.spice', 'buck_boost_converter.spice',
        'flyback_converter.spice', 'ldo_regulator.spice', 'bandgap_reference.spice',
        'differential_amplifier.spice', 'rc_highpass.spice',
        'sar_adc.spice', 'sigma_delta_adc.spice', 'r2r_dac.spice',
    ]
    for f in expected:
        path = STANDARD_CIRCUITS_DIR / f
        assert path.exists(), f"Missing: {f}"


@test("Standard circuits load in engine (bulk)")
def test_standard_circuits_load():
    from simulator.engine.analog_engine import AnalogEngine
    
    loaded = 0
    for spice_file in STANDARD_CIRCUITS_DIR.glob("*.spice"):
        engine = AnalogEngine()
        netlist = spice_file.read_text()
        engine.load_netlist(netlist)
        assert len(engine._elements) > 0, f"{spice_file.name} has no elements"
        loaded += 1
    
    assert loaded >= 11, f"Only loaded {loaded}/11 circuits"


test_standard_circuits_exist()
test_standard_circuits_load()


# ============================================================
# 5. NETLIST-TO-SCHEMATIC PARSER TESTS
# ============================================================
print("\n" + "="*70)
print("5. NETLIST-TO-SCHEMATIC PARSER TESTS")
print("="*70)


@test("Parse SPICE value strings")
def test_parse_spice_values():
    from simulator.gui.schematic_editor import SchematicEditor
    
    parse = SchematicEditor._parse_spice_value
    
    assert parse('100') == 100.0
    assert parse('1k') == 1000.0
    assert parse('1K') == 1000.0
    assert abs(parse('100u') - 100e-6) < 1e-12
    assert abs(parse('10n') - 10e-9) < 1e-15
    assert abs(parse('47p') - 47e-12) < 1e-18
    assert abs(parse('1MEG') - 1e6) < 1
    assert abs(parse('2.2k') - 2200.0) < 1
    assert abs(parse('4.7u') - 4.7e-6) < 1e-12


@test("Load simple RC netlist to schematic")
def test_load_simple_netlist():
    """Requires QApplication for QGraphicsScene."""
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        from simulator.gui.schematic_editor import SchematicEditor
        
        editor = SchematicEditor()
        netlist = """
        * RC Test
        V1 in 0 DC 5
        R1 in out 1k
        C1 out 0 100n
        .TRAN 1u 1m
        .END
        """
        editor.load_from_netlist(netlist)
        
        assert len(editor._components) >= 3, f"Expected >=3 components, got {len(editor._components)}"
        
        # Check component types
        types = [c.__class__.__name__ for c in editor._components.values()]
        assert 'VoltageSource' in types, f"No VoltageSource found. Types: {types}"
        assert 'Resistor' in types, f"No Resistor found. Types: {types}"
        assert 'Capacitor' in types, f"No Capacitor found. Types: {types}"
        
    except ImportError as e:
        raise AssertionError(f"PyQt6 not available: {e}")


@test("Load buck converter netlist to schematic")
def test_load_buck_converter_schematic():
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        from simulator.gui.schematic_editor import SchematicEditor
        
        editor = SchematicEditor()
        buck_path = STANDARD_CIRCUITS_DIR / "buck_converter.spice"
        netlist = buck_path.read_text()
        
        editor.load_from_netlist(netlist)
        
        # Buck converter has: Vin, M1, Vgate, D1, L1, C1, Rload => 7+ components
        assert len(editor._components) >= 5, \
            f"Expected >=5 components, got {len(editor._components)}"
        
        # Check wires were created
        assert len(editor._wires) >= 1, \
            f"Expected wires, got {len(editor._wires)}"
        
    except ImportError as e:
        raise AssertionError(f"PyQt6 not available: {e}")


@test("Load all standard circuits to schematic")
def test_load_all_standard_circuits():
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        from simulator.gui.schematic_editor import SchematicEditor
        
        loaded = 0
        for spice_file in STANDARD_CIRCUITS_DIR.glob("*.spice"):
            editor = SchematicEditor()
            netlist = spice_file.read_text()
            editor.load_from_netlist(netlist)
            
            assert len(editor._components) >= 1, \
                f"{spice_file.name}: No components created"
            loaded += 1
        
        assert loaded >= 11, f"Only loaded {loaded}/11 circuits"
        
    except ImportError as e:
        raise AssertionError(f"PyQt6 not available: {e}")


test_parse_spice_values()
test_load_simple_netlist()
test_load_buck_converter_schematic()
test_load_all_standard_circuits()


# ============================================================
# 6. GUI WIDGET TESTS (requires QApplication)
# ============================================================
print("\n" + "="*70)
print("6. GUI WIDGET TESTS")
print("="*70)


@test("SchematicEditor: add and remove component")
def test_editor_add_remove():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from simulator.gui.schematic_editor import SchematicEditor
    from simulator.components.passive import Resistor
    
    editor = SchematicEditor()
    r = Resistor()
    r.x = 100
    r.y = 200
    
    editor.add_component(r)
    assert r.id in editor._components
    assert r.id in editor._component_items
    
    editor.remove_component(r.id)
    assert r.id not in editor._components


@test("SchematicEditor: undo/redo")
def test_editor_undo_redo():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from simulator.gui.schematic_editor import SchematicEditor
    from simulator.components.passive import Resistor
    
    editor = SchematicEditor()
    r = Resistor()
    editor.add_component(r)
    
    # Undo should restore to empty
    editor.undo()
    assert len(editor._components) == 0
    
    # Redo should bring it back
    editor.redo()
    assert len(editor._components) == 1


@test("SchematicEditor: select all and delete")
def test_editor_select_delete():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from simulator.gui.schematic_editor import SchematicEditor
    from simulator.components.passive import Resistor, Capacitor
    
    editor = SchematicEditor()
    r = Resistor()
    c = Capacitor()
    editor.add_component(r)
    editor.add_component(c)
    
    assert len(editor._components) == 2
    
    editor.select_all()
    editor.delete_selected()
    assert len(editor._components) == 0


@test("SchematicEditor: generate netlist from components")
def test_editor_generate_netlist():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from simulator.gui.schematic_editor import SchematicEditor
    from simulator.components.passive import Resistor
    from simulator.components.sources import VoltageSource
    
    editor = SchematicEditor()
    
    vs = VoltageSource()
    vs.pins[0].connect('in')
    vs.pins[1].connect('0')
    editor.add_component(vs)
    
    r = Resistor()
    r.pins[0].connect('in')
    r.pins[1].connect('out')
    editor.add_component(r)
    
    netlist = editor.generate_netlist()
    assert 'AMS Simulator Netlist' in netlist
    assert '.END' in netlist


@test("SchematicEditor: save and load JSON round-trip")
def test_editor_save_load():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from simulator.gui.schematic_editor import SchematicEditor
    from simulator.components.passive import Resistor
    import tempfile
    
    editor1 = SchematicEditor()
    r = Resistor()
    r.x = 50
    r.y = 60
    r.set_property('resistance', 4700)
    editor1.add_component(r)
    
    # Save
    with tempfile.NamedTemporaryFile(suffix='.ams', delete=False, mode='w') as f:
        tmpfile = f.name
    editor1.save_to_file(tmpfile)
    
    # Load
    editor2 = SchematicEditor()
    editor2.load_from_file(tmpfile)
    
    assert len(editor2._components) == 1
    comp = list(editor2._components.values())[0]
    assert comp.x == 50
    assert comp.y == 60
    
    os.unlink(tmpfile)


@test("WaveformViewer: display results")
def test_waveform_display():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from simulator.gui.waveform_viewer import WaveformViewer
    import numpy as np
    
    viewer = WaveformViewer()
    t = np.linspace(0, 1e-3, 100)
    results = {
        'type': 'transient',
        'time': t.tolist(),
        'V(out)': (3.3 * (1 - np.exp(-t / 1e-4))).tolist(),
        'V(in)': (5.0 * np.ones_like(t)).tolist(),
    }
    
    viewer.display_results(results)
    assert len(viewer._waveforms) == 2


@test("ComponentLibrary: registry and categories")
def test_component_library():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from simulator.gui.component_library import ComponentLibrary, COMPONENT_CATEGORIES
    
    lib = ComponentLibrary()
    
    # Check tree has items
    assert lib.tree.topLevelItemCount() > 0
    
    # Check all categories exist
    for cat in COMPONENT_CATEGORIES:
        found = False
        for i in range(lib.tree.topLevelItemCount()):
            if lib.tree.topLevelItem(i).text(0) == cat:
                found = True
                break
        assert found, f"Category '{cat}' not in tree"


@test("NetlistViewer: set and get netlist")
def test_netlist_viewer():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from simulator.gui.netlist_viewer import NetlistViewer
    
    viewer = NetlistViewer()
    test_netlist = "* Test\nR1 in out 1k\n.END"
    viewer.set_netlist(test_netlist)
    
    result = viewer.get_netlist()
    assert result == test_netlist


test_editor_add_remove()
test_editor_undo_redo()
test_editor_select_delete()
test_editor_generate_netlist()
test_editor_save_load()
test_waveform_display()
test_component_library()
test_netlist_viewer()


# ============================================================
# 7. TOOLBAR / MAIN WINDOW TESTS
# ============================================================
print("\n" + "="*70)
print("7. TOOLBAR AND MAIN WINDOW TESTS")
print("="*70)


@test("MainWindow: creates successfully")
def test_mainwindow_creation():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from simulator.gui.main_window import MainWindow
    
    window = MainWindow()
    assert window is not None
    assert window.schematic_editor is not None
    assert window.waveform_viewer is not None
    assert window.component_library is not None
    assert window.netlist_viewer is not None
    assert window.terminal_widget is not None


@test("MainWindow: toolbar Run/Stop actions are connected")
def test_toolbar_connections():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from simulator.gui.main_window import MainWindow
    
    window = MainWindow()
    
    # Find the simulation toolbar
    assert hasattr(window, '_run_action'), "No _run_action attribute"
    assert hasattr(window, '_stop_action'), "No _stop_action attribute"
    
    # Check Run action has connected signals
    run_receivers = window._run_action.receivers(window._run_action.triggered)
    assert run_receivers > 0, "Run action has no connected signals"
    
    # Check Stop action has connected signals
    stop_receivers = window._stop_action.receivers(window._stop_action.triggered)
    assert stop_receivers > 0, "Stop action has no connected signals"


@test("MainWindow: load standard circuit creates schematic")
def test_load_circuit_creates_schematic():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from simulator.gui.main_window import MainWindow
    
    window = MainWindow()
    window._load_standard_circuit("rc_highpass.spice")
    
    # Should now have a tab with the circuit name
    editor = window.schematic_editor
    assert len(editor._components) >= 2, \
        f"Expected >=2 components after loading rc_highpass, got {len(editor._components)}"
    
    # Netlist viewer should have content
    netlist = window.netlist_viewer.get_netlist()
    assert len(netlist) > 0, "Netlist viewer is empty after loading circuit"


@test("MainWindow: load and simulate circuit")
def test_load_and_simulate():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from simulator.gui.main_window import MainWindow
    
    window = MainWindow()
    window._load_standard_circuit("rc_highpass.spice", simulate=True)
    
    # Should have waveforms after simulation
    assert len(window.waveform_viewer._waveforms) > 0, \
        "No waveforms after load+simulate"


@test("CircuitLibraryDialog: lists all circuits")
def test_circuit_library_dialog():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from simulator.gui.main_window import CircuitLibraryDialog
    
    dialog = CircuitLibraryDialog()
    
    # Count items (excluding category headers)
    count = 0
    for i in range(dialog.circuit_list.count()):
        item = dialog.circuit_list.item(i)
        if item.data(256):  # Qt.ItemDataRole.UserRole = 256
            count += 1
    
    assert count >= 11, f"Expected >= 11 circuits in dialog, got {count}"


test_mainwindow_creation()
test_toolbar_connections()
test_load_circuit_creates_schematic()
test_load_and_simulate()
test_circuit_library_dialog()


# ============================================================
# 8. API SERVER TESTS
# ============================================================
print("\n" + "="*70)
print("8. API SERVER TESTS")
print("="*70)


@test("API server: start and check status")
def test_api_start():
    import urllib.request
    from simulator.api.server import start_api_server
    
    server = start_api_server(port=5199)
    
    try:
        req = urllib.request.Request('http://127.0.0.1:5199/api/status')
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            assert data['status'] == 'running'
            assert data['simulator'] == 'AMS Simulator'
    finally:
        server.shutdown()


@test("API server: list circuits")
def test_api_list_circuits():
    import urllib.request
    from simulator.api.server import start_api_server
    
    server = start_api_server(port=5198)
    
    try:
        req = urllib.request.Request('http://127.0.0.1:5198/api/circuits')
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            assert data['count'] >= 11
            assert 'circuits' in data
    finally:
        server.shutdown()


@test("API server: headless simulate")
def test_api_headless_simulate():
    import urllib.request
    from simulator.api.server import start_api_server
    
    server = start_api_server(port=5197)
    
    try:
        body = json.dumps({
            'type': 'Transient',
            'netlist': '* Test\nV1 in 0 DC 5\nR1 in out 1k\nC1 out 0 1u\n.END',
            'settings': {'tstop': 5e-3, 'tstep': 50e-6}
        }).encode()
        
        req = urllib.request.Request(
            'http://127.0.0.1:5197/api/simulate',
            data=body,
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            assert data['status'] == 'completed'
    finally:
        server.shutdown()


test_api_start()
test_api_list_circuits()
test_api_headless_simulate()


# ============================================================
# 9. SIMULATION OUTPUT PROOF
# ============================================================
print("\n" + "="*70)
print("9. SIMULATION PROOF: Running real circuits")
print("="*70)


@test("Run voltage divider and verify V(mid) ≈ 5V")
def test_proof_voltage_divider():
    from simulator.engine.analog_engine import AnalogEngine, DCAnalysis
    
    netlist = """
    * Voltage Divider - 10V input, equal resistors
    V1 in 0 DC 10
    R1 in mid 1k
    R2 mid 0 1k
    .END
    """
    engine = AnalogEngine()
    engine.load_netlist(netlist)
    result = DCAnalysis(engine).run({})
    
    v_mid = result['V(mid)']
    assert abs(v_mid - 5.0) < 0.1, f"V(mid) = {v_mid}, expected 5.0V"
    print(f"    → V(mid) = {v_mid:.4f}V ✓")


@test("Run RC transient and verify charging curve")
def test_proof_rc_transient():
    from simulator.engine.analog_engine import AnalogEngine, TransientAnalysis
    import numpy as np
    
    netlist = """
    * RC charging circuit - tau = RC = 1k * 1u = 1ms
    V1 in 0 DC 5
    R1 in out 1k
    C1 out 0 1u
    .END
    """
    engine = AnalogEngine()
    engine.load_netlist(netlist)
    result = TransientAnalysis(engine).run({'tstop': 5e-3, 'tstep': 10e-6})
    
    time = np.array(result['time'])
    v_out = np.array(result.get('V(out)', []))
    
    if len(v_out) == 0:
        # Try alternate key
        for key in result:
            if 'out' in key.lower() and key != 'time':
                v_out = np.array(result[key])
                break
    
    assert len(v_out) > 0, f"No output voltage found. Keys: {list(result.keys())}"
    
    final_v = v_out[-1]
    assert final_v > 4.0, f"Final V(out) = {final_v:.3f}V, expected > 4V (approaching 5V)"
    print(f"    → V(out) final = {final_v:.4f}V (expected ~5V) ✓")


@test("Run AC analysis and verify frequency response")
def test_proof_ac_analysis():
    from simulator.engine.analog_engine import AnalogEngine, ACAnalysis
    
    netlist = """
    * RC low-pass filter, fc = 1/(2π × 1k × 100n) ≈ 1.59kHz
    V1 in 0 DC 0 AC 1 0
    R1 in out 1k
    C1 out 0 100n
    .END
    """
    engine = AnalogEngine()
    engine.load_netlist(netlist)
    result = ACAnalysis(engine).run({
        'variation': 'decade',
        'points': 20,
        'fstart': 10,
        'fstop': 100e3,
    })
    
    assert 'frequency' in result
    assert len(result['frequency']) > 10
    print(f"    → Frequency points: {len(result['frequency'])} ✓")


test_proof_voltage_divider()
test_proof_rc_transient()
test_proof_ac_analysis()


# ============================================================
# SUMMARY
# ============================================================
print("\n" + "="*70)
print("TEST SUMMARY")
print("="*70)

total = results["passed"] + results["failed"] + results["skipped"]
print(f"\n  Total:   {total}")
print(f"  Passed:  {results['passed']}")
print(f"  Failed:  {results['failed']}")
print(f"  Skipped: {results['skipped']}")

if results["failed"] > 0:
    print(f"\n  FAILED TESTS:")
    for name, status, msg in results["details"]:
        if status == "FAIL":
            print(f"    - {name}: {msg[:200]}")

print()
if results["failed"] == 0:
    print("  🎉 ALL TESTS PASSED! 🎉")
else:
    print(f"  ⚠️  {results['failed']} test(s) failed")

print()
sys.exit(0 if results["failed"] == 0 else 1)
