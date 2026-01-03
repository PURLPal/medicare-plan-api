# Rhode Island Medicare Plans - Completion Plan

**State:** Rhode Island (RI)  
**Status:** 33/34 plans scraped, needs mock_api rebuild  
**Priority:** High (smallest state, quick completion)  
**Estimated Time:** 10-15 minutes

---

## Current Situation

### What We Have ✅
- **State Data File:** `state_data/Rhode_Island.json` - 34 plans
- **Scraped JSON Files:** 33/34 files in `scraped_json_all/Rhode_Island-*.json`
- **Data Quality:** 100% (33/33 files have complete data)
- **Raw HTML:** Likely exists in `raw_ri_plans/` if scraped previously

### What's Missing ❌
1. **Missing Plan:** `H3113_010_0` (1 plan needs scraping)
2. **Mock API:** `mock_api/Rhode_Island/` directory doesn't exist
3. **Live Endpoints:** No RI data in production

### Root Cause
Rhode Island data was scraped but never went through the `build_all_state_apis.py` process, so the mock_api structure was never created. The API build script considers a state "complete" only if all plans are scraped AND the mock_api exists.

---

## Phase 1: Scrape Missing Plan (5 min)

### Objectives
- Scrape the missing plan `H3113_010_0`
- Verify all 34 plans are now complete

### Steps
1. Verify existing scraper scripts work for RI
2. Scrape the single missing plan
3. Parse the raw HTML to JSON
4. Verify data quality

### Success Criteria
- ✅ 34/34 RI plans in `scraped_json_all/`
- ✅ 100% data quality maintained
- ✅ All files have premiums and/or benefits data

---

## Phase 2: Build Mock API (2 min)

### Objectives
- Generate `mock_api/Rhode_Island/` structure
- Create county-level JSON files
- Build ZIP-to-plans mappings

### Steps
1. Run `python3 build_all_state_apis.py`
2. Verify `mock_api/Rhode_Island/` exists
3. Verify county files created
4. Check ZIP mappings

### Success Criteria
- ✅ `mock_api/Rhode_Island/counties/*.json` exists
- ✅ All 34 plans mapped to counties
- ✅ Rhode Island included in complete states list

---

## Phase 3: Rebuild & Deploy API (5 min)

### Objectives
- Regenerate all static API files (including RI)
- Deploy to S3
- Verify live endpoints

### Steps
1. Run `python3 build_static_api.py`
2. Sync to S3: `aws s3 sync static_api/ s3://purlpal-medicare-api/`
3. Invalidate CloudFront cache for RI
4. Test live endpoints

### Success Criteria
- ✅ RI ZIP endpoints return plans (e.g., 02903 Providence)
- ✅ 29 states in states.json shows RI with 34 plans
- ✅ All RI endpoints accessible

---

## Rhode Island Quick Facts

### Geography
- **Counties:** 5 (Bristol, Kent, Newport, Providence, Washington)
- **Major Cities:** Providence, Warwick, Cranston, Pawtucket
- **Population:** ~1.1 million (smallest state)
- **ZIP Codes:** ~70 active ZIPs

### Medicare Market
- **Total Plans:** 34 Medicare Advantage plans
- **Market:** Small but competitive market
- **Carriers:** Primarily Aetna, UnitedHealthcare, Blue Cross
- **Sample Plans:** 
  - Most plans cover "All Counties"
  - Mix of HMO, PPO, and PFFS plans
  - Strong prescription drug coverage

### Test ZIPs
```
02903 - Providence (capital)
02860 - Pawtucket
02908 - Providence
02886 - Warwick
02840 - Newport
```

---

## Technical Details

### File Structure
```
state_data/Rhode_Island.json          # 34 plans ✅
scraped_json_all/Rhode_Island-*.json  # 33/34 files ✅
raw_ri_plans/*.html                   # Raw HTML (if exists)
mock_api/Rhode_Island/                # NEEDS CREATION ❌
```

### Missing Plan Details
- **Plan ID:** H3113_010_0
- **Likely Carrier:** Based on H3113 contract number, likely CVS Health/Aetna
- **Status:** Listed in state_data but not scraped

### Data Quality
Current scraped plans show:
- 100% have premiums data
- 100% have benefits data
- Standard Medicare Advantage structure
- No parsing issues detected

---

## Comparison with Other States

| State | Plans | Status | Time to Complete |
|-------|-------|--------|------------------|
| Rhode Island | 34 | 97% complete | 10-15 min |
| Vermont | 14 | ✅ Complete | N/A |
| Delaware | 47 | ✅ Complete | N/A |
| New Hampshire | 30 | ✅ Complete | N/A |

Rhode Island is the **4th smallest** state by plan count, making it an ideal candidate for quick completion.

---

## Estimated Timeline

| Phase | Task | Time | Total |
|-------|------|------|-------|
| 1 | Scrape missing plan H3113_010_0 | 3 min | 3 min |
| 1 | Parse to JSON | 1 min | 4 min |
| 1 | Verify quality | 1 min | 5 min |
| 2 | Build mock_api | 2 min | 7 min |
| 3 | Rebuild static API | 2 min | 9 min |
| 3 | Deploy to S3 | 3 min | 12 min |
| 3 | Verify endpoints | 1 min | 13 min |

**Total Estimated Time:** 10-15 minutes

---

## Success Metrics

### Completion Criteria
1. ✅ All 34 RI plans scraped and parsed
2. ✅ mock_api/Rhode_Island/ structure created
3. ✅ 70+ RI ZIP endpoints live and returning data
4. ✅ States.json includes RI with accurate counts
5. ✅ 100% data quality maintained

### Verification Tests
```bash
# Test Providence
curl https://medicare.purlpal-api.com/medicare/zip/02903.json

# Test Pawtucket
curl https://medicare.purlpal-api.com/medicare/zip/02860.json

# Test Newport
curl https://medicare.purlpal-api.com/medicare/zip/02840.json

# Verify states.json
curl https://medicare.purlpal-api.com/medicare/states.json | jq '.states[] | select(.abbreviation=="RI")'
```

Expected: Each ZIP should return plans with RI as primary_state

---

## Risk Assessment

### Low Risk ✅
- Only 1 plan to scrape
- Proven scraping methodology
- Small state = fast completion
- No complex geography

### Potential Issues
1. **Missing plan might be discontinued** - Check Medicare.gov first
2. **Raw HTML might not exist** - May need fresh scrape
3. **County mappings** - Verify all 5 counties covered

### Mitigation
- If H3113_010_0 is invalid, document and proceed with 33 plans
- Use existing scraper scripts (proven for FL, AZ, MA)
- CMS Landscape file has county mappings

---

## Next Steps After RI

With Rhode Island complete, we'll have:
- ✅ **29 states fully deployed**
- ✅ **2,898 total plans** (2,864 + 34)
- ✅ **Complete New England coverage** (MA, CT, ME, VT, NH, RI)
- ✅ **Smallest gaps closed**

Recommended next targets:
1. **Wyoming (26 plans)** - Another small, quick state
2. **Montana (45 plans)** - Already deployed but verify
3. **Large states:** TX, PA, OH, IL

---

## Notes

- Rhode Island is the perfect "cleanup" project before tackling larger states
- Completing RI gives us 100% New England region coverage
- The infrastructure is already in place; just need to fill the gap
- This validates our ability to quickly onboard small states

---

**Ready to Execute:** All prerequisites met, methodology proven, low risk.
