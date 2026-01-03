#!/usr/bin/env python3
"""
Parse raw_content from South Carolina JSON files to extract structured data.
This updates the existing files with premiums, deductibles, and benefits.
"""

import json
import re
from pathlib import Path

def extract_section_data(raw_content, section_name):
    """Extract key-value pairs from a section."""
    data = {}
    
    # Find the section
    section_pattern = rf'{section_name}\n(.*?)(?=\n[A-Z][A-Z\s]+\n|$)'
    section_match = re.search(section_pattern, raw_content, re.DOTALL)
    
    if not section_match:
        return data
    
    section_text = section_match.group(1)
    
    # Extract key-value pairs
    # Pattern: "Key name\n$value" or "Key name\nvalue"
    lines = section_text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines and "What's..." questions
        if not line or line.startswith("What's"):
            i += 1
            continue
        
        # Check if next line is a value
        if i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            
            # If it looks like a value (starts with $, or is a simple phrase)
            if next_line and (next_line.startswith('$') or 
                            next_line.startswith('In-network:') or
                            next_line.startswith('Not offered') or
                            'copay' in next_line.lower() or
                            'coinsurance' in next_line.lower()):
                data[line] = next_line
                i += 2
                continue
        
        i += 1
    
    return data


def parse_benefits(raw_content):
    """Extract benefits sections."""
    benefits = {}
    
    # Find all benefit section headers (like "DOCTOR SERVICES", "TESTS, LABS, & IMAGING", etc.)
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
        
        # Find section content
        pattern = rf'{section}\n(.*?)(?=\n[A-Z][A-Z\s]+\n|Benefits & Costs|Drug Coverage|Extra Benefits|$)'
        match = re.search(pattern, raw_content, re.DOTALL)
        
        if not match:
            continue
        
        section_text = match.group(1)
        lines = section_text.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty, "View..." lines, and parenthetical notes
            if not line or line.startswith('View ') or line.startswith('('):
                i += 1
                continue
            
            # Check if next line is a value
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                
                # If next line looks like a value
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


def parse_plan_file(filepath):
    """Parse a single plan file and update it with structured data."""
    with open(filepath) as f:
        data = json.load(f)
    
    raw_content = data.get('raw_content', '')
    
    if not raw_content:
        return False
    
    # Extract plan info
    plan_info = data.get('plan_info', {})
    
    # Extract organization and type from raw content
    org_match = re.search(r'Aetna Medicare|Humana|UnitedHealthcare|Wellcare|Wellpoint|Devoted Health|NHC Advantage|First Choice VIP|Clover Health', raw_content)
    if org_match:
        plan_info['organization'] = org_match.group(0)
    
    type_match = re.search(r'Plan type:\s*([^\n]+)', raw_content)
    if type_match:
        plan_info['type'] = type_match.group(1).strip()
    
    # Extract ID
    id_match = re.search(r'Plan ID:\s*([^\n]+)', raw_content)
    if id_match:
        plan_info['id'] = id_match.group(1).strip()
    
    data['plan_info'] = plan_info
    
    # Extract premiums
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
    
    # Extract deductibles
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
    
    # Extract maximum out-of-pocket
    moop_match = re.search(r'Maximum you pay for health services[^\n]*\n([^\n]+)', raw_content)
    if moop_match:
        data['maximum_out_of_pocket'] = {
            'Maximum you pay for health services': moop_match.group(1).strip()
        }
    
    # Extract contact info
    address_match = re.search(r'Plan address\n([^\n]+(?:\n[^\n]+)?)', raw_content)
    if address_match:
        data['contact_info'] = {
            'Plan address': address_match.group(1).strip()
        }
    
    # Extract benefits
    benefits = parse_benefits(raw_content)
    data['benefits'] = benefits
    
    # Write back to file
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    return True


def main():
    sc_files = list(Path('scraped_json_all').glob('South_Carolina-*.json'))
    
    print(f"=== Parsing {len(sc_files)} South Carolina Files ===\n")
    
    success = 0
    failed = 0
    
    for filepath in sc_files:
        try:
            if parse_plan_file(filepath):
                success += 1
                print(f"  ✓ {filepath.name}")
            else:
                failed += 1
                print(f"  ✗ {filepath.name} - No raw content")
        except Exception as e:
            failed += 1
            print(f"  ✗ {filepath.name} - Error: {e}")
    
    print(f"\n=== Results ===")
    print(f"Success: {success}")
    print(f"Failed: {failed}")
    
    # Verify one file
    if sc_files:
        print(f"\n=== Verifying Sample File ===")
        with open(sc_files[0]) as f:
            data = json.load(f)
        
        print(f"File: {sc_files[0].name}")
        print(f"  Plan name: {data.get('plan_info', {}).get('name', 'N/A')}")
        print(f"  Premiums: {len(data.get('premiums', {}))} fields")
        print(f"  Deductibles: {len(data.get('deductibles', {}))} fields")
        print(f"  Benefits: {len(data.get('benefits', {}))} sections")
        
        if data.get('premiums'):
            print(f"\n  Sample premium: {list(data['premiums'].items())[0]}")
        if data.get('benefits'):
            print(f"  Sample benefit section: {list(data['benefits'].keys())[0]}")


if __name__ == '__main__':
    main()
