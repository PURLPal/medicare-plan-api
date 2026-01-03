#!/usr/bin/env python3
import csv
import json
from collections import defaultdict

input_file = './CY2026_Landscape_202511/CY2026_Landscape_202511.csv'
output_file = './data_analysis/state_plans_analysis.json'

state_data = {}

# Read the CSV and organize by state
with open(input_file, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)

    state_rows = defaultdict(list)

    for row in reader:
        state = row['State Territory Name']
        state_rows[state].append(row)

# Analyze each state
for state, rows in sorted(state_rows.items()):
    unique_plan_ids = set()
    counties = set()
    plans_by_county = defaultdict(set)

    for row in rows:
        plan_id = row['ContractPlanSegmentID']
        county = row['County Name']

        unique_plan_ids.add(plan_id)
        counties.add(county)
        plans_by_county[county].add(plan_id)

    # Calculate metrics
    all_counties_plans = plans_by_county.get("All Counties", set())

    specific_county_plans = set()
    for county, plans in plans_by_county.items():
        if county != "All Counties":
            specific_county_plans.update(plans)

    # Count actual counties (excluding "All Counties" if present)
    actual_county_count = len(counties) - (1 if "All Counties" in counties else 0)

    state_data[state] = {
        "total_unique_plans": len(unique_plan_ids),
        "total_rows": len(rows),
        "total_counties_in_data": len(counties),
        "actual_county_count": actual_county_count,
        "plans_marked_all_counties": len(all_counties_plans),
        "plans_in_specific_counties_only": len(specific_county_plans),
        "counties": sorted(list(counties))
    }

    print(f"Processed {state}: {len(unique_plan_ids)} unique plans")

# Write to JSON
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(state_data, f, indent=2, ensure_ascii=False)

print(f"\n{'='*60}")
print(f"Analysis complete!")
print(f"Analyzed {len(state_data)} states/territories")
print(f"Output saved to: {output_file}")
print(f"{'='*60}")
