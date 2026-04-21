"""Copilot CLI watchdog with premium-budget gating and auto-backup hooks.

This script is intended to wrap a long-running Copilot CLI or agent command.
It can:
- start and relaunch the command if it exits
- detect output stalls and restart the command
- stop or pause relaunch when premium usage drops below a threshold
- trigger repository backup checks after each cycle or on a timed basis

Premium monitoring note:
There is no stable local/public API in this repository for Copilot premium balance.
This script therefore supports two practical inputs:
1. --premium-file: JSON file with {"remaining_percent": 42}
2. --premium-check-cmd: command that prints a numeric remaining percent

Examples:
    python scripts/copilot_cli_watchdog.py \
        --command "python -m simulator.agents.cli lin-asic --output designs" \
        --continue-on-exit \
        --stall-seconds 300 \
        --premium-file .copilot_usage.json \
        --min-premium-percent 30 \
        --backup-cmd "python scripts/repo_backup_guard.py --push"
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class PremiumStatus:
    remaining_percent: Optional[float]
    source: str
    ok: bool
    detail: str


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def log(message: str) -> None:
    print(f"[{_now()}] {message}", flush=True)


def read_premium_from_file(path: Path) -> PremiumStatus:
    if not path.exists():
        return PremiumStatus(None, str(path), False, "premium file not found")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return PremiumStatus(None, str(path), False, f"invalid JSON: {exc}")

    if "remaining_percent" not in data:
        return PremiumStatus(None, str(path), False, "missing remaining_percent field")

    value = float(data["remaining_percent"])
    return PremiumStatus(value, str(path), True, "ok")


def read_premium_from_command(command: str) -> PremiumStatus:
    try:
        completed = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        return PremiumStatus(None, command, False, detail)

    output = completed.stdout.strip().splitlines()
    if not output:
        return PremiumStatus(None, command, False, "no output from premium check command")

    raw = output[-1].strip().replace("%", "")
    try:
        value = float(raw)
    except ValueError:
        return PremiumStatus(None, command, False, f"could not parse numeric value from: {raw}")

    return PremiumStatus(value, command, True, "ok")


def get_premium_status(args: argparse.Namespace) -> PremiumStatus:
    if args.premium_file:
        return read_premium_from_file(Path(args.premium_file))
    if args.premium_check_cmd:
        return read_premium_from_command(args.premium_check_cmd)
    return PremiumStatus(None, "disabled", True, "premium monitoring disabled")


def run_backup_command(backup_cmd: Optional[str]) -> int:
    if not backup_cmd:
        return 0
    log(f"running backup command: {backup_cmd}")
    completed = subprocess.run(backup_cmd, shell=True)
    return int(completed.returncode)


def launch_process(command: str, cwd: Optional[str]) -> subprocess.Popen[str]:
    return subprocess.Popen(
        command,
        cwd=cwd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )


def monitor_process(process: subprocess.Popen[str], stall_seconds: int) -> tuple[int, float]:
    """Stream output and detect stalls.

    Returns:
        (exit_code, last_output_timestamp)
    """
    last_output = time.time()
    assert process.stdout is not None

    while True:
        line = process.stdout.readline()
        if line:
            last_output = time.time()
            print(line.rstrip())
            continue

        exit_code = process.poll()
        if exit_code is not None:
            return exit_code, last_output

        if stall_seconds > 0 and (time.time() - last_output) > stall_seconds:
            log(f"detected output stall > {stall_seconds}s, terminating process")
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            return -9, last_output

        time.sleep(1.0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Watchdog wrapper for Copilot CLI workflows")
    parser.add_argument("--command", required=True, help="Command to run and supervise")
    parser.add_argument("--cwd", default=None, help="Working directory for the supervised command")
    parser.add_argument("--continue-on-exit", action="store_true",
                        help="Restart the command after it exits while conditions allow")
    parser.add_argument("--restart-delay", type=int, default=10,
                        help="Seconds to wait before restarting")
    parser.add_argument("--max-restarts", type=int, default=0,
                        help="Maximum restart attempts, 0 means unlimited")
    parser.add_argument("--stall-seconds", type=int, default=0,
                        help="Restart if no output is produced for this many seconds")
    parser.add_argument("--premium-file", default=None,
                        help="JSON file containing remaining_percent")
    parser.add_argument("--premium-check-cmd", default=None,
                        help="Command that prints remaining premium percent")
    parser.add_argument("--min-premium-percent", type=float, default=30.0,
                        help="Minimum remaining premium percent required to continue")
    parser.add_argument("--pause-on-low-premium", action="store_true",
                        help="Pause and retry premium checks instead of exiting on low premium")
    parser.add_argument("--premium-check-interval", type=int, default=300,
                        help="Seconds between premium rechecks while paused")
    parser.add_argument("--backup-cmd", default=None,
                        help="Command to run after each process exit/restart cycle")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    restarts = 0

    while True:
        premium = get_premium_status(args)
        if premium.remaining_percent is not None:
            log(f"premium remaining: {premium.remaining_percent:.1f}% via {premium.source}")

        if not premium.ok:
            log(f"premium status unavailable: {premium.detail}")
        elif premium.remaining_percent is not None and premium.remaining_percent < args.min_premium_percent:
            log(
                f"remaining premium {premium.remaining_percent:.1f}% is below threshold "
                f"{args.min_premium_percent:.1f}%"
            )
            backup_code = run_backup_command(args.backup_cmd)
            if backup_code != 0:
                log(f"backup command returned {backup_code}")
            if args.pause_on_low_premium:
                log(f"pausing for {args.premium_check_interval}s before rechecking premium budget")
                time.sleep(args.premium_check_interval)
                continue
            return 2

        log(f"starting supervised command: {args.command}")
        process = launch_process(args.command, args.cwd)
        exit_code, _ = monitor_process(process, args.stall_seconds)
        log(f"supervised command exited with code {exit_code}")

        backup_code = run_backup_command(args.backup_cmd)
        if backup_code != 0:
            log(f"backup command returned {backup_code}")

        if not args.continue_on_exit:
            return int(exit_code)

        restarts += 1
        if args.max_restarts > 0 and restarts > args.max_restarts:
            log(f"max restarts reached: {args.max_restarts}")
            return int(exit_code)

        log(f"restart #{restarts} in {args.restart_delay}s")
        time.sleep(args.restart_delay)


if __name__ == "__main__":
    sys.exit(main())
