# Autonomous Agent Prompt

Cycle: 26
Generated: 2026-05-02T20:21:06.550334
Workspace: My Simulator
Branch: master
Commit: d33d405dda4bbbff8d84bf129444a0df46f9eae3

## Controller Handshake Files

- Handshake JSON: reports/agent_handshake_latest.json
- Feedback Markdown: reports/agent_feedback_latest.md
- Controller State JSON: reports/agent_controller_state.json
- Current Prompt File: reports/agent_prompt_latest.md

## Goal

Run validation and reporting, then feed the next concrete improvement batch back into the CLI agent without needing a fresh manual prompt.

## Validation Commands Already Run This Cycle

- PASS verify-project-status (log: reports/agent_cycles/cycle_0026_verify-project-status.log)
- PASS generate-chip-catalog-all (log: reports/agent_cycles/cycle_0026_generate-chip-catalog-all.log)
- PASS generate-chip-catalog-generic130 (log: reports/agent_cycles/cycle_0026_generate-chip-catalog-generic130.log)
- PASS generate-chip-catalog-generic65 (log: reports/agent_cycles/cycle_0026_generate-chip-catalog-generic65.log)
- PASS generate-chip-catalog-bcd180 (log: reports/agent_cycles/cycle_0026_generate-chip-catalog-bcd180.log)
- PASS run-strict-autopilot (log: reports/agent_cycles/cycle_0026_run-strict-autopilot.log)
- PASS repo-backup-report (log: reports/agent_cycles/cycle_0026_repo-backup-report.log)

## Priority Build Targets

- Reusable IP backlog: high_speed_comparator, differential_amplifier, buffered_precision_dac, lvds_receiver, ethernet_phy, profibus_transceiver, canopen_controller, isolated_gate_driver
- Verification IP backlog: ethernet_vip, profibus_vip, canopen_vip, clock_gating_vip, precision_dac_vip, high_speed_signal_vip
- Digital subsystem backlog: clock_gating_plane, ethernet_control_plane, safety_monitor_plane, infotainment_control_plane, power_conversion_plane
- Chip profile backlog: automotive_infotainment_soc, industrial_iot_gateway, isolated_power_supply_controller, ethernet_sensor_hub, safe_motor_drive_controller
- Prefer implementing or closing these catalog items before unrelated polish work.

## Observations

- All queued validation/report commands exited cleanly in the latest cycle.
- Strict autopilot overall status: PASS.
- Chip catalog inventory: 69 reusable IPs, 35 VIPs, 25 digital subsystems, 24 chip profiles.
- generic130: 69/69 reusable IPs and 24/24 chip profiles are currently compatible.
- generic65: 69/69 reusable IPs and 24/24 chip profiles are currently compatible.
- bcd180: 69/69 reusable IPs and 24/24 chip profiles are currently compatible.
- Priority backlog configured for 24 targeted reusable IP, VIP, digital-subsystem, and chip-profile items.
- Workflow focus: Use the latest strict autopilot and chip-catalog reports to decide the next implementation batch.
- Workflow focus: Prefer improvements that expand reusable chip IP, VIP, and technology coverage.
- Workflow focus: Keep the workflow resumable so the next cycle continues cleanly after token or context limits.

## Next Improvements To Implement

- Harden reusable IP priority targets with stronger generators, validation coverage, and example integrations: high_speed_comparator, differential_amplifier, buffered_precision_dac, lvds_receiver.
- Deepen verification IP priority targets with richer protocol scenarios and mixed-signal regressions: ethernet_vip, profibus_vip, canopen_vip, clock_gating_vip.
- Expand digital subsystem priority targets with reusable control planes, integration rules, and validation coverage: clock_gating_plane, ethernet_control_plane, safety_monitor_plane, infotainment_control_plane.
- Expand chip profile priority targets with assembled top-level references, automation coverage, and design collateral: automotive_infotainment_soc, industrial_iot_gateway, isolated_power_supply_controller, ethernet_sensor_hub.

## Agent Instructions

- Treat the script as the initiator. Continue from the latest handshake, feedback, and repo state instead of asking for a fresh prompt.
- Prioritize concrete repo changes that improve automation, chip assembly coverage, technology portability, or validation completeness.
- After making changes, rerun only the necessary repo commands or let the controller launch the next cycle.
- Do not invoke scripts/agent_cli_controller.py, scripts/start_agent_cli_daemon.ps1, or scripts/open_agent_cli_window.ps1 from inside the external agent run; the controller already owns cycle orchestration.
- If you hit a token, context, or rate limit, stop cleanly after writing any useful partial progress. The controller will generate the next cycle prompt and continue.
- Use the current repo state as the source of truth. Do not assume a previous cycle fully completed unless the reports show it.
