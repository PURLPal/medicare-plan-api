#!/usr/bin/env python3
import json
import random
import time
import os
from pathlib import Path
import requests
from fake_useragent import UserAgent

# Create directory for saving HTML responses
html_dir = Path('./scraped_html')
html_dir.mkdir(exist_ok=True)

# List of realistic Chrome user agents (fallback if fake_useragent doesn't work)
CHROME_USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
]

def get_random_headers():
    """Generate realistic browser headers with rotating user agent"""
    try:
        ua = UserAgent()
        user_agent = ua.chrome
    except:
        # Fallback to our static list
        user_agent = random.choice(CHROME_USER_AGENTS)

    headers = {
        'User-Agent': user_agent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
    return headers

def scrape_plan(plan_data, state_name):
    """Scrape a single plan and save the HTML"""
    url = plan_data['url']
    contract_plan_segment_id = plan_data['ContractPlanSegmentID']

    print(f"\nScraping: {contract_plan_segment_id}")
    print(f"  State: {state_name}")
    print(f"  Plan: {plan_data['Plan Name']}")
    print(f"  URL: {url}")

    # Get random headers
    headers = get_random_headers()
    print(f"  User-Agent: {headers['User-Agent'][:80]}...")

    try:
        # Add random delay between 2-5 seconds
        delay = random.uniform(2.0, 5.0)
        print(f"  Waiting {delay:.2f}s before request...")
        time.sleep(delay)

        # Make the request
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        # Save the HTML
        safe_filename = f"{state_name}_{contract_plan_segment_id}.html"
        output_path = html_dir / safe_filename

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(response.text)

        print(f"  ✓ Success! Saved to {output_path}")
        print(f"  Status: {response.status_code}, Size: {len(response.text)} bytes")

        return {
            'success': True,
            'status_code': response.status_code,
            'size': len(response.text),
            'file': str(output_path)
        }

    except requests.exceptions.RequestException as e:
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
    print("MEDICARE PLAN SCRAPER - TEST RUN")
    print("="*80)
    print(f"Selected {len(selected_states)} random states for testing")
    print()

    results = []

    for state_file in selected_states:
        state_name = state_file.stem  # filename without extension

        with open(state_file, 'r') as f:
            plans = json.load(f)

        print(f"\n{'='*80}")
        print(f"STATE: {state_name} ({len(plans)} total plans)")
        print(f"{'='*80}")

        # Randomly select 5 plans from this state
        num_to_sample = min(5, len(plans))
        selected_plans = random.sample(plans, num_to_sample)

        for i, plan in enumerate(selected_plans, 1):
            print(f"\n[{i}/{num_to_sample}]", end=" ")
            result = scrape_plan(plan, state_name)

            results.append({
                'state': state_name,
                'plan_id': plan['ContractPlanSegmentID'],
                'url': plan['url'],
                **result
            })

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
