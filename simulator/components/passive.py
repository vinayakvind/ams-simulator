"""
Passive components: Resistor, Capacitor, Inductor.
"""

from simulator.components.base import (
    Component, ComponentType, Pin, PinType,
    ComponentProperty, PropertyType
)


class Resistor(Component):
    """Resistor component."""
    
    def __init__(self):
        self._ref_prefix = "R"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.PASSIVE
    
    @property
    def display_name(self) -> str:
        return "Resistor"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """American-style zigzag resistor symbol."""
        return [
            ('line', -30, 0, -20, 0),
            ('line', -20, 0, -15, -8),
            ('line', -15, -8, -5, 8),
            ('line', -5, 8, 5, -8),
            ('line', 5, -8, 15, 8),
            ('line', 15, 8, 20, 0),
            ('line', 20, 0, 30, 0),
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("1", PinType.BIDIRECTIONAL, -30, 0),
            Pin("2", PinType.BIDIRECTIONAL, 30, 0),
        ]
    
    def _init_properties(self):
        self._properties = {
            'resistance': ComponentProperty(
                name='resistance',
                display_name='Resistance',
                property_type=PropertyType.FLOAT,
                default_value=1000.0,
                unit='Ω',
                min_value=0.0,
                description='Resistance value in Ohms'
            ),
            'tolerance': ComponentProperty(
                name='tolerance',
                display_name='Tolerance',
                property_type=PropertyType.FLOAT,
                default_value=5.0,
                unit='%',
                min_value=0.0,
                max_value=100.0,
                description='Resistance tolerance in percent'
            ),
            'power_rating': ComponentProperty(
                name='power_rating',
                display_name='Power Rating',
                property_type=PropertyType.FLOAT,
                default_value=0.25,
                unit='W',
                min_value=0.0,
                description='Maximum power dissipation'
            ),
            'temp_coeff': ComponentProperty(
                name='temp_coeff',
                display_name='Temp Coefficient',
                property_type=PropertyType.FLOAT,
                default_value=100.0,
                unit='ppm/°C',
                description='Temperature coefficient'
            ),
        }
    
    def get_spice_model(self) -> str:
        r_val = self._properties['resistance'].value
        p1 = self._pins[0].connected_net or '0'
        p2 = self._pins[1].connected_net or '0'
        return f"{self.reference} {p1} {p2} {r_val}"


class Capacitor(Component):
    """Capacitor component."""
    
    def __init__(self):
        self._ref_prefix = "C"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.PASSIVE
    
    @property
    def display_name(self) -> str:
        return "Capacitor"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """Standard capacitor symbol with two parallel plates."""
        return [
            ('line', -30, 0, -5, 0),
            ('line', -5, -15, -5, 15),
            ('line', 5, -15, 5, 15),
            ('line', 5, 0, 30, 0),
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("1", PinType.BIDIRECTIONAL, -30, 0),
            Pin("2", PinType.BIDIRECTIONAL, 30, 0),
        ]
    
    def _init_properties(self):
        self._properties = {
            'capacitance': ComponentProperty(
                name='capacitance',
                display_name='Capacitance',
                property_type=PropertyType.FLOAT,
                default_value=1e-6,
                unit='F',
                min_value=0.0,
                description='Capacitance value in Farads'
            ),
            'voltage_rating': ComponentProperty(
                name='voltage_rating',
                display_name='Voltage Rating',
                property_type=PropertyType.FLOAT,
                default_value=50.0,
                unit='V',
                min_value=0.0,
                description='Maximum voltage rating'
            ),
            'initial_voltage': ComponentProperty(
                name='initial_voltage',
                display_name='Initial Voltage',
                property_type=PropertyType.FLOAT,
                default_value=0.0,
                unit='V',
                description='Initial voltage for transient analysis'
            ),
            'esr': ComponentProperty(
                name='esr',
                display_name='ESR',
                property_type=PropertyType.FLOAT,
                default_value=0.01,
                unit='Ω',
                min_value=0.0,
                description='Equivalent Series Resistance'
            ),
        }
    
    def get_spice_model(self) -> str:
        c_val = self._properties['capacitance'].value
        ic = self._properties['initial_voltage'].value
        p1 = self._pins[0].connected_net or '0'
        p2 = self._pins[1].connected_net or '0'
        return f"{self.reference} {p1} {p2} {c_val} IC={ic}"


