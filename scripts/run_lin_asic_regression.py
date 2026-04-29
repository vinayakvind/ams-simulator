#!/usr/bin/env python3
"""Run the LIN ASIC regression suite and emit JSON/Markdown reports."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from simulator.verification.lin_asic_regression import (  # noqa: E402
    get_default_report_paths,
    run_lin_asic_regression,
)


def _console_safe(text: str) -> str:
    """Return text that can be printed on the current console encoding."""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    return text.encode(encoding, errors="replace").decode(encoding, errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the LIN ASIC regression suite")
    defaults = get_default_report_paths()
    parser.add_argument("--json", default=str(defaults["json"]), help="Path to JSON report output")
    parser.add_argument("--markdown", default=str(defaults["markdown"]), help="Path to Markdown report output")
    parser.add_argument("--log", default=str(defaults["log"]), help="Path to regression log output")
    parser.add_argument("--quiet", action="store_true", help="Suppress per-test console output")
    args = parser.parse_args()

    log_path = Path(args.log)
    log_lines: list[str] = []

    def _capture(line: str) -> None:
        log_lines.append(line)

    def _emit(line: str) -> None:
        print(_console_safe(line))
        log_lines.append(line)

    report = run_lin_asic_regression(
        json_path=Path(args.json),
        markdown_path=Path(args.markdown),
        log_path=log_path,
        verbose=True,
        emit=_capture if args.quiet else _emit,
    )

    summary = report["summary"]
    _emit("")
    _emit("=== LIN ASIC Regression Summary ===")
    _emit(f"Total  : {summary['total']}")
    _emit(f"Passed : {summary['passed']}")
    _emit(f"Failed : {summary['failed']}")
    _emit(f"Overall: {summary['overall']}")
    _emit(f"JSON   : {report['report_path']}")
    _emit(f"MD     : {report['markdown_report_path']}")
    _emit(f"LOG    : {report['log_path']}")

    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    return 0 if summary["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())