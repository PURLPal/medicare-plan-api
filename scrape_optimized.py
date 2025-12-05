#!/usr/bin/env python3
"""
Optimized Medicare plan scraper with resource management
- Reduced worker count (2-3 workers)
- Periodic driver restart
- Better progress tracking
- Resource-friendly delays
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

# Configuration
NUM_WORKERS = 3  # Reduced from 8 to 3 for stability
REQUESTS_PER_WORKER = 50  # Restart driver after this many requests
MIN_DELAY = 2.0  # Increased from 1.0
MAX_DELAY = 4.0  # Increased from 3.0
BATCH_SIZE = 100  # Process in batches
PROGRESS_SAVE_INTERVAL = 10  # Save progress every N plans

# Directories
state_data_dir = Path('./state_data')
html_dir = Path('./scraped_html_all')
json_dir = Path('./scraped_json_all')
html_dir.mkdir(exist_ok=True)
json_dir.mkdir(exist_ok=True)

progress_file = Path('./scraping_progress.json')
progress_lock = Lock()

# User agents for rotation
CHROME_USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
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
    chrome_options.add_argument('--disable-images')  # Don't load images
    chrome_options.add_argument('--blink-settings=imagesEnabled=false')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument(f'--user-agent={user_agent}')

    # Memory optimizations
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
                # Clean up multiple consecutive newlines
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
    """Track worker state for driver restart"""
    def __init__(self, worker_id):
        self.worker_id = worker_id
        self.requests_count = 0
        self.driver = None
        self.user_agent = CHROME_USER_AGENTS[worker_id % len(CHROME_USER_AGENTS)]

    def get_driver(self):
        """Get driver, creating new one if needed"""
        if self.driver is None or self.requests_count >= REQUESTS_PER_WORKER:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            self.driver = create_driver(self.user_agent)
            self.requests_count = 0
        return self.driver

    def increment(self):
        """Increment request counter"""
        self.requests_count += 1

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

    # Get driver (will restart if needed)
    driver = worker_state.get_driver()

    try:
        # Add delay between requests
        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        time.sleep(delay)

        # Load page
        driver.get(url)

        # Wait for content
        wait = WebDriverWait(driver, 30)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "mct-c-table")))

        # Additional wait for dynamic content
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

        worker_state.increment()

        return {
            'success': True,
            'plan_id': contract_plan_segment_id,
            'state': state_name
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

def save_progress(progress):
    """Save progress tracking data"""
    with progress_lock:
        with open(progress_file, 'w') as f:
            json.dump(progress, f, indent=2)

def main():
    print("="*80)
    print(f"OPTIMIZED MEDICARE PLAN SCRAPER")
    print(f"Workers: {NUM_WORKERS} (reduced for stability)")
    print(f"Driver restart every: {REQUESTS_PER_WORKER} requests")
    print(f"Delay between requests: {MIN_DELAY}-{MAX_DELAY} seconds")
    print(f"Batch size: {BATCH_SIZE} plans")
    print("="*80)

    # Load all state files
    state_files = sorted(state_data_dir.glob('*.json'))

    # Load progress
    progress = load_progress()
    completed_ids = set(progress['completed'])

    print(f"\nFound {len(state_files)} states")
    print(f"Already completed: {len(completed_ids)} plans")
    print()

    # Build list of all plans to scrape
    all_tasks = []
    for state_file in state_files:
        state_name = state_file.stem
        with open(state_file, 'r') as f:
            state_data = json.load(f)

        for plan in state_data:
            plan_id = plan['ContractPlanSegmentID']
            if plan_id not in completed_ids:
                all_tasks.append((plan, state_name))

    total_remaining = len(all_tasks)
    print(f"Plans to scrape: {total_remaining}")

    if total_remaining == 0:
        print("All plans already scraped!")
        return

    # Process in batches
    batch_num = 0
    for batch_start in range(0, total_remaining, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total_remaining)
        batch_tasks = all_tasks[batch_start:batch_end]
        batch_num += 1

        print(f"\n{'='*80}")
        print(f"BATCH {batch_num}: Processing plans {batch_start+1} to {batch_end} of {total_remaining}")
        print(f"{'='*80}\n")

        # Create worker states
        worker_states = [WorkerState(i) for i in range(NUM_WORKERS)]

        # Process batch
        success_count = 0
        failed_count = 0
        save_counter = 0

        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
            future_to_task = {}

            for i, (plan, state_name) in enumerate(batch_tasks):
                worker_state = worker_states[i % NUM_WORKERS]
                future = executor.submit(scrape_plan, plan, state_name, worker_state)
                future_to_task[future] = (plan['ContractPlanSegmentID'], state_name)

            for future in future_to_task:
                plan_id, state_name = future_to_task[future]
                result = future.result()

                if result['success']:
                    print(f"✓ {state_name}-{plan_id}")
                    progress['completed'].append(plan_id)
                    success_count += 1
                else:
                    print(f"✗ {state_name}-{plan_id}: {result.get('error', 'Unknown error')}")
                    progress['failed'].append({'plan_id': plan_id, 'state': state_name, 'error': result.get('error')})
                    failed_count += 1

                save_counter += 1
                if save_counter >= PROGRESS_SAVE_INTERVAL:
                    save_progress(progress)
                    save_counter = 0

        # Clean up worker states
        for worker_state in worker_states:
            worker_state.cleanup()

        # Save progress after batch
        save_progress(progress)

        print(f"\nBatch {batch_num} complete: {success_count} succeeded, {failed_count} failed")

        # Take a break between batches
        if batch_end < total_remaining:
            print("Taking a 30-second break before next batch...")
            time.sleep(30)

    print("\n" + "="*80)
    print("SCRAPING COMPLETE!")
    print(f"Total completed: {len(progress['completed'])}")
    print(f"Total failed: {len(progress['failed'])}")
    print("="*80)

if __name__ == "__main__":
    main()
