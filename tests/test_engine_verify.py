"""Quick test: verify the simulation engine works for analog and digital."""
import sys
sys.path.insert(0, ".")

from simulator.engine.analog_engine import AnalogEngine, DCAnalysis, TransientAnalysis, ACAnalysis

def test_resistor_divider():
    print("TEST 1 - Resistor divider (DC):")
    engine = AnalogEngine()
    netlist = """
V1 vdd 0 DC 3.3
R1 vdd out 10k
R2 out 0 10k
.end
"""
    engine.load_netlist(netlist)
    result = engine.solve_dc()
    for k, v in sorted(result.items()):
        print(f"  {k} = {v:.4f}")
    vout = result.get("V(out)", 0)
    ok = abs(vout - 1.65) < 0.01
    print(f"  Expected=1.65  Got={vout:.4f}  PASS={ok}")
    return ok

def test_mosfet_dc():
    print("\nTEST 2 - NMOS common source (DC with NR):")
    engine = AnalogEngine()
    netlist = """
.MODEL NMOS1 NMOS (VTO=0.5 KP=120u LAMBDA=0.01)
V1 vdd 0 DC 3.3
V2 gate 0 DC 1.5
R1 vdd drain 5k
M1 drain gate 0 0 NMOS1 W=10u L=1u
.end
"""
    engine.load_netlist(netlist)
    result = engine.solve_dc()
    for k, v in sorted(result.items()):
        print(f"  {k} = {v:.4f}")
    vd = result.get("V(drain)", -1)
    ok = 0 < vd < 3.3
    print(f"  V(drain)={vd:.4f} in (0, 3.3)  PASS={ok}")
    return ok

def test_rc_transient():
    print("\nTEST 3 - RC transient:")
    engine = AnalogEngine()
    netlist = """
V1 vin 0 PULSE(0 3.3 0 1n 1n 5u 10u)
R1 vin out 10k
C1 out 0 100p
.end
"""
    engine.load_netlist(netlist)
    tran = TransientAnalysis(engine)
    result = tran.run({"tstop": 2e-6, "tstep": 10e-9})
    vout = result.get("V(out)", [])
    print(f"  Time points: {len(result['time'])}")
    if vout:
        print(f"  V(out) range: {min(vout):.4f} to {max(vout):.4f}")
        ok = max(vout) > 2.0
        print(f"  PASS={ok}")
        return ok
    print("  FAIL - no output")
    return False

def test_bandgap_dc():
    print("\nTEST 4 - Bandgap reference (multi-transistor DC):")
    engine = AnalogEngine()
    netlist = """
* Simple bandgap test
.MODEL NMOS_3P3 NMOS (VTO=0.5 KP=120u LAMBDA=0.01)
.MODEL PMOS_3P3 PMOS (VTO=-0.5 KP=40u LAMBDA=0.01)

V1 VDD 0 DC 3.3
V_EN EN 0 DC 3.3

* PMOS current mirror
M_P1 n_c1 n_bp VDD VDD PMOS_3P3 W=20u L=2u
M_P2 n_c2 n_bp VDD VDD PMOS_3P3 W=20u L=2u
M_P3 n_bp n_bp VDD VDD PMOS_3P3 W=20u L=2u

* Bias resistor
R_BIAS n_bp 0 100k

* Load resistors (modeling BJTs as resistors for test)
R1 n_c1 0 50k
R2 n_c2 0 50k

* Output
R_OUT n_c1 VREF 10k
R_REF VREF 0 100k

.end
"""
    engine.load_netlist(netlist)
    result = engine.solve_dc()
    for k, v in sorted(result.items()):
        if "V(" in k:
            print(f"  {k} = {v:.4f}")
    vref = result.get("V(VREF)", result.get("V(vref)", 0))
    ok = vref > 0
    print(f"  VREF={vref:.4f}  PASS={ok}")
    return ok

def test_ldo_dc():
    print("\nTEST 5 - PMOS pass transistor + CMOS inverter (regulated output):")
    engine = AnalogEngine()
    netlist = """
.MODEL NMOS_3P3 NMOS (VTO=0.5 KP=120u LAMBDA=0.01)
.MODEL PMOS_3P3 PMOS (VTO=-0.5 KP=40u LAMBDA=0.01)

* Supply
V_VIN VIN 0 DC 5.0
V_CTRL CTRL 0 DC 3.0

* PMOS pass transistor: gate forced to 3V, source=5V, so Vgs=-2V
M_PASS VOUT CTRL VIN VIN PMOS_3P3 W=200u L=1u

* Load
R_LOAD VOUT 0 1k

* CMOS inverter as buffer
M_INV_P INV_OUT VOUT VIN VIN PMOS_3P3 W=20u L=1u
M_INV_N INV_OUT VOUT 0 0 NMOS_3P3 W=10u L=1u
R_INV INV_OUT 0 100k

.end
"""
    engine.load_netlist(netlist)
    result = engine.solve_dc()
    for k, v in sorted(result.items()):
        if "V(" in k:
            print(f"  {k} = {v:.4f}")
    vout = result.get("V(VOUT)", result.get("V(vout)", 0))
    inv_out = result.get("V(INV_OUT)", result.get("V(inv_out)", 0))
    ok = 3.0 < vout < 5.0 and inv_out > -0.1
    print(f"  VOUT={vout:.4f}  INV_OUT={inv_out:.4f}  PASS={ok}")
    return ok

def test_digital():
    print("\nTEST 6 - Digital simulation:")
    from simulator.engine.digital_engine import DigitalEngine, LogicValue
    engine = DigitalEngine()
    verilog = """
module test_logic(input a, input b, output y);
    and g1(y, a, b);
endmodule
"""
    engine.load_verilog(verilog)
    engine.set_signal("a", LogicValue.LOGIC_1)
    engine.set_signal("b", LogicValue.LOGIC_1)
    engine.run(max_time=10)
    y_sig = engine.get_signal("y")
    y_val = y_sig.value if y_sig else LogicValue.LOGIC_X
    print(f"  a=1, b=1 => y={y_val}")
    ok1 = (y_val == LogicValue.LOGIC_1)

    engine.set_signal("a", LogicValue.LOGIC_0)
    engine.run(max_time=20)
    y_sig = engine.get_signal("y")
    y_val = y_sig.value if y_sig else LogicValue.LOGIC_X
    print(f"  a=0, b=1 => y={y_val}")
    ok2 = (y_val == LogicValue.LOGIC_0)
    
    ok = ok1 and ok2
    print(f"  PASS={ok}")
    return ok

if __name__ == "__main__":
    results = []
    results.append(("Resistor Divider", test_resistor_divider()))
    results.append(("MOSFET DC", test_mosfet_dc()))
    results.append(("RC Transient", test_rc_transient()))
    results.append(("Bandgap DC", test_bandgap_dc()))
    results.append(("LDO DC", test_ldo_dc()))
    results.append(("Digital Logic", test_digital()))

    print("\n" + "="*50)
    print("SUMMARY:")
    all_pass = True
    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        print(f"  {name:25s} {status}")
        if not ok:
            all_pass = False
    print(f"\nOverall: {'ALL PASS' if all_pass else 'SOME FAILURES'}")
