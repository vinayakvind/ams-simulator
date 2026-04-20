"""
Chip - SoC-level hierarchical composition of Blocks.

Provides the `Chip` class for composing multiple Blocks into a top-level
chip design with power domains, mixed-signal wiring, and hierarchical
netlist generation using .SUBCKT.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from simulator.dsl.project import Project

from simulator.db.models import CircuitDesign
from simulator.db import queries
from simulator.dsl.block import Block, PortDef, PinRef


# ── Supporting dataclasses ──────────────────────────────────


@dataclass
class BlockPortRef:
    """Reference to a port on a block instance."""
    instance_name: str
    port_name: str

    def __repr__(self) -> str:
        return f"{self.instance_name}.{self.port_name}"


@dataclass
class BlockInstanceHandle:
    """Handle to an instantiated block, with port attributes."""
    instance_name: str
    block_name: str
    _port_names: list[str] = field(default_factory=list)

    def __post_init__(self):
        for port_name in self._port_names:
            if not hasattr(self, port_name):
                object.__setattr__(
                    self, port_name,
                    BlockPortRef(self.instance_name, port_name),
                )


@dataclass
class DigitalBlockDef:
    """Definition of a digital block."""
    name: str
    instance_name: str
    verilog: str = ""
    gate_list: list = field(default_factory=list)


@dataclass
class DigitalBlockHandle:
    """Handle to a digital block instance."""
    instance_name: str
    name: str
    _port_names: list[str] = field(default_factory=list)

    def __post_init__(self):
        for port_name in self._port_names:
            if not hasattr(self, port_name):
                object.__setattr__(
                    self, port_name,
                    BlockPortRef(self.instance_name, port_name),
                )


@dataclass
class WireDef:
    """A wire connecting ports across block instances."""
    net_name: str
    ports: list[BlockPortRef]


@dataclass
class PowerDomain:
    """Power domain definition grouping blocks at a supply voltage."""
    name: str
    voltage: float
    blocks: list[str]


# ── Chip class ──────────────────────────────────────────────


class Chip:
    """Top-level SoC composition - hierarchical instantiation of Blocks.

    Usage:
        with proj.chip("serdes_top") as chip:
            bgr = chip.use("bandgap_ref")
            ldo = chip.use("ldo_regulator")
            chip.wire(bgr.vout, ldo.vref)
            chip.power_domain("core", voltage=1.8, blocks=["ldo_regulator"])
    """

    def __init__(self, project: Project, name: str):
        self._project = project
        self._name = name
        self._block_instances: list[dict] = []
        self._digital_blocks: list[DigitalBlockDef] = []
        self._wires: list[WireDef] = []
        self._power_domains: dict[str, PowerDomain] = {}
        self._circuit_id: Optional[int] = None
        self._instance_counter = 0

    # ── Context manager ──

    def __enter__(self) -> Chip:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is None:
            self.save()

    # ── Block instantiation ──

    def use(
        self,
        block_name: str,
        instance_name: Optional[str] = None,
        **param_overrides: Any,
    ) -> BlockInstanceHandle:
        """Instantiate an existing Block by name.

        Args:
            block_name: Name of block in DB
            instance_name: Instance name (default: auto-generated)
            **param_overrides: Parameter overrides for this instance

        Returns:
            BlockInstanceHandle with port attributes.
        """
        block = Block.load(self._project, block_name)

        if instance_name is None:
            self._instance_counter += 1
            instance_name = f"{block_name}_{self._instance_counter}"

        port_names = [p.name for p in block.ports]

        self._block_instances.append({
            "block_name": block_name,
            "instance_name": instance_name,
            "circuit_id": block.circuit_id,
            "params": param_overrides,
            "port_names": port_names,
        })

        return BlockInstanceHandle(
            instance_name=instance_name,
            block_name=block_name,
            _port_names=port_names,
        )

    # ── Digital blocks ──

    def digital(
        self,
        name: str,
        instance_name: Optional[str] = None,
        verilog: Optional[str] = None,
        gate_list: Optional[list] = None,
    ) -> DigitalBlockHandle:
        """Instantiate a digital block.

        Args:
            name: Block name
            instance_name: Instance name (auto-generated if not given)
            verilog: Verilog source code or file path
            gate_list: List of gate definitions (alternative to verilog)

        Returns:
            DigitalBlockHandle with port attributes.
        """
        if instance_name is None:
            self._instance_counter += 1
            instance_name = f"{name}_{self._instance_counter}"

        dblock = DigitalBlockDef(
            name=name,
            instance_name=instance_name,
            verilog=verilog or "",
            gate_list=gate_list or [],
        )
        self._digital_blocks.append(dblock)

        # Infer ports from verilog if available
        port_names = ["vdd", "vss", "clk", "reset"]
        return DigitalBlockHandle(
            instance_name=instance_name,
            name=name,
            _port_names=port_names,
        )

    # ── Wiring ──

    def wire(self, *ports: Any, name: Optional[str] = None) -> str:
        """Wire ports from different block instances together.

        Args:
            *ports: BlockPortRef objects from .use() handles
            name: Optional net name

        Returns:
            The net name.
        """
        port_refs: list[BlockPortRef] = []
        for p in ports:
            if isinstance(p, BlockPortRef):
                port_refs.append(p)
            elif isinstance(p, str):
                if name is None:
                    name = p
            else:
                raise TypeError(f"Cannot wire {type(p)}: expected BlockPortRef or str")

        if name is None:
            name = "_".join(str(p) for p in port_refs)

        wire = WireDef(net_name=name, ports=port_refs)
        self._wires.append(wire)
        return name

    # ── Power domains ──

    def power_domain(
        self, name: str, voltage: float, blocks: list[str]
    ) -> None:
        """Define a power domain grouping blocks at a supply voltage."""
        self._power_domains[name] = PowerDomain(
            name=name, voltage=voltage, blocks=blocks,
        )

    # ── Netlist generation ──

    def to_netlist(self, corner: str = "TT", temp: float = 27.0) -> str:
        """Generate top-level netlist with .SUBCKT for each block."""
        lines: list[str] = []
        lines.append(f"* Chip: {self._name}")
        lines.append(f"* Corner: {corner}  Temp: {temp}C")
        lines.append("")

        # Emit .SUBCKT for each block dependency
        emitted_subckt: set[str] = set()
        for inst in self._block_instances:
            bname = inst["block_name"]
            if bname not in emitted_subckt:
                block = Block.load(self._project, bname)
                port_names = " ".join(p.name for p in block.ports)

                lines.append(f".SUBCKT {bname} {port_names}")
                # Emit the block's internal netlist (minus header/footer)
                inner = block.to_netlist(corner, temp)
                for inner_line in inner.split("\n"):
                    stripped = inner_line.strip()
                    if stripped.startswith("*") or stripped.upper() == ".END":
                        continue
                    if stripped.startswith(".MODEL"):
                        continue  # Models go at top level
                    if stripped:
                        lines.append(f"  {stripped}")
                lines.append(f".ENDS {bname}")
                lines.append("")
                emitted_subckt.add(bname)

        # Emit model cards at top level
        db = self._project.db
        tech_name = self._project.technology_name
        model_text = queries.get_all_models_spice(db, tech_name, corner)
        if model_text:
            lines.append("* Device Models")
            lines.append(model_text)
            lines.append("")

        # Emit power supply sources for each power domain
        for pd in self._power_domains.values():
            lines.append(f"V_{pd.name} {pd.name}_vdd 0 DC {pd.voltage}")

        # Emit block instantiations
        for inst in self._block_instances:
            bname = inst["block_name"]
            iname = inst["instance_name"]
            port_names_list = inst["port_names"]

            # Map instance ports to top-level nets
            port_nets = []
            for pname in port_names_list:
                # Check if wired to something
                wire_net = None
                for w in self._wires:
                    for pr in w.ports:
                        if pr.instance_name == iname and pr.port_name == pname:
                            wire_net = w.net_name
                            break
                    if wire_net:
                        break
                port_nets.append(wire_net or f"{iname}_{pname}")

            nets_str = " ".join(port_nets)
            lines.append(f"X_{iname} {nets_str} {bname}")

        lines.append("")
        lines.append(".END")
        return "\n".join(lines)

    # ── DB persistence ──

    def save(self) -> int:
        """Save the chip as a circuit in the DB with hierarchy JSON."""
        db = self._project.db

        hierarchy = {
            "type": "chip",
            "block_instances": self._block_instances,
            "digital_blocks": [
                {
                    "name": d.name,
                    "instance_name": d.instance_name,
                    "verilog": d.verilog,
                }
                for d in self._digital_blocks
            ],
            "wires": [
                {
                    "net": w.net_name,
                    "ports": [
                        {"instance": p.instance_name, "port": p.port_name}
                        for p in w.ports
                    ],
                }
                for w in self._wires
            ],
            "power_domains": {
                name: {"voltage": pd.voltage, "blocks": pd.blocks}
                for name, pd in self._power_domains.items()
            },
        }

        circuit = CircuitDesign(
            id=self._circuit_id,
            name=self._name,
            technology_id=self._project.technology_id,
            description=f"Chip: {self._name}",
            netlist=self.to_netlist(),
            hierarchy=hierarchy,
            status="active",
        )
        self._circuit_id = queries.save_circuit(db, circuit)
        db.commit()
        return self._circuit_id

    @property
    def name(self) -> str:
        return self._name

    def __repr__(self) -> str:
        return (
            f"Chip('{self._name}', blocks={len(self._block_instances)}, "
            f"wires={len(self._wires)}, domains={len(self._power_domains)})"
        )
