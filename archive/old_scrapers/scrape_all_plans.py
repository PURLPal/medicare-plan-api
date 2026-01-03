#!/usr/bin/env python3
"""
Production scraper for all Medicare plans
Includes error handling, progress tracking, and resumption capability
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

def scrape_plan(driver, plan_data, state_name):
    """Scrape a single plan and save both HTML and JSON"""
    url = plan_data['url']
    contract_plan_segment_id = plan_data['ContractPlanSegmentID']

    print(f"  Scraping: {contract_plan_segment_id}")

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

        print(f"    ✓ Success! HTML: {len(html_content)} bytes, JSON saved")

        return {
            'success': True,
            'size': len(html_content),
            'html_file': str(html_path),
            'json_file': str(json_path)
        }

    except TimeoutException:
        print(f"    ✗ Timeout")
        return {'success': False, 'error': 'Timeout'}
    except Exception as e:
        print(f"    ✗ Error: {e}")
        return {'success': False, 'error': str(e)}

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
    print("MEDICARE PLAN SCRAPER - FULL PRODUCTION RUN")
    print("="*80)

    # Load all state files
    state_files = sorted(state_data_dir.glob('*.json'))

    # Load progress
    progress = load_progress()
    completed_ids = set(progress['completed'])

    print(f"\nFound {len(state_files)} states")
    print(f"Already completed: {len(completed_ids)} plans")
    print()

    # Count total plans
    total_plans = 0
    for state_file in state_files:
        with open(state_file, 'r') as f:
            plans = json.load(f)
            total_plans += len(plans)

    remaining = total_plans - len(completed_ids)
    print(f"Total plans: {total_plans}")
    print(f"Remaining: {remaining}")
    print("="*80)

    user_agent_idx = 0
    plans_scraped = 0

    for state_file in state_files:
        state_name = state_file.stem

        with open(state_file, 'r') as f:
            plans = json.load(f)

        # Filter out already completed plans
        plans_to_scrape = [p for p in plans if p['ContractPlanSegmentID'] not in completed_ids]

        if not plans_to_scrape:
            print(f"\n{state_name}: All {len(plans)} plans already completed ✓")
            continue

        print(f"\n{'='*80}")
        print(f"STATE: {state_name}")
        print(f"  Total plans: {len(plans)}")
        print(f"  Remaining: {len(plans_to_scrape)}")
        print(f"{'='*80}")

        # Create a new driver
        user_agent = CHROME_USER_AGENTS[user_agent_idx % len(CHROME_USER_AGENTS)]
        user_agent_idx += 1

        driver = create_driver(user_agent)

        try:
            for i, plan in enumerate(plans_to_scrape, 1):
                plan_id = plan['ContractPlanSegmentID']

                print(f"\n[{i}/{len(plans_to_scrape)}]", end=" ")
                result = scrape_plan(driver, plan, state_name)

                if result['success']:
                    progress['completed'].append(plan_id)
                    plans_scraped += 1
                else:
                    progress['failed'].append({
                        'plan_id': plan_id,
                        'state': state_name,
                        'error': result.get('error', 'Unknown')
                    })

                # Save progress every 10 plans
                if plans_scraped % 10 == 0:
                    save_progress(progress)
                    print(f"\n    Progress saved ({plans_scraped} total)")

        finally:
            driver.quit()
            save_progress(progress)
            print(f"\n  Driver closed, progress saved")

    # Final summary
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)
    print(f"Total plans scraped: {len(progress['completed'])}")
    print(f"Failed: {len(progress['failed'])}")

    if progress['failed']:
        print(f"\nFailed plans saved to: {progress_file}")

    print(f"\nHTML files: {html_dir}/")
    print(f"JSON files: {json_dir}/")
    print(f"Progress file: {progress_file}")

if __name__ == '__main__':
    main()
