#!/usr/bin/env python3
"""
Recovery scraper for crash - 6 states (4 complete + 2 partial)
Total: ~189 plans to recover in ~76 minutes
"""
import json, time, random, os
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re

MIN_DELAY, MAX_DELAY = 8.0, 15.0
html_dir, json_dir = Path('./scraped_html_all'), Path('./scraped_json_all')
html_dir.mkdir(exist_ok=True); json_dir.mkdir(exist_ok=True)

USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]
WINDOW_SIZES = ['1920,1080', '1366,768', '1536,864']

def create_driver():
    opts = Options()
    opts.add_argument('--headless=new'); opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-gpu'); opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_argument(f'--window-size={random.choice(WINDOW_SIZES)}')
    opts.add_argument(f'--user-agent={random.choice(USER_AGENTS)}')
    opts.add_experimental_option('prefs', {'profile.default_content_setting_values': {'images': 2}})
    d = webdriver.Chrome(options=opts)
    d.set_page_load_timeout(60)
    return d

def extract_data(html):
    soup = BeautifulSoup(html, 'html.parser')
    for br in soup.find_all('br'): br.replace_with('\n')
    data = {'plan_info': {}, 'premiums': {}, 'deductibles': {}, 'maximum_out_of_pocket': {},
            'contact_info': {}, 'benefits': {}, 'drug_coverage': {}, 'extra_benefits': {}}
    hdr = soup.find('div', class_='PlanDetailsPagePlanInfo')
    if hdr:
        h1 = hdr.find('h1')
        if h1: data['plan_info']['name'] = h1.get_text(strip=True)
        for li in hdr.find_all('li'):
            t = li.get_text()
            if 'Plan ID:' in t: data['plan_info']['id'] = t.replace('Plan ID:', '').strip()
    for tbl in soup.find_all('table', class_='mct-c-table'):
        cap = tbl.find('caption')
        if not cap: continue
        title = cap.get_text(strip=True)
        td = {}
        for row in tbl.find_all('tr'):
            th, tc = row.find('th'), row.find('td')
            if th and tc:
                ht = re.sub(r"What's.*?\?", "", th.get_text(strip=True)).strip()
                ct = re.sub(r'\n\s*\n', '\n', tc.get_text(separator='\n').strip())
                td[ht] = ct
        if 'Premiums' in title: data['premiums'].update(td)
        elif 'Deductibles' in title: data['deductibles'].update(td)
        elif 'Maximum you pay' in title: data['maximum_out_of_pocket'].update(td)
        elif 'Contact Information' in title: data['contact_info'].update(td)
        elif 'Drug' in title: data['drug_coverage'][title] = td
        else: data['benefits'][title] = td
    return data

def scrape(plan, state):
    pid = plan['ContractPlanSegmentID']
    driver = None
    try:
        driver = create_driver()
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY) + random.uniform(0, 2))
        driver.get(plan['url'])
        wait = WebDriverWait(driver, 45)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        driver.execute_script(f"window.scrollBy(0, {random.randint(100, 500)})")
        time.sleep(random.uniform(0.5, 1.5))
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "mct-c-table")))
        time.sleep(random.uniform(3, 6))
        html = driver.page_source
        with open(html_dir / f"{state}-{pid}.html", 'w') as f: f.write(html)
        data = extract_data(html)
        with open(json_dir / f"{state}-{pid}.json", 'w') as f: json.dump(data, f, indent=2)
        return {'success': True, 'plan_id': pid, 'state': state}
    except Exception as e:
        return {'success': False, 'plan_id': pid, 'state': state, 'error': str(e)[:200]}
    finally:
        if driver:
            try: driver.quit()
            except: pass

# Load states to recover
states_to_recover = {
    'Hawaii': 'state_data/Hawaii.json',
    'Montana': 'state_data/Montana.json',
    'North_Dakota': 'state_data/North_Dakota.json',
    'South_Dakota': 'state_data/South_Dakota.json',
    'Delaware': 'state_data/Delaware.json',
    'Rhode_Island': 'state_data/Rhode_Island.json'
}

# Identify missing plans
all_missing = []
scraped_files = os.listdir('scraped_json_all')

print('='*80)
print('CRASH RECOVERY - IDENTIFYING MISSING PLANS')
print('='*80)
print()

for state, filepath in states_to_recover.items():
    # Try multiple possible paths
    possible_paths = [
        filepath,
        f'state_data/{state}.json',
        f'CY2026_Landscape_202511/state_data/{state}.json'
    ]
    
    state_file = None
    for path in possible_paths:
        if os.path.exists(path):
            state_file = path
            break
    
    if not state_file:
        print(f'⚠️  {state}: Cannot find source file, skipping')
        continue
    
    with open(state_file) as f:
        all_plans = json.load(f)
    
    scraped_ids = [f.replace(f'{state}-', '').replace('.json', '') 
                   for f in scraped_files if f.startswith(f'{state}-')]
    
    missing = [p for p in all_plans if p['ContractPlanSegmentID'] not in scraped_ids]
    
    if missing:
        all_missing.extend([(state, p) for p in missing])
        print(f'{state:20s} Missing: {len(missing):3d}/{len(all_plans):3d} plans')
    else:
        print(f'{state:20s} ✅ Complete ({len(all_plans)} plans)')

print()
print('='*80)
print(f'TOTAL TO RECOVER: {len(all_missing)} plans')
print(f'Estimated time: {len(all_missing) * 0.4:.0f} minutes ({len(all_missing) * 0.4 / 60:.1f} hours)')
print('='*80)
print()

if len(all_missing) == 0:
    print('🎉 Nothing to recover! All states are complete.')
    exit(0)

# Start recovery
results, ok = [], 0
start = time.time()

for i, (state, plan) in enumerate(all_missing, 1):
    print(f"[{i}/{len(all_missing)}] [{state}] {plan['ContractPlanSegmentID']}: {plan['Plan Name'][:45]}")
    r = scrape(plan, state)
    results.append(r)
    if r['success']:
        ok += 1
        print(f"  ✓")
    else:
        print(f"  ✗ {r.get('error', '')[:50]}")
    
    if i < len(all_missing):
        time.sleep(random.uniform(10, 15))
    
    if i % 10 == 0:
        elapsed = time.time() - start
        rate = i / elapsed
        eta = (len(all_missing) - i) / rate if rate > 0 else 0
        print(f"  Progress: {ok}/{i} | ETA: {eta/60:.1f} min")

print(f"\n{'='*80}")
print(f"RECOVERY COMPLETE! {ok}/{len(all_missing)} succeeded in {(time.time()-start)/60:.1f} min")
print(f"{'='*80}")

# Summary by state
by_state = {}
for r in results:
    s = r['state']
    if s not in by_state: by_state[s] = {'success': 0, 'failed': 0}
    if r['success']: by_state[s]['success'] += 1
    else: by_state[s]['failed'] += 1

print('\nResults by state:')
for state, counts in sorted(by_state.items()):
    print(f"  {state:20s} {counts['success']} succeeded, {counts['failed']} failed")

with open('./recovery_results.json', 'w') as f: json.dump(results, f, indent=2)
print(f"\nResults saved to: recovery_results.json")
