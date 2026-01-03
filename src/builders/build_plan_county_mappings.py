#!/usr/bin/env python3
"""
Extract plan-to-county mappings from CMS Landscape CSV.
This is the source of truth for which counties each plan serves.
"""
import csv
import json
from pathlib import Path
from collections import defaultdict

CSV_PATH = Path('downloaded_data/CY2026_Landscape_202511.csv')
OUTPUT_FILE = Path('plan_county_mappings.json')

def build_plan_county_mappings():
    """Extract which counties each plan serves from CMS data."""
    
    # plan_id -> {state, counties: set, all_counties: bool}
    plan_mappings = defaultdict(lambda: {
        'state': '',
        'state_abbrev': '',
        'plan_name': '',
        'plan_type': '',
        'category': '',
        'counties': set(),
        'all_counties': False
    })
    
    print("Reading CMS Landscape CSV...")
    
    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            plan_id = row.get('ContractPlanSegmentID', '').strip()
            county = row.get('County Name', '').strip()
            state = row.get('State Territory Name', '').strip()
            state_abbrev = row.get('State Territory Abbreviation', '').strip()
            plan_name = row.get('Plan Name', '').strip()
            plan_type = row.get('Plan Type', '').strip()
            category = row.get('Contract Category Type', '').strip()
            
            if not plan_id:
                continue
            
            # Store plan metadata
            if not plan_mappings[plan_id]['state']:
                plan_mappings[plan_id]['state'] = state
                plan_mappings[plan_id]['state_abbrev'] = state_abbrev
                plan_mappings[plan_id]['plan_name'] = plan_name
                plan_mappings[plan_id]['plan_type'] = plan_type
                plan_mappings[plan_id]['category'] = category
            
            # Check if this plan serves all counties
            if county == 'All Counties':
                plan_mappings[plan_id]['all_counties'] = True
            else:
                plan_mappings[plan_id]['counties'].add(county)
    
    # Convert sets to lists for JSON serialization
    result = {}
    for plan_id, data in plan_mappings.items():
        result[plan_id] = {
            'state': data['state'],
            'state_abbrev': data['state_abbrev'],
            'plan_name': data['plan_name'],
            'plan_type': data['plan_type'],
            'category': data['category'],
            'all_counties': data['all_counties'],
            'counties': sorted(list(data['counties']))
        }
    
    return result

def main():
    print("="*80)
    print("BUILDING PLAN-TO-COUNTY MAPPINGS FROM CMS DATA")
    print("="*80)
    print()
    
    mappings = build_plan_county_mappings()
    
    # Save mappings
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(mappings, f, indent=2)
    
    print(f"\n✅ Saved mappings for {len(mappings):,} plans")
    print(f"   Output: {OUTPUT_FILE}")
    
    # Statistics
    all_counties_count = sum(1 for p in mappings.values() if p['all_counties'])
    county_specific_count = len(mappings) - all_counties_count
    
    print(f"\n📊 Statistics:")
    print(f"   All Counties plans: {all_counties_count:,}")
    print(f"   County-specific plans: {county_specific_count:,}")
    
    # Show example
    print(f"\n📋 Example plan:")
    example_id = list(mappings.keys())[0]
    example = mappings[example_id]
    print(f"   Plan ID: {example_id}")
    print(f"   Name: {example['plan_name'][:60]}")
    print(f"   State: {example['state']}")
    print(f"   All Counties: {example['all_counties']}")
    if example['counties']:
        print(f"   Specific Counties: {', '.join(example['counties'][:3])}{'...' if len(example['counties']) > 3 else ''}")
    print()

if __name__ == '__main__':
    main()
