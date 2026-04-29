# AMS Design Framework - Master Index

## Overview
Structured framework for designing any mixed-signal ASIC architecture.
Each design follows an indexed, step-by-step flow from architecture to signoff.

## Framework Structure

| Index | Document | Purpose |
|-------|----------|---------|
| 00 | `00_INDEX.md` | This file - master navigation |
| 01 | `01_ARCHITECTURE_TEMPLATE.md` | Define chip architecture, block list, connectivity |
| 02 | `02_BLOCK_DESIGN_GUIDE.md` | Design individual analog/digital blocks |
| 03 | `03_SIMULATION_GUIDE.md` | Simulate and verify each block standalone |
| 04 | `04_INTEGRATION_GUIDE.md` | Integrate blocks into chip top-level |
| 05 | `05_VERIFICATION_CHECKLIST.md` | Full verification checklist with pass/fail |
| 06 | `06_DESIGN_REFERENCE_GUIDE.md` | Build a reusable indexed design-reference manifest and webpage |

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/create_design.py` | Create new design directory with all templates |
| `scripts/simulate_block.py` | Simulate a single block (DC, AC, Transient) |
| `scripts/verify_block.py` | Verify block results against spec |
| `scripts/run_regression.py` | Run full regression across all blocks |
| `scripts/query_design_reference.py` | Retrieve indexed methodology data for one design or block |
| `scripts/generate_design_reference.py` | Render the design-reference manifest into a standalone HTML page |
| `scripts/run_design_snapshot.py` | Run a top-level design snapshot from block spec verification settings |
| `scripts/generate_portfolio_presentation.py` | Create JSON, Markdown, and PPT portfolio summaries across indexed designs |
| `scripts/run_autopilot.py` | Execute the full indexed design flow end to end: regressions, snapshots, HTML pages, portfolio outputs, and validation |
| `scripts/generate_chip_catalog_report.py` | Create JSON and Markdown reports for supported technologies, reusable IPs, VIPs, digital subsystems, and chip assembly profiles |

## Operational Automation

| Script | Purpose |
|--------|---------|
| `../../scripts/copilot_cli_watchdog.py` | Supervise long-running Copilot CLI or agent commands, restart on stop/stall, gate on premium threshold |
| `../../scripts/repo_backup_guard.py` | Detect major repository changes and auto-commit/push backup snapshots |
| `../../scripts/verify_project_status.py` | Verify that key deliverables exist, repo is synced, and the API smoke test passes |
| `../../scripts/agent_cli_controller.py` | Script-driven agent controller: handshake, queued CLI steps, feedback generation, prompt handoff, and resumable continuation |
| `../../scripts/start_agent_cli_daemon.ps1` | Launch the controller in watch mode so it can keep running when the laptop is on |
| `../../scripts/install_agent_startup.ps1` | Register a Windows scheduled task so the controller starts automatically on login or startup |

## Templates

| Template | Purpose |
|----------|---------|
| `templates/block_spec.yaml` | Block specification template |
| `templates/testbench.spice` | Testbench template for any block |
| `templates/block_report.md` | Block report template |

## Design Flow

```
1. Create Architecture (01) → Define blocks, pins, connectivity
2. Design Blocks (02)       → Use BlockBuilder or custom SPICE
3. Simulate Blocks (03)     → DC/AC/Transient per block
4. Integrate (04)           → Connect blocks at top-level 
5. Verify (05)              → Regression, specs check, signoff
6. Publish Reference (06)   → Save architecture, formulas, knobs, and debug flow into one indexed webpage
```

## Quick Start
```bash
# Create a new design
python designs/framework/scripts/create_design.py --name my_chip --tech generic180

# Create a full chip scaffold from the integrated IP/VIP catalog
python designs/framework/scripts/create_design.py --name my_lin_chip --profile lin_node_asic --tech generic180

# Inspect the reusable chip catalog inventory
python designs/framework/scripts/create_design.py --list-profiles
python designs/framework/scripts/create_design.py --list-ips
python designs/framework/scripts/create_design.py --list-vips

# Simulate a block
python designs/framework/scripts/simulate_block.py --design my_chip --block bandgap --analysis dc

# Verify all blocks
python designs/framework/scripts/verify_block.py --design my_chip --all

# Full regression
python designs/framework/scripts/run_regression.py --design my_chip

# Query indexed design knowledge
python designs/framework/scripts/query_design_reference.py \
	--input designs/my_chip/design_reference.json --list-blocks

# Run one top-level design snapshot using spec.yaml verification settings
python designs/framework/scripts/run_design_snapshot.py --design my_chip --block top_level

# Render standalone webpage
python designs/framework/scripts/generate_design_reference.py \
	--input designs/my_chip/design_reference.json \
	--output reports/my_chip_design_reference.html

# Create the cross-design portfolio PPT / architecture summary
python designs/framework/scripts/generate_portfolio_presentation.py

# Run the full indexed design autopilot flow
python designs/framework/scripts/run_autopilot.py

# CI-style autopilot: non-zero unless every design is PASS
python designs/framework/scripts/run_autopilot.py --strict

# Generate a reusable chip-catalog report for one technology
python designs/framework/scripts/generate_chip_catalog_report.py --technology generic130

# Run the script-driven controller once to generate handshake, feedback, and next-agent prompt files
python scripts/agent_cli_controller.py
```
