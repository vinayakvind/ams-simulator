#!/usr/bin/env python
import json

data = json.load(open('reports/design_autopilot_latest.json'))
print('Overall:', data.get('overall'))
print('Designs:')
for d in data.get('designs', []):
    print(f'  - {d["id"]}: {d.get("overall")}')
