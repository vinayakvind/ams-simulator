"""Project status verifier for key deliverables.

Checks the completion state of the major repo tasks:
- agent CLI entrypoint
- LIN ASIC artifacts
- indexed design framework
- analog books catalog scaffold
- backup automation scripts
- git sync state
- optional API smoke test

Usage:
    python scripts/verify_project_status.py
    python scripts/verify_project_status.py --check-api
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"


def check(condition: bool, name: str, detail: str) -> tuple[bool, str, str]:
    return condition, name, detail


def run_git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def check_api() -> tuple[bool, str, str]:
    port = 5102
    process = subprocess.Popen(
        [sys.executable, "-c", (
            "from simulator.api.server import start_api_server; "
            "import time; "
            f"server=start_api_server(main_window=None, port={port}); "
            "time.sleep(3); "
            "server.shutdown()"
        )],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        time.sleep(1.0)
        response = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=5)
        payload = json.loads(response.read().decode("utf-8"))
        ok = response.status == 200 and payload.get("status") == "running"
        return check(ok, "api.status", f"HTTP {response.status}, status={payload.get('status')}")
    except Exception as exc:
        return check(False, "api.status", str(exc))
    finally:
        try:
            process.terminate()
            process.wait(timeout=5)
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify major project deliverables")
    parser.add_argument("--check-api", action="store_true", help="Run headless API smoke test")
    args = parser.parse_args()

    checks: list[tuple[bool, str, str]] = []

    pyproject_text = PYPROJECT.read_text(encoding="utf-8")
    checks.append(check(
        'ams-agent = "simulator.agents.cli:main"' in pyproject_text,
        "agent.cli.entrypoint",
        "ams-agent entrypoint present in pyproject.toml",
    ))

    checks.append(check((ROOT / "simulator" / "agents" / "cli.py").exists(),
                        "agent.cli.module", "simulator.agents.cli exists"))
    checks.append(check((ROOT / "designs" / "lin_asic" / "lin_asic_top.spice").exists(),
                        "lin.top.netlist", "LIN ASIC top netlist exists"))
    checks.append(check((ROOT / "designs" / "lin_asic" / "lin_asic_architecture.json").exists(),
                        "lin.architecture", "LIN ASIC architecture file exists"))
    checks.append(check((ROOT / "designs" / "lin_asic" / "design_index.json").exists(),
                        "lin.index", "LIN ASIC design index exists"))
    checks.append(check((ROOT / "analog_books_repo" / "catalog" / "analog_books_index.json").exists(),
                        "analog.books.catalog", "analog books catalog exists"))
    checks.append(check((ROOT / "scripts" / "copilot_cli_watchdog.py").exists(),
                        "automation.watchdog", "Copilot CLI watchdog exists"))
    checks.append(check((ROOT / "scripts" / "repo_backup_guard.py").exists(),
                        "automation.backup.guard", "repo backup guard exists"))

    git_status = run_git("status", "--short", "--branch")
    synced = "## master...origin/master" in git_status.stdout
    checks.append(check(synced, "git.sync", git_status.stdout.strip().splitlines()[0] if git_status.stdout.strip() else "unknown"))

    if args.check_api:
        checks.append(check_api())

    passed = 0
    for ok, name, detail in checks:
        mark = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"[{mark}] {name}: {detail}")

    print(f"\nSummary: {passed}/{len(checks)} checks passed")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
