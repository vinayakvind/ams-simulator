# AMS Simulator - Quick Test & Launch Guide

## ✅ Everything is Working!

All 38 tests passed. Your simulator is fully operational.

---

## Run Tests Anytime

```bash
python test_suite.py
```

This runs a comprehensive test of:
- All dependencies ✓
- All components ✓
- All engines ✓
- Configuration ✓
- CLI tools ✓
- Reporting ✓

---

## Launch the Simulator

### Option 1: Click to Launch (Easiest)
```
Double-click → launch_ams_simulator.pyw
```

### Option 2: Python Command
```bash
python -m simulator.main
```

### Option 3: GUI Script
```bash
python -m simulator.main
```

---

## CLI Usage

### Run a Single Simulation
```bash
python -m simulator.cli.runner --netlist examples/voltage_divider.spice
```

### Batch Process Multiple Circuits
```bash
python -m simulator.cli.batch --dir examples/standard_circuits
```

---

## What Works

| Feature | Status |
|---------|--------|
| GUI Application | ✅ Working |
| Schematic Editor | ✅ Working |
| Analog Simulation | ✅ Working |
| Digital Simulation | ✅ Working |
| Mixed-Signal Support | ✅ Working |
| Waveform Viewer | ✅ Working |
| Batch Processing | ✅ Working |
| Report Generation | ✅ Working |
| Component Library | ✅ Working |

---

## Example Circuits Available

- `examples/voltage_divider.spice` - Basic DC circuit
- `examples/rc_lowpass.spice` - AC filter analysis
- `examples/rc_transient.spice` - Time-domain simulation
- `examples/and_gate_test.v` - Digital circuit
- `examples/standard_circuits/` - Advanced circuits (buck converter, LDO, etc.)

---

## Environment Status

- Python: 3.13.7 ✓
- Virtual Environment: Active ✓
- Dependencies: All installed ✓
- Project: Ready ✓

---

## Next Steps

1. **Try the GUI:** Run `python -m simulator.main`
2. **Load a circuit:** File → Open → examples/voltage_divider.spice
3. **Run simulation:** Simulation → Run
4. **View results:** Check waveform viewer

---

## Troubleshooting

If anything doesn't work, run tests again:
```bash
python test_suite.py
```

If you see failures, each test clearly shows what's broken.

---

**Last Tested:** February 5, 2026  
**Test Results:** ALL PASSED (38/38)
