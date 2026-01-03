#!/usr/bin/env python3
"""
Scrape ALL remaining states efficiently.

This script:
1. Deduplicates plan IDs upfront
2. Skips already scraped plans
3. Processes all states in one run
4. Groups by state for progress reporting

Total: ~3,800 plans across 47 states
Estimated time: ~20-25 hours

Usage:
    nohup python3 scrape_all_remaining.py > all_remaining_output.log 2>&1 &
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

# No excluded states - this script handles ALL states
# Already-scraped plans are detected by checking existing files
EXCLUDED_STATES = set()

# State name to abbreviation mapping
STATE_ABBREVS = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR',
    'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE',
    'District of Columbia': 'DC', 'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI',
    'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA',
    'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME',
    'Maryland': 'MD', 'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN',
    'Mississippi': 'MS', 'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE',
    'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM',
    'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH',
    'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI',
    'South Carolina': 'SC', 'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX',
    'Utah': 'UT', 'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA',
    'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY',
    'Puerto Rico': 'PR', 'American Samoa': 'AS', 'Guam': 'GU',
    'Northern Mariana Islands': 'MP', 'Virgin Islands': 'VI',
}


def get_all_remaining_plans():
    """Get all unique plans for remaining states, sorted by state size (largest first)."""
    landscape_file = Path('downloaded_data/CY2026_Landscape_202511/CY2026_Landscape_202511.csv')
    
    # Collect unique plans per state
    state_plans = defaultdict(list)
    seen = set()
    
    with open(landscape_file, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            state_name = row.get('State Territory Name', '')
            plan_id = row.get('ContractPlanSegmentID', '')
            
            # Skip excluded states and duplicates
            if state_name in EXCLUDED_STATES:
                continue
            if not plan_id or plan_id in seen:
                continue
            
            seen.add(plan_id)
            state_abbrev = STATE_ABBREVS.get(state_name, state_name[:2].upper())
            state_plans[state_name].append({
                'plan_id': plan_id,
                'state': state_abbrev,
                'state_name': state_name
            })
    
    # Sort states by number of plans (largest first for better progress visibility)
    sorted_states = sorted(state_plans.items(), key=lambda x: -len(x[1]))
    
    # Flatten into single list, maintaining state grouping
    all_plans = []
    for state_name, plans in sorted_states:
        all_plans.extend(plans)
    
    return all_plans, dict(sorted_states)


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
    
    try:
        plan_name = driver.find_element(By.CSS_SELECTOR, "h1").text.strip()
        plan_data['plan_info'] = {'name': plan_name}
    except:
        plan_data['plan_info'] = {}
    
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
        
        if 'offered by' in body_text.lower():
            lines = body_text.split('\n')
            for i, line in enumerate(lines):
                if 'offered by' in line.lower() and i + 1 < len(lines):
                    plan_data['plan_info']['organization'] = lines[i + 1].strip()
                    break
        
        for ptype in ['Medicare Advantage with drug coverage', 'Drug plan (Part D)', 
                      'Medicare Advantage (without drug coverage)']:
            if ptype in body_text:
                plan_data['plan_info']['type'] = ptype
                break
        
        plan_data['premiums'] = {}
        if 'Monthly premium' in body_text or 'monthly premium' in body_text:
            import re
            premium_match = re.search(r'\$[\d,]+\.?\d*(?:\s*(?:per month|/month|monthly))?', body_text)
            if premium_match:
                plan_data['premiums']['Total monthly premium'] = premium_match.group(0).split()[0]
        
        plan_data['deductibles'] = {}
        if 'Drug deductible' in body_text:
            import re
            match = re.search(r'Drug deductible[:\s]*\$[\d,]+\.?\d*', body_text)
            if match:
                plan_data['deductibles']['Drug deductible'] = match.group(0).split('$')[-1]
        
    except Exception as e:
        pass
    
    plan_data.setdefault('maximum_out_of_pocket', {})
    plan_data.setdefault('contact_info', {})
    plan_data.setdefault('benefits', {})
    plan_data.setdefault('drug_coverage', {})
    plan_data.setdefault('extra_benefits', {})
    
    return plan_data


def main():
    print("=" * 80)
    print("ALL REMAINING STATES MEDICARE PLAN SCRAPER")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Get all plans
    all_plans, plans_by_state = get_all_remaining_plans()
    
    print(f"\nStates to scrape: {len(plans_by_state)}")
    print(f"Total unique plans: {len(all_plans)}")
    print("\nPlans by state:")
    for state_name, plans in sorted(plans_by_state.items(), key=lambda x: -len(x[1])):
        print(f"  {state_name}: {len(plans)}")
    
    # Check for already scraped
    # Handle both file formats: 'PlanID.json' and 'State-PlanID.json'
    output_dir = Path('scraped_json_all')
    output_dir.mkdir(exist_ok=True)
    
    already_scraped = set()
    for f in output_dir.glob('*.json'):
        name = f.stem
        if '-' in name:
            # Format: State-PlanID (e.g., Iowa-H5216_413_0)
            parts = name.split('-', 1)
            if len(parts) == 2:
                already_scraped.add(parts[1])
        else:
            # Format: PlanID (e.g., H5216_413_0)
            already_scraped.add(name)
    
    plans_to_scrape = [p for p in all_plans if p['plan_id'] not in already_scraped]
    
    print(f"\nAlready scraped: {len(all_plans) - len(plans_to_scrape)}")
    print(f"Remaining to scrape: {len(plans_to_scrape)}")
    
    if not plans_to_scrape:
        print("\nAll plans already scraped!")
        return
    
    # Estimate time
    est_minutes = len(plans_to_scrape) * 0.4  # ~2.5 plans/min
    est_hours = est_minutes / 60
    print(f"Estimated time: {est_hours:.1f} hours")
    
    # Create driver
    driver = create_stealth_driver()
    
    try:
        start_time = time.time()
        current_state = None
        state_count = 0
        state_start_idx = 0
        
        for i, plan in enumerate(plans_to_scrape, 1):
            plan_id = plan['plan_id']
            state_name = plan['state_name']
            
            # Print state header when changing states
            if state_name != current_state:
                if current_state:
                    print(f"  Completed {state_name}: {i - state_start_idx} plans")
                current_state = state_name
                state_count += 1
                state_start_idx = i
                print(f"\n{'=' * 60}")
                print(f"[State {state_count}/{len(plans_by_state)}] {state_name}")
                print(f"{'=' * 60}")
            
            print(f"[{i}/{len(plans_to_scrape)}] [{plan['state']}] {plan_id}", end='', flush=True)
            
            try:
                plan_data = scrape_plan_details(driver, plan_id)
                
                output_file = output_dir / f"{plan_id}.json"
                with open(output_file, 'w') as f:
                    json.dump(plan_data, f, indent=2)
                
                print("  ✓")
                
            except Exception as e:
                print(f"  ✗ Error: {e}")
            
            # Progress update every 50 plans
            if i % 50 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed * 60
                remaining = len(plans_to_scrape) - i
                eta = remaining / rate if rate > 0 else 0
                print(f"\n  === Progress: {i}/{len(plans_to_scrape)} | Rate: {rate:.1f}/min | ETA: {eta:.0f} min ===\n")
            
            # Random delay
            time.sleep(random.uniform(1.5, 3.0))
            
            # Restart driver periodically
            if i % 100 == 0:
                print("  Restarting browser...")
                driver.quit()
                time.sleep(5)
                driver = create_stealth_driver()
        
        elapsed = time.time() - start_time
        print(f"\n{'=' * 80}")
        print(f"COMPLETE!")
        print(f"Scraped {len(plans_to_scrape)} plans across {len(plans_by_state)} states")
        print(f"Total time: {elapsed/3600:.1f} hours")
        print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 80}")
        
    finally:
        driver.quit()


if __name__ == '__main__':
    main()
