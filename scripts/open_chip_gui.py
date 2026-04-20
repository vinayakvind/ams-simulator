"""
Open the SoC chip in the AMS Simulator GUI schematic editor.

Loads the chip netlist from the database, launches the GUI directly
in-process, and calls load_from_netlist() synchronously so the
schematic is populated before the event loop starts.

Usage:
    python scripts/open_chip_gui.py
"""

import os
import sys
import subprocess

# Ensure project root on path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def get_chip_netlist() -> str:
    """Read the chip netlist from the SoC demo database."""
    from simulator.db import SimDB, get_circuit

    db_path = os.path.join(ROOT, "serdes_chip.ams.db")
    if not os.path.exists(db_path):
        print("Chip DB not found. Running SoC demo first...")
        subprocess.run(
            [sys.executable, os.path.join(ROOT, "scripts", "run_soc_demo.py")],
            cwd=ROOT,
            check=True,
        )

    db = SimDB(db_path)
    db.initialize()

    chip = get_circuit(db, "serdes_top")
    if chip and chip.netlist:
        netlist = chip.netlist
        db.close()
        return netlist

    # Fallback: load individual blocks and concatenate
    all_netlists = []
    for name in ["bandgap_ref", "ldo_regulator", "voltage_divider", "diff_amp"]:
        c = get_circuit(db, name)
        if c and c.netlist:
            all_netlists.append(f"* Block: {name}\n{c.netlist}")

    db.close()

    if all_netlists:
        return "\n\n".join(all_netlists)

    raise RuntimeError("No circuit netlists found in database")


def main():
    print("[1/3] Reading chip netlist from database...")
    netlist = get_chip_netlist()
    line_count = netlist.count("\n") + 1
    print(f"       Loaded: {len(netlist)} chars, {line_count} lines")

    print("[2/3] Launching AMS Simulator GUI...")
    from PyQt6.QtWidgets import QApplication
    from simulator.gui.main_window import MainWindow

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    window.setWindowTitle("AMS Simulator - SoC Chip: serdes_top")

    print("[3/3] Loading chip netlist into schematic...")
    try:
        # Set the netlist text in the viewer tab
        window.netlist_viewer.set_netlist(netlist)

        # Load into the schematic editor (synchronous, in main thread)
        window.schematic_editor.load_from_netlist(netlist)

        comp_count = len(window.schematic_editor._components)
        wire_count = len(window.schematic_editor._wires)
        print(f"       Schematic: {comp_count} components, {wire_count} wires")

        window.statusbar.showMessage(
            f"SoC Chip: serdes_top  |  {comp_count} components, {wire_count} wires  |  "
            f"bandgap + LDO + diff_amp + voltage_divider"
        )
    except Exception as e:
        print(f"       Load error: {e}")
        import traceback
        traceback.print_exc()

    # Start API server for external control
    try:
        from simulator.api.server import start_api_server
        start_api_server(window, port=5100)
        print(f"       API server running on http://127.0.0.1:5100")
    except Exception:
        pass

    print()
    print("GUI is open. Close the window to exit.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
