# Autonomous Agent Prompt

Cycle: 1
Generated: 2026-04-29T23:55:57.390731
Workspace: My Simulator
Branch: master
Commit: b6af87dfed6131141b93a6d6d2647a28b6328a58

## Controller Handshake Files

- Handshake JSON: reports/agent_handshake_test_handshake.json
- Feedback Markdown: reports/agent_handshake_test_feedback.md
- Controller State JSON: reports/agent_handshake_test_state.json
- Current Prompt File: reports/agent_handshake_test_prompt.md

## Goal

Handshake test only. Do not modify repository files and do not start implementation work. Confirm that the controller prompt reached the CLI by replying with exactly one line: HANDSHAKE_OK repo=ams-simulator mode=controller.

## Validation Commands Already Run This Cycle

- PASS verify-project-status (log: reports/agent_cycles/cycle_0001_verify-project-status.log)

## Observations

- All queued validation/report commands exited cleanly in the latest cycle.
- Strict autopilot overall status: PASS.
- Chip catalog inventory: 15 reusable IPs, 6 VIPs, 3 digital subsystems, 5 chip profiles.
- generic130: 15/15 reusable IPs and 5/5 chip profiles are currently compatible.
- generic65: 11/15 reusable IPs and 3/5 chip profiles are currently compatible.
- bcd180: 15/15 reusable IPs and 5/5 chip profiles are currently compatible.
- Workflow focus: Validate script-to-CLI prompt handoff
- Workflow focus: Keep the external CLI response limited to a one-line acknowledgment
- Workflow focus: Do not modify repository files during this test

## Next Improvements To Implement

- Expand generic65 chip-profile support for: lin_node_asic, power_management_unit.
- Expand generic65 reusable IP support for: buck_converter, ldo_analog, ldo_lin, lin_transceiver.

## Agent Instructions

- Treat the script as the initiator. Continue from the latest handshake, feedback, and repo state instead of asking for a fresh prompt.
- Prioritize concrete repo changes that improve automation, chip assembly coverage, technology portability, or validation completeness.
- After making changes, rerun only the necessary repo commands or let the controller launch the next cycle.
- If you hit a token, context, or rate limit, stop cleanly after writing any useful partial progress. The controller will generate the next cycle prompt and continue.
- Use the current repo state as the source of truth. Do not assume a previous cycle fully completed unless the reports show it.
