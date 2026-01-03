#!/usr/bin/env python3
"""
Parse New Jersey raw HTML content into structured JSON.
Based on proven Arkansas parser with clean data extraction.
"""
import json
import re
from pathlib import Path

RAW_DIR = Path('raw_nj_plans')
SCRAPED_DIR = Path('scraped_json_all')

def extract_plan_data(raw_content):
    data = {}
    
    if not raw_content or len(raw_content) < 100:
        return False, "Empty or invalid content"
    
    plan_info = {}
    
    # Find ALL h1 tags and take the one that contains plan details (not "Menu")
    h1_matches = re.findall(r'<h1[^>]*>([^<]+)', raw_content)
    for h1_text in h1_matches:
        # Skip "Menu" and other non-plan names
        if h1_text.strip() not in ['Menu', 'Skip to main content'] and len(h1_text.strip()) > 10:
            plan_info['name'] = h1_text.strip()
            break
    
    org_match = re.search(r'Aetna Medicare|Humana|UnitedHealthcare|Wellcare|Blue Cross Blue Shield|BCBS|Devoted Health|Cigna|CareSource|Health Net|Kaiser Permanente|Clover|Emblem|Oxford|Highmark', raw_content, re.IGNORECASE)
    if org_match:
        plan_info['organization'] = org_match.group(0)
    
    type_match = re.search(r'(Medicare Advantage[^P]*?|Drug plan \(Part D\)|HMO|PPO|PDP|PFFS|MSA)', raw_content)
    if type_match:
        plan_type = type_match.group(1).strip()
        plan_type = plan_type.split('\n')[0].strip()
        if 'Plan ID:' in plan_type:
            plan_type = plan_type.split('Plan ID:')[0].strip()
        plan_info['type'] = plan_type
    
    id_match = re.search(r'Plan ID:\s*([A-Z0-9\-]+)', raw_content)
    if id_match:
        plan_info['id'] = id_match.group(1).strip()
    
    data['plan_info'] = plan_info
    data['raw_content'] = ''
    
    premiums = {}
    premium_patterns = {
        'Total monthly premium': r'Total monthly premium[^$]*?\$([0-9.,]+)',
        'Health premium': r'Health premium[^$]*?\$([0-9.,]+)',
        'Drug premium': r'Drug premium[^$]*?\$([0-9.,]+)',
        'Standard Part B premium': r'Standard Part B premium[^$]*?\$([0-9.,]+)',
        'Part B premium reduction': r'Part B premium reduction[^$]*?(Not offered|\$[0-9.,]+|−\$[0-9.,]+)'
    }
    
    for key, pattern in premium_patterns.items():
        match = re.search(pattern, raw_content)
        if match:
            value = match.group(1).strip()
            premiums[key] = f'${value}' if not value.startswith('$') and value != 'Not offered' and not value.startswith('−') else value
    
    data['premiums'] = premiums
    
    deductibles = {}
    ded_patterns = {
        'Health deductible': r'Health deductible[^$]*?\$([0-9.,]+)',
        'Drug deductible': r'Drug deductible[^$]*?\$([0-9.,]+)'
    }
    
    for key, pattern in ded_patterns.items():
        match = re.search(pattern, raw_content)
        if match:
            deductibles[key] = f'${match.group(1)}'
    
    data['deductibles'] = deductibles
    
    moop_match = re.search(r'Maximum you pay for health services[^$]*?\$([0-9.,]+)', raw_content)
    if moop_match:
        data['maximum_out_of_pocket'] = {
            'Maximum you pay for health services': moop_match.group(1).strip()
        }
    
    address_match = re.search(r'Plan address\n([^\n]+(?:\n[^\n]+)?)', raw_content)
    if address_match:
        data['contact_info'] = {
            'Plan address': address_match.group(1).strip()
        }
    
    data['benefits'] = {}
    data['drug_coverage'] = {}
    data['extra_benefits'] = {}
    
    return True, data

def parse_plan_file(plan_id):
    raw_file = RAW_DIR / f'{plan_id}.html'
    json_file = SCRAPED_DIR / f'New_Jersey-{plan_id}.json'
    
    if not raw_file.exists():
        return False, "Raw file not found"
    
    if not json_file.exists():
        return False, "JSON file not found"
    
    with open(raw_file, 'r', encoding='utf-8') as f:
        raw_content = f.read()
    
    with open(json_file) as f:
        existing_data = json.load(f)
    
    success, result = extract_plan_data(raw_content)
    
    if not success:
        return False, result
    
    existing_data.update(result)
    
    with open(json_file, 'w') as f:
        json.dump(existing_data, f, indent=2)
    
    return True, "Success"

def main():
    print("\n" + "="*80)
    print("NEW JERSEY HTML PARSER")
    print("="*80)
    
    raw_files = list(RAW_DIR.glob('*.html'))
    print(f"\nFound {len(raw_files)} HTML files to parse")
    
    success_count = 0
    failed_count = 0
    
    for raw_file in sorted(raw_files):
        plan_id = raw_file.stem
        
        success, message = parse_plan_file(plan_id)
        
        if success:
            print(f"  ✓ {plan_id}")
            success_count += 1
        else:
            print(f"  ✗ {plan_id}: {message}")
            failed_count += 1
    
    print("\n" + "="*80)
    print("PARSING COMPLETE")
    print("="*80)
    print(f"✓ Success: {success_count}")
    print(f"✗ Failed: {failed_count}")
    
    if success_count > 0:
        sample_file = SCRAPED_DIR / f'New_Jersey-{sorted(raw_files)[0].stem}.json'
        with open(sample_file) as f:
            sample_data = json.load(f)
        
        print("\n" + "="*80)
        print(f"SAMPLE VERIFICATION: {sorted(raw_files)[0].stem}")
        print("="*80)
        print(f"Plan name: {sample_data.get('plan_info', {}).get('name', 'N/A')}")
        print(f"Premiums extracted: {len(sample_data.get('premiums', {}))} fields")
        print(f"Deductibles extracted: {len(sample_data.get('deductibles', {}))} fields")
        print(f"Benefits sections: {len(sample_data.get('benefits', {}))} sections")
        
        if sample_data.get('premiums'):
            print(f"\nSample premium: {list(sample_data['premiums'].items())[0]}")
    
    print("\n" + "="*80)
    print("Next step: Run build_all_state_apis.py to create mock_api/NJ/")
    print("="*80 + "\n")

if __name__ == '__main__':
    main()
