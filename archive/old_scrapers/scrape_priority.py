#!/usr/bin/env python3
"""
Priority scraper for South Carolina and North Carolina.
SC first (for ZIP 29401), then NC.
"""

import csv
import json
import time
import random
import re
from pathlib import Path
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth

# Priority states - SC first, then NC
PRIORITY_STATES = [
    ('South Carolina', 'SC'),
    ('North Carolina', 'NC'),
]

def get_priority_plans():
    """Get plans for priority states, deduplicated."""
    landscape_file = Path('downloaded_data/CY2026_Landscape_202511/CY2026_Landscape_202511.csv')
    
    state_name_to_abbrev = {name: abbrev for name, abbrev in PRIORITY_STATES}
    
    seen = set()
    plans_by_state = {abbrev: [] for _, abbrev in PRIORITY_STATES}
    
    with open(landscape_file, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            state_name = row.get('State Territory Name', '')
            if state_name in state_name_to_abbrev:
                plan_id = row.get('ContractPlanSegmentID', '')
                if plan_id and plan_id not in seen:
                    seen.add(plan_id)
                    abbrev = state_name_to_abbrev[state_name]
                    plans_by_state[abbrev].append({
                        'plan_id': plan_id,
                        'state': abbrev,
                        'state_name': state_name
                    })
    
    # Return SC first, then NC
    all_plans = []
    for _, abbrev in PRIORITY_STATES:
        all_plans.extend(plans_by_state[abbrev])
    
    return all_plans

def create_stealth_driver():
    """Create a stealth Chrome driver."""
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=options)
    
    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )
    
    return driver

def scrape_plan(driver, plan_id):
    """Scrape a single plan's details."""
    url = f"https://www.medicare.gov/plan-compare/#/plan-details/{plan_id}?year=2025&lang=en"
    
    try:
        driver.get(url)
        time.sleep(random.uniform(2, 4))
        
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1, .plan-name, [class*='plan']"))
        )
        
        time.sleep(random.uniform(1, 2))
        
        # Extract plan data
        plan_data = {
            'plan_id': plan_id,
            'scraped_at': datetime.now().isoformat(),
            'url': url
        }
        
        # Get page content
        try:
            page_text = driver.find_element(By.TAG_NAME, 'body').text
            plan_data['raw_content'] = page_text[:50000]
        except:
            pass
        
        # Extract structured data
        sections = [
            ('plan_info', ['h1', '.plan-name', '[class*="plan-header"]']),
            ('premiums', ['[class*="premium"]', '[class*="cost"]']),
            ('benefits', ['[class*="benefit"]', '[class*="coverage"]']),
        ]
        
        for section_name, selectors in sections:
            for selector in selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        plan_data[section_name] = [el.text for el in elements[:10]]
                        break
                except:
                    continue
        
        # Try to get JSON data from page
        try:
            scripts = driver.find_elements(By.TAG_NAME, 'script')
            for script in scripts:
                content = script.get_attribute('innerHTML')
                if content and 'planDetails' in content:
                    plan_data['script_data'] = content[:10000]
                    break
        except:
            pass
        
        return plan_data
        
    except Exception as e:
        return {
            'plan_id': plan_id,
            'error': str(e),
            'scraped_at': datetime.now().isoformat()
        }

def main():
    print("=" * 70)
    print("PRIORITY SCRAPER: South Carolina + North Carolina")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()
    
    # Get all priority plans
    all_plans = get_priority_plans()
    
    # Check already scraped
    output_dir = Path('scraped_json_all')
    output_dir.mkdir(exist_ok=True)
    
    already_scraped = set()
    for f in output_dir.glob('*.json'):
        name = f.stem
        if '-' in name:
            parts = name.split('-', 1)
            if len(parts) == 2:
                already_scraped.add(parts[1])
        else:
            already_scraped.add(name)
    
    plans_to_scrape = [p for p in all_plans if p['plan_id'] not in already_scraped]
    
    # Count by state
    sc_count = sum(1 for p in plans_to_scrape if p['state'] == 'SC')
    nc_count = sum(1 for p in plans_to_scrape if p['state'] == 'NC')
    
    print(f"South Carolina: {sc_count} plans to scrape")
    print(f"North Carolina: {nc_count} plans to scrape")
    print(f"Total: {len(plans_to_scrape)} plans")
    print()
    
    if not plans_to_scrape:
        print("All priority plans already scraped!")
        return
    
    driver = create_stealth_driver()
    
    try:
        current_state = None
        for i, plan in enumerate(plans_to_scrape):
            plan_id = plan['plan_id']
            state = plan['state']
            
            if state != current_state:
                current_state = state
                print()
                print("=" * 50)
                print(f"[{state}] Starting {plan['state_name']}")
                print("=" * 50)
            
            print(f"[{i+1}/{len(plans_to_scrape)}] [{state}] {plan_id}", end="  ", flush=True)
            
            plan_data = scrape_plan(driver, plan_id)
            
            # Save with just plan_id (no state prefix)
            output_file = output_dir / f"{plan_id}.json"
            with open(output_file, 'w') as f:
                json.dump(plan_data, f, indent=2)
            
            if 'error' in plan_data:
                print(f"⚠ {plan_data['error'][:30]}")
            else:
                print("✓")
            
            # Random delay
            time.sleep(random.uniform(3, 6))
            
    finally:
        driver.quit()
    
    print()
    print("=" * 70)
    print("PRIORITY SCRAPING COMPLETE!")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

if __name__ == '__main__':
    main()
