# Arizona Medicare Plan Scraping Plan

**State:** Arizona (AZ)  
**Target:** 143 Medicare plans  
**Strategy:** Replicate Massachusetts scraping methodology  
**Created:** December 22, 2025

---

## 📊 Arizona Data Assessment

### Plan Inventory
- **Total Plans:** 143 unique plans
- **Counties:** 16 (including "All Counties" for PDPs)
- **Existing Scraped:** 18 files (12.6% complete)
- **Remaining:** 125 plans to scrape

### Plan Type Breakdown
| Type | Count | Description |
|------|-------|-------------|
| HMO | 45 | Health Maintenance Organization |
| PPO | 24 | Preferred Provider Organization |
| HMO C-SNP | 19 | Chronic/Disabling Condition SNP |
| HMO-POS | 13 | HMO with Point of Service |
| HMO-POS C-SNP | 12 | HMO-POS Chronic SNP |
| PDP | 10 | Prescription Drug Plans |
| HMO D-SNP | 9 | Dual-Eligible SNP |
| HMO I-SNP | 3 | Institutional SNP |
| HMO-POS D-SNP | 2 | HMO-POS Dual-Eligible SNP |
| Regional PPO | 2 | Regional Preferred Provider |
| HMO-POS I-SNP | 2 | HMO-POS Institutional SNP |
| PPO C-SNP | 1 | PPO Chronic SNP |
| PPO I-SNP | 1 | PPO Institutional SNP |

### Counties Covered
```
All Counties (PDPs), Apache, Cochise, Coconino, Gila, Graham, 
Greenlee, La Paz, Maricopa, Mohave, Navajo, Pima, Pinal, 
Santa Cruz, Yavapai, Yuma
```

### Sample Plan IDs
```
S4802_092_0  - Wellcare Classic (PDP)
S5617_138_0  - HealthSpring Assurance Rx (PDP)
H2228_014_0  - Humana Gold Plus HMO
H3759_015_0  - Devoted Health HMO
H5459_003_0  - Alignment Health Plan HMO
```

---

## 🎯 Scraping Strategy

### Methodology (Proven from MA)
Follow the successful **two-step Massachusetts approach**:

#### **Step 1: Raw HTML Scraping**
- Use Selenium WebDriver with Chrome
- Apply stealth mode to avoid bot detection
- Navigate to Medicare.gov plan detail pages
- Save raw HTML for each plan
- Track progress with resume capability

#### **Step 2: HTML Parsing**
- Parse saved HTML with BeautifulSoup
- Extract structured data from `<dt>`/`<dd>` elements
- Extract benefit tables
- Extract premium and deductible information
- Generate clean JSON output

---

## 📋 Implementation Plan

### Phase 1: Setup (5 minutes)

**1.1 Create Scraping Script**
```bash
cp scrape_massachusetts.py scrape_arizona.py
```

Update in `scrape_arizona.py`:
- Change `STATE_NAME = 'Arizona'`
- Change `STATE_DATA_FILE = Path('./state_data/Arizona.json')`
- Update `RAW_DIR = Path('./raw_az_plans')`
- Update `PROGRESS_FILE = Path('./az_scraping_progress.json')`

**1.2 Create Parsing Script**
```bash
cp parse_ma_raw_content.py parse_az_raw_content.py
```

Update in `parse_az_raw_content.py`:
- Change `STATE = 'Arizona'`
- Change `RAW_DIR = Path('./raw_az_plans')`

**1.3 Prepare Directories**
```bash
mkdir -p raw_az_plans
```

**1.4 Verify State Data**
Confirm `state_data/Arizona.json` has all 143 plans.

---

### Phase 2: Scraping (20 minutes)

**2.1 Start Scraper**
```bash
python3 scrape_arizona.py
```

**Expected Behavior:**
- Loads 143 plans from `state_data/Arizona.json`
- Checks for existing progress (18 files already scraped)
- Resumes from where it left off
- Scrapes ~8 seconds per plan
- Saves progress every 10 plans
- Creates HTML files in `raw_az_plans/`

**2.2 Monitor Progress**
```bash
# Watch progress in real-time
tail -f az_scraping_progress.json

# Or check status manually
python3 check_az_progress.py
```

**Expected Output:**
- 143 HTML files in `raw_az_plans/`
- Progress file with success/failure tracking
- Success rate should be >95% (based on MA experience)

**2.3 Handle Issues**
If plans fail:
- Review error messages
- Check for 404s (plans may be unavailable)
- Retry failed plans if needed

---

### Phase 3: Parsing (5 minutes)

**3.1 Parse Raw HTML**
```bash
python3 parse_az_raw_content.py
```

**Expected Behavior:**
- Reads all 143 HTML files from `raw_az_plans/`
- Extracts structured data using BeautifulSoup
- Updates JSON files in `scraped_json_all/Arizona-*.json`
- Validates data quality

