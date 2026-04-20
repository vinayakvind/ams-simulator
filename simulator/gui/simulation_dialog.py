"""
Simulation Dialog - Configure and run simulations.
"""

import os
import tempfile
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QFormLayout, QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox,
    QCheckBox, QGroupBox, QPushButton, QProgressBar, QTextEdit,
    QLabel, QDialogButtonBox, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

import numpy as np


class SimulationWorker(QThread):
    """Worker thread for running simulations."""
    
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    log = pyqtSignal(str)

    # Default NgSpice .MODEL definitions keyed by uppercase model name
    _DEFAULT_NGSPICE_MODELS: Dict[str, str] = {
        'NMOS_DEFAULT': '.MODEL NMOS_DEFAULT NMOS (VTO=0.4 KP=120u LAMBDA=0.01)',
        'PMOS_DEFAULT': '.MODEL PMOS_DEFAULT PMOS (VTO=-0.4 KP=40u LAMBDA=0.01)',
        'NPN_DEFAULT': '.MODEL NPN_DEFAULT NPN (BF=100 IS=1e-14 VAF=100)',
        'PNP_DEFAULT': '.MODEL PNP_DEFAULT PNP (BF=100 IS=1e-14 VAF=100)',
        'D1N4148': '.MODEL D1N4148 D (IS=2.52e-9 N=1.752 BV=100 RS=0.568)',
        'BZX79C5V1': '.MODEL BZX79C5V1 D (IS=1e-14 BV=5.1 IBV=5e-3 RS=10)',
    }
    
    def __init__(self, analysis_type: str, netlist: str, settings: dict, use_ngspice: bool = False):
        super().__init__()
        self.analysis_type = analysis_type
        self.netlist = netlist
        self.settings = settings
        self.use_ngspice = use_ngspice
        self._cancelled = False
    
    def cancel(self):
        self._cancelled = True
    
    def run(self):
        try:
            if self.use_ngspice:
                self._run_ngspice()
            else:
                self._run_python_engine()
        except Exception as e:
            import traceback
            self.error.emit(f"{str(e)}\n{traceback.format_exc()}")
    
    def _run_ngspice(self):
        """Run simulation using ngspice backend."""
        from simulator.engine.ngspice_backend import NgSpiceBackend
        
        self.log.emit("Using NgSpice backend...")
        self.progress.emit(10)
        
        backend = NgSpiceBackend()
        if not backend.is_available():
            raise RuntimeError("NgSpice is not available. Please install ngspice or use Python engine.")
        
        self.log.emit(f"NgSpice path: {backend.ngspice_path}")
        self.progress.emit(20)
        
        # Create a complete netlist with analysis commands
        complete_netlist = self._prepare_ngspice_netlist()
        
        self.log.emit(f"Running {self.analysis_type} analysis...")
        self.progress.emit(40)
        
        if self._cancelled:
            return
        
        # Run ngspice simulation
        results = backend.simulate(complete_netlist)
        
        self.progress.emit(90)
        
        # Post-process results
        if not results:
            # Try to extract from the netlist using Python engine as fallback
            self.log.emit("NgSpice returned no parsed results, trying Python engine...")
            self._run_python_engine()
            return
        
        # Format results with proper keys
        formatted_results = {'type': self.analysis_type.lower()}
        for key, value in results.items():
            if not key.startswith('V(') and not key.startswith('I('):
                formatted_results[f'V({key})'] = value
            else:
                formatted_results[key] = value
        
        self.progress.emit(100)
        self.log.emit("NgSpice simulation completed successfully.")
        self.finished.emit(formatted_results)
    
    def _prepare_ngspice_netlist(self) -> str:
        """Prepare netlist with proper analysis commands for ngspice.
        
        Ensures that every model name referenced by M (MOSFET), Q (BJT),
        or D (diode) element lines has a corresponding .MODEL definition.
        Missing models are supplied from the built-in defaults.
        """
        import re

        lines = self.netlist.strip().split('\n')
        
        # ----------------------------------------------------------
        # 1.  Split lines into element lines, .MODEL lines, and other
        # ----------------------------------------------------------
        filtered_lines: list[str] = []
        existing_models: set[str] = set()        # model names already defined
        referenced_models: set[str] = set()       # model names used by elements

        for line in lines:
            stripped = line.strip()
            line_lower = stripped.lower()

            # Skip analysis / control directives (they will be re-added below)
            if any(line_lower.startswith(cmd) for cmd in ['.dc', '.ac', '.tran', '.op', '.end', '.control', '.endc']):
                continue

            # Track existing .MODEL definitions
            m = re.match(r'\.model\s+(\S+)', stripped, re.IGNORECASE)
            if m:
                existing_models.add(m.group(1).upper())

            # Track model names referenced by elements (M, Q, D)
            if stripped and not stripped.startswith('*') and not stripped.startswith('.'):
                tokens = stripped.split()
                prefix = tokens[0][0].upper() if tokens else ''
                if prefix == 'M' and len(tokens) >= 6:
                    # MOSFET: Mname drain gate source bulk model ...
                    referenced_models.add(tokens[5].upper())
                elif prefix == 'Q' and len(tokens) >= 5:
                    # BJT: Qname collector base emitter model ...
                    referenced_models.add(tokens[4].upper())
                elif prefix == 'D' and len(tokens) >= 4:
                    # Diode: Dname anode cathode model
                    referenced_models.add(tokens[3].upper())

            filtered_lines.append(line)

        # ----------------------------------------------------------
        # 2.  Inject default .MODEL for any referenced but undefined
        # ----------------------------------------------------------
        missing = referenced_models - existing_models
        if missing:
            filtered_lines.append("")
            filtered_lines.append("* Auto-injected default model definitions")
            for model_name in sorted(missing):
                if model_name in self._DEFAULT_NGSPICE_MODELS:
                    filtered_lines.append(self._DEFAULT_NGSPICE_MODELS[model_name])
                else:
                    # Heuristic: guess type from the element prefix that uses it
                    for raw_line in lines:
                        tok = raw_line.strip().split()
                        if not tok or tok[0].startswith('*') or tok[0].startswith('.'):
                            continue
                        p = tok[0][0].upper()
                        if p == 'M' and len(tok) >= 6 and tok[5].upper() == model_name:
                            # Guess NMOS by default
                            filtered_lines.append(f".MODEL {model_name} NMOS (VTO=0.7 KP=110u LAMBDA=0.04)")
                            break
                        elif p == 'Q' and len(tok) >= 5 and tok[4].upper() == model_name:
                            filtered_lines.append(f".MODEL {model_name} NPN (BF=100 IS=1e-14 VAF=100)")
                            break
                        elif p == 'D' and len(tok) >= 4 and tok[3].upper() == model_name:
                            filtered_lines.append(f".MODEL {model_name} D (IS=1e-14 N=1.0 BV=100 RS=0.1)")
                            break

        # ----------------------------------------------------------
        # 3.  Add analysis command
        # ----------------------------------------------------------
        if self.analysis_type == "DC":
            source = self.settings.get('source', 'V1')
            start = self.settings.get('start', 0)
            stop = self.settings.get('stop', 5)
            step = self.settings.get('step', 0.1)
            if source and start != stop:
                filtered_lines.append(f".dc {source} {start} {stop} {step}")
            else:
                filtered_lines.append(".op")
        elif self.analysis_type == "AC":
            variation = self.settings.get('variation', 'dec')
            points = self.settings.get('points', 10)
            fstart = self.settings.get('fstart', 1)
            fstop = self.settings.get('fstop', 1e6)
            filtered_lines.append(f".ac {variation} {points} {fstart} {fstop}")
        elif self.analysis_type == "Transient":
            tstop = self.settings.get('tstop', 1e-3)
            tstep = self.settings.get('tstep', 1e-6)
            tstart = self.settings.get('tstart', 0)
            filtered_lines.append(f".tran {tstep} {tstop} {tstart}")
        
        filtered_lines.append(".end")
        
        return '\n'.join(filtered_lines)
    
    def _run_python_engine(self):
        """Run simulation using built-in Python engine."""
        from simulator.engine import (
            AnalogEngine, DCAnalysis, ACAnalysis, TransientAnalysis
        )
        
        self.log.emit(f"Starting {self.analysis_type} analysis (Python engine)...")
        self.progress.emit(10)
        
        # Create engine
        engine = AnalogEngine()
        engine.load_netlist(self.netlist)
        
        self.progress.emit(30)
        
        if self._cancelled:
            return
        
        # Run appropriate analysis
        if self.analysis_type == "DC":
            analysis = DCAnalysis(engine)
            results = analysis.run(self.settings)
        elif self.analysis_type == "AC":
            analysis = ACAnalysis(engine)
            results = analysis.run(self.settings)
        elif self.analysis_type == "Transient":
            analysis = TransientAnalysis(engine)
            results = analysis.run(
                self.settings,
                progress_callback=lambda p: self.progress.emit(30 + int(p * 0.6))
            )
        else:
            raise ValueError(f"Unknown analysis type: {self.analysis_type}")
        
        self.progress.emit(100)
        self.log.emit("Simulation completed successfully.")
        self.finished.emit(results)


