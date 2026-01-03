#!/usr/bin/env python3
"""
Test the optimized scraper on a small batch (10 plans)
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

# Configuration - Small test batch
NUM_WORKERS = 2  # Even more conservative for testing
TEST_BATCH_SIZE = 10  # Just 10 plans
MIN_DELAY = 2.0
MAX_DELAY = 4.0

# Directories
state_data_dir = Path('./state_data')
html_dir = Path('./scraped_html_all')
json_dir = Path('./scraped_json_all')
html_dir.mkdir(exist_ok=True)
json_dir.mkdir(exist_ok=True)

progress_file = Path('./scraping_progress.json')
progress_lock = Lock()

CHROME_USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

def create_driver(user_agent):
    """Create Chrome driver with optimized settings"""
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-software-rasterizer')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-images')
    chrome_options.add_argument('--blink-settings=imagesEnabled=false')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument(f'--user-agent={user_agent}')
    chrome_options.add_argument('--disable-features=VizDisplayCompositor')
    chrome_options.add_argument('--disk-cache-size=1')

    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(45)
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

class WorkerState:
    """Track worker state"""
    def __init__(self, worker_id):
        self.worker_id = worker_id
        self.driver = None
        self.user_agent = CHROME_USER_AGENTS[worker_id % len(CHROME_USER_AGENTS)]

    def get_driver(self):
        """Get driver"""
        if self.driver is None:
            self.driver = create_driver(self.user_agent)
        return self.driver

    def cleanup(self):
        """Clean up driver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

def scrape_plan(plan_data, state_name, worker_state):
    """Scrape a single plan"""
    url = plan_data['url']
    contract_plan_segment_id = plan_data['ContractPlanSegmentID']

    driver = worker_state.get_driver()

    try:
        # Add delay
        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        time.sleep(delay)

        # Load page
        print(f"  [{worker_state.worker_id}] Loading {state_name}-{contract_plan_segment_id}...")
        driver.get(url)

        # Wait for content
        wait = WebDriverWait(driver, 30)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "mct-c-table")))
        time.sleep(5)

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

        # Verify address formatting
        address = plan_info.get('contact_info', {}).get('Plan address', '')
        has_newline = '\n' in address
        address_status = "✓" if has_newline else "✗"

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
            'error': str(e)
        }

def load_progress():
    """Load progress tracking data"""
    if progress_file.exists():
        with open(progress_file, 'r') as f:
            return json.load(f)
    return {'completed': [], 'failed': []}

def main():
    print("="*80)
    print(f"TEST BATCH SCRAPER - {TEST_BATCH_SIZE} plans")
    print(f"Workers: {NUM_WORKERS}")
    print(f"Delay: {MIN_DELAY}-{MAX_DELAY} seconds")
    print("="*80)

    # Load progress
    progress = load_progress()
    completed_ids = set(progress['completed'])

    # Find plans to scrape
    state_files = sorted(state_data_dir.glob('*.json'))
    all_tasks = []

    for state_file in state_files:
        state_name = state_file.stem
        with open(state_file, 'r') as f:
            state_data = json.load(f)

        for plan in state_data:
            plan_id = plan['ContractPlanSegmentID']
            if plan_id not in completed_ids:
                all_tasks.append((plan, state_name))

        if len(all_tasks) >= TEST_BATCH_SIZE:
            break

    # Limit to test batch size
    test_tasks = all_tasks[:TEST_BATCH_SIZE]

    print(f"\nTesting with {len(test_tasks)} plans:")
    for plan, state in test_tasks[:5]:
        print(f"  - {state}-{plan['ContractPlanSegmentID']}")
    if len(test_tasks) > 5:
        print(f"  ... and {len(test_tasks) - 5} more")
    print()

    # Create worker states
    worker_states = [WorkerState(i) for i in range(NUM_WORKERS)]

    # Process
    success_count = 0
    failed_count = 0
    address_ok_count = 0
    start_time = time.time()

    try:
        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
            future_to_task = {}

            for i, (plan, state_name) in enumerate(test_tasks):
                worker_state = worker_states[i % NUM_WORKERS]
                future = executor.submit(scrape_plan, plan, state_name, worker_state)
                future_to_task[future] = (plan['ContractPlanSegmentID'], state_name)

            for future in future_to_task:
                plan_id, state_name = future_to_task[future]
                result = future.result()

                if result['success']:
                    address_indicator = "✓" if result.get('address_ok') else "✗"
                    print(f"✓ {state_name}-{plan_id} {address_indicator}")
                    progress['completed'].append(plan_id)
                    success_count += 1
                    if result.get('address_ok'):
                        address_ok_count += 1
                else:
                    print(f"✗ {state_name}-{plan_id}: {result.get('error', 'Unknown error')[:50]}")
                    failed_count += 1

    finally:
        # Clean up
        for worker_state in worker_states:
            worker_state.cleanup()

    elapsed = time.time() - start_time

    print("\n" + "="*80)
    print("TEST BATCH COMPLETE!")
    print(f"Time elapsed: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    print(f"Success: {success_count}/{len(test_tasks)}")
    print(f"Failed: {failed_count}/{len(test_tasks)}")
    print(f"Addresses with proper newlines: {address_ok_count}/{success_count}")
    print(f"Average time per plan: {elapsed/len(test_tasks):.1f} seconds")
    print("="*80)

    # Estimated time for full scrape
    remaining_plans = 6581 - len(progress['completed'])
    estimated_hours = (remaining_plans * elapsed / len(test_tasks)) / 3600
    print(f"\nEstimated time for remaining {remaining_plans} plans: {estimated_hours:.1f} hours")

if __name__ == "__main__":
    main()
