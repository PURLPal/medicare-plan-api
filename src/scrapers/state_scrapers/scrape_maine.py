#!/usr/bin/env python3
"""Maine - 61 plans"""
import json, time, random
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

def scrape(plan):
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
        with open(html_dir / f"Maine-{pid}.html", 'w') as f: f.write(html)
        data = extract_data(html)
        with open(json_dir / f"Maine-{pid}.json", 'w') as f: json.dump(data, f, indent=2)
        return {'success': True, 'plan_id': pid}
    except Exception as e:
        return {'success': False, 'plan_id': pid, 'error': str(e)[:200]}
    finally:
        if driver:
            try: driver.quit()
            except: pass

with open('./state_data/Maine.json') as f: plans = json.load(f)
print(f"{'='*80}\nMAINE - {len(plans)} plans\n{'='*80}")
results, ok = [], 0
start = time.time()
for i, plan in enumerate(plans, 1):
    print(f"[{i}/{len(plans)}] {plan['ContractPlanSegmentID']}: {plan['Plan Name'][:50]}")
    r = scrape(plan)
    results.append(r)
    if r['success']: ok += 1; print(f"  ✓")
    else: print(f"  ✗ {r.get('error', '')[:50]}")
    if i < len(plans): time.sleep(random.uniform(10, 15))
    if i % 5 == 0:
        elapsed = time.time() - start
        eta = (len(plans) - i) / (i / elapsed) if i > 0 else 0
        print(f"  Progress: {ok}/{i} | ETA: {eta/60:.1f} min")
print(f"\n{'='*80}\nDONE! {ok}/{len(plans)} in {(time.time()-start)/60:.1f} min\n{'='*80}")
with open('./maine_results.json', 'w') as f: json.dump(results, f, indent=2)
