#!/usr/bin/env python3
"""
Scrape batch 7 - DC + next smallest US states
- District of Columbia (30 plans)
- Idaho (58 plans)
- Oklahoma (93 plans)
- Minnesota (95 plans)
- Kansas (99 plans)
Total: 375 plans, ~150 minutes (~2.5 hours)
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
        'plan_info': {}, 'premiums': {}, 'deductibles': {},
        'maximum_out_of_pocket': {}, 'contact_info': {},
        'benefits': {}, 'drug_coverage': {}, 'extra_benefits': {}
    }
    
    # Plan info
    if h1 := soup.find('h1'):
        data['plan_info']['name'] = h1.get_text(strip=True)
    for item in soup.select('.plan-info-item, .plan-detail-item'):
        label = item.select_one('.label, .item-label')
        value = item.select_one('.value, .item-value')
        if label and value:
            data['plan_info'][label.get_text(strip=True).rstrip(':')] = value.get_text(strip=True)
    
    # Sections
    section_map = {
        'premium': 'premiums', 'deductible': 'deductibles',
        'maximum out-of-pocket': 'maximum_out_of_pocket',
        'contact': 'contact_info', 'benefit': 'benefits',
        'drug': 'drug_coverage', 'extra': 'extra_benefits'
    }
    
    for section in soup.select('section, .section, .card, .benefit-section'):
        header = section.select_one('h2, h3, .section-header, .card-header')
        if not header: continue
        header_text = header.get_text(strip=True).lower()
        
        target = None
        for key, val in section_map.items():
            if key in header_text:
                target = val
                break
        
        if target:
            if target == 'benefits':
                subsection_name = header.get_text(strip=True)
                subsection_data = {}
                for row in section.select('tr, .benefit-row, .row'):
                    cells = row.select('td, .cell, .col')
                    if len(cells) >= 2:
                        subsection_data[cells[0].get_text(strip=True)] = cells[1].get_text(strip=True)
                if subsection_data:
                    data['benefits'][subsection_name] = subsection_data
            else:
                for row in section.select('tr, .row, .item'):
                    cells = row.select('td, .cell, .col, .label, .value')
                    if len(cells) >= 2:
                        data[target][cells[0].get_text(strip=True).rstrip(':')] = cells[1].get_text(strip=True)
    
    return data

def scrape_plan(driver, url, plan_id):
    try:
        driver.get(url)
        time.sleep(random.uniform(2, 4))
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, 'h1')))
        time.sleep(random.uniform(1, 2))
        return driver.page_source
    except Exception as e:
        print(f"  Error: {e}")
        return None

def main():
    import csv
    from collections import defaultdict
    
    # Load plans from CSV
    states_to_scrape = ['District of Columbia', 'Idaho', 'Oklahoma', 'Minnesota', 'Kansas']
    state_plans = defaultdict(list)
    
    with open('downloaded_data/CY2026_Landscape_202511/CY2026_Landscape_202511.csv', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        seen = set()
        for row in reader:
            state = row.get('State Territory Name', '')
            if state not in states_to_scrape:
                continue
            
            plan_id = row.get('ContractPlanSegmentID', '')
            if not plan_id or plan_id in seen:
                continue
            seen.add(plan_id)
            
            contract_id = row.get('Contract ID', '')
            plan_num = row.get('Plan ID', '')
            segment = row.get('Segment ID', '0')
            
            url = f"https://www.medicare.gov/plan-compare/#/plan-details/{contract_id}-{plan_num}-{segment}"
            state_plans[state].append({'plan_id': plan_id, 'url': url, 'state': state})
    
    # Build full list
    all_plans = []
    for state in states_to_scrape:
        all_plans.extend(state_plans[state])
    
    print(f"Total plans to scrape: {len(all_plans)}")
    for state in states_to_scrape:
        print(f"  {state}: {len(state_plans[state])} plans")
    print()
    
    driver = create_driver()
    start_time = time.time()
    
    try:
        for i, plan in enumerate(all_plans, 1):
            plan_id = plan['plan_id']
            state = plan['state'].replace(' ', '_')
            url = plan['url']
            
            # Check if already scraped
            json_file = json_dir / f"{state}_{plan_id}.json"
            if json_file.exists():
                print(f"[{i}/{len(all_plans)}] [{state}] {plan_id}: Already scraped, skipping")
                continue
            
            elapsed = time.time() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            eta = (len(all_plans) - i) / rate / 60 if rate > 0 else 0
            
            print(f"[{i}/{len(all_plans)}] [{state}] {plan_id}: {plan['url'][:60]}...")
            print(f"  Progress: {i}/{len(all_plans)} | ETA: {eta:.1f} min")
            
            html = scrape_plan(driver, url, plan_id)
            if html:
                # Save HTML
                html_file = html_dir / f"{state}_{plan_id}.html"
                with open(html_file, 'w') as f:
                    f.write(html)
                
                # Extract and save JSON
                data = extract_data(html)
                data['plan_id'] = plan_id
                data['url'] = url
                data['state'] = state
                
                with open(json_file, 'w') as f:
                    json.dump(data, f, indent=2)
                
                print(f"  ✓")
            else:
                print(f"  ✗ Failed")
            
            # Delay
            delay = random.uniform(MIN_DELAY, MAX_DELAY)
            time.sleep(delay)
            
            # Recreate driver periodically
            if i % 25 == 0:
                driver.quit()
                time.sleep(random.uniform(5, 10))
                driver = create_driver()
    
    finally:
        driver.quit()
    
    print(f"\nComplete! Scraped {len(all_plans)} plans")

if __name__ == '__main__':
    main()
