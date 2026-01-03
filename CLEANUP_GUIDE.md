# Cleanup Guide

After verifying the reorganized structure works correctly, use this guide to remove original files from the root directory.

## ⚠️ Important: Verify First!

**DO NOT run cleanup until you've tested:**
1. API tests work: `./tests/test_medicare_api.sh`
2. Builders work: `python3 src/builders/build_static_api.py`
3. All your workflows function correctly

## What Will Be Removed

### Documentation Files (42 files)
These have been copied to `docs/` subdirectories and can be safely removed from root:

```bash
# API documentation
API_USER_GUIDE.md
API_REFERENCE.md
API_ARCHITECTURE.md
API_STATUS.md
API_SETUP_GUIDE.md
API_DEPLOYMENT.md
CHROME_EXTENSION_QUICK_START.md

# Deployment documentation
DEPLOYMENT_COMPLETE.md
DEPLOYMENT_COMPLETE_MD.md
DEPLOYMENT_GUIDE.md
DEPLOYMENT_INFO.md
DEPLOYMENT_PLAN_V2.md
DEPLOY_DATABASE_API.md
DEPLOY_MINIFIED_MD.md
DEPLOYED_STATES_STATUS.md
AWS_LAMBDA_SUMMARY.md
AWS_MIGRATION_PLAN.md

# Scraping documentation
SCRAPING_GUIDE.md
ALL_STATES_SCRAPING_PLAN.md
ARIZONA_SCRAPING_PLAN.md
ARKANSAS_SCRAPING_PLAN.md
FLORIDA_SCRAPING_PLAN.md
MA_SCRAPING_PLAN.md
RHODE_ISLAND_PLAN.md
SC_SCRAPING_COMPLETE.md
SC_DEPLOYMENT.md
SUCCESSFUL_SCRAPING_PROCESS.md
EC2_SELENIUM_SETUP.md

# Development & testing
TESTING_GUIDE.md
DATABASE_API_GUIDE.md

# Notes
NOTES_ZIP_MULTI_STATE.md
CORS_SECURITY_NOTES.md
CORS_SETUP.md
ZIP_COUNTY_MAPPING_NEEDS.md

# Reference/status docs
QUICK_REFERENCE.md
FILE_GUIDE.md
MINIFIED_ENDPOINT_GUIDE.md
S3_UPLOAD_GUIDE.md

# Example endpoints
02108_ENDPOINTS.md
29401_ENDPOINTS.md
85001_ENDPOINTS.md
```

### Python Scripts (72+ files)
These have been copied to `src/`, `tests/`, or `scripts/`:

**Scrapers** (moved to `src/scrapers/state_scrapers/` or archived):
- scrape_arizona.py, scrape_arkansas.py, scrape_florida.py, etc.
- scrape_all_plans.py, scrape_all_remaining.py, etc.

**Parsers** (moved to `src/scrapers/parsers/`):
- parse_ar_raw_content.py, parse_az_raw_content.py, etc.

**Builders** (moved to `src/builders/`):
- build_static_api.py, build_all_state_apis.py, etc.

**API Servers** (moved to `src/api/` or archived):
- api_server.py, api_server_v2.py, api_server_v3.py

**Deployment** (moved to `src/deploy/`):
- deploy_api.py, deploy_sc.py, etc.

**Tests** (moved to `tests/`):
- test_api.py, test_scraper.py, etc.

**Utilities** (moved to `scripts/`):
- analyze_all_states.py, verify_all_states.py, etc.

### Configuration Files
- openapi.yaml, openapi-compact.yaml → `config/`
- cors-config.json, parallel_config.json → `config/`
- chrome_extension_example.js → `config/`

### Data Files
- fips_to_county_name.json → `data/reference/`
- multi_state_zctas.json → `data/reference/`
- unified_zip_to_fips.json → `data/reference/`
- plan_county_mappings.json → `data/mappings/`
- zip_coverage_report.txt → `data/mappings/`

### Shell Scripts
- incremental_update.sh, update_api.sh → `scripts/`
- deploy_medicare_api.sh, deploy_lambda.sh → `src/deploy/`
- test_*.sh → `tests/`

## Manual Cleanup Steps

### Step 1: Create a Backup (Recommended)
```bash
# Create a backup of the entire repo before cleanup
cd ..
tar -czf medicare_overview_test_backup_$(date +%Y%m%d).tar.gz medicare_overview_test/
```

### Step 2: Test Everything
```bash
# Test API
./tests/test_medicare_api.sh

# Test comprehensive
python3 tests/test_api_comprehensive.py

# Test builder
python3 src/builders/build_static_api.py --help
```

