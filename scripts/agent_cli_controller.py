"""Script-driven controller for resumable agent CLI workflows.

This controller is designed to be the initiator for long-running autonomous
work in this repository. It performs a repeatable cycle:

1. Write a handshake snapshot for the repo and optional live API session.
2. Run a queue of repo CLI validation/report commands.
3. Generate structured improvement feedback from the latest reports.
4. Render a prompt file for an external agent CLI.
5. Optionally invoke that external agent command and auto-continue when the
   command exits because of token/context limits.

The controller does not remove external token limits. Instead, it makes the
workflow resumable by persisting state and re-launching the next cycle with the
remaining feedback and queued work.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime
import json
import os
import platform
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_QUEUE_PATH = ROOT / "scripts" / "agent_workflow.json"
DEFAULT_STATE_PATH = ROOT / "reports" / "agent_controller_state.json"
DEFAULT_HANDSHAKE_PATH = ROOT / "reports" / "agent_handshake_latest.json"
DEFAULT_FEEDBACK_PATH = ROOT / "reports" / "agent_feedback_latest.md"
DEFAULT_FEEDBACK_JSON_PATH = ROOT / "reports" / "agent_feedback_latest.json"
DEFAULT_PROMPT_PATH = ROOT / "reports" / "agent_prompt_latest.md"
DEFAULT_AGENT_LOG_PATH = ROOT / "reports" / "agent_cli_output_latest.log"
DEFAULT_STEP_LOG_DIR = ROOT / "reports" / "agent_cycles"
DEFAULT_API_HANDSHAKE_URL = "http://127.0.0.1:5102/api/session/handshake"
CONTROLLER_ACTIVE_ENV = "AMS_AGENT_CONTROLLER_ACTIVE"
DEFAULT_TOKEN_PATTERNS = [
    r"token limit",
    r"context length",
    r"rate limit",
    r"maximum context",
    r"too many tokens",
]

DEFAULT_QUEUE: dict[str, Any] = {
    "name": "daily autonomous chip improvement loop",
    "goal": "Run repo validation, generate feedback, and hand the next improvement batch to the CLI agent.",
    "focus_areas": [
        "Use the latest strict autopilot and chip-catalog reports to decide what to improve next.",
        "Prefer automation, reusable IP coverage, and technology portability over one-off fixes.",
        "Keep the workflow resumable so the next cycle can continue after token or context limits.",
    ],
    "priority_build_targets": {
        "reusable_ips": [
            "high_speed_comparator",
            "differential_amplifier",
            "buffered_precision_dac",
            "lvds_receiver",
            "ethernet_phy",
            "profibus_transceiver",
            "canopen_controller",
            "isolated_gate_driver",
        ],
        "verification_ips": [
            "ethernet_vip",
            "profibus_vip",
            "canopen_vip",
            "clock_gating_vip",
            "precision_dac_vip",
            "high_speed_signal_vip",
        ],
        "digital_subsystems": [
            "clock_gating_plane",
            "ethernet_control_plane",
            "safety_monitor_plane",
            "infotainment_control_plane",
            "power_conversion_plane",
        ],
        "chip_profiles": [
            "automotive_infotainment_soc",
            "industrial_iot_gateway",
            "isolated_power_supply_controller",
            "ethernet_sensor_hub",
            "safe_motor_drive_controller",
        ],
    },
    "steps": [
        {
            "id": "verify-project-status",
            "title": "Verify major project deliverables",
            "command": '"{python}" scripts/verify_project_status.py',
            "continue_on_failure": True,
        },
        {
            "id": "generate-chip-catalog-all",
            "title": "Generate overall chip catalog report",
            "command": '"{python}" designs/framework/scripts/generate_chip_catalog_report.py',
            "continue_on_failure": True,
        },
        {
            "id": "generate-chip-catalog-generic130",
            "title": "Generate generic130 chip catalog report",
            "command": '"{python}" designs/framework/scripts/generate_chip_catalog_report.py --technology generic130',
            "continue_on_failure": True,
        },
        {
            "id": "generate-chip-catalog-generic65",
            "title": "Generate generic65 chip catalog report",
            "command": '"{python}" designs/framework/scripts/generate_chip_catalog_report.py --technology generic65',
            "continue_on_failure": True,
        },
        {
            "id": "generate-chip-catalog-bcd180",
            "title": "Generate bcd180 chip catalog report",
            "command": '"{python}" designs/framework/scripts/generate_chip_catalog_report.py --technology bcd180',
            "continue_on_failure": True,
        },
        {
            "id": "run-strict-autopilot",
            "title": "Run strict indexed design autopilot",
            "command": '"{python}" designs/framework/scripts/run_autopilot.py --strict --quiet',
            "continue_on_failure": True,
        },
        {
            "id": "repo-backup-report",
            "title": "Report current repo change size",
            "command": '"{python}" scripts/repo_backup_guard.py --report',
            "continue_on_failure": True,
        },
    ],
}


def _timestamp() -> str:
    return datetime.now().isoformat()


def _resolve_path(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (repo_root / path).resolve()


def _format_prompt_path(repo_root: Path, value: str | Path) -> str:
    path = Path(value)
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")


def _format_prompt_text(repo_root: Path, text: str) -> str:
    root_with_sep = str(repo_root) + "\\"
    normalized = text.replace(root_with_sep, "").replace(str(repo_root), repo_root.name)
    return normalized.replace("\\", "/")


def _run_git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict):
        return payload
    return None


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_default_queue(path: Path) -> None:
    """Write the default workflow queue to disk."""
    _write_json(path, deepcopy(DEFAULT_QUEUE))


def load_queue(path: Path) -> dict[str, Any]:
    """Load a queue file or fall back to the built-in default queue."""
    payload = _read_json(path)
    if payload is None:
        return deepcopy(DEFAULT_QUEUE)
    payload.setdefault("name", DEFAULT_QUEUE["name"])
    payload.setdefault("goal", DEFAULT_QUEUE["goal"])
    payload.setdefault("focus_areas", list(DEFAULT_QUEUE["focus_areas"]))
    priority_targets = payload.setdefault("priority_build_targets", deepcopy(DEFAULT_QUEUE["priority_build_targets"]))
    for key, values in DEFAULT_QUEUE["priority_build_targets"].items():
        priority_targets.setdefault(key, list(values))
    payload.setdefault("steps", list(DEFAULT_QUEUE["steps"]))
    return payload


def _is_local_api_url(api_url: str) -> bool:
    parsed = urllib.parse.urlparse(api_url)
    return parsed.scheme in {"http", "https"} and parsed.hostname in {"127.0.0.1", "localhost"}


def _is_connection_refused_error(exc: BaseException) -> bool:
    reason = getattr(exc, "reason", exc)
    if isinstance(reason, ConnectionRefusedError):
        return True

    text = str(reason).lower()
    return any(token in text for token in (
        "connection refused",
        "actively refused",
        "winerror 10061",
        "timed out",
        "connection aborted",
    ))


def _run_headless_api_smoke_test() -> tuple[bool, str]:
    try:
        from simulator.api.server import start_api_server
    except Exception as exc:  # pragma: no cover - defensive import failure path
        return False, f"server import failed: {exc}"

    server = None
    try:
        server = start_api_server(main_window=None, port=0)
        port = int(getattr(server, "server_port", server.server_address[1]))
        deadline = time.time() + 3.0
        last_error: Exception | None = None
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=1) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                ok = response.status == 200 and payload.get("status") == "running"
                return ok, f"HTTP {response.status}, status={payload.get('status')}"
            except Exception as exc:  # pragma: no cover - retry loop
                last_error = exc
                time.sleep(0.1)

        detail = str(last_error) if last_error is not None else "timed out waiting for headless API server"
        return False, detail
    finally:
        if server is not None:
            try:
                server.shutdown()
            except Exception:
                pass
            try:
                server.server_close()
            except Exception:
                pass


def build_handshake(repo_root: Path, api_url: str) -> dict[str, Any]:
    """Capture repository and optional live-API handshake metadata."""
    branch = _run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() or "unknown"
    commit = _run_git(repo_root, "rev-parse", "HEAD").stdout.strip() or "unknown"
    status = _run_git(repo_root, "status", "--short", "--branch").stdout.strip().splitlines()
    handshake: dict[str, Any] = {
        "generated_at": _timestamp(),
        "session_id": str(uuid.uuid4()),
        "repo_root": str(repo_root),
        "branch": branch,
        "commit": commit,
        "git_status": status,
        "host": socket.gethostname(),
        "platform": platform.platform(),
        "python_executable": sys.executable,
        "api_handshake_url": api_url,
        "api_handshake": None,
        "api_handshake_ok": False,
        "api_handshake_live": False,
    }

    if not api_url.strip():
        handshake["api_handshake_status"] = "disabled"
        return handshake

    try:
        with urllib.request.urlopen(api_url, timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
        handshake["api_handshake"] = payload
        handshake["api_handshake_ok"] = True
        handshake["api_handshake_live"] = True
        handshake["api_handshake_status"] = "live"
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
        if _is_local_api_url(api_url) and _is_connection_refused_error(exc):
            smoke_ok, smoke_detail = _run_headless_api_smoke_test()
            handshake["api_smoke_test_ok"] = smoke_ok
            handshake["api_smoke_test_detail"] = smoke_detail
            handshake["api_handshake_status"] = "inactive" if smoke_ok else "error"
            if smoke_ok:
                handshake["api_handshake_note"] = "Live API session is not running; headless API smoke test passed."
            else:
                handshake["api_handshake_error"] = str(exc)
        else:
            handshake["api_handshake_status"] = "error"
            handshake["api_handshake_error"] = str(exc)

    return handshake


def _command_log_name(step_id: str, cycle: int) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", step_id).strip("_") or "step"
    return f"cycle_{cycle:04d}_{safe}.log"


def run_command_step(step: dict[str, Any], repo_root: Path, cycle: int, log_dir: Path) -> dict[str, Any]:
    """Run one queued command step and capture its log."""
    log_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    step_id = str(step.get("id", f"step_{cycle}"))
    cwd = _resolve_path(repo_root, step.get("cwd", "."))
    command = str(step.get("command", "")).format(
        python=sys.executable,
        repo_root=str(repo_root),
        cycle=cycle,
    )
    completed = subprocess.run(
        command,
        cwd=cwd,
        shell=True,
        check=False,
        capture_output=True,
        text=True,
    )
    output = (completed.stdout or "")
    if completed.stderr:
        output += ("\n" if output else "") + completed.stderr
    log_path = log_dir / _command_log_name(step_id, cycle)
    log_path.write_text(output, encoding="utf-8", errors="replace")
    return {
        "id": step_id,
        "title": step.get("title", step_id),
        "command": command,
        "cwd": str(cwd),
        "started_at": datetime.fromtimestamp(started).isoformat(),
        "finished_at": _timestamp(),
        "duration_seconds": round(time.time() - started, 3),
        "exit_code": int(completed.returncode),
        "continue_on_failure": bool(step.get("continue_on_failure", False)),
        "log_path": str(log_path),
        "output_tail": output.strip().splitlines()[-10:],
    }


def _detect_patterns(text: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True
    return False


def _load_autopilot_summary(repo_root: Path) -> dict[str, Any] | None:
    return _read_json(repo_root / "reports" / "design_autopilot_latest.json")


def _load_chip_catalog(repo_root: Path, suffix: str = "") -> dict[str, Any] | None:
    return _read_json(repo_root / "reports" / f"chip_catalog{suffix}_latest.json")


def _technology_gap_actions(technology: str, payload: dict[str, Any]) -> list[str]:
    missing_ips = [entry.get("key", "") for entry in payload.get("reusable_ips", []) if not entry.get("compatible", True)]
    missing_profiles = [entry.get("key", "") for entry in payload.get("chip_profiles", []) if not entry.get("compatible", True)]
    actions: list[str] = []
    if missing_profiles:
        actions.append(
            f"Expand {technology} chip-profile support for: {', '.join(missing_profiles[:4])}."
        )
    if missing_ips:
        actions.append(
            f"Expand {technology} reusable IP support for: {', '.join(missing_ips[:6])}."
        )
    return actions


def _priority_target_actions(
    queue: dict[str, Any],
    chip_catalog: dict[str, Any] | None,
    technology_catalogs: dict[str, dict[str, Any]],
) -> tuple[list[str], list[str]]:
    priority_targets = queue.get("priority_build_targets", {}) or {}
    if not priority_targets:
        return [], []

    observations: list[str] = []
    improvements: list[str] = []
    configured_total = 0

    category_specs = (
        (
            "reusable_ips",
            "reusable_ips",
            "reusable IP",
            "Harden reusable IP priority targets with stronger generators, validation coverage, and example integrations",
        ),
        (
            "verification_ips",
            "verification_ips",
            "verification IP",
            "Deepen verification IP priority targets with richer protocol scenarios and mixed-signal regressions",
        ),
        (
            "digital_subsystems",
            "digital_subsystems",
            "digital subsystem",
            "Expand digital subsystem priority targets with reusable control planes, integration rules, and validation coverage",
        ),
        (
            "chip_profiles",
            "chip_profiles",
            "chip profile",
            "Expand chip profile priority targets with assembled top-level references, automation coverage, and design collateral",
        ),
    )

    for queue_key, catalog_key, label, hardening_message in category_specs:
        targets = [str(item).strip() for item in priority_targets.get(queue_key, []) if str(item).strip()]
        if not targets:
            continue

        configured_total += len(targets)
        overall_entries = chip_catalog.get(catalog_key, []) if chip_catalog else []
        overall_keys = {
            str(entry.get("key", "")).strip()
            for entry in overall_entries
            if str(entry.get("key", "")).strip()
        }
        missing_targets = [target for target in targets if target not in overall_keys]
        if missing_targets:
            improvements.append(
                f"Implement missing {label} priority targets: {', '.join(missing_targets[:6])}."
            )
            continue

        technology_gaps: list[str] = []
        for technology, payload in technology_catalogs.items():
            compatible_keys = {
                str(entry.get("key", "")).strip()
                for entry in payload.get(catalog_key, [])
                if str(entry.get("key", "")).strip() and entry.get("compatible", True)
            }
            missing_in_technology = [target for target in targets if target not in compatible_keys]
            if missing_in_technology:
                technology_gaps.append(f"{technology}: {', '.join(missing_in_technology[:4])}")

        if technology_gaps:
            improvements.append(
                f"Close {label} priority-target technology gaps for {'; '.join(technology_gaps)}."
            )
            continue

        improvements.append(f"{hardening_message}: {', '.join(targets[:4])}.")

    if configured_total:
        observations.append(
            f"Priority backlog configured for {configured_total} targeted reusable IP, VIP, digital-subsystem, and chip-profile items."
        )

    return observations, improvements


def collect_feedback(repo_root: Path, validation_results: list[dict[str, Any]], queue: dict[str, Any]) -> dict[str, Any]:
    """Collect improvement feedback from the latest reports and queue results."""
    observations: list[str] = []
    improvements: list[str] = []

    failed_steps = [result for result in validation_results if result.get("exit_code") != 0]
    if failed_steps:
        for step in failed_steps:
            improvements.append(
                f"Fix validation step '{step['id']}' because it exited with code {step['exit_code']}. See {step['log_path']}."
            )
    else:
        observations.append("All queued validation/report commands exited cleanly in the latest cycle.")

    autopilot = _load_autopilot_summary(repo_root)
    if autopilot is None:
        improvements.append("Generate and inspect the strict autopilot summary because reports/design_autopilot_latest.json is missing.")
    else:
        overall = str(autopilot.get("overall", "UNKNOWN"))
        observations.append(f"Strict autopilot overall status: {overall}.")
        if overall != "PASS":
            failing_designs = [
                design.get("id", "unknown")
                for design in autopilot.get("designs", [])
                if design.get("overall") != "PASS"
            ]
            if failing_designs:
                improvements.append(
                    f"Return strict autopilot to PASS by resolving: {', '.join(failing_designs)}."
                )

    chip_catalog = _load_chip_catalog(repo_root)
    if chip_catalog is not None:
        summary = chip_catalog.get("summary", {})
        observations.append(
            "Chip catalog inventory: "
            f"{summary.get('reusable_ip_count', 0)} reusable IPs, "
            f"{summary.get('verification_ip_count', 0)} VIPs, "
            f"{summary.get('digital_subsystem_count', 0)} digital subsystems, "
            f"{summary.get('chip_profile_count', 0)} chip profiles."
        )

    technology_catalogs: dict[str, dict[str, Any]] = {}
    for technology in ("generic130", "generic65", "bcd180"):
        payload = _load_chip_catalog(repo_root, suffix=f"_{technology}")
        if payload is None:
            improvements.append(f"Generate the {technology} chip catalog report because it is missing.")
            continue
        technology_catalogs[technology] = payload
        summary = payload.get("summary", {})
        observations.append(
            f"{technology}: {summary.get('compatible_ip_count', 0)}/{summary.get('reusable_ip_count', 0)} reusable IPs and "
            f"{summary.get('compatible_chip_profile_count', 0)}/{summary.get('chip_profile_count', 0)} chip profiles are currently compatible."
        )
        improvements.extend(_technology_gap_actions(technology, payload))

    priority_observations, priority_improvements = _priority_target_actions(
        queue=queue,
        chip_catalog=chip_catalog,
        technology_catalogs=technology_catalogs,
    )
    observations.extend(priority_observations)
    improvements.extend(priority_improvements)

    for focus_area in queue.get("focus_areas", []):
        observations.append(f"Workflow focus: {focus_area}")

    deduped_improvements: list[str] = []
    seen: set[str] = set()
    for item in improvements:
        normalized = item.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduped_improvements.append(normalized)

    if not deduped_improvements:
        deduped_improvements.append(
            "Expand the reusable chip library with additional IPs, VIPs, or technology-specific implementations so future cycles improve capability instead of only revalidating.")

    return {
        "generated_at": _timestamp(),
        "observations": observations,
        "improvements": deduped_improvements,
        "next_actions": deduped_improvements[:5],
        "failed_validation_steps": [step["id"] for step in failed_steps],
    }


def write_feedback_markdown(feedback: dict[str, Any], path: Path) -> None:
    """Persist feedback in Markdown for agent consumption."""
    lines = [
        "# Agent Feedback",
        "",
        f"Generated: {feedback['generated_at']}",
        "",
        "## Observations",
        "",
    ]
    for item in feedback.get("observations", []):
        lines.append(f"- {item}")

    lines.extend(["", "## Improvements", ""])
    for item in feedback.get("improvements", []):
        lines.append(f"- {item}")

    lines.extend(["", "## Next Actions", ""])
    for item in feedback.get("next_actions", []):
        lines.append(f"- {item}")

    if feedback.get("failed_validation_steps"):
        lines.extend(["", "## Failed Validation Steps", ""])
        for step_id in feedback["failed_validation_steps"]:
            lines.append(f"- {step_id}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def render_agent_prompt(
    handshake: dict[str, Any],
    feedback: dict[str, Any],
    queue: dict[str, Any],
    validation_results: list[dict[str, Any]],
    state: dict[str, Any],
    prompt_path: Path,
    feedback_path: Path,
    state_path: Path,
    handshake_path: Path,
) -> str:
    """Render the script-generated prompt that can be fed into an external agent CLI."""
    repo_root = Path(handshake.get("repo_root", ROOT))
    priority_targets = queue.get("priority_build_targets", {})
    lines = [
        "# Autonomous Agent Prompt",
        "",
        f"Cycle: {state.get('cycle_count', 0)}",
        f"Generated: {feedback.get('generated_at', _timestamp())}",
        f"Workspace: {repo_root.name}",
        f"Branch: {handshake.get('branch', '')}",
        f"Commit: {handshake.get('commit', '')}",
        "",
        "## Controller Handshake Files",
        "",
        f"- Handshake JSON: {_format_prompt_path(repo_root, handshake_path)}",
        f"- Feedback Markdown: {_format_prompt_path(repo_root, feedback_path)}",
        f"- Controller State JSON: {_format_prompt_path(repo_root, state_path)}",
        f"- Current Prompt File: {_format_prompt_path(repo_root, prompt_path)}",
        "",
        "## Goal",
        "",
        str(queue.get("goal", "Continue the autonomous AMS chip improvement workflow.")),
        "",
        "## Validation Commands Already Run This Cycle",
        "",
    ]
    for result in validation_results:
        log_path = result.get("log_path")
        log_suffix = f" (log: {_format_prompt_path(repo_root, log_path)})" if log_path else ""
        lines.append(
            f"- {'PASS' if result.get('exit_code') == 0 else 'FAIL'} {result.get('id')}{log_suffix}"
        )

    if priority_targets:
        lines.extend(["", "## Priority Build Targets", ""])
        reusable_ips = priority_targets.get("reusable_ips", [])
        verification_ips = priority_targets.get("verification_ips", [])
        digital_subsystems = priority_targets.get("digital_subsystems", [])
        chip_profiles = priority_targets.get("chip_profiles", [])
        if reusable_ips:
            lines.append(f"- Reusable IP backlog: {', '.join(str(item) for item in reusable_ips)}")
        if verification_ips:
            lines.append(f"- Verification IP backlog: {', '.join(str(item) for item in verification_ips)}")
        if digital_subsystems:
            lines.append(f"- Digital subsystem backlog: {', '.join(str(item) for item in digital_subsystems)}")
        if chip_profiles:
            lines.append(f"- Chip profile backlog: {', '.join(str(item) for item in chip_profiles)}")
        lines.append("- Prefer implementing or closing these catalog items before unrelated polish work.")

    lines.extend(["", "## Observations", ""])
    for item in feedback.get("observations", []):
        lines.append(f"- {_format_prompt_text(repo_root, item)}")

    lines.extend(["", "## Next Improvements To Implement", ""])
    for item in feedback.get("next_actions", []):
        lines.append(f"- {_format_prompt_text(repo_root, item)}")

    lines.extend([
        "",
        "## Agent Instructions",
        "",
        "- Treat the script as the initiator. Continue from the latest handshake, feedback, and repo state instead of asking for a fresh prompt.",
        "- Prioritize concrete repo changes that improve automation, chip assembly coverage, technology portability, or validation completeness.",
        "- After making changes, rerun only the necessary repo commands or let the controller launch the next cycle.",
        "- Do not invoke scripts/agent_cli_controller.py, scripts/start_agent_cli_daemon.ps1, or scripts/open_agent_cli_window.ps1 from inside the external agent run; the controller already owns cycle orchestration.",
        "- If you hit a token, context, or rate limit, stop cleanly after writing any useful partial progress. The controller will generate the next cycle prompt and continue.",
        "- Use the current repo state as the source of truth. Do not assume a previous cycle fully completed unless the reports show it.",
    ])
    return "\n".join(lines).rstrip() + "\n"


def run_agent_command(
    command_template: str,
    prompt_path: Path,
    state_path: Path,
    feedback_path: Path,
    handshake_path: Path,
    queue_path: Path,
    repo_root: Path,
    cycle_count: int,
    log_path: Path,
    token_patterns: list[str],
) -> dict[str, Any]:
    """Invoke an external agent CLI command using the script-generated prompt file."""
    command = command_template.format(
        prompt_file=str(prompt_path),
        state_file=str(state_path),
        feedback_file=str(feedback_path),
        handshake_file=str(handshake_path),
        queue_file=str(queue_path),
        repo_root=str(repo_root),
        cycle=cycle_count,
    )
    completed = subprocess.run(
        command,
        cwd=repo_root,
        shell=True,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output = (completed.stdout or "")
    if completed.stderr:
        output += ("\n" if output else "") + completed.stderr
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(output, encoding="utf-8", errors="replace")
    return {
        "command": command,
        "exit_code": int(completed.returncode),
        "token_limit_detected": _detect_patterns(output, token_patterns),
        "log_path": str(log_path),
        "output_tail": output.strip().splitlines()[-20:],
    }


def initialize_state(queue_path: Path) -> dict[str, Any]:
    """Create a fresh controller state payload."""
    return {
        "created_at": _timestamp(),
        "queue_file": str(queue_path),
        "cycle_count": 0,
        "status": "initialized",
        "validation_history": [],
        "last_feedback_json": None,
        "last_prompt_file": None,
        "last_agent_result": None,
    }


def load_state(path: Path, queue_path: Path) -> dict[str, Any]:
    """Load or initialize controller state."""
    state = _read_json(path)
    if state is None:
        return initialize_state(queue_path)
    state.setdefault("queue_file", str(queue_path))
    state.setdefault("cycle_count", 0)
    state.setdefault("status", "initialized")
    state.setdefault("validation_history", [])
    return state


def run_cycle(args: argparse.Namespace) -> dict[str, Any]:
    """Run one full controller cycle."""
    repo_root = _resolve_path(ROOT, args.repo)
    queue_path = _resolve_path(repo_root, args.queue_file)
    state_path = _resolve_path(repo_root, args.state_file)
    handshake_path = _resolve_path(repo_root, args.handshake_file)
    feedback_path = _resolve_path(repo_root, args.feedback_file)
    feedback_json_path = _resolve_path(repo_root, args.feedback_json_file)
    prompt_path = _resolve_path(repo_root, args.prompt_file)
    agent_log_path = _resolve_path(repo_root, args.agent_log_file)
    step_log_dir = _resolve_path(repo_root, args.step_log_dir)

    queue = load_queue(queue_path)
    state = load_state(state_path, queue_path)
    state["cycle_count"] = int(state.get("cycle_count", 0)) + 1
    state["status"] = "running"
    state["last_cycle_started_at"] = _timestamp()

    handshake = build_handshake(repo_root, args.api_handshake_url)
    _write_json(handshake_path, handshake)

    validation_results: list[dict[str, Any]] = []
    for step in queue.get("steps", []):
        result = run_command_step(step, repo_root, state["cycle_count"], step_log_dir)
        validation_results.append(result)
        if result["exit_code"] != 0 and not result["continue_on_failure"]:
            state["status"] = "blocked"
            break

    feedback = collect_feedback(repo_root, validation_results, queue)
    _write_json(feedback_json_path, feedback)
    write_feedback_markdown(feedback, feedback_path)

    prompt_text = render_agent_prompt(
        handshake=handshake,
        feedback=feedback,
        queue=queue,
        validation_results=validation_results,
        state=state,
        prompt_path=prompt_path,
        feedback_path=feedback_path,
        state_path=state_path,
        handshake_path=handshake_path,
    )
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt_text, encoding="utf-8")

    agent_result = None
    if args.agent_command_template:
        agent_result = run_agent_command(
            command_template=args.agent_command_template,
            prompt_path=prompt_path,
            state_path=state_path,
            feedback_path=feedback_path,
            handshake_path=handshake_path,
            queue_path=queue_path,
            repo_root=repo_root,
            cycle_count=state["cycle_count"],
            log_path=agent_log_path,
            token_patterns=args.token_limit_pattern,
        )

    state["last_cycle_finished_at"] = _timestamp()
    state["last_feedback_json"] = str(feedback_json_path)
    state["last_feedback_markdown"] = str(feedback_path)
    state["last_prompt_file"] = str(prompt_path)
    state["last_handshake_file"] = str(handshake_path)
    state["last_validation_results"] = validation_results
    state["last_agent_result"] = agent_result
    state["validation_history"] = (state.get("validation_history", []) + [
        {
            "cycle": state["cycle_count"],
            "started_at": state.get("last_cycle_started_at"),
            "finished_at": state.get("last_cycle_finished_at"),
            "failed_steps": feedback.get("failed_validation_steps", []),
            "next_actions": feedback.get("next_actions", []),
        }
    ])[-20:]

    if state["status"] == "running":
        state["status"] = "waiting_for_next_cycle" if agent_result else "idle"
        if agent_result and agent_result.get("token_limit_detected"):
            state["status"] = "continuation_requested"

    _write_json(state_path, state)

    return {
        "state": state,
        "queue": queue,
        "feedback": feedback,
        "agent_result": agent_result,
        "prompt_path": prompt_path,
        "feedback_path": feedback_path,
        "feedback_json_path": feedback_json_path,
        "handshake_path": handshake_path,
        "state_path": state_path,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse controller CLI arguments."""
    parser = argparse.ArgumentParser(description="Run the script-driven agent CLI controller")
    parser.add_argument("--repo", default=str(ROOT), help="Repository root")
    parser.add_argument("--queue-file", default=str(DEFAULT_QUEUE_PATH), help="JSON workflow queue path")
    parser.add_argument("--write-default-queue", action="store_true", help="Write the built-in default queue and exit")
    parser.add_argument("--state-file", default=str(DEFAULT_STATE_PATH), help="Controller state JSON path")
    parser.add_argument("--handshake-file", default=str(DEFAULT_HANDSHAKE_PATH), help="Handshake JSON path")
    parser.add_argument("--feedback-file", default=str(DEFAULT_FEEDBACK_PATH), help="Feedback Markdown path")
    parser.add_argument("--feedback-json-file", default=str(DEFAULT_FEEDBACK_JSON_PATH), help="Feedback JSON path")
    parser.add_argument("--prompt-file", default=str(DEFAULT_PROMPT_PATH), help="Generated prompt path for the external agent CLI")
    parser.add_argument("--agent-log-file", default=str(DEFAULT_AGENT_LOG_PATH), help="External agent CLI log path")
    parser.add_argument("--step-log-dir", default=str(DEFAULT_STEP_LOG_DIR), help="Directory for queued command logs")
    parser.add_argument("--api-handshake-url", default=DEFAULT_API_HANDSHAKE_URL, help="Optional simulator API handshake endpoint")
    parser.add_argument("--agent-command-template", default=os.environ.get("AMS_AGENT_COMMAND_TEMPLATE"),
                        help="External agent CLI command template. Supported placeholders: {prompt_file}, {state_file}, {feedback_file}, {handshake_file}, {queue_file}, {repo_root}, {cycle}")
    parser.add_argument("--token-limit-pattern", action="append", default=list(DEFAULT_TOKEN_PATTERNS),
                        help="Regex pattern that indicates the external agent hit a token/context/rate limit and should be continued")
    parser.add_argument("--continue-on-agent-exit", action="store_true",
                        help="Continue cycling after the external agent command exits")
    parser.add_argument("--allow-nested-controller", action="store_true",
                        help="Allow this controller process to start even if another controller already marked the environment active")
    parser.add_argument("--watch", action="store_true", help="Run continuously")
    parser.add_argument("--watch-interval-seconds", type=int, default=86400,
                        help="Delay between daily-style controller cycles when no external agent command is configured")
    parser.add_argument("--agent-loop-delay-seconds", type=int, default=60,
                        help="Delay between iterative agent-controlled cycles when an external agent command is configured")
    parser.add_argument("--max-cycles", type=int, default=0,
                        help="Maximum cycles to run in watch mode. 0 means unlimited")
    return parser.parse_args(argv)


