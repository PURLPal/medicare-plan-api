#!/usr/bin/env python3
"""
Build static API files for Arkansas ZIP codes only (71xxx-72xxx).
Generates ~1,355 ZIP files without touching existing 39K files.
"""
import json
from pathlib import Path
from datetime import datetime

MOCK_API_DIR = Path('mock_api/AR')
STATE_DATA_DIR = Path('state_data')
SCRAPED_DIR = Path('scraped_json_all')
OUTPUT_DIR = Path('static_api/medicare/zip')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_cms_categories():
    """Load CMS category mappings for Arkansas plans."""
    categories = {}
    ar_file = STATE_DATA_DIR / 'Arkansas.json'
    
    if ar_file.exists():
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
    
    return categories

def build_arkansas_zips():
    """Build static API files for Arkansas ZIP codes."""
    print("\n" + "="*80)
    print("ARKANSAS STATIC API BUILDER")
    print("="*80)
    
    zip_to_plans_file = MOCK_API_DIR / 'zip_to_plans.json'
    if not zip_to_plans_file.exists():
        print("❌ mock_api/AR/zip_to_plans.json not found!")
        return 0
    
    with open(zip_to_plans_file) as f:
        zip_to_plans = json.load(f)
    
    print(f"\nFound {len(zip_to_plans)} Arkansas ZIP codes")
    
    print("Loading CMS categories...")
    categories = load_cms_categories()
    print(f"Loaded categories for {len(categories)} plans")
    
    timestamp = datetime.utcnow().isoformat() + 'Z'
    count = 0
    category_counts = {'MAPD': 0, 'MA': 0, 'PD': 0}
    
    print(f"\nGenerating ZIP endpoint files...")
    
    for zip_code, plan_ids in sorted(zip_to_plans.items()):
        plans = []
        
        for plan_id in plan_ids:
            plan_file = SCRAPED_DIR / f'Arkansas-{plan_id}.json'
            if plan_file.exists():
                with open(plan_file) as f:
                    plan_data = json.load(f)
                
                plan_info = plan_data.get('plan_info', {})
                category = categories.get(plan_id, 'MAPD')
                
                # Don't include raw_content - it's huge and not needed in API
                plans.append({
                    'plan_id': plan_id,
                    'name': plan_info.get('name', ''),
                    'type': plan_info.get('type', ''),
                    'organization': plan_info.get('organization', ''),
                    'category': category,
                    'premiums': plan_data.get('premiums', {}),
                    'deductibles': plan_data.get('deductibles', {}),
                    'benefits': plan_data.get('benefits', {}),
                    'maximum_out_of_pocket': plan_data.get('maximum_out_of_pocket', {}),
                    'contact_info': plan_data.get('contact_info', {})
                })
        
        # Main ZIP endpoint
        response = {
            'zip': zip_code,
            'state': 'Arkansas',
            'state_code': 'AR',
            'plans': plans,
            'count': len(plans),
            'timestamp': timestamp
        }
        
        zip_file = OUTPUT_DIR / f'{zip_code}.json'
        with open(zip_file, 'w') as f:
            json.dump(response, f, separators=(',', ':'))
        
        # Category-specific endpoints
        for category in ['MAPD', 'MA', 'PD']:
            cat_plans = [p for p in plans if p['category'] == category]
            
            if cat_plans:
                cat_response = {
                    'zip': zip_code,
                    'state': 'Arkansas',
                    'state_code': 'AR',
                    'category': category,
                    'plans': cat_plans,
                    'count': len(cat_plans),
                    'timestamp': timestamp
                }
                
                cat_file = OUTPUT_DIR / f'{zip_code}_{category}.json'
                with open(cat_file, 'w') as f:
                    json.dump(cat_response, f, separators=(',', ':'))
                
                category_counts[category] += 1
        
        count += 1
        if count % 100 == 0:
            print(f"  Generated {count}/{len(zip_to_plans)} ZIPs...")
    
    print(f"\n{'='*80}")
    print("COMPLETE!")
    print(f"{'='*80}")
    print(f"✅ Generated {count} Arkansas ZIP endpoints")
    print(f"   - MAPD endpoints: {category_counts['MAPD']}")
    print(f"   - MA endpoints: {category_counts['MA']}")
    print(f"   - PD endpoints: {category_counts['PD']}")
    print(f"📁 Output: {OUTPUT_DIR}")
    print(f"{'='*80}\n")
    
    return count

if __name__ == '__main__':
    build_arkansas_zips()
