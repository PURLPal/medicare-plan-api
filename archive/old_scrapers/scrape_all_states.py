#!/usr/bin/env python3
"""
Master scraper for all 56 US states and territories
Scrapes all Medicare plans with progress tracking and resume capability
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

# Configuration
STATE_DATA_DIR = Path('state_data')
OUTPUT_BASE = Path('output')
PROGRESS_FILE = Path('scraping_progress.json')
RATE_LIMIT_SECONDS = 1.5

# Create output directories
(OUTPUT_BASE / 'html').mkdir(parents=True, exist_ok=True)
(OUTPUT_BASE / 'json').mkdir(parents=True, exist_ok=True)
(OUTPUT_BASE / 'summaries').mkdir(parents=True, exist_ok=True)

def load_progress():
    """Load scraping progress from file."""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {
        'completed': [],
        'failed': [],
        'current': None,
        'total_states': 0,
        'total_plans_scraped': 0,
        'total_plans_failed': 0,
        'started_at': datetime.utcnow().isoformat() + 'Z'
    }

def save_progress(progress):
    """Save scraping progress to file."""
    progress['updated_at'] = datetime.utcnow().isoformat() + 'Z'
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

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
        time.sleep(6)
        
        html_content = driver.page_source
        result['html_size'] = len(html_content)
        
        if '<title>Medicare.gov</title>' in html_content or 'Page Not Found' in html_content:
            result['status'] = 'not_found'
            return result
        
        # Save HTML
        html_file = html_dir / f"{plan_id}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        result['status'] = 'scraped'
        
        # Parse
        parse_success, parsed_data = extract_plan_data(html_content)
        result['parse_success'] = parse_success
        
        if not parse_success:
            result['issues'].append("Parser failed")
            return result
        
        # Add metadata
        parsed_data['plan_id'] = plan_id
        parsed_data['state'] = state_name
        parsed_data['plan_info']['contract_id'] = plan_info.get('ContractPlanID', '')
        parsed_data['plan_info']['plan_type'] = plan_info.get('Plan Type', '')
        parsed_data['plan_info']['organization'] = plan_info.get('Organization Marketing Name', '')
        
        # Validate
        is_complete, issues = validate_data_completeness(parsed_data)
        result['data_complete'] = is_complete
        result['issues'] = issues
        
        # Save JSON
        json_file = json_dir / f"{plan_id}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(parsed_data, f, indent=2)
        
        result['status'] = 'success'
        return result
        
    except Exception as e:
        result['status'] = 'error'
        result['issues'].append(f"Error: {str(e)[:100]}")
        return result

def scrape_state(state_name, driver, progress):
    """Scrape all plans for a single state."""
    print(f"\n{'='*80}")
    print(f"SCRAPING: {state_name.upper()}")
    print(f"{'='*80}")
    
    # Load state data
    state_file = STATE_DATA_DIR / f"{state_name}.json"
    if not state_file.exists():
        print(f"  ❌ State file not found: {state_file}")
        return False
    
    with open(state_file) as f:
        plans = json.load(f)
    
    print(f"Total plans: {len(plans)}")
    
    # Create state output directories
    html_dir = OUTPUT_BASE / 'html' / state_name
    json_dir = OUTPUT_BASE / 'json' / state_name
    html_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)
    
    # Track stats
    stats = {
        'success': 0,
        'not_found': 0,
        'errors': 0,
        'parse_failures': 0,
        'incomplete_data': 0
    }
    
    results = []
    
    # Scrape each plan
    for i, plan in enumerate(plans, 1):
        plan_id = plan['ContractPlanSegmentID']
        
        # Progress indicator every 25 plans
        if i % 25 == 0 or i == 1:
            print(f"\n[{i}/{len(plans)}] {plan_id}")
        
        result = scrape_and_parse_plan(driver, plan, html_dir, json_dir, state_name)
        results.append(result)
        
        # Update stats
        if result['status'] == 'success':
            stats['success'] += 1
            if not result['data_complete']:
                stats['incomplete_data'] += 1
        elif result['status'] == 'scraped' and not result['parse_success']:
            stats['parse_failures'] += 1
        elif result['status'] == 'not_found':
            stats['not_found'] += 1
        else:
            stats['errors'] += 1
        
        # Update global progress
        progress['total_plans_scraped'] += (1 if result['status'] == 'success' else 0)
        progress['total_plans_failed'] += (1 if result['status'] != 'success' else 0)
        
        time.sleep(RATE_LIMIT_SECONDS)
    
    # Save state summary
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
    
    # Print state summary
    print(f"\n{'─'*80}")
    print(f"STATE SUMMARY: {state_name}")
    print(f"{'─'*80}")
    print(f"  Total plans: {len(plans)}")
    print(f"  ✅ Success: {stats['success']} ({stats['success']/len(plans)*100:.1f}%)")
    print(f"  ⚠️  Not found: {stats['not_found']}")
    print(f"  ❌ Errors: {stats['errors']}")
    print(f"  📋 Data quality: {pct_complete:.1f}% complete")
    
    success_rate = stats['success'] / len(plans) if len(plans) > 0 else 0
    return success_rate >= 0.95  # 95% success threshold

def main():
    print("="*80)
    print("MEDICARE PLAN SCRAPER - ALL 56 STATES/TERRITORIES")
    print("="*80)
    
    # Load progress
    progress = load_progress()
    
    # Get all state files
    state_files = sorted(STATE_DATA_DIR.glob('*.json'))
    state_names = [f.stem for f in state_files]
    
    # Filter out already completed states
    remaining_states = [s for s in state_names if s not in progress['completed']]
    
    print(f"\nTotal states: {len(state_names)}")
    print(f"Completed: {len(progress['completed'])}")
    print(f"Remaining: {len(remaining_states)}")
    
    if not remaining_states:
        print("\n✅ All states already scraped!")
        return
    
    print(f"\nStarting scraping of {len(remaining_states)} states...")
    print(f"Rate limit: {RATE_LIMIT_SECONDS}s per plan")
    
    # Initialize driver
    driver = create_driver()
    
    try:
        for i, state_name in enumerate(remaining_states, 1):
            print(f"\n\n{'█'*80}")
            print(f"STATE {i}/{len(remaining_states)}: {state_name}")
            print(f"Overall Progress: {len(progress['completed'])}/{len(state_names)} states complete")
            print(f"{'█'*80}")
            
            progress['current'] = state_name
            progress['total_states'] = len(state_names)
            save_progress(progress)
            
            # Scrape state
            success = scrape_state(state_name, driver, progress)
            
            # Update progress
            if success:
                progress['completed'].append(state_name)
            else:
                progress['failed'].append(state_name)
            
            progress['current'] = None
            save_progress(progress)
            
            print(f"\n✅ {state_name} complete!")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Scraping interrupted by user")
        print(f"Progress saved. Re-run script to resume from {progress['current']}")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        print(f"Progress saved. Re-run script to resume")
    finally:
        driver.quit()
        save_progress(progress)
    
    # Final summary
    print(f"\n\n{'='*80}")
    print("FINAL SUMMARY")
    print(f"{'='*80}")
    print(f"States completed: {len(progress['completed'])}/{len(state_names)}")
    print(f"States failed: {len(progress['failed'])}")
    print(f"Total plans scraped: {progress['total_plans_scraped']}")
    print(f"Total plans failed: {progress['total_plans_failed']}")
    
    if progress['failed']:
        print(f"\n⚠️  Failed states:")
        for state in progress['failed']:
            print(f"  - {state}")
    
    print(f"\n✅ Scraping complete!")
    print(f"Results saved to: {OUTPUT_BASE}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
