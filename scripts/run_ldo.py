"""
LDO Regulator Validation Script.

Imports the LDO SPICE netlist, runs simulation across 3 corners x 3 temps,
checks output voltage specs, and generates an HTML report.

Usage:
    ams-run scripts/run_ldo.py
    python scripts/run_ldo.py
"""

import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulator.dsl import Project


def main():
    # Create project with DB-backed workspace
    proj = Project("ldo_validation", technology="generic180")

    # Import existing SPICE netlist as a Block
    proj.import_spice(
        "examples/standard_circuits/ldo_regulator.spice",
        block_name="ldo_regulator",
    )

    # List what's in the project
    print(f"Project: {proj.name}")
    print(f"Blocks: {proj.list_blocks()}")
    print()

    # Run full simulation campaign
    results = proj.run(
        blocks=["ldo_regulator"],
        analyses=["dc"],
        corners=["TT", "FF", "SS"],
        temps=[-40, 27, 125],
        specs={
            "ldo_regulator": {
                "V(output)": (2.5, 4.0, "V"),
            },
        },
    )

    # Print summary
    results.summary()

    # Generate reports
    results.report("reports/ldo_validation.html")
    results.report("reports/ldo_validation.md")

    # Show pass/fail
    if results.passed:
        print("\nAll specs PASSED across all corners and temperatures.")
    else:
        print("\nSome specs FAILED. Check report for details.")
        worst = results.get_worst_case("ldo_regulator")
        if worst:
            print(f"  Worst case: corner={worst['corner']}, temp={worst['temp']}C")

    proj.close()


if __name__ == "__main__":
    main()
