"""
Component Library - Panel for selecting components to place.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLineEdit, QLabel, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from simulator.components.passive import Resistor, Capacitor, Inductor, PolarizedCapacitor
from simulator.components.transistors import NMOS, PMOS, NPN, PNP
from simulator.components.sources import (
    VoltageSource, CurrentSource, PulseSource, SineSource, PWLSource,
    VoltageProbe, CurrentProbe, Ground, VDD
)
from simulator.components.digital import (
    ANDGate, ORGate, NOTGate, NANDGate, NORGate, XORGate, XNORGate,
    Buffer, DFlipFlop, SRLatch, Mux2to1
)
from simulator.components.amplifiers import OpAmp, Comparator, InstrumentationAmplifier
from simulator.components.diodes import Diode, Zener, LED, SchottkyDiode
from simulator.components.analog_blocks import (
    LDORegulator, BandgapReference, CurrentMirror, OTA,
    VoltageBuffer, LevelShifter
)


# Component registry for serialization
COMPONENT_REGISTRY = {
    'Resistor': Resistor,
    'Capacitor': Capacitor,
    'Inductor': Inductor,
    'PolarizedCapacitor': PolarizedCapacitor,
    'NMOS': NMOS,
    'PMOS': PMOS,
    'NPN': NPN,
    'PNP': PNP,
    'VoltageSource': VoltageSource,
    'CurrentSource': CurrentSource,
    'PulseSource': PulseSource,
    'SineSource': SineSource,
    'PWLSource': PWLSource,
    'VoltageProbe': VoltageProbe,
    'CurrentProbe': CurrentProbe,
    'Ground': Ground,
    'VDD': VDD,
    'Diode': Diode,
    'Zener': Zener,
    'LED': LED,
    'SchottkyDiode': SchottkyDiode,
    'OpAmp': OpAmp,
    'Comparator': Comparator,
    'InstrumentationAmplifier': InstrumentationAmplifier,
    'ANDGate': ANDGate,
    'ORGate': ORGate,
    'NOTGate': NOTGate,
    'NANDGate': NANDGate,
    'NORGate': NORGate,
    'XORGate': XORGate,
    'XNORGate': XNORGate,
    'Buffer': Buffer,
    'DFlipFlop': DFlipFlop,
    'SRLatch': SRLatch,
    'Mux2to1': Mux2to1,
    'LDORegulator': LDORegulator,
    'BandgapReference': BandgapReference,
    'CurrentMirror': CurrentMirror,
    'OTA': OTA,
    'VoltageBuffer': VoltageBuffer,
    'LevelShifter': LevelShifter,
}


# Component categories
COMPONENT_CATEGORIES = {
    'Passive': [
        ('Resistor', Resistor),
        ('Capacitor', Capacitor),
        ('Polarized Capacitor', PolarizedCapacitor),
        ('Inductor', Inductor),
    ],
    'Transistors': [
        ('NMOS', NMOS),
        ('PMOS', PMOS),
        ('NPN BJT', NPN),
        ('PNP BJT', PNP),
    ],
    'Diodes': [
        ('Diode', Diode),
        ('Zener Diode', Zener),
        ('Schottky Diode', SchottkyDiode),
        ('LED', LED),
    ],
    'Sources': [
        ('DC Voltage', VoltageSource),
        ('DC Current', CurrentSource),
        ('Pulse Source', PulseSource),
        ('Sine Source', SineSource),
        ('PWL Source', PWLSource),
        ('Ground', Ground),
        ('VDD', VDD),
    ],
    'Probes': [
        ('Voltage Probe', VoltageProbe),
        ('Current Probe', CurrentProbe),
    ],
    'Amplifiers': [
        ('Op-Amp', OpAmp),
        ('Comparator', Comparator),
        ('Instrumentation Amp', InstrumentationAmplifier),
    ],
    'Digital Gates': [
        ('AND Gate', ANDGate),
        ('OR Gate', ORGate),
        ('NOT Gate', NOTGate),
        ('NAND Gate', NANDGate),
        ('NOR Gate', NORGate),
        ('XOR Gate', XORGate),
        ('XNOR Gate', XNORGate),
        ('Buffer', Buffer),
    ],
    'Digital Sequential': [
        ('D Flip-Flop', DFlipFlop),
        ('SR Latch', SRLatch),
        ('2:1 Multiplexer', Mux2to1),
    ],
    'Analog Blocks': [
        ('LDO Regulator', LDORegulator),
        ('Bandgap Reference', BandgapReference),
        ('Current Mirror', CurrentMirror),
        ('OTA (Gm Amp)', OTA),
        ('Voltage Buffer', VoltageBuffer),
        ('Level Shifter', LevelShifter),
    ],
}


class ComponentLibrary(QWidget):
    """Component library panel for selecting components."""
    
    component_selected = pyqtSignal(type)  # Emits component class
    
    def __init__(self):
        super().__init__()
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Title
        title = QLabel("Component Library")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search components...")
        self.search_box.textChanged.connect(self._filter_components)
        layout.addWidget(self.search_box)
        
        # Component tree
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(15)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.tree)
        
        # Populate tree
        self._populate_tree()
    
    def _populate_tree(self):
        """Populate the component tree."""
        self.tree.clear()
        
        for category, components in COMPONENT_CATEGORIES.items():
            category_item = QTreeWidgetItem([category])
            category_item.setFont(0, QFont("Arial", 10, QFont.Weight.Bold))
            category_item.setExpanded(True)
            
            for name, comp_class in components:
                comp_item = QTreeWidgetItem([name])
                comp_item.setData(0, Qt.ItemDataRole.UserRole, comp_class)
                category_item.addChild(comp_item)
            
            self.tree.addTopLevelItem(category_item)
    
    def _filter_components(self, text: str):
        """Filter components by search text."""
        text = text.lower()
        
        for i in range(self.tree.topLevelItemCount()):
            category = self.tree.topLevelItem(i)
            category_visible = False
            
            for j in range(category.childCount()):
                item = category.child(j)
                name = item.text(0).lower()
                visible = text in name or not text
                item.setHidden(not visible)
                if visible:
                    category_visible = True
            
            category.setHidden(not category_visible)
    
    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle double-click on component."""
        comp_class = item.data(0, Qt.ItemDataRole.UserRole)
        if comp_class:
            self.component_selected.emit(comp_class)
