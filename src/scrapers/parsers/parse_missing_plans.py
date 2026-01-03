#!/usr/bin/env python3
"""
Parse the 35 missing SC plan HTML files and update their JSON data.
"""
import json
from pathlib import Path
from bs4 import BeautifulSoup

RAW_DIR = Path('raw_sc_plans')
JSON_DIR = Path('scraped_json_all')

MISSING_PLANS = [
    "H3146_036_0", "H3146_038_0", "H3146_040_0", "H5216_466_0",
    "H5521_140_0", "H5521_245_0", "H5521_249_0", "H5521_251_0",
    "H5521_319_0", "H5521_500_0", "H5525_049_0", "H6345_002_0",
    "H7020_010_1", "H7020_010_2", "H7020_011_1", "H7020_011_2",
    "H7849_136_1", "H7849_136_2", "H8003_001_0", "H8003_002_0",
    "H8003_004_0", "H8003_005_0", "H8145_069_0", "H8176_004_1",
    "S4802_070_0", "S4802_144_0", "S5601_018_0", "S5617_218_0",
    "S5617_359_0", "S5884_134_0", "S5884_155_0", "S5884_188_0",
    "S5921_354_0", "S5921_391_0", "S5953_001_0"
]

def extract_table_data(soup, section_id):
    """Extract data from a table section."""
    section = soup.find('div', id=section_id)
    if not section:
        return {}
    
    data = {}
    rows = section.find_all('div', class_='m-c-table__body-row')
    
    for row in rows:
        cells = row.find_all('div', class_='m-c-table__body-cell')
        if len(cells) >= 2:
            # Get label
            label_elem = cells[0].find('span', class_='m-c-table__label')
            if not label_elem:
                label_elem = cells[0].find('button')
            
            # Get value
            value_elem = cells[1].find('span', class_='m-c-table__value')
            
            if label_elem and value_elem:
                label = label_elem.get_text(strip=True)
                value = value_elem.get_text(strip=True)
                data[label] = value
    
    return data

def extract_benefits(soup):
    """Extract benefits from the page."""
    benefits = {}
    
    # Find all benefit accordions/sections
    sections = soup.find_all('div', class_='m-c-accordion__panel')
    
    for section in sections:
        # Get section title from accordion button
        button = section.find_previous('button', class_='m-c-accordion__button')
        if not button:
            continue
        
        title = button.get_text(strip=True)
        
        # Extract data from this section
        section_data = {}
        rows = section.find_all('div', class_='m-c-table__body-row')
        
        for row in rows:
            cells = row.find_all('div', class_='m-c-table__body-cell')
            if len(cells) >= 2:
                label_elem = cells[0].find('span', class_='m-c-table__label')
                if not label_elem:
                    label_elem = cells[0].find('button')
                
                value_elem = cells[1].find('span', class_='m-c-table__value')
                
                if label_elem and value_elem:
                    label = label_elem.get_text(strip=True)
                    value = value_elem.get_text(strip=True)
                    section_data[label] = value
        
        if section_data:
            benefits[title] = section_data
    
    return benefits

def parse_plan(plan_id):
    """Parse a plan's HTML and update its JSON."""
    html_file = RAW_DIR / f"{plan_id}.html"
    json_file = JSON_DIR / f"South_Carolina-{plan_id}.json"
    
    if not html_file.exists():
        print(f"  ✗ {plan_id}: No HTML file")
        return False
    
    if not json_file.exists():
        print(f"  ✗ {plan_id}: No JSON file")
        return False
    
    try:
        # Read HTML
        with open(html_file, 'r', encoding='utf-8') as f:
            html = f.read()
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Read existing JSON
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        # Extract plan name and organization
        name_elem = soup.find('h1')
        if name_elem:
            data['plan_info']['name'] = name_elem.get_text(strip=True)
        
        org_elem = soup.find('p', string=lambda t: t and 'Organization' in t)
        if org_elem:
            org_text = org_elem.get_text(strip=True)
            data['plan_info']['organization'] = org_text.replace('Organization:', '').strip()
        
        # Extract sections
        data['premiums'] = extract_table_data(soup, 'premiums')
        data['deductibles'] = extract_table_data(soup, 'deductibles')
        data['out_of_pocket'] = extract_table_data(soup, 'out-of-pocket-costs')
        data['benefits'] = extract_benefits(soup)
        
        # Save updated JSON
        with open(json_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Report
        prem = len(data['premiums'])
        ded = len(data['deductibles'])
        ben = len(data['benefits'])
        
        print(f"  ✓ {plan_id}: P={prem} D={ded} B={ben}")
        
        return prem > 0 or ben > 0
        
    except Exception as e:
        print(f"  ✗ {plan_id}: {e}")
        return False

def main():
    print("="*80)
    print("PARSING MISSING SC PLAN HTML FILES")
    print("="*80)
    print(f"Plans to parse: {len(MISSING_PLANS)}\n")
    
    success = 0
    for plan_id in MISSING_PLANS:
        if parse_plan(plan_id):
            success += 1
    
    print(f"\n{'='*80}")
    print(f"PARSING COMPLETE: {success}/{len(MISSING_PLANS)} successful")
    print(f"{'='*80}\n")
    
    # Final count
    all_sc_files = list(JSON_DIR.glob("South_Carolina-*.json"))
    with_data = 0
    
    for f in all_sc_files:
        with open(f) as fp:
            data = json.load(fp)
        if len(data.get('premiums', {})) > 0 or len(data.get('benefits', {})) > 0:
            with_data += 1
    
    print(f"Total SC plans: {len(all_sc_files)}")
    print(f"With data: {with_data}")
    print(f"Quality: {(with_data/len(all_sc_files)*100):.1f}%")

if __name__ == "__main__":
    main()
