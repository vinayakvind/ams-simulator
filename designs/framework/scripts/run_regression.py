"""
Run full regression on a design - simulates and verifies all blocks.

Usage:
    python designs/framework/scripts/run_regression.py --design lin_asic
    python designs/framework/scripts/run_regression.py --design lin_asic --verbose
"""

import argparse
import json
import sys
import time
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    parser = argparse.ArgumentParser(description="Run full design regression")
    parser.add_argument("--design", required=True, help="Design name")
    parser.add_argument("--verbose", action="store_true", help="Detailed output")
    parser.add_argument("--output", help="Output JSON report")
    args = parser.parse_args()

    # Import verify_block from sibling script
    scripts_dir = Path(__file__).parent
    sys.path.insert(0, str(scripts_dir))
    from verify_block import verify_block, write_report

    design_dir = PROJECT_ROOT / "designs" / args.design
    blocks_dir = design_dir / "blocks"

    if not blocks_dir.exists():
        print(f"Error: No blocks directory in {design_dir}")
        sys.exit(1)

    block_names = sorted(d.name for d in blocks_dir.iterdir() if d.is_dir())

    print(f"╔══════════════════════════════════════════════════════╗")
    print(f"║  REGRESSION: {args.design:38s}  ║")
    print(f"║  Blocks: {len(block_names):3d}                                       ║")
    print(f"║  Date: {datetime.now().strftime('%Y-%m-%d %H:%M'):42s}  ║")
    print(f"╚══════════════════════════════════════════════════════╝")

    results = []
    start_time = time.time()

    for i, name in enumerate(block_names):
        print(f"\n[{i+1}/{len(block_names)}] {name}...", end=" ", flush=True)

        t0 = time.time()
        try:
            result = verify_block(name, design_dir)
            write_report(name, result, design_dir)
        except Exception as e:
            result = {"name": name, "status": "ERROR", "checks": [],
                      "error": str(e)}

        elapsed = time.time() - t0
        result["time_s"] = round(elapsed, 2)
        results.append(result)

        status = result["status"]
        symbol = {"PASS": "✓", "FAIL": "✗", "SKIP": "○", "ERROR": "!"}.get(status, "?")
        print(f"{symbol} {status} ({elapsed:.1f}s)")

        if args.verbose and result.get("checks"):
            for c in result["checks"]:
                pf = "PASS" if c["pass"] else "FAIL"
                print(f"    [{pf}] {c['test']}: {c['value']}")

    total_time = time.time() - start_time

    # Summary
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    skipped = sum(1 for r in results if r["status"] == "SKIP")
    errors = sum(1 for r in results if r["status"] == "ERROR")
    total = len(results)

    print(f"\n{'='*55}")
    print(f"  RESULTS: {passed} PASS | {failed} FAIL | {skipped} SKIP | {errors} ERROR")
    print(f"  Total: {total} blocks in {total_time:.1f}s")
    print(f"{'='*55}")

    for r in results:
        s = r["status"]
        sym = {"PASS": "✓", "FAIL": "✗", "SKIP": "○", "ERROR": "!"}.get(s, "?")
        print(f"  {sym} {r['name']:30s} {s:6s} ({r.get('time_s', 0):.1f}s)")

    overall = "PASS" if failed == 0 and errors == 0 and passed > 0 else "FAIL"
    print(f"\n  Overall: {overall}")

    # Write regression report
    report_path = design_dir / "REGRESSION_REPORT.md"
    with open(report_path, "w") as f:
        f.write(f"# Regression Report - {args.design}\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"## Summary\n")
        f.write(f"- Total blocks: {total}\n")
        f.write(f"- Passing: {passed}\n")
        f.write(f"- Failing: {failed}\n")
        f.write(f"- Skipped: {skipped}\n")
        f.write(f"- Errors: {errors}\n")
        f.write(f"- Runtime: {total_time:.1f}s\n")
        f.write(f"- Overall: **{overall}**\n\n")
        f.write(f"## Block Results\n")
        f.write(f"| Block | Status | Time | Details |\n")
        f.write(f"|-------|--------|------|---------|\n")
        for r in results:
            checks_summary = "; ".join(
                f"{c['test']}={'PASS' if c['pass'] else 'FAIL'}"
                for c in r.get("checks", [])
            )
            f.write(f"| {r['name']} | {r['status']} | {r.get('time_s', 0):.1f}s | {checks_summary} |\n")

    print(f"\n  Report: {report_path}")

    # JSON output
    if args.output:
        with open(args.output, "w") as f:
            json.dump({
                "design": args.design,
                "date": datetime.now().isoformat(),
                "summary": {
                    "total": total, "passed": passed, "failed": failed,
                    "skipped": skipped, "errors": errors, "overall": overall,
                },
                "blocks": results,
            }, f, indent=2)
        print(f"  JSON: {args.output}")

    sys.exit(0 if overall == "PASS" else 1)


if __name__ == "__main__":
    main()
