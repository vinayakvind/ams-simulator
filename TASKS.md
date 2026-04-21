# AMS Simulator — Task Board & Review Status

> Updated: 2026-04-21  
> Branch: `master` (HEAD: see `git log --oneline -1`)

---

## Legend
| Symbol | Meaning |
|--------|---------|
| ✅ | Done & verified |
| 🔄 | In progress |
| ❌ | Known gap / TODO |
| ⚠️ | Partial / needs more work |

---

## 1. GUI — Schematic Editor

| Task | Status | Notes |
|------|--------|-------|
| Schematic canvas renders components | ✅ | `SchematicEditor` with `QGraphicsScene` |
| Wire routing (orthogonal) | ✅ | Auto-connected via net names |
| Load from SPICE netlist | ✅ | `load_from_netlist()` — Phases 1-3 |
| **SUBCKT-only block files show blank canvas** | ✅ **FIXED** | Phase 1.5 added — falls back to first SUBCKT body if no top-level elements. All 6 tabs now render (TOP: 110 comps, bandgap: 15, ldo_analog: 17, ldo_digital: 14, ldo_lin: 16, lin_transceiver: 32) |
| Hierarchy tabs per LIN ASIC block | ✅ | `load_block_tab()` in `main_window.py`, called by `POST /api/asic/load` |
| Component drag-and-drop from library | ✅ | `CircuitLibraryDialog` |
| Component property editing | ✅ | Double-click or property panel |
| Zoom fit after load | ✅ | `zoom_fit()` called at end of `load_from_netlist` |

---

## 2. Simulation Engine

| Task | Status | Notes |
|------|--------|-------|
| DC analysis | ✅ | MNA solver in `analog_engine.py` |
| Transient analysis | ✅ | Time-stepping MNA |
| AC analysis | ✅ | Frequency sweep |
| SPICE element parsing (R, C, L, V, I, M, Q, D) | ✅ | `analog_engine.py` element models |
| Subcircuit expansion for simulation | ✅ | `_ASIC_BLOCK_TESTS` testbenches are flat SPICE |
| Verilog digital simulation | ✅ | `digital_engine.py` |
| Verilog-AMS mixed-signal | ✅ | `mixed_signal_engine.py` |

---

## 3. LIN ASIC Demo (5 Blocks)

| Block | Simulation Status | Schematic Renders | Spec |
|-------|-----------------|-------------------|------|
| Bandgap Reference | ✅ PASS — 1.1995 V | ✅ 15 components | VREF ∈ [1.14, 1.26] V |
| LDO Analog Supply | ✅ PASS — 3.300 V | ✅ 17 components | VOUT ∈ [3.135, 3.465] V |
| LDO Digital Supply | ✅ PASS — 1.800 V | ✅ 14 components | VOUT ∈ [1.71, 1.89] V |
| LDO LIN Supply | ✅ PASS — 5.000 V | ✅ 16 components | VOUT ∈ [4.75, 5.25] V |
| LIN Transceiver | ✅ PASS — 11.49V / 1.09V | ✅ 32 components | bus_high ≥ 0.6·VBAT, bus_low ≤ 2V |
| **Top-Level (all blocks)** | N/A (testbench per block) | ✅ 110 components | — |

---

## 4. Waveform Viewer

| Task | Status | Notes |
|------|--------|-------|
| Embedded waveform panel | ✅ | `WaveformViewer` in right panel |
| **Separate waveform window per block** | ✅ | `WaveformWindow(QMainWindow)` in `waveform_viewer.py`; GC-safe via `_instances` list |
| Waveform signal list (min/max/mean) | ✅ | `GET /api/waveform/info` |
| Export waveform as PNG | ✅ | `POST /api/export/waveform` |
| Export data as CSV | ✅ | `POST /api/export/csv` |

---

## 5. REST API Server (`simulator/api/server.py`)

| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/api/status` | GET | ✅ | Server + GUI health |
| `/api/circuits` | GET | ✅ | List standard circuits |
| `/api/circuits/load` | POST | ✅ | Load a standard circuit |
| `/api/simulate` | POST | ✅ | Run DC/AC/Tran simulation |
| `/api/results` | GET | ✅ | Last simulation results |
| `/api/netlist` | GET | ✅ **IMPROVED** | Returns active schematic editor netlist + tab name + component count (was: only netlist_viewer text) |
| `/api/netlist/load` | POST | ✅ | Load SPICE text into schematic |
| `/api/schematic/info` | GET | ✅ | Component/wire counts |
| `/api/schematic/tabs` | GET | ✅ **NEW** | All open tabs with per-tab component/wire counts |
| `/api/schematic/component` | POST | ✅ | Add a component programmatically |
| `/api/schematic/clear` | POST | ✅ | Clear the canvas |
| `/api/waveform/info` | GET | ✅ | Signal list with stats |
| `/api/errors` | GET | ✅ | Error log |
| `/api/errors/monitor` | GET/POST | ✅ | Error monitor status/control |
| `/api/errors/scan` | POST | ✅ | Trigger error scan |
| `/api/auto-design/blocks` | GET | ✅ | Auto-design block list |
| `/api/auto-design` | POST | ✅ | Run auto-design |
| `/api/export/schematic` | POST | ✅ | Export schematic PNG/PDF |
| `/api/export/waveform` | POST | ✅ | Export waveform plot |
| `/api/export/csv` | POST | ✅ | Export results CSV |
| `/api/asic/info` | GET | ✅ | List LIN ASIC blocks |
| `/api/asic/load` | POST | ✅ | Load hierarchy tabs into GUI |
| `/api/asic/simulate` | POST | ✅ | Run all 5 block tests |
| `/api/asic/test-report` | GET | ✅ | Structured PASS/FAIL report |
| `/api/asic/waveform-window` | POST | ✅ | Open standalone waveform window |

---

## 6. Error Monitoring & Auto-Correction

| Task | Status | Notes |
|------|--------|-------|
| `_error_log` ring buffer | ✅ | `deque(maxlen=200)` |
| Error classification (4 categories) | ✅ | `_classify_error()` |
| Auto-correction hooks | ✅ | `_attempt_auto_correction()` |
| Background monitor thread | ✅ | 30 s interval, runs in daemon thread |
| `_auto_corrections` log | ✅ | `deque(maxlen=50)` |

---

## 7. Known Remaining Gaps / Future Work

| Gap | Priority | Notes |
|-----|----------|-------|
| Bus notation `REG_ADDR[7:0]` in netlist not expanded for visual | LOW | Complex X-instances with buses are partially expanded |
| Schematic auto-routing quality (components overlap) | MED | Grid layout; no placer-router yet |
| `load_from_netlist` does not handle `X` instances whose SUBCKT is in a separate file | MED | Would require file-include parsing |
| No RTL schematic view for `.v` / Verilog blocks | MED | `lin_controller.v` etc. are not visualised |
| Top-level netlist view could show block icons instead of raw transistors | LOW | UX enhancement |
| Tests for `load_from_netlist` SUBCKT fix | LOW | Add to `test_suite.py` |

---

## 8. How to Run / Verify

```powershell
# Start GUI
cd "c:\Users\vinay\My Simulator"
pythonw -m simulator.main

# Run full ASIC demo (requires GUI running on port 5100)
python scripts/launch_asic_demo.py

# Verify schematic tabs via API
Invoke-RestMethod http://127.0.0.1:5100/api/schematic/tabs | ConvertTo-Json

# Get active schematic netlist
Invoke-RestMethod http://127.0.0.1:5100/api/netlist | Select-Object active_tab, component_count

# Headless block simulation test
python -c "
from simulator.engine.analog_engine import AnalogEngine
from simulator.api.server import _ASIC_BLOCK_TESTS, _evaluate_block, _check_block_pass
eng = AnalogEngine()
for bname, spec in _ASIC_BLOCK_TESTS.items():
    r = eng.run_simulation(spec['netlist'], spec['settings'])
    m = _evaluate_block(bname, spec, r)
    ok = _check_block_pass(bname, spec, m)
    print(bname, 'PASS' if ok else 'FAIL', m)
"
```

---

## 9. Git History (recent)
| Commit | Message |
|--------|---------|
| `bff24e2` | feat: ASIC GUI demo — hierarchy tabs, waveform windows, 5-block test report |
| `4ddc323` | feat: API error monitoring + auto-correction |
| (earlier) | various simulator features |
