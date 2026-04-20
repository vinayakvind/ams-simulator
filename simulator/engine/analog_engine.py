"""
Analog Simulation Engine - SPICE-like circuit simulator.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve
import re


@dataclass
class CircuitNode:
    """Represents a node in the circuit."""
    name: str
    index: int = -1  # Matrix index
    voltage: float = 0.0
    is_ground: bool = False


@dataclass
class CircuitElement:
    """Base class for circuit elements."""
    name: str
    nodes: List[str]
    value: float = 0.0
    model: Optional[str] = None
    params: Dict[str, float] = field(default_factory=dict)


class AnalogEngine:
    """
    SPICE-like analog circuit simulator.
    
    Implements Modified Nodal Analysis (MNA) for circuit simulation
    supporting DC, AC, and Transient analysis.
    """
    
    def __init__(self):
        self._nodes: Dict[str, CircuitNode] = {}
        self._elements: List[CircuitElement] = []
        self._models: Dict[str, dict] = {}
        self._num_nodes = 0
        self._num_vsources = 0
        
        # MNA matrices
        self._G = None  # Conductance matrix
        self._C = None  # Capacitance matrix
        self._B = None  # Voltage source contribution
        self._I = None  # Current vector
        
        # Simulation results
        self._solution = None
        
        # Default models
        self._init_default_models()
    
    def _init_default_models(self):
        """Initialize default device models."""
        self._models['NMOS_DEFAULT'] = {
            'type': 'nmos',
            'vth0': 0.4,
            'kp': 120e-6,
            'lambda': 0.01,
        }
        self._models['PMOS_DEFAULT'] = {
            'type': 'pmos',
            'vth0': -0.4,
            'kp': 40e-6,
            'lambda': 0.01,
        }
        self._models['NPN_DEFAULT'] = {
            'type': 'npn',
            'bf': 100,
            'is': 1e-14,
            'vaf': 100,
        }
        self._models['PNP_DEFAULT'] = {
            'type': 'pnp',
            'bf': 100,
            'is': 1e-14,
            'vaf': 100,
        }
        self._models['D1N4148'] = {
            'type': 'diode',
            'is': 2.52e-9,
            'n': 1.752,
            'bv': 100,
            'rs': 0.568,
        }
    
    def load_netlist(self, netlist: str):
        """Load circuit from netlist string."""
        self._nodes.clear()
        self._elements.clear()
        self._num_vsources = 0
        
        # Add ground node
        self._nodes['0'] = CircuitNode(name='0', index=0, is_ground=True)
        self._nodes['GND'] = self._nodes['0']
        
        # Pre-process: join SPICE continuation lines (lines starting with '+')
        raw_lines = netlist.strip().split('\n')
        joined_lines: list[str] = []
        for raw in raw_lines:
            stripped = raw.strip()
            if stripped.startswith('+'):
                # Append to previous logical line
                if joined_lines:
                    joined_lines[-1] += ' ' + stripped[1:].strip()
                continue
            joined_lines.append(stripped)
        
        for line in joined_lines:
            # Skip empty lines and comments
            if not line or line.startswith('*'):
                continue
            
            # Handle directives
            if line.startswith('.'):
                self._parse_directive(line)
                continue
            
            # Parse element
            self._parse_element(line)
        
        # Assign node indices
        self._assign_node_indices()
    
    def _parse_directive(self, line: str):
        """Parse a SPICE directive."""
        parts = line.upper().split()
        directive = parts[0]
        
        if directive == '.MODEL':
            self._parse_model(line)
        elif directive == '.END':
            pass
        # Other directives handled by analysis classes
    
    def _parse_model(self, line: str):
        """Parse a .MODEL directive."""
        # .MODEL name type (params)
        match = re.match(r'\.MODEL\s+(\w+)\s+(\w+)\s*\(([^)]*)\)', line, re.IGNORECASE)
        if match:
            name = match.group(1)
            mtype = match.group(2).lower()
            params_str = match.group(3)
            
            params = {'type': mtype}
            for param in params_str.split():
                if '=' in param:
                    key, val = param.split('=')
                    params[key.lower()] = self._parse_value(val)
            
            self._models[name] = params
    
    def _parse_element(self, line: str):
        """Parse a circuit element."""
        parts = line.split()
        if not parts:
            return
        
        name = parts[0]
        prefix = name[0].upper()
        
        if prefix == 'R':
            # Resistor: R<name> <n+> <n-> <value>
            self._add_node(parts[1])
            self._add_node(parts[2])
            elem = CircuitElement(
                name=name,
                nodes=[parts[1], parts[2]],
                value=self._parse_value(parts[3])
            )
            self._elements.append(elem)
        
        elif prefix == 'C':
            # Capacitor: C<name> <n+> <n-> <value> [IC=<v>]
            self._add_node(parts[1])
            self._add_node(parts[2])
            elem = CircuitElement(
                name=name,
                nodes=[parts[1], parts[2]],
                value=self._parse_value(parts[3])
            )
            # Check for initial condition
            for part in parts[4:]:
                if part.upper().startswith('IC='):
                    elem.params['ic'] = self._parse_value(part[3:])
            self._elements.append(elem)
        
        elif prefix == 'L':
            # Inductor: L<name> <n+> <n-> <value> [IC=<i>]
            self._add_node(parts[1])
            self._add_node(parts[2])
            elem = CircuitElement(
                name=name,
                nodes=[parts[1], parts[2]],
                value=self._parse_value(parts[3])
            )
            for part in parts[4:]:
                if part.upper().startswith('IC='):
                    elem.params['ic'] = self._parse_value(part[3:])
            self._elements.append(elem)
        
        elif prefix == 'V':
            # Voltage source: V<name> <n+> <n-> [DC <v>] [AC <mag> [<phase>]]
            self._add_node(parts[1])
            self._add_node(parts[2])
            elem = CircuitElement(
                name=name,
                nodes=[parts[1], parts[2]],
            )
            self._parse_source_value(elem, parts[3:])
            self._elements.append(elem)
            self._num_vsources += 1
        
        elif prefix == 'I':
            # Current source: I<name> <n+> <n-> [DC <i>] [AC <mag> [<phase>]]
            self._add_node(parts[1])
            self._add_node(parts[2])
            elem = CircuitElement(
                name=name,
                nodes=[parts[1], parts[2]],
            )
            self._parse_source_value(elem, parts[3:])
            self._elements.append(elem)
        
        elif prefix == 'M':
            # MOSFET: M<name> <nd> <ng> <ns> <nb> <model> [W=<w>] [L=<l>]
            for node in parts[1:5]:
                self._add_node(node)
            elem = CircuitElement(
                name=name,
                nodes=parts[1:5],
                model=parts[5] if len(parts) > 5 else 'NMOS_DEFAULT'
            )
            for part in parts[6:]:
                if '=' in part:
                    key, val = part.split('=')
                    elem.params[key.lower()] = self._parse_value(val)
            self._elements.append(elem)
        
        elif prefix == 'Q':
            # BJT: Q<name> <nc> <nb> <ne> <model>
            for node in parts[1:4]:
                self._add_node(node)
            elem = CircuitElement(
                name=name,
                nodes=parts[1:4],
                model=parts[4] if len(parts) > 4 else 'NPN_DEFAULT'
            )
            self._elements.append(elem)
        
        elif prefix == 'D':
            # Diode: D<name> <na> <nk> <model>
            self._add_node(parts[1])
            self._add_node(parts[2])
            elem = CircuitElement(
                name=name,
                nodes=[parts[1], parts[2]],
                model=parts[3] if len(parts) > 3 else 'D1N4148'
            )
            self._elements.append(elem)
        
        elif prefix == 'E':
            # VCVS: E<name> <n+> <n-> <nc+> <nc-> <gain>
            # Also: E<name> <n+> <n-> VCVS <nc+> <nc-> <gain>
            # TABLE/POLY forms stored but flagged unsupported
            self._add_node(parts[1])
            self._add_node(parts[2])
            rest = ' '.join(parts[3:]).upper()
            if 'TABLE' in rest or 'POLY' in rest:
                elem = CircuitElement(
                    name=name,
                    nodes=[parts[1], parts[2]],
                    params={'unsupported': True, 'definition': ' '.join(parts[3:])}
                )
                self._elements.append(elem)
                self._num_vsources += 1
            else:
                offset = 3
                if len(parts) > 3 and parts[3].upper() == 'VCVS':
                    offset = 4
                nc_plus = parts[offset]
                nc_minus = parts[offset + 1]
                gain = self._parse_value(parts[offset + 2])
                self._add_node(nc_plus)
                self._add_node(nc_minus)
                elem = CircuitElement(
                    name=name,
                    nodes=[parts[1], parts[2], nc_plus, nc_minus],
                    value=gain,
                )
                self._elements.append(elem)
                self._num_vsources += 1
        
        elif prefix == 'G':
            # VCCS: G<name> <n+> <n-> <nc+> <nc-> <gm>
            for node in parts[1:5]:
                self._add_node(node)
            elem = CircuitElement(
                name=name,
                nodes=parts[1:5],
                value=self._parse_value(parts[5])
            )
            self._elements.append(elem)
        
        elif prefix == 'K':
            # Coupled inductors: K<name> <L1> <L2> <coupling>
            elem = CircuitElement(
                name=name,
                nodes=[],
                value=self._parse_value(parts[3]) if len(parts) > 3 else 0.98,
                params={'l1': parts[1], 'l2': parts[2]}
            )
            self._elements.append(elem)
        
        elif prefix == 'S':
            # Voltage-controlled switch: S<name> <n+> <n-> <nc+> <nc-> <model>
            for node in parts[1:5]:
                self._add_node(node)
            elem = CircuitElement(
                name=name,
                nodes=parts[1:5],
                model=parts[5] if len(parts) > 5 else None
            )
            self._elements.append(elem)
    
    def _parse_source_value(self, elem: CircuitElement, parts: List[str]):
        """Parse source value specification."""
        i = 0
        while i < len(parts):
            part = parts[i].upper()
            
            if part == 'DC':
                elem.value = self._parse_value(parts[i+1])
                i += 2
            elif part == 'AC':
                elem.params['ac_mag'] = self._parse_value(parts[i+1])
                if i+2 < len(parts) and not parts[i+2].upper() in ['DC', 'PULSE', 'SIN', 'PWL']:
                    elem.params['ac_phase'] = self._parse_value(parts[i+2])
                    i += 3
                else:
                    i += 2
            elif part.startswith('PULSE'):
                # PULSE(v1 v2 td tr tf pw per)
                pulse_match = re.search(r'PULSE\s*\(([^)]+)\)', ' '.join(parts[i:]), re.IGNORECASE)
                if pulse_match:
                    pulse_params = pulse_match.group(1).split()
                    elem.params['type'] = 'pulse'
                    elem.params['v1'] = self._parse_value(pulse_params[0])
                    elem.params['v2'] = self._parse_value(pulse_params[1])
                    if len(pulse_params) > 2:
                        elem.params['td'] = self._parse_value(pulse_params[2])
                    if len(pulse_params) > 3:
                        elem.params['tr'] = self._parse_value(pulse_params[3])
                    if len(pulse_params) > 4:
                        elem.params['tf'] = self._parse_value(pulse_params[4])
                    if len(pulse_params) > 5:
                        elem.params['pw'] = self._parse_value(pulse_params[5])
                    if len(pulse_params) > 6:
                        elem.params['per'] = self._parse_value(pulse_params[6])
                break
            elif part.startswith('SIN'):
                # SIN(vo va freq td theta phase)
                sin_match = re.search(r'SIN\s*\(([^)]+)\)', ' '.join(parts[i:]), re.IGNORECASE)
                if sin_match:
                    sin_params = sin_match.group(1).split()
                    elem.params['type'] = 'sin'
                    elem.params['vo'] = self._parse_value(sin_params[0])
                    elem.params['va'] = self._parse_value(sin_params[1])
                    if len(sin_params) > 2:
                        elem.params['freq'] = self._parse_value(sin_params[2])
                break
            else:
                # Assume DC value
                elem.value = self._parse_value(part)
                i += 1
    
    def _parse_value(self, value_str: str) -> float:
        """Parse a value string with optional SI suffix and unit.
        
        Handles standard SPICE value notation where trailing
        characters after the SI multiplier are unit labels (ignored):
          5V → 5.0,  10k → 10e3,  47uH → 47e-6,  100nF → 100e-9,
          1.25V → 1.25,  3.3V → 3.3,  1MEG → 1e6,  2.52e-9 → 2.52e-9
        """
        value_str = value_str.strip()
        if not value_str:
            return 0.0
        
        # Separate numeric part from alpha suffix using regex
        match = re.match(
            r'^([+-]?[\d.]+(?:[eE][+-]?\d+)?)(.*)', value_str
        )
        if not match:
            return 0.0
        
        num_str = match.group(1)
        suffix_str = match.group(2).strip().upper()
        
        try:
            num = float(num_str)
        except ValueError:
            return 0.0
        
        if not suffix_str:
            return num
        
        # SI multiplier prefixes (longest match first)
        multipliers = [
            ('MEG', 1e6),
            ('T', 1e12),
            ('G', 1e9),
            ('K', 1e3),
            ('M', 1e-3),
            ('U', 1e-6),
            ('N', 1e-9),
            ('P', 1e-12),
            ('F', 1e-15),
        ]
        
        for prefix, mult in multipliers:
            if suffix_str.startswith(prefix):
                return num * mult
        
        # No SI multiplier — suffix is a unit label, ignore it
        return num
    
    def _add_node(self, name: str):
        """Add a node if it doesn't exist."""
        name_upper = name.upper()
        # Check if this is a ground reference
        if name == '0' or name_upper == 'GND':
            return  # Ground already added in load_netlist
        if name_upper not in self._nodes and name not in self._nodes:
            self._nodes[name] = CircuitNode(name=name)
    
    def _assign_node_indices(self):
        """Assign matrix indices to nodes."""
        index = 0
        for name, node in self._nodes.items():
            if not node.is_ground:
                node.index = index
                index += 1
        self._num_nodes = index
    
    def _get_node_index(self, name: str) -> int:
        """Get the matrix index for a node. Returns -1 for ground."""
        # Check for ground reference
        if name == '0' or name.upper() == 'GND':
            return -1
        if name in self._nodes:
            node = self._nodes[name]
            if node.is_ground:
                return -1
            return node.index
        name_upper = name.upper()
        if name_upper in self._nodes:
            node = self._nodes[name_upper]
            if node.is_ground:
                return -1
            return node.index
        return -1  # Unknown node treated as ground
    
    def build_mna_matrices(self, dc_inductors=True):
        """Build the MNA matrices for DC analysis."""
        n = self._num_nodes + self._num_vsources
        
        self._G = np.zeros((n, n))
        self._C = np.zeros((n, n))
        self._I = np.zeros(n)
        
        vsource_idx = self._num_nodes
        
        for elem in self._elements:
            prefix = elem.name[0].upper()
            
            if prefix == 'R':
                # Resistor: stamp conductance
                n1 = self._get_node_index(elem.nodes[0])
                n2 = self._get_node_index(elem.nodes[1])
                g = 1.0 / elem.value if elem.value != 0 else 0
                
                if n1 >= 0:
                    self._G[n1, n1] += g
                if n2 >= 0:
                    self._G[n2, n2] += g
                if n1 >= 0 and n2 >= 0:
                    self._G[n1, n2] -= g
                    self._G[n2, n1] -= g
            
            elif prefix == 'C':
                # Capacitor: stamp capacitance for transient
                n1 = self._get_node_index(elem.nodes[0])
                n2 = self._get_node_index(elem.nodes[1])
                c = elem.value
                
                if n1 >= 0:
                    self._C[n1, n1] += c
                if n2 >= 0:
                    self._C[n2, n2] += c
                if n1 >= 0 and n2 >= 0:
                    self._C[n1, n2] -= c
                    self._C[n2, n1] -= c
            
            elif prefix == 'V':
                # Voltage source: stamp B matrix
                n1 = self._get_node_index(elem.nodes[0])
                n2 = self._get_node_index(elem.nodes[1])
                vs_idx = vsource_idx
                vsource_idx += 1
                
                if n1 >= 0:
                    self._G[n1, vs_idx] += 1
                    self._G[vs_idx, n1] += 1
                if n2 >= 0:
                    self._G[n2, vs_idx] -= 1
                    self._G[vs_idx, n2] -= 1
                
                self._I[vs_idx] = elem.value
            
            elif prefix == 'I':
                # Current source: stamp current vector
                n1 = self._get_node_index(elem.nodes[0])
                n2 = self._get_node_index(elem.nodes[1])
                
                if n1 >= 0:
                    self._I[n1] -= elem.value
                if n2 >= 0:
                    self._I[n2] += elem.value
            
            elif prefix == 'L':
                if dc_inductors:
                    # DC: inductor is short circuit (very high conductance)
                    n1 = self._get_node_index(elem.nodes[0])
                    n2 = self._get_node_index(elem.nodes[1])
                    g_short = 1e3  # Equivalent to 1mOhm
                    if n1 >= 0:
                        self._G[n1, n1] += g_short
                    if n2 >= 0:
                        self._G[n2, n2] += g_short
                    if n1 >= 0 and n2 >= 0:
                        self._G[n1, n2] -= g_short
                        self._G[n2, n1] -= g_short
            
            elif prefix == 'E':
                # VCVS: adds constraint row like voltage source
                vs_idx = vsource_idx
                vsource_idx += 1
                n_plus = self._get_node_index(elem.nodes[0])
                n_minus = self._get_node_index(elem.nodes[1])
                
                # Current through E enters n+, leaves n-
                if n_plus >= 0:
                    self._G[n_plus, vs_idx] += 1
                    self._G[vs_idx, n_plus] += 1
                if n_minus >= 0:
                    self._G[n_minus, vs_idx] -= 1
                    self._G[vs_idx, n_minus] -= 1
                
                if not elem.params.get('unsupported'):
                    # Simple VCVS: V(n+)-V(n-)=gain*(V(nc+)-V(nc-))
                    gain = elem.value
                    nc_plus = self._get_node_index(elem.nodes[2])
                    nc_minus = self._get_node_index(elem.nodes[3])
                    if nc_plus >= 0:
                        self._G[vs_idx, nc_plus] -= gain
                    if nc_minus >= 0:
                        self._G[vs_idx, nc_minus] += gain
                # Unsupported (TABLE/POLY): output forced to 0V
            
            elif prefix == 'G':
                # VCCS: I = gm*(V(nc+)-V(nc-)) from n+ to n-
                n_plus = self._get_node_index(elem.nodes[0])
                n_minus = self._get_node_index(elem.nodes[1])
                nc_plus = self._get_node_index(elem.nodes[2])
                nc_minus = self._get_node_index(elem.nodes[3])
                gm = elem.value
                
                if n_plus >= 0 and nc_plus >= 0:
                    self._G[n_plus, nc_plus] += gm
                if n_plus >= 0 and nc_minus >= 0:
                    self._G[n_plus, nc_minus] -= gm
                if n_minus >= 0 and nc_plus >= 0:
                    self._G[n_minus, nc_plus] -= gm
                if n_minus >= 0 and nc_minus >= 0:
                    self._G[n_minus, nc_minus] += gm
    
    def _stamp_mosfet(self, elem: CircuitElement, v: np.ndarray):
        """Stamp MOSFET Level-1 model (Shichman-Hodges) using Newton-Raphson."""
        # Get node indices
        nd = self._get_node_index(elem.nodes[0])  # Drain
        ng = self._get_node_index(elem.nodes[1])  # Gate
        ns = self._get_node_index(elem.nodes[2])  # Source
        nb = self._get_node_index(elem.nodes[3]) if len(elem.nodes) > 3 else ns  # Bulk
        
        # Get voltages
        vd = v[nd] if nd >= 0 else 0.0
        vg = v[ng] if ng >= 0 else 0.0
        vs = v[ns] if ns >= 0 else 0.0
        vb = v[nb] if nb >= 0 else 0.0
        
        vgs = vg - vs
        vds = vd - vs
        vbs = vb - vs
        
        # Get model parameters (prefer elem.model set by parser, fallback to params)
        model_name = elem.model or elem.params.get('model', 'NMOS_DEFAULT')
        model = self._models.get(model_name)
        if model is None:
            model = self._models.get(model_name.upper())
        if model is None:
            # Infer default from model name: names containing 'pmos'/'PMOS' → PMOS_DEFAULT
            name_up = model_name.upper()
            if 'PMOS' in name_up or name_up.startswith('P'):
                model = self._models.get('PMOS_DEFAULT', {})
            else:
                model = self._models.get('NMOS_DEFAULT', {})
        
        # Determine PMOS vs NMOS from model type
        is_pmos = model.get('type', 'nmos').lower() == 'pmos'
        
        vto = model.get('VTO', model.get('vto', model.get('vth0', -0.7 if is_pmos else 0.7)))
        kp = model.get('KP', model.get('kp', 40e-6 if is_pmos else 120e-6))
        lambda_val = model.get('LAMBDA', model.get('lambda', 0.01))
        w = elem.params.get('W', elem.params.get('w', 10e-6))
        l = elem.params.get('L', elem.params.get('l', 1e-6))
        
        # For PMOS, invert voltages so equations produce positive current
        if is_pmos:
            vgs = -vgs
            vds = -vds
            vbs = -vbs
            vto = abs(vto)  # Use positive threshold for equation
        
        # Body effect
        gamma = model.get('GAMMA', 0.4)
        phi = model.get('PHI', 0.8)
        vth = vto + gamma * (np.sqrt(np.abs(phi - vbs)) - np.sqrt(phi))
        
        # Calculate drain current and derivatives
        vgs_eff = vgs - vth
        
        if vgs_eff <= 0:
            # Cutoff
            ids = 0.0
            gm = 0.0
            gds = 0.0
            gmbs = 0.0
        elif vds < vgs_eff:
            # Linear region
            beta = kp * w / l
            ids = beta * (vgs_eff * vds - 0.5 * vds**2) * (1 + lambda_val * vds)
            gm = beta * vds * (1 + lambda_val * vds)
            gds = beta * (vgs_eff - vds) * (1 + lambda_val * vds) + beta * (vgs_eff * vds - 0.5 * vds**2) * lambda_val
            gmbs = -gm * gamma / (2 * np.sqrt(np.abs(phi - vbs) + 1e-12))
        else:
            # Saturation region
            beta = kp * w / l
            ids = 0.5 * beta * vgs_eff**2 * (1 + lambda_val * vds)
            gm = beta * vgs_eff * (1 + lambda_val * vds)
            gds = 0.5 * beta * vgs_eff**2 * lambda_val
            gmbs = -gm * gamma / (2 * np.sqrt(np.abs(phi - vbs) + 1e-12))
        
        # For PMOS, invert current direction (current flows source to drain)
        if is_pmos:
            ids = -ids
        
        # Compute offset current for Newton-Raphson linearization:
        #   I_d = gm*(Vg-Vs) + gds*(Vd-Vs) + gmbs*(Vb-Vs) + ids_offset
        # For NMOS: vgs/vds/vbs are the actual node voltages
        # For PMOS: vgs/vds/vbs are INVERTED (positive), so actual = -inverted
        if is_pmos:
            # ids_offset = ids_actual - gm*Vgs_actual - gds*Vds_actual - gmbs*Vbs_actual
            # Vgs_actual = -vgs, etc., so: ids - gm*(-vgs) - gds*(-vds) - gmbs*(-vbs)
            ids_offset = ids + gm*vgs + gds*vds + gmbs*vbs
        else:
            ids_offset = ids - gm*vgs - gds*vds - gmbs*vbs
        
        # Stamp G matrix (conductances)
        # gds stamps (drain-source conductance: d(id)/d(vds))
        if nd >= 0 and ns >= 0:
            self._G[nd, nd] += gds
            self._G[nd, ns] -= gds
            self._G[ns, nd] -= gds
            self._G[ns, ns] += gds
        elif nd >= 0:
            self._G[nd, nd] += gds
        elif ns >= 0:
            self._G[ns, ns] += gds
            
        # gm stamps (transconductance: d(id)/d(vgs), vgs = vg - vs)
        # Drain KCL: d(id)/d(vg) = +gm, d(id)/d(vs) = -gm
        # Source KCL: d(-id)/d(vg) = -gm, d(-id)/d(vs) = +gm
        if ng >= 0:
            if nd >= 0:
                self._G[nd, ng] += gm
            if ns >= 0:
                self._G[ns, ng] -= gm
        if ns >= 0:
            if nd >= 0:
                self._G[nd, ns] -= gm
            self._G[ns, ns] += gm
        
        # gmbs stamps (body-effect transconductance: d(id)/d(vbs), vbs = vb - vs)
        # Drain KCL: d(id)/d(vb) = +gmbs, d(id)/d(vs) = -gmbs
        # Source KCL: d(-id)/d(vb) = -gmbs, d(-id)/d(vs) = +gmbs
        if nb >= 0:
            if nd >= 0:
                self._G[nd, nb] += gmbs
            if ns >= 0:
                self._G[ns, nb] -= gmbs
        if ns >= 0:
            if nd >= 0:
                self._G[nd, ns] -= gmbs
            self._G[ns, ns] += gmbs
            
        # Stamp I vector (offset current)
        if nd >= 0:
            self._I[nd] -= ids_offset
        if ns >= 0:
            self._I[ns] += ids_offset
    
    def _stamp_bjt(self, elem: CircuitElement, v: np.ndarray):
        """Stamp BJT Ebers-Moll model using Newton-Raphson."""
        # Get node indices
        nc = self._get_node_index(elem.nodes[0])  # Collector
        nb = self._get_node_index(elem.nodes[1])  # Base
        ne = self._get_node_index(elem.nodes[2])  # Emitter
        
        # Get voltages
        vc = v[nc] if nc >= 0 else 0.0
        vb = v[nb] if nb >= 0 else 0.0
        ve = v[ne] if ne >= 0 else 0.0
        
        vbe = vb - ve
        vbc = vb - vc
        
        # Get model parameters (prefer elem.model set by parser, fallback to params)
        model_name = elem.model or elem.params.get('model', 'NPN_DEFAULT')
        model = self._models.get(model_name, self._models.get(model_name.upper(),
                    self._models.get('NPN_DEFAULT')))
        
        # Handle PNP by inverting junction voltages
        is_pnp = model.get('type', 'npn').lower() == 'pnp'
        if is_pnp:
            vbe = -vbe
            vbc = -vbc
        
        is_val = model.get('IS', model.get('is', 1e-14))  # Saturation current
        bf = model.get('BF', model.get('bf', 100))  # Forward beta
        br = model.get('BR', model.get('br', 1))  # Reverse beta
        vt = 0.026  # Thermal voltage at 300K
        
        # Ebers-Moll equations
        ief = is_val * (np.exp(vbe / vt) - 1)  # Forward emitter current
        ier = is_val * (np.exp(vbc / vt) - 1)  # Reverse emitter current
        
        ic = ief / bf - ier
        ib = ief / bf + ier / br
        ie = -ief - ier / br
        
        # Derivatives
        gm_f = is_val / (bf * vt) * np.exp(vbe / vt)
        gm_r = is_val / vt * np.exp(vbc / vt)
        
        gbe = gm_f / bf
        gbc = gm_r / br
        gce = gm_f / bf
        
        # Current offsets
        ic_offset = ic - gm_f * vbe + gm_r * vbc
        ib_offset = ib - gbe * vbe - gbc * vbc
        ie_offset = ie + gm_f * vbe + gce * vbc
        
        # Stamp base-emitter junction
        if nb >= 0 and ne >= 0:
            self._G[nb, nb] += gbe
            self._G[nb, ne] -= gbe
            self._G[ne, nb] -= gbe
            self._G[ne, ne] += gbe
            
        # Stamp base-collector junction
        if nb >= 0 and nc >= 0:
            self._G[nb, nb] += gbc
            self._G[nb, nc] -= gbc
            self._G[nc, nb] -= gbc
            self._G[nc, nc] += gbc
            
        # Stamp collector current control
        if nc >= 0 and nb >= 0:
            self._G[nc, nb] += gm_f
        if nc >= 0 and nc >= 0:
            self._G[nc, nc] -= gm_r
        if nc >= 0 and ne >= 0:
            self._G[nc, ne] -= gm_f
            
        # Stamp currents
        if nc >= 0:
            self._I[nc] -= ic_offset
        if nb >= 0:
            self._I[nb] -= ib_offset
        if ne >= 0:
            self._I[ne] -= ie_offset
    
    def _stamp_diode(self, elem: CircuitElement, v: np.ndarray):
        """Stamp diode exponential model using Newton-Raphson."""
        # Get node indices
        na = self._get_node_index(elem.nodes[0])  # Anode
        nk = self._get_node_index(elem.nodes[1])  # Cathode
        
        # Get voltages
        va = v[na] if na >= 0 else 0.0
        vk = v[nk] if nk >= 0 else 0.0
        vd = va - vk
        
        # Get model parameters (prefer elem.model set by parser, fallback to params)
        model_name = elem.model or elem.params.get('model', 'D1N4148')
        model = self._models.get(model_name, self._models.get(model_name.upper(),
                    self._models.get('D1N4148')))
        
        is_val = model.get('IS', model.get('is', 1e-14))  # Saturation current
        n = model.get('N', model.get('n', 1.0))  # Emission coefficient
        vt = 0.026  # Thermal voltage
        
        # Exponential model with limiting
        if vd > 0.5:
            # Forward bias limiting
            id_val = is_val * np.exp(0.5 / (n * vt)) * (1 + (vd - 0.5) / (n * vt))
            gd = is_val * np.exp(0.5 / (n * vt)) / (n * vt)
        else:
            id_val = is_val * (np.exp(vd / (n * vt)) - 1)
            gd = is_val / (n * vt) * np.exp(vd / (n * vt))
        
        # Current offset for Newton-Raphson
        id_offset = id_val - gd * vd
        
        # Stamp conductance
        if na >= 0 and nk >= 0:
            self._G[na, na] += gd
            self._G[na, nk] -= gd
            self._G[nk, na] -= gd
            self._G[nk, nk] += gd
        elif na >= 0:
            self._G[na, na] += gd
        elif nk >= 0:
            self._G[nk, nk] += gd
            
        # Stamp current
        if na >= 0:
            self._I[na] -= id_offset
        if nk >= 0:
            self._I[nk] += id_offset

    def solve_dc(self) -> Dict[str, float]:
        """Solve DC operating point with Newton-Raphson iteration for nonlinear devices."""
        # Check if we have nonlinear devices
        has_nonlinear = any(elem.name[0].upper() in ['M', 'Q', 'D'] for elem in self._elements)
        
        if not has_nonlinear:
            # Linear circuit - direct solve
            self.build_mna_matrices()
            
            try:
                self._solution = np.linalg.solve(self._G, self._I)
            except np.linalg.LinAlgError:
                # Try sparse solver
                G_sparse = sparse.csr_matrix(self._G)
                self._solution = spsolve(G_sparse, self._I)
        else:
            # Nonlinear circuit - Newton-Raphson iteration
            max_iter = 100
            tol = 1e-6
            
            # Count voltage sources for sizing
            num_vsources = sum(1 for elem in self._elements if elem.name[0].upper() == 'V')
            total_size = self._num_nodes + num_vsources
            
            # Initial guess: set voltages from voltage sources and propagate
            # through resistive paths for a better starting point
            v = np.zeros(total_size)
            vsrc_idx = 0
            for elem in self._elements:
                if elem.name[0].upper() == 'V':
                    n_plus = self._get_node_index(elem.nodes[0])
                    n_minus = self._get_node_index(elem.nodes[1])
                    src_val = elem.value
                    if n_plus >= 0:
                        v[n_plus] = src_val
                    if n_minus >= 0:
                        v[n_minus] = 0.0
                    vsrc_idx += 1
            
            # Propagate initial guess through resistive dividers
            for _ in range(5):  # iterate to propagate through chains
                for elem in self._elements:
                    if elem.name[0].upper() == 'R' and elem.value > 0:
                        n1 = self._get_node_index(elem.nodes[0])
                        n2 = self._get_node_index(elem.nodes[1])
                        v1 = v[n1] if n1 >= 0 else 0.0
                        v2 = v[n2] if n2 >= 0 else 0.0
                        if v1 != 0 and v2 == 0 and n2 >= 0:
                            v[n2] = v1 * 0.5  # conservative estimate
                        elif v2 != 0 and v1 == 0 and n1 >= 0:
                            v[n1] = v2 * 0.5
            
            # Use source stepping for robust convergence:
            # Ramp voltage sources from 10% to 100% in steps
            source_steps = [0.1, 0.3, 0.5, 0.7, 1.0]
            original_values = {}
            for elem in self._elements:
                if elem.name[0].upper() == 'V':
                    original_values[elem.name] = elem.value
            
            converged = False
            for step_frac in source_steps:
                # Scale voltage sources
                for elem in self._elements:
                    if elem.name[0].upper() == 'V':
                        elem.value = original_values[elem.name] * step_frac
                
                gmin = 1e-9  # start with larger gmin for stability
                damping = 0.5
                
                for iteration in range(max_iter):
                    # Build linear part of matrices
                    self.build_mna_matrices()
                    
                    # Add Gmin to diagonal (prevents singularity)
                    for i in range(self._num_nodes):
                        self._G[i, i] += gmin
                    
                    # Stamp nonlinear devices (using only node voltages)
                    v_nodes = v[:self._num_nodes]
                    for elem in self._elements:
                        prefix = elem.name[0].upper()
                        if prefix == 'M':
                            self._stamp_mosfet(elem, v_nodes)
                        elif prefix == 'Q':
                            self._stamp_bjt(elem, v_nodes)
                        elif prefix == 'D':
                            self._stamp_diode(elem, v_nodes)
                    
                    # Solve linearized system
                    try:
                        G_sparse = sparse.csr_matrix(self._G)
                        v_new = spsolve(G_sparse, self._I)
                        if np.any(np.isnan(v_new)) or np.any(np.isinf(v_new)):
                            gmin *= 10
                            if gmin > 1e-3:
                                break
                            continue
                    except Exception:
                        gmin *= 10
                        if gmin > 1e-3:
                            break
                        continue
                    
                    # Voltage step limiting to prevent huge jumps
                    dv = v_new[:self._num_nodes] - v[:self._num_nodes]
                    max_dv = np.max(np.abs(dv))
                    if max_dv > 5.0:
                        scale = 5.0 / max_dv
                        v_new[:self._num_nodes] = v[:self._num_nodes] + scale * dv
                    
                    # Damped update to help convergence
                    v_update = v + damping * (v_new - v)
                    
                    # Check convergence (compare node voltages only)
                    delta = np.max(np.abs(v_update[:self._num_nodes] - v[:self._num_nodes]))
                    if delta < tol:
                        converged = True
                        v = v_update
                        break
                    
                    v = v_update
                    
                    # Progressively relax damping and reduce gmin
                    if iteration > 5:
                        damping = min(1.0, damping + 0.05)
                    if iteration > 10 and gmin > 1e-12:
                        gmin *= 0.1
                
                if not converged and step_frac < 1.0:
                    converged = False  # reset for next source step
            
            # Restore original source values
            for elem in self._elements:
                if elem.name[0].upper() == 'V':
                    if elem.name in original_values:
                        elem.value = original_values[elem.name]
            
            self._solution = v
            if not converged:
                print(f"Warning: Newton-Raphson did not converge after source stepping")
        
        # Extract node voltages
        results = {}
        for name, node in self._nodes.items():
            if node.is_ground:
                results[f'V({name})'] = 0.0
            else:
                results[f'V({name})'] = self._solution[node.index]
        
        return results
    
    def get_node_voltage(self, name: str) -> float:
        """Get the voltage at a node."""
        if self._solution is None:
            return 0.0
        
        idx = self._get_node_index(name)
        if idx < 0:
            return 0.0
        return self._solution[idx]
    
    def get_element_current(self, name: str) -> float:
        """Get the current through an element."""
        if self._solution is None:
            return 0.0
        
        # Find voltage source index
        vs_idx = self._num_nodes
        for elem in self._elements:
            if elem.name[0].upper() == 'V':
                if elem.name.upper() == name.upper():
                    return self._solution[vs_idx]
                vs_idx += 1
        
        return 0.0


