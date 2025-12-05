#!/usr/bin/env python3
"""Re-extract JSON from existing HTML files"""

import json
from pathlib import Path
from scrape_multithreaded import extract_plan_data

html_dir = Path('scraped_html_all')
json_dir = Path('scraped_json_all')

# Find all Arizona HTML files
arizona_files = sorted(html_dir.glob('Arizona-*.html'))

print(f"Found {len(arizona_files)} Arizona HTML files to reprocess\n")

for html_file in arizona_files:
    print(f"Processing {html_file.name}...")

    # Read HTML
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Extract data using current (fixed) extraction logic
    plan_data = extract_plan_data(html_content)

    # Get corresponding JSON filename
    json_filename = html_file.stem + '.json'
    json_path = json_dir / json_filename

    # Write JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(plan_data, f, indent=2)

    # Verify address has newline
    if 'Plan address' in plan_data.get('contact_info', {}):
        address = plan_data['contact_info']['Plan address']
        has_newline = '\n' in address
        status = "✓ HAS NEWLINE" if has_newline else "✗ NO NEWLINE"
        print(f"  {status}: {repr(address[:60])}...")
    else:
        print("  ⚠ No address found")

print(f"\nReprocessed {len(arizona_files)} files")
