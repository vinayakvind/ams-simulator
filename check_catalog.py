import json
from pathlib import Path

reports_dir = Path("reports")
for tech in ["generic65", "generic130", "bcd180"]:
    catalog_file = reports_dir / f"chip_catalog_{tech}_latest.json"
    if catalog_file.exists():
        data = json.load(open(catalog_file))
        summary = data["summary"]
        print(f"{tech}: {summary['compatible_ip_count']}/{summary['reusable_ip_count']} IPs, {summary['compatible_chip_profile_count']}/{summary['chip_profile_count']} profiles")