class DCAnalysis:
    """DC Analysis - operating point and DC sweep."""
    
    def __init__(self, engine: AnalogEngine):
        self.engine = engine
    
    def run(self, settings: dict) -> dict:
        """Run DC analysis."""
        if settings and 'source' in settings and settings['source']:
            return self._run_sweep(settings)
        else:
            return self._run_op()
    
    def _run_op(self) -> dict:
        """Run operating point analysis."""
        results = self.engine.solve_dc()
        return {
            'type': 'dc_op',
            **results
        }
    
    def _run_sweep(self, settings: dict) -> dict:
        """Run DC sweep analysis."""
        source = settings['source']
        start = settings['start']
        stop = settings['stop']
        step = settings['step']
        
        sweep_values = np.arange(start, stop + step, step)
        results = {'sweep': sweep_values.tolist()}
        
        # Find the source element
        source_elem = None
        for elem in self.engine._elements:
            if elem.name.upper() == source.upper():
                source_elem = elem
                break
        
        if source_elem is None:
            raise ValueError(f"Source {source} not found")
        
        # Sweep and collect results
        node_voltages = {name: [] for name in self.engine._nodes.keys()}
        
        for val in sweep_values:
            source_elem.value = val
            dc_results = self.engine.solve_dc()
            
            for name in self.engine._nodes.keys():
                key = f'V({name})'
                if key in dc_results:
                    node_voltages[name].append(dc_results[key])
        
        for name, values in node_voltages.items():
            results[f'V({name})'] = values
        
        return results


