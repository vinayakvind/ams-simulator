"""
Property Editor - Panel for editing component properties.
Enhanced with MOSFET sizing calculator and engineering unit support.
"""

from typing import Optional
import re

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, QLineEdit,
    QComboBox, QCheckBox, QDoubleSpinBox, QSpinBox,
    QGroupBox, QScrollArea, QHBoxLayout, QPushButton,
    QSlider, QGridLayout, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from simulator.components.base import Component, ComponentProperty, PropertyType


class EngineeringSpinBox(QWidget):
    """Custom widget for entering values with engineering unit prefixes."""
    
    valueChanged = pyqtSignal(float)
    
    PREFIXES = [
        ('T', 1e12), ('G', 1e9), ('M', 1e6), ('k', 1e3),
        ('', 1), ('m', 1e-3), ('µ', 1e-6), ('u', 1e-6),
        ('n', 1e-9), ('p', 1e-12), ('f', 1e-15)
    ]
    
    def __init__(self, unit: str = "", min_val: float = 1e-15, max_val: float = 1e15):
        super().__init__()
        self._value = 0.0
        self._unit = unit
        self._min = min_val
        self._max = max_val
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        self.edit = QLineEdit()
        self.edit.setMaximumWidth(80)
        self.edit.editingFinished.connect(self._parse_value)
        layout.addWidget(self.edit)
        
        self.prefix_combo = QComboBox()
        self.prefix_combo.addItems(['T', 'G', 'M', 'k', '', 'm', 'µ', 'n', 'p', 'f'])
        self.prefix_combo.setCurrentText('')
        self.prefix_combo.setMaximumWidth(50)
        self.prefix_combo.currentTextChanged.connect(self._on_prefix_changed)
        layout.addWidget(self.prefix_combo)
        
        self.unit_label = QLabel(self._unit)
        layout.addWidget(self.unit_label)
    
    def setValue(self, value: float):
        """Set the value and update display."""
        self._value = value
        self._update_display()
    
    def value(self) -> float:
        return self._value
    
    def _update_display(self):
        """Update the display with appropriate prefix."""
        if self._value == 0:
            self.edit.setText("0")
            self.prefix_combo.setCurrentText('')
            return
        
        # Find best prefix
        abs_val = abs(self._value)
        best_prefix = ''
        best_multiplier = 1
        
        for prefix, mult in self.PREFIXES:
            if abs_val >= mult * 0.1 and abs_val < mult * 1000:
                best_prefix = prefix
                best_multiplier = mult
                break
        
        display_val = self._value / best_multiplier
        self.edit.setText(f"{display_val:.4g}")
        self.prefix_combo.setCurrentText(best_prefix if best_prefix else '')
    
    def _parse_value(self):
        """Parse the entered value."""
        try:
            text = self.edit.text().strip()
            # Handle engineering notation in text (e.g., "10u" or "1.5k")
            match = re.match(r'^([+-]?[\d.]+(?:[eE][+-]?\d+)?)\s*([TGMkmuµnpf]?)$', text)
            if match:
                num = float(match.group(1))
                prefix = match.group(2) or self.prefix_combo.currentText()
                multiplier = dict(self.PREFIXES).get(prefix, 1)
                self._value = num * multiplier
            else:
                num = float(text)
                prefix = self.prefix_combo.currentText()
                multiplier = dict(self.PREFIXES).get(prefix, 1)
                self._value = num * multiplier
            
            self._value = max(self._min, min(self._max, self._value))
            self.valueChanged.emit(self._value)
        except ValueError:
            self._update_display()
    
    def _on_prefix_changed(self):
        """Handle prefix change - recalculate value."""
        self._parse_value()


