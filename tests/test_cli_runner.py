"""Unit tests for CLI runner backend selection and result normalization."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from simulator.cli.runner import SimulationRunner


class SimulationRunnerTests(unittest.TestCase):
    """Verify CLI runner fallback behavior for unsupported transient netlists."""

    def test_behavioral_transient_uses_ngspice_and_normalizes_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            netlist_path = root / "behavioral_adc.spice"
            output_path = root / "results.json"
            netlist_path.write_text(
                """
* demo behavioral adc
Vdd vdd 0 DC 3.3
Vin analog_in 0 SIN(1.25 0.5 1k)
Ecomp out 0 TABLE {V(analog_in)} (0,0) (1.0,0) (1.5,3.3)
.TRAN 1n 2n
.END
""".strip(),
                encoding="utf-8",
            )

            class FakeBackend:
                def __init__(self) -> None:
                    self.ngspice_path = "C:/ngspice/bin/ngspice_con.exe"
                    self.seen_netlist = ""

                def is_available(self) -> bool:
                    return True

                def simulate(self, netlist_content: str):
                    self.seen_netlist = netlist_content
                    return {
                        "time": np.array([0.0, 1e-9, 2e-9]),
                        "v(analog_in)": np.array([1.0, 1.1, 1.2]),
                        "v(out)": np.array([0.0, 0.0, 3.3]),
                    }

            fake_backend = FakeBackend()

            with patch("simulator.cli.runner.NgSpiceBackend", return_value=fake_backend), patch.object(
                SimulationRunner,
                "_run_transient_analysis",
                side_effect=AssertionError("Python transient engine should not run for unsupported behavioral sources"),
            ):
                runner = SimulationRunner(verbose=False)
                results = runner.run_netlist(
                    str(netlist_path),
                    analysis_type="transient",
                    output_file=str(output_path),
                    tstop=2e-9,
                    tstep=1e-9,
                )

            self.assertIn(".tran 1e-09 2e-09 0", fake_backend.seen_netlist.lower())
            self.assertEqual(results["metadata"]["backend"], "ngspice")
            self.assertEqual(results["time"], [0.0, 1e-9, 2e-9])
            self.assertEqual(results["V(analog_in)"], [1.0, 1.1, 1.2])
            self.assertEqual(results["V(out)"], [0.0, 0.0, 3.3])

            saved = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["V(analog_in)"], [1.0, 1.1, 1.2])
            self.assertEqual(saved["metadata"]["backend"], "ngspice")


if __name__ == "__main__":
    unittest.main()