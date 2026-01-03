#!/usr/bin/env python3
"""
Test scraper for Rhode Island on EC2
Tests Chrome/Selenium setup and scrapes 5 RI plans as proof of concept
"""
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from pathlib import Path

# Load Rhode Island plans
with open('state_data/Rhode_Island.json') as f:
    all_plans = json.load(f)

# Test with first 5 plans
TEST_PLANS = all_plans[:5]

def create_driver():
    """Create Chrome driver for EC2."""
    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--disable-dev-shm-usage')  # Important for EC2!
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option('useAutomationExtension', False)
    opts.add_argument('--window-size=1920,1080')
    opts.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=opts)
    
    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Linux x86_64",  # EC2 platform
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )
    
    return driver

def scrape_plan(driver, plan_info):
    """Scrape a single plan."""
    plan_id = plan_info['ContractPlanSegmentID']
    plan_name = plan_info.get('Plan Name', 'Unknown')
    
    # Format URL
    plan_id_formatted = plan_id.replace('_', '-')
    url = f"https://www.medicare.gov/plan-compare/#/plan-details/2026-{plan_id_formatted}?year=2026&lang=en"
    
    print(f"  Scraping: {plan_id} - {plan_name[:50]}")
    
    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(6)  # Wait for React to hydrate
        
        html_content = driver.page_source
        
        # Check if valid plan
        if '<title>Medicare.gov</title>' in html_content or 'Page Not Found' in html_content:
            return {'status': 'not_found', 'size': 0}
        
        # Check for key data
        has_premium = 'premium' in html_content.lower()
        has_deductible = 'deductible' in html_content.lower()
        
        # Save to file
        output_file = Path(f'ri_test_output/{plan_id}.html')
        output_file.parent.mkdir(exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return {
            'status': 'success',
            'size': len(html_content),
            'has_premium': has_premium,
            'has_deductible': has_deductible
        }
        
    except Exception as e:
        return {'status': 'error', 'error': str(e)[:100]}

def main():
    print("="*80)
    print("RHODE ISLAND EC2 SCRAPING TEST")
    print("="*80)
    print(f"Testing with {len(TEST_PLANS)} plans\n")
    
    driver = create_driver()
    results = []
    
    try:
        for i, plan in enumerate(TEST_PLANS, 1):
            print(f"[{i}/{len(TEST_PLANS)}]")
            result = scrape_plan(driver, plan)
            result['plan_id'] = plan['ContractPlanSegmentID']
            results.append(result)
            
            if result['status'] == 'success':
                print(f"    ✅ Success - {result['size']:,} bytes")
                print(f"       Premium: {'✓' if result['has_premium'] else '✗'} | Deductible: {'✓' if result['has_deductible'] else '✗'}")
            elif result['status'] == 'not_found':
                print(f"    ⚠️  Plan not found")
            else:
                print(f"    ❌ Error: {result.get('error', 'Unknown')}")
            
            time.sleep(2)  # Rate limiting
        
    finally:
        driver.quit()
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    
    success = [r for r in results if r['status'] == 'success']
    not_found = [r for r in results if r['status'] == 'not_found']
    errors = [r for r in results if r['status'] == 'error']
    
    print(f"✅ Success: {len(success)}/{len(TEST_PLANS)}")
    print(f"⚠️  Not found: {len(not_found)}/{len(TEST_PLANS)}")
    print(f"❌ Errors: {len(errors)}/{len(TEST_PLANS)}")
    
    if success:
        avg_size = sum(r['size'] for r in success) / len(success)
        print(f"\nAverage HTML size: {avg_size:,.0f} bytes")
        
        with_data = [r for r in success if r['has_premium'] and r['has_deductible']]
        print(f"Plans with premium & deductible: {len(with_data)}/{len(success)}")
    
    print(f"\n{'='*80}")
    print("✅ EC2 Chrome/Selenium is working!")
    print(f"Output saved to: ri_test_output/")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