class MOSFETSizingWidget(QWidget):
    """Special widget for MOSFET W/L sizing with calculator."""
    
    sizingChanged = pyqtSignal(float, float)  # width, length
    
    def __init__(self):
        super().__init__()
        self._width = 1e-6
        self._length = 100e-9
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Width input
        w_layout = QHBoxLayout()
        w_layout.addWidget(QLabel("W:"))
        self.w_spin = EngineeringSpinBox("m", 1e-9, 1e-3)
        self.w_spin.setValue(self._width)
        self.w_spin.valueChanged.connect(self._on_width_changed)
        w_layout.addWidget(self.w_spin)
        layout.addLayout(w_layout)
        
        # Length input
        l_layout = QHBoxLayout()
        l_layout.addWidget(QLabel("L:"))
        self.l_spin = EngineeringSpinBox("m", 1e-9, 1e-3)
        self.l_spin.setValue(self._length)
        self.l_spin.valueChanged.connect(self._on_length_changed)
        l_layout.addWidget(self.l_spin)
        layout.addLayout(l_layout)
        
        # W/L ratio display and slider
        ratio_frame = QFrame()
        ratio_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        ratio_layout = QVBoxLayout(ratio_frame)
        ratio_layout.setContentsMargins(5, 5, 5, 5)
        
        self.ratio_label = QLabel("W/L = 10.0")
        self.ratio_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        ratio_layout.addWidget(self.ratio_label)
        
        self.ratio_slider = QSlider(Qt.Orientation.Horizontal)
        self.ratio_slider.setRange(1, 1000)  # W/L from 0.1 to 100
        self.ratio_slider.setValue(100)  # Default W/L = 10
        self.ratio_slider.valueChanged.connect(self._on_ratio_slider_changed)
        ratio_layout.addWidget(self.ratio_slider)
        
        layout.addWidget(ratio_frame)
        
        # Quick sizing buttons
        btn_layout = QGridLayout()
        sizes = [
            ("Min", 0.18e-6, 0.18e-6),
            ("1x", 1e-6, 0.18e-6),
            ("2x", 2e-6, 0.18e-6),
            ("5x", 5e-6, 0.18e-6),
            ("10x", 10e-6, 0.18e-6),
            ("Power", 100e-6, 0.35e-6),
        ]
        for i, (name, w, l) in enumerate(sizes):
            btn = QPushButton(name)
            btn.setMaximumWidth(50)
            btn.clicked.connect(lambda checked, w=w, l=l: self._set_size(w, l))
            btn_layout.addWidget(btn, i // 3, i % 3)
        layout.addLayout(btn_layout)
        
        self._update_ratio_display()
    
    def setWidth(self, w: float):
        self._width = w
        self.w_spin.setValue(w)
        self._update_ratio_display()
    
    def setLength(self, l: float):
        self._length = l
        self.l_spin.setValue(l)
        self._update_ratio_display()
    
    def _on_width_changed(self, value: float):
        self._width = value
        self._update_ratio_display()
        self.sizingChanged.emit(self._width, self._length)
    
    def _on_length_changed(self, value: float):
        self._length = value
        self._update_ratio_display()
        self.sizingChanged.emit(self._width, self._length)
    
    def _on_ratio_slider_changed(self, value: int):
        """Adjust width to match desired W/L ratio, keeping length fixed."""
        ratio = value / 10.0  # Slider value 1-1000 maps to W/L 0.1-100
        self._width = self._length * ratio
        self.w_spin.setValue(self._width)
        self._update_ratio_display()
        self.sizingChanged.emit(self._width, self._length)
    
    def _set_size(self, w: float, l: float):
        """Set a predefined size."""
        self._width = w
        self._length = l
        self.w_spin.setValue(w)
        self.l_spin.setValue(l)
        self._update_ratio_display()
        self.sizingChanged.emit(self._width, self._length)
    
    def _update_ratio_display(self):
        if self._length > 0:
            ratio = self._width / self._length
            self.ratio_label.setText(f"W/L = {ratio:.2f}")
            # Update slider without triggering signal
            self.ratio_slider.blockSignals(True)
            self.ratio_slider.setValue(int(ratio * 10))
            self.ratio_slider.blockSignals(False)


class PropertyEditor(QWidget):
    """Panel for editing component properties with enhanced MOSFET sizing."""
    
    property_changed = pyqtSignal(object)  # Emits component after change
    
    def __init__(self):
        super().__init__()
        self._current_component: Optional[Component] = None
        self._property_widgets: dict = {}
        self._mosfet_sizing_widget: Optional[MOSFETSizingWidget] = None
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Title
        self.title_label = QLabel("Properties")
        self.title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(self.title_label)
        
        # Scroll area for properties
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(scroll)
        
        # Content widget
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.content)
        
        # Component info group
        self.info_group = QGroupBox("Component Info")
        info_layout = QFormLayout()
        
        self.ref_edit = QLineEdit()
        self.ref_edit.editingFinished.connect(self._on_reference_changed)
        info_layout.addRow("Reference:", self.ref_edit)
        
        self.type_label = QLabel()
        info_layout.addRow("Type:", self.type_label)
        
        self.pos_label = QLabel()
        info_layout.addRow("Position:", self.pos_label)
        
        self.info_group.setLayout(info_layout)
        self.content_layout.addWidget(self.info_group)
        
        # MOSFET Sizing group (shown only for MOSFETs)
        self.mosfet_group = QGroupBox("MOSFET Sizing")
        mosfet_layout = QVBoxLayout()
        self._mosfet_sizing_widget = MOSFETSizingWidget()
        self._mosfet_sizing_widget.sizingChanged.connect(self._on_mosfet_sizing_changed)
        mosfet_layout.addWidget(self._mosfet_sizing_widget)
        self.mosfet_group.setLayout(mosfet_layout)
        self.content_layout.addWidget(self.mosfet_group)
        
        # Properties group
        self.props_group = QGroupBox("Parameters")
        self.props_layout = QFormLayout()
        self.props_group.setLayout(self.props_layout)
        self.content_layout.addWidget(self.props_group)
        
        # Pins group
        self.pins_group = QGroupBox("Pin Connections")
        self.pins_layout = QFormLayout()
        self.pins_group.setLayout(self.pins_layout)
        self.content_layout.addWidget(self.pins_group)
        
        # Initially hide all groups
        self.info_group.hide()
        self.mosfet_group.hide()
        self.props_group.hide()
        self.pins_group.hide()
    
    def set_component(self, component: Optional[Component]):
        """Set the component to edit."""
        self._current_component = component
        self._property_widgets.clear()
        
        # Clear existing property widgets
        while self.props_layout.count():
            item = self.props_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        while self.pins_layout.count():
            item = self.pins_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if component is None:
            self.title_label.setText("Properties")
            self.info_group.hide()
            self.mosfet_group.hide()
            self.props_group.hide()
            self.pins_group.hide()
            return
        
        # Show groups
        self.info_group.show()
        self.props_group.show()
        self.pins_group.show()
        
        # Check if MOSFET - show special sizing widget
        is_mosfet = 'NMOS' in component.display_name or 'PMOS' in component.display_name
        if is_mosfet:
            self.mosfet_group.show()
            # Set current W/L values
            w = component.properties.get('w', None)
            l = component.properties.get('l', None)
            if w and l:
                self._mosfet_sizing_widget.setWidth(float(w.value))
                self._mosfet_sizing_widget.setLength(float(l.value))
        else:
            self.mosfet_group.hide()
        
        # Update title
        self.title_label.setText(f"Properties: {component.display_name}")
        
        # Update info
        self.ref_edit.setText(component.reference)
        self.type_label.setText(component.display_name)
        self.pos_label.setText(f"({component.x:.1f}, {component.y:.1f})")
        
        # Create property widgets (skip W/L for MOSFETs as they have special widget)
        skip_props = ['w', 'l'] if is_mosfet else []
        for name, prop in component.properties.items():
            if name in skip_props:
                continue
            widget = self._create_property_widget(prop)
            if widget:
                self._property_widgets[name] = widget
                label = QLabel(f"{prop.display_name}:")
                label.setToolTip(prop.description)
                self.props_layout.addRow(label, widget)
        
        # Create pin connection displays
        for pin in component.pins:
            net_label = QLabel(pin.connected_net or "(unconnected)")
            self.pins_layout.addRow(f"{pin.name}:", net_label)
    
    def _on_mosfet_sizing_changed(self, width: float, length: float):
        """Handle MOSFET sizing change."""
        if self._current_component:
            self._current_component.set_property('w', width)
            self._current_component.set_property('l', length)
            self.property_changed.emit(self._current_component)
    
    def _create_property_widget(self, prop: ComponentProperty) -> Optional[QWidget]:
        """Create a widget for editing a property."""
        if prop.property_type == PropertyType.FLOAT:
            widget = QDoubleSpinBox()
            widget.setDecimals(9)
            widget.setRange(-1e15, 1e15)
            widget.setValue(float(prop.value))
            widget.setSuffix(f" {prop.unit}" if prop.unit else "")
            widget.valueChanged.connect(
                lambda v, n=prop.name: self._on_property_changed(n, v)
            )
            return widget
        
        elif prop.property_type == PropertyType.INTEGER:
            widget = QSpinBox()
            widget.setRange(
                int(prop.min_value) if prop.min_value else -1000000,
                int(prop.max_value) if prop.max_value else 1000000
            )
            widget.setValue(int(prop.value))
            widget.valueChanged.connect(
                lambda v, n=prop.name: self._on_property_changed(n, v)
            )
            return widget
        
        elif prop.property_type == PropertyType.STRING:
            widget = QLineEdit()
            widget.setText(str(prop.value))
            widget.editingFinished.connect(
                lambda n=prop.name, w=widget: self._on_property_changed(n, w.text())
            )
            return widget
        
        elif prop.property_type == PropertyType.BOOLEAN:
            widget = QCheckBox()
            widget.setChecked(bool(prop.value))
            widget.stateChanged.connect(
                lambda s, n=prop.name: self._on_property_changed(n, s == Qt.CheckState.Checked.value)
            )
            return widget
        
        elif prop.property_type == PropertyType.ENUM:
            widget = QComboBox()
            widget.addItems(prop.enum_values)
            if prop.value in prop.enum_values:
                widget.setCurrentText(str(prop.value))
            widget.currentTextChanged.connect(
                lambda v, n=prop.name: self._on_property_changed(n, v)
            )
            return widget
        
        return None
    
    def _on_reference_changed(self):
        """Handle reference designator change."""
        if self._current_component:
            self._current_component.reference = self.ref_edit.text()
            self.property_changed.emit(self._current_component)
    
    def _on_property_changed(self, name: str, value):
        """Handle property value change."""
        if self._current_component:
            success, error = self._current_component.set_property(name, value)
            if success:
                self.property_changed.emit(self._current_component)
