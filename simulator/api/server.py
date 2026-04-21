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

    from PyQt6.QtCore import QTimer

    def _load():
        _main_window.netlist_viewer.set_netlist(_last_loaded_netlist)
        _main_window.schematic_editor.load_from_netlist(_last_loaded_netlist)

    QTimer.singleShot(0, _load)
    return True, "scheduled last netlist reload on GUI thread"


def _retry_clear_schematic() -> tuple[bool, str]:
    """Retry clearing the schematic through the GUI thread."""
    if _main_window is None:
        return False, "no GUI available for schematic clear"

    from PyQt6.QtCore import QTimer

    def _clear():
        _main_window.schematic_editor.select_all()
        _main_window.schematic_editor.delete_selected()

    QTimer.singleShot(0, _clear)
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
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode("utf-8"))

    def _send_file(self, filepath: str, content_type: str):
        data = Path(filepath).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

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
        try:
            body = self._read_body()
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
    def _handle_status(self):
        info = {
            "status": "running",
            "simulator": "AMS Simulator",
            "version": "1.0.0",
            "has_gui": _main_window is not None,
            "has_results": _last_results is not None,
            "error_count": len(_error_log),
            "error_monitor_enabled": _monitor_state.get("enabled", False),
            "error_monitor_interval_seconds": _monitor_state.get("interval_seconds"),
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
        netlist = _main_window.netlist_viewer.get_netlist()
        self._send_json({"netlist": netlist})

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
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, lambda: _main_window._load_standard_circuit(
            filename, simulate=simulate))
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
        from PyQt6.QtCore import QTimer
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
        QTimer.singleShot(0, _add)
        self._send_json({"status": "adding"})

    def _handle_clear_schematic(self, body: dict = None):
        if not _main_window:
            self._send_json({"error": "No GUI available"}, 503)
            return
        from PyQt6.QtCore import QTimer
        def _clear():
            try:
                _main_window.schematic_editor.select_all()
                _main_window.schematic_editor.delete_selected()
            except Exception as e:
                _record_error("clear_schematic", str(e), traceback.format_exc())
        QTimer.singleShot(0, _clear)
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
        from PyQt6.QtCore import QTimer
        def _load():
            try:
                _main_window.netlist_viewer.set_netlist(netlist)
                _main_window.schematic_editor.load_from_netlist(netlist)
            except Exception as e:
                _record_error("load_netlist", str(e), traceback.format_exc())
        QTimer.singleShot(0, _load)
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


# Wire up route tables after the class body is defined
SimulatorAPIHandler._GET_ROUTES = {
    "/api/status":         SimulatorAPIHandler._handle_status,
    "/api/circuits":       SimulatorAPIHandler._handle_list_circuits,
    "/api/results":        SimulatorAPIHandler._handle_get_results,
    "/api/schematic/info": SimulatorAPIHandler._handle_schematic_info,
    "/api/netlist":        SimulatorAPIHandler._handle_get_netlist,
    "/api/waveform/info":  SimulatorAPIHandler._handle_waveform_info,
    "/api/errors":         SimulatorAPIHandler._handle_get_errors,
    "/api/errors/monitor": SimulatorAPIHandler._handle_error_monitor_status,
    "/api/auto-design/blocks": SimulatorAPIHandler._handle_list_blocks,
}
SimulatorAPIHandler._POST_ROUTES = {
    "/api/circuits/load":       SimulatorAPIHandler._handle_load_circuit,
    "/api/simulate":            SimulatorAPIHandler._handle_simulate,
    "/api/schematic/component": SimulatorAPIHandler._handle_add_component,
    "/api/schematic/clear":     SimulatorAPIHandler._handle_clear_schematic,
    "/api/netlist/load":        SimulatorAPIHandler._handle_load_netlist,
    "/api/export/schematic":    SimulatorAPIHandler._handle_export_schematic,
    "/api/export/waveform":     SimulatorAPIHandler._handle_export_waveform,
    "/api/export/csv":          SimulatorAPIHandler._handle_export_csv,
    "/api/errors/clear":        SimulatorAPIHandler._handle_clear_errors,
    "/api/errors/scan":         SimulatorAPIHandler._handle_scan_errors,
    "/api/errors/monitor":      SimulatorAPIHandler._handle_error_monitor_control,
    "/api/auto-design":         SimulatorAPIHandler._handle_auto_design,
}


# ────────────────────────────────────────────────────────────────────
def start_api_server(main_window=None, port: int = 5100) -> HTTPServer:
    """Start the API server in a background thread."""
    global _main_window, _monitor_thread
    _main_window = main_window

    server = HTTPServer(("127.0.0.1", port), SimulatorAPIHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

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
