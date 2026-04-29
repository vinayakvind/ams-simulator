#!/usr/bin/env python
import json
import time

time.sleep(1)
data = json.load(open('reports/design_autopilot_latest.json'))
print('Overall:', data.get('overall'))
for d in data.get('designs', []):
    print(f'  - {d["id"]}: {d.get("overall")}')
