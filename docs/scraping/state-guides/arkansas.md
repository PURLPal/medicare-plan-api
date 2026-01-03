# Arkansas Medicare Plan Scraping Plan

**Date:** December 22, 2025  
**Status:** Ready to Execute

---

## 📊 Current Situation

### Data Check Results:
- **Total AR Plans in Landscape:** 103 unique plans
- **Already Scraped:** 0 plans (0%)
- **Need to Scrape:** 103 plans

### Plan Type Breakdown:
| Type | Count |
|------|-------|
| MA-PD | 46 |
| SNP (various) | 35 |
| PDP | 12 |
| MA | 10 |

### Arkansas Coverage:
- **ZIP Codes:** ~1,355 ZIPs (70xxx-72xxx range)
- **Counties:** 75 counties
- **Static API Status:** Currently deployed with existing data (needs update with scraped plans)

---

## 🎯 Scraping Strategy

### Two-Step Approach (Proven with South Carolina & Massachusetts):

**Step 1: Raw HTML Scraping**
- Use `scrape_arkansas.py`
- Selenium with stealth options to avoid bot detection
- Save raw HTML for each plan
- Output: `raw_ar_plans/*.html`

**Step 2: Data Extraction**
- Use `parse_ar_raw_content.py`
- BeautifulSoup to parse HTML
- Extract premiums, deductibles, benefits
- Output: `scraped_json_all/Arkansas-*.json`

### Why This Works:
✅ **Proven Method:** Successfully used for SC (71 plans) and MA
✅ **Stealth Mode:** Anti-detection tactics prevent blocking
✅ **Two-Step Process:** Separates scraping from parsing
✅ **Rate Limiting:** 1.5 second delay between requests
✅ **Error Handling:** Captures 404s and errors gracefully
✅ **Resume Capability:** Skips already-scraped plans

---

## 🚀 Execution Plan

### Phase 1: Prepare Plan List
```bash
python3 << 'EOF'
import json
with open('state_data/Arkansas.json') as f:
    plans = json.load(f)

ar_plans = []
for plan in plans:
    plan_id = plan.get('ContractPlanSegmentID', '')
    if plan_id:
        ar_plans.append({
            'plan_id': plan_id,
            'name': plan.get('Plan Name', ''),
            'type': plan.get('Contract Category Type', ''),
            'organization': plan.get('Organization Marketing Name', '')
        })

with open('ar_plans_to_scrape.json', 'w') as f:
    json.dump(ar_plans, f, indent=2)

print(f"Created ar_plans_to_scrape.json with {len(ar_plans)} plans")
EOF
```

**Expected Output:**
- `ar_plans_to_scrape.json` with 103 plans

### Phase 2: Scrape Raw HTML (~20-30 minutes)
```bash
python3 scrape_arkansas.py
```

**Expected Output:**
- ~70-90 HTML files saved to `raw_ar_plans/`
- Some plans may return 404 (discontinued)
- Progress updates every 25 plans

**Time Estimate:**
- 103 plans × 5.5 seconds per plan = ~9.5 minutes
- With overhead: 20-30 minutes

### Phase 3: Parse HTML to JSON (~1 minute)
```bash
python3 parse_ar_raw_content.py
```

**Expected Output:**
- 70-90 JSON files in `scraped_json_all/`
- Full plan data extracted (premiums, deductibles, benefits)
- Quality report showing data completeness

### Phase 4: Build Mock API
```bash
python3 build_all_state_apis.py
```

**Creates:**
- `mock_api/AR/` directory structure
- County-level plan mappings
- ZIP to plans mapping
- ~1,355 Arkansas ZIP codes mapped

### Phase 5: Build Static API
```bash
python3 build_static_api.py
```

**Creates:**
- ~1,355 AR ZIP code endpoints
- Full JSON files for each ZIP
- Correct plan categorization (MAPD, MA, PD)

### Phase 6: Generate Minified Versions (Optional)
```bash
cd minification
python3 minify_state_endpoint.py AR
```

**Creates:**
- Minified JSON files (40-50% smaller)
- Category-specific endpoints (MAPD, MA, PD)

### Phase 7: Deploy to Production
```bash
# Sync to S3
aws s3 sync static_api/medicare/zip/ s3://purlpal-medicare-api/medicare/zip/ \
  --exclude "*" --include "7[0-2]*.json" \
  --content-type "application/json"

# Invalidate CloudFront
aws cloudfront create-invalidation \
  --distribution-id E3SHXUEGZALG4E \
  --paths "/medicare/zip/7[0-2]*"
```

