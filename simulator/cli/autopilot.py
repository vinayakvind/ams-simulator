"""Autopilot CLI for indexed design execution, reporting, and validation."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any

from simulator.reporting import (
    generate_portfolio_artifacts,
    load_design_reference,
    render_design_reference_html,
)
from simulator.verification import run_design_snapshot, run_lin_asic_regression


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JSON_REPORT = PROJECT_ROOT / "reports" / "design_autopilot_latest.json"
DEFAULT_MARKDOWN_REPORT = PROJECT_ROOT / "reports" / "design_autopilot_latest.md"


def _console_safe(text: str) -> str:
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    return text.encode(encoding, errors="replace").decode(encoding, errors="replace")


def _log(message: str, quiet: bool = False) -> None:
    if not quiet:
        print(_console_safe(message))


def _artifact_check(path: Path) -> dict[str, Any]:
    exists = path.exists()
    return {
        "path": str(path),
        "exists": exists,
        "size_bytes": path.stat().st_size if exists else 0,
    }


def _discover_design_manifests(design_ids: list[str] | None = None) -> list[tuple[str, Path]]:
    manifests = {
        path.parent.name: path
        for path in sorted((PROJECT_ROOT / "designs").glob("*/design_reference.json"))
    }
    if design_ids:
        missing = [design_id for design_id in design_ids if design_id not in manifests]
        if missing:
            raise FileNotFoundError(f"Missing design_reference.json for: {', '.join(missing)}")
        return [(design_id, manifests[design_id]) for design_id in design_ids]
    return sorted(manifests.items())


def _write_design_reference(manifest_path: Path) -> Path:
    reference = load_design_reference(manifest_path)
    design_id = str(reference.get("design", {}).get("id", manifest_path.parent.name))
    output_path = PROJECT_ROOT / "reports" / f"{design_id}_design_reference.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_design_reference_html(reference), encoding="utf-8")
    return output_path


def _run_design_pipeline(design_id: str, manifest_path: Path, quiet: bool) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    steps: list[dict[str, Any]] = []
    reference = load_design_reference(manifest_path)
    title = str(reference.get("design", {}).get("title", design_id))
    mode = "lin-regression" if design_id == "lin_asic" else "design-snapshot"
    _log(f"[design] {design_id}: start {mode}", quiet)

    result: dict[str, Any] = {
        "id": design_id,
        "title": title,
        "execution_mode": mode,
        "overall": "FAIL",
        "artifact_checks": [],
    }

    try:
        if design_id == "lin_asic":
            report = run_lin_asic_regression()
        else:
            report = run_design_snapshot(design_id)
        result["report_path"] = report["report_path"]
        result["markdown_report_path"] = report["markdown_report_path"]
        result["overall"] = report["summary"].get("overall", "FAIL")
        result["summary"] = report["summary"]
        steps.append(
            {
                "step": f"Execute {design_id}",
                "status": result["overall"],
                "details": f"{mode} completed with overall {result['overall']}",
            }
        )
        html_path = _write_design_reference(manifest_path)
        result["html_path"] = str(html_path)
        result["artifact_checks"] = [
            _artifact_check(Path(report["report_path"])),
            _artifact_check(Path(report["markdown_report_path"])),
            _artifact_check(html_path),
        ]
        steps.append(
            {
                "step": f"Render {design_id} HTML",
                "status": "PASS" if html_path.exists() else "FAIL",
                "details": str(html_path),
            }
        )
    except Exception as exc:
        result["error"] = str(exc)
        result["overall"] = "FAIL"
        steps.append(
            {
                "step": f"Execute {design_id}",
                "status": "FAIL",
                "details": str(exc),
            }
        )
    return result, steps


def _overall_status(designs: list[dict[str, Any]], portfolio_checks: list[dict[str, Any]]) -> str:
    if any(not check.get("exists") for design in designs for check in design.get("artifact_checks", [])):
        return "FAIL"
    if any(not check.get("exists") for check in portfolio_checks):
        return "FAIL"
    if any(design.get("overall") == "FAIL" for design in designs):
        return "FAIL"
    if any(design.get("overall") == "UNRESOLVED" for design in designs):
        return "UNRESOLVED"
    return "PASS"


def _write_markdown_report(summary: dict[str, Any], output_path: Path) -> None:
    lines = [
        "# Design Autopilot Report",
        "",
        f"Generated: {summary['generated_at']}",
        f"Overall: {summary['overall']}",
        f"Strict mode: {summary['strict_mode']}",
        "",
        "## Executed Plan",
        "",
        "| Step | Status | Details |",
        "|------|--------|---------|",
    ]
    for step in summary.get("steps", []):
        lines.append(f"| {step['step']} | {step['status']} | {step['details']} |")

    lines.extend(["", "## Design Results", "", "| Design | Mode | Overall | JSON | HTML |", "|--------|------|---------|------|------|"])
    for design in summary.get("designs", []):
        lines.append(
            f"| {design['id']} | {design['execution_mode']} | {design['overall']} | {design.get('report_path', '---')} | {design.get('html_path', '---')} |"
        )

    lines.extend(["", "## Portfolio Outputs", ""])
    portfolio = summary.get("portfolio", {})
    lines.append(f"- JSON: {portfolio.get('json_path', '---')}")
    lines.append(f"- Markdown: {portfolio.get('markdown_path', '---')}")
    lines.append(f"- PowerPoint: {portfolio.get('ppt_path', '---')}")

    lines.extend(["", "## Validation", ""])
    for design in summary.get("designs", []):
        lines.append(f"### {design['id']}")
        lines.append("")
        for check in design.get("artifact_checks", []):
            state = "OK" if check.get("exists") else "MISSING"
            lines.append(f"- {state}: {check['path']}")
        if design.get("error"):
            lines.append(f"- Error: {design['error']}")
        lines.append("")
    lines.append("### Portfolio")
    lines.append("")
    for check in portfolio.get("artifact_checks", []):
        state = "OK" if check.get("exists") else "MISSING"
        lines.append(f"- {state}: {check['path']}")
    lines.append("")

    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_autopilot(
    design_ids: list[str] | None = None,
    json_report: Path = DEFAULT_JSON_REPORT,
    markdown_report: Path = DEFAULT_MARKDOWN_REPORT,
    strict: bool = False,
    quiet: bool = False,
) -> dict[str, Any]:
    """Run the indexed design autopilot flow and write summary artifacts."""
    manifests = _discover_design_manifests(design_ids)
    steps: list[dict[str, Any]] = [
        {
            "step": "Discover indexed designs",
            "status": "PASS",
            "details": ", ".join(design_id for design_id, _path in manifests) or "No designs found",
        }
    ]

    design_results: list[dict[str, Any]] = []
    for design_id, manifest_path in manifests:
        design_result, design_steps = _run_design_pipeline(design_id, manifest_path, quiet)
        design_results.append(design_result)
        steps.extend(design_steps)

    _log("[portfolio] generate portfolio artifacts", quiet)
    portfolio_payload = generate_portfolio_artifacts(design_ids=[design_id for design_id, _path in manifests])
    portfolio_checks = [
        _artifact_check(portfolio_payload["json"]),
        _artifact_check(portfolio_payload["markdown"]),
        _artifact_check(portfolio_payload["ppt"]),
    ]
    steps.append(
        {
            "step": "Generate portfolio artifacts",
            "status": "PASS" if all(check["exists"] for check in portfolio_checks) else "FAIL",
            "details": str(portfolio_payload["ppt"]),
        }
    )

    overall = _overall_status(design_results, portfolio_checks)
    summary = {
        "generated_at": datetime.now().isoformat(),
        "python_executable": sys.executable,
        "strict_mode": strict,
        "overall": overall,
        "steps": steps,
        "designs": design_results,
        "portfolio": {
            "json_path": str(portfolio_payload["json"]),
            "markdown_path": str(portfolio_payload["markdown"]),
            "ppt_path": str(portfolio_payload["ppt"]),
            "artifact_checks": portfolio_checks,
        },
    }

    json_report.parent.mkdir(parents=True, exist_ok=True)
    json_report.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_markdown_report(summary, markdown_report)
    summary["json_report"] = str(json_report)
    summary["markdown_report"] = str(markdown_report)
    return summary


def main(argv: list[str] | None = None) -> int:
    """Run the autopilot CLI."""
    parser = argparse.ArgumentParser(description="Run the indexed design autopilot flow")
    parser.add_argument(
        "--design",
        action="append",
        dest="designs",
        help="Restrict autopilot to one or more indexed design IDs",
    )
    parser.add_argument("--json", help="Override the autopilot JSON summary path")
    parser.add_argument("--markdown", help="Override the autopilot Markdown summary path")
    parser.add_argument("--strict", action="store_true", help="Return non-zero unless every design is PASS")
    parser.add_argument("--quiet", action="store_true", help="Reduce console output")
    args = parser.parse_args(argv)

    summary = run_autopilot(
        design_ids=args.designs,
        json_report=Path(args.json) if args.json else DEFAULT_JSON_REPORT,
        markdown_report=Path(args.markdown) if args.markdown else DEFAULT_MARKDOWN_REPORT,
        strict=args.strict,
        quiet=args.quiet,
    )
    _log(f"[done] autopilot summary: {summary['json_report']}", args.quiet)
    if args.strict and summary["overall"] != "PASS":
        return 1
    return 0


__all__ = ["run_autopilot", "main"]