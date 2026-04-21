"""Repository backup guard for major-change detection and push automation.

This script checks whether the current working tree has "major" changes using
simple thresholds and can automatically commit and push those changes.

Major changes are defined by either:
- changed files >= --major-files
- inserted + deleted lines >= --major-lines

Examples:
    python scripts/repo_backup_guard.py --report
    python scripts/repo_backup_guard.py --push
    python scripts/repo_backup_guard.py --watch --interval 600 --push
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class DiffSummary:
    changed_files: int
    insertions: int
    deletions: int

    @property
    def changed_lines(self) -> int:
        return self.insertions + self.deletions


def run_git(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def get_repo_root(start: Path) -> Optional[Path]:
    completed = subprocess.run(
        ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    return Path(completed.stdout.strip())


def parse_diff_stat(text: str) -> DiffSummary:
    changed_files = 0
    insertions = 0
    deletions = 0

    files_match = re.search(r"(\d+) files? changed", text)
    ins_match = re.search(r"(\d+) insertions?\(\+\)", text)
    del_match = re.search(r"(\d+) deletions?\(-\)", text)

    if files_match:
        changed_files = int(files_match.group(1))
    if ins_match:
        insertions = int(ins_match.group(1))
    if del_match:
        deletions = int(del_match.group(1))

    return DiffSummary(changed_files=changed_files, insertions=insertions, deletions=deletions)


def current_diff_summary(repo_root: Path) -> DiffSummary:
    completed = run_git(repo_root, ["diff", "--shortstat", "HEAD"])
    if completed.returncode != 0:
        return DiffSummary(0, 0, 0)

    summary = parse_diff_stat(completed.stdout.strip())

    untracked = run_git(repo_root, ["status", "--short"])
    if untracked.returncode == 0:
        extra = sum(1 for line in untracked.stdout.splitlines() if line.startswith("?? "))
        summary.changed_files += extra

    return summary


def is_major_change(summary: DiffSummary, major_files: int, major_lines: int) -> bool:
    return summary.changed_files >= major_files or summary.changed_lines >= major_lines


def has_any_change(summary: DiffSummary) -> bool:
    return summary.changed_files > 0 or summary.changed_lines > 0


def auto_commit_and_push(repo_root: Path, message: str) -> int:
    add = run_git(repo_root, ["add", "-A"])
    if add.returncode != 0:
        sys.stderr.write(add.stderr)
        return add.returncode

    commit = run_git(repo_root, ["commit", "-m", message])
    if commit.returncode != 0:
        combined = f"{commit.stdout}\n{commit.stderr}".lower()
        if "nothing to commit" in combined:
            return 0
        sys.stderr.write(commit.stderr or commit.stdout)
        return commit.returncode

    push = run_git(repo_root, ["push"])
    if push.returncode != 0:
        sys.stderr.write(push.stderr or push.stdout)
    return push.returncode


def report(summary: DiffSummary, major: bool) -> None:
    print(f"changed_files={summary.changed_files}")
    print(f"insertions={summary.insertions}")
    print(f"deletions={summary.deletions}")
    print(f"changed_lines={summary.changed_lines}")
    print(f"major_change={'yes' if major else 'no'}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Guard and back up repo on major changes")
    parser.add_argument("--repo", default=".", help="Repository root or child path")
    parser.add_argument("--major-files", type=int, default=10,
                        help="Major change threshold by file count")
    parser.add_argument("--major-lines", type=int, default=500,
                        help="Major change threshold by changed lines")
    parser.add_argument("--report", action="store_true", help="Print summary report")
    parser.add_argument("--push", action="store_true",
                        help="Commit and push when a major change is detected")
    parser.add_argument("--force-push-any-change", action="store_true",
                        help="Commit and push any change, not only major changes")
    parser.add_argument("--watch", action="store_true",
                        help="Run continuously and recheck on an interval")
    parser.add_argument("--interval", type=int, default=600,
                        help="Recheck interval in seconds for --watch")
    parser.add_argument("--message", default=None,
                        help="Commit message override")
    return parser.parse_args()


def run_once(args: argparse.Namespace) -> int:
    repo_root = get_repo_root(Path(args.repo).resolve())
    if repo_root is None:
        print("not inside a git repository", file=sys.stderr)
        return 2

    summary = current_diff_summary(repo_root)
    major = is_major_change(summary, args.major_files, args.major_lines)

    if args.report or not (args.push or args.force_push_any_change):
        report(summary, major)

    should_push = False
    if args.force_push_any_change and has_any_change(summary):
        should_push = True
    elif args.push and major:
        should_push = True

    if not should_push:
        return 0

    message = args.message or (
        f"Auto backup: {summary.changed_files} files, {summary.changed_lines} changed lines"
    )
    return auto_commit_and_push(repo_root, message)


def main() -> int:
    args = parse_args()
    if not args.watch:
        return run_once(args)

    while True:
        code = run_once(args)
        if code != 0:
            return code
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
