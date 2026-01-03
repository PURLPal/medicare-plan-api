#!/usr/bin/env python3
"""
Thoroughly check for existing Massachusetts data in all possible locations
"""
import json
from pathlib import Path

print("="*80)
print("SEARCHING FOR EXISTING MASSACHUSETTS DATA")
print("="*80)
print()

# 1. Check scraped_json_all
print("1. SCRAPED JSON FILES")
print("-" * 80)
scraped_dir = Path('scraped_json_all')
if scraped_dir.exists():
    ma_files = list(scraped_dir.glob('Massachusetts-*.json'))
    print(f"Massachusetts files found: {len(ma_files)}")
    
    if ma_files:
        print("\nFiles:")
        for f in sorted(ma_files):
            with open(f) as fp:
                data = json.load(fp)
            plan_id = data.get('plan_id', 'Unknown')
            name = data.get('plan_info', {}).get('name', 'Unknown')[:60]
            has_data = len(data.get('premiums', {})) > 0 or len(data.get('benefits', {})) > 0
            status = "✓" if has_data else "✗"
            print(f"  {status} {plan_id}: {name}")
else:
    print("scraped_json_all directory not found")

# 2. Check state_data
print()
print("2. STATE DATA DIRECTORY")
print("-" * 80)
state_data = Path('state_data')
if state_data.exists():
    ma_state = state_data / 'MA'
    if ma_state.exists():
        files = list(ma_state.glob('*.json'))
        print(f"✓ state_data/MA/ exists with {len(files)} files")
        if files:
            for f in sorted(files)[:5]:
                print(f"  • {f.name}")
    else:
        print("✗ state_data/MA/ does not exist")
        
    # Check for any MA-related files
    ma_files = list(state_data.glob('*MA*')) + list(state_data.glob('*massachusetts*'))
    if ma_files:
        print(f"\nOther MA-related files: {len(ma_files)}")
        for f in ma_files[:5]:
            print(f"  • {f}")
else:
    print("state_data directory not found")

# 3. Check mock_api
print()
print("3. MOCK API DIRECTORY")
print("-" * 80)
mock_api = Path('mock_api')
if mock_api.exists():
    ma_mock = mock_api / 'MA'
    if ma_mock.exists():
        print(f"✓ mock_api/MA/ exists")
        api_info = ma_mock / 'api_info.json'
        if api_info.exists():
            with open(api_info) as f:
                info = json.load(f)
            print(f"  Plans: {info.get('total_plans', 0)}")
            print(f"  Counties: {info.get('total_counties', 0)}")
    else:
        print("✗ mock_api/MA/ does not exist")
else:
    print("mock_api directory not found")

# 4. Check for landscape/CSV files
print()
print("4. CMS LANDSCAPE DATA")
print("-" * 80)

# Look for landscape files
landscape_dirs = [
    Path('CY2026_Landscape_202511'),
    Path('.'),
]

landscape_file = None
for d in landscape_dirs:
    if d.exists():
        csv_files = list(d.glob('*landscape*.csv')) + list(d.glob('*Landscape*.csv'))
        if csv_files:
            landscape_file = csv_files[0]
            break

if landscape_file and landscape_file.exists():
    print(f"✓ Found landscape file: {landscape_file.name}")
    
    # Count MA plans
    import csv
    ma_plans = []
    with open(landscape_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            state = row.get('State', '').strip()
            if state == 'MA' or state == 'Massachusetts':
                plan_id = row.get('Contract ID', '') + '_' + row.get('Plan ID', '') + '_' + row.get('Segment ID', '')
                plan_name = row.get('Plan Name', '')
                ma_plans.append((plan_id, plan_name))
    
    print(f"✓ Massachusetts plans in landscape file: {len(ma_plans)}")
    
    if ma_plans:
        print("\nSample plans:")
        for plan_id, name in sorted(ma_plans)[:10]:
            print(f"  • {plan_id}: {name[:60]}")
        
        if len(ma_plans) > 10:
            print(f"  ... and {len(ma_plans) - 10} more")
else:
    print("✗ No landscape file found")
    print("\nChecking for any CSV files...")
    csv_files = list(Path('.').glob('*.csv'))
    if csv_files:
        print(f"Found {len(csv_files)} CSV files:")
        for f in csv_files[:5]:
            print(f"  • {f.name}")

print()
print("="*80)
print("SUMMARY")
print("="*80)
print()

# Count what we have
scraped_count = len(list(Path('scraped_json_all').glob('Massachusetts-*.json'))) if Path('scraped_json_all').exists() else 0
mock_exists = Path('mock_api/MA').exists()
landscape_count = len(ma_plans) if landscape_file and landscape_file.exists() else 0

print(f"Scraped plans: {scraped_count}")
print(f"Mock API exists: {mock_exists}")
print(f"Landscape plans: {landscape_count}")
print()

if scraped_count == 0:
    print("❌ NO MASSACHUSETTS DATA FOUND")
    print()
    if landscape_count > 0:
        print(f"✓ Landscape file shows {landscape_count} MA plans available to scrape")
        print()
        print("RECOMMENDATION: Proceed with scraping Massachusetts")
    else:
        print("⚠️  No landscape data found - need to locate CMS landscape file first")
elif scraped_count < landscape_count * 0.5:
    print(f"⚠️  PARTIAL DATA: {scraped_count}/{landscape_count} plans scraped")
    print()
    print("RECOMMENDATION: Scrape missing plans")
else:
    print(f"✓ GOOD COVERAGE: {scraped_count}/{landscape_count} plans")
    print()
    print("RECOMMENDATION: Build and deploy API")

print()
print("="*80)
