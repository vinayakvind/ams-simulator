"""
Amplifier components: Op-Amp, Comparator.
"""

from simulator.components.base import (
    Component, ComponentType, Pin, PinType,
    ComponentProperty, PropertyType
)


class OpAmp(Component):
    """Operational Amplifier."""
    
    def __init__(self):
        self._ref_prefix = "U"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.AMPLIFIER
    
    @property
    def display_name(self) -> str:
        return "Op-Amp"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """Op-Amp symbol (triangle)."""
        return [
            ('polygon', [(-30, -35), (-30, 35), (30, 0)]),
            ('text', -20, -15, '+', 12),
            ('text', -20, 15, '-', 12),
            ('line', -45, -20, -30, -20),   # Non-inverting input
            ('line', -45, 20, -30, 20),     # Inverting input
            ('line', 30, 0, 45, 0),          # Output
            ('line', 0, -35, 0, -45),        # V+
            ('line', 0, 35, 0, 45),          # V-
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("IN+", PinType.ANALOG, -45, -20),    # Non-inverting input
            Pin("IN-", PinType.ANALOG, -45, 20),     # Inverting input
            Pin("OUT", PinType.ANALOG, 45, 0),       # Output
            Pin("V+", PinType.POWER, 0, -45),        # Positive supply
            Pin("V-", PinType.POWER, 0, 45),         # Negative supply
        ]
    
    def _init_properties(self):
        self._properties = {
            'model': ComponentProperty(
                name='model',
                display_name='Model',
                property_type=PropertyType.STRING,
                default_value='OPAMP_IDEAL',
                description='SPICE model name'
            ),
            'gain': ComponentProperty(
                name='gain',
                display_name='Open-Loop Gain',
                property_type=PropertyType.FLOAT,
                default_value=100000.0,
                min_value=1.0,
                description='Open-loop voltage gain'
            ),
            'gbw': ComponentProperty(
                name='gbw',
                display_name='GBW',
                property_type=PropertyType.FLOAT,
                default_value=1e6,
                unit='Hz',
                min_value=0.0,
                description='Gain-Bandwidth Product'
            ),
            'slew_rate': ComponentProperty(
                name='slew_rate',
                display_name='Slew Rate',
                property_type=PropertyType.FLOAT,
                default_value=1e6,
                unit='V/s',
                min_value=0.0,
                description='Slew rate'
            ),
            'input_offset': ComponentProperty(
                name='input_offset',
                display_name='Input Offset',
                property_type=PropertyType.FLOAT,
                default_value=0.0,
                unit='V',
                description='Input offset voltage'
            ),
            'input_bias': ComponentProperty(
                name='input_bias',
                display_name='Input Bias Current',
                property_type=PropertyType.FLOAT,
                default_value=0.0,
                unit='A',
                description='Input bias current'
            ),
            'input_impedance': ComponentProperty(
                name='input_impedance',
                display_name='Input Impedance',
                property_type=PropertyType.FLOAT,
                default_value=1e12,
                unit='Ω',
                min_value=0.0,
                description='Input impedance'
            ),
            'output_impedance': ComponentProperty(
                name='output_impedance',
                display_name='Output Impedance',
                property_type=PropertyType.FLOAT,
                default_value=75.0,
                unit='Ω',
                min_value=0.0,
                description='Output impedance'
            ),
        }
    
    def get_spice_model(self) -> str:
        model = self._properties['model'].value
        
        inp = self._pins[0].connected_net or '0'
        inn = self._pins[1].connected_net or '0'
        out = self._pins[2].connected_net or '0'
        vp = self._pins[3].connected_net or 'VDD'
        vn = self._pins[4].connected_net or 'VSS'
        
        return f"X{self.reference} {inp} {inn} {vp} {vn} {out} {model}"


