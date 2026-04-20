"""
Agent CLI - Command-line interface for the chip design agents.

Provides CLI commands for:
    ams-agent design  <chip_name>  - Design a chip from spec
    ams-agent list                 - List available block types
    ams-agent tech                 - List technologies
    ams-agent build   <block>      - Build a single block
    ams-agent template <name>      - Show design template
    ams-agent info                 - Show agent capabilities
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the agent CLI."""
    parser = argparse.ArgumentParser(
        prog="ams-agent",
        description="AMS Simulator - Chip Design Agent CLI",
    )
    sub = parser.add_subparsers(dest="command", help="Agent command")

    # ── design ──
    p_design = sub.add_parser("design", help="Design a complete chip")
    p_design.add_argument("chip_name", help="Name of the chip to design")
    p_design.add_argument("--spec", type=str,
                          help="Path to JSON spec file")
    p_design.add_argument("--tech", default="generic180",
                          help="Technology node (default: generic180)")
    p_design.add_argument("--output", "-o", default="designs",
                          help="Output directory")
    p_design.add_argument("--template", type=str,
                          help="Use a design template")

    # ── build ──
    p_build = sub.add_parser("build", help="Build a single block")
    p_build.add_argument("block_name", help="Block type to build")
    p_build.add_argument("--tech", default="generic180")
    p_build.add_argument("--vdd", type=float, default=3.3,
                         help="Supply voltage")
    p_build.add_argument("--vio", type=float, default=12.0,
                         help="IO voltage")
    p_build.add_argument("--output", "-o", type=str,
                         help="Output file (SPICE netlist)")

    # ── list ──
    sub.add_parser("list", help="List available block types")

    # ── tech ──
    sub.add_parser("tech", help="List available technologies")

    # ── template ──
    p_template = sub.add_parser("template", help="Show design template")
    p_template.add_argument("name", nargs="?", default=None,
                            help="Template name (omit to list all)")

    # ── info ──
    sub.add_parser("info", help="Show agent capabilities")

    # ── lin-asic ──
    p_lin = sub.add_parser("lin-asic",
                           help="Design a complete LIN Protocol ASIC")
    p_lin.add_argument("--tech", default="generic180")
    p_lin.add_argument("--output", "-o", default="designs")
    p_lin.add_argument("--vbat", type=float, default=12.0,
                       help="Battery voltage (default: 12V)")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    try:
        if args.command == "design":
            return _cmd_design(args)
        elif args.command == "build":
            return _cmd_build(args)
        elif args.command == "list":
            return _cmd_list()
        elif args.command == "tech":
            return _cmd_tech()
        elif args.command == "template":
            return _cmd_template(args)
        elif args.command == "info":
            return _cmd_info()
        elif args.command == "lin-asic":
            return _cmd_lin_asic(args)
        else:
            parser.print_help()
            return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _cmd_design(args) -> int:
    """Design a complete chip."""
    from simulator.agents.chip_designer import ChipDesigner

    spec: dict[str, Any] = {}
    if args.spec:
        spec_path = Path(args.spec)
        if spec_path.exists():
            spec = json.loads(spec_path.read_text())
        else:
            print(f"Spec file not found: {args.spec}", file=sys.stderr)
            return 1
    elif args.template:
        spec = _get_template_spec(args.template)

    designer = ChipDesigner(technology=args.tech, output_dir=args.output)
    result = designer.create_chip(args.chip_name, spec)

    v = result.get("verification", {})
    print(f"\nDesign complete: {result.get('name')}")
    print(f"Blocks: {len(result.get('blocks', {}))}")
    print(f"Verification: {v.get('passed', 0)}/{v.get('total', 0)} checks passed")
    return 0


def _cmd_build(args) -> int:
    """Build a single block."""
    from simulator.agents.block_builder import BlockBuilder

    builder = BlockBuilder(args.tech)
    result = builder.build_block(
        args.block_name,
        supply_voltage=args.vdd,
        io_voltage=args.vio,
    )

    if args.output:
        Path(args.output).write_text(result.get("netlist", ""))
        print(f"Block netlist saved to: {args.output}")
    else:
        print(f"Block: {result['name']} ({result['type']})")
        print(f"Subcircuit: {result.get('subckt_name', 'N/A')}")
        print(f"Transistors: {result.get('transistor_count', 0)}")
        if result.get("gate_count"):
            print(f"Gates: {result['gate_count']}")
        print(f"Ports: {', '.join(result.get('ports', []))}")
        if result.get("specs"):
            print("\nSpecifications:")
            for k, v in result["specs"].items():
                print(f"  {k}: {v}")
        print(f"\n--- SPICE Netlist ---")
        print(result.get("netlist", "(empty)"))

    return 0


def _cmd_list() -> int:
    """List available block types."""
    from simulator.agents.block_builder import BlockBuilder

    builder = BlockBuilder()
    blocks = builder.list_block_types()

    print("Available block types:")
    print("=" * 40)
    for b in blocks:
        print(f"  {b}")
    print(f"\nTotal: {len(blocks)} block types")
    return 0


