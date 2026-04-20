"""
Transistor components: NMOS, PMOS, NPN, PNP.
"""

from simulator.components.base import (
    Component, ComponentType, Pin, PinType,
    ComponentProperty, PropertyType
)


class NMOS(Component):
    """N-channel MOSFET transistor."""
    
    def __init__(self):
        self._ref_prefix = "M"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.TRANSISTOR
    
    @property
    def display_name(self) -> str:
        return "NMOS Transistor"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """NMOS transistor symbol."""
        return [
            # Gate
            ('line', -30, 0, -15, 0),
            ('line', -15, -20, -15, 20),
            # Channel
            ('line', -10, -20, -10, -10),
            ('line', -10, -5, -10, 5),
            ('line', -10, 10, -10, 20),
            # Drain
            ('line', -10, -15, 15, -15),
            ('line', 15, -15, 15, -30),
            # Source
            ('line', -10, 15, 15, 15),
            ('line', 15, 15, 15, 30),
            # Arrow (pointing inward for NMOS)
            ('line', -10, 0, 5, 0),
            ('polygon', [(5, 0), (-2, -5), (-2, 5)]),
            # Bulk connection line
            ('line', 15, 0, 30, 0),
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("G", PinType.INPUT, -30, 0),       # Gate
            Pin("D", PinType.BIDIRECTIONAL, 15, -30),  # Drain
            Pin("S", PinType.BIDIRECTIONAL, 15, 30),   # Source
            Pin("B", PinType.BIDIRECTIONAL, 30, 0),    # Bulk/Body
        ]
    
    def _init_properties(self):
        self._properties = {
            'model': ComponentProperty(
                name='model',
                display_name='Model',
                property_type=PropertyType.STRING,
                default_value='NMOS_DEFAULT',
                description='SPICE model name'
            ),
            'w': ComponentProperty(
                name='w',
                display_name='Width',
                property_type=PropertyType.FLOAT,
                default_value=1e-6,
                unit='m',
                min_value=1e-9,
                description='Channel width'
            ),
            'l': ComponentProperty(
                name='l',
                display_name='Length',
                property_type=PropertyType.FLOAT,
                default_value=100e-9,
                unit='m',
                min_value=1e-9,
                description='Channel length'
            ),
            'vth0': ComponentProperty(
                name='vth0',
                display_name='Threshold Voltage',
                property_type=PropertyType.FLOAT,
                default_value=0.4,
                unit='V',
                description='Threshold voltage'
            ),
            'kp': ComponentProperty(
                name='kp',
                display_name='Transconductance',
                property_type=PropertyType.FLOAT,
                default_value=120e-6,
                unit='A/V²',
                min_value=0.0,
                description='Transconductance parameter'
            ),
            'lambda': ComponentProperty(
                name='lambda',
                display_name='Lambda',
                property_type=PropertyType.FLOAT,
                default_value=0.01,
                unit='1/V',
                min_value=0.0,
                description='Channel length modulation'
            ),
            'multiplier': ComponentProperty(
                name='multiplier',
                display_name='Multiplier',
                property_type=PropertyType.INTEGER,
                default_value=1,
                min_value=1,
                description='Number of parallel devices'
            ),
        }
    
    def get_spice_model(self) -> str:
        model = self._properties['model'].value
        w = self._properties['w'].value
        l = self._properties['l'].value
        m = self._properties['multiplier'].value
        
        d = self._pins[1].connected_net or '0'
        g = self._pins[0].connected_net or '0'
        s = self._pins[2].connected_net or '0'
        b = self._pins[3].connected_net or s
        
        return f"{self.reference} {d} {g} {s} {b} {model} W={w} L={l} M={m}"


