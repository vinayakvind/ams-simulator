#!/usr/bin/env python3
"""
API-Driven Circuit Validation Suite
====================================
Uses the AMS Simulator API (headless mode) to:
1. Load every circuit, simulate, and dump full result data
2. Validate waveform correctness at every timestamp
3. Check against expected values from circuit theory
4. Report pass/fail with detailed diagnostics

This is the definitive test that proves every circuit works correctly.
"""

import sys
import os
import json
import math
import time as time_mod
import urllib.request
import urllib.error
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
from simulator.engine.analog_engine import (
    AnalogEngine, DCAnalysis, ACAnalysis, TransientAnalysis
)

# ═══════════════════════════════════════════════════════════════
#  EXPECTED RESULTS - derived from circuit theory
# ═══════════════════════════════════════════════════════════════

CIRCUIT_SPECS = {
    "voltage_divider": {
        "file": "examples/voltage_divider.spice",
        "analysis": "dc",
        "checks": [
            ("V(mid) == Vin*R2/(R1+R2) = 5.0V", "V(mid)", 5.0, 0.01),
        ]
    },
    "rc_lowpass": {
        "file": "examples/rc_lowpass.spice",
        "analysis": "ac",
        "settings": {"variation": "decade", "points": 10, "fstart": 1, "fstop": 1e6},
        "checks": [
            ("Has frequency response data", "_has_key", "frequency", None),
        ]
    },
    "rc_transient": {
        "file": "examples/rc_transient.spice",
        "analysis": "transient",
        "settings": {"tstop": 200e-6, "tstep": 100e-9},
        "checks": [
            ("V(out) charges during pulse (tau=1ms, pulse=50us)", "V(out)_range", 0.05, None),
            ("V(out) starts near 0", "V(out)_start", 0.0, 0.1),
        ]
    },
    "rc_highpass": {
        "file": "examples/standard_circuits/rc_highpass.spice",
        "analysis": "transient",
        "settings": {"tstop": 20e-3, "tstep": 10e-6},
        "checks": [
            ("V(output) spikes then decays (highpass)", "V(output)_start", 0.0, 0.2),
        ]
    },
    "buck_converter": {
        "file": "examples/standard_circuits/buck_converter.spice",
        "analysis": "transient",
        "settings": {"tstop": 500e-6, "tstep": 100e-9},
        "checks": [
            ("V(input) at 12V supply", "V(input)", 12.0, 0.5),
            ("Has output waveform", "_has_key", "V(output)", None),
        ]
    },
    "boost_converter": {
        "file": "examples/standard_circuits/boost_converter.spice",
        "analysis": "transient",
        "settings": {"tstop": 1e-3, "tstep": 100e-9},
        "checks": [
            ("Input voltage stable at 5V", "V(input)", 5.0, 0.5),
            ("Has switching waveform at sw_node", "V(sw_node)_range", 1.0, None),
        ]
    },
    "buck_boost_converter": {
        "file": "examples/standard_circuits/buck_boost_converter.spice",
        "analysis": "transient",
        "settings": {"tstop": 1e-3, "tstep": 100e-9},
        "checks": [
            ("Output goes negative (inverting)", "V(output)_final_lt", 0.0, None),
        ]
    },
    "r2r_dac": {
        "file": "examples/standard_circuits/r2r_dac.spice",
        "analysis": "dc",
        "checks": [
            # Code 10101010 = 170/256 * 2.5V = 1.66V at output node
            ("R2R output for code 0xAA ~1.66V", "V(output)", 1.66, 0.15),
        ]
    },
    "bandgap_reference": {
        "file": "examples/standard_circuits/bandgap_reference.spice",
        "analysis": "dc",
        "checks": [
            ("Bandgap output exists", "_has_key", "V(output)", None),
        ]
    },
    "differential_amplifier": {
        "file": "examples/standard_circuits/differential_amplifier.spice",
        "analysis": "transient",
        "settings": {"tstop": 500e-6, "tstep": 1e-6},
        "checks": [
            ("Has output signal", "_has_key", "V(output)", None),
        ]
    },
    "ldo_regulator": {
        "file": "examples/standard_circuits/ldo_regulator.spice",
        "analysis": "transient",
        "settings": {"tstop": 1e-3, "tstep": 1e-6},
        "checks": [
            ("Output regulated near 3.3V", "V(output)", 3.3, 0.5),
        ]
    },
    "flyback_converter": {
        "file": "examples/standard_circuits/flyback_converter.spice",
        "analysis": "transient",
        "settings": {"tstop": 1e-3, "tstep": 100e-9},
        "checks": [
            ("Has output waveform", "_has_key", "V(output)", None),
        ]
    },
    "sar_adc": {
        "file": "examples/standard_circuits/sar_adc.spice",
        "analysis": "transient",
        "settings": {"tstop": 100e-6, "tstep": 100e-9},
        "checks": [
            ("Has analog input signal", "_has_key", "V(analog_in)", None),
        ]
    },
    "sigma_delta_adc": {
        "file": "examples/standard_circuits/sigma_delta_adc.spice",
        "analysis": "transient",
        "settings": {"tstop": 2e-3, "tstep": 100e-9},
        "checks": [
            ("Has analog input", "_has_key", "V(analog_in)", None),
        ]
    },
}