**Deploys:**
- All AR ZIP files to S3 (~1,355 files)
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

Based on South Carolina and Massachusetts experience:

### Scraping Success Rate: 70-85%
- SC had 71/106 available (67%)
- MA had higher success rate
- AR likely: ~70-85 real plans out of 103

### Data Quality: 100%
- All available plans should have full data
- Premiums, deductibles, benefits extracted
- Organization and plan details captured

### Deployment Impact:
- **Arkansas ZIPs:** ~1,355
- **Estimated plans per ZIP:** 20-40
- **File size per ZIP:** ~150-300 KB
- **Total data:** ~200-400 MB

---

## 🔧 Scripts to Create

### 1. `scrape_arkansas.py`
```python
#!/usr/bin/env python3
"""
Scrape Arkansas Medicare plans from Medicare.gov.
Two-step process: scrape raw HTML first, parse later.
"""
# Based on scrape_massachusetts.py and rescrape_south_carolina.py
# Includes stealth mode, rate limiting, error handling
```

### 2. `parse_ar_raw_content.py`
```python
#!/usr/bin/env python3
"""
Parse raw HTML files from raw_ar_plans/ into structured JSON.
Extracts premiums, deductibles, benefits, etc.
"""
# Based on parse_sc_raw_content.py and parse_ma_raw_content.py
```

### 3. `ar_plans_to_scrape.json`
- List of 103 unique AR plans
- Plan IDs, names, types
- Auto-generated from state_data/Arkansas.json

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
- ✅ At least 70 plans with full data (68%)
- ✅ All available plans scraped
- ✅ No IP blocks or detection issues

---

## 📝 Script Creation Needed

Before starting, create these scripts:

1. **Create `scrape_arkansas.py`:** Based on `scrape_massachusetts.py` template
2. **Create `parse_ar_raw_content.py`:** Based on `parse_ma_raw_content.py` template
3. **Generate plan list:** Run Phase 1 command to create `ar_plans_to_scrape.json`

---

## 🎯 Success Comparison

### South Carolina (Completed):
- ✅ 71/71 available plans scraped (100%)
- ✅ 525 ZIP codes deployed
- ✅ Live and operational

### Massachusetts (In Progress):
- 🔄 113 plans to scrape
- 🔄 ~1,500 ZIP codes to deploy

### Arkansas (Target):
- 🎯 ~70-85/103 available plans (expected)
- 🎯 ~1,355 ZIP codes to deploy
- 🎯 Same quality as SC

---

## 📍 Arkansas Specifics

### Geographic Coverage:
- **State Code:** AR
- **ZIP Range:** 71601-72959 (primary), 75502 (Texarkana)
- **Major Cities:** Little Rock, Fort Smith, Fayetteville, Springdale, Jonesboro
- **Population:** ~3 million
- **Counties:** 75 counties

### Test ZIPs for Verification:
- **72201** - Little Rock (Pulaski County)
- **72903** - Fort Smith (Sebastian County)
- **72701** - Fayetteville (Washington County)
- **72404** - Jonesboro (Craighead County)

---

## ⏱️ Estimated Timeline

| Phase | Duration | Notes |
|-------|----------|-------|
| Phase 1: Prepare plan list | 2 min | Automated |
| Phase 2: Scrape HTML | 20-30 min | Rate limited |
| Phase 3: Parse HTML | 1 min | Fast processing |
| Phase 4: Build mock API | 2 min | Automated |
| Phase 5: Build static API | 3 min | 1,355 ZIPs |
| Phase 6: Minification | 5 min | Optional |
| Phase 7: Deploy | 10 min | S3 upload + cache |
| **Total** | **45-60 min** | Mostly automated |

---

## 🚦 Ready to Execute

**Prerequisites:**
- ✅ State data file exists (103 plans)
- ✅ Scraping infrastructure ready
- ✅ Deployment pipeline tested
- ⚠️ Need to create scraper scripts

**Next Steps:**
1. Create `scrape_arkansas.py` and `parse_ar_raw_content.py`
2. Generate `ar_plans_to_scrape.json`
3. Run scraper
4. Build and deploy API

**Estimated Total Time:** 1 hour (mostly automated)

---

**Ready to create scripts and begin scraping when you give the go-ahead!**
