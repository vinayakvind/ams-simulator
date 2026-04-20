"""
Waveform Viewer - Display simulation results as waveforms.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QToolBar,
    QLabel, QComboBox, QCheckBox, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLineEdit, QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt, pyqtSignal

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
import numpy as np


@dataclass
class WaveformData:
    """Container for waveform data."""
    name: str
    time: np.ndarray
    values: np.ndarray
    unit: str = "V"
    color: str = None
    visible: bool = True
    
    @property
    def min_value(self) -> float:
        return float(np.min(self.values))
    
    @property
    def max_value(self) -> float:
        return float(np.max(self.values))
    
    @property
    def mean_value(self) -> float:
        return float(np.mean(self.values))


class MplCanvas(FigureCanvasQTAgg):
    """Matplotlib canvas for waveform display."""
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        
        # Configure appearance
        self.fig.set_facecolor('#ffffff')
        self.axes.set_facecolor('#fafafa')
        self.axes.grid(True, linestyle='--', alpha=0.7)
        self.axes.set_xlabel('Time (s)')
        self.axes.set_ylabel('Voltage (V)')


class WaveformViewer(QWidget):
    """Widget for viewing simulation waveforms."""
    
    cursor_moved = pyqtSignal(float, float)  # time, value
    
    def __init__(self):
        super().__init__()
        
        # Waveform data storage
        self._waveforms: Dict[str, WaveformData] = {}
        self._cursor_time: Optional[float] = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Left panel - Signal list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        
        # Signal tree
        self.signal_tree = QTreeWidget()
        self.signal_tree.setHeaderLabels(["Signal", "Value"])
        self.signal_tree.setColumnWidth(0, 150)
        self.signal_tree.itemChanged.connect(self._on_signal_visibility_changed)
        left_layout.addWidget(self.signal_tree)
        
        # Measurements group
        meas_group = QGroupBox("Measurements")
        meas_layout = QFormLayout()
        
        self.cursor_time_label = QLabel("---")
        meas_layout.addRow("Cursor Time:", self.cursor_time_label)
        
        self.cursor_value_label = QLabel("---")
        meas_layout.addRow("Cursor Value:", self.cursor_value_label)
        
        self.min_label = QLabel("---")
        meas_layout.addRow("Min:", self.min_label)
        
        self.max_label = QLabel("---")
        meas_layout.addRow("Max:", self.max_label)
        
        self.mean_label = QLabel("---")
        meas_layout.addRow("Mean:", self.mean_label)
        
        meas_group.setLayout(meas_layout)
        left_layout.addWidget(meas_group)
        
        splitter.addWidget(left_panel)
        
        # Right panel - Waveform display
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Toolbar
        toolbar = QToolBar()
        
        toolbar.addAction("Zoom In", self._zoom_in)
        toolbar.addAction("Zoom Out", self._zoom_out)
        toolbar.addAction("Fit", self._fit_view)
        toolbar.addSeparator()
        toolbar.addAction("Cursor", self._toggle_cursor)
        toolbar.addSeparator()
        toolbar.addAction("Export", self._export_data)
        
        right_layout.addWidget(toolbar)
        
        # Matplotlib canvas
        self.canvas = MplCanvas(self, width=8, height=4, dpi=100)
        right_layout.addWidget(self.canvas)
        
        # Navigation toolbar
        self.nav_toolbar = NavigationToolbar2QT(self.canvas, self)
        right_layout.addWidget(self.nav_toolbar)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([200, 600])
        
        # Connect canvas events
        self.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)
        self.canvas.mpl_connect('button_press_event', self._on_mouse_click)
    
    def display_results(self, results: dict):
        """Display simulation results."""
        self._waveforms.clear()
        self.signal_tree.clear()
        
        # Process results
        time_data = results.get('time', np.array([]))
        
        # Keys to skip (metadata, not waveform data)
        skip_keys = {'time', 'type', 'dc_op'}
        
        for name, data in results.items():
            if name in skip_keys:
                continue
            
            # Skip non-numeric data
            if isinstance(data, str):
                continue
            
            # Create waveform data
            if isinstance(data, dict):
                values = np.array(data.get('values', []))
                unit = data.get('unit', 'V')
            else:
                try:
                    values = np.array(data, dtype=float)
                except (ValueError, TypeError):
                    continue  # Skip non-numeric data
                unit = 'V' if name.startswith('v') or name.startswith('V') else 'A'
            
            if values.size == 0:
                continue
            
            waveform = WaveformData(
                name=name,
                time=time_data,
                values=values,
                unit=unit
            )
            self._waveforms[name] = waveform
            
            # Add to signal tree
            item = QTreeWidgetItem([name, f"{waveform.mean_value:.4g} {unit}"])
            item.setCheckState(0, Qt.CheckState.Checked)
            item.setData(0, Qt.ItemDataRole.UserRole, name)
            self.signal_tree.addTopLevelItem(item)
        
        self._update_plot()
    
    def add_waveform(self, name: str, time: np.ndarray, values: np.ndarray,
                     unit: str = "V"):
        """Add a single waveform."""
        waveform = WaveformData(
            name=name,
            time=time,
            values=values,
            unit=unit
        )
        self._waveforms[name] = waveform
        
        item = QTreeWidgetItem([name, f"{waveform.mean_value:.4g} {unit}"])
        item.setCheckState(0, Qt.CheckState.Checked)
        item.setData(0, Qt.ItemDataRole.UserRole, name)
        self.signal_tree.addTopLevelItem(item)
        
        self._update_plot()
    
    def clear_waveforms(self):
        """Clear all waveforms."""
        self._waveforms.clear()
        self.signal_tree.clear()
        self.canvas.axes.clear()
        self.canvas.draw()
    
    def _update_plot(self):
        """Update the waveform plot."""
        self.canvas.axes.clear()
        self.canvas.axes.grid(True, linestyle='--', alpha=0.7)
        
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                  '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        
        visible_count = 0
        for i, (name, waveform) in enumerate(self._waveforms.items()):
            if not waveform.visible:
                continue
            
            color = colors[i % len(colors)]
            self.canvas.axes.plot(
                waveform.time, waveform.values,
                label=name, color=color, linewidth=1.5
            )
            visible_count += 1
        
        if visible_count > 0:
            self.canvas.axes.legend(loc='upper right')
        
        self.canvas.axes.set_xlabel('Time (s)')
        self.canvas.axes.set_ylabel('Value')
        self.canvas.fig.tight_layout()
        self.canvas.draw()
    
    def _on_signal_visibility_changed(self, item: QTreeWidgetItem, column: int):
        """Handle signal visibility change."""
        name = item.data(0, Qt.ItemDataRole.UserRole)
        if name and name in self._waveforms:
            self._waveforms[name].visible = (
                item.checkState(0) == Qt.CheckState.Checked
            )
            self._update_plot()
    
    def _on_mouse_move(self, event):
        """Handle mouse move on canvas."""
        if event.inaxes != self.canvas.axes:
            return
        
        time = event.xdata
        self.cursor_time_label.setText(f"{time:.6g} s")
        
        # Find values at this time
        for name, waveform in self._waveforms.items():
            if not waveform.visible:
                continue
            
            # Find nearest time index
            idx = np.argmin(np.abs(waveform.time - time))
            value = waveform.values[idx]
            
            # Update tree item
            for i in range(self.signal_tree.topLevelItemCount()):
                item = self.signal_tree.topLevelItem(i)
                if item.data(0, Qt.ItemDataRole.UserRole) == name:
                    item.setText(1, f"{value:.4g} {waveform.unit}")
                    break
    
    def _on_mouse_click(self, event):
        """Handle mouse click on canvas."""
        if event.inaxes != self.canvas.axes:
            return
        
        if event.button == 1:  # Left click
            self._cursor_time = event.xdata
            self._update_measurements()
    
    def _update_measurements(self):
        """Update measurement displays."""
        if not self._waveforms:
            return
        
        # Get first visible waveform for measurements
        for waveform in self._waveforms.values():
            if waveform.visible:
                self.min_label.setText(f"{waveform.min_value:.4g} {waveform.unit}")
                self.max_label.setText(f"{waveform.max_value:.4g} {waveform.unit}")
                self.mean_label.setText(f"{waveform.mean_value:.4g} {waveform.unit}")
                
                if self._cursor_time is not None:
                    idx = np.argmin(np.abs(waveform.time - self._cursor_time))
                    value = waveform.values[idx]
                    self.cursor_value_label.setText(f"{value:.4g} {waveform.unit}")
                break
    
    def _zoom_in(self):
        """Zoom in."""
        self.nav_toolbar.zoom()
    
    def _zoom_out(self):
        """Zoom out."""
        self.canvas.axes.autoscale()
        self.canvas.draw()
    
    def _fit_view(self):
        """Fit view to data."""
        self.canvas.axes.autoscale()
        self.canvas.draw()
    
    def _toggle_cursor(self):
        """Toggle cursor display."""
        pass  # TODO: Implement cursor line
    
    def _export_data(self):
        """Export waveform data."""
        from PyQt6.QtWidgets import QFileDialog
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Waveform Data",
            "",
            "CSV Files (*.csv);;All Files (*.*)"
        )
        
        if filename:
            self._export_to_csv(filename)
    
    def _export_to_csv(self, filename: str):
        """Export waveforms to CSV file."""
        if not self._waveforms:
            return
        
        # Get time array from first waveform
        time_array = list(self._waveforms.values())[0].time
        
        with open(filename, 'w') as f:
            # Header
            headers = ['time'] + list(self._waveforms.keys())
            f.write(','.join(headers) + '\n')
            
            # Data rows
            for i, t in enumerate(time_array):
                row = [str(t)]
                for waveform in self._waveforms.values():
                    row.append(str(waveform.values[i]))
                f.write(','.join(row) + '\n')
