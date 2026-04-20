"""
Block - Hierarchical circuit definition for the DSL.

Provides the core `Block` class for defining circuits programmatically,
with automatic SPICE netlist generation and DB persistence.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from simulator.dsl.project import Project

from simulator.db.connection import SimDB
from simulator.db.models import CircuitDesign, DesignSpecRecord
from simulator.db import queries


# ── Component registry: maps DSL names to SPICE prefixes and pin lists ──

COMP_REGISTRY: dict[str, tuple[str, list[str]]] = {
    # Passive
    "R": ("R", ["p1", "p2"]),
    "C": ("C", ["p1", "p2"]),
    "L": ("L", ["p1", "p2"]),
    # Active - MOSFET
    "NMOS": ("M", ["drain", "gate", "source", "bulk"]),
    "PMOS": ("M", ["drain", "gate", "source", "bulk"]),
    # Active - BJT
    "NPN": ("Q", ["collector", "base", "emitter"]),
    "PNP": ("Q", ["collector", "base", "emitter"]),
    # Diodes
    "D": ("D", ["anode", "cathode"]),
    "Diode": ("D", ["anode", "cathode"]),
    "Zener": ("D", ["anode", "cathode"]),
    "LED": ("D", ["anode", "cathode"]),
    "Schottky": ("D", ["anode", "cathode"]),
    # Sources
    "VoltageSource": ("V", ["p", "n"]),
    "CurrentSource": ("I", ["p", "n"]),
    "V": ("V", ["p", "n"]),
    "I": ("I", ["p", "n"]),
    # Controlled sources
    "VCVS": ("E", ["p", "n", "cp", "cn"]),
    "VCCS": ("G", ["p", "n", "cp", "cn"]),
    "CCVS": ("H", ["p", "n"]),
    "CCCS": ("F", ["p", "n"]),
    "E": ("E", ["p", "n", "cp", "cn"]),
    "G": ("G", ["p", "n", "cp", "cn"]),
    "H": ("H", ["p", "n"]),
    "F": ("F", ["p", "n"]),
}

# Friendly aliases
COMP_REGISTRY["Resistor"] = COMP_REGISTRY["R"]
COMP_REGISTRY["Capacitor"] = COMP_REGISTRY["C"]
COMP_REGISTRY["Inductor"] = COMP_REGISTRY["L"]


def _parse_eng_value(val: str) -> float:
    """Parse engineering notation value string to float.

    Supports: 10k, 4.7u, 100m, 1MEG, etc.
    """
    if isinstance(val, (int, float)):
        return float(val)
    val = str(val).strip().upper()
    # Remove trailing unit characters (V, A, F, H, ohm)
    val = re.sub(r'[VAFHΩ]$', '', val)
    suffixes = {
        'T': 1e12, 'G': 1e9, 'MEG': 1e6, 'K': 1e3,
        'M': 1e-3, 'U': 1e-6, 'N': 1e-9, 'P': 1e-12, 'F': 1e-15,
    }
    for suffix, multiplier in suffixes.items():
        if val.endswith(suffix):
            num_part = val[: -len(suffix)]
            try:
                return float(num_part) * multiplier
            except ValueError:
                break
    try:
        return float(val)
    except ValueError:
        return 0.0


# ── Supporting dataclasses ──────────────────────────────────


@dataclass
class PinRef:
    """Reference to a specific pin on a component instance."""
    instance_ref: str
    pin_name: str

    def __repr__(self) -> str:
        return f"{self.instance_ref}.{self.pin_name}"


@dataclass
class InstanceHandle:
    """Returned by Block.add(), exposes pin names as attributes for wiring."""

    ref: str
    comp_type: str
    _pin_names: list[str] = field(default_factory=list)

    def __post_init__(self):
        for pin_name in self._pin_names:
            if not hasattr(self, pin_name):
                object.__setattr__(self, pin_name, PinRef(self.ref, pin_name))


@dataclass
class PortDef:
    """Block-level port definition."""
    name: str
    direction: str = "inout"  # input, output, inout, power, ground
    net_name: Optional[str] = None  # internal net this port maps to


@dataclass
class InstanceDef:
    """A component instance within a block."""
    ref: str
    comp_type: str  # DSL name: "R", "NMOS", etc.
    spice_prefix: str  # SPICE prefix: "R", "M", etc.
    props: dict = field(default_factory=dict)
    pins: dict[str, str] = field(default_factory=dict)  # pin_name -> net_name
    model_name: Optional[str] = None


@dataclass
class SpecDef:
    """Design specification for a block."""
    name: str
    parameter: str  # signal expression, e.g. "V(vout)"
    min_val: Optional[float] = None
    typ_val: Optional[float] = None
    max_val: Optional[float] = None
    unit: str = ""
    weight: float = 1.0


# ── Auto name counters ──────────────────────────────────────

_PREFIX_COUNTERS: dict[str, int] = {}


def _next_ref(prefix: str, existing: set[str]) -> str:
    """Generate next unique reference designator."""
    count = _PREFIX_COUNTERS.get(prefix, 0) + 1
    while True:
        ref = f"{prefix}{count}"
        if ref not in existing:
            _PREFIX_COUNTERS[prefix] = count
            return ref
        count += 1


# ── Block class ─────────────────────────────────────────────


class Block:
    """Hierarchical circuit block with ports, parameters, and components.

    Used as a context manager:
        with proj.block("ldo") as ldo:
            ldo.port("vin", "input")
            r1 = ldo.add("R", value="10k")
            ...
    """

    def __init__(self, project: Project, name: str, **params: Any):
        self._project = project
        self._name = name
        self._ports: list[PortDef] = []
        self._instances: list[InstanceDef] = []
        self._specs: list[SpecDef] = []
        self._params: dict[str, Any] = dict(params)
        self._nets: dict[str, list[str]] = {}  # net_name -> list of "ref.pin"
        self._net_counter = 0
        self._existing_refs: set[str] = set()
        self._netlist_cache: Optional[str] = None
        self._circuit_id: Optional[int] = None

    # ── Context manager ──

    def __enter__(self) -> Block:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is None:
            self.save()

    # ── Port definitions ──

    def port(self, name: str, direction: str = "inout") -> PortDef:
        """Define a block-level port (interface pin)."""
        p = PortDef(name=name, direction=direction, net_name=name)
        self._ports.append(p)
        return p

    # ── Parameter definitions ──

    def param(self, name: str, value: Any) -> None:
        """Define or update a block parameter."""
        self._params[name] = value

    # ── Component instantiation ──

    def add(
        self,
        comp_type: str,
        name: Optional[str] = None,
        **props: Any,
    ) -> InstanceHandle:
        """Add a component instance to this block.

        Args:
            comp_type: Component type ("R", "C", "NMOS", "PMOS", etc.)
            name: Optional reference name (auto-generated if not given)
            **props: Component properties (value, W, L, dc, gain, etc.)

        Returns:
            InstanceHandle with pin attributes for wiring.
        """
        reg = COMP_REGISTRY.get(comp_type)
        if reg is None:
            raise ValueError(
                f"Unknown component type '{comp_type}'. "
                f"Available: {sorted(COMP_REGISTRY.keys())}"
            )
        spice_prefix, pin_names = reg

        # Determine model name for semiconductors
        model_name = props.pop("model", None)
        if model_name is None and comp_type in ("NMOS", "PMOS", "NPN", "PNP"):
            model_name = comp_type
        if model_name is None and comp_type in ("D", "Diode", "Zener", "LED", "Schottky"):
            model_name = props.pop("model_name", "D1N4148")

        # Auto-generate reference if not provided
        ref = name if name else _next_ref(spice_prefix, self._existing_refs)
        # Ensure uniqueness
        if ref in self._existing_refs:
            ref = _next_ref(spice_prefix, self._existing_refs)
        self._existing_refs.add(ref)

        inst = InstanceDef(
            ref=ref,
            comp_type=comp_type,
            spice_prefix=spice_prefix,
            props=dict(props),
            model_name=model_name,
        )
        self._instances.append(inst)
        self._netlist_cache = None

        return InstanceHandle(ref=ref, comp_type=comp_type, _pin_names=list(pin_names))

    # ── Net connections ──

    def connect(self, *pins_or_ports: Any, name: Optional[str] = None) -> str:
        """Connect pins and/or ports to the same net.

        Args:
            *pins_or_ports: PinRef objects, PortDef objects, or net name strings
            name: Optional net name (auto-generated if not given)

        Returns:
            The net name.
        """
        # Determine net name
        net = name
        refs_to_connect: list[tuple[str, str]] = []  # (instance_ref, pin_name)

        for item in pins_or_ports:
            if isinstance(item, PinRef):
                refs_to_connect.append((item.instance_ref, item.pin_name))
            elif isinstance(item, PortDef):
                if net is None:
                    net = item.name
                item.net_name = net or item.name
            elif isinstance(item, str):
                if net is None:
                    net = item
            else:
                raise TypeError(f"Cannot connect {type(item)}: expected PinRef, PortDef, or str")

        if net is None:
            self._net_counter += 1
            net = f"net{self._net_counter}"

        # Update port net names
        for item in pins_or_ports:
            if isinstance(item, PortDef):
                item.net_name = net

        # Update instance pin mappings
        for inst_ref, pin_name in refs_to_connect:
            for inst in self._instances:
                if inst.ref == inst_ref:
                    inst.pins[pin_name] = net
                    break

        # Track in nets dict
        if net not in self._nets:
            self._nets[net] = []
        for inst_ref, pin_name in refs_to_connect:
            self._nets[net].append(f"{inst_ref}.{pin_name}")

        self._netlist_cache = None
        return net

    # ── Specification definitions ──

    def spec(
        self,
        name: str,
        parameter: Optional[str] = None,
        min: Optional[float] = None,
        typ: Optional[float] = None,
        max: Optional[float] = None,
        unit: str = "",
        weight: float = 1.0,
    ) -> SpecDef:
        """Define a design specification for this block."""
        s = SpecDef(
            name=name,
            parameter=parameter or name,
            min_val=min,
            typ_val=typ,
            max_val=max,
            unit=unit,
            weight=weight,
        )
        self._specs.append(s)
        return s

    # ── Netlist generation ──

    def to_netlist(self, corner: str = "TT", temp: float = 27.0) -> str:
        """Generate a full SPICE netlist string.

        If the block was imported from a .spice file, returns the cached
        raw netlist. Otherwise, builds it from the instance definitions.
        """
        if self._netlist_cache is not None:
            return self._netlist_cache

        lines: list[str] = []
        lines.append(f"* {self._name}")
        lines.append(f"* Corner: {corner}  Temperature: {temp}C")
        lines.append("")

        # Fetch model cards from DB
        db = self._project.db
        tech_name = self._project.technology_name
        model_text = queries.get_all_models_spice(db, tech_name, corner)
        if model_text:
            lines.append("* Device Models")
            lines.append(model_text)
            lines.append("")

        # Emit element lines
        for inst in self._instances:
            line = self._instance_to_spice(inst)
            if line:
                lines.append(line)

        lines.append("")
        lines.append(".END")
        return "\n".join(lines)

    def _instance_to_spice(self, inst: InstanceDef) -> str:
        """Convert a single InstanceDef to a SPICE element line."""
        prefix = inst.spice_prefix
        ref = inst.ref

        # Ensure ref starts with the correct SPICE prefix
        if not ref.upper().startswith(prefix.upper()):
            ref = f"{prefix}_{ref}"

        props = inst.props

        if prefix == "R":
            n1 = inst.pins.get("p1", "0")
            n2 = inst.pins.get("p2", "0")
            val = props.get("value", props.get("resistance", "1k"))
            return f"{ref} {n1} {n2} {val}"

        elif prefix == "C":
            n1 = inst.pins.get("p1", "0")
            n2 = inst.pins.get("p2", "0")
            val = props.get("value", props.get("capacitance", "1u"))
            ic = props.get("ic", props.get("IC", ""))
            ic_str = f" IC={ic}" if ic else ""
            return f"{ref} {n1} {n2} {val}{ic_str}"

        elif prefix == "L":
            n1 = inst.pins.get("p1", "0")
            n2 = inst.pins.get("p2", "0")
            val = props.get("value", props.get("inductance", "1u"))
            return f"{ref} {n1} {n2} {val}"

        elif prefix == "M":
            nd = inst.pins.get("drain", "0")
            ng = inst.pins.get("gate", "0")
            ns = inst.pins.get("source", "0")
            nb = inst.pins.get("bulk", ns)
            model = inst.model_name or inst.comp_type
            w = props.get("W", "10u")
            l = props.get("L", "1u")
            return f"{ref} {nd} {ng} {ns} {nb} {model} W={w} L={l}"

        elif prefix == "Q":
            nc = inst.pins.get("collector", "0")
            nb = inst.pins.get("base", "0")
            ne = inst.pins.get("emitter", "0")
            model = inst.model_name or inst.comp_type
            return f"{ref} {nc} {nb} {ne} {model}"

        elif prefix == "D":
            na = inst.pins.get("anode", "0")
            nc = inst.pins.get("cathode", "0")
            model = inst.model_name or "D1N4148"
            return f"{ref} {na} {nc} {model}"

        elif prefix == "V":
            np_ = inst.pins.get("p", "0")
            nn = inst.pins.get("n", "0")
            parts = [f"{ref} {np_} {nn}"]
            if "dc" in props:
                parts.append(f"DC {props['dc']}")
            if "ac" in props or "ac_mag" in props:
                ac = props.get("ac", props.get("ac_mag", ""))
                parts.append(f"AC {ac}")
            if "pulse" in props:
                parts.append(f"PULSE({props['pulse']})")
            if "sin" in props:
                parts.append(f"SIN({props['sin']})")
            # If no spec at all, default to DC 0
            if len(parts) == 1:
                val = props.get("value", "0")
                parts.append(f"DC {val}")
            return " ".join(parts)

        elif prefix == "I":
            np_ = inst.pins.get("p", "0")
            nn = inst.pins.get("n", "0")
            parts = [f"{ref} {np_} {nn}"]
            if "dc" in props:
                parts.append(f"DC {props['dc']}")
            if len(parts) == 1:
                val = props.get("value", "0")
                parts.append(f"DC {val}")
            return " ".join(parts)

        elif prefix in ("E", "G"):
            np_ = inst.pins.get("p", "0")
            nn = inst.pins.get("n", "0")
            cp = inst.pins.get("cp", "0")
            cn = inst.pins.get("cn", "0")
            gain = props.get("gain", props.get("value", "1"))
            label = "VCVS" if prefix == "E" else "VCCS"
            return f"{ref} {np_} {nn} {label} {cp} {cn} {gain}"

        elif prefix in ("H", "F"):
            np_ = inst.pins.get("p", "0")
            nn = inst.pins.get("n", "0")
            vsource = props.get("vsource", "V1")
            gain = props.get("gain", props.get("value", "1"))
            label = "CCVS" if prefix == "H" else "CCCS"
            return f"{ref} {np_} {nn} {label} {vsource} {gain}"

        return f"* Unknown: {inst.ref} {inst.comp_type}"

    # ── DB persistence ──

    @property
    def name(self) -> str:
        return self._name

    @property
    def circuit_id(self) -> Optional[int]:
        return self._circuit_id

    @property
    def specs(self) -> list[SpecDef]:
        return list(self._specs)

    @property
    def ports(self) -> list[PortDef]:
        return list(self._ports)

    @property
    def instances(self) -> list[InstanceDef]:
        return list(self._instances)

    def save(self) -> int:
        """Save this block as a circuit in the DB. Returns circuit ID."""
        db = self._project.db

        # Build hierarchy JSON
        hierarchy = {
            "ports": [
                {"name": p.name, "direction": p.direction, "net": p.net_name}
                for p in self._ports
            ],
            "instances": [
                {
                    "ref": i.ref,
                    "comp_type": i.comp_type,
                    "props": i.props,
                    "pins": i.pins,
                    "model": i.model_name,
                }
                for i in self._instances
            ],
            "nets": self._nets,
        }

        circuit = CircuitDesign(
            id=self._circuit_id,
            name=self._name,
            technology_id=self._project.technology_id,
            description=self._params.get("description", ""),
            netlist=self._netlist_cache or self.to_netlist(),
            hierarchy=hierarchy,
            params=self._params,
            status="active",
        )
        self._circuit_id = queries.save_circuit(db, circuit)

        # Save specs
        for s in self._specs:
            spec_rec = DesignSpecRecord(
                circuit_id=self._circuit_id,
                name=s.name,
                parameter=s.parameter,
                min_val=s.min_val,
                max_val=s.max_val,
                typical=s.typ_val,
                unit=s.unit,
                weight=s.weight,
            )
            queries.save_design_spec(db, spec_rec)

        db.commit()
        return self._circuit_id

    @classmethod
    def load(cls, project: Project, name: str) -> Block:
        """Load a block from the DB by circuit name."""
        db = project.db
        circuit = queries.get_circuit(db, name)
        if circuit is None:
            raise ValueError(f"Block '{name}' not found in database")

        block = cls(project, name)
        block._circuit_id = circuit.id
        block._params = circuit.params or {}

        # Restore from netlist if hierarchy is empty
        if circuit.netlist:
            block._netlist_cache = circuit.netlist

        # Restore from hierarchy JSON
        hierarchy = circuit.hierarchy or {}
        for p_data in hierarchy.get("ports", []):
            port = PortDef(
                name=p_data["name"],
                direction=p_data.get("direction", "inout"),
                net_name=p_data.get("net"),
            )
            block._ports.append(port)

        for i_data in hierarchy.get("instances", []):
            inst = InstanceDef(
                ref=i_data["ref"],
                comp_type=i_data["comp_type"],
                spice_prefix=COMP_REGISTRY.get(i_data["comp_type"], ("X", []))[0],
                props=i_data.get("props", {}),
                pins=i_data.get("pins", {}),
                model_name=i_data.get("model"),
            )
            block._instances.append(inst)
            block._existing_refs.add(inst.ref)

        block._nets = hierarchy.get("nets", {})

        # Restore specs from DB
        specs = queries.get_design_specs(db, circuit.id)
        for s in specs:
            block._specs.append(
                SpecDef(
                    name=s.name,
                    parameter=s.parameter,
                    min_val=s.min_val,
                    typ_val=s.typical,
                    max_val=s.max_val,
                    unit=s.unit,
                    weight=s.weight,
                )
            )

        return block

    def __repr__(self) -> str:
        return (
            f"Block('{self._name}', ports={len(self._ports)}, "
            f"instances={len(self._instances)}, specs={len(self._specs)})"
        )
