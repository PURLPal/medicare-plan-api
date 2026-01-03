#!/usr/bin/env python3
"""
Re-scrape 3 priority plans for ZIP 29401 to ensure perfect data quality.
Plans: H5322_043_0, H5322_044_0, R2604_005_0
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

JSON_DIR = Path('./scraped_json_all')
JSON_DIR.mkdir(exist_ok=True)

# Priority plans
PRIORITY_PLANS = [
    {
        'plan_id': 'H5322_043_0',
        'contract': 'H5322',
        'plan_num': '043',
        'segment': '0',
        'name': 'AARP Medicare Advantage Patriot No Rx SC-MA01 (HMO-POS)'
    },
    {
        'plan_id': 'H5322_044_0',
        'contract': 'H5322',
        'plan_num': '044',
        'segment': '0',
        'name': 'AARP Medicare Advantage from UHC SC-0006 (HMO-POS)'
    },
    {
        'plan_id': 'R2604_005_0',
        'contract': 'R2604',
        'plan_num': '005',
        'segment': '0',
        'name': 'UHC Medicare Advantage Patriot No Rx GS-MA01 (Regional PPO)'
    }
]

USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

def create_driver():
    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_argument('--window-size=1920,1080')
    opts.add_argument(f'--user-agent={USER_AGENTS[0]}')
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
    """Extract data using BeautifulSoup like batch_7 scraper."""
    soup = BeautifulSoup(html, 'html.parser')
    for br in soup.find_all('br'):
        br.replace_with('\n')
    
    data = {
        'plan_info': {}, 'premiums': {}, 'deductibles': {},
        'maximum_out_of_pocket': {}, 'contact_info': {},
        'benefits': {}, 'drug_coverage': {}, 'extra_benefits': {}
    }
    
    # Plan name
    for h1 in soup.find_all('h1'):
        text = h1.get_text(strip=True)
        if text and text.lower() != 'menu':
            data['plan_info']['name'] = text
            break
    
    # Extract sections
    section_map = {
        'premium': 'premiums', 
        'deductible': 'deductibles',
        'maximum': 'maximum_out_of_pocket',
        'contact': 'contact_info', 
        'benefit': 'benefits',
        'drug': 'drug_coverage', 
        'extra': 'extra_benefits'
    }
    
    for section in soup.select('section, .section, .card'):
        header = section.select_one('h2, h3, .section-header')
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
                for row in section.select('tr, .benefit-row'):
                    cells = row.select('td, .cell')
                    if len(cells) >= 2:
                        subsection_data[cells[0].get_text(strip=True)] = cells[1].get_text(strip=True)
                if subsection_data:
                    data['benefits'][subsection_name] = subsection_data
            else:
                for row in section.select('tr, .row'):
                    cells = row.select('td, .cell')
                    if len(cells) >= 2:
                        key = cells[0].get_text(strip=True).rstrip(':')
                        value = cells[1].get_text(strip=True)
                        data[target][key] = value
    
    return data

def scrape_plan(driver, plan):
    """Scrape a single plan."""
    url = f"https://www.medicare.gov/plan-compare/#/plan-details/2026-{plan['contract']}-{plan['plan_num']}-{plan['segment']}?year=2026&lang=en"
    
    print(f"\n  URL: {url}")
    
    try:
        driver.get(url)
        time.sleep(random.uniform(3, 5))
        
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'h1, .e2e-plan-details-plan-header'))
        )
        
        time.sleep(random.uniform(2, 4))
        return driver.page_source
    except Exception as e:
        print(f"  Error: {e}")
        return None

def main():
    print("=== Re-scraping Priority Plans for ZIP 29401 ===\n")
    print("Plans to scrape:")
    for p in PRIORITY_PLANS:
        print(f"  - {p['plan_id']}: {p['name']}")
    print()
    
    driver = create_driver()
    success = 0
    
    try:
        for i, plan in enumerate(PRIORITY_PLANS, 1):
            plan_id = plan['plan_id']
            print(f"[{i}/{len(PRIORITY_PLANS)}] {plan_id}")
            print(f"  {plan['name'][:60]}")
            
            html = scrape_plan(driver, plan)
            if html:
                # Extract data
                data = extract_data(html)
                data['plan_id'] = plan_id
                data['state'] = 'South_Carolina'
                data['scraped_at'] = time.strftime('%Y-%m-%dT%H:%M:%S')
                
                # Save
                json_file = JSON_DIR / f"South_Carolina-{plan_id}.json"
                with open(json_file, 'w') as f:
                    json.dump(data, f, indent=2)
                
                # Verify quality
                prem_count = len(data.get('premiums', {}))
                ded_count = len(data.get('deductibles', {}))
                ben_count = len(data.get('benefits', {}))
                
                print(f"  ✓ Scraped: {prem_count} premiums, {ded_count} deductibles, {ben_count} benefit sections")
                
                if prem_count >= 3 and ben_count >= 5:
                    print(f"  ✓ Quality: EXCELLENT")
                    success += 1
                elif prem_count >= 2:
                    print(f"  ✓ Quality: GOOD")
                    success += 1
                else:
                    print(f"  ⚠ Quality: POOR")
            else:
                print(f"  ✗ Failed to scrape")
            
            # Delay between plans
            if i < len(PRIORITY_PLANS):
                delay = random.uniform(10, 15)
                print(f"  Waiting {delay:.1f}s...")
                time.sleep(delay)
    
    finally:
        driver.quit()
    
    print(f"\n=== Complete ===")
    print(f"Successfully scraped: {success}/{len(PRIORITY_PLANS)}")

if __name__ == '__main__':
    main()
