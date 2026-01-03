#!/usr/bin/env python3
"""
Build static JSON API from scraped Medicare data.
Input: scraped_data/json/ (6,402 plans across 56 states)
Output: static_api/medicare/ (ZIP, state, and plan endpoints)
"""
import json
import re
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

# Paths
SCRAPED_DATA_DIR = Path('scraped_data/json')
STATE_DATA_DIR = Path('state_data')
UNIFIED_ZIP_FILE = Path('unified_zip_to_fips.json')
OUTPUT_DIR = Path('static_api/medicare')

# State abbreviation mapping
STATE_NAME_TO_ABBREV = {
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
    'American_Samoa': 'AS', 'Guam': 'GU', 'Northern_Mariana_Islands': 'MP',
    'Puerto_Rico': 'PR', 'Virgin_Islands': 'VI'
}

TERRITORIES = {'AS', 'GU', 'MP', 'PR', 'VI'}

# CMS Category mapping
CMS_CATEGORY_TO_SUNFIRE = {
    'MA-PD': 'MAPD',
    'SNP': 'MAPD',
    'MA': 'MA',
    'PDP': 'PD',
}

def extract_plan_type(plan_name):
    """Extract network type from plan name (HMO, PPO, etc.)"""
    if not plan_name:
        return None
    match = re.search(r'\(([^)]+)\)\s*$', plan_name)
    return match.group(1) if match else None

def load_cms_categories():
    """Load CMS category data from state_data files."""
    categories = {}
    
    for state_file in STATE_DATA_DIR.glob('*.json'):
        state_name = state_file.stem
        state_abbrev = STATE_NAME_TO_ABBREV.get(state_name)
        if not state_abbrev:
            continue
        
        with open(state_file) as f:
            state_plans = json.load(f)
        
        for plan in state_plans:
            plan_id = plan.get('ContractPlanSegmentID', '')
            cms_category = plan.get('Contract Category Type', '')
            if plan_id and cms_category:
                sunfire_cat = CMS_CATEGORY_TO_SUNFIRE.get(cms_category, 'MAPD')
                categories[plan_id] = sunfire_cat
    
    return categories

def load_all_scraped_plans():
    """Load all scraped plan data organized by state."""
    states = {}
    total_plans = 0
    
    for state_dir in sorted(SCRAPED_DATA_DIR.iterdir()):
        if not state_dir.is_dir():
            continue
        
        state_name = state_dir.name
        state_abbrev = STATE_NAME_TO_ABBREV.get(state_name)
        
        if not state_abbrev:
            print(f"  ⚠️  Unknown state: {state_name}")
            continue
        
        # Load all plans from this state
        plans = {}
        for plan_file in state_dir.glob('*.json'):
            try:
                with open(plan_file) as f:
                    plan = json.load(f)
                plan_id = plan.get('plan_id', '')
                if plan_id:
                    plans[plan_id] = plan
            except Exception as e:
                print(f"  ⚠️  Error loading {plan_file}: {e}")
        
        states[state_abbrev] = {
            'name': state_name,
            'plans': plans
        }
        
        total_plans += len(plans)
        print(f"  {state_abbrev}: {len(plans):4d} plans")
    
    print(f"\n  Total: {total_plans:,} plans across {len(states)} states")
    return states

def build_plan_to_zips_mapping(states):
    """Build mapping of plan_id -> list of ZIP codes."""
    plan_to_zips = defaultdict(set)
    
    # Load state data files which contain ZIP mappings
    for state_abbrev in states.keys():
        state_name = states[state_abbrev]['name']
        state_file = STATE_DATA_DIR / f'{state_name}.json'
        
        if not state_file.exists():
            continue
        
        with open(state_file) as f:
            state_plans = json.load(f)
        
        for plan in state_plans:
            plan_id = plan.get('ContractPlanSegmentID', '')
            counties = plan.get('CountyList', [])
            
            if not plan_id or not counties:
                continue
            
            # Each county has ZIPs
            for county in counties:
                zips = county.get('ZipList', [])
                for zip_code in zips:
                    plan_to_zips[plan_id].add(zip_code)
    
    return plan_to_zips

