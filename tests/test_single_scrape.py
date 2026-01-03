#!/usr/bin/env python3
"""Test script to scrape a single plan and verify address formatting"""

import json
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import re

def create_driver():
    """Create Chrome driver"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')

    driver = webdriver.Chrome(options=chrome_options)
    return driver

def extract_plan_data(html_content):
    """Extract all plan data from HTML content"""
    soup = BeautifulSoup(html_content, 'html.parser')

    # Replace <br> tags with newlines before parsing
    for br in soup.find_all('br'):
        br.replace_with('\n')

    plan_data = {
        'contact_info': {}
    }

    # Extract all tables
    tables = soup.find_all('table', class_='mct-c-table')

    for table in tables:
        caption = table.find('caption')
        if not caption:
            continue

        table_title = caption.get_text(strip=True)

        if 'Contact Information' in table_title:
            rows = table.find_all('tr')
            for row in rows:
                header = row.find('th')
                cell = row.find('td')

                if header and cell:
                    header_text = header.get_text(strip=True)
                    header_text = re.sub(r"What's.*?\?", "", header_text).strip()

                    # Get cell text preserving newlines from <br> tags
                    cell_text = cell.get_text(separator='\n').strip()
                    # Clean up multiple consecutive newlines
                    cell_text = re.sub(r'\n\s*\n', '\n', cell_text)

                    plan_data['contact_info'][header_text] = cell_text

    return plan_data

# Test with Arizona plan H4931-007-0
url = "https://www.medicare.gov/plan-compare/plan-details/2026-H4931-007-0?year=2026&lang=en"

print("Testing single plan scrape...")
print(f"URL: {url}\n")

driver = create_driver()

try:
    print("Loading page...")
    driver.get(url)

    # Wait for page to load
    wait = WebDriverWait(driver, 30)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "mct-c-table")))
    time.sleep(5)

    print("Extracting data...")
    html_content = driver.page_source
    plan_data = extract_plan_data(html_content)

    print("\nExtracted contact info:")
    print(json.dumps(plan_data['contact_info'], indent=2))

    if 'Plan address' in plan_data['contact_info']:
        address = plan_data['contact_info']['Plan address']
        print(f"\nAddress repr: {repr(address)}")
        print(f"Has newline character: {chr(10) in address}")
        print(f"Number of lines: {len(address.split(chr(10)))}")

finally:
    driver.quit()

print("\nTest complete!")
