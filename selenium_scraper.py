#!/usr/bin/env python3
"""
Robust Medicare plan scraper using Selenium
"""
import json
import random
import time
import os
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Create directory for saving HTML responses
html_dir = Path('./scraped_html_selenium')
html_dir.mkdir(exist_ok=True)

# List of realistic Chrome user agents
CHROME_USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
]

def create_driver(user_agent):
    """Create a Chrome driver with specific user agent"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run in background
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument(f'user-agent={user_agent}')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=chrome_options)
    return driver

def scrape_plan(driver, plan_data, state_name):
    """Scrape a single plan and save the HTML"""
    url = plan_data['url']
    contract_plan_segment_id = plan_data['ContractPlanSegmentID']

    print(f"\nScraping: {contract_plan_segment_id}")
    print(f"  State: {state_name}")
    print(f"  Plan: {plan_data['Plan Name']}")
    print(f"  URL: {url}")

    try:
        # Add random delay between 2-5 seconds
        delay = random.uniform(2.0, 5.0)
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

        # Give it extra time for all content to fully render
        time.sleep(5)

        # Get the rendered HTML
        html_content = driver.page_source

        # Save the HTML
        safe_filename = f"{state_name}_{contract_plan_segment_id}.html"
        output_path = html_dir / safe_filename

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"  ✓ Success! Saved to {output_path}")
        print(f"  Size: {len(html_content)} bytes")

        return {
            'success': True,
            'size': len(html_content),
            'file': str(output_path)
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
    # Load all state files
    state_data_dir = Path('./state_data')
    state_files = list(state_data_dir.glob('*.json'))

    # Randomly select 4 states
    selected_states = random.sample(state_files, 4)

    print("="*80)
    print("MEDICARE PLAN SCRAPER - SELENIUM TEST RUN")
    print("="*80)
    print(f"Selected {len(selected_states)} random states for testing")
    print()

    results = []
    user_agent_idx = 0

    for state_file in selected_states:
        state_name = state_file.stem

        with open(state_file, 'r') as f:
            plans = json.load(f)

        print(f"\n{'='*80}")
        print(f"STATE: {state_name} ({len(plans)} total plans)")
        print(f"{'='*80}")

        # Randomly select 5 plans from this state
        num_to_sample = min(5, len(plans))
        selected_plans = random.sample(plans, num_to_sample)

        # Create a new driver with rotated user agent
        user_agent = CHROME_USER_AGENTS[user_agent_idx % len(CHROME_USER_AGENTS)]
        user_agent_idx += 1

        print(f"\nCreating Chrome driver with user agent: {user_agent[:80]}...")
        driver = create_driver(user_agent)

        try:
            for i, plan in enumerate(selected_plans, 1):
                print(f"\n[{i}/{num_to_sample}]", end=" ")
                result = scrape_plan(driver, plan, state_name)

                results.append({
                    'state': state_name,
                    'plan_id': plan['ContractPlanSegmentID'],
                    'url': plan['url'],
                    **result
                })
        finally:
            driver.quit()
            print(f"\nClosed driver for {state_name}")

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    successful = sum(1 for r in results if r['success'])
    failed = sum(1 for r in results if not r['success'])

    print(f"Total requests: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")

    if failed > 0:
        print("\nFailed requests:")
        for r in results:
            if not r['success']:
                print(f"  - {r['state']}/{r['plan_id']}: {r['error']}")

    # Save results log
    with open('./selenium_scraping_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nDetailed results saved to: ./selenium_scraping_test_results.json")
    print(f"HTML files saved to: {html_dir}/")

if __name__ == '__main__':
    main()
