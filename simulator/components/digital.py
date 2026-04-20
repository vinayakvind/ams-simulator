"""
Digital gate components for the AMS Simulator.
"""

from simulator.components.base import (
    Component, ComponentType, Pin, PinType,
    ComponentProperty, PropertyType
)


class ANDGate(Component):
    """2-input AND gate."""
    
    def __init__(self):
        self._ref_prefix = "U"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.DIGITAL_GATE
    
    @property
    def display_name(self) -> str:
        return "AND Gate"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """AND gate symbol."""
        return [
            ('line', -30, -20, -30, 20),
            ('line', -30, -20, 0, -20),
            ('line', -30, 20, 0, 20),
            ('arc', 0, 0, 20, -90, 90),
            ('line', 20, 0, 35, 0),
            ('line', -45, -10, -30, -10),
            ('line', -45, 10, -30, 10),
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("A", PinType.DIGITAL, -45, -10),
            Pin("B", PinType.DIGITAL, -45, 10),
            Pin("Y", PinType.DIGITAL, 35, 0),
        ]
    
    def _init_properties(self):
        self._properties = {
            'propagation_delay': ComponentProperty(
                name='propagation_delay',
                display_name='Propagation Delay',
                property_type=PropertyType.FLOAT,
                default_value=1e-9,
                unit='s',
                min_value=0.0,
                description='Gate propagation delay'
            ),
            'input_capacitance': ComponentProperty(
                name='input_capacitance',
                display_name='Input Capacitance',
                property_type=PropertyType.FLOAT,
                default_value=1e-15,
                unit='F',
                min_value=0.0,
                description='Input pin capacitance'
            ),
        }
    
    def get_spice_model(self) -> str:
        a = self._pins[0].connected_net or '0'
        b = self._pins[1].connected_net or '0'
        y = self._pins[2].connected_net or '0'
        delay = self._properties['propagation_delay'].value
        return f"A{self.reference} [{a} {b}] [{y}] AND TPLH={delay} TPHL={delay}"


class ORGate(Component):
    """2-input OR gate."""
    
    def __init__(self):
        self._ref_prefix = "U"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.DIGITAL_GATE
    
    @property
    def display_name(self) -> str:
        return "OR Gate"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """OR gate symbol."""
        return [
            ('arc', -50, 0, 25, -50, 50),
            ('arc', -15, -35, 40, 60, 90),
            ('arc', -15, 35, 40, -90, -60),
            ('line', 20, 0, 35, 0),
            ('line', -45, -10, -30, -10),
            ('line', -45, 10, -30, 10),
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("A", PinType.DIGITAL, -45, -10),
            Pin("B", PinType.DIGITAL, -45, 10),
            Pin("Y", PinType.DIGITAL, 35, 0),
        ]
    
    def _init_properties(self):
        self._properties = {
            'propagation_delay': ComponentProperty(
                name='propagation_delay',
                display_name='Propagation Delay',
                property_type=PropertyType.FLOAT,
                default_value=1e-9,
                unit='s',
                min_value=0.0,
                description='Gate propagation delay'
            ),
            'input_capacitance': ComponentProperty(
                name='input_capacitance',
                display_name='Input Capacitance',
                property_type=PropertyType.FLOAT,
                default_value=1e-15,
                unit='F',
                min_value=0.0,
                description='Input pin capacitance'
            ),
        }
    
    def get_spice_model(self) -> str:
        a = self._pins[0].connected_net or '0'
        b = self._pins[1].connected_net or '0'
        y = self._pins[2].connected_net or '0'
        delay = self._properties['propagation_delay'].value
        return f"A{self.reference} [{a} {b}] [{y}] OR TPLH={delay} TPHL={delay}"


