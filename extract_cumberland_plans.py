#!/usr/bin/env python3
import csv
import json

input_file = './CY2026_Landscape_202511/CY2026_Landscape_202511.csv'
output_file = 'cumberland_county_maine_plans.json'

plans = []

with open(input_file, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['State Territory Name'] == 'Maine' and row['County Name'] == 'Cumberland':
            plans.append(row)

print(f"Found {len(plans)} plans for Cumberland County, Maine")

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(plans, f, indent=2, ensure_ascii=False)

print(f"Saved to {output_file}")
