#!/usr/bin/env python3
"""
Stealth scraper to finish Alaska and DC
- Alaska: 1 remaining plan
- District of Columbia: 5 remaining plans
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

# Configuration - Very conservative for avoiding bans
MIN_DELAY = 8.0
MAX_DELAY = 15.0

# Directories
html_dir = Path('./scraped_html_all')
json_dir = Path('./scraped_json_all')
html_dir.mkdir(exist_ok=True)
json_dir.mkdir(exist_ok=True)

# Large pool of realistic user agents
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
]

# Randomize window sizes
WINDOW_SIZES = [
    '1920,1080',
    '1366,768',
    '1536,864',
    '1440,900',
    '1280,720',
]

# Missing plans by state
MISSING_PLANS = {
    'Alaska': ['S5617_227_0'],
    'District_of_Columbia': [
        'H5521_480_0',
        'H7379_002_0',
        'H7379_003_0',
        'H7464_010_0',
        'H7849_142_0'
    ]
}

def create_stealth_driver():
    """Create Chrome driver with stealth settings"""
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

    # Randomize some preferences
    prefs = {
        'profile.default_content_setting_values': {
            'images': 2,  # Disable images
        },
        'profile.managed_default_content_settings': {
            'images': 2
        }
    }
    chrome_options.add_experimental_option('prefs', prefs)

    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(60)

    # Execute CDP commands to mask automation
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": user_agent,
        "platform": "MacIntel" if "Mac" in user_agent else "Win32"
    })
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return driver

def extract_plan_data(html_content):
    """Extract all plan data from HTML content"""
    soup = BeautifulSoup(html_content, 'html.parser')

    # Replace <br> tags with newlines before parsing
    for br in soup.find_all('br'):
        br.replace_with('\n')

    plan_data = {
        'plan_info': {},
        'premiums': {},
        'deductibles': {},
        'maximum_out_of_pocket': {},
        'contact_info': {},
        'benefits': {},
        'drug_coverage': {},
        'extra_benefits': {}
    }

    # Extract plan name and ID
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

    # Extract all tables
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

                # Get cell text preserving newlines from <br> tags
                cell_text = cell.get_text(separator='\n').strip()
                cell_text = re.sub(r'\n\s*\n', '\n', cell_text)

                table_data[header_text] = cell_text

        # Categorize tables
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
    """Scrape a single plan with stealth techniques"""
    url = plan_data['url']
    contract_plan_segment_id = plan_data['ContractPlanSegmentID']

    driver = None

    try:
        # Create fresh stealth driver
        driver = create_stealth_driver()

        # Extended random delay with jitter
        base_delay = random.uniform(MIN_DELAY, MAX_DELAY)
        jitter = random.uniform(0, 2.0)
        total_delay = base_delay + jitter
        
        print(f"  Waiting {total_delay:.1f}s before request...")
        time.sleep(total_delay)

        print(f"  Loading page...")
        driver.get(url)

        # Longer wait times to mimic human behavior
        wait = WebDriverWait(driver, 45)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))

        # Random scroll to mimic human interaction
        scroll_amount = random.randint(100, 500)
        driver.execute_script(f"window.scrollBy(0, {scroll_amount})")
        time.sleep(random.uniform(0.5, 1.5))

        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "mct-c-table")))

        # Additional wait to let page fully render
        render_delay = random.uniform(3, 6)
        print(f"  Letting page render ({render_delay:.1f}s)...")
        time.sleep(render_delay)

        html_content = driver.page_source

        # Save HTML
        safe_filename = f"{state_name}-{contract_plan_segment_id}.html"
        html_path = html_dir / safe_filename
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"  ✓ HTML saved: {html_path}")

        # Extract and save JSON
        plan_info = extract_plan_data(html_content)
        json_filename = f"{state_name}-{contract_plan_segment_id}.json"
        json_path = json_dir / json_filename
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(plan_info, f, indent=2)
        
        print(f"  ✓ JSON saved: {json_path}")

        address = plan_info.get('contact_info', {}).get('Plan address', '')
        has_newline = '\n' in address

        return {
            'success': True,
            'plan_id': contract_plan_segment_id,
            'state': state_name,
            'address_ok': has_newline
        }

    except Exception as e:
        print(f"  ✗ Error: {str(e)[:100]}")
        return {
            'success': False,
            'plan_id': contract_plan_segment_id,
            'state': state_name,
            'error': str(e)[:200]
        }

    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def main():
    print("="*80)
    print("STEALTH SCRAPER - FINISHING ALASKA & DC")
    print("="*80)
    print(f"Workers: 1 (sequential)")
    print(f"Delay: {MIN_DELAY}-{MAX_DELAY} seconds + jitter")
    print(f"Randomized: User agents, window sizes, scroll patterns")
    print("="*80)
    
    # Build task list
    all_tasks = []
    
    for state_name, plan_ids in MISSING_PLANS.items():
        state_file = Path(f'./state_data/{state_name}.json')
        with open(state_file, 'r') as f:
            all_plans = json.load(f)
        
        for plan in all_plans:
            if plan['ContractPlanSegmentID'] in plan_ids:
                all_tasks.append((plan, state_name))
    
    print(f"\nPlans to scrape: {len(all_tasks)}")
    print()
    for plan, state in all_tasks:
        print(f"  - [{state}] {plan['ContractPlanSegmentID']}: {plan['Plan Name']}")
    
    avg_time_per_plan = (MIN_DELAY + MAX_DELAY) / 2 + 8
    estimated_minutes = len(all_tasks) * avg_time_per_plan / 60
    print(f"\nEstimated time: {estimated_minutes:.1f} minutes")
    print()
    
    results = []
    success_count = 0
    start_time = time.time()
    
    for i, (plan, state_name) in enumerate(all_tasks, 1):
        print(f"\n{'='*80}")
        print(f"[{i}/{len(all_tasks)}] [{state_name}] {plan['ContractPlanSegmentID']}: {plan['Plan Name']}")
        print(f"{'='*80}")
        
        result = scrape_plan(plan, state_name)
        results.append(result)
        
        if result['success']:
            success_count += 1
            address_indicator = "✓" if result.get('address_ok') else "✗"
            print(f"\n✓ Success! Address newlines: {address_indicator}")
        else:
            print(f"\n✗ Failed: {result.get('error', 'Unknown')[:100]}")
        
        # Extra pause between plans
        if i < len(all_tasks):
            pause = random.uniform(10.0, 15.0)
            print(f"\nPausing {pause:.1f}s before next plan...")
            time.sleep(pause)
    
    elapsed = time.time() - start_time
    
    print("\n" + "="*80)
    print("STEALTH SCRAPE COMPLETE!")
    print("="*80)
    print(f"Time elapsed: {elapsed:.0f} seconds ({elapsed/60:.1f} minutes)")
    print(f"Success: {success_count}/{len(all_tasks)}")
    print(f"Failed: {len(all_tasks) - success_count}/{len(all_tasks)}")
    
    if success_count > 0:
        success_rate = success_count / len(all_tasks) * 100
        print(f"Success rate: {success_rate:.1f}%")
        
        address_ok_count = sum(1 for r in results if r.get('address_ok'))
        print(f"Addresses with proper newlines: {address_ok_count}/{success_count}")
    
    # Group results by state
    by_state = {}
    for r in results:
        state = r['state']
        if state not in by_state:
            by_state[state] = {'success': 0, 'failed': 0}
        if r['success']:
            by_state[state]['success'] += 1
        else:
            by_state[state]['failed'] += 1
    
    print("\nResults by state:")
    for state, counts in by_state.items():
        total = counts['success'] + counts['failed']
        print(f"  {state}: {counts['success']}/{total} succeeded")
    
    if success_count < len(all_tasks):
        print("\nFailed plans:")
        for r in results:
            if not r['success']:
                print(f"  ✗ [{r['state']}] {r['plan_id']}: {r.get('error', 'Unknown')[:80]}")
    
    print("="*80)
    
    # Save results
    results_file = './alaska_dc_finish_results.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {results_file}")

if __name__ == "__main__":
    main()
