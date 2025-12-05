#!/usr/bin/env python3
"""
Retry failed plans with fresh driver for each request
More reliable but slightly slower
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

# Configuration - More conservative
NUM_WORKERS = 2  # Reduced to 2 for stability
MIN_DELAY = 2.0
MAX_DELAY = 4.0
PROGRESS_SAVE_INTERVAL = 5

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

def scrape_plan(plan_data, state_name, worker_id):
    """Scrape a single plan with fresh driver each time"""
    url = plan_data['url']
    contract_plan_segment_id = plan_data['ContractPlanSegmentID']

    user_agent = CHROME_USER_AGENTS[worker_id % len(CHROME_USER_AGENTS)]
    driver = None

    try:
        # Create fresh driver for this request
        driver = create_driver(user_agent)

        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        time.sleep(delay)

        driver.get(url)

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
        # Always clean up driver
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
    print(f"RETRY FAILED PLANS")
    print(f"Workers: {NUM_WORKERS} (fresh driver per plan)")
    print(f"Delay: {MIN_DELAY}-{MAX_DELAY} seconds")
    print("="*80)

    # Load progress
    progress = load_progress()
    completed_ids = set(progress['completed'])
    failed_plan_ids = {f['plan_id'] for f in progress.get('failed', [])}

    print(f"\nCompleted so far: {len(completed_ids)}")
    print(f"Failed attempts: {len(failed_plan_ids)}")

    # Build list of all uncompleted plans
    all_tasks = []
    state_files = sorted(state_data_dir.glob('*.json'))

    for state_file in state_files:
        state_name = state_file.stem
        with open(state_file, 'r') as f:
            state_data = json.load(f)

        for plan in state_data:
            plan_id = plan['ContractPlanSegmentID']
            # Include if not completed (regardless of previous failure)
            if plan_id not in completed_ids:
                all_tasks.append((plan, state_name))

    print(f"\nPlans to retry: {len(all_tasks)}")
    print(f"Estimated time: {len(all_tasks) * 25 / 3600:.1f} hours\n")

    if len(all_tasks) == 0:
        print("All plans already completed!")
        return

    # Clear old failures since we're retrying
    progress['failed'] = []

    # Process
    success_count = 0
    failed_count = 0
    address_ok_count = 0
    save_counter = 0
    start_time = time.time()

    try:
        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
            future_to_task = {}

            for i, (plan, state_name) in enumerate(all_tasks):
                future = executor.submit(scrape_plan, plan, state_name, i)
                future_to_task[future] = (plan['ContractPlanSegmentID'], state_name)

            for future in future_to_task:
                plan_id, state_name = future_to_task[future]
                result = future.result()

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
                    print(f"    Progress: {success_count}/{len(all_tasks)} success, {failed_count} failed | ETA: {eta_seconds/60:.0f} min")

    finally:
        # Final save
        save_progress(progress)

    elapsed = time.time() - start_time

    print("\n" + "="*80)
    print("RETRY COMPLETE!")
    print(f"Time elapsed: {elapsed:.0f} seconds ({elapsed/60:.1f} minutes)")
    print(f"Success: {success_count}/{len(all_tasks)}")
    print(f"Failed: {failed_count}/{len(all_tasks)}")
    print(f"Addresses with proper newlines: {address_ok_count}/{success_count}")
    print(f"Average time per plan: {elapsed/len(all_tasks):.1f} seconds")
    print("="*80)

    # Overall stats
    total_completed = len(progress['completed'])
    total_failed = len(progress['failed'])
    print(f"\nOVERALL PROGRESS:")
    print(f"Total completed: {total_completed}")
    print(f"Total failed: {total_failed}")
    print(f"Total remaining: {6581 - total_completed - total_failed}")

if __name__ == "__main__":
    main()
