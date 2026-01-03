#!/usr/bin/env python3
"""
Parser for Rhode Island Medicare plan HTML
Extracts structured data from raw HTML
"""
import re
from bs4 import BeautifulSoup

def extract_plan_data(html_content):
    """
    Extract structured plan data from raw HTML.
    Returns (success, data_dict)
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Initialize data structure
    data = {
        'plan_info': {},
        'premiums': {},
        'deductibles': {},
        'out_of_pocket': {},
        'benefits': {},
        'drug_coverage': {},
        'extra_benefits': []
    }
    
    # Extract plan name from title
    title_tag = soup.find('title')
    if title_tag:
        title_text = title_tag.get_text(strip=True)
        if title_text != 'Medicare.gov':
            data['plan_info']['name'] = title_text
    
    # Extract from dt/dd pairs (common in Medicare.gov React app)
    dt_dd_data = {}
    dts = soup.find_all('dt')
    for dt in dts:
        label = dt.get_text(strip=True)
        dd = dt.find_next_sibling('dd')
        if dd:
            value = dd.get_text(strip=True)
            dt_dd_data[label] = value
    
    # Parse premiums - use flexible regex to handle HTML tags
    premium_patterns = {
        'Total monthly premium': r'Total monthly premium[^$]*?\$([0-9.,]+)',
        'Health premium': r'Health premium[^$]*?\$([0-9.,]+)',
        'Drug premium': r'Drug premium[^$]*?\$([0-9.,]+)',
        'Standard Part B premium': r'Standard Part B premium[^$]*?\$([0-9.,]+)',
        'Part B premium reduction': r'Part B premium reduction[^$]*?(Not offered|\$[0-9.,]+|−\$[0-9.,]+)'
    }
    
    for field, pattern in premium_patterns.items():
        match = re.search(pattern, html_content, re.IGNORECASE)
        if match:
            data['premiums'][field] = match.group(1)
    
    # Also check dt/dd data for premiums
    for key, value in dt_dd_data.items():
        if 'premium' in key.lower():
            data['premiums'][key] = value
    
    # Parse deductibles
    deductible_patterns = {
        'Health deductible': r'Health deductible[^$]*?\$([0-9.,]+)',
        'Drug deductible': r'Drug deductible[^$]*?\$([0-9.,]+)'
    }
    
    for field, pattern in deductible_patterns.items():
        match = re.search(pattern, html_content, re.IGNORECASE)
        if match:
            data['deductibles'][field] = match.group(1)
    
    for key, value in dt_dd_data.items():
        if 'deductible' in key.lower():
            data['deductibles'][key] = value
    
    # Parse maximum out-of-pocket
    moop_match = re.search(r'Maximum you pay for health services[^$]*?\$([0-9.,]+)', html_content, re.IGNORECASE)
    if moop_match:
        data['out_of_pocket']['Maximum out-of-pocket'] = moop_match.group(1)
    
    # Extract from tables
    tables = soup.find_all('table')
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['th', 'td'])
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                
                if label and value:
                    # Categorize the data
                    label_lower = label.lower()
                    if 'premium' in label_lower and label not in data['premiums']:
                        data['premiums'][label] = value
                    elif 'deductible' in label_lower and label not in data['deductibles']:
                        data['deductibles'][label] = value
                    elif any(word in label_lower for word in ['doctor', 'specialist', 'hospital', 'emergency']):
                        data['benefits'][label] = value
                    elif 'drug' in label_lower or 'pharmacy' in label_lower:
                        data['drug_coverage'][label] = value
    
    # Determine success based on data completeness
    has_premiums = bool(data['premiums'])
    has_deductibles = bool(data['deductibles'])
    has_benefits = bool(data['benefits'])
    
    success = has_premiums or has_deductibles or has_benefits
    
    return success, data

def validate_data_completeness(data):
    """
    Check if extracted data is complete (non-null/non-empty).
    Returns (is_complete, issues_list)
    """
    issues = []
    
    # Check plan_info
    if not data.get('plan_info', {}).get('name'):
        issues.append("Missing plan name")
    
    # Check premiums
    if not data.get('premiums'):
        issues.append("No premium data")
    
    # Check deductibles
    if not data.get('deductibles'):
        issues.append("No deductible data")
    
    # Check benefits (at least some should exist)
    if not data.get('benefits') and not data.get('drug_coverage'):
        issues.append("No benefits or drug coverage data")
    
    is_complete = len(issues) == 0
    
    return is_complete, issues
