# 05 - Verification Checklist

## Complete Verification Flow

### Per-Block Verification

For each block, complete all applicable checks:

#### Analog Blocks

| # | Check | Analysis | Pass Criteria | Status |
|---|-------|----------|---------------|--------|
| A1 | DC operating point | DC OP | All nodes in valid range | ☐ |
| A2 | Output voltage accuracy | DC OP | Within spec tolerance | ☐ |
| A3 | Supply current | DC OP | < max quiescent spec | ☐ |
| A4 | Line regulation | DC Sweep | < spec % over input range | ☐ |
| A5 | Load regulation | DC Sweep | < spec % over load range | ☐ |
| A6 | Gain / bandwidth | AC | Meets gain and BW spec | ☐ |
| A7 | Phase margin | AC | > 45° (preferably > 60°) | ☐ |
| A8 | PSRR | AC | > spec dB at key frequencies | ☐ |
| A9 | Startup transient | Transient | Settles within spec time | ☐ |
| A10 | Load step response | Transient | Undershoot/overshoot < spec | ☐ |

#### Digital Blocks

| # | Check | Method | Pass Criteria | Status |
|---|-------|--------|---------------|--------|
| D1 | Functional truth table | Simulation | All vectors pass | ☐ |
| D2 | Reset behavior | Simulation | Correct initial state | ☐ |
| D3 | Clock edge sensitivity | Simulation | Proper edge detection | ☐ |
| D4 | State machine coverage | Simulation | All states reached | ☐ |
| D5 | Protocol timing | Simulation | Meets protocol spec | ☐ |

### Top-Level Verification

| # | Check | Method | Pass Criteria | Status |
|---|-------|--------|---------------|--------|
| T1 | Power sequencing | Transient | Supplies come up in order | ☐ |
| T2 | Supply voltage accuracy | DC | All rails within ±5% | ☐ |
| T3 | Cross-domain signals | Mixed-signal | Clean transitions | ☐ |
| T4 | Current consumption | DC | Total < power budget | ☐ |
| T5 | Functional test | End-to-end | Protocol communicates | ☐ |

### Regression Report Format

After running full regression, generate report:

```markdown
# Regression Report - [Design Name]
Date: YYYY-MM-DD

## Summary
- Total blocks: N
- Blocks passing: M
- Blocks failing: K
- Coverage: M/N (XX%)

## Block Results
| Block | DC OP | AC | Transient | Overall |
|-------|-------|----|-----------|---------|
| bandgap | PASS | PASS | PASS | PASS |
| ldo_analog | PASS | N/A | PASS | PASS |
...
```

### Signoff Criteria

A design is ready for signoff when:
1. All blocks pass standalone verification (100%)
2. Top-level integration passes all checks
3. Power consumption within budget
4. No convergence warnings in any simulation
5. All specs met with margin
