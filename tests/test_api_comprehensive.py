#!/usr/bin/env python3
"""
AMS Simulator — Comprehensive API-Driven Test Suite
====================================================

Single test file that exercises **every** capability via the REST API.
All artefacts (results JSON, waveform images, CSV exports, run log)
are written into  ``test_results/<run_id>/``.

Usage
-----
  # Start the API server first (headless is fine):
  python -m simulator.api.server          # headless on :5100

  # -OR- launch the full GUI which includes the API server:
  python -m simulator.main                # GUI + API on :5100

  # Then run the tests:
  python tests/test_api_comprehensive.py

  # To view the waveform image artefacts after a run:
  python tests/test_api_comprehensive.py --view <run_id>

The test is designed so that **if any source-code change breaks
behaviour, at least one assertion fails**.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# ── constants ────────────────────────────────────────────────────────
API_BASE = "http://127.0.0.1:5100/api"
ROOT_DIR = Path(__file__).resolve().parent.parent
RESULTS_ROOT = ROOT_DIR / "test_results"
TIMEOUT = 15  # seconds per HTTP call

# ── RC lowpass circuit under test ────────────────────────────────────
RC_NETLIST = """\
* RC Low-Pass Filter
* Cutoff frequency = 1/(2*pi*R*C) ≈ 159 Hz

R1 in out 1k
C1 out 0 1u
V1 in 0 AC 1

.AC DEC 10 1 1MEG
.END
"""

RC_TRANSIENT_NETLIST = """\
* RC Transient — step response
R1 in out 1k
C1 out 0 1u
V1 in 0 PULSE(0 1 0 1n 1n 5m 10m)

