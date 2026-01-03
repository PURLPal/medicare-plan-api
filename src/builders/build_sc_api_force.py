#!/usr/bin/env python3
"""
Force build South Carolina API even though not 100% complete.
This will build the API for the 71 plans we have scraped.
"""
import json
import csv
import os
from pathlib import Path
from collections import defaultdict

# Directories
SCRAPED_JSON_DIR = Path('./scraped_json_all')
OUTPUT_DIR = Path('./mock_api')
STATE_DATA_DIR = Path('./state_data')
CSV_PATH = Path('./downloaded_data/CY2026_Landscape_202511/CY2026_Landscape_202511.csv')

def load_plan_county_assignments():
    """Load which plans are available in which counties from CY2026 CSV."""
    plan_counties = defaultdict(set)
    plan_states = {}
    
    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            plan_id = row.get('ContractPlanSegmentID', '').strip()
            county = row.get('County Name', '').strip()
            state = row.get('State Territory Name', '').replace(' ', '_')
            
            if not plan_id:
                continue
            
            plan_counties[plan_id].add(county)
            plan_states[plan_id] = state
    
    return plan_counties, plan_states

def build_state(state_name):
    """Build API for a single state."""
    print(f"\n=== Building {state_name} ===")
    
    # Load scraped plans
    plans = {}
    for f in SCRAPED_JSON_DIR.glob(f'{state_name}-*.json'):
        with open(f) as fp:
            plan = json.load(fp)
        plan_id = plan.get('plan_id', '')
        if plan_id:
            plans[plan_id] = plan
    
    print(f"  Loaded {len(plans)} scraped plans")
    
    # Load county assignments
    plan_counties, plan_states = load_plan_county_assignments()
    
    # Group plans by county
    county_plans = defaultdict(list)
    counties_seen = set()
    zip_to_plans = defaultdict(list)
    
    for plan_id, plan in plans.items():
        # Get counties this plan serves
        counties = plan_counties.get(plan_id, set())
        
        for county in counties:
            county_plans[county].append(plan)
            counties_seen.add(county)
    
    print(f"  Plans serve {len(counties_seen)} counties")
    
    # Create output directory
    state_dir = OUTPUT_DIR / state_name
    state_dir.mkdir(parents=True, exist_ok=True)
    
    # Write API info
    api_info = {
        'state': state_name,
        'total_plans': len(plans),
        'total_counties': len(counties_seen),
        'counties': sorted(list(counties_seen))
    }
    
    with open(state_dir / 'api_info.json', 'w') as f:
        json.dump(api_info, f, indent=2)
    
    # Write county files
    county_dir = state_dir / 'counties'
    county_dir.mkdir(exist_ok=True)
    
    for county, county_plan_list in county_plans.items():
        county_file = county_dir / f'{county.replace(" ", "_")}.json'
        with open(county_file, 'w') as f:
            json.dump(county_plan_list, f, indent=2)
    
    print(f"  ✓ Wrote {len(county_plans)} county files")
    
    # Build ZIP to plans mapping from CSV
    # This maps each ZIP code to the list of plan IDs available in that ZIP
    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            state = row.get('State Territory Name', '').replace(' ', '_')
            if state != state_name:
                continue
            
            # Note: The CY2026 CSV doesn't have ZIP codes directly
            # It has counties. We'll need to rely on the unified_zip_to_fips
            # mapping to connect ZIPs to counties to plans
            
            plan_id = row.get('ContractPlanSegmentID', '').strip()
            county = row.get('County Name', '').strip()
            
            # For now, save county-level data
            # The build_static_api.py will handle ZIP resolution
    
    # Create a simple zip_to_plans.json for counties we have
    # The actual ZIP resolution will be done by build_static_api.py
    # using the unified_zip_to_fips.json file
    
    with open(state_dir / 'zip_to_plans.json', 'w') as f:
        json.dump({}, f, indent=2)  # Empty for now, let build_static_api resolve
    
    print(f"  ✓ Complete!\n")
    
    return len(plans)

def main():
    print("="*80)
    print("FORCE BUILDING SOUTH CAROLINA API")
    print("="*80)
    
    state = 'South_Carolina'
    plan_count = build_state(state)
    
    print("\n" + "="*80)
    print(f"BUILD COMPLETE: {plan_count} plans")
    print(f"Output: mock_api/{state}/")
    print("="*80)
    print("\nNext step: Run build_static_api.py to generate final ZIP files")

if __name__ == '__main__':
    main()
