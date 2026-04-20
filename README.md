# AMS Simulator

A comprehensive **Analog Mixed Signal (AMS) Simulator** with GUI schematic editor, SPICE-like analog simulation, Verilog digital simulation, and Verilog-AMS mixed-signal support.

## Features

### Schematic Capture
- **Drag-and-drop component placement** from an organized component library
- **Wire routing** with automatic connection detection and orthogonal routing
- **Component property editing** with real-time parameter updates
- **Undo/Redo** support with full history
- **Zoom and pan** with grid snapping
- **Export** schematics to PNG, SVG, or PDF

### Components
- **Passive**: Resistors, Capacitors, Inductors, Polarized Capacitors
- **Active**: NMOS, PMOS, NPN, PNP Transistors
- **Diodes**: Standard, Zener, LED, Schottky
- **Sources**: DC/AC Voltage/Current, Pulse, Sine, PWL sources
- **Amplifiers**: Op-Amp, Comparator, Instrumentation Amplifier
- **Digital Gates**: AND, OR, NOT, NAND, NOR, XOR, XNOR, Buffer
- **Sequential**: D Flip-Flop, SR Latch, 2:1 Mux
- **Probes**: Voltage probe, Current probe

### Simulation Types

#### DC Analysis
- Operating point calculation
- DC sweep analysis
- Node voltage and branch current extraction

#### AC Analysis
- Frequency response (magnitude and phase)
- Decade, octave, or linear frequency sweep
- Bode plot generation

#### Transient Analysis
- Time-domain simulation
- Support for pulse, sine, and PWL sources
- Capacitor/inductor dynamics with trapezoidal integration

#### Digital Simulation
- Event-driven simulator with four-state logic (0, 1, X, Z)
- Gate-level Verilog support
- Continuous assignment support

#### Mixed-Signal Simulation
- Verilog-AMS style discipline resolution
- Connect modules for A/D and D/A conversion
- Simultaneous analog and digital simulation

### Waveform Viewer
- Multi-signal plotting with zoom and pan
- Signal measurements (min, max, average, RMS)
- Cursors for precise measurements
- CSV export for external analysis

### CLI Tools
- **Single simulation runner**: `ams-sim --netlist circuit.spice --analysis dc`
- **Batch processing**: `ams-batch --dir ./netlists --workers 4`
- Parallel execution with progress reporting

### Reporting
- **Specs monitoring**: Define pass/fail criteria for measurements
- **Automatic violation detection** with tolerances
- **Report generation**: HTML, Markdown, JSON, CSV formats

## Installation

### Prerequisites
- Python 3.10 or later
- pip package manager

### Install from source

```bash
# Clone the repository
git clone https://github.com/your-repo/ams-simulator.git
cd ams-simulator

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install in development mode
pip install -e .
```

### Install dependencies only

```bash
pip install PyQt6 numpy scipy matplotlib pyyaml jinja2 pandas ply
```

## Usage

### GUI Application

```bash
# Launch the GUI
python -m simulator.main
# Or using the entry point:
ams-gui
```

### Command Line - Single Simulation

```bash
# DC analysis
ams-sim --netlist circuit.spice --analysis dc --verbose

# AC analysis
ams-sim --netlist circuit.spice --analysis ac --fstart 1 --fstop 1e9 --points 10

# Transient analysis
ams-sim --netlist circuit.spice --analysis transient --tstop 1e-6 --tstep 1e-9

# Digital simulation
ams-sim --netlist circuit.v --analysis digital --max-time 1000

# Save results
ams-sim --netlist circuit.spice --analysis dc --output results.json
```

### Command Line - Batch Simulation

```bash
# Process all netlists in a directory
ams-batch --dir ./netlists --analysis dc

# Parallel execution with 4 workers
ams-batch --dir ./netlists --analysis transient --workers 4

# Generate HTML report
ams-batch --dir ./netlists --analysis dc --report report.html

# Use configuration file
ams-batch --config batch_config.json
```

### Batch Configuration File (JSON)

