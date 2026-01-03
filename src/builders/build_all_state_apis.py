#!/usr/bin/env python3
"""
Build API data structures for all states with complete scraped data.
Creates county caches and ZIP-to-plans mappings for each state.
"""
import json
import os
import csv
from pathlib import Path
from collections import defaultdict

# Directories
SCRAPED_JSON_DIR = Path('./scraped_json_all')
ZIP_COUNTY_DIR = Path('./zip_county_data')
STATE_DATA_DIR = Path('./state_data')
API_DIR = Path('./mock_api')
CSV_PATH = Path('./downloaded_data/CY2026_Landscape_202511/CY2026_Landscape_202511.csv')

# State name to abbreviation mapping
STATE_ABBREVS = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR',
    'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE',
    'District_of_Columbia': 'DC', 'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI',
    'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA',
    'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME',
    'Maryland': 'MD', 'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN',
    'Mississippi': 'MS', 'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE',
    'Nevada': 'NV', 'New_Hampshire': 'NH', 'New_Jersey': 'NJ', 'New_Mexico': 'NM',
    'New_York': 'NY', 'North_Carolina': 'NC', 'North_Dakota': 'ND', 'Ohio': 'OH',
    'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode_Island': 'RI',
    'South_Carolina': 'SC', 'South_Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX',
    'Utah': 'UT', 'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA',
    'West_Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY',
    'Puerto_Rico': 'PR', 'Virgin_Islands': 'VI', 'Guam': 'GU',
    'American_Samoa': 'AS', 'Northern_Mariana_Islands': 'MP'
}

# Region-based states (no counties, all ZIPs get all plans)
REGION_STATES = {'DC', 'GU', 'AS', 'MP', 'VI'}

def get_complete_states():
    """Find states with 100% scraped data."""
    scraped_files = os.listdir(SCRAPED_JSON_DIR)
    state_counts = defaultdict(int)
    
    for f in scraped_files:
        if f.endswith('.json') and '-' in f:
            state = f.split('-')[0]
            state_counts[state] += 1
    
    # Load expected counts
    complete = []
    for state_file in os.listdir(STATE_DATA_DIR):
        if not state_file.endswith('.json'):
            continue
        state = state_file.replace('.json', '')
        with open(STATE_DATA_DIR / state_file) as f:
            expected = len(json.load(f))
        
        actual = state_counts.get(state, 0)
        if actual >= expected and expected > 0:
            complete.append(state)
    
    return sorted(complete)

def load_plan_county_assignments():
    """Load which plans are available in which counties from CY2026 CSV."""
    plan_counties = defaultdict(set)  # plan_id -> set of county names
    plan_states = {}  # plan_id -> state
    
    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Use correct column names from CY2026 CSV
            plan_id = row.get('ContractPlanSegmentID', '').strip()
            county = row.get('County Name', '').strip()
            state = row.get('State Territory Name', '').replace(' ', '_')
            
            if not plan_id:
                continue
            
            plan_states[plan_id] = state
            
            if county == 'All Counties':
                plan_counties[plan_id].add('ALL_COUNTIES')
            else:
                plan_counties[plan_id].add(county)
    
    return plan_counties, plan_states

def load_scraped_plan_data(state):
    """Load all scraped JSON data for a state."""
    plans = {}
    prefix = f"{state}-"
    
    for f in os.listdir(SCRAPED_JSON_DIR):
        if f.startswith(prefix) and f.endswith('.json'):
            plan_id = f.replace(prefix, '').replace('.json', '')
            with open(SCRAPED_JSON_DIR / f) as fp:
                plans[plan_id] = json.load(fp)
    
    return plans

def load_zip_county_mapping(state_abbrev):
    """Load ZIP to county mapping for a state."""
    filepath = ZIP_COUNTY_DIR / f"{state_abbrev}_zip_county.json"
    if not filepath.exists():
        return None
    
    with open(filepath) as f:
        return json.load(f)

def load_fips_to_name():
    """Load FIPS to county name mapping."""
    with open('fips_to_county_name.json') as f:
        return json.load(f)

