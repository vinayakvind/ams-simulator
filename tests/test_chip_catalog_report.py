"""Unit tests for chip catalog report generation."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from simulator.reporting.chip_catalog import build_chip_catalog_payload, generate_chip_catalog_report


class ChipCatalogReportTests(unittest.TestCase):
    """Verify technology-filtered chip catalog reports are generated."""

    def test_build_payload_marks_compatibility_for_selected_technology(self) -> None:
        payload = build_chip_catalog_payload(technology="generic130")

        self.assertEqual(payload["technology_filter"], "generic130")
        self.assertGreater(payload["summary"]["compatible_ip_count"], 0)
        self.assertTrue(any(entry["key"] == "lin_node_asic" and entry["compatible"] for entry in payload["chip_profiles"]))
        self.assertTrue(any(entry["key"] == "bandgap" and entry["compatible"] for entry in payload["reusable_ips"]))

    def test_generate_report_writes_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            json_path = root / "chip_catalog_generic130_latest.json"
            markdown_path = root / "chip_catalog_generic130_latest.md"

            report = generate_chip_catalog_report(
                technology="generic130",
                json_output=json_path,
                markdown_output=markdown_path,
            )

            self.assertTrue(json_path.exists())
            self.assertTrue(markdown_path.exists())
            self.assertEqual(report["json"], json_path)
            self.assertEqual(report["markdown"], markdown_path)


if __name__ == "__main__":
    unittest.main()