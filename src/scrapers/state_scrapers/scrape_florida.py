#!/usr/bin/env python3
"""
Scrape remaining Florida Medicare plans using optimized two-step approach.
Florida has 621 total plans, with 417 already scraped.
Based on successful Massachusetts and Arizona scraping methodology.
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

# Directories
RAW_DIR = Path('./raw_fl_plans')
RAW_DIR.mkdir(exist_ok=True)

JSON_DIR = Path('./scraped_json_all')
JSON_DIR.mkdir(exist_ok=True)

# Progress file for resumability
PROGRESS_FILE = Path('./fl_scraping_progress.json')

def load_progress():
    """Load scraping progress from file."""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {'completed': [], 'not_found': [], 'errors': []}

def save_progress(progress):
    """Save scraping progress to file."""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

# Load plans to scrape from state data
STATE_DATA_FILE = Path('./state_data/Florida.json')
with open(STATE_DATA_FILE) as f:
    all_plans = json.load(f)

# Check which plans already have scraped JSON files
existing_json = set()
for json_file in JSON_DIR.glob('Florida-*.json'):
    plan_id = json_file.stem.replace('Florida-', '')
    existing_json.add(plan_id)

# Load progress
progress = load_progress()

# Filter out already completed plans (from both progress file AND existing JSON files)
already_completed = set(progress['completed'] + progress['not_found']) | existing_json
PLANS_TO_SCRAPE = [p for p in all_plans if p['plan_id'] not in already_completed]

print(f"Total FL plans: {len(all_plans)}")
print(f"Previously completed: {len(already_completed)}")
if already_completed:
    print(f"  ✓ Success: {len(progress['completed'])}")
    print(f"  ⚠️  Not found: {len(progress['not_found'])}")
    print(f"  ✗ Errors: {len(progress['errors'])}")
    print(f"  📁 Existing JSON files: {len(existing_json)}")
print(f"Remaining to scrape: {len(PLANS_TO_SCRAPE)}")

def create_driver():
    """Create Chrome driver with stealth options to avoid bot detection."""
    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option('useAutomationExtension', False)
    opts.add_argument('--window-size=1920,1080')
    opts.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=opts)
    
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

def scrape_raw_html(driver, plan_id, zip_code="33101"):
    """Step 1: Scrape and save raw HTML."""
    # New Medicare.gov URL format (changed in 2026)
    # Convert underscores to hyphens (e.g., H2256_015_2 -> H2256-015-2)
    plan_id_formatted = plan_id.replace('_', '-')
    url = f"https://www.medicare.gov/plan-compare/#/plan-details/2026-{plan_id_formatted}?year=2026&lang=en"
    
    try:
        driver.get(url)
        
        # Wait for React app to load (SPA with # routing)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Extra wait for dynamic content to fully render
        # React apps take longer to hydrate content
        time.sleep(6)
        
        # Save raw HTML
        raw_file = RAW_DIR / f"{plan_id}.html"
        html_content = driver.page_source
        with open(raw_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Check if plan loaded successfully
        # React SPA loads, so check for plan content instead of 404 errors
        # Valid plans have the plan name in the title tag
        if '<title>Medicare.gov</title>' in html_content or 'Page Not Found' in html_content:
            return 'not_found'
        
        # Check if actual plan content exists (plan name, premiums, etc.)
        if 'HMO' in html_content or 'PPO' in html_content or 'Premium' in html_content:
            return 'success'
        
        return 'not_found'
        
    except Exception as e:
        print(f"    Error: {str(e)[:50]}")
        return 'error'

def create_plan_json(plan_info):
    """Create initial JSON structure for a plan."""
    return {
        "plan_id": plan_info['plan_id'],
        "state": "Florida",
        "county": plan_info.get('county', ''),
        "fips": plan_info.get('fips', ''),
        "plan_info": {
            "name": "",
            "type": "",
            "organization": ""
        },
        "premiums": {},
        "deductibles": {},
        "out_of_pocket": {},
        "benefits": {},
        "raw_content": ""
    }

def main():
    print("="*80)
    print("FLORIDA MEDICARE PLAN SCRAPER (RESUMABLE)")
    print("="*80)
    print(f"Plans to scrape: {len(PLANS_TO_SCRAPE)}")
    print(f"Output: {RAW_DIR}")
    print()
    
    if PLANS_TO_SCRAPE:
        print("Press Ctrl+C at any time to safely stop scraping.")
        print("Progress is saved after each plan - you can resume later.\n")
    else:
        print("✓ All plans already scraped!")
        print(f"\nRun: python3 parse_fl_raw_content.py")
        return
    
    driver = create_driver()
    
    # Load current progress
    prog = load_progress()
    
    try:
        for i, plan in enumerate(PLANS_TO_SCRAPE, 1):
            plan_id = plan['plan_id']
            total_done = len(prog['completed']) + len(prog['not_found']) + len(existing_json)
            overall_progress = total_done + i
            
            print(f"[{overall_progress}/{len(all_plans)}] {plan_id}...", flush=True)
            
            # Create JSON file first
            json_file = JSON_DIR / f"Florida-{plan_id}.json"
            if not json_file.exists():
                plan_data = create_plan_json(plan)
                with open(json_file, 'w') as f:
                    json.dump(plan_data, f, indent=2)
            
            # Scrape raw HTML
            result = scrape_raw_html(driver, plan_id)
            
            # Update progress based on result
            if result == 'success':
                prog['completed'].append(plan_id)
                print(f"  ✓ Saved HTML", flush=True)
            elif result == 'not_found':
                prog['not_found'].append(plan_id)
                print(f"  ⚠️  404 Not Found", flush=True)
            else:
                prog['errors'].append(plan_id)
                print(f"  ✗ Error", flush=True)
            
            # Save progress after each plan (resumability)
            save_progress(prog)
            
            # Rate limiting - be gentle on Medicare.gov
            time.sleep(1.5)
            
            # Progress update every 10 plans
            if i % 10 == 0:
                total_complete = len(prog['completed']) + len(prog['not_found']) + len(existing_json)
                print(f"\n  ━━━ Progress Checkpoint ━━━")
                print(f"  Completed: {total_complete}/{len(all_plans)} ({total_complete/len(all_plans)*100:.1f}%)")
                print(f"  ✓ Success: {len(prog['completed'])}")
                print(f"  ⚠️  Not Found: {len(prog['not_found'])}")
                print(f"  ✗ Errors: {len(prog['errors'])}")
                print(f"  Remaining: {len(all_plans) - total_complete}")
                print(f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        
        print(f"\n{'='*80}")
        print(f"RAW HTML SCRAPING COMPLETE")
        print(f"{'='*80}")
        print(f"✓ Success: {len(prog['completed'])}")
        print(f"⚠️  Not Found (404): {len(prog['not_found'])}")
        print(f"✗ Errors: {len(prog['errors'])}")
        print(f"Total scraped: {len(prog['completed']) + len(prog['not_found'])}/{len(all_plans)}")
        print()
        print("Next step: Run parse_fl_raw_content.py to extract structured data")
        print(f"{'='*80}\n")
        
    except KeyboardInterrupt:
        print(f"\n\n{'='*80}")
        print("SCRAPING INTERRUPTED BY USER")
        print(f"{'='*80}")
        total_complete = len(prog['completed']) + len(prog['not_found']) + len(existing_json)
        print(f"Progress saved: {total_complete}/{len(all_plans)} plans completed")
        print(f"  ✓ Success: {len(prog['completed'])}")
        print(f"  ⚠️  Not Found: {len(prog['not_found'])}")
        print(f"  ✗ Errors: {len(prog['errors'])}")
        print()
        print("To resume: Run this script again")
        print(f"{'='*80}\n")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
