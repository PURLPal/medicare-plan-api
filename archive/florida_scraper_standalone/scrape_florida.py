#!/usr/bin/env python3
"""
Florida Medicare Plan Scraper
Scrapes 621 Florida Medicare plans from Medicare.gov
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

# Configuration
MIN_DELAY = 8.0
MAX_DELAY = 15.0

# Directories
html_dir = Path('./scraped_html_all')
json_dir = Path('./scraped_json_all')
html_dir.mkdir(exist_ok=True)
json_dir.mkdir(exist_ok=True)

# User agents for stealth
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

WINDOW_SIZES = ['1920,1080', '1366,768', '1536,864', '1440,900']

def create_driver():
    """Create Chrome driver with stealth settings to avoid detection"""
    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option('useAutomationExtension', False)
    opts.add_argument(f'--window-size={random.choice(WINDOW_SIZES)}')
    opts.add_argument(f'--user-agent={random.choice(USER_AGENTS)}')
    
    # Disable images to speed up loading
    prefs = {'profile.default_content_setting_values': {'images': 2}}
    opts.add_experimental_option('prefs', prefs)
    
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(60)
    
    # Execute CDP commands to mask automation
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def extract_data(html):
    """Extract all plan data from HTML content"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Replace <br> tags with newlines for better address formatting
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
    
    # Extract plan header info
    hdr = soup.find('div', class_='PlanDetailsPagePlanInfo')
    if hdr:
        h1 = hdr.find('h1')
        if h1:
            plan_data['plan_info']['name'] = h1.get_text(strip=True)
        
        h2 = hdr.find('h2')
        if h2:
            plan_data['plan_info']['organization'] = h2.get_text(strip=True)
        
        for li in hdr.find_all('li'):
            text = li.get_text()
            if 'Plan type:' in text:
                plan_data['plan_info']['type'] = text.replace('Plan type:', '').strip()
            elif 'Plan ID:' in text:
                plan_data['plan_info']['id'] = text.replace('Plan ID:', '').strip()
    
    # Extract all tables
    for table in soup.find_all('table', class_='mct-c-table'):
        caption = table.find('caption')
        if not caption:
            continue
        
        table_title = caption.get_text(strip=True)
        table_data = {}
        
        for row in table.find_all('tr'):
            th = row.find('th')
            td = row.find('td')
            
            if th and td:
                header_text = re.sub(r"What's.*?\?", "", th.get_text(strip=True)).strip()
                cell_text = re.sub(r'\n\s*\n', '\n', td.get_text(separator='\n').strip())
                table_data[header_text] = cell_text
        
        # Categorize table data
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

def scrape_plan(plan):
    """Scrape a single plan"""
    pid = plan['ContractPlanSegmentID']
    driver = None
    
    try:
        # Create fresh driver for each plan (helps avoid detection)
        driver = create_driver()
        
        # Random delay before request
        delay = random.uniform(MIN_DELAY, MAX_DELAY) + random.uniform(0, 2)
        time.sleep(delay)
        
        # Load the page
        driver.get(plan['url'])
        
        # Wait for content to load
        wait = WebDriverWait(driver, 45)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        
        # Simulate human-like scrolling
        driver.execute_script(f"window.scrollBy(0, {random.randint(100, 500)})")
        time.sleep(random.uniform(0.5, 1.5))
        
        # Wait for tables to load
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "mct-c-table")))
        time.sleep(random.uniform(3, 6))
        
        # Get the page source
        html = driver.page_source
        
        # Save HTML
        with open(html_dir / f"Florida-{pid}.html", 'w', encoding='utf-8') as f:
            f.write(html)
        
        # Extract and save JSON
        data = extract_data(html)
        with open(json_dir / f"Florida-{pid}.json", 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        return {'success': True, 'plan_id': pid}
    
    except Exception as e:
        return {'success': False, 'plan_id': pid, 'error': str(e)[:200]}
    
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def main():
    # Load Florida plans
    with open('./state_data/Florida.json') as f:
        plans = json.load(f)
    
    print('='*80)
    print('FLORIDA MEDICARE PLAN SCRAPER')
    print('='*80)
    print(f'Total plans to scrape: {len(plans)}')
    print(f'Delay: {MIN_DELAY}-{MAX_DELAY} seconds + jitter')
    print(f'Estimated time: {len(plans) * 0.4:.0f} minutes ({len(plans) * 0.4 / 60:.1f} hours)')
    print('='*80)
    print()
    
    results = []
    success_count = 0
    start_time = time.time()
    
    for i, plan in enumerate(plans, 1):
        print(f"[{i}/{len(plans)}] {plan['ContractPlanSegmentID']}: {plan['Plan Name'][:50]}")
        
        result = scrape_plan(plan)
        results.append(result)
        
        if result['success']:
            success_count += 1
            print(f"  ✓ Success")
        else:
            print(f"  ✗ Failed: {result.get('error', '')[:50]}")
        
        # Pause between plans
        if i < len(plans):
            pause = random.uniform(10.0, 15.0)
            time.sleep(pause)
        
        # Progress update every 10 plans
        if i % 10 == 0:
            elapsed = time.time() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            remaining = len(plans) - i
            eta_seconds = remaining / rate if rate > 0 else 0
            print(f"  Progress: {success_count}/{i} succeeded | ETA: {eta_seconds/60:.1f} min")
        
        print()
    
    elapsed = time.time() - start_time
    
    print('='*80)
    print('FLORIDA SCRAPE COMPLETE!')
    print('='*80)
    print(f'Time elapsed: {elapsed/60:.1f} minutes ({elapsed/3600:.2f} hours)')
    print(f'Success: {success_count}/{len(plans)} ({success_count/len(plans)*100:.1f}%)')
    print(f'Failed: {len(plans) - success_count}')
    print('='*80)
    
    # Save results
    with open('./florida_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print(f'\nResults saved to: ./florida_results.json')
    
    if success_count < len(plans):
        failed_ids = [r['plan_id'] for r in results if not r['success']]
        print(f'\nFailed plan IDs ({len(failed_ids)}):')
        for plan_id in failed_ids[:20]:  # Show first 20
            print(f'  - {plan_id}')
        if len(failed_ids) > 20:
            print(f'  ... and {len(failed_ids) - 20} more')

if __name__ == "__main__":
    main()
