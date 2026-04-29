"""Design reference utilities for indexed design methodology pages."""

from __future__ import annotations

from datetime import datetime
import html
import json
import math
from pathlib import Path
import re
from typing import Any, Optional


def load_design_reference(reference_path: str | Path) -> dict[str, Any]:
    """Load a design-reference JSON manifest from disk."""
    path = Path(reference_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("source_path", str(path))
    data["runtime_results"] = _load_runtime_results(path, data)
    return data


def _project_root_for_reference(reference_path: Path) -> Path:
    resolved = reference_path.resolve()
    if len(resolved.parents) >= 3:
        return resolved.parents[2]
    return resolved.parent


def _relative_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _load_json_artifact(path: Path) -> Optional[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(payload, dict):
        return payload
    return None


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _report_sort_key(report: dict[str, Any]) -> tuple[float, str]:
    timestamp = _parse_timestamp(report.get("generated_at") or report.get("timestamp"))
    return (
        timestamp.timestamp() if timestamp else 0.0,
        str(report.get("source_path", "")),
    )


def _load_runtime_results(reference_path: Path, reference: dict[str, Any]) -> dict[str, Any]:
    project_root = _project_root_for_reference(reference_path)
    reports_dir = project_root / "reports"
    design_id = str(reference.get("design", {}).get("id", "")).strip()

    runtime_results: dict[str, Any] = {
        "regression_history": [],
        "latest_regression": None,
        "psrr_reports": [],
        "results_by_block": {},
        "psrr_by_block": {},
    }
    if not design_id or not reports_dir.exists():
        return runtime_results

    regression_history: list[dict[str, Any]] = []
    for report_path in reports_dir.glob(f"{design_id}_regression*.json"):
        report = _load_json_artifact(report_path)
        if report is None:
            continue
        report["source_path"] = _relative_path(report_path, project_root)
        regression_history.append(report)
    regression_history.sort(key=_report_sort_key, reverse=True)
    runtime_results["regression_history"] = regression_history
    if regression_history:
        runtime_results["latest_regression"] = regression_history[0]

    psrr_reports: list[dict[str, Any]] = []
    for report_path in reports_dir.glob("*psrr*.json"):
        report = _load_json_artifact(report_path)
        if report is None:
            continue
        context = report.get("context", {})
        if str(context.get("design", "")).strip() != design_id:
            continue
        report["source_path"] = _relative_path(report_path, project_root)
        psrr_reports.append(report)
    psrr_reports.sort(
        key=lambda report: (
            str(report.get("context", {}).get("block", "")),
            str(report.get("context", {}).get("corner", "")),
            float(report.get("context", {}).get("temperature_c", 0.0)),
            str(report.get("source_path", "")),
        )
    )
    runtime_results["psrr_reports"] = psrr_reports

    latest_regression = runtime_results.get("latest_regression")
    if latest_regression:
        for test in latest_regression.get("tests", []):
            block = find_design_block(reference, str(test.get("block", "")))
            if block is None:
                continue
            block_key = str(block.get("block_key", "")).strip()
            if block_key:
                runtime_results["results_by_block"][block_key] = test

    for report in psrr_reports:
        block = find_design_block(reference, str(report.get("context", {}).get("block", "")))
        if block is None:
            continue
        block_key = str(block.get("block_key", "")).strip()
        if block_key:
            runtime_results["psrr_by_block"][block_key] = report

    return runtime_results


def _normalize_lookup(value: str) -> str:
    return "".join(character for character in value.lower() if character.isalnum())


def _block_candidates(block: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    for key in ("block_key", "name"):
        value = block.get(key)
        if isinstance(value, str) and value.strip():
            candidates.append(value.strip())

    aliases = block.get("aliases", [])
    if isinstance(aliases, list):
        for alias in aliases:
            if isinstance(alias, str) and alias.strip():
                candidates.append(alias.strip())

    block_key = block.get("block_key", "")
    if isinstance(block_key, str) and block_key.endswith("_ref"):
        candidates.append(block_key[:-4])

    name = block.get("name", "")
    if isinstance(name, str) and name.lower().endswith(" reference"):
        candidates.append(name[: -len(" reference")])

    return candidates


def find_design_block(reference: dict[str, Any], block_key: str) -> Optional[dict[str, Any]]:
    """Return one block entry by key or display name."""
    query = (block_key or "").strip().lower()
    normalized_query = _normalize_lookup(query)
    fallback_matches: list[dict[str, Any]] = []
    for block in reference.get("blocks", []):
        for candidate in _block_candidates(block):
            candidate_lower = candidate.lower()
            candidate_normalized = _normalize_lookup(candidate)
            if candidate_lower == query or candidate_normalized == normalized_query:
                return block
            if normalized_query and (
                candidate_normalized.startswith(normalized_query)
                or normalized_query in candidate_normalized
            ):
                fallback_matches.append(block)
                break

    unique_matches: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for block in fallback_matches:
        key = str(block.get("block_key") or block.get("name") or id(block))
        if key not in seen_keys:
            seen_keys.add(key)
            unique_matches.append(block)
    if len(unique_matches) == 1:
        return unique_matches[0]
    return None


def summarize_design_reference(reference: dict[str, Any]) -> dict[str, Any]:
    """Return a compact summary for CLI/API use."""
    blocks = reference.get("blocks", [])
    block_counts = {"analog": 0, "digital": 0, "mixed": 0}
    for block in blocks:
        domain = (block.get("domain") or "mixed").lower()
        if domain not in block_counts:
            domain = "mixed"
        block_counts[domain] += 1

    return {
        "design": reference.get("design", {}),
        "block_counts": block_counts,
        "script_count": len(reference.get("script_index", [])),
        "flow_steps": len(reference.get("indexed_flow", [])),
        "analysis_steps": len(reference.get("analysis_playbook", [])),
        "corner_matrix": reference.get("corner_closure", {}).get("matrix", {}),
    }


def query_design_reference(
    reference: dict[str, Any],
    block_key: Optional[str] = None,
    section: str = "summary",
) -> Any:
    """Return a selected slice of the design reference."""
    if block_key:
        block = find_design_block(reference, block_key)
        if block is None:
            raise KeyError(f"Unknown block: {block_key}")
        if section == "summary":
            return {
                "block_key": block.get("block_key"),
                "name": block.get("name"),
                "domain": block.get("domain"),
                "role": block.get("role"),
                "architecture": block.get("architecture"),
            }
        return block.get(section)

    if section == "summary":
        return summarize_design_reference(reference)
    return reference.get(section)


def _escape(value: Any) -> str:
    return html.escape(str(value))


def _render_badges(items: list[str]) -> str:
    if not items:
        return ""
    badges = []
    for item in items:
        badges.append(f'<span class="badge">{_escape(item)}</span>')
    return '<div class="badge-row">' + "".join(badges) + "</div>"


def _render_kv_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
    if not rows:
        return '<p class="muted">No data recorded.</p>'

    header_html = "".join(f"<th>{_escape(title)}</th>" for title, _key in columns)
    row_html = []
    for row in rows:
        cells = []
        for _title, key in columns:
            value = row.get(key, "")
            if isinstance(value, list):
                value = ", ".join(str(item) for item in value)
            cells.append(f"<td>{_escape(value)}</td>")
        row_html.append("<tr>" + "".join(cells) + "</tr>")
    return (
        '<div class="table-wrap"><table>'
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{''.join(row_html)}</tbody>"
        "</table></div>"
    )


def _render_bullets(items: list[Any]) -> str:
    if not items:
        return '<p class="muted">No data recorded.</p>'
    rendered = []
    for item in items:
        if isinstance(item, dict):
            title = item.get("title") or item.get("name") or item.get("step") or item.get("block") or "Item"
            details = item.get("description") or item.get("detail") or item.get("purpose") or item.get("value") or ""
            if not details and item.get("command"):
                details = item["command"]
            rendered.append(f"<li><strong>{_escape(title)}</strong><span>{_escape(details)}</span></li>")
        else:
            rendered.append(f"<li><span>{_escape(item)}</span></li>")
    return '<ul class="bullet-list">' + "".join(rendered) + "</ul>"


def _render_formula_cards(formulas: list[dict[str, Any]]) -> str:
    if not formulas:
        return '<p class="muted">No sizing formulas captured.</p>'

    cards = []
    for formula in formulas:
        variables = formula.get("variables", [])
        cards.append(
            '<article class="formula-card">'
            f'<h4>{_escape(formula.get("title", "Formula"))}</h4>'
            f'<pre>{_escape(formula.get("formula", ""))}</pre>'
            f'<p>{_escape(formula.get("explanation", ""))}</p>'
            f'{_render_badges(variables)}'
            '</article>'
        )
    return '<div class="formula-grid">' + "".join(cards) + "</div>"


def _render_analysis_cards(analyses: list[dict[str, Any]]) -> str:
    if not analyses:
        return '<p class="muted">No analysis plan captured.</p>'

    cards = []
    for analysis in analyses:
        cards.append(
            '<article class="analysis-card">'
            f'<div class="eyebrow">{_escape(analysis.get("type", "analysis"))}</div>'
            f'<h4>{_escape(analysis.get("name", "Analysis"))}</h4>'
            f'<p>{_escape(analysis.get("purpose", ""))}</p>'
            f'<div class="code-block">{_escape(analysis.get("command", ""))}</div>'
            f'<p><strong>Pass criteria:</strong> {_escape(analysis.get("pass_criteria", ""))}</p>'
            f'<p><strong>Tweak first:</strong> {_escape(analysis.get("debug_focus", ""))}</p>'
            '</article>'
        )
    return '<div class="analysis-grid">' + "".join(cards) + "</div>"


def _format_timestamp(value: Any) -> str:
    timestamp = _parse_timestamp(value)
    if timestamp is None:
        return str(value or "Not recorded")
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_measurement_value(value: Any, unit: str = "", precision: int = 3) -> str:
    numeric = _as_float(value)
    if numeric is None:
        return str(value)
    suffix = f" {unit}" if unit else ""
    return f"{numeric:.{precision}f}{suffix}"


def _render_status_chip(status: str, tone: Optional[str] = None) -> str:
    normalized = (status or "UNKNOWN").strip().upper()
    css_class = tone
    if css_class is None:
        if normalized in {"PASS", "MET", "MEETS TARGET"}:
            css_class = "status-pass"
        elif normalized in {"FAIL", "NOT MET", "BELOW TARGET"}:
            css_class = "status-fail"
        else:
            css_class = "status-warn"
    return f'<span class="status-chip {css_class}">{_escape(normalized)}</span>'


def _summarize_measurements(measurements: dict[str, Any]) -> str:
    if not measurements:
        return "No measurements recorded"

    if "output_steady_mean" in measurements:
        summary = [f"mean {_format_measurement_value(measurements.get('output_steady_mean'), 'V')}"]
        if "settling_time_ns" in measurements:
            summary.append(f"settle {_format_measurement_value(measurements.get('settling_time_ns'), 'ns', 1)}")
        return ", ".join(summary)

    if "bus_high_v" in measurements and "bus_low_v" in measurements:
        return (
            f"high {_format_measurement_value(measurements.get('bus_high_v'), 'V')}, "
            f"low {_format_measurement_value(measurements.get('bus_low_v'), 'V')}"
        )

    if "output_peak" in measurements and "output_valley" in measurements:
        return (
            f"peak {_format_measurement_value(measurements.get('output_peak'), 'V')}, "
            f"valley {_format_measurement_value(measurements.get('output_valley'), 'V')}"
        )

    snippets: list[str] = []
    for key, value in measurements.items():
        if len(snippets) >= 3:
            break
        snippets.append(f"{key}={value}")
    return ", ".join(snippets) if snippets else "No measurements recorded"


def _extract_psrr_target(block: dict[str, Any]) -> Optional[dict[str, Any]]:
    for spec in block.get("primary_specs", []):
        if "psrr" not in str(spec.get("name", "")).lower():
            continue
        target_text = str(spec.get("target", ""))
        db_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*dB", target_text, re.IGNORECASE)
        freq_match = re.search(r"at\s*([0-9]+(?:\.[0-9]+)?)\s*([kKmM]?)\s*Hz", target_text, re.IGNORECASE)
        if not db_match:
            continue
        target_db = float(db_match.group(1))
        frequency_hz: Optional[float] = None
        if freq_match:
            scale = {"": 1.0, "k": 1_000.0, "m": 1_000_000.0}[freq_match.group(2).lower()]
            frequency_hz = float(freq_match.group(1)) * scale
        return {
            "target_db": target_db,
            "frequency_hz": frequency_hz,
            "target_text": target_text,
        }
    return None


def _parse_psrr_summary(summary: dict[str, Any]) -> dict[float, float]:
    points: dict[float, float] = {}
    for key, value in summary.items():
        match = re.fullmatch(r"psrr_at_([0-9]+(?:k|m)?)_db", key)
        if not match:
            continue
        label = match.group(1).lower()
        scale = 1.0
        if label.endswith("k"):
            scale = 1_000.0
            label = label[:-1]
        elif label.endswith("m"):
            scale = 1_000_000.0
            label = label[:-1]
        try:
            points[float(label) * scale] = float(value)
        except ValueError:
            continue
    return points


def _psrr_report_is_valid(psrr_report: dict[str, Any]) -> bool:
    if "analysis_valid" in psrr_report:
        return bool(psrr_report.get("analysis_valid"))
    if "dc_converged" in psrr_report:
        return bool(psrr_report.get("dc_converged"))
    return True


def _evaluate_psrr_against_spec(block: dict[str, Any], psrr_report: dict[str, Any]) -> Optional[dict[str, Any]]:
    if not _psrr_report_is_valid(psrr_report):
        return None
    target = _extract_psrr_target(block)
    if target is None:
        return None

    summary_map = _parse_psrr_summary(psrr_report.get("psrr_summary", {}))
    if not summary_map:
        return None

    frequency_hz = target.get("frequency_hz")
    if frequency_hz is None:
        return None
    measured_raw = summary_map.get(frequency_hz)
    if measured_raw is None:
        closest_frequency = min(summary_map, key=lambda value: abs(value - frequency_hz))
        measured_raw = summary_map[closest_frequency]
        frequency_hz = closest_frequency

    measured_magnitude = abs(float(measured_raw))
    target_db = float(target["target_db"])
    return {
        "target_db": target_db,
        "frequency_hz": frequency_hz,
        "measured_raw_db": float(measured_raw),
        "measured_magnitude_db": measured_magnitude,
        "meets_target": measured_magnitude >= target_db,
        "target_text": target["target_text"],
    }


def _render_svg_bar_chart(series: list[tuple[str, float]], unit: str) -> str:
    if not series:
        return '<p class="muted">No chart data recorded.</p>'

    width = 720
    height = 280
    left = 56
    right = 20
    top = 18
    bottom = 56
    plot_width = width - left - right
    plot_height = height - top - bottom
    max_value = max(value for _label, value in series) or 1.0
    bar_width = plot_width / max(1, len(series)) * 0.62

    bars: list[str] = []
    labels: list[str] = []
    value_labels: list[str] = []
    for index, (label, value) in enumerate(series):
        center_x = left + (index + 0.5) * (plot_width / max(1, len(series)))
        bar_height = (value / max_value) * plot_height
        y = top + plot_height - bar_height
        x = center_x - bar_width / 2
        bars.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" '
            'rx="10" fill="#d17f2f" opacity="0.88" />'
        )
        labels.append(
            f'<text x="{center_x:.2f}" y="{height - 18}" text-anchor="middle" class="chart-label">{_escape(label)}</text>'
        )
        value_labels.append(
            f'<text x="{center_x:.2f}" y="{max(top + 14, y - 8):.2f}" text-anchor="middle" class="chart-value">'
            f'{_escape(_format_measurement_value(value, unit, 1))}</text>'
        )

    grid_lines: list[str] = []
    for fraction in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = top + plot_height - fraction * plot_height
        value = fraction * max_value
        grid_lines.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{width - right}" y2="{y:.2f}" class="chart-grid-line" />'
        )
        grid_lines.append(
            f'<text x="{left - 10}" y="{y + 4:.2f}" text-anchor="end" class="chart-label">'
            f'{_escape(_format_measurement_value(value, unit, 0))}</text>'
        )

    return (
        '<div class="chart-shell">'
        f'<svg viewBox="0 0 {width} {height}" class="chart-svg" role="img" aria-label="Bar chart">'
        + "".join(grid_lines)
        + "".join(bars)
        + "".join(value_labels)
        + "".join(labels)
        + '</svg></div>'
    )


def _render_svg_line_chart(x_values: list[float], y_values: list[float], y_unit: str) -> str:
    if not x_values or not y_values or len(x_values) != len(y_values):
        return '<p class="muted">No chart data recorded.</p>'

    width = 760
    height = 320
    left = 62
    right = 24
    top = 20
    bottom = 58
    plot_width = width - left - right
    plot_height = height - top - bottom

    safe_x_values = [max(value, 1e-12) for value in x_values]
    log_values = [math.log10(value) for value in safe_x_values]
    min_x = min(log_values)
    max_x = max(log_values)
    min_y = min(y_values)
    max_y = max(y_values)
    if math.isclose(min_x, max_x):
        max_x = min_x + 1.0
    if math.isclose(min_y, max_y):
        max_y = min_y + 1.0

    def scale_x(value: float) -> float:
        return left + ((math.log10(max(value, 1e-12)) - min_x) / (max_x - min_x)) * plot_width

    def scale_y(value: float) -> float:
        return top + ((max_y - value) / (max_y - min_y)) * plot_height

    polyline = " ".join(
        f"{scale_x(x):.2f},{scale_y(y):.2f}" for x, y in zip(safe_x_values, y_values)
    )

    x_ticks = [10.0, 100.0, 1_000.0, 10_000.0, 100_000.0, 1_000_000.0]
    x_labels = {
        10.0: "10 Hz",
        100.0: "100 Hz",
        1_000.0: "1 kHz",
        10_000.0: "10 kHz",
        100_000.0: "100 kHz",
        1_000_000.0: "1 MHz",
    }
    grid_lines: list[str] = []
    for tick in x_ticks:
        if tick < min(safe_x_values) or tick > max(safe_x_values):
            continue
        x = scale_x(tick)
        grid_lines.append(f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{height - bottom}" class="chart-grid-line" />')
        grid_lines.append(
            f'<text x="{x:.2f}" y="{height - 18}" text-anchor="middle" class="chart-label">{x_labels[tick]}</text>'
        )

    for index in range(5):
        fraction = index / 4 if 4 else 0
        y_value = min_y + fraction * (max_y - min_y)
        y = scale_y(y_value)
        grid_lines.append(f'<line x1="{left}" y1="{y:.2f}" x2="{width - right}" y2="{y:.2f}" class="chart-grid-line" />')
        grid_lines.append(
            f'<text x="{left - 10}" y="{y + 4:.2f}" text-anchor="end" class="chart-label">'
            f'{_escape(_format_measurement_value(y_value, y_unit, 0))}</text>'
        )

    return (
        '<div class="chart-shell">'
        f'<svg viewBox="0 0 {width} {height}" class="chart-svg" role="img" aria-label="Line chart">'
        + "".join(grid_lines)
        + f'<polyline points="{polyline}" fill="none" stroke="#8d4f0b" stroke-width="4" stroke-linejoin="round" stroke-linecap="round" />'
        + '</svg></div>'
    )


def _render_validation_overview(reference: dict[str, Any]) -> str:
    runtime_results = reference.get("runtime_results", {})
    latest_regression = runtime_results.get("latest_regression")
    psrr_reports = runtime_results.get("psrr_reports", [])
    regression_history = runtime_results.get("regression_history", [])
    design_meta = reference.get("design", {})
    design_title = str(design_meta.get("title") or design_meta.get("id") or "this design")
    design_id = str(design_meta.get("id") or "design")
    if latest_regression is None and not psrr_reports:
        return ""

    summary = (latest_regression or {}).get("summary", {})
    coverage = (latest_regression or {}).get("coverage", {})
    overview_cards = [
        {"title": "Stored Runs", "value": str(len(regression_history))},
        {"title": "Latest Regression", "value": _format_timestamp((latest_regression or {}).get("generated_at")) if latest_regression else "Not recorded"},
        {"title": "Overall Status", "value": summary.get("overall", "NO DATA") if latest_regression else "NO DATA"},
        {
            "title": "Coverage",
            "value": (
                f"{coverage.get('functional_percent', 0):.1f}% functional / "
                f"{coverage.get('standards_percent', 0):.1f}% standards"
            ) if latest_regression else "No regression coverage recorded",
        },
    ]

    note = (
        f"Only one stored regression run for {design_title} is currently on disk, so this page can show the latest measured snapshot but not a multi-run trend yet. "
        f"Additional regression JSON files matching reports/{design_id}_regression*.json will appear here automatically."
        if len(regression_history) <= 1 else
        f"Multiple stored regression runs for {design_title} were found and are listed below as the captured run history for this design."
    )

    analog_rows: list[str] = []
    if latest_regression:
        for test in latest_regression.get("tests", []):
            if not str(test.get("case_id", "")).startswith("ANA-"):
                continue
            analog_rows.append(
                "<tr>"
                f"<td>{_escape(str(test.get('block', '')))}</td>"
                f"<td>{_render_status_chip(str(test.get('status', 'UNKNOWN')))}</td>"
                f"<td>{_escape(_summarize_measurements(test.get('measurements', {})))}</td>"
                f"<td>{_escape(str(test.get('details', '')))}</td>"
                "</tr>"
            )

    settling_series: list[tuple[str, float]] = []
    if latest_regression:
        for test in latest_regression.get("tests", []):
            settling_time_ns = _as_float(test.get("measurements", {}).get("settling_time_ns"))
            if settling_time_ns is None:
                continue
            settling_series.append((str(test.get("block", "")).replace("_", " "), settling_time_ns))

    run_history_rows: list[str] = []
    for report in regression_history:
        report_summary = report.get("summary", {})
        run_history_rows.append(
            "<tr>"
            f"<td>{_escape(_format_timestamp(report.get('generated_at') or report.get('timestamp')))}</td>"
            f"<td>{_render_status_chip(str(report_summary.get('overall', 'UNKNOWN')))}</td>"
            f"<td>{_escape(str(report_summary.get('passed', 0)))}/{_escape(str(report_summary.get('total', 0)))}</td>"
            f"<td>{_escape(str(report.get('source_path', '')))}</td>"
            "</tr>"
        )

    psrr_panels = "".join(_render_psrr_panel(reference, report) for report in psrr_reports)
    chart_items = [
        '<li><strong>Regression evidence table</strong><span>Shows the measured values and status outcomes from the latest saved regression run.</span></li>'
    ]
    if settling_series:
        chart_items.insert(
            0,
            '<li><strong>Startup settling chart</strong><span>Compares the stored analog startup settling times from the latest saved regression run.</span></li>',
        )
    if psrr_reports:
        chart_items.append(
            '<li><strong>PSRR sweep chart</strong><span>Plots saved LDO PSRR attenuation magnitude against frequency using the stored PSRR JSON artifact.</span></li>'
        )

    settling_panel = ""
    if settling_series:
        settling_panel = (
            '<article class="panel">'
            '<h3>Startup Settling Across Analog Blocks</h3>'
            '<p class="lead">Measured from the latest stored regression run.</p>'
            + _render_svg_bar_chart(settling_series, "ns")
            + '</article>'
        )
    return (
        '<section id="results" class="panel">'
        '<div class="section-heading"><div class="eyebrow">Measured Results</div><h3>Stored Validation Evidence</h3></div>'
        f'<p class="lead">{_escape(note)}</p>'
        '<div class="summary-grid">'
        + "".join(
            '<article class="summary-card"><h3>' + _escape(card["title"]) + '</h3><p>' + _escape(card["value"]) + '</p></article>'
            for card in overview_cards
        )
        + '</div>'
        + '<div class="card-grid">'
        + '<article class="panel">'
        + '<h3>What This Page Is Charting</h3>'
        + '<ul class="bullet-list">'
        + ''.join(chart_items)
        + '</ul>'
        + '</article>'
        + '<article class="panel">'
        + '<h3>Stored Run History</h3>'
        + '<div class="table-wrap"><table><thead><tr><th>Timestamp</th><th>Overall</th><th>Pass Count</th><th>Artifact</th></tr></thead><tbody>'
        + ("".join(run_history_rows) or '<tr><td colspan="4">No regression history recorded.</td></tr>')
        + '</tbody></table></div>'
        + '</article>'
        + '</div>'
        + '<article class="panel">'
        + '<h3>Latest Analog and Mixed-Signal Results</h3>'
        + '<div class="table-wrap"><table><thead><tr><th>Block</th><th>Status</th><th>Measured</th><th>Requirement Check</th></tr></thead><tbody>'
        + ("".join(analog_rows) or '<tr><td colspan="4">No analog measurements recorded.</td></tr>')
        + '</tbody></table></div>'
        + '</article>'
        + settling_panel
        + psrr_panels
        + '</section>'
    )


def _render_psrr_panel(reference: dict[str, Any], psrr_report: dict[str, Any]) -> str:
    context = psrr_report.get("context", {})
    block = find_design_block(reference, str(context.get("block", "")))
    block_name = str((block or {}).get("name") or context.get("block") or "Block")
    summary = psrr_report.get("psrr_summary", {})
    summary_map = _parse_psrr_summary(summary)
    report_valid = _psrr_report_is_valid(psrr_report)
    attenuation_points = [(frequency, abs(value)) for frequency, value in sorted(summary_map.items())]
    chart_html = _render_svg_line_chart(
        list(psrr_report.get("frequency", [])),
        [abs(float(value)) for value in psrr_report.get("psrr_db", [])],
        "dB",
    )
    evaluation = _evaluate_psrr_against_spec(block or {}, psrr_report) if block else None
    evaluation_html = '<p class="muted">No PSRR target could be parsed from the block spec.</p>'
    if not report_valid:
        evaluation_html = (
            '<p>'
            + _render_status_chip("unresolved", "status-warn")
            + ' '
            + _escape(
                "The corrected operating point did not converge, so this PSRR sweep is shown only as debug data and should not be used for signoff."
            )
            + '</p>'
        )
    elif evaluation is not None:
        frequency_hz = float(evaluation["frequency_hz"])
        frequency_label = f"{frequency_hz / 1000:g} kHz" if frequency_hz >= 1000 else f"{frequency_hz:g} Hz"
        evaluation_html = (
            '<p>'
            + _render_status_chip(
                "meets target" if evaluation.get("meets_target") else "below target",
                "status-pass" if evaluation.get("meets_target") else "status-fail",
            )
            + ' '
            + _escape(
                f"At {frequency_label}, attenuation magnitude is {evaluation['measured_magnitude_db']:.2f} dB "
                f"against target {evaluation['target_db']:.2f} dB."
            )
            + '</p>'
        )

    summary_rows = []
    for frequency_hz, value in attenuation_points:
        if frequency_hz >= 1_000_000:
            label = f"{frequency_hz / 1_000_000:g} MHz"
        elif frequency_hz >= 1_000:
            label = f"{frequency_hz / 1_000:g} kHz"
        else:
            label = f"{frequency_hz:g} Hz"
        summary_rows.append(
            "<tr>"
            f"<td>{_escape(label)}</td>"
            f"<td>{_escape(_format_measurement_value(value, 'dB', 2))}</td>"
            "</tr>"
        )

    return (
        '<article class="panel">'
        f'<h3>Saved PSRR Sweep: {_escape(block_name)}</h3>'
        f'<p class="lead">Stored artifact {_escape(str(psrr_report.get("source_path", "")))} at '
        f'{_escape(str(context.get("corner", "TT")))} corner, {_escape(_format_measurement_value(context.get("temperature_c"), "C", 0))}.</p>'
        f'{evaluation_html}'
        f'<p class="chart-note">{_escape("The chart below is rendered as attenuation magnitude using abs(psrr_db), because the current saved JSON stores rejection using negative dB values." if report_valid else "The chart below is raw debug output from a non-converged operating point. Keep it for diagnosis, not signoff.")}</p>'
        f'{chart_html}'
        '<div class="card-grid">'
        '<article class="panel">'
        '<h3>Sampled PSRR Points</h3>'
        '<div class="table-wrap"><table><thead><tr><th>Frequency</th><th>Attenuation Magnitude</th></tr></thead><tbody>'
        + "".join(summary_rows)
        + '</tbody></table></div>'
        '</article>'
        '<article class="panel">'
        '<h3>Raw Saved Convention</h3>'
        f'<p class="muted">Stored output node: {_escape(str(psrr_report.get("psrr_output_node", "")))}</p>'
        f'<p class="muted">Raw saved 1 kHz value: {_escape(_format_measurement_value(summary.get("psrr_at_1k_db"), "dB", 2))}</p>'
        f'<p class="muted">Artifact context: block={_escape(str(context.get("block", "")))}, analysis={_escape(str(context.get("analysis", "")))}</p>'
        '</article>'
        '</div>'
        '</article>'
    )


def _render_block_results_panel(block: dict[str, Any], runtime_results: dict[str, Any]) -> str:
    block_key = str(block.get("block_key", "")).strip()
    latest_result = runtime_results.get("results_by_block", {}).get(block_key)
    psrr_report = runtime_results.get("psrr_by_block", {}).get(block_key)
    if latest_result is None and psrr_report is None:
        return ""

    cards: list[str] = []
    if latest_result is not None:
        cards.append(
            '<article class="panel">'
            '<h3>Latest Stored Validation</h3>'
            f'<p>{_render_status_chip(str(latest_result.get("status", "UNKNOWN")))} '
            f'{_escape(str(latest_result.get("case_id", "")))}</p>'
            f'<p class="muted">{_escape(_summarize_measurements(latest_result.get("measurements", {})))}</p>'
            f'<p class="muted">{_escape(str(latest_result.get("details", "")))}</p>'
            '</article>'
        )

    if psrr_report is not None:
        if not _psrr_report_is_valid(psrr_report):
            status_text = _render_status_chip("unresolved", "status-warn")
            detail = "Corrected PSRR simulation did not converge at the intended operating point, so the saved sweep cannot yet confirm the 1 kHz target."
        else:
            evaluation = _evaluate_psrr_against_spec(block, psrr_report)
            if evaluation is None:
                status_text = _render_status_chip("psrr saved", "status-warn")
                detail = "Saved PSRR sweep found, but the page could not compare it against a parsed block target."
            else:
                status_text = _render_status_chip(
                    "meets target" if evaluation.get("meets_target") else "below target",
                    "status-pass" if evaluation.get("meets_target") else "status-fail",
                )
                frequency_hz = float(evaluation["frequency_hz"])
                frequency_label = f"{frequency_hz / 1000:g} kHz" if frequency_hz >= 1000 else f"{frequency_hz:g} Hz"
                detail = (
                    f"Saved PSRR attenuation magnitude at {frequency_label} is "
                    f"{evaluation['measured_magnitude_db']:.2f} dB against target {evaluation['target_db']:.2f} dB."
                )
        cards.append(
            '<article class="panel">'
            '<h3>Saved PSRR Status</h3>'
            f'<p>{status_text}</p>'
            f'<p class="muted">{_escape(detail)}</p>'
            f'<p class="muted">Artifact: {_escape(str(psrr_report.get("source_path", "")))}</p>'
            '</article>'
        )

    return '<div class="card-grid">' + "".join(cards) + '</div>'


def _render_block_section(block: dict[str, Any], runtime_results: Optional[dict[str, Any]] = None) -> str:
    block_id = _escape(block.get("block_key", "block"))
    specs_table = _render_kv_table(
        block.get("primary_specs", []),
        [("Spec", "name"), ("Target", "target"), ("Reason", "reason")],
    )
    dc_table = _render_kv_table(
        block.get("dc_operating_points", []),
        [("Node or Signal", "node"), ("Target", "target"), ("How Set", "how_set"), ("Why", "why")],
    )
    files_table = _render_kv_table(
        block.get("files", []),
        [("Path", "path"), ("Role", "role")],
    )
    corner_table = _render_kv_table(
        block.get("corner_focus", []),
        [("Condition", "condition"), ("Risk", "risk"), ("Primary Knob", "primary_knob")],
    )
    results_panel = _render_block_results_panel(block, runtime_results or {})

    return (
        f'<section id="{block_id}" class="block-section">'
        f'<div class="section-heading"><div class="eyebrow">{_escape(block.get("domain", "mixed"))}</div>'
        f'<h2>{_escape(block.get("name", block.get("block_key", "Block")))}</h2></div>'
        f'<p class="lead">{_escape(block.get("role", ""))}</p>'
        f'{results_panel}'
        '<div class="card-grid">'
        '<article class="panel">'
        '<h3>Architecture</h3>'
        f'<p>{_escape(block.get("architecture", ""))}</p>'
        f'{_render_bullets(block.get("implementation_steps", []))}'
        '</article>'
        '<article class="panel">'
        '<h3>Primary Specs</h3>'
        f'{specs_table}'
        '</article>'
        '</div>'
        '<article class="panel">'
        '<h3>Sizing Formulas</h3>'
        f'{_render_formula_cards(block.get("sizing_formulas", []))}'
        '</article>'
        '<article class="panel">'
        '<h3>DC Operating Points</h3>'
        f'{dc_table}'
        '</article>'
        '<article class="panel">'
        '<h3>Analysis Plan</h3>'
        f'{_render_analysis_cards(block.get("analysis_steps", []))}'
        '</article>'
        '<div class="card-grid">'
        '<article class="panel">'
        '<h3>Corner Focus</h3>'
        f'{corner_table}'
        '</article>'
        '<article class="panel">'
        '<h3>Tuning Knobs</h3>'
        f'{_render_bullets(block.get("tuning_knobs", []))}'
        '</article>'
        '</div>'
        '<article class="panel">'
        '<h3>Referenced Files</h3>'
        f'{files_table}'
        '</article>'
        '</section>'
    )


def render_design_reference_html(reference: dict[str, Any]) -> str:
    """Render a full standalone HTML design-reference page."""
    design = reference.get("design", {})
    architecture = reference.get("architecture", {})
    flow_steps = reference.get("indexed_flow", [])
    analysis_playbook = reference.get("analysis_playbook", [])
    script_index = reference.get("script_index", [])
    corner = reference.get("corner_closure", {})
    blocks = reference.get("blocks", [])
    debug_playbook = reference.get("debug_playbook", [])
    reuse = reference.get("future_design_reuse", [])
    chip_profile = reference.get("chip_profile", {})
    reusable_ips = reference.get("reusable_ips", [])
    verification_ips = reference.get("verification_ips", [])
    digital_subsystems = reference.get("digital_subsystems", [])
    runtime_results = reference.get("runtime_results", {})
    has_chip_assembly = bool(chip_profile or reusable_ips or verification_ips or digital_subsystems)
    has_validation_results = bool(
      runtime_results.get("latest_regression") or runtime_results.get("psrr_reports")
    )

    nav_items = [
        '<a href="#overview">Overview</a>',
                '<a href="#assembly">Chip Assembly</a>' if has_chip_assembly else '',
      '<a href="#results">Measured Results</a>' if has_validation_results else '',
        '<a href="#flow">Indexed Flow</a>',
        '<a href="#analysis">Analysis Playbook</a>',
        '<a href="#corners">Corner Closure</a>',
        '<a href="#scripts">Script Index</a>',
    ]
    for block in blocks:
        nav_items.append(
            f'<a href="#{_escape(block.get("block_key", "block"))}">{_escape(block.get("name", "Block"))}</a>'
        )

    overview_cards = [
        {"title": "Standard", "value": design.get("standard", "")},
        {"title": "Technology", "value": design.get("technology", "")},
        {"title": "Primary Rails", "value": architecture.get("power_tree_summary", "")},
        {"title": "Signoff Boundary", "value": design.get("signoff_boundary", "")},
    ]

    flow_cards = []
    for step in flow_steps:
        flow_cards.append(
            '<article class="step-card">'
            f'<div class="step-index">{_escape(step.get("index", "--"))}</div>'
            f'<h4>{_escape(step.get("title", "Step"))}</h4>'
            f'<p>{_escape(step.get("description", ""))}</p>'
            f'{_render_badges(step.get("outputs", []))}'
            '</article>'
        )

    script_rows = []
    for script in script_index:
        script_rows.append({
            "name": script.get("name"),
            "purpose": script.get("purpose"),
            "command": script.get("command"),
        })

    reusable_ip_rows = []
    for entry in reusable_ips:
        reusable_ip_rows.append(
            {
                "name": entry.get("name", entry.get("key", "")),
                "domain": entry.get("domain", ""),
                "category": entry.get("category", ""),
                "technology_support": entry.get("technology_support", []),
            }
        )

    verification_ip_rows = []
    for entry in verification_ips:
        verification_ip_rows.append(
            {
                "name": entry.get("name", entry.get("key", "")),
                "protocol": entry.get("protocol", ""),
                "checks": entry.get("checks", []),
                "command": entry.get("command", ""),
            }
        )

    digital_subsystem_rows = []
    for entry in digital_subsystems:
        digital_subsystem_rows.append(
            {
                "name": entry.get("name", entry.get("key", "")),
                "blocks": entry.get("blocks", []),
                "description": entry.get("description", ""),
            }
        )

    validation_section = _render_validation_overview(reference)

    return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{_escape(design.get('title', 'Design Reference'))}</title>
  <style>
    :root {{
      --bg: #f2ede3;
      --panel: rgba(11, 28, 41, 0.92);
      --panel-soft: rgba(255, 248, 236, 0.88);
      --ink: #0b1c29;
      --ink-soft: #51606a;
      --accent: #d17f2f;
      --accent-deep: #8d4f0b;
      --mint: #7ab7a5;
      --line: rgba(11, 28, 41, 0.14);
      --shadow: 0 18px 50px rgba(11, 28, 41, 0.16);
      --radius: 24px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Trebuchet MS", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(209, 127, 47, 0.18), transparent 28%),
        radial-gradient(circle at top right, rgba(122, 183, 165, 0.20), transparent 24%),
        linear-gradient(180deg, #fbf7ef 0%, #efe6d7 55%, #f7f3ec 100%);
      min-height: 100vh;
    }}
    a {{ color: inherit; text-decoration: none; }}
    .shell {{
      display: grid;
      grid-template-columns: 300px minmax(0, 1fr);
      gap: 28px;
      padding: 28px;
    }}
    .sidebar {{
      position: sticky;
      top: 24px;
      height: calc(100vh - 48px);
      overflow: auto;
      padding: 22px;
      border-radius: var(--radius);
      background: var(--panel);
      color: #eef6f2;
      box-shadow: var(--shadow);
    }}
    .sidebar h1 {{
      margin: 0 0 8px;
      font-family: Georgia, Cambria, serif;
      font-size: 2rem;
      line-height: 1.05;
    }}
    .sidebar p {{ color: rgba(238, 246, 242, 0.76); line-height: 1.5; }}
    .nav-group {{ display: grid; gap: 10px; margin-top: 22px; }}
    .nav-group a {{
      padding: 10px 12px;
      border-radius: 14px;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.08);
      transition: background 120ms ease, transform 120ms ease;
    }}
    .nav-group a:hover {{ background: rgba(255, 255, 255, 0.12); transform: translateX(3px); }}
    main {{ display: grid; gap: 24px; }}
    .hero {{
      padding: 34px;
      border-radius: 32px;
      background: linear-gradient(135deg, rgba(11, 28, 41, 0.95), rgba(17, 54, 58, 0.92));
      color: #f8f4eb;
      box-shadow: var(--shadow);
      overflow: hidden;
      position: relative;
    }}
    .hero::after {{
      content: "";
      position: absolute;
      inset: auto -40px -50px auto;
      width: 220px;
      height: 220px;
      border-radius: 50%;
      background: rgba(209, 127, 47, 0.20);
      filter: blur(12px);
    }}
    .hero .eyebrow, .eyebrow {{
      letter-spacing: 0.16em;
      text-transform: uppercase;
      font-size: 0.72rem;
      color: var(--accent);
      margin-bottom: 8px;
    }}
    .hero h2 {{
      margin: 0 0 14px;
      font-family: Georgia, Cambria, serif;
      font-size: clamp(2.3rem, 4vw, 3.9rem);
      line-height: 0.97;
      max-width: 12ch;
    }}
    .hero p {{
      max-width: 72ch;
      line-height: 1.65;
      color: rgba(248, 244, 235, 0.88);
    }}
    .summary-grid, .card-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 18px;
    }}
    .summary-card, .panel, .step-card {{
      border-radius: 22px;
      background: var(--panel-soft);
      border: 1px solid rgba(11, 28, 41, 0.08);
      box-shadow: var(--shadow);
    }}
    .summary-card {{ padding: 20px; }}
    .summary-card h3 {{ margin: 0 0 8px; font-size: 0.9rem; text-transform: uppercase; color: var(--ink-soft); letter-spacing: 0.08em; }}
    .summary-card p {{ margin: 0; font-size: 1.08rem; line-height: 1.45; }}
    .panel {{ padding: 24px; }}
    .panel h3 {{ margin-top: 0; font-family: Georgia, Cambria, serif; font-size: 1.5rem; }}
    .lead {{ font-size: 1.08rem; color: var(--ink-soft); margin-top: 0; }}
    .badge-row {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }}
    .badge {{
      display: inline-flex;
      align-items: center;
      padding: 6px 10px;
      border-radius: 999px;
      background: rgba(122, 183, 165, 0.16);
      color: #12363f;
      font-size: 0.82rem;
      border: 1px solid rgba(122, 183, 165, 0.22);
    }}
    .step-card {{ padding: 20px; position: relative; overflow: hidden; }}
    .step-index {{
      width: 42px;
      height: 42px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      background: linear-gradient(135deg, var(--accent), #f0b068);
      color: #20150b;
      font-weight: 700;
      margin-bottom: 12px;
    }}
    .step-card h4 {{ margin: 0 0 8px; font-size: 1.15rem; }}
    .step-card p {{ margin: 0; color: var(--ink-soft); line-height: 1.55; }}
    .block-section {{ display: grid; gap: 18px; }}
    .section-heading h2 {{ margin: 0; font-family: Georgia, Cambria, serif; font-size: 2rem; }}
    .formula-grid, .analysis-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; }}
    .formula-card, .analysis-card {{
      padding: 18px;
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.72);
      border: 1px solid rgba(11, 28, 41, 0.08);
    }}
    .formula-card h4, .analysis-card h4 {{ margin: 0 0 10px; }}
    pre, .code-block {{
      margin: 0;
      padding: 14px;
      border-radius: 16px;
      background: #12212d;
      color: #edf4ef;
      overflow: auto;
      font-family: Consolas, "Courier New", monospace;
      font-size: 0.9rem;
      line-height: 1.55;
      white-space: pre-wrap;
    }}
    .table-wrap {{ overflow: auto; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.95rem; }}
    th, td {{ padding: 12px 10px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
    th {{ font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.07em; color: var(--ink-soft); }}
    .bullet-list {{ margin: 0; padding-left: 20px; display: grid; gap: 8px; }}
    .bullet-list li {{ line-height: 1.55; }}
    .bullet-list span {{ display: block; color: var(--ink-soft); }}
    .muted {{ color: var(--ink-soft); }}
    .footer-note {{ font-size: 0.9rem; color: var(--ink-soft); line-height: 1.65; }}
    .status-chip {{
      display: inline-flex;
      align-items: center;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 0.78rem;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      font-weight: 700;
    }}
    .status-pass {{ background: rgba(48, 128, 79, 0.16); color: #25633e; }}
    .status-fail {{ background: rgba(176, 0, 32, 0.14); color: #92112d; }}
    .status-warn {{ background: rgba(209, 127, 47, 0.16); color: #8d4f0b; }}
    .chart-shell {{
      padding: 12px;
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.64);
      border: 1px solid rgba(11, 28, 41, 0.08);
      overflow: auto;
    }}
    .chart-svg {{ width: 100%; height: auto; display: block; }}
    .chart-grid-line {{ stroke: rgba(11, 28, 41, 0.12); stroke-width: 1; }}
    .chart-label {{ fill: #51606a; font-size: 12px; font-family: "Segoe UI", sans-serif; }}
    .chart-value {{ fill: #0b1c29; font-size: 12px; font-weight: 700; font-family: "Segoe UI", sans-serif; }}
    .chart-note {{ color: var(--ink-soft); font-size: 0.92rem; line-height: 1.55; }}
    @media (max-width: 1040px) {{
      .shell {{ grid-template-columns: 1fr; }}
      .sidebar {{ position: static; height: auto; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <aside class="sidebar">
      <div class="eyebrow">Indexed Design Reference</div>
      <h1>{_escape(design.get('title', 'Design Reference'))}</h1>
      <p>{_escape(design.get('summary', ''))}</p>
      <div class="nav-group">{''.join(item for item in nav_items if item)}</div>
    </aside>
    <main>
      <section class="hero" id="overview">
        <div class="eyebrow">{_escape(design.get('standard', ''))}</div>
        <h2>{_escape(design.get('headline', design.get('title', 'Design Reference')))}</h2>
        <p>{_escape(design.get('narrative', ''))}</p>
        {_render_badges(design.get('tags', []))}
      </section>

      <section class="summary-grid">
        {''.join('<article class="summary-card"><h3>' + _escape(card['title']) + '</h3><p>' + _escape(card['value']) + '</p></article>' for card in overview_cards)}
      </section>

            {f'''
            <section class="panel" id="assembly">
                <div class="section-heading"><div class="eyebrow">Assembly</div><h3>Reusable IP, VIP, and Digital Subsystem Inventory</h3></div>
                <div class="card-grid">
                    <article class="panel">
                        <h3>Chip Profile</h3>
                        <p>{_escape(chip_profile.get('name', chip_profile.get('key', 'Custom chip assembly')))}</p>
                        <p class="lead">{_escape(chip_profile.get('summary', 'This design is assembled from reusable chip-library building blocks.'))}</p>
                        {_render_badges(chip_profile.get('technology_support', []))}
                    </article>
                    <article class="panel">
                        <h3>Integrated Digital Subsystems</h3>
                        {_render_kv_table(digital_subsystem_rows, [('Subsystem', 'name'), ('Blocks', 'blocks'), ('Role', 'description')])}
                    </article>
                </div>
                <div class="card-grid">
                    <article class="panel">
                        <h3>Reusable IP Inventory</h3>
                        {_render_kv_table(reusable_ip_rows, [('IP', 'name'), ('Domain', 'domain'), ('Category', 'category'), ('Technology Support', 'technology_support')])}
                    </article>
                    <article class="panel">
                        <h3>Verification IP Inventory</h3>
                        {_render_kv_table(verification_ip_rows, [('VIP', 'name'), ('Protocol', 'protocol'), ('Checks', 'checks'), ('Command', 'command')])}
                    </article>
                </div>
            </section>
            ''' if has_chip_assembly else ''}

      {validation_section}

      <section class="panel">
        <div class="section-heading"><div class="eyebrow">Architecture</div><h3>Power Tree and Control Partition</h3></div>
        <p class="lead">{_escape(architecture.get('summary', ''))}</p>
        {_render_kv_table(architecture.get('domains', []), [('Domain', 'name'), ('Voltage', 'voltage'), ('Source', 'source'), ('Drives', 'drives')])}
        <div class="card-grid">
          <article class="panel"><h3>Bring-Up Order</h3>{_render_bullets(architecture.get('power_sequence', []))}</article>
          <article class="panel"><h3>Control Path</h3>{_render_bullets(architecture.get('control_path', []))}</article>
        </div>
      </section>

      <section id="flow" class="panel">
        <div class="section-heading"><div class="eyebrow">Flow</div><h3>Indexed Design Flow</h3></div>
        <p class="lead">{_escape(reference.get('flow_summary', ''))}</p>
        <div class="card-grid">{''.join(flow_cards)}</div>
      </section>

      <section id="analysis" class="panel">
        <div class="section-heading"><div class="eyebrow">Verification</div><h3>DC, AC, PSRR, and Debug Structure</h3></div>
        <p class="lead">{_escape(reference.get('analysis_summary', ''))}</p>
        {_render_analysis_cards(analysis_playbook)}
      </section>

      <section id="corners" class="panel">
        <div class="section-heading"><div class="eyebrow">Corners</div><h3>Corner Closure Strategy</h3></div>
        <p class="lead">{_escape(corner.get('summary', ''))}</p>
        <div class="card-grid">
          <article class="panel">
            <h3>Matrix</h3>
            {_render_kv_table([corner.get('matrix', {})], [('Process', 'process'), ('Voltage', 'voltage'), ('Temperature', 'temperature_c')])}
          </article>
          <article class="panel">
            <h3>Closure Order</h3>
            {_render_bullets(corner.get('closure_order', []))}
          </article>
        </div>
        <div class="card-grid">
          <article class="panel"><h3>Pass Rule</h3><p>{_escape(corner.get('pass_rule', ''))}</p></article>
          <article class="panel"><h3>Model Note</h3><p>{_escape(corner.get('model_note', ''))}</p></article>
        </div>
      </section>

      <section id="scripts" class="panel">
        <div class="section-heading"><div class="eyebrow">Automation</div><h3>Script Index</h3></div>
        <p class="lead">{_escape(reference.get('script_summary', ''))}</p>
        {_render_kv_table(script_rows, [('Script', 'name'), ('Purpose', 'purpose'), ('Command', 'command')])}
      </section>

      {''.join(_render_block_section(block, runtime_results) for block in blocks)}

      <section class="panel">
        <div class="section-heading"><div class="eyebrow">Debug</div><h3>Debug Playbook</h3></div>
        {_render_bullets(debug_playbook)}
      </section>

      <section class="panel">
        <div class="section-heading"><div class="eyebrow">Reuse</div><h3>How to Reuse for the Next Design</h3></div>
        {_render_bullets(reuse)}
        <p class="footer-note">Source manifest: {_escape(reference.get('source_path', ''))}</p>
      </section>
    </main>
  </div>
</body>
</html>
"""