class PMOS(Component):
    """P-channel MOSFET transistor."""
    
    def __init__(self):
        self._ref_prefix = "M"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.TRANSISTOR
    
    @property
    def display_name(self) -> str:
        return "PMOS Transistor"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """PMOS transistor symbol with bubble on gate."""
        return [
            # Gate with bubble
            ('line', -30, 0, -20, 0),
            ('circle', -17, 0, 3),
            ('line', -14, -20, -14, 20),
            # Channel
            ('line', -10, -20, -10, -10),
            ('line', -10, -5, -10, 5),
            ('line', -10, 10, -10, 20),
            # Drain
            ('line', -10, -15, 15, -15),
            ('line', 15, -15, 15, -30),
            # Source
            ('line', -10, 15, 15, 15),
            ('line', 15, 15, 15, 30),
            # Arrow (pointing outward for PMOS)
            ('line', -10, 0, 5, 0),
            ('polygon', [(-10, 0), (-3, -5), (-3, 5)]),
            # Bulk connection line
            ('line', 15, 0, 30, 0),
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("G", PinType.INPUT, -30, 0),       # Gate
            Pin("D", PinType.BIDIRECTIONAL, 15, -30),  # Drain
            Pin("S", PinType.BIDIRECTIONAL, 15, 30),   # Source
            Pin("B", PinType.BIDIRECTIONAL, 30, 0),    # Bulk/Body
        ]
    
    def _init_properties(self):
        self._properties = {
            'model': ComponentProperty(
                name='model',
                display_name='Model',
                property_type=PropertyType.STRING,
                default_value='PMOS_DEFAULT',
                description='SPICE model name'
            ),
            'w': ComponentProperty(
                name='w',
                display_name='Width',
                property_type=PropertyType.FLOAT,
                default_value=2e-6,
                unit='m',
                min_value=1e-9,
                description='Channel width'
            ),
            'l': ComponentProperty(
                name='l',
                display_name='Length',
                property_type=PropertyType.FLOAT,
                default_value=100e-9,
                unit='m',
                min_value=1e-9,
                description='Channel length'
            ),
            'vth0': ComponentProperty(
                name='vth0',
                display_name='Threshold Voltage',
                property_type=PropertyType.FLOAT,
                default_value=-0.4,
                unit='V',
                description='Threshold voltage'
            ),
            'kp': ComponentProperty(
                name='kp',
                display_name='Transconductance',
                property_type=PropertyType.FLOAT,
                default_value=40e-6,
                unit='A/V²',
                min_value=0.0,
                description='Transconductance parameter'
            ),
            'lambda': ComponentProperty(
                name='lambda',
                display_name='Lambda',
                property_type=PropertyType.FLOAT,
                default_value=0.01,
                unit='1/V',
                min_value=0.0,
                description='Channel length modulation'
            ),
            'multiplier': ComponentProperty(
                name='multiplier',
                display_name='Multiplier',
                property_type=PropertyType.INTEGER,
                default_value=1,
                min_value=1,
                description='Number of parallel devices'
            ),
        }
    
    def get_spice_model(self) -> str:
        model = self._properties['model'].value
        w = self._properties['w'].value
        l = self._properties['l'].value
        m = self._properties['multiplier'].value
        
        d = self._pins[1].connected_net or '0'
        g = self._pins[0].connected_net or '0'
        s = self._pins[2].connected_net or '0'
        b = self._pins[3].connected_net or s
        
        return f"{self.reference} {d} {g} {s} {b} {model} W={w} L={l} M={m}"