class ACAnalysis:
    """AC Analysis - frequency domain analysis."""
    
    def __init__(self, engine: AnalogEngine):
        self.engine = engine
    
    def run(self, settings: dict) -> dict:
        """Run AC analysis."""
        variation = settings.get('variation', 'decade')
        points = settings.get('points', 10)
        fstart = settings.get('fstart', 1)
        fstop = settings.get('fstop', 1e6)
        
        # Generate frequency points
        if variation == 'decade':
            num_decades = np.log10(fstop / fstart)
            num_points = int(num_decades * points)
            frequencies = np.logspace(np.log10(fstart), np.log10(fstop), num_points)
        elif variation == 'linear':
            frequencies = np.linspace(fstart, fstop, points)
        else:
            frequencies = np.logspace(np.log10(fstart), np.log10(fstop), points)
        
        results = {
            'type': 'ac',
            'frequency': frequencies.tolist(),
        }
        
        # First solve DC operating point
        self.engine.solve_dc()
        
        # Build AC matrices and solve for each frequency
        n = self.engine._num_nodes + self.engine._num_vsources
        
        magnitude = {name: [] for name in self.engine._nodes.keys() if not self.engine._nodes[name].is_ground}
        phase = {name: [] for name in self.engine._nodes.keys() if not self.engine._nodes[name].is_ground}
        
        for freq in frequencies:
            omega = 2 * np.pi * freq
            
            # Build frequency-domain matrix: G + j*omega*C
            Y = self.engine._G + 1j * omega * self.engine._C
            
            # AC stimulus
            I_ac = np.zeros(n, dtype=complex)
            for elem in self.engine._elements:
                if elem.name[0].upper() == 'V' and 'ac_mag' in elem.params:
                    # Find voltage source index
                    vs_idx = self.engine._num_nodes
                    for e in self.engine._elements:
                        if e.name[0].upper() == 'V':
                            if e.name == elem.name:
                                break
                            vs_idx += 1
                    
                    mag = elem.params['ac_mag']
                    ph = elem.params.get('ac_phase', 0) * np.pi / 180
                    I_ac[vs_idx] = mag * np.exp(1j * ph)
            
            # Solve
            try:
                V_ac = np.linalg.solve(Y, I_ac)
            except np.linalg.LinAlgError:
                V_ac = np.zeros(n, dtype=complex)
            
            # Extract results
            for name, node in self.engine._nodes.items():
                if not node.is_ground:
                    v = V_ac[node.index]
                    magnitude[name].append(np.abs(v))
                    phase[name].append(np.angle(v, deg=True))
        
        for name in magnitude.keys():
            results[f'mag({name})'] = magnitude[name]
            results[f'phase({name})'] = phase[name]
        
        return results


