#!/usr/bin/env python3
"""
Balanced scraper - faster with stealth
- 4 workers for 4x speed improvement
- 5-8 second delays (still respectful)
- Anti-detection features
- Should complete in ~8-10 hours instead of 34
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

# Balanced configuration
NUM_WORKERS = 4  # 4x parallelism
MIN_DELAY = 5.0  # Faster but still safe
MAX_DELAY = 8.0
PROGRESS_SAVE_INTERVAL = 10

# Directories
state_data_dir = Path('./state_data')
html_dir = Path('./scraped_html_all')
json_dir = Path('./scraped_json_all')
html_dir.mkdir(exist_ok=True)
json_dir.mkdir(exist_ok=True)

progress_file = Path('./scraping_progress.json')
progress_lock = Lock()

USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
]

WINDOW_SIZES = ['1920,1080', '1366,768', '1536,864', '1440,900']

def create_stealth_driver(worker_id):
    """Create Chrome driver with stealth settings"""
    user_agent = USER_AGENTS[worker_id % len(USER_AGENTS)]
    window_size = WINDOW_SIZES[worker_id % len(WINDOW_SIZES)]

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
    chrome_options.add_argument('--disable-images')

    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(50)

    # Mask automation
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": user_agent})
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return driver

def extract_plan_data(html_content):
    """Extract all plan data from HTML content"""
    soup = BeautifulSoup(html_content, 'html.parser')
    for br in soup.find_all('br'):
        br.replace_with('\n')

    plan_data = {
        'plan_info': {}, 'premiums': {}, 'deductibles': {},
        'maximum_out_of_pocket': {}, 'contact_info': {},
        'benefits': {}, 'drug_coverage': {}, 'extra_benefits': {}
    }

    plan_header_section = soup.find('div', class_='PlanDetailsPagePlanInfo')
    if plan_header_section:
        plan_name_h1 = plan_header_section.find('h1')
        if plan_name_h1:
            plan_data['plan_info']['name'] = plan_name_h1.get_text(strip=True)
        plan_name_h2 = plan_header_section.find('h2')
        if plan_name_h2:
            plan_data['plan_info']['organization'] = plan_name_h2.get_text(strip=True)
        for li in plan_header_section.find_all('li'):
            text = li.get_text()
            if 'Plan type:' in text:
                plan_data['plan_info']['type'] = text.replace('Plan type:', '').strip()
            elif 'Plan ID:' in text:
                plan_data['plan_info']['id'] = text.replace('Plan ID:', '').strip()

    tables = soup.find_all('table', class_='mct-c-table')
    for table in tables:
        caption = table.find('caption')
        if not caption:
            continue
        table_title = caption.get_text(strip=True)
        table_data = {}
        for row in table.find_all('tr'):
            header = row.find('th')
            cell = row.find('td')
            if header and cell:
                header_text = re.sub(r"What's.*?\?", "", header.get_text(strip=True)).strip()
                cell_text = re.sub(r'\n\s*\n', '\n', cell.get_text(separator='\n').strip())
                table_data[header_text] = cell_text

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
    """Scrape a single plan"""
    url = plan_data['url']
    contract_plan_segment_id = plan_data['ContractPlanSegmentID']
    driver = None

    try:
        driver = create_stealth_driver(worker_id)

        # Randomized delay
        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        time.sleep(delay)

        driver.get(url)
        wait = WebDriverWait(driver, 40)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "mct-c-table")))
        time.sleep(random.uniform(2, 4))

        html_content = driver.page_source

        # Save files
        safe_filename = f"{state_name}-{contract_plan_segment_id}.html"
        with open(html_dir / safe_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)

        plan_info = extract_plan_data(html_content)
        json_filename = f"{state_name}-{contract_plan_segment_id}.json"
        with open(json_dir / json_filename, 'w', encoding='utf-8') as f:
            json.dump(plan_info, f, indent=2)

        address = plan_info.get('contact_info', {}).get('Plan address', '')
        return {
            'success': True,
            'plan_id': contract_plan_segment_id,
            'state': state_name,
            'address_ok': '\n' in address
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
    if progress_file.exists():
        with open(progress_file, 'r') as f:
            return json.load(f)
    return {'completed': [], 'failed': []}

def save_progress(progress):
    with progress_lock:
        with open(progress_file, 'w') as f:
            json.dump(progress, f, indent=2)

def main():
    print("="*80)
    print(f"BALANCED SCRAPER - Speed + Stealth")
    print(f"Workers: {NUM_WORKERS} parallel")
    print(f"Delay: {MIN_DELAY}-{MAX_DELAY} seconds per request")
    print(f"Anti-detection: Randomized user agents, window sizes, WebDriver masking")
    print("="*80)

    progress = load_progress()
    completed_ids = set(progress['completed'])
    print(f"\nCompleted so far: {len(completed_ids)}")

    all_tasks = []
    for state_file in sorted(state_data_dir.glob('*.json')):
        with open(state_file, 'r') as f:
            for plan in json.load(f):
                if plan['ContractPlanSegmentID'] not in completed_ids:
                    all_tasks.append((plan, state_file.stem))

    random.shuffle(all_tasks)  # Randomize order
    print(f"Plans to scrape: {len(all_tasks)}")
    est_hours = len(all_tasks) * (MIN_DELAY + MAX_DELAY) / 2 / NUM_WORKERS / 3600
    print(f"Estimated time: {est_hours:.1f} hours\n")

    if not all_tasks:
        print("All plans completed!")
        return

    progress['failed'] = []
    success_count = failed_count = address_ok_count = save_counter = 0
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        future_to_task = {}
        for i, (plan, state_name) in enumerate(all_tasks):
            future = executor.submit(scrape_plan, plan, state_name, i % NUM_WORKERS)
            future_to_task[future] = (plan['ContractPlanSegmentID'], state_name)

        for future in future_to_task:
            plan_id, state_name = future_to_task[future]
            result = future.result()

            if result['success']:
                addr_ind = "✓" if result.get('address_ok') else "✗"
                print(f"✓ [{success_count+1}] {state_name:30s} {plan_id} {addr_ind}")
                progress['completed'].append(plan_id)
                success_count += 1
                if result.get('address_ok'):
                    address_ok_count += 1
            else:
                error_msg = result.get('error', '')[:50]
                print(f"✗ [{success_count+failed_count+1}] {state_name:30s} {plan_id}: {error_msg}")
                progress['failed'].append({
                    'plan_id': plan_id,
                    'state': state_name,
                    'error': result.get('error')
                })
                failed_count += 1

            save_counter += 1
            if save_counter >= PROGRESS_SAVE_INTERVAL:
                save_progress(progress)
                save_counter = 0
                elapsed = time.time() - start_time
                completed = success_count + failed_count
                rate = completed / elapsed if elapsed > 0 else 0
                remaining = len(all_tasks) - completed
                eta = remaining / rate if rate > 0 else 0
                success_rate = success_count / completed * 100 if completed else 0
                print(f"    [{success_count}/{len(all_tasks)}] Success: {success_rate:.1f}% | ETA: {eta/3600:.1f}hrs")

    save_progress(progress)
    elapsed = time.time() - start_time

    print("\n" + "="*80)
    print("SCRAPING COMPLETE!")
    print(f"Time: {elapsed/3600:.1f} hours")
    print(f"Success: {success_count}/{len(all_tasks)} ({success_count/(success_count+failed_count)*100:.1f}%)")
    print(f"Failed: {failed_count}")
    print(f"Addresses OK: {address_ok_count}/{success_count}")
    print("="*80)

if __name__ == "__main__":
    main()
