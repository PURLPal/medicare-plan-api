#!/usr/bin/env python3
"""
Fast multi-threaded Medicare plan scraper using concurrent.futures
"""
import json
import random
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Directories
state_data_dir = Path('./state_data')
html_dir = Path('./scraped_html_all')
json_dir = Path('./scraped_json_all')
html_dir.mkdir(exist_ok=True)
json_dir.mkdir(exist_ok=True)

# Progress tracking
progress_file = Path('./scraping_progress.json')
progress_lock = threading.Lock()

# User agents for rotation
CHROME_USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
]

# Number of parallel workers
NUM_WORKERS = 8

def create_driver(user_agent):
    """Create a Chrome driver with specific user agent"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument(f'user-agent={user_agent}')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=chrome_options)
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

        # Categorize the table data
        title_lower = table_title.lower()

        if 'premium' in title_lower:
            plan_data['premiums'].update(table_data)
        elif 'deductible' in title_lower:
            plan_data['deductibles'].update(table_data)
        elif 'maximum you pay' in title_lower or 'moop' in title_lower:
            plan_data['maximum_out_of_pocket'].update(table_data)
        elif 'contact' in title_lower or 'address' in title_lower:
            plan_data['contact_info'].update(table_data)
        elif 'drug' in title_lower or 'pharmacy' in title_lower or 'tier' in title_lower or 'part b drug' in title_lower:
            if 'drug_tables' not in plan_data['drug_coverage']:
                plan_data['drug_coverage']['drug_tables'] = {}
            plan_data['drug_coverage']['drug_tables'][table_title] = table_data
        elif any(keyword in title_lower for keyword in ['hearing', 'dental', 'vision', 'fitness', 'transportation']):
            plan_data['extra_benefits'][table_title] = table_data
        else:
            plan_data['benefits'][table_title] = table_data

    return plan_data

def scrape_plan(plan_data, state_name, worker_id):
    """Scrape a single plan"""
    url = plan_data['url']
    contract_plan_segment_id = plan_data['ContractPlanSegmentID']

    user_agent = CHROME_USER_AGENTS[worker_id % len(CHROME_USER_AGENTS)]
    driver = create_driver(user_agent)

    try:
        # Random delay
        delay = random.uniform(1.0, 3.0)
        time.sleep(delay)

        # Navigate to the page
        driver.get(url)

        # Wait for content to load
        wait = WebDriverWait(driver, 30)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "mct-c-table")))

        # Extra time for full render
        time.sleep(5)

        # Get the rendered HTML
        html_content = driver.page_source

        # Save HTML
        safe_filename = f"{state_name}-{contract_plan_segment_id}.html"
        html_path = html_dir / safe_filename
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        # Parse and save JSON
        parsed_data = extract_plan_data(html_content)
        parsed_data['source_file'] = str(html_path)
        parsed_data['state'] = state_name
        parsed_data['plan_id'] = contract_plan_segment_id
        parsed_data['url'] = url

        json_filename = f"{state_name}-{contract_plan_segment_id}.json"
        json_path = json_dir / json_filename
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(parsed_data, f, indent=2, ensure_ascii=False)

        driver.quit()

        return {
            'success': True,
            'plan_id': contract_plan_segment_id,
            'state': state_name,
            'size': len(html_content)
        }

    except TimeoutException:
        driver.quit()
        return {
            'success': False,
            'plan_id': contract_plan_segment_id,
            'state': state_name,
            'error': 'Timeout'
        }
    except Exception as e:
        driver.quit()
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
    print(f"MULTI-THREADED MEDICARE PLAN SCRAPER - {NUM_WORKERS} WORKERS")
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
            plans = json.load(f)

        for plan in plans:
            if plan['ContractPlanSegmentID'] not in completed_ids:
                all_tasks.append((plan, state_name))

    print(f"Total plans to scrape: {len(all_tasks)}")
    print(f"Using {NUM_WORKERS} parallel workers")
    print("="*80)
    print()

    # Process in parallel using threads
    completed = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        # Submit all tasks
        future_to_task = {}
        for i, (plan, state_name) in enumerate(all_tasks):
            future = executor.submit(scrape_plan, plan, state_name, i)
            future_to_task[future] = (plan['ContractPlanSegmentID'], state_name)

        # Process results as they complete
        for future in as_completed(future_to_task):
            plan_id, state_name = future_to_task[future]
            try:
                result = future.result()

                if result['success']:
                    progress['completed'].append(result['plan_id'])
                    completed += 1
                    print(f"[{completed + failed}/{len(all_tasks)}] ✓ {result['state']}-{result['plan_id']}")
                else:
                    progress['failed'].append({
                        'plan_id': result['plan_id'],
                        'state': result['state'],
                        'error': result.get('error', 'Unknown')
                    })
                    failed += 1
                    print(f"[{completed + failed}/{len(all_tasks)}] ✗ {result['state']}-{result['plan_id']}: {result.get('error')}")

                # Save progress every 10 plans
                if (completed + failed) % 10 == 0:
                    save_progress(progress)
                    print(f"  Progress saved ({completed} completed, {failed} failed)")

            except Exception as e:
                print(f"[{completed + failed}/{len(all_tasks)}] ✗ {state_name}-{plan_id}: {e}")
                failed += 1

    # Final save
    save_progress(progress)

    # Final summary
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)
    print(f"Total completed: {completed}")
    print(f"Total failed: {failed}")
    print(f"Success rate: {100*completed/(completed+failed) if (completed+failed) > 0 else 0:.1f}%")
    print(f"\nHTML files: {html_dir}/")
    print(f"JSON files: {json_dir}/")
    print(f"Progress file: {progress_file}")

if __name__ == '__main__':
    main()
