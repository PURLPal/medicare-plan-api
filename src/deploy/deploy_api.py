#!/usr/bin/env python3
"""
Medicare API Deployment Script

This script handles the complete pipeline from scraped JSON files to deployed API:
1. Identifies complete states from scraped data
2. Builds mock_api structure for each state
3. Generates static API files (ZIP, state, plan endpoints)
4. Uploads to S3
5. Invalidates CloudFront cache

Usage:
    python3 deploy_api.py              # Full deployment
    python3 deploy_api.py --dry-run    # Show what would be done
    python3 deploy_api.py --skip-upload # Build only, no S3 upload
"""

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Configuration
SCRAPED_DIR = Path('./scraped_json_all')
MOCK_API_DIR = Path('./mock_api')
STATIC_API_DIR = Path('./static_api/medicare')
LANDSCAPE_FILE = Path('./downloaded_data/CY2026_Landscape_202511/CY2026_Landscape_202511.csv')
UNIFIED_ZIP_FILE = Path('./unified_zip_to_fips.json')
S3_BUCKET = 'purlpal-medicare-api'
CLOUDFRONT_DIST_ID = 'E3SHXUEGZALG4E'

# Territories to skip for state-level files
TERRITORIES = {'AS', 'GU', 'MP', 'PR', 'VI'}

# State mappings
STATE_ABBREVS = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR',
    'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE',
    'District of Columbia': 'DC', 'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI',
    'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA',
    'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME',
    'Maryland': 'MD', 'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN',
    'Mississippi': 'MS', 'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE',
    'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM',
    'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH',
    'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI',
    'South Carolina': 'SC', 'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX',
    'Utah': 'UT', 'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA',
    'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY',
    'Puerto Rico': 'PR', 'Virgin Islands': 'VI', 'Guam': 'GU',
    'American Samoa': 'AS', 'Northern Mariana Islands': 'MP'
}

def log(msg, level='INFO'):
    """Print timestamped log message."""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] [{level}] {msg}")

def log_progress(current, total, prefix=''):
    """Print progress bar."""
    pct = current / total * 100 if total > 0 else 0
    bar_len = 30
    filled = int(bar_len * current / total) if total > 0 else 0
    bar = '█' * filled + '░' * (bar_len - filled)
    print(f"\r[{bar}] {current:,}/{total:,} ({pct:.1f}%) {prefix}", end='', flush=True)

def get_scraped_plan_ids():
    """Get all scraped plan IDs, handling both file naming formats."""
    log("Loading scraped plan IDs...")
    scraped = set()
    for f in SCRAPED_DIR.glob('*.json'):
        name = f.stem
        if '-' in name:
            parts = name.split('-', 1)
            if len(parts) == 2:
                scraped.add(parts[1])
        else:
            scraped.add(name)
    log(f"  Found {len(scraped):,} unique scraped plans")
    return scraped

