#!/usr/bin/env python3
"""
Check Massachusetts scraping progress and data quality.
Run this anytime to see current status.
"""
import json
from pathlib import Path

PROGRESS_FILE = Path('ma_scraping_progress.json')
RAW_DIR = Path('raw_ma_plans')
JSON_DIR = Path('scraped_json_all')

print("="*80)
print("MASSACHUSETTS SCRAPING PROGRESS")
print("="*80)
print()

# Load progress
if PROGRESS_FILE.exists():
    with open(PROGRESS_FILE) as f:
        prog = json.load(f)
    
    total = 114  # Total MA plans
    completed = len(prog['completed'])
    not_found = len(prog['not_found'])
    errors = len(prog['errors'])
    total_done = completed + not_found
    remaining = total - total_done
    
    print(f"Overall Progress: {total_done}/{total} ({total_done/total*100:.1f}%)")
    print()
    print(f"✓ Successfully scraped: {completed}")
    print(f"⚠️  Not found (404): {not_found}")
    print(f"✗ Errors (will retry): {errors}")
    print(f"📋 Remaining: {remaining}")
    print()
    
    # Show last 5 completed
    if prog['completed']:
        print("Last 5 successfully scraped:")
        for plan_id in prog['completed'][-5:]:
            print(f"  • {plan_id}")
        print()
    
    # Show errors if any
    if prog['errors']:
        print("Plans with errors (review these):")
        for plan_id in prog['errors']:
            print(f"  • {plan_id}")
        print()
    
else:
    print("No scraping started yet.")
    print(f"\nRun: python3 scrape_massachusetts.py")
    print()

# Check data quality of scraped plans
print("="*80)
print("DATA QUALITY CHECK")
print("="*80)
print()

ma_files = list(JSON_DIR.glob('Massachusetts-*.json'))
if ma_files:
    print(f"Total JSON files: {len(ma_files)}")
    
    with_premiums = 0
    with_benefits = 0
    complete = 0
    
    for f in ma_files:
        with open(f) as fp:
            data = json.load(fp)
        
        has_prem = len(data.get('premiums', {})) > 0
        has_ben = len(data.get('benefits', {})) > 0
        
        if has_prem:
            with_premiums += 1
        if has_ben:
            with_benefits += 1
        if has_prem and has_ben:
            complete += 1
    
    print(f"With premium data: {with_premiums}/{len(ma_files)} ({with_premiums/len(ma_files)*100:.1f}%)")
    print(f"With benefits data: {with_benefits}/{len(ma_files)} ({with_benefits/len(ma_files)*100:.1f}%)")
    print(f"Complete (both): {complete}/{len(ma_files)} ({complete/len(ma_files)*100:.1f}%)")
    print()
    
    # Sample a few to show details
    if complete > 0:
        print("Sample complete plans:")
        count = 0
        for f in sorted(ma_files):
            with open(f) as fp:
                data = json.load(fp)
            
            has_prem = len(data.get('premiums', {})) > 0
            has_ben = len(data.get('benefits', {})) > 0
            
            if has_prem and has_ben and count < 3:
                plan_id = data.get('plan_id', f.stem.replace('Massachusetts-', ''))
                name = data.get('plan_info', {}).get('name', 'Unknown')[:50]
                prem_count = len(data.get('premiums', {}))
                ben_count = len(data.get('benefits', {}))
                
                print(f"\n  {plan_id}")
                print(f"    Name: {name}")
                print(f"    Premiums: {prem_count} fields")
                print(f"    Benefits: {ben_count} sections")
                
                # Show a sample premium if available
                if data.get('premiums'):
                    sample_key = list(data['premiums'].keys())[0]
                    sample_val = data['premiums'][sample_key]
                    print(f"    Sample: {sample_key} = {sample_val}")
                
                count += 1
else:
    print("No Massachusetts plans scraped yet.")

print()
print("="*80)
print("NEXT STEPS")
print("="*80)
print()

if PROGRESS_FILE.exists():
    with open(PROGRESS_FILE) as f:
        prog = json.load(f)
    
    total_done = len(prog['completed']) + len(prog['not_found'])
    
    if total_done < 114:
        print(f"Continue scraping: python3 scrape_massachusetts.py")
        print(f"  ({114 - total_done} plans remaining)")
    else:
        print("✓ Scraping complete!")
        print()
        print("Parse HTML to extract data: python3 parse_ma_raw_content.py")
else:
    print("Start scraping: python3 scrape_massachusetts.py")

print()
print("="*80)