class NOTGate(Component):
    """Inverter gate."""
    
    def __init__(self):
        self._ref_prefix = "U"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.DIGITAL_GATE
    
    @property
    def display_name(self) -> str:
        return "NOT Gate (Inverter)"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """NOT gate symbol (triangle with bubble)."""
        return [
            ('polygon', [(-25, -15), (-25, 15), (10, 0)]),
            ('circle', 15, 0, 5),
            ('line', 20, 0, 35, 0),
            ('line', -40, 0, -25, 0),
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("A", PinType.DIGITAL, -40, 0),
            Pin("Y", PinType.DIGITAL, 35, 0),
        ]
    
    def _init_properties(self):
        self._properties = {
            'propagation_delay': ComponentProperty(
                name='propagation_delay',
                display_name='Propagation Delay',
                property_type=PropertyType.FLOAT,
                default_value=0.5e-9,
                unit='s',
                min_value=0.0,
                description='Gate propagation delay'
            ),
            'input_capacitance': ComponentProperty(
                name='input_capacitance',
                display_name='Input Capacitance',
                property_type=PropertyType.FLOAT,
                default_value=1e-15,
                unit='F',
                min_value=0.0,
                description='Input pin capacitance'
            ),
        }
    
    def get_spice_model(self) -> str:
        a = self._pins[0].connected_net or '0'
        y = self._pins[1].connected_net or '0'
        delay = self._properties['propagation_delay'].value
        return f"A{self.reference} [{a}] [{y}] INV TPLH={delay} TPHL={delay}"


class NANDGate(Component):
    """2-input NAND gate."""
    
    def __init__(self):
        self._ref_prefix = "U"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.DIGITAL_GATE
    
    @property
    def display_name(self) -> str:
        return "NAND Gate"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """NAND gate symbol (AND with bubble)."""
        return [
            ('line', -30, -20, -30, 20),
            ('line', -30, -20, 0, -20),
            ('line', -30, 20, 0, 20),
            ('arc', 0, 0, 20, -90, 90),
            ('circle', 25, 0, 5),
            ('line', 30, 0, 40, 0),
            ('line', -45, -10, -30, -10),
            ('line', -45, 10, -30, 10),
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("A", PinType.DIGITAL, -45, -10),
            Pin("B", PinType.DIGITAL, -45, 10),
            Pin("Y", PinType.DIGITAL, 40, 0),
        ]
    
    def _init_properties(self):
        self._properties = {
            'propagation_delay': ComponentProperty(
                name='propagation_delay',
                display_name='Propagation Delay',
                property_type=PropertyType.FLOAT,
                default_value=1e-9,
                unit='s',
                min_value=0.0,
                description='Gate propagation delay'
            ),
            'input_capacitance': ComponentProperty(
                name='input_capacitance',
                display_name='Input Capacitance',
                property_type=PropertyType.FLOAT,
                default_value=1e-15,
                unit='F',
                min_value=0.0,
                description='Input pin capacitance'
            ),
        }
    
    def get_spice_model(self) -> str:
        a = self._pins[0].connected_net or '0'
        b = self._pins[1].connected_net or '0'
        y = self._pins[2].connected_net or '0'
        delay = self._properties['propagation_delay'].value
        return f"A{self.reference} [{a} {b}] [{y}] NAND TPLH={delay} TPHL={delay}"


class NORGate(Component):
    """2-input NOR gate."""
    
    def __init__(self):
        self._ref_prefix = "U"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.DIGITAL_GATE
    
    @property
    def display_name(self) -> str:
        return "NOR Gate"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """NOR gate symbol (OR with bubble)."""
        return [
            ('arc', -50, 0, 25, -50, 50),
            ('arc', -15, -35, 40, 60, 90),
            ('arc', -15, 35, 40, -90, -60),
            ('circle', 25, 0, 5),
            ('line', 30, 0, 40, 0),
            ('line', -45, -10, -30, -10),
            ('line', -45, 10, -30, 10),
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("A", PinType.DIGITAL, -45, -10),
            Pin("B", PinType.DIGITAL, -45, 10),
            Pin("Y", PinType.DIGITAL, 40, 0),
        ]
    
    def _init_properties(self):
        self._properties = {
            'propagation_delay': ComponentProperty(
                name='propagation_delay',
                display_name='Propagation Delay',
                property_type=PropertyType.FLOAT,
                default_value=1e-9,
                unit='s',
                min_value=0.0,
                description='Gate propagation delay'
            ),
            'input_capacitance': ComponentProperty(
                name='input_capacitance',
                display_name='Input Capacitance',
                property_type=PropertyType.FLOAT,
                default_value=1e-15,
                unit='F',
                min_value=0.0,
                description='Input pin capacitance'
            ),
        }
    
    def get_spice_model(self) -> str:
        a = self._pins[0].connected_net or '0'
        b = self._pins[1].connected_net or '0'
        y = self._pins[2].connected_net or '0'
        delay = self._properties['propagation_delay'].value
        return f"A{self.reference} [{a} {b}] [{y}] NOR TPLH={delay} TPHL={delay}"


