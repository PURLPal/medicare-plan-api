#!/usr/bin/env python3
"""
Retry scraper for failed plans - slower rate with detailed logging
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

OUTPUT_BASE = Path('output')
RATE_LIMIT_SECONDS = 10.0  # Increased from 3s to 10s
WAIT_AFTER_LOAD = 8

(OUTPUT_BASE / 'html').mkdir(parents=True, exist_ok=True)
(OUTPUT_BASE / 'json').mkdir(parents=True, exist_ok=True)
(OUTPUT_BASE / 'summaries').mkdir(parents=True, exist_ok=True)

def log(msg, level="INFO"):
    """Detailed logging with timestamps"""
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [{level}] {msg}", flush=True)

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
    """Scrape and parse a single plan with detailed logging."""
    plan_id = plan_info['plan_id']
    
    result = {
        'plan_id': plan_id,
        'state': state_name,
        'status': None,
        'html_size': 0,
        'parse_success': False,
        'data_complete': False,
        'issues': [],
        'attempt_time': datetime.utcnow().isoformat()
    }
    
    plan_id_formatted = plan_id.replace('_', '-')
    url = f"https://www.medicare.gov/plan-compare/#/plan-details/2026-{plan_id_formatted}?year=2026&lang=en"
    
    log(f"Attempting {plan_id} ({state_name})")
    
    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(WAIT_AFTER_LOAD)
        
        html_content = driver.page_source
        result['html_size'] = len(html_content)
        
        # Check for error pages with detailed logging
        if 'Unable to view Plan Details' in html_content:
            result['status'] = 'error_page'
            result['issues'].append("Got 'Unable to view Plan Details' error page")
            log(f"  ❌ {plan_id}: ERROR PAGE (rate limited)", "WARN")
            return result
        
        if '<title>Medicare.gov</title>' in html_content or 'Page Not Found' in html_content:
            result['status'] = 'not_found'
            result['issues'].append("Page not found - plan may not exist")
            log(f"  ⚠️  {plan_id}: NOT FOUND (404)", "WARN")
            return result
        
        # Save HTML
        html_dir = OUTPUT_BASE / 'html' / state_name
        html_dir.mkdir(parents=True, exist_ok=True)
        html_file = html_dir / f"{plan_id}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        result['status'] = 'scraped'
        log(f"  📄 {plan_id}: HTML downloaded ({len(html_content):,} bytes)")
        
        # Try parsing
        parse_success, parsed_data = extract_plan_data(html_content)
        result['parse_success'] = parse_success
        
        if not parse_success:
            result['issues'].append("Parser returned False")
            log(f"  ⚠️  {plan_id}: Parser failed", "WARN")
            return result
        
        # Validate data completeness
        is_complete, issues = validate_data_completeness(parsed_data)
        result['data_complete'] = is_complete
        result['issues'] = issues
        
        # Add metadata
        parsed_data['plan_id'] = plan_id
        parsed_data['state'] = state_name
        
        # Save JSON
        json_dir = OUTPUT_BASE / 'json' / state_name
        json_dir.mkdir(parents=True, exist_ok=True)
        json_file = json_dir / f"{plan_id}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(parsed_data, f, indent=2)
        
        result['status'] = 'success'
        
        if is_complete:
            log(f"  ✅ {plan_id}: Complete data extracted")
        else:
            log(f"  ⚠️  {plan_id}: Partial data - {', '.join(issues[:2])}", "WARN")
        
        return result
        
    except Exception as e:
        result['status'] = 'error'
        result['issues'].append(f"Exception: {str(e)[:100]}")
        log(f"  ❌ {plan_id}: Exception - {str(e)[:80]}", "ERROR")
        return result

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scrape_retry.py <instance_id>")
        sys.exit(1)
    
    instance_id = int(sys.argv[1])
    
    # Load retry list for this instance
    with open(f'retry_plans_{instance_id}.json') as f:
        plans_to_retry = json.load(f)
    
    log(f"{'='*80}")
    log(f"RETRY SCRAPER - Instance {instance_id}")
    log(f"{'='*80}")
    log(f"Plans to retry: {len(plans_to_retry)}")
    log(f"Rate limit: {RATE_LIMIT_SECONDS}s between plans")
    log(f"Estimated time: {len(plans_to_retry) * (RATE_LIMIT_SECONDS + 10) / 3600:.1f} hours")
    log(f"Started: {datetime.utcnow().isoformat()}Z")
    log("")
    
    driver = create_driver()
    results = []
    stats = {
        'success': 0,
        'not_found': 0,
        'error_pages': 0,
        'errors': 0,
        'parse_failures': 0
    }
    
    try:
        for i, plan_info in enumerate(plans_to_retry, 1):
            log(f"[{i}/{len(plans_to_retry)}] Processing {plan_info['plan_id']}")
            
            result = scrape_and_parse_plan(driver, plan_info, plan_info['state'])
            results.append(result)
            
            # Update stats
            if result['status'] == 'success':
                stats['success'] += 1
            elif result['status'] == 'not_found':
                stats['not_found'] += 1
            elif result['status'] == 'error_page':
                stats['error_pages'] += 1
            else:
                stats['errors'] += 1
            
            if not result['parse_success'] and result['status'] == 'scraped':
                stats['parse_failures'] += 1
            
            # Progress logging every 10 plans
            if i % 10 == 0:
                success_rate = stats['success'] / i * 100
                log(f"Progress: {i}/{len(plans_to_retry)} | Success: {stats['success']} ({success_rate:.1f}%) | Errors: {stats['error_pages']}")
            
            time.sleep(RATE_LIMIT_SECONDS)
            
    finally:
        driver.quit()
    
    # Final summary
    log("")
    log(f"{'='*80}")
    log(f"RETRY COMPLETE - Instance {instance_id}")
    log(f"{'='*80}")
    log(f"Total attempted: {len(plans_to_retry)}")
    log(f"✅ Success: {stats['success']} ({stats['success']/len(plans_to_retry)*100:.1f}%)")
    log(f"⚠️  Not found: {stats['not_found']}")
    log(f"❌ Error pages: {stats['error_pages']}")
    log(f"❌ Errors: {stats['errors']}")
    log(f"❌ Parse failures: {stats['parse_failures']}")
    
    summary = {
        'instance_id': instance_id,
        'total_attempted': len(plans_to_retry),
        'stats': stats,
        'results': results,
        'completed_at': datetime.utcnow().isoformat() + 'Z'
    }
    
    with open(f'retry_instance_{instance_id}_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    log(f"Summary saved: retry_instance_{instance_id}_summary.json")
    log(f"{'='*80}")

if __name__ == "__main__":
    main()
