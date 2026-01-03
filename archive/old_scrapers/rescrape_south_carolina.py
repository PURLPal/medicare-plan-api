#!/usr/bin/env python3
"""
Re-scrape all South Carolina Medicare plans.
Handles timeouts and errors better than the original scraper.
"""

import json
import time
import random
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime

# Configuration
STATE = "South_Carolina"
OUTPUT_DIR = Path("./scraped_json_all")
COUNTY_DIR = Path("./mock_api/SC/counties")
DELAY_MIN = 25  # Minimum delay between requests
DELAY_MAX = 35  # Maximum delay between requests
MAX_RETRIES = 3
TIMEOUT = 60  # Longer timeout for slow pages

def setup_driver():
    """Set up Chrome driver with options."""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(TIMEOUT)
    return driver

def get_plan_ids():
    """Get all South Carolina plan IDs from county files."""
    plan_ids = set()

    for county_file in COUNTY_DIR.glob("*.json"):
        try:
            with open(county_file) as f:
                plans = json.load(f)
                for plan in plans:
                    if isinstance(plan, dict):
                        plan_id = plan.get('plan_id', '').strip()
                        if plan_id:
                            plan_ids.add(plan_id)
        except Exception as e:
            print(f"Error reading {county_file}: {e}")

    return sorted(plan_ids)

def scrape_plan(driver, plan_id, retry_count=0):
    """Scrape a single plan with retry logic."""
    # Convert underscores to hyphens for URL (e.g., H5521_279_0 -> H5521-279-0)
    url_plan_id = plan_id.replace('_', '-')
    # Use 2026 year with year-prefixed plan ID format
    url = f"https://www.medicare.gov/plan-compare/#/plan-details/2026-{url_plan_id}?year=2026&lang=en"
    output_file = OUTPUT_DIR / f"{STATE}-{plan_id}.json"

    try:
        print(f"  Loading {url}...")
        driver.get(url)

        # Wait for page to load - try multiple strategies
        wait = WebDriverWait(driver, 30)

        # Strategy 1: Wait for plan name
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1, .plan-name, [class*='plan-title']")))
            print(f"    ✓ Page loaded successfully")
        except TimeoutException:
            # Strategy 2: Wait for any content
            try:
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                print(f"    ⚠ Page loaded but plan details may be missing")
            except TimeoutException:
                print(f"    ✗ Page load timeout")
                if retry_count < MAX_RETRIES:
                    print(f"    Retrying ({retry_count + 1}/{MAX_RETRIES})...")
                    time.sleep(10)
                    return scrape_plan(driver, plan_id, retry_count + 1)
                raise

        # Give page extra time to render
        time.sleep(3)

        # Get page content
        page_text = driver.find_element(By.TAG_NAME, "body").text

        # Check for error messages
        if "Unable to view Plan Details" in page_text:
            print(f"    ✗ Error: Unable to view plan details")
            if retry_count < MAX_RETRIES:
                print(f"    Retrying ({retry_count + 1}/{MAX_RETRIES})...")
                time.sleep(15)
                return scrape_plan(driver, plan_id, retry_count + 1)

        if "having trouble" in page_text.lower():
            print(f"    ✗ Error: Medicare.gov having trouble")
            if retry_count < MAX_RETRIES:
                print(f"    Retrying ({retry_count + 1}/{MAX_RETRIES})...")
                time.sleep(15)
                return scrape_plan(driver, plan_id, retry_count + 1)

        # Extract structured data
        result = {
            'plan_id': plan_id,
            'scraped_at': datetime.now().isoformat(),
            'url': url,
            'raw_content': page_text,
            'plan_info': extract_plan_info(driver)
        }

        # Save to file
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"    ✓ Saved to {output_file.name}")
        return True

    except TimeoutException:
        print(f"    ✗ Timeout loading page")
        if retry_count < MAX_RETRIES:
            print(f"    Retrying ({retry_count + 1}/{MAX_RETRIES})...")
            time.sleep(15)
            return scrape_plan(driver, plan_id, retry_count + 1)
        return False
    except Exception as e:
        print(f"    ✗ Error: {e}")
        if retry_count < MAX_RETRIES:
            print(f"    Retrying ({retry_count + 1}/{MAX_RETRIES})...")
            time.sleep(15)
            return scrape_plan(driver, plan_id, retry_count + 1)
        return False

def extract_plan_info(driver):
    """Extract basic plan info from the page."""
    try:
        # Try to find plan name
        selectors = [
            "h1",
            ".plan-name",
            "[class*='plan-title']",
            "[class*='planName']"
        ]

        for selector in selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                if element.text.strip():
                    return {
                        'name': element.text.strip(),
                        'found': True
                    }
            except NoSuchElementException:
                continue

        return {
            'name': '',
            'found': False,
            'note': 'Plan name not found'
        }
    except Exception as e:
        return {
            'error': str(e)
        }

def main():
    """Main scraping function."""
    print("=" * 60)
    print("South Carolina Medicare Plans - Re-scraping")
    print("=" * 60)
    print()

    # Get all plan IDs
    plan_ids = get_plan_ids()
    total = len(plan_ids)

    print(f"Found {total} South Carolina plans to scrape")
    print(f"Delay between requests: {DELAY_MIN}-{DELAY_MAX} seconds")
    print(f"Max retries per plan: {MAX_RETRIES}")
    print()

    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Set up driver
    print("Setting up Chrome driver...")
    driver = setup_driver()

    try:
        success_count = 0
        failed_count = 0

        for i, plan_id in enumerate(plan_ids, 1):
            print(f"\n[{i}/{total}] Scraping {plan_id}")

            if scrape_plan(driver, plan_id):
                success_count += 1
            else:
                failed_count += 1

            # Delay between requests (except for last one)
            if i < total:
                delay = random.uniform(DELAY_MIN, DELAY_MAX)
                print(f"  Waiting {delay:.1f}s before next request...")
                time.sleep(delay)

            # Progress update every 10 plans
            if i % 10 == 0:
                print()
                print(f"Progress: {i}/{total} ({i*100//total}%)")
                print(f"  Success: {success_count}")
                print(f"  Failed: {failed_count}")
                print()

        print()
        print("=" * 60)
        print("Scraping Complete!")
        print("=" * 60)
        print(f"Total plans: {total}")
        print(f"Successful: {success_count}")
        print(f"Failed: {failed_count}")
        print()

        if failed_count > 0:
            print("⚠ Some plans failed to scrape. You may want to retry them.")
        else:
            print("✓ All plans scraped successfully!")
            print()
            print("Next steps:")
            print("  1. Run: python3 extract_state_plans_v2.py SC")
            print("  2. Run: ./update_api.sh")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