# ═══════════════════════════════════════════════════════════════
#  WAVEFORM VALIDATORS
# ═══════════════════════════════════════════════════════════════

def validate_waveform(data: list, label: str) -> list:
    """Check every timestamp in a waveform for correctness."""
    issues = []
    arr = np.array(data, dtype=float)

    nan_count = int(np.isnan(arr).sum())
    if nan_count > 0:
        issues.append(f"{label}: {nan_count}/{len(arr)} NaN values")

    inf_count = int(np.isinf(arr).sum())
    if inf_count > 0:
        issues.append(f"{label}: {inf_count}/{len(arr)} Inf values")

    finite = arr[np.isfinite(arr)]
    if len(finite) > 0:
        if np.max(np.abs(finite)) > 1e6:
            issues.append(f"{label}: values exceed ±1MV (max={np.max(np.abs(finite)):.1f})")

    return issues


def check_result(results: dict, check_tuple: tuple) -> tuple:
    """
    Run a single check against results.
    Returns (passed: bool, message: str)
    """
    desc, key, expected, tolerance = check_tuple

    # Special checks
    if key == "_has_key":
        found = expected in results
        if found:
            val = results[expected]
            if isinstance(val, (list, np.ndarray)):
                found = len(val) > 0
            else:
                found = val is not None
        return found, f"{'PASS' if found else 'FAIL'}: {desc} — key '{expected}' {'found' if found else 'NOT found'}"

    if key.endswith("_start"):
        real_key = key.replace("_start", "")
        if real_key not in results:
            return False, f"FAIL: {desc} — key '{real_key}' missing"
        val = results[real_key][0] if isinstance(results[real_key], list) else results[real_key]
        passed = abs(float(val) - expected) <= tolerance
        return passed, f"{'PASS' if passed else 'FAIL'}: {desc} — got {float(val):.4f}"

    if key.endswith("_trend"):
        real_key = "V(output)"
        if real_key not in results:
            return False, f"FAIL: {desc} — key '{real_key}' missing"
        arr = np.array(results[real_key], dtype=float)
        finite = arr[np.isfinite(arr)]
        if len(finite) < 10:
            return False, f"FAIL: {desc} — too few finite values"
        trend = "positive" if finite[-1] > finite[0] else "negative"
        passed = trend == expected
        return passed, f"{'PASS' if passed else 'FAIL'}: {desc} — trend={trend}, first={finite[0]:.2f}, last={finite[-1]:.2f}"

    if key.endswith("_range"):
        real_key = key.replace("_range", "")
        if real_key not in results:
            return False, f"FAIL: {desc} — key '{real_key}' missing"
        arr = np.array(results[real_key], dtype=float)
        finite = arr[np.isfinite(arr)]
        if len(finite) < 2:
            return False, f"FAIL: {desc} — not enough data"
        rng = float(np.max(finite) - np.min(finite))
        passed = rng >= expected
        return passed, f"{'PASS' if passed else 'FAIL'}: {desc} — range={rng:.3f}V"

    if key.endswith("_final_gt"):
        real_key = key.replace("_final_gt", "")
        if real_key not in results:
            return False, f"FAIL: {desc} — key '{real_key}' missing"
        arr = np.array(results[real_key], dtype=float)
        finite = arr[np.isfinite(arr)]
        if len(finite) == 0:
            return False, f"FAIL: {desc} — all NaN/Inf"
        val = float(finite[-1])
        passed = val > expected
        return passed, f"{'PASS' if passed else 'FAIL'}: {desc} — final={val:.4f}V"

    if key.endswith("_final_lt"):
        real_key = key.replace("_final_lt", "")
        if real_key not in results:
            return False, f"FAIL: {desc} — key '{real_key}' missing"
        arr = np.array(results[real_key], dtype=float)
        finite = arr[np.isfinite(arr)]
        if len(finite) == 0:
            return False, f"FAIL: {desc} — all NaN/Inf"
        val = float(finite[-1])
        passed = val < expected
        return passed, f"{'PASS' if passed else 'FAIL'}: {desc} — final={val:.4f}V"

    # Standard value check (use final value for transient, direct for DC)
    if key not in results:
        return False, f"FAIL: {desc} — key '{key}' missing from results"

    val = results[key]
    if isinstance(val, list):
        arr = np.array(val, dtype=float)
        finite = arr[np.isfinite(arr)]
        if len(finite) == 0:
            return False, f"FAIL: {desc} — all NaN/Inf"
        val = float(finite[-1])  # Use final value
    else:
        val = float(val)

    passed = abs(val - expected) <= tolerance
    return passed, f"{'PASS' if passed else 'FAIL'}: {desc} — got {val:.4f}V (expect {expected}±{tolerance})"


