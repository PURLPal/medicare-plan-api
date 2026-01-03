#!/usr/bin/env python3
import csv
from collections import defaultdict

input_file = './CY2026_Landscape_202511/CY2026_Landscape_202511.csv'

# Track plans by ContractPlanID to see which have multiple segments
plans_by_contract_plan_id = defaultdict(list)

with open(input_file, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)

    for row in reader:
        contract_plan_id = row['ContractPlanID']
        segment_id = row['Segment ID']
        contract_plan_segment_id = row['ContractPlanSegmentID']

        # Store unique combinations
        key = (contract_plan_id, segment_id, contract_plan_segment_id)
        if key not in plans_by_contract_plan_id[contract_plan_id]:
            plans_by_contract_plan_id[contract_plan_id].append({
                'ContractPlanID': contract_plan_id,
                'Segment ID': segment_id,
                'ContractPlanSegmentID': contract_plan_segment_id,
                'State': row['State Territory Name'],
                'County': row['County Name'],
                'Plan Name': row['Plan Name'],
                'Plan Type': row['Plan Type'],
                'Part C Premium': row['Part C Premium'],
                'Part D Total Premium': row['Part D Total Premium'],
                'MOOP': row['In-Network Maximum Out-of-Pocket (MOOP) Amount']
            })

# Find plans with multiple segments
multi_segment_plans = {k: v for k, v in plans_by_contract_plan_id.items() if len(v) > 1}

print(f"Total ContractPlanIDs: {len(plans_by_contract_plan_id)}")
print(f"ContractPlanIDs with multiple segments: {len(multi_segment_plans)}")

# Show some examples
print("\n" + "="*80)
print("EXAMPLES OF PLANS WITH MULTIPLE SEGMENTS")
print("="*80)

count = 0
for contract_plan_id, segments in sorted(multi_segment_plans.items()):
    if count >= 5:  # Show first 5 examples
        break

    print(f"\nContractPlanID: {contract_plan_id}")
    print(f"State: {segments[0]['State']}")
    print(f"Plan Name: {segments[0]['Plan Name']}")
    print(f"Plan Type: {segments[0]['Plan Type']}")
    print(f"Number of segments: {len(segments)}\n")

    for seg in segments:
        print(f"  Segment {seg['Segment ID']}: {seg['ContractPlanSegmentID']}")
        print(f"    County: {seg['County']}")
        print(f"    Part C Premium: {seg['Part C Premium']}")
        print(f"    Part D Premium: {seg['Part D Total Premium']}")
        print(f"    MOOP: {seg['MOOP']}")
        print()

    count += 1

# Check Maine specifically
print("\n" + "="*80)
print("MAINE MULTI-SEGMENT PLANS")
print("="*80)

maine_multi_segment = 0
for contract_plan_id, segments in multi_segment_plans.items():
    if segments[0]['State'] == 'Maine':
        maine_multi_segment += 1
        print(f"\n{contract_plan_id}: {len(segments)} segments")
        for seg in segments:
            print(f"  {seg['ContractPlanSegmentID']} - Premium C: {seg['Part C Premium']}, D: {seg['Part D Total Premium']}")

print(f"\nMaine: {maine_multi_segment} ContractPlanIDs with multiple segments")
