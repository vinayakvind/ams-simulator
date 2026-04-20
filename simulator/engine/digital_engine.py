"""
Digital Simulation Engine - Verilog and event-driven simulator.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Set, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re
import heapq


class LogicValue(Enum):
    """Four-state logic values."""
    LOGIC_0 = 0
    LOGIC_1 = 1
    LOGIC_X = 2  # Unknown
    LOGIC_Z = 3  # High impedance
    
    def __str__(self):
        if self == LogicValue.LOGIC_0:
            return '0'
        elif self == LogicValue.LOGIC_1:
            return '1'
        elif self == LogicValue.LOGIC_X:
            return 'X'
        else:
            return 'Z'
    
    def __bool__(self):
        return self == LogicValue.LOGIC_1
    
    @staticmethod
    def from_int(val: int) -> 'LogicValue':
        if val == 0:
            return LogicValue.LOGIC_0
        elif val == 1:
            return LogicValue.LOGIC_1
        else:
            return LogicValue.LOGIC_X
    
    @staticmethod
    def from_str(s: str) -> 'LogicValue':
        s = s.strip().lower()
        if s in ['0', 'false', 'low']:
            return LogicValue.LOGIC_0
        elif s in ['1', 'true', 'high']:
            return LogicValue.LOGIC_1
        elif s in ['x', 'unknown']:
            return LogicValue.LOGIC_X
        else:
            return LogicValue.LOGIC_Z


@dataclass
class Signal:
    """A digital signal (wire or register)."""
    name: str
    width: int = 1
    values: List[LogicValue] = field(default_factory=list)
    is_reg: bool = False
    
    def __post_init__(self):
        if not self.values:
            self.values = [LogicValue.LOGIC_X] * self.width
    
    @property
    def value(self) -> LogicValue:
        """Get value for single-bit signals."""
        return self.values[0]
    
    @value.setter
    def value(self, val: LogicValue):
        """Set value for single-bit signals."""
        self.values[0] = val
    
    def get_int(self) -> int:
        """Get integer value of the signal."""
        result = 0
        for i, v in enumerate(self.values):
            if v == LogicValue.LOGIC_1:
                result |= (1 << i)
        return result
    
    def set_int(self, val: int):
        """Set signal from integer value."""
        for i in range(self.width):
            self.values[i] = LogicValue.LOGIC_1 if (val >> i) & 1 else LogicValue.LOGIC_0


@dataclass
class Event:
    """A simulation event."""
    time: int
    signal_name: str
    new_value: LogicValue
    bit_index: int = 0
    
    def __lt__(self, other):
        return self.time < other.time


@dataclass
class Gate:
    """A digital gate."""
    name: str
    gate_type: str
    inputs: List[str]
    output: str
    delay: int = 1  # Gate delay in time units
    params: Dict = field(default_factory=dict)


class DigitalEngine:
    """
    Event-driven digital simulator with four-state logic.
    Supports Verilog-style gate-level and behavioral simulation.
    """
    
    def __init__(self):
        self._signals: Dict[str, Signal] = {}
        self._gates: List[Gate] = []
        self._event_queue: List[Event] = []
        self._time: int = 0
        self._max_time: int = 1000
        self._time_scale: float = 1e-9  # 1ns default
        
        # Signal change callbacks
        self._signal_callbacks: Dict[str, List[Callable]] = {}
        
        # Waveform storage
        self._waveforms: Dict[str, List[Tuple[int, LogicValue]]] = {}
        
        # Always blocks
        self._always_blocks: List[dict] = []
        self._initial_blocks: List[dict] = []
    
    def add_signal(self, name: str, width: int = 1, is_reg: bool = False) -> Signal:
        """Add a signal to the simulation."""
        sig = Signal(name=name, width=width, is_reg=is_reg)
        self._signals[name] = sig
        self._waveforms[name] = [(0, sig.value)]
        return sig
    
    def get_signal(self, name: str) -> Optional[Signal]:
        """Get a signal by name."""
        return self._signals.get(name)
    
    def add_gate(self, gate_type: str, name: str, output: str, inputs: List[str], delay: int = 1):
        """Add a gate to the simulation."""
        gate = Gate(
            name=name,
            gate_type=gate_type.lower(),
            inputs=inputs,
            output=output,
            delay=delay
        )
        self._gates.append(gate)
        
        # Ensure signals exist
        if output not in self._signals:
            self.add_signal(output)
        for inp in inputs:
            if inp not in self._signals:
                self.add_signal(inp)
    
    def schedule_event(self, time: int, signal_name: str, value: LogicValue, bit_index: int = 0):
        """Schedule a signal change event."""
        event = Event(time=time, signal_name=signal_name, new_value=value, bit_index=bit_index)
        heapq.heappush(self._event_queue, event)
    
    def set_signal(self, name: str, value: LogicValue, delay: int = 0):
        """Set a signal value with optional delay."""
        if delay > 0:
            self.schedule_event(self._time + delay, name, value)
        else:
            if name in self._signals:
                old_value = self._signals[name].value
                self._signals[name].value = value
                
                # Record waveform
                if name in self._waveforms:
                    self._waveforms[name].append((self._time, value))
                
                # Trigger callbacks
                if old_value != value and name in self._signal_callbacks:
                    for callback in self._signal_callbacks[name]:
                        callback(name, value, self._time)
    
    def evaluate_gate(self, gate: Gate) -> LogicValue:
        """Evaluate a gate's output."""
        # Get input values
        inputs = []
        for inp in gate.inputs:
            if inp in self._signals:
                inputs.append(self._signals[inp].value)
            else:
                inputs.append(LogicValue.LOGIC_X)
        
        gate_type = gate.gate_type
        
        # Handle X and Z propagation
        has_x = any(v == LogicValue.LOGIC_X for v in inputs)
        has_z = any(v == LogicValue.LOGIC_Z for v in inputs)
        
        if gate_type == 'and':
            if any(v == LogicValue.LOGIC_0 for v in inputs):
                return LogicValue.LOGIC_0
            elif has_x or has_z:
                return LogicValue.LOGIC_X
            return LogicValue.LOGIC_1
        
        elif gate_type == 'nand':
            if any(v == LogicValue.LOGIC_0 for v in inputs):
                return LogicValue.LOGIC_1
            elif has_x or has_z:
                return LogicValue.LOGIC_X
            return LogicValue.LOGIC_0
        
        elif gate_type == 'or':
            if any(v == LogicValue.LOGIC_1 for v in inputs):
                return LogicValue.LOGIC_1
            elif has_x or has_z:
                return LogicValue.LOGIC_X
            return LogicValue.LOGIC_0
        
        elif gate_type == 'nor':
            if any(v == LogicValue.LOGIC_1 for v in inputs):
                return LogicValue.LOGIC_0
            elif has_x or has_z:
                return LogicValue.LOGIC_X
            return LogicValue.LOGIC_1
        
        elif gate_type == 'xor':
            if has_x or has_z:
                return LogicValue.LOGIC_X
            ones = sum(1 for v in inputs if v == LogicValue.LOGIC_1)
            return LogicValue.LOGIC_1 if ones % 2 == 1 else LogicValue.LOGIC_0
        
        elif gate_type == 'xnor':
            if has_x or has_z:
                return LogicValue.LOGIC_X
            ones = sum(1 for v in inputs if v == LogicValue.LOGIC_1)
            return LogicValue.LOGIC_0 if ones % 2 == 1 else LogicValue.LOGIC_1
        
        elif gate_type in ['not', 'inv', 'inverter']:
            if len(inputs) > 0:
                if inputs[0] == LogicValue.LOGIC_0:
                    return LogicValue.LOGIC_1
                elif inputs[0] == LogicValue.LOGIC_1:
                    return LogicValue.LOGIC_0
                else:
                    return LogicValue.LOGIC_X
        
        elif gate_type in ['buf', 'buffer']:
            if len(inputs) > 0:
                return inputs[0]
        
        return LogicValue.LOGIC_X
    
    def propagate(self):
        """Propagate signals through all gates."""
        changed = True
        iterations = 0
        max_iterations = 1000  # Prevent infinite loops
        
        while changed and iterations < max_iterations:
            changed = False
            iterations += 1
            
            for gate in self._gates:
                new_value = self.evaluate_gate(gate)
                old_value = self._signals[gate.output].value if gate.output in self._signals else LogicValue.LOGIC_X
                
                if new_value != old_value:
                    self.schedule_event(self._time + gate.delay, gate.output, new_value)
                    changed = True
    
    def process_events(self):
        """Process all events at current time."""
        while self._event_queue and self._event_queue[0].time == self._time:
            event = heapq.heappop(self._event_queue)
            self.set_signal(event.signal_name, event.new_value)
    
    def run(self, max_time: Optional[int] = None, progress_callback: Optional[Callable] = None) -> dict:
        """Run the simulation."""
        if max_time is not None:
            self._max_time = max_time
        
        self._time = 0
        
        # Initialize all gates
        self.propagate()
        
        while self._time <= self._max_time:
            if progress_callback:
                progress_callback(self._time / self._max_time)
            
            # Process events at current time
            self.process_events()
            
            # Propagate changes
            self.propagate()
            
            # Advance to next event
            if self._event_queue:
                self._time = self._event_queue[0].time
            else:
                self._time = self._max_time + 1
        
        return self.get_results()
    
    def get_results(self) -> dict:
        """Get simulation results."""
        results = {
            'type': 'digital',
            'time_scale': self._time_scale,
            'max_time': self._max_time,
        }
        
        for name, waveform in self._waveforms.items():
            times = [t * self._time_scale for t, _ in waveform]
            values = [str(v) for _, v in waveform]
            results[name] = {'times': times, 'values': values}
        
        return results
    
    def load_verilog(self, verilog_code: str):
        """Load a Verilog module."""
        # Simple Verilog parser for gate-level netlists
        lines = verilog_code.split('\n')
        
        current_module = None
        
        for line in lines:
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('//'):
                continue
            
            # Module declaration
            module_match = re.match(r'module\s+(\w+)\s*\(([^)]*)\)\s*;', line)
            if module_match:
                current_module = module_match.group(1)
                ports = [p.strip() for p in module_match.group(2).split(',')]
                continue
            
            # Wire/reg declaration
            wire_match = re.match(r'(wire|reg)\s+(\[(\d+):(\d+)\])?\s*(\w+)\s*;', line)
            if wire_match:
                is_reg = wire_match.group(1) == 'reg'
                msb = int(wire_match.group(3)) if wire_match.group(3) else 0
                lsb = int(wire_match.group(4)) if wire_match.group(4) else 0
                name = wire_match.group(5)
                width = msb - lsb + 1
                self.add_signal(name, width=width, is_reg=is_reg)
                continue
            
            # Input/output declaration
            io_match = re.match(r'(input|output)\s+(\[(\d+):(\d+)\])?\s*(\w+)\s*;', line)
            if io_match:
                msb = int(io_match.group(3)) if io_match.group(3) else 0
                lsb = int(io_match.group(4)) if io_match.group(4) else 0
                name = io_match.group(5)
                width = msb - lsb + 1
                self.add_signal(name, width=width)
                continue
            
            # Gate instantiation
            gate_match = re.match(r'(and|or|not|nand|nor|xor|xnor|buf)\s+(\w+)\s*\(([^)]+)\)\s*;', line, re.IGNORECASE)
            if gate_match:
                gate_type = gate_match.group(1).lower()
                gate_name = gate_match.group(2)
                ports = [p.strip() for p in gate_match.group(3).split(',')]
                
                if gate_type in ['not', 'buf']:
                    output = ports[0]
                    inputs = ports[1:]
                else:
                    output = ports[0]
                    inputs = ports[1:]
                
                self.add_gate(gate_type, gate_name, output, inputs)
                continue
            
            # Continuous assignment
            assign_match = re.match(r'assign\s+(\w+)\s*=\s*(.+);', line)
            if assign_match:
                output = assign_match.group(1)
                expr = assign_match.group(2).strip()
                self._parse_assignment(output, expr)
                continue
    
    def _parse_assignment(self, output: str, expr: str):
        """Parse a continuous assignment expression."""
        # Handle simple operators
        expr = expr.strip()
        
        # NOT
        if expr.startswith('~'):
            inp = expr[1:].strip()
            self.add_gate('not', f'assign_{output}', output, [inp])
            return
        
        # AND
        if '&' in expr and not expr.startswith('&'):
            inputs = [s.strip() for s in expr.split('&')]
            self.add_gate('and', f'assign_{output}', output, inputs)
            return
        
        # OR
        if '|' in expr:
            inputs = [s.strip() for s in expr.split('|')]
            self.add_gate('or', f'assign_{output}', output, inputs)
            return
        
        # XOR
        if '^' in expr:
            inputs = [s.strip() for s in expr.split('^')]
            self.add_gate('xor', f'assign_{output}', output, inputs)
            return
        
        # Buffer (direct assignment)
        if expr and not any(c in expr for c in '~&|^'):
            self.add_gate('buf', f'assign_{output}', output, [expr])


