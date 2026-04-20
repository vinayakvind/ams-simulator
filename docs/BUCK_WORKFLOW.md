# Buck Converter Validation & Workflow Documentation
## Hierarchical Structure

```
AMS Simulator - Buck Converter Validation
├── 1. SIMULATION ENGINES
│   ├── 1.1 Python Built-in Engine
│   │   ├── Status: ✓ WORKING
│   │   ├── Method: Modified Nodal Analysis (MNA)
│   │   ├── Features: R, C, L, M, Q, D, E (VCVS), G (VCCS), V, I
│   │   ├── Newton-Raphson: Enabled (max 30 iterations)
│   │   └── Results: Vout avg = 5.513V, ripple = 421mV
│   │
│   └── 1.2 NgSpice Backend
│       ├── Status: ⚠ PARTIAL (runs but incorrect results)
│       ├── Path: C:\ngspice\bin\ngspice_con.exe
│       ├── Issue: Vout = 0.277V (should be ~5V)
│       └── Action Required: Debug netlist preparation

├── 2. BUCK CONVERTER CIRCUIT
│   ├── 2.1 Topology
│   │   ├── Type: Synchronous Buck (PMOS high-side)
│   │   ├── Input: 12V DC
│   │   ├── Output Target: 5V DC
│   │   ├── Frequency: 100kHz
│   │   ├── Duty Cycle: 32.74% (tuned)
│   │   └── Components:
│   │       ├── M1: PMOS high-side switch (W=20µm, L=0.18µm)
│   │       ├── D1: Freewheeling diode (DFAST model)
│   │       ├── L1: Output inductor (100µH, IC=0.5A)
│   │       ├── C1: Output capacitor (100µF, IC=5V)
│   │       └── Rload: Load resistor (5Ω = 1A load)
│   │
│   ├── 2.2 Current Status
│   │   ├── Python Engine Results:
│   │   │   ├── Vin: 12.000V ✓
│   │   │   ├── Vout (final): 5.305V
│   │   │   ├── Vout (400-500µs avg): 5.513V
│   │   │   ├── Ripple: 421mV (< 500mV target) ✓
│   │   │   └── Switch node range: 1491V (large swings)
│   │   │
│   │   └── Improvements Needed:
│   │       ├── Reduce Vout overshoot (5.513V → 5.0V target)
│   │       ├── Tune duty cycle: currently 32.74%
│   │       ├── Suggested: 27.3% for exact 5V (12V × 0.273 ≈ 3.28V after losses)
│   │       └── Investigate large switch node swings (→1500V unrealistic)
│   │
│   └── 2.3 Netlist
│       ├── File: examples/standard_circuits/buck_converter.spice
│       ├── Key Lines:
│       │   ├── Vin input 0 DC 12V
│       │   ├── M1 sw_node gate input input PMOS W=20u L=0.18u
│       │   ├── Vgate gate 0 PULSE(0 16 0 10n 10n 3.274u 10u)
│       │   ├── D1 sw_node 0 DFAST
│       │   ├── L1 sw_node output 100u IC=0.5
│       │   ├── C1 output 0 100u IC=5
│       │   └── Rload output 0 5
│       └── Models:
│           ├── .MODEL PMOS PMOS (VTO=-0.7 KP=80u LAMBDA=0.02)
│           ├── .MODEL NMOS NMOS (VTO=0.7 KP=110u LAMBDA=0.04)
│           └── .MODEL DFAST D (IS=1e-14 RS=0.01 BV=30)

├── 3. VALIDATION WORKFLOW
│   ├── 3.1 Automated Test Suite
│   │   ├── Script: scripts/buck_validation_suite.py
│   │   ├── Features:
│   │   │   ├── Tests both Python and NgSpice engines
│   │   │   ├── Computes steady-state metrics (400-500µs window)
│   │   │   ├── Validates against target specs
│   │   │   └── Generates JSON report
│   │   │
│   │   └── Run Command:
│   │       └── python scripts/buck_validation_suite.py
│   │
│   ├── 3.2 Validation Checks
│   │   ├── [✓] Python: Vout steady-state near 5V (±1V tolerance)
│   │   ├── [✓] Python: Vout ripple < 500mV
│   │   ├── [✓] Python: Vin stable at 12V
│   │   └── [✗] NgSpice: Vout converged (currently 0.277V)
│   │
│   └── 3.3 Output Reports
│       ├── Location: reports/buck_validation_report.json
│       └── Contains:
│           ├── Timestamp
│           ├── Test results (Python & NgSpice)
│           ├── Metrics (Vout avg, ripple, Vin, switch node)
│           ├── Waveform data
│           └── Validation status

├── 4. KNOWN ISSUES & FIXES
│   ├── 4.1 NgSpice Low Output (0.277V)
│   │   ├── Root Cause: TBD - netlist format or model issue
│   │   ├── Investigation:
│   │   │   ├── Check PMOS polarity in NgSpice
│   │   │   ├── Verify .MODEL PMOS parameters
│   │   │   ├── Test with simple NMOS + diode topology
│   │   │   └── Review NgSpice raw file parsing
│   │   └── Workaround: Use Python engine for now
│   │
│   ├── 4.2 Progress Bar Hangs at 40%
│   │   ├── Location: simulator/gui/simulation_dialog.py:238
│   │   ├── Code: progress_callback=lambda p: self.progress.emit(30 + int(p * 0.6))
│   │   ├── Issue: TransientAnalysis.run() may not call callback frequently
│   │   ├── Fix: Add callback at each timestep in transient loop
│   │   └── Status: NOT YET FIXED
│   │
│   ├── 4.3 Large Switch Node Swings (1491V)
│   │   ├── Observation: V(sw_node) ranges from -400V to +451V
│   │   ├── Expected: Should swing between 0V and 12V
│   │   ├── Root Cause: Numerical instability in NR convergence
│   │   ├── Mitigation: Increase damping, add snubber, tune NR params
│   │   └── Status: UNDER INVESTIGATION
│   │
│   └── 4.4 Vout Overshoot (5.513V vs 5.0V target)
│       ├── Error: +0.513V (+10.3%)
│       ├── Cause: Duty cycle needs fine-tuning
│       ├── Current: 32.74% → Vout ≈ 5.5V
│       ├── Suggested: 27.3% → Vout ≈ 5.0V
│       └── Formula: D_new = D_old × (Vout_target / Vout_measured)

├── 5. API OPERATIONS
│   ├── 5.1 Available Endpoints (port 5198)
│   │   ├── GET  /api/status          - Server health
│   │   ├── GET  /api/circuits        - List circuits
│   │   ├── POST /api/circuits/load   - Load circuit by name
│   │   ├── POST /api/simulate        - Run simulation
│   │   ├── GET  /api/results         - Get last results
│   │   └── POST /api/netlist/load    - Load custom netlist
│   │
│   ├── 5.2 Buck Simulation via API
│   │   ├── Example cURL:
│   │   │   ```bash
│   │   │   curl -X POST http://localhost:5198/api/simulate \
│   │   │     -H "Content-Type: application/json" \
│   │   │     -d '{
│   │   │       "netlist": "...",
│   │   │       "analysis": "transient",
│   │   │       "settings": {
│   │   │         "tstop": 0.0005,
│   │   │         "tstep": 1e-7
│   │   │       }
│   │   │     }'
│   │   │   ```
│   │   │
│   │   └── Python Example:
│   │       ```python
│   │       import requests
│   │       resp = requests.post('http://localhost:5198/api/simulate',
│   │                            json={'netlist': netlist_str,
│   │                                  'analysis': 'transient',
│   │                                  'settings': {'tstop': 5e-4}})
│   │       results = resp.json()
│   │       ```
│   │
│   └── 5.3 Waveform Export
│       ├── Format: JSON arrays (time, voltage/current)
│       ├── Example: {"time": [0, 1e-9, ...], "V(output)": [0, 0.01, ...]}
│       └── Loadable in: matplotlib, plotly, GUI waveform viewer

├── 6. SCHEMATIC GENERATION
│   ├── 6.1 Netlist → Schematic
│   │   ├── Parser: simulator/gui/schematic_editor.py::load_from_netlist()
│   │   ├── Steps:
│   │   │   ├── Parse netlist elements (R, C, L, M, D, V, etc.)
│   │   │   ├── Infer component positions (auto-layout)
│   │   │   ├── Create wire routing (node connections)
│   │   │   └── Generate JSON schematic file
│   │   │
│   │   ├── Status: ✓ WORKING for most components
│   │   └── Limitations: Auto-layout may overlap components
│   │
│   └── 6.2 Schematic → Netlist
│       ├── Generator: schematic_editor.generate_netlist()
│       ├── Features:
│       │   ├── Converts visual components to SPICE elements
│       │   ├── Auto-injects .MODEL statements
│       │   ├── Adds analysis commands
│       │   └── Validates node connectivity
│       └── Status: ✓ WORKING

├── 7. PROGRESS CALLBACK FIX
│   ├── 7.1 Current Behavior
│   │   ├── GUI progress bar reaches 40% and stops
│   │   ├── Simulation continues in background
│   │   ├── Bar jumps to 100% when done
│   │   └── No intermediate updates during 30-90% range
│   │
│   ├── 7.2 Root Cause
│   │   ├── File: simulator/engine/analog_engine.py
│   │   ├── Method: TransientAnalysis.run()
│   │   ├── Issue: progress_callback only called once before loop
│   │   └── Fix location: Inside timestep loop (line ~1110)
│   │
│   └── 7.3 Proposed Fix
│       └── Add inside transient loop (every N steps):
│           ```python
│           if i % 100 == 0 and progress_callback:
│               progress_callback(i / len(time))
│           ```

├── 8. AGENT DELEGATION WORKFLOW
│   ├── 8.1 Simple Agent Tasks
│   │   ├── Task 1: Load buck_converter.spice
│   │   ├── Task 2: Run transient analysis (Python engine)
│   │   ├── Task 3: Extract Vout at t=500µs
│   │   ├── Task 4: Compare to 5V target
│   │   └── Task 5: Report pass/fail
│   │
│   ├── 8.2 Delegation Script
│   │   ├── File: scripts/agent_delegate_buck_test.py
│   │   ├── Features:
│   │   │   ├── Accepts task ID as argument
│   │   │   ├── Executes specific sub-task
│   │   │   ├── Returns JSON result
│   │   │   └── Can be chained via API
│   │   │
│   │   └── Usage:
│   │       └── python scripts/agent_delegate_buck_test.py --task=run_sim
│   │
│   └── 8.3 Task Breakdown (for simple agents)
│       ├── Level 1 (Easy):
│       │   ├── Read netlist file
│       │   ├── Check file exists
│       │   └── Count circuit elements
│       │
│       ├── Level 2 (Moderate):
│       │   ├── Load netlist into engine
│       │   ├── Run DC operating point
│       │   └── Extract single node voltage
│       │
│       └── Level 3 (Complex):
│           ├── Run full transient simulation
│           ├── Compute metrics (avg, ripple, etc.)
│           └── Generate validation report

└── 9. NEXT ACTIONS
    ├── [HIGH] Fix NgSpice output discrepancy (0.277V → 5V)
    ├── [HIGH] Add progress callback to transient timestep loop
    ├── [MEDIUM] Tune duty cycle for exact 5V output (27.3%)
    ├── [MEDIUM] Investigate large switch node swings (numerical stability)
    ├── [MEDIUM] Create agent delegation script
    ├── [LOW] Optimize transient step size for faster simulation
    └── [LOW] Add waveform export to CSV/HDF5

---

## Quick Command Reference

### Run Buck Validation
```bash
python scripts/buck_validation_suite.py
```

### API Simulation (PowerShell)
```powershell
$body = @{
    netlist = (Get-Content examples\standard_circuits\buck_converter.spice -Raw)
    analysis = "transient"
    settings = @{tstop=0.0005; tstep=1e-7}
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:5198/api/simulate" -Method POST -Body $body -ContentType "application/json"
```

### Load Schematic from Netlist (Python)
```python
from simulator.gui.schematic_editor import SchematicEditor
editor = SchematicEditor()
editor.load_from_netlist("examples/standard_circuits/buck_converter.spice")
editor.save_schematic("buck_schematic.json")
```

### Generate Netlist from Schematic
```python
netlist = editor.generate_netlist()
print(netlist)
```

---
**Last Updated:** 2026-02-08
**Version:** 1.0
**Status:** In Progress - Python engine validated, NgSpice needs debugging