def _cmd_tech() -> int:
    """List available technologies."""
    from simulator.agents.tech_mapper import TechMapper

    techs = TechMapper.list_technologies()
    print("Available technologies:")
    print("=" * 50)
    for t in techs:
        print(f"  {t['name']:15s} {t['node']:6s} VDD={t['vdd']}V  {t['description']}")
    return 0


def _cmd_template(args) -> int:
    """Show design templates."""
    from simulator.agents.design_index import DESIGN_TEMPLATES

    if args.name is None:
        print("Available design templates:")
        print("=" * 40)
        for name in DESIGN_TEMPLATES:
            steps = DESIGN_TEMPLATES[name]
            print(f"  {name} ({len(steps)} phases)")
        return 0

    template = DESIGN_TEMPLATES.get(args.name)
    if template is None:
        print(f"Template not found: {args.name}", file=sys.stderr)
        print(f"Available: {', '.join(DESIGN_TEMPLATES.keys())}")
        return 1

    print(f"Design Template: {args.name}")
    print("=" * 50)
    for i, step in enumerate(template, 1):
        print(f"  {i:2d}. [{step['phase']}] {step['description']}")
        if "actions" in step:
            for action in step["actions"]:
                print(f"      -> {action}")
    return 0


def _cmd_info() -> int:
    """Show agent capabilities."""
    from simulator.agents.chip_designer import ChipDesigner

    designer = ChipDesigner()
    caps = designer.list_capabilities()

    print("AMS Simulator - Chip Design Agent")
    print("=" * 50)
    print(f"\nTechnology: {caps['technology']}")
    print(f"\nSupported blocks ({len(caps['supported_blocks'])}):")
    for b in caps["supported_blocks"]:
        print(f"  - {b}")
    print(f"\nDesign phases:")
    for p in caps["phases"]:
        print(f"  - {p}")
    print(f"\nTech parameters:")
    for k, v in caps["tech_params"].items():
        print(f"  {k}: {v}")
    return 0


def _cmd_lin_asic(args) -> int:
    """Design a complete LIN Protocol ASIC."""
    from simulator.agents.chip_designer import ChipDesigner

    spec = {
        "description": "LIN Protocol ASIC - ISO 17987 compliant",
        "technology": args.tech,
        "supply_voltage": 3.3,
        "io_voltage": args.vbat,
        "temperature_range": (-40.0, 125.0),
        "target_power": 50e-3,
        "blocks": [
            {"name": "bandgap_ref", "type": "analog"},
            {"name": "ldo_analog", "type": "analog"},
            {"name": "ldo_digital", "type": "analog"},
            {"name": "ldo_lin", "type": "analog"},
            {"name": "lin_transceiver", "type": "analog"},
            {"name": "spi_controller", "type": "digital"},
            {"name": "lin_controller", "type": "digital"},
            {"name": "register_file", "type": "digital"},
            {"name": "control_logic", "type": "mixed"},
        ],
        "power_domains": [
            {"name": "VBAT", "voltage": args.vbat, "source": "external",
             "description": "Battery / LIN bus supply"},
            {"name": "VDD_LIN", "voltage": 5.0, "source": "ldo_lin",
             "description": "LIN transceiver supply"},
            {"name": "VDD_ANA", "voltage": 3.3, "source": "ldo_analog",
             "description": "Analog core supply"},
            {"name": "VDD_DIG", "voltage": 1.8, "source": "ldo_digital",
             "description": "Digital core supply"},
        ],
        "interfaces": [
            {"name": "LIN_BUS", "type": "analog", "direction": "bidirectional",
             "description": "LIN bus single-wire interface"},
            {"name": "SPI", "type": "digital",
             "signals": ["SCLK", "MOSI", "MISO", "CS_N"],
             "description": "SPI slave for host MCU register access"},
            {"name": "IRQ", "type": "digital", "direction": "output",
             "description": "Interrupt output to host MCU"},
        ],
    }

    designer = ChipDesigner(technology=args.tech, output_dir=args.output)
    result = designer.create_chip("lin_asic", spec)

    v = result.get("verification", {})
    print(f"\nLIN ASIC Design Complete!")
    print(f"Blocks: {len(result.get('blocks', {}))}")
    print(f"Verification: {v.get('passed', 0)}/{v.get('total', 0)} checks passed")
    print(f"Output: {Path(args.output) / 'lin_asic'}")
    return 0


def _get_template_spec(template_name: str) -> dict[str, Any]:
    """Convert a template name to a chip spec."""
    if template_name == "lin_protocol_asic":
        return {
            "supply_voltage": 3.3,
            "io_voltage": 12.0,
            "blocks": [
                "bandgap_ref", "ldo_analog", "ldo_digital", "ldo_lin",
                "lin_transceiver", "spi_controller", "lin_controller",
                "register_file", "control_logic",
            ],
        }
    return {"blocks": []}


if __name__ == "__main__":
    sys.exit(main())