def build_state_api(state, plan_counties, plan_states, fips_to_name):
    """Build API data for a single state."""
    abbrev = STATE_ABBREVS.get(state)
    if not abbrev:
        print(f"  ⚠️ Unknown state: {state}")
        return False
    
    # Create state API directory
    state_api_dir = API_DIR / abbrev
    state_api_dir.mkdir(parents=True, exist_ok=True)
    
    # Load scraped plan data
    scraped_plans = load_scraped_plan_data(state)
    if not scraped_plans:
        print(f"  ⚠️ No scraped plans for {state}")
        return False
    
    # Load ZIP-county mapping
    zip_mapping = load_zip_county_mapping(abbrev)
    if not zip_mapping:
        print(f"  ⚠️ No ZIP mapping for {abbrev}")
        return False
    
    # Check if region-based (no counties)
    is_region = abbrev in REGION_STATES
    
    if is_region:
        return build_region_api(state, abbrev, scraped_plans, zip_mapping, state_api_dir)
    else:
        return build_county_api(state, abbrev, scraped_plans, zip_mapping, 
                                plan_counties, fips_to_name, state_api_dir)

def build_region_api(state, abbrev, scraped_plans, zip_mapping, state_api_dir):
    """Build API for region-based state (no counties)."""
    # All plans available to all ZIPs
    all_plans = list(scraped_plans.values())
    all_zips = [entry['zip'] for entry in zip_mapping]
    
    # Region cache (single region with all plans)
    region_cache = {
        'region': state.replace('_', ' '),
        'plans': all_plans
    }
    
    # ZIP to region mapping
    zip_to_region = {entry['zip']: state.replace('_', ' ') for entry in zip_mapping}
    
    # ZIP to plans (all ZIPs get all plans)
    zip_to_plans = {zip_code: list(scraped_plans.keys()) for zip_code in all_zips}
    
    # Save files
    with open(state_api_dir / 'region_cache.json', 'w') as f:
        json.dump(region_cache, f, indent=2)
    
    with open(state_api_dir / 'zip_to_region.json', 'w') as f:
        json.dump(zip_to_region, f, indent=2)
    
    with open(state_api_dir / 'zip_to_plans.json', 'w') as f:
        json.dump(zip_to_plans, f, indent=2)
    
    # API info
    api_info = {
        'state': state,
        'state_abbrev': abbrev,
        'type': 'region',
        'has_counties': False,
        'plan_count': len(scraped_plans),
        'zip_count': len(all_zips),
        'scraped_plans': len(scraped_plans)
    }
    
    with open(state_api_dir / 'api_info.json', 'w') as f:
        json.dump(api_info, f, indent=2)
    
    return True

