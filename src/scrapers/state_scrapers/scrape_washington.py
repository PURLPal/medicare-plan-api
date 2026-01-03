#!/usr/bin/env python3
"""
Scrape Washington Medicare plans - 136 plans total.
Uses proven New Jersey URL format: 2026-HXXXX-XXX-X
"""
import json
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from parse_wa_raw_content import extract_plan_data

RAW_DIR = Path('raw_wa_plans')
RAW_DIR.mkdir(exist_ok=True)

SCRAPED_DIR = Path('scraped_json_all')
SCRAPED_DIR.mkdir(exist_ok=True)

PROGRESS_FILE = Path('wa_scraping_progress.json')

def load_progress():
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {'completed': [], 'failed': [], 'current_index': 0}

def save_progress(progress):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

def create_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=chrome_options)
    
    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="MacIntel",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )
    
    return driver

def scrape_raw_html(driver, plan_id, state='Washington'):
    zip_code = '98101'
    fips = '53033'
    
    # Convert plan_id format: H0029_007_0 -> 2026-H0029-007-0
    plan_id_formatted = f"2026-{plan_id.replace('_', '-')}"
    
    url = f'https://www.medicare.gov/plan-compare/#/plan-details/{plan_id_formatted}?fips={fips}&zip={zip_code}&year=2026&lang=en'
    
    try:
        driver.get(url)
        time.sleep(3)
        
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        time.sleep(2)
        
        page_source = driver.page_source
        
        # Better 404 detection - check page size and content
        if len(page_source) < 10000:
            return None, "Page too short"
        
        # Check if actual plan content exists
        if 'Total monthly premium' not in page_source and 'Plan ID:' not in page_source:
            return None, "No plan content found"
        
        return page_source, None
        
    except Exception as e:
        return None, str(e)

def main():
    print("\n" + "="*80)
    print("WASHINGTON MEDICARE PLAN SCRAPER")
    print("="*80)
    
    with open('wa_plans_to_scrape.json') as f:
        plans = json.load(f)
    
    progress = load_progress()
    
    print(f"\nTotal plans: {len(plans)}")
    print(f"Already completed: {len(progress['completed'])}")
    print(f"Failed: {len(progress['failed'])}")
    print(f"Remaining: {len(plans) - len(progress['completed']) - len(progress['failed'])}")
    
    driver = create_driver()
    
    try:
        for i in range(progress['current_index'], len(plans)):
            plan = plans[i]
            plan_id = plan['plan_id']
            
            if plan_id in progress['completed']:
                continue
            
            print(f"\n[{i+1}/{len(plans)}] Scraping {plan_id}...")
            
            raw_file = RAW_DIR / f'{plan_id}.html'
            json_file = SCRAPED_DIR / f'Washington-{plan_id}.json'
            
            if raw_file.exists():
                print(f"  ✓ Already exists")
                progress['completed'].append(plan_id)
                continue
            
            raw_content, error = scrape_raw_html(driver, plan_id)
            
            if error:
                print(f"  ✗ Failed: {error}")
                progress['failed'].append({'plan_id': plan_id, 'error': error})
                progress['current_index'] = i + 1
                save_progress(progress)
                continue
            
            with open(raw_file, 'w', encoding='utf-8') as f:
                f.write(raw_content)
            
            # Parse immediately
            success, parsed_data = extract_plan_data(raw_content)
            
            if success:
                parsed_data['plan_id'] = plan_id
                parsed_data['state'] = 'Washington'
                with open(json_file, 'w') as f:
                    json.dump(parsed_data, f, indent=2)
            else:
                # Fallback to basic data if parsing fails
                initial_data = {
                    'plan_id': plan_id,
                    'state': 'Washington',
                    'plan_info': {'name': plan.get('plan_name', ''), 'id': plan_id},
                    'premiums': {},
                    'deductibles': {},
                    'raw_content': ''
                }
                with open(json_file, 'w') as f:
                    json.dump(initial_data, f, indent=2)
            
            print(f"  ✓ Saved")
            progress['completed'].append(plan_id)
            progress['current_index'] = i + 1
            save_progress(progress)
            
            time.sleep(2)
    
    finally:
        driver.quit()
    
    print("\n" + "="*80)
    print("SCRAPING COMPLETE")
    print("="*80)
    print(f"✓ Success: {len(progress['completed'])}")
    print(f"✗ Failed: {len(progress['failed'])}")
    print("="*80 + "\n")

if __name__ == '__main__':
    main()
