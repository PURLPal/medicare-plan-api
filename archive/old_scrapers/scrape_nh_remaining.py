#!/usr/bin/env python3
"""
Scrape the 3 remaining New Hampshire plans with enhanced anti-detection measures
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

# Create directories
html_dir = Path('./scraped_html_selenium')
html_dir.mkdir(exist_ok=True)
json_dir = Path('./scraped_json_all')
json_dir.mkdir(exist_ok=True)

# Enhanced user agents
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
]

# The 3 missing plans
MISSING_PLANS = [
    "H5216_059_0",  # Humana USAA Honor Giveback (PPO)
    "H5216_138_0",  # HumanaChoice Giveback H5216-138 (PPO)
    "H7617_046_0",  # HumanaChoice Giveback H7617-046 (PPO)
]

def create_stealth_driver(user_agent):
    """Create a Chrome driver with enhanced stealth features"""
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')  # Use new headless mode
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument(f'user-agent={user_agent}')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Additional stealth options
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-software-rasterizer')
    
    driver = webdriver.Chrome(options=chrome_options)
    
    # Execute CDP commands to hide automation
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": user_agent
    })
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def extract_plan_data(html_content):
    """Extract relevant plan data from HTML (placeholder for now)"""
    # This is a simplified version - you may want to enhance this
    # to extract specific fields from the HTML
    return {
        "html_size": len(html_content),
        "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }

def scrape_plan(driver, plan_data, state_name="New_Hampshire"):
    """Scrape a single plan"""
    url = plan_data['url']
    contract_plan_segment_id = plan_data['ContractPlanSegmentID']
    
    print(f"\n{'='*80}")
    print(f"Scraping: {contract_plan_segment_id}")
    print(f"  Plan: {plan_data['Plan Name']}")
    print(f"  URL: {url}")
    print(f"{'='*80}")
    
    try:
        # Random delay between 5-10 seconds (longer to avoid detection)
        delay = random.uniform(5.0, 10.0)
        print(f"  Waiting {delay:.2f}s before request...")
        time.sleep(delay)
        
        # Navigate to the page
        print(f"  Loading page...")
        driver.get(url)
        
        # Wait for the plan name heading to appear
        print(f"  Waiting for content to load...")
        wait = WebDriverWait(driver, 30)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        
        # Wait for the actual data tables to load
        print(f"  Waiting for tables to render...")
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "mct-c-table")))
        
        # Give extra time for all content to fully render
        print(f"  Allowing content to fully render...")
        time.sleep(8)
        
        # Get the rendered HTML
        html_content = driver.page_source
        
        # Save the HTML
        html_filename = f"{state_name}_{contract_plan_segment_id}.html"
        html_path = html_dir / html_filename
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"  ✓ HTML saved to {html_path}")
        print(f"  Size: {len(html_content)} bytes")
        
        # Create a basic JSON file with the scraped data
        # You may want to parse the HTML more thoroughly later
        json_data = {
            **plan_data,
            "scraped_data": extract_plan_data(html_content),
            "html_file": html_filename
        }
        
        json_filename = f"{state_name}-{contract_plan_segment_id}.json"
        json_path = json_dir / json_filename
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)
        
        print(f"  ✓ JSON saved to {json_path}")
        
        return {
            'success': True,
            'size': len(html_content),
            'html_file': str(html_path),
            'json_file': str(json_path)
        }
        
    except TimeoutException:
        print(f"  ✗ Timeout waiting for content")
        return {
            'success': False,
            'error': 'Timeout waiting for content'
        }
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def main():
    # Load New Hampshire plans
    nh_file = Path('./state_data/New_Hampshire.json')
    with open(nh_file, 'r') as f:
        all_plans = json.load(f)
    
    # Filter to just the missing plans
    plans_to_scrape = [p for p in all_plans if p['ContractPlanSegmentID'] in MISSING_PLANS]
    
    print("="*80)
    print("SCRAPING REMAINING NEW HAMPSHIRE PLANS")
    print("="*80)
    print(f"Plans to scrape: {len(plans_to_scrape)}")
    for plan in plans_to_scrape:
        print(f"  - {plan['ContractPlanSegmentID']}: {plan['Plan Name']}")
    print()
    
    results = []
    
    # Use a different user agent for each plan
    for i, plan in enumerate(plans_to_scrape):
        user_agent = USER_AGENTS[i % len(USER_AGENTS)]
        
        print(f"\n{'#'*80}")
        print(f"PLAN {i+1}/{len(plans_to_scrape)}")
        print(f"{'#'*80}")
        print(f"Creating new Chrome driver...")
        print(f"User agent: {user_agent[:80]}...")
        
        driver = create_stealth_driver(user_agent)
        
        try:
            result = scrape_plan(driver, plan)
            results.append({
                'plan_id': plan['ContractPlanSegmentID'],
                'plan_name': plan['Plan Name'],
                'url': plan['url'],
                **result
            })
        finally:
            driver.quit()
            print(f"\nClosed driver for {plan['ContractPlanSegmentID']}")
            
            # Extra delay between plans (if not the last one)
            if i < len(plans_to_scrape) - 1:
                pause = random.uniform(10.0, 15.0)
                print(f"\nPausing {pause:.2f}s before next plan...")
                time.sleep(pause)
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    successful = sum(1 for r in results if r['success'])
    failed = sum(1 for r in results if not r['success'])
    
    print(f"Total plans: {len(results)}")
    print(f"✓ Successful: {successful}")
    print(f"✗ Failed: {failed}")
    
    if successful > 0:
        print("\nSuccessfully scraped:")
        for r in results:
            if r['success']:
                print(f"  ✓ {r['plan_id']}: {r['plan_name']}")
    
    if failed > 0:
        print("\nFailed to scrape:")
        for r in results:
            if not r['success']:
                print(f"  ✗ {r['plan_id']}: {r['error']}")
    
    # Save results log
    results_file = './nh_remaining_scrape_results.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {results_file}")
    print(f"HTML files saved to: {html_dir}/")
    print(f"JSON files saved to: {json_dir}/")
    
    if successful == len(results):
        print("\n🎉 All remaining New Hampshire plans successfully scraped!")

if __name__ == '__main__':
    main()
