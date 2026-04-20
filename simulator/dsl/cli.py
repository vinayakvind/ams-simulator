"""
CLI entry point for running Python design scripts.

Usage:
    ams-run scripts/run_ldo.py
    ams-run scripts/run_bandgap.py --verbose
    python -m simulator.dsl.cli scripts/run_ldo.py
"""

import argparse
import sys
import runpy


def main():
    parser = argparse.ArgumentParser(
        prog="ams-run",
        description="AMS Simulator - Run a Python design script",
    )
    parser.add_argument("script", help="Path to Python design script")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose output"
    )
    args = parser.parse_args()

    # Make verbose flag available to scripts
    if args.verbose:
        import os
        os.environ["AMS_VERBOSE"] = "1"

    # Execute the script
    sys.argv = [args.script]
    runpy.run_path(args.script, run_name="__main__")


if __name__ == "__main__":
    main()
