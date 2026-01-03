#!/usr/bin/env python3
"""
Sample-first scraper: Test 3 plans per state before full scraping
Validates parser works before downloading all HTML
"""
import json
import time
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from parse_ri_html import extract_plan_data, validate_data_completeness

STATE_DATA_DIR = Path('state_data')
OUTPUT_BASE = Path('sample_validation')
RATE_LIMIT_SECONDS = 3.0  # Increased from 1.5s
WAIT_AFTER_LOAD = 8  # Increased from 6s

OUTPUT_BASE.mkdir(exist_ok=True)

def create_driver():
    """Create Chrome driver for EC2."""
    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option('useAutomationExtension', False)
    opts.add_argument('--window-size=1920,1080')
    opts.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=opts)
    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Linux x86_64",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )
    return driver

def scrape_and_parse_plan(driver, plan_info, state_name):
    """Scrape and parse a single plan."""
    plan_id = plan_info['ContractPlanSegmentID']
    
    result = {
        'plan_id': plan_id,
        'plan_type': 'MA' if plan_id[0] == 'H' else 'PDP',
        'status': None,
        'html_size': 0,
        'parse_success': False,
        'data_complete': False,
        'issues': [],
        'extracted_fields': {}
    }
    
    plan_id_formatted = plan_id.replace('_', '-')
    url = f"https://www.medicare.gov/plan-compare/#/plan-details/2026-{plan_id_formatted}?year=2026&lang=en"
    
    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(WAIT_AFTER_LOAD)
        
        html_content = driver.page_source
        result['html_size'] = len(html_content)
        
        # Check for error pages
        if 'Unable to view Plan Details' in html_content:
            result['status'] = 'error_page'
            result['issues'].append("Got 'Unable to view Plan Details' error page")
            return result
        
        if '<title>Medicare.gov</title>' in html_content or 'Page Not Found' in html_content:
            result['status'] = 'not_found'
            result['issues'].append("Page not found")
            return result
        
        result['status'] = 'scraped'
        
        # Try parsing
        parse_success, parsed_data = extract_plan_data(html_content)
        result['parse_success'] = parse_success
        
        if not parse_success:
            result['issues'].append("Parser returned False")
        
        # Record what was extracted
        result['extracted_fields'] = {
            'plan_name': parsed_data['plan_info'].get('name', ''),
            'premium_count': len(parsed_data['premiums']),
            'deductible_count': len(parsed_data['deductibles']),
            'benefit_count': len(parsed_data['benefits']),
            'drug_coverage_count': len(parsed_data['drug_coverage'])
        }
        
        is_complete, issues = validate_data_completeness(parsed_data)
        result['data_complete'] = is_complete
        if issues:
            result['issues'].extend(issues)
        
        if parse_success:
            result['status'] = 'success'
        
        return result
        
    except Exception as e:
        result['status'] = 'error'
        result['issues'].append(f"Exception: {str(e)[:100]}")
        return result

