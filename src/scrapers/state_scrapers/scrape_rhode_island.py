#!/usr/bin/env python3
"""
Stealth scraper for Rhode Island's 14 missing plans
"""

import json
import time
import random
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re

MIN_DELAY = 8.0
MAX_DELAY = 15.0

html_dir = Path('./scraped_html_all')
json_dir = Path('./scraped_json_all')
html_dir.mkdir(exist_ok=True)
json_dir.mkdir(exist_ok=True)

USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
]

WINDOW_SIZES = ['1920,1080', '1366,768', '1536,864', '1440,900', '1280,720']

MISSING_PLAN_IDS = [
    'S2893_001_0', 'S2893_003_0', 'S4802_076_0', 'S4802_137_0', 'S5601_004_0',
    'S5617_008_0', 'S5884_102_0', 'S5884_149_0', 'S5884_182_0', 'S5921_348_0',
    'S5921_385_0', 'H0710_035_0', 'H0764_001_0', 'H2126_001_0'
]

def create_stealth_driver():
    user_agent = random.choice(USER_AGENTS)
    window_size = random.choice(WINDOW_SIZES)
    
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument(f'--window-size={window_size}')
    chrome_options.add_argument(f'--user-agent={user_agent}')
    
    prefs = {'profile.default_content_setting_values': {'images': 2}}
    chrome_options.add_experimental_option('prefs', prefs)
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(60)
    
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": user_agent,
        "platform": "MacIntel" if "Mac" in user_agent else "Win32"
    })
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def extract_plan_data(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    for br in soup.find_all('br'):
        br.replace_with('\n')
    
    plan_data = {
        'plan_info': {}, 'premiums': {}, 'deductibles': {},
        'maximum_out_of_pocket': {}, 'contact_info': {},
        'benefits': {}, 'drug_coverage': {}, 'extra_benefits': {}
    }
    
    plan_header_section = soup.find('div', class_='PlanDetailsPagePlanInfo')
    if plan_header_section:
        plan_name_h1 = plan_header_section.find('h1')
        if plan_name_h1:
            plan_data['plan_info']['name'] = plan_name_h1.get_text(strip=True)
        
        plan_name_h2 = plan_header_section.find('h2')
        if plan_name_h2:
            plan_data['plan_info']['organization'] = plan_name_h2.get_text(strip=True)
        
        list_items = plan_header_section.find_all('li')
        for li in list_items:
            text = li.get_text()
            if 'Plan type:' in text:
                plan_data['plan_info']['type'] = text.replace('Plan type:', '').strip()
            elif 'Plan ID:' in text:
                plan_data['plan_info']['id'] = text.replace('Plan ID:', '').strip()
    
    tables = soup.find_all('table', class_='mct-c-table')
    
    for table in tables:
        caption = table.find('caption')
        if not caption:
            continue
        
        table_title = caption.get_text(strip=True)
        rows = table.find_all('tr')
        table_data = {}
        
        for row in rows:
            header = row.find('th')
            cell = row.find('td')
            
            if header and cell:
                header_text = header.get_text(strip=True)
                header_text = re.sub(r"What's.*?\?", "", header_text).strip()
                cell_text = cell.get_text(separator='\n').strip()
                cell_text = re.sub(r'\n\s*\n', '\n', cell_text)
                table_data[header_text] = cell_text
        
        if 'Premiums' in table_title:
            plan_data['premiums'].update(table_data)
        elif 'Deductibles' in table_title:
            plan_data['deductibles'].update(table_data)
        elif 'Maximum you pay' in table_title:
            plan_data['maximum_out_of_pocket'].update(table_data)
        elif 'Contact Information' in table_title:
            plan_data['contact_info'].update(table_data)
        elif 'Drug' in table_title:
            plan_data['drug_coverage'][table_title] = table_data
        elif 'Extra' in table_title or 'Additional' in table_title:
            plan_data['extra_benefits'][table_title] = table_data
        else:
            plan_data['benefits'][table_title] = table_data
    
    return plan_data

def scrape_plan(plan_data, state_name):
    url = plan_data['url']
    contract_plan_segment_id = plan_data['ContractPlanSegmentID']
    driver = None
    
    try:
        driver = create_stealth_driver()
        
        total_delay = random.uniform(MIN_DELAY, MAX_DELAY) + random.uniform(0, 2.0)
        print(f"  Waiting {total_delay:.1f}s...")
        time.sleep(total_delay)
        
        driver.get(url)
        
        wait = WebDriverWait(driver, 45)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        
        scroll_amount = random.randint(100, 500)
        driver.execute_script(f"window.scrollBy(0, {scroll_amount})")
        time.sleep(random.uniform(0.5, 1.5))
        
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "mct-c-table")))
        time.sleep(random.uniform(3, 6))
        
        html_content = driver.page_source
        
        html_path = html_dir / f"{state_name}-{contract_plan_segment_id}.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        plan_info = extract_plan_data(html_content)
        json_path = json_dir / f"{state_name}-{contract_plan_segment_id}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(plan_info, f, indent=2)
        
        address = plan_info.get('contact_info', {}).get('Plan address', '')
        
        return {
            'success': True,
            'plan_id': contract_plan_segment_id,
            'address_ok': '\n' in address
        }
    
    except Exception as e:
        return {
            'success': False,
            'plan_id': contract_plan_segment_id,
            'error': str(e)[:200]
        }
    
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def main():
    with open('./state_data/Rhode_Island.json', 'r') as f:
        all_plans = json.load(f)
    
    plans_to_scrape = [p for p in all_plans if p['ContractPlanSegmentID'] in MISSING_PLAN_IDS]
    
    print("="*80)
    print("STEALTH SCRAPER - RHODE ISLAND (MISSING PLANS)")
    print("="*80)
    print(f"Plans to scrape: {len(plans_to_scrape)}")
    print(f"Estimated time: {len(plans_to_scrape) * 0.4:.0f} minutes")
    print("="*80)
    print()
    
    results = []
    success_count = 0
    start_time = time.time()
    
    for i, plan in enumerate(plans_to_scrape, 1):
        print(f"[{i}/{len(plans_to_scrape)}] {plan['ContractPlanSegmentID']}: {plan['Plan Name'][:55]}")
        
        result = scrape_plan(plan, "Rhode_Island")
        results.append(result)
        
        if result['success']:
            success_count += 1
            addr_status = "✓" if result.get('address_ok') else "✗"
            print(f"  ✓ Success (addr: {addr_status})")
        else:
            print(f"  ✗ Failed: {result.get('error', 'Unknown')[:60]}")
        
        if i < len(plans_to_scrape):
            pause = random.uniform(10.0, 15.0)
            print(f"  Pausing {pause:.1f}s...")
            time.sleep(pause)
        
        print()
    
    elapsed = time.time() - start_time
    
    print("="*80)
    print("RHODE ISLAND SCRAPE COMPLETE!")
    print("="*80)
    print(f"Time: {elapsed/60:.1f} minutes")
    print(f"Success: {success_count}/{len(plans_to_scrape)} ({success_count/len(plans_to_scrape)*100:.1f}%)")
    
    if success_count > 0:
        address_ok = sum(1 for r in results if r.get('address_ok'))
        print(f"Addresses OK: {address_ok}/{success_count}")
    
    if success_count < len(plans_to_scrape):
        print("\nFailed plans:")
        for r in results:
            if not r['success']:
                print(f"  ✗ {r['plan_id']}")
    
    print("="*80)
    
    with open('./rhode_island_results.json', 'w') as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    main()
