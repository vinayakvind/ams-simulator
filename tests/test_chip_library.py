"""Unit tests for reusable chip assembly catalog composition."""

from __future__ import annotations

import unittest

from simulator.catalog import compose_chip_profile, list_chip_profiles, list_reusable_ips


class ChipLibraryTests(unittest.TestCase):
    """Verify reusable chip profile composition and compatibility handling."""

    def test_compose_sensor_hub_profile_for_generic130(self) -> None:
        payload = compose_chip_profile(
            profile_key="mixed_signal_sensor_hub",
            design_name="demo_sensor_hub",
            technology="generic130",
        )

        self.assertEqual(payload["chip_profile"]["key"], "mixed_signal_sensor_hub")
        self.assertIn("sar_adc_top", payload["blocks"])
        self.assertIn("sigma_delta_adc_top", payload["blocks"])
        self.assertIn("spi_controller", payload["blocks"])
        self.assertTrue(any(entry["key"] == "adc_transient_vip" for entry in payload["verification_ips"]))
        self.assertTrue(any(entry["key"] == "sensor_hub_control_plane" for entry in payload["digital_subsystems"]))

    def test_incompatible_profile_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            compose_chip_profile(
                profile_key="lin_node_asic",
                design_name="demo_lin_chip",
                technology="generic65",
            )

    def test_profile_and_ip_listings_expose_expected_keys(self) -> None:
        profile_keys = {entry["key"] for entry in list_chip_profiles()}
        ip_keys = {entry["key"] for entry in list_reusable_ips()}

        self.assertIn("lin_node_asic", profile_keys)
        self.assertIn("mixed_signal_sensor_hub", profile_keys)
        self.assertIn("bandgap", ip_keys)
        self.assertIn("sar_adc_top", ip_keys)


if __name__ == "__main__":
    unittest.main()