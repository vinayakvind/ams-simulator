"""
Main application window for the AMS Simulator.
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QToolBar, QStatusBar, QMenuBar, QMenu, QFileDialog, QMessageBox,
    QDockWidget, QTabWidget, QLabel, QDialog, QListWidget, QListWidgetItem,
    QPushButton, QTextEdit, QDialogButtonBox, QApplication, QLineEdit,
    QTreeWidget, QTreeWidgetItem, QAbstractItemView
)
from PyQt6.QtCore import Qt, QSettings, QSize, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QKeySequence

from simulator.gui.schematic_editor import SchematicEditor
from simulator.gui.component_library import ComponentLibrary
from simulator.gui.property_editor import PropertyEditor
from simulator.gui.source_viewer import SourceCodeWindow
from simulator.gui.test_tracker_window import TestTrackerWindow
from simulator.gui.waveform_viewer import WaveformWindow
from simulator.gui.simulation_dialog import SimulationDialog
from simulator.gui.netlist_viewer import NetlistViewer
from simulator.gui.terminal_widget import TerminalWidget


SUPPORTED_DESIGN_LIBRARY_SUFFIXES = {
    ".sp",
    ".spice",
    ".v",
    ".sv",
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".html",
    ".txt",
    ".py",
}


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

    gui_call_requested = pyqtSignal(object)
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("AMS Simulator - Analog Mixed Signal Circuit Simulator")
        self.setMinimumSize(1200, 800)
        
        # Settings
        self.settings = QSettings("AMSSimulator", "AMSSimulator")
        
        # Current project state
        self._repo_root = Path(__file__).parent.parent.parent
        self._designs_root = self._repo_root / "designs"
        self._reports_root = self._repo_root / "reports"
        self.current_file = None
        self.modified = False
        self.api_session_guid = "waiting-for-server"
        self.api_base_url = "http://127.0.0.1:5100"
        self._hierarchy_tab_specs: dict[str, dict] = {}
        self._hierarchy_top_level_tab_name: Optional[str] = None
        self._hierarchy_top_level_spec: Optional[dict] = None
        self._source_windows: dict[str, SourceCodeWindow] = {}
        self._last_source_window_key: Optional[str] = None
        self._test_tracker_window: Optional[TestTrackerWindow] = None
        self._last_regression_report: Optional[dict] = None
        self._last_regression_command = ""
        self._design_library_recent_entry: Optional[dict[str, Any]] = None
        self._asic_test_plan_path = (
            self._designs_root / "lin_asic" / "LIN_ASIC_TESTPLAN.md"
        )
        self._asic_architecture_path = (
            self._designs_root / "lin_asic" / "01_ARCHITECTURE.md"
        )
        self._asic_regression_report_path = (
            self._reports_root / "lin_asic_regression_latest.json"
        )
        self._asic_regression_log_path = (
            self._reports_root / "lin_asic_regression_latest.log"
        )
        self._latest_waveform_window: Optional[WaveformWindow] = None
        self._waveform_windows: list = []
        self.gui_call_requested.connect(self._execute_gui_call)
        
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
        
        # Center panel - Schematic Editor and terminal
        center_splitter = QSplitter(Qt.Orientation.Vertical)
        self._center_splitter = center_splitter
        
        # Schematic editor tabs
        self.schematic_tabs = QTabWidget()
        self.schematic_tabs.setTabsClosable(True)
        self.schematic_tabs.setMovable(True)
        
        # Create initial schematic
        self.schematic_editor = SchematicEditor()
        self.schematic_tabs.addTab(self.schematic_editor, "Untitled")
        
        # Terminal widget
        self.terminal_widget = TerminalWidget()
        self.terminal_widget.setMinimumHeight(150)
        
        center_splitter.addWidget(self.schematic_tabs)
        center_splitter.addWidget(self.terminal_widget)
        center_splitter.setSizes([700, 200])
        
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

        self._create_api_session_monitor()
        self._create_design_library_browser()

    def _create_api_session_monitor(self):
        """Create a live dock that shows API session GUID and call flow."""
        dock = QDockWidget("API Session Monitor", self)
        dock.setObjectName("api_session_monitor_dock")
        dock.setAllowedAreas(
            Qt.DockWidgetArea.BottomDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea
        )

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 8, 8, 8)

        self.api_session_label = QLabel()
        self.api_session_label.setWordWrap(True)
        self.api_session_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.api_handshake_label = QLabel()
        self.api_handshake_label.setWordWrap(True)
        self.api_handshake_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.api_session_log = QTextEdit()
        self.api_session_log.setReadOnly(True)
        self.api_session_log.setMinimumHeight(170)
        self.api_session_log.setPlaceholderText(
            "Live API calls, request payloads, and schematic handshake will appear here."
        )

        layout.addWidget(self.api_session_label)
        layout.addWidget(self.api_handshake_label)
        layout.addWidget(self.api_session_log)

        dock.setWidget(content)
        self.api_session_dock = dock
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
        self._refresh_api_session_monitor()

    def _create_design_library_browser(self) -> None:
        """Create a docked browser for design projects, files, and chip views."""
        dock = QDockWidget("Design Library Browser", self)
        dock.setObjectName("design_library_browser_dock")
        dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea
        )

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 8, 8, 8)

        self.design_library_filter = QLineEdit()
        self.design_library_filter.setPlaceholderText(
            "Filter projects, blocks, RTL, reports, or chip profiles..."
        )
        self.design_library_filter.textChanged.connect(self._apply_design_library_filter)
        layout.addWidget(self.design_library_filter)

        action_row = QHBoxLayout()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_design_library_browser)
        action_row.addWidget(refresh_btn)

        open_btn = QPushButton("Open Selected")
        open_btn.clicked.connect(self._open_selected_design_library_item)
        action_row.addWidget(open_btn)

        run_btn = QPushButton("Run + Waveforms")
        run_btn.clicked.connect(self._run_selected_design_library_item)
        action_row.addWidget(run_btn)

        recent_btn = QPushButton("Launch Recent Chip")
        recent_btn.clicked.connect(self._launch_recent_chip_design)
        action_row.addWidget(recent_btn)

        layout.addLayout(action_row)

        browser_splitter = QSplitter(Qt.Orientation.Vertical)

        self.design_library_tree = QTreeWidget()
        self.design_library_tree.setHeaderLabels(["Design Item", "Type"])
        self.design_library_tree.setAlternatingRowColors(True)
        self.design_library_tree.setRootIsDecorated(True)
        self.design_library_tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.design_library_tree.setColumnWidth(0, 260)
        self.design_library_tree.currentItemChanged.connect(self._on_design_library_item_selected)
        self.design_library_tree.itemDoubleClicked.connect(self._on_design_library_item_activated)
        browser_splitter.addWidget(self.design_library_tree)

        self.design_library_preview = QTextEdit()
        self.design_library_preview.setReadOnly(True)
        self.design_library_preview.setPlaceholderText(
            "Select a project, block, or file to preview its location and contents."
        )
        browser_splitter.addWidget(self.design_library_preview)
        browser_splitter.setSizes([340, 260])

        layout.addWidget(browser_splitter)

        dock.setWidget(content)
        self.design_library_dock = dock
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)

        self._refresh_design_library_browser()

    @staticmethod
    def _make_design_library_entry(
        label: str,
        kind: str,
        *,
        path: str = "",
        open_mode: str = "",
        run_mode: str = "",
        run_path: str = "",
        title: str = "",
        focus_alias: str = "",
        pin_names: Optional[list[str]] = None,
        summary_lines: Optional[list[str]] = None,
        children: Optional[list[dict[str, Any]]] = None,
        recent_candidate: bool = False,
        modified_at: float = 0.0,
    ) -> dict[str, Any]:
        """Create a serialisable design-library tree entry."""
        return {
            "label": label,
            "kind": kind,
            "path": path,
            "open_mode": open_mode,
            "run_mode": run_mode,
            "run_path": run_path,
            "title": title or label,
            "focus_alias": focus_alias,
            "pin_names": list(pin_names or []),
            "summary_lines": list(summary_lines or []),
            "children": list(children or []),
            "recent_candidate": recent_candidate,
            "modified_at": modified_at,
        }

    @staticmethod
    def _read_json_file_safe(path: Path) -> Optional[dict[str, Any]]:
        """Read a JSON document if it exists and is valid."""
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _friendly_design_label(value: str) -> str:
        """Convert a snake_case file stem into a readable title."""
        return value.replace("_", " ").replace("-", " ").title()

    @staticmethod
    def _extract_subckt_ports(file_path: Path) -> list[str]:
        """Return the first .SUBCKT port list declared in a SPICE file."""
        if not file_path.exists() or file_path.suffix.lower() not in {".sp", ".spice"}:
            return []

        try:
            file_text = MainWindow._read_text_file(file_path)
            for raw_line in file_text.splitlines():
                stripped = raw_line.strip()
                if stripped.upper().startswith(".SUBCKT"):
                    parts = stripped.split()
                    return parts[2:] if len(parts) > 2 else []
        except OSError:
            return []
        return []

    @staticmethod
    def _format_pin_summary(pin_names: list[str], limit: int = 8) -> str:
        """Render a compact pin summary for the browser preview."""
        if not pin_names:
            return ""
        if len(pin_names) <= limit:
            return ", ".join(pin_names)
        return f"{', '.join(pin_names[:limit])}, +{len(pin_names) - limit} more"

    @staticmethod
    def _netlist_has_analysis(netlist_text: str) -> bool:
        """Return whether a netlist contains an executable analysis directive."""
        upper_text = netlist_text.upper()
        return any(token in upper_text for token in (".TRAN", ".AC", ".DC", ".OP"))

    @staticmethod
    def _find_default_run_entry(entries: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
        """Return the first nested entry that has a run action."""
        for entry in entries:
            if entry.get("run_mode"):
                return entry
            nested = MainWindow._find_default_run_entry(entry.get("children", []))
            if nested:
                return nested
        return None

    @staticmethod
    def _parse_spice_include_target(line: str) -> Optional[str]:
        """Extract a .include path from one SPICE line."""
        stripped = line.strip()
        if not stripped.lower().startswith(".include"):
            return None
        parts = stripped.split(maxsplit=1)
        if len(parts) < 2:
            return None
        return parts[1].strip().strip('"').strip("'")

    def _read_spice_file_with_includes(
        self,
        file_path: Path,
        seen: Optional[set[Path]] = None,
    ) -> str:
        """Inline local .include files so browser-run testbenches stay self-contained."""
        resolved_path = file_path.resolve()
        visited = seen or set()
        if resolved_path in visited:
            return f"* Skipping recursive include: {resolved_path}"

        visited.add(resolved_path)
        rendered_lines: list[str] = []
        for raw_line in self._read_text_file(file_path).splitlines():
            include_target = self._parse_spice_include_target(raw_line)
            if include_target is None:
                rendered_lines.append(raw_line)
                continue

            include_path = Path(include_target)
            if not include_path.is_absolute():
                include_path = (file_path.parent / include_path).resolve()

            if not include_path.exists():
                rendered_lines.append(f"* Missing include skipped: {include_target}")
                continue

            rendered_lines.append(f"* Begin include: {include_path}")
            rendered_lines.append(self._read_spice_file_with_includes(include_path, visited))
            rendered_lines.append(f"* End include: {include_path}")

        return "\n".join(rendered_lines)

    def _build_block_wrapper_netlist(self, dut_path: Path) -> str:
        """Build a runnable top-level wrapper around one IP block netlist."""
        netlist_text = self._read_text_file(dut_path)
        body_lines: list[str] = []
        ports: list[str] = []
        in_subckt = False
        found_subckt = False

        for raw_line in netlist_text.splitlines():
            stripped = raw_line.strip()
            if stripped.upper().startswith(".SUBCKT"):
                parts = stripped.split()
                ports = parts[2:] if len(parts) > 2 else []
                found_subckt = True
                in_subckt = True
                continue
            if stripped.upper().startswith(".ENDS") and in_subckt:
                break
            if in_subckt:
                body_lines.append(raw_line)

        if not found_subckt:
            body_lines = [line for line in netlist_text.splitlines() if not line.strip().startswith(".")]
            ports = self._extract_subckt_ports(dut_path)

        if not body_lines:
            raise ValueError(f"No runnable DUT body found in {dut_path.name}")

        block_name = dut_path.stem.lower()
        has_vout = any(port.upper() == "VOUT" for port in ports)
        supply_lines: list[str] = []
        load_lines: list[str] = []

        for port in ports:
            upper = port.upper()
            if upper in {"0", "GND", "VSS", "VGND", "AVSS"} or "GND" in upper:
                supply_lines.append(f"V_{upper} {port} 0 DC 0")
            elif upper in {"VDD", "VDD_IO", "VDD_ANA", "VDD_DIGITAL"}:
                supply_lines.append(f"V_{upper} {port} 0 DC 3.3")
            elif upper == "VBAT":
                supply_lines.append(f"V_{upper} {port} 0 DC 12")
            elif upper == "VIN":
                vin_voltage = 3.3 if "digital" in block_name else 12.0
                supply_lines.append(f"V_{upper} {port} 0 DC {vin_voltage}")
            elif upper == "VREF" and has_vout:
                supply_lines.append(f"V_{upper} {port} 0 DC 1.2")
            elif upper in {"EN", "SLP_N", "TXD", "CLK", "CLK_IN", "RST_N", "CS_N", "WR", "RD", "MOSI", "SCLK"}:
                supply_lines.append(f"V_{upper} {port} 0 DC 3.3")

        for port in ports:
            upper = port.upper()
            if upper == "VOUT":
                load_lines.append(f"R_LOAD_{upper} {port} 0 100k")
                load_lines.append(f"C_LOAD_{upper} {port} 0 100p")
            elif upper == "VREF" and not has_vout:
                load_lines.append(f"R_LOAD_{upper} {port} 0 100k")

        return "\n".join([
            f"* Auto-generated wrapper for {dut_path.stem}",
            ".MODEL NMOS_3P3 NMOS (VTO=0.5 KP=120u LAMBDA=0.01 GAMMA=0.4 PHI=0.8)",
            ".MODEL PMOS_3P3 PMOS (VTO=-0.5 KP=40u LAMBDA=0.01 GAMMA=0.4 PHI=0.8)",
            ".MODEL PMOS_HV PMOS (VTO=-0.8 KP=20u LAMBDA=0.005)",
            ".MODEL NPN_VERT NPN (IS=1e-15 BF=100 BR=1)",
            "",
            *body_lines,
            "",
            "* Auto-generated supplies",
            *supply_lines,
            "",
            "* Auto-generated loads",
            *load_lines,
            "",
            ".OP",
            ".END",
        ])

    @staticmethod
    def _detect_netlist_analysis_type(netlist: str) -> str:
        """Detect the dominant analysis directive in a SPICE netlist."""
        upper_text = netlist.upper()
        if ".DC" in upper_text:
            return "DC"
        if ".AC" in upper_text:
            return "AC"
        if ".TRAN" in upper_text:
            return "Transient"
        if ".OP" in upper_text:
            return "Operating Point"
        return "Transient"

    def _normalize_results_for_waveform_viewer(
        self,
        results: dict[str, Any],
        analysis_type: str,
    ) -> dict[str, Any]:
        """Make scalar or single-point results plottable in the waveform window."""
        if not results:
            return {}

        normalized = dict(results)
        axis = normalized.get("time")
        if axis is not None:
            return normalized

        if "frequency" in normalized and "time" not in normalized:
            normalized["time"] = normalized.pop("frequency")
            return normalized

        waveform_map: dict[str, list[float]] = {}
        point_count = 2
        for key, value in normalized.items():
            if key in {"type", "dc_op", "metadata"} or isinstance(value, str):
                continue

            values: list[float]
            if isinstance(value, dict):
                raw_values = value.get("values", [])
            elif hasattr(value, "tolist"):
                raw_values = value.tolist()
            elif isinstance(value, (list, tuple)):
                raw_values = list(value)
            else:
                raw_values = [value]

            try:
                values = [float(item) for item in raw_values]
            except (TypeError, ValueError):
                continue

            if not values:
                continue
            if len(values) == 1:
                values = [values[0], values[0]]
            point_count = max(point_count, len(values))
            waveform_map[key] = values

        if not waveform_map:
            return normalized

        for key, values in list(waveform_map.items()):
            if len(values) < point_count:
                waveform_map[key] = values + [values[-1]] * (point_count - len(values))

        prepared = {
            "type": analysis_type.lower().replace(" ", "_"),
            "time": [float(index) for index in range(point_count)],
            "dc_op": analysis_type == "Operating Point",
        }
        prepared.update(waveform_map)
        return prepared

    def _is_supported_design_library_file(self, path: Path) -> bool:
        """Return whether a path belongs in the design browser."""
        return path.is_file() and path.suffix.lower() in SUPPORTED_DESIGN_LIBRARY_SUFFIXES

    def _latest_supported_file_mtime(self, root: Path) -> float:
        """Return the newest modification time beneath a root path."""
        if not root.exists():
            return 0.0
        if root.is_file():
            return root.stat().st_mtime

        latest = 0.0
        for candidate in root.rglob("*"):
            if self._is_supported_design_library_file(candidate):
                latest = max(latest, candidate.stat().st_mtime)
        return latest

    def _find_first_openable_entry(self, entries: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
        """Return the first nested entry that has an open action."""
        for entry in entries:
            if entry.get("open_mode"):
                return entry
            nested = self._find_first_openable_entry(entry.get("children", []))
            if nested:
                return nested
        return None

    def _build_design_library_entries(self) -> list[dict[str, Any]]:
        """Build the top-level contents for the design browser."""
        entries: list[dict[str, Any]] = []

        project_entries = []
        if self._designs_root.exists():
            for project_dir in sorted(
                (path for path in self._designs_root.iterdir() if path.is_dir()),
                key=lambda path: path.name.lower(),
            ):
                project_entry = self._build_design_project_entry(project_dir)
                if project_entry:
                    project_entries.append(project_entry)

        if project_entries:
            entries.append(self._make_design_library_entry(
                "Design Projects",
                "Collection",
                path=str(self._designs_root),
                summary_lines=[
                    "Browse all checked-in design projects and open netlists, RTL, specs, and collateral from one tree.",
                    f"Projects found: {len(project_entries)}",
                ],
                children=project_entries,
            ))

        testbench_entries = self._build_testbench_library_entries()
        if testbench_entries is not None:
            entries.append(testbench_entries)

        chip_profiles_entry = self._build_chip_profile_entries()
        if chip_profiles_entry is not None:
            entries.append(chip_profiles_entry)

        generated_reports_entry = self._build_generated_report_entries()
        if generated_reports_entry is not None:
            entries.append(generated_reports_entry)

        return entries

    def _build_design_project_entry(self, project_dir: Path) -> Optional[dict[str, Any]]:
        """Build a browser entry for a design project under designs/."""
        child_entries: list[dict[str, Any]] = []
        project_name = project_dir.name

        if project_name == "lin_asic":
            top_path = project_dir / "lin_asic_top.spice"
            child_entries.append(self._make_design_library_entry(
                "Launch Full LIN ASIC Hierarchy",
                "Hierarchy Demo",
                path=str(top_path),
                open_mode="lin_asic_hierarchy",
                title="LIN ASIC Hierarchy",
                summary_lines=[
                    "Open the full LIN ASIC top-level schematic with child analog/digital tabs and hierarchy navigation.",
                    "This is the best entry point if you want to descend into block-level views.",
                ],
                recent_candidate=top_path.exists(),
                modified_at=top_path.stat().st_mtime if top_path.exists() else 0.0,
            ))
            lin_hierarchy = self._build_lin_asic_hierarchy_entry()
            if lin_hierarchy is not None:
                child_entries.append(lin_hierarchy)

        root_files = [
            self._build_file_entry(path)
            for path in sorted(project_dir.iterdir(), key=lambda path: (path.is_file(), path.name.lower()))
            if path.is_file() and self._is_supported_design_library_file(path)
        ]
        if root_files:
            child_entries.append(self._make_design_library_entry(
                "Project Files",
                "Section",
                path=str(project_dir),
                summary_lines=["Top-level files for this design project."],
                children=root_files,
            ))

        for directory in sorted(
            (path for path in project_dir.iterdir() if path.is_dir()),
            key=lambda path: path.name.lower(),
        ):
            directory_entry = self._build_directory_entry(directory)
            if directory_entry is not None:
                child_entries.append(directory_entry)

        if not child_entries:
            return None

        default_entry = self._find_first_openable_entry(child_entries)
        run_entry = self._find_default_run_entry(child_entries)
        project_file_count = sum(1 for candidate in project_dir.rglob("*") if self._is_supported_design_library_file(candidate))
        summary_lines = [
            f"Project path: {project_dir.relative_to(self._repo_root).as_posix()}",
            f"Browsable design files: {project_file_count}",
        ]
        if project_name == "lin_asic":
            summary_lines.append("Includes a ready-to-open hierarchical chip demo plus block-level source views.")

        return self._make_design_library_entry(
            self._friendly_design_label(project_name),
            "Project",
            path=str(project_dir),
            open_mode=(default_entry or {}).get("open_mode", ""),
            run_mode=(run_entry or {}).get("run_mode", ""),
            run_path=(run_entry or {}).get("run_path", ""),
            title=(default_entry or {}).get("title", self._friendly_design_label(project_name)),
            focus_alias=(default_entry or {}).get("focus_alias", ""),
            summary_lines=summary_lines,
            children=child_entries,
            recent_candidate=project_name == "lin_asic",
            modified_at=self._latest_supported_file_mtime(project_dir),
        )

    def _build_testbench_library_entries(self) -> Optional[dict[str, Any]]:
        """Build a dedicated library of runnable IP testbenches."""
        testbench_paths = sorted(
            self._designs_root.glob("**/testbench.spice"),
            key=lambda path: path.parent.as_posix().lower(),
        )
        if not testbench_paths:
            return None

        entries: list[dict[str, Any]] = []
        for testbench_path in testbench_paths:
            block_dir = testbench_path.parent
            block_name = self._friendly_design_label(block_dir.name)
            dut_path = block_dir / f"{block_dir.name}.spice"
            simulate_path = block_dir / "simulate.py"
            pin_names = self._extract_subckt_ports(dut_path) if dut_path.exists() else []

            child_entries = [self._build_file_entry(testbench_path)]
            if dut_path.exists():
                child_entries.append(self._build_file_entry(dut_path))
            if simulate_path.exists():
                child_entries.append(self._build_file_entry(simulate_path))

            summary_lines = [
                f"Testbench path: {testbench_path.relative_to(self._repo_root).as_posix()}",
                "Run Selected launches a normalized wrapper simulation for this IP and opens a waveform window.",
            ]
            pin_summary = self._format_pin_summary(pin_names)
            if pin_summary:
                summary_lines.append(f"Pins: {pin_summary}")

            entries.append(self._make_design_library_entry(
                block_name,
                "IP Testbench",
                path=str(testbench_path),
                open_mode="source",
                run_mode="block_wrapper" if dut_path.exists() else "",
                run_path=str(dut_path) if dut_path.exists() else "",
                title=f"{block_name} Testbench",
                pin_names=pin_names,
                summary_lines=summary_lines,
                children=child_entries,
                modified_at=max(path.stat().st_mtime for path in [testbench_path, dut_path] if path.exists()),
            ))

        return self._make_design_library_entry(
            "IP Testbench Library",
            "Collection",
            path=str(self._designs_root),
            summary_lines=[
                "Runnable block-level testbenches with matching DUT collateral and optional helper scripts.",
                f"Testbenches found: {len(entries)}",
            ],
            children=entries,
        )

    def _build_lin_asic_hierarchy_entry(self) -> Optional[dict[str, Any]]:
        """Build explicit block-level entries for the LIN ASIC hierarchy."""
        try:
            from simulator.api.server import _asic_design_root, _get_asic_block_catalog
        except Exception:
            return None

        design_root = _asic_design_root()
        catalog = _get_asic_block_catalog()
        block_entries: list[dict[str, Any]] = []

        for block_key, spec in sorted(
            catalog.items(),
            key=lambda item: ((item[1].get("domain") or "mixed"), item[1].get("name") or item[0]),
        ):
            child_files: list[dict[str, Any]] = []
            candidate_paths = []
            spice_path: Optional[Path] = None
            for relative_path in (spec.get("spice_file"), spec.get("rtl_file")):
                if not relative_path:
                    continue
                candidate = design_root / relative_path
                if candidate.exists():
                    if candidate.suffix.lower() in {".sp", ".spice"}:
                        spice_path = candidate
                    candidate_paths.append(candidate)
                    child_files.append(self._build_file_entry(candidate))

            pin_names = self._extract_subckt_ports(spice_path) if spice_path is not None else []
            pin_summary = self._format_pin_summary(pin_names)
            summary_lines = [
                spec.get("description") or "No description available.",
                f"Domain: {spec.get('domain', 'mixed')}",
                f"Primary open action: focuses the hierarchy tab for {spec.get('name') or block_key}.",
            ]
            if pin_summary:
                summary_lines.append(f"Pins: {pin_summary}")

            block_entries.append(self._make_design_library_entry(
                spec.get("name") or self._friendly_design_label(block_key),
                f"{(spec.get('domain') or 'mixed').title()} Block",
                path=str(candidate_paths[0]) if candidate_paths else str(design_root),
                open_mode="lin_asic_focus",
                title=f"LIN ASIC — {spec.get('name') or block_key}",
                focus_alias=block_key,
                pin_names=pin_names,
                summary_lines=summary_lines,
                children=child_files,
                modified_at=max((path.stat().st_mtime for path in candidate_paths), default=0.0),
            ))

        return self._make_design_library_entry(
            "LIN ASIC Block Hierarchy",
            "Hierarchy",
            path=str(design_root),
            summary_lines=[
                "Open any LIN ASIC block directly from this section.",
                "Digital block entries also open their RTL source window when available.",
            ],
            children=block_entries,
        ) if block_entries else None

    def _build_chip_profile_entries(self) -> Optional[dict[str, Any]]:
        """Build entries for the newest generated chip-profile collateral."""
        reference_files = sorted(
            self._reports_root.glob("cycle_*_reference_implementation.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        reference_payload = self._read_json_file_safe(reference_files[0]) if reference_files else None
        if not reference_payload:
            return None

        catalog_payload = self._read_json_file_safe(self._reports_root / "chip_catalog_latest.json") or {}
        profile_map = {
            entry.get("key", ""): entry
            for entry in catalog_payload.get("chip_profiles", [])
            if isinstance(entry, dict) and entry.get("key")
        }

        children: list[dict[str, Any]] = []
        for profile_key, result in (reference_payload.get("profiles") or {}).items():
            if not isinstance(result, dict):
                continue

            profile_data = profile_map.get(profile_key, {})
            html_path = self._reports_root / f"{profile_key}_design_reference.html"
            summary_lines = [
                profile_data.get("summary") or f"Reference implementation status: {result.get('status', 'unknown')}",
                (
                    f"Status: {result.get('status', 'unknown')}  |  blocks={result.get('blocks_count', 0)}  "
                    f"VIPs={result.get('vips_count', 0)}  subsystems={result.get('subsystems_count', 0)}"
                ),
            ]
            tech_support = profile_data.get("technology_support") or result.get("technology_support") or []
            if tech_support:
                summary_lines.append(f"Technology support: {', '.join(tech_support)}")
            if profile_data.get("headline"):
                summary_lines.append(profile_data["headline"])
            collateral = profile_data.get("design_collateral") or []
            if collateral:
                summary_lines.append(f"Collateral highlights: {', '.join(collateral[:3])}")

            child_entries: list[dict[str, Any]] = []
            if html_path.exists():
                child_entries.append(self._build_file_entry(html_path))

            children.append(self._make_design_library_entry(
                profile_data.get("name") or self._friendly_design_label(profile_key),
                "Chip Profile",
                path=str(html_path if html_path.exists() else reference_files[0]),
                open_mode="source" if html_path.exists() else "",
                title=f"Chip Profile — {profile_data.get('name') or self._friendly_design_label(profile_key)}",
                summary_lines=summary_lines,
                children=child_entries,
                recent_candidate=html_path.exists(),
                modified_at=html_path.stat().st_mtime if html_path.exists() else reference_files[0].stat().st_mtime,
            ))

        return self._make_design_library_entry(
            "Recent Chip Profiles",
            "Collection",
            path=str(self._reports_root),
            summary_lines=[
                "Generated reference collateral for the newest chip-profile work.",
                f"Profiles listed: {len(children)}",
            ],
            children=children,
        ) if children else None

    def _build_generated_report_entries(self) -> Optional[dict[str, Any]]:
        """Build entries for generated design references and reports."""
        report_files: list[Path] = []
        patterns = [
            "*_design_reference.html",
            "*_regression_latest.json",
            "*_regression_latest.md",
            "chip_catalog*.json",
            "chip_catalog*.md",
            "design_portfolio_overview.json",
            "design_portfolio_overview.md",
        ]
        for pattern in patterns:
            report_files.extend(self._reports_root.glob(pattern))

        unique_files = sorted({path for path in report_files if path.exists()}, key=lambda path: path.name.lower())
        if not unique_files:
            return None

        return self._make_design_library_entry(
            "Generated Design Reports",
            "Collection",
            path=str(self._reports_root),
            summary_lines=[
                "Rendered design references, regression summaries, and chip catalog snapshots.",
                f"Files listed: {len(unique_files)}",
            ],
            children=[self._build_file_entry(path) for path in unique_files],
        )

    def _build_directory_entry(self, directory: Path) -> Optional[dict[str, Any]]:
        """Recursively build a tree entry for a design directory."""
        if directory.name.startswith("."):
            return None

        children: list[dict[str, Any]] = []
        for child in sorted(directory.iterdir(), key=lambda path: (path.is_file(), path.name.lower())):
            if child.is_dir():
                nested = self._build_directory_entry(child)
                if nested is not None:
                    children.append(nested)
            elif self._is_supported_design_library_file(child):
                children.append(self._build_file_entry(child))

        if not children:
            return None

        default_entry = self._find_first_openable_entry(children)
        run_entry = self._find_default_run_entry(children)
        return self._make_design_library_entry(
            self._friendly_design_label(directory.name),
            "Folder",
            path=str(directory),
            open_mode=(default_entry or {}).get("open_mode", ""),
            run_mode=(run_entry or {}).get("run_mode", ""),
            run_path=(run_entry or {}).get("run_path", ""),
            title=(default_entry or {}).get("title", self._friendly_design_label(directory.name)),
            focus_alias=(default_entry or {}).get("focus_alias", ""),
            summary_lines=[
                f"Folder: {directory.relative_to(self._repo_root).as_posix()}",
                f"Browsable children: {len(children)}",
            ],
            children=children,
            modified_at=self._latest_supported_file_mtime(directory),
        )

    def _build_file_entry(self, file_path: Path) -> dict[str, Any]:
        """Build a leaf entry for one browsable design file."""
        suffix = file_path.suffix.lower()
        relative_path = file_path.relative_to(self._repo_root).as_posix()
        open_mode = "source"
        kind = "Source"
        run_mode = ""
        run_path = ""
        pin_names: list[str] = []

        if suffix in {".sp", ".spice"} and file_path.name != "testbench.spice":
            pin_names = self._extract_subckt_ports(file_path)

        if file_path.name == "lin_asic_top.spice":
            open_mode = "lin_asic_hierarchy"
            kind = "Hierarchy Schematic"
        elif file_path.name == "testbench.spice":
            kind = "Testbench"
            dut_path = file_path.parent / f"{file_path.parent.name}.spice"
            if dut_path.exists():
                run_mode = "block_wrapper"
                run_path = str(dut_path)
            else:
                run_mode = "spice_file"
                run_path = str(file_path)
        elif suffix in {".sp", ".spice"}:
            open_mode = "schematic"
            kind = "Schematic"
            sibling_testbench = file_path.parent / "testbench.spice"
            if sibling_testbench.exists() and file_path.parent.name == file_path.stem:
                run_mode = "block_wrapper"
                run_path = str(file_path)
            elif self._netlist_has_analysis(self._read_text_file(file_path)):
                run_mode = "spice_file"
                run_path = str(file_path)
            else:
                testbench_path = file_path.parent / "testbench.spice"
                if testbench_path.exists() and file_path.parent.name == file_path.stem:
                    run_mode = "block_wrapper"
                    run_path = str(file_path)
        elif suffix in {".v", ".sv"}:
            kind = "RTL Source"
        elif suffix in {".md", ".txt"}:
            kind = "Document"
        elif suffix in {".json", ".yaml", ".yml"}:
            kind = "Manifest"
        elif suffix == ".html":
            kind = "Rendered View"

        summary_lines = [
            f"Path: {relative_path}",
            f"Size: {file_path.stat().st_size} bytes",
        ]
        pin_summary = self._format_pin_summary(pin_names)
        if pin_summary:
            summary_lines.append(f"Pins: {pin_summary}")
        if run_path:
            summary_lines.append(f"Run action: {Path(run_path).name}")

        return self._make_design_library_entry(
            file_path.name,
            kind,
            path=str(file_path),
            open_mode=open_mode,
            run_mode=run_mode,
            run_path=run_path,
            title=file_path.name if suffix in {".sp", ".spice"} else relative_path,
            pin_names=pin_names,
            summary_lines=summary_lines,
            modified_at=file_path.stat().st_mtime,
        )

    def _refresh_design_library_browser(self) -> None:
        """Re-scan the repo-backed design browser and refresh the tree."""
        self.design_library_tree.clear()
        self._design_library_recent_entry = None

        for entry in self._build_design_library_entries():
            self._add_design_library_tree_item(None, entry)

        self.design_library_tree.expandToDepth(1)
        self._apply_design_library_filter(self.design_library_filter.text())

        recent_entry = self._design_library_recent_entry
        if recent_entry is not None:
            self.design_library_tree.setCurrentItem(recent_entry["item"])

    def _add_design_library_tree_item(
        self,
        parent: Optional[QTreeWidgetItem],
        entry: dict[str, Any],
    ) -> QTreeWidgetItem:
        """Append one design-library entry to the tree and recurse into children."""
        item = QTreeWidgetItem([entry.get("label", "Item"), entry.get("kind", "")])
        item.setData(0, Qt.ItemDataRole.UserRole, entry)
        tooltip = entry.get("path") or entry.get("label", "")
        item.setToolTip(0, tooltip)
        item.setToolTip(1, entry.get("kind", ""))

        if parent is None:
            self.design_library_tree.addTopLevelItem(item)
        else:
            parent.addChild(item)

        if entry.get("recent_candidate"):
            current = self._design_library_recent_entry
            if current is None or entry.get("modified_at", 0.0) >= current["entry"].get("modified_at", 0.0):
                self._design_library_recent_entry = {"item": item, "entry": entry}

        for child in entry.get("children", []):
            self._add_design_library_tree_item(item, child)

        return item

    def _entry_search_text(self, entry: dict[str, Any]) -> str:
        """Flatten an entry into searchable text for tree filtering."""
        fields = [
            entry.get("label", ""),
            entry.get("kind", ""),
            entry.get("path", ""),
            " ".join(entry.get("summary_lines", [])),
        ]
        return " ".join(fields).lower()

    def _filter_design_library_item(self, item: QTreeWidgetItem, query: str) -> bool:
        """Recursively filter one tree item and return whether it should stay visible."""
        entry = item.data(0, Qt.ItemDataRole.UserRole) or {}
        matches = not query or query in self._entry_search_text(entry)
        child_matches = False

        for index in range(item.childCount()):
            child_matches = self._filter_design_library_item(item.child(index), query) or child_matches

        visible = matches or child_matches
        item.setHidden(not visible)
        if child_matches and query:
            item.setExpanded(True)
        return visible

    def _apply_design_library_filter(self, text: str) -> None:
        """Apply a case-insensitive filter to the design library tree."""
        query = (text or "").strip().lower()
        for index in range(self.design_library_tree.topLevelItemCount()):
            self._filter_design_library_item(self.design_library_tree.topLevelItem(index), query)

    def _read_entry_preview_text(self, entry: dict[str, Any]) -> str:
        """Build a preview payload for the selected design entry."""
        lines = [entry.get("label", "Item"), f"Type: {entry.get('kind', 'Unknown')}"]
        if entry.get("path"):
            path = Path(entry["path"])
            lines.append(f"Path: {path}")
        else:
            path = None

        summary_lines = entry.get("summary_lines", [])
        if summary_lines:
            lines.extend(["", *summary_lines])

        if path is not None and path.exists() and path.is_file():
            try:
                preview = self._read_text_file(path)
                preview_lines = preview.splitlines()
                if preview_lines:
                    lines.extend(["", *preview_lines[:80]])
            except Exception as exc:
                lines.extend(["", f"Preview unavailable: {exc}"])

        pin_names = entry.get("pin_names", [])
        if pin_names:
            lines.extend(["", f"Pins: {', '.join(pin_names)}"])

        if entry.get("open_mode"):
            lines.extend(["", f"Double-click or press Open Selected to: {entry['open_mode']}"])
        if entry.get("run_mode"):
            run_target = entry.get("run_path") or entry.get("path") or "selected design"
            lines.append(f"Run + Waveforms executes: {run_target}")

        return "\n".join(lines)

    def _on_design_library_item_selected(
        self,
        current: Optional[QTreeWidgetItem],
        _previous: Optional[QTreeWidgetItem],
    ) -> None:
        """Update the preview pane when the design browser selection changes."""
        if current is None:
            self.design_library_preview.clear()
            return

        entry = current.data(0, Qt.ItemDataRole.UserRole) or {}
        self.design_library_preview.setPlainText(self._read_entry_preview_text(entry))

    def _on_design_library_item_activated(self, item: QTreeWidgetItem, _column: int) -> None:
        """Open or expand the selected design browser item on double-click."""
        entry = item.data(0, Qt.ItemDataRole.UserRole) or {}
        if entry.get("open_mode"):
            self._open_design_library_entry(entry)
            return

        item.setExpanded(not item.isExpanded())

    def _show_design_library_browser(self) -> None:
        """Refresh and reveal the design library browser dock."""
        self._refresh_design_library_browser()
        self.design_library_dock.show()
        self.design_library_dock.raise_()
        self.design_library_dock.activateWindow()

    def _expand_design_library_parents(self, item: QTreeWidgetItem) -> None:
        """Expand all ancestors for a selected design-library item."""
        parent = item.parent()
        while parent is not None:
            parent.setExpanded(True)
            parent = parent.parent()

    def _launch_recent_chip_design(self) -> None:
        """Open the newest chip-related browser entry and bring the dock forward."""
        self._show_design_library_browser()
        recent_entry = self._design_library_recent_entry
        if recent_entry is None:
            self.statusbar.showMessage("No recent chip entry is available in the design browser")
            return

        item = recent_entry["item"]
        self._expand_design_library_parents(item)
        self.design_library_tree.setCurrentItem(item)
        self._open_design_library_entry(recent_entry["entry"])

    def _open_selected_design_library_item(self) -> None:
        """Open the currently selected item from the design library tree."""
        item = self.design_library_tree.currentItem()
        if item is None:
            self.statusbar.showMessage("Select a design, block, or file from the browser first")
            return

        entry = item.data(0, Qt.ItemDataRole.UserRole) or {}
        self._open_design_library_entry(entry)

    def _run_selected_design_library_item(self) -> None:
        """Simulate the currently selected browser entry when it has a run action."""
        item = self.design_library_tree.currentItem()
        if item is None:
            self.statusbar.showMessage("Select a runnable design or testbench from the browser first")
            return

        entry = item.data(0, Qt.ItemDataRole.UserRole) or {}
        self._run_design_library_entry(entry)

    def _run_design_library_entry(self, entry: dict[str, Any]) -> None:
        """Run the selected browser entry and show waveforms when possible."""
        run_mode = entry.get("run_mode", "")
        if not run_mode:
            self.statusbar.showMessage("Select a testbench or design entry with a run action")
            return

        path_text = entry.get("run_path") or entry.get("path", "")
        if not path_text:
            self.statusbar.showMessage("This browser item is missing a runnable file path")
            return

        run_path = Path(path_text)
        if not run_path.exists():
            self.statusbar.showMessage(f"Missing run target: {run_path}")
            return

        if run_mode == "spice_file":
            self._run_spice_file_simulation(run_path, entry.get("title") or entry.get("label") or run_path.stem)
            return

        if run_mode == "block_wrapper":
            self._run_block_wrapper_simulation(run_path, entry.get("title") or entry.get("label") or run_path.stem)
            return

        self.statusbar.showMessage(f"Unsupported browser run action: {run_mode}")

    def _open_design_library_entry(self, entry: dict[str, Any]) -> None:
        """Open one browser entry using the correct helper for its type."""
        open_mode = entry.get("open_mode", "")
        if not open_mode:
            self.statusbar.showMessage("Open a specific file or hierarchy view from this section")
            return

        if open_mode == "lin_asic_hierarchy":
            self._load_lin_asic_hierarchy(entry.get("focus_alias") or None)
            return

        if open_mode == "lin_asic_focus":
            self._load_lin_asic_hierarchy(entry.get("focus_alias") or None)
            return

        path_text = entry.get("path", "")
        if not path_text:
            self.statusbar.showMessage("This browser item is missing a file path")
            return

        path = Path(path_text)
        if not path.exists():
            self.statusbar.showMessage(f"Missing design file: {path}")
            return

        if open_mode == "schematic":
            self._open_netlist_file(path, entry.get("title") or self._friendly_design_label(path.stem))
            return

        if open_mode == "source":
            self._open_source_file(path, entry.get("title") or path.name)
            return

        self.statusbar.showMessage(f"Unsupported browser action: {open_mode}")

    def _open_source_file(self, path: Path, title: str) -> None:
        """Open one text-like design file in the standalone source window."""
        self._show_source_window(
            title,
            self._read_text_file(path),
            str(path),
        )
        self.statusbar.showMessage(f"Opened source view: {path.name}")

    def _open_netlist_file(self, path: Path, tab_name: str) -> None:
        """Open a SPICE netlist file in a new schematic tab and netlist viewer."""
        netlist = self._read_text_file(path)
        self.netlist_viewer.set_netlist(netlist)

        editor = SchematicEditor()
        index = self.schematic_tabs.addTab(editor, tab_name)
        self.schematic_tabs.setCurrentIndex(index)
        self.schematic_editor = editor
        self._connect_editor_signals(editor)
        editor.load_from_netlist(netlist)
        self.statusbar.showMessage(f"Opened schematic view: {path.name}")

    def _run_spice_file_simulation(self, path: Path, title: str) -> None:
        """Run a SPICE file from disk and open the waveform window."""
        try:
            from simulator.engine.ngspice_backend import NgSpiceBackend

            source_netlist = self._read_text_file(path)
            expanded_netlist = self._read_spice_file_with_includes(path)
            analysis_type = self._detect_netlist_analysis_type(expanded_netlist)
            backend = NgSpiceBackend()

            if backend.is_available():
                self.statusbar.showMessage(f"{title}: Running {analysis_type} with NgSpice...")
                QApplication.processEvents()
                results = backend.simulate(expanded_netlist)
                prepared_results = self._normalize_results_for_waveform_viewer(results, analysis_type)
                if not prepared_results or len(prepared_results) <= 1:
                    raise RuntimeError("Simulation completed but produced no plottable signals")
                self._show_waveform_viewer(prepared_results, title=f"{title} — {analysis_type}")
                self.statusbar.showMessage(f"{title}: {analysis_type} analysis complete")
                return

            if ".include" in source_netlist.lower() or re.search(r"(?mi)^\s*x\w+", expanded_netlist):
                raise RuntimeError(
                    "NgSpice is required to run this testbench because it uses includes or hierarchical subcircuits."
                )

            self._run_netlist_simulation(expanded_netlist, title)
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Simulation Error",
                f"Failed to run simulation for {path.name}:\n{exc}",
            )
            self.statusbar.showMessage(f"Simulation error: {exc}")

    def _run_block_wrapper_simulation(self, dut_path: Path, title: str) -> None:
        """Run a browser-selected IP using a generated wrapper around the DUT body."""
        try:
            wrapper_netlist = self._build_block_wrapper_netlist(dut_path)
            self._run_netlist_simulation(wrapper_netlist, title)
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Simulation Error",
                f"Failed to run wrapper simulation for {dut_path.name}:\n{exc}",
            )
            self.statusbar.showMessage(f"Simulation error: {exc}")

    def _load_lin_asic_hierarchy(self, focus_alias: Optional[str] = None) -> None:
        """Load or refocus the LIN ASIC hierarchy demo from the design browser."""
        try:
            from simulator.api.server import _asic_design_root, _get_asic_block_catalog, _read_asic_design_file
        except Exception as exc:
            QMessageBox.critical(self, "LIN ASIC Loader", f"Failed to import ASIC loader helpers:\n{exc}")
            return

        top_spec = self._find_hierarchy_spec("lin_asic", "top_level")
        if top_spec is None:
            design_root = _asic_design_root()
            catalog = _get_asic_block_catalog()

            top_file = design_root / "lin_asic_top.spice"
            loaded_tabs = [{
                "tab_name": "★ LIN ASIC — Top Level",
                "netlist": self._read_text_file(top_file) if top_file.exists() else "",
                "hierarchical": True,
                "block_key": None,
                "parent_tab_name": None,
                "block_aliases": ["lin_asic", "top_level"],
                "domain": None,
                "rtl_file": None,
                "spice_file": "lin_asic_top.spice",
                "display_name": "LIN ASIC Top Level",
            }]

            for block_key, spec in catalog.items():
                netlist = _read_asic_design_file(spec.get("spice_file"))
                if not netlist and spec.get("rtl_file"):
                    netlist = _read_asic_design_file(spec.get("rtl_file"))
                domain_tag = "DIG" if spec.get("domain") == "digital" else "ANA"
                if spec.get("domain") == "mixed":
                    domain_tag = "MS"
                loaded_tabs.append({
                    "tab_name": f"[{domain_tag}:{spec['icon']}] {spec['name']}",
                    "netlist": netlist,
                    "hierarchical": False,
                    "block_key": block_key,
                    "parent_tab_name": "★ LIN ASIC — Top Level",
                    "block_aliases": [spec["name"]],
                    "domain": spec.get("domain"),
                    "rtl_file": spec.get("rtl_file"),
                    "spice_file": spec.get("spice_file"),
                    "display_name": spec.get("name"),
                })

            for entry in loaded_tabs:
                self.load_block_tab(
                    entry["tab_name"],
                    entry["netlist"],
                    hierarchical=entry["hierarchical"],
                    block_key=entry.get("block_key"),
                    parent_tab_name=entry.get("parent_tab_name"),
                    block_aliases=entry.get("block_aliases"),
                    domain=entry.get("domain"),
                    rtl_file=entry.get("rtl_file"),
                    spice_file=entry.get("spice_file"),
                    display_name=entry.get("display_name"),
                )

        target_spec = self._find_hierarchy_spec(focus_alias or "lin_asic", focus_alias or "top_level")
        if target_spec is None:
            self.statusbar.showMessage(
                f"LIN ASIC hierarchy is loaded, but no specific view matched '{focus_alias or 'top level'}'"
            )
            self.present_asic_demo_ui()
            return

        target_index = self._ensure_hierarchy_tab_open(target_spec)
        if target_index >= 0:
            self.schematic_tabs.setCurrentIndex(target_index)
            if target_spec.get("domain") == "digital":
                self._open_digital_block_source(target_spec)
            self.statusbar.showMessage(
                f"Opened LIN ASIC view: {target_spec.get('display_name') or target_spec.get('tab_name')}")

        self.present_asic_demo_ui()

    def _refresh_api_session_monitor(self):
        """Refresh the session GUID + schematic handshake summary."""
        current_tab = "No tab"
        component_count = 0
        wire_count = 0
        tab_count = self.schematic_tabs.count()

        try:
            current_index = self.schematic_tabs.currentIndex()
            if current_index >= 0:
                current_tab = self.schematic_tabs.tabText(current_index)
            if self.schematic_editor is not None:
                component_count = len(self.schematic_editor._components)
                wire_count = len(self.schematic_editor._wires)
        except Exception:
            pass

        self.api_session_label.setText(
            f"Session GUID: {self.api_session_guid}    API: {self.api_base_url}"
        )
        self.api_handshake_label.setText(
            "Handshake: "
            f"tab='{current_tab}'  |  components={component_count}  |  "
            f"wires={wire_count}  |  open_tabs={tab_count}"
        )

    def set_api_session_info(self, session_guid: str, api_base: str) -> None:
        """Called by the API server when a session is started or restarted."""
        self.api_session_guid = session_guid
        self.api_base_url = api_base
        self._refresh_api_session_monitor()
        self.api_session_dock.show()

    def run_on_gui(self, func) -> None:
        """Queue arbitrary callable work onto the Qt GUI thread."""
        self.gui_call_requested.emit(func)

    def _execute_gui_call(self, func) -> None:
        """Execute a callable that was queued from a worker thread."""
        try:
            func()
        except Exception as exc:
            if hasattr(self, "statusbar"):
                self.statusbar.showMessage(f"GUI dispatch failed: {exc}")

    def append_api_session_event(self, entry: dict) -> None:
        """Append a single API call entry to the visible monitor dock."""
        gui_state = entry.get("gui_state", {})
        body = entry.get("request_body", "")
        response = entry.get("response_summary", "")
        line = (
            f"[{entry.get('timestamp_iso', '?')}] "
            f"#{entry.get('request_id', '?')} "
            f"{entry.get('method', '?')} {entry.get('path', '?')} -> "
            f"{entry.get('status', '?')}  |  "
            f"tab={gui_state.get('current_tab', '?')}  "
            f"components={gui_state.get('component_count', '?')}  "
            f"wires={gui_state.get('wire_count', '?')}"
        )
        if body:
            line += f"  |  body={body}"
        if response:
            line += f"  |  response={response}"

        self.api_session_log.insertPlainText(line + "\n")
        self.api_session_log.verticalScrollBar().setValue(
            self.api_session_log.verticalScrollBar().maximum()
        )
        self._refresh_api_session_monitor()
        self.api_session_dock.show()

    def present_asic_demo_ui(self) -> None:
        """Make the ASIC demo UI visible and focused in the current session."""
        self.showNormal()
        self.show()
        self.raise_()
        self.activateWindow()
        self.api_session_dock.show()
        self.api_session_dock.raise_()
        self._refresh_api_session_monitor()
        QApplication.processEvents()

    def _on_schematic_tab_changed(self, index: int):
        """Track the active tab so API handshakes reflect the real schematic."""
        editor = self.schematic_tabs.widget(index)
        if isinstance(editor, SchematicEditor):
            self.schematic_editor = editor
            self._refresh_api_session_monitor()

    @staticmethod
    def _normalize_hierarchy_key(value: str) -> str:
        """Normalize hierarchy aliases so netlist names and tab labels match."""
        return "".join(ch for ch in (value or "").lower() if ch.isalnum())

    def _extract_hierarchy_aliases(
        self,
        tab_name: str,
        netlist: str,
        block_key: Optional[str] = None,
        block_aliases: Optional[list[str]] = None,
    ) -> set[str]:
        """Build a set of normalized aliases for a hierarchy tab."""
        aliases: set[str] = set(block_aliases or [])
        if block_key:
            aliases.add(block_key)
        aliases.add(tab_name)
        if "] " in tab_name:
            aliases.add(tab_name.split("] ", 1)[1])

        for line in netlist.splitlines():
            stripped = line.strip()
            if stripped.upper().startswith(".SUBCKT "):
                parts = stripped.split()
                if len(parts) >= 2:
                    aliases.add(parts[1])

        normalized_aliases: set[str] = set()
        for alias in aliases:
            normalized = self._normalize_hierarchy_key(alias)
            if normalized:
                normalized_aliases.add(normalized)
        return normalized_aliases

    def _register_hierarchy_tab_spec(
        self,
        tab_name: str,
        netlist: str,
        hierarchical: bool = False,
        block_key: Optional[str] = None,
        parent_tab_name: Optional[str] = None,
        block_aliases: Optional[list[str]] = None,
        domain: Optional[str] = None,
        rtl_file: Optional[str] = None,
        spice_file: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> dict:
        """Cache enough information to reopen and navigate hierarchy tabs."""
        resolved_parent = parent_tab_name
        if not hierarchical and not resolved_parent:
            resolved_parent = self._hierarchy_top_level_tab_name

        alias_sources = list(block_aliases or [])
        if block_key:
            alias_sources.append(block_key)

        spec = {
            "tab_name": tab_name,
            "netlist": netlist,
            "hierarchical": hierarchical,
            "block_key": block_key,
            "parent_tab_name": resolved_parent,
            "block_aliases": alias_sources,
            "domain": domain,
            "rtl_file": rtl_file,
            "spice_file": spice_file,
            "display_name": display_name or (tab_name.split("] ", 1)[1] if "] " in tab_name else tab_name),
            "aliases": self._extract_hierarchy_aliases(
                tab_name,
                netlist,
                block_key=block_key,
                block_aliases=block_aliases,
            ),
        }

        if hierarchical and resolved_parent is None:
            self._hierarchy_top_level_tab_name = tab_name
            self._hierarchy_top_level_spec = spec

        for alias in spec["aliases"]:
            self._hierarchy_tab_specs[alias] = spec

        return spec

    def _iter_hierarchy_specs(self):
        """Yield unique cached hierarchy tab specifications."""
        seen_tab_names: set[str] = set()
        if self._hierarchy_top_level_spec:
            seen_tab_names.add(self._hierarchy_top_level_spec["tab_name"])
            yield self._hierarchy_top_level_spec

        for spec in self._hierarchy_tab_specs.values():
            tab_name = spec["tab_name"]
            if tab_name in seen_tab_names:
                continue
            seen_tab_names.add(tab_name)
            yield spec

    def _find_schematic_tab_index(self, tab_name: str) -> int:
        """Return the tab index for a schematic tab label, or -1."""
        for index in range(self.schematic_tabs.count()):
            if self.schematic_tabs.tabText(index) == tab_name:
                return index
        return -1

    def _find_hierarchy_spec(self, *aliases: str) -> Optional[dict]:
        """Find a cached hierarchy tab spec by any block alias."""
        for alias in aliases:
            normalized = self._normalize_hierarchy_key(alias)
            if normalized and normalized in self._hierarchy_tab_specs:
                return self._hierarchy_tab_specs[normalized]
        return None

    def _ensure_hierarchy_tab_open(self, spec: dict) -> int:
        """Open a cached hierarchy tab if it was closed, then return its index."""
        index = self._find_schematic_tab_index(spec["tab_name"])
        if index >= 0:
            return index

        self.load_block_tab(
            spec["tab_name"],
            spec["netlist"],
            hierarchical=spec.get("hierarchical", False),
            block_key=spec.get("block_key"),
            parent_tab_name=spec.get("parent_tab_name"),
            block_aliases=spec.get("block_aliases"),
            domain=spec.get("domain"),
            rtl_file=spec.get("rtl_file"),
            spice_file=spec.get("spice_file"),
            display_name=spec.get("display_name"),
        )
        return self._find_schematic_tab_index(spec["tab_name"])

    @staticmethod
    def _read_text_file(path: Path) -> str:
        """Read a text file using the same Windows-friendly fallback policy as design loading."""
        for encoding in ("utf-8", "cp1252", "latin-1"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        return path.read_text(errors="replace")

    @staticmethod
    def _resolve_asic_design_path(relative_path: str) -> Path:
        """Resolve a path relative to designs/lin_asic."""
        return Path(__file__).parent.parent.parent / "designs" / "lin_asic" / relative_path

    def _open_digital_block_source(self, spec: dict) -> bool:
        """Show the mapped RTL source for a digital block in a standalone source window."""
        display_name = spec.get("display_name") or spec.get("tab_name") or "Digital Block"

        candidates: list[tuple[str, Optional[str]]] = [
            ("RTL source", spec.get("rtl_file")),
            ("block wrapper", spec.get("spice_file")),
        ]

        for label, relative_path in candidates:
            if not relative_path:
                continue

            source_path = self._resolve_asic_design_path(relative_path)
            if not source_path.exists():
                continue

            self._show_source_window(
                f"RTL Source — {display_name}",
                self._read_text_file(source_path),
                str(source_path),
            )

            if label == "RTL source":
                self.statusbar.showMessage(
                    f"Opened RTL source for {display_name}: {source_path.name}"
                )
            else:
                self.statusbar.showMessage(
                    f"No standalone RTL file for {display_name}; showing {source_path.name}"
                )
            return True

        self.statusbar.showMessage(f"No RTL source file is available for {display_name}")
        return False

    def _descend_into_hierarchy_block(self, source_editor: SchematicEditor, component) -> None:
        """Switch from a symbolic hierarchy block into its cached child tab."""
        model_name = getattr(component, "model_name", "")
        block_name = getattr(component, "display_name", "Block")
        instance_name = getattr(component, "instance_name", "")
        spec = self._find_hierarchy_spec(model_name, block_name, instance_name)
        if spec is None:
            self.statusbar.showMessage(f"No child schematic is available for {block_name}")
            return

        current_index = self.schematic_tabs.indexOf(source_editor)
        current_tab_name = self.schematic_tabs.tabText(current_index) if current_index >= 0 else ""
        if spec["tab_name"] == current_tab_name:
            if spec.get("domain") == "digital":
                self._open_digital_block_source(spec)
                return
            self.statusbar.showMessage(f"Already at the deepest available view for {block_name}")
            return

        target_index = self._ensure_hierarchy_tab_open(spec)
        if target_index < 0:
            self.statusbar.showMessage(f"Failed to open the child schematic for {block_name}")
            return

        self.schematic_tabs.setCurrentIndex(target_index)
        if spec.get("domain") == "digital":
            self._open_digital_block_source(spec)
            return
        self.statusbar.showMessage(f"Descended into {block_name}")

    def _ascend_hierarchy(self, source_editor: SchematicEditor) -> None:
        """Return from a child hierarchy tab to its parent or top-level tab."""
        target_tab_name = getattr(source_editor, "_navigation_parent_tab_name", None)
        if not target_tab_name:
            self.statusbar.showMessage("Already at the top-level schematic")
            return

        target_index = self._find_schematic_tab_index(target_tab_name)
        if target_index < 0:
            target_spec: Optional[dict] = None
            for spec in self._iter_hierarchy_specs():
                if spec["tab_name"] == target_tab_name:
                    target_spec = spec
                    break
            if target_spec is not None:
                target_index = self._ensure_hierarchy_tab_open(target_spec)

        if target_index < 0:
            self.statusbar.showMessage(f"Parent schematic '{target_tab_name}' is not available")
            return

        self.schematic_tabs.setCurrentIndex(target_index)
        self.statusbar.showMessage(f"Returned to {target_tab_name}")

    def _remove_waveform_window(self, window) -> None:
        """Drop a closed standalone waveform window from the keepalive list."""
        try:
            self._waveform_windows.remove(window)
        except ValueError:
            pass

    def _remove_source_window(self, key: str) -> None:
        """Drop a closed standalone source window from the registry."""
        self._source_windows.pop(key, None)
        if self._last_source_window_key == key:
            self._last_source_window_key = None

    def _clear_latest_waveform_window(self) -> None:
        """Clear the reusable waveform window reference after it is closed."""
        self._latest_waveform_window = None

    def _get_latest_waveform_window(self) -> WaveformWindow:
        """Return the reusable standalone waveform window for local simulations."""
        if self._latest_waveform_window is None:
            win = WaveformWindow("Latest Simulation")
            win.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
            win.move(self.x() + 80, self.y() + 80)
            win.destroyed.connect(lambda _obj=None: self._clear_latest_waveform_window())
            self._latest_waveform_window = win
        return self._latest_waveform_window

    @staticmethod
    def _language_from_source_path(file_path: str) -> str:
        """Infer a source-viewer language from the file extension."""
        suffix = Path(file_path).suffix.lower()
        if suffix in {".v", ".sv"}:
            return "systemverilog"
        if suffix in {".sp", ".spice"}:
            return "spice"
        if suffix == ".md":
            return "markdown"
        return "text"

    def _show_source_window(
        self,
        title: str,
        text: str,
        file_path: str,
        language: Optional[str] = None,
    ) -> None:
        """Open or reuse a standalone source window for RTL, SPICE, or docs."""
        key = file_path or title
        window = self._source_windows.get(key)
        if window is None:
            window = SourceCodeWindow(title)
            window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
            offset = 28 * (len(self._source_windows) % 6)
            window.move(self.x() + 90 + offset, self.y() + 90 + offset)
            window.destroyed.connect(lambda _obj=None, source_key=key: self._remove_source_window(source_key))
            self._source_windows[key] = window

        window.set_source(
            title,
            text,
            file_path,
            language or self._language_from_source_path(file_path),
        )
        self._last_source_window_key = key
        window.showNormal()
        window.show()
        window.raise_()
        window.activateWindow()

    def _show_latest_source_window(self) -> None:
        """Bring the last opened standalone source window to the foreground."""
        if not self._last_source_window_key:
            self.statusbar.showMessage("No source window has been opened yet")
            return

        window = self._source_windows.get(self._last_source_window_key)
        if window is None:
            self.statusbar.showMessage("The last source window is no longer open")
            return

        window.showNormal()
        window.show()
        window.raise_()
        window.activateWindow()

    def close_source_window(self, file_path: Optional[str] = None) -> bool:
        """Close a standalone source window by file path or the most recent one."""
        key = file_path or self._last_source_window_key
        if not key:
            return False

        window = self._source_windows.get(key)
        if window is None:
            return False

        window.close()
        return True

    def close_test_tracker_window(self) -> bool:
        """Close the standalone ASIC regression tracker window."""
        if self._test_tracker_window is None:
            return False
        self._test_tracker_window.close()
        return True

    def hide_api_session_monitor(self) -> None:
        """Hide the API session monitor dock."""
        self.api_session_dock.hide()

    def _open_asic_architecture_overview(self) -> None:
        """Open the ASIC architecture document in a standalone source window."""
        if not self._asic_architecture_path.exists():
            self.statusbar.showMessage("ASIC architecture document is missing")
            return

        self._show_source_window(
            "ASIC Architecture",
            self._read_text_file(self._asic_architecture_path),
            str(self._asic_architecture_path),
            language="markdown",
        )

    def _open_asic_regression_log(self) -> None:
        """Open the ASIC regression log in a standalone source window."""
        if self._asic_regression_log_path.exists():
            text = self._read_text_file(self._asic_regression_log_path)
            file_path = str(self._asic_regression_log_path)
        else:
            text = self.terminal_widget.get_output_text() or "No regression log has been generated yet."
            file_path = str(self._asic_regression_log_path)

        self._show_source_window(
            "ASIC Regression Log",
            text,
            file_path,
            language="text",
        )

    def get_gui_window_status(self) -> dict:
        """Return a summary of currently open GUI windows for API polling."""
        source_windows = []
        for key, window in self._source_windows.items():
            source_windows.append({
                "key": key,
                "title": window.windowTitle(),
                "file_path": window.file_path or key,
                "visible": window.isVisible(),
            })

        return {
            "test_tracker_visible": bool(self._test_tracker_window and self._test_tracker_window.isVisible()),
            "api_monitor_visible": self.api_session_dock.isVisible(),
            "design_library_visible": self.design_library_dock.isVisible(),
            "source_window_count": len(source_windows),
            "source_windows": source_windows,
            "latest_source_key": self._last_source_window_key,
            "test_plan_open": str(self._asic_test_plan_path) in self._source_windows,
            "architecture_open": str(self._asic_architecture_path) in self._source_windows,
            "regression_log_open": str(self._asic_regression_log_path) in self._source_windows,
            "waveform_window_count": int(self._latest_waveform_window is not None) + len(self._waveform_windows),
        }

    def _ensure_test_tracker_window(self) -> TestTrackerWindow:
        """Create the standalone ASIC regression tracker on demand."""
        if self._test_tracker_window is None:
            from simulator.verification import build_lin_asic_test_catalog

            window = TestTrackerWindow()
            window.set_test_cases(build_lin_asic_test_catalog())
            window.run_regression_requested.connect(self._run_asic_regression_from_terminal)
            window.refresh_requested.connect(self._refresh_regression_report_from_disk)
            window.open_regression_log_requested.connect(self._open_asic_regression_log)
            window.open_test_plan_requested.connect(self._open_asic_test_plan)
            window.show_terminal_requested.connect(self._focus_terminal)
            window.show_api_monitor_requested.connect(self._show_api_session_monitor)
            window.destroyed.connect(lambda _obj=None: setattr(self, "_test_tracker_window", None))
            self._test_tracker_window = window

            if self._last_regression_report:
                window.update_report(self._last_regression_report)
            window.set_terminal_status(self.terminal_widget.get_status())

        return self._test_tracker_window

    def show_test_tracker_window(self) -> None:
        """Present the standalone ASIC regression tracker window."""
        window = self._ensure_test_tracker_window()
        window.showNormal()
        window.show()
        window.raise_()
        window.activateWindow()

    def _build_asic_regression_command(self) -> str:
        """Return the terminal command used for the LIN ASIC regression suite."""
        return (
            "python scripts/run_lin_asic_regression.py "
            "--json reports/lin_asic_regression_latest.json "
            "--markdown reports/lin_asic_regression_latest.md "
            "--log reports/lin_asic_regression_latest.log"
        )

    def _refresh_regression_report_from_disk(self) -> None:
        """Load the latest ASIC regression report into the tracker window."""
        if not self._asic_regression_report_path.exists():
            self.statusbar.showMessage("No ASIC regression report is available yet")
            return

        try:
            self._last_regression_report = json.loads(
                self._asic_regression_report_path.read_text(encoding="utf-8")
            )
            self._last_regression_report["report_path"] = str(self._asic_regression_report_path)
            self._last_regression_report.setdefault("log_path", str(self._asic_regression_log_path))
            tracker = self._ensure_test_tracker_window()
            tracker.update_report(self._last_regression_report)
            tracker.set_terminal_status(self.terminal_widget.get_status())
            self.statusbar.showMessage("Loaded latest ASIC regression report")
        except Exception as exc:
            self.statusbar.showMessage(f"Failed to load regression report: {exc}")

    def _open_asic_test_plan(self) -> None:
        """Open the ASIC verification plan in a standalone source window."""
        if not self._asic_test_plan_path.exists():
            self.statusbar.showMessage("ASIC test plan file is missing")
            return

        self._show_source_window(
            "ASIC Test Plan",
            self._read_text_file(self._asic_test_plan_path),
            str(self._asic_test_plan_path),
            language="markdown",
        )

    def _run_asic_regression_from_terminal(self) -> bool:
        """Run the ASIC regression suite through the integrated terminal."""
        command = self._build_asic_regression_command()
        self._last_regression_command = command
        self.show_test_tracker_window()
        tracker = self._ensure_test_tracker_window()
        tracker.set_regression_state(True, command)
        tracker.append_debug_line(f"[GUI] Starting regression: {command}")
        if self.terminal_widget.run_command(command):
            self.statusbar.showMessage("ASIC regression started in the integrated terminal")
            return True

        tracker.set_regression_state(False, command)
        tracker.append_debug_line("[GUI] Regression start failed")
        return False

    def _on_terminal_command_started(self, command: str) -> None:
        """Mirror terminal lifecycle into the tracker window."""
        if self._test_tracker_window:
            self._test_tracker_window.set_terminal_status(self.terminal_widget.get_status())
            self._test_tracker_window.append_debug_line(f"[TERM] Started: {command}")
            if "run_lin_asic_regression.py" in command:
                self._test_tracker_window.set_regression_state(True, command)

    def _on_terminal_command_output(self, text: str, is_error: bool) -> None:
        """Stream terminal output snippets into the tracker debug log."""
        if not self._test_tracker_window or not text.strip():
            return

        prefix = "[ERR]" if is_error else "[OUT]"
        for line in text.rstrip().splitlines()[-6:]:
            self._test_tracker_window.append_debug_line(f"{prefix} {line}")

    def _on_terminal_command_finished(self, exit_code: int, command: str) -> None:
        """Refresh tracker state when a terminal command completes."""
        if self._test_tracker_window:
            self._test_tracker_window.set_terminal_status(self.terminal_widget.get_status())
            self._test_tracker_window.append_debug_line(
                f"[TERM] Finished (exit={exit_code}): {command}"
            )
            if "run_lin_asic_regression.py" in command:
                self._test_tracker_window.set_regression_state(False, command)
                self._refresh_regression_report_from_disk()

    def _focus_terminal(self) -> None:
        """Bring the integrated terminal into focus and reserve visible space."""
        sizes = self._center_splitter.sizes()
        if len(sizes) >= 2 and sizes[1] < 180:
            total = sum(sizes)
            self._center_splitter.setSizes([max(400, total - 260), 260])
        self.terminal_widget.command_input.setFocus()

    def _show_api_session_monitor(self) -> None:
        """Bring the API session dock to the foreground."""
        self.api_session_dock.show()
        self.api_session_dock.raise_()

    def run_terminal_command(self, command: str) -> bool:
        """Public GUI-thread hook used by the API layer to run terminal commands."""
        return self.terminal_widget.run_command(command)

    def stop_terminal_command(self) -> None:
        """Public GUI-thread hook used by the API layer to stop terminal commands."""
        self.terminal_widget.stop_command()

    def get_terminal_status(self) -> dict:
        """Return terminal status for API polling."""
        return self.terminal_widget.get_status()

    def get_terminal_output(self) -> str:
        """Return terminal output for API polling."""
        return self.terminal_widget.get_output_text()

    def get_test_tracker_status(self) -> dict:
        """Return the latest ASIC verification status for API polling."""
        terminal_status = self.terminal_widget.get_status()
        return {
            "report_path": str(self._asic_regression_report_path),
            "log_path": str(self._asic_regression_log_path),
            "test_plan_path": str(self._asic_test_plan_path),
            "architecture_path": str(self._asic_architecture_path),
            "has_report": self._last_regression_report is not None,
            "summary": (self._last_regression_report or {}).get("summary", {}),
            "coverage": (self._last_regression_report or {}).get("coverage", {}),
            "running": terminal_status.get("running", False),
            "active_command": terminal_status.get("active_command", ""),
            "tests": (self._last_regression_report or {}).get("tests", []),
        }
    
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

        browse_design_library_action = QAction("Browse &Design Library...", self)
        browse_design_library_action.setShortcut(QKeySequence("Ctrl+Shift+L"))
        browse_design_library_action.triggered.connect(self._show_design_library_browser)
        file_menu.addAction(browse_design_library_action)

        launch_recent_chip_action = QAction("Launch Recent &Chip", self)
        launch_recent_chip_action.triggered.connect(self._launch_recent_chip_design)
        file_menu.addAction(launch_recent_chip_action)
        
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
        view_menu.addSeparator()
        waveform_window_action = QAction("Show &Waveform Window", self)
        waveform_window_action.setShortcut(QKeySequence("Ctrl+Shift+W"))
        waveform_window_action.triggered.connect(lambda: self._show_waveform_viewer())
        view_menu.addAction(waveform_window_action)
        source_window_action = QAction("Show Last &Source Window", self)
        source_window_action.setShortcut(QKeySequence("Ctrl+Shift+R"))
        source_window_action.triggered.connect(self._show_latest_source_window)
        view_menu.addAction(source_window_action)
        view_menu.addAction(self.design_library_dock.toggleViewAction())
        view_menu.addAction(self.api_session_dock.toggleViewAction())
        
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

        verification_menu = menubar.addMenu("&Verification")

        run_regression_action = QAction("Run &ASIC Regression", self)
        run_regression_action.setShortcut(QKeySequence("Ctrl+Shift+T"))
        run_regression_action.triggered.connect(self._run_asic_regression_from_terminal)
        verification_menu.addAction(run_regression_action)

        show_tracker_action = QAction("Show Test &Tracker", self)
        show_tracker_action.triggered.connect(self.show_test_tracker_window)
        verification_menu.addAction(show_tracker_action)

        refresh_tracker_action = QAction("&Refresh Regression Report", self)
        refresh_tracker_action.triggered.connect(self._refresh_regression_report_from_disk)
        verification_menu.addAction(refresh_tracker_action)

        open_regression_log_action = QAction("Open Regression &Log", self)
        open_regression_log_action.triggered.connect(self._open_asic_regression_log)
        verification_menu.addAction(open_regression_log_action)

        open_test_plan_action = QAction("Open ASIC Test &Plan", self)
        open_test_plan_action.triggered.connect(self._open_asic_test_plan)
        verification_menu.addAction(open_test_plan_action)

        open_architecture_action = QAction("Open ASIC &Architecture", self)
        open_architecture_action.triggered.connect(self._open_asic_architecture_overview)
        verification_menu.addAction(open_architecture_action)

        debug_menu = menubar.addMenu("&Debug")

        focus_terminal_action = QAction("Focus &Terminal", self)
        focus_terminal_action.setShortcut(QKeySequence("Ctrl+Shift+`"))
        focus_terminal_action.triggered.connect(self._focus_terminal)
        debug_menu.addAction(focus_terminal_action)

        api_monitor_action = QAction("Show API Session &Monitor", self)
        api_monitor_action.triggered.connect(self._show_api_session_monitor)
        debug_menu.addAction(api_monitor_action)

        latest_source_action = QAction("Show Latest &Source Window", self)
        latest_source_action.triggered.connect(self._show_latest_source_window)
        debug_menu.addAction(latest_source_action)
        
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

        design_lib_act = circuit_toolbar.addAction("🗂 Design Browser")
        design_lib_act.triggered.connect(self._show_design_library_browser)

        recent_chip_act = circuit_toolbar.addAction("🚀 Recent Chip")
        recent_chip_act.triggered.connect(self._launch_recent_chip_design)
    
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
        
        self._connect_editor_signals(self.schematic_editor)
        
        # Property editor -> Schematic editor (update component)
        self.property_editor.property_changed.connect(
            self.schematic_editor.update_component
        )
        
        # Schematic tabs
        self.schematic_tabs.tabCloseRequested.connect(self._close_tab)
        self.schematic_tabs.currentChanged.connect(self._on_schematic_tab_changed)

        self.terminal_widget.command_started.connect(self._on_terminal_command_started)
        self.terminal_widget.command_output.connect(self._on_terminal_command_output)
        self.terminal_widget.command_finished.connect(self._on_terminal_command_finished)
    
    def _restore_state(self):
        """Restore window state from settings."""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)

        # Keep the live API monitor visible even when restoring an older layout.
        self.api_session_dock.show()
        self.design_library_dock.show()
    
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

        if self._test_tracker_window is not None:
            self._test_tracker_window.close()
        for window in list(self._source_windows.values()):
            window.close()

        if self._latest_waveform_window is not None:
            self._latest_waveform_window.close()
        for window in list(self._waveform_windows):
            window.close()
        
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
            self._refresh_api_session_monitor()
    
    def _connect_editor_signals(self, editor: SchematicEditor):
        """Connect signals for a new editor."""
        editor.selection_changed.connect(self.property_editor.set_component)
        editor.cursor_moved.connect(self._update_coordinates)
        editor.zoom_changed.connect(self._update_zoom)
        editor.mode_changed.connect(self._update_mode)
        editor.schematic_modified.connect(self._refresh_api_session_monitor)
        editor.hierarchy_descend_requested.connect(
            lambda component, source_editor=editor: self._descend_into_hierarchy_block(source_editor, component)
        )
        editor.hierarchy_ascend_requested.connect(
            lambda source_editor=editor: self._ascend_hierarchy(source_editor)
        )
    
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
                    self._show_waveform_viewer(
                        results,
                        title=f"{analysis_type} Simulation",
                    )
                    self.statusbar.showMessage(f"{analysis_type} simulation completed")
        except Exception as e:
            QMessageBox.critical(self, "Simulation Error", str(e))
    
    def _show_waveform_viewer(
        self,
        results: Optional[dict] = None,
        title: str = "Latest Simulation",
    ) -> None:
        """Show the reusable standalone waveform window for local simulations."""
        window = self._get_latest_waveform_window()
        window.setWindowTitle(f"Waveforms — {title}")
        if results is not None:
            window.display_results(results)
        window.showNormal()
        window.show()
        window.raise_()
        window.activateWindow()
        QApplication.processEvents()
    
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
            "<li>Standalone waveform window with measurements</li>"
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
        and displays results in a separate waveform window.
        
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
            op_match = re.search(r'\.OP\b', netlist, re.I)
            
            if dc_match:
                analysis_type = "DC"
            elif ac_match:
                analysis_type = "AC"
            elif tran_match:
                analysis_type = "Transient"
            elif op_match:
                analysis_type = "Operating Point"
            
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
            elif analysis_type == "Operating Point":
                results = engine.solve_dc()
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
                results = self._normalize_results_for_waveform_viewer(results, analysis_type)
                self._show_waveform_viewer(
                    results,
                    title=f"{name} — {analysis_type}",
                )
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
            if hasattr(self, 'terminal_widget'):
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
                self.terminal_widget.append_text(summary)
        except Exception as e:
            QMessageBox.critical(self, "Auto-Design Error", f"Failed:\n{e}")

    # ──────────────────────────────────────────────────────────────
    #  ASIC hierarchy helpers  (called from the API server thread
    #  via QTimer.singleShot so they always run on the GUI thread)
    # ──────────────────────────────────────────────────────────────

    def load_block_tab(
        self,
        tab_name: str,
        netlist: str,
        hierarchical: bool = False,
        block_key: Optional[str] = None,
        parent_tab_name: Optional[str] = None,
        block_aliases: Optional[list[str]] = None,
        domain: Optional[str] = None,
        rtl_file: Optional[str] = None,
        spice_file: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> None:
        """Open a new schematic tab and load *netlist* into it.

        Used by the API server to populate one tab per LIN ASIC block so
        the schematic editor shows the full chip hierarchy.
        """
        spec = self._register_hierarchy_tab_spec(
            tab_name,
            netlist,
            hierarchical=hierarchical,
            block_key=block_key,
            parent_tab_name=parent_tab_name,
            block_aliases=block_aliases,
            domain=domain,
            rtl_file=rtl_file,
            spice_file=spice_file,
            display_name=display_name,
        )

        editor = SchematicEditor()
        editor.configure_hierarchy_navigation(
            tab_name,
            parent_tab_name=spec.get("parent_tab_name"),
            root_tab_name=self._hierarchy_top_level_tab_name or tab_name,
        )
        editor._hierarchy_aliases = set(spec.get("aliases", set()))
        index = self.schematic_tabs.addTab(editor, tab_name)
        self.schematic_tabs.setCurrentIndex(index)
        self.schematic_editor = editor
        self._connect_editor_signals(editor)
        if netlist:
            editor.load_from_netlist(netlist, preserve_hierarchy=hierarchical)
        self.statusbar.showMessage(f"Loaded: {tab_name}")

    def run_netlist_in_window(self, results: dict, title: str) -> None:
        """Display simulation results in a new standalone waveform window.

        Opens a separate WaveformWindow so that
        each block's waveform is shown in its own resizable window.
        """
        win = WaveformWindow(title)
        win.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        win.display_results(results)
        offset = 36 * (len(self._waveform_windows) % 6)
        win.move(self.x() + 60 + offset, self.y() + 60 + offset)
        self._waveform_windows.append(win)
        win.destroyed.connect(lambda _obj=None, window=win: self._remove_waveform_window(window))
        win.showNormal()
        win.show()
        win.raise_()
        win.activateWindow()
        QApplication.processEvents()

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