def nested_controller_block_reason(args: argparse.Namespace) -> str | None:
    """Return a reason when this invocation should refuse a nested controller launch."""
    if getattr(args, "allow_nested_controller", False):
        return None

    active_marker = os.environ.get(CONTROLLER_ACTIVE_ENV, "").strip()
    if not active_marker:
        return None

    return (
        f"Nested controller launch blocked because {CONTROLLER_ACTIVE_ENV}="
        f"{active_marker}. Pass --allow-nested-controller only for intentional manual recursion."
    )


def main(argv: list[str] | None = None) -> int:
    """Entry point for the script-driven controller."""
    args = parse_args(argv)
    repo_root = _resolve_path(ROOT, args.repo)
    queue_path = _resolve_path(repo_root, args.queue_file)

    if args.write_default_queue:
        write_default_queue(queue_path)
        print(queue_path)
        return 0

    block_reason = nested_controller_block_reason(args)
    if block_reason:
        print(block_reason)
        return 0

    os.environ[CONTROLLER_ACTIVE_ENV] = f"pid:{os.getpid()}"

    cycles_completed = 0
    while True:
        result = run_cycle(args)
        cycles_completed += 1

        if not args.watch:
            return 0

        if args.max_cycles > 0 and cycles_completed >= args.max_cycles:
            return 0

        delay = args.watch_interval_seconds
        agent_result = result.get("agent_result")
        if args.agent_command_template:
            delay = args.agent_loop_delay_seconds
            if agent_result is None and not args.continue_on_agent_exit:
                return 0
            if agent_result is not None and not args.continue_on_agent_exit and not agent_result.get("token_limit_detected"):
                return int(agent_result.get("exit_code", 0))

        time.sleep(max(delay, 1))


if __name__ == "__main__":
    raise SystemExit(main())