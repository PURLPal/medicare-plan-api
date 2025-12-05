#!/usr/bin/env python3
"""
Test parser to extract data from scraped HTML
"""
from bs4 import BeautifulSoup
import json

# Load one of the scraped HTML files
html_file = './scraped_html_selenium/Pennsylvania_H3916_038_0.html'

print(f"Parsing: {html_file}")
print("="*80)

with open(html_file, 'r', encoding='utf-8') as f:
    html_content = f.read()

soup = BeautifulSoup(html_content, 'html.parser')

print(f"\nHTML size: {len(html_content)} bytes")
print(f"Number of tables found: {len(soup.find_all('table'))}")
print(f"Number of tables with class 'mct-c-table': {len(soup.find_all('table', class_='mct-c-table'))}")

# Extract plan name
plan_name = soup.find('h1')
print(f"\nPlan name: {plan_name.get_text(strip=True) if plan_name else 'NOT FOUND'}")

# Find all tables
tables = soup.find_all('table', class_='mct-c-table')
print(f"\n{'='*80}")
print(f"TABLES FOUND: {len(tables)}")
print(f"{'='*80}")

for i, table in enumerate(tables, 1):
    caption = table.find('caption')
    caption_text = caption.get_text(strip=True) if caption else f"Table {i}"

    print(f"\n--- {caption_text} ---")

    # Extract all rows
    rows = table.find_all('tr')
    print(f"Rows: {len(rows)}")

    for row in rows[:5]:  # Show first 5 rows
        header = row.find('th')
        cell = row.find('td')

        if header and cell:
            header_text = header.get_text(strip=True)
            cell_text = cell.get_text(strip=True)
            print(f"  {header_text}: {cell_text}")

print(f"\n{'='*80}")
print("CHECKING FOR EXTRA BENEFITS SECTION")
print(f"{'='*80}")

# Look for Extra Benefits section
extra_benefits_section = soup.find('section', id='extra-benefits')
if extra_benefits_section:
    print("✓ Extra Benefits section FOUND")
    extra_tables = extra_benefits_section.find_all('table', class_='mct-c-table')
    print(f"  Tables in Extra Benefits: {len(extra_tables)}")
else:
    print("✗ Extra Benefits section NOT FOUND")

# Check if we have the full content or just the shell
content_div = soup.find('div', id='mct-root')
if content_div:
    content_text = content_div.get_text(strip=True)
    print(f"\nContent div text length: {len(content_text)} characters")
    print(f"Sample: {content_text[:200]}...")
else:
    print("\n✗ Main content div NOT FOUND")
