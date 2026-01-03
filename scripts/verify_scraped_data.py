#!/usr/bin/env python3
"""
Verify downloaded scraped data quality and completeness
"""
import json
import random
from pathlib import Path
from collections import Counter

scraped_dir = Path('scraped_data')
json_dir = scraped_dir / 'json'

print("=== Scraped Data Verification ===\n")

# Count all JSON files
all_json_files = list(json_dir.rglob('*.json'))
print(f"Total JSON files: {len(all_json_files)}")
print(f"Expected: 6,402 plans")

if len(all_json_files) >= 6300:
    coverage = len(all_json_files) / 6402 * 100
    print(f"✅ Coverage: {coverage:.1f}%\n")
else:
    coverage = len(all_json_files) / 6402 * 100
    print(f"⚠️  Coverage: {coverage:.1f}%\n")

# Count by state
states = {}
for file in all_json_files:
    state = file.parent.name
    states[state] = states.get(state, 0) + 1

print(f"States with data: {len(states)}")
print(f"Expected: 56 states/territories\n")

# Sample 20 random files for quality check
print("=== Data Quality Check (20 random samples) ===\n")

sample_files = random.sample(all_json_files, min(20, len(all_json_files)))

required_fields = ['plan_id', 'plan_name', 'plan_type', 'state']
important_fields = ['monthly_premium', 'drug_deductible', 'medical_deductible']

valid_count = 0
field_stats = Counter()

for file in sample_files:
    try:
        with open(file) as f:
            data = json.load(f)
        
        # Check required fields
        has_required = all(field in data for field in required_fields)
        has_important = sum(1 for field in important_fields if field in data and data[field])
        
        # Count which fields are present
        for field in required_fields + important_fields:
            if field in data and data[field]:
                field_stats[field] += 1
        
        if has_required:
            valid_count += 1
            status = "✅"
        else:
            status = "⚠️"
        
        print(f"{status} {file.name}")
        print(f"   Plan: {data.get('plan_name', 'N/A')[:50]}")
        print(f"   ID: {data.get('plan_id', 'MISSING')}")
        print(f"   Premium: ${data.get('monthly_premium', 'N/A')}")
        print(f"   Type: {data.get('plan_type', 'N/A')}")
        print()
        
    except Exception as e:
        print(f"❌ {file.name}: ERROR - {str(e)}\n")

print(f"=== Summary ===")
print(f"Valid samples: {valid_count}/{len(sample_files)} ({valid_count/len(sample_files)*100:.0f}%)\n")

print("Field presence in samples:")
for field in required_fields + important_fields:
    count = field_stats[field]
    pct = count / len(sample_files) * 100
    print(f"  {field}: {count}/{len(sample_files)} ({pct:.0f}%)")

print("\n=== Top 5 States by Plan Count ===")
for state, count in sorted(states.items(), key=lambda x: x[1], reverse=True)[:5]:
    print(f"  {state}: {count} plans")

print(f"\n=== Storage ===")
import subprocess
result = subprocess.run(['du', '-sh', 'scraped_data/json'], capture_output=True, text=True)
print(f"JSON: {result.stdout.split()[0]}")
result = subprocess.run(['du', '-sh', 'scraped_data/html'], capture_output=True, text=True)
print(f"HTML: {result.stdout.split()[0]}")
result = subprocess.run(['du', '-sh', 'scraped_data'], capture_output=True, text=True)
print(f"Total: {result.stdout.split()[0]}")

print("\n✅ Verification complete!")
