#!/usr/bin/env python3
"""
Scrape the remaining 35 South Carolina Medicare plans to complete coverage.
Uses robust extraction similar to scrape_priority_plans.py
"""
import json
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth
from bs4 import BeautifulSoup

# Missing plan IDs
MISSING_PLANS = [
    "H3146_036_0", "H3146_038_0", "H3146_040_0", "H5216_466_0",
    "H5521_140_0", "H5521_245_0", "H5521_249_0", "H5521_251_0",
    "H5521_319_0", "H5521_500_0", "H5525_049_0", "H6345_002_0",
    "H7020_010_1", "H7020_010_2", "H7020_011_1", "H7020_011_2",
    "H7849_136_1", "H7849_136_2", "H8003_001_0", "H8003_002_0",
    "H8003_004_0", "H8003_005_0", "H8145_069_0", "H8176_004_1",
    "S4802_070_0", "S4802_144_0", "S5601_018_0", "S5617_218_0",
    "S5617_359_0", "S5884_134_0", "S5884_155_0", "S5884_188_0",
    "S5921_354_0", "S5921_391_0", "S5953_001_0"
]

OUTPUT_DIR = Path("scraped_json_all")
OUTPUT_DIR.mkdir(exist_ok=True)

def setup_driver():
    """Setup Chrome driver with stealth options."""
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=chrome_options)
    
    # Apply stealth
    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="MacIntel",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )
    
    return driver

def extract_section_data(soup, section_id):
    """Extract data from a section by ID."""
    section = soup.find('div', id=section_id)
    if not section:
        return {}
    
    data = {}
    rows = section.find_all('div', class_='m-c-table__body-row')
    
    for row in rows:
        cells = row.find_all('div', class_='m-c-table__body-cell')
        if len(cells) >= 2:
            label_elem = cells[0].find('span', class_='m-c-table__label')
            value_elem = cells[1].find('span', class_='m-c-table__value')
            
            if label_elem and value_elem:
                label = label_elem.get_text(strip=True)
                value = value_elem.get_text(strip=True)
                data[label] = value
    
    return data

def extract_benefits_data(soup):
    """Extract benefits sections."""
    benefits = {}
    
    # Find all benefit sections
    benefit_sections = soup.find_all('div', class_='m-c-compare-table')
    
    for section in benefit_sections:
        # Get section title
        title_elem = section.find_previous('h3')
        if not title_elem:
            continue
        
        section_title = title_elem.get_text(strip=True)
        section_data = {}
        
        # Get rows
        rows = section.find_all('div', class_='m-c-table__body-row')
        for row in rows:
            cells = row.find_all('div', class_='m-c-table__body-cell')
            if len(cells) >= 2:
                label_elem = cells[0].find('span', class_='m-c-table__label')
                value_elem = cells[1].find('span', class_='m-c-table__value')
                
                if label_elem and value_elem:
                    label = label_elem.get_text(strip=True)
                    value = value_elem.get_text(strip=True)
                    section_data[label] = value
        
        if section_data:
            benefits[section_title] = section_data
    
    return benefits

def extract_data(driver, plan_id):
    """Extract all data from a plan detail page."""
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    data = {
        'plan_id': plan_id,
        'state': 'South_Carolina',
        'plan_info': {},
        'premiums': {},
        'deductibles': {},
        'out_of_pocket': {},
        'benefits': {}
    }
    
    # Extract plan name and organization
    try:
        name_elem = soup.find('h1', class_='plan-name')
        if name_elem:
            data['plan_info']['name'] = name_elem.get_text(strip=True)
        
        org_elem = soup.find('div', class_='organization-name')
        if org_elem:
            data['plan_info']['organization'] = org_elem.get_text(strip=True)
    except Exception as e:
        print(f"  Warning: Could not extract plan name/org: {e}")
    
    # Extract premiums
    data['premiums'] = extract_section_data(soup, 'premiums')
    
    # Extract deductibles
    data['deductibles'] = extract_section_data(soup, 'deductibles')
    
    # Extract out of pocket costs
    data['out_of_pocket'] = extract_section_data(soup, 'out-of-pocket-costs')
    
    # Extract benefits
    data['benefits'] = extract_benefits_data(soup)
    
    return data

def scrape_plan(driver, plan_id, zip_code="29401"):
    """Scrape a single plan."""
    url = f"https://www.medicare.gov/plan/details/{plan_id}?zip={zip_code}&year=2026"
    
    print(f"Scraping {plan_id}...", flush=True)
    
    try:
        driver.get(url)
        
        # Wait for page to load
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except:
            print(f"  ⚠ Timeout waiting for page")
        
        # Additional wait for dynamic content
        time.sleep(3)
        
        # Extract data
        data = extract_data(driver, plan_id)
        
        # Save to file
        output_file = OUTPUT_DIR / f"South_Carolina-{plan_id}.json"
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Check data quality
        premium_count = len(data.get('premiums', {}))
        benefit_sections = len(data.get('benefits', {}))
        
        print(f"  ✓ Premiums: {premium_count} | Benefits: {benefit_sections} sections", flush=True)
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}", flush=True)
        return False

def main():
    print("="*80)
    print("SCRAPING MISSING SOUTH CAROLINA PLANS")
    print("="*80)
    print(f"\nTotal plans to scrape: {len(MISSING_PLANS)}")
    print(f"Output directory: {OUTPUT_DIR}")
    
    driver = setup_driver()
    
    try:
        success_count = 0
        failed_plans = []
        
        for i, plan_id in enumerate(MISSING_PLANS, 1):
            print(f"\n[{i}/{len(MISSING_PLANS)}]", end=" ")
            
            if scrape_plan(driver, plan_id):
                success_count += 1
            else:
                failed_plans.append(plan_id)
            
            # Brief pause between requests
            time.sleep(1)
        
        print("\n" + "="*80)
        print("SCRAPING COMPLETE")
        print("="*80)
        print(f"\nSuccessful: {success_count}/{len(MISSING_PLANS)}")
        
        if failed_plans:
            print(f"\nFailed plans ({len(failed_plans)}):")
            for plan_id in failed_plans:
                print(f"  - {plan_id}")
        else:
            print("\n✓ All plans scraped successfully!")
        
        # Final count
        total_sc_files = len(list(OUTPUT_DIR.glob("South_Carolina-*.json")))
        print(f"\nTotal SC plans now: {total_sc_files}")
        print(f"Target: 106 plans")
        print(f"Progress: {total_sc_files}/106 = {(total_sc_files/106*100):.1f}%")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