def get_landscape_data():
    """Load plan data from landscape CSV."""
    log("Loading landscape data...")
    state_plans = defaultdict(set)
    plan_counties = defaultdict(lambda: defaultdict(set))  # state -> plan_id -> counties
    county_fips = defaultdict(dict)  # state -> county -> fips
    
    with open(LANDSCAPE_FILE, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            state_name = row.get('State Territory Name', '')
            plan_id = row.get('ContractPlanSegmentID', '')
            county = row.get('County Name', '')
            fips = row.get('County FIPS Code', '')
            
            if state_name and plan_id:
                state_plans[state_name].add(plan_id)
                if county:
                    plan_counties[state_name][plan_id].add(county)
                    county_fips[state_name][county] = fips
    
    log(f"  Loaded {sum(len(p) for p in state_plans.values()):,} plan-state combinations")
    return state_plans, plan_counties, county_fips

def find_complete_states(scraped, state_plans):
    """Find states where all plans are scraped."""
    log("Identifying complete states...")
    complete = []
    for state_name, plans in sorted(state_plans.items()):
        if plans <= scraped:
            abbrev = STATE_ABBREVS.get(state_name, state_name[:2].upper())
            complete.append((state_name, abbrev, len(plans)))
    
    log(f"  Found {len(complete)} complete states")
    for state_name, abbrev, count in sorted(complete, key=lambda x: -x[2])[:10]:
        log(f"    ✅ {abbrev}: {count} plans")
    if len(complete) > 10:
        log(f"    ... and {len(complete) - 10} more")
    
    return complete

def load_scraped_data():
    """Load all scraped JSON data into memory."""
    log("Loading scraped JSON data...")
    data = {}
    files = list(SCRAPED_DIR.glob('*.json'))
    
    for i, f in enumerate(files):
        if i % 500 == 0:
            log_progress(i, len(files), "loading")
        
        name = f.stem
        plan_id = name.split('-', 1)[1] if '-' in name else name
        
        try:
            with open(f) as fp:
                data[plan_id] = json.load(fp)
        except Exception as e:
            pass  # Skip invalid files
    
    print()  # New line after progress bar
    log(f"  Loaded {len(data):,} plan records")
    return data

def build_mock_api(complete_states, plan_counties, county_fips, scraped_data):
    """Build mock_api directory structure for complete states."""
    log("Building mock_api structure...")
    
    for i, (state_name, abbrev, plan_count) in enumerate(complete_states):
        log_progress(i + 1, len(complete_states), f"{abbrev}")
        
        state_dir = MOCK_API_DIR / abbrev
        state_dir.mkdir(exist_ok=True)
        counties_dir = state_dir / 'counties'
        counties_dir.mkdir(exist_ok=True)
        
        # Build county files
        county_plans = defaultdict(list)
        for plan_id, counties in plan_counties[state_name].items():
            if plan_id in scraped_data:
                for county in counties:
                    county_plans[county].append(scraped_data[plan_id])
        
        for county, plans in county_plans.items():
            county_file = counties_dir / f'{county.replace(" ", "_")}.json'
            with open(county_file, 'w') as f:
                json.dump(plans, f)
        
        # Build api_info.json
        api_info = {
            'state': abbrev,
            'state_name': state_name,
            'type': 'county',
            'plan_count': plan_count,
            'county_count': len(county_plans),
            'counties': [{'name': c, 'fips': county_fips[state_name].get(c, '')} 
                        for c in sorted(county_plans.keys())]
        }
        with open(state_dir / 'api_info.json', 'w') as f:
            json.dump(api_info, f, indent=2)
        
        with open(state_dir / 'zip_to_plans.json', 'w') as f:
            json.dump({}, f)
    
    print()
    log(f"  Built mock_api for {len(complete_states)} states")

def build_static_api(complete_states, scraped_data):
    """Build static API files."""
    log("Building static API files...")
    
    # Load unified ZIP mapping
    with open(UNIFIED_ZIP_FILE) as f:
        unified_zip = json.load(f)
    
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Create directories
    STATIC_API_DIR.mkdir(parents=True, exist_ok=True)
    zip_dir = STATIC_API_DIR / 'zip'
    zip_dir.mkdir(exist_ok=True)
    state_dir = STATIC_API_DIR / 'state'
    state_dir.mkdir(exist_ok=True)
    plan_dir = STATIC_API_DIR / 'plan'
    plan_dir.mkdir(exist_ok=True)
    
    # Load state data from mock_api
    states = {}
    for state_name, abbrev, _ in complete_states:
        if abbrev in TERRITORIES:
            continue
        
        mock_dir = MOCK_API_DIR / abbrev
        if not mock_dir.exists():
            continue
        
        info_file = mock_dir / 'api_info.json'
        if not info_file.exists():
            continue
        
        with open(info_file) as f:
            info = json.load(f)
        
        plans = {}
        counties_dir = mock_dir / 'counties'
        if counties_dir.exists():
            for county_file in counties_dir.glob('*.json'):
                with open(county_file) as f:
                    county_plans = json.load(f)
                    for plan in county_plans:
                        if isinstance(plan, dict):
                            plan_id = plan.get('plan_id', '')
                            if plan_id:
                                plans[plan_id] = plan
        
        states[abbrev] = {'info': info, 'plans': plans}
    
    log(f"  Loaded {len(states)} states from mock_api")
    
    # Generate ZIP files
    log("  Generating ZIP files...")
    zip_count = 0
    zip_items = list(unified_zip.items())
    
    for i, (zip_code, zip_info) in enumerate(zip_items):
        if i % 2000 == 0:
            log_progress(i, len(zip_items), "ZIPs")
        
        # Collect plans for this ZIP
        all_plans = {}
        counties_data = []
        
        for county in zip_info.get('counties', []):
            state = county.get('state')
            if state not in states or state in TERRITORIES:
                continue
            
            county_name = county.get('name', '').replace(' ', '_')
            county_file = MOCK_API_DIR / state / 'counties' / f'{county_name}.json'
            
            if county_file.exists():
                with open(county_file) as f:
                    plans = json.load(f)
                    for plan in plans:
                        if isinstance(plan, dict):
                            pid = plan.get('plan_id', '')
                            if pid and pid not in all_plans:
                                all_plans[pid] = plan
            
            counties_data.append({
                'fips': county.get('fips'),
                'name': county.get('name'),
                'state': state,
                'ratio': county.get('ratio', 1.0),
                'plans_available': len(all_plans) > 0,
                'plan_count': len(all_plans)
            })
        
        if not all_plans:
            continue
        
        # Build response
        plans_list = []
        for p in all_plans.values():
            plan_info = p.get('plan_info', {})
            if isinstance(plan_info, list):
                plan_info = {'name': plan_info[0] if plan_info else ''}
            
            plans_list.append({
                'plan_id': p.get('plan_id', ''),
                'category': get_plan_category(plan_info),
                'plan_type': extract_plan_type(plan_info.get('name', '') if isinstance(plan_info, dict) else ''),
                'plan_info': plan_info,
                'premiums': p.get('premiums', {}),
                'deductibles': p.get('deductibles', {}),
                'maximum_out_of_pocket': p.get('maximum_out_of_pocket', {}),
                'contact_info': p.get('contact_info', {}),
                'benefits': p.get('benefits', {}),
                'drug_coverage': p.get('drug_coverage', {}),
                'extra_benefits': p.get('extra_benefits', {}),
            })
        
        response = {
            'zip_code': zip_code,
            'multi_county': zip_info.get('multi_county', False),
            'multi_state': zip_info.get('multi_state', False),
            'states': zip_info.get('states', []),
            'primary_state': zip_info.get('primary_state'),
            'counties': counties_data,
            'plans': plans_list,
            'plan_count': len(plans_list),
            'generated_at': timestamp
        }
        
        with open(zip_dir / f'{zip_code}.json', 'w') as f:
            json.dump(response, f)
        
        zip_count += 1
    
    print()
    log(f"  Generated {zip_count:,} ZIP files")
    
    # Generate state files
    log("  Generating state files...")
    for abbrev, state_data in states.items():
        if abbrev in TERRITORIES:
            continue
        
        state_out = state_dir / abbrev
        state_out.mkdir(exist_ok=True)
        
        info = state_data['info']
        plans = state_data['plans']
        
        # info.json
        with open(state_out / 'info.json', 'w') as f:
            json.dump({
                'state_code': abbrev,
                'state_name': info.get('state_name', ''),
                'plan_count': len(plans),
                'county_count': info.get('county_count', 0),
                'counties': info.get('counties', []),
                'generated_at': timestamp
            }, f, indent=2)
        
        # plans.json
        with open(state_out / 'plans.json', 'w') as f:
            json.dump({
                'state_code': abbrev,
                'plans': [get_plan_summary(p) for p in plans.values()],
                'generated_at': timestamp
            }, f)
    
    log(f"  Generated state files for {len(states)} states")
    
    # Generate plan files
    log("  Generating plan files...")
    all_plans = {}
    for state_data in states.values():
        for plan_id, plan in state_data['plans'].items():
            if plan_id not in all_plans:
                all_plans[plan_id] = plan
    
    for plan_id, plan in all_plans.items():
        with open(plan_dir / f'{plan_id}.json', 'w') as f:
            json.dump(plan, f)
    
    log(f"  Generated {len(all_plans):,} plan files")
    
    # Generate states index
    log("  Generating states.json...")
    states_list = []
    for abbrev, state_data in sorted(states.items()):
        if abbrev in TERRITORIES:
            continue
        info = state_data['info']
        states_list.append({
            'abbrev': abbrev,
            'name': info.get('state_name', ''),
            'type': info.get('type', 'county'),
            'plan_count': len(state_data['plans']),
            'info_url': f'/medicare/state/{abbrev}/info.json',
            'plans_url': f'/medicare/state/{abbrev}/plans.json'
        })
    
    with open(STATIC_API_DIR / 'states.json', 'w') as f:
        json.dump({
            'state_count': len(states_list),
            'total_plans': sum(s['plan_count'] for s in states_list),
            'states': states_list,
            'generated_at': timestamp
        }, f, indent=2)
    
    log(f"  Generated states.json with {len(states_list)} states")
    
    return zip_count, len(states), len(all_plans)

def get_plan_category(plan_info):
    """Determine plan category: MAPD, PD, or MA."""
    if not isinstance(plan_info, dict):
        return 'MAPD'
    
    plan_type = plan_info.get('type', '').lower()
    name = plan_info.get('name', '').lower()
    
    if 'drug plan' in plan_type or 'part d' in plan_type or '(pdp)' in name:
        return 'PD'
    elif 'without drug' in plan_type or 'ma-only' in name:
        return 'MA'
    else:
        return 'MAPD'

def extract_plan_type(name):
    """Extract plan type (HMO, PPO, etc.) from plan name."""
    if not name:
        return None
    
    name_upper = name.upper()
    for plan_type in ['HMO-POS', 'PPO', 'HMO', 'PDP', 'PFFS', 'MSA']:
        if plan_type in name_upper:
            return plan_type
    return None

def get_plan_summary(plan):
    """Extract summary from a plan."""
    plan_info = plan.get('plan_info', {})
    if isinstance(plan_info, list):
        plan_info = {'name': plan_info[0] if plan_info else ''}
    
    premiums = plan.get('premiums', {})
    deductibles = plan.get('deductibles', {})
    
    return {
        'plan_id': plan.get('plan_id', ''),
        'plan_name': plan_info.get('name', '') if isinstance(plan_info, dict) else '',
        'organization': plan_info.get('organization', '') if isinstance(plan_info, dict) else '',
        'monthly_premium': premiums.get('Total monthly premium', ''),
    }

def upload_to_s3(dry_run=False):
    """Upload static API to S3."""
    log("Uploading to S3...")
    
    if dry_run:
        log("  [DRY RUN] Would upload to s3://{S3_BUCKET}/")
        return True
    
    cmd = [
        'aws', 's3', 'sync',
        './static_api/',
        f's3://{S3_BUCKET}/',
        '--delete'
    ]
    
    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start
    
    if result.returncode == 0:
        log(f"  ✅ Upload complete in {elapsed:.1f}s")
        return True
    else:
        log(f"  ❌ Upload failed: {result.stderr}", level='ERROR')
        return False

def invalidate_cloudfront(dry_run=False):
    """Invalidate CloudFront cache."""
    log("Invalidating CloudFront cache...")
    
    if dry_run:
        log("  [DRY RUN] Would invalidate CloudFront distribution")
        return True
    
    cmd = [
        'aws', 'cloudfront', 'create-invalidation',
        '--distribution-id', CLOUDFRONT_DIST_ID,
        '--paths', '/*'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        log("  ✅ Cache invalidation started")
        return True
    else:
        log(f"  ⚠ Cache invalidation failed (non-critical): {result.stderr}", level='WARN')
        return False

def main():
    parser = argparse.ArgumentParser(description='Deploy Medicare API')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    parser.add_argument('--skip-upload', action='store_true', help='Build only, no S3 upload')
    args = parser.parse_args()
    
    print("=" * 60)
    print("MEDICARE API DEPLOYMENT")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if args.dry_run:
        print("[DRY RUN MODE]")
    print("=" * 60)
    print()
    
    start_time = time.time()
    
    # Step 1: Load data
    scraped = get_scraped_plan_ids()
    state_plans, plan_counties, county_fips = get_landscape_data()
    
    # Step 2: Find complete states
    complete_states = find_complete_states(scraped, state_plans)
    
    if not complete_states:
        log("No complete states found!", level='ERROR')
        return 1
    
    # Step 3: Load scraped data
    scraped_data = load_scraped_data()
    
    # Step 4: Build mock_api
    build_mock_api(complete_states, plan_counties, county_fips, scraped_data)
    
    # Step 5: Build static API
    zip_count, state_count, plan_count = build_static_api(complete_states, scraped_data)
    
    # Step 6: Upload to S3
    if not args.skip_upload:
        if not upload_to_s3(args.dry_run):
            return 1
        
        # Step 7: Invalidate CloudFront
        invalidate_cloudfront(args.dry_run)
    else:
        log("Skipping S3 upload (--skip-upload)")
    
    elapsed = time.time() - start_time
    
    print()
    print("=" * 60)
    print("DEPLOYMENT COMPLETE!")
    print("=" * 60)
    print(f"  States: {state_count}")
    print(f"  ZIP files: {zip_count:,}")
    print(f"  Plan files: {plan_count:,}")
    print(f"  Time: {elapsed:.1f}s")
    print()
    print("API URL: https://medicare.purlpal-api.com/medicare/")
    print("=" * 60)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
