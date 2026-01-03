#!/usr/bin/env python3
"""
Fixed scraper for remaining Medicare plans.
Uses BeautifulSoup for proper HTML parsing like the working batch scrapers.
"""
import csv
import json
import time
import random
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from bs4 import BeautifulSoup

# Directories
HTML_DIR = Path('./scraped_html_all')
JSON_DIR = Path('./scraped_json_all')
HTML_DIR.mkdir(exist_ok=True)
JSON_DIR.mkdir(exist_ok=True)

# Timing - be polite to avoid blocks
MIN_DELAY, MAX_DELAY = 8.0, 15.0

# Browser fingerprinting
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
]
WINDOW_SIZES = ['1920,1080', '1366,768', '1536,864', '1440,900']

# State abbreviations
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


def create_driver():
    """Create a stealth Chrome driver."""
    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_argument(f'--window-size={random.choice(WINDOW_SIZES)}')
    opts.add_argument(f'--user-agent={random.choice(USER_AGENTS)}')
    opts.add_experimental_option('prefs', {'profile.default_content_setting_values': {'images': 2}})
    driver = webdriver.Chrome(options=opts)
    
    # Apply stealth to avoid bot detection
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


def extract_data(html):
    """Extract plan data from HTML using BeautifulSoup."""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Replace <br> with newlines
    for br in soup.find_all('br'):
        br.replace_with('\n')
    
    data = {
        'plan_info': {}, 'premiums': {}, 'deductibles': {},
        'maximum_out_of_pocket': {}, 'contact_info': {},
        'benefits': {}, 'drug_coverage': {}, 'extra_benefits': {}
    }
    
    # Plan info - get name from the specific plan header h1 (not the Menu h1)
    plan_header = soup.select_one('h1.e2e-plan-details-plan-header, .e2e-plan-details-plan-header')
    if plan_header:
        data['plan_info']['name'] = plan_header.get_text(strip=True)
    else:
        # Fallback: find h1 that's not "Menu"
        for h1 in soup.find_all('h1'):
            text = h1.get_text(strip=True)
            if text and text.lower() != 'menu':
                data['plan_info']['name'] = text
                break
    
    # Get plan info items
    for item in soup.select('.plan-info-item, .plan-detail-item'):
        label = item.select_one('.label, .item-label')
        value = item.select_one('.value, .item-value')
        if label and value:
            data['plan_info'][label.get_text(strip=True).rstrip(':')] = value.get_text(strip=True)
    
    # Section mapping
    section_map = {
        'premium': 'premiums', 'deductible': 'deductibles',
        'maximum out-of-pocket': 'maximum_out_of_pocket',
        'contact': 'contact_info', 'benefit': 'benefits',
        'drug': 'drug_coverage', 'extra': 'extra_benefits'
    }
    
    # Process sections
    for section in soup.select('section, .section, .card, .benefit-section'):
        header = section.select_one('h2, h3, .section-header, .card-header')
        if not header:
            continue
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


def scrape_plan(driver, plan_id):
    """Scrape a single plan and return HTML."""
    # Convert plan_id format: H5216_413_0 -> H5216-413-0
    # URL format requires year prefix: 2026-H5216-413-0
    url_plan_id = plan_id.replace('_', '-')
    url = f"https://www.medicare.gov/plan-compare/#/plan-details/2026-{url_plan_id}?year=2026&lang=en"
    
    try:
        driver.get(url)
        time.sleep(random.uniform(3, 5))
        
        # Wait for the actual plan header, not just any h1
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.e2e-plan-details-plan-header, h1.e2e-plan-details-plan-header'))
        )
        
        # Extra wait for JS to finish rendering
        time.sleep(random.uniform(2, 4))
        return driver.page_source
    except Exception as e:
        print(f"  Error loading page: {e}")
        return None


def get_already_scraped():
    """Get set of already scraped plan IDs (with good data)."""
    scraped = set()
    
    for f in JSON_DIR.glob('*.json'):
        try:
            with open(f) as fp:
                data = json.load(fp)
            
            # Check if it has actual data
            plan_info = data.get('plan_info', {})
            name = ''
            if isinstance(plan_info, dict):
                name = plan_info.get('name', '')
            elif isinstance(plan_info, list) and plan_info:
                name = plan_info[0]
            
            # Only count as scraped if it has a name
            if name:
                # Extract plan_id from filename
                fname = f.stem
                if '-' in fname:
                    plan_id = fname.split('-', 1)[1]
                else:
                    plan_id = fname
                scraped.add(plan_id)
        except:
            pass
    
    return scraped