class XORGate(Component):
    """2-input XOR gate."""
    
    def __init__(self):
        self._ref_prefix = "U"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.DIGITAL_GATE
    
    @property
    def display_name(self) -> str:
        return "XOR Gate"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """XOR gate symbol (OR with extra curve)."""
        return [
            ('arc', -55, 0, 25, -50, 50),  # Extra curve
            ('arc', -50, 0, 25, -50, 50),
            ('arc', -15, -35, 40, 60, 90),
            ('arc', -15, 35, 40, -90, -60),
            ('line', 20, 0, 35, 0),
            ('line', -50, -10, -30, -10),
            ('line', -50, 10, -30, 10),
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("A", PinType.DIGITAL, -50, -10),
            Pin("B", PinType.DIGITAL, -50, 10),
            Pin("Y", PinType.DIGITAL, 35, 0),
        ]
    
    def _init_properties(self):
        self._properties = {
            'propagation_delay': ComponentProperty(
                name='propagation_delay',
                display_name='Propagation Delay',
                property_type=PropertyType.FLOAT,
                default_value=1.5e-9,
                unit='s',
                min_value=0.0,
                description='Gate propagation delay'
            ),
            'input_capacitance': ComponentProperty(
                name='input_capacitance',
                display_name='Input Capacitance',
                property_type=PropertyType.FLOAT,
                default_value=1e-15,
                unit='F',
                min_value=0.0,
                description='Input pin capacitance'
            ),
        }
    
    def get_spice_model(self) -> str:
        a = self._pins[0].connected_net or '0'
        b = self._pins[1].connected_net or '0'
        y = self._pins[2].connected_net or '0'
        delay = self._properties['propagation_delay'].value
        return f"A{self.reference} [{a} {b}] [{y}] XOR TPLH={delay} TPHL={delay}"


class XNORGate(Component):
    """2-input XNOR gate."""
    
    def __init__(self):
        self._ref_prefix = "U"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.DIGITAL_GATE
    
    @property
    def display_name(self) -> str:
        return "XNOR Gate"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """XNOR gate symbol (XOR with bubble)."""
        return [
            ('arc', -55, 0, 25, -50, 50),
            ('arc', -50, 0, 25, -50, 50),
            ('arc', -15, -35, 40, 60, 90),
            ('arc', -15, 35, 40, -90, -60),
            ('circle', 25, 0, 5),
            ('line', 30, 0, 40, 0),
            ('line', -50, -10, -30, -10),
            ('line', -50, 10, -30, 10),
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("A", PinType.DIGITAL, -50, -10),
            Pin("B", PinType.DIGITAL, -50, 10),
            Pin("Y", PinType.DIGITAL, 40, 0),
        ]
    
    def _init_properties(self):
        self._properties = {
            'propagation_delay': ComponentProperty(
                name='propagation_delay',
                display_name='Propagation Delay',
                property_type=PropertyType.FLOAT,
                default_value=1.5e-9,
                unit='s',
                min_value=0.0,
                description='Gate propagation delay'
            ),
            'input_capacitance': ComponentProperty(
                name='input_capacitance',
                display_name='Input Capacitance',
                property_type=PropertyType.FLOAT,
                default_value=1e-15,
                unit='F',
                min_value=0.0,
                description='Input pin capacitance'
            ),
        }
    
    def get_spice_model(self) -> str:
        a = self._pins[0].connected_net or '0'
        b = self._pins[1].connected_net or '0'
        y = self._pins[2].connected_net or '0'
        delay = self._properties['propagation_delay'].value
        return f"A{self.reference} [{a} {b}] [{y}] XNOR TPLH={delay} TPHL={delay}"


