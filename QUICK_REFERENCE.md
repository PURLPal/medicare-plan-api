# Quick Reference: Scraping & API Build

## 1. Check Data Quality

```bash
# Analyze scraped data by state
python3 << 'EOF'
import json
from pathlib import Path
from collections import defaultdict

files = list(Path('scraped_json_all').glob('*.json'))
states = defaultdict(lambda: {'total': 0, 'has_name': 0, 'has_premiums': 0})

for f in files:
    fname = f.stem
    if '-' in fname:
        state = fname.split('-')[0]
    else:
        continue
    
    try:
        with open(f) as fp:
            d = json.load(fp)
    except:
        continue
    
    states[state]['total'] += 1
    name = d.get('plan_info', {}).get('name', '')
    if name and name.lower() != 'menu':
        states[state]['has_name'] += 1
    
    if d.get('premiums', {}):
        states[state]['has_premiums'] += 1

print(f"{'State':<25} {'Total':>6} {'Names':>7} {'Premiums':>9} {'Quality':>10}")
print('-' * 65)

for state in sorted(states.keys()):
    s = states[state]
    if s['total'] == 0:
        continue
    name_pct = s['has_name'] / s['total'] * 100
    prem_pct = s['has_premiums'] / s['total'] * 100
    
    if name_pct >= 90 and prem_pct >= 50:
        quality = 'GREAT ✓'
    elif name_pct >= 90:
        quality = 'GOOD'
    else:
        quality = 'POOR'
    
    print(f"{state:<25} {s['total']:>6} {name_pct:>6.0f}% {prem_pct:>8.0f}% {quality:>10}")
EOF
```

## 2. Build Static API

```bash
# Build all API files from scraped data
python3 build_static_api.py

# Check output
ls -lh static_api/medicare/
ls static_api/medicare/state/
```

Expected output:
- `states.json` - Index file
- `zip/` - 39,298 ZIP code files
- `state/` - 26+ state directories
- `plan/` - 2,630+ plan files

## 3. Test API Locally

```bash
# Start a local server
cd static_api
python3 -m http.server 8000

# Test in another terminal
curl http://localhost:8000/medicare/zip/50316.json | jq '.plans | length'
curl http://localhost:8000/medicare/states.json | jq '.state_count'
```

## 4. Deploy to Production

```bash
# Sync to S3 (destructive - removes old files)
aws s3 sync static_api/ s3://purlpal-medicare-api/ \
  --delete \
  --cache-control "public, max-age=3600"

# Check upload
aws s3 ls s3://purlpal-medicare-api/medicare/ --recursive | head -20

# Invalidate CloudFront cache (optional, costs $)
aws cloudfront create-invalidation \
  --distribution-id E3SHXUEGZALG4E \
  --paths "/medicare/*"
```

## 5. Test Production API

```bash
# Test GREAT states
python3 test_great_states_api.py

# Manual tests
curl https://medicare.purlpal-api.com/medicare/states.json | jq
curl https://medicare.purlpal-api.com/medicare/zip/50316.json | jq '.plans[0]'
curl https://medicare.purlpal-api.com/medicare/state/IA/info.json | jq
```

## 6. Sample Scraper (For New States)

