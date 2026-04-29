"""Run one design-level snapshot using verification settings recorded in block spec.yaml."""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from simulator.verification.design_snapshot import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())