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

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/create_design.py` | Create new design directory with all templates |
| `scripts/simulate_block.py` | Simulate a single block (DC, AC, Transient) |
| `scripts/verify_block.py` | Verify block results against spec |
| `scripts/run_regression.py` | Run full regression across all blocks |

## Operational Automation

| Script | Purpose |
|--------|---------|
| `../../scripts/copilot_cli_watchdog.py` | Supervise long-running Copilot CLI or agent commands, restart on stop/stall, gate on premium threshold |
| `../../scripts/repo_backup_guard.py` | Detect major repository changes and auto-commit/push backup snapshots |

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
```

## Quick Start
```bash
# Create a new design
python designs/framework/scripts/create_design.py --name my_chip --tech generic180

# Simulate a block
python designs/framework/scripts/simulate_block.py --design my_chip --block bandgap --analysis dc

# Verify all blocks
python designs/framework/scripts/verify_block.py --design my_chip --all

# Full regression
python designs/framework/scripts/run_regression.py --design my_chip
```
