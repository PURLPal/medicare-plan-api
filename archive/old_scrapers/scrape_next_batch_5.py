#!/usr/bin/env python3
"""
Scrape next batch of 5 smallest states
- Virgin Islands (1 plan)
- American Samoa (1 plan)
- Connecticut (58 plans)
- Maine (61 plans)
- Nebraska (65 plans)
Total: 186 plans, ~74 minutes
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
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
]
WINDOW_SIZES = ['1920,1080', '1366,768', '1536,864', '1440,900']

def create_driver():
    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--disable-blink-features=AutomationControlled')
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
    
    data = {
        'plan_info': {}, 'premiums': {}, 'deductibles': {}, 'maximum_out_of_pocket': {},
        'contact_info': {}, 'benefits': {}, 'drug_coverage': {}, 'extra_benefits': {}
    }
    
    # Extract plan header info
    hdr = soup.find('div', class_='PlanDetailsPagePlanInfo')
    if hdr:
        h1 = hdr.find('h1')
        if h1: data['plan_info']['name'] = h1.get_text(strip=True)
        for li in hdr.find_all('li'):
            t = li.get_text()
            if 'Plan ID:' in t: data['plan_info']['id'] = t.replace('Plan ID:', '').strip()
    
    # Extract tables
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

def scrape_plan(plan, state):
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

# States to scrape
states_to_scrape = [
    ('Virgin_Islands', 'state_data/Virgin_Islands.json'),
    ('American_Samoa', 'state_data/American_Samoa.json'),
    ('Connecticut', 'state_data/Connecticut.json'),
    ('Maine', 'state_data/Maine.json'),
    ('Nebraska', 'state_data/Nebraska.json')
]

print('='*80)
print('SCRAPING NEXT 5 STATES')
print('='*80)
print()

# Load all plans and check what's already scraped
all_plans = []
scraped_files = set(os.listdir('scraped_json_all'))

for state, filepath in states_to_scrape:
    with open(filepath) as f:
        plans = json.load(f)
    
    # Filter out already scraped plans
    missing_plans = []
    for plan in plans:
        filename = f"{state}-{plan['ContractPlanSegmentID']}.json"
        if filename not in scraped_files:
            missing_plans.append(plan)
    
    for plan in missing_plans:
        all_plans.append((state, plan))
    
    status = '✅ Complete' if len(missing_plans) == 0 else f'{len(missing_plans)} to scrape'
    print(f'{state:30s} {len(plans):3d} total, {status}')

print()
print('='*80)
print(f'TOTAL TO SCRAPE: {len(all_plans)} plans')
print(f'Estimated time: {len(all_plans) * 0.4:.0f} minutes ({len(all_plans) * 0.4 / 60:.1f} hours)')
print('='*80)
print()

if len(all_plans) == 0:
    print('🎉 All states already complete!')
    exit(0)

# Start scraping
results = []
success_count = 0
start_time = time.time()

for i, (state, plan) in enumerate(all_plans, 1):
    plan_name = plan['Plan Name'][:50]
    print(f"[{i}/{len(all_plans)}] [{state}] {plan['ContractPlanSegmentID']}: {plan_name}")
    
    result = scrape_plan(plan, state)
    results.append(result)
    
    if result['success']:
        success_count += 1
        print(f"  ✓")
    else:
        print(f"  ✗ {result.get('error', '')[:60]}")
    
    # Progress update every 10 plans
    if i % 10 == 0:
        elapsed = time.time() - start_time
        rate = i / elapsed if elapsed > 0 else 0
        eta = (len(all_plans) - i) / rate if rate > 0 else 0
        print(f"  Progress: {success_count}/{i} | ETA: {eta/60:.1f} min")
    
    # Delay before next plan (except for last one)
    if i < len(all_plans):
        time.sleep(random.uniform(10, 15))

# Final summary
elapsed_total = time.time() - start_time
print()
print('='*80)
print(f"SCRAPING COMPLETE!")
print(f"  Success: {success_count}/{len(all_plans)} ({success_count/len(all_plans)*100:.1f}%)")
print(f"  Time: {elapsed_total/60:.1f} minutes")
print(f"  Rate: {len(all_plans)/(elapsed_total/60):.1f} plans/minute")
print('='*80)

# Summary by state
print()
print('Results by state:')
by_state = {}
for r in results:
    s = r['state']
    if s not in by_state:
        by_state[s] = {'success': 0, 'failed': 0}
    if r['success']:
        by_state[s]['success'] += 1
    else:
        by_state[s]['failed'] += 1

for state in ['Virgin_Islands', 'American_Samoa', 'Connecticut', 'Maine', 'Nebraska']:
    if state in by_state:
        counts = by_state[state]
        status = '✅' if counts['failed'] == 0 else '⚠️'
        print(f"  {status} {state:30s} {counts['success']} succeeded, {counts['failed']} failed")

# Save results
with open('./batch5_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f"\nResults saved to: batch5_results.json")