class Inductor(Component):
    """Inductor component."""
    
    def __init__(self):
        self._ref_prefix = "L"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.PASSIVE
    
    @property
    def display_name(self) -> str:
        return "Inductor"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """Inductor symbol with humps."""
        return [
            ('line', -30, 0, -20, 0),
            ('arc', -15, 0, 5, 180, 0),
            ('arc', -5, 0, 5, 180, 0),
            ('arc', 5, 0, 5, 180, 0),
            ('arc', 15, 0, 5, 180, 0),
            ('line', 20, 0, 30, 0),
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("1", PinType.BIDIRECTIONAL, -30, 0),
            Pin("2", PinType.BIDIRECTIONAL, 30, 0),
        ]
    
    def _init_properties(self):
        self._properties = {
            'inductance': ComponentProperty(
                name='inductance',
                display_name='Inductance',
                property_type=PropertyType.FLOAT,
                default_value=1e-3,
                unit='H',
                min_value=0.0,
                description='Inductance value in Henries'
            ),
            'initial_current': ComponentProperty(
                name='initial_current',
                display_name='Initial Current',
                property_type=PropertyType.FLOAT,
                default_value=0.0,
                unit='A',
                description='Initial current for transient analysis'
            ),
            'dcr': ComponentProperty(
                name='dcr',
                display_name='DCR',
                property_type=PropertyType.FLOAT,
                default_value=0.1,
                unit='Ω',
                min_value=0.0,
                description='DC Resistance'
            ),
            'saturation_current': ComponentProperty(
                name='saturation_current',
                display_name='Saturation Current',
                property_type=PropertyType.FLOAT,
                default_value=1.0,
                unit='A',
                min_value=0.0,
                description='Saturation current'
            ),
        }
    
    def get_spice_model(self) -> str:
        l_val = self._properties['inductance'].value
        ic = self._properties['initial_current'].value
        p1 = self._pins[0].connected_net or '0'
        p2 = self._pins[1].connected_net or '0'
        return f"{self.reference} {p1} {p2} {l_val} IC={ic}"


class PolarizedCapacitor(Component):
    """Polarized (electrolytic) capacitor component."""
    
    def __init__(self):
        self._ref_prefix = "C"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.PASSIVE
    
    @property
    def display_name(self) -> str:
        return "Polarized Capacitor"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """Polarized capacitor symbol with + marking."""
        return [
            ('line', -30, 0, -5, 0),
            ('line', -5, -15, -5, 15),
            ('arc', 15, 0, 10, 120, 240),  # Curved plate
            ('line', 5, 0, 30, 0),
            ('text', -15, -12, '+', 10),  # Plus sign for polarity
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("+", PinType.BIDIRECTIONAL, -30, 0),
            Pin("-", PinType.BIDIRECTIONAL, 30, 0),
        ]
    
    def _init_properties(self):
        self._properties = {
            'capacitance': ComponentProperty(
                name='capacitance',
                display_name='Capacitance',
                property_type=PropertyType.FLOAT,
                default_value=100e-6,
                unit='F',
                min_value=0.0,
                description='Capacitance value in Farads'
            ),
            'voltage_rating': ComponentProperty(
                name='voltage_rating',
                display_name='Voltage Rating',
                property_type=PropertyType.FLOAT,
                default_value=25.0,
                unit='V',
                min_value=0.0,
                description='Maximum voltage rating'
            ),
            'initial_voltage': ComponentProperty(
                name='initial_voltage',
                display_name='Initial Voltage',
                property_type=PropertyType.FLOAT,
                default_value=0.0,
                unit='V',
                description='Initial voltage for transient analysis'
            ),
            'esr': ComponentProperty(
                name='esr',
                display_name='ESR',
                property_type=PropertyType.FLOAT,
                default_value=0.1,
                unit='Ω',
                min_value=0.0,
                description='Equivalent Series Resistance'
            ),
        }
    
    def get_spice_model(self) -> str:
        c_val = self._properties['capacitance'].value
        ic = self._properties['initial_voltage'].value
        p1 = self._pins[0].connected_net or '0'
        p2 = self._pins[1].connected_net or '0'
        return f"{self.reference} {p1} {p2} {c_val} IC={ic}"