class VerilogParser:
    """Enhanced Verilog parser for behavioral constructs."""
    
    def __init__(self, engine: DigitalEngine):
        self.engine = engine
        self._tokens = []
        self._pos = 0
    
    def parse(self, code: str):
        """Parse Verilog code."""
        self._tokenize(code)
        self._parse_module()
    
    def _tokenize(self, code: str):
        """Tokenize Verilog code."""
        # Remove comments
        code = re.sub(r'//.*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        
        # Tokenize
        token_pattern = r'''
            (\d+'[bBhHdDoO][0-9a-fA-FxXzZ_]+)  | # Number literals
            (\d+)                              | # Decimal numbers
            (\w+)                              | # Identifiers
            (<=|>=|==|!=|&&|\|\||<<|>>)        | # Multi-char operators
            ([;,\(\)\[\]{}:=+\-*&|^~!<>@#])     # Single-char operators
        '''
        
        self._tokens = []
        for match in re.finditer(token_pattern, code, re.VERBOSE):
            token = match.group(0)
            if token.strip():
                self._tokens.append(token)
        
        self._pos = 0
    
    def _current(self) -> Optional[str]:
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return None
    
    def _advance(self) -> Optional[str]:
        token = self._current()
        self._pos += 1
        return token
    
    def _expect(self, expected: str):
        token = self._advance()
        if token != expected:
            raise SyntaxError(f"Expected '{expected}', got '{token}'")
    
    def _parse_module(self):
        """Parse a module declaration."""
        if self._current() != 'module':
            return
        
        self._advance()  # module
        module_name = self._advance()  # module name
        
        self._expect('(')
        
        # Parse port list
        ports = []
        while self._current() != ')':
            port = self._advance()
            if port and port != ',':
                ports.append(port)
        
        self._expect(')')
        self._expect(';')
        
        # Parse module body
        while self._current() not in [None, 'endmodule']:
            self._parse_statement()
        
        if self._current() == 'endmodule':
            self._advance()
    
    def _parse_statement(self):
        """Parse a statement."""
        keyword = self._current()
        
        if keyword == 'input':
            self._parse_port_declaration('input')
        elif keyword == 'output':
            self._parse_port_declaration('output')
        elif keyword == 'wire':
            self._parse_wire_declaration()
        elif keyword == 'reg':
            self._parse_reg_declaration()
        elif keyword == 'assign':
            self._parse_continuous_assignment()
        elif keyword == 'always':
            self._parse_always_block()
        elif keyword == 'initial':
            self._parse_initial_block()
        elif keyword in ['and', 'or', 'not', 'nand', 'nor', 'xor', 'xnor', 'buf']:
            self._parse_gate_instantiation()
        else:
            self._advance()  # Skip unknown
    
    def _parse_port_declaration(self, direction: str):
        """Parse input/output declaration."""
        self._advance()  # input/output
        
        # Check for width
        width = 1
        if self._current() == '[':
            self._advance()
            msb = int(self._advance())
            self._expect(':')
            lsb = int(self._advance())
            self._expect(']')
            width = msb - lsb + 1
        
        # Port name
        name = self._advance()
        self.engine.add_signal(name, width=width)
        
        self._expect(';')
    
    def _parse_wire_declaration(self):
        """Parse wire declaration."""
        self._advance()  # wire
        
        width = 1
        if self._current() == '[':
            self._advance()
            msb = int(self._advance())
            self._expect(':')
            lsb = int(self._advance())
            self._expect(']')
            width = msb - lsb + 1
        
        name = self._advance()
        self.engine.add_signal(name, width=width)
        
        self._expect(';')
    
    def _parse_reg_declaration(self):
        """Parse reg declaration."""
        self._advance()  # reg
        
        width = 1
        if self._current() == '[':
            self._advance()
            msb = int(self._advance())
            self._expect(':')
            lsb = int(self._advance())
            self._expect(']')
            width = msb - lsb + 1
        
        name = self._advance()
        self.engine.add_signal(name, width=width, is_reg=True)
        
        self._expect(';')
    
    def _parse_continuous_assignment(self):
        """Parse assign statement."""
        self._advance()  # assign
        
        lhs = self._advance()
        self._expect('=')
        
        # Collect expression until semicolon
        expr_tokens = []
        while self._current() != ';':
            expr_tokens.append(self._advance())
        self._expect(';')
        
        expr = ' '.join(expr_tokens)
        self.engine._parse_assignment(lhs, expr)
    
    def _parse_gate_instantiation(self):
        """Parse gate instantiation."""
        gate_type = self._advance()
        gate_name = self._advance()
        
        self._expect('(')
        
        ports = []
        while self._current() != ')':
            token = self._advance()
            if token and token != ',':
                ports.append(token)
        
        self._expect(')')
        self._expect(';')
        
        if gate_type in ['not', 'buf']:
            output = ports[0]
            inputs = ports[1:]
        else:
            output = ports[0]
            inputs = ports[1:]
        
        self.engine.add_gate(gate_type, gate_name, output, inputs)
    
    def _parse_always_block(self):
        """Parse always block (simplified)."""
        self._advance()  # always
        
        # Skip sensitivity list
        if self._current() == '@':
            self._advance()
            if self._current() == '(':
                depth = 0
                while True:
                    token = self._advance()
                    if token == '(':
                        depth += 1
                    elif token == ')':
                        depth -= 1
                        if depth == 0:
                            break
        
        # Parse block body
        if self._current() == 'begin':
            self._advance()
            while self._current() != 'end':
                self._advance()
            self._advance()  # end
    
    def _parse_initial_block(self):
        """Parse initial block (simplified)."""
        self._advance()  # initial
        
        if self._current() == 'begin':
            self._advance()
            while self._current() != 'end':
                self._advance()
            self._advance()  # end
