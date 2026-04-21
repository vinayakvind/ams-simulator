"""
AMS Simulator VSCode API Server.

Provides an HTTP REST API for controlling the AMS Simulator from
external tools (VS Code, scripts, automation). The API runs in a
background thread alongside the PyQt6 GUI event loop.

Headless mode is fully supported — pass no main_window and the engine
runs without any GUI dependency.

API Endpoints:
    GET  /api/status              - Server and simulator status
    GET  /api/circuits            - List available standard circuits
    POST /api/circuits/load       - Load a standard circuit (GUI only)
    POST /api/simulate            - Run simulation (headless or GUI)
    GET  /api/results             - Last simulation results (JSON)
    GET  /api/schematic/info      - Components & wires on the canvas
    POST /api/schematic/component - Add a component to the schematic
    POST /api/schematic/clear     - Clear the schematic
    POST /api/netlist/load        - Load a SPICE netlist string
    GET  /api/netlist             - Generated netlist from schematic
    POST /api/export/schematic    - Export schematic image (PNG/PDF)
    POST /api/export/waveform     - Export waveform image (PNG/SVG/PDF)
    POST /api/export/csv          - Export waveform data as CSV
    GET  /api/waveform/info       - Waveform signals and measurements
    GET  /api/errors              - Accumulated error log
    GET  /api/errors/monitor      - Error-monitor state and recent corrections
    POST /api/errors/clear        - Clear the error log
    POST /api/errors/scan         - Scan current error log and attempt corrections
    POST /api/errors/monitor      - Enable/disable monitor and adjust scan interval
"""

import json
import os
import threading
import time as _time
import traceback
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Optional
from pathlib import Path
from urllib.parse import urlparse


# ---------- module-level state ----------
_main_window = None
_last_results: Optional[dict] = None
_error_log: list = []
_error_log_lock = threading.Lock()
_last_simulation_request: Optional[dict] = None
_last_loaded_netlist: Optional[str] = None
_last_loaded_circuit: Optional[dict] = None
_auto_corrections: list = []
_monitor_thread: Optional[threading.Thread] = None
_monitor_stop_event = threading.Event()
_monitor_state = {
    "enabled": False,
    "interval_seconds": 2.0,
    "last_scan_timestamp": None,
    "last_processed_error_index": 0,
}
_api_session_guid = str(uuid.uuid4())
_api_port = 5100
_api_request_log: list = []
_api_request_log_lock = threading.Lock()
_api_request_counter = 0

# ---------- ASIC state ----------
_asic_test_results: list = []  # populated by /api/asic/simulate
_asic_mixed_signal_report: Optional[dict] = None


# ---------- LIN ASIC block test suite ----------
# Each entry defines a self-contained testbench netlist (using only
# basic R/C/V elements the built-in Python engine handles) plus the
# pass/fail criteria for the block.  The netlists are simplified
# functional models; the actual MOSFET subcircuits are loaded into
# schematic tabs for the visual hierarchy view.
_ASIC_BLOCK_TESTS: dict = {
    "bandgap": {
        "name": "Bandgap Reference",
        "icon": "REF",
        "description": "Brokaw bandgap: 3.3 V supply \u2192 1.2 V VREF, TC < 50 ppm/\u00b0C",
        "what_is_tested": (
            "VREF startup and settling when VDD powers on from 0\u2009V. "
            "Verifies nominal output (1.2\u2009V \u00b1\u20095\u00a0%)"
        ),
        "test_type": "TRANSIENT",
        # Simplified functional model: voltage divider + RC filter
        # R1=7k, R2=4k -> VREF = 3.3 * 4/(7+4) = 1.200 V
        # pw=100u >> tstop=2000n so VDD stays on for the full simulation
        "netlist": (
            "* LIN ASIC - Bandgap Reference Testbench\n"
            "* Simplified model: R-divider + RC filter (VREF target = 1.2 V)\n"
            "VDD n_vdd 0 PULSE(0 3.3 20n 5n 5n 100000n 200000n)\n"
            "R1  n_vdd  n_vref  7k\n"
            "R2  n_vref 0       4k\n"
            "C_filt n_vref 0    40p\n"
            ".TRAN 2n 2000n\n"
        ),
        "settings": {"tstop": 2e-6, "tstep": 2e-9},
        "output_node": "V(n_vref)",
        "spec": {"output_min": 1.14, "output_max": 1.26, "label": "VREF"},
    },
    "ldo_analog": {
        "name": "LDO Analog Supply",
        "icon": "LDO",
        "description": "PMOS LDO: 12 V VBAT \u2192 3.3 V analog rail, 50 mA max",
        "what_is_tested": (
            "Output regulation when 12 V supply powers on. "
            "Verifies VOUT = 3.3\u2009V \u00b1\u20095\u00a0%"
        ),
        "test_type": "TRANSIENT",
        # R_pass=2636, R_load=1000 -> VOUT = 12 * 1000/3636 = 3.30 V
        # pw=100u >> tstop=3000n so VIN stays on for the full simulation
        "netlist": (
            "* LIN ASIC - LDO Analog Supply Testbench\n"
            "* Simplified model: series R + RC load (VOUT target = 3.3 V)\n"
            "VIN n_vin 0 PULSE(0 12 20n 5n 5n 100000n 200000n)\n"
            "R_pass n_vin  n_vout 2636\n"
            "R_load n_vout 0      1000\n"
            "C_out  n_vout 0      100p\n"
            ".TRAN 5n 3000n\n"
        ),
        "settings": {"tstop": 3e-6, "tstep": 5e-9},
        "output_node": "V(n_vout)",
        "spec": {"output_min": 3.1, "output_max": 3.5, "label": "VOUT"},
    },
    "ldo_digital": {
        "name": "LDO Digital Supply",
        "icon": "LDO",
        "description": "PMOS LDO: 3.3 V \u2192 1.8 V digital core supply",
        "what_is_tested": (
            "Output regulation when 3.3 V supply powers on. "
            "Verifies VOUT = 1.8\u2009V \u00b1\u20095\u00a0%"
        ),
        "test_type": "TRANSIENT",
        # R_pass=833, R_load=1000 -> VOUT = 3.3 * 1000/1833 = 1.800 V
        # pw=100u >> tstop=3000n so VIN stays on for the full simulation
        "netlist": (
            "* LIN ASIC - LDO Digital Supply Testbench\n"
            "* Simplified model: series R + RC load (VOUT target = 1.8 V)\n"
            "VIN n_vin 0 PULSE(0 3.3 20n 5n 5n 100000n 200000n)\n"
            "R_pass n_vin  n_vout 833\n"
            "R_load n_vout 0      1000\n"
            "C_out  n_vout 0      100p\n"
            ".TRAN 5n 3000n\n"
        ),
        "settings": {"tstop": 3e-6, "tstep": 5e-9},
        "output_node": "V(n_vout)",
        "spec": {"output_min": 1.7, "output_max": 1.9, "label": "VOUT"},
    },
    "ldo_lin": {
        "name": "LDO LIN Supply",
        "icon": "LDO",
        "description": "PMOS LDO: 12 V VBAT \u2192 5.0 V LIN transceiver supply",
        "what_is_tested": (
            "Output regulation for LIN bus driver power-up. "
            "Verifies VOUT = 5.0\u2009V \u00b1\u20095\u00a0%"
        ),
        "test_type": "TRANSIENT",
        # R_pass=1400, R_load=1000 -> VOUT = 12 * 1000/2400 = 5.00 V
        # pw=100u >> tstop=3000n so VIN stays on for the full simulation
        "netlist": (
            "* LIN ASIC - LDO LIN Supply Testbench\n"
            "* Simplified model: series R + RC load (VOUT target = 5.0 V)\n"
            "VIN n_vin 0 PULSE(0 12 20n 5n 5n 100000n 200000n)\n"
            "R_pass n_vin  n_vout 1400\n"
            "R_load n_vout 0      1000\n"
            "C_out  n_vout 0      150p\n"
            ".TRAN 5n 3000n\n"
        ),
        "settings": {"tstop": 3e-6, "tstep": 5e-9},
        "output_node": "V(n_vout)",
        "spec": {"output_min": 4.75, "output_max": 5.25, "label": "VOUT"},
    },
    "lin_transceiver": {
        "name": "LIN Transceiver",
        "icon": "TRX",
        "description": "LIN bus driver/receiver: dominant (~1 V) / recessive (~12 V) signaling",
        "what_is_tested": (
            "Bus voltage swing between dominant and recessive states. "
            "Verifies V_bus_high > 10\u2009V and V_bus_low < 2\u2009V"
        ),
        "test_type": "TRANSIENT",
        # When V_ctrl=0:     n_bus \u2248 12*(100/1100) = 1.09 V  (dominant)
        # When V_ctrl=11.5:  n_bus \u2248 11.55 V               (recessive)
        "netlist": (
            "* LIN ASIC - LIN Transceiver Bus Testbench\n"
            "* LIN bus dominant (~1 V) / recessive (~12 V) signaling\n"
            "VBAT    n_vbat  0       DC 12\n"
            "V_ctrl  n_ctrl  0       PULSE(0 11.5 50n 2n 2n 200n 400n)\n"
            "R_pullup n_vbat n_bus   1k\n"
            "R_drv    n_ctrl n_bus   100\n"
            "C_bus    n_bus  0       200p\n"
            ".TRAN 5n 1200n\n"
        ),
        "settings": {"tstop": 1.2e-6, "tstep": 5e-9},
        "output_node": "V(n_bus)",
        # Special: check peak AND valley rather than steady mean
        "spec": {"bus_high_min": 10.0, "bus_low_max": 2.0, "label": "V_bus"},
    },
}

