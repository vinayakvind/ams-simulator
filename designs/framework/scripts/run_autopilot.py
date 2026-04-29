"""Run the indexed design autopilot flow from the framework scripts folder."""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from simulator.cli.autopilot import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())