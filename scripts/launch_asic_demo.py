#!/usr/bin/env python3
"""
LIN ASIC Demo Launcher
======================
Drives the AMS Simulator GUI through its REST API to demonstrate the full
LIN ASIC chip working in simulation.

What this script does
---------------------
1. Checks whether the API server is reachable on port 5100.
2. Fetches the ASIC architecture overview  (GET  /api/asic/info).
3. Loads every block as its own schematic tab  (POST /api/asic/load)
   so the schematic editor shows the complete hierarchy.
4. Runs a transient simulation for every block (POST /api/asic/simulate)
   with *open_waveforms=True* so each block's waveform pops up in a
   separate window automatically.
5. Polls for the test report           (GET  /api/asic/test-report)
   and prints a structured PASS/FAIL summary.

Usage
-----
  # With GUI already running:
  python scripts/launch_asic_demo.py

  # Start the GUI and wait for API to come up:
  python scripts/launch_asic_demo.py --start-gui

  # Run simulations only (no GUI required, skip waveform windows):
  python scripts/launch_asic_demo.py --headless
"""

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API_BASE = "http://127.0.0.1:5100"
TIMEOUT = 10  # seconds per request


# ─────────────────────────────────────────────────────────────────────────────
#  HTTP helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get(path: str) -> dict:
    url = f"{API_BASE}{path}"
    with urllib.request.urlopen(url, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode())


def _post(path: str, payload: dict) -> dict:
    url = f"{API_BASE}{path}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode())


# ─────────────────────────────────────────────────────────────────────────────
#  Wait for server
# ─────────────────────────────────────────────────────────────────────────────

def wait_for_server(max_wait: float = 30.0) -> bool:
    """Poll /api/status until the server responds or timeout expires."""
    deadline = time.time() + max_wait
    attempt = 0
    while time.time() < deadline:
        try:
            _get("/api/status")
            return True
        except Exception:
            attempt += 1
            if attempt % 5 == 0:
                print(f"  Waiting for API server… ({int(deadline - time.time())}s left)")
            time.sleep(0.5)
    return False


# ─────────────────────────────────────────────────────────────────────────────
#  Pretty-print helpers
# ─────────────────────────────────────────────────────────────────────────────

PASS_SYM  = "\u2705 PASS"
FAIL_SYM  = "\u274c FAIL"
ERROR_SYM = "\u26a0  ERROR"
SKIP_SYM  = "\u23ed  SKIP"

def _status_sym(status: str) -> str:
    s = status.upper()
    if s == "PASS":   return PASS_SYM
    if s == "FAIL":   return FAIL_SYM
    if s == "ERROR":  return ERROR_SYM
    return SKIP_SYM


def _hr(char: str = "─", width: int = 70) -> str:
    return char * width


def _print_header(title: str):
    print()
    print(_hr("═"))
    print(f"  {title}")
    print(_hr("═"))


def _print_block_result(entry: dict, index: int):
    status = entry.get("status", "SKIP")
    sym    = _status_sym(status)
    name   = entry.get("name", entry.get("block", "?"))
    tested = entry.get("what_is_tested", "")
    meas   = entry.get("measurements", {})
    spec   = entry.get("spec", {})
    ms     = entry.get("elapsed_ms", 0)
    err    = entry.get("error")

    print(f"\n  [{index}]  {sym}  {name}")
    print(f"       What is tested : {tested}")

    if err:
        print(f"       Error          : {err}")
    else:
        _label = spec.get("label", "output")
        # LIN transceiver: report peak/valley
        if "bus_high_min" in spec:
            hi  = meas.get("output_peak",   "?")
            lo  = meas.get("output_valley", "?")
            hi_lim = spec.get("bus_high_min", 10.0)
            lo_lim = spec.get("bus_low_max",   2.0)
            print(f"       Bus high (recessive): {_fmt(hi)} V  "
                  f"(spec > {hi_lim} V)")
            print(f"       Bus low  (dominant) : {_fmt(lo)} V  "
                  f"(spec < {lo_lim} V)")
        else:
            mean   = meas.get("output_steady_mean", None)
            lo_lim = spec.get("output_min", "?")
            hi_lim = spec.get("output_max", "?")
            settle = meas.get("settling_time_ns", None)
            print(f"       {_label:<16}  : {_fmt(mean)} V  "
                  f"(spec {lo_lim}\u2013{hi_lim} V)")
            if settle is not None:
                print(f"       Settling time    : {settle:.1f} ns")

    print(f"       Elapsed          : {ms:.1f} ms")


def _fmt(v) -> str:
    if v is None:
        return "---"
    try:
        return f"{float(v):.4f}"
    except (TypeError, ValueError):
        return str(v)


# ─────────────────────────────────────────────────────────────────────────────
#  Main demo steps
# ─────────────────────────────────────────────────────────────────────────────

def step_check_server(headless: bool) -> bool:
    _print_header("STEP 1 / 5  —  API server connectivity check")
    try:
        status = _get("/api/status")
        has_gui = status.get("has_gui", False)
        print(f"  API server  : RUNNING  (port 5100)")
        print(f"  GUI window  : {'OPEN' if has_gui else 'NOT available (headless)'}")
        if has_gui:
            print(f"  Current tab : {status.get('current_tab', '?')}")
        if not has_gui and not headless:
            print()
            print("  NOTE: GUI is not open.  Use --headless to skip GUI features,")
            print("        or open the simulator first and re-run this script.")
        return True
    except Exception as exc:
        print(f"  FAILED: cannot reach API server — {exc}")
        print("  Make sure the simulator is running:  python -m simulator.main")
        return False


