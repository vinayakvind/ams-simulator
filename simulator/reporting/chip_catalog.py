"""Reports for reusable chip assembly technologies, IPs, and VIPs."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from simulator.catalog import (
    list_chip_profiles,
    list_digital_subsystems,
    list_reusable_ips,
    list_supported_technologies,
    list_verification_ips,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def build_chip_catalog_payload(technology: str | None = None) -> dict[str, Any]:
    """Build a technology and chip-library readiness payload."""
    technologies = list_supported_technologies()
    reusable_ips = list_reusable_ips(technology=technology)
    profiles = list_chip_profiles(technology=technology)
    digital_subsystems = list_digital_subsystems(technology=technology)
    verification_ips = list_verification_ips()

    compatible_ip_count = sum(1 for entry in reusable_ips if entry.get("compatible", True))
    compatible_profile_count = sum(1 for entry in profiles if entry.get("compatible", True))
    compatible_subsystem_count = sum(1 for entry in digital_subsystems if entry.get("compatible", True))

    return {
        "generated_at": datetime.now().isoformat(),
        "technology_filter": technology,
        "summary": {
            "technology_count": len(technologies),
            "reusable_ip_count": len(reusable_ips),
            "verification_ip_count": len(verification_ips),
            "digital_subsystem_count": len(digital_subsystems),
            "chip_profile_count": len(profiles),
            "compatible_ip_count": compatible_ip_count,
            "compatible_digital_subsystem_count": compatible_subsystem_count,
            "compatible_chip_profile_count": compatible_profile_count,
        },
        "technologies": technologies,
        "reusable_ips": reusable_ips,
        "verification_ips": verification_ips,
        "digital_subsystems": digital_subsystems,
        "chip_profiles": profiles,
    }


def write_chip_catalog_markdown(payload: dict[str, Any], output_path: Path) -> None:
    """Write a Markdown report for the chip catalog payload."""
    summary = payload["summary"]
    lines = [
        "# Chip Assembly Catalog Report",
        "",
        f"Generated: {payload['generated_at']}",
        f"Technology filter: {payload.get('technology_filter') or 'all'}",
        "",
        "## Summary",
        "",
        f"- Technologies: {summary['technology_count']}",
        f"- Reusable IPs: {summary['reusable_ip_count']}",
        f"- Verification IPs: {summary['verification_ip_count']}",
        f"- Digital subsystems: {summary['digital_subsystem_count']}",
        f"- Chip profiles: {summary['chip_profile_count']}",
        f"- Compatible IPs: {summary['compatible_ip_count']}",
        f"- Compatible digital subsystems: {summary['compatible_digital_subsystem_count']}",
        f"- Compatible chip profiles: {summary['compatible_chip_profile_count']}",
        "",
        "## Technologies",
        "",
        "| Name | Node | VDD | Description |",
        "|------|------|-----|-------------|",
    ]
    for technology in payload.get("technologies", []):
        lines.append(
            f"| {technology.get('name', '')} | {technology.get('node', '')} | {technology.get('vdd', '')} | {technology.get('description', '')} |"
        )

    lines.extend([
        "",
        "## Chip Profiles",
        "",
        "| Profile | Compatible | Summary |",
        "|---------|------------|---------|",
    ])
    for profile in payload.get("chip_profiles", []):
        compatible = profile.get("compatible", True)
        lines.append(
            f"| {profile.get('key', '')} | {'yes' if compatible else 'no'} | {profile.get('summary', '')} |"
        )

    lines.extend([
        "",
        "## Reusable IPs",
        "",
        "| IP | Domain | Category | Compatible | Technology Support |",
        "|----|--------|----------|------------|--------------------|",
    ])
    for ip in payload.get("reusable_ips", []):
        lines.append(
            f"| {ip.get('key', '')} | {ip.get('domain', '')} | {ip.get('category', '')} | {'yes' if ip.get('compatible', True) else 'no'} | {', '.join(ip.get('technology_support', []))} |"
        )

    lines.extend([
        "",
        "## Verification IPs",
        "",
        "| VIP | Protocol | Checks |",
        "|-----|----------|--------|",
    ])
    for vip in payload.get("verification_ips", []):
        lines.append(
            f"| {vip.get('key', '')} | {vip.get('protocol', '')} | {', '.join(vip.get('checks', []))} |"
        )

    lines.extend([
        "",
        "## Digital Subsystems",
        "",
        "| Subsystem | Compatible | Blocks |",
        "|-----------|------------|--------|",
    ])
    for subsystem in payload.get("digital_subsystems", []):
        lines.append(
            f"| {subsystem.get('key', '')} | {'yes' if subsystem.get('compatible', True) else 'no'} | {', '.join(subsystem.get('blocks', []))} |"
        )

    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def generate_chip_catalog_report(
    technology: str | None = None,
    json_output: Path | None = None,
    markdown_output: Path | None = None,
) -> dict[str, Any]:
    """Generate JSON and Markdown reports for chip assembly catalog readiness."""
    suffix = f"_{technology}" if technology else ""
    json_path = json_output or (PROJECT_ROOT / "reports" / f"chip_catalog{suffix}_latest.json")
    markdown_path = markdown_output or (PROJECT_ROOT / "reports" / f"chip_catalog{suffix}_latest.md")

    payload = build_chip_catalog_payload(technology=technology)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_chip_catalog_markdown(payload, markdown_path)

    return {
        "json": json_path,
        "markdown": markdown_path,
        "payload": payload,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for chip catalog reporting."""
    parser = argparse.ArgumentParser(description="Generate reusable chip assembly catalog reports")
    parser.add_argument("--technology", help="Optional technology filter such as generic130 or bcd180")
    parser.add_argument("--json", help="Override JSON output path")
    parser.add_argument("--markdown", help="Override Markdown output path")
    args = parser.parse_args(argv)

    report = generate_chip_catalog_report(
        technology=args.technology,
        json_output=Path(args.json) if args.json else None,
        markdown_output=Path(args.markdown) if args.markdown else None,
    )
    print(report["json"])
    return 0


__all__ = [
    "build_chip_catalog_payload",
    "generate_chip_catalog_report",
    "main",
    "write_chip_catalog_markdown",
]