def build_county_api(state, abbrev, scraped_plans, zip_mapping, plan_counties, fips_to_name, state_api_dir):
    """Build API for county-based state."""
    # Build FIPS to county name mapping for this state
    fips_to_county = {}
    for entry in zip_mapping:
        for county in entry['counties']:
            fips_to_county[county['fips']] = county.get('name', f"Unknown ({county['fips']})")
    
    # Get all unique counties in this state (full names from FIPS)
    all_counties = set(fips_to_county.values())
    
    # Build a mapping from short county names to full names
    # e.g., "Belknap" -> "Belknap County"
    short_to_full = {}
    for full_name in all_counties:
        # Remove common suffixes to create short name
        short_name = full_name
        for suffix in [' County', ' Parish', ' Borough', ' Census Area', ' Municipality', 
                       ' city', ' City and Borough', ' Planning Region']:
            if full_name.endswith(suffix):
                short_name = full_name[:-len(suffix)]
                break
        short_to_full[short_name] = full_name
        short_to_full[full_name] = full_name  # Also map full name to itself
    
    # Build county -> plans mapping
    county_plans = defaultdict(list)
    all_county_plans = []  # Plans available in all counties
    
    for plan_id, plan_data in scraped_plans.items():
        counties_for_plan = plan_counties.get(plan_id, set())
        
        if 'ALL_COUNTIES' in counties_for_plan:
            all_county_plans.append(plan_id)
        else:
            for county_name in counties_for_plan:
                # Try to match to full county name
                full_name = short_to_full.get(county_name, county_name)
                county_plans[full_name].append(plan_id)
    
    # Create counties directory
    counties_dir = state_api_dir / 'counties'
    counties_dir.mkdir(exist_ok=True)
    
    # Build county cache files
    county_count = 0
    for county_name in all_counties:
        # Get plans for this county
        plans_in_county = county_plans.get(county_name, []) + all_county_plans
        plans_in_county = list(set(plans_in_county))  # Dedupe
        
        if not plans_in_county:
            continue
        
        # Get full plan data
        county_plan_data = []
        for plan_id in plans_in_county:
            if plan_id in scraped_plans:
                plan_data = scraped_plans[plan_id].copy()
                plan_data['plan_id'] = plan_id
                county_plan_data.append(plan_data)
        
        if county_plan_data:
            # Clean county name for filename
            safe_name = county_name.replace(' ', '_').replace('/', '_')
            with open(counties_dir / f"{safe_name}.json", 'w') as f:
                json.dump(county_plan_data, f, indent=2)
            county_count += 1
    
    # Build ZIP to county mapping (multi-county aware)
    zip_to_county_multi = []
    for entry in zip_mapping:
        zip_entry = {
            'zip': entry['zip'],
            'multi_county': entry['multi_county'],
            'county_count': entry['county_count'],
            'primary_county': entry['primary_county'],
            'counties': entry['counties']
        }
        zip_to_county_multi.append(zip_entry)
    
    with open(state_api_dir / 'zip_to_county_multi.json', 'w') as f:
        json.dump(zip_to_county_multi, f, indent=2)
    
    # Build ZIP to plans mapping (for fast lookups)
    zip_to_plans = {}
    for entry in zip_mapping:
        zip_code = entry['zip']
        plans_for_zip = set(all_county_plans)  # Start with statewide plans
        
        for county in entry['counties']:
            county_name = county.get('name', '')
            plans_for_zip.update(county_plans.get(county_name, []))
        
        zip_to_plans[zip_code] = list(plans_for_zip)
    
    with open(state_api_dir / 'zip_to_plans.json', 'w') as f:
        json.dump(zip_to_plans, f, indent=2)
    
    # API info
    api_info = {
        'state': state,
        'state_abbrev': abbrev,
        'type': 'county',
        'has_counties': True,
        'plan_count': len(scraped_plans),
        'county_count': county_count,
        'zip_count': len(zip_mapping),
        'scraped_plans': len(scraped_plans)
    }
    
    with open(state_api_dir / 'api_info.json', 'w') as f:
        json.dump(api_info, f, indent=2)
    
    return True

def main():
    print("="*80)
    print("BUILDING API DATA FOR ALL COMPLETE STATES")
    print("="*80)
    print()
    
    # Get complete states
    complete_states = get_complete_states()
    print(f"Found {len(complete_states)} complete states:")
    for s in complete_states:
        abbrev = STATE_ABBREVS.get(s, '??')
        print(f"  - {s} ({abbrev})")
    print()
    
    # Load plan-county assignments from CSV
    print("Loading plan-county assignments from CY2026 CSV...")
    plan_counties, plan_states = load_plan_county_assignments()
    print(f"  Loaded {len(plan_counties)} plan assignments")
    print()
    
    # Load FIPS to name mapping
    fips_to_name = load_fips_to_name()
    
    # Build API for each state
    print("Building API data...")
    success = 0
    failed = []
    
    for state in complete_states:
        abbrev = STATE_ABBREVS.get(state, '??')
        print(f"  {state} ({abbrev})...", end=' ')
        
        if build_state_api(state, plan_counties, plan_states, fips_to_name):
            print("✅")
            success += 1
        else:
            print("❌")
            failed.append(state)
    
    print()
    print("="*80)
    print(f"COMPLETE!")
    print(f"  Success: {success}/{len(complete_states)}")
    if failed:
        print(f"  Failed: {failed}")
    print(f"  Output: {API_DIR}/")
    print("="*80)

if __name__ == '__main__':
    main()
