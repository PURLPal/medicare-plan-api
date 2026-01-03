#!/usr/bin/env python3
"""
Parse raw HTML files from raw_ar_plans/ into structured JSON.
Extracts premiums, deductibles, benefits from Arkansas Medicare plans.
"""

import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

RAW_DIR = Path('./raw_ar_plans')
JSON_DIR = Path('./scraped_json_all')

def extract_text_from_html(html_content):
    """Extract clean text from HTML using BeautifulSoup."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    for script in soup(["script", "style"]):
        script.decompose()
    
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    
    return text

def parse_benefits(raw_content):
    """Extract benefits sections."""
    benefits = {}
    
    benefit_sections = [
        'DOCTOR SERVICES',
        'TESTS, LABS, & IMAGING',
        'HOSPITAL SERVICES',
        'PREVENTIVE SERVICES',
        'VISION',
        'HEARING',
        'PREVENTIVE DENTAL',
        'COMPREHENSIVE DENTAL',
        'DENTAL',
        'EMERGENCY CARE',
        'MENTAL HEALTH',
        'SKILLED NURSING FACILITY',
        'DURABLE MEDICAL EQUIPMENT',
        'PROSTHETIC DEVICES',
        'DIABETES SUPPLIES',
        'TRANSPORTATION',
        'OVER-THE-COUNTER ITEMS',
        'MEALS',
        'FITNESS',
        'TELEHEALTH'
    ]
    
    for section in benefit_sections:
        section_data = {}
        
        pattern = rf'{section}\n(.*?)(?=\n[A-Z][A-Z\s]+\n|Benefits & Costs|Drug Coverage|Extra Benefits|$)'
        match = re.search(pattern, raw_content, re.DOTALL)
        
        if not match:
            continue
        
        section_text = match.group(1)
        lines = section_text.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if not line or line.startswith('View ') or line.startswith('('):
                i += 1
                continue
            
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                
                if next_line and not next_line.startswith('(') and (
                    next_line.startswith('In-network:') or
                    next_line.startswith('$') or
                    'copay' in next_line.lower() or
                    'coinsurance' in next_line.lower() or
                    next_line.startswith('Not covered') or
                    next_line.startswith('Tier ') or
                    'per day' in next_line.lower()
                ):
                    section_data[line] = next_line
                    i += 2
                    continue
            
            i += 1
        
        if section_data:
            benefits[section.title().replace(' ', ' ')] = section_data
    
    return benefits

def parse_plan_file(plan_id):
    """Parse raw HTML and update JSON file with structured data."""
    json_file = JSON_DIR / f"Arkansas-{plan_id}.json"
    html_file = RAW_DIR / f"{plan_id}.html"
    
    if not json_file.exists():
        return False, "JSON file not found"
    
    if not html_file.exists():
        return False, "HTML file not found"
    
    with open(html_file, encoding='utf-8') as f:
        html_content = f.read()
    
    with open(json_file) as f:
        data = json.load(f)
    
    raw_content = extract_text_from_html(html_content)
    data['raw_content'] = raw_content
    
    if not raw_content or len(raw_content) < 100:
        return False, "Empty or invalid content"
    
    plan_info = data.get('plan_info', {})
    
    org_match = re.search(r'Aetna Medicare|Humana|UnitedHealthcare|Wellcare|Blue Cross Blue Shield|BCBS|Devoted Health|Cigna|CareSource|Health Net|Kaiser Permanente', raw_content, re.IGNORECASE)
    if org_match:
        plan_info['organization'] = org_match.group(0)
    
    # Extract plan type - look for specific patterns, not "Plan type:" which doesn't exist
    # Common patterns: "Medicare Advantage", "Drug plan (Part D)", "HMO", "PPO", etc.
    type_match = re.search(r'(Medicare Advantage[^P]*?|Drug plan \(Part D\)|HMO|PPO|PDP|PFFS|MSA)', raw_content)
    if type_match:
        plan_type = type_match.group(1).strip()
        # Truncate to first line only
        plan_type = plan_type.split('\n')[0].strip()
        # Remove "Plan ID:" and anything after
        if 'Plan ID:' in plan_type:
            plan_type = plan_type.split('Plan ID:')[0].strip()
        plan_info['type'] = plan_type
    
    id_match = re.search(r'Plan ID:\s*([^\n]+)', raw_content)
    if id_match:
        plan_info['id'] = id_match.group(1).strip()
    
    data['plan_info'] = plan_info
    
    # Remove raw_content to save space - not needed in API
    data['raw_content'] = ''
    
    premiums = {}
    premium_patterns = {
        'Total monthly premium': r'Total monthly premium\s*\$([0-9.,]+)',
        'Health premium': r'Health premium\s*\$([0-9.,]+)',
        'Drug premium': r'Drug premium\s*\$([0-9.,]+)',
        'Standard Part B premium': r'Standard Part B premium.*?\n.*?\$([0-9.,]+)',
        'Part B premium reduction': r'Part B premium reduction.*?\n.*?(Not offered|.*)'
    }
    
    for key, pattern in premium_patterns.items():
        match = re.search(pattern, raw_content)
        if match:
            value = match.group(1).strip()
            premiums[key] = f'${value}' if not value.startswith('$') and value != 'Not offered' else value
    
    data['premiums'] = premiums
    
    deductibles = {}
    ded_patterns = {
        'Health deductible': r'Health deductible\s*\$([0-9.,]+)',
        'Drug deductible': r'Drug deductible\s*\$([0-9.,]+)'
    }
    
    for key, pattern in ded_patterns.items():
        match = re.search(pattern, raw_content)
        if match:
            deductibles[key] = f'${match.group(1)}'
    
    data['deductibles'] = deductibles
    
    moop_match = re.search(r'Maximum you pay for health services[^\n]*\n([^\n]+)', raw_content)
    if moop_match:
        data['maximum_out_of_pocket'] = {
            'Maximum you pay for health services': moop_match.group(1).strip()
        }
    
    address_match = re.search(r'Plan address\n([^\n]+(?:\n[^\n]+)?)', raw_content)
    if address_match:
        data['contact_info'] = {
            'Plan address': address_match.group(1).strip()
        }
    
    benefits = parse_benefits(raw_content)
    data['benefits'] = benefits
    
    with open(json_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    return True, "Success"

def main():
    print("="*80)
    print("ARKANSAS HTML PARSER")
    print("="*80)
    
    html_files = list(RAW_DIR.glob('*.html'))
    print(f"\nFound {len(html_files)} HTML files to parse")
    
    if not html_files:
        print("❌ No HTML files found in raw_ar_plans/")
        print("Run scrape_arkansas.py first!")
        return
    
    success = 0
    failed = 0
    errors = []
    
    for html_file in html_files:
        plan_id = html_file.stem
        try:
            result, msg = parse_plan_file(plan_id)
            if result:
                success += 1
                print(f"  ✓ {plan_id}")
            else:
                failed += 1
                errors.append((plan_id, msg))
                print(f"  ✗ {plan_id} - {msg}")
        except Exception as e:
            failed += 1
            errors.append((plan_id, str(e)))
            print(f"  ✗ {plan_id} - Error: {str(e)[:50]}")
    
    print(f"\n{'='*80}")
    print(f"PARSING COMPLETE")
    print(f"{'='*80}")
    print(f"✓ Success: {success}")
    print(f"✗ Failed: {failed}")
    
    if errors:
        print(f"\nFailed plans:")
        for plan_id, msg in errors[:5]:
            print(f"  - {plan_id}: {msg}")
    
    if success > 0:
        sample_file = JSON_DIR / f"Arkansas-{html_files[0].stem}.json"
        if sample_file.exists():
            with open(sample_file) as f:
                data = json.load(f)
            
            print(f"\n{'='*80}")
            print(f"SAMPLE VERIFICATION: {html_files[0].stem}")
            print(f"{'='*80}")
            print(f"Plan name: {data.get('plan_info', {}).get('name', 'N/A')}")
            print(f"Premiums extracted: {len(data.get('premiums', {}))} fields")
            print(f"Deductibles extracted: {len(data.get('deductibles', {}))} fields")
            print(f"Benefits sections: {len(data.get('benefits', {}))} sections")
            
            if data.get('premiums'):
                print(f"\nSample premium: {list(data['premiums'].items())[0]}")
            if data.get('benefits'):
                print(f"Sample benefit: {list(data['benefits'].keys())[0]}")
    
    print(f"\n{'='*80}")
    print("Next step: Run build_all_state_apis.py to create mock_api/AR/")
    print(f"{'='*80}\n")

if __name__ == '__main__':
    main()
