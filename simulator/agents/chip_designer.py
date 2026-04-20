"""
ChipDesigner Agent - Top-level autonomous chip design orchestrator.

Orchestrates the complete chip design flow: architecture definition,
block creation, integration, verification, and reporting. Can create
any ASIC design given a specification.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Optional

from simulator.agents.block_builder import BlockBuilder
from simulator.agents.tech_mapper import TechMapper
from simulator.agents.design_index import DesignIndex


class DesignPhase(Enum):
    """Phases of the chip design flow."""
    SPEC_CAPTURE = auto()
    ARCHITECTURE = auto()
    BLOCK_DESIGN = auto()
    INTEGRATION = auto()
    VERIFICATION = auto()
    SIGNOFF = auto()


@dataclass
class ChipSpec:
    """Top-level chip specification."""
    name: str
    description: str = ""
    technology: str = "generic180"
    supply_voltage: float = 3.3
    io_voltage: float = 12.0
    temperature_range: tuple[float, float] = (-40.0, 125.0)
    target_power: float = 50e-3  # 50mW
    blocks: list[dict[str, Any]] = field(default_factory=list)
    power_domains: list[dict[str, Any]] = field(default_factory=list)
    interfaces: list[dict[str, Any]] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)


@dataclass
class DesignStep:
    """A single step in the design flow."""
    phase: DesignPhase
    name: str
    description: str
    action: str  # Function name to call
    params: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending, running, completed, failed
    result: Any = None
    timestamp: Optional[float] = None


class ChipDesigner:
    """Autonomous chip design agent.

    Given a chip specification, orchestrates the entire design flow
    from architecture through verification.

    Usage:
        designer = ChipDesigner(technology="generic180")
        chip = designer.create_chip("lin_asic", spec={
            "supply_voltage": 3.3,
            "io_voltage": 12.0,
            "blocks": ["bandgap", "ldo_digital", "ldo_analog", "lin_tx", "lin_rx",
                       "spi_controller", "lin_controller", "register_file"]
        })
    """

    def __init__(self, technology: str = "generic180", output_dir: str = "designs"):
        self.technology = technology
        self.output_dir = Path(output_dir)
        self.block_builder = BlockBuilder(technology)
        self.tech_mapper = TechMapper(technology)
        self.design_index = DesignIndex()
        self._steps: list[DesignStep] = []
        self._current_phase = DesignPhase.SPEC_CAPTURE
        self._log: list[str] = []

    def log(self, message: str) -> None:
        """Log a design message."""
        ts = time.strftime("%H:%M:%S")
        entry = f"[{ts}] {message}"
        self._log.append(entry)
        print(entry)

    def create_chip(self, name: str, spec: dict[str, Any]) -> dict[str, Any]:
        """Create a complete chip design from specification.

        Args:
            name: Chip name
            spec: Chip specification dictionary

        Returns:
            Design result with netlists, reports, and verification status
        """
        chip_spec = ChipSpec(name=name, **spec)
        self.log(f"=== Starting chip design: {name} ===")
        self.log(f"Technology: {self.technology}")
        self.log(f"Supply: {chip_spec.supply_voltage}V, IO: {chip_spec.io_voltage}V")

        result = {
            "name": name,
            "technology": self.technology,
            "phases": {},
            "netlists": {},
            "blocks": {},
            "verification": {},
        }

        # Phase 1: Architecture
        self._current_phase = DesignPhase.ARCHITECTURE
        self.log("\n--- Phase 1: Architecture Definition ---")
        arch = self._define_architecture(chip_spec)
        result["phases"]["architecture"] = arch
        self.design_index.record_step(name, "architecture", arch)

        # Phase 2: Block Design
        self._current_phase = DesignPhase.BLOCK_DESIGN
        self.log("\n--- Phase 2: Block Design ---")
        blocks = self._design_blocks(chip_spec, arch)
        result["blocks"] = blocks
        self.design_index.record_step(name, "block_design", {
            "blocks_designed": list(blocks.keys())
        })

        # Phase 3: Integration
        self._current_phase = DesignPhase.INTEGRATION
        self.log("\n--- Phase 3: Top-Level Integration ---")
        integration = self._integrate_chip(chip_spec, arch, blocks)
        result["netlists"] = integration
        self.design_index.record_step(name, "integration", {
            "top_netlist_lines": len(integration.get("top_netlist", "").split("\n"))
        })

        # Phase 4: Verification
        self._current_phase = DesignPhase.VERIFICATION
        self.log("\n--- Phase 4: Verification ---")
        verification = self._verify_design(chip_spec, result)
        result["verification"] = verification
        self.design_index.record_step(name, "verification", verification)

        # Phase 5: Sign-off
        self._current_phase = DesignPhase.SIGNOFF
        self.log("\n--- Phase 5: Sign-off ---")
        self._generate_reports(chip_spec, result)
        self.design_index.record_step(name, "signoff", {"status": "complete"})

        # Save to disk
        self._save_design(name, result)
        self.log(f"\n=== Chip design '{name}' complete ===")
        return result

    def _define_architecture(self, spec: ChipSpec) -> dict[str, Any]:
        """Define chip architecture from spec."""
        arch = {
            "name": spec.name,
            "power_domains": [],
            "block_hierarchy": [],
            "interfaces": [],
            "signal_routing": [],
        }

        # Automatically define power domains
        if spec.power_domains:
            arch["power_domains"] = spec.power_domains
        else:
            # Default power domains for mixed-signal ASIC
            arch["power_domains"] = [
                {"name": "VDD_IO", "voltage": spec.io_voltage, "source": "external",
                 "description": "I/O supply (battery/bus)"},
                {"name": "VDD_ANA", "voltage": spec.supply_voltage, "source": "ldo_analog",
                 "description": "Analog core supply from LDO"},
                {"name": "VDD_DIG", "voltage": 1.8, "source": "ldo_digital",
                 "description": "Digital core supply from LDO"},
            ]

        # Define block hierarchy
        for block_def in spec.blocks:
            if isinstance(block_def, str):
                block_def = {"name": block_def, "type": "auto"}
            arch["block_hierarchy"].append(block_def)

        # Define interfaces
        if spec.interfaces:
            arch["interfaces"] = spec.interfaces
        else:
            arch["interfaces"] = [
                {"name": "spi", "type": "digital", "signals": ["sclk", "mosi", "miso", "cs_n"]},
            ]

        self.log(f"  Architecture: {len(arch['power_domains'])} power domains, "
                 f"{len(arch['block_hierarchy'])} blocks")
        return arch

    def _design_blocks(self, spec: ChipSpec, arch: dict) -> dict[str, Any]:
        """Design individual blocks."""
        blocks = {}

        for block_def in arch["block_hierarchy"]:
            block_name = block_def if isinstance(block_def, str) else block_def["name"]
            self.log(f"  Designing block: {block_name}")

            block_result = self.block_builder.build_block(
                block_name,
                supply_voltage=spec.supply_voltage,
                io_voltage=spec.io_voltage,
                tech_params=self.tech_mapper.get_params(),
            )
            blocks[block_name] = block_result
            self.log(f"    -> {block_result.get('type', 'unknown')} block, "
                     f"{block_result.get('transistor_count', 0)} transistors")

        return blocks

    def _integrate_chip(self, spec: ChipSpec, arch: dict,
                        blocks: dict) -> dict[str, Any]:
        """Generate top-level integration netlist."""
        lines = [
            f"* {spec.name} - LIN Protocol ASIC Top-Level Netlist",
            f"* Technology: {self.technology}",
            f"* Generated by AMS Simulator ChipDesigner Agent",
            f"* Date: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        # Global parameters
        lines.append(f".param vdd_io={spec.io_voltage}")
        lines.append(f".param vdd_ana={spec.supply_voltage}")
        lines.append(f".param vdd_dig=1.8")
        lines.append(f".param temp=27")
        lines.append("")

        # Include block subcircuits
        for block_name, block_data in blocks.items():
            netlist = block_data.get("netlist", "")
            if netlist:
                lines.append(f"* === {block_name} ===")
                lines.append(netlist)
                lines.append("")

        # Top-level instantiation
        lines.append("* === Top-Level Instantiation ===")
        for block_name, block_data in blocks.items():
            ports = block_data.get("ports", [])
            port_str = " ".join(ports) if ports else "vdd gnd"
            subckt = block_data.get("subckt_name", block_name.upper())
            lines.append(f"X_{block_name} {port_str} {subckt}")

        # Power supplies for simulation
        lines.append("")
        lines.append("* === Power Supplies ===")
        lines.append(f"V_VBAT vbat 0 DC {spec.io_voltage}")
        lines.append(f"V_VDD vdd 0 DC {spec.supply_voltage}")
        lines.append("")

        # Analysis commands
        lines.append("* === Analysis ===")
        lines.append(".op")
        lines.append(".dc V_VBAT 8 18 0.1")
        lines.append(".tran 1u 10m")
        lines.append(".end")

        top_netlist = "\n".join(lines)
        return {
            "top_netlist": top_netlist,
            "block_count": len(blocks),
            "power_domains": arch["power_domains"],
        }

    def _verify_design(self, spec: ChipSpec,
                       result: dict) -> dict[str, Any]:
        """Run basic verification checks."""
        checks = []

        # Check all blocks have netlists
        for name, block in result["blocks"].items():
            has_netlist = bool(block.get("netlist", ""))
            checks.append({
                "check": f"block_{name}_netlist",
                "status": "PASS" if has_netlist else "FAIL",
                "message": f"Block {name} {'has' if has_netlist else 'missing'} netlist",
            })

        # Check power domains
        for pd in result.get("netlists", {}).get("power_domains", []):
            checks.append({
                "check": f"power_domain_{pd['name']}",
                "status": "PASS",
                "message": f"Power domain {pd['name']} at {pd['voltage']}V defined",
            })

        # Check top-level netlist
        top = result.get("netlists", {}).get("top_netlist", "")
        checks.append({
            "check": "top_level_netlist",
            "status": "PASS" if ".end" in top else "FAIL",
            "message": f"Top-level netlist {'complete' if '.end' in top else 'incomplete'}",
        })

        passed = sum(1 for c in checks if c["status"] == "PASS")
        total = len(checks)
        return {
            "checks": checks,
            "passed": passed,
            "total": total,
            "pass_rate": f"{passed/total*100:.1f}%" if total > 0 else "N/A",
        }

    def _generate_reports(self, spec: ChipSpec, result: dict) -> None:
        """Generate design reports."""
        report_dir = self.output_dir / spec.name / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)

        # Design summary
        summary = {
            "chip_name": spec.name,
            "technology": self.technology,
            "supply_voltage": spec.supply_voltage,
            "io_voltage": spec.io_voltage,
            "block_count": len(result["blocks"]),
            "blocks": list(result["blocks"].keys()),
            "verification": result["verification"],
            "design_log": self._log,
        }

        summary_path = report_dir / "design_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2, default=str))
        self.log(f"  Report saved: {summary_path}")

    def _save_design(self, name: str, result: dict) -> None:
        """Save all design artifacts to disk."""
        design_dir = self.output_dir / name
        design_dir.mkdir(parents=True, exist_ok=True)

        # Save top-level netlist
        netlist = result.get("netlists", {}).get("top_netlist", "")
        if netlist:
            (design_dir / f"{name}_top.spice").write_text(netlist)

        # Save block netlists
        blocks_dir = design_dir / "blocks"
        blocks_dir.mkdir(exist_ok=True)
        for block_name, block_data in result["blocks"].items():
            block_netlist = block_data.get("netlist", "")
            if block_netlist:
                (blocks_dir / f"{block_name}.spice").write_text(block_netlist)

        # Save design index
        self.design_index.save(design_dir / "design_index.json")

        self.log(f"  Design saved to: {design_dir}")

    def list_capabilities(self) -> dict[str, Any]:
        """List the designer's capabilities."""
        return {
            "supported_blocks": self.block_builder.list_block_types(),
            "technology": self.technology,
            "tech_params": self.tech_mapper.get_params(),
            "phases": [p.name for p in DesignPhase],
        }
