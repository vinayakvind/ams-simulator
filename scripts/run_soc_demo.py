"""
SoC Demo Script - Multi-block chip composition and validation.

Demonstrates the full SoC flow:
1. Import multiple analog blocks from SPICE files
2. Define a custom block programmatically
3. Compose them into a chip-level design
4. Run validation campaign across corners/temps
5. Generate combined HTML report

Usage:
    ams-run scripts/run_soc_demo.py
    python scripts/run_soc_demo.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulator.dsl import Project


def main():
    proj = Project("serdes_chip", technology="generic180")

    # ── Step 1: Import existing SPICE blocks ──
    print("=== Step 1: Importing SPICE blocks ===")

    proj.import_spice(
        "examples/standard_circuits/bandgap_reference.spice",
        "bandgap_ref",
    )
    proj.import_spice(
        "examples/standard_circuits/ldo_regulator.spice",
        "ldo_regulator",
    )
    proj.import_spice(
        "examples/standard_circuits/differential_amplifier.spice",
        "diff_amp",
    )

    print(f"Imported blocks: {proj.list_blocks()}")
    print()

    # ── Step 2: Define a custom voltage divider block ──
    print("=== Step 2: Defining custom block ===")

    with proj.block("voltage_divider") as vd:
        vd.port("vin", "input")
        vd.port("vout", "output")
        vd.port("vss", "ground")

        vin = vd.add("VoltageSource", name="Vin", dc="5")
        r1 = vd.add("R", name="R1", value="10k")
        r2 = vd.add("R", name="R2", value="10k")
        rload = vd.add("R", name="Rload", value="100k")

        vd.connect(vin.p, r1.p1, name="vin")
        vd.connect(r1.p2, r2.p1, rload.p1, name="vout")
        vd.connect(vin.n, r2.p2, rload.p2, name="0")

        vd.spec("output_voltage", parameter="V(vout)", min=2.3, typ=2.5, max=2.7, unit="V")

    print(f"All blocks: {proj.list_blocks()}")
    print()

    # ── Step 3: Compose SoC chip ──
    print("=== Step 3: Composing SoC chip ===")

    with proj.chip("serdes_top") as chip:
        bgr = chip.use("bandgap_ref")
        ldo = chip.use("ldo_regulator")
        damp = chip.use("diff_amp")

        # Define power domains
        chip.power_domain("analog_1v8", voltage=1.8, blocks=["bandgap_ref"])
        chip.power_domain("io_3v3", voltage=3.3, blocks=["ldo_regulator"])

    print(f"Chip composed: {chip}")
    print()

    # ── Step 4: Run validation campaign on individual blocks ──
    print("=== Step 4: Running validation campaign ===")

    results = proj.run(
        blocks=["bandgap_ref", "ldo_regulator", "voltage_divider"],
        analyses=["dc"],
        corners=["TT", "FF", "SS"],
        temps=[-40, 27, 125],
        specs={
            "bandgap_ref": {"V(output)": (1.0, 1.5, "V")},
            "ldo_regulator": {"V(output)": (2.5, 4.0, "V")},
            "voltage_divider": {"V(vout)": (2.0, 3.0, "V")},
        },
    )

    # ── Step 5: Results and reporting ──
    print()
    print("=== Step 5: Results ===")
    results.summary()

    results.report("reports/soc_demo.html")
    results.report("reports/soc_demo.md")

    # Show campaign history
    print()
    print("Campaign history:")
    for c in proj.list_campaigns():
        print(f"  [{c['id']}] {c['name']} - {c['status']} "
              f"({c['completed_jobs']}/{c['total_jobs']} jobs)")

    proj.close()


if __name__ == "__main__":
    main()