def step_asic_info():
    _print_header("STEP 2 / 5  —  LIN ASIC architecture overview")
    try:
        info = _get("/api/asic/info")
        print(f"  Chip        : {info['chip']}")
        print(f"  Technology  : {info['technology']}")
        print(f"  Blocks ({len(info['blocks'])}):")
        for b in info["blocks"]:
            print(f"    [{b['icon']:3s}]  {b['name']:<25}  {b['description']}")
        return info
    except Exception as exc:
        print(f"  Could not fetch ASIC info: {exc}")
        return {}


def step_load_hierarchy(has_gui: bool):
    _print_header("STEP 3 / 5  —  Load ASIC hierarchy into schematic editor")
    if not has_gui:
        print("  Skipped (no GUI available).")
        return
    try:
        resp = _post("/api/asic/load", {})
        print(f"  Status  : {resp.get('status')}")
        for i, tab in enumerate(resp.get("tabs", []), 1):
            print(f"    Tab {i:2d}  : {tab}")
        print()
        print("  The schematic editor now shows one tab per block.")
        print("  Each tab renders the actual SUBCKT netlist from designs/lin_asic/blocks/")
        # Give the GUI a moment to load all tabs
        time.sleep(1.5)
    except Exception as exc:
        print(f"  Could not load hierarchy: {exc}")


def step_simulate(has_gui: bool):
    _print_header("STEP 4 / 5  —  Run ASIC block simulations")
    print("  Running transient simulations for all blocks…")
    print("  (Simplified functional models; actual SUBCKT shown in schematic tabs)")
    print()
    try:
        resp = _post("/api/asic/simulate", {
            "open_waveforms": has_gui,   # Each block gets its own waveform window
        })
        tested = resp.get("blocks_tested", 0)
        passed = resp.get("blocks_passed", 0)
        failed = resp.get("blocks_failed", 0)
        print(f"  Blocks tested : {tested}")
        print(f"  Passed        : {passed}")
        print(f"  Failed        : {failed}")
        if has_gui and tested > 0:
            print()
            print("  A separate waveform window has been opened for each block.")
        return resp.get("results", [])
    except Exception as exc:
        print(f"  Simulation failed: {exc}")
        return []


def step_test_report():
    _print_header("STEP 5 / 5  —  Structured test report")
    try:
        report = _get("/api/asic/test-report")
    except Exception as exc:
        print(f"  Could not fetch test report: {exc}")
        return

    summary = report.get("summary", {})
    overall = summary.get("overall", "?")
    sym = PASS_SYM if overall == "PASS" else FAIL_SYM

    print(f"  Overall result : {sym}")
    print(f"  Total blocks   : {summary.get('total', 0)}")
    print(f"  Passed         : {summary.get('passed', 0)}")
    print(f"  Failed         : {summary.get('failed', 0)}")
    print(f"  Errors         : {summary.get('errors', 0)}")

    print()
    print(_hr())
    print("  BLOCK-BY-BLOCK RESULTS")
    print(_hr())

    for i, block in enumerate(report.get("blocks", []), 1):
        _print_block_result(block, i)

    print()
    print(_hr())
    print()
    return report


# ─────────────────────────────────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="LIN ASIC GUI demo via the AMS Simulator REST API"
    )
    parser.add_argument(
        "--start-gui", action="store_true",
        help="Launch the simulator GUI in a subprocess before running demo",
    )
    parser.add_argument(
        "--headless", action="store_true",
        help="Skip GUI-only steps (hierarchy tabs, waveform windows)",
    )
    parser.add_argument(
        "--port", type=int, default=5100,
        help="API server port (default 5100)",
    )
    args = parser.parse_args()

    global API_BASE
    API_BASE = f"http://127.0.0.1:{args.port}"

    print(_hr("═"))
    print("  LIN ASIC Demo  —  AMS Simulator")
    print(_hr("═"))

    gui_proc = None
    if args.start_gui:
        print("\n  Starting GUI…")
        sim_root = Path(__file__).parent.parent
        gui_proc = subprocess.Popen(
            [sys.executable, "-m", "simulator.main"],
            cwd=str(sim_root),
        )
        print(f"  GUI process PID: {gui_proc.pid}")

    if not wait_for_server(max_wait=30.0):
        print("\n  ERROR: API server did not respond within 30 s.")
        if gui_proc:
            gui_proc.terminate()
        sys.exit(1)

    # ── run demo steps ──────────────────────────────────────────────
    ok = step_check_server(args.headless)
    if not ok:
        sys.exit(1)

    # Determine whether the GUI responded with has_gui=True
    try:
        has_gui = _get("/api/status").get("has_gui", False) and not args.headless
    except Exception:
        has_gui = False

    step_asic_info()
    step_load_hierarchy(has_gui)
    step_simulate(has_gui)
    report = step_test_report()

    print("  Demo complete.")
    print()

    # Exit with non-zero code if any block failed
    if report:
        if report.get("summary", {}).get("overall") != "PASS":
            sys.exit(2)


if __name__ == "__main__":
    main()