**Expected Output:**
- 143 JSON files in `scraped_json_all/`
- Each with premiums, deductibles, benefits data
- Quality report showing completion rate

**3.2 Verify Data Quality**
```bash
python3 << 'EOF'
from pathlib import Path
import json

az_files = list(Path('scraped_json_all').glob('Arizona-*.json'))
print(f"Total: {len(az_files)}")

complete = 0
for f in az_files[:10]:
    with open(f) as fp:
        data = json.load(fp)
    if data.get('premiums') and data.get('benefits'):
        complete += 1

print(f"Sample quality: {complete}/10 have data")
EOF
```

---

### Phase 4: API Generation (10 minutes)

**4.1 Build Mock API Structure**
```bash
python3 build_all_state_apis.py
```

This will:
- Read Arizona plans from `scraped_json_all/Arizona-*.json`
- Load county assignments from CMS Landscape CSV
- Load ZIP-to-county mappings
- Create `mock_api/AZ/` directory structure
- Generate `counties/*.json` files
- Generate `zip_to_plans.json` mapping
- Create `api_info.json`

**Expected Output:**
```
mock_api/AZ/
├── api_info.json
├── counties/
│   ├── Maricopa.json
│   ├── Pima.json
│   └── [14 more counties]
└── zip_to_plans.json (400+ AZ ZIP codes)
```

**4.2 Generate Static API Files**
```bash
python3 build_static_api.py
```

This will:
- Load all state data (including new AZ)
- Generate ZIP endpoint files
- Generate state endpoint files
- Update states index
- Output to `static_api/medicare/`

**Expected Output:**
- 400+ new ZIP files for Arizona
- `static_api/medicare/state/AZ/info.json`
- `static_api/medicare/state/AZ/plans.json`
- Updated `static_api/medicare/states.json`

---

### Phase 5: Deployment (5 minutes)

**5.1 Deploy to S3**
```bash
./deploy_medicare_api.sh
```

This will:
- Sync `static_api/` to S3 bucket
- Upload ~62,000+ files (adding AZ files)
- Preserve existing state data

**5.2 Invalidate CloudFront Cache**
```bash
aws cloudfront create-invalidation \
  --distribution-id E3SHXUEGZALG4E \
  --paths "/medicare/zip/85*" "/medicare/zip/86*" \
          "/medicare/state/AZ/*" "/medicare/states.json"
```

**5.3 Verify Live**
```bash
# Test Phoenix ZIP
curl -s "https://medicare.purlpal-api.com/medicare/zip/85001.json" | python3 -m json.tool | head -20

# Test Tucson ZIP
curl -s "https://medicare.purlpal-api.com/medicare/zip/85701.json" | python3 -m json.tool | head -20
```

---

## 🔧 Technical Details

### URL Format (2026 Medicare.gov)
```
https://www.medicare.gov/plan-compare/#/plan-details/2026-{plan_id}?year=2026&lang=en
```

Where `{plan_id}` has underscores replaced with hyphens:
- `H2228_014_0` → `H2228-014-0`

### Scraping Configuration
```python
# Timing
PAGE_LOAD_WAIT = 6 seconds  # React SPA render time
BETWEEN_REQUESTS = 2 seconds  # Rate limiting

# Detection
USER_AGENT = Chrome 119 + Windows
STEALTH_MODE = Enabled
HEADLESS = True
```

### Data Extraction Points
```
Plan Name:     <title> tag
Premiums:      <dt>/<dd> pairs with "premium" keyword
Deductibles:   <dt>/<dd> pairs with "deductible" keyword
Benefits:      <table> elements with preceding <h3> headers
Organization:  Meta tags or footer
```

---

## ⚠️ Known Issues & Solutions

### Issue 1: 404 Pages
**Symptom:** Some plans return "Page Not Found"  
**Cause:** Plan may be discontinued or not available  
**Solution:** Mark as 'not_found' and continue  
**Expected:** 5-10% of plans may be 404s

### Issue 2: Rate Limiting
**Symptom:** Connection timeouts or blocks  
**Cause:** Too many requests too fast  
**Solution:** Already built-in (2 sec delay + stealth mode)

### Issue 3: Dynamic Content Not Loading
**Symptom:** Empty HTML or missing data  
**Cause:** React SPA needs more time to render  
**Solution:** 6-second wait already configured

### Issue 4: Stale CloudFront Cache
**Symptom:** Old/empty data served after deployment  
**Solution:** Always run cache invalidation after deployment

---

## 📊 Success Criteria

### Scraping Phase
- ✅ At least 95% of plans successfully scraped (136/143)
- ✅ All HTML files >200 KB (indicating full page load)
- ✅ No more than 7 plans with 404 errors
- ✅ Progress file shows completion

