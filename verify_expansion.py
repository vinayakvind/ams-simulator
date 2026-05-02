#!/usr/bin/env python3
import json

for tech in ['generic130', 'generic65', 'bcd180']:
    with open(f'reports/chip_catalog_{tech}_latest.json') as f:
        data = json.load(f)
        print(f'{tech}: {len(data["reusable_ips"])} IPs, {len(data["verification_ips"])} VIPs, {len(data["digital_subsystems"])} subsystems, {len(data["chip_profiles"])} profiles')