def build_zip_files(unified_zip, states, plan_to_zips, cms_categories, timestamp):
    """Generate JSON file for each ZIP code."""
    zip_dir = OUTPUT_DIR / 'zip'
    zip_dir.mkdir(parents=True, exist_ok=True)
    
    generated = 0
    
    for zip_code, zip_info in unified_zip.items():
        # Collect plans for this ZIP
        all_plans = {}
        counties_data = []
        
        for county in zip_info['counties']:
            state_abbrev = county['state']
            fips = county['fips']
            county_name = county['name']
            
            county_entry = {
                'fips': fips,
                'name': county_name,
                'state': state_abbrev,
                'ratio': county.get('ratio', 1.0)
            }
            
            # Check if we have data for this state
            if state_abbrev not in states or state_abbrev in TERRITORIES:
                county_entry['plans_available'] = False
                counties_data.append(county_entry)
                continue
            
            county_entry['plans_available'] = True
            county_entry['plan_count'] = 0
            
            # Find plans available in this ZIP
            state_plans = states[state_abbrev]['plans']
            for plan_id, plan in state_plans.items():
                if zip_code in plan_to_zips.get(plan_id, set()):
                    if plan_id not in all_plans:
                        all_plans[plan_id] = plan
                        county_entry['plan_count'] += 1
            
            counties_data.append(county_entry)
        
        # Build response with full plan data
        plans_list = []
        for plan in all_plans.values():
            plan_id = plan.get('plan_id', '')
            plan_name = plan.get('plan_info', {}).get('name', '')
            
            # Get category from CMS data
            category = cms_categories.get(plan_id, 'MAPD')
            
            plan_data = {
                'plan_id': plan_id,
                'category': category,
                'plan_type': extract_plan_type(plan_name),
                'plan_info': plan.get('plan_info', {}),
                'premiums': plan.get('premiums', {}),
                'deductibles': plan.get('deductibles', {}),
                'out_of_pocket': plan.get('out_of_pocket', {}),
                'benefits': plan.get('benefits', {}),
                'drug_coverage': plan.get('drug_coverage', {}),
                'extra_benefits': plan.get('extra_benefits', []),
            }
            plans_list.append(plan_data)
        
        # Group by category
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
        
        # Write main file
        with open(zip_dir / f'{zip_code}.json', 'w') as f:
            json.dump(response, f, separators=(',', ':'))
        
        # Write category files
        for cat in ['MAPD', 'PD', 'MA']:
            if plans_by_category[cat]:
                cat_response = response.copy()
                cat_response['category'] = cat
                cat_response['plans'] = plans_by_category[cat]
                cat_response['plan_count'] = len(plans_by_category[cat])
                
                with open(zip_dir / f'{zip_code}_{cat}.json', 'w') as f:
                    json.dump(cat_response, f, separators=(',', ':'))
        
        generated += 1
        if generated % 5000 == 0:
            print(f"    Generated {generated:,} ZIP files...")
    
    return generated

