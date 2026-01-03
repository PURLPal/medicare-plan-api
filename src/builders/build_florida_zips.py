#!/usr/bin/env python3
"""
Build Florida ZIP-level API files from parsed plan data.
Generates only FL ZIP files (32xxx, 33xxx ranges).
"""
import json
from pathlib import Path
from datetime import datetime

# Paths
MOCK_API_DIR = Path('mock_api/FL')
SCRAPED_JSON_DIR = Path('scraped_json_all')
OUTPUT_DIR = Path('static_api/medicare/zip')

def load_fl_plans():
    """Load all parsed Florida plan data."""
    plans = {}
    fl_files = list(SCRAPED_JSON_DIR.glob('Florida-*.json'))
    
    print(f"Loading {len(fl_files)} Florida plan files...")
    
    for plan_file in fl_files:
        try:
            with open(plan_file) as f:
                plan_data = json.load(f)
            plan_id = plan_data.get('plan_id')
            if plan_id:
                plans[plan_id] = plan_data
        except Exception as e:
            print(f"  Error loading {plan_file.name}: {e}")
    
    print(f"Loaded {len(plans)} Florida plans")
    return plans

def load_zip_to_plans_mapping():
    """Load ZIP to plans mapping from mock_api."""
    zip_mapping_file = MOCK_API_DIR / 'zip_to_plans.json'
    
    with open(zip_mapping_file) as f:
        return json.load(f)

def build_zip_file(zip_code, plan_ids, all_plans):
    """Build a single ZIP file."""
    plans_for_zip = []
    
    for plan_id in plan_ids:
        if plan_id in all_plans:
            plan_data = all_plans[plan_id]
            
            # Create compact plan representation
            compact_plan = {
                'plan_id': plan_data.get('plan_id', ''),
                'plan_name': plan_data.get('plan_info', {}).get('name', ''),
                'plan_type': plan_data.get('plan_info', {}).get('type', ''),
                'organization': plan_data.get('plan_info', {}).get('organization', ''),
                'premiums': plan_data.get('premiums', {}),
                'deductibles': plan_data.get('deductibles', {}),
                'out_of_pocket': plan_data.get('out_of_pocket', {}),
                'benefits': plan_data.get('benefits', {})
            }
            
            plans_for_zip.append(compact_plan)
    
    # Build ZIP API response
    response = {
        'zip': zip_code,
        'state': 'Florida',
        'plan_count': len(plans_for_zip),
        'plans': plans_for_zip,
        'generated_at': datetime.utcnow().isoformat() + 'Z'
    }
    
    # Write to file
    output_file = OUTPUT_DIR / f"{zip_code}.json"
    with open(output_file, 'w') as f:
        json.dump(response, f, separators=(',', ':'))  # Compact JSON
    
    return len(plans_for_zip)

def main():
    print("="*80)
    print("BUILDING FLORIDA ZIP-LEVEL API FILES")
    print("="*80)
    
    # Load data
    all_plans = load_fl_plans()
    zip_to_plans = load_zip_to_plans_mapping()
    
    # Filter for FL ZIPs only (32xxx and 33xxx)
    fl_zips = {zip_code: plan_ids for zip_code, plan_ids in zip_to_plans.items() 
               if zip_code.startswith('32') or zip_code.startswith('33')}
    
    print(f"\nFlorida ZIPs to build: {len(fl_zips)}")
    print(f"Output directory: {OUTPUT_DIR}\n")
    
    # Build each ZIP file
    total_plans = 0
    for i, (zip_code, plan_ids) in enumerate(sorted(fl_zips.items()), 1):
        plan_count = build_zip_file(zip_code, plan_ids, all_plans)
        total_plans += plan_count
        
        if i % 100 == 0:
            print(f"  Generated {i}/{len(fl_zips)} ZIP files...")
    
    print(f"\n{'='*80}")
    print(f"BUILD COMPLETE")
    print(f"{'='*80}")
    print(f"ZIP files generated: {len(fl_zips)}")
    print(f"Total plan entries: {total_plans}")
    print(f"Output: {OUTPUT_DIR}")
    
    # Check file sizes
    fl_files = list(OUTPUT_DIR.glob('32*.json')) + list(OUTPUT_DIR.glob('33*.json'))
    total_size = sum(f.stat().st_size for f in fl_files)
    avg_size = total_size / len(fl_files) if fl_files else 0
    
    print(f"\nFile statistics:")
    print(f"  Total size: {total_size / (1024*1024):.2f} MB")
    print(f"  Average per file: {avg_size:.0f} bytes")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