class Buffer(Component):
    """Buffer gate."""
    
    def __init__(self):
        self._ref_prefix = "U"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.DIGITAL_GATE
    
    @property
    def display_name(self) -> str:
        return "Buffer"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """Buffer symbol (triangle without bubble)."""
        return [
            ('polygon', [(-25, -15), (-25, 15), (15, 0)]),
            ('line', 15, 0, 35, 0),
            ('line', -40, 0, -25, 0),
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("A", PinType.DIGITAL, -40, 0),
            Pin("Y", PinType.DIGITAL, 35, 0),
        ]
    
    def _init_properties(self):
        self._properties = {
            'propagation_delay': ComponentProperty(
                name='propagation_delay',
                display_name='Propagation Delay',
                property_type=PropertyType.FLOAT,
                default_value=0.5e-9,
                unit='s',
                min_value=0.0,
                description='Gate propagation delay'
            ),
            'input_capacitance': ComponentProperty(
                name='input_capacitance',
                display_name='Input Capacitance',
                property_type=PropertyType.FLOAT,
                default_value=1e-15,
                unit='F',
                min_value=0.0,
                description='Input pin capacitance'
            ),
        }
    
    def get_spice_model(self) -> str:
        a = self._pins[0].connected_net or '0'
        y = self._pins[1].connected_net or '0'
        delay = self._properties['propagation_delay'].value
        return f"A{self.reference} [{a}] [{y}] BUF TPLH={delay} TPHL={delay}"


class DFlipFlop(Component):
    """D-type Flip-Flop."""
    
    def __init__(self):
        self._ref_prefix = "U"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.DIGITAL_SEQUENTIAL
    
    @property
    def display_name(self) -> str:
        return "D Flip-Flop"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """D Flip-Flop symbol."""
        return [
            ('rect', -30, -30, 60, 60),
            ('text', -20, -15, 'D', 10),
            ('text', -20, 15, 'CLK', 8),
            ('text', 15, -15, 'Q', 10),
            ('text', 15, 15, 'Q\'', 10),
            ('polygon', [(-30, 10), (-22, 15), (-30, 20)]),  # Clock symbol
            ('line', -45, -15, -30, -15),
            ('line', -45, 15, -30, 15),
            ('line', 30, -15, 45, -15),
            ('line', 30, 15, 45, 15),
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("D", PinType.DIGITAL, -45, -15),
            Pin("CLK", PinType.DIGITAL, -45, 15),
            Pin("Q", PinType.DIGITAL, 45, -15),
            Pin("Qn", PinType.DIGITAL, 45, 15),
        ]
    
    def _init_properties(self):
        self._properties = {
            'setup_time': ComponentProperty(
                name='setup_time',
                display_name='Setup Time',
                property_type=PropertyType.FLOAT,
                default_value=1e-9,
                unit='s',
                min_value=0.0,
                description='Setup time'
            ),
            'hold_time': ComponentProperty(
                name='hold_time',
                display_name='Hold Time',
                property_type=PropertyType.FLOAT,
                default_value=0.5e-9,
                unit='s',
                min_value=0.0,
                description='Hold time'
            ),
            'clk_to_q': ComponentProperty(
                name='clk_to_q',
                display_name='Clock-to-Q Delay',
                property_type=PropertyType.FLOAT,
                default_value=2e-9,
                unit='s',
                min_value=0.0,
                description='Clock to Q propagation delay'
            ),
            'initial_state': ComponentProperty(
                name='initial_state',
                display_name='Initial State',
                property_type=PropertyType.ENUM,
                default_value='0',
                enum_values=['0', '1', 'X'],
                description='Initial output state'
            ),
        }
    
    def get_spice_model(self) -> str:
        d = self._pins[0].connected_net or '0'
        clk = self._pins[1].connected_net or '0'
        q = self._pins[2].connected_net or '0'
        qn = self._pins[3].connected_net or '0'
        delay = self._properties['clk_to_q'].value
        return f"A{self.reference} [{d} {clk}] [{q} {qn}] DFF IC={self._properties['initial_state'].value} TD={delay}"