def get_remaining_plans():
    """Get all plans that need to be scraped (missing or empty)."""
    landscape_file = Path('downloaded_data/CY2026_Landscape_202511/CY2026_Landscape_202511.csv')
    
    # Get already scraped (with good data)
    already_scraped = get_already_scraped()
    print(f"Already scraped with good data: {len(already_scraped)}")
    
    # Collect all unique plans
    state_plans = defaultdict(list)
    seen = set()
    
    with open(landscape_file, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            state_name = row.get('State Territory Name', '')
            plan_id = row.get('ContractPlanSegmentID', '')
            
            if not plan_id or plan_id in seen:
                continue
            
            # Skip if already scraped with good data
            if plan_id in already_scraped:
                continue
            
            seen.add(plan_id)
            state_abbrev = STATE_ABBREVS.get(state_name, state_name[:2].upper())
            state_plans[state_name].append({
                'plan_id': plan_id,
                'state': state_name,
                'state_abbrev': state_abbrev,
            })
    
    # Sort states by size (largest first)
    sorted_states = sorted(state_plans.items(), key=lambda x: -len(x[1]))
    
    # Build flat list
    all_plans = []
    for state_name, plans in sorted_states:
        all_plans.extend(plans)
    
    return all_plans, dict(sorted_states)


def main():
    print("=" * 70)
    print("MEDICARE PLAN SCRAPER (FIXED)")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Get remaining plans
    all_plans, plans_by_state = get_remaining_plans()
    
    print(f"\nStates to scrape: {len(plans_by_state)}")
    print(f"Total plans to scrape: {len(all_plans)}")
    print("\nPlans by state:")
    for state_name, plans in sorted(plans_by_state.items(), key=lambda x: -len(x[1])):
        print(f"  {state_name}: {len(plans)}")
    
    if not all_plans:
        print("\nAll plans already scraped!")
        return
    
    # Estimate time
    est_minutes = len(all_plans) * 0.2  # ~12 sec/plan with delays
    est_hours = est_minutes / 60
    print(f"\nEstimated time: {est_hours:.1f} hours")
    
    # Create driver
    driver = create_driver()
    
    try:
        start_time = time.time()
        current_state = None
        state_count = 0
        success_count = 0
        fail_count = 0
        
        for i, plan in enumerate(all_plans):
            plan_id = plan['plan_id']
            state_name = plan['state']
            state_abbrev = plan['state_abbrev']
            
            # State header
            if state_name != current_state:
                if current_state:
                    print(f"  Completed {current_state}")
                current_state = state_name
                state_count += 1
                print(f"\n{'='*60}")
                print(f"[State {state_count}/{len(plans_by_state)}] {state_name}")
                print(f"{'='*60}")
            
            # Scrape
            print(f"[{i+1}/{len(all_plans)}] [{state_abbrev}] {plan_id}", end="  ")
            
            html = scrape_plan(driver, plan_id)
            
            if html:
                # Save HTML
                html_file = HTML_DIR / f"{state_name.replace(' ', '_')}-{plan_id}.html"
                with open(html_file, 'w') as f:
                    f.write(html)
                
                # Extract and save JSON
                data = extract_data(html)
                data['plan_id'] = plan_id
                
                json_file = JSON_DIR / f"{state_name.replace(' ', '_')}-{plan_id}.json"
                with open(json_file, 'w') as f:
                    json.dump(data, f, indent=2)
                
                # Check if we got good data
                if data.get('plan_info', {}).get('name'):
                    print("✓")
                    success_count += 1
                else:
                    print("⚠ (no name)")
                    fail_count += 1
            else:
                print("✗")
                fail_count += 1
            
            # Delay between requests
            delay = random.uniform(MIN_DELAY, MAX_DELAY)
            time.sleep(delay)
            
            # Restart driver periodically
            if (i + 1) % 50 == 0:
                print(f"\n  [Restarting browser after {i+1} plans...]")
                driver.quit()
                time.sleep(5)
                driver = create_driver()
        
        elapsed = time.time() - start_time
        print(f"\n{'='*70}")
        print("SCRAPING COMPLETE!")
        print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration: {elapsed/3600:.1f} hours")
        print(f"Success: {success_count}, Failed: {fail_count}")
        print(f"{'='*70}")
        
    finally:
        driver.quit()


if __name__ == '__main__':
    main()
