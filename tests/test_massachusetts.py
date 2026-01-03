#!/usr/bin/env python3
"""
Test Massachusetts Medicare API coverage and data availability
"""
import requests
import json
from pathlib import Path

print("="*80)
print("MASSACHUSETTS MEDICARE API - COVERAGE ANALYSIS")
print("="*80)
print()

# Test multiple MA ZIP codes
ma_zips = {
    '02101': 'Boston - Downtown',
    '02108': 'Boston - Beacon Hill',
    '02109': 'Boston - North End',
    '02110': 'Boston - Financial District',
    '02111': 'Boston - Chinatown',
    '02115': 'Boston - Fenway',
    '02116': 'Boston - Back Bay',
    '02118': 'Boston - South End',
    '02119': 'Boston - Roxbury',
    '02120': 'Boston - Mission Hill',
    '02121': 'Boston - Dorchester',
    '02124': 'Boston - Dorchester',
    '02125': 'Boston - Dorchester',
    '02126': 'Boston - Mattapan',
    '02127': 'Boston - South Boston',
    '02128': 'Boston - East Boston',
    '02129': 'Boston - Charlestown',
    '02130': 'Boston - Jamaica Plain',
    '02131': 'Boston - Roslindale',
    '02132': 'Boston - West Roxbury',
    '02134': 'Boston - Allston',
    '02135': 'Boston - Brighton',
    '02136': 'Boston - Hyde Park',
    '02138': 'Cambridge',
    '02139': 'Cambridge - Central',
    '02140': 'Cambridge - North',
    '02141': 'Cambridge - East',
    '02142': 'Cambridge - Kendall Square',
    '02143': 'Somerville',
    '02144': 'Somerville - Davis Square',
    '02145': 'Somerville - Assembly',
    '02148': 'Malden',
    '02149': 'Everett',
    '02150': 'Chelsea',
    '02151': 'Revere',
    '02152': 'Winthrop',
    '02155': 'Medford',
    '02169': 'Quincy',
    '02170': 'Quincy - Wollaston',
    '01609': 'Worcester',
    '01701': 'Framingham',
    '02740': 'New Bedford',
    '01960': 'Peabody',
    '01852': 'Lowell',
}

print("TESTING LIVE API ENDPOINTS")
print("-" * 80)

accessible = []
not_found = []
empty = []
errors = []

for zip_code, location in sorted(ma_zips.items()):
    url = f'https://medicare.purlpal-api.com/medicare/zip/{zip_code}.json'
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            plan_count = data.get('plan_count', 0)
            if plan_count > 0:
                accessible.append((zip_code, location, plan_count))
                print(f"✓ {zip_code} ({location}): {plan_count} plans")
            else:
                empty.append((zip_code, location))
                print(f"⚠️  {zip_code} ({location}): 0 plans (empty)")
        elif response.status_code == 404:
            not_found.append((zip_code, location))
            print(f"✗ {zip_code} ({location}): 404 Not Found")
        else:
            errors.append((zip_code, location, response.status_code))
            print(f"✗ {zip_code} ({location}): HTTP {response.status_code}")
    except Exception as e:
        errors.append((zip_code, location, str(e)[:40]))
        print(f"✗ {zip_code} ({location}): Error - {str(e)[:40]}")

print()
print("="*80)
print("CHECKING LOCAL DATA")
print("="*80)
print()

# Check scraped data
print("Scraped Data:")
print("-" * 80)
scraped_dir = Path('scraped_json_all')
ma_scraped = list(scraped_dir.glob('Massachusetts-*.json')) if scraped_dir.exists() else []
print(f"Massachusetts plan files: {len(ma_scraped)}")

if ma_scraped:
    print("\nSample files:")
    for f in sorted(ma_scraped)[:10]:
        with open(f) as fp:
            data = json.load(fp)
        plan_id = data.get('plan_id', 'Unknown')
        name = data.get('plan_info', {}).get('name', 'Unknown')[:50]
        print(f"  • {plan_id}: {name}")
