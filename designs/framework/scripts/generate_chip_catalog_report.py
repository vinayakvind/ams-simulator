"""Generate reusable chip assembly catalog reports."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from simulator.reporting.chip_catalog import main


if __name__ == "__main__":
    raise SystemExit(main())