```json
{
  "jobs": [
    {
      "netlist": "circuit1.spice",
      "analysis": "dc",
      "output": "results/circuit1.json"
    },
    {
      "netlist": "circuit2.spice",
      "analysis": "transient",
      "parameters": {
        "tstop": 1e-6,
        "tstep": 1e-9
      }
    }
  ]
}
```

### Programmatic Usage

```python
from simulator import AnalogEngine, DCAnalysis, SpecsMonitor, ReportGenerator

# Load and simulate
engine = AnalogEngine()
engine.load_netlist('''
R1 in out 1k
R2 out 0 1k
V1 in 0 DC 5
''')

# Run DC analysis
analysis = DCAnalysis(engine)
results = analysis.run({})

# Check specifications
monitor = SpecsMonitor()
monitor.add_spec('Output Voltage', 'out', '>=', 2.4)
monitor.add_spec('Output Voltage', 'out', '<=', 2.6)

report = monitor.check_dc(results)
print(f"Pass rate: {report.pass_rate}%")

# Generate report
gen = ReportGenerator("DC Analysis Report")
gen.add_specs_results(report)
gen.save("report.html")
```

## Netlist Formats

### SPICE Netlist

```spice
* RC Low-Pass Filter
R1 in out 1k
C1 out 0 1u
V1 in 0 AC 1 DC 0

.AC DEC 10 1 1MEG
.END
```

### Verilog (Digital)

```verilog
module counter(
    input clk,
    input rst,
    output [3:0] count
);
    reg [3:0] count;
    
    always @(posedge clk or posedge rst) begin
        if (rst)
            count <= 0;
        else
            count <= count + 1;
    end
endmodule
```

### Verilog-AMS (Mixed Signal)

```verilog
`include "disciplines.vams"

module adc_8bit(
    input electrical ain,
    output logic [7:0] dout
);
    parameter real vref = 3.3;
    
    analog begin
        @(cross(V(ain) - vref/2, +1)) begin
            // ADC conversion logic
        end
    end
endmodule
```

## Specifications File Format

```json
{
  "specs": [
    {
      "name": "Output High",
      "signal": "out",
      "operator": ">=",
      "value": 2.4,
      "tolerance": 5,
      "units": "V"
    },
    {
      "name": "Output Low", 
      "signal": "out",
      "operator": "<=",
      "value": 0.4,
      "units": "V"
    },
    {
      "name": "Bandwidth",
      "signal": "gain",
      "operator": "range",
      "value": [1e6, 10e6],
      "units": "Hz"
    }
  ]
}
```

## Project Structure

```
simulator/
├── __init__.py          # Package initialization
├── main.py              # GUI application entry point
├── components/          # Circuit components
│   ├── base.py          # Base component classes
│   ├── passive.py       # R, L, C components
│   ├── transistors.py   # MOSFET, BJT
│   ├── sources.py       # Voltage/current sources
│   ├── digital.py       # Logic gates
│   ├── diodes.py        # Diodes
│   └── amplifiers.py    # Op-amps, comparators
├── engine/              # Simulation engines
│   ├── analog_engine.py # SPICE-like MNA solver
│   ├── digital_engine.py# Event-driven digital sim
│   └── mixed_signal_engine.py  # Verilog-AMS
├── gui/                 # PyQt6 GUI components
│   ├── main_window.py   # Main application window
│   ├── schematic_editor.py  # Schematic canvas
│   ├── component_library.py # Component browser
│   ├── property_editor.py   # Property panel
│   ├── waveform_viewer.py   # Waveform display
│   ├── simulation_dialog.py # Sim configuration
│   └── netlist_viewer.py    # Netlist display
├── cli/                 # Command-line tools
│   ├── runner.py        # Single simulation CLI
│   └── batch.py         # Batch simulation CLI
└── reporting/           # Reports and specs
    ├── specs_monitor.py # Specification checking
    └── report_generator.py  # Report generation
```

## Contributing

Contributions are welcome! Please read the contributing guidelines before submitting pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- NumPy/SciPy for numerical computations
- PyQt6 for the GUI framework
- Matplotlib for waveform visualization
