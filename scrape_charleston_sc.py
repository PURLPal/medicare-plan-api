#!/usr/bin/env python3
"""
Scrape remaining Charleston County, SC Medicare plans for ZIP 29401.
Uses proven scraper with 100% success rate.
"""
import json
import time
import random
import os
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from bs4 import BeautifulSoup

MIN_DELAY, MAX_DELAY = 8.0, 15.0
HTML_DIR = Path('./scraped_html_all')
JSON_DIR = Path('./scraped_json_all')
HTML_DIR.mkdir(exist_ok=True)
JSON_DIR.mkdir(exist_ok=True)

USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
]
WINDOW_SIZES = ['1920,1080', '1366,768', '1536,864', '1440,900']

def create_driver():
    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_argument(f'--window-size={random.choice(WINDOW_SIZES)}')
    opts.add_argument(f'--user-agent={random.choice(USER_AGENTS)}')
    opts.add_experimental_option('prefs', {'profile.default_content_setting_values': {'images': 2}})
    driver = webdriver.Chrome(options=opts)
    
    stealth(driver,
        languages=['en-US', 'en'],
        vendor='Google Inc.',
        platform='Win32',
        webgl_vendor='Intel Inc.',
        renderer='Intel Iris OpenGL Engine',
        fix_hairline=True,
    )
    
    driver.set_page_load_timeout(60)
    return driver

def extract_data(html):
    soup = BeautifulSoup(html, 'html.parser')
    for br in soup.find_all('br'):
        br.replace_with('\n')
    
    data = {
        'plan_info': {}, 'premiums': {}, 'deductibles': {},
        'maximum_out_of_pocket': {}, 'contact_info': {},
        'benefits': {}, 'drug_coverage': {}, 'extra_benefits': {}
    }
    
    # Plan name
    plan_header = soup.select_one('h1.e2e-plan-details-plan-header, .e2e-plan-details-plan-header')
    if plan_header:
        data['plan_info']['name'] = plan_header.get_text(strip=True)
    else:
        for h1 in soup.find_all('h1'):
            text = h1.get_text(strip=True)
            if text and text.lower() != 'menu':
                data['plan_info']['name'] = text
                break
    
    # Plan info items
    for item in soup.select('.plan-info-item, .plan-detail-item'):
        label = item.select_one('.label, .item-label')
        value = item.select_one('.value, .item-value')
        if label and value:
            data['plan_info'][label.get_text(strip=True).rstrip(':')] = value.get_text(strip=True)
    
    # Sections
    section_map = {
        'premium': 'premiums', 'deductible': 'deductibles',
        'maximum out-of-pocket': 'maximum_out_of_pocket',
        'contact': 'contact_info', 'benefit': 'benefits',
        'drug': 'drug_coverage', 'extra': 'extra_benefits'
    }
    
    for section in soup.select('section, .section, .card, .benefit-section'):
        header = section.select_one('h2, h3, .section-header, .card-header')
        if not header:
            continue
        header_text = header.get_text(strip=True).lower()
        
        target = None
        for key, val in section_map.items():
            if key in header_text:
                target = val
                break
        
        if target:
            if target == 'benefits':
                subsection_name = header.get_text(strip=True)
                subsection_data = {}
                for row in section.select('tr, .benefit-row, .row'):
                    cells = row.select('td, .cell, .col')
                    if len(cells) >= 2:
                        subsection_data[cells[0].get_text(strip=True)] = cells[1].get_text(strip=True)
                if subsection_data:
                    data['benefits'][subsection_name] = subsection_data
            else:
                for row in section.select('tr, .row, .item'):
                    cells = row.select('td, .cell, .col, .label, .value')
                    if len(cells) >= 2:
                        data[target][cells[0].get_text(strip=True).rstrip(':')] = cells[1].get_text(strip=True)
    
    return data

def scrape_plan(driver, plan_id, contract, plan_num, segment):
    url = f"https://www.medicare.gov/plan-compare/#/plan-details/2026-{contract}-{plan_num}-{segment}?year=2026&lang=en"
    
    try:
        driver.get(url)
        time.sleep(random.uniform(3, 5))
        
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.e2e-plan-details-plan-header, h1'))
        )
        
        time.sleep(random.uniform(2, 4))
        return driver.page_source
    except Exception as e:
        print(f"    Error: {e}")
        return None

def main():
    # Load Charleston County plans to scrape
    with open('charleston_plans_to_scrape.json') as f:
        plans_to_scrape = json.load(f)
    
    print(f"=== Scraping Charleston County, SC Plans ===")
    print(f"Total plans to scrape: {len(plans_to_scrape)}")
    print(f"Destination: ZIP 29401\n")
    
    driver = create_driver()
    start_time = time.time()
    scraped_count = 0
    
    try:
        for i, plan in enumerate(plans_to_scrape, 1):
            plan_id = plan['plan_id']
            
            # Parse plan ID components
            parts = plan_id.split('_')
            contract = parts[0]
            plan_num = parts[1]
            segment = parts[2] if len(parts) > 2 else '0'
            
            # Check if already scraped
            json_file = JSON_DIR / f"South_Carolina-{plan_id}.json"
            if json_file.exists():
                # Check if it has good data
                try:
                    with open(json_file) as f:
                        existing = json.load(f)
                    if existing.get('premiums') and existing.get('benefits'):
                        print(f"[{i}/{len(plans_to_scrape)}] {plan_id}: Already scraped with good data, skipping")
                        continue
                except:
                    pass
            
            elapsed = time.time() - start_time
            rate = scraped_count / elapsed if elapsed > 0 and scraped_count > 0 else 0
            eta = (len(plans_to_scrape) - i) / rate / 60 if rate > 0 else 0
            
            print(f"[{i}/{len(plans_to_scrape)}] {plan_id}: {plan['name'][:50]}...")
            if eta > 0:
                print(f"  Progress: {i}/{len(plans_to_scrape)} | ETA: {eta:.1f} min")
            
            html = scrape_plan(driver, plan_id, contract, plan_num, segment)
            if html:
                # Save HTML
                html_file = HTML_DIR / f"South_Carolina-{plan_id}.html"
                with open(html_file, 'w') as f:
                    f.write(html)
                
                # Extract and save JSON
                data = extract_data(html)
                data['plan_id'] = plan_id
                data['state'] = 'South_Carolina'
                
                with open(json_file, 'w') as f:
                    json.dump(data, f, indent=2)
                
                scraped_count += 1
                print(f"  ✓")
            else:
                print(f"  ✗ Failed")
            
            # Delay
            delay = random.uniform(MIN_DELAY, MAX_DELAY)
            time.sleep(delay)
            
            # Restart browser every 25 plans
            if i % 25 == 0 and i < len(plans_to_scrape):
                print(f"\n  [Restarting browser after {i} plans...]\n")
                driver.quit()
                time.sleep(random.uniform(5, 10))
                driver = create_driver()
    
    finally:
        driver.quit()
    
    total_time = time.time() - start_time
    print(f"\n=== Complete ===")
    print(f"Scraped: {scraped_count} new plans")
    print(f"Time: {total_time / 60:.1f} minutes")
    print(f"Average: {total_time / scraped_count:.1f} seconds per plan" if scraped_count > 0 else "")
    
    # Verify total SC plans
    sc_files = list(JSON_DIR.glob('South_Carolina-*.json'))
    print(f"\nTotal South Carolina plans: {len(sc_files)}")
    print(f"Target for Charleston County (ZIP 29401): 69 plans")

if __name__ == '__main__':
    main()
