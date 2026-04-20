# AMS Simulator - Copilot Instructions

## Project Overview
This is an Analog Mixed Signal (AMS) Simulator application built with Python and PyQt6.

## Architecture
- **GUI Module** (`simulator/gui/`): Schematic editor, component library, waveform viewer
- **Simulation Engine** (`simulator/engine/`): SPICE-like analog, Verilog digital, Verilog-AMS mixed signal
- **Components** (`simulator/components/`): All circuit components (transistors, passives, sources, digital gates)
- **CLI Tools** (`simulator/cli/`): Command-line interface for batch simulations
- **Reporting** (`simulator/reporting/`): Test reporting, specs monitoring, pass/fail analysis

## Key Features
1. Schematic capture with drag-and-drop components
2. Wire routing with automatic connection detection
3. DC, AC, and Transient analysis
4. Verilog, Verilog-A, and Verilog-AMS simulation
5. Mixed-signal interface between analog and digital domains
6. Waveform plotting and measurement
7. Batch simulation with parallel execution
8. Specs monitoring and violation reporting

## Coding Guidelines
- Use type hints for all function parameters and returns
- Follow PEP 8 style guidelines
- Document all public classes and methods
- Use dataclasses for component models
- Keep simulation engines modular and extensible

## Running the Application
- GUI: `python -m simulator.main`
- CLI: `python -m simulator.cli.runner --netlist <file>`
- Batch: `python -m simulator.cli.batch --dir <netlists_dir>`

## Dependencies
- PyQt6: GUI framework
- NumPy/SciPy: Numerical computations
- Matplotlib: Waveform plotting
- PLY: Parser for Verilog files