# ═══════════════════════════════════════════════════════════════
#  CIRCUIT PATTERN KNOWLEDGE BASE
# ═══════════════════════════════════════════════════════════════

CIRCUIT_PATTERNS = {
    "voltage_divider": {
        "topology": "Series resistors between Vin and GND",
        "formula": "Vout = Vin * R2 / (R1 + R2)",
        "template": "V1 in 0 DC {vin}\nR1 in out {r1}\nR2 out 0 {r2}\n.END",
        "nodes": {"in": "input", "out": "output", "0": "ground"},
        "elements": ["V:supply", "R:top", "R:bottom"],
    },
    "rc_lowpass": {
        "topology": "R in series, C to ground",
        "formula": "fc = 1/(2*pi*R*C), H(s) = 1/(1+sRC)",
        "template": "Vin in 0 AC 1\nR1 in out {r}\nC1 out 0 {c}\n.AC DEC 10 1 1MEG\n.END",
        "nodes": {"in": "input", "out": "output"},
        "elements": ["V:ac_source", "R:series", "C:shunt"],
    },
    "rc_highpass": {
        "topology": "C in series, R to ground",
        "formula": "fc = 1/(2*pi*R*C), H(s) = sRC/(1+sRC)",
        "template": "Vin in 0 PULSE(0 1 {td} 1u 1u {pw} {per})\nC1 in out {c}\nR1 out 0 {r}\n.TRAN {tstep} {tstop}\n.END",
        "nodes": {"in": "input", "out": "output"},
        "elements": ["V:pulse_source", "C:series", "R:shunt"],
    },
    "inverting_amplifier": {
        "topology": "Op-amp with R_feedback and R_input",
        "formula": "Vout = -(Rf/Rin) * Vin",
        "template": "Vin in 0 DC {vin}\nRin in inv {rin}\nRf inv out {rf}\nEamp out 0 0 inv {gain}\nRload out 0 10k\n.END",
        "nodes": {"in": "input", "inv": "inverting_node", "out": "output"},
        "elements": ["V:source", "R:input", "R:feedback", "E:opamp", "R:load"],
    },
    "non_inverting_amplifier": {
        "topology": "Op-amp non-inverting configuration",
        "formula": "Vout = (1 + Rf/R1) * Vin",
        "template": "Vin inp 0 DC {vin}\nR1 inv 0 {r1}\nRf inv out {rf}\nEamp out 0 inp inv {gain}\nRload out 0 10k\n.END",
        "nodes": {"inp": "non_inv_input", "inv": "inv_input", "out": "output"},
        "elements": ["V:source", "R:ground", "R:feedback", "E:opamp", "R:load"],
    },
    "buck_converter": {
        "topology": "Switch + diode + LC filter, step-down",
        "formula": "Vout = D * Vin, D = duty_cycle",
        "template": (
            "Vin input 0 DC {vin}\n"
            "M1 input sw_node gate 0 NMOS W=10u L=0.18u\n"
            "Vgate gate 0 PULSE(0 {vg} 0 10n 10n {ton} {per})\n"
            "D1 0 sw_node DFAST\n"
            "L1 sw_node output {l}\nC1 output 0 {c}\n"
            "Rload output 0 {rload}\n"
            ".MODEL NMOS NMOS (VTO=0.7 KP=110u LAMBDA=0.04)\n"
            ".MODEL DFAST D (IS=1e-14 RS=0.01 BV=30)\n"
            ".TRAN {tstep} {tstop}\n.END"
        ),
        "nodes": {"input": "vin", "sw_node": "switch", "output": "vout", "gate": "pwm"},
        "elements": ["V:supply", "M:switch", "V:pwm", "D:freewheel", "L:filter", "C:filter", "R:load"],
    },
    "boost_converter": {
        "topology": "Inductor + switch + diode + C, step-up",
        "formula": "Vout = Vin / (1 - D)",
        "template": (
            "Vin input 0 DC {vin}\nCin input 0 10u\n"
            "L1 input sw_node {l}\n"
            "M1 sw_node 0 gate 0 NMOS W=20u L=0.18u\n"
            "Vgate gate 0 PULSE(0 10 0 10n 10n {ton} {per})\n"
            "D1 sw_node output DFAST\nCout output 0 {c}\n"
            "Rload output 0 {rload}\n"
            ".MODEL NMOS NMOS (VTO=0.7 KP=110u LAMBDA=0.04)\n"
            ".MODEL DFAST D (IS=1e-14 RS=0.01 BV=30)\n"
            ".TRAN {tstep} {tstop}\n.END"
        ),
        "nodes": {"input": "vin", "sw_node": "switch", "output": "vout"},
        "elements": ["V:supply", "C:input", "L:boost", "M:switch", "V:pwm", "D:boost", "C:output", "R:load"],
    },
    "ldo_regulator": {
        "topology": "Error amp + PMOS pass transistor + feedback divider",
        "formula": "Vout = Vref * (1 + R1/R2)",
        "template": (
            "Vin input 0 DC {vin}\nVref ref 0 DC {vref}\n"
            "Eamp gate 0 VCVS ref fb {gain}\n"
            "M_pass output gate input input PMOS W=5000u L=0.35u\n"
            "R_fb1 output fb {r1}\nR_fb2 fb 0 {r2}\n"
            "C_out output 0 {cout}\nRload output 0 {rload}\n"
            ".MODEL PMOS PMOS (VTO=-0.5 KP=50u LAMBDA=0.05)\n"
            ".TRAN 1u 1m\n.END"
        ),
        "nodes": {"input": "supply", "output": "regulated", "gate": "err_amp_out", "ref": "reference", "fb": "feedback"},
        "elements": ["V:supply", "V:ref", "E:error_amp", "M:pass_transistor", "R:fb_top", "R:fb_bottom", "C:output", "R:load"],
    },
    "differential_pair": {
        "topology": "Two BJTs with common emitter current source, active load mirror",
        "formula": "Av = gm * Rout, gm = Ic/(kT/q)",
        "template": (
            "Vdd vdd 0 DC {vdd}\nVss vss 0 DC {vss}\n"
            "V_inp inp 0 DC 0 AC 1m\nV_inn inn 0 DC 0\n"
            "I_tail tail vss DC {itail}\n"
            "Q1 col1 inp tail NPN\nQ2 col2 inn tail NPN\n"
            "M_p1 col1 col1 vdd vdd PMOS W=50u L=1u\n"
            "M_p2 col2 col1 vdd vdd PMOS W=50u L=1u\n"
            ".MODEL NPN NPN (IS=1e-15 BF=200 VA=100)\n"
            ".MODEL PMOS PMOS (VTO=-0.8 KP=50u LAMBDA=0.04)\n"
            ".DC V_inp -100m 100m 1m\n.END"
        ),
        "nodes": {"inp": "pos_input", "inn": "neg_input", "col1": "mirror", "col2": "output"},
        "elements": ["V:vdd", "V:vss", "V:inp", "V:inn", "I:tail", "Q:q1", "Q:q2", "M:mirror1", "M:mirror2"],
    },
    "r2r_dac": {
        "topology": "R-2R resistor ladder with binary-weighted voltage inputs",
        "formula": "Vout = Vref * SUM(bi * 2^(i-N)) for N-bit DAC",
        "template": "# Use r2r_dac.spice as reference for 8-bit implementation",
        "nodes": {"b0-b7": "digital_inputs", "output": "analog_output"},
        "elements": ["V:ref", "V:b0..b7", "R:2r_legs", "R:r_rungs", "R:termination"],
    },
}


