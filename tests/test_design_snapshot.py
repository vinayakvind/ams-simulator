"""Unit tests for aggregated design snapshot execution."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from simulator.verification.design_snapshot import run_design_snapshot


class DesignSnapshotTests(unittest.TestCase):
    """Verify that design snapshots can aggregate multiple verified blocks."""

    def test_run_design_snapshot_aggregates_multiple_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            design_dir = root / "designs" / "demo"
            reports_dir = root / "reports"
            sources_dir = root / "sources"
            reports_dir.mkdir(parents=True, exist_ok=True)
            sources_dir.mkdir(parents=True, exist_ok=True)

            spec_template = """
block:
  name: {block}
  type: mixed
  source: sources/{block}.spice
verification:
  case_id: TOP-{block_upper}
  category: Top
  standard: Demo spec
  description: Demo snapshot for {block}
  analysis: transient
  settings:
    tstop: 1e-6
    tstep: 1e-7
  checks:
    - type: has_key
      key: V(analog_in)
      description: Input waveform exists
    - type: has_any_key
      keys: [V(output)]
      description: Output waveform exists
    - type: min_length
      key: time
      min: 3
      description: Enough samples were produced
""".strip()

            for block in ("alpha", "beta"):
                block_dir = design_dir / "blocks" / block
                block_dir.mkdir(parents=True, exist_ok=True)
                (sources_dir / f"{block}.spice").write_text("* demo\n.END\n", encoding="utf-8")
                (block_dir / "spec.yaml").write_text(
                    spec_template.format(block=block, block_upper=block.upper()),
                    encoding="utf-8",
                )

            def fake_run_netlist(self, netlist_path, analysis_type="transient", output_file=None, **kwargs):
                if output_file:
                    raw_path = Path(output_file)
                    raw_path.parent.mkdir(parents=True, exist_ok=True)
                    raw_path.write_text(json.dumps({"saved": str(netlist_path)}), encoding="utf-8")
                return {
                    "type": analysis_type,
                    "time": [0.0, 5e-7, 1e-6],
                    "V(analog_in)": [0.0, 0.5, 1.0],
                    "V(output)": [0.0, 0.4, 0.8],
                }

            with patch("simulator.verification.design_snapshot.PROJECT_ROOT", root), patch(
                "simulator.verification.design_snapshot.SimulationRunner.run_netlist",
                new=fake_run_netlist,
            ):
                report = run_design_snapshot("demo")

            self.assertEqual(report["summary"]["total"], 2)
            self.assertEqual(report["summary"]["passed"], 2)
            self.assertEqual(report["summary"]["overall"], "PASS")
            self.assertEqual(len(report["tests"]), 2)
            self.assertEqual(len(report["raw_results_paths"]), 2)
            self.assertTrue((reports_dir / "demo_regression_latest.json").exists())
            self.assertTrue((reports_dir / "demo_regression_latest.md").exists())


if __name__ == "__main__":
    unittest.main()