else:
    print("  No Massachusetts scraped data found")

# Check mock_api
print()
print("Mock API Data:")
print("-" * 80)
mock_ma = Path('mock_api/MA')
if mock_ma.exists():
    api_info = mock_ma / 'api_info.json'
    if api_info.exists():
        with open(api_info) as f:
            info = json.load(f)
        print(f"✓ mock_api/MA/ exists")
        print(f"  Plans: {info.get('total_plans', 0)}")
        print(f"  Counties: {info.get('total_counties', 0)}")
        
        zip_to_plans = mock_ma / 'zip_to_plans.json'
        if zip_to_plans.exists():
            with open(zip_to_plans) as f:
                mapping = json.load(f)
            print(f"  ZIP mappings: {len(mapping)}")
    else:
        print(f"✓ mock_api/MA/ exists but no api_info.json")
else:
    print("✗ mock_api/MA/ does not exist")

# Check static_api
print()
print("Static API Files:")
print("-" * 80)
static_zip_dir = Path('static_api/medicare/zip')
if static_zip_dir.exists():
    # Check if any MA ZIP files exist
    ma_api_files = [f for f in static_zip_dir.glob('0*.json')]
    print(f"Files starting with '0' (MA range): {len(ma_api_files)}")
    
    if ma_api_files:
        # Check a sample
        sample = ma_api_files[0]
        with open(sample) as f:
            data = json.load(f)
        if 'MA' in data.get('states', []) or data.get('primary_state') == 'MA':
            print(f"✓ Found MA data in static_api")
        else:
            print(f"⚠️  Files exist but may not be MA")
else:
    print("⚠️  static_api/medicare/zip/ not found (may be gitignored)")

print()
print("="*80)
print("SUMMARY")
print("="*80)
print()

print(f"Tested ZIP codes: {len(ma_zips)}")
print(f"✓ Accessible with data: {len(accessible)}")
print(f"⚠️  Accessible but empty: {len(empty)}")
print(f"✗ Not found (404): {len(not_found)}")
print(f"✗ Errors: {len(errors)}")
print()

if accessible:
    print("TOP ACCESSIBLE ZIP CODES:")
    print("-" * 80)
    for zip_code, location, count in sorted(accessible, key=lambda x: x[2], reverse=True)[:10]:
        print(f"  {zip_code} ({location}): {count} plans")
    print()

print("="*80)
print("DIAGNOSIS")
print("="*80)
print()

if not accessible and not_found:
    print("❌ MASSACHUSETTS IS NOT DEPLOYED")
    print()
    print("All tested ZIP codes return 404 Not Found.")
    print()
    if ma_scraped:
        print(f"However, {len(ma_scraped)} Massachusetts plans have been scraped.")
        print("The data exists but the API has not been built/deployed for MA.")
        print()
        print("TO DEPLOY MASSACHUSETTS:")
        print("1. Run: python3 build_static_api.py")
        print("2. Deploy to S3")
        print("3. Invalidate CloudFront cache")
    else:
        print("No scraped data found. Massachusetts needs to be scraped first.")
        print()
        print("TO GET MASSACHUSETTS DATA:")
        print("1. Add MA to scraping pipeline")
        print("2. Scrape all MA Medicare plans")
        print("3. Build and deploy API")
elif accessible:
    print(f"✅ MASSACHUSETTS IS PARTIALLY ACCESSIBLE")
    print()
    print(f"{len(accessible)} ZIP codes have data available.")
    print(f"Coverage: {len(accessible)/len(ma_zips)*100:.1f}%")
elif empty:
    print("⚠️  MASSACHUSETTS ENDPOINTS EXIST BUT ARE EMPTY")
    print()
    print("API files exist but contain 0 plans.")
    print("This suggests the API was built but no plans were found for MA ZIPs.")

print()
print("="*80)
