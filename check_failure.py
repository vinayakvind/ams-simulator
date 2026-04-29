#!/usr/bin/env python
import json

data = json.load(open('reports/design_autopilot_latest.json'))
for d in data.get('designs', []):
    if d.get('overall') == 'FAIL':
        print(f"Failed design: {d['id']}")
        print(f"Error: {d.get('error')}")
        print(f"Artifact checks:")
        for check in d.get('artifact_checks', []):
            print(f"  - {check['path']}: exists={check.get('exists')}, size={check.get('size_bytes')}")
