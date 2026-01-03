#!/usr/bin/env python3
"""
Full Rhode Island Medicare scraper with integrated parsing
Scrapes all RI plans, parses HTML to JSON, validates data completeness
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
from parse_ri_html import extract_plan_data, validate_data_completeness

# Load Rhode Island plans
with open('state_data/Rhode_Island.json') as f:
    ALL_PLANS = json.load(f)

# Output directories
HTML_DIR = Path('ri_html_output')
JSON_DIR = Path('ri_json_output')
HTML_DIR.mkdir(exist_ok=True)
JSON_DIR.mkdir(exist_ok=True)

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

def scrape_and_parse_plan(driver, plan_info):
    """
    Scrape a plan and parse immediately.
    Returns result dict with status and data quality info.
    """
    plan_id = plan_info['ContractPlanSegmentID']
    plan_name = plan_info.get('Plan Name', 'Unknown')
    
    result = {
        'plan_id': plan_id,
        'plan_name': plan_name,
        'status': None,
        'html_size': 0,
        'parse_success': False,
        'data_complete': False,
        'issues': []
    }
    
    # Format URL
    plan_id_formatted = plan_id.replace('_', '-')
    url = f"https://www.medicare.gov/plan-compare/#/plan-details/2026-{plan_id_formatted}?year=2026&lang=en"
    
    try:
        # Scrape
        driver.get(url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(6)
        
        html_content = driver.page_source
        result['html_size'] = len(html_content)
        
        # Check if valid plan
        if '<title>Medicare.gov</title>' in html_content or 'Page Not Found' in html_content:
            result['status'] = 'not_found'
            return result
        
        # Save HTML
        html_file = HTML_DIR / f"{plan_id}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        result['status'] = 'scraped'
        
        # Parse immediately
        parse_success, parsed_data = extract_plan_data(html_content)
        result['parse_success'] = parse_success
        
        if not parse_success:
            result['issues'].append("Parser failed to extract data")
            return result
        
        # Add metadata
        parsed_data['plan_id'] = plan_id
        parsed_data['state'] = 'Rhode Island'
        parsed_data['plan_info']['contract_id'] = plan_info.get('ContractPlanID', '')
        parsed_data['plan_info']['plan_type'] = plan_info.get('Plan Type', '')
        parsed_data['plan_info']['organization'] = plan_info.get('Organization Marketing Name', '')
        
        # Validate data completeness
        is_complete, issues = validate_data_completeness(parsed_data)
        result['data_complete'] = is_complete
        result['issues'] = issues
        
        # Save JSON
        json_file = JSON_DIR / f"{plan_id}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(parsed_data, f, indent=2)
        
        result['status'] = 'success'
        
        return result
        
    except Exception as e:
        result['status'] = 'error'
        result['issues'].append(f"Error: {str(e)[:100]}")
        return result

def main():
    print("="*80)
    print("RHODE ISLAND FULL SCRAPE WITH PARSING & VALIDATION")
    print("="*80)
    print(f"Total plans to scrape: {len(ALL_PLANS)}")
    print(f"HTML output: {HTML_DIR}")
    print(f"JSON output: {JSON_DIR}\n")
    
    driver = create_driver()
    results = []
    
    stats = {
        'success': 0,
        'not_found': 0,
        'errors': 0,
        'parse_failures': 0,
        'incomplete_data': 0
    }
    
    try:
        for i, plan in enumerate(ALL_PLANS, 1):
            plan_id = plan['ContractPlanSegmentID']
            print(f"[{i}/{len(ALL_PLANS)}] {plan_id}")
            
            result = scrape_and_parse_plan(driver, plan)
            results.append(result)
            
            # Update stats
            if result['status'] == 'success':
                stats['success'] += 1
                if result['data_complete']:
                    print(f"  ✅ Complete - {result['html_size']:,} bytes, all fields populated")
                else:
                    stats['incomplete_data'] += 1
                    print(f"  ⚠️  Incomplete - {', '.join(result['issues'])}")
            elif result['status'] == 'scraped' and not result['parse_success']:
                stats['parse_failures'] += 1
                print(f"  ❌ Parse failed - {', '.join(result['issues'])}")
            elif result['status'] == 'not_found':
                stats['not_found'] += 1
                print(f"  ⚠️  Not found")
            else:
                stats['errors'] += 1
                print(f"  ❌ Error - {', '.join(result['issues'])}")
            
            time.sleep(1.5)  # Rate limiting
            
            # Progress checkpoint every 10 plans
            if i % 10 == 0:
                print(f"\n  ━━━ Checkpoint: {i}/{len(ALL_PLANS)} ━━━")
                print(f"  Success: {stats['success']}, Incomplete: {stats['incomplete_data']}")
                print(f"  Parse failures: {stats['parse_failures']}, Errors: {stats['errors']}\n")
        
    finally:
        driver.quit()
    
    # Final summary
    print(f"\n{'='*80}")
    print("FINAL SUMMARY")
    print(f"{'='*80}")
    print(f"\n📊 Scraping Results:")
    print(f"  Total plans: {len(ALL_PLANS)}")
    print(f"  ✅ Successfully scraped & parsed: {stats['success']}")
    print(f"  ⚠️  Not found: {stats['not_found']}")
    print(f"  ❌ Parse failures: {stats['parse_failures']}")
    print(f"  ❌ Errors: {stats['errors']}")
    
    print(f"\n📋 Data Quality:")
    complete = stats['success'] - stats['incomplete_data']
    if stats['success'] > 0:
        pct_complete = (complete / stats['success']) * 100
        print(f"  ✅ Complete data (all fields): {complete}/{stats['success']} ({pct_complete:.1f}%)")
        print(f"  ⚠️  Incomplete data: {stats['incomplete_data']}/{stats['success']}")
    
    # List plans with issues
    incomplete_plans = [r for r in results if r['status'] == 'success' and not r['data_complete']]
    if incomplete_plans:
        print(f"\n⚠️  Plans with incomplete data:")
        for r in incomplete_plans[:10]:  # Show first 10
            print(f"    {r['plan_id']}: {', '.join(r['issues'])}")
        if len(incomplete_plans) > 10:
            print(f"    ... and {len(incomplete_plans) - 10} more")
    
    # Save summary
    summary = {
        'total_plans': len(ALL_PLANS),
        'stats': stats,
        'results': results
    }
    with open('ri_scrape_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"✅ Scraping complete!")
    print(f"Summary saved to: ri_scrape_summary.json")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
