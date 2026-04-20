# Standard Circuit Test Report

**Date:** 2026-02-01 11:57:15

## Summary

- **Total Tests:** 7
- **Passed:** 1 (14.3%)
- **Failed:** 6 (85.7%)

## Test Results

### [FAIL] Buck Converter (12V to 5V)

- **File:** `buck_converter.spice`
- **Analysis:** transient
- **Status:** FAILED

**Expected Results:**

- `output`: 0.000 V (expected 5.000 ± 0.500 V)

**Errors:**

- output: 0.000 vs expected 5.000

### [FAIL] Boost Converter (5V to 12V)

- **File:** `boost_converter.spice`
- **Analysis:** transient
- **Status:** FAILED

**Expected Results:**

- `output`: 0.000 V (expected 12.000 ± 1.000 V)

**Errors:**

- output: 0.000 vs expected 12.000

### [FAIL] Buck-Boost Converter

- **File:** `buck_boost_converter.spice`
- **Analysis:** transient
- **Status:** FAILED

**Expected Results:**

- `output`: 0.000 V (expected -12.000 ± 1.500 V)

**Errors:**

- output: 0.000 vs expected -12.000

### [FAIL] LDO Regulator (3.3V)

- **File:** `ldo_regulator.spice`
- **Analysis:** dc
- **Status:** FAILED

**Expected Results:**

- `output`: N/A (expected 3.300 ± 0.100 V)

**Errors:**

- output: NaN result (simulation failed)

### [FAIL] Bandgap Reference (1.25V)

- **File:** `bandgap_reference.spice`
- **Analysis:** dc
- **Status:** FAILED

**Expected Results:**

- `output`: N/A (expected 1.250 ± 0.100 V)

**Errors:**

- output: NaN result (simulation failed)

### [FAIL] Differential Amplifier

- **File:** `differential_amplifier.spice`
- **Analysis:** transient
- **Status:** FAILED

**Expected Results:**

- `output`: N/A (expected 0.000 ± 0.500 V)

**Errors:**

- output: NaN result (simulation failed)

### [PASS] RC High-Pass Filter

- **File:** `rc_highpass.spice`
- **Analysis:** transient
- **Status:** PASSED

**Expected Results:**

- `output`: 0.000 V (expected 0.000 ± 0.100 V)

