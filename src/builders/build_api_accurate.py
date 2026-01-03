#!/usr/bin/env python3
"""
Build static JSON API with ACCURATE geographic data.
Uses CMS county-level plan coverage + ZIP-to-county mappings.
"""
import json
import re
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

# Paths
SCRAPED_DATA_DIR = Path('scraped_data/json')
PLAN_COUNTY_MAPPINGS = Path('plan_county_mappings.json')
UNIFIED_ZIP_FILE = Path('unified_zip_to_fips.json')
ZIP_COUNTY_DIR = Path('zip_county_data')
OUTPUT_DIR = Path('static_api/medicare')

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

ABBREV_TO_NAME = {v: k for k, v in STATE_NAME_TO_ABBREV.items()}
TERRITORIES = {'AS', 'GU', 'MP', 'PR', 'VI'}

CMS_CATEGORY_TO_SUNFIRE = {
    'MA-PD': 'MAPD',
    'SNP': 'MAPD',
    'MA': 'MA',
    'PDP': 'PD',
}

def extract_plan_type(plan_name):
    """Extract network type from plan name."""
    if not plan_name:
        return None
    match = re.search(r'\(([^)]+)\)\s*$', plan_name)
    return match.group(1) if match else None

def load_plan_county_mappings():
    """Load which counties each plan serves."""
    print("Loading plan-county mappings from CMS data...")
    with open(PLAN_COUNTY_MAPPINGS) as f:
        return json.load(f)

def load_scraped_plans():
    """Load all scraped plan details."""
    print("Loading scraped plan data...")
    plans = {}
    
    for state_dir in SCRAPED_DATA_DIR.iterdir():
        if not state_dir.is_dir():
            continue
        
        for plan_file in state_dir.glob('*.json'):
            try:
                with open(plan_file) as f:
                    plan = json.load(f)
                plan_id = plan.get('plan_id', '')
                if plan_id:
                    plans[plan_id] = plan
            except Exception as e:
                print(f"  ⚠️  Error loading {plan_file}: {e}")
    
    print(f"  Loaded {len(plans):,} scraped plans")
    return plans

def build_county_to_plans_index(plan_county_mappings):
    """Build reverse index: (state, county) -> [plan_ids]"""
    print("Building county→plans index...")
    county_plans = defaultdict(list)
    
    for plan_id, mapping in plan_county_mappings.items():
        state_abbrev = mapping['state_abbrev']
        
        if mapping['all_counties']:
            # Mark this as an "all counties" plan for this state
            county_plans[(state_abbrev, '__ALL_COUNTIES__')].append(plan_id)
        else:
            # Add to each specific county
            for county in mapping['counties']:
                county_plans[(state_abbrev, county)].append(plan_id)
    
    print(f"  Indexed {len(county_plans):,} county entries")
    return county_plans

def build_zip_files(unified_zip, scraped_plans, plan_county_mappings, county_plans_index, timestamp):
    """Generate JSON file for each ZIP code."""
    zip_dir = OUTPUT_DIR / 'zip'
    zip_dir.mkdir(parents=True, exist_ok=True)
    
    generated = 0
    
    for zip_code, zip_info in unified_zip.items():
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
            
            # Skip territories
            if state_abbrev in TERRITORIES:
                county_entry['plans_available'] = False
                counties_data.append(county_entry)
                continue
            
            # Find plans for this county
            plan_ids = []
            
            # Get "all counties" plans for this state
            plan_ids.extend(county_plans_index.get((state_abbrev, '__ALL_COUNTIES__'), []))
            
            # Get county-specific plans
            plan_ids.extend(county_plans_index.get((state_abbrev, county_name), []))
            
            # Remove duplicates
            plan_ids = list(set(plan_ids))
            
            county_entry['plans_available'] = len(plan_ids) > 0
            county_entry['plan_count'] = len(plan_ids)
            
            # Add plans to response
            for plan_id in plan_ids:
                if plan_id in scraped_plans and plan_id not in all_plans:
                    all_plans[plan_id] = scraped_plans[plan_id]
            
            counties_data.append(county_entry)
        
        # Build response with full plan data
        plans_list = []
        for plan_id, plan in all_plans.items():
            plan_name = plan.get('plan_info', {}).get('name', '')
            
            # Get category from CMS data
            cms_mapping = plan_county_mappings.get(plan_id, {})
            cms_category = cms_mapping.get('category', '')
            category = CMS_CATEGORY_TO_SUNFIRE.get(cms_category, 'MAPD')
            
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