```python
#!/usr/bin/env python3
"""
Scrape Medicare plans for a specific state.
Usage: python3 scrape_state.py STATE_NAME
"""
import sys
import json
import time
import random
import csv
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from bs4 import BeautifulSoup

# Configuration
MIN_DELAY, MAX_DELAY = 8.0, 15.0
HTML_DIR = Path('./scraped_html_all')
JSON_DIR = Path('./scraped_json_all')
HTML_DIR.mkdir(exist_ok=True)
JSON_DIR.mkdir(exist_ok=True)

def create_driver():
    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_argument('--window-size=1920,1080')
    opts.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
    opts.add_experimental_option('prefs', {'profile.default_content_setting_values': {'images': 2}})
    driver = webdriver.Chrome(options=opts)
    
    stealth(driver,
        languages=['en-US', 'en'],
        vendor='Google Inc.',
        platform='Win32',
        webgl_vendor='Intel Inc.',
        renderer='Intel Iris OpenGL Engine',
        fix_hairline=True,
    )
    
    driver.set_page_load_timeout(60)
    return driver

def scrape_plan(driver, plan_id, contract, plan, segment):
    """Scrape a single plan."""
    url = f"https://www.medicare.gov/plan-compare/#/plan-details/2026-{contract}-{plan}-{segment}?year=2026&lang=en"
    
    try:
        driver.get(url)
        time.sleep(random.uniform(3, 5))
        
        # Wait for plan header
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.e2e-plan-details-plan-header'))
        )
        
        time.sleep(random.uniform(2, 4))
        return driver.page_source
    except Exception as e:
        print(f"  Error: {e}")
        return None

def extract_data(html):
    """Extract data from HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    for br in soup.find_all('br'):
        br.replace_with('\n')
    
    data = {
        'plan_info': {}, 'premiums': {}, 'deductibles': {},
        'maximum_out_of_pocket': {}, 'contact_info': {},
        'benefits': {}, 'drug_coverage': {}, 'extra_benefits': {}
    }
    
    # Get plan name
    plan_header = soup.select_one('h1.e2e-plan-details-plan-header')
    if plan_header:
        data['plan_info']['name'] = plan_header.get_text(strip=True)
    
    # Extract sections using generic selectors
    # (Add full extraction logic from scrape_batch_7.py)
    
    return data

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scrape_state.py STATE_NAME")
        sys.exit(1)
    
    state_name = sys.argv[1]
    
    # Load plans from CSV
    plans = []
    with open('downloaded_data/CY2026_Landscape_202511/CY2026_Landscape_202511.csv', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        seen = set()
        for row in reader:
            if row.get('State Territory Name', '') != state_name:
                continue
            
            plan_id = row.get('ContractPlanSegmentID', '')
            if plan_id in seen:
                continue
            seen.add(plan_id)
            
            plans.append({
                'plan_id': plan_id,
                'contract': row.get('Contract ID', ''),
                'plan': row.get('Plan ID', ''),
                'segment': row.get('Segment ID', '0')
            })
    
    print(f"Found {len(plans)} plans for {state_name}")
    
    driver = create_driver()
    state_abbrev = state_name.replace(' ', '_')
    
    try:
        for i, plan in enumerate(plans, 1):
            plan_id = plan['plan_id']
            json_file = JSON_DIR / f"{state_abbrev}-{plan_id}.json"
            
            if json_file.exists():
                print(f"[{i}/{len(plans)}] {plan_id}: Already scraped")
                continue
            
            print(f"[{i}/{len(plans)}] {plan_id}: Scraping...")
            
            html = scrape_plan(driver, plan_id, plan['contract'], plan['plan'], plan['segment'])
            if html:
                # Save HTML
                html_file = HTML_DIR / f"{state_abbrev}-{plan_id}.html"
                with open(html_file, 'w') as f:
                    f.write(html)
                
                # Extract and save JSON
                data = extract_data(html)
                data['plan_id'] = plan_id
                
                with open(json_file, 'w') as f:
                    json.dump(data, f, indent=2)
                
                print(f"  ✓")
            else:
                print(f"  ✗ Failed")
            
            # Delay
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
            
            # Restart browser periodically
            if i % 25 == 0:
                driver.quit()
                time.sleep(random.uniform(5, 10))
                driver = create_driver()
    
    finally:
        driver.quit()
    
    print(f"\nComplete! Scraped {len(plans)} plans for {state_name}")

if __name__ == '__main__':
    main()
```

## 7. Common Issues

### Issue: Empty JSON files
```bash
# Find and delete empty files
python3 -c "
import json, os
from pathlib import Path
for f in Path('scraped_json_all').glob('*.json'):
    with open(f) as fp:
        d = json.load(fp)
    if not d.get('plan_info', {}).get('name'):
        print(f'Deleting: {f.name}')
        os.remove(f)
"
```

### Issue: API not updating
```bash
# Clear CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id E3SHXUEGZALG4E \
  --paths "/*"
```

### Issue: Wrong state count
```bash
# Check what's actually in static_api
ls static_api/medicare/state/ | wc -l
cat static_api/medicare/states.json | jq '.state_count'
```

## 8. File Naming Conventions

### Scraped Files
- Format: `{State}-{PlanID}.json`
- Example: `Iowa-H5216_413_0.json`
- State: Spaces replaced with underscores
- PlanID: From CSV `ContractPlanSegmentID` field

### API Files
- ZIP: `static_api/medicare/zip/{zipcode}.json`
- State: `static_api/medicare/state/{ST}/`
- Plan: `static_api/medicare/plan/{plan_id}.json`

## 9. Key Files

- `build_static_api.py` - Main API builder
- `scrape_batch_7.py` - Reference working scraper
- `test_great_states_api.py` - API test script
- `SUCCESSFUL_SCRAPING_PROCESS.md` - Full documentation

## 10. Data Sources

- **Landscape CSV**: `downloaded_data/CY2026_Landscape_202511/CY2026_Landscape_202511.csv`
- **ZIP Mapping**: `zip_county_data/unified_zip_to_fips.json`
- **Scraped Data**: `scraped_json_all/`
- **API Output**: `static_api/medicare/`
