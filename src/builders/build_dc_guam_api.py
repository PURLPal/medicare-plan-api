#!/usr/bin/env python3
"""
Build API data for DC and Guam (no counties - all ZIPs get all plans)
"""
import json
import os
from pathlib import Path

# DC ZIP ranges
DC_ZIPS = []
DC_ZIPS.extend(range(20001, 20099))  # 20001-20098
DC_ZIPS.extend(range(20201, 20600))  # 20201-20599
DC_ZIPS.extend(range(56901, 57000))  # 56901-56999
DC_ZIPS = [str(z) for z in DC_ZIPS]

# Guam ZIP codes
GUAM_ZIPS = ['96910', '96913', '96915', '96916', '96917', '96919', 
             '96921', '96923', '96928', '96929', '96931', '96932']

def build_region_api(state_name, state_abbrev, zip_codes, output_dir):
    """Build API structure for a region without counties"""
    
    print(f"\n{'='*80}")
    print(f"Building API for {state_name}")
    print(f"{'='*80}")
    
    # Create directory structure
    api_dir = Path(output_dir) / state_abbrev
    api_dir.mkdir(parents=True, exist_ok=True)
    
    # Load scraped plans
    scraped_dir = Path('scraped_json_all')
    state_prefix = state_name.replace(' ', '_')
    
    scraped_files = list(scraped_dir.glob(f'{state_prefix}-*.json'))
    print(f"Found {len(scraped_files)} scraped plans")
    
    if len(scraped_files) == 0:
        print(f"⚠️  No scraped data found for {state_name}")
        return
    
    # Load all plans
    all_plans = []
    for plan_file in scraped_files:
        plan_id = plan_file.stem.replace(f'{state_prefix}-', '')
        
        with open(plan_file) as f:
            plan_data = json.load(f)
        
        # Extract summary info
        summary = {
            'contract_plan_segment_id': plan_id,
            'plan_name': plan_data.get('plan_info', {}).get('name', 'Unknown'),
            'plan_type': plan_data.get('plan_info', {}).get('type', 'Unknown'),
            'organization': plan_data.get('plan_info', {}).get('organization', 'Unknown'),
            'plan_id': plan_data.get('plan_info', {}).get('id', plan_id)
        }
        
        all_plans.append({
            'summary': summary,
            'details': plan_data,
            'has_scraped_details': True
        })
    
    print(f"Processed {len(all_plans)} plans")
    
    # Create region cache (like county cache but for entire region)
    region_cache = {
        'region': state_name,
        'state': state_abbrev,
        'plan_count': len(all_plans),
        'scraped_details_available': len(all_plans),
        'plans': all_plans
    }
    
    with open(api_dir / 'region_cache.json', 'w') as f:
        json.dump(region_cache, f, indent=2)
    
    print(f"✅ Created region_cache.json with {len(all_plans)} plans")
    
    # Create ZIP to region mapping
    zip_mapping = []
    for zip_code in zip_codes:
        zip_mapping.append({
            'zip': zip_code,
            'region': state_name,
            'state': state_abbrev,
            'all_plans': True,  # All ZIPs get all plans
            'plan_count': len(all_plans)
        })
    
    with open(api_dir / 'zip_to_region.json', 'w') as f:
        json.dump(zip_mapping, f, indent=2)
    
    print(f"✅ Created zip_to_region.json with {len(zip_codes)} ZIP codes")
    
    # Create ZIP to plans direct mapping (for fast lookups)
    zip_to_plans = {}
    for zip_code in zip_codes:
        zip_to_plans[zip_code] = {
            'zip': zip_code,
            'region': state_name,
            'plan_count': len(all_plans),
            'plans': all_plans
        }
    
    with open(api_dir / 'zip_to_plans.json', 'w') as f:
        json.dump(zip_to_plans, f, indent=2)
    
    print(f"✅ Created zip_to_plans.json")
    
    # Create API info file
    api_info = {
        'state': state_name,
        'state_abbrev': state_abbrev,
        'type': 'region',
        'has_counties': False,
        'plan_count': len(all_plans),
        'zip_count': len(zip_codes),
        'scraped_plans': len(all_plans),
        'endpoints': {
            'by_zip': f'/api/{state_abbrev.lower()}/<zip_code>',
            'by_plan': f'/api/{state_abbrev.lower()}/plan/<plan_id>',
            'all_plans': f'/api/{state_abbrev.lower()}/plans'
        },
        'notes': f'{state_name} does not use counties - all plans available to all ZIP codes'
    }
    
    with open(api_dir / 'api_info.json', 'w') as f:
        json.dump(api_info, f, indent=2)
    
    print(f"✅ Created api_info.json")
    print(f"\n{'='*80}")
    print(f"✅ {state_name} API data complete!")
    print(f"   Location: {api_dir}")
    print(f"   Plans: {len(all_plans)}")
    print(f"   ZIP codes: {len(zip_codes)}")
    print(f"{'='*80}")

if __name__ == '__main__':
    output_dir = 'mock_api'
    
    print("Building API data for non-county regions...")
    
    # Build DC
    build_region_api(
        state_name='District_of_Columbia',
        state_abbrev='DC',
        zip_codes=DC_ZIPS,
        output_dir=output_dir
    )
    
    # Build Guam
    build_region_api(
        state_name='Guam',
        state_abbrev='GU',
        zip_codes=GUAM_ZIPS,
        output_dir=output_dir
    )
    
    print("\n" + "="*80)
    print("✅ All region APIs built successfully!")
    print("="*80)
