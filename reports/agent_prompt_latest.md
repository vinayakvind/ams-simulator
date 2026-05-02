# Autonomous Agent Prompt

Cycle: 19
Generated: 2026-05-02T18:54:45.275303
Workspace: My Simulator
Branch: master
Commit: c7348523fdd72dc2c9572e318ed8f63b25c81722

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

## Observations

- All queued validation/report commands exited cleanly in the latest cycle.
- Strict autopilot overall status: PASS.
- Chip catalog inventory: 49 reusable IPs, 23 VIPs, 17 digital subsystems, 15 chip profiles.
- generic130: 49/49 reusable IPs and 15/15 chip profiles are currently compatible.
- generic65: 49/49 reusable IPs and 15/15 chip profiles are currently compatible.
- bcd180: 49/49 reusable IPs and 15/15 chip profiles are currently compatible.
- Workflow focus: Use the latest strict autopilot and chip-catalog reports to decide the next implementation batch.
- Workflow focus: Prefer improvements that expand reusable chip IP, VIP, and technology coverage.
- Workflow focus: Keep the workflow resumable so the next cycle continues cleanly after token or context limits.

## Next Improvements To Implement

- Expand the reusable chip library with additional IPs, VIPs, or technology-specific implementations so future cycles improve capability instead of only revalidating.

## Agent Instructions

- Treat the script as the initiator. Continue from the latest handshake, feedback, and repo state instead of asking for a fresh prompt.
- Prioritize concrete repo changes that improve automation, chip assembly coverage, technology portability, or validation completeness.
- After making changes, rerun only the necessary repo commands or let the controller launch the next cycle.
- If you hit a token, context, or rate limit, stop cleanly after writing any useful partial progress. The controller will generate the next cycle prompt and continue.
- Use the current repo state as the source of truth. Do not assume a previous cycle fully completed unless the reports show it.
