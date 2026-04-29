#!/usr/bin/env python
import sys
sys.path.insert(0, '.')
from simulator.verification import run_design_snapshot

print('Running sigma_delta_adc design snapshot after deleting old file...')
try:
    result = run_design_snapshot('sigma_delta_adc')
    print('SUCCESS!')
    print(f'Overall: {result["summary"].get("overall")}')
    print(f'Checks passed: {sum(1 for c in result["summary"].get("checks", []) if c.get("status") == "PASS")}')
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