class SimulationDialog(QDialog):
    """Dialog for configuring and running simulations."""
    
    def __init__(self, analysis_type: str, netlist: str, parent=None):
        super().__init__(parent)
        
        self.analysis_type = analysis_type
        self.netlist = netlist
        self._results: Optional[dict] = None
        self._worker: Optional[SimulationWorker] = None
        
        self.setWindowTitle(f"{analysis_type} Analysis")
        self.setMinimumSize(500, 400)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        
        # Settings tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Analysis-specific settings
        if self.analysis_type == "DC":
            self._setup_dc_tab()
        elif self.analysis_type == "AC":
            self._setup_ac_tab()
        elif self.analysis_type == "Transient":
            self._setup_transient_tab()
        else:
            self._setup_settings_tab()
        
        # Options tab
        self._setup_options_tab()
        
        # Progress section
        progress_group = QGroupBox("Simulation Progress")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        progress_layout.addWidget(self.progress_bar)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        progress_layout.addWidget(self.log_text)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.run_button = QPushButton("Run Simulation")
        self.run_button.clicked.connect(self._run_simulation)
        button_layout.addWidget(self.run_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._cancel_simulation)
        self.cancel_button.setEnabled(False)
        button_layout.addWidget(self.cancel_button)
        
        button_layout.addStretch()
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
    
    def _setup_dc_tab(self):
        """Setup DC analysis settings."""
        tab = QWidget()
        layout = QFormLayout(tab)
        
        # Sweep source
        self.dc_source = QComboBox()
        self.dc_source.addItems(["V1", "V2", "I1"])
        self.dc_source.setEditable(True)
        layout.addRow("Sweep Source:", self.dc_source)
        
        # Start value
        self.dc_start = QDoubleSpinBox()
        self.dc_start.setRange(-1e6, 1e6)
        self.dc_start.setValue(0)
        self.dc_start.setSuffix(" V")
        layout.addRow("Start:", self.dc_start)
        
        # Stop value
        self.dc_stop = QDoubleSpinBox()
        self.dc_stop.setRange(-1e6, 1e6)
        self.dc_stop.setValue(5)
        self.dc_stop.setSuffix(" V")
        layout.addRow("Stop:", self.dc_stop)
        
        # Step
        self.dc_step = QDoubleSpinBox()
        self.dc_step.setRange(1e-12, 1e6)
        self.dc_step.setValue(0.1)
        self.dc_step.setSuffix(" V")
        layout.addRow("Step:", self.dc_step)
        
        self.tabs.addTab(tab, "DC Analysis")
    
    def _setup_ac_tab(self):
        """Setup AC analysis settings."""
        tab = QWidget()
        layout = QFormLayout(tab)
        
        # Frequency type
        self.ac_type = QComboBox()
        self.ac_type.addItems(["Decade", "Octave", "Linear"])
        layout.addRow("Variation:", self.ac_type)
        
        # Points per decade
        self.ac_points = QSpinBox()
        self.ac_points.setRange(1, 1000)
        self.ac_points.setValue(10)
        layout.addRow("Points/Decade:", self.ac_points)
        
        # Start frequency
        self.ac_fstart = QDoubleSpinBox()
        self.ac_fstart.setRange(1e-3, 1e15)
        self.ac_fstart.setValue(1)
        self.ac_fstart.setSuffix(" Hz")
        self.ac_fstart.setDecimals(3)
        layout.addRow("Start Frequency:", self.ac_fstart)
        
        # Stop frequency
        self.ac_fstop = QDoubleSpinBox()
        self.ac_fstop.setRange(1e-3, 1e15)
        self.ac_fstop.setValue(1e6)
        self.ac_fstop.setSuffix(" Hz")
        self.ac_fstop.setDecimals(3)
        layout.addRow("Stop Frequency:", self.ac_fstop)
        
        self.tabs.addTab(tab, "AC Analysis")
    
    def _setup_transient_tab(self):
        """Setup transient analysis settings."""
        tab = QWidget()
        layout = QFormLayout(tab)
        
        # Stop time
        self.tran_stop = QDoubleSpinBox()
        self.tran_stop.setRange(1e-15, 1e6)
        self.tran_stop.setValue(1e-6)
        self.tran_stop.setSuffix(" s")
        self.tran_stop.setDecimals(12)
        layout.addRow("Stop Time:", self.tran_stop)
        
        # Time step
        self.tran_step = QDoubleSpinBox()
        self.tran_step.setRange(1e-18, 1e6)
        self.tran_step.setValue(1e-9)
        self.tran_step.setSuffix(" s")
        self.tran_step.setDecimals(15)
        layout.addRow("Max Step:", self.tran_step)
        
        # Start time
        self.tran_start = QDoubleSpinBox()
        self.tran_start.setRange(0, 1e6)
        self.tran_start.setValue(0)
        self.tran_start.setSuffix(" s")
        layout.addRow("Start Save:", self.tran_start)
        
        # Use initial conditions
        self.tran_uic = QCheckBox()
        layout.addRow("Use IC:", self.tran_uic)
        
        self.tabs.addTab(tab, "Transient Analysis")
    
    def _setup_settings_tab(self):
        """Setup general settings tab."""
        tab = QWidget()
        layout = QFormLayout(tab)
        
        layout.addRow(QLabel("Select analysis type from Simulate menu."))
        
        self.tabs.addTab(tab, "Settings")
    
    def _setup_options_tab(self):
        """Setup simulation options tab."""
        tab = QWidget()
        layout = QFormLayout(tab)
        
        # === Simulation Engine Selection ===
        engine_group = QGroupBox("Simulation Engine")
        engine_layout = QVBoxLayout()
        
        self.engine_button_group = QButtonGroup(self)
        
        # Python Engine option
        self.python_engine_radio = QRadioButton("Python Engine (Built-in)")
        self.python_engine_radio.setToolTip(
            "Use the built-in Python simulation engine.\n"
            "Good for simple circuits and learning.\n"
            "Supports: R, L, C, MOSFETs, BJTs, Diodes"
        )
        self.engine_button_group.addButton(self.python_engine_radio, 0)
        engine_layout.addWidget(self.python_engine_radio)
        
        # NgSpice option
        self.ngspice_radio = QRadioButton("NgSpice (Professional)")
        self.ngspice_radio.setToolTip(
            "Use NgSpice for professional-grade simulation.\n"
            "Better convergence and accuracy.\n"
            "Supports all SPICE models."
        )
        self.engine_button_group.addButton(self.ngspice_radio, 1)
        engine_layout.addWidget(self.ngspice_radio)
        
        # Check ngspice availability and set default
        self._check_ngspice_availability()
        
        # Status label
        self.engine_status_label = QLabel()
        self._update_engine_status()
        engine_layout.addWidget(self.engine_status_label)
        
        engine_group.setLayout(engine_layout)
        layout.addRow(engine_group)
        
        # Connect signals
        self.engine_button_group.buttonClicked.connect(self._update_engine_status)
        
        # === Simulation Options ===
        layout.addRow(QLabel(""))  # Spacer
        
        # Tolerance
        self.opt_reltol = QDoubleSpinBox()
        self.opt_reltol.setRange(1e-12, 1)
        self.opt_reltol.setValue(1e-3)
        self.opt_reltol.setDecimals(12)
        layout.addRow("Relative Tolerance:", self.opt_reltol)
        
        self.opt_abstol = QDoubleSpinBox()
        self.opt_abstol.setRange(1e-18, 1)
        self.opt_abstol.setValue(1e-12)
        self.opt_abstol.setDecimals(18)
        layout.addRow("Absolute Tolerance:", self.opt_abstol)
        
        # Temperature
        self.opt_temp = QDoubleSpinBox()
        self.opt_temp.setRange(-273.15, 1000)
        self.opt_temp.setValue(27)
        self.opt_temp.setSuffix(" °C")
        layout.addRow("Temperature:", self.opt_temp)
        
        # Max iterations
        self.opt_itl = QSpinBox()
        self.opt_itl.setRange(1, 10000)
        self.opt_itl.setValue(100)
        layout.addRow("Max Iterations:", self.opt_itl)
        
        self.tabs.addTab(tab, "Options")
    
    def _check_ngspice_availability(self):
        """Check if ngspice is available and set default engine."""
        try:
            from simulator.engine.ngspice_backend import NgSpiceBackend
            backend = NgSpiceBackend()
            self._ngspice_available = backend.is_available()
            self._ngspice_path = backend.ngspice_path if self._ngspice_available else None
        except Exception:
            self._ngspice_available = False
            self._ngspice_path = None
        
        # Set default: prefer ngspice if available
        if self._ngspice_available:
            self.ngspice_radio.setChecked(True)
        else:
            self.python_engine_radio.setChecked(True)
            self.ngspice_radio.setEnabled(False)
    
    def _update_engine_status(self):
        """Update the engine status label."""
        if self.ngspice_radio.isChecked():
            if self._ngspice_available:
                self.engine_status_label.setText(
                    f"✓ NgSpice ready: {self._ngspice_path}"
                )
                self.engine_status_label.setStyleSheet("color: green;")
            else:
                self.engine_status_label.setText(
                    "✗ NgSpice not available. Install from ngspice.sourceforge.io"
                )
                self.engine_status_label.setStyleSheet("color: red;")
        else:
            self.engine_status_label.setText(
                "✓ Python engine ready (MOSFETs, BJTs, Diodes supported)"
            )
            self.engine_status_label.setStyleSheet("color: green;")
    
    def _use_ngspice(self) -> bool:
        """Check if ngspice should be used."""
        return self.ngspice_radio.isChecked() and self._ngspice_available
    
    def _get_settings(self) -> dict:
        """Get current settings."""
        settings = {
            'reltol': self.opt_reltol.value(),
            'abstol': self.opt_abstol.value(),
            'temp': self.opt_temp.value(),
            'itl': self.opt_itl.value(),
        }
        
        if self.analysis_type == "DC":
            settings.update({
                'source': self.dc_source.currentText(),
                'start': self.dc_start.value(),
                'stop': self.dc_stop.value(),
                'step': self.dc_step.value(),
            })
        elif self.analysis_type == "AC":
            settings.update({
                'variation': self.ac_type.currentText().lower(),
                'points': self.ac_points.value(),
                'fstart': self.ac_fstart.value(),
                'fstop': self.ac_fstop.value(),
            })
        elif self.analysis_type == "Transient":
            settings.update({
                'tstop': self.tran_stop.value(),
                'tstep': self.tran_step.value(),
                'tstart': self.tran_start.value(),
                'uic': self.tran_uic.isChecked(),
            })
        
        return settings
    
    def _run_simulation(self):
        """Start the simulation."""
        settings = self._get_settings()
        use_ngspice = self._use_ngspice()
        
        self.run_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.log_text.clear()
        
        # Log which engine is being used
        engine_name = "NgSpice" if use_ngspice else "Python Engine"
        self._append_log(f"Starting simulation with {engine_name}...")
        
        self._worker = SimulationWorker(
            self.analysis_type, self.netlist, settings, use_ngspice=use_ngspice
        )
        self._worker.progress.connect(self.progress_bar.setValue)
        self._worker.log.connect(self._append_log)
        self._worker.finished.connect(self._on_simulation_finished)
        self._worker.error.connect(self._on_simulation_error)
        self._worker.start()
    
    def _cancel_simulation(self):
        """Cancel the running simulation."""
        if self._worker:
            self._worker.cancel()
            self._worker.wait()
        
        self.run_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self._append_log("Simulation cancelled.")
    
    def _on_simulation_finished(self, results: dict):
        """Handle simulation completion."""
        self._results = results
        self.run_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
    
    def _on_simulation_error(self, error: str):
        """Handle simulation error."""
        self._append_log(f"Error: {error}")
        self.run_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
    
    def _append_log(self, message: str):
        """Append message to log."""
        self.log_text.append(message)
    
    def get_results(self) -> Optional[dict]:
        """Get simulation results."""
        return self._results
