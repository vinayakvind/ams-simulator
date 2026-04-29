# 06 - Design Reference Guide

## Purpose

Every design should leave behind one structured reference that captures:
- architecture intent
- block-level formulas and tuning knobs
- DC operating-point targets
- AC and PSRR verification steps
- corner-closure strategy
- debug workflow

This turns one successful design into a reusable template for the next one.

## Required Files

Each design should add:

```text
designs/<design_name>/
  design_reference.json      ← structured source of truth
reports/
  <design_name>_design_reference.html  ← generated webpage
```

## Manifest Structure

The `design_reference.json` file should capture:

1. `design`
   - chip name, standard, technology, narrative, signoff boundary
2. `architecture`
   - power domains, sequence, control path, partitioning
3. `indexed_flow`
   - ordered steps from spec capture through reference publication
4. `analysis_playbook`
   - DC, AC, PSRR, transient, and corner analysis commands
5. `corner_closure`
   - process/voltage/temperature matrix and pass rule
6. `script_index`
   - exact commands used to query, simulate, and render
7. `blocks`
   - one detailed section per block with formulas, operating points, analyses, files, and knobs
8. `debug_playbook`
   - triage order when a spec fails

## Retrieval Scripts

List all blocks:

```powershell
python designs/framework/scripts/query_design_reference.py \
  --input designs/lin_asic/design_reference.json --list-blocks
```

Show one block summary:

```powershell
python designs/framework/scripts/query_design_reference.py \
  --input designs/lin_asic/design_reference.json \
  --block ldo_analog --section summary
```

Show one block formulas:

```powershell
python designs/framework/scripts/query_design_reference.py \
  --input designs/lin_asic/design_reference.json \
  --block ldo_analog --section sizing_formulas
```

## Rendering the Webpage

```powershell
python designs/framework/scripts/generate_design_reference.py \
  --input designs/lin_asic/design_reference.json \
  --output reports/lin_asic_design_reference.html
```

## Analysis Commands

DC operating point:

```powershell
python designs/framework/scripts/simulate_block.py \
  --design lin_asic --block ldo_analog --analysis dc
```

AC loop-oriented inspection:

```powershell
python designs/framework/scripts/simulate_block.py \
  --design lin_asic --block ldo_analog --analysis ac \
  --fstart 10 --fstop 1e7 --points 60
```

PSRR:

```powershell
python designs/framework/scripts/simulate_block.py \
  --design lin_asic --block ldo_analog --analysis psrr \
  --fstart 10 --fstop 1e7 --points 60
```

Corner-aware run:

```powershell
python designs/framework/scripts/simulate_block.py \
  --design lin_asic --block ldo_analog --analysis dc \
  --corner FF --temperature 125
```

## Corner Methodology

Use the framework corner options for early closure and design tuning.
For tapeout signoff, replace the generic corner scalers with foundry `.LIB` or PDK corner decks.

Recommended closure order:

1. Close the bandgap first.
2. Freeze the reference and close each LDO at min/max load.
3. Check AC stability and PSRR before broad corner sweeps.
4. Sweep PVT corners and note which knob moved each failure back into spec.
5. Save those knobs and failure signatures into the manifest.

## Why This Matters

If the design knowledge stays only in reports or memory, the next design restarts from zero.
If the knowledge is indexed, queried, and rendered, the next design starts from a proven playbook.