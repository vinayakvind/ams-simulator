"""Render a design-reference manifest into a standalone HTML page."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from simulator.reporting import load_design_reference, render_design_reference_html  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a design-reference webpage")
    parser.add_argument("--input", required=True, help="Path to design_reference.json")
    parser.add_argument("--output", help="Path to the generated HTML page")
    args = parser.parse_args()

    reference = load_design_reference(args.input)
    design_id = reference.get("design", {}).get("id", "design")
    output_path = Path(args.output) if args.output else PROJECT_ROOT / "reports" / f"{design_id}_design_reference.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_design_reference_html(reference), encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())