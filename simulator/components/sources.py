"""
Voltage and current sources, and probes.
"""

from simulator.components.base import (
    Component, ComponentType, Pin, PinType,
    ComponentProperty, PropertyType
)


class VoltageSource(Component):
    """DC Voltage Source."""
    
    def __init__(self):
        self._ref_prefix = "V"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.SOURCE
    
    @property
    def display_name(self) -> str:
        return "DC Voltage Source"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """Voltage source symbol (circle with + and -)."""
        return [
            ('line', 0, -30, 0, -15),
            ('circle', 0, 0, 15),
            ('text', 0, -7, '+', 10),
            ('text', 0, 7, '-', 10),
            ('line', 0, 15, 0, 30),
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("+", PinType.BIDIRECTIONAL, 0, -30),
            Pin("-", PinType.BIDIRECTIONAL, 0, 30),
        ]
    
    def _init_properties(self):
        self._properties = {
            'voltage': ComponentProperty(
                name='voltage',
                display_name='Voltage',
                property_type=PropertyType.FLOAT,
                default_value=5.0,
                unit='V',
                description='DC voltage value'
            ),
            'ac_magnitude': ComponentProperty(
                name='ac_magnitude',
                display_name='AC Magnitude',
                property_type=PropertyType.FLOAT,
                default_value=1.0,
                unit='V',
                min_value=0.0,
                description='AC analysis magnitude'
            ),
            'ac_phase': ComponentProperty(
                name='ac_phase',
                display_name='AC Phase',
                property_type=PropertyType.FLOAT,
                default_value=0.0,
                unit='°',
                description='AC analysis phase'
            ),
        }
    
    def get_spice_model(self) -> str:
        v = self._properties['voltage'].value
        ac_mag = self._properties['ac_magnitude'].value
        ac_phase = self._properties['ac_phase'].value
        
        p_pos = self._pins[0].connected_net or '0'
        p_neg = self._pins[1].connected_net or '0'
        
        return f"{self.reference} {p_pos} {p_neg} DC {v} AC {ac_mag} {ac_phase}"


class CurrentSource(Component):
    """DC Current Source."""
    
    def __init__(self):
        self._ref_prefix = "I"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.SOURCE
    
    @property
    def display_name(self) -> str:
        return "DC Current Source"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """Current source symbol (circle with arrow)."""
        return [
            ('line', 0, -30, 0, -15),
            ('circle', 0, 0, 15),
            ('line', 0, -10, 0, 10),
            ('polygon', [(0, -10), (-5, -3), (5, -3)]),  # Arrow pointing up
            ('line', 0, 15, 0, 30),
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("+", PinType.BIDIRECTIONAL, 0, -30),
            Pin("-", PinType.BIDIRECTIONAL, 0, 30),
        ]
    
    def _init_properties(self):
        self._properties = {
            'current': ComponentProperty(
                name='current',
                display_name='Current',
                property_type=PropertyType.FLOAT,
                default_value=1e-3,
                unit='A',
                description='DC current value'
            ),
            'ac_magnitude': ComponentProperty(
                name='ac_magnitude',
                display_name='AC Magnitude',
                property_type=PropertyType.FLOAT,
                default_value=1e-3,
                unit='A',
                min_value=0.0,
                description='AC analysis magnitude'
            ),
            'ac_phase': ComponentProperty(
                name='ac_phase',
                display_name='AC Phase',
                property_type=PropertyType.FLOAT,
                default_value=0.0,
                unit='°',
                description='AC analysis phase'
            ),
        }
    
    def get_spice_model(self) -> str:
        i = self._properties['current'].value
        ac_mag = self._properties['ac_magnitude'].value
        ac_phase = self._properties['ac_phase'].value
        
        p_pos = self._pins[0].connected_net or '0'
        p_neg = self._pins[1].connected_net or '0'
        
        return f"{self.reference} {p_pos} {p_neg} DC {i} AC {ac_mag} {ac_phase}"


