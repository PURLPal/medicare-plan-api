# API Setup Guide for All States

## What You Need for Each State API

### 1. **Scraped Plan Data** ✅ (You have this for 13 states!)
- JSON files in `scraped_json_all/` with full plan details
- Example: `Hawaii-H2406_044_0.json`

### 2. **ZIP Code Mapping**
For each state, you need a ZIP to county/region mapping file:
```json
// For regular states (with counties):
{
  "zip": "03256",
  "multi_county": true,
  "counties": [
    {"fips": "33001", "name": "Belknap", "percentage": 98.5},
    {"fips": "33009", "name": "Grafton", "percentage": 1.5}
  ],
  "primary_county": {"fips": "33001", "name": "Belknap"}
}

// For DC/Guam (no counties - all ZIPs get all plans):
{
  "zip": "20001",
  "region": "District of Columbia",
  "all_plans": true
}
```

### 3. **County/Region Caches**
Organized plan data by geographic area:
```json
{
  "county": "Belknap",
  "fips": "33001",
  "state": "NH",
  "plan_count": 28,
  "scraped_details_available": 28,
  "plans": [
    {
      "summary": {
        "contract_plan_segment_id": "H2406_044_0",
        "plan_name": "AARP Medicare Advantage",
        "plan_type": "PPO",
        "organization": "UnitedHealthcare"
      },
      "details": { /* full scraped data */ },
      "has_scraped_details": true
    }
  ]
}
```

## Special Cases: DC, Guam, Territories

### DC ZIP Code Ranges:
- 20001–20098
- 20201–20599  
- 56901–56999

### Guam ZIP Codes:
- 96910, 96913, 96915, 96916, 96917, 96919, 96921, 96923, 96928, 96929, 96931, 96932

### Strategy for Non-County Territories:
Since DC/Guam don't have counties, **all plans are available to all ZIP codes** in the region.

## What's Already Built:
- ✅ NH API (working)
- ✅ VT, AK, WY mock data (partial)

## What You Have Scraped:
✅ **13 Complete States:**
1. Alaska (9 plans)
2. Delaware (47 plans)
3. District of Columbia (30 plans)
4. Guam (1 plan)
5. Hawaii (52 plans)
6. Montana (43 plans)
7. New Hampshire (28 plans)
8. North Dakota (40 plans)
9. Northern Mariana Islands (1 plan)
10. Rhode Island (34 plans)
11. South Dakota (38 plans)
12. Vermont (14 plans)
13. Wyoming (25 plans)

## Build Process for Each State:

### Step 1: Get ZIP to County Mapping
**Sources:**
- HUD USPS ZIP to County file: https://www.huduser.gov/portal/datasets/usps_crosswalk.html
- Census Bureau data
- Medicare.gov plan availability data (already in CY2026 CSV)

### Step 2: Build County Caches
Script needed: `build_county_caches_v2.py` (I'll create this)
- Read scraped JSON files
- Read CY2026 CSV for county assignments
- Organize by county
- Create cache files

### Step 3: Create ZIP to Plans Mapping
For fast lookups without needing county logic

### Step 4: Update API Server
Make it state-agnostic with dynamic routing

## Next Steps to Enable All 13 States:

1. ✅ Scrape plans (DONE for 13 states!)
2. ⏳ Download ZIP-County mapping data
3. ⏳ Build county caches for each state
4. ⏳ Update API to support multiple states
5. ⏳ Handle DC/Guam special case

I can automate steps 3-5 for you!