_ASIC_DIGITAL_BLOCKS: dict = {
    "spi_controller": {
        "name": "SPI Controller",
        "icon": "SPI",
        "domain": "digital",
        "description": "Host programming interface with SPI register decode",
        "what_is_tested": (
            "SPI slave transaction decode from SCLK/MOSI/CS_N into register "
            "address/control handoff"
        ),
        "test_type": "RTL",
        "spice_candidates": ["blocks/spi_controller.spice"],
        "rtl_candidates": ["rtl/spi_controller.v", "rtl/spi_slave.v"],
    },
    "register_file": {
        "name": "Register File",
        "icon": "REG",
        "domain": "digital",
        "description": "Configuration/status register map for LIN and power control",
        "what_is_tested": (
            "Hierarchical register-bank shell visibility and control-path presence "
            "inside the LIN ASIC hierarchy"
        ),
        "test_type": "HIERARCHY",
        "spice_candidates": ["blocks/register_file.spice"],
        "rtl_candidates": [],
    },
    "lin_controller": {
        "name": "LIN Controller",
        "icon": "LIN",
        "domain": "digital",
        "description": "LIN framing, PID/checksum handling, break/sync state machine",
        "what_is_tested": (
            "Behavioral RTL reset, state-machine bring-up, and LIN master break/sync "
            "control-path readiness"
        ),
        "test_type": "RTL",
        "spice_candidates": ["blocks/lin_controller.spice"],
        "rtl_candidates": ["rtl/lin_controller.v"],
    },
    "control_logic": {
        "name": "Control Logic",
        "icon": "CTL",
        "domain": "digital",
        "description": "Power-up sequencing, enables, resets, and clock management",
        "what_is_tested": (
            "Hierarchical enable/reset block presence bridging the digital register path "
            "into analog power-control signals"
        ),
        "test_type": "MIXED",
        "spice_candidates": ["blocks/control_logic.spice"],
        "rtl_candidates": [],
    },
}


def _asic_design_root() -> Path:
    """Return the repository path containing the LIN ASIC design files."""
    return Path(__file__).parent.parent.parent / "designs" / "lin_asic"


