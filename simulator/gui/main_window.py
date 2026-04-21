"""
Main application window for the AMS Simulator.
"""

import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QToolBar, QStatusBar, QMenuBar, QMenu, QFileDialog, QMessageBox,
    QDockWidget, QTabWidget, QLabel, QDialog, QListWidget, QListWidgetItem,
    QPushButton, QTextEdit, QDialogButtonBox, QApplication
)
from PyQt6.QtCore import Qt, QSettings, QSize
from PyQt6.QtGui import QAction, QIcon, QKeySequence

from simulator.gui.schematic_editor import SchematicEditor
from simulator.gui.component_library import ComponentLibrary
from simulator.gui.property_editor import PropertyEditor
from simulator.gui.waveform_viewer import WaveformViewer
from simulator.gui.simulation_dialog import SimulationDialog
from simulator.gui.netlist_viewer import NetlistViewer
from simulator.gui.terminal_widget import TerminalWidget


class CircuitLibraryDialog(QDialog):
    """Dialog for browsing and loading standard circuits."""
    
    CIRCUIT_CATEGORIES = {
        "Power Electronics": [
            ("buck_converter.spice", "Buck Converter", "Step-down DC-DC converter (12V to 5V)"),
            ("boost_converter.spice", "Boost Converter", "Step-up DC-DC converter (5V to 12V)"),
            ("buck_boost_converter.spice", "Buck-Boost Converter", "Inverting DC-DC converter"),
            ("flyback_converter.spice", "Flyback Converter", "Isolated DC-DC converter"),
            ("ldo_regulator.spice", "LDO Regulator", "Low dropout linear regulator (3.3V output)"),
        ],
        "Analog Circuits": [
            ("bandgap_reference.spice", "Bandgap Reference", "Temperature-stable 1.25V reference"),
            ("differential_amplifier.spice", "Differential Amplifier", "Classic long-tail pair (~40dB gain)"),
            ("rc_highpass.spice", "RC High-Pass Filter", "First order high-pass (1kHz cutoff)"),
        ],
        "Data Converters": [
            ("sar_adc.spice", "SAR ADC", "8-bit Successive Approximation ADC"),
            ("sigma_delta_adc.spice", "Sigma-Delta ADC", "First order sigma-delta modulator"),
            ("r2r_dac.spice", "R-2R DAC", "8-bit R-2R ladder DAC"),
        ],
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Standard Circuit Library")
        self.setMinimumSize(700, 500)
        self.selected_circuit = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        
        # Left panel - circuit list
        left_layout = QVBoxLayout()
        
        self.circuit_list = QListWidget()
        self.circuit_list.currentItemChanged.connect(self._on_circuit_selected)
        self.circuit_list.itemDoubleClicked.connect(self._on_circuit_double_clicked)
        
        # Populate list
        for category, circuits in self.CIRCUIT_CATEGORIES.items():
            # Category header
            cat_item = QListWidgetItem(f"── {category} ──")
            cat_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.circuit_list.addItem(cat_item)
            
            for filename, name, description in circuits:
                item = QListWidgetItem(f"   {name}")
                item.setData(Qt.ItemDataRole.UserRole, {
                    'filename': filename,
                    'name': name,
                    'description': description
                })
                self.circuit_list.addItem(item)
        
        left_layout.addWidget(QLabel("Select a Circuit:"))
        left_layout.addWidget(self.circuit_list)
        
        # Right panel - circuit preview
        right_layout = QVBoxLayout()
        
        self.description_label = QLabel("Select a circuit to view its description.")
        self.description_label.setWordWrap(True)
        right_layout.addWidget(self.description_label)
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMinimumHeight(300)
        right_layout.addWidget(QLabel("Circuit Netlist:"))
        right_layout.addWidget(self.preview_text)
        
        # Buttons
        button_box = QDialogButtonBox()
        self.load_btn = QPushButton("Load Circuit")
        self.load_btn.setEnabled(False)
        self.load_btn.clicked.connect(self.accept)
        
        self.simulate_btn = QPushButton("Load && Simulate")
        self.simulate_btn.setEnabled(False)
        self.simulate_btn.clicked.connect(self._load_and_simulate)
        
        button_box.addButton(self.load_btn, QDialogButtonBox.ButtonRole.AcceptRole)
        button_box.addButton(self.simulate_btn, QDialogButtonBox.ButtonRole.ActionRole)
        button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        button_box.rejected.connect(self.reject)
        
        right_layout.addWidget(button_box)
        
        # Add panels to layout
        layout.addLayout(left_layout, 1)
        layout.addLayout(right_layout, 2)
    
    def _on_circuit_selected(self, item):
        if not item:
            return
        
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        self.selected_circuit = data
        self.load_btn.setEnabled(True)
        self.simulate_btn.setEnabled(True)
        
        # Update description
        self.description_label.setText(
            f"<b>{data['name']}</b><br><br>{data['description']}"
        )
        
        # Load and show netlist preview
        circuit_path = self._get_circuit_path(data['filename'])
        if circuit_path and circuit_path.exists():
            self.preview_text.setText(circuit_path.read_text())
        else:
            self.preview_text.setText("Circuit file not found.")
    
    def _on_circuit_double_clicked(self, item):
        if item.data(Qt.ItemDataRole.UserRole):
            self.accept()
    
    def _load_and_simulate(self):
        self.selected_circuit['simulate'] = True
        self.accept()
    
    def _get_circuit_path(self, filename: str) -> Path:
        """Get the full path to a standard circuit file."""
        # Look in examples/standard_circuits directory
        base_path = Path(__file__).parent.parent.parent / "examples" / "standard_circuits"
        return base_path / filename
    
    def get_selected_circuit(self):
        """Return the selected circuit data."""
        return self.selected_circuit


class AutoDesignDialog(QDialog):
    """Dialog for configuring auto-design parameters.

    Lets the user pick a block type and set target specifications,
    then kicks off iterative optimization.
    """

    BLOCK_SPECS = {
        'ldo': {
            'title': 'LDO Voltage Regulator',
            'params': [
                ('vout', 'Output Voltage (V)', 1.2, 0.3, 5.0),
                ('vin', 'Input Voltage (V)', 3.3, 1.0, 5.5),
                ('dropout', 'Dropout Voltage (V)', 0.2, 0.05, 1.0),
                ('iout_max', 'Max Output Current (A)', 0.1, 1e-6, 1.0),
                ('loop_gain', 'Loop Gain (dB)', 60.0, 20.0, 100.0),
                ('bandwidth', 'Bandwidth (Hz)', 1e6, 1e3, 100e6),
            ],
        },
        'ota': {
            'title': 'OTA (Transconductance Amp)',
            'params': [
                ('gain', 'DC Gain (dB)', 70.0, 20.0, 120.0),
                ('bandwidth', 'Bandwidth (Hz)', 10e6, 1e3, 1e9),
                ('ibias', 'Bias Current (A)', 50e-6, 1e-6, 1e-3),
                ('vdd', 'Supply Voltage (V)', 1.8, 1.0, 5.0),
                ('cl', 'Load Capacitance (F)', 2e-12, 0.1e-12, 100e-12),
            ],
        },
        'current_mirror': {
            'title': 'Current Mirror',
            'params': [
                ('iref', 'Reference Current (A)', 10e-6, 1e-9, 10e-3),
                ('ratio', 'Mirror Ratio', 1.0, 0.01, 100.0),
            ],
        },
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Auto-Design - Target Specifications")
        self.setMinimumSize(500, 450)
        self._block_type = 'ldo'
        self._param_edits: dict[str, 'QLineEdit'] = {}
        self._setup_ui()

    def _setup_ui(self):
        from PyQt6.QtWidgets import (
            QComboBox, QFormLayout, QGroupBox, QLineEdit
        )

        layout = QVBoxLayout(self)

        # Block type selector
        layout.addWidget(QLabel("Select Analog Block:"))
        self.block_combo = QComboBox()
        for key, info in self.BLOCK_SPECS.items():
            self.block_combo.addItem(info['title'], key)
        self.block_combo.currentIndexChanged.connect(self._on_block_changed)
        layout.addWidget(self.block_combo)

        # Specs group
        self.specs_group = QGroupBox("Target Specifications")
        self.specs_layout = QFormLayout()
        self.specs_group.setLayout(self.specs_layout)
        layout.addWidget(self.specs_group)

        self._populate_specs('ldo')

        # Buttons
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _on_block_changed(self, index):
        block_key = self.block_combo.currentData()
        if block_key:
            self._block_type = block_key
            self._populate_specs(block_key)

    def _populate_specs(self, block_key: str):
        from PyQt6.QtWidgets import QLineEdit

        # Clear existing
        while self.specs_layout.count():
            item = self.specs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._param_edits.clear()
        info = self.BLOCK_SPECS.get(block_key, {})
        for name, label, default, min_v, max_v in info.get('params', []):
            edit = QLineEdit(str(default))
            edit.setToolTip(f"Range: {min_v} – {max_v}")
            self._param_edits[name] = edit
            self.specs_layout.addRow(label, edit)

    def get_block_type(self) -> str:
        return self._block_type

    def get_specs(self) -> dict[str, float]:
        specs = {}
        for name, edit in self._param_edits.items():
            try:
                specs[name] = float(edit.text())
            except ValueError:
                pass
        return specs


class MainWindow(QMainWindow):
    """Main application window for the AMS Simulator."""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("AMS Simulator - Analog Mixed Signal Circuit Simulator")
        self.setMinimumSize(1200, 800)
        
        # Settings
        self.settings = QSettings("AMSSimulator", "AMSSimulator")
        
        # Current project state
        self.current_file = None
        self.modified = False
        
        # Initialize UI
        self._setup_ui()
        self._create_menus()
        self._create_toolbars()
        self._create_statusbar()
        self._connect_signals()
        
        # Restore window state
        self._restore_state()
    
    def _setup_ui(self):
        """Setup the main UI layout."""
        # Central widget with splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Main splitter (horizontal)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.main_splitter)
        
        # Left panel - Component Library
        self.component_library = ComponentLibrary()
        self.component_library.setMinimumWidth(200)
        self.component_library.setMaximumWidth(350)
        
        # Center panel - Schematic Editor and Waveform Viewer
        center_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Schematic editor tabs
        self.schematic_tabs = QTabWidget()
        self.schematic_tabs.setTabsClosable(True)
        self.schematic_tabs.setMovable(True)
        
        # Create initial schematic
        self.schematic_editor = SchematicEditor()
        self.schematic_tabs.addTab(self.schematic_editor, "Untitled")
        
        # Waveform viewer
        self.waveform_viewer = WaveformViewer()
        self.waveform_viewer.setMinimumHeight(150)
        
        # Terminal widget
        self.terminal_widget = TerminalWidget()
        self.terminal_widget.setMinimumHeight(150)
        
        center_splitter.addWidget(self.schematic_tabs)
        center_splitter.addWidget(self.waveform_viewer)
        center_splitter.addWidget(self.terminal_widget)
        center_splitter.setSizes([500, 150, 200])
        
        # Right panel - Property Editor and Netlist
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        
        self.property_editor = PropertyEditor()
        self.property_editor.setMinimumWidth(250)
        self.property_editor.setMaximumWidth(400)
        
        self.netlist_viewer = NetlistViewer()
        self.netlist_viewer.setMinimumHeight(100)
        
        right_splitter.addWidget(self.property_editor)
        right_splitter.addWidget(self.netlist_viewer)
        right_splitter.setSizes([400, 200])
        
        # Add all to main splitter
        self.main_splitter.addWidget(self.component_library)
        self.main_splitter.addWidget(center_splitter)
        self.main_splitter.addWidget(right_splitter)
        self.main_splitter.setSizes([250, 700, 300])
    
    def _create_menus(self):
        """Create the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        new_action = QAction("&New", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._new_schematic)
        file_menu.addAction(new_action)
        
        open_action = QAction("&Open...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_file)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        save_action = QAction("&Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._save_file)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.triggered.connect(self._save_file_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        export_netlist_action = QAction("Export &Netlist...", self)
        export_netlist_action.triggered.connect(self._export_netlist)
        file_menu.addAction(export_netlist_action)
        
        export_image_action = QAction("Export &Image...", self)
        export_image_action.triggered.connect(self._export_image)
        file_menu.addAction(export_image_action)
        
        file_menu.addSeparator()
        
        # Standard Circuits submenu
        circuits_menu = file_menu.addMenu("Open Standard &Circuit")
        
        open_library_action = QAction("Browse Circuit &Library...", self)
        open_library_action.triggered.connect(self._open_circuit_library)
        circuits_menu.addAction(open_library_action)
        
        circuits_menu.addSeparator()
        
        # Quick access to common circuits
        buck_action = QAction("Buck Converter", self)
        buck_action.triggered.connect(lambda: self._load_standard_circuit("buck_converter.spice"))
        circuits_menu.addAction(buck_action)
        
        boost_action = QAction("Boost Converter", self)
        boost_action.triggered.connect(lambda: self._load_standard_circuit("boost_converter.spice"))
        circuits_menu.addAction(boost_action)
        
        ldo_action = QAction("LDO Regulator", self)
        ldo_action.triggered.connect(lambda: self._load_standard_circuit("ldo_regulator.spice"))
        circuits_menu.addAction(ldo_action)
        
        bandgap_action = QAction("Bandgap Reference", self)
        bandgap_action.triggered.connect(lambda: self._load_standard_circuit("bandgap_reference.spice"))
        circuits_menu.addAction(bandgap_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        
        undo_action = QAction("&Undo", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self._undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("&Redo", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self._redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        cut_action = QAction("Cu&t", self)
        cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        cut_action.triggered.connect(self._cut)
        edit_menu.addAction(cut_action)
        
        copy_action = QAction("&Copy", self)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.triggered.connect(self._copy)
        edit_menu.addAction(copy_action)
        
        paste_action = QAction("&Paste", self)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        paste_action.triggered.connect(self._paste)
        edit_menu.addAction(paste_action)
        
        delete_action = QAction("&Delete", self)
        delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        delete_action.triggered.connect(self._delete)
        edit_menu.addAction(delete_action)
        
        edit_menu.addSeparator()
        
        select_all_action = QAction("Select &All", self)
        select_all_action.setShortcut(QKeySequence.StandardKey.SelectAll)
        select_all_action.triggered.connect(self._select_all)
        edit_menu.addAction(select_all_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        zoom_in_action = QAction("Zoom &In", self)
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.triggered.connect(self._zoom_in)
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("Zoom &Out", self)
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out_action.triggered.connect(self._zoom_out)
        view_menu.addAction(zoom_out_action)
        
        zoom_fit_action = QAction("&Fit to Window", self)
        zoom_fit_action.setShortcut(QKeySequence("Ctrl+0"))
        zoom_fit_action.triggered.connect(self._zoom_fit)
        view_menu.addAction(zoom_fit_action)
        
        view_menu.addSeparator()
        
        grid_action = QAction("Show &Grid", self)
        grid_action.setCheckable(True)
        grid_action.setChecked(True)
        grid_action.triggered.connect(self._toggle_grid)
        view_menu.addAction(grid_action)
        
        # Component menu
        component_menu = menubar.addMenu("&Component")
        
        rotate_cw_action = QAction("Rotate &Clockwise", self)
        rotate_cw_action.setShortcut(QKeySequence("R"))
        rotate_cw_action.triggered.connect(self._rotate_cw)
        component_menu.addAction(rotate_cw_action)
        
        rotate_ccw_action = QAction("Rotate &Counter-Clockwise", self)
        rotate_ccw_action.setShortcut(QKeySequence("Shift+R"))
        rotate_ccw_action.triggered.connect(self._rotate_ccw)
        component_menu.addAction(rotate_ccw_action)
        
        flip_h_action = QAction("Flip &Horizontal", self)
        flip_h_action.setShortcut(QKeySequence("H"))
        flip_h_action.triggered.connect(self._flip_horizontal)
        component_menu.addAction(flip_h_action)
        
        flip_v_action = QAction("Flip &Vertical", self)
        flip_v_action.setShortcut(QKeySequence("V"))
        flip_v_action.triggered.connect(self._flip_vertical)
        component_menu.addAction(flip_v_action)
        
        # Simulate menu
        simulate_menu = menubar.addMenu("&Simulate")
        
        dc_analysis_action = QAction("&DC Analysis", self)
        dc_analysis_action.triggered.connect(lambda: self._run_simulation("DC"))
        simulate_menu.addAction(dc_analysis_action)
        
        ac_analysis_action = QAction("&AC Analysis", self)
        ac_analysis_action.triggered.connect(lambda: self._run_simulation("AC"))
        simulate_menu.addAction(ac_analysis_action)
        
        transient_action = QAction("&Transient Analysis", self)
        transient_action.setShortcut(QKeySequence("F5"))
        transient_action.triggered.connect(lambda: self._run_simulation("Transient"))
        simulate_menu.addAction(transient_action)
        
        simulate_menu.addSeparator()
        
        simulation_settings_action = QAction("Simulation &Settings...", self)
        simulation_settings_action.triggered.connect(self._simulation_settings)
        simulate_menu.addAction(simulation_settings_action)
        
        simulate_menu.addSeparator()
        
        run_verilog_action = QAction("Run &Verilog Simulation", self)
        run_verilog_action.triggered.connect(self._run_verilog)
        simulate_menu.addAction(run_verilog_action)
        
        run_verilog_a_action = QAction("Run Verilog-&A Simulation", self)
        run_verilog_a_action.triggered.connect(self._run_verilog_a)
        simulate_menu.addAction(run_verilog_a_action)
        
        run_verilog_ams_action = QAction("Run Verilog-A&MS Simulation", self)
        run_verilog_ams_action.triggered.connect(self._run_verilog_ams)
        simulate_menu.addAction(run_verilog_ams_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        
        netlist_action = QAction("Generate &Netlist", self)
        netlist_action.setShortcut(QKeySequence("Ctrl+N"))
        netlist_action.triggered.connect(self._generate_netlist)
        tools_menu.addAction(netlist_action)
        
        tools_menu.addSeparator()
        
        batch_sim_action = QAction("&Batch Simulation...", self)
        batch_sim_action.triggered.connect(self._batch_simulation)
        tools_menu.addAction(batch_sim_action)
        
        specs_monitor_action = QAction("&Specs Monitor...", self)
        specs_monitor_action.triggered.connect(self._specs_monitor)
        tools_menu.addAction(specs_monitor_action)
        
        tools_menu.addSeparator()
        
        # Ready Configs - One Click Design & Simulate
        ready_menu = tools_menu.addMenu("Ready &Configs")
        
        ldo_ready_action = QAction("LDO Regulator (3.3V → 1.2V)", self)
        ldo_ready_action.triggered.connect(
            lambda: self._load_ready_config("ldo_regulator.spice"))
        ready_menu.addAction(ldo_ready_action)
        
        ota_ready_action = QAction("OTA (70dB gain, 10MHz BW)", self)
        ota_ready_action.triggered.connect(
            lambda: self._auto_design_and_simulate("ota"))
        ready_menu.addAction(ota_ready_action)
        
        cm_ready_action = QAction("Current Mirror (10μA, 1:1)", self)
        cm_ready_action.triggered.connect(
            lambda: self._auto_design_and_simulate("current_mirror"))
        ready_menu.addAction(cm_ready_action)
        
        tools_menu.addSeparator()
        
        # Auto-Design
        auto_design_action = QAction("🔧 &Auto-Design...", self)
        auto_design_action.setShortcut(QKeySequence("Ctrl+Shift+D"))
        auto_design_action.triggered.connect(self._open_auto_design_dialog)
        tools_menu.addAction(auto_design_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._about)
        help_menu.addAction(about_action)
    
    def _create_toolbars(self):
        """Create toolbars."""
        # File toolbar
        file_toolbar = QToolBar("File")
        file_toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(file_toolbar)
        
        new_act = file_toolbar.addAction("New")
        new_act.triggered.connect(self._new_schematic)
        open_act = file_toolbar.addAction("Open")
        open_act.triggered.connect(self._open_file)
        save_act = file_toolbar.addAction("Save")
        save_act.triggered.connect(self._save_file)
        file_toolbar.addSeparator()
        
        # Edit toolbar
        edit_toolbar = QToolBar("Edit")
        edit_toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(edit_toolbar)
        
        undo_act = edit_toolbar.addAction("Undo")
        undo_act.triggered.connect(self._undo)
        redo_act = edit_toolbar.addAction("Redo")
        redo_act.triggered.connect(self._redo)
        edit_toolbar.addSeparator()
        cut_act = edit_toolbar.addAction("Cut")
        cut_act.triggered.connect(self._cut)
        copy_act = edit_toolbar.addAction("Copy")
        copy_act.triggered.connect(self._copy)
        paste_act = edit_toolbar.addAction("Paste")
        paste_act.triggered.connect(self._paste)
        edit_toolbar.addSeparator()
        
        # Component toolbar
        component_toolbar = QToolBar("Component")
        component_toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(component_toolbar)
        
        rcw_act = component_toolbar.addAction("Rotate CW")
        rcw_act.triggered.connect(self._rotate_cw)
        rccw_act = component_toolbar.addAction("Rotate CCW")
        rccw_act.triggered.connect(self._rotate_ccw)
        fh_act = component_toolbar.addAction("Flip H")
        fh_act.triggered.connect(self._flip_horizontal)
        fv_act = component_toolbar.addAction("Flip V")
        fv_act.triggered.connect(self._flip_vertical)
        component_toolbar.addSeparator()
        
        # Wire toolbar
        wire_toolbar = QToolBar("Wire")
        wire_toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(wire_toolbar)
        
        wire_act = wire_toolbar.addAction("Wire")
        wire_act.triggered.connect(self._start_wire_mode)
        bus_act = wire_toolbar.addAction("Bus")
        bus_act.triggered.connect(self._start_wire_mode)
        wire_toolbar.addSeparator()
        
        # Simulation toolbar
        sim_toolbar = QToolBar("Simulation")
        sim_toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(sim_toolbar)
        
        dc_act = sim_toolbar.addAction("DC")
        dc_act.triggered.connect(lambda: self._run_simulation("DC"))
        ac_act = sim_toolbar.addAction("AC")
        ac_act.triggered.connect(lambda: self._run_simulation("AC"))
        tran_act = sim_toolbar.addAction("Transient")
        tran_act.triggered.connect(lambda: self._run_simulation("Transient"))
        sim_toolbar.addSeparator()
        
        self._run_action = sim_toolbar.addAction("▶ Run")
        self._run_action.triggered.connect(self._run_toolbar_simulation)
        self._stop_action = sim_toolbar.addAction("■ Stop")
        self._stop_action.triggered.connect(self._stop_toolbar_simulation)
        self._stop_action.setEnabled(False)
        
        # Standard circuits toolbar
        circuit_toolbar = QToolBar("Circuits")
        circuit_toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(circuit_toolbar)
        
        lib_act = circuit_toolbar.addAction("📚 Circuit Library")
        lib_act.triggered.connect(self._open_circuit_library)
    
    def _start_wire_mode(self):
        """Put the schematic editor into wire drawing mode."""
        from PyQt6.QtCore import QPointF
        self.schematic_editor._start_wire_draw(
            self.schematic_editor._last_mouse_pos
        )
    
    def _run_toolbar_simulation(self):
        """Run simulation from the toolbar Run button.
        
        If components exist on the schematic, run from schematic.
        If a netlist is loaded in the viewer, run from the netlist text.
        """
        # Check if there are components on the schematic
        if self.schematic_editor._components:
            self._run_simulation("Transient")
        else:
            # Try to run from the netlist viewer text
            netlist = self.netlist_viewer.get_netlist()
            if netlist and netlist.strip():
                tab_name = self.schematic_tabs.tabText(
                    self.schematic_tabs.currentIndex()
                )
                self._run_action.setEnabled(False)
                self._stop_action.setEnabled(True)
                self._run_netlist_simulation(netlist, tab_name)
                self._run_action.setEnabled(True)
                self._stop_action.setEnabled(False)
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self, "No Circuit",
                    "Please draw a schematic or load a standard circuit first.\n\n"
                    "Tip: Use File → Open Standard Circuit → Browse Circuit Library"
                )
    
    def _stop_toolbar_simulation(self):
        """Stop the current running simulation."""
        self._run_action.setEnabled(True)
        self._stop_action.setEnabled(False)
        self.statusbar.showMessage("Simulation stopped.")
    
    def _create_statusbar(self):
        """Create status bar."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        # Coordinate display
        self.coord_label = QLabel("X: 0  Y: 0")
        self.statusbar.addPermanentWidget(self.coord_label)
        
        # Zoom display
        self.zoom_label = QLabel("Zoom: 100%")
        self.statusbar.addPermanentWidget(self.zoom_label)
        
        # Mode display
        self.mode_label = QLabel("Mode: Select")
        self.statusbar.addPermanentWidget(self.mode_label)
        
        # Engine status display
        self.engine_label = QLabel()
        self._update_engine_status()
        self.statusbar.addPermanentWidget(self.engine_label)
        
        self.statusbar.showMessage("Ready")
    
    def _update_engine_status(self):
        """Update the simulation engine status in status bar."""
        try:
            from simulator.engine.ngspice_backend import NgSpiceBackend
            backend = NgSpiceBackend()
            if backend.is_available():
                self.engine_label.setText("Engine: NgSpice ✓")
                self.engine_label.setToolTip(f"NgSpice available at {backend.ngspice_path}")
                self.engine_label.setStyleSheet("color: green;")
            else:
                self.engine_label.setText("Engine: Python")
                self.engine_label.setToolTip("NgSpice not found. Using built-in Python engine.")
                self.engine_label.setStyleSheet("color: orange;")
        except Exception:
            self.engine_label.setText("Engine: Python")
            self.engine_label.setStyleSheet("color: orange;")
    
    def _connect_signals(self):
        """Connect signals between components."""
        # Component library -> Schematic editor
        self.component_library.component_selected.connect(
            self.schematic_editor.start_component_placement
        )
        
        # Schematic editor -> Property editor
        self.schematic_editor.selection_changed.connect(
            self.property_editor.set_component
        )
        
        # Schematic editor -> Status bar
        self.schematic_editor.cursor_moved.connect(self._update_coordinates)
        self.schematic_editor.zoom_changed.connect(self._update_zoom)
        self.schematic_editor.mode_changed.connect(self._update_mode)
        
        # Property editor -> Schematic editor (update component)
        self.property_editor.property_changed.connect(
            self.schematic_editor.update_component
        )
        
        # Schematic tabs
        self.schematic_tabs.tabCloseRequested.connect(self._close_tab)
    
    def _restore_state(self):
        """Restore window state from settings."""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)
    
    def closeEvent(self, event):
        """Handle window close event."""
        if self.modified:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "Do you want to save changes before closing?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Save:
                self._save_file()
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        
        # Save window state
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        
        event.accept()
    
    # File operations
    def _new_schematic(self):
        """Create a new schematic."""
        editor = SchematicEditor()
        index = self.schematic_tabs.addTab(editor, "Untitled")
        self.schematic_tabs.setCurrentIndex(index)
        self.schematic_editor = editor
        self._connect_editor_signals(editor)
    
    def _open_file(self):
        """Open a schematic file."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open Schematic",
            "",
            "AMS Schematic (*.ams);;Netlist (*.sp *.spice);;Verilog (*.v *.sv);;All Files (*.*)"
        )
        if filename:
            self._load_file(filename)
    
    def _load_file(self, filename: str):
        """Load a file."""
        try:
            editor = SchematicEditor()
            editor.load_from_file(filename)
            
            import os
            tab_name = os.path.basename(filename)
            index = self.schematic_tabs.addTab(editor, tab_name)
            self.schematic_tabs.setCurrentIndex(index)
            self.schematic_editor = editor
            self._connect_editor_signals(editor)
            
            self.current_file = filename
            self.statusbar.showMessage(f"Loaded: {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file:\n{str(e)}")
    
    def _save_file(self):
        """Save the current schematic."""
        if self.current_file:
            self._save_to_file(self.current_file)
        else:
            self._save_file_as()
    
    def _save_file_as(self):
        """Save the current schematic with a new name."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Schematic",
            "",
            "AMS Schematic (*.ams);;All Files (*.*)"
        )
        if filename:
            self._save_to_file(filename)
    
    def _save_to_file(self, filename: str):
        """Save to a specific file."""
        try:
            self.schematic_editor.save_to_file(filename)
            self.current_file = filename
            self.modified = False
            
            import os
            tab_name = os.path.basename(filename)
            current_index = self.schematic_tabs.currentIndex()
            self.schematic_tabs.setTabText(current_index, tab_name)
            
            self.statusbar.showMessage(f"Saved: {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file:\n{str(e)}")
    
    def _export_netlist(self):
        """Export the circuit netlist."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Netlist",
            "",
            "SPICE Netlist (*.sp *.spice);;All Files (*.*)"
        )
        if filename:
            try:
                netlist = self.schematic_editor.generate_netlist()
                with open(filename, 'w') as f:
                    f.write(netlist)
                self.statusbar.showMessage(f"Netlist exported: {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export netlist:\n{str(e)}")
    
    def _export_image(self):
        """Export schematic as image."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Image",
            "",
            "PNG Image (*.png);;PDF Document (*.pdf);;SVG Image (*.svg)"
        )
        if filename:
            try:
                self.schematic_editor.export_image(filename)
                self.statusbar.showMessage(f"Image exported: {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export image:\n{str(e)}")
    
    def _close_tab(self, index: int):
        """Close a schematic tab."""
        if self.schematic_tabs.count() > 1:
            self.schematic_tabs.removeTab(index)
            self.schematic_editor = self.schematic_tabs.currentWidget()
    
    def _connect_editor_signals(self, editor: SchematicEditor):
        """Connect signals for a new editor."""
        editor.selection_changed.connect(self.property_editor.set_component)
        editor.cursor_moved.connect(self._update_coordinates)
        editor.zoom_changed.connect(self._update_zoom)
        editor.mode_changed.connect(self._update_mode)
    
    # Edit operations
    def _undo(self):
        self.schematic_editor.undo()
    
    def _redo(self):
        self.schematic_editor.redo()
    
    def _cut(self):
        self.schematic_editor.cut()
    
    def _copy(self):
        self.schematic_editor.copy()
    
    def _paste(self):
        self.schematic_editor.paste()
    
    def _delete(self):
        self.schematic_editor.delete_selected()
    
    def _select_all(self):
        self.schematic_editor.select_all()
    
    # View operations
    def _zoom_in(self):
        self.schematic_editor.zoom_in()
    
    def _zoom_out(self):
        self.schematic_editor.zoom_out()
    
    def _zoom_fit(self):
        self.schematic_editor.zoom_fit()
    
    def _toggle_grid(self, checked: bool):
        self.schematic_editor.set_grid_visible(checked)
    
    # Component operations
    def _rotate_cw(self):
        self.schematic_editor.rotate_selected(90)
    
    def _rotate_ccw(self):
        self.schematic_editor.rotate_selected(-90)
    
    def _flip_horizontal(self):
        self.schematic_editor.flip_selected_horizontal()
    
    def _flip_vertical(self):
        self.schematic_editor.flip_selected_vertical()
    
    # Simulation operations
    def _run_simulation(self, analysis_type: str):
        """Run a simulation."""
        try:
            # Generate netlist
            netlist = self.schematic_editor.generate_netlist()
            
            # Show simulation dialog
            dialog = SimulationDialog(analysis_type, netlist, self)
            if dialog.exec():
                results = dialog.get_results()
                if results:
                    self.waveform_viewer.display_results(results)
                    self._show_waveform_viewer()  # Auto-open waveform viewer
                    self.statusbar.showMessage(f"{analysis_type} simulation completed")
        except Exception as e:
            QMessageBox.critical(self, "Simulation Error", str(e))
    
    def _show_waveform_viewer(self):
        """Ensure the waveform viewer is visible and has adequate space."""
        # Get the center splitter (parent of waveform viewer)
        center_splitter = self.waveform_viewer.parent()
        if isinstance(center_splitter, QSplitter):
            sizes = center_splitter.sizes()
            # Ensure waveform viewer has at least 200 pixels
            if len(sizes) >= 2 and sizes[1] < 200:
                total = sum(sizes)
                sizes[0] = total - 400  # Reserve 400 for waveform + terminal
                sizes[1] = 250  # Waveform viewer
                if len(sizes) > 2:
                    sizes[2] = 150  # Terminal
                center_splitter.setSizes(sizes)
    
    def _simulation_settings(self):
        """Open simulation settings dialog."""
        dialog = SimulationDialog("Settings", "", self)
        dialog.exec()
    
    def _run_verilog(self):
        """Run Verilog digital simulation."""
        self.statusbar.showMessage("Running Verilog simulation...")
        # TODO: Implement Verilog simulation
    
    def _run_verilog_a(self):
        """Run Verilog-A analog simulation."""
        self.statusbar.showMessage("Running Verilog-A simulation...")
        # TODO: Implement Verilog-A simulation
    
    def _run_verilog_ams(self):
        """Run Verilog-AMS mixed signal simulation."""
        self.statusbar.showMessage("Running Verilog-AMS simulation...")
        # TODO: Implement Verilog-AMS simulation
    
    # Tool operations
    def _generate_netlist(self):
        """Generate and display netlist."""
        netlist = self.schematic_editor.generate_netlist()
        self.netlist_viewer.set_netlist(netlist)
    
    def _batch_simulation(self):
        """Open batch simulation dialog."""
        QMessageBox.information(self, "Batch Simulation", 
            "Batch simulation allows running multiple simulations.\n"
            "Use the CLI: ams-batch --dir <netlists_dir>")
    
    def _specs_monitor(self):
        """Open specs monitor dialog."""
        QMessageBox.information(self, "Specs Monitor",
            "Specs monitoring tracks simulation results against specifications.\n"
            "Define specs in your simulation configuration.")
    
    # Status bar updates
    def _update_coordinates(self, x: float, y: float):
        self.coord_label.setText(f"X: {x:.1f}  Y: {y:.1f}")
    
    def _update_zoom(self, zoom: float):
        self.zoom_label.setText(f"Zoom: {zoom*100:.0f}%")
    
    def _update_mode(self, mode: str):
        self.mode_label.setText(f"Mode: {mode}")
    
    def _about(self):
        """Show about dialog."""
        QMessageBox.about(self, "About AMS Simulator",
            "<h3>AMS Simulator</h3>"
            "<p>Version 1.0.0</p>"
            "<p>Analog Mixed Signal Circuit Simulator</p>"
            "<p>Features:</p>"
            "<ul>"
            "<li>Schematic capture with drag-and-drop components</li>"
            "<li>DC, AC, and Transient analysis</li>"
            "<li>Verilog, Verilog-A, and Verilog-AMS simulation</li>"
            "<li>Mixed-signal interface</li>"
            "<li>Waveform viewer with measurements</li>"
            "<li>Batch simulation and reporting</li>"
            "</ul>")
    
    def _open_circuit_library(self):
        """Open the standard circuit library browser."""
        dialog = CircuitLibraryDialog(self)
        if dialog.exec():
            circuit_data = dialog.get_selected_circuit()
            if circuit_data:
                self._load_standard_circuit(
                    circuit_data['filename'],
                    simulate=circuit_data.get('simulate', False)
                )
    
    def _load_standard_circuit(self, filename: str, simulate: bool = False):
        """Load a standard circuit from the library.
        
        Reads the SPICE netlist, displays it in the netlist viewer,
        creates a visual schematic on the canvas, and optionally runs simulation.
        
        Args:
            filename: Name of the .spice file in examples/standard_circuits/.
            simulate: If True, automatically run simulation after loading.
        """
        # Find the circuit file
        base_path = Path(__file__).parent.parent.parent / "examples" / "standard_circuits"
        circuit_path = base_path / filename
        
        if not circuit_path.exists():
            QMessageBox.warning(
                self, "Circuit Not Found",
                f"Could not find circuit file:\n{circuit_path}"
            )
            return
        
        try:
            # Read the netlist
            netlist = circuit_path.read_text()
            
            # Show in netlist viewer
            self.netlist_viewer.set_netlist(netlist)
            
            # Create a new editor tab for this circuit
            circuit_name = filename.replace('.spice', '').replace('_', ' ').title()
            editor = SchematicEditor()
            index = self.schematic_tabs.addTab(editor, circuit_name)
            self.schematic_tabs.setCurrentIndex(index)
            self.schematic_editor = editor
            self._connect_editor_signals(editor)
            
            # Parse netlist and draw schematic components on the canvas
            editor.load_from_netlist(netlist)
            
            self.statusbar.showMessage(f"Loaded: {circuit_name}")
            
            # Auto-run simulation if requested
            if simulate:
                self._run_netlist_simulation(netlist, circuit_name)
                
        except Exception as e:
            QMessageBox.critical(
                self, "Error Loading Circuit",
                f"Failed to load circuit:\n{str(e)}"
            )
    
    def _run_netlist_simulation(self, netlist: str, name: str):
        """Run simulation directly on a netlist string.
        
        Parses the netlist for analysis commands (.TRAN, .AC, .DC),
        extracts parameters, runs the appropriate engine analysis,
        and displays results in the waveform viewer.
        
        Args:
            netlist: SPICE netlist text.
            name: Display name for status messages.
        """
        try:
            import re
            from simulator.engine.analog_engine import (
                AnalogEngine, DCAnalysis, ACAnalysis, TransientAnalysis
            )
            
            # Parse netlist for analysis commands
            analysis_type = "Transient"  # Default
            tran_match = re.search(
                r'\.TRAN\s+(\S+)\s+(\S+)', netlist, re.I
            )
            ac_match = re.search(
                r'\.AC\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)', netlist, re.I
            )
            dc_match = re.search(
                r'\.DC\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)', netlist, re.I
            )
            
            if dc_match:
                analysis_type = "DC"
            elif ac_match:
                analysis_type = "AC"
            elif tran_match:
                analysis_type = "Transient"
            
            # Create engine and load netlist
            engine = AnalogEngine()
            engine.load_netlist(netlist)
            
            self.statusbar.showMessage(f"{name}: Running {analysis_type} analysis...")
            QApplication.processEvents()
            
            # Run appropriate analysis
            results = None
            if analysis_type == "DC":
                analysis = DCAnalysis(engine)
                settings = {}
                if dc_match:
                    settings = {
                        'source': dc_match.group(1),
                        'start': self._parse_spice_num(dc_match.group(2)),
                        'stop': self._parse_spice_num(dc_match.group(3)),
                        'step': self._parse_spice_num(dc_match.group(4)),
                    }
                results = analysis.run(settings)
            elif analysis_type == "AC":
                analysis = ACAnalysis(engine)
                settings = {
                    'variation': 'decade',
                    'points': 10,
                    'fstart': 1,
                    'fstop': 1e6
                }
                if ac_match:
                    settings = {
                        'variation': ac_match.group(1).lower(),
                        'points': int(float(ac_match.group(2))),
                        'fstart': self._parse_spice_num(ac_match.group(3)),
                        'fstop': self._parse_spice_num(ac_match.group(4)),
                    }
                results = analysis.run(settings)
            else:  # Transient
                analysis = TransientAnalysis(engine)
                settings = {
                    'tstop': 1e-3,
                    'tstep': 1e-6,
                    'tstart': 0
                }
                if tran_match:
                    tstep = self._parse_spice_num(tran_match.group(1))
                    tstop = self._parse_spice_num(tran_match.group(2))
                    # Limit number of points to keep UI responsive
                    if tstop / tstep > 50000:
                        tstep = tstop / 50000
                    settings = {
                        'tstop': tstop,
                        'tstep': tstep,
                        'tstart': 0
                    }
                
                # Progress callback
                def progress_cb(progress: float):
                    self.statusbar.showMessage(
                        f"{name}: Simulating... {progress*100:.0f}%"
                    )
                    QApplication.processEvents()
                
                results = analysis.run(settings, progress_cb)
            
            if results:
                self.waveform_viewer.display_results(results)
                self._show_waveform_viewer()
                self.statusbar.showMessage(
                    f"{name}: {analysis_type} analysis complete"
                )
            
        except Exception as e:
            QMessageBox.warning(
                self, "Simulation Error",
                f"Failed to run simulation:\n{str(e)}"
            )
            self.statusbar.showMessage(f"Simulation error: {str(e)}")
    
    def _load_ready_config(self, filename: str):
        """Load a ready-config analog block and auto-simulate it.

        Reads from examples/analog_blocks/ and runs transient analysis.
        """
        base_path = Path(__file__).parent.parent.parent / "examples" / "analog_blocks"
        circuit_path = base_path / filename

        if not circuit_path.exists():
            QMessageBox.warning(
                self, "Config Not Found",
                f"Ready config not found:\n{circuit_path}"
            )
            return

        try:
            netlist = circuit_path.read_text()
            self.netlist_viewer.set_netlist(netlist)
            circuit_name = filename.replace('.spice', '').replace('_', ' ').title()

            editor = SchematicEditor()
            index = self.schematic_tabs.addTab(editor, f"⚡ {circuit_name}")
            self.schematic_tabs.setCurrentIndex(index)
            self.schematic_editor = editor
            self._connect_editor_signals(editor)
            editor.load_from_netlist(netlist)

            self.statusbar.showMessage(f"Ready Config: {circuit_name} - Running simulation...")
            QApplication.processEvents()
            self._run_netlist_simulation(netlist, circuit_name)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load config:\n{e}")

    def _auto_design_and_simulate(self, block_type: str):
        """Run auto-designer for a block type and display results."""
        from simulator.engine.auto_designer import AutoDesigner

        default_specs = {
            'ota': {'gain': 70, 'bandwidth': 10e6, 'ibias': 50e-6, 'vdd': 1.8, 'cl': 2e-12},
            'current_mirror': {'iref': 10e-6, 'ratio': 1.0, 'type': 'nmos'},
            'ldo': {'vout': 1.2, 'vin': 3.3, 'dropout': 0.2, 'iout_max': 0.1,
                    'loop_gain': 60, 'bandwidth': 1e6},
        }
        specs = default_specs.get(block_type, {})

        self.statusbar.showMessage(f"Auto-designing {block_type.upper()}...")
        QApplication.processEvents()

        try:
            designer = AutoDesigner(max_iterations=20, verbose=False)
            result = designer.design(block_type, specs)

            netlist = result.netlist
            self.netlist_viewer.set_netlist(netlist)

            editor = SchematicEditor()
            title = f"⚡ Auto-{block_type.upper()}"
            index = self.schematic_tabs.addTab(editor, title)
            self.schematic_tabs.setCurrentIndex(index)
            self.schematic_editor = editor
            self._connect_editor_signals(editor)
            editor.load_from_netlist(netlist)

            # Run simulation on the generated netlist
            self._run_netlist_simulation(netlist, title)

            status = "✓ All specs met" if result.success else "⚠ Partial convergence"
            iters = len(result.iterations)
            self.statusbar.showMessage(
                f"Auto-Design {block_type.upper()}: {status} ({iters} iterations, "
                f"{result.elapsed_seconds:.1f}s)"
            )
        except Exception as e:
            QMessageBox.critical(self, "Auto-Design Error", f"Failed:\n{e}")

    def _open_auto_design_dialog(self):
        """Open the auto-design parameter dialog."""
        dialog = AutoDesignDialog(self)
        if dialog.exec():
            block_type = dialog.get_block_type()
            specs = dialog.get_specs()
            self._run_auto_design(block_type, specs)

    def _run_auto_design(self, block_type: str, specs: dict):
        """Run full auto-design with custom specs."""
        from simulator.engine.auto_designer import AutoDesigner

        self.statusbar.showMessage(f"Auto-designing {block_type.upper()} with custom specs...")
        QApplication.processEvents()

        try:
            designer = AutoDesigner(max_iterations=30, verbose=False)
            result = designer.design(block_type, specs)

            self.netlist_viewer.set_netlist(result.netlist)

            editor = SchematicEditor()
            title = f"⚡ {block_type.upper()} (custom)"
            index = self.schematic_tabs.addTab(editor, title)
            self.schematic_tabs.setCurrentIndex(index)
            self.schematic_editor = editor
            self._connect_editor_signals(editor)
            editor.load_from_netlist(result.netlist)

            self._run_netlist_simulation(result.netlist, title)

            # Show summary in terminal
            if hasattr(self, 'terminal'):
                summary = (
                    f"\n=== Auto-Design Results: {block_type.upper()} ===\n"
                    f"Status: {'SUCCESS' if result.success else 'PARTIAL'}\n"
                    f"Iterations: {len(result.iterations)}\n"
                    f"Time: {result.elapsed_seconds:.2f}s\n"
                    f"Final Measurements:\n"
                )
                for k, v in result.final_measurements.items():
                    summary += f"  {k}: {v:.4g}\n"
                summary += f"Design Variables:\n"
                for k, v in result.variables.items():
                    summary += f"  {k}: {v:.4g}\n"
                self.terminal.append_text(summary)
        except Exception as e:
            QMessageBox.critical(self, "Auto-Design Error", f"Failed:\n{e}")

    # ──────────────────────────────────────────────────────────────
    #  ASIC hierarchy helpers  (called from the API server thread
    #  via QTimer.singleShot so they always run on the GUI thread)
    # ──────────────────────────────────────────────────────────────

    def load_block_tab(self, tab_name: str, netlist: str) -> None:
        """Open a new schematic tab and load *netlist* into it.

        Used by the API server to populate one tab per LIN ASIC block so
        the schematic editor shows the full chip hierarchy.
        """
        editor = SchematicEditor()
        index = self.schematic_tabs.addTab(editor, tab_name)
        self.schematic_tabs.setCurrentIndex(index)
        self.schematic_editor = editor
        self._connect_editor_signals(editor)
        if netlist:
            editor.load_from_netlist(netlist)
        self.statusbar.showMessage(f"Loaded: {tab_name}")

    def run_netlist_in_window(self, results: dict, title: str) -> None:
        """Display simulation results in a new standalone waveform window.

        Opens a separate WaveformWindow (not the embedded panel) so that
        each block's waveform is shown in its own resizable window.
        """
        from simulator.gui.waveform_viewer import WaveformWindow
        win = WaveformWindow(title)
        win.display_results(results)
        win.show()
        win.raise_()

    @staticmethod
    def _parse_spice_num(s: str) -> float:
        """Parse a SPICE number with engineering suffix.
        
        Args:
            s: String like '100u', '1.5k', '10MEG', '500n'.
            
        Returns:
            Parsed float value.
        """
        import re
        s = s.strip().upper()
        suffixes = {
            'T': 1e12, 'G': 1e9, 'MEG': 1e6, 'K': 1e3,
            'M': 1e-3, 'U': 1e-6, 'N': 1e-9, 'P': 1e-12, 'F': 1e-15,
        }
        match = re.match(
            r'^([+-]?\d+\.?\d*(?:[eE][+-]?\d+)?)\s*(MEG|[TGKMNUPF])?',
            s, re.I
        )
        if match:
            num = float(match.group(1))
            suffix = (match.group(2) or '').upper()
            return num * suffixes.get(suffix, 1.0)
        return float(s)

