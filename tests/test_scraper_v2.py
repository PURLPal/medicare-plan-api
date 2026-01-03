#!/usr/bin/env python3
import json
import random
import time
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

# Create directory for saving HTML responses
html_dir = Path('./scraped_html')
html_dir.mkdir(exist_ok=True)

# List of realistic Chrome user agents
CHROME_USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
]

def scrape_plan(page, plan_data, state_name):
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
        page.goto(url, wait_until='networkidle', timeout=60000)

        # Wait for content to load - look for the plan name heading
        print(f"  Waiting for content to render...")
        page.wait_for_selector('h1', timeout=30000)

        # Give it a bit more time for all content to load
        time.sleep(2)

        # Get the rendered HTML
        html_content = page.content()

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
    print("MEDICARE PLAN SCRAPER - TEST RUN (with Playwright)")
    print("="*80)
    print(f"Selected {len(selected_states)} random states for testing")
    print()

    results = []

    with sync_playwright() as p:
        # Launch browser in headless mode
        print("Launching headless Chrome browser...")
        browser = p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )

        # Rotate user agents
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

            for i, plan in enumerate(selected_plans, 1):
                # Rotate user agent
                user_agent = CHROME_USER_AGENTS[user_agent_idx % len(CHROME_USER_AGENTS)]
                user_agent_idx += 1

                # Create a new context with the user agent
                context = browser.new_context(
                    user_agent=user_agent,
                    viewport={'width': 1920, 'height': 1080}
                )
                page = context.new_page()

                print(f"\n[{i}/{num_to_sample}]", end=" ")
                print(f"User-Agent: {user_agent[:80]}...")

                result = scrape_plan(page, plan, state_name)

                results.append({
                    'state': state_name,
                    'plan_id': plan['ContractPlanSegmentID'],
                    'url': plan['url'],
                    **result
                })

                # Close the context
                context.close()

        browser.close()

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
    with open('./scraping_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nDetailed results saved to: ./scraping_test_results.json")
    print(f"HTML files saved to: {html_dir}/")

if __name__ == '__main__':
    main()