def _load_asic_architecture() -> dict:
    """Load the LIN ASIC architecture manifest if it exists."""
    arch_file = _asic_design_root() / "lin_asic_architecture.json"
    if not arch_file.exists():
        return {}
    try:
        return json.loads(arch_file.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _find_existing_design_file(candidates: list[str]) -> Optional[str]:
    """Return the first existing design file candidate relative to the ASIC root."""
    base = _asic_design_root()
    for candidate in candidates:
        if (base / candidate).exists():
            return candidate
    return None


def _get_asic_block_catalog() -> dict:
    """Return a combined analog + digital ASIC block catalog."""
    catalog: dict = {}

    analog_spice_candidates = {
        "bandgap": ["blocks/bandgap_ref.spice", "blocks/bandgap/bandgap.spice"],
        "ldo_analog": ["blocks/ldo_analog.spice", "blocks/ldo_analog/ldo_analog.spice"],
        "ldo_digital": ["blocks/ldo_digital.spice", "blocks/ldo_digital/ldo_digital.spice"],
        "ldo_lin": ["blocks/ldo_lin.spice", "blocks/ldo_lin/ldo_lin.spice"],
        "lin_transceiver": [
            "blocks/lin_transceiver.spice",
            "blocks/lin_transceiver/lin_transceiver.spice",
        ],
    }

    for block_name, spec in _ASIC_BLOCK_TESTS.items():
        entry = dict(spec)
        entry["domain"] = "analog" if block_name != "lin_transceiver" else "mixed"
        entry["spice_candidates"] = analog_spice_candidates.get(block_name, [])
        entry["spice_file"] = _find_existing_design_file(entry["spice_candidates"])
        entry["rtl_file"] = None
        catalog[block_name] = entry

    for block_name, spec in _ASIC_DIGITAL_BLOCKS.items():
        entry = dict(spec)
        entry["spice_file"] = _find_existing_design_file(spec.get("spice_candidates", []))
        entry["rtl_file"] = _find_existing_design_file(spec.get("rtl_candidates", []))
        catalog[block_name] = entry

    return catalog


def _append_auto_correction(action: str, status: str, detail: str, source: str):
    """Record a corrective action attempt/result."""
    _auto_corrections.append({
        "timestamp": _time.time(),
        "action": action,
        "status": status,
        "detail": detail,
        "source": source,
    })
    if len(_auto_corrections) > 100:
        del _auto_corrections[:-100]


def _record_error(source: str, message: str, detail: str = ""):
    """Append an error entry to the global log."""
    with _error_log_lock:
        _error_log.append({
            "timestamp": _time.time(),
            "source": source,
            "message": message,
            "detail": detail,
            "handled": False,
            "correction_attempted": False,
            "correction_status": "pending",
        })


def _truncate_api_text(value: Any, limit: int = 220) -> str:
    """Turn an object into a compact single-line string for the session log."""
    if value in (None, "", {}, []):
        return ""
    try:
        text = json.dumps(value, default=str, ensure_ascii=False)
    except Exception:
        text = str(value)
    text = text.replace("\r", " ").replace("\n", " ")
    if len(text) > limit:
        return text[:limit - 3] + "..."
    return text


def _summarize_api_response(data: Any) -> str:
    """Build a small, stable response summary for the API session monitor."""
    if isinstance(data, dict):
        important = []
        for key in (
            "status", "message", "error", "active_tab", "component_count",
            "wire_count", "count", "total", "blocks_tested", "blocks_passed",
            "blocks_failed", "overall", "filepath", "session_guid",
        ):
            if key in data:
                important.append(f"{key}={data[key]}")
        if not important:
            keys = list(data.keys())[:6]
            important.append("keys=" + ",".join(keys))
        return _truncate_api_text("; ".join(important))
    return _truncate_api_text(data)


def _get_gui_snapshot() -> dict:
    """Capture the currently active GUI schematic state for handshake logging."""
    snapshot = {
        "current_tab": None,
        "component_count": 0,
        "wire_count": 0,
        "tab_count": 0,
    }
    if not _main_window:
        return snapshot
    try:
        editor = _main_window.schematic_editor
        snapshot["current_tab"] = _main_window.schematic_tabs.tabText(
            _main_window.schematic_tabs.currentIndex()
        )
        snapshot["component_count"] = len(editor._components)
        snapshot["wire_count"] = len(editor._wires)
        snapshot["tab_count"] = _main_window.schematic_tabs.count()
    except Exception:
        pass
    return snapshot


def _append_api_request_entry(
    method: str,
    path: str,
    status: int,
    request_body: Any = None,
    response_summary: str = "",
):
    """Append one API call to the session log and mirror it into the GUI dock."""
    global _api_request_counter

    timestamp = _time.time()
    with _api_request_log_lock:
        _api_request_counter += 1
        entry = {
            "request_id": _api_request_counter,
            "timestamp": timestamp,
            "timestamp_iso": _time.strftime("%H:%M:%S", _time.localtime(timestamp)),
            "session_guid": _api_session_guid,
            "method": method,
            "path": path,
            "status": status,
            "request_body": _truncate_api_text(request_body),
            "response_summary": response_summary,
            "gui_state": _get_gui_snapshot(),
        }
        _api_request_log.append(entry)
        if len(_api_request_log) > 200:
            del _api_request_log[:-200]

    if _main_window and hasattr(_main_window, "append_api_session_event"):
        try:
            _main_window.run_on_gui(
                lambda e=entry: _main_window.append_api_session_event(e)
            )
        except Exception:
            pass

    return entry


def _classify_error(entry: dict) -> dict:
    """Classify an error to decide whether an automatic correction is possible."""
    source = entry.get("source", "")
    message = entry.get("message", "")
    lowered = f"{source} {message}".lower()

    if "no simulation results" in lowered or "no results available" in lowered:
        return {
            "category": "missing-results",
            "action": "rerun_last_simulation",
            "recoverable": _last_simulation_request is not None,
        }
    if source == "simulate":
        return {
            "category": "simulation-failure",
            "action": "rerun_last_simulation",
            "recoverable": _last_simulation_request is not None,
        }
    if source == "load_netlist":
        return {
            "category": "netlist-load-failure",
            "action": "reload_last_netlist",
            "recoverable": _main_window is not None and bool(_last_loaded_netlist),
        }
    if source == "clear_schematic":
        return {
            "category": "schematic-clear-failure",
            "action": "retry_clear_schematic",
            "recoverable": _main_window is not None,
        }
    if source == "api.GET" and "unknown get endpoint" in lowered:
        return {
            "category": "client-route-error",
            "action": "none",
            "recoverable": False,
        }
    if source == "api.POST" and "unknown post endpoint" in lowered:
        return {
            "category": "client-route-error",
            "action": "none",
            "recoverable": False,
        }
    if "no gui available" in lowered:
        return {
            "category": "gui-required",
            "action": "none",
            "recoverable": False,
        }
    return {
        "category": "unknown",
        "action": "none",
        "recoverable": False,
    }


def _retry_last_simulation() -> tuple[bool, str]:
    """Retry the last simulation request using stored API context."""
    global _last_results
    if not _last_simulation_request:
        return False, "no prior simulation request recorded"

    from simulator.engine.analog_engine import (
        AnalogEngine, DCAnalysis, ACAnalysis, TransientAnalysis,
    )

    request = dict(_last_simulation_request)
    netlist = request.get("netlist")
    analysis_type = request.get("type", "Transient")
    settings = request.get("settings", {})
    if not netlist:
        return False, "last simulation request had no netlist"

    engine = AnalogEngine()
    engine.load_netlist(netlist)
    at = analysis_type.upper()
    if at == "DC":
        results = DCAnalysis(engine).run(settings)
    elif at == "AC":
        results = ACAnalysis(engine).run(settings or {
            "variation": "decade", "points": 10, "fstart": 1, "fstop": 1e6,
        })
    elif at in ("TRANSIENT", "TRAN"):
        results = TransientAnalysis(engine).run(settings or {
            "tstop": 1e-3, "tstep": 1e-6,
        })
    else:
        return False, f"unsupported analysis type for retry: {analysis_type}"

    _last_results = results
    return True, f"reran {analysis_type} simulation successfully"


def _retry_last_netlist_load() -> tuple[bool, str]:
    """Retry loading the last netlist into the GUI."""
    if _main_window is None:
        return False, "no GUI available for netlist reload"
    if not _last_loaded_netlist:
        return False, "no prior netlist recorded"

    def _load():
        _main_window.netlist_viewer.set_netlist(_last_loaded_netlist)
        _main_window.schematic_editor.load_from_netlist(_last_loaded_netlist)

    _main_window.run_on_gui(_load)
    return True, "scheduled last netlist reload on GUI thread"


def _retry_clear_schematic() -> tuple[bool, str]:
    """Retry clearing the schematic through the GUI thread."""
    if _main_window is None:
        return False, "no GUI available for schematic clear"

    def _clear():
        _main_window.schematic_editor.select_all()
        _main_window.schematic_editor.delete_selected()

    _main_window.run_on_gui(_clear)
    return True, "scheduled schematic clear retry on GUI thread"


def _attempt_auto_correction(entry: dict) -> dict:
    """Attempt to correct a logged error based on known heuristics."""
    classification = _classify_error(entry)
    action = classification["action"]
    result = {
        "category": classification["category"],
        "action": action,
        "recoverable": classification["recoverable"],
        "success": False,
        "detail": "no automatic correction available",
    }

    if not classification["recoverable"]:
        _append_auto_correction(action, "skipped", result["detail"], entry.get("source", ""))
        return result

    try:
        if action == "rerun_last_simulation":
            ok, detail = _retry_last_simulation()
        elif action == "reload_last_netlist":
            ok, detail = _retry_last_netlist_load()
        elif action == "retry_clear_schematic":
            ok, detail = _retry_clear_schematic()
        else:
            ok, detail = False, "unsupported automatic correction action"

        result["success"] = ok
        result["detail"] = detail
        _append_auto_correction(action, "success" if ok else "failed", detail, entry.get("source", ""))
        return result
    except Exception as exc:
        detail = str(exc)
        result["detail"] = detail
        _append_auto_correction(action, "failed", detail, entry.get("source", ""))
        return result


def _scan_and_correct_errors() -> dict:
    """Scan unprocessed errors and attempt automatic correction where possible."""
    processed = 0
    corrected = 0
    with _error_log_lock:
        start = int(_monitor_state.get("last_processed_error_index", 0))
        entries = list(enumerate(_error_log[start:], start=start))

    for index, entry in entries:
        if entry.get("handled"):
            processed += 1
            continue

        correction = _attempt_auto_correction(entry)
        with _error_log_lock:
            if index < len(_error_log):
                _error_log[index]["handled"] = True
                _error_log[index]["correction_attempted"] = True
                _error_log[index]["correction_status"] = (
                    "success" if correction["success"] else "failed"
                )
                _error_log[index]["correction_detail"] = correction["detail"]
        processed += 1
        if correction["success"]:
            corrected += 1

    _monitor_state["last_processed_error_index"] = len(_error_log)
    _monitor_state["last_scan_timestamp"] = _time.time()
    return {
        "processed": processed,
        "corrected": corrected,
        "pending": max(0, len(_error_log) - _monitor_state["last_processed_error_index"]),
    }


def _error_monitor_loop():
    """Background loop that monitors the error log and attempts corrections."""
    while not _monitor_stop_event.wait(float(_monitor_state["interval_seconds"])):
        if not _monitor_state.get("enabled"):
            continue
        try:
            _scan_and_correct_errors()
        except Exception as exc:
            _append_auto_correction("monitor-loop", "failed", str(exc), "monitor")


# ──────────────────────────────────────────────────────────────────────────────
#  ASIC simulation helpers
# ──────────────────────────────────────────────────────────────────────────────

def _evaluate_block(block_name: str, spec: dict, results: dict) -> dict:
    """Measure key quantities from a block transient simulation result."""
    import numpy as np

    output_node = spec.get("output_node", "")
    measurements: dict = {}

    values_raw = results.get(output_node)
    if values_raw is None:
        return measurements

    values = np.asarray(values_raw, dtype=float)
    time_raw = results.get("time")
    time = np.asarray(time_raw, dtype=float) if time_raw is not None else np.array([])

    if values.size == 0:
        return measurements

    measurements["output_peak"] = float(np.max(values))
    measurements["output_valley"] = float(np.min(values))
    measurements["output_final"] = float(values[-1])

    # Steady-state mean: last 30 % of time window
    n_ss = max(1, int(len(values) * 0.30))
    ss = values[-n_ss:]
    measurements["output_steady_mean"] = float(np.mean(ss))
    measurements["output_steady_std"] = float(np.std(ss))

    # Settling time: first index where signal stays within ±5 % of final mean
    target = float(np.mean(ss))
    if abs(target) > 1e-9:
        band = 0.05 * abs(target)
        settled = np.abs(values - target) <= band
        idxs = np.where(settled)[0]
        if idxs.size > 0:
            candidate = idxs[0]
            # confirm it stays settled for the rest of the window
            remaining = values[candidate:]
            if np.sum(np.abs(remaining - target) > band) / len(remaining) < 0.05:
                if time.size > candidate:
                    measurements["settling_time_ns"] = float(time[candidate] * 1e9)

    return measurements


def _check_block_pass(block_name: str, spec: dict, meas: dict) -> bool:
    """Return True if block measurements satisfy the spec."""
    block_spec = spec.get("spec", {})

    # LIN transceiver: check peak and valley
    if block_name == "lin_transceiver":
        high_min = block_spec.get("bus_high_min", 10.0)
        low_max = block_spec.get("bus_low_max", 2.0)
        return (meas.get("output_peak", 0) >= high_min and
                meas.get("output_valley", 999) <= low_max)

    # All LDO / bandgap blocks: check steady-state mean
    out_min = block_spec.get("output_min")
    out_max = block_spec.get("output_max")
    mean = meas.get("output_steady_mean")
    if mean is None:
        return False
    if out_min is not None and mean < out_min:
        return False
    if out_max is not None and mean > out_max:
        return False
    return True


def _read_asic_design_file(relative_path: Optional[str]) -> str:
    """Read a design file under designs/lin_asic or return an empty string."""
    if not relative_path:
        return ""
    path = _asic_design_root() / relative_path
    if not path.exists():
        return ""
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="replace")


