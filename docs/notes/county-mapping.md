# ZIP-County Mapping Requirements for API

## 📋 States Needing ZIP-County Mapping

### **10 States with Scraped Data Need Mapping:**

1. **Alaska** (9 plans)
2. **Delaware** (47 plans)
3. **Hawaii** (52 plans)
4. **Montana** (43 plans)
5. **North Dakota** (40 plans)
6. **Rhode Island** (34 plans)
7. **South Dakota** (38 plans)
8. **Vermont** (14 plans)
9. **Wyoming** (25 plans)
10. **Northern Mariana Islands** (1 plan) - Needs ZIP list, not county mapping

**Total:** 303 plans ready for API once mapping is added

## ✅ States Already with API Infrastructure

- **New Hampshire** (28 plans) - Full API working
- **District of Columbia** (30 plans) - Region API (no counties)
- **Guam** (1 plan) - Region API (no counties)

## 📥 Where to Get ZIP-County Mapping

### **HUD USPS ZIP Code Crosswalk Files**
**URL:** https://www.huduser.gov/portal/datasets/usps_crosswalk.html

**What You Get:**
- ZIP to County relationships for all US states
- FIPS codes for counties
- Residential/Business/Other ratios (for multi-county ZIPs)
- Updated quarterly

**File Format:**
```csv
ZIP,COUNTY,RES_RATIO,BUS_RATIO,OTH_RATIO,TOT_RATIO
96701,15001,100,100,100,100
96703,15001,100,100,100,100
```

### **Alternative: Census Bureau**
**URL:** https://www.census.gov/geographies/reference-files/time-series/geo/relationship-files.html

## 🔧 What the Build Script Will Do

I can create `build_all_state_apis.py` that will:

1. **Read HUD ZIP-County file** → Map ZIPs to counties with percentages
2. **Read CY2026 CSV** → Know which plans are in which counties
3. **Read scraped JSON files** → Get full plan details
4. **Build county caches** → Organize plans by county
5. **Create ZIP mappings** → Fast ZIP → Plans lookups
6. **Generate API structure** → Ready for api_server_v2.py

## 📊 Special Cases Already Handled

### **Territories (No Counties):**
- ✅ **DC** - 596 ZIPs, all get same 30 plans
- ✅ **Guam** - 12 ZIPs, all get same 1 plan
- ⏳ **Northern Mariana Islands** - Need ZIP list (likely 5-10 ZIPs)
- ⏳ **Virgin Islands** - Need ZIP list (00801-00851 range)
- ⏳ **American Samoa** - Need ZIP list (96799)

### **Multi-County ZIPs:**
Already handled! Will show:
- Primary county (highest percentage)
- All counties with percentages
- Plans from all applicable counties

## 🎯 Next Steps

### **Option A: Quick Setup (30 minutes)**
1. Download HUD ZIP-County file
2. I create the build script
3. Run script → Generates APIs for all 10 states
4. Test with api_server_v2.py

### **Option B: Progressive Build**
Build APIs as you complete each state's scraping

### **Option C: Priority States**
Build APIs for high-value states first:
- Hawaii (52 plans) - Tourist destination
- Delaware (47 plans)
- Montana (43 plans)

## 💡 What You'll Get

After building, each state will have:

```
mock_api/
├── HI/
│   ├── api_info.json              # State metadata
│   ├── counties/
│   │   ├── Hawaii.json            # Plans for Hawaii County
│   │   ├── Honolulu.json          # Plans for Honolulu County
│   │   ├── Maui.json              # Plans for Maui County
│   │   └── Kauai.json             # Plans for Kauai County
│   ├── zip_to_county_multi.json   # ZIP → County mapping
│   └── zip_to_plans.json          # Fast ZIP → Plans lookup
```

Then you can query:
```bash
curl http://localhost:5000/api/HI/96701  # Honolulu ZIP
curl http://localhost:5000/api/HI/plans  # All Hawaii plans
```

## 📈 Impact

**Current API Coverage:**
- 3 states (NH, DC, GU) = 59 plans

**After ZIP-County Mapping:**
- 13 states = 362 plans (6x increase!)

**After Next Scraping Batch:**
- 18 states = 548 plans (9x increase!)

Ready to download the ZIP-County file and build the APIs?
