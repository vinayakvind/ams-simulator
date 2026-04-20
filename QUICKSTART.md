# AMS Simulator - Quick Start Guide

## 🚀 Launching the Simulator

### From Desktop Icon
- Double-click the **"AMS Simulator"** icon on your desktop

### From Command Line
```bash
# Navigate to simulator directory
cd "C:\Users\vinay\My Simulator"

# Run directly
.venv\Scripts\python.exe -m simulator.main

# Or use the batch file
launch_ams_simulator.bat
```

## 📟 Integrated Terminal

The GUI now includes an **integrated terminal** at the bottom of the window where you can run CLI commands without leaving the application!

### Quick Commands
Use the dropdown menu for common commands:
- **DC Analysis** - Run DC operating point or sweep
- **AC Analysis** - Frequency response analysis
- **Transient Analysis** - Time-domain simulation
- **Digital Simulation** - Event-driven logic simulation
- **Batch Simulation** - Run multiple simulations in parallel

### Terminal Commands

#### Single Simulation
```bash
# DC Analysis
ams-sim --netlist circuit.spice --analysis dc --verbose

# AC Analysis  
ams-sim --netlist circuit.spice --analysis ac --fstart 1 --fstop 1e9

# Transient Analysis
ams-sim --netlist circuit.spice --analysis transient --tstop 1e-6 --tstep 1e-9

# Digital Simulation
ams-sim --netlist circuit.v --analysis digital --max-time 1000
```

#### Batch Simulation
```bash
# Process directory of netlists
ams-batch --dir ./netlists --analysis dc --workers 4

# With output directory
ams-batch --dir ./netlists --analysis transient --output-dir ./results

# Generate HTML report
ams-batch --dir ./netlists --report report.html
```

#### Python Module Commands
```bash
# Run simulation module directly
python -m simulator.cli.runner --netlist circuit.spice --analysis dc

# Get help
python -m simulator.cli.runner --help
python -m simulator.cli.batch --help
```

### Terminal Features
- **Command History**: Use ↑/↓ arrow keys to navigate previous commands
- **Quick Commands**: Select from dropdown for instant templates
- **Color Coding**: 
  - Green = Success/Commands
  - Red = Errors
  - Yellow = Warnings
- **Stop Button**: Terminate long-running processes
- **Clear Button**: Clear terminal output

## 🎨 GUI Features

### Main Window Layout

```
┌─────────────────────────────────────────────────────────┐
│  Menu Bar | Toolbar                                      │
├──────────┬──────────────────────────────┬───────────────┤
│          │                              │               │
│Component │   Schematic Editor           │   Property    │
│ Library  │   (Draw circuits here)       │   Editor      │
│          │                              │               │
│ (Drag &  ├──────────────────────────────┤  (Component   │
│  Drop)   │   Waveform Viewer            │   settings)   │
│          │   (Simulation results)       │               │
│          ├──────────────────────────────┤               │
│          │   Integrated Terminal        │   Netlist     │
│          │   (CLI Commands)             │   Viewer      │
└──────────┴──────────────────────────────┴───────────────┘
```

### Schematic Editor
- **Add Components**: Drag from Component Library on left
- **Wire Connections**: Click to start, click to route, click to end
- **Edit Properties**: Select component, edit in Property Editor on right
- **Zoom**: Mouse wheel or View menu
- **Pan**: Middle mouse button drag
- **Undo/Redo**: Ctrl+Z / Ctrl+Y

### Component Library
Organized categories:
- Passive (R, L, C)
- Transistors (NMOS, PMOS, BJT)
- Diodes
- Sources (V, I, Pulse, Sine)
- Digital Gates (AND, OR, NOT, etc.)
- Amplifiers (Op-Amp, Comparator)

### Running Simulations

1. **Draw Circuit** in schematic editor
2. **Click Simulate** → Choose analysis type
3. **Configure Parameters** (DC/AC/Transient settings)
4. **View Results** in Waveform Viewer
5. **Use Terminal** for batch processing or advanced commands

## 📂 Example Netlists

Create a file `voltage_divider.spice`:
```spice
* Voltage Divider
R1 in out 1k
R2 out 0 1k
V1 in 0 DC 5

.DC
.END
```

Run in terminal:
```bash
ams-sim --netlist voltage_divider.spice --analysis dc --verbose
```

Expected output: V(in) = 5V, V(out) = 2.5V

## 🔧 Tips & Tricks

### Terminal Shortcuts
- Type `clear` to clear terminal output
- Use Tab key (future) for auto-completion
- Commands run in PowerShell environment

### Save Your Work
- File → Save: Save current schematic
- File → Save As: Save with new name
- File → Export: Export to PNG/SVG/PDF

### Batch Processing
1. Create a `netlists/` folder with multiple .spice files
2. Run: `ams-batch --dir netlists --workers 4`
3. Get parallel execution across all CPU cores

### Keyboard Shortcuts
- `Ctrl+N` - New schematic
- `Ctrl+O` - Open file
- `Ctrl+S` - Save
- `Ctrl+Z` - Undo
- `Ctrl+Y` - Redo
- `Ctrl+Q` - Quit

## 📊 Output Files

Results are saved in JSON format by default:
```json
{
  "type": "dc",
  "V(in)": 5.0,
  "V(out)": 2.5,
  "metadata": {
    "elapsed_time": 0.005
  }
}
```

Export to CSV for Excel/MATLAB:
```bash
ams-sim --netlist circuit.spice --output results.csv
```

## 🐛 Troubleshooting

**Terminal shows "Command not found"**
- Make sure you're in the simulator directory
- Use full `python -m simulator.cli.runner` syntax

**GUI doesn't launch**
- Check Python installation: `.venv\Scripts\python.exe --version`
- Reinstall dependencies: `pip install -r requirements.txt`

**Desktop shortcut doesn't work**
- Re-run: `python create_desktop_shortcut.py`
- Or manually run: `launch_ams_simulator.bat`

## 📚 Learn More

- Full documentation: See [README.md](README.md)
- CLI help: `ams-sim --help` or `ams-batch --help`
- Examples: Check `examples/` folder (if created)

---

**Enjoy simulating with AMS Simulator!** 🎉