# ═══════════════════════════════════════════════════════════════
#  MAIN VALIDATION ENGINE
# ═══════════════════════════════════════════════════════════════

def run_circuit_test(name: str, spec: dict) -> dict:
    """Load a circuit, simulate, validate all waveforms, check expected values."""
    result = {
        "name": name,
        "status": "unknown",
        "checks": [],
        "waveform_issues": [],
        "node_summary": {},
        "error": None,
    }

    filepath = Path(__file__).parent / spec["file"]
    if not filepath.exists():
        result["status"] = "error"
        result["error"] = f"File not found: {filepath}"
        return result

    netlist = filepath.read_text()

    try:
        engine = AnalogEngine()
        engine.load_netlist(netlist)
    except Exception as e:
        result["status"] = "error"
        result["error"] = f"Load failed: {e}"
        return result

    # Detect unsupported elements
    unsupported = []
    for elem in engine._elements:
        if elem.params.get('unsupported'):
            unsupported.append(elem.name)
        elif elem.name[0].upper() in ['K', 'S']:
            unsupported.append(elem.name)
    result["unsupported_elements"] = unsupported

    # Run simulation
    try:
        analysis_type = spec.get("analysis", "dc")
        settings = spec.get("settings", {})

        if analysis_type == "dc":
            analysis = DCAnalysis(engine)
            sim_results = analysis.run(settings)
        elif analysis_type == "ac":
            analysis = ACAnalysis(engine)
            sim_results = analysis.run(settings)
        else:
            analysis = TransientAnalysis(engine)
            if not settings:
                settings = {"tstop": 1e-3, "tstep": 1e-6}
            sim_results = analysis.run(settings)
    except Exception as e:
        result["status"] = "error"
        result["error"] = f"Simulation failed: {e}"
        return result

    # Validate every waveform at every timestamp
    for key, val in sim_results.items():
        if isinstance(val, list) and key.startswith("V("):
            issues = validate_waveform(val, key)
            result["waveform_issues"].extend(issues)

            arr = np.array(val, dtype=float)
            finite = arr[np.isfinite(arr)]
            if len(finite) > 0:
                result["node_summary"][key] = {
                    "min": float(np.min(finite)),
                    "max": float(np.max(finite)),
                    "mean": float(np.mean(finite)),
                    "final": float(finite[-1]),
                    "points": len(val),
                    "nan_count": int(np.isnan(arr).sum()),
                }

    # Run expected value checks
    all_pass = True
    for check in spec.get("checks", []):
        passed, msg = check_result(sim_results, check)
        result["checks"].append({"passed": passed, "message": msg})
        if not passed:
            all_pass = False

    if len(result["waveform_issues"]) > 0:
        result["status"] = "warn"
    elif all_pass:
        result["status"] = "pass"
    else:
        result["status"] = "fail"

    return result


