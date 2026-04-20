"""
Diode components: Diode, Zener, LED.
"""

from simulator.components.base import (
    Component, ComponentType, Pin, PinType,
    ComponentProperty, PropertyType
)


class Diode(Component):
    """Standard PN Junction Diode."""
    
    def __init__(self):
        self._ref_prefix = "D"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.DIODE
    
    @property
    def display_name(self) -> str:
        return "Diode"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """Diode symbol."""
        return [
            ('line', -30, 0, -10, 0),
            ('polygon', [(-10, -12), (-10, 12), (10, 0)]),
            ('line', 10, -12, 10, 12),
            ('line', 10, 0, 30, 0),
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("A", PinType.BIDIRECTIONAL, -30, 0),  # Anode
            Pin("K", PinType.BIDIRECTIONAL, 30, 0),   # Cathode
        ]
    
    def _init_properties(self):
        self._properties = {
            'model': ComponentProperty(
                name='model',
                display_name='Model',
                property_type=PropertyType.STRING,
                default_value='D1N4148',
                description='SPICE diode model'
            ),
            'is': ComponentProperty(
                name='is',
                display_name='Saturation Current',
                property_type=PropertyType.FLOAT,
                default_value=1e-14,
                unit='A',
                min_value=0.0,
                description='Reverse saturation current'
            ),
            'n': ComponentProperty(
                name='n',
                display_name='Emission Coefficient',
                property_type=PropertyType.FLOAT,
                default_value=1.0,
                min_value=0.5,
                max_value=2.5,
                description='Emission coefficient'
            ),
            'bv': ComponentProperty(
                name='bv',
                display_name='Breakdown Voltage',
                property_type=PropertyType.FLOAT,
                default_value=100.0,
                unit='V',
                min_value=0.0,
                description='Reverse breakdown voltage'
            ),
            'rs': ComponentProperty(
                name='rs',
                display_name='Series Resistance',
                property_type=PropertyType.FLOAT,
                default_value=0.1,
                unit='Ω',
                min_value=0.0,
                description='Series resistance'
            ),
            'cjo': ComponentProperty(
                name='cjo',
                display_name='Junction Capacitance',
                property_type=PropertyType.FLOAT,
                default_value=1e-12,
                unit='F',
                min_value=0.0,
                description='Zero-bias junction capacitance'
            ),
        }
    
    def get_spice_model(self) -> str:
        model = self._properties['model'].value
        
        a = self._pins[0].connected_net or '0'
        k = self._pins[1].connected_net or '0'
        
        return f"{self.reference} {a} {k} {model}"


class Zener(Component):
    """Zener Diode."""
    
    def __init__(self):
        self._ref_prefix = "D"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.DIODE
    
    @property
    def display_name(self) -> str:
        return "Zener Diode"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """Zener diode symbol (with bent cathode bar)."""
        return [
            ('line', -30, 0, -10, 0),
            ('polygon', [(-10, -12), (-10, 12), (10, 0)]),
            ('line', 10, -12, 10, 12),
            ('line', 10, -12, 5, -12),  # Bent top
            ('line', 10, 12, 15, 12),   # Bent bottom
            ('line', 10, 0, 30, 0),
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("A", PinType.BIDIRECTIONAL, -30, 0),
            Pin("K", PinType.BIDIRECTIONAL, 30, 0),
        ]
    
    def _init_properties(self):
        self._properties = {
            'model': ComponentProperty(
                name='model',
                display_name='Model',
                property_type=PropertyType.STRING,
                default_value='BZX79C5V1',
                description='SPICE zener model'
            ),
            'vz': ComponentProperty(
                name='vz',
                display_name='Zener Voltage',
                property_type=PropertyType.FLOAT,
                default_value=5.1,
                unit='V',
                min_value=0.0,
                description='Zener breakdown voltage'
            ),
            'iz': ComponentProperty(
                name='iz',
                display_name='Test Current',
                property_type=PropertyType.FLOAT,
                default_value=5e-3,
                unit='A',
                min_value=0.0,
                description='Zener test current'
            ),
            'zz': ComponentProperty(
                name='zz',
                display_name='Zener Impedance',
                property_type=PropertyType.FLOAT,
                default_value=10.0,
                unit='Ω',
                min_value=0.0,
                description='Dynamic impedance at Iz'
            ),
            'power_rating': ComponentProperty(
                name='power_rating',
                display_name='Power Rating',
                property_type=PropertyType.FLOAT,
                default_value=0.5,
                unit='W',
                min_value=0.0,
                description='Maximum power dissipation'
            ),
        }
    
    def get_spice_model(self) -> str:
        model = self._properties['model'].value
        
        a = self._pins[0].connected_net or '0'
        k = self._pins[1].connected_net or '0'
        
        return f"{self.reference} {a} {k} {model}"


