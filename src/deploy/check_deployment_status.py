#!/usr/bin/env python3
"""
Check which states are fully deployed and operational in the Medicare API
"""
import json
from pathlib import Path
from collections import defaultdict
import requests

print("="*80)
print("MEDICARE API - DEPLOYMENT STATUS BY STATE")
print("="*80)
print()

# 1. Check mock_api directory for states with data
print("📁 CHECKING MOCK API DATA")
print("-" * 80)

mock_api_dir = Path('mock_api')
states_in_mock = {}

for state_dir in sorted(mock_api_dir.iterdir()):
    if state_dir.is_dir() and state_dir.name not in ['.', '..', 'SC_old']:
        api_info_file = state_dir / 'api_info.json'
        if api_info_file.exists():
            with open(api_info_file) as f:
                info = json.load(f)
            states_in_mock[state_dir.name] = {
                'plans': info.get('total_plans', 0),
                'counties': info.get('total_counties', 0)
            }

print(f"States with mock API data: {len(states_in_mock)}")
print()

# 2. Check scraped data
print("📊 CHECKING SCRAPED DATA")
print("-" * 80)

scraped_dir = Path('scraped_json_all')
states_with_scraped = defaultdict(int)

if scraped_dir.exists():
    for json_file in scraped_dir.glob('*.json'):
        # Format: State_Name-PLAN_ID.json
        state_name = json_file.stem.rsplit('-', 1)[0]
        states_with_scraped[state_name] += 1

print(f"States with scraped plan data: {len(states_with_scraped)}")
print()

# 3. Check static_api directory
print("🏗️  CHECKING GENERATED API FILES")
print("-" * 80)

static_api_zip = Path('static_api/medicare/zip')
states_with_api = defaultdict(int)

if static_api_zip.exists():
    # Load ZIP to state mapping
    with open('unified_zip_to_fips.json') as f:
        zip_mapping = json.load(f)
    
    # Sample check: for each state, verify a few ZIP codes
    for state_abbrev in states_in_mock.keys():
        # Find ZIPs for this state
        state_zips = [z for z, info in zip_mapping.items() 
                      if state_abbrev in info.get('states', [])]
        
        if state_zips:
            # Check if first ZIP has an API file
            sample_zip = state_zips[0]
            api_file = static_api_zip / f'{sample_zip}.json'
            if api_file.exists():
                states_with_api[state_abbrev] = len(state_zips)
    
    print(f"States with generated API files: {len(states_with_api)}")
else:
    print("⚠️  static_api directory not found (may be gitignored)")

print()

# 4. Create comprehensive status table
print("📋 COMPREHENSIVE STATE STATUS")
print("="*80)
print()

# Combine all data
all_states = sorted(set(list(states_in_mock.keys()) + list(states_with_scraped.keys())))

# State name mappings for full names
state_names = {
    'AK': 'Alaska', 'AS': 'American Samoa', 'CA': 'California',
    'CT': 'Connecticut', 'DC': 'District of Columbia', 'DE': 'Delaware',
    'FL': 'Florida', 'GU': 'Guam', 'HI': 'Hawaii', 'IA': 'Iowa',
    'MD': 'Maryland', 'ME': 'Maine', 'MI': 'Michigan', 'MP': 'Northern Mariana Islands',
    'MT': 'Montana', 'NC': 'North Carolina', 'ND': 'North Dakota',
    'NE': 'Nebraska', 'NH': 'New Hampshire', 'NY': 'New York',
    'OR': 'Oregon', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'UT': 'Utah', 'VI': 'Virgin Islands',
    'VT': 'Vermont', 'WA': 'Washington', 'WV': 'West Virginia', 'WY': 'Wyoming'
}

# Map scraped data states to abbreviations
scraped_to_abbrev = {
    'South_Carolina': 'SC', 'South_Dakota': 'SD', 'West_Virginia': 'WV',
    'North_Carolina': 'NC', 'North_Dakota': 'ND', 'New_Hampshire': 'NH',
    'New_York': 'NY', 'Virgin_Islands': 'VI'
}

print(f"{'State':<25} {'Plans':<8} {'Counties':<10} {'ZIPs':<8} {'Status':<15}")
print("-" * 80)

for state in all_states:
    name = state_names.get(state, state)
    plans = states_in_mock.get(state, {}).get('plans', 0)
    counties = states_in_mock.get(state, {}).get('counties', 0)
    zips = states_with_api.get(state, 0)
    
    # Determine status
    if plans > 0 and zips > 0:
        status = "✅ Deployed"
    elif plans > 0:
        status = "⚠️  Ready to deploy"
    else:
        status = "❌ No data"
    
    print(f"{name:<25} {plans:<8} {counties:<10} {zips:<8} {status:<15}")

print()
print("="*80)

# Summary statistics
deployed = sum(1 for s in all_states if states_in_mock.get(s, {}).get('plans', 0) > 0 and states_with_api.get(s, 0) > 0)
ready = sum(1 for s in all_states if states_in_mock.get(s, {}).get('plans', 0) > 0 and states_with_api.get(s, 0) == 0)
no_data = len(all_states) - deployed - ready

print("SUMMARY:")
print("-" * 80)
print(f"✅ Deployed and operational: {deployed} states")
print(f"⚠️  Data ready, not deployed: {ready} states")
print(f"❌ No data: {no_data} states")
print()

total_plans = sum(states_in_mock.get(s, {}).get('plans', 0) for s in all_states)
total_zips = sum(states_with_api.get(s, 0) for s in all_states)

print(f"Total plans across all states: {total_plans}")
print(f"Total ZIP codes with API files: {total_zips}")
print()

print("="*80)
print("TESTING LIVE ENDPOINTS (Sample)")
print("="*80)
print()

# Test a few states
test_states = [
    ('SC', '29401', 'South Carolina - Charleston'),
    ('FL', '33101', 'Florida - Miami'),
    ('CA', '90001', 'California - Los Angeles'),
    ('NY', '10001', 'New York - Manhattan'),
    ('NC', '27601', 'North Carolina - Raleigh'),
]

for state_abbrev, zip_code, description in test_states:
    url = f'https://medicare.purlpal-api.com/medicare/zip/{zip_code}.json'
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ {description} ({zip_code}): {data.get('plan_count', 0)} plans")
        else:
            print(f"✗ {description} ({zip_code}): HTTP {response.status_code}")
    except Exception as e:
        print(f"✗ {description} ({zip_code}): {str(e)[:50]}")

print()
print("="*80)