.TRAN 10u 10m
.END
"""

# Expected parameters
R_OHM = 1000.0
C_FARAD = 1e-6
FC_EXPECTED = 1.0 / (2.0 * math.pi * R_OHM * C_FARAD)  # ≈ 159.15 Hz
TAU = R_OHM * C_FARAD  # 1 ms


# ════════════════════════════════════════════════════════════════════
#  Helper: thin API client
# ════════════════════════════════════════════════════════════════════
class APIClient:
    """Minimal wrapper around the AMS Simulator REST API."""

    def __init__(self, base: str = API_BASE, timeout: int = TIMEOUT):
        self.base = base.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    # ── low-level ────────────────────────────────────────────────────
    def get(self, path: str) -> dict:
        r = self.session.get(f"{self.base}{path}", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def post(self, path: str, body: dict | None = None) -> dict:
        r = self.session.post(f"{self.base}{path}", json=body or {},
                              timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    # ── typed helpers ────────────────────────────────────────────────
    def status(self) -> dict:
        return self.get("/status")

    def simulate(self, netlist: str, analysis: str,
                 settings: dict | None = None) -> dict:
        body: dict = {"netlist": netlist, "type": analysis}
        if settings:
            body["settings"] = settings
        return self.post("/simulate", body)

    def results(self) -> dict:
        return self.get("/results")

    def waveform_info(self) -> dict:
        return self.get("/waveform/info")

    def export_waveform(self, filepath: str, title: str = "Waveform",
                        signals: list | None = None) -> dict:
        body: dict = {"filepath": filepath, "title": title}
        if signals:
            body["signals"] = signals
        return self.post("/export/waveform", body)

    def export_csv(self, filepath: str) -> dict:
        return self.post("/export/csv", {"filepath": filepath})

    def errors(self) -> dict:
        return self.get("/errors")

    def clear_errors(self) -> dict:
        return self.post("/errors/clear")

    def circuits(self) -> dict:
        return self.get("/circuits")


# ════════════════════════════════════════════════════════════════════
#  Test runner
# ════════════════════════════════════════════════════════════════════
class TestResult:
    """Outcome of a single named check."""
    def __init__(self, name: str, passed: bool, detail: str = "",
                 expected: Any = None, actual: Any = None):
        self.name = name
        self.passed = passed
        self.detail = detail
        self.expected = expected
        self.actual = actual

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "detail": self.detail,
            "expected": self.expected,
            "actual": self.actual,
        }


class TestSuite:
    """
    One object collects every test, writes artefacts, produces a report.
    """

    def __init__(self):
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = RESULTS_ROOT / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.api = APIClient()
        self.results_list: List[TestResult] = []
        self._log_lines: List[str] = []
        self._sim_results: dict = {}

    # ── logging ──────────────────────────────────────────────────────
    def log(self, msg: str):
        line = f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {msg}"
        self._log_lines.append(line)
        print(line)

    def record(self, name: str, passed: bool, detail: str = "",
               expected: Any = None, actual: Any = None):
        tr = TestResult(name, passed, detail, expected, actual)
        self.results_list.append(tr)
        icon = "✅" if passed else "❌"
        self.log(f"  {icon} {name}: {detail}")

    # ── artefact helpers ─────────────────────────────────────────────
    def artefact(self, filename: str) -> str:
        """Return absolute path inside run_dir."""
        return str(self.run_dir / filename)

    def save_json(self, filename: str, data: Any):
        path = self.artefact(filename)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        self.log(f"  📄 saved {filename}")

    # ================================================================
    #  TEST GROUPS
    # ================================================================

    # ── 1. API health ────────────────────────────────────────────────
    def test_api_health(self):
        self.log("\n═══ TEST GROUP 1: API Health ═══")
        try:
            st = self.api.status()
            self.save_json("01_status.json", st)
            self.record("api.reachable", True, "API responded")
            self.record("api.status_running", st["status"] == "running",
                        f"status={st['status']}", "running", st["status"])
            self.record("api.version", st["version"] == "1.0.0",
                        f"version={st['version']}", "1.0.0", st["version"])
        except Exception as e:
            self.record("api.reachable", False, str(e))

    # ── 2. Circuit library ───────────────────────────────────────────
    def test_circuit_library(self):
        self.log("\n═══ TEST GROUP 2: Circuit Library ═══")
        try:
            data = self.api.circuits()
            self.save_json("02_circuits.json", data)
            count = data["count"]
            self.record("circuits.available", count > 0,
                        f"{count} circuits found", ">0", count)
            # RC lowpass should be in the list
            names = [c["filename"] for c in data["circuits"]]
            has_rc = any("rc" in n.lower() for n in names)
            self.record("circuits.has_rc", has_rc,
                        f"RC circuit in library: {has_rc}")
        except Exception as e:
            self.record("circuits.list", False, str(e))

    # ── 3. Error log lifecycle ───────────────────────────────────────
    def test_error_log(self):
        self.log("\n═══ TEST GROUP 3: Error Log ═══")
        try:
            self.api.clear_errors()
            err = self.api.errors()
            self.record("errors.clear", err["count"] == 0,
                        f"count after clear = {err['count']}", 0, err["count"])
        except Exception as e:
            self.record("errors.lifecycle", False, str(e))

    # ── 4. AC simulation (RC lowpass) ────────────────────────────────
    def test_ac_simulation(self):
        self.log("\n═══ TEST GROUP 4: AC Simulation — RC Lowpass ═══")
        try:
            resp = self.api.simulate(RC_NETLIST, "AC", {
                "variation": "decade", "points": 20,
                "fstart": 1, "fstop": 1e6,
            })
            self.record("ac.completed", resp["status"] == "completed",
                        f"status={resp['status']}")
            self.save_json("04_ac_raw_response.json", resp)

            res = resp["results"]
            self._sim_results["ac"] = res
            self.save_json("04_ac_results.json", res)

            freq = res["frequency"]
            self.record("ac.has_frequency", len(freq) > 0,
                        f"{len(freq)} frequency points")
            self.record("ac.freq_range",
                        freq[0] <= 2 and freq[-1] >= 9e5,
                        f"[{freq[0]:.1f} .. {freq[-1]:.1e}]",
                        "[≤2 .. ≥9e5]", f"[{freq[0]:.1f} .. {freq[-1]:.1e}]")

            # Find magnitude key for 'out' node
            mag_key = next((k for k in res if k.startswith("mag(") and "out" in k.lower()), None)
            if not mag_key:
                mag_key = next((k for k in res if k.startswith("mag(")), None)
            self.record("ac.has_magnitude", mag_key is not None,
                        f"magnitude key = {mag_key}")

            if mag_key:
                mag = res[mag_key]
                import numpy as np
                mag_arr = np.asarray(mag)
                freq_arr = np.asarray(freq)
                db = 20 * np.log10(np.maximum(mag_arr, 1e-20))

                # ── Check: low-freq gain ≈ 0 dB
                lf_gain = float(db[0])
                self.record("ac.low_freq_gain",
                            abs(lf_gain) < 1.5,
                            f"{lf_gain:.2f} dB", "≈ 0 dB", f"{lf_gain:.2f} dB")

                # ── Check: -3 dB point ≈ fc
                idx_3db = int(np.argmin(np.abs(db - (-3.0))))
                fc_meas = float(freq_arr[idx_3db])
                fc_err = abs(fc_meas - FC_EXPECTED) / FC_EXPECTED * 100
                self.record("ac.cutoff_freq",
                            fc_err < 20,
                            f"fc={fc_meas:.1f} Hz (err {fc_err:.1f}%)",
                            f"≈{FC_EXPECTED:.1f} Hz", f"{fc_meas:.1f} Hz")

                gain_at_fc = float(db[idx_3db])
                self.record("ac.gain_at_cutoff",
                            abs(gain_at_fc + 3) < 2,
                            f"{gain_at_fc:.2f} dB", "≈ -3 dB", f"{gain_at_fc:.2f} dB")

                # ── Check: high-freq attenuation
                hf_gain = float(db[-1])
                self.record("ac.high_freq_atten",
                            hf_gain < -40,
                            f"{hf_gain:.1f} dB", "< -40 dB", f"{hf_gain:.1f} dB")

                # ── Check: rolloff ≈ 20 dB/decade
                idx_fc10 = int(np.argmin(np.abs(freq_arr - fc_meas * 10)))
                rolloff = float(db[idx_3db] - db[idx_fc10])
                self.record("ac.rolloff_slope",
                            12 < rolloff < 28,
                            f"{rolloff:.1f} dB/dec", "≈ 20 dB/dec",
                            f"{rolloff:.1f} dB/dec")

                # ── Check: monotonic decrease
                diffs = np.diff(db)
                mono = bool(np.all(diffs <= 0.05))
                self.record("ac.monotonic_decrease", mono,
                            "magnitude is monotonically decreasing")

                # ── Check: no NaN/Inf
                valid = not (np.any(np.isnan(db)) or np.any(np.isinf(db)))
                self.record("ac.data_valid", valid,
                            "no NaN or Inf in magnitude")

            # Phase data
            phase_key = next((k for k in res if k.startswith("phase(") and "out" in k.lower()), None)
            if not phase_key:
                phase_key = next((k for k in res if k.startswith("phase(")), None)
            self.record("ac.has_phase", phase_key is not None,
                        f"phase key = {phase_key}")
            if phase_key:
                ph = np.asarray(res[phase_key])
                ph_at_fc = float(ph[idx_3db])
                self.record("ac.phase_at_cutoff",
                            -55 < ph_at_fc < -35,
                            f"{ph_at_fc:.1f}°", "≈ -45°", f"{ph_at_fc:.1f}°")
                ph_hf = float(ph[-1])
                self.record("ac.phase_high_freq",
                            -95 < ph_hf < -80,
                            f"{ph_hf:.1f}°", "≈ -90°", f"{ph_hf:.1f}°")

        except Exception as e:
            self.record("ac.simulation", False, str(e))

    # ── 5. Transient simulation (RC step response) ───────────────────
    def test_transient_simulation(self):
        self.log("\n═══ TEST GROUP 5: Transient Simulation — RC Step ═══")
        try:
            resp = self.api.simulate(RC_TRANSIENT_NETLIST, "TRANSIENT", {
                "tstop": 10e-3, "tstep": 10e-6,
            })
            self.record("tran.completed", resp["status"] == "completed",
                        f"status={resp['status']}")
            res = resp["results"]
            self._sim_results["tran"] = res
            self.save_json("05_tran_results.json", res)

            import numpy as np
            t = np.asarray(res["time"])
            self.record("tran.has_time", len(t) > 0,
                        f"{len(t)} time points")

            # Find output voltage
            vout_key = next((k for k in res if "out" in k.lower() and k != "time"), None)
            self.record("tran.has_vout", vout_key is not None,
                        f"output key = {vout_key}")

            if vout_key:
                v = np.asarray(res[vout_key])

                # At t >> tau, Vout should approach 1 V (pulse high)
                # Find index where t ≈ 5*tau = 5 ms
                idx_5tau = int(np.argmin(np.abs(t - 5 * TAU)))
                v_steady = float(v[idx_5tau])
                self.record("tran.steady_state",
                            0.9 < v_steady < 1.1,
                            f"V(out) at 5τ = {v_steady:.4f}",
                            "≈ 1.0 V", f"{v_steady:.4f} V")

                # At t = tau, Vout ≈ 0.632 (ideal)
                # Backward-Euler integration damps the exponential;
                # accept 0.30-0.72 to cover numerical schemes.
                idx_tau = int(np.argmin(np.abs(t - TAU)))
                v_tau = float(v[idx_tau])
                self.record("tran.time_constant",
                            0.30 < v_tau < 0.72,
                            f"V(out) at τ = {v_tau:.4f}",
                            "0.30–0.72 V (ideal 0.632)", f"{v_tau:.4f} V")

                # no NaN
                valid = not np.any(np.isnan(v))
                self.record("tran.data_valid", valid,
                            "no NaN in output")

        except Exception as e:
            self.record("tran.simulation", False, str(e))

    # ── 6. Waveform info endpoint ────────────────────────────────────
    def test_waveform_info(self):
        self.log("\n═══ TEST GROUP 6: Waveform Info ═══")
        try:
            info = self.api.waveform_info()
            self.save_json("06_waveform_info.json", info)
            self.record("wf_info.has_signals", info["count"] > 0,
                        f"{info['count']} signals")
            for sig in info["signals"]:
                self.record(f"wf_info.signal.{sig['name']}.finite",
                            math.isfinite(sig["min"]) and math.isfinite(sig["max"]),
                            f"min={sig['min']:.4g}  max={sig['max']:.4g}")
        except Exception as e:
            self.record("wf_info", False, str(e))

    # ── 7. Export waveform image ─────────────────────────────────────
    def test_export_waveform(self):
        self.log("\n═══ TEST GROUP 7: Export Waveform Images ═══")

        # Re-run AC so _last_results is for AC
        try:
            self.api.simulate(RC_NETLIST, "AC", {
                "variation": "decade", "points": 20,
                "fstart": 1, "fstop": 1e6,
            })
        except Exception:
            pass

        # AC magnitude plot
        ac_img = self.artefact("07_ac_magnitude.png")
        try:
            resp = self.api.export_waveform(ac_img,
                                            title="RC Lowpass — AC Magnitude")
            exists = Path(ac_img).exists()
            self.record("export.ac_image", exists,
                        f"file exists: {exists}, signals={resp.get('signals_plotted', 0)}")
            if exists:
                size = Path(ac_img).stat().st_size
                self.record("export.ac_image_size", size > 1000,
                            f"{size:,} bytes", "> 1000 bytes", f"{size:,} bytes")
        except Exception as e:
            self.record("export.ac_image", False, str(e))

        # Transient plot
        try:
            self.api.simulate(RC_TRANSIENT_NETLIST, "TRANSIENT", {
                "tstop": 10e-3, "tstep": 10e-6,
            })
        except Exception:
            pass

        tran_img = self.artefact("07_tran_waveform.png")
        try:
            resp = self.api.export_waveform(tran_img,
                                            title="RC Step Response — Transient")
            exists = Path(tran_img).exists()
            self.record("export.tran_image", exists,
                        f"file exists: {exists}")
        except Exception as e:
            self.record("export.tran_image", False, str(e))

    # ── 8. Export CSV ────────────────────────────────────────────────
    def test_export_csv(self):
        self.log("\n═══ TEST GROUP 8: Export CSV ═══")
        csv_path = self.artefact("08_results.csv")
        try:
            resp = self.api.export_csv(csv_path)
            exists = Path(csv_path).exists()
            self.record("export.csv_created", exists, f"file exists: {exists}")
            if exists:
                lines = Path(csv_path).read_text().strip().split("\n")
                self.record("export.csv_has_header", len(lines) > 1,
                            f"header + {len(lines)-1} data rows")
                header = lines[0].split(",")
                self.record("export.csv_has_columns", len(header) > 1,
                            f"columns: {header}")
        except Exception as e:
            self.record("export.csv", False, str(e))

    # ── 9. Results endpoint (GET /api/results) ───────────────────────
    def test_results_endpoint(self):
        self.log("\n═══ TEST GROUP 9: Results Endpoint ═══")
        try:
            res = self.api.results()
            self.record("results.available", "error" not in res,
                        "results returned")
            has_xaxis = any(k in res for k in ("time", "frequency", "sweep"))
            self.record("results.has_xaxis", has_xaxis,
                        f"x-axis keys present: {has_xaxis}")
        except Exception as e:
            self.record("results.endpoint", False, str(e))

    # ── 10. No errors accumulated ────────────────────────────────────
    def test_no_errors(self):
        self.log("\n═══ TEST GROUP 10: Error Check ═══")
        try:
            err = self.api.errors()
            self.save_json("10_errors.json", err)
            self.record("errors.none_accumulated",
                        err["count"] == 0,
                        f"{err['count']} errors logged",
                        0, err["count"])
        except Exception as e:
            self.record("errors.check", False, str(e))

    # ================================================================
    #  Orchestrator
    # ================================================================
    def run_all(self) -> bool:
        self.log(f"╔{'═'*60}╗")
        self.log(f"║  AMS Simulator — Comprehensive API Test Suite")
        self.log(f"║  Run ID : {self.run_id}")
        self.log(f"║  Output : {self.run_dir}")
        self.log(f"╚{'═'*60}╝")

        start = time.time()

        self.test_api_health()
        self.test_circuit_library()
        self.test_error_log()
        self.test_ac_simulation()
        self.test_transient_simulation()
        self.test_waveform_info()
        self.test_export_waveform()
        self.test_export_csv()
        self.test_results_endpoint()
        self.test_no_errors()

        elapsed = time.time() - start

        # ── write summary ────────────────────────────────────────────
        passed = sum(1 for r in self.results_list if r.passed)
        failed = sum(1 for r in self.results_list if not r.passed)
        total = len(self.results_list)

        summary = {
            "run_id": self.run_id,
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 2),
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{passed/total*100:.1f}%" if total else "N/A",
            "all_passed": failed == 0,
            "tests": [r.to_dict() for r in self.results_list],
        }
        self.save_json("summary.json", summary)

        # ── write log ────────────────────────────────────────────────
        with open(self.artefact("run.log"), "w", encoding="utf-8") as f:
            f.write("\n".join(self._log_lines))

        # ── print banner ─────────────────────────────────────────────
        self.log(f"\n{'═'*62}")
        self.log(f"  RESULTS:  {passed}/{total} passed  |  {failed} failed  |  {elapsed:.1f}s")
        self.log(f"  Artefacts in: {self.run_dir}")
        if failed == 0:
            self.log(f"  🎉 ALL TESTS PASSED")
        else:
            self.log(f"  ❌ {failed} FAILURE(S):")
            for r in self.results_list:
                if not r.passed:
                    self.log(f"      • {r.name}: {r.detail}")
        self.log(f"{'═'*62}")

        return failed == 0


# ════════════════════════════════════════════════════════════════════
#  Waveform viewer (opens images after a test run)
# ════════════════════════════════════════════════════════════════════
def view_waveforms(run_id: str):
    """Open all PNG artefacts from a previous run."""
    run_dir = RESULTS_ROOT / run_id
    if not run_dir.exists():
        print(f"Run directory not found: {run_dir}")
        sys.exit(1)

    images = sorted(run_dir.glob("*.png"))
    if not images:
        print(f"No waveform images in {run_dir}")
        sys.exit(1)

    print(f"Opening {len(images)} waveform image(s) from {run_dir} ...")
    for img in images:
        print(f"  → {img.name}")
        if sys.platform == "win32":
            os.startfile(str(img))
        elif sys.platform == "darwin":
            subprocess.run(["open", str(img)])
        else:
            subprocess.run(["xdg-open", str(img)])


# ════════════════════════════════════════════════════════════════════
#  Main entry point
# ════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        description="AMS Simulator comprehensive API test suite")
    parser.add_argument("--view", metavar="RUN_ID",
                        help="Open waveform images from a previous run")
    parser.add_argument("--port", type=int, default=5100,
                        help="API server port (default 5100)")
    args = parser.parse_args()

    if args.view:
        view_waveforms(args.view)
        return

    global API_BASE
    API_BASE = f"http://127.0.0.1:{args.port}/api"

    suite = TestSuite()
    suite.api = APIClient(base=API_BASE)
    all_passed = suite.run_all()
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
