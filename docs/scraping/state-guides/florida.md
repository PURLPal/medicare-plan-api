# Florida Medicare Plan Scraping - Completion Plan

## 📊 Current Status

**Excellent Progress Already Made!**

- ✅ **417/621 plans already scraped** (67.1% complete)
- ✅ State data file exists (`state_data/Florida.json`)
- ✅ Mock API structure already built (`mock_api/FL/`)
- ⏳ **204 plans remaining** to scrape (32.9%)

---

## 🎯 Objective

Complete the Florida Medicare plan scraping by collecting the remaining **204 plans**, bringing total coverage to **621 plans** across Florida's **67 counties**.

---

## 📋 5-Phase Completion Plan

### **Phase 1: Setup & Verification** ⏱️ ~5 minutes

**Tasks:**
1. ✅ Verify existing 417 scraped files in `scraped_json_all/`
2. ✅ Check `state_data/Florida.json` structure (621 plans total)
3. ⚠️ Create `raw_fl_plans/` directory for HTML storage
4. ⚠️ Create or copy `scrape_florida.py` from Arizona template
5. ⚠️ Create or copy `parse_fl_raw_content.py` from Arizona template
6. ⚠️ Update scripts for Florida-specific paths and settings
7. ✅ Verify 204 remaining plans need scraping

**Verification:**
```bash
# Count existing files
ls scraped_json_all/Florida-*.json | wc -l  # Should show 417

# Check state data
python3 -c "import json; print(len(json.load(open('state_data/Florida.json'))))"  # Should show 621

# Identify remaining plans
python3 << EOF
import json
from pathlib import Path

state_plans = json.load(open('state_data/Florida.json'))
scraped = set(f.stem.replace('Florida-', '') for f in Path('scraped_json_all').glob('Florida-*.json'))
remaining = [p for p in state_plans if p['plan_id'] not in scraped]
print(f"Remaining to scrape: {len(remaining)}")
EOF
```

---

### **Phase 2: Scrape Remaining Plans** ⏱️ ~30-40 minutes

**Approach:**
- Use **resumable two-step scraping** (proven successful with MA & AZ)
- Selenium WebDriver with stealth mode
- Rate limiting: 1.5 seconds between requests
- Progress saved after each plan

**Details:**
- **Plans to scrape:** 204 (33% of total)
- **Default ZIP:** 33101 (Miami)
- **Raw output:** `raw_fl_plans/` directory
- **JSON output:** `scraped_json_all/Florida-{plan_id}.json`
- **Progress file:** `fl_scraping_progress.json`

**Estimated Time:**
- 204 plans × 1.5 seconds = ~306 seconds = **~5 minutes of scraping**
- + overhead/loading time = **~30-40 minutes total**

**Command:**
```bash
python3 scrape_florida.py
```

**Expected Output:**
```
================================================================================
FLORIDA MEDICARE PLAN SCRAPER (RESUMABLE)
================================================================================
Total FL plans: 621
Previously completed: 417
Remaining to scrape: 204
...
[1/204] H1036_001_0...
  ✓ Saved HTML
...
================================================================================
RAW HTML SCRAPING COMPLETE
================================================================================
✓ Success: 204
⚠️  Not Found (404): 0
✗ Errors: 0
Total scraped: 204/204
```

---

### **Phase 3: Parse HTML to Structured JSON** ⏱️ ~3-5 minutes

**Approach:**
- BeautifulSoup HTML parsing
- Extract premiums, deductibles, benefits from dt/dd pairs and tables
- Update existing JSON files with parsed data

**Details:**
- **Input:** `raw_fl_plans/*.html` (204 files)
- **Output:** Update `scraped_json_all/Florida-*.json` with parsed data
- **Success rate:** Expect 100% (proven with MA: 114/114, AZ: 143/143)

**Command:**
```bash
python3 parse_fl_raw_content.py
```

**Expected Output:**
```
================================================================================
PARSING FLORIDA RAW HTML FILES
================================================================================
HTML files to parse: 204

✓ H1036_001_0
✓ H1036_002_0
...
================================================================================
PARSING COMPLETE
================================================================================
Success: 204
Empty: 0
Not found (404): 0
Errors: 0
Total: 204

Total FL plan files: 621
With complete data: 621
Quality: 100.0%
```

