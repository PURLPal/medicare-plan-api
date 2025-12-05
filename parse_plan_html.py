#!/usr/bin/env python3
"""
Parse scraped Medicare plan HTML and extract all data into JSON
"""
from bs4 import BeautifulSoup
import json
import re
from pathlib import Path

def extract_plan_data(html_file):
    """Extract all plan data from an HTML file"""

    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, 'html.parser')

    # Initialize data structure
    plan_data = {
        'source_file': str(html_file),
        'plan_info': {},
        'premiums': {},
        'deductibles': {},
        'maximum_out_of_pocket': {},
        'contact_info': {},
        'benefits': {},
        'drug_coverage': {},
        'extra_benefits': {}
    }

    # Extract plan name and ID
    plan_header_section = soup.find('div', class_='PlanDetailsPagePlanInfo')
    if plan_header_section:
        plan_name_h1 = plan_header_section.find('h1')
        if plan_name_h1:
            plan_data['plan_info']['name'] = plan_name_h1.get_text(strip=True)

        plan_name_h2 = plan_header_section.find('h2')
        if plan_name_h2:
            plan_data['plan_info']['organization'] = plan_name_h2.get_text(strip=True)

        # Extract plan type and ID from list items
        list_items = plan_header_section.find_all('li')
        for li in list_items:
            text = li.get_text()
            if 'Plan type:' in text:
                plan_data['plan_info']['type'] = text.replace('Plan type:', '').strip()
            elif 'Plan ID:' in text:
                plan_data['plan_info']['id'] = text.replace('Plan ID:', '').strip()

    # Extract all tables
    tables = soup.find_all('table', class_='mct-c-table')

    for table in tables:
        caption = table.find('caption')
        if not caption:
            continue

        table_title = caption.get_text(strip=True)

        # Extract rows
        rows = table.find_all('tr')
        table_data = {}

        for row in rows:
            header = row.find('th')
            cell = row.find('td')

            if header and cell:
                # Clean up header text (remove help drawer text)
                header_text = header.get_text(strip=True)
                # Remove "What's..." help text
                header_text = re.sub(r"What's.*?\?", "", header_text).strip()

                cell_text = cell.get_text(strip=True)

                table_data[header_text] = cell_text

        # Categorize the table data
        title_lower = table_title.lower()

        if 'premium' in title_lower:
            plan_data['premiums'].update(table_data)
        elif 'deductible' in title_lower:
            plan_data['deductibles'].update(table_data)
        elif 'maximum you pay' in title_lower or 'moop' in title_lower:
            plan_data['maximum_out_of_pocket'].update(table_data)
        elif 'contact' in title_lower or 'address' in title_lower:
            plan_data['contact_info'].update(table_data)
        elif 'drug' in title_lower or 'pharmacy' in title_lower or 'tier' in title_lower or 'part b drug' in title_lower:
            if 'drug_tables' not in plan_data['drug_coverage']:
                plan_data['drug_coverage']['drug_tables'] = {}
            plan_data['drug_coverage']['drug_tables'][table_title] = table_data
        elif any(keyword in title_lower for keyword in ['hearing', 'dental', 'vision', 'fitness', 'transportation']):
            plan_data['extra_benefits'][table_title] = table_data
        else:
            # General benefits
            plan_data['benefits'][table_title] = table_data

    return plan_data


def main():
    # Test with a few files
    html_dir = Path('./scraped_html_selenium')
    html_files = list(html_dir.glob('*.html'))[:3]  # Test with first 3

    print("="*80)
    print("PARSING MEDICARE PLAN HTML FILES")
    print("="*80)

    all_parsed_data = []

    for html_file in html_files:
        print(f"\nParsing: {html_file.name}")

        plan_data = extract_plan_data(html_file)

        # Save individual JSON
        output_file = html_file.with_suffix('.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(plan_data, f, indent=2, ensure_ascii=False)

        print(f"  ✓ Saved to: {output_file}")
        print(f"  Plan: {plan_data['plan_info'].get('name', 'Unknown')}")
        print(f"  Premiums: {len(plan_data['premiums'])} fields")
        print(f"  Benefits: {len(plan_data['benefits'])} categories")
        print(f"  Extra Benefits: {len(plan_data['extra_benefits'])} categories")

        all_parsed_data.append(plan_data)

    print(f"\n{'='*80}")
    print(f"Successfully parsed {len(all_parsed_data)} plans")
    print(f"{'='*80}")

    # Show sample of one plan
    if all_parsed_data:
        print("\n" + "="*80)
        print("SAMPLE OUTPUT (First Plan)")
        print("="*80)
        print(json.dumps(all_parsed_data[0], indent=2)[:2000] + "...")

if __name__ == '__main__':
    main()