### Step 3: Remove Documentation Files
```bash
# Remove all the markdown files from root (they're in docs/ now)
rm -f API_*.md DEPLOYMENT_*.md DEPLOY_*.md SCRAPING_*.md TESTING_GUIDE.md \
      DATABASE_API_GUIDE.md NOTES_*.md CORS_*.md ZIP_*.md QUICK_REFERENCE.md \
      FILE_GUIDE.md MINIFIED_*.md S3_*.md CHROME_*.md AWS_*.md SC_*.md \
      SUCCESSFUL_*.md EC2_*.md MA_*.md RHODE_*.md FLORIDA_*.md ARIZONA_*.md \
      ARKANSAS_*.md ALL_*.md 02108_ENDPOINTS.md 29401_ENDPOINTS.md 85001_ENDPOINTS.md
```

### Step 4: Remove Python Scripts
```bash
# Remove scrapers (now in src/scrapers/)
rm -f scrape_*.py

# Remove parsers (now in src/scrapers/parsers/)
rm -f parse_*.py

# Remove builders (now in src/builders/)
rm -f build_*.py

# Remove old API servers (now in src/api/ or archived)
rm -f api_server.py api_server_v2.py api_server_v3.py

# Remove deployment scripts (now in src/deploy/)
rm -f deploy_*.py

# Remove tests (now in tests/)
rm -f test_*.py

# Remove utilities (now in scripts/)
rm -f analyze_*.py check_*.py verify_*.py investigate_*.py review_*.py \
      create_*.py extract_*.py upload_*.py rename_*.py reprocess_*.py \
      minify_*.py parallel_scrape_config.py retry_*.py

# Remove old lambda function (archived)
rm -f lambda_function.py selenium_scraper.py
```

### Step 5: Remove Configuration Files
```bash
# Remove config files (now in config/)
rm -f openapi.yaml openapi-compact.yaml cors-config.json \
      parallel_config.json upload_metadata.json chrome_extension_example.js
```

### Step 6: Remove Data Files
```bash
# Remove reference data (now in data/reference/)
rm -f fips_to_county_name.json multi_state_zctas.json unified_zip_to_fips.json

# Remove mappings (now in data/mappings/)
rm -f plan_county_mappings.json zip_coverage_report.txt
```

### Step 7: Remove Shell Scripts
```bash
# Remove update scripts (now in scripts/)
rm -f incremental_update.sh update_api.sh

# Remove deployment scripts (now in src/deploy/)
rm -f deploy_medicare_api.sh deploy_lambda.sh deploy_to_aws.sh

# Remove test scripts (now in tests/)
rm -f test_*.sh

# Remove old start scripts (archived)
rm -f start_*.sh
```

## Automated Cleanup Script

See `cleanup_original_files.sh` for an automated script that removes all original files.

**Warning:** Only run after thorough testing!

## What to Keep in Root

After cleanup, your root directory should contain only:
- `README.md` - Main project README (updated)
- `CONTRIBUTING.md` - Contribution guide (new)
- `DIRECTORY_STRUCTURE.md` - Directory guide (new)
- `REORGANIZATION_PLAN.md` - Reorganization plan (new)
- `REORGANIZATION_SUMMARY.md` - Summary (new)
- `CLEANUP_GUIDE.md` - This file (new)
- `.gitignore` - Updated gitignore
- `.git/` - Git repository
- `docs/` - Organized documentation
- `src/` - Organized source code
- `tests/` - Test files
- `scripts/` - Utility scripts
- `lambda/` - AWS Lambda (unchanged)
- `database/` - Database scripts (unchanged)
- `data/` - Data files (organized)
- `config/` - Configuration files
- `archive/` - Deprecated files

Plus any data directories and files you need to keep:
- `scraped_data/`, `state_data/`, `output/`, etc.

## Verification After Cleanup

After cleanup, verify:
```bash
# Check directory structure
ls -la

# Test API
./tests/test_medicare_api.sh

# Test builder
python3 src/builders/build_static_api.py

# Run comprehensive tests
python3 tests/test_api_comprehensive.py
```

## Rollback if Needed

If something doesn't work after cleanup:
```bash
# Restore from backup
cd ..
tar -xzf medicare_overview_test_backup_YYYYMMDD.tar.gz
```

## Git Commit Recommended Structure

After cleanup and verification:
```bash
git add -A
git commit -m "Reorganize repository structure

- Organize 72 Python scripts into src/, tests/, scripts/
- Consolidate 42 markdown docs into docs/ hierarchy  
- Move config files to config/
- Move data files to data/ subdirectories
- Archive obsolete files
- Update README and create comprehensive guides
- Remove original files from root after verification"
```
