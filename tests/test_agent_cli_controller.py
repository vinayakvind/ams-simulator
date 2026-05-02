"""Unit tests for the script-driven agent CLI controller."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "agent_cli_controller.py"
SPEC = importlib.util.spec_from_file_location("agent_cli_controller", SCRIPT_PATH)
agent_cli_controller = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(agent_cli_controller)


class AgentCliControllerTests(unittest.TestCase):
    """Verify resumable controller feedback and state generation."""

    def test_load_queue_adds_default_priority_targets_for_legacy_queue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            queue_path = Path(tmp_dir) / "agent_workflow.json"
            queue_path.write_text(
                json.dumps({"name": "legacy", "goal": "legacy goal", "focus_areas": [], "steps": []}),
                encoding="utf-8",
            )

            queue = agent_cli_controller.load_queue(queue_path)

            self.assertIn("priority_build_targets", queue)
            self.assertIn("reusable_ips", queue["priority_build_targets"])

    def test_collect_feedback_reports_generic65_compatibility_gap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            reports = root / "reports"
            reports.mkdir(parents=True, exist_ok=True)

            (reports / "design_autopilot_latest.json").write_text(
                json.dumps({"overall": "PASS", "designs": []}),
                encoding="utf-8",
            )
            (reports / "chip_catalog_latest.json").write_text(
                json.dumps({
                    "summary": {
                        "reusable_ip_count": 15,
                        "verification_ip_count": 6,
                        "digital_subsystem_count": 3,
                        "chip_profile_count": 5,
                    }
                }),
                encoding="utf-8",
            )
            for technology, compatible_profiles, incompatible_ips in (
                ("generic130", 5, []),
                ("generic65", 3, ["ldo_analog", "lin_transceiver"]),
                ("bcd180", 5, []),
            ):
                payload = {
                    "summary": {
                        "compatible_ip_count": 11 if technology == "generic65" else 15,
                        "reusable_ip_count": 15,
                        "compatible_chip_profile_count": compatible_profiles,
                        "chip_profile_count": 5,
                    },
                    "reusable_ips": [
                        {"key": key, "compatible": False} for key in incompatible_ips
                    ],
                    "chip_profiles": [
                        {"key": "lin_node_asic", "compatible": technology != "generic65"},
                        {"key": "power_management_unit", "compatible": technology != "generic65"},
                    ],
                }
                (reports / f"chip_catalog_{technology}_latest.json").write_text(json.dumps(payload), encoding="utf-8")

            feedback = agent_cli_controller.collect_feedback(
                repo_root=root,
                validation_results=[{"id": "verify", "exit_code": 0}],
                queue={"focus_areas": []},
            )

            self.assertTrue(any("generic65" in item for item in feedback["improvements"]))
            self.assertTrue(any("ldo_analog" in item for item in feedback["improvements"]))

    def test_collect_feedback_uses_priority_targets_when_reports_are_green(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            reports = root / "reports"
            reports.mkdir(parents=True, exist_ok=True)

            (reports / "design_autopilot_latest.json").write_text(
                json.dumps({"overall": "PASS", "designs": []}),
                encoding="utf-8",
            )

            chip_catalog_payload = {
                "summary": {
                    "reusable_ip_count": 4,
                    "verification_ip_count": 2,
                    "digital_subsystem_count": 1,
                    "chip_profile_count": 2,
                },
                "reusable_ips": [
                    {"key": "bandgap"},
                    {"key": "buck_converter"},
                    {"key": "ldo_analog"},
                    {"key": "lin_transceiver"},
                ],
                "verification_ips": [
                    {"key": "spi_vip"},
                    {"key": "lin_vip"},
                ],
                "chip_profiles": [
                    {"key": "lin_node_asic"},
                    {"key": "power_management_unit"},
                ],
            }
            (reports / "chip_catalog_latest.json").write_text(
                json.dumps(chip_catalog_payload),
                encoding="utf-8",
            )

            for technology in ("generic130", "generic65", "bcd180"):
                (reports / f"chip_catalog_{technology}_latest.json").write_text(
                    json.dumps(
                        {
                            "summary": {
                                "compatible_ip_count": 4,
                                "reusable_ip_count": 4,
                                "compatible_chip_profile_count": 2,
                                "chip_profile_count": 2,
                            },
                            "reusable_ips": [
                                {"key": "bandgap", "compatible": True},
                                {"key": "buck_converter", "compatible": True},
                                {"key": "ldo_analog", "compatible": True},
                                {"key": "lin_transceiver", "compatible": True},
                            ],
                            "verification_ips": [
                                {"key": "spi_vip", "compatible": True},
                                {"key": "lin_vip", "compatible": True},
                            ],
                            "chip_profiles": [
                                {"key": "lin_node_asic", "compatible": True},
                                {"key": "power_management_unit", "compatible": True},
                            ],
                        }
                    ),
                    encoding="utf-8",
                )

            feedback = agent_cli_controller.collect_feedback(
                repo_root=root,
                validation_results=[{"id": "verify", "exit_code": 0}],
                queue={
                    "focus_areas": [],
                    "priority_build_targets": {
                        "reusable_ips": ["bandgap", "buck_converter", "ldo_analog", "lin_transceiver"],
                        "verification_ips": ["spi_vip", "lin_vip"],
                        "chip_profiles": ["lin_node_asic", "power_management_unit"],
                    },
                },
            )

            self.assertTrue(any("Harden reusable IP priority targets" in item for item in feedback["improvements"]))
            self.assertTrue(any("Deepen verification IP priority targets" in item for item in feedback["improvements"]))
            self.assertTrue(any("Expand chip profile priority targets" in item for item in feedback["improvements"]))
            self.assertFalse(any(item.startswith("Expand the reusable chip library with additional IPs") for item in feedback["improvements"]))

    def test_run_cycle_writes_handshake_state_feedback_and_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            reports = root / "reports"
            reports.mkdir(parents=True, exist_ok=True)
            queue_path = root / "agent_workflow.json"
            queue_path.write_text(
                json.dumps(
                    {
                        "name": "test loop",
                        "goal": "Test the controller loop.",
                        "focus_areas": ["Keep prompts resumable."],
                        "priority_build_targets": {
                            "reusable_ips": ["bandgap", "buck_converter"],
                            "verification_ips": ["spi_vip"],
                            "chip_profiles": ["power_management_unit"]
                        },
                        "steps": [
                            {
                                "id": "hello",
                                "title": "Echo hello",
                                "command": f'"{sys.executable}" -c "print(\"hello\")"',
                                "continue_on_failure": True,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            args = SimpleNamespace(
                repo=str(root),
                queue_file=str(queue_path),
                state_file=str(root / "reports" / "agent_controller_state.json"),
                handshake_file=str(root / "reports" / "agent_handshake_latest.json"),
                feedback_file=str(root / "reports" / "agent_feedback_latest.md"),
                feedback_json_file=str(root / "reports" / "agent_feedback_latest.json"),
                prompt_file=str(root / "reports" / "agent_prompt_latest.md"),
                agent_log_file=str(root / "reports" / "agent_cli_output_latest.log"),
                step_log_dir=str(root / "reports" / "agent_cycles"),
                api_handshake_url="http://127.0.0.1:59999/api/session/handshake",
                agent_command_template=None,
                token_limit_pattern=list(agent_cli_controller.DEFAULT_TOKEN_PATTERNS),
            )

            result = agent_cli_controller.run_cycle(args)

            self.assertTrue(Path(args.handshake_file).exists())
            self.assertTrue(Path(args.state_file).exists())
            self.assertTrue(Path(args.feedback_file).exists())
            self.assertTrue(Path(args.feedback_json_file).exists())
            self.assertTrue(Path(args.prompt_file).exists())
            self.assertEqual(result["state"]["cycle_count"], 1)
            self.assertEqual(result["state"]["status"], "idle")
            prompt_text = Path(args.prompt_file).read_text(encoding="utf-8")
            self.assertIn("Autonomous Agent Prompt", prompt_text)
            self.assertIn("reports/agent_handshake_latest.json", prompt_text)
            self.assertNotIn(str(root), prompt_text)
            self.assertIn("Priority Build Targets", prompt_text)
            self.assertIn("bandgap, buck_converter", prompt_text)

    def test_run_agent_command_detects_token_limit_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            prompt_file = root / "prompt.md"
            prompt_file.write_text("prompt", encoding="utf-8")
            state_file = root / "state.json"
            feedback_file = root / "feedback.md"
            handshake_file = root / "handshake.json"
            queue_file = root / "queue.json"
            log_file = root / "agent.log"

            result = agent_cli_controller.run_agent_command(
                command_template=f'"{sys.executable}" -c "print(\'token limit reached\')"',
                prompt_path=prompt_file,
                state_path=state_file,
                feedback_path=feedback_file,
                handshake_path=handshake_file,
                queue_path=queue_file,
                repo_root=root,
                cycle_count=1,
                log_path=log_file,
                token_patterns=list(agent_cli_controller.DEFAULT_TOKEN_PATTERNS),
            )

            self.assertEqual(result["exit_code"], 0)
            self.assertTrue(result["token_limit_detected"])
            self.assertTrue(log_file.exists())

    def test_parse_args_reads_agent_command_template_from_environment(self) -> None:
        with mock.patch.dict(agent_cli_controller.os.environ, {"AMS_AGENT_COMMAND_TEMPLATE": "echo handshake"}, clear=False):
            args = agent_cli_controller.parse_args([])

        self.assertEqual(args.agent_command_template, "echo handshake")


if __name__ == "__main__":
    unittest.main()