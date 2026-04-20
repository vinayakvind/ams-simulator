"""
Mixed-Signal Simulation Engine - Verilog-AMS and analog/digital interface.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Callable, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import numpy as np

from .analog_engine import AnalogEngine
from .digital_engine import DigitalEngine, LogicValue, Signal


class DisciplineType(Enum):
    """Signal discipline types."""
    ELECTRICAL = "electrical"
    LOGIC = "logic"


@dataclass
class MixedSignal:
    """A mixed-signal node that can be analog or digital."""
    name: str
    discipline: DisciplineType
    analog_value: float = 0.0
    digital_value: LogicValue = field(default=LogicValue.LOGIC_X)
    
    # Threshold levels for A/D conversion
    vth_high: float = 2.5  # Voltage above this is logic 1
    vth_low: float = 0.8   # Voltage below this is logic 0
    
    # Output levels for D/A conversion
    v_high: float = 3.3    # Logic 1 voltage
    v_low: float = 0.0     # Logic 0 voltage
    
    def to_digital(self) -> LogicValue:
        """Convert analog value to digital."""
        if self.analog_value >= self.vth_high:
            return LogicValue.LOGIC_1
        elif self.analog_value <= self.vth_low:
            return LogicValue.LOGIC_0
        else:
            return LogicValue.LOGIC_X
    
    def to_analog(self) -> float:
        """Convert digital value to analog."""
        if self.digital_value == LogicValue.LOGIC_1:
            return self.v_high
        elif self.digital_value == LogicValue.LOGIC_0:
            return self.v_low
        else:
            return (self.v_high + self.v_low) / 2  # Undefined


@dataclass
class ConnectModule:
    """A connect module for discipline conversion."""
    name: str
    analog_port: str
    digital_port: str
    direction: str  # 'a2d', 'd2a', or 'bidir'
    
    # Timing parameters
    rise_delay: float = 1e-9
    fall_delay: float = 1e-9
    
    # Threshold parameters
    vth_high: float = 2.5
    vth_low: float = 0.8
    v_high: float = 3.3
    v_low: float = 0.0


class MixedSignalEngine:
    """
    Mixed-signal simulator combining analog and digital engines.
    Implements Verilog-AMS style discipline resolution and 
    connect modules for analog/digital interfaces.
    """
    
    def __init__(self):
        self.analog_engine = AnalogEngine()
        self.digital_engine = DigitalEngine()
        
        self._mixed_signals: Dict[str, MixedSignal] = {}
        self._connect_modules: List[ConnectModule] = []
        
        # Simulation parameters
        self._time: float = 0.0
        self._time_step: float = 1e-9
        self._max_time: float = 1e-6
        
        # Results storage
        self._analog_results: Dict[str, List[Tuple[float, float]]] = {}
        self._digital_results: Dict[str, List[Tuple[float, LogicValue]]] = {}
    
    def add_mixed_signal(self, name: str, discipline: DisciplineType,
                         vth_high: float = 2.5, vth_low: float = 0.8,
                         v_high: float = 3.3, v_low: float = 0.0) -> MixedSignal:
        """Add a mixed-signal node."""
        signal = MixedSignal(
            name=name,
            discipline=discipline,
            vth_high=vth_high,
            vth_low=vth_low,
            v_high=v_high,
            v_low=v_low
        )
        self._mixed_signals[name] = signal
        
        # Also add to appropriate engine
        if discipline == DisciplineType.ELECTRICAL:
            self.analog_engine._add_node(name)
        else:
            self.digital_engine.add_signal(name)
        
        return signal
    
    def add_connect_module(self, name: str, analog_port: str, digital_port: str,
                           direction: str = 'bidir', **kwargs) -> ConnectModule:
        """Add a connect module for discipline resolution."""
        module = ConnectModule(
            name=name,
            analog_port=analog_port,
            digital_port=digital_port,
            direction=direction,
            **{k: v for k, v in kwargs.items() if hasattr(ConnectModule, k)}
        )
        self._connect_modules.append(module)
        
        # Ensure signals exist
        if analog_port not in self._mixed_signals:
            self.add_mixed_signal(analog_port, DisciplineType.ELECTRICAL)
        if digital_port not in self._mixed_signals:
            self.add_mixed_signal(digital_port, DisciplineType.LOGIC)
        
        return module
    
    def load_netlist(self, netlist: str):
        """Load a mixed-signal netlist."""
        lines = netlist.strip().split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            # Skip comments
            if not line or line.startswith('*') or line.startswith('//'):
                continue
            
            # Section markers
            if line.upper() == '.ANALOG':
                current_section = 'analog'
                continue
            elif line.upper() == '.DIGITAL':
                current_section = 'digital'
                continue
            elif line.upper() == '.CONNECT':
                current_section = 'connect'
                continue
            elif line.upper().startswith('.END'):
                current_section = None
                continue
            
            # Process based on section
            if current_section == 'analog':
                self._parse_analog_element(line)
            elif current_section == 'digital':
                self._parse_digital_element(line)
            elif current_section == 'connect':
                self._parse_connect_statement(line)
            else:
                # Auto-detect based on element prefix
                self._auto_parse_element(line)
    
    def _parse_analog_element(self, line: str):
        """Parse an analog circuit element."""
        # Forward to analog engine
        self.analog_engine._parse_element(line)
    
    def _parse_digital_element(self, line: str):
        """Parse a digital element."""
        parts = line.split()
        if not parts:
            return
        
        # Gate instantiation
        gate_type = parts[0].lower()
        if gate_type in ['and', 'or', 'not', 'nand', 'nor', 'xor', 'xnor', 'buf']:
            name = parts[1]
            ports = [p.strip().rstrip(',') for p in parts[2:]]
            
            if gate_type in ['not', 'buf']:
                output = ports[0]
                inputs = ports[1:]
            else:
                output = ports[0]
                inputs = ports[1:]
            
            self.digital_engine.add_gate(gate_type, name, output, inputs)
    
    def _parse_connect_statement(self, line: str):
        """Parse a connect module statement."""
        # CONNECT <name> <analog> <digital> [direction] [params]
        parts = line.split()
        if len(parts) >= 4 and parts[0].upper() == 'CONNECT':
            name = parts[1]
            analog_port = parts[2]
            digital_port = parts[3]
            direction = parts[4] if len(parts) > 4 else 'bidir'
            
            self.add_connect_module(name, analog_port, digital_port, direction)
    
    def _auto_parse_element(self, line: str):
        """Auto-detect and parse element."""
        if not line:
            return
        
        prefix = line[0].upper()
        
        # Analog elements
        if prefix in ['R', 'C', 'L', 'V', 'I', 'M', 'Q', 'D']:
            self._parse_analog_element(line)
        # Digital gates
        elif line.split()[0].lower() in ['and', 'or', 'not', 'nand', 'nor', 'xor', 'xnor', 'buf']:
            self._parse_digital_element(line)
    
    def resolve_disciplines(self):
        """Resolve discipline connections at current time."""
        for module in self._connect_modules:
            analog_signal = self._mixed_signals.get(module.analog_port)
            digital_signal = self._mixed_signals.get(module.digital_port)
            
            if not analog_signal or not digital_signal:
                continue
            
            if module.direction == 'a2d':
                # Analog to digital conversion
                analog_signal.analog_value = self.analog_engine.get_node_voltage(module.analog_port)
                analog_signal.vth_high = module.vth_high
                analog_signal.vth_low = module.vth_low
                digital_value = analog_signal.to_digital()
                
                # Update digital engine
                self.digital_engine.set_signal(module.digital_port, digital_value)
                digital_signal.digital_value = digital_value
            
            elif module.direction == 'd2a':
                # Digital to analog conversion
                dig_signal = self.digital_engine.get_signal(module.digital_port)
                if dig_signal:
                    digital_signal.digital_value = dig_signal.value
                    digital_signal.v_high = module.v_high
                    digital_signal.v_low = module.v_low
                    analog_value = digital_signal.to_analog()
                    
                    # Update analog node (would need to add as source)
                    analog_signal.analog_value = analog_value
            
            elif module.direction == 'bidir':
                # Bidirectional - determine direction based on driver strength
                # For now, default to analog -> digital
                analog_signal.analog_value = self.analog_engine.get_node_voltage(module.analog_port)
                digital_value = analog_signal.to_digital()
                self.digital_engine.set_signal(module.digital_port, digital_value)
    
    def run(self, settings: dict, progress_callback: Optional[Callable] = None) -> dict:
        """Run mixed-signal simulation."""
        self._max_time = settings.get('tstop', 1e-6)
        self._time_step = settings.get('tstep', 1e-9)
        
        # Calculate number of steps
        num_steps = int(self._max_time / self._time_step) + 1
        time_points = np.linspace(0, self._max_time, num_steps)
        
        # Initialize results
        results = {
            'type': 'mixed_signal',
            'time': time_points.tolist(),
        }
        
        # Storage for waveforms
        analog_waveforms: Dict[str, List[float]] = {}
        digital_waveforms: Dict[str, List[str]] = {}
        
        # Run simulation
        for i, t in enumerate(time_points):
            self._time = t
            
            if progress_callback:
                progress_callback(i / len(time_points))
            
            # Step 1: Update analog simulation
            self._step_analog(t)
            
            # Step 2: Resolve discipline boundaries
            self.resolve_disciplines()
            
            # Step 3: Update digital simulation
            self._step_digital(t)
            
            # Step 4: Collect results
            for name, signal in self._mixed_signals.items():
                if signal.discipline == DisciplineType.ELECTRICAL:
                    if name not in analog_waveforms:
                        analog_waveforms[name] = []
                    analog_waveforms[name].append(signal.analog_value)
                else:
                    if name not in digital_waveforms:
                        digital_waveforms[name] = []
                    digital_waveforms[name].append(str(signal.digital_value))
        
        # Pack results
        for name, values in analog_waveforms.items():
            results[f'V({name})'] = values
        
        for name, values in digital_waveforms.items():
            results[f'D({name})'] = values
        
        return results
    
    def _step_analog(self, t: float):
        """Step the analog simulation."""
        # Update time-dependent sources
        self.analog_engine._update_sources = lambda t: None  # Disable for base engine
        
        # Simple: solve DC at each time step (simplified transient)
        try:
            dc_results = self.analog_engine.solve_dc()
            
            # Update mixed signals
            for name in self._mixed_signals.keys():
                key = f'V({name})'
                if key in dc_results:
                    self._mixed_signals[name].analog_value = dc_results[key]
        except Exception:
            pass
    
    def _step_digital(self, t: float):
        """Step the digital simulation."""
        # Convert time to digital time units
        digital_time = int(t / self.digital_engine._time_scale)
        self.digital_engine._time = digital_time
        
        # Process events and propagate
        self.digital_engine.process_events()
        self.digital_engine.propagate()
        
        # Update mixed signals
        for name, signal in self._mixed_signals.items():
            if signal.discipline == DisciplineType.LOGIC:
                dig_signal = self.digital_engine.get_signal(name)
                if dig_signal:
                    signal.digital_value = dig_signal.value


class VerilogAMSParser:
    """Parser for Verilog-AMS modules."""
    
    def __init__(self, engine: MixedSignalEngine):
        self.engine = engine
    
    def parse(self, code: str):
        """Parse Verilog-AMS code."""
        import re
        
        # Extract module
        module_match = re.search(r'module\s+(\w+)\s*\(([^)]*)\)\s*;', code)
        if module_match:
            module_name = module_match.group(1)
            ports = [p.strip() for p in module_match.group(2).split(',')]
        
        # Extract disciplines
        for match in re.finditer(r'electrical\s+(\w+)\s*;', code):
            self.engine.add_mixed_signal(match.group(1), DisciplineType.ELECTRICAL)
        
        for match in re.finditer(r'logic\s+(\w+)\s*;', code):
            self.engine.add_mixed_signal(match.group(1), DisciplineType.LOGIC)
        
        # Extract analog blocks
        analog_blocks = re.findall(r'analog\s+begin(.*?)end', code, re.DOTALL)
        for block in analog_blocks:
            self._parse_analog_block(block)
        
        # Extract digital blocks (initial, always)
        digital_code = re.sub(r'analog\s+begin.*?end', '', code, flags=re.DOTALL)
        self.engine.digital_engine.load_verilog(digital_code)
    
    def _parse_analog_block(self, block: str):
        """Parse analog behavioral block."""
        import re
        
        # Look for V() and I() contributions
        # V(node) <+ expression;
        for match in re.finditer(r'V\((\w+)\)\s*<\+\s*([^;]+);', block):
            node = match.group(1)
            expr = match.group(2).strip()
            
            # Try to parse as a simple value or expression
            try:
                value = self._evaluate_analog_expr(expr)
                # Add as voltage source
                self.engine.analog_engine._parse_element(
                    f'V_contrib_{node} {node} 0 DC {value}'
                )
            except:
                pass
    
    def _evaluate_analog_expr(self, expr: str) -> float:
        """Evaluate a simple analog expression."""
        import re
        
        # Simple numeric value
        try:
            return float(expr)
        except ValueError:
            pass
        
        # Expression with SI suffix
        match = re.match(r'([\d.]+)\s*([a-zA-Z]*)', expr)
        if match:
            value = float(match.group(1))
            suffix = match.group(2).lower()
            
            suffixes = {
                'f': 1e-15, 'p': 1e-12, 'n': 1e-9,
                'u': 1e-6, 'm': 1e-3, 'k': 1e3,
                'meg': 1e6, 'g': 1e9, 't': 1e12
            }
            
            if suffix in suffixes:
                return value * suffixes[suffix]
            return value
        
        return 0.0


class ADCModel:
    """Analog-to-Digital Converter model."""
    
    def __init__(self, bits: int = 8, vref: float = 3.3):
        self.bits = bits
        self.vref = vref
        self.lsb = vref / (2 ** bits)
    
    def convert(self, analog_value: float) -> int:
        """Convert analog voltage to digital code."""
        # Clamp input
        clamped = max(0, min(self.vref, analog_value))
        
        # Quantize
        code = int(clamped / self.lsb)
        return min(code, (2 ** self.bits) - 1)


class DACModel:
    """Digital-to-Analog Converter model."""
    
    def __init__(self, bits: int = 8, vref: float = 3.3):
        self.bits = bits
        self.vref = vref
        self.lsb = vref / (2 ** bits)
    
    def convert(self, digital_code: int) -> float:
        """Convert digital code to analog voltage."""
        # Clamp input
        clamped = max(0, min((2 ** self.bits) - 1, digital_code))
        
        return clamped * self.lsb


class SampleAndHold:
    """Sample and Hold circuit model."""
    
    def __init__(self, acquisition_time: float = 100e-9):
        self.acquisition_time = acquisition_time
        self._held_value: float = 0.0
        self._sampling: bool = False
    
    def sample(self, analog_value: float):
        """Sample the input value."""
        self._held_value = analog_value
    
    def hold(self) -> float:
        """Return held value."""
        return self._held_value


class PLLModel:
    """Phase-Locked Loop model for mixed-signal simulation."""
    
    def __init__(self, fref: float = 10e6, n: int = 100, kvco: float = 100e6):
        self.fref = fref          # Reference frequency
        self.n = n                 # Divider ratio
        self.kvco = kvco          # VCO gain (Hz/V)
        self.fout = fref * n       # Output frequency
        
        # PLL state
        self.phase_error: float = 0.0
        self.vctrl: float = 1.65   # Control voltage
        self._locked: bool = False
    
    def update(self, dt: float) -> float:
        """Update PLL state and return VCO output frequency."""
        # Simplified PLL model
        self.fout = self.fref * self.n + self.kvco * (self.vctrl - 1.65)
        
        # Phase detector
        self.phase_error *= 0.99  # Damping
        
        # Lock detection
        self._locked = abs(self.phase_error) < 0.01
        
        return self.fout
    
    @property
    def is_locked(self) -> bool:
        return self._locked