class Comparator(Component):
    """Voltage Comparator."""
    
    def __init__(self):
        self._ref_prefix = "U"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.AMPLIFIER
    
    @property
    def display_name(self) -> str:
        return "Comparator"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """Comparator symbol (triangle with hysteresis symbol)."""
        return [
            ('polygon', [(-30, -35), (-30, 35), (30, 0)]),
            ('text', -20, -15, '+', 12),
            ('text', -20, 15, '-', 12),
            # Hysteresis symbol inside
            ('line', -5, -5, 0, -5),
            ('line', 0, -5, 0, 5),
            ('line', 0, 5, 5, 5),
            ('line', -45, -20, -30, -20),
            ('line', -45, 20, -30, 20),
            ('line', 30, 0, 45, 0),
            ('line', 0, -35, 0, -45),
            ('line', 0, 35, 0, 45),
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("IN+", PinType.ANALOG, -45, -20),
            Pin("IN-", PinType.ANALOG, -45, 20),
            Pin("OUT", PinType.DIGITAL, 45, 0),
            Pin("V+", PinType.POWER, 0, -45),
            Pin("V-", PinType.POWER, 0, 45),
        ]
    
    def _init_properties(self):
        self._properties = {
            'model': ComponentProperty(
                name='model',
                display_name='Model',
                property_type=PropertyType.STRING,
                default_value='COMP_IDEAL',
                description='SPICE model name'
            ),
            'hysteresis': ComponentProperty(
                name='hysteresis',
                display_name='Hysteresis',
                property_type=PropertyType.FLOAT,
                default_value=0.0,
                unit='V',
                min_value=0.0,
                description='Hysteresis voltage'
            ),
            'propagation_delay': ComponentProperty(
                name='propagation_delay',
                display_name='Propagation Delay',
                property_type=PropertyType.FLOAT,
                default_value=100e-9,
                unit='s',
                min_value=0.0,
                description='Propagation delay'
            ),
            'output_high': ComponentProperty(
                name='output_high',
                display_name='Output High',
                property_type=PropertyType.FLOAT,
                default_value=5.0,
                unit='V',
                description='Output high voltage'
            ),
            'output_low': ComponentProperty(
                name='output_low',
                display_name='Output Low',
                property_type=PropertyType.FLOAT,
                default_value=0.0,
                unit='V',
                description='Output low voltage'
            ),
        }
    
    def get_spice_model(self) -> str:
        model = self._properties['model'].value
        
        inp = self._pins[0].connected_net or '0'
        inn = self._pins[1].connected_net or '0'
        out = self._pins[2].connected_net or '0'
        vp = self._pins[3].connected_net or 'VDD'
        vn = self._pins[4].connected_net or 'VSS'
        
        return f"X{self.reference} {inp} {inn} {vp} {vn} {out} {model}"


class InstrumentationAmplifier(Component):
    """Instrumentation Amplifier."""
    
    def __init__(self):
        self._ref_prefix = "U"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.AMPLIFIER
    
    @property
    def display_name(self) -> str:
        return "Instrumentation Amp"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """Instrumentation amplifier symbol."""
        return [
            ('polygon', [(-30, -40), (-30, 40), (35, 0)]),
            ('text', -20, -20, '+', 10),
            ('text', -20, 20, '-', 10),
            ('text', -5, 0, 'INA', 8),
            ('line', -45, -25, -30, -25),
            ('line', -45, 25, -30, 25),
            ('line', 35, 0, 50, 0),
            ('line', 0, -40, 0, -50),
            ('line', 0, 40, 0, 50),
            ('line', 20, 40, 20, 50),  # Reference pin
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("IN+", PinType.ANALOG, -45, -25),
            Pin("IN-", PinType.ANALOG, -45, 25),
            Pin("OUT", PinType.ANALOG, 50, 0),
            Pin("V+", PinType.POWER, 0, -50),
            Pin("V-", PinType.POWER, 0, 50),
            Pin("REF", PinType.ANALOG, 20, 50),
        ]
    
    def _init_properties(self):
        self._properties = {
            'model': ComponentProperty(
                name='model',
                display_name='Model',
                property_type=PropertyType.STRING,
                default_value='INA_IDEAL',
                description='SPICE model name'
            ),
            'gain': ComponentProperty(
                name='gain',
                display_name='Gain',
                property_type=PropertyType.FLOAT,
                default_value=100.0,
                min_value=1.0,
                description='Voltage gain'
            ),
            'cmrr': ComponentProperty(
                name='cmrr',
                display_name='CMRR',
                property_type=PropertyType.FLOAT,
                default_value=100.0,
                unit='dB',
                description='Common Mode Rejection Ratio'
            ),
        }
    
    def get_spice_model(self) -> str:
        model = self._properties['model'].value
        
        inp = self._pins[0].connected_net or '0'
        inn = self._pins[1].connected_net or '0'
        out = self._pins[2].connected_net or '0'
        vp = self._pins[3].connected_net or 'VDD'
        vn = self._pins[4].connected_net or 'VSS'
        ref = self._pins[5].connected_net or '0'
        
        return f"X{self.reference} {inp} {inn} {vp} {vn} {ref} {out} {model}"