class LED(Component):
    """Light Emitting Diode."""
    
    def __init__(self):
        self._ref_prefix = "D"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.DIODE
    
    @property
    def display_name(self) -> str:
        return "LED"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """LED symbol (diode with light arrows)."""
        return [
            ('line', -30, 0, -10, 0),
            ('polygon', [(-10, -12), (-10, 12), (10, 0)]),
            ('line', 10, -12, 10, 12),
            ('line', 10, 0, 30, 0),
            # Light arrows
            ('line', 0, -15, 8, -25),
            ('polygon', [(8, -25), (5, -20), (10, -22)]),
            ('line', 8, -15, 16, -25),
            ('polygon', [(16, -25), (13, -20), (18, -22)]),
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("A", PinType.BIDIRECTIONAL, -30, 0),
            Pin("K", PinType.BIDIRECTIONAL, 30, 0),
        ]
    
    def _init_properties(self):
        self._properties = {
            'model': ComponentProperty(
                name='model',
                display_name='Model',
                property_type=PropertyType.STRING,
                default_value='LED_RED',
                description='SPICE LED model'
            ),
            'color': ComponentProperty(
                name='color',
                display_name='Color',
                property_type=PropertyType.ENUM,
                default_value='Red',
                enum_values=['Red', 'Green', 'Blue', 'Yellow', 'Orange', 'White', 'IR', 'UV'],
                description='LED color'
            ),
            'vf': ComponentProperty(
                name='vf',
                display_name='Forward Voltage',
                property_type=PropertyType.FLOAT,
                default_value=2.0,
                unit='V',
                min_value=0.0,
                description='Forward voltage drop'
            ),
            'if_max': ComponentProperty(
                name='if_max',
                display_name='Max Forward Current',
                property_type=PropertyType.FLOAT,
                default_value=20e-3,
                unit='A',
                min_value=0.0,
                description='Maximum forward current'
            ),
            'luminous_intensity': ComponentProperty(
                name='luminous_intensity',
                display_name='Luminous Intensity',
                property_type=PropertyType.FLOAT,
                default_value=10.0,
                unit='mcd',
                min_value=0.0,
                description='Luminous intensity at IF'
            ),
        }
    
    def get_spice_model(self) -> str:
        model = self._properties['model'].value
        
        a = self._pins[0].connected_net or '0'
        k = self._pins[1].connected_net or '0'
        
        return f"{self.reference} {a} {k} {model}"


class SchottkyDiode(Component):
    """Schottky Barrier Diode."""
    
    def __init__(self):
        self._ref_prefix = "D"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.DIODE
    
    @property
    def display_name(self) -> str:
        return "Schottky Diode"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """Schottky diode symbol (with S-shaped cathode bar)."""
        return [
            ('line', -30, 0, -10, 0),
            ('polygon', [(-10, -12), (-10, 12), (10, 0)]),
            ('line', 5, -12, 10, -12),
            ('line', 10, -12, 10, 12),
            ('line', 10, 12, 15, 12),
            ('line', 5, -12, 5, -8),
            ('line', 15, 12, 15, 8),
            ('line', 10, 0, 30, 0),
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("A", PinType.BIDIRECTIONAL, -30, 0),
            Pin("K", PinType.BIDIRECTIONAL, 30, 0),
        ]
    
    def _init_properties(self):
        self._properties = {
            'model': ComponentProperty(
                name='model',
                display_name='Model',
                property_type=PropertyType.STRING,
                default_value='1N5819',
                description='SPICE model'
            ),
            'vf': ComponentProperty(
                name='vf',
                display_name='Forward Voltage',
                property_type=PropertyType.FLOAT,
                default_value=0.3,
                unit='V',
                min_value=0.0,
                description='Forward voltage drop'
            ),
            'vrrm': ComponentProperty(
                name='vrrm',
                display_name='Max Reverse Voltage',
                property_type=PropertyType.FLOAT,
                default_value=40.0,
                unit='V',
                min_value=0.0,
                description='Maximum reverse voltage'
            ),
            'if_avg': ComponentProperty(
                name='if_avg',
                display_name='Avg Forward Current',
                property_type=PropertyType.FLOAT,
                default_value=1.0,
                unit='A',
                min_value=0.0,
                description='Average forward current'
            ),
        }
    
    def get_spice_model(self) -> str:
        model = self._properties['model'].value
        
        a = self._pins[0].connected_net or '0'
        k = self._pins[1].connected_net or '0'
        
        return f"{self.reference} {a} {k} {model}"