class PulseSource(Component):
    """Pulse Voltage Source for digital and transient simulation."""
    
    def __init__(self):
        self._ref_prefix = "V"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.SOURCE
    
    @property
    def display_name(self) -> str:
        return "Pulse Source"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """Pulse source symbol."""
        return [
            ('line', 0, -30, 0, -15),
            ('circle', 0, 0, 15),
            # Pulse waveform inside
            ('line', -8, 5, -8, -5),
            ('line', -8, -5, -2, -5),
            ('line', -2, -5, -2, 5),
            ('line', -2, 5, 4, 5),
            ('line', 4, 5, 4, -5),
            ('line', 4, -5, 8, -5),
            ('line', 0, 15, 0, 30),
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("+", PinType.BIDIRECTIONAL, 0, -30),
            Pin("-", PinType.BIDIRECTIONAL, 0, 30),
        ]
    
    def _init_properties(self):
        self._properties = {
            'v_low': ComponentProperty(
                name='v_low',
                display_name='Low Voltage',
                property_type=PropertyType.FLOAT,
                default_value=0.0,
                unit='V',
                description='Low voltage level'
            ),
            'v_high': ComponentProperty(
                name='v_high',
                display_name='High Voltage',
                property_type=PropertyType.FLOAT,
                default_value=5.0,
                unit='V',
                description='High voltage level'
            ),
            'delay': ComponentProperty(
                name='delay',
                display_name='Delay',
                property_type=PropertyType.FLOAT,
                default_value=0.0,
                unit='s',
                min_value=0.0,
                description='Initial delay'
            ),
            'rise_time': ComponentProperty(
                name='rise_time',
                display_name='Rise Time',
                property_type=PropertyType.FLOAT,
                default_value=1e-9,
                unit='s',
                min_value=0.0,
                description='Rise time'
            ),
            'fall_time': ComponentProperty(
                name='fall_time',
                display_name='Fall Time',
                property_type=PropertyType.FLOAT,
                default_value=1e-9,
                unit='s',
                min_value=0.0,
                description='Fall time'
            ),
            'pulse_width': ComponentProperty(
                name='pulse_width',
                display_name='Pulse Width',
                property_type=PropertyType.FLOAT,
                default_value=50e-9,
                unit='s',
                min_value=0.0,
                description='Pulse width'
            ),
            'period': ComponentProperty(
                name='period',
                display_name='Period',
                property_type=PropertyType.FLOAT,
                default_value=100e-9,
                unit='s',
                min_value=0.0,
                description='Pulse period'
            ),
        }
    
    def get_spice_model(self) -> str:
        v_low = self._properties['v_low'].value
        v_high = self._properties['v_high'].value
        delay = self._properties['delay'].value
        tr = self._properties['rise_time'].value
        tf = self._properties['fall_time'].value
        pw = self._properties['pulse_width'].value
        per = self._properties['period'].value
        
        p_pos = self._pins[0].connected_net or '0'
        p_neg = self._pins[1].connected_net or '0'
        
        return f"{self.reference} {p_pos} {p_neg} PULSE({v_low} {v_high} {delay} {tr} {tf} {pw} {per})"


class SineSource(Component):
    """Sinusoidal Voltage Source."""
    
    def __init__(self):
        self._ref_prefix = "V"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.SOURCE
    
    @property
    def display_name(self) -> str:
        return "Sine Source"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """Sine source symbol."""
        return [
            ('line', 0, -30, 0, -15),
            ('circle', 0, 0, 15),
            # Sine wave inside (simplified)
            ('arc', -5, 0, 5, 0, 180),
            ('arc', 5, 0, 5, 180, 360),
            ('line', 0, 15, 0, 30),
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("+", PinType.BIDIRECTIONAL, 0, -30),
            Pin("-", PinType.BIDIRECTIONAL, 0, 30),
        ]
    
    def _init_properties(self):
        self._properties = {
            'offset': ComponentProperty(
                name='offset',
                display_name='DC Offset',
                property_type=PropertyType.FLOAT,
                default_value=0.0,
                unit='V',
                description='DC offset voltage'
            ),
            'amplitude': ComponentProperty(
                name='amplitude',
                display_name='Amplitude',
                property_type=PropertyType.FLOAT,
                default_value=1.0,
                unit='V',
                min_value=0.0,
                description='Peak amplitude'
            ),
            'frequency': ComponentProperty(
                name='frequency',
                display_name='Frequency',
                property_type=PropertyType.FLOAT,
                default_value=1e6,
                unit='Hz',
                min_value=0.0,
                description='Frequency'
            ),
            'delay': ComponentProperty(
                name='delay',
                display_name='Delay',
                property_type=PropertyType.FLOAT,
                default_value=0.0,
                unit='s',
                min_value=0.0,
                description='Time delay'
            ),
            'damping': ComponentProperty(
                name='damping',
                display_name='Damping Factor',
                property_type=PropertyType.FLOAT,
                default_value=0.0,
                unit='1/s',
                min_value=0.0,
                description='Damping factor'
            ),
            'phase': ComponentProperty(
                name='phase',
                display_name='Phase',
                property_type=PropertyType.FLOAT,
                default_value=0.0,
                unit='°',
                description='Phase offset'
            ),
        }
    
    def get_spice_model(self) -> str:
        vo = self._properties['offset'].value
        va = self._properties['amplitude'].value
        freq = self._properties['frequency'].value
        td = self._properties['delay'].value
        theta = self._properties['damping'].value
        phase = self._properties['phase'].value
        
        p_pos = self._pins[0].connected_net or '0'
        p_neg = self._pins[1].connected_net or '0'
        
        return f"{self.reference} {p_pos} {p_neg} SIN({vo} {va} {freq} {td} {theta} {phase})"


