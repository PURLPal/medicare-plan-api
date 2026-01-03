#!/usr/bin/env python3
"""
Build Arkansas ZIP files using the EXACT SAME format as other states.
Only processes Arkansas ZIPs (71xxx-72xxx) to avoid wasteful regeneration.
"""
import json
from pathlib import Path
from datetime import datetime
import re

# Import the standard helper functions
import sys
sys.path.insert(0, str(Path(__file__).parent))

OUTPUT_DIR = Path('static_api/medicare')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def extract_plan_type(plan_name):
    """Extract plan type (HMO, PPO, etc.) from plan name."""
    if not plan_name:
        return ''
    match = re.search(r'\(([A-Z\-]+)\)', plan_name)
    if match:
        plan_type = match.group(1)
        # Filter out non-plan-type codes
        if plan_type not in ['D-SNP', 'C-SNP', 'I-SNP']:
            return plan_type
    return ''

def load_cms_categories():
    """Load CMS category mappings from state_data files."""
    state_categories = {}
    state_data_dir = Path('state_data')
    
    ar_file = state_data_dir / 'Arkansas.json'
    if ar_file.exists():
        categories = {}
        with open(ar_file) as f:
            plans = json.load(f)
            for plan in plans:
                plan_id = plan.get('ContractPlanSegmentID')
                contract_type = plan.get('Contract Category Type', '')
                part_d = plan.get('Part D Coverage Indicator', '')
                
                if contract_type == 'PDP':
                    category = 'PD'
                elif part_d == 'Yes':
                    category = 'MAPD'
                else:
                    category = 'MA'
                
                categories[plan_id] = category
        
        state_categories['Arkansas'] = categories
    
    return state_categories

def build_arkansas_zips():
    """Build Arkansas ZIP files in standard format."""
    print("\n" + "="*80)
    print("BUILDING ARKANSAS IN STANDARD FORMAT")
    print("="*80)
    
    # Load unified ZIP mapping
    unified_file = Path('unified_zip_to_fips.json')
    if not unified_file.exists():
        print("❌ Unified ZIP mapping not found!")
        return 0
    
    with open(unified_file) as f:
        unified_zip = json.load(f)
    
    # Load Arkansas mock API data
    mock_api_dir = Path('mock_api/AR')
    with open(mock_api_dir / 'zip_to_plans.json') as f:
        ar_zip_to_plans = json.load(f)
    
    # Load scraped plans
    ar_plans = {}
    scraped_dir = Path('scraped_json_all')
    for plan_file in scraped_dir.glob('Arkansas-*.json'):
        with open(plan_file) as f:
            plan_data = json.load(f)
            plan_id = plan_data.get('plan_id')
            if plan_id:
                ar_plans[plan_id] = plan_data
    
    print(f"Loaded {len(ar_plans)} Arkansas plans")
    
    # Load CMS categories
    state_categories = load_cms_categories()
    ar_categories = state_categories.get('Arkansas', {})
    print(f"Loaded {len(ar_categories)} category mappings")
    
    timestamp = datetime.utcnow().isoformat() + 'Z'
    
    # Filter to only Arkansas ZIPs (71xxx-72xxx)
    ar_zips = [z for z in unified_zip.keys() if z.startswith('71') or z.startswith('72')]
    print(f"\nFound {len(ar_zips)} Arkansas ZIPs to generate")
    
    zip_dir = OUTPUT_DIR / 'zip'
    zip_dir.mkdir(parents=True, exist_ok=True)
    
    count = 0
    for zip_code in sorted(ar_zips):
        zip_info = unified_zip[zip_code]
        
        # Build counties data
        counties_data = []
        for county in zip_info.get('counties', []):
            county_entry = {
                'name': county['name'],
                'fips': county['fips'],
                'state': county['state'],
                'plans_available': county['state'] == 'Arkansas'
            }
            counties_data.append(county_entry)
        
        # Get Arkansas plans for this ZIP
        plan_ids = ar_zip_to_plans.get(zip_code, [])
        
        plans_list = []
        for plan_id in plan_ids:
            if plan_id not in ar_plans:
                continue
            
            p = ar_plans[plan_id]
            plan_info = p.get('plan_info', {})
            
            # Get category from CMS data
            category = ar_categories.get(plan_id, 'MAPD')
            
            # Extract plan type from name
            plan_name = plan_info.get('name', '')
            plan_type = extract_plan_type(plan_name)
            
            # Build in STANDARD format
            plan_data = {
                'plan_id': plan_id,
                'category': category,
                'plan_type': plan_type,
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
        
        # Group by category
        plans_by_category = {'MAPD': [], 'PD': [], 'MA': []}
        for plan in plans_list:
            cat = plan.get('category', 'MAPD')
            if cat in plans_by_category:
                plans_by_category[cat].append(plan)
        
        # Build STANDARD response format
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
        
        # Write category-filtered files
        for cat in ['MAPD', 'PD', 'MA']:
            if plans_by_category[cat]:
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
        
        count += 1
        if count % 100 == 0:
            print(f"  Generated {count}/{len(ar_zips)} ZIPs...")
    
    print(f"\n{'='*80}")
    print("COMPLETE!")
    print(f"{'='*80}")
    print(f"✅ Generated {count} Arkansas ZIPs in STANDARD format")
    print(f"📁 Output: {zip_dir}")
    print(f"{'='*80}\n")
    
    return count

if __name__ == '__main__':
    build_arkansas_zips()