def build_state_files(states, timestamp):
    """Generate state info and plans files."""
    state_dir = OUTPUT_DIR / 'state'
    state_dir.mkdir(parents=True, exist_ok=True)
    
    for state_abbrev, state_data in states.items():
        if state_abbrev in TERRITORIES:
            continue
        
        st_dir = state_dir / state_abbrev
        st_dir.mkdir(exist_ok=True)
        
        plans = state_data['plans']
        
        # State info
        info_response = {
            'state': state_data['name'].replace('_', ' '),
            'state_abbrev': state_abbrev,
            'plan_count': len(plans),
            'generated_at': timestamp
        }
        
        with open(st_dir / 'info.json', 'w') as f:
            json.dump(info_response, f, separators=(',', ':'))
        
        # All plans (summaries)
        plans_list = []
        for plan in plans.values():
            plan_info = plan.get('plan_info', {})
            premiums = plan.get('premiums', {})
            deductibles = plan.get('deductibles', {})
            
            plans_list.append({
                'plan_id': plan.get('plan_id', ''),
                'plan_name': plan_info.get('name', ''),
                'monthly_premium': premiums.get('Total monthly premium', ''),
                'drug_deductible': deductibles.get('Drug deductible', ''),
                'health_deductible': deductibles.get('Health deductible', ''),
            })
        
        plans_response = {
            'state': state_data['name'].replace('_', ' '),
            'state_abbrev': state_abbrev,
            'plan_count': len(plans),
            'plans': plans_list,
            'generated_at': timestamp
        }
        
        with open(st_dir / 'plans.json', 'w') as f:
            json.dump(plans_response, f, separators=(',', ':'))
    
    print(f"  Generated state files for {len([s for s in states.keys() if s not in TERRITORIES])} states")

def build_plan_files(states, timestamp):
    """Generate individual plan detail files."""
    plan_dir = OUTPUT_DIR / 'plan'
    plan_dir.mkdir(parents=True, exist_ok=True)
    
    all_plans = {}
    
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
    
    for plan_id, data in all_plans.items():
        plan = data['plan']
        
        response = {
            'plan_id': plan_id,
            'states': data['states'],
            'plan_info': plan.get('plan_info', {}),
            'premiums': plan.get('premiums', {}),
            'deductibles': plan.get('deductibles', {}),
            'out_of_pocket': plan.get('out_of_pocket', {}),
            'benefits': plan.get('benefits', {}),
            'drug_coverage': plan.get('drug_coverage', {}),
            'extra_benefits': plan.get('extra_benefits', []),
            'generated_at': timestamp
        }
        
        with open(plan_dir / f'{plan_id}.json', 'w') as f:
            json.dump(response, f, separators=(',', ':'))
    
    print(f"  Generated {len(all_plans):,} plan files")

def build_states_index(states, timestamp):
    """Generate states.json index."""
    states_list = []
    
    for state_abbrev, state_data in states.items():
        if state_abbrev in TERRITORIES:
            continue
        
        states_list.append({
            'abbrev': state_abbrev,
            'name': state_data['name'].replace('_', ' '),
            'plan_count': len(state_data['plans']),
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
    print("BUILDING STATIC API FROM SCRAPED DATA")
    print("="*80)
    print()
    
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load scraped plans
    print("Loading scraped plans...")
    states = load_all_scraped_plans()
    print()
    
    # Load CMS categories
    print("Loading CMS category mappings...")
    cms_categories = load_cms_categories()
    print(f"  Loaded {len(cms_categories):,} plan categories")
    print()
    
    # Build plan->ZIP mapping
    print("Building plan-to-ZIP mappings...")
    plan_to_zips = build_plan_to_zips_mapping(states)
    print(f"  Mapped {len(plan_to_zips):,} plans to ZIP codes")
    print()
    
    # Load unified ZIP mapping
    print("Loading unified ZIP mapping...")
    with open(UNIFIED_ZIP_FILE) as f:
        unified_zip = json.load(f)
    print(f"  Loaded {len(unified_zip):,} ZIP codes")
    print()
    
    # Generate files
    print("Generating ZIP files...")
    zip_count = build_zip_files(unified_zip, states, plan_to_zips, cms_categories, timestamp)
    print(f"  Generated {zip_count:,} ZIP files")
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
    print(f"  Output: {OUTPUT_DIR}")
    print(f"  ZIP files: {zip_count:,}")
    print(f"  State directories: {len([s for s in states.keys() if s not in TERRITORIES])}")
    print()
    print("Next: Upload to S3")
    print(f"  aws s3 sync {OUTPUT_DIR}/ s3://purlpal-medicare-api/medicare/")
    print("="*80)

if __name__ == '__main__':
    main()
