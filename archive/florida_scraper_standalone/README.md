# Florida Medicare Plan Scraper

Standalone scraper for **621 Florida Medicare plans** from Medicare.gov.

## 📋 Requirements

- Python 3.7+
- Chrome browser installed
- Internet connection

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install selenium beautifulsoup4
```

### 2. Run the Scraper

```bash
python3 scrape_florida.py
```

That's it! The scraper will:
- Scrape all 621 Florida plans
- Save HTML files to `scraped_html/`
- Save parsed JSON data to `scraped_json/`
- Show real-time progress
- Take approximately **4-5 hours** to complete

## 📁 What Gets Created

```
florida_scraper_standalone/
├── scrape_florida.py          # Main scraper script
├── state_data/
│   └── Florida.json           # Source data (621 plans)
├── scraped_html_all/          # Raw HTML files (created during scrape)
│   ├── Florida-H0001_001_0.html
│   ├── Florida-H0001_002_0.html
│   └── ...
├── scraped_json_all/          # Parsed JSON files (created during scrape)
│   ├── Florida-H0001_001_0.json
│   ├── Florida-H0001_002_0.json
│   └── ...
└── florida_results.json       # Summary of results
```

## ⏱️ Timing & Progress

- **Total plans**: 621
- **Estimated time**: 4-5 hours
- **Delay between requests**: 8-15 seconds (to avoid rate limiting)
- **Progress updates**: Every 10 plans

The scraper shows real-time progress:
```
[1/621] H0001_001_0: Example Plan Name
  ✓ Success
  
[10/621] H0001_010_0: Another Plan
  ✓ Success
  Progress: 10/10 succeeded | ETA: 245.2 min
```

## 🛡️ Anti-Detection Features

The scraper includes several features to avoid being blocked:

- **Randomized delays** (8-15 seconds between requests)
- **User agent rotation** (appears as different browsers)
- **Headless mode** (runs without opening windows)
- **Fresh browser** per plan (avoids tracking)
- **Human-like scrolling** (simulates real user behavior)
- **Disabled images** (faster loading)

## 📊 Output Format

Each plan is saved as JSON with this structure:

```json
{
  "plan_info": {
    "name": "Plan Name",
    "organization": "Organization Name",
    "type": "HMO",
    "id": "H0001-001-0"
  },
  "premiums": {
    "Total monthly premium": "$25.00",
    "Health premium": "$15.00",
    "Drug premium": "$10.00"
  },
  "deductibles": {
    "Health deductible": "$250",
    "Drug deductible": "$100"
  },
  "maximum_out_of_pocket": { ... },
  "contact_info": {
    "Plan address": "123 Main St\nCity, FL 12345"
  },
  "benefits": { ... },
  "drug_coverage": { ... },
  "extra_benefits": { ... }
}
```

## ❌ If Something Goes Wrong

### Scraper stops or crashes
- Check `florida_results.json` to see which plans succeeded
- Restart the script - it will re-scrape everything (or modify to skip completed)

### Low success rate (< 80%)
- Your IP might be rate-limited
- Wait 30-60 minutes before retrying
- Consider using a VPN

### Chrome/ChromeDriver errors
```bash
# Update ChromeDriver automatically
pip install --upgrade selenium
```

## 🔄 Resuming After Interruption

If the scraper stops, you can modify `scrape_florida.py` to skip already scraped plans:

```python
# Add this after loading plans, before the main loop:
already_scraped = set()
for f in json_dir.glob('Florida-*.json'):
    plan_id = f.stem.replace('Florida-', '')
    already_scraped.add(plan_id)

# Then filter plans:
plans = [p for p in plans if p['ContractPlanSegmentID'] not in already_scraped]
print(f'Skipping {len(already_scraped)} already scraped plans')
print(f'Remaining: {len(plans)} plans')
```

## 📤 Sending Results Back

Once complete, you can send back just the JSON files:

```bash
# Create a zip of just the JSON data
zip -r florida_scraped_json.zip scraped_json_all/

# Or tar.gz
tar -czf florida_scraped_json.tar.gz scraped_json_all/
```

The JSON files are what matter most - the HTML files are just backups.

## 💡 Tips

1. **Run overnight**: 4-5 hours is a long time - let it run while you sleep
2. **Check progress occasionally**: Look at the terminal output or `florida_results.json`
3. **Don't interrupt**: Let it finish completely for best results
4. **Save your work**: The JSON files are the valuable output

## 🐛 Troubleshooting

**"No module named 'selenium'"**
```bash
pip install selenium beautifulsoup4
```

**"Chrome driver not found"**
- Make sure Chrome browser is installed
- Selenium will auto-download the driver

**Script runs but all fail**
- Check your internet connection
- Try running with just 1-2 plans first to test

## 📞 Questions?

- Total plans: 621
- Expected success rate: 85-95%
- Average time per plan: ~25 seconds
- Total estimated time: 4-5 hours

Good luck! 🍀
