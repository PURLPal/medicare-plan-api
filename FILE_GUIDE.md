# File Guide - What's What

## 🚀 For Your Teammate (Chrome Extension Developer)

### Start Here:
1. **`CHROME_EXTENSION_QUICK_START.md`** - Quick integration guide
2. **`chrome_extension_example.js`** - Complete working examples (400+ lines)
3. **`cors-config.json`** - CORS configuration (AllowOrigins: ["*"])

### Copy to Your Extension:
- `chrome_extension_example.js` - Copy the whole thing, update `API_BASE_URL`

## 🔧 For Deployment

### Run These:
1. **`deploy_lambda.sh`** - Deploy to AWS (run this first!)
2. **`test_api_curl.sh`** - Test all endpoints after deployment

### Configuration:
- **`cors-config.json`** - CORS settings (permanent file, not /tmp anymore!)
- **`lambda_function.py`** - The actual Lambda function

## 📊 Data Files (Bundled in Deployment)

```
mock_api/
├── AK/
│   ├── zip_to_county_multi.json   (142 ZIPs)
│   └── counties/                   (no county-specific plans)
├── NH/
│   ├── zip_to_county_multi.json   (241 ZIPs)
│   └── counties/                   (10 county files)
├── VT/
│   ├── zip_to_county_multi.json   (298 ZIPs)
│   └── counties/                   (6 county files)
└── WY/
    ├── zip_to_county_multi.json   (173 ZIPs)
    └── counties/                   (23 county files)
```

## 📚 Documentation

### Quick Reference:
- **`CHROME_EXTENSION_QUICK_START.md`** - For extension developers (your teammate!)
- **`AWS_LAMBDA_SUMMARY.md`** - Quick deployment summary
- **`FILE_GUIDE.md`** - This file

### Detailed Guides:
- **`DEPLOYMENT_GUIDE.md`** - Complete AWS deployment walkthrough
- **`API_ARCHITECTURE.md`** - How the caching system works
- **`CORS_SETUP.md`** - How CORS is configured (technical details)
- **`CORS_SECURITY_NOTES.md`** - Why AllowOrigins: ["*"] is OK here

## 🛠️ Build Scripts

- **`build_all_county_caches.py`** - Rebuild caches after scraping new plans
- **`build_zip_to_plans_mapping.py`** - Legacy (not used, county caches are better)

## 🧪 Testing

- **`test_api_curl.sh`** - Test all endpoints with curl
- **`test_api.py`** - Local Python testing (no server needed)
- **`lambda_function.py`** - Has built-in tests (run: `python3 lambda_function.py`)

## 📦 Scraping Scripts (Background Info)

These were used to get the plan data:
- `scrape_multithreaded.py` - Original scraper
- `scrape_balanced.py` - With anti-detection for IP ban
- `scrape_small_states.py` - Successfully scraped small states
- Various other scraping scripts...

## 🗂️ Data Source

- **`CY2026_Landscape_202511/CY2026_Landscape_202511.csv`** - Original Medicare plan data (6,581 plans nationwide)
- **`scraped_json_all/*.json`** - Individual plan details scraped from Medicare.gov (610 files)

## File Tree

```
medicare_overview_test/
│
├── 🎯 FOR CHROME EXTENSION DEV
│   ├── CHROME_EXTENSION_QUICK_START.md  ← START HERE
│   ├── chrome_extension_example.js       ← COPY THIS
│   └── cors-config.json                  ← CORS settings
│
├── 🚀 FOR DEPLOYMENT
│   ├── deploy_lambda.sh                  ← Run this to deploy
│   ├── lambda_function.py                ← The Lambda function
│   └── test_api_curl.sh                  ← Test after deploy
│
├── 📚 DOCUMENTATION
│   ├── FILE_GUIDE.md                     ← This file
│   ├── AWS_LAMBDA_SUMMARY.md             ← Quick reference
│   ├── DEPLOYMENT_GUIDE.md               ← Detailed deployment
│   ├── CORS_SETUP.md                     ← CORS technical details
│   ├── CORS_SECURITY_NOTES.md            ← Why "*" is OK
│   └── API_ARCHITECTURE.md               ← How caching works
│
├── 📊 DATA (bundled in deployment)
│   └── mock_api/
│       ├── AK/ (Alaska)
│       ├── NH/ (New Hampshire)
│       ├── VT/ (Vermont)
│       └── WY/ (Wyoming)
│
└── 🛠️ BUILD & TEST
    ├── build_all_county_caches.py        ← Rebuild caches
    ├── test_api.py                       ← Local testing
    └── scraping_progress.json            ← Scraping status
```

## What Gets Deployed to AWS?

When you run `deploy_lambda.sh`, it creates `lambda_package.zip` containing:

```
lambda_package/
├── lambda_function.py        (~10 KB)
└── mock_api/                 (~2 MB)
    ├── AK/
    ├── NH/
    ├── VT/
    └── WY/
```

**Total package**: ~2 MB
**Deployment time**: ~2 minutes
**Cost**: FREE (under free tier)

## Quick Command Reference

```bash
# Deploy to AWS
./deploy_lambda.sh

# Test locally
python3 lambda_function.py

# Test deployed API
./test_api_curl.sh https://your-url.lambda-url.us-east-1.on.aws

# Rebuild caches after scraping new data
python3 build_all_county_caches.py

# Check what's been scraped
ls -lh scraped_json_all/ | wc -l
```

## Questions?

- **Extension integration?** → `CHROME_EXTENSION_QUICK_START.md`
- **Deployment issues?** → `DEPLOYMENT_GUIDE.md`
- **CORS errors?** → `CORS_SETUP.md` (but you shouldn't have any!)
- **API usage?** → `AWS_LAMBDA_SUMMARY.md`