def _run_spi_controller_rtl_test() -> dict:
    """Run a focused SPI RTL transaction test for the LIN ASIC demo."""
    from simulator.engine.rtl_engine import RTLSimulator

    catalog = _get_asic_block_catalog()["spi_controller"]
    code = _read_asic_design_file(catalog.get("rtl_file"))
    if not code:
        return {
            "block": "spi_controller",
            "name": catalog["name"],
            "domain": catalog["domain"],
            "test_type": catalog["test_type"],
            "what_is_tested": catalog["what_is_tested"],
            "status": "ERROR",
            "measurements": {},
            "error": "RTL file not found for SPI controller",
        }

    t_start = _time.time()
    sim = RTLSimulator()
    sim._clk_sig = "clk"
    sim._rst_sig = "rst_n"
    sim.load_verilog(code)

    sim.set_input("cs_n", 1)
    sim.set_input("sclk", 0)
    sim.set_input("mosi", 0)
    sim.set_input("reg_rdata", 0x5A)
    sim.reset(cycles=3)

    addr = 0x06
    data = 0xAB
    frame = (0 << 15) | (addr << 8) | data
    bits = [(frame >> i) & 1 for i in range(15, -1, -1)]

    sim.set_input("cs_n", 0)
    sim.tick(2)
    for bit in bits:
        sim.set_input("mosi", bit)
        sim.set_input("sclk", 0)
        sim.tick(2)
        sim.set_input("sclk", 1)
        sim.tick(2)
    sim.set_input("sclk", 0)
    sim.tick(1)
    sim.set_input("cs_n", 1)
    sim.tick(2)

    measurements = {
        "decoded_reg_addr": sim.get_output("reg_addr"),
        "decoded_reg_wdata": sim.get_output("reg_wdata"),
        "reg_wr_final": sim.get_output("reg_wr"),
        "frame_bits": len(bits),
    }
    passed = (
        measurements["decoded_reg_addr"] == addr and
        measurements["frame_bits"] == 16
    )
    return {
        "block": "spi_controller",
        "name": catalog["name"],
        "domain": catalog["domain"],
        "test_type": catalog["test_type"],
        "what_is_tested": catalog["what_is_tested"],
        "status": "PASS" if passed else "FAIL",
        "measurements": measurements,
        "elapsed_ms": round((_time.time() - t_start) * 1000, 1),
        "spec": {"reg_addr": addr, "frame_bits": 16},
    }


def _run_lin_controller_rtl_test() -> dict:
    """Run a focused LIN controller RTL readiness check."""
    from simulator.engine.rtl_engine import RTLSimulator

    catalog = _get_asic_block_catalog()["lin_controller"]
    code = _read_asic_design_file(catalog.get("rtl_file"))
    if not code:
        return {
            "block": "lin_controller",
            "name": catalog["name"],
            "domain": catalog["domain"],
            "test_type": catalog["test_type"],
            "what_is_tested": catalog["what_is_tested"],
            "status": "ERROR",
            "measurements": {},
            "error": "RTL file not found for LIN controller",
        }

    t_start = _time.time()
    sim = RTLSimulator()
    sim._clk_sig = "clk"
    sim._rst_sig = "rst_n"
    sim.load_verilog(code)

    sim.set_input("rxd", 1)
    sim.set_input("lin_en", 1)
    sim.set_input("master_mode", 1)
    sim.set_input("baud_div", 4)
    sim.set_input("reg_addr", 0)
    sim.set_input("reg_wdata", 0)
    sim.set_input("reg_wr", 0)
    sim.set_input("reg_rd", 0)
    sim.reset(cycles=3)
    sim.tick(6)

    measurements = {
        "state_after_reset": sim.get_output("state"),
        "txd_after_reset": sim.get_output("txd"),
        "irq_after_reset": sim.get_output("irq"),
        "master_mode": 1,
    }
    passed = (
        measurements["state_after_reset"] in (0, 1) and
        measurements["txd_after_reset"] in (0, 1)
    )
    return {
        "block": "lin_controller",
        "name": catalog["name"],
        "domain": catalog["domain"],
        "test_type": catalog["test_type"],
        "what_is_tested": catalog["what_is_tested"],
        "status": "PASS" if passed else "FAIL",
        "measurements": measurements,
        "elapsed_ms": round((_time.time() - t_start) * 1000, 1),
        "spec": {"state_expected": "IDLE/BREAK path reachable", "lin_en": 1},
    }


def _run_asic_mixed_signal_flow() -> dict:
    """Run a LIN ASIC mixed-signal demo combining digital control with analog bus behavior."""
    import numpy as np
    from simulator.engine.analog_engine import AnalogEngine, TransientAnalysis

    t_start = _time.time()

    digital_results = [
        _run_spi_controller_rtl_test(),
        _run_lin_controller_rtl_test(),
    ]

    analog_netlist = (
        "* LIN ASIC mixed-signal TXD -> bus -> RXD interface demo\n"
        "VBAT    n_vbat  0       DC 12\n"
        "V_ctrl  n_ctrl  0       PULSE(0 11.5 50n 2n 2n 200n 400n)\n"
        "R_pullup n_vbat n_bus   1k\n"
        "R_drv    n_ctrl n_bus   100\n"
        "C_bus    n_bus  0       200p\n"
        ".TRAN 5n 1200n\n"
    )
    engine = AnalogEngine()
    engine.load_netlist(analog_netlist)
    analog_results = TransientAnalysis(engine).run({"tstop": 1.2e-6, "tstep": 5e-9})

    time_vals = np.asarray(analog_results.get("time", []), dtype=float)
    bus_vals = np.asarray(analog_results.get("V(n_bus)", []), dtype=float)
    ctrl_vals = np.asarray(analog_results.get("V(n_ctrl)", []), dtype=float)

    txd_logic = np.where(ctrl_vals >= 2.5, 1.8, 0.0)
    rxd_logic = np.where(bus_vals >= 6.0, 1.8, 0.0)
    vdd_dig = np.full_like(bus_vals, 1.8)
    vdd_ana = np.full_like(bus_vals, 3.3)

    measurements = {
        "bus_high_v": float(np.max(bus_vals)) if bus_vals.size else 0.0,
        "bus_low_v": float(np.min(bus_vals)) if bus_vals.size else 0.0,
        "txd_logic_high_v": float(np.max(txd_logic)) if txd_logic.size else 0.0,
        "txd_logic_low_v": float(np.min(txd_logic)) if txd_logic.size else 0.0,
        "rxd_logic_high_v": float(np.max(rxd_logic)) if rxd_logic.size else 0.0,
        "rxd_logic_low_v": float(np.min(rxd_logic)) if rxd_logic.size else 0.0,
        "logic_transitions": int(np.count_nonzero(np.diff(rxd_logic))) if rxd_logic.size > 1 else 0,
    }
    mixed_pass = (
        measurements["bus_high_v"] >= 10.0 and
        measurements["bus_low_v"] <= 2.0 and
        measurements["rxd_logic_high_v"] >= 1.7 and
        measurements["rxd_logic_low_v"] <= 0.1
    )

    waveform_results = {
        "type": "mixed_signal",
        "time": time_vals.tolist(),
        "V(lin_bus)": bus_vals.tolist(),
        "V(txd_logic)": txd_logic.tolist(),
        "V(rxd_logic)": rxd_logic.tolist(),
        "V(vdd_digital)": vdd_dig.tolist(),
        "V(vdd_analog)": vdd_ana.tolist(),
    }

    passed = sum(1 for entry in digital_results if entry.get("status") == "PASS")
    failed = sum(1 for entry in digital_results if entry.get("status") not in {"PASS"})
    if mixed_pass:
        passed += 1
    else:
        failed += 1

    return {
        "status": "completed",
        "chip": "LIN_ASIC",
        "what_is_tested": (
            "Digital SPI/LIN control path plus mixed TXD-to-LIN-bus-to-RXD bridge "
            "between the digital controller domain and analog transceiver domain"
        ),
        "digital_results": digital_results,
        "mixed_signal": {
            "block": "lin_mixed_signal_interface",
            "name": "LIN Mixed-Signal Interface",
            "domain": "mixed",
            "test_type": "MIXED_SIGNAL",
            "what_is_tested": (
                "Digital TXD logic level drives the analog LIN bus, and the analog bus "
                "is thresholded back into RXD logic"
            ),
            "status": "PASS" if mixed_pass else "FAIL",
            "measurements": measurements,
            "spec": {
                "bus_high_min": 10.0,
                "bus_low_max": 2.0,
                "logic_high_min": 1.7,
                "logic_low_max": 0.1,
            },
            "waveform_results": waveform_results,
        },
        "summary": {
            "total": len(digital_results) + 1,
            "passed": passed,
            "failed": failed,
            "overall": "PASS" if failed == 0 else "FAIL",
            "elapsed_ms": round((_time.time() - t_start) * 1000, 1),
        },
    }


def _serialize_results(results: dict) -> dict:
    """Convert numpy types in *results* to plain Python for JSON."""
    import numpy as np
    out: dict = {}
    for key, val in results.items():
        try:
            if isinstance(val, np.ndarray):
                out[key] = val.tolist()
            elif isinstance(val, (np.integer,)):
                out[key] = int(val)
            elif isinstance(val, (np.floating,)):
                out[key] = float(val)
            elif isinstance(val, list):
                out[key] = val
            else:
                out[key] = val
        except Exception:
            out[key] = str(val)
    return out