class TransientAnalysis:
    """Transient Analysis - time domain simulation."""
    
    def __init__(self, engine: AnalogEngine):
        self.engine = engine
    
    def run(self, settings: dict, progress_callback: Optional[Callable] = None) -> dict:
        """Run transient analysis with inductor companions and NR for nonlinear devices."""
        tstop = settings.get('tstop', 1e-6)
        tstep = settings.get('tstep', 1e-9)
        tstart = settings.get('tstart', 0)
        uic = settings.get('uic', False)
        
        # Time points
        num_points = int(tstop / tstep) + 1
        time = np.linspace(0, tstop, num_points)
        
        results = {
            'type': 'transient',
            'time': time.tolist(),
        }
        
        # Initialize node voltages
        n = self.engine._num_nodes + self.engine._num_vsources
        V = np.zeros(n)
        
        # Get initial conditions
        if not uic:
            dc_result = self.engine.solve_dc()
            if self.engine._solution is not None:
                V = self.engine._solution.copy()
        
        # Storage for results
        node_voltages = {name: [] for name in self.engine._nodes.keys()}
        
        # Initialize inductor currents from IC params
        inductor_currents = {}
        for elem in self.engine._elements:
            if elem.name[0].upper() == 'L':
                inductor_currents[elem.name] = elem.params.get('ic', 0.0)
        
        has_nonlinear = any(
            e.name[0].upper() in ['M', 'Q', 'D'] for e in self.engine._elements
        )
        
        dt = tstep
        V_prev = V.copy()
        
        # Progress tracking
        progress_update_interval = max(1, len(time) // 100)  # Update every 1%
        
        for i, t in enumerate(time):
            if progress_callback and i % progress_update_interval == 0:
                progress_callback(i / len(time))
            
            # Update time-dependent sources
            self._update_sources(t)
            
            if has_nonlinear:
                # Newton-Raphson iteration at each timestep
                v_guess = V.copy()
                
                for nr_iter in range(30):
                    self.engine.build_mna_matrices(dc_inductors=False)
                    
                    # Stamp nonlinear devices at current guess
                    v_nodes = v_guess[:self.engine._num_nodes]
                    for elem in self.engine._elements:
                        p = elem.name[0].upper()
                        if p == 'M':
                            self.engine._stamp_mosfet(elem, v_nodes)
                        elif p == 'Q':
                            self.engine._stamp_bjt(elem, v_nodes)
                        elif p == 'D':
                            self.engine._stamp_diode(elem, v_nodes)
                    
                    G_eq = self.engine._G.copy()
                    I_eq = self.engine._I.copy()
                    
                    # Add companion models
                    self._stamp_capacitor_companions(G_eq, I_eq, V_prev, dt)
                    self._stamp_inductor_companions(
                        G_eq, I_eq, V_prev, inductor_currents, dt
                    )
                    
                    try:
                        V_new = np.linalg.solve(G_eq, I_eq)
                    except np.linalg.LinAlgError:
                        try:
                            G_sparse = sparse.csr_matrix(G_eq)
                            V_new = spsolve(G_sparse, I_eq)
                        except Exception:
                            V_new = v_guess
                            break
                    
                    if np.max(np.abs(
                        V_new[:self.engine._num_nodes]
                        - v_guess[:self.engine._num_nodes]
                    )) < 1e-6:
                        V = V_new
                        break
                    
                    # Voltage step limiting for convergence
                    dv = V_new[:self.engine._num_nodes] - v_guess[:self.engine._num_nodes]
                    max_dv = np.max(np.abs(dv))
                    if max_dv > 5.0:
                        scale = 5.0 / max_dv
                        V_new[:self.engine._num_nodes] = (
                            v_guess[:self.engine._num_nodes] + scale * dv
                        )
                    
                    # Damping for convergence
                    v_guess = 0.7 * V_new + 0.3 * v_guess
                else:
                    V = V_new  # Use last iteration
            else:
                # Linear circuit - single solve per timestep
                self.engine.build_mna_matrices(dc_inductors=False)
                G_eq = self.engine._G.copy()
                I_eq = self.engine._I.copy()
                
                self._stamp_capacitor_companions(G_eq, I_eq, V_prev, dt)
                self._stamp_inductor_companions(
                    G_eq, I_eq, V_prev, inductor_currents, dt
                )
                
                try:
                    V = np.linalg.solve(G_eq, I_eq)
                except np.linalg.LinAlgError:
                    try:
                        G_sparse = sparse.csr_matrix(G_eq)
                        V = spsolve(G_sparse, I_eq)
                    except Exception:
                        pass
            
            # Update inductor currents for next timestep
            for elem in self.engine._elements:
                if elem.name[0].upper() == 'L':
                    n1 = self.engine._get_node_index(elem.nodes[0])
                    n2 = self.engine._get_node_index(elem.nodes[1])
                    l_val = elem.value
                    if l_val <= 0:
                        continue
                    v_l_prev = (V_prev[n1] if n1 >= 0 else 0) - (
                        V_prev[n2] if n2 >= 0 else 0
                    )
                    v_l_new = (V[n1] if n1 >= 0 else 0) - (
                        V[n2] if n2 >= 0 else 0
                    )
                    inductor_currents[elem.name] += (
                        dt / (2 * l_val)
                    ) * (v_l_prev + v_l_new)
            
            V_prev = V.copy()
            
            # Store results
            for name, node in self.engine._nodes.items():
                if node.is_ground:
                    node_voltages[name].append(0.0)
                else:
                    node_voltages[name].append(float(V[node.index]))
        
        for name, values in node_voltages.items():
            results[f'V({name})'] = values
        
        return results
    
    def _stamp_capacitor_companions(
        self, G_eq: np.ndarray, I_eq: np.ndarray,
        V_prev: np.ndarray, dt: float
    ):
        """Stamp trapezoidal capacitor companion models."""
        for elem in self.engine._elements:
            if elem.name[0].upper() == 'C':
                n1 = self.engine._get_node_index(elem.nodes[0])
                n2 = self.engine._get_node_index(elem.nodes[1])
                c = elem.value
                g_eq = 2 * c / dt
                
                if n1 >= 0:
                    G_eq[n1, n1] += g_eq
                if n2 >= 0:
                    G_eq[n2, n2] += g_eq
                if n1 >= 0 and n2 >= 0:
                    G_eq[n1, n2] -= g_eq
                    G_eq[n2, n1] -= g_eq
                
                v_prev = (V_prev[n1] if n1 >= 0 else 0) - (
                    V_prev[n2] if n2 >= 0 else 0
                )
                i_eq = g_eq * v_prev
                
                if n1 >= 0:
                    I_eq[n1] += i_eq
                if n2 >= 0:
                    I_eq[n2] -= i_eq
    
    def _stamp_inductor_companions(
        self, G_eq: np.ndarray, I_eq: np.ndarray,
        V_prev: np.ndarray, inductor_currents: dict, dt: float
    ):
        """Stamp trapezoidal inductor companion models."""
        for elem in self.engine._elements:
            if elem.name[0].upper() == 'L':
                n1 = self.engine._get_node_index(elem.nodes[0])
                n2 = self.engine._get_node_index(elem.nodes[1])
                l_val = elem.value
                if l_val <= 0:
                    continue
                
                g_eq = dt / (2 * l_val)
                v_prev = (V_prev[n1] if n1 >= 0 else 0) - (
                    V_prev[n2] if n2 >= 0 else 0
                )
                i_hist = inductor_currents[elem.name] + g_eq * v_prev
                
                # Conductance stamp (like resistor)
                if n1 >= 0:
                    G_eq[n1, n1] += g_eq
                if n2 >= 0:
                    G_eq[n2, n2] += g_eq
                if n1 >= 0 and n2 >= 0:
                    G_eq[n1, n2] -= g_eq
                    G_eq[n2, n1] -= g_eq
                
                # History current source (i_hist from n1 to n2)
                if n1 >= 0:
                    I_eq[n1] -= i_hist
                if n2 >= 0:
                    I_eq[n2] += i_hist
    
    def _update_sources(self, t: float):
        """Update time-dependent source values."""
        for elem in self.engine._elements:
            if elem.name[0].upper() in ['V', 'I']:
                source_type = elem.params.get('type', 'dc')
                
                if source_type == 'pulse':
                    v1 = elem.params.get('v1', 0)
                    v2 = elem.params.get('v2', 0)
                    td = elem.params.get('td', 0)
                    tr = elem.params.get('tr', 1e-9)
                    tf = elem.params.get('tf', 1e-9)
                    pw = elem.params.get('pw', 1e-9)
                    per = elem.params.get('per', 2e-9)
                    
                    # Calculate phase within period
                    if per > 0:
                        t_phase = (t - td) % per if t >= td else 0
                    else:
                        t_phase = t - td if t >= td else 0
                    
                    if t < td:
                        elem.value = v1
                    elif t_phase < tr:
                        elem.value = v1 + (v2 - v1) * t_phase / tr
                    elif t_phase < tr + pw:
                        elem.value = v2
                    elif t_phase < tr + pw + tf:
                        elem.value = v2 + (v1 - v2) * (t_phase - tr - pw) / tf
                    else:
                        elem.value = v1
                
                elif source_type == 'sin':
                    vo = elem.params.get('vo', 0)
                    va = elem.params.get('va', 1)
                    freq = elem.params.get('freq', 1e6)
                    
                    elem.value = vo + va * np.sin(2 * np.pi * freq * t)
