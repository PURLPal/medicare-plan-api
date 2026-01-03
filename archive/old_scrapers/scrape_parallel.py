#!/usr/bin/env python3
"""
Parallel scraper - scrapes assigned states for a specific instance
Usage: python3 scrape_parallel.py <instance_id>
"""
import json
import time
import sys
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
OUTPUT_BASE = Path('output')
RATE_LIMIT_SECONDS = 3.0
WAIT_AFTER_LOAD = 8

(OUTPUT_BASE / 'html').mkdir(parents=True, exist_ok=True)
(OUTPUT_BASE / 'json').mkdir(parents=True, exist_ok=True)
(OUTPUT_BASE / 'summaries').mkdir(parents=True, exist_ok=True)

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

def scrape_and_parse_plan(driver, plan_info, html_dir, json_dir, state_name):
    """Scrape and parse a single plan."""
    plan_id = plan_info['ContractPlanSegmentID']
    
    result = {
        'plan_id': plan_id,
        'status': None,
        'html_size': 0,
        'parse_success': False,
        'data_complete': False,
        'issues': []
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
        
        if 'Unable to view Plan Details' in html_content:
            result['status'] = 'error_page'
            result['issues'].append("Got error page")
            return result
        
        if '<title>Medicare.gov</title>' in html_content or 'Page Not Found' in html_content:
            result['status'] = 'not_found'
            return result
        
        html_file = html_dir / f"{plan_id}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        result['status'] = 'scraped'
        
        parse_success, parsed_data = extract_plan_data(html_content)
        result['parse_success'] = parse_success
        
        if not parse_success:
            result['issues'].append("Parser failed")
            return result
        
        parsed_data['plan_id'] = plan_id
        parsed_data['state'] = state_name
        parsed_data['plan_info']['contract_id'] = plan_info.get('ContractPlanID', '')
        parsed_data['plan_info']['plan_type'] = plan_info.get('Plan Type', '')
        parsed_data['plan_info']['organization'] = plan_info.get('Organization Marketing Name', '')
        
        is_complete, issues = validate_data_completeness(parsed_data)
        result['data_complete'] = is_complete
        result['issues'] = issues
        
        json_file = json_dir / f"{plan_id}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(parsed_data, f, indent=2)
        
        result['status'] = 'success'
        return result
        
    except Exception as e:
        result['status'] = 'error'
        result['issues'].append(f"Error: {str(e)[:100]}")
        return result

def scrape_state(state_name, driver):
    """Scrape all plans for a single state."""
    print(f"\n{'='*80}")
    print(f"SCRAPING: {state_name.upper()}")
    print(f"{'='*80}")
    
    state_file = STATE_DATA_DIR / f"{state_name}.json"
    with open(state_file) as f:
        plans = json.load(f)
    
    print(f"Total plans: {len(plans)}")
    
    html_dir = OUTPUT_BASE / 'html' / state_name
    json_dir = OUTPUT_BASE / 'json' / state_name
    html_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)
    
    stats = {
        'success': 0,
        'not_found': 0,
        'errors': 0,
        'error_pages': 0,
        'parse_failures': 0,
        'incomplete_data': 0
    }
    
    results = []
    
    for i, plan in enumerate(plans, 1):
        plan_id = plan['ContractPlanSegmentID']
        print(f"[{i}/{len(plans)}] {plan_id}", end=' ', flush=True)
        
        result = scrape_and_parse_plan(driver, plan, html_dir, json_dir, state_name)
        results.append(result)
        
        if result['status'] == 'success':
            stats['success'] += 1
            if result['data_complete']:
                print(f"✅")
            else:
                stats['incomplete_data'] += 1
                print(f"⚠️")
        elif result['status'] == 'not_found':
            stats['not_found'] += 1
            print(f"⚠️  404")
        elif result['status'] == 'error_page':
            stats['error_pages'] += 1
            print(f"❌ Error page")
        else:
            stats['errors'] += 1
            print(f"❌")
        
        time.sleep(RATE_LIMIT_SECONDS)
    
    complete = stats['success'] - stats['incomplete_data']
    pct_complete = (complete / stats['success'] * 100) if stats['success'] > 0 else 0
    
    summary = {
        'state': state_name,
        'total_plans': len(plans),
        'stats': stats,
        'data_quality': {
            'complete': complete,
            'incomplete': stats['incomplete_data'],
            'completeness_pct': pct_complete
        },
        'results': results,
        'scraped_at': datetime.utcnow().isoformat() + 'Z'
    }
    
    summary_file = OUTPUT_BASE / 'summaries' / f"{state_name}_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n{'─'*80}")
    print(f"STATE SUMMARY: {state_name}")
    print(f"  ✅ Success: {stats['success']}/{len(plans)} ({stats['success']/len(plans)*100:.1f}%)")
    print(f"  📋 Data quality: {pct_complete:.1f}% complete")
    print(f"{'─'*80}")
    
    return summary

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scrape_parallel.py <instance_id>")
        sys.exit(1)
    
    instance_id = int(sys.argv[1])
    
    # Load config
    with open('parallel_config.json') as f:
        config = json.load(f)
    
    my_group = next(g for g in config['groups'] if g['instance_id'] == instance_id)
    my_states = my_group['states']
    
    print("="*80)
    print(f"MEDICARE PARALLEL SCRAPER - Instance {instance_id}")
    print("="*80)
    print(f"Assigned states: {len(my_states)}")
    print(f"Total plans: {my_group['plan_count']:,}")
    for state in my_states:
        print(f"  - {state}")
    
    est_time = my_group['plan_count'] * 13 / 3600
    print(f"\nEstimated time: {est_time:.1f} hours")
    print(f"Started: {datetime.utcnow().isoformat()}")
    print()
    
    driver = create_driver()
    all_summaries = []
    
    try:
        for i, state_name in enumerate(my_states, 1):
            print(f"\n{'█'*80}")
            print(f"STATE {i}/{len(my_states)}: {state_name}")
            print(f"{'█'*80}")
            
            summary = scrape_state(state_name, driver)
            all_summaries.append(summary)
            
    finally:
        driver.quit()
    
    # Final summary
    print(f"\n\n{'='*80}")
    print(f"INSTANCE {instance_id} COMPLETE")
    print(f"{'='*80}")
    
    total_success = sum(s['stats']['success'] for s in all_summaries)
    total_scraped = sum(s['total_plans'] for s in all_summaries)
    total_complete = sum(s['data_quality']['complete'] for s in all_summaries)
    
    print(f"\nStates scraped: {len(all_summaries)}/{len(my_states)}")
    print(f"Total plans: {total_scraped:,}")
    print(f"✅ Successfully scraped: {total_success}/{total_scraped} ({total_success/total_scraped*100:.1f}%)")
    print(f"📋 Complete data: {total_complete}/{total_success} ({total_complete/total_success*100:.1f}%)")
    
    instance_summary = {
        'instance_id': instance_id,
        'assigned_states': my_states,
        'total_plans': total_scraped,
        'total_success': total_success,
        'total_complete': total_complete,
        'state_summaries': all_summaries,
        'completed_at': datetime.utcnow().isoformat() + 'Z'
    }
    
    with open(f'instance_{instance_id}_summary.json', 'w') as f:
        json.dump(instance_summary, f, indent=2)
    
    print(f"\n✅ Instance {instance_id} complete!")
    print(f"Summary: instance_{instance_id}_summary.json")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