class NPN(Component):
    """NPN Bipolar Junction Transistor."""
    
    def __init__(self):
        self._ref_prefix = "Q"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.TRANSISTOR
    
    @property
    def display_name(self) -> str:
        return "NPN Transistor"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """NPN BJT symbol."""
        return [
            # Base
            ('line', -30, 0, -10, 0),
            ('line', -10, -15, -10, 15),
            # Collector
            ('line', -10, -10, 15, -25),
            ('line', 15, -25, 15, -30),
            # Emitter with arrow
            ('line', -10, 10, 15, 25),
            ('line', 15, 25, 15, 30),
            ('polygon', [(10, 22), (15, 25), (8, 18)]),  # Arrow on emitter
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("B", PinType.INPUT, -30, 0),      # Base
            Pin("C", PinType.BIDIRECTIONAL, 15, -30),  # Collector
            Pin("E", PinType.BIDIRECTIONAL, 15, 30),   # Emitter
        ]
    
    def _init_properties(self):
        self._properties = {
            'model': ComponentProperty(
                name='model',
                display_name='Model',
                property_type=PropertyType.STRING,
                default_value='NPN_DEFAULT',
                description='SPICE model name'
            ),
            'bf': ComponentProperty(
                name='bf',
                display_name='Forward Beta',
                property_type=PropertyType.FLOAT,
                default_value=100.0,
                min_value=1.0,
                description='Forward current gain'
            ),
            'is': ComponentProperty(
                name='is',
                display_name='Saturation Current',
                property_type=PropertyType.FLOAT,
                default_value=1e-14,
                unit='A',
                min_value=0.0,
                description='Saturation current'
            ),
            'vaf': ComponentProperty(
                name='vaf',
                display_name='Early Voltage',
                property_type=PropertyType.FLOAT,
                default_value=100.0,
                unit='V',
                min_value=0.0,
                description='Forward Early voltage'
            ),
            'area': ComponentProperty(
                name='area',
                display_name='Area Factor',
                property_type=PropertyType.FLOAT,
                default_value=1.0,
                min_value=0.0,
                description='Area multiplier'
            ),
        }
    
    def get_spice_model(self) -> str:
        model = self._properties['model'].value
        area = self._properties['area'].value
        
        c = self._pins[1].connected_net or '0'
        b = self._pins[0].connected_net or '0'
        e = self._pins[2].connected_net or '0'
        
        return f"{self.reference} {c} {b} {e} {model} AREA={area}"


class PNP(Component):
    """PNP Bipolar Junction Transistor."""
    
    def __init__(self):
        self._ref_prefix = "Q"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.TRANSISTOR
    
    @property
    def display_name(self) -> str:
        return "PNP Transistor"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """PNP BJT symbol with arrow on emitter pointing inward."""
        return [
            # Base
            ('line', -30, 0, -10, 0),
            ('line', -10, -15, -10, 15),
            # Collector
            ('line', -10, -10, 15, -25),
            ('line', 15, -25, 15, -30),
            # Emitter with arrow pointing inward
            ('line', -10, 10, 15, 25),
            ('line', 15, 25, 15, 30),
            ('polygon', [(-5, 12), (-10, 10), (-3, 16)]),  # Arrow pointing in
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("B", PinType.INPUT, -30, 0),      # Base
            Pin("C", PinType.BIDIRECTIONAL, 15, -30),  # Collector
            Pin("E", PinType.BIDIRECTIONAL, 15, 30),   # Emitter
        ]
    
    def _init_properties(self):
        self._properties = {
            'model': ComponentProperty(
                name='model',
                display_name='Model',
                property_type=PropertyType.STRING,
                default_value='PNP_DEFAULT',
                description='SPICE model name'
            ),
            'bf': ComponentProperty(
                name='bf',
                display_name='Forward Beta',
                property_type=PropertyType.FLOAT,
                default_value=100.0,
                min_value=1.0,
                description='Forward current gain'
            ),
            'is': ComponentProperty(
                name='is',
                display_name='Saturation Current',
                property_type=PropertyType.FLOAT,
                default_value=1e-14,
                unit='A',
                min_value=0.0,
                description='Saturation current'
            ),
            'vaf': ComponentProperty(
                name='vaf',
                display_name='Early Voltage',
                property_type=PropertyType.FLOAT,
                default_value=100.0,
                unit='V',
                min_value=0.0,
                description='Forward Early voltage'
            ),
            'area': ComponentProperty(
                name='area',
                display_name='Area Factor',
                property_type=PropertyType.FLOAT,
                default_value=1.0,
                min_value=0.0,
                description='Area multiplier'
            ),
        }
    
    def get_spice_model(self) -> str:
        model = self._properties['model'].value
        area = self._properties['area'].value
        
        c = self._pins[1].connected_net or '0'
        b = self._pins[0].connected_net or '0'
        e = self._pins[2].connected_net or '0'
        
        return f"{self.reference} {c} {b} {e} {model} AREA={area}"
