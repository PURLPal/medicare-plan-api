#!/usr/bin/env python3
import csv
from collections import defaultdict

input_file = './CY2026_Landscape_202511/CY2026_Landscape_202511.csv'

maine_plans = []
unique_plan_ids = set()
counties = set()
plans_by_county = defaultdict(set)

with open(input_file, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['State Territory Name'] == 'Maine':
            maine_plans.append(row)
            plan_id = row['ContractPlanSegmentID']
            county = row['County Name']

            unique_plan_ids.add(plan_id)
            counties.add(county)
            plans_by_county[county].add(plan_id)

print(f"Total rows for Maine: {len(maine_plans)}")
print(f"Total unique ContractPlanSegmentIDs: {len(unique_plan_ids)}")
print(f"\nCounties in Maine data: {len(counties)}")
for county in sorted(counties):
    print(f"  - {county}: {len(plans_by_county[county])} plans")

# Check for "All Counties"
if "All Counties" in counties:
    all_counties_plans = plans_by_county["All Counties"]
    print(f"\nPlans marked as 'All Counties': {len(all_counties_plans)}")

    # Find plans that appear in specific counties too
    specific_county_plans = set()
    for county, plans in plans_by_county.items():
        if county != "All Counties":
            specific_county_plans.update(plans)

    print(f"Plans appearing in specific counties: {len(specific_county_plans)}")

    # Check overlap
    overlap = all_counties_plans & specific_county_plans
    only_all_counties = all_counties_plans - specific_county_plans
    only_specific = specific_county_plans - all_counties_plans

    print(f"\nPlans in both 'All Counties' AND specific counties: {len(overlap)}")
    print(f"Plans ONLY in 'All Counties': {len(only_all_counties)}")
    print(f"Plans ONLY in specific counties: {len(only_specific)}")

print(f"\n{'='*60}")
print(f"TOTAL UNIQUE PLANS IN MAINE: {len(unique_plan_ids)}")
print(f"{'='*60}")
