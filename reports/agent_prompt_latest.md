# Autonomous Agent Prompt

Cycle: 5
Generated: 2026-04-30T00:49:52.081348
Workspace: My Simulator
Branch: master
Commit: b6af87dfed6131141b93a6d6d2647a28b6328a58

## Controller Handshake Files

- Handshake JSON: reports/agent_handshake_latest.json
- Feedback Markdown: reports/agent_feedback_latest.md
- Controller State JSON: reports/agent_controller_state.json
- Current Prompt File: reports/agent_prompt_latest.md

## Goal

Run validation and reporting, then feed the next concrete improvement batch back into the CLI agent without needing a fresh manual prompt.

## Validation Commands Already Run This Cycle

- PASS verify-project-status (log: reports/agent_cycles/cycle_0005_verify-project-status.log)
- PASS generate-chip-catalog-all (log: reports/agent_cycles/cycle_0005_generate-chip-catalog-all.log)
- PASS generate-chip-catalog-generic130 (log: reports/agent_cycles/cycle_0005_generate-chip-catalog-generic130.log)
- PASS generate-chip-catalog-generic65 (log: reports/agent_cycles/cycle_0005_generate-chip-catalog-generic65.log)
- PASS generate-chip-catalog-bcd180 (log: reports/agent_cycles/cycle_0005_generate-chip-catalog-bcd180.log)
- PASS run-strict-autopilot (log: reports/agent_cycles/cycle_0005_run-strict-autopilot.log)
- PASS repo-backup-report (log: reports/agent_cycles/cycle_0005_repo-backup-report.log)

## Observations

- All queued validation/report commands exited cleanly in the latest cycle.
- Strict autopilot overall status: PASS.
- Chip catalog inventory: 15 reusable IPs, 6 VIPs, 3 digital subsystems, 5 chip profiles.
- generic130: 15/15 reusable IPs and 5/5 chip profiles are currently compatible.
- generic65: 15/15 reusable IPs and 5/5 chip profiles are currently compatible.
- bcd180: 15/15 reusable IPs and 5/5 chip profiles are currently compatible.
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
