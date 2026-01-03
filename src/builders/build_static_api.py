#!/usr/bin/env python3
"""
Build static JSON API files for S3 + CloudFront deployment.

Generates:
- /zip/{zip_code}.json - Plans for each ZIP code
- /state/{ST}/info.json - State info
- /state/{ST}/plans.json - All plans in state  
- /plan/{plan_id}.json - Individual plan details
- /states.json - Index of all states

Output directory: ./static_api/medicare/
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

# CMS Contract Category Type to Sunfire category mapping
CMS_CATEGORY_TO_SUNFIRE = {
    'MA-PD': 'MAPD',  # Medicare Advantage with Part D
    'SNP': 'MAPD',    # Special Needs Plans (typically have Part D)
    'MA': 'MA',       # Medicare Advantage only
    'PDP': 'PD',      # Prescription Drug Plan only
}

def extract_plan_type(plan_name):
    """Extract network type (HMO, PPO, PDP, etc.) from plan name."""
    if not plan_name:
        return None
    match = re.search(r'\(([^)]+)\)\s*$', plan_name)
    if match:
        return match.group(1)
    return None

def get_plan_category_from_cms(cms_category):
    """Convert CMS Contract Category Type to Sunfire category."""
    return CMS_CATEGORY_TO_SUNFIRE.get(cms_category, 'MAPD')  # Default to MAPD if unknown

def load_cms_categories_for_state(state_abbrev):
    """Load CMS category data from state_data files."""
    # Map state abbreviation back to state name
    state_name_map = {
        'AK': 'Alaska', 'AL': 'Alabama', 'AR': 'Arkansas', 'AZ': 'Arizona',
        'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
        'DC': 'District_of_Columbia', 'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii',
        'IA': 'Iowa', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana',
        'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'MA': 'Massachusetts',
        'MD': 'Maryland', 'ME': 'Maine', 'MI': 'Michigan', 'MN': 'Minnesota',
        'MO': 'Missouri', 'MS': 'Mississippi', 'MT': 'Montana', 'NC': 'North_Carolina',
        'ND': 'North_Dakota', 'NE': 'Nebraska', 'NH': 'New_Hampshire', 'NJ': 'New_Jersey',
        'NM': 'New_Mexico', 'NV': 'Nevada', 'NY': 'New_York', 'OH': 'Ohio',
        'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode_Island',
        'SC': 'South_Carolina', 'SD': 'South_Dakota', 'TN': 'Tennessee', 'TX': 'Texas',
        'UT': 'Utah', 'VA': 'Virginia', 'VT': 'Vermont', 'WA': 'Washington',
        'WI': 'Wisconsin', 'WV': 'West_Virginia', 'WY': 'Wyoming',
        'AS': 'American_Samoa', 'GU': 'Guam', 'MP': 'Northern_Mariana_Islands',
        'PR': 'Puerto_Rico', 'VI': 'Virgin_Islands'
    }
    
    state_name = state_name_map.get(state_abbrev)
    if not state_name:
        return {}
    
    state_file = Path(f'./state_data/{state_name}.json')
    if not state_file.exists():
        return {}
    
    with open(state_file) as f:
        state_plans = json.load(f)
    
    # Create plan_id -> category mapping
    categories = {}
    for plan in state_plans:
        plan_id = plan.get('ContractPlanSegmentID', '')
        cms_category = plan.get('Contract Category Type', '')
        if plan_id and cms_category:
            categories[plan_id] = get_plan_category_from_cms(cms_category)
    
    return categories

# Directories
OUTPUT_DIR = Path('./static_api/medicare')
UNIFIED_ZIP_FILE = Path('./unified_zip_to_fips.json')
MOCK_API_DIR = Path('./mock_api')
SCRAPED_JSON_DIR = Path('./scraped_json_all')

# Skip territories, focus on states
TERRITORIES = {'AS', 'GU', 'MP', 'PR', 'VI'}

def load_unified_zip_mapping():
    """Load the unified ZIP to FIPS mapping."""
    with open(UNIFIED_ZIP_FILE) as f:
        return json.load(f)

def load_state_data():
    """Load all state API data."""
    states = {}
    
    for state_dir in MOCK_API_DIR.iterdir():
        if not state_dir.is_dir():
            continue
        
        state_abbrev = state_dir.name
        info_file = state_dir / 'api_info.json'
        
        if not info_file.exists():
            continue
        
        with open(info_file) as f:
            info = json.load(f)
        
        # Load plans
        plans = {}
        county_dir = state_dir / 'counties'
        if county_dir.exists():
            for county_file in county_dir.glob('*.json'):
                with open(county_file) as f:
                    county_plans = json.load(f)
                    for plan in county_plans:
                        if isinstance(plan, dict):
                            plan_id = plan.get('plan_id') or plan.get('plan_info', {}).get('id', '')
                            plan_id = plan_id.replace('-', '_')
                            if plan_id:
                                plans[plan_id] = plan
        
        # Load ZIP mapping
        zip_file = state_dir / 'zip_to_plans.json'
        zip_to_plans = {}
        if zip_file.exists():
            with open(zip_file) as f:
                zip_to_plans = json.load(f)
        
        states[state_abbrev] = {
            'info': info,
            'plans': plans,
            'zip_to_plans': zip_to_plans
        }
        
        print(f"  Loaded {state_abbrev}: {len(plans)} plans")
    
    return states

def get_plan_summary(plan):
    """Extract summary from a plan."""
    plan_info = plan.get('plan_info', {})
    # Handle case where plan_info is a list instead of dict
    if isinstance(plan_info, list):
        plan_info = {'name': plan_info[0] if plan_info else ''}
    premiums = plan.get('premiums', {})
    deductibles = plan.get('deductibles', {})
    moop = plan.get('maximum_out_of_pocket', {})
    
    return {
        'plan_id': plan.get('plan_id', ''),
        'plan_name': plan_info.get('name', '') if isinstance(plan_info, dict) else '',
        'organization': plan_info.get('organization', '') if isinstance(plan_info, dict) else '',
        'type': plan_info.get('type', '') if isinstance(plan_info, dict) else '',
        'monthly_premium': premiums.get('Total monthly premium', premiums.get('Monthly Premium', '')),
        'drug_deductible': deductibles.get('Drug deductible', ''),
        'health_deductible': deductibles.get('Health deductible', ''),
        'max_out_of_pocket': moop.get('Maximum Out-of-Pocket', moop.get('In-Network', '')),
    }

def build_zip_files(unified_zip, states, timestamp):
    """Generate JSON file for each ZIP code."""
    zip_dir = OUTPUT_DIR / 'zip'
    zip_dir.mkdir(parents=True, exist_ok=True)
    
    # Load CMS category mappings for all states
    print("\nLoading CMS category mappings...")
    state_categories = {}
    for state_abbrev in states.keys():
        state_categories[state_abbrev] = load_cms_categories_for_state(state_abbrev)
        cat_count = len(state_categories[state_abbrev])
        if cat_count > 0:
            print(f"  {state_abbrev}: {cat_count} plans categorized")
    
    generated = 0
    skipped = 0
    
    for zip_code, zip_info in unified_zip.items():
        # Collect plans from all states for this ZIP
        all_plans = {}
        counties_data = []
        
        for county in zip_info['counties']:
            state = county['state']
            fips = county['fips']
            county_name = county['name']
            
            county_entry = {
                'fips': fips,
                'name': county_name,
                'state': state,
                'ratio': county.get('ratio', 1.0)
            }
            
            # Check if state is scraped
            if state not in states or state in TERRITORIES:
                county_entry['plans_available'] = False
                counties_data.append(county_entry)
                continue
            
            state_data = states[state]
            
            # Get plans for this ZIP
            plan_ids = state_data['zip_to_plans'].get(zip_code, [])
            
            county_entry['plans_available'] = True
            county_entry['plan_count'] = 0
            
            for pid in plan_ids:
                if pid in state_data['plans'] and pid not in all_plans:
                    all_plans[pid] = state_data['plans'][pid]
                    county_entry['plan_count'] = county_entry.get('plan_count', 0) + 1
            
            counties_data.append(county_entry)
        
        # Build response - include FULL plan data, not just summaries
        plans_list = []
        for p in all_plans.values():
            plan_info = p.get('plan_info', {})
            # Handle case where plan_info is a list instead of dict
            if isinstance(plan_info, list):
                plan_info = {'name': plan_info[0] if plan_info else ''}
            plan_name = plan_info.get('name', '') if isinstance(plan_info, dict) else ''
            
            # Get correct category from CMS data
            plan_id = p.get('plan_id', '')
            # Determine which state this plan came from
            plan_state = None
            for county in zip_info['counties']:
                if county['state'] in states:
                    state_plans = states[county['state']]['zip_to_plans'].get(zip_code, [])
                    if plan_id in state_plans:
                        plan_state = county['state']
                        break
            
            # Look up category from CMS data
            category = 'MAPD'  # default
            if plan_state and plan_state in state_categories:
                category = state_categories[plan_state].get(plan_id, 'MAPD')
            
            # Include the full plan object with category and plan_type
            plan_data = {
                'plan_id': plan_id,
                'category': category,  # MAPD, PD, or MA from CMS data
                'plan_type': extract_plan_type(plan_name),  # HMO, PPO, PDP, etc.
                'plan_info': plan_info,
                'premiums': p.get('premiums', {}),
                'deductibles': p.get('deductibles', {}),
                'maximum_out_of_pocket': p.get('maximum_out_of_pocket', {}),
                'contact_info': p.get('contact_info', {}),
                'benefits': p.get('benefits', {}),
                'drug_coverage': p.get('drug_coverage', {}),
                'extra_benefits': p.get('extra_benefits', {}),
            }
            plans_list.append(plan_data)
        
        # Group plans by category
        plans_by_category = {'MAPD': [], 'PD': [], 'MA': []}
        for plan in plans_list:
            cat = plan.get('category', 'MAPD')
            if cat in plans_by_category:
                plans_by_category[cat].append(plan)
        
        response = {
            'zip_code': zip_code,
            'multi_county': zip_info.get('multi_county', False),
            'multi_state': zip_info.get('multi_state', False),
            'states': zip_info.get('states', []),
            'primary_state': zip_info.get('primary_state'),
            'counties': counties_data,
            'plans': plans_list,
            'plan_count': len(plans_list),
            'plan_counts_by_category': {
                'MAPD': len(plans_by_category['MAPD']),
                'PD': len(plans_by_category['PD']),
                'MA': len(plans_by_category['MA'])
            },
            'generated_at': timestamp
        }
        
        # Write main file (all plans)
        with open(zip_dir / f'{zip_code}.json', 'w') as f:
            json.dump(response, f, separators=(',', ':'))  # Compact JSON
        
        # Write category-filtered files
        for cat in ['MAPD', 'PD', 'MA']:
            if plans_by_category[cat]:  # Only write if there are plans
                cat_response = {
                    'zip_code': zip_code,
                    'category': cat,
                    'multi_county': zip_info.get('multi_county', False),
                    'multi_state': zip_info.get('multi_state', False),
                    'states': zip_info.get('states', []),
                    'primary_state': zip_info.get('primary_state'),
                    'counties': counties_data,
                    'plans': plans_by_category[cat],
                    'plan_count': len(plans_by_category[cat]),
                    'generated_at': timestamp
                }
                with open(zip_dir / f'{zip_code}_{cat}.json', 'w') as f:
                    json.dump(cat_response, f, separators=(',', ':'))
        
        generated += 1
        
        if generated % 5000 == 0:
            print(f"    Generated {generated} ZIP files...")
    
    return generated

def build_state_files(states, timestamp):
    """Generate state info and plans files."""
    state_dir = OUTPUT_DIR / 'state'
    state_dir.mkdir(parents=True, exist_ok=True)
    
    for state_abbrev, state_data in states.items():
        if state_abbrev in TERRITORIES:
            continue
        
        # Create state directory
        st_dir = state_dir / state_abbrev
        st_dir.mkdir(exist_ok=True)
        
        info = state_data['info']
        plans = state_data['plans']
        
        # State info
        info_response = {
            'state': info.get('state', ''),
            'state_abbrev': state_abbrev,
            'type': info.get('type', 'county'),
            'plan_count': len(plans),
            'zip_count': info.get('zip_count', 0),
            'generated_at': timestamp
        }
        
        with open(st_dir / 'info.json', 'w') as f:
            json.dump(info_response, f, separators=(',', ':'))
        
        # All plans (summaries)
        plans_response = {
            'state': info.get('state', ''),
            'state_abbrev': state_abbrev,
            'plan_count': len(plans),
            'plans': [get_plan_summary(p) for p in plans.values()],
            'generated_at': timestamp
        }
        
        with open(st_dir / 'plans.json', 'w') as f:
            json.dump(plans_response, f, separators=(',', ':'))
    
    print(f"  Generated state files for {len(states) - len(TERRITORIES)} states")

def build_plan_files(states, timestamp):
    """Generate individual plan detail files."""
    plan_dir = OUTPUT_DIR / 'plan'
    plan_dir.mkdir(parents=True, exist_ok=True)
    
    all_plans = {}
    
    # Collect all unique plans
    for state_abbrev, state_data in states.items():
        if state_abbrev in TERRITORIES:
            continue
        
        for plan_id, plan in state_data['plans'].items():
            if plan_id not in all_plans:
                all_plans[plan_id] = {
                    'plan': plan,
                    'states': [state_abbrev]
                }
            else:
                all_plans[plan_id]['states'].append(state_abbrev)
    
    # Write plan files
    for plan_id, data in all_plans.items():
        plan = data['plan']
        
        response = {
            'plan_id': plan_id,
            'states': data['states'],
            'plan_info': plan.get('plan_info', {}),
            'premiums': plan.get('premiums', {}),
            'deductibles': plan.get('deductibles', {}),
            'maximum_out_of_pocket': plan.get('maximum_out_of_pocket', {}),
            'contact_info': plan.get('contact_info', {}),
            'benefits': plan.get('benefits', {}),
            'drug_coverage': plan.get('drug_coverage', {}),
            'extra_benefits': plan.get('extra_benefits', {}),
            'generated_at': timestamp
        }
        
        with open(plan_dir / f'{plan_id}.json', 'w') as f:
            json.dump(response, f, separators=(',', ':'))
    
    print(f"  Generated {len(all_plans)} plan files")

def build_states_index(states, timestamp):
    """Generate states.json index."""
    states_list = []
    
    for state_abbrev, state_data in states.items():
        if state_abbrev in TERRITORIES:
            continue
        
        info = state_data['info']
        states_list.append({
            'abbrev': state_abbrev,
            'name': info.get('state', ''),
            'type': info.get('type', 'county'),
            'plan_count': len(state_data['plans']),
            'zip_count': info.get('zip_count', 0),
            'info_url': f"/medicare/state/{state_abbrev}/info.json",
            'plans_url': f"/medicare/state/{state_abbrev}/plans.json"
        })
    
    response = {
        'state_count': len(states_list),
        'total_plans': sum(s['plan_count'] for s in states_list),
        'states': sorted(states_list, key=lambda x: x['name']),
        'generated_at': timestamp
    }
    
    with open(OUTPUT_DIR / 'states.json', 'w') as f:
        json.dump(response, f, indent=2)
    
    print(f"  Generated states.json with {len(states_list)} states")

def main():
    print("="*80)
    print("BUILDING STATIC API FILES")
    print("="*80)
    print()
    
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load data
    print("Loading unified ZIP mapping...")
    unified_zip = load_unified_zip_mapping()
    print(f"  Loaded {len(unified_zip)} ZIP codes")
    print()
    
    print("Loading state data...")
    states = load_state_data()
    print()
    
    # Generate files
    print("Generating ZIP files...")
    zip_count = build_zip_files(unified_zip, states, timestamp)
    print(f"  Generated {zip_count} ZIP files")
    print()
    
    print("Generating state files...")
    build_state_files(states, timestamp)
    print()
    
    print("Generating plan files...")
    build_plan_files(states, timestamp)
    print()
    
    print("Generating states index...")
    build_states_index(states, timestamp)
    print()
    
    # Summary
    print("="*80)
    print("COMPLETE!")
    print(f"  Output directory: {OUTPUT_DIR}")
    print(f"  ZIP files: {zip_count}")
    print(f"  State directories: {len(states) - len(TERRITORIES)}")
    print()
    print("Next steps:")
    print("  1. aws s3 sync ./static_api/ s3://YOUR-BUCKET/")
    print("  2. Configure CloudFront distribution")
    print("  3. Point purlpal-api.com to CloudFront")
    print("="*80)

if __name__ == '__main__':
    main()
