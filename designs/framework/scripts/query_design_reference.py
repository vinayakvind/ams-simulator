"""Query an indexed design-reference manifest from the command line."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from simulator.reporting import load_design_reference, query_design_reference  # noqa: E402


def _format_value(value: Any, indent: int = 0) -> str:
    prefix = " " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, child in value.items():
            if isinstance(child, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.append(_format_value(child, indent + 2))
            else:
                lines.append(f"{prefix}{key}: {child}")
        return "\n".join(lines)

    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}-")
                lines.append(_format_value(item, indent + 2))
            else:
                lines.append(f"{prefix}- {item}")
        return "\n".join(lines)

    return f"{prefix}{value}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Query a design-reference manifest")
    parser.add_argument("--input", required=True, help="Path to design_reference.json")
    parser.add_argument("--block", help="Optional block key or block name")
    parser.add_argument("--section", default="summary", help="Section to return")
    parser.add_argument("--list-blocks", action="store_true", help="List block keys only")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of plain text")
    args = parser.parse_args()

    reference = load_design_reference(args.input)

    if args.list_blocks:
        blocks = [
            {
                "block_key": block.get("block_key", ""),
                "name": block.get("name", ""),
                "domain": block.get("domain", ""),
            }
            for block in reference.get("blocks", [])
        ]
        if args.json:
            print(json.dumps(blocks, indent=2))
        else:
            for block in blocks:
                print(f"{block['block_key']}: {block['name']} [{block['domain']}]")
        return 0

    result = query_design_reference(reference, block_key=args.block, section=args.section)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(_format_value(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())