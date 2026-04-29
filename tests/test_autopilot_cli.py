"""Unit tests for the design autopilot CLI."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from simulator.cli import autopilot


class AutopilotCliTests(unittest.TestCase):
    """Verify the autopilot CLI writes summary artifacts and validates outputs."""

    def test_main_writes_summary_and_validates_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            reports_dir = root / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)

            for design_id, title in (("lin_asic", "LIN ASIC"), ("demo_adc", "Demo ADC")):
                design_dir = root / "designs" / design_id
                design_dir.mkdir(parents=True, exist_ok=True)
                manifest = {
                    "design": {
                        "id": design_id,
                        "title": title,
                        "headline": title,
                        "summary": f"Summary for {title}",
                        "narrative": f"Narrative for {title}",
                        "standard": "Internal",
                        "technology": "generic180",
                        "signoff_boundary": "Demo only",
                        "tags": ["demo"],
                    },
                    "architecture": {
                        "summary": f"Architecture for {title}",
                        "power_tree_summary": "3.3V",
                        "domains": [],
                        "power_sequence": [],
                        "control_path": [],
                    },
                    "indexed_flow": [],
                    "analysis_playbook": [],
                    "script_index": [],
                    "corner_closure": {"matrix": {}},
                    "blocks": [],
                }
                (design_dir / "design_reference.json").write_text(json.dumps(manifest), encoding="utf-8")

            def fake_lin_regression():
                json_path = reports_dir / "lin_asic_regression_latest.json"
                markdown_path = reports_dir / "lin_asic_regression_latest.md"
                payload = {
                    "summary": {"total": 1, "passed": 1, "failed": 0, "overall": "PASS"},
                    "tests": [],
                    "report_path": str(json_path),
                    "markdown_report_path": str(markdown_path),
                }
                json_path.write_text(json.dumps(payload), encoding="utf-8")
                markdown_path.write_text("# lin\n", encoding="utf-8")
                return payload

            def fake_snapshot(design_id):
                json_path = reports_dir / f"{design_id}_regression_latest.json"
                markdown_path = reports_dir / f"{design_id}_regression_latest.md"
                payload = {
                    "summary": {"total": 1, "passed": 1, "failed": 0, "unresolved": 0, "overall": "PASS"},
                    "tests": [],
                    "report_path": str(json_path),
                    "markdown_report_path": str(markdown_path),
                }
                json_path.write_text(json.dumps(payload), encoding="utf-8")
                markdown_path.write_text("# snapshot\n", encoding="utf-8")
                return payload

            def fake_portfolio_artifacts(output_ppt=None, project_root=None, design_ids=None):
                json_path = reports_dir / "design_portfolio_overview.json"
                markdown_path = reports_dir / "design_portfolio_overview.md"
                ppt_path = reports_dir / "design_portfolio_overview.pptx"
                json_path.write_text(json.dumps({"designs": list(design_ids or [])}), encoding="utf-8")
                markdown_path.write_text("# portfolio\n", encoding="utf-8")
                ppt_path.write_bytes(b"ppt")
                return {"json": json_path, "markdown": markdown_path, "ppt": ppt_path, "payload": {}}

            summary_json = reports_dir / "autopilot.json"
            summary_md = reports_dir / "autopilot.md"

            with patch("simulator.cli.autopilot.PROJECT_ROOT", root), patch(
                "simulator.cli.autopilot.run_lin_asic_regression",
                side_effect=fake_lin_regression,
            ), patch(
                "simulator.cli.autopilot.run_design_snapshot",
                side_effect=fake_snapshot,
            ), patch(
                "simulator.cli.autopilot.generate_portfolio_artifacts",
                side_effect=fake_portfolio_artifacts,
            ):
                exit_code = autopilot.main(
                    [
                        "--json",
                        str(summary_json),
                        "--markdown",
                        str(summary_md),
                        "--quiet",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(summary_json.exists())
            self.assertTrue(summary_md.exists())

            payload = json.loads(summary_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["overall"], "PASS")
            self.assertEqual(len(payload["designs"]), 2)
            self.assertTrue(any(design["id"] == "lin_asic" for design in payload["designs"]))
            self.assertTrue(any(design["id"] == "demo_adc" for design in payload["designs"]))


if __name__ == "__main__":
    unittest.main()