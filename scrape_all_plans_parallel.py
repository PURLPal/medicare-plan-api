#!/usr/bin/env python3
"""
Parallel Medicare plan scraper using multiple Selenium instances
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
from bs4 import BeautifulSoup, NavigableString
import re
from multiprocessing import Pool, Manager
import threading

# Directories
state_data_dir = Path('./state_data')
html_dir = Path('./scraped_html_all')
json_dir = Path('./scraped_json_all')
html_dir.mkdir(exist_ok=True)
json_dir.mkdir(exist_ok=True)

# Progress tracking
progress_file = Path('./scraping_progress.json')

# User agents for rotation
CHROME_USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
]

# Number of parallel workers
NUM_WORKERS = 4

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

def extract_text_with_breaks(element):
    """Extract text from element preserving line breaks"""
    if element is None:
        return ""

    parts = []
    for item in element.descendants:
        if isinstance(item, NavigableString):
            text = str(item).strip()
            if text:
                parts.append(text)
        elif item.name == 'br':
            parts.append('\n')

    # Join and clean up
    text = ''.join(parts)
    # Replace multiple newlines with single newline
    text = re.sub(r'\n+', '\n', text)
    return text.strip()

def extract_plan_data(html_content):
    """Extract all plan data from HTML content"""
    soup = BeautifulSoup(html_content, 'html.parser')

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

                # Extract cell text preserving line breaks
                cell_text = extract_text_with_breaks(cell)

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

def scrape_plan(args):
    """Scrape a single plan - designed for multiprocessing"""
    plan_data, state_name, worker_id, completed_set = args

    url = plan_data['url']
    contract_plan_segment_id = plan_data['ContractPlanSegmentID']

    # Check if already completed
    if contract_plan_segment_id in completed_set:
        return {'success': True, 'skipped': True, 'plan_id': contract_plan_segment_id}

    user_agent = CHROME_USER_AGENTS[worker_id % len(CHROME_USER_AGENTS)]
    driver = create_driver(user_agent)

    try:
        # Random delay
        delay = random.uniform(2.0, 5.0)
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
            'skipped': False,
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
    with open(progress_file, 'w') as f:
        json.dump(progress, f, indent=2)

def main():
    print("="*80)
    print(f"PARALLEL MEDICARE PLAN SCRAPER - {NUM_WORKERS} WORKERS")
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
                all_tasks.append((plan, state_name, len(all_tasks), completed_ids))

    print(f"Total plans to scrape: {len(all_tasks)}")
    print(f"Using {NUM_WORKERS} parallel workers")
    print("="*80)
    print()

    # Process in parallel
    with Pool(NUM_WORKERS) as pool:
        results_iter = pool.imap_unordered(scrape_plan, all_tasks)

        completed = 0
        failed = 0

        for result in results_iter:
            if result.get('skipped'):
                continue

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

    # Final save
    save_progress(progress)

    # Final summary
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)
    print(f"Total completed: {completed}")
    print(f"Total failed: {failed}")
    print(f"Success rate: {100*completed/(completed+failed):.1f}%")
    print(f"\nHTML files: {html_dir}/")
    print(f"JSON files: {json_dir}/")
    print(f"Progress file: {progress_file}")

if __name__ == '__main__':
    main()
