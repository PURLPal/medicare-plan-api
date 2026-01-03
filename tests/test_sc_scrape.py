#!/usr/bin/env python3
"""
Test scraping 3 South Carolina plans to verify it works before doing all 106.
"""

import json
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime

# Test with just 3 plans
TEST_PLANS = ["H2001_032_0", "H3146_014_0", "H5521_319_0"]
OUTPUT_DIR = Path("./test_sc_scrape_output")

def setup_driver():
    """Set up Chrome driver."""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(60)
    return driver

def scrape_plan(driver, plan_id):
    """Scrape a single plan."""
    # Convert underscores to hyphens for URL (e.g., H5521_279_0 -> H5521-279-0)
    url_plan_id = plan_id.replace('_', '-')
    # Use 2026 year with year-prefixed plan ID format
    url = f"https://www.medicare.gov/plan-compare/#/plan-details/2026-{url_plan_id}?year=2026&lang=en"

    print(f"\nScraping {plan_id}...")
    print(f"  URL: {url}")

    try:
        driver.get(url)

        # Wait for body to load
        wait = WebDriverWait(driver, 30)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        # Extra wait for dynamic content
        time.sleep(5)

        # Get page text
        page_text = driver.find_element(By.TAG_NAME, "body").text

        # Check for errors
        if "Unable to view Plan Details" in page_text:
            print(f"  ✗ ERROR: Unable to view plan details")
            return False

        if "having trouble" in page_text.lower():
            print(f"  ✗ ERROR: Medicare.gov having trouble")
            return False

        # Try to find plan name
        plan_name = None
        selectors = ["h1", ".plan-name", "[class*='plan']"]

        for selector in selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                text = element.text.strip()
                if text and len(text) > 5:
                    plan_name = text
                    break
            except:
                continue

        result = {
            'plan_id': plan_id,
            'scraped_at': datetime.now().isoformat(),
            'url': url,
            'plan_name': plan_name,
            'page_length': len(page_text),
            'has_error': False,
            'preview': page_text[:500]
        }

        # Save result
        output_file = OUTPUT_DIR / f"{plan_id}.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"  ✓ SUCCESS")
        print(f"  Plan name: {plan_name}")
        print(f"  Page length: {len(page_text)} chars")
        print(f"  Saved to: {output_file.name}")

        return True

    except TimeoutException:
        print(f"  ✗ TIMEOUT")
        return False
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        return False

def main():
    print("=" * 60)
    print("South Carolina - Test Scrape (3 plans)")
    print("=" * 60)

    OUTPUT_DIR.mkdir(exist_ok=True)

    print(f"\nTesting with {len(TEST_PLANS)} plans:")
    for plan_id in TEST_PLANS:
        print(f"  - {plan_id}")

    driver = setup_driver()

    try:
        success = 0
        failed = 0

        for plan_id in TEST_PLANS:
            if scrape_plan(driver, plan_id):
                success += 1
            else:
                failed += 1

            # Wait between requests
            if plan_id != TEST_PLANS[-1]:
                print("\n  Waiting 30s before next plan...")
                time.sleep(30)

        print("\n" + "=" * 60)
        print("Test Complete!")
        print("=" * 60)
        print(f"Success: {success}/{len(TEST_PLANS)}")
        print(f"Failed: {failed}/{len(TEST_PLANS)}")

        if success == len(TEST_PLANS):
            print("\n✓ All test plans scraped successfully!")
            print("\nYou can now run: python3 rescrape_south_carolina.py")
        elif success > 0:
            print(f"\n⚠ Partial success ({success}/{len(TEST_PLANS)})")
            print("Check the output files to see what worked")
        else:
            print("\n✗ All test plans failed!")
            print("There may be an issue with the scraper or Medicare.gov")

        print(f"\nTest results saved to: {OUTPUT_DIR}/")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
