#!/usr/bin/env python3
"""Quick retry for single Hawaii plan"""
import json, time, random
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re

html_dir, json_dir = Path('./scraped_html_all'), Path('./scraped_json_all')
html_dir.mkdir(exist_ok=True); json_dir.mkdir(exist_ok=True)

USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

def create_driver():
    opts = Options()
    opts.add_argument('--headless=new'); opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-gpu'); opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_argument('--window-size=1920,1080')
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

# Load Hawaii state data
with open('state_data/Hawaii.json') as f:
    hawaii_plans = json.load(f)

# Find the missing plan
target_plan = None
for plan in hawaii_plans:
    if plan['ContractPlanSegmentID'] == 'H2406_058_0':
        target_plan = plan
        break

if not target_plan:
    print("Plan not found!")
    exit(1)

print("Retrying Hawaii plan: H2406_058_0")
print(f"Plan: {target_plan['Plan Name']}")
print(f"URL: {target_plan['url']}")
print()

driver = None
try:
    driver = create_driver()
    time.sleep(random.uniform(8, 12))
    driver.get(target_plan['url'])
    wait = WebDriverWait(driver, 45)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
    driver.execute_script(f"window.scrollBy(0, {random.randint(100, 500)})")
    time.sleep(random.uniform(0.5, 1.5))
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "mct-c-table")))
    time.sleep(random.uniform(3, 6))
    html = driver.page_source
    with open(html_dir / "Hawaii-H2406_058_0.html", 'w') as f: f.write(html)
    data = extract_data(html)
    with open(json_dir / "Hawaii-H2406_058_0.json", 'w') as f: json.dump(data, f, indent=2)
    print("✅ SUCCESS! Plan scraped and saved.")
except Exception as e:
    print(f"❌ FAILED: {e}")
finally:
    if driver:
        try: driver.quit()
        except: pass