---

### **Phase 4: Rebuild API Files** ⏱️ ~2-3 minutes

**Approach:**
- Rebuild mock API to include all 621 plans
- Regenerate static API files for all Florida ZIP codes
- Maintain additive approach (won't affect other states)

**Steps:**
1. Run `build_all_state_apis.py` - Updates `mock_api/FL/`
2. Run `build_static_api.py` - Regenerates all ZIP endpoints

**Details:**
- **Florida ZIPs:** ~1,000+ unique ZIP codes
- **Counties:** 67 counties
- **Plan files:** 621 individual plan endpoints

**Commands:**
```bash
python3 build_all_state_apis.py
python3 build_static_api.py
```

**Expected Output:**
```
Building API data...
  Florida (FL)... ✅
  
Generating ZIP files...
  Generated 39,298 ZIP files
  
Generating plan files...
  Generated 2,864 plan files (includes 621 FL plans)
```

---

### **Phase 5: Deploy to Production** ⏱️ ~10-15 minutes

**Approach:**
- Sync updated files to S3
- Invalidate CloudFront cache for Florida paths
- Verify endpoints are live

**Steps:**

1. **Upload to S3:**
```bash
aws s3 sync static_api/ s3://purlpal-medicare-api/ --delete
```

2. **Invalidate CloudFront Cache:**
```bash
aws cloudfront create-invalidation \
  --distribution-id E3SHXUEGZALG4E \
  --paths "/medicare/zip/32*" "/medicare/zip/33*" "/medicare/zip/34*" \
         "/medicare/state/FL/*" "/medicare/states.json"
```

3. **Verify Endpoints:**
```bash
# Miami
curl -s "https://medicare.purlpal-api.com/medicare/zip/33101.json" | jq '.plan_count'

# Orlando
curl -s "https://medicare.purlpal-api.com/medicare/zip/32801.json" | jq '.plan_count'

# Tampa
curl -s "https://medicare.purlpal-api.com/medicare/zip/33601.json" | jq '.plan_count'

# Jacksonville
curl -s "https://medicare.purlpal-api.com/medicare/zip/32099.json" | jq '.plan_count'
```

**Expected Results:**
- HTTP 200 status
- Valid JSON with plan data
- Florida listed in `states.json` with 621 plans

---

## 🔧 Technical Details

### Florida Specifics

**State Info:**
- **Total Plans:** 621 (largest state so far!)
- **Counties:** 67
- **ZIP Codes:** ~1,000+
- **Plan Types:** HMO, PPO, HMO-POS, PFFS, PDP, C-SNP, D-SNP
- **Major Markets:** Miami, Orlando, Tampa, Jacksonville, Fort Lauderdale

**Plan Distribution:**
- Medicare Advantage (MAPD): ~550 plans
- Prescription Drug (PDP): ~71 plans

**Carriers:**
- UnitedHealthcare, Humana, WellCare, Freedom Health, Optimum HealthCare, CarePlus, Simply Healthcare, Aetna, etc.

### Script Configuration

**scrape_florida.py:**
```python
RAW_DIR = Path('./raw_fl_plans')
JSON_DIR = Path('./scraped_json_all')
PROGRESS_FILE = Path('./fl_scraping_progress.json')
STATE_DATA_FILE = Path('./state_data/Florida.json')
DEFAULT_ZIP = "33101"  # Miami
STATE_NAME = "Florida"
```

**parse_fl_raw_content.py:**
```python
RAW_DIR = Path('raw_fl_plans')
JSON_DIR = Path('scraped_json_all')
STATE_NAME = "Florida"
```

---

## ⚠️ Known Issues & Solutions

### Issue 1: Already Partially Complete
**Solution:** Script will automatically detect 417 existing files and only scrape the remaining 204 plans.

### Issue 2: React SPA 404 Detection
**Solution:** Check for generic "Medicare.gov" title to identify valid plan pages (already implemented in parser).

### Issue 3: Large Number of Plans (621)
**Solution:** 
- Resumable scraping with progress tracking
- Can stop/restart at any time
- Only 204 remaining (manageable)

### Issue 4: Timeout/Rate Limiting
**Solution:**
- 1.5 second delay between requests
- Stealth mode enabled
- User-agent rotation

---

## ✅ Success Criteria

### Phase Completion:
- ✅ **Phase 1:** Scripts created and configured
- ✅ **Phase 2:** 204/204 plans successfully scraped (100%)
- ✅ **Phase 3:** 204/204 plans parsed with complete data (100%)
- ✅ **Phase 4:** All 621 plans in mock API, all ZIPs regenerated
- ✅ **Phase 5:** Endpoints live and verified

### Data Quality:
- ✅ All 621 plans have structured JSON files
- ✅ 100% parse success rate
- ✅ All premiums, deductibles, and benefits extracted
- ✅ No 404 errors or missing data

### Deployment:
- ✅ All Florida ZIPs accessible via API
- ✅ State endpoint returns 621 plans
- ✅ Sample endpoints verified (Miami, Orlando, Tampa, Jacksonville)
- ✅ CloudFront serving updated data

---

## 📈 Estimated Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| **Phase 1** | 5 min | Setup scripts and directories |
| **Phase 2** | 30-40 min | Scrape 204 remaining plans |
| **Phase 3** | 3-5 min | Parse HTML to JSON |
| **Phase 4** | 2-3 min | Rebuild API files |
| **Phase 5** | 10-15 min | Deploy and verify |
| **TOTAL** | **~50-70 min** | Complete Florida deployment |

---

## 🧪 Testing Plan

### Pre-Deployment Tests:
```python
# 1. Verify local data completeness
import json
from pathlib import Path

fl_files = list(Path('scraped_json_all').glob('Florida-*.json'))
print(f"Total FL files: {len(fl_files)}")  # Should be 621

# 2. Check data quality
complete = 0
for f in fl_files:
    data = json.load(open(f))
    if len(data.get('premiums', {})) > 0 or len(data.get('benefits', {})) > 0:
        complete += 1
print(f"With complete data: {complete}/{len(fl_files)}")

# 3. Verify ZIP mapping
with open('static_api/medicare/zip/33101.json') as f:
    miami_data = json.load(f)
print(f"Miami (33101) plans: {miami_data['plan_count']}")
```

### Post-Deployment Tests:
```bash
# Test major Florida cities
curl -s "https://medicare.purlpal-api.com/medicare/zip/33101.json" | jq '.plan_count'  # Miami
curl -s "https://medicare.purlpal-api.com/medicare/zip/32801.json" | jq '.plan_count'  # Orlando
curl -s "https://medicare.purlpal-api.com/medicare/zip/33601.json" | jq '.plan_count'  # Tampa
curl -s "https://medicare.purlpal-api.com/medicare/zip/32099.json" | jq '.plan_count'  # Jacksonville

# Verify state endpoint
curl -s "https://medicare.purlpal-api.com/medicare/state/FL/info.json"
curl -s "https://medicare.purlpal-api.com/medicare/state/FL/plans.json" | jq '.length'  # Should be 621
```

---

## 🚀 Ready to Start?

**To begin Florida completion:**

```bash
# 1. Create scripts (if needed)
# 2. Run: python3 scrape_florida.py
# 3. Run: python3 parse_fl_raw_content.py
# 4. Run: python3 build_all_state_apis.py
# 5. Run: python3 build_static_api.py
# 6. Deploy to AWS
```

---

## 📊 Impact

**Florida Stats:**
- **621 plans** (largest state deployment yet!)
- **67 counties** covered
- **~1,000+ ZIP codes** with data
- **Major metros:** Miami-Dade, Broward, Palm Beach, Orange, Hillsborough

**API Growth:**
- Current: 29 states
- After FL completion: **30 states** (still showing as 29, but with complete FL data)
- Total plans: 2,864 → **2,864** (FL already counted, just completing the data)

---

## 🎯 Next Steps After Florida

With Florida complete, potential next targets:
1. **Texas** - Large state, high impact
2. **Georgia** - Southeast expansion
3. **Pennsylvania** - Northeast coverage
4. **Illinois** - Midwest expansion

---

**Let's complete Florida and make it the most comprehensive state in the API! 🌴**
