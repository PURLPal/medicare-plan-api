#!/usr/bin/env python3
"""
Verify data quality by sampling one plan from each state/territory
"""
import json
from pathlib import Path
from collections import defaultdict

json_dir = Path('scraped_data/json')

# Group files by state
states_data = defaultdict(list)
for file in json_dir.rglob('*.json'):
    state = file.parent.name
    states_data[state].append(file)

print(f"=== Sampling 1 Plan Per State/Territory ===")
print(f"Total states: {len(states_data)}\n")

valid_count = 0
missing_fields = []
field_stats = defaultdict(int)

for state in sorted(states_data.keys()):
    # Sample one file from this state
    file = states_data[state][0]
    
    try:
        with open(file) as f:
            data = json.load(f)
        
        # Check key fields
        has_name = 'plan_info' in data and 'name' in data.get('plan_info', {})
        has_premium = 'premiums' in data
        has_deductibles = 'deductibles' in data
        has_benefits = 'benefits' in data
        has_drug_coverage = 'drug_coverage' in data
        
        # Count field presence
        if has_name:
            field_stats['plan_name'] += 1
        if has_premium:
            field_stats['premiums'] += 1
        if has_deductibles:
            field_stats['deductibles'] += 1
        if has_benefits:
            field_stats['benefits'] += 1
        if has_drug_coverage:
            field_stats['drug_coverage'] += 1
        
        # Validate
        if has_name and has_premium:
            valid_count += 1
            plan_name = data.get('plan_info', {}).get('name', 'N/A')
            premium = data.get('premiums', {}).get('Total monthly premium', 'N/A')
            print(f"✅ {state:20s} | {plan_name[:40]:40s} | {premium}")
        else:
            missing = []
            if not has_name:
                missing.append('name')
            if not has_premium:
                missing.append('premium')
            missing_fields.append((state, missing))
            print(f"⚠️  {state:20s} | Missing: {', '.join(missing)}")
            
    except Exception as e:
        print(f"❌ {state:20s} | ERROR: {str(e)[:40]}")

print(f"\n=== Summary ===")
print(f"States validated: {valid_count}/{len(states_data)} ({valid_count/len(states_data)*100:.1f}%)")

print(f"\nField coverage across all {len(states_data)} states:")
for field, count in sorted(field_stats.items()):
    pct = count / len(states_data) * 100
    print(f"  {field:20s}: {count}/{len(states_data)} ({pct:.0f}%)")

if missing_fields:
    print(f"\n⚠️  States with missing fields:")
    for state, fields in missing_fields:
        print(f"  - {state}: {', '.join(fields)}")
else:
    print(f"\n🎉 All {len(states_data)} states have complete data structure!")
