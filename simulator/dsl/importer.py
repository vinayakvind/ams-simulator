"""
SpiceImporter - Import existing .spice netlist files into the DSL system.

Converts raw SPICE netlists into Block objects stored in the database,
with proper component instances, connections, and inferred ports.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from simulator.dsl.project import Project

from simulator.db.models import CircuitDesign, DeviceModel
from simulator.db import queries
from simulator.dsl.block import Block, PortDef, InstanceDef, COMP_REGISTRY


# Heuristic port names (nodes likely to be external interfaces)
_PORT_PATTERNS = re.compile(
    r'^(v?in|v?out|vdd|vss|vcc|vee|gnd|input|output|ref|fb|enable|clk|reset)$',
    re.IGNORECASE,
)


class SpiceImporter:
    """Import existing SPICE netlist files into the DSL system."""

    def __init__(self, project: Project):
        self._project = project

    def import_file(
        self, spice_path: str, block_name: Optional[str] = None
    ) -> Block:
        """Import a single .spice file as a Block.

        The raw netlist is stored verbatim for direct simulation.
        Ports are inferred from node naming conventions.
        Models are extracted and stored in the device_models table.

        Args:
            spice_path: Path to the .spice/.cir file
            block_name: Name for the block (default: filename stem)

        Returns:
            The imported Block, saved to DB.
        """
        path = Path(spice_path)
        if not path.exists():
            raise FileNotFoundError(f"SPICE file not found: {path}")

        netlist = path.read_text(encoding="utf-8")
        name = block_name or path.stem

        # Check if block already exists
        existing = queries.get_circuit(self._project.db, name)
        if existing is not None:
            block = Block.load(self._project, name)
            return block

        # Parse models and store in DB
        self._extract_and_store_models(netlist)

        # Parse element lines and node connectivity
        elements, all_nodes = self._parse_elements(netlist)

        # Infer ports
        ports = self._infer_ports(netlist, all_nodes)

        # Create block with raw netlist cached
        block = Block(self._project, name)
        block._netlist_cache = netlist
        block._ports = ports

        # Store parsed instances (for queryability, not netlist generation)
        for elem in elements:
            inst = InstanceDef(
                ref=elem["ref"],
                comp_type=elem["comp_type"],
                spice_prefix=elem["prefix"],
                props=elem.get("props", {}),
                pins=elem.get("pins", {}),
                model_name=elem.get("model"),
            )
            block._instances.append(inst)
            block._existing_refs.add(inst.ref)

        # Save to DB
        block.save()
        return block

    def import_directory(
        self, dir_path: str, pattern: str = "*.spice"
    ) -> list[Block]:
        """Import all matching SPICE files from a directory.

        Args:
            dir_path: Directory path
            pattern: Glob pattern (default: *.spice)

        Returns:
            List of imported Blocks.
        """
        directory = Path(dir_path)
        if not directory.is_dir():
            raise NotADirectoryError(f"Not a directory: {dir_path}")

        blocks = []
        for spice_file in sorted(directory.glob(pattern)):
            block = self.import_file(str(spice_file))
            blocks.append(block)
        return blocks

    def _extract_and_store_models(self, netlist: str) -> None:
        """Extract .MODEL directives and store in device_models table."""
        db = self._project.db
        tech_id = self._project.technology_id

        for match in re.finditer(
            r'\.MODEL\s+(\S+)\s+(\S+)\s*\(([^)]*)\)',
            netlist,
            re.IGNORECASE,
        ):
            model_name = match.group(1)
            model_type = match.group(2).lower()
            params_str = match.group(3)

            # Parse parameters
            params = {}
            for p in re.finditer(r'(\w+)\s*=\s*([\d.eE+\-]+[a-zA-Z]*)', params_str):
                key = p.group(1)
                val_str = p.group(2)
                try:
                    val = float(re.sub(r'[a-zA-Z]+$', '', val_str))
                except ValueError:
                    val = val_str
                params[key] = val

            # Map type
            type_map = {
                "nmos": "nmos", "pmos": "pmos",
                "npn": "npn", "pnp": "pnp",
                "d": "diode",
            }
            device_type = type_map.get(model_type, model_type)

            model = DeviceModel(
                technology_id=tech_id,
                corner_id=None,
                name=model_name,
                device_type=device_type,
                params=params,
                spice_text=match.group(0).strip(),
            )
            queries.save_device_model(db, model)

        db.commit()

    def _parse_elements(self, netlist: str) -> tuple[list[dict], set[str]]:
        """Parse element lines from netlist. Returns (elements, all_nodes)."""
        elements = []
        all_nodes: set[str] = set()

        # Join continuation lines
        lines = []
        for raw in netlist.strip().split('\n'):
            stripped = raw.strip()
            if stripped.startswith('+'):
                if lines:
                    lines[-1] += ' ' + stripped[1:].strip()
                continue
            lines.append(stripped)

        for line in lines:
            if not line or line.startswith('*') or line.startswith('.'):
                continue

            parts = line.split()
            if not parts:
                continue

            ref = parts[0]
            prefix = ref[0].upper()
            elem: Optional[dict] = None

            if prefix == 'R' and len(parts) >= 4:
                n1, n2 = parts[1], parts[2]
                val = parts[3]
                all_nodes.update([n1, n2])
                elem = {
                    "ref": ref, "prefix": "R", "comp_type": "R",
                    "pins": {"p1": n1, "p2": n2},
                    "props": {"value": val},
                }

            elif prefix == 'C' and len(parts) >= 4:
                n1, n2 = parts[1], parts[2]
                val = parts[3]
                props = {"value": val}
                # Check for IC=
                for p in parts[4:]:
                    if p.upper().startswith("IC="):
                        props["IC"] = p.split("=")[1]
                all_nodes.update([n1, n2])
                elem = {
                    "ref": ref, "prefix": "C", "comp_type": "C",
                    "pins": {"p1": n1, "p2": n2}, "props": props,
                }

            elif prefix == 'L' and len(parts) >= 4:
                n1, n2 = parts[1], parts[2]
                val = parts[3]
                all_nodes.update([n1, n2])
                elem = {
                    "ref": ref, "prefix": "L", "comp_type": "L",
                    "pins": {"p1": n1, "p2": n2},
                    "props": {"value": val},
                }

            elif prefix == 'V' and len(parts) >= 3:
                np_, nn = parts[1], parts[2]
                all_nodes.update([np_, nn])
                props = self._parse_source_props(parts[3:])
                elem = {
                    "ref": ref, "prefix": "V", "comp_type": "VoltageSource",
                    "pins": {"p": np_, "n": nn}, "props": props,
                }

            elif prefix == 'I' and len(parts) >= 3:
                np_, nn = parts[1], parts[2]
                all_nodes.update([np_, nn])
                props = self._parse_source_props(parts[3:])
                elem = {
                    "ref": ref, "prefix": "I", "comp_type": "CurrentSource",
                    "pins": {"p": np_, "n": nn}, "props": props,
                }

            elif prefix == 'M' and len(parts) >= 6:
                nd, ng, ns, nb = parts[1], parts[2], parts[3], parts[4]
                model = parts[5]
                all_nodes.update([nd, ng, ns, nb])
                props = {}
                for p in parts[6:]:
                    if '=' in p:
                        k, v = p.split('=', 1)
                        props[k] = v
                comp_type = "NMOS" if "NMOS" in model.upper() else "PMOS"
                elem = {
                    "ref": ref, "prefix": "M", "comp_type": comp_type,
                    "pins": {"drain": nd, "gate": ng, "source": ns, "bulk": nb},
                    "props": props, "model": model,
                }

            elif prefix == 'Q' and len(parts) >= 5:
                nc, nb, ne = parts[1], parts[2], parts[3]
                model = parts[4]
                all_nodes.update([nc, nb, ne])
                comp_type = "NPN" if "NPN" in model.upper() else "PNP"
                elem = {
                    "ref": ref, "prefix": "Q", "comp_type": comp_type,
                    "pins": {"collector": nc, "base": nb, "emitter": ne},
                    "model": model,
                }

            elif prefix == 'D' and len(parts) >= 4:
                na, nc_ = parts[1], parts[2]
                model = parts[3]
                all_nodes.update([na, nc_])
                elem = {
                    "ref": ref, "prefix": "D", "comp_type": "D",
                    "pins": {"anode": na, "cathode": nc_},
                    "model": model,
                }

            elif prefix == 'E' and len(parts) >= 6:
                np_, nn = parts[1], parts[2]
                # Skip 'VCVS' keyword if present
                idx = 3
                if parts[idx].upper() == "VCVS":
                    idx += 1
                cp, cn = parts[idx], parts[idx + 1]
                gain = parts[idx + 2] if idx + 2 < len(parts) else "1"
                all_nodes.update([np_, nn, cp, cn])
                elem = {
                    "ref": ref, "prefix": "E", "comp_type": "VCVS",
                    "pins": {"p": np_, "n": nn, "cp": cp, "cn": cn},
                    "props": {"gain": gain},
                }

            elif prefix == 'G' and len(parts) >= 6:
                np_, nn = parts[1], parts[2]
                idx = 3
                if parts[idx].upper() == "VCCS":
                    idx += 1
                cp, cn = parts[idx], parts[idx + 1]
                gain = parts[idx + 2] if idx + 2 < len(parts) else "1"
                all_nodes.update([np_, nn, cp, cn])
                elem = {
                    "ref": ref, "prefix": "G", "comp_type": "VCCS",
                    "pins": {"p": np_, "n": nn, "cp": cp, "cn": cn},
                    "props": {"gain": gain},
                }

            if elem:
                elements.append(elem)

        # Remove ground from node set
        all_nodes.discard("0")
        all_nodes.discard("GND")
        all_nodes.discard("gnd")

        return elements, all_nodes

    def _parse_source_props(self, parts: list[str]) -> dict:
        """Parse source properties from SPICE tokens."""
        props = {}
        i = 0
        while i < len(parts):
            token = parts[i].upper()
            if token == "DC" and i + 1 < len(parts):
                props["dc"] = parts[i + 1]
                i += 2
            elif token == "AC" and i + 1 < len(parts):
                props["ac"] = parts[i + 1]
                i += 2
            elif token.startswith("PULSE(") or token == "PULSE":
                # Collect until closing paren
                pulse_str = " ".join(parts[i:])
                m = re.search(r'PULSE\(([^)]*)\)', pulse_str, re.IGNORECASE)
                if m:
                    props["pulse"] = m.group(1)
                i = len(parts)
            elif token.startswith("SIN(") or token == "SIN":
                sin_str = " ".join(parts[i:])
                m = re.search(r'SIN\(([^)]*)\)', sin_str, re.IGNORECASE)
                if m:
                    props["sin"] = m.group(1)
                i = len(parts)
            else:
                # Could be a bare value like "5V"
                if not props:
                    props["dc"] = parts[i]
                i += 1
        return props

    def _infer_ports(self, netlist: str, all_nodes: set[str]) -> list[PortDef]:
        """Infer block ports from node names using heuristics."""
        ports: list[PortDef] = []
        seen: set[str] = set()

        for node in sorted(all_nodes):
            if node in seen:
                continue

            # Check if node name matches port patterns
            if _PORT_PATTERNS.match(node):
                direction = "inout"
                name_lower = node.lower()
                if "in" in name_lower and "out" not in name_lower:
                    direction = "input"
                elif "out" in name_lower:
                    direction = "output"
                elif name_lower in ("vdd", "vcc"):
                    direction = "power"
                elif name_lower in ("vss", "vee", "gnd"):
                    direction = "ground"

                ports.append(PortDef(name=node, direction=direction, net_name=node))
                seen.add(node)

        return ports
