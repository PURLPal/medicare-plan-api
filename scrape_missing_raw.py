#!/usr/bin/env python3
"""
Scrape remaining 35 SC plans - save RAW HTML then parse.
Two-step approach that worked for priority plans.
"""
import json
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth

RAW_DIR = Path('./raw_sc_plans')
RAW_DIR.mkdir(exist_ok=True)

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

def create_driver():
    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_argument('--window-size=1920,1080')
    opts.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=opts)
    
    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="MacIntel",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )
    
    return driver

def scrape_raw(driver, plan_id, zip_code="29401"):
    """Scrape and save raw HTML."""
    url = f"https://www.medicare.gov/plan/details/{plan_id}?zip={zip_code}&year=2026"
    
    try:
        driver.get(url)
        
        # Wait for body
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        time.sleep(4)  # Let JS render
        
        # Save raw HTML
        raw_file = RAW_DIR / f"{plan_id}.html"
        with open(raw_file, 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        
        print(f"  ✓ Saved raw HTML: {raw_file.name}", flush=True)
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}", flush=True)
        return False

def main():
    print("="*80)
    print("SCRAPING MISSING SC PLANS - RAW HTML")
    print("="*80)
    print(f"Plans: {len(MISSING_PLANS)}")
    print(f"Output: {RAW_DIR}\n")
    
    driver = create_driver()
    
    try:
        success = 0
        for i, plan_id in enumerate(MISSING_PLANS, 1):
            print(f"[{i}/{len(MISSING_PLANS)}] {plan_id}...", flush=True)
            if scrape_raw(driver, plan_id):
                success += 1
            time.sleep(1)
        
        print(f"\n{'='*80}")
        print(f"RAW SCRAPING COMPLETE: {success}/{len(MISSING_PLANS)}")
        print(f"{'='*80}\n")
        print("Next step: Parse with parse_sc_raw_content.py")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