class PWLSource(Component):
    """Piecewise Linear Voltage Source."""
    
    def __init__(self):
        self._ref_prefix = "V"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.SOURCE
    
    @property
    def display_name(self) -> str:
        return "PWL Source"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """PWL source symbol."""
        return [
            ('line', 0, -30, 0, -15),
            ('circle', 0, 0, 15),
            # PWL line inside
            ('line', -10, 5, -5, 5),
            ('line', -5, 5, -3, -5),
            ('line', -3, -5, 3, -5),
            ('line', 3, -5, 5, 5),
            ('line', 5, 5, 10, 5),
            ('line', 0, 15, 0, 30),
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("+", PinType.BIDIRECTIONAL, 0, -30),
            Pin("-", PinType.BIDIRECTIONAL, 0, 30),
        ]
    
    def _init_properties(self):
        self._properties = {
            'pwl_data': ComponentProperty(
                name='pwl_data',
                display_name='PWL Data',
                property_type=PropertyType.STRING,
                default_value='0 0 1n 5 10n 5 11n 0',
                description='Time-Voltage pairs (t1 v1 t2 v2 ...)'
            ),
            'repeat': ComponentProperty(
                name='repeat',
                display_name='Repeat',
                property_type=PropertyType.BOOLEAN,
                default_value=False,
                description='Repeat the PWL pattern'
            ),
        }
    
    def get_spice_model(self) -> str:
        pwl_data = self._properties['pwl_data'].value
        
        p_pos = self._pins[0].connected_net or '0'
        p_neg = self._pins[1].connected_net or '0'
        
        return f"{self.reference} {p_pos} {p_neg} PWL({pwl_data})"


class VoltageProbe(Component):
    """Voltage measurement probe."""
    
    def __init__(self):
        self._ref_prefix = "VP"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.PROBE
    
    @property
    def display_name(self) -> str:
        return "Voltage Probe"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """Voltage probe symbol."""
        return [
            ('line', 0, 20, 0, 5),
            ('polygon', [(0, 5), (-5, 15), (5, 15)]),
            ('text', 0, -5, 'V', 12),
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("+", PinType.INPUT, 0, 20),
        ]
    
    def _init_properties(self):
        self._properties = {
            'label': ComponentProperty(
                name='label',
                display_name='Label',
                property_type=PropertyType.STRING,
                default_value='',
                description='Probe label for waveform display'
            ),
        }
    
    def get_spice_model(self) -> str:
        node = self._pins[0].connected_net or '0'
        return f".PROBE V({node})"


class CurrentProbe(Component):
    """Current measurement probe (inserted in series)."""
    
    def __init__(self):
        self._ref_prefix = "IP"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.PROBE
    
    @property
    def display_name(self) -> str:
        return "Current Probe"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """Current probe symbol."""
        return [
            ('line', 0, -20, 0, 20),
            ('circle', 0, 0, 8),
            ('text', 0, 0, 'A', 10),
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("+", PinType.BIDIRECTIONAL, 0, -20),
            Pin("-", PinType.BIDIRECTIONAL, 0, 20),
        ]
    
    def _init_properties(self):
        self._properties = {
            'label': ComponentProperty(
                name='label',
                display_name='Label',
                property_type=PropertyType.STRING,
                default_value='',
                description='Probe label for waveform display'
            ),
        }
    
    def get_spice_model(self) -> str:
        # Current probe is implemented as 0V voltage source
        p_pos = self._pins[0].connected_net or '0'
        p_neg = self._pins[1].connected_net or '0'
        return f"V{self.reference} {p_pos} {p_neg} 0"


class Ground(Component):
    """Ground/reference node."""
    
    def __init__(self):
        self._ref_prefix = "GND"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.SOURCE
    
    @property
    def display_name(self) -> str:
        return "Ground"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """Ground symbol."""
        return [
            ('line', 0, 0, 0, 10),
            ('line', -15, 10, 15, 10),
            ('line', -10, 15, 10, 15),
            ('line', -5, 20, 5, 20),
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("GND", PinType.GROUND, 0, 0),
        ]
    
    def _init_properties(self):
        self._properties = {}
    
    def get_spice_model(self) -> str:
        # Ground doesn't generate a SPICE element
        return ""


class VDD(Component):
    """Power supply rail."""
    
    def __init__(self):
        self._ref_prefix = "VDD"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.SOURCE
    
    @property
    def display_name(self) -> str:
        return "VDD"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """VDD symbol."""
        return [
            ('line', 0, 10, 0, 0),
            ('line', -10, 0, 10, 0),
            ('text', 0, -10, 'VDD', 10),
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("VDD", PinType.POWER, 0, 10),
        ]
    
    def _init_properties(self):
        self._properties = {
            'voltage': ComponentProperty(
                name='voltage',
                display_name='Voltage',
                property_type=PropertyType.FLOAT,
                default_value=5.0,
                unit='V',
                description='Supply voltage'
            ),
        }
    
    def get_spice_model(self) -> str:
        # VDD is typically connected to a global power net
        return ""
