#!/usr/bin/env python3
"""
Build ZIP to plans mapping for South Carolina.
Maps each SC ZIP code to the list of plan IDs available in that ZIP.
"""
import json
import csv
from pathlib import Path
from collections import defaultdict

# Files
UNIFIED_ZIP_FILE = Path('./unified_zip_to_fips.json')
CSV_PATH = Path('./downloaded_data/CY2026_Landscape_202511/CY2026_Landscape_202511.csv')
SCRAPED_DIR = Path('./scraped_json_all')
OUTPUT_FILE = Path('./mock_api/South_Carolina/zip_to_plans.json')

# Load FIPS to county name mapping from CSV
def load_fips_county_map():
    """Map FIPS codes to county names for South Carolina."""
    fips_to_county = {}
    
    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            state = row.get('State Territory Name', '')
            if state != 'South Carolina':
                continue
            
            county = row.get('County Name', '').strip()
            # Note: CSV doesn't have FIPS directly, we'll use county name
            if county:
                # Create a simple mapping - in practice we'd need actual FIPS
                # but for now we'll just use county names
                fips_to_county[county] = county
    
    return fips_to_county

# Load which plans serve which counties
def load_county_plans():
    """Map county names to plan IDs for South Carolina."""
    county_plans = defaultdict(set)
    
    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            state = row.get('State Territory Name', '')
            if state != 'South Carolina':
                continue
            
            county = row.get('County Name', '').strip()
            plan_id = row.get('ContractPlanSegmentID', '').strip()
            
            if county and plan_id:
                county_plans[county].add(plan_id)
    
    return county_plans

# Load our scraped plan IDs
def load_scraped_plans():
    """Get set of plan IDs we have scraped."""
    scraped = set()
    
    for f in SCRAPED_DIR.glob('South_Carolina-*.json'):
        with open(f) as fp:
            data = json.load(fp)
        plan_id = data.get('plan_id', '')
        if plan_id:
            scraped.add(plan_id)
    
    return scraped

def main():
    print("=== Building SC ZIP to Plans Mapping ===\n")
    
    # Load unified ZIP mapping
    with open(UNIFIED_ZIP_FILE) as f:
        unified_zip = json.load(f)
    
    # Get all SC ZIPs
    sc_zips = {}
    for zip_code, zip_info in unified_zip.items():
        states = zip_info.get('states', [])
        if 'SC' in states:
            sc_zips[zip_code] = zip_info
    
    print(f"Found {len(sc_zips)} ZIP codes in South Carolina")
    
    # Load county to plans mapping
    county_plans = load_county_plans()
    print(f"Found {len(county_plans)} counties with plans")
    
    # Load our scraped plans
    scraped_plans = load_scraped_plans()
    print(f"We have {len(scraped_plans)} scraped SC plans")
    
    # Build ZIP to plans mapping
    zip_to_plans = {}
    
    for zip_code, zip_info in sc_zips.items():
        plans_for_zip = set()
        
        # Get all counties for this ZIP
        counties = zip_info.get('counties', [])
        
        for county_info in counties:
            county_name = county_info.get('name', '')
            
            # Strip " County" suffix to match CSV format
            county_name_short = county_name.replace(' County', '')
            
            # Get plans for this county (try both full and short name)
            plans = county_plans.get(county_name, set()) | county_plans.get(county_name_short, set())
            
            # Only include plans we have scraped
            for plan_id in plans:
                if plan_id in scraped_plans:
                    plans_for_zip.add(plan_id)
        
        # Convert to list for JSON
        if plans_for_zip:
            zip_to_plans[zip_code] = sorted(list(plans_for_zip))
    
    print(f"\n=== Results ===")
    print(f"ZIPs with plans: {len(zip_to_plans)}")
    
    # Check ZIP 29401 specifically
    if '29401' in zip_to_plans:
        print(f"\n✓ ZIP 29401: {len(zip_to_plans['29401'])} plans")
        print(f"  Sample plans: {zip_to_plans['29401'][:5]}")
        
        # Check priority plans
        priority = ['H5322_043_0', 'H5322_044_0', 'R2604_005_0']
        print(f"\n  Priority plans in 29401:")
        for p in priority:
            found = p in zip_to_plans['29401']
            print(f"    {'✓' if found else '✗'} {p}")
    else:
        print(f"\n✗ ZIP 29401 not in mapping")
    
    # Save
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(zip_to_plans, f, indent=2)
    
    print(f"\n✓ Saved to {OUTPUT_FILE}")

if __name__ == '__main__':
    main()