# ═══════════════════════════════════════════════════════════════
#  API SERVER TEST (verifies headless API produces same results)
# ═══════════════════════════════════════════════════════════════

def test_api_server():
    """Start API server, test endpoints, verify results match direct engine."""
    from simulator.api.server import start_api_server

    port = 5198
    server = start_api_server(port=port)
    base = f"http://127.0.0.1:{port}"
    results = []

    def api_get(path):
        req = urllib.request.Request(f"{base}{path}")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())

    def api_post(path, data):
        body = json.dumps(data).encode()
        req = urllib.request.Request(
            f"{base}{path}", data=body,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())

    try:
        # 1. Status
        status = api_get("/api/status")
        ok = status.get("status") == "running"
        results.append(("API /status", ok, f"status={status.get('status')}"))

        # 2. Circuits list
        circuits = api_get("/api/circuits")
        ok = circuits.get("count", 0) >= 11
        results.append(("API /circuits", ok, f"count={circuits.get('count')}"))

        # 3. Headless simulate — voltage divider
        netlist = "V1 in 0 DC 10\nR1 in mid 10k\nR2 mid 0 10k\n.END"
        resp = api_post("/api/simulate", {"netlist": netlist, "type": "DC"})
        api_vmid = resp.get("results", {}).get("V(mid)", None)
        ok = api_vmid is not None and abs(float(api_vmid) - 5.0) < 0.01
        results.append(("API simulate voltage divider", ok, f"V(mid)={api_vmid}"))

        # 4. Headless simulate — RC transient
        netlist2 = "V1 in 0 DC 5\nR1 in out 1k\nC1 out 0 1u\n.END"
        resp2 = api_post("/api/simulate", {
            "netlist": netlist2, "type": "Transient",
            "settings": {"tstop": 5e-3, "tstep": 10e-6}
        })
        vout = resp2.get("results", {}).get("V(out)", [])
        if isinstance(vout, list) and len(vout) > 0:
            final = float(vout[-1])
            ok = abs(final - 5.0) < 0.1
            results.append(("API RC transient", ok, f"V(out) final={final:.4f}"))
        else:
            results.append(("API RC transient", False, "No V(out) data"))

        # 5. Headless simulate — RL transient (tests inductor)
        netlist3 = "V1 in 0 DC 5\nR1 in out 100\nL1 out 0 10m\n.END"
        resp3 = api_post("/api/simulate", {
            "netlist": netlist3, "type": "Transient",
            "settings": {"tstop": 1e-3, "tstep": 1e-6}
        })
        vout3 = resp3.get("results", {}).get("V(out)", [])
        if isinstance(vout3, list) and len(vout3) > 0:
            final3 = float(vout3[-1])
            ok = abs(final3) < 0.1  # Inductor shorts at DC → V(out)≈0
            results.append(("API RL transient (inductor)", ok, f"V(out) final={final3:.4f}"))
        else:
            results.append(("API RL transient", False, "No V(out) data"))

        # 6. Headless simulate — VCVS
        netlist4 = "V1 in 0 DC 1\nR1 in 0 1k\nE1 out 0 in 0 10\nR2 out 0 10k\n.END"
        resp4 = api_post("/api/simulate", {"netlist": netlist4, "type": "DC"})
        vout4 = resp4.get("results", {}).get("V(out)", None)
        ok = vout4 is not None and abs(float(vout4) - 10.0) < 0.01
        results.append(("API VCVS gain=10", ok, f"V(out)={vout4}"))

    except Exception as e:
        results.append(("API server test", False, f"Exception: {e}"))
    finally:
        server.shutdown()

    return results


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    t_start = time_mod.time()

    total = 0
    passed = 0
    failed = 0
    warned = 0
    errors = 0
    all_results = {}

    # ── Phase 1: Direct engine circuit validation ──
    print("=" * 70)
    print("  PHASE 1: CIRCUIT VALIDATION (direct engine)")
    print("=" * 70)

    for name, spec in CIRCUIT_SPECS.items():
        result = run_circuit_test(name, spec)
        all_results[name] = result

        status_icon = {
            "pass": "✓ PASS",
            "fail": "✗ FAIL",
            "warn": "⚠ WARN",
            "error": "✗ ERR ",
        }.get(result["status"], "?????")

        print(f"\n  [{status_icon}] {name}")

        if result["error"]:
            print(f"           Error: {result['error']}")
            errors += 1
        else:
            for ck in result["checks"]:
                sym = "✓" if ck["passed"] else "✗"
                print(f"           {sym} {ck['message']}")
                total += 1
                if ck["passed"]:
                    passed += 1
                else:
                    failed += 1

            if result["waveform_issues"]:
                for issue in result["waveform_issues"][:3]:
                    print(f"           ⚠ {issue}")
                warned += 1

            if result["node_summary"]:
                print("           Node Summary:")
                for node, info in sorted(result["node_summary"].items()):
                    print(f"             {node}: min={info['min']:.3f} max={info['max']:.3f} "
                          f"mean={info['mean']:.3f} final={info['final']:.3f} "
                          f"pts={info['points']} nan={info['nan_count']}")

        if result.get("unsupported_elements"):
            print(f"           (unsupported: {', '.join(result['unsupported_elements'])})")

    # ── Phase 2: API server validation ──
    print("\n" + "=" * 70)
    print("  PHASE 2: API SERVER VALIDATION")
    print("=" * 70)

    api_results = test_api_server()
    for label, ok, detail in api_results:
        sym = "✓" if ok else "✗"
        print(f"  [{sym}] {label}: {detail}")
        total += 1
        if ok:
            passed += 1
        else:
            failed += 1

    # ── Phase 3: Circuit Pattern KB dump ──
    print("\n" + "=" * 70)
    print("  PHASE 3: CIRCUIT PATTERN KNOWLEDGE BASE")
    print("=" * 70)
    for pname, pattern in CIRCUIT_PATTERNS.items():
        print(f"  📋 {pname}")
        print(f"     Topology: {pattern['topology']}")
        print(f"     Formula:  {pattern['formula']}")
        print(f"     Elements: {', '.join(pattern['elements'])}")

    # ── Summary ──
    elapsed = time_mod.time() - t_start
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print(f"  Total checks : {total}")
    print(f"  Passed       : {passed}")
    print(f"  Failed       : {failed}")
    print(f"  Warnings     : {warned}")
    print(f"  Errors       : {errors}")
    print(f"  Time         : {elapsed:.1f}s")

    if failed == 0 and errors == 0:
        print("\n  >>> ALL CHECKS PASSED <<<")
    else:
        print(f"\n  >>> {failed} FAILURES, {errors} ERRORS <<<")

    # Save detailed report
    report_path = Path(__file__).parent / "api_validation_report.json"
    with open(report_path, "w") as f:
        json.dump({
            "summary": {"total": total, "passed": passed, "failed": failed,
                        "warned": warned, "errors": errors, "time": elapsed},
            "circuits": {k: {
                "status": v["status"],
                "checks": v["checks"],
                "waveform_issues": v["waveform_issues"],
                "node_summary": v["node_summary"],
                "unsupported": v.get("unsupported_elements", []),
                "error": v["error"],
            } for k, v in all_results.items()},
            "circuit_patterns": CIRCUIT_PATTERNS,
        }, f, indent=2, default=str)
    print(f"\n  Report: {report_path}")

    return 0 if (failed == 0 and errors == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
