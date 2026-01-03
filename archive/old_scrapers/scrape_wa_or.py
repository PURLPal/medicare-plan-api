#!/usr/bin/env python3
"""
Scrape Washington and Oregon Medicare plans.
Washington: 136 plans, Oregon: 112 plans
Total: 248 plans

Usage:
    nohup python3 scrape_wa_or.py > wa_or_output.log 2>&1 &
"""

import csv
import json
import time
import random
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth

# Target states
TARGET_STATES = [
    ('Washington', 'WA'),
    ('Oregon', 'OR'),
]

def get_state_plans():
    """Get all plans for target states from the landscape file."""
    plans = []
    landscape_file = Path('downloaded_data/CY2026_Landscape_202511/CY2026_Landscape_202511.csv')
    
    state_name_to_abbrev = {name: abbrev for name, abbrev in TARGET_STATES}
    
    with open(landscape_file, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            state_name = row.get('State Territory Name', '')
            if state_name in state_name_to_abbrev:
                plan_id = row.get('ContractPlanSegmentID', '')
                if plan_id:
                    plans.append({
                        'plan_id': plan_id,
                        'state': state_name_to_abbrev[state_name],
                        'state_name': state_name
                    })
    
    # Deduplicate by plan_id
    seen = set()
    unique_plans = []
    for p in plans:
        if p['plan_id'] not in seen:
            seen.add(p['plan_id'])
            unique_plans.append(p)
    
    return unique_plans

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

def scrape_plan_details(driver, plan_id):
    """Scrape details for a single plan."""
    url = f"https://www.medicare.gov/plan-compare/#/plan-details/{plan_id}?year=2025&lang=en"
    
    driver.get(url)
    time.sleep(random.uniform(2.5, 4.0))
    
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1, .plan-name, [data-testid='plan-name']"))
        )
    except:
        pass
    
    time.sleep(random.uniform(1.0, 2.0))
    
    # Extract plan data
    plan_data = {'plan_id': plan_id}
    
    # Plan info
    try:
        plan_name = driver.find_element(By.CSS_SELECTOR, "h1").text.strip()
        plan_data['plan_info'] = {'name': plan_name}
    except:
        plan_data['plan_info'] = {}
    
    # Get all text content for parsing
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
        
        # Extract organization
        if 'offered by' in body_text.lower():
            lines = body_text.split('\n')
            for i, line in enumerate(lines):
                if 'offered by' in line.lower() and i + 1 < len(lines):
                    plan_data['plan_info']['organization'] = lines[i + 1].strip()
                    break
        
        # Extract plan type
        for ptype in ['Medicare Advantage with drug coverage', 'Drug plan (Part D)', 
                      'Medicare Advantage (without drug coverage)']:
            if ptype in body_text:
                plan_data['plan_info']['type'] = ptype
                break
        
        # Extract premiums
        plan_data['premiums'] = {}
        if 'Monthly premium' in body_text or 'monthly premium' in body_text:
            import re
            premium_match = re.search(r'\$[\d,]+\.?\d*(?:\s*(?:per month|/month|monthly))?', body_text)
            if premium_match:
                plan_data['premiums']['Total monthly premium'] = premium_match.group(0).split()[0]
        
        # Extract deductibles
        plan_data['deductibles'] = {}
        if 'Drug deductible' in body_text:
            match = re.search(r'Drug deductible[:\s]*\$[\d,]+\.?\d*', body_text)
            if match:
                plan_data['deductibles']['Drug deductible'] = match.group(0).split('$')[-1]
        
    except Exception as e:
        print(f"    Error parsing: {e}")
    
    # Initialize other sections
    plan_data.setdefault('maximum_out_of_pocket', {})
    plan_data.setdefault('contact_info', {})
    plan_data.setdefault('benefits', {})
    plan_data.setdefault('drug_coverage', {})
    plan_data.setdefault('extra_benefits', {})
    
    return plan_data

def main():
    print(f"=" * 80)
    print(f"WASHINGTON & OREGON MEDICARE PLAN SCRAPER")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=" * 80)
    
    # Get plans
    all_plans = get_state_plans()
    
    # Group by state for reporting
    by_state = defaultdict(list)
    for p in all_plans:
        by_state[p['state_name']].append(p)
    
    print(f"\nPlans by state:")
    for state_name, abbrev in TARGET_STATES:
        print(f"  {state_name}: {len(by_state[state_name])} plans")
    print(f"  Total: {len(all_plans)} plans")
    
    # Check for already scraped
    output_dir = Path('scraped_json_all')
    output_dir.mkdir(exist_ok=True)
    
    already_scraped = set()
    for f in output_dir.glob('*.json'):
        already_scraped.add(f.stem)
    
    plans_to_scrape = [p for p in all_plans if p['plan_id'] not in already_scraped]
    print(f"\nAlready scraped: {len(all_plans) - len(plans_to_scrape)}")
    print(f"Remaining: {len(plans_to_scrape)}")
    
    if not plans_to_scrape:
        print("All plans already scraped!")
        return
    
    # Create driver
    driver = create_stealth_driver()
    
    try:
        start_time = time.time()
        current_state = None
        
        for i, plan in enumerate(plans_to_scrape, 1):
            plan_id = plan['plan_id']
            state_name = plan['state_name']
            
            # Print state header when changing states
            if state_name != current_state:
                current_state = state_name
                print(f"\n{'=' * 40}")
                print(f"Starting {state_name}")
                print(f"{'=' * 40}")
            
            print(f"[{i}/{len(plans_to_scrape)}] [{plan['state']}] {plan_id}", end='', flush=True)
            
            try:
                plan_data = scrape_plan_details(driver, plan_id)
                
                # Save
                output_file = output_dir / f"{plan_id}.json"
                with open(output_file, 'w') as f:
                    json.dump(plan_data, f, indent=2)
                
                print("  ✓")
                
            except Exception as e:
                print(f"  ✗ Error: {e}")
            
            # Progress update every 50 plans
            if i % 50 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed * 60  # plans per minute
                remaining = len(plans_to_scrape) - i
                eta = remaining / rate if rate > 0 else 0
                print(f"  Progress: {i}/{len(plans_to_scrape)} | Rate: {rate:.1f}/min | ETA: {eta:.1f} min")
            
            # Random delay
            time.sleep(random.uniform(1.5, 3.0))
            
            # Restart driver periodically
            if i % 100 == 0:
                print("  Restarting browser...")
                driver.quit()
                time.sleep(5)
                driver = create_stealth_driver()
        
        print(f"\n{'=' * 80}")
        print(f"COMPLETE!")
        print(f"Scraped {len(plans_to_scrape)} plans")
        print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 80}")
        
    finally:
        driver.quit()

if __name__ == '__main__':
    main()
