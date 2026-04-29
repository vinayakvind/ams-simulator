"""Generate a portfolio-level design summary in JSON, Markdown, and PowerPoint formats."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from simulator.reporting import generate_portfolio_artifacts  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a portfolio summary PPT across indexed designs")
    parser.add_argument("--output", help="Override PPT output path")
    parser.add_argument("--design", action="append", dest="designs", help="Restrict to one or more indexed design IDs")
    args = parser.parse_args()

    outputs = generate_portfolio_artifacts(
        output_ppt=Path(args.output) if args.output else None,
        design_ids=args.designs,
    )
    print(outputs["ppt"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())