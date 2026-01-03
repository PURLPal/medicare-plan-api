#!/usr/bin/env python3
"""
Stealth scraper with anti-detection techniques for security testing
- Randomized user agents
- Extended delays with jitter
- Browser fingerprint randomization
- Request throttling
"""

import json
import time
import random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re
from threading import Lock
import hashlib

# Configuration - Very conservative for avoiding bans
NUM_WORKERS = 1  # Single worker to minimize detection
MIN_DELAY = 8.0  # Much longer delays
MAX_DELAY = 15.0
PROGRESS_SAVE_INTERVAL = 3

# Directories
state_data_dir = Path('./state_data')
html_dir = Path('./scraped_html_all')
json_dir = Path('./scraped_json_all')
html_dir.mkdir(exist_ok=True)
json_dir.mkdir(exist_ok=True)

progress_file = Path('./scraping_progress.json')
progress_lock = Lock()

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

def scrape_plan(plan_data, state_name, worker_id):
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
        time.sleep(total_delay)

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
        time.sleep(random.uniform(3, 6))

        html_content = driver.page_source

        # Save HTML
        safe_filename = f"{state_name}-{contract_plan_segment_id}.html"
        html_path = html_dir / safe_filename
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        # Extract and save JSON
        plan_info = extract_plan_data(html_content)
        json_filename = f"{state_name}-{contract_plan_segment_id}.json"
        json_path = json_dir / json_filename
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(plan_info, f, indent=2)

        address = plan_info.get('contact_info', {}).get('Plan address', '')
        has_newline = '\n' in address

        return {
            'success': True,
            'plan_id': contract_plan_segment_id,
            'state': state_name,
            'address_ok': has_newline
        }

    except Exception as e:
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

def load_progress():
    """Load progress tracking data"""
    if progress_file.exists():
        with open(progress_file, 'r') as f:
            return json.load(f)
    return {'completed': [], 'failed': []}

def save_progress(progress):
    """Save progress tracking data"""
    with progress_lock:
        with open(progress_file, 'w') as f:
            json.dump(progress, f, indent=2)

def main():
    print("="*80)
    print(f"STEALTH SCRAPER - Anti-Detection Mode")
    print(f"Workers: {NUM_WORKERS} (sequential)")
    print(f"Delay: {MIN_DELAY}-{MAX_DELAY} seconds + jitter")
    print(f"Randomized: User agents, window sizes, scroll patterns")
    print("="*80)

    # Load progress
    progress = load_progress()
    completed_ids = set(progress['completed'])

    print(f"\nCompleted so far: {len(completed_ids)}")

    # Build list of all uncompleted plans
    all_tasks = []
    state_files = sorted(state_data_dir.glob('*.json'))

    for state_file in state_files:
        state_name = state_file.stem
        with open(state_file, 'r') as f:
            state_data = json.load(f)

        for plan in state_data:
            plan_id = plan['ContractPlanSegmentID']
            if plan_id not in completed_ids:
                all_tasks.append((plan, state_name))

    # Randomize order to avoid pattern detection
    random.shuffle(all_tasks)

    print(f"\nPlans to scrape: {len(all_tasks)}")
    avg_time_per_plan = (MIN_DELAY + MAX_DELAY) / 2 + 8  # delays + processing
    estimated_hours = len(all_tasks) * avg_time_per_plan / 3600
    print(f"Estimated time: {estimated_hours:.1f} hours\n")

    if len(all_tasks) == 0:
        print("All plans already completed!")
        return

    # Clear old failures
    progress['failed'] = []

    # Process sequentially
    success_count = 0
    failed_count = 0
    address_ok_count = 0
    save_counter = 0
    start_time = time.time()

    for i, (plan, state_name) in enumerate(all_tasks):
        result = scrape_plan(plan, state_name, 0)
        plan_id = plan['ContractPlanSegmentID']

        if result['success']:
            address_indicator = "✓" if result.get('address_ok') else "✗"
            print(f"✓ [{success_count+1}/{len(all_tasks)}] {state_name:30s} {plan_id} {address_indicator}")
            progress['completed'].append(plan_id)
            success_count += 1
            if result.get('address_ok'):
                address_ok_count += 1
        else:
            error_msg = result.get('error', 'Unknown')[:60]
            print(f"✗ [{success_count+failed_count+1}/{len(all_tasks)}] {state_name:30s} {plan_id}: {error_msg}")
            progress['failed'].append({
                'plan_id': plan_id,
                'state': state_name,
                'error': result.get('error')
            })
            failed_count += 1

        # Save progress periodically
        save_counter += 1
        if save_counter >= PROGRESS_SAVE_INTERVAL:
            save_progress(progress)
            save_counter = 0
            elapsed = time.time() - start_time
            completed = success_count + failed_count
            rate = completed / elapsed if elapsed > 0 else 0
            remaining = len(all_tasks) - completed
            eta_seconds = remaining / rate if rate > 0 else 0
            success_rate = (success_count / completed * 100) if completed > 0 else 0
            print(f"    Progress: {success_count} success ({success_rate:.1f}%), {failed_count} failed | ETA: {eta_seconds/3600:.1f} hrs")

    # Final save
    save_progress(progress)

    elapsed = time.time() - start_time

    print("\n" + "="*80)
    print("STEALTH SCRAPE COMPLETE!")
    print(f"Time elapsed: {elapsed:.0f} seconds ({elapsed/3600:.1f} hours)")
    print(f"Success: {success_count}/{len(all_tasks)}")
    print(f"Failed: {failed_count}/{len(all_tasks)}")
    print(f"Success rate: {success_count/(success_count+failed_count)*100:.1f}%")
    print(f"Addresses with proper newlines: {address_ok_count}/{success_count}")
    print("="*80)

if __name__ == "__main__":
    main()