### Parsing Phase
- ✅ 100% of scraped HTML parsed into JSON
- ✅ Each plan has `premiums` object (may be empty for MA-only plans)
- ✅ Each plan has `benefits` object with 5+ sections
- ✅ Plan names extracted from title tags

### API Generation Phase
- ✅ `mock_api/AZ/` created with all files
- ✅ ZIP mappings cover 400+ Arizona ZIP codes
- ✅ County files created for all 16 counties
- ✅ Static API includes 400+ new ZIP endpoints

### Deployment Phase
- ✅ All files uploaded to S3
- ✅ Cache invalidated for AZ endpoints
- ✅ Sample ZIP endpoints return data
- ✅ Data structure matches MA/SC format

---

## 🧪 Testing Plan

### Test Sample ZIPs
```bash
# Phoenix (Maricopa County)
curl -s "https://medicare.purlpal-api.com/medicare/zip/85001.json"

# Tucson (Pima County)
curl -s "https://medicare.purlpal-api.com/medicare/zip/85701.json"

# Flagstaff (Coconino County)
curl -s "https://medicare.purlpal-api.com/medicare/zip/86001.json"

# Yuma (Yuma County)
curl -s "https://medicare.purlpal-api.com/medicare/zip/85364.json"
```

### Verify Data Structure
```bash
python3 << 'EOF'
import requests
import json

# Compare AZ with MA reference
az_url = "https://medicare.purlpal-api.com/medicare/zip/85001.json"
ma_url = "https://medicare.purlpal-api.com/medicare/zip/02108.json"

az_data = requests.get(az_url, timeout=10).json()
ma_data = requests.get(ma_url, timeout=10).json()

az_keys = set(az_data.keys())
ma_keys = set(ma_data.keys())

print(f"Structure match: {az_keys == ma_keys}")
print(f"AZ plan count: {az_data.get('plan_count')}")

if az_data.get('plans'):
    az_plan_keys = set(az_data['plans'][0].keys())
    ma_plan_keys = set(ma_data['plans'][0].keys())
    print(f"Plan structure match: {az_plan_keys == ma_plan_keys}")
EOF
```

---

## 📝 Checklist

### Pre-Scraping
- [ ] Copy and update `scrape_arizona.py`
- [ ] Copy and update `parse_az_raw_content.py`
- [ ] Create `raw_az_plans/` directory
- [ ] Verify `state_data/Arizona.json` exists (143 plans)
- [ ] Check existing progress (18 files already exist)

### Scraping
- [ ] Run `python3 scrape_arizona.py`
- [ ] Monitor progress every 10 plans
- [ ] Verify HTML files are being created
- [ ] Check for error messages
- [ ] Wait for completion (~20 min)

### Parsing
- [ ] Run `python3 parse_az_raw_content.py`
- [ ] Verify JSON files created in `scraped_json_all/`
- [ ] Check data quality (premiums, benefits present)
- [ ] Review parsing success rate

### API Building
- [ ] Run `python3 build_all_state_apis.py`
- [ ] Verify `mock_api/AZ/` created
- [ ] Check ZIP mappings exist
- [ ] Run `python3 build_static_api.py`
- [ ] Verify static API files generated

### Deployment
- [ ] Run `./deploy_medicare_api.sh`
- [ ] Monitor upload progress
- [ ] Run CloudFront cache invalidation
- [ ] Test sample ZIP endpoints
- [ ] Verify data structure consistency

### Documentation
- [ ] Create `85001_ENDPOINTS.md` (Phoenix example)
- [ ] Update `DEPLOYED_STATES_STATUS.md`
- [ ] Document any issues encountered
- [ ] Note success rate and findings

---

## 📈 Expected Timeline

| Phase | Duration | Task |
|-------|----------|------|
| Setup | 5 min | Create/modify scripts, prepare directories |
| Scraping | 20 min | Scrape 143 plans (125 new + verify 18 existing) |
| Parsing | 5 min | Parse HTML to JSON |
| API Gen | 10 min | Build mock_api + static API files |
| Deploy | 5 min | Upload to S3 + invalidate cache |
| Testing | 5 min | Verify endpoints work |
| **Total** | **50 min** | End-to-end Arizona deployment |

---

## 🎯 Deliverables

Upon completion, Arizona will have:
- ✅ 143 raw HTML files in `raw_az_plans/`
- ✅ 143 JSON files in `scraped_json_all/Arizona-*.json`
- ✅ `mock_api/AZ/` with full API structure
- ✅ 400+ ZIP endpoint files for Arizona ZIPs
- ✅ State-level API endpoints for AZ
- ✅ Live deployment at `medicare.purlpal-api.com`
- ✅ Documentation matching MA/SC format
- ✅ Consistent data structure with all other states

---

## 🚀 Ready to Execute

All prerequisites are met. Arizona scraping can begin immediately using the proven Massachusetts methodology.

**Next Command:**
```bash
python3 scrape_arizona.py
```
