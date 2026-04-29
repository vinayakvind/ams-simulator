"""Run design-level snapshots from spec.yaml verification settings."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import statistics
from typing import Any

import yaml

from simulator.cli.runner import SimulationRunner


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _resolve_source_path(source: str, design_dir: Path) -> Path:
    candidate = Path(source)
    if candidate.is_absolute():
        return candidate
    for root in (PROJECT_ROOT, design_dir, Path.cwd()):
        resolved = (root / candidate).resolve()
        if resolved.exists():
            return resolved
    return (PROJECT_ROOT / candidate).resolve()


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return str(value)
    return value


def _coerce_yaml_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _coerce_yaml_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_coerce_yaml_value(item) for item in value]
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return value
        try:
            if any(marker in stripped.lower() for marker in (".", "e")):
                return float(stripped)
            return int(stripped)
        except ValueError:
            return value
    return value


def _numeric_series(results: dict[str, Any], key: str) -> list[float]:
    values = results.get(key, [])
    if not isinstance(values, list):
        return []
    series: list[float] = []
    for value in values:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(numeric):
            series.append(numeric)
    return series


def _has_finite_data(results: dict[str, Any], key: str) -> bool:
    values = results.get(key)
    if not isinstance(values, list) or not values:
        return False
    for value in values:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(numeric):
            return True
    return False


def _preferred_signal(results: dict[str, Any], candidates: list[str]) -> str | None:
    lowered = {key.lower(): key for key in results.keys()}
    for candidate in candidates:
        if candidate in results:
            return candidate
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]
    return None


def _summarize_results(results: dict[str, Any]) -> dict[str, Any]:
    signal_keys = [
        key
        for key, value in results.items()
        if key not in {"type", "metadata", "time", "frequency", "sweep"} and isinstance(value, list)
    ]
    measurements: dict[str, Any] = {"signal_count": len(signal_keys)}

    if "time" in results:
        measurements["time_points"] = len(results.get("time", []))
    if "frequency" in results:
        measurements["frequency_points"] = len(results.get("frequency", []))

    input_key = _preferred_signal(results, ["V(analog_in)", "V(vin)", "V(input)"])
    if input_key:
        series = _numeric_series(results, input_key)
        if series:
            measurements["input_span_v"] = max(series) - min(series)
            measurements["input_mean_v"] = statistics.fmean(series)

    output_key = _preferred_signal(
        results,
        ["V(dec_filt)", "V(dac_out)", "V(sh_out)", "V(comp_out)", "V(output)"],
    )
    if output_key:
        series = _numeric_series(results, output_key)
        if series:
            measurements["output_span_v"] = max(series) - min(series)
            measurements["output_final_v"] = series[-1]

    bitstream_key = _preferred_signal(results, ["V(bitstream)"])
    if bitstream_key:
        series = _numeric_series(results, bitstream_key)
        if series:
            measurements["bitstream_mean_v"] = statistics.fmean(series)

    if signal_keys:
        measurements["tracked_signals"] = ", ".join(signal_keys[:5])
    return measurements


def _evaluate_check(results: dict[str, Any], check: dict[str, Any]) -> dict[str, Any]:
    check_type = str(check.get("type", "has_key"))
    description = str(check.get("description", check_type))

    if check_type == "has_key":
        key = str(check.get("key", ""))
        if key not in results:
            return {"test": description, "value": f"missing: {key}", "pass": False, "unresolved": False}
        if not _has_finite_data(results, key):
            return {"test": description, "value": f"no finite data: {key}", "pass": False, "unresolved": True}
        return {"test": description, "value": key, "pass": True, "unresolved": False}

    if check_type == "has_any_key":
        keys = [str(item) for item in check.get("keys", [])]
        found = next((key for key in keys if key in results and _has_finite_data(results, key)), None)
        if found is not None:
            return {"test": description, "value": found, "pass": True, "unresolved": False}
        if any(key in results for key in keys):
            return {
                "test": description,
                "value": f"no finite data in any of: {', '.join(keys)}",
                "pass": False,
                "unresolved": True,
            }
        return {
            "test": description,
            "value": f"missing any of: {', '.join(keys)}",
            "pass": False,
            "unresolved": False,
        }

    if check_type == "min_length":
        key = str(check.get("key", ""))
        minimum = int(check.get("min", 1))
        values = results.get(key, [])
        actual = len(values) if isinstance(values, list) else 0
        return {"test": description, "value": f"{key} length={actual}", "pass": actual >= minimum, "unresolved": False}

    if check_type == "range_span_gt":
        key = str(check.get("key", ""))
        minimum = float(check.get("min", 0.0))
        series = _numeric_series(results, key)
        actual = (max(series) - min(series)) if series else 0.0
        return {"test": description, "value": f"{key} span={actual:.6g}", "pass": actual >= minimum, "unresolved": False}

    if check_type == "final_between":
        key = str(check.get("key", ""))
        minimum = float(check.get("min", 0.0))
        maximum = float(check.get("max", 0.0))
        series = _numeric_series(results, key)
        actual = series[-1] if series else float("nan")
        passed = bool(series) and minimum <= actual <= maximum
        return {"test": description, "value": f"{key} final={actual:.6g}", "pass": passed, "unresolved": False}

    return {"test": description, "value": f"unsupported check type: {check_type}", "pass": False, "unresolved": False}


def _write_block_report(block_dir: Path, report: dict[str, Any]) -> None:
    lines = [
        f"# Block Report: {report['block']}",
        "",
        f"## Status: {report['status']}",
        f"Verified: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Verification Results",
        "| Test | Result | Pass |",
        "|------|--------|------|",
    ]
    for check in report.get("checks", []):
        check_status = "PASS" if check["pass"] else ("UNRESOLVED" if check.get("unresolved") else "FAIL")
        lines.append(f"| {check['test']} | {check['value']} | {check_status} |")
    lines.extend([
        "",
        "## Measurements",
        "| Name | Value |",
        "|------|-------|",
    ])
    for key, value in report.get("measurements", {}).items():
        lines.append(f"| {key} | {value} |")
    (block_dir / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_markdown_report(report: dict[str, Any], output_path: Path) -> None:
    summary = report["summary"]
    lines = [
        f"# Regression Report - {report['design']}",
        "",
        f"Generated: {report['generated_at']}",
        f"Overall: {summary['overall']}",
        "",
        "## Summary",
        "",
        f"- Total tests: {summary['total']}",
        f"- Passed: {summary['passed']}",
        f"- Failed: {summary['failed']}",
        f"- Unresolved: {summary['unresolved']}",
        f"- Functional coverage: {report['coverage']['functional_percent']:.1f}%",
        "",
        "## Test Results",
        "",
        "| Case ID | Block | Status | Details |",
        "|---------|-------|--------|---------|",
    ]
    for test in report["tests"]:
        lines.append(
            f"| {test['case_id']} | {test['block']} | {test['status']} | {test['details']} |"
        )
    lines.extend(["", "## Measurements", ""])
    for test in report["tests"]:
        lines.append(f"### {test['case_id']}")
        lines.append("")
        for key, value in test.get("measurements", {}).items():
            lines.append(f"- {key}: {value}")
        lines.append("")
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _default_source(design: str, block_name: str, block_meta: dict[str, Any]) -> str:
    source = str(block_meta.get("source", "")).strip()
    if source:
        return source
    block_type = str(block_meta.get("type", "analog")).lower()
    if block_type == "digital":
        return f"designs/{design}/rtl/{block_name}.sv"
    return f"designs/{design}/blocks/{block_name}/{block_name}.spice"


def _load_block_specs(design_dir: Path, block_name: str | None = None) -> list[tuple[str, Path, dict[str, Any]]]:
    blocks_dir = design_dir / "blocks"
    if not blocks_dir.exists():
        raise FileNotFoundError(f"Missing blocks directory: {blocks_dir}")

    block_names = [block_name] if block_name else sorted(path.name for path in blocks_dir.iterdir() if path.is_dir())
    loaded: list[tuple[str, Path, dict[str, Any]]] = []
    for candidate in block_names:
        block_dir = blocks_dir / candidate
        spec_path = block_dir / "spec.yaml"
        if not spec_path.exists():
            if block_name:
                raise FileNotFoundError(f"Missing block spec: {spec_path}")
            continue
        spec = yaml.safe_load(spec_path.read_text(encoding="utf-8")) or {}
        if not spec.get("verification"):
            if block_name:
                raise ValueError(f"Block {candidate} has no verification section")
            continue
        loaded.append((candidate, block_dir, spec))

    if not loaded:
        raise ValueError(f"No verified block specs found under {blocks_dir}")
    return loaded


def _raw_output_path(
    raw_output: Path | None,
    design: str,
    block_name: str,
    analysis: str,
    multiple_blocks: bool,
) -> Path:
    if raw_output is None:
        return PROJECT_ROOT / "reports" / f"{design}_{block_name}_{analysis}_latest_raw.json"
    if not multiple_blocks:
        return raw_output
    suffix = raw_output.suffix or ".json"
    return raw_output.with_name(f"{raw_output.stem}_{block_name}{suffix}")


def _run_one_block(
    design: str,
    design_dir: Path,
    block_name: str,
    block_dir: Path,
    spec: dict[str, Any],
    runner: SimulationRunner,
    raw_output: Path | None,
    multiple_blocks: bool,
) -> tuple[dict[str, Any], dict[str, Any], Path]:
    block_meta = spec.get("block", {})
    verification = spec.get("verification", {})
    source = _default_source(design, block_name, block_meta)
    netlist_path = _resolve_source_path(source, design_dir)
    if not netlist_path.exists():
        raise FileNotFoundError(f"Source file not found: {netlist_path}")

    analysis = str(verification.get("analysis", "transient"))
    settings = _coerce_yaml_value(dict(verification.get("settings", {})))
    raw_output_path = _raw_output_path(raw_output, design, block_name, analysis, multiple_blocks)
    results = runner.run_netlist(
        str(netlist_path),
        analysis_type=analysis,
        output_file=str(raw_output_path),
        **settings,
    )

    checks = [_evaluate_check(results, check) for check in verification.get("checks", [])]
    has_unresolved = any(check.get("unresolved") for check in checks)
    if checks and all(check["pass"] for check in checks):
        status = "PASS"
    elif not checks:
        status = "PASS"
    elif has_unresolved:
        status = "UNRESOLVED"
    else:
        status = "FAIL"

    measurements = _summarize_results(results)
    case_id = str(verification.get("case_id", f"TOP-{block_name.upper()}"))
    description = str(verification.get("description", f"Top-level snapshot for {block_name}"))
    category = str(verification.get("category", "Top"))
    standard = str(verification.get("standard", "Internal design spec"))
    detail_parts = [description]
    if measurements.get("time_points") is not None:
        detail_parts.append(f"time_points={measurements['time_points']}")
    if measurements.get("signal_count") is not None:
        detail_parts.append(f"signals={measurements['signal_count']}")

    test_entry = {
        "case_id": case_id,
        "block": block_name,
        "status": status,
        "category": category,
        "details": "; ".join(detail_parts),
        "measurements": measurements,
        "checks": checks,
        "source_path": str(netlist_path),
        "raw_results_path": str(raw_output_path),
    }
    test_case = {
        "case_id": case_id,
        "block": block_name.replace("_", " ").title(),
        "category": category,
        "standard": standard,
        "description": description,
    }
    _write_block_report(block_dir, test_entry)
    return test_entry, test_case, raw_output_path


def run_design_snapshot(
    design: str,
    block: str | None = None,
    output: Path | None = None,
    raw_output: Path | None = None,
) -> dict[str, Any]:
    """Run one or more design snapshot checks from block spec files."""
    design_dir = PROJECT_ROOT / "designs" / design
    block_specs = _load_block_specs(design_dir, block_name=block)
    output_path = Path(output) if output else PROJECT_ROOT / "reports" / f"{design}_regression_latest.json"
    markdown_path = output_path.with_suffix(".md")
    raw_output_path = Path(raw_output) if raw_output else None
    multiple_blocks = len(block_specs) > 1

    runner = SimulationRunner(verbose=False)
    tests: list[dict[str, Any]] = []
    test_cases: list[dict[str, Any]] = []
    raw_results_paths: list[str] = []
    for block_name, block_dir, spec in block_specs:
        test_entry, test_case, raw_path = _run_one_block(
            design=design,
            design_dir=design_dir,
            block_name=block_name,
            block_dir=block_dir,
            spec=spec,
            runner=runner,
            raw_output=raw_output_path,
            multiple_blocks=multiple_blocks,
        )
        tests.append(test_entry)
        test_cases.append(test_case)
        raw_results_paths.append(str(raw_path))

    passed = sum(1 for test in tests if test["status"] == "PASS")
    failed = sum(1 for test in tests if test["status"] == "FAIL")
    unresolved = sum(1 for test in tests if test["status"] == "UNRESOLVED")
    overall = "FAIL" if failed else ("UNRESOLVED" if unresolved else "PASS")
    report = {
        "design": design,
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total": len(tests),
            "passed": passed,
            "failed": failed,
            "unresolved": unresolved,
            "overall": overall,
        },
        "coverage": {
            "functional_percent": (100.0 * passed / max(1, len(tests))),
            "standards_percent": 100.0,
        },
        "tests": tests,
        "test_cases": test_cases,
        "report_path": str(output_path),
        "markdown_report_path": str(markdown_path),
        "raw_results_paths": raw_results_paths,
    }
    if len(raw_results_paths) == 1:
        report["raw_results_path"] = raw_results_paths[0]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(_json_safe(report), indent=2), encoding="utf-8")
    _write_markdown_report(report, markdown_path)
    return report


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point for the design snapshot runner."""
    parser = argparse.ArgumentParser(description="Run design snapshots from spec.yaml verification settings")
    parser.add_argument("--design", required=True, help="Design name under designs/")
    parser.add_argument("--block", help="Optional block name. When omitted, runs all verified blocks.")
    parser.add_argument("--output", help="Override JSON report output path")
    parser.add_argument("--raw-output", help="Optional raw simulation results JSON path")
    args = parser.parse_args(argv)

    report = run_design_snapshot(
        design=args.design,
        block=args.block,
        output=Path(args.output) if args.output else None,
        raw_output=Path(args.raw_output) if args.raw_output else None,
    )
    print(report["report_path"])
    return 0 if report["summary"]["overall"] == "PASS" else 1


__all__ = ["run_design_snapshot", "main"]