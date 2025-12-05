#!/usr/bin/env python3
import csv
import json
import os
from collections import defaultdict

input_file = './CY2026_Landscape_202511/CY2026_Landscape_202511.csv'
output_dir = './state_data'

# Ensure output directory exists
os.makedirs(output_dir, exist_ok=True)

# Read the CSV and organize by state
state_plans = defaultdict(dict)

with open(input_file, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)

    for row in reader:
        state = row['State Territory Name']
        contract_plan_segment_id = row['ContractPlanSegmentID']
        county = row['County Name']

        # If we haven't seen this ContractPlanSegmentID for this state, add it
        if contract_plan_segment_id not in state_plans[state]:
            # Generate URL by replacing underscore with dash
            # Format: 2026-H5521-296-0 from H5521_296_0
            url_path = contract_plan_segment_id.replace('_', '-')
            url = f"https://www.medicare.gov/plan-compare/#/plan-details/2026-{url_path}?year=2026&lang=en"

            # Check if this plan is marked as "All Counties"
            all_counties = (county == "All Counties")

            state_plans[state][contract_plan_segment_id] = {
                "State": row['State Territory Name'],
                "State Territory Abbreviation": row['State Territory Abbreviation'],
                "Contract Category Type": row['Contract Category Type'],
                "ContractPlanSegmentID": contract_plan_segment_id,
                "ContractPlanID": row['ContractPlanID'],
                "Segment ID": row['Segment ID'],
                "Parent Organization Name": row['Parent Organization Name'],
                "Contract Name": row['Contract Name'],
                "Organization Marketing Name": row['Organization Marketing Name'],
                "Organization Type": row['Organization Type'],
                "Plan Name": row['Plan Name'],
                "Plan Type": row['Plan Type'],
                "In-Network Maximum Out-of-Pocket (MOOP) Amount": row['In-Network Maximum Out-of-Pocket (MOOP) Amount'],
                "all_counties": all_counties,
                "url": url
            }
        else:
            # If we've seen this plan before, update all_counties if we find it marked as such
            if county == "All Counties":
                state_plans[state][contract_plan_segment_id]["all_counties"] = True

# Write one JSON file per state
for state, plans in sorted(state_plans.items()):
    # Create a safe filename from state name
    safe_state_name = state.replace(' ', '_').replace('/', '_')
    output_file = os.path.join(output_dir, f"{safe_state_name}.json")

    # Convert dict to list
    plans_list = list(plans.values())

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(plans_list, f, indent=2, ensure_ascii=False)

    print(f"{state:30} - {len(plans_list):4} unique ContractPlanSegmentIDs -> {safe_state_name}.json")

print(f"\n{'='*60}")
print(f"Complete! Created {len(state_plans)} state files in {output_dir}")
print(f"{'='*60}")