class SRLatch(Component):
    """SR Latch."""
    
    def __init__(self):
        self._ref_prefix = "U"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.DIGITAL_SEQUENTIAL
    
    @property
    def display_name(self) -> str:
        return "SR Latch"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """SR Latch symbol."""
        return [
            ('rect', -30, -25, 60, 50),
            ('text', -20, -10, 'S', 10),
            ('text', -20, 10, 'R', 10),
            ('text', 15, -10, 'Q', 10),
            ('text', 15, 10, 'Q\'', 10),
            ('line', -45, -10, -30, -10),
            ('line', -45, 10, -30, 10),
            ('line', 30, -10, 45, -10),
            ('line', 30, 10, 45, 10),
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("S", PinType.DIGITAL, -45, -10),
            Pin("R", PinType.DIGITAL, -45, 10),
            Pin("Q", PinType.DIGITAL, 45, -10),
            Pin("Qn", PinType.DIGITAL, 45, 10),
        ]
    
    def _init_properties(self):
        self._properties = {
            'propagation_delay': ComponentProperty(
                name='propagation_delay',
                display_name='Propagation Delay',
                property_type=PropertyType.FLOAT,
                default_value=2e-9,
                unit='s',
                min_value=0.0,
                description='Propagation delay'
            ),
            'initial_state': ComponentProperty(
                name='initial_state',
                display_name='Initial State',
                property_type=PropertyType.ENUM,
                default_value='0',
                enum_values=['0', '1', 'X'],
                description='Initial output state'
            ),
        }
    
    def get_spice_model(self) -> str:
        s = self._pins[0].connected_net or '0'
        r = self._pins[1].connected_net or '0'
        q = self._pins[2].connected_net or '0'
        qn = self._pins[3].connected_net or '0'
        delay = self._properties['propagation_delay'].value
        return f"A{self.reference} [{s} {r}] [{q} {qn}] SRFF IC={self._properties['initial_state'].value} TD={delay}"


class Mux2to1(Component):
    """2-to-1 Multiplexer."""
    
    def __init__(self):
        self._ref_prefix = "U"
        super().__init__()
    
    @property
    def component_type(self) -> ComponentType:
        return ComponentType.DIGITAL_GATE
    
    @property
    def display_name(self) -> str:
        return "2:1 Multiplexer"
    
    @property
    def symbol_path(self) -> list[tuple]:
        """2:1 Mux symbol (trapezoid)."""
        return [
            ('polygon', [(-25, -30), (-25, 30), (15, 20), (15, -20)]),
            ('text', -15, -12, '0', 8),
            ('text', -15, 12, '1', 8),
            ('text', -5, 22, 'S', 8),
            ('line', -40, -12, -25, -12),
            ('line', -40, 12, -25, 12),
            ('line', 0, 30, 0, 45),
            ('line', 15, 0, 30, 0),
        ]
    
    def _init_pins(self):
        self._pins = [
            Pin("A", PinType.DIGITAL, -40, -12),   # Input 0
            Pin("B", PinType.DIGITAL, -40, 12),    # Input 1
            Pin("S", PinType.DIGITAL, 0, 45),      # Select
            Pin("Y", PinType.DIGITAL, 30, 0),      # Output
        ]
    
    def _init_properties(self):
        self._properties = {
            'propagation_delay': ComponentProperty(
                name='propagation_delay',
                display_name='Propagation Delay',
                property_type=PropertyType.FLOAT,
                default_value=1.5e-9,
                unit='s',
                min_value=0.0,
                description='Propagation delay'
            ),
        }
    
    def get_spice_model(self) -> str:
        a = self._pins[0].connected_net or '0'
        b = self._pins[1].connected_net or '0'
        s = self._pins[2].connected_net or '0'
        y = self._pins[3].connected_net or '0'
        delay = self._properties['propagation_delay'].value
        return f"A{self.reference} [{a} {b} {s}] [{y}] MUX21 TD={delay}"
