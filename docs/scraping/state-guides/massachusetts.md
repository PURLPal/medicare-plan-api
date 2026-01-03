# Massachusetts Medicare Plan Scraping Plan

**Date:** December 22, 2025  
**Status:** Ready to Execute

---

## 📊 Current Situation

### Data Check Results:
- **Total MA Plans in Landscape:** 114 unique plans
- **Already Scraped:** 1 plan (0.9%)
- **Need to Scrape:** 113 plans

### Plan Type Breakdown:
| Type | Count |
|------|-------|
| HMO | 43 |
| PPO | 28 |
| HMO D-SNP | 16 |
| HMO-POS | 13 |
| PDP | 11 |
| Other SNPs | 3 |

---

## 🎯 Scraping Strategy

### Two-Step Approach (Proven with South Carolina):

**Step 1: Raw HTML Scraping**
- Use `scrape_massachusetts.py`
- Selenium with stealth options to avoid bot detection
- Save raw HTML for each plan
- Output: `raw_ma_plans/*.html`

**Step 2: Data Extraction**
- Use `parse_ma_raw_content.py`
- BeautifulSoup to parse HTML
- Extract premiums, deductibles, benefits
- Output: `scraped_json_all/Massachusetts-*.json`

### Why This Works:
✅ **Stealth Mode:** Same anti-detection tactics as SC
✅ **Two-Step Process:** Separates scraping from parsing
✅ **Rate Limiting:** 1.5 second delay between requests
✅ **Error Handling:** Captures 404s and errors gracefully
✅ **Resume Capability:** Skips already-scraped plans

---

## 🚀 Execution Plan

### Phase 1: Scrape Raw HTML (~ 3-4 hours)
```bash
python3 scrape_massachusetts.py
```

**Expected Output:**
- 113 HTML files saved to `raw_ma_plans/`
- Some plans may return 404 (discontinued, like SC)
- Progress updates every 25 plans

**Time Estimate:**
- 113 plans × 5.5 seconds per plan = ~10 minutes
- With overhead: 15-20 minutes

### Phase 2: Parse HTML to JSON (~ 1 minute)
```bash
python3 parse_ma_raw_content.py
```

**Expected Output:**
- 113 JSON files updated in `scraped_json_all/`
- Full plan data extracted (premiums, deductibles, benefits)
- Quality report showing data completeness

### Phase 3: Build Mock API
```bash
python3 build_ma_zip_mapping.py  # Create this
```

**Creates:**
- `mock_api/MA/` directory structure
- County-level plan mappings
- ZIP to plans mapping

### Phase 4: Build Static API
```bash
python3 build_static_api.py
```

**Creates:**
- ~1,500 MA ZIP code endpoints
- Full JSON files for each ZIP

### Phase 5: Generate Minified Versions
```bash
cd minification
python3 minify_state_endpoint.py MA
```

**Creates:**
- Minified JSON files (8-99% smaller)
- Category-specific endpoints (MAPD, MA, PDP)

### Phase 6: Deploy to Production
```bash
python3 deploy_ma.py  # Create deployment script
```

**Deploys:**
- All MA ZIP files to S3
- Invalidates CloudFront cache
- Verifies live endpoints

---

## 🛡️ Anti-Detection Features

**Chrome Options:**
- Headless mode with `--headless=new`
- Custom user agent (Mac/Chrome)
- Disabled automation flags
- Window size 1920x1080

**Selenium Stealth:**
- Modified navigator properties
- Webdriver flag removal
- Language/platform spoofing

**Rate Limiting:**
- 1.5 second delay between requests
- Progress checkpoints every 25 plans
- Automatic retry on errors

---

## 📈 Expected Results

Based on South Carolina experience:

### Scraping Success Rate: 67-100%
- SC had 71/106 available (67%)
- 35 plans were 404 (discontinued)
- MA likely similar: ~75-100 real plans

### Data Quality: 100%
- All available plans should have full data
- Premiums, deductibles, benefits extracted
- Organization and plan details captured

### Deployment Impact:
- **Massachusetts ZIPs:** ~1,500
- **Estimated plan count per ZIP:** 30-60
- **File size per ZIP:** ~200-400 KB
- **Total data:** ~300-600 MB

---

## 🔧 Scripts Created

### 1. `scrape_massachusetts.py`
- Main scraper with Selenium + stealth
- Saves raw HTML files
- Handles 404s and errors
- Progress tracking

### 2. `parse_ma_raw_content.py`
- Parses HTML with BeautifulSoup
- Extracts structured data
- Updates JSON files
- Quality reporting

### 3. `ma_plans_to_scrape.json`
- List of 114 unique MA plans
- Plan IDs, names, types
- Ready for scraping

---

## ⚠️ Known Issues & Mitigations

### Potential Issues:
1. **Bot Detection:** Medicare.gov may block requests
   - **Mitigation:** Stealth mode + rate limiting
   
2. **404 Errors:** Some plans may not exist
   - **Mitigation:** Expected behavior, handled gracefully
   
3. **Empty Data:** Some plans may not load properly
   - **Mitigation:** Two-step process allows re-parsing

### Success Criteria:
- ✅ At least 70 plans with full data (60%)
- ✅ All available plans scraped
- ✅ No IP blocks or detection issues

---

## 📝 Next Steps

**Ready to Execute:**
1. Run `python3 scrape_massachusetts.py`
2. Wait ~15-20 minutes for completion
3. Run `python3 parse_ma_raw_content.py`
4. Verify data quality
5. Proceed with API build & deployment

**Estimated Total Time:** 1-2 hours (mostly automated)

---

## 🎯 Success Comparison

### South Carolina (Completed):
- ✅ 71/71 available plans scraped (100%)
- ✅ 525 ZIP codes deployed
- ✅ Live and operational

### Massachusetts (Target):
- 🎯 ~75-100/114 available plans (expected)
- 🎯 ~1,500 ZIP codes to deploy
- 🎯 Same quality as SC

---

**Ready to scrape when you give the go-ahead!**
