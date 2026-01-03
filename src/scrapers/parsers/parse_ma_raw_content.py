#!/usr/bin/env python3
"""
Parse raw HTML from Massachusetts plans to extract structured data.
Step 2 of the two-step scraping process.
"""
import json
from pathlib import Path
from bs4 import BeautifulSoup

RAW_DIR = Path('raw_ma_plans')
JSON_DIR = Path('scraped_json_all')

def extract_dt_dd_data(soup):
    """Extract data from dt/dd definition lists (new React format)."""
    data = {}
    
    # Find all dt/dd pairs
    dts = soup.find_all('dt')
    
    for dt in dts:
        # Get the label from dt
        label = dt.get_text(strip=True)
        
        # Get the corresponding dd (next sibling)
        dd = dt.find_next_sibling('dd')
        if dd:
            value = dd.get_text(strip=True)
            data[label] = value
    
    return data

def extract_table_data(soup):
    """Extract data from tables (new React format)."""
    data = {}
    
    # Find all tables
    tables = soup.find_all('table')
    
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['th', 'td'])
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                if label and value:
                    data[label] = value
    
    return data

def extract_benefits(soup):
    """Extract benefits from tables (new React format)."""
    benefits = {}
    
    # Find all tables with benefit data
    tables = soup.find_all('table')
    
    for table in tables:
        # Try to find a heading or caption for this table
        heading = table.find_previous(['h2', 'h3', 'h4'])
        section_title = heading.get_text(strip=True) if heading else "General Benefits"
        
        # Skip if we already have this section
        if section_title in benefits:
            section_title = f"{section_title} (additional)"
        
        section_data = {}
        rows = table.find_all('tr')
        
        for row in rows:
            cells = row.find_all(['th', 'td'])
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                
                # Skip header rows and empty data
                if label and value and label != value and 'What you pay' not in label:
                    section_data[label] = value
        
        if section_data:
            benefits[section_title] = section_data
    
    return benefits

def parse_plan(plan_id):
    """Parse a plan's HTML and update its JSON."""
    html_file = RAW_DIR / f"{plan_id}.html"
    json_file = JSON_DIR / f"Massachusetts-{plan_id}.json"
    
    if not html_file.exists():
        return None
    
    if not json_file.exists():
        return None
    
    try:
        # Read HTML
        with open(html_file, 'r', encoding='utf-8') as f:
            html = f.read()
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Check for valid plan (has title that's not generic Medicare.gov)
        title_tag = soup.find('title')
        if not title_tag or title_tag.get_text(strip=True) == 'Medicare.gov':
            return 'not_found'
        
        # Read existing JSON
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        # Extract plan name from title tag (more reliable in React SPA)
        title_tag = soup.find('title')
        if title_tag:
            title_text = title_tag.get_text(strip=True)
            if title_text != 'Medicare.gov':
                data['plan_info']['name'] = title_text
        
        # Extract all dt/dd data (includes premiums, deductibles, etc.)
        dt_dd_data = extract_dt_dd_data(soup)
        
        # Separate into categories
        premiums = {}
        deductibles = {}
        out_of_pocket = {}
        
        for key, value in dt_dd_data.items():
            key_lower = key.lower()
            if 'premium' in key_lower:
                premiums[key] = value
            elif 'deductible' in key_lower:
                deductibles[key] = value
            elif 'out-of-pocket' in key_lower or 'maximum' in key_lower:
                out_of_pocket[key] = value
            elif any(word in key_lower for word in ['doctor', 'specialist', 'hospital', 'copay']):
                # Put copays in a general section
                if 'Copays' not in data:
                    data['Copays'] = {}
                data['Copays'][key] = value
        
        data['premiums'] = premiums
        data['deductibles'] = deductibles
        data['out_of_pocket'] = out_of_pocket
        
        # Extract table data (additional details)
        table_data = extract_table_data(soup)
        for key, value in table_data.items():
            key_lower = key.lower()
            if 'premium' in key_lower and key not in premiums:
                premiums[key] = value
            elif 'deductible' in key_lower and key not in deductibles:
                deductibles[key] = value
        
        # Extract benefits
        data['benefits'] = extract_benefits(soup)
        
        # Save updated JSON
        with open(json_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Return stats
        prem = len(data['premiums'])
        ded = len(data['deductibles'])
        ben = len(data['benefits'])
        
        if prem > 0 or ben > 0:
            return 'success'
        else:
            return 'empty'
        
    except Exception as e:
        return 'error'

def main():
    print("="*80)
    print("PARSING MASSACHUSETTS RAW HTML FILES")
    print("="*80)
    
    # Get all HTML files
    html_files = list(RAW_DIR.glob('*.html'))
    print(f"HTML files to parse: {len(html_files)}\n")
    
    stats = {
        'success': 0,
        'empty': 0,
        'not_found': 0,
        'error': 0
    }
    
    for html_file in sorted(html_files):
        plan_id = html_file.stem
        result = parse_plan(plan_id)
        
        if result == 'success':
            stats['success'] += 1
            print(f"✓ {plan_id}")
        elif result == 'empty':
            stats['empty'] += 1
            print(f"⚠️  {plan_id} (no data extracted)")
        elif result == 'not_found':
            stats['not_found'] += 1
            print(f"✗ {plan_id} (404)")
        else:
            stats['error'] += 1
            print(f"✗ {plan_id} (error)")
    
    print(f"\n{'='*80}")
    print(f"PARSING COMPLETE")
    print(f"{'='*80}")
    print(f"Success: {stats['success']}")
    print(f"Empty: {stats['empty']}")
    print(f"Not found (404): {stats['not_found']}")
    print(f"Errors: {stats['error']}")
    print(f"Total: {len(html_files)}")
    print()
    
    # Check final data quality
    all_ma_files = list(JSON_DIR.glob('Massachusetts-*.json'))
    with_data = 0
    
    for f in all_ma_files:
        with open(f) as fp:
            data = json.load(fp)
        if len(data.get('premiums', {})) > 0 or len(data.get('benefits', {})) > 0:
            with_data += 1
    
    print(f"Total MA plan files: {len(all_ma_files)}")
    print(f"With complete data: {with_data}")
    print(f"Quality: {(with_data/len(all_ma_files)*100):.1f}%")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
