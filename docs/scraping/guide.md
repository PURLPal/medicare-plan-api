# Medicare Plan Scraping Guide

## Overview

This guide documents the scraping process for Medicare plan data from medicare.gov.

## Critical: Deduplication

**ALWAYS deduplicate plan IDs before scraping.**

The CMS landscape file contains duplicate entries for plans that serve multiple counties. For example:
- Florida has **621 unique plans** but **4,253 entries** in the landscape file
- Some plans appear up to **67 times** (once per county they serve)

### Wrong Approach (DO NOT USE)

```python
def get_state_plans():
    plans = []
    with open(landscape_file) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('State Territory Name') == TARGET_STATE:
                plan_id = row.get('ContractPlanSegmentID', '')
                if plan_id:
                    plans.append({'plan_id': plan_id, ...})
    return plans  # Contains duplicates!
```

This will make **6-7x more HTTP requests** than necessary.

### Correct Approach

```python
def get_state_plans():
    seen = set()  # Track seen plan IDs
    plans = []
    
    with open(landscape_file) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('State Territory Name') == TARGET_STATE:
                plan_id = row.get('ContractPlanSegmentID', '')
                if plan_id and plan_id not in seen:  # Deduplicate
                    seen.add(plan_id)
                    plans.append({'plan_id': plan_id, ...})
    
    return plans  # Only unique plans
```

## Scraping Architecture

### Data Flow

```
CMS Landscape CSV → Unique Plan IDs → Scrape medicare.gov → JSON files
                         ↓
                    Deduplicate here!
```

### File Structure

```
scraped_json_all/           # All scraped plan JSON files
  H1234_001_0.json
  H5678_002_0.json
  ...

mock_api/{STATE}/           # State-specific data
  zip_to_plans.json         # ZIP code to plan mapping
  counties/                 # County data
```

### Scripts

| Script | Purpose | States |
|--------|---------|--------|
| `scrape_batch_N.py` | Batch scraping | Various small states |
| `scrape_florida.py` | Florida only | FL (621 plans) |
| `scrape_wa_or.py` | WA + OR | WA (136), OR (112) |
| `scrape_big_states.py` | Large states | TX, CA, PA, NY, OH, MI |

## Creating a New Scrape Script

### Template

```python
#!/usr/bin/env python3
"""
Scrape [STATE] Medicare plans.
[STATE]: X plans

Usage:
    nohup python3 scrape_[state].py > [state]_output.log 2>&1 &
"""

import csv
import json
import time
import random
from pathlib import Path
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth

TARGET_STATES = [
    ('State Name', 'ST'),
]

def get_state_plans():
    """Get all UNIQUE plans for target states."""
    landscape_file = Path('downloaded_data/CY2026_Landscape_202511/CY2026_Landscape_202511.csv')
    
    state_name_to_abbrev = {name: abbrev for name, abbrev in TARGET_STATES}
    
    # CRITICAL: Deduplicate by plan_id
    seen = set()
    plans = []
    
    with open(landscape_file, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            state_name = row.get('State Territory Name', '')
            if state_name in state_name_to_abbrev:
                plan_id = row.get('ContractPlanSegmentID', '')
                if plan_id and plan_id not in seen:
                    seen.add(plan_id)
                    plans.append({
                        'plan_id': plan_id,
                        'state': state_name_to_abbrev[state_name],
                        'state_name': state_name
                    })
    
    return plans

# ... rest of scraping logic
```

### Checklist for New Scripts

- [ ] Deduplicate plan IDs in `get_state_plans()`
- [ ] Check for already scraped files before starting
- [ ] Use stealth driver to avoid detection
- [ ] Add random delays between requests (1.5-3.0 seconds)
- [ ] Restart browser every 100 plans
- [ ] Log progress every 50 plans
- [ ] Handle errors gracefully

## Running Scrapers

### Start a scraper

```bash
nohup python3 scrape_florida.py > florida_output.log 2>&1 &
```

### Monitor progress

```bash
# Watch live output
tail -f florida_output.log

# Count completed plans
grep -c "✓" florida_output.log

# Check if running
pgrep -f "scrape_florida.py"
```

### Chain scrapers

Use watcher scripts to auto-start the next scraper:

```bash
# start_next_after_current.sh
while pgrep -f "current_scraper.py" > /dev/null; do
    sleep 60
done
nohup python3 next_scraper.py > next_output.log 2>&1 &
```

## Rate Limiting

- **Delay between requests**: 1.5-3.0 seconds (randomized)
- **Browser restart**: Every 100 plans
- **Estimated rate**: ~2-3 plans/minute
- **Time estimates**:
  - 100 plans ≈ 35-50 minutes
  - 500 plans ≈ 3-4 hours
  - 1000 plans ≈ 6-8 hours

## Troubleshooting

### "ModuleNotFoundError: No module named 'selenium_stealth'"

```bash
pip3 install selenium-stealth
```

### Scraper seems slow

Check if deduplication is working:
```python
plans = get_state_plans()
print(f"Unique plans: {len(plans)}")
print(f"Expected: {EXPECTED_COUNT}")  # Compare to CMS data
```

### Plans being re-scraped

The script should skip already scraped plans. **IMPORTANT**: Handle both file naming formats!

```python
# WRONG - misses files with state prefix
already_scraped = set(f.stem for f in Path('scraped_json_all').glob('*.json'))

# CORRECT - handles both 'PlanID.json' and 'State-PlanID.json' formats
already_scraped = set()
for f in output_dir.glob('*.json'):
    name = f.stem
    if '-' in name:
        # Format: State-PlanID (e.g., Iowa-H5216_413_0)
        parts = name.split('-', 1)
        if len(parts) == 2:
            already_scraped.add(parts[1])
    else:
        # Format: PlanID (e.g., H5216_413_0)
        already_scraped.add(name)

plans_to_scrape = [p for p in plans if p['plan_id'] not in already_scraped]
```

## Data Sources

- **Landscape file**: `downloaded_data/CY2026_Landscape_202511/CY2026_Landscape_202511.csv`
- **Plan details URL**: `https://www.medicare.gov/plan-compare/#/plan-details/{plan_id}?year=2025&lang=en`

## State Plan Counts (Unique)

| State | Plans | | State | Plans |
|-------|-------|-|-------|-------|
| Florida | 621 | | Texas | 435 |
| California | 414 | | Pennsylvania | 344 |
| New York | 228 | | Ohio | 222 |
| Michigan | 204 | | North Carolina | 187 |
| Georgia | 176 | | Illinois | 172 |
| Missouri | 167 | | Virginia | 152 |
| Tennessee | 144 | | Arizona | 143 |
| Indiana | 137 | | Washington | 136 |
| Wisconsin | 131 | | Kentucky | 124 |
| Louisiana | 121 | | Colorado | 117 |
| Nevada | 115 | | Massachusetts | 114 |
| Oregon | 112 | | Alabama | 110 |

Total unique plans nationwide: **~6,581**