def build_state_and_plan_files(scraped_plans, plan_county_mappings, timestamp):
    """Generate state and individual plan files."""
    
    # Organize plans by state
    states = defaultdict(list)
    for plan_id, plan in scraped_plans.items():
        cms_mapping = plan_county_mappings.get(plan_id, {})
        state_abbrev = cms_mapping.get('state_abbrev', '')
        if state_abbrev and state_abbrev not in TERRITORIES:
            states[state_abbrev].append(plan)
    
    # Build state files
    state_dir = OUTPUT_DIR / 'state'
    state_dir.mkdir(parents=True, exist_ok=True)
    
    for state_abbrev, plans in states.items():
        st_dir = state_dir / state_abbrev
        st_dir.mkdir(exist_ok=True)
        
        state_name = ABBREV_TO_NAME.get(state_abbrev, state_abbrev).replace('_', ' ')
        
        # State info
        info_response = {
            'state': state_name,
            'state_abbrev': state_abbrev,
            'plan_count': len(plans),
            'generated_at': timestamp
        }
        
        with open(st_dir / 'info.json', 'w') as f:
            json.dump(info_response, f, separators=(',', ':'))
        
        # Plans list (summaries)
        plans_list = []
        for plan in plans:
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
            'state': state_name,
            'state_abbrev': state_abbrev,
            'plan_count': len(plans),
            'plans': plans_list,
            'generated_at': timestamp
        }
        
        with open(st_dir / 'plans.json', 'w') as f:
            json.dump(plans_response, f, separators=(',', ':'))
    
    print(f"  Generated state files for {len(states)} states")
    
    # Build individual plan files
    plan_dir = OUTPUT_DIR / 'plan'
    plan_dir.mkdir(parents=True, exist_ok=True)
    
    for plan_id, plan in scraped_plans.items():
        cms_mapping = plan_county_mappings.get(plan_id, {})
        state_abbrev = cms_mapping.get('state_abbrev', '')
        
        if state_abbrev in TERRITORIES:
            continue
        
        response = {
            'plan_id': plan_id,
            'state': cms_mapping.get('state', ''),
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
    
    print(f"  Generated {len(scraped_plans):,} plan files")

def build_states_index(scraped_plans, plan_county_mappings, timestamp):
    """Generate states.json index."""
    states_count = defaultdict(int)
    
    for plan_id, plan in scraped_plans.items():
        cms_mapping = plan_county_mappings.get(plan_id, {})
        state_abbrev = cms_mapping.get('state_abbrev', '')
        if state_abbrev and state_abbrev not in TERRITORIES:
            states_count[state_abbrev] += 1
    
    states_list = []
    for state_abbrev, count in states_count.items():
        state_name = ABBREV_TO_NAME.get(state_abbrev, state_abbrev).replace('_', ' ')
        states_list.append({
            'abbrev': state_abbrev,
            'name': state_name,
            'plan_count': count,
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
    print("BUILDING STATIC API WITH ACCURATE GEOGRAPHIC DATA")
    print("="*80)
    print()
    
    timestamp = datetime.now(timezone.utc).isoformat()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load all data
    plan_county_mappings = load_plan_county_mappings()
    scraped_plans = load_scraped_plans()
    county_plans_index = build_county_to_plans_index(plan_county_mappings)
    
    print("\nLoading unified ZIP mapping...")
    with open(UNIFIED_ZIP_FILE) as f:
        unified_zip = json.load(f)
    print(f"  Loaded {len(unified_zip):,} ZIP codes")
    print()
    
    # Generate files
    print("Generating ZIP files...")
    zip_count = build_zip_files(unified_zip, scraped_plans, plan_county_mappings, county_plans_index, timestamp)
    print(f"  ✅ Generated {zip_count:,} ZIP files")
    print()
    
    print("Generating state and plan files...")
    build_state_and_plan_files(scraped_plans, plan_county_mappings, timestamp)
    print()
    
    print("Generating states index...")
    build_states_index(scraped_plans, plan_county_mappings, timestamp)
    print()
    
    # Summary
    print("="*80)
    print("COMPLETE!")
    print(f"  Output: {OUTPUT_DIR}")
    print(f"  ZIP files: {zip_count:,}")
    print(f"  Plans: {len(scraped_plans):,}")
    print()
    print("Next: Upload to S3")
    print(f"  aws s3 sync {OUTPUT_DIR}/ s3://purlpal-medicare-api/medicare/ --delete")
    print("="*80)

if __name__ == '__main__':
    main()
