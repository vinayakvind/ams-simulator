# Autonomous Agent Prompt

Cycle: 19
Generated: 2026-05-02T19:05:55.269031
Workspace: My Simulator
Branch: master
Commit: 81369a6ac4ec8918c3aaedfe490e4e429bd1dbdf

## Controller Handshake Files

- Handshake JSON: reports/agent_handshake_latest.json
- Feedback Markdown: reports/agent_feedback_latest.md
- Controller State JSON: reports/agent_controller_state.json
- Current Prompt File: reports/agent_prompt_latest.md

## Goal

Run validation and reporting, then feed the next concrete improvement batch back into the CLI agent without needing a fresh manual prompt.

## Validation Commands Already Run This Cycle

- PASS verify-project-status (log: reports/agent_cycles/cycle_0019_verify-project-status.log)
- PASS generate-chip-catalog-all (log: reports/agent_cycles/cycle_0019_generate-chip-catalog-all.log)
- PASS generate-chip-catalog-generic130 (log: reports/agent_cycles/cycle_0019_generate-chip-catalog-generic130.log)
- PASS generate-chip-catalog-generic65 (log: reports/agent_cycles/cycle_0019_generate-chip-catalog-generic65.log)
- PASS generate-chip-catalog-bcd180 (log: reports/agent_cycles/cycle_0019_generate-chip-catalog-bcd180.log)
- PASS run-strict-autopilot (log: reports/agent_cycles/cycle_0019_run-strict-autopilot.log)
- PASS repo-backup-report (log: reports/agent_cycles/cycle_0019_repo-backup-report.log)

## Priority Build Targets

- Reusable IP backlog: high_speed_comparator, differential_amplifier, buffered_precision_dac, lvds_receiver, ethernet_phy, profibus_transceiver, canopen_controller, isolated_gate_driver
- Verification IP backlog: ethernet_vip, profibus_vip, canopen_vip, clock_gating_vip, precision_dac_vip, high_speed_signal_vip
- Digital subsystem backlog: clock_gating_plane, ethernet_control_plane, safety_monitor_plane, infotainment_control_plane, power_conversion_plane
- Chip profile backlog: automotive_infotainment_soc, industrial_iot_gateway, isolated_power_supply_controller, ethernet_sensor_hub, safe_motor_drive_controller
- Prefer implementing or closing these catalog items before unrelated polish work.

## Observations

- All queued validation/report commands exited cleanly in the latest cycle.
- Strict autopilot overall status: PASS.
- Chip catalog inventory: 61 reusable IPs, 29 VIPs, 20 digital subsystems, 19 chip profiles.
- generic130: 50/61 reusable IPs and 16/19 chip profiles are currently compatible.
- generic65: 59/61 reusable IPs and 18/19 chip profiles are currently compatible.
- bcd180: 49/61 reusable IPs and 15/19 chip profiles are currently compatible.
- Priority backlog configured for 24 targeted reusable IP, VIP, digital-subsystem, and chip-profile items.
- Workflow focus: Use the latest strict autopilot and chip-catalog reports to decide the next implementation batch.
- Workflow focus: Prefer improvements that expand reusable chip IP, VIP, and technology coverage.
- Workflow focus: Keep the workflow resumable so the next cycle continues cleanly after token or context limits.

## Next Improvements To Implement

- Expand generic130 chip-profile support for: iot_edge_hub, secure_iot_gateway, wireless_powered_sensor.
- Expand generic130 reusable IP support for: aes_accelerator, ble_transceiver, bms_controller, i3c_controller, imu_interface, nfc_controller.
- Expand generic65 chip-profile support for: secure_iot_gateway.
- Expand generic65 reusable IP support for: rf_front_end, uwb_transceiver.
- Expand bcd180 chip-profile support for: iot_edge_hub, secure_iot_gateway, smart_battery_pack, wireless_powered_sensor.

## Agent Instructions

- Treat the script as the initiator. Continue from the latest handshake, feedback, and repo state instead of asking for a fresh prompt.
- Prioritize concrete repo changes that improve automation, chip assembly coverage, technology portability, or validation completeness.
- After making changes, rerun only the necessary repo commands or let the controller launch the next cycle.
- If you hit a token, context, or rate limit, stop cleanly after writing any useful partial progress. The controller will generate the next cycle prompt and continue.
- Use the current repo state as the source of truth. Do not assume a previous cycle fully completed unless the reports show it.