def test_state_sample(state_name, driver, num_samples=3):
    """Test a few plans from a state to validate parser."""
    print(f"\n{'='*80}")
    print(f"TESTING: {state_name.upper()}")
    print(f"{'='*80}")
    
    state_file = STATE_DATA_DIR / f"{state_name}.json"
    with open(state_file) as f:
        plans = json.load(f)
    
    # Sample: 1 PDP and 2 MA plans (or whatever's available)
    pdp_plans = [p for p in plans if p['ContractPlanSegmentID'][0] == 'S']
    ma_plans = [p for p in plans if p['ContractPlanSegmentID'][0] == 'H']
    
    sample_plans = []
    if pdp_plans:
        sample_plans.append(pdp_plans[0])
    if ma_plans:
        sample_plans.extend(ma_plans[:2])
    
    # If we don't have 3 yet, fill with whatever
    if len(sample_plans) < num_samples:
        sample_plans.extend([p for p in plans if p not in sample_plans][:num_samples - len(sample_plans)])
    
    sample_plans = sample_plans[:num_samples]
    
    print(f"Total plans in state: {len(plans)}")
    print(f"Testing {len(sample_plans)} sample plans:")
    for p in sample_plans:
        plan_id = p['ContractPlanSegmentID']
        plan_type = 'MA' if plan_id[0] == 'H' else 'PDP'
        print(f"  - {plan_id} ({plan_type})")
    print()
    
    results = []
    for i, plan in enumerate(sample_plans, 1):
        plan_id = plan['ContractPlanSegmentID']
        plan_type = 'MA' if plan_id[0] == 'H' else 'PDP'
        print(f"[{i}/{len(sample_plans)}] {plan_id} ({plan_type})...", end=' ')
        
        result = scrape_and_parse_plan(driver, plan, state_name)
        results.append(result)
        
        if result['status'] == 'success':
            print(f"✅ Success")
        elif result['status'] == 'error_page':
            print(f"⚠️  ERROR PAGE: {result['issues'][0]}")
        else:
            print(f"❌ {result['status']}: {', '.join(result['issues'][:2])}")
        
        time.sleep(RATE_LIMIT_SECONDS)
    
    # Summary
    success_count = sum(1 for r in results if r['status'] == 'success')
    error_page_count = sum(1 for r in results if r['status'] == 'error_page')
    parse_fail_count = sum(1 for r in results if r['status'] == 'scraped' and not r['parse_success'])
    
    summary = {
        'state': state_name,
        'total_plans': len(plans),
        'samples_tested': len(sample_plans),
        'success': success_count,
        'error_pages': error_page_count,
        'parse_failures': parse_fail_count,
        'results': results,
        'parser_ready': success_count == len(sample_plans)
    }
    
    print(f"\n{'─'*80}")
    print(f"SAMPLE TEST: {state_name}")
    print(f"  ✅ Success: {success_count}/{len(sample_plans)}")
    print(f"  ⚠️  Error pages: {error_page_count}/{len(sample_plans)}")
    print(f"  ❌ Parse failures: {parse_fail_count}/{len(sample_plans)}")
    print(f"  Parser ready: {'YES ✅' if summary['parser_ready'] else 'NO ❌'}")
    print(f"{'─'*80}")
    
    return summary

def main():
    print("="*80)
    print("SAMPLE-FIRST VALIDATION - Test 3 plans per state")
    print("="*80)
    
    # Get all states
    state_files = sorted(STATE_DATA_DIR.glob('*.json'))
    all_states = [f.stem for f in state_files]
    
    print(f"\nFound {len(all_states)} states")
    print("Testing ALL states with 3 sample plans each...\n")
    
    test_states = all_states
    
    driver = create_driver()
    all_summaries = []
    
    try:
        for i, state_name in enumerate(test_states, 1):
            print(f"\n{'█'*80}")
            print(f"STATE {i}/{len(test_states)}: {state_name}")
            print(f"{'█'*80}")
            
            summary = test_state_sample(state_name, driver, num_samples=3)
            all_summaries.append(summary)
            
    finally:
        driver.quit()
    
    # Final summary
    print(f"\n\n{'='*80}")
    print("VALIDATION SUMMARY")
    print(f"{'='*80}")
    
    ready_count = sum(1 for s in all_summaries if s['parser_ready'])
    error_page_states = [s for s in all_summaries if s['error_pages'] > 0]
    parse_fail_states = [s for s in all_summaries if s['parse_failures'] > 0]
    
    print(f"\nStates tested: {len(all_summaries)}")
    print(f"Parser ready: {ready_count}/{len(all_summaries)}")
    print(f"\nStates with error pages: {len(error_page_states)}")
    for s in error_page_states:
        print(f"  - {s['state']}: {s['error_pages']}/{s['samples_tested']} samples")
    
    print(f"\nStates with parse failures: {len(parse_fail_states)}")
    for s in parse_fail_states:
        print(f"  - {s['state']}: {s['parse_failures']}/{s['samples_tested']} samples")
        # Show plan types that failed
        for r in s['results']:
            if not r['parse_success'] and r['status'] == 'scraped':
                print(f"    • {r['plan_id']} ({r['plan_type']}): {', '.join(r['issues'][:2])}")
    
    # Save detailed results
    output_file = OUTPUT_BASE / 'sample_validation_results.json'
    with open(output_file, 'w') as f:
        json.dump(all_summaries, f, indent=2)
    
    print(f"\n✅ Validation results saved: {output_file}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