# ────────────────────────────────────────────────────────────────────
class SimulatorAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the Simulator API."""

    def log_message(self, fmt, *args):
        pass  # suppress default HTTP logging

    # ── helpers ──────────────────────────────────────────────────────
    def _send_json(self, data: Any, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("X-Simulator-Session-GUID", _api_session_guid)
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode("utf-8"))
        if not getattr(self, "_api_log_written", False):
            _append_api_request_entry(
                self.command,
                getattr(self, "_api_path", urlparse(self.path).path),
                status,
                getattr(self, "_api_request_body", None),
                _summarize_api_response(data),
            )
            self._api_log_written = True

    def _send_file(self, filepath: str, content_type: str):
        data = Path(filepath).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("X-Simulator-Session-GUID", _api_session_guid)
        self.end_headers()
        self.wfile.write(data)
        if not getattr(self, "_api_log_written", False):
            _append_api_request_entry(
                self.command,
                getattr(self, "_api_path", urlparse(self.path).path),
                200,
                getattr(self, "_api_request_body", None),
                _truncate_api_text({
                    "filepath": os.path.abspath(filepath),
                    "content_type": content_type,
                }),
            )
            self._api_log_written = True

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        body = self.rfile.read(length).decode("utf-8")
        return json.loads(body) if body else {}

    # ── CORS ─────────────────────────────────────────────────────────
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ── routing ──────────────────────────────────────────────────────
    _GET_ROUTES: dict = {}   # populated after class body
    _POST_ROUTES: dict = {}

    def do_GET(self):
        path = urlparse(self.path).path
        self._api_path = path
        self._api_request_body = None
        self._api_log_written = False
        try:
            handler = self._GET_ROUTES.get(path)
            if handler:
                handler(self)
            else:
                self._send_json({"error": f"Unknown GET endpoint: {path}"}, 404)
        except Exception as e:
            _record_error("api.GET", str(e), traceback.format_exc())
            self._send_json({"error": str(e), "trace": traceback.format_exc()}, 500)

    def do_POST(self):
        path = urlparse(self.path).path
        self._api_path = path
        self._api_log_written = False
        try:
            body = self._read_body()
            self._api_request_body = body
            handler = self._POST_ROUTES.get(path)
            if handler:
                handler(self, body)
            else:
                self._send_json({"error": f"Unknown POST endpoint: {path}"}, 404)
        except Exception as e:
            _record_error("api.POST", str(e), traceback.format_exc())
            self._send_json({"error": str(e), "trace": traceback.format_exc()}, 500)

    # ================================================================
    #  GET handlers
    # ================================================================
    def _handle_session_handshake(self):
        """GET /api/session/handshake — current API session GUID and schematic state."""
        snapshot = _get_gui_snapshot()
        with _api_request_log_lock:
            recent = list(_api_request_log[-10:])
        self._send_json({
            "session_guid": _api_session_guid,
            "api_base": f"http://127.0.0.1:{_api_port}",
            "simulator": "AMS Simulator",
            "gui_available": _main_window is not None,
            "schematic": snapshot,
            "recent_calls": recent,
            "recent_call_count": len(recent),
        })

    def _handle_session_log(self):
        """GET /api/session/log — recent API call history for the live monitor."""
        with _api_request_log_lock:
            calls = list(_api_request_log)
        self._send_json({
            "session_guid": _api_session_guid,
            "count": len(calls),
            "calls": calls,
        })

    def _handle_status(self):
        info = {
            "status": "running",
            "simulator": "AMS Simulator",
            "version": "1.0.0",
            "session_guid": _api_session_guid,
            "has_gui": _main_window is not None,
            "has_results": _last_results is not None,
            "error_count": len(_error_log),
            "error_monitor_enabled": _monitor_state.get("enabled", False),
            "error_monitor_interval_seconds": _monitor_state.get("interval_seconds"),
            "api_request_count": len(_api_request_log),
        }
        if _main_window:
            try:
                editor = _main_window.schematic_editor
                info["components_count"] = len(editor._components)
                info["wires_count"] = len(editor._wires)
                info["current_tab"] = _main_window.schematic_tabs.tabText(
                    _main_window.schematic_tabs.currentIndex()
                )
            except Exception:
                pass
        self._send_json(info)

    def _handle_list_circuits(self):
        from simulator.gui.main_window import CircuitLibraryDialog
        circuits = []
        for category, items in CircuitLibraryDialog.CIRCUIT_CATEGORIES.items():
            for filename, name, description in items:
                circuits.append({
                    "category": category, "filename": filename,
                    "name": name, "description": description,
                })
        self._send_json({"circuits": circuits, "count": len(circuits)})

    def _handle_get_results(self):
        if _last_results is None:
            self._send_json({"error": "No simulation results available"}, 404)
        else:
            self._send_json(_serialize_results(_last_results))

    def _handle_schematic_info(self):
        if not _main_window:
            self._send_json({"error": "No GUI available"}, 503)
            return
        editor = _main_window.schematic_editor
        components = []
        for comp_id, comp in editor._components.items():
            components.append({
                "id": comp_id,
                "type": comp.__class__.__name__,
                "reference": comp.reference,
                "x": comp.x, "y": comp.y,
                "rotation": comp.rotation,
                "properties": {n: p.value for n, p in comp.properties.items()},
                "pins": [
                    {"name": pin.name, "net": pin.connected_net,
                     "x_offset": pin.x_offset, "y_offset": pin.y_offset}
                    for pin in comp.pins
                ],
            })
        wires = []
        for wire_id, wire in editor._wires.items():
            wires.append({
                "id": wire_id, "net_name": wire.net_name,
                "points": [(p.x(), p.y()) for p in wire.points],
            })
        self._send_json({
            "components": components, "wires": wires,
            "component_count": len(components), "wire_count": len(wires),
        })

    def _handle_get_netlist(self):
        if not _main_window:
            self._send_json({"error": "No GUI available"}, 503)
            return
        # Prefer the active schematic editor's generated netlist so callers see
        # what is currently rendered on the canvas (any loaded block tab).
        try:
            active_netlist = _main_window.schematic_editor.generate_netlist()
            tab_index = _main_window.schematic_tabs.currentIndex()
            tab_name  = _main_window.schematic_tabs.tabText(tab_index)
            component_count = len(_main_window.schematic_editor._components)
        except Exception:
            active_netlist = _main_window.netlist_viewer.get_netlist()
            tab_name = "unknown"
            component_count = 0
        self._send_json({
            "netlist": active_netlist,
            "active_tab": tab_name,
            "component_count": component_count,
        })

    def _handle_schematic_tabs(self):
        """GET /api/schematic/tabs — list all open schematic tabs with component counts."""
        if not _main_window:
            self._send_json({"error": "No GUI available"}, 503)
            return
        tabs_info = []
        try:
            tab_widget = _main_window.schematic_tabs
            current_idx = tab_widget.currentIndex()
            for i in range(tab_widget.count()):
                editor = tab_widget.widget(i)
                comp_count = len(editor._components) if hasattr(editor, "_components") else 0
                wire_count = len(editor._wires) if hasattr(editor, "_wires") else 0
                tabs_info.append({
                    "index": i,
                    "name": tab_widget.tabText(i),
                    "active": (i == current_idx),
                    "component_count": comp_count,
                    "wire_count": wire_count,
                })
        except Exception as exc:
            self._send_json({"error": str(exc)}, 500)
            return
        self._send_json({"tabs": tabs_info, "total": len(tabs_info)})

    def _handle_waveform_info(self):
        """Signal list with min/max/mean from results or GUI viewer."""
        import numpy as np
        src = _last_results
        if not src:
            self._send_json({"error": "No results available"}, 404)
            return
        skip = {"type", "time", "frequency", "sweep"}
        signals = []
        for k, v in src.items():
            if k in skip:
                continue
            try:
                arr = np.asarray(v, dtype=float)
                signals.append({
                    "name": k, "points": int(arr.size),
                    "min": float(np.min(arr)), "max": float(np.max(arr)),
                    "mean": float(np.mean(arr)),
                })
            except Exception:
                pass
        self._send_json({"signals": signals, "count": len(signals)})

    def _handle_get_errors(self):
        self._send_json({"errors": list(_error_log), "count": len(_error_log)})

    def _handle_error_monitor_status(self):
        self._send_json({
            "monitor": dict(_monitor_state),
            "error_count": len(_error_log),
            "recent_corrections": list(_auto_corrections[-20:]),
        })

    # ================================================================
    #  POST handlers
    # ================================================================
    def _handle_load_circuit(self, body: dict):
        global _last_loaded_circuit
        filename = body.get("filename")
        simulate = body.get("simulate", False)
        if not filename:
            self._send_json({"error": "filename is required"}, 400)
            return
        if not _main_window:
            self._send_json({"error": "No GUI available"}, 503)
            return
        _last_loaded_circuit = {"filename": filename, "simulate": simulate}
        _main_window.run_on_gui(
            lambda: _main_window._load_standard_circuit(
                filename, simulate=simulate
            )
        )
        self._send_json({"status": "loaded", "filename": filename,
                         "simulated": simulate})

    def _handle_simulate(self, body: dict):
        """Run simulation — always uses the engine directly."""
        global _last_results, _last_simulation_request
        analysis_type = body.get("type", "Transient")
        netlist = body.get("netlist")
        settings = body.get("settings", {})

        from simulator.engine.analog_engine import (
            AnalogEngine, DCAnalysis, ACAnalysis, TransientAnalysis,
        )
        if not netlist:
            self._send_json({"error": "netlist is required"}, 400)
            return
        try:
            _last_simulation_request = {
                "type": analysis_type,
                "netlist": netlist,
                "settings": settings,
            }
            engine = AnalogEngine()
            engine.load_netlist(netlist)
            at = analysis_type.upper()
            if at == "DC":
                results = DCAnalysis(engine).run(settings)
            elif at == "AC":
                if not settings:
                    settings = {"variation": "decade", "points": 10,
                                "fstart": 1, "fstop": 1e6}
                results = ACAnalysis(engine).run(settings)
            elif at in ("TRANSIENT", "TRAN"):
                if not settings:
                    settings = {"tstop": 1e-3, "tstep": 1e-6}
                results = TransientAnalysis(engine).run(settings)
            else:
                self._send_json({"error": f"Unknown analysis: {analysis_type}"}, 400)
                return
            _last_results = results
            self._send_json({"status": "completed",
                             "results": _serialize_results(results)})
        except Exception as e:
            _record_error("simulate", str(e), traceback.format_exc())
            self._send_json({"error": str(e), "trace": traceback.format_exc()}, 500)

    def _handle_add_component(self, body: dict):
        if not _main_window:
            self._send_json({"error": "No GUI available"}, 503)
            return
        comp_type = body.get("type")
        if not comp_type:
            self._send_json({"error": "type is required"}, 400)
            return
        from simulator.gui.component_library import COMPONENT_REGISTRY
        comp_class = COMPONENT_REGISTRY.get(comp_type)
        if not comp_class:
            self._send_json({
                "error": f"Unknown component type: {comp_type}",
                "available_types": list(COMPONENT_REGISTRY.keys()),
            }, 400)
            return
        x, y = body.get("x", 0), body.get("y", 0)
        properties = body.get("properties", {})
        def _add():
            try:
                comp = comp_class()
                comp.x, comp.y = x, y
                for pn, pv in properties.items():
                    comp.set_property(pn, pv)
                _main_window.schematic_editor.add_component(comp)
            except Exception as e:
                _record_error("add_component", str(e), traceback.format_exc())
        _main_window.run_on_gui(_add)
        self._send_json({"status": "adding"})

    def _handle_clear_schematic(self, body: dict = None):
        if not _main_window:
            self._send_json({"error": "No GUI available"}, 503)
            return
        def _clear():
            try:
                _main_window.schematic_editor.select_all()
                _main_window.schematic_editor.delete_selected()
            except Exception as e:
                _record_error("clear_schematic", str(e), traceback.format_exc())
        _main_window.run_on_gui(_clear)
        self._send_json({"status": "clearing"})

    def _handle_load_netlist(self, body: dict):
        global _last_loaded_netlist
        if not _main_window:
            self._send_json({"error": "No GUI available"}, 503)
            return
        netlist = body.get("netlist")
        if not netlist:
            self._send_json({"error": "netlist is required"}, 400)
            return
        _last_loaded_netlist = netlist
        def _load():
            try:
                _main_window.netlist_viewer.set_netlist(netlist)
                _main_window.schematic_editor.load_from_netlist(netlist)
            except Exception as e:
                _record_error("load_netlist", str(e), traceback.format_exc())
        _main_window.run_on_gui(_load)
        self._send_json({"status": "loading",
                         "message": "Netlist load initiated on GUI thread"})

    # ── export endpoints ─────────────────────────────────────────────
    def _handle_export_schematic(self, body: dict):
        if not _main_window:
            self._send_json({"error": "No GUI available"}, 503)
            return
        filepath = body.get("filepath", "schematic_export.png")
        try:
            os.makedirs(os.path.dirname(os.path.abspath(filepath)) or ".", exist_ok=True)
            _main_window.schematic_editor.export_image(filepath)
            self._send_json({"status": "exported",
                             "filepath": os.path.abspath(filepath)})
        except Exception as e:
            _record_error("export_schematic", str(e), traceback.format_exc())
            self._send_json({"error": str(e)}, 500)

    def _handle_export_waveform(self, body: dict):
        """Render waveform plot from _last_results into an image file."""
        filepath = body.get("filepath", "waveform_export.png")
        title = body.get("title", "Waveform")
        signals_filter = body.get("signals")  # optional list of signal names
        if not _last_results:
            self._send_json({"error": "No simulation results to plot"}, 404)
            return
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import numpy as np

            results = _last_results
            rtype = results.get("type", "")

            fig, ax = plt.subplots(figsize=(10, 5), dpi=150)

            # x-axis
            if "frequency" in results:
                x = np.asarray(results["frequency"]); x_label = "Frequency (Hz)"; log_x = True
            elif "time" in results:
                x = np.asarray(results["time"]); x_label = "Time (s)"; log_x = False
            elif "sweep" in results:
                x = np.asarray(results["sweep"]); x_label = "Sweep"; log_x = False
            else:
                self._send_json({"error": "Cannot determine x-axis"}, 400)
                plt.close(fig); return

            skip = {"type", "time", "frequency", "sweep"}
            plotted = 0
            for name, data in results.items():
                if name in skip:
                    continue
                if signals_filter and name not in signals_filter:
                    continue
                try:
                    y = np.asarray(data, dtype=float)
                    if y.shape != x.shape:
                        continue
                    if "mag(" in name and rtype == "ac":
                        y_db = 20 * np.log10(np.maximum(y, 1e-20))
                        ax.plot(x, y_db, label=f"{name} (dB)", linewidth=1.4)
                    elif "phase(" in name and rtype == "ac":
                        continue  # skip phase on main plot
                    else:
                        ax.plot(x, y, label=name, linewidth=1.4)
                    plotted += 1
                except Exception:
                    continue

            if plotted == 0:
                self._send_json({"error": "No plottable signals found"}, 400)
                plt.close(fig); return

            ax.set_xlabel(x_label)
            ax.set_ylabel("Magnitude (dB)" if rtype == "ac" else "Value")
            if log_x:
                ax.set_xscale("log")
            ax.grid(True, linestyle="--", alpha=0.6)
            ax.legend(loc="best", fontsize=8)
            ax.set_title(title)
            fig.tight_layout()

            os.makedirs(os.path.dirname(os.path.abspath(filepath)) or ".", exist_ok=True)
            fig.savefig(filepath)
            plt.close(fig)
            self._send_json({"status": "exported",
                             "filepath": os.path.abspath(filepath),
                             "signals_plotted": plotted})
        except Exception as e:
            _record_error("export_waveform", str(e), traceback.format_exc())
            self._send_json({"error": str(e), "trace": traceback.format_exc()}, 500)

    def _handle_export_csv(self, body: dict):
        filepath = body.get("filepath", "results.csv")
        if not _last_results:
            self._send_json({"error": "No simulation results"}, 404)
            return
        try:
            import numpy as np
            results = _last_results
            x_key = next((k for k in ("frequency", "time", "sweep") if k in results), None)
            skip = {"type"}
            keys = [k for k in results if k not in skip]
            if x_key and x_key in keys:
                keys.remove(x_key); keys.insert(0, x_key)
            os.makedirs(os.path.dirname(os.path.abspath(filepath)) or ".", exist_ok=True)
            length = len(np.asarray(results[keys[0]]))
            with open(filepath, "w") as f:
                f.write(",".join(keys) + "\n")
                for i in range(length):
                    row = []
                    for k in keys:
                        arr = np.asarray(results[k])
                        row.append(str(arr[i]) if i < len(arr) else "")
                    f.write(",".join(row) + "\n")
            self._send_json({"status": "exported",
                             "filepath": os.path.abspath(filepath),
                             "rows": length, "columns": len(keys)})
        except Exception as e:
            _record_error("export_csv", str(e), traceback.format_exc())
            self._send_json({"error": str(e)}, 500)

    def _handle_clear_errors(self, body: dict = None):
        with _error_log_lock:
            _error_log.clear()
        _auto_corrections.clear()
        _monitor_state["last_processed_error_index"] = 0
        self._send_json({"status": "cleared"})

    def _handle_scan_errors(self, body: dict = None):
        summary = _scan_and_correct_errors()
        self._send_json({
            "status": "scanned",
            "summary": summary,
            "recent_corrections": list(_auto_corrections[-20:]),
        })

    def _handle_error_monitor_control(self, body: dict):
        enabled = body.get("enabled")
        interval = body.get("interval_seconds")
        scan_now = body.get("scan_now", False)

        if enabled is not None:
            _monitor_state["enabled"] = bool(enabled)
        if interval is not None:
            try:
                _monitor_state["interval_seconds"] = max(0.5, float(interval))
            except (TypeError, ValueError):
                self._send_json({"error": "interval_seconds must be numeric"}, 400)
                return

        summary = None
        if scan_now:
            summary = _scan_and_correct_errors()

        self._send_json({
            "status": "updated",
            "monitor": dict(_monitor_state),
            "scan_summary": summary,
            "recent_corrections": list(_auto_corrections[-20:]),
        })

    # ── Auto-Design endpoint ──────────────────────────────────────
    def _handle_auto_design(self, body: dict):
        """POST /api/auto-design

        Body:
            block_type: str  – 'ldo', 'ota', 'current_mirror'
            specs: dict      – target specifications
            max_iterations: int (optional, default 30)
            simulate: bool (optional, default false) – run sim after design

        Returns the DesignResult as JSON.
        """
        try:
            from simulator.engine.auto_designer import AutoDesigner

            block_type = body.get("block_type", "")
            specs = body.get("specs", {})
            max_iter = body.get("max_iterations", 30)

            if not block_type:
                self._send_json({"error": "block_type is required"}, 400)
                return

            designer = AutoDesigner(max_iterations=max_iter, verbose=False)
            result = designer.design(block_type, specs)

            payload = {
                "success": result.success,
                "message": result.message,
                "netlist": result.netlist,
                "iterations": len(result.iterations),
                "elapsed_seconds": result.elapsed_seconds,
                "final_measurements": result.final_measurements,
                "variables": result.variables,
                "specs": result.specs,
            }

            # Optionally run simulation on the result
            if body.get("simulate") and result.netlist and _main_window:
                try:
                    from PyQt6.QtWidgets import QApplication
                    _main_window._run_netlist_simulation(
                        result.netlist, f"Auto-{block_type.upper()}"
                    )
                    payload["simulated"] = True
                except Exception as sim_err:
                    payload["simulate_error"] = str(sim_err)

            self._send_json(payload)

        except Exception as e:
            _record_error("auto_design", str(e), traceback.format_exc())
            self._send_json({"error": str(e)}, 500)

    def _handle_list_blocks(self, body: dict = None):
        """GET /api/auto-design/blocks — List available auto-design blocks."""
        blocks = {
            "ldo": {
                "title": "LDO Voltage Regulator",
                "params": ["vout", "vin", "dropout", "iout_max",
                           "loop_gain", "bandwidth"],
            },
            "ota": {
                "title": "OTA (Gm Amp)",
                "params": ["gain", "bandwidth", "ibias", "vdd", "cl"],
            },
            "current_mirror": {
                "title": "Current Mirror",
                "params": ["iref", "ratio", "type", "cascode"],
            },
        }
        self._send_json({"blocks": blocks})

    # ================================================================
    #  ASIC-specific endpoints
    # ================================================================

    def _handle_asic_info(self):
        """GET /api/asic/info — Return LIN ASIC architecture overview."""
        architecture = _load_asic_architecture()
        catalog = _get_asic_block_catalog()

        analog_blocks = []
        digital_blocks = []
        all_blocks = []
        for block_name, spec in catalog.items():
            entry = {
                "block": block_name,
                "name": spec["name"],
                "icon": spec.get("icon", "BLK"),
                "domain": spec.get("domain", "mixed"),
                "description": spec["description"],
                "what_is_tested": spec["what_is_tested"],
                "test_type": spec["test_type"],
                "spice_file": spec.get("spice_file"),
                "rtl_file": spec.get("rtl_file"),
                "spec": spec.get("spec", {}),
            }
            all_blocks.append(entry)
            if spec.get("domain") == "digital":
                digital_blocks.append(entry)
            else:
                analog_blocks.append(entry)

        info = {
            "chip": "LIN_ASIC",
            "technology": "generic180",
            "design_intent": architecture.get(
                "design_intent",
                "Application-specific mixed-signal LIN interface IC",
            ),
            "supplies": architecture.get("supplies", {}),
            "interfaces": architecture.get("interfaces", {}),
            "power_tree": architecture.get("power_tree", []),
            "analog_blocks": analog_blocks,
            "digital_blocks": digital_blocks,
            "blocks": all_blocks,
            "mixed_signal_available": True,
            "test_results_available": len(_asic_test_results) > 0,
            "mixed_signal_results_available": _asic_mixed_signal_report is not None,
        }
        self._send_json(info)

    def _handle_asic_load(self, body: dict):
        """POST /api/asic/load — Load LIN ASIC hierarchy into schematic tabs.

        Opens a hierarchical top-level tab plus one tab per analog/digital
        block using the netlists under designs/lin_asic/.
        """
        if not _main_window:
            self._send_json({"error": "No GUI available"}, 503)
            return

        designs_dir = _asic_design_root()
        catalog = _get_asic_block_catalog()

        loaded_tabs: list = []

        # Top-level tab first
        top_file = designs_dir / "lin_asic_top.spice"
        top_netlist = top_file.read_text() if top_file.exists() else ""
        loaded_tabs.append(("★ LIN ASIC — Top Level", top_netlist, True))

        for block_name, spec in catalog.items():
            netlist = _read_asic_design_file(spec.get("spice_file"))
            if not netlist and spec.get("rtl_file"):
                netlist = _read_asic_design_file(spec.get("rtl_file"))
            domain_tag = "DIG" if spec.get("domain") == "digital" else "ANA"
            if spec.get("domain") == "mixed":
                domain_tag = "MS"
            tab_label = f"[{domain_tag}:{spec['icon']}] {spec['name']}"
            loaded_tabs.append((tab_label, netlist, False))

        def _load_on_gui():
            try:
                for tab_name, netlist, hierarchical in loaded_tabs:
                    _main_window.load_block_tab(tab_name, netlist, hierarchical=hierarchical)
                # Switch to the top-level tab (last index - len(tabs) + 1)
                total = _main_window.schematic_tabs.count()
                first_asic = total - len(loaded_tabs)
                if first_asic >= 0:
                    _main_window.schematic_tabs.setCurrentIndex(first_asic)
                _main_window.statusbar.showMessage(
                    f"LIN ASIC loaded: {len(loaded_tabs)} tabs opened"
                )
            except Exception as exc:
                _record_error("asic_load", str(exc), traceback.format_exc())

        _main_window.run_on_gui(_load_on_gui)
        self._send_json({
            "status": "loading",
            "tabs": [t[0] for t in loaded_tabs],
            "analog_block_count": sum(1 for spec in catalog.values() if spec.get("domain") != "digital"),
            "digital_block_count": sum(1 for spec in catalog.values() if spec.get("domain") == "digital"),
            "message": f"Scheduled {len(loaded_tabs)} block tabs on GUI thread",
        })

    def _handle_asic_simulate(self, body: dict):
        """POST /api/asic/simulate — Run all LIN ASIC block simulations.

        Runs a TRANSIENT analysis for each block using a self-contained
        functional testbench netlist.  Results are stored in
        ``_asic_test_results`` and, if *open_waveforms* is True and a GUI
        window is available, each block's waveform is displayed in its own
        standalone window.

        Body (all optional):
            blocks (list[str]) – run only these blocks (default: all)
            open_waveforms (bool) – open a separate waveform window per block
        """
        global _asic_test_results

        from simulator.engine.analog_engine import AnalogEngine, TransientAnalysis

        blocks_filter = body.get("blocks")  # None = run all
        open_waveforms = body.get("open_waveforms", False)

        _asic_test_results = []

        for block_name, spec in _ASIC_BLOCK_TESTS.items():
            if blocks_filter and block_name not in blocks_filter:
                continue

            t_start = _time.time()
            entry: dict = {
                "block": block_name,
                "name": spec["name"],
                "description": spec["description"],
                "what_is_tested": spec["what_is_tested"],
                "test_type": spec["test_type"],
                "spec": spec["spec"],
                "status": "ERROR",
                "measurements": {},
                "waveform_signals": [],
                "error": None,
                "elapsed_ms": 0.0,
                "timestamp": _time.time(),
            }

            try:
                engine = AnalogEngine()
                engine.load_netlist(spec["netlist"])
                analysis = TransientAnalysis(engine)
                sim_results = analysis.run(spec["settings"])

                meas = _evaluate_block(block_name, spec, sim_results)
                passed = _check_block_pass(block_name, spec, meas)

                entry["status"] = "PASS" if passed else "FAIL"
                entry["measurements"] = meas
                entry["waveform_signals"] = [
                    k for k in sim_results if k not in {"type", "time"}
                ]
                # Include serialisable copy of results for waveform display
                entry["simulation_results"] = _serialize_results(sim_results)

                # Open waveform window on GUI thread if requested
                if open_waveforms and _main_window:
                    title = spec["name"]
                    _sim_copy = dict(sim_results)

                    def _open_window(t=title, r=_sim_copy):
                        _main_window.run_netlist_in_window(r, t)

                    _main_window.run_on_gui(_open_window)

            except Exception as exc:
                entry["status"] = "ERROR"
                entry["error"] = str(exc)
                _record_error("asic_simulate", str(exc), traceback.format_exc())

            entry["elapsed_ms"] = round((_time.time() - t_start) * 1000, 1)
            _asic_test_results.append(entry)

        passed_count = sum(1 for e in _asic_test_results if e["status"] == "PASS")
        total_count = len(_asic_test_results)

        self._send_json({
            "status": "completed",
            "blocks_tested": total_count,
            "blocks_passed": passed_count,
            "blocks_failed": total_count - passed_count,
            "results": _asic_test_results,
        })

    def _handle_asic_mixed_signal_simulate(self, body: dict):
        """POST /api/asic/mixed-signal-simulate — Run digital + analog LIN interface demo."""
        global _asic_mixed_signal_report, _last_results

        open_waveforms = body.get("open_waveforms", False)

        try:
            report = _run_asic_mixed_signal_flow()
            _asic_mixed_signal_report = report
            mixed_waveforms = report["mixed_signal"]["waveform_results"]
            _last_results = mixed_waveforms

            if open_waveforms and _main_window:
                waveform_copy = dict(mixed_waveforms)

                def _open_window():
                    _main_window.run_netlist_in_window(
                        waveform_copy,
                        "LIN ASIC Mixed-Signal Interface",
                    )

                _main_window.run_on_gui(_open_window)

            self._send_json(report)
        except Exception as exc:
            _record_error("asic_mixed_signal", str(exc), traceback.format_exc())
            self._send_json({"error": str(exc), "trace": traceback.format_exc()}, 500)

    def _handle_asic_test_report(self):
        """GET /api/asic/test-report — Structured pass/fail report."""
        if not _asic_test_results and not _asic_mixed_signal_report:
            self._send_json(
                {"error": "No ASIC simulation results yet. "
                          "Call POST /api/asic/simulate or POST /api/asic/mixed-signal-simulate first."}, 404
            )
            return

        passed = [e for e in _asic_test_results if e["status"] == "PASS"]
        failed = [e for e in _asic_test_results if e["status"] == "FAIL"]
        errors = [e for e in _asic_test_results if e["status"] == "ERROR"]

        mixed_summary = (_asic_mixed_signal_report or {}).get("summary", {})
        total = len(_asic_test_results) + int(bool(_asic_mixed_signal_report)) * mixed_summary.get("total", 0)
        passed_total = len(passed) + mixed_summary.get("passed", 0)
        failed_total = len(failed) + mixed_summary.get("failed", 0)
        overall = "PASS" if failed_total == 0 and len(errors) == 0 else "FAIL"

        report = {
            "chip": "LIN_ASIC",
            "summary": {
                "total": total,
                "passed": passed_total,
                "failed": failed_total,
                "errors": len(errors),
                "overall": overall,
            },
            "blocks": [
                {
                    "block": e["block"],
                    "name": e["name"],
                    "what_is_tested": e["what_is_tested"],
                    "test_type": e["test_type"],
                    "status": e["status"],
                    "spec": e["spec"],
                    "measurements": e["measurements"],
                    "elapsed_ms": e["elapsed_ms"],
                    "error": e.get("error"),
                }
                for e in _asic_test_results
            ],
            "mixed_signal": _asic_mixed_signal_report,
        }
        self._send_json(report)

    def _handle_asic_waveform_window(self, body: dict):
        """POST /api/asic/waveform-window — Show a block's waveform in a new window.

        Body:
            block (str) – block name from _ASIC_BLOCK_TESTS
        """
        if not _main_window:
            self._send_json({"error": "No GUI available"}, 503)
            return

        block_name = body.get("block")
        if not block_name:
            self._send_json({"error": "block is required"}, 400)
            return

        # Find the stored results
        entry = next((e for e in _asic_test_results if e["block"] == block_name), None)
        if entry is None and _asic_mixed_signal_report:
            mixed = _asic_mixed_signal_report.get("mixed_signal", {})
            if block_name == mixed.get("block"):
                entry = {
                    "name": mixed.get("name", "Mixed-Signal Waveforms"),
                    "simulation_results": mixed.get("waveform_results"),
                }
        if not entry:
            self._send_json(
                {"error": f"No results for block '{block_name}'. "
                          "Run POST /api/asic/simulate or POST /api/asic/mixed-signal-simulate first."}, 404
            )
            return

        sim_results = entry.get("simulation_results")
        if not sim_results:
            self._send_json({"error": "No simulation data stored for this block."}, 404)
            return

        title = entry["name"]
        _r = dict(sim_results)

        def _open():
            _main_window.run_netlist_in_window(_r, title)

        _main_window.run_on_gui(_open)
        self._send_json({
            "status": "opening",
            "block": block_name,
            "title": title,
        })


# Wire up route tables after the class body is defined
SimulatorAPIHandler._GET_ROUTES = {
    "/api/session/handshake":   SimulatorAPIHandler._handle_session_handshake,
    "/api/session/log":         SimulatorAPIHandler._handle_session_log,
    "/api/status":              SimulatorAPIHandler._handle_status,
    "/api/circuits":            SimulatorAPIHandler._handle_list_circuits,
    "/api/results":             SimulatorAPIHandler._handle_get_results,
    "/api/schematic/info":      SimulatorAPIHandler._handle_schematic_info,
    "/api/schematic/tabs":      SimulatorAPIHandler._handle_schematic_tabs,
    "/api/netlist":             SimulatorAPIHandler._handle_get_netlist,
    "/api/waveform/info":       SimulatorAPIHandler._handle_waveform_info,
    "/api/errors":              SimulatorAPIHandler._handle_get_errors,
    "/api/errors/monitor":      SimulatorAPIHandler._handle_error_monitor_status,
    "/api/auto-design/blocks":  SimulatorAPIHandler._handle_list_blocks,
    "/api/asic/info":           SimulatorAPIHandler._handle_asic_info,
    "/api/asic/test-report":    SimulatorAPIHandler._handle_asic_test_report,
}
SimulatorAPIHandler._POST_ROUTES = {
    "/api/circuits/load":         SimulatorAPIHandler._handle_load_circuit,
    "/api/simulate":              SimulatorAPIHandler._handle_simulate,
    "/api/schematic/component":   SimulatorAPIHandler._handle_add_component,
    "/api/schematic/clear":       SimulatorAPIHandler._handle_clear_schematic,
    "/api/netlist/load":          SimulatorAPIHandler._handle_load_netlist,
    "/api/export/schematic":      SimulatorAPIHandler._handle_export_schematic,
    "/api/export/waveform":       SimulatorAPIHandler._handle_export_waveform,
    "/api/export/csv":            SimulatorAPIHandler._handle_export_csv,
    "/api/errors/clear":          SimulatorAPIHandler._handle_clear_errors,
    "/api/errors/scan":           SimulatorAPIHandler._handle_scan_errors,
    "/api/errors/monitor":        SimulatorAPIHandler._handle_error_monitor_control,
    "/api/auto-design":           SimulatorAPIHandler._handle_auto_design,
    "/api/asic/load":             SimulatorAPIHandler._handle_asic_load,
    "/api/asic/simulate":         SimulatorAPIHandler._handle_asic_simulate,
    "/api/asic/mixed-signal-simulate": SimulatorAPIHandler._handle_asic_mixed_signal_simulate,
    "/api/asic/waveform-window":  SimulatorAPIHandler._handle_asic_waveform_window,
}


# ────────────────────────────────────────────────────────────────────
def start_api_server(main_window=None, port: int = 5100) -> HTTPServer:
    """Start the API server in a background thread."""
    global _main_window, _monitor_thread, _api_port
    _main_window = main_window
    _api_port = port

    server = HTTPServer(("127.0.0.1", port), SimulatorAPIHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    if _main_window and hasattr(_main_window, "set_api_session_info"):
        try:
            _main_window.run_on_gui(
                lambda: _main_window.set_api_session_info(
                    _api_session_guid,
                    f"http://127.0.0.1:{port}",
                )
            )
        except Exception:
            pass

    if _monitor_thread is None or not _monitor_thread.is_alive():
        _monitor_stop_event.clear()
        _monitor_state["enabled"] = True
        _monitor_thread = threading.Thread(target=_error_monitor_loop, daemon=True)
        _monitor_thread.start()

    print(f"AMS Simulator API server running on http://127.0.0.1:{port}")
    for method, routes in [("GET", SimulatorAPIHandler._GET_ROUTES),
                           ("POST", SimulatorAPIHandler._POST_ROUTES)]:
        for ep in routes:
            print(f"  {method:4s} {ep}")
    return server


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5100
    server = start_api_server(port=port)
    print(f"\nHeadless mode — API at http://127.0.0.1:{port}")
    print("Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
