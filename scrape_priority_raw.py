#!/usr/bin/env python3
"""
Scrape priority plans and save RAW content for parsing.
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
from selenium_stealth import stealth

JSON_DIR = Path('./scraped_json_all')

PRIORITY_PLANS = [
    {
        'plan_id': 'H5322_043_0',
        'contract': 'H5322',
        'plan_num': '043',
        'segment': '0',
        'name': 'AARP Medicare Advantage Patriot No Rx SC-MA01 (HMO-POS)'
    },
    {
        'plan_id': 'H5322_044_0',
        'contract': 'H5322',
        'plan_num': '044',
        'segment': '0',
        'name': 'AARP Medicare Advantage from UHC SC-0006 (HMO-POS)'
    },
    {
        'plan_id': 'R2604_005_0',
        'contract': 'R2604',
        'plan_num': '005',
        'segment': '0',
        'name': 'UHC Medicare Advantage Patriot No Rx GS-MA01 (Regional PPO)'
    }
]

def create_driver():
    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_argument('--window-size=1920,1080')
    opts.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
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

def main():
    print("=== Scraping Priority Plans (Raw Content) ===\n")
    
    driver = create_driver()
    
    try:
        for i, plan in enumerate(PRIORITY_PLANS, 1):
            plan_id = plan['plan_id']
            url = f"https://www.medicare.gov/plan-compare/#/plan-details/2026-{plan['contract']}-{plan['plan_num']}-{plan['segment']}?year=2026&lang=en"
            
            print(f"[{i}/3] {plan_id}: {plan['name'][:60]}")
            
            try:
                driver.get(url)
                time.sleep(random.uniform(4, 6))
                
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'h1'))
                )
                
                time.sleep(random.uniform(2, 3))
                
                # Get page text content
                body = driver.find_element(By.TAG_NAME, 'body')
                raw_content = body.text
                
                # Find plan name
                try:
                    h1 = driver.find_element(By.CSS_SELECTOR, 'h1')
                    plan_name = h1.text.strip()
                except:
                    plan_name = plan['name']
                
                # Save with raw_content
                data = {
                    'plan_id': plan_id,
                    'scraped_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
                    'url': url,
                    'raw_content': raw_content,
                    'plan_info': {
                        'name': plan_name,
                        'found': True
                    }
                }
                
                json_file = JSON_DIR / f"South_Carolina-{plan_id}.json"
                with open(json_file, 'w') as f:
                    json.dump(data, f, indent=2)
                
                print(f"  ✓ Saved {len(raw_content):,} chars of raw content")
                
                # Check for key data
                has_prem = 'Total monthly premium' in raw_content or 'Monthly Premium' in raw_content
                has_ded = 'deductible' in raw_content.lower()
                print(f"  Contains: Premium={has_prem}, Deductible={has_ded}")
                
            except Exception as e:
                print(f"  ✗ Error: {e}")
            
            if i < len(PRIORITY_PLANS):
                time.sleep(random.uniform(8, 12))
    
    finally:
        driver.quit()
    
    print("\n=== Now parsing raw content ===\n")
    
    # Parse the raw content
    import sys
    sys.path.insert(0, '.')
    from parse_sc_raw_content import parse_plan_file
    
    for plan in PRIORITY_PLANS:
        plan_id = plan['plan_id']
        filepath = JSON_DIR / f"South_Carolina-{plan_id}.json"
        
        if filepath.exists():
            print(f"Parsing {plan_id}...")
            try:
                parse_plan_file(filepath)
                
                # Verify
                with open(filepath) as f:
                    data = json.load(f)
                
                prem = len(data.get('premiums', {}))
                ded = len(data.get('deductibles', {}))
                ben = len(data.get('benefits', {}))
                
                print(f"  ✓ {prem} premiums, {ded} deductibles, {ben} benefits")
            except Exception as e:
                print(f"  ✗ Error: {e}")

if __name__ == '__main__':
    main()
