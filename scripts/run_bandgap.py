"""
Bandgap Reference Validation Script.

Imports the bandgap reference SPICE netlist, runs DC analysis across
process corners and temperatures, checks the ~1.25V output spec.

Usage:
    ams-run scripts/run_bandgap.py
    python scripts/run_bandgap.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulator.dsl import Project


def main():
    proj = Project("bandgap_validation", technology="generic180")

    # Import bandgap reference
    proj.import_spice(
        "examples/standard_circuits/bandgap_reference.spice",
        block_name="bandgap_ref",
    )

    print(f"Project: {proj.name}")
    print(f"Blocks: {proj.list_blocks()}")
    print()

    # Run DC analysis across corners/temps
    results = proj.run(
        blocks=["bandgap_ref"],
        analyses=["dc"],
        corners=["TT", "FF", "SS"],
        temps=[-40, 27, 125],
        specs={
            "bandgap_ref": {
                "V(output)": (1.0, 1.5, "V"),
            },
        },
    )

    results.summary()
    results.report("reports/bandgap_validation.md")

    proj.close()


if __name__ == "__main__":
    main()
