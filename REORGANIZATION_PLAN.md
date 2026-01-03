# Repository Reorganization Plan

## Objective
Organize the Medicare Plan API repository into a clear, maintainable structure with logical groupings and consolidated documentation.

## Current Problems
- 72 Python scripts in root directory (difficult to navigate)
- 42 markdown files in root directory (documentation scattered)
- Build scripts mixed with scraping scripts mixed with test scripts
- Duplicate/obsolete documentation files
- Large data files not properly organized
- No clear entry point for new contributors

## Proposed Directory Structure

```
medicare-plan-api/
├── README.md                          # Main entry point (updated)
├── CONTRIBUTING.md                    # New: How to contribute
├── CHANGELOG.md                       # New: Version history
├── .gitignore                         # Updated
│
├── docs/                              # All documentation consolidated
│   ├── api/                           # API documentation
│   │   ├── README.md                  # API overview
│   │   ├── user-guide.md             # From API_USER_GUIDE.md
│   │   ├── reference.md              # From API_REFERENCE.md
│   │   ├── architecture.md           # From API_ARCHITECTURE.md
│   │   └── examples/                 # Example usage
│   │       ├── chrome-extension.md   # From CHROME_EXTENSION_QUICK_START.md
│   │       ├── zip-endpoints.md      # From 02108_ENDPOINTS.md, etc.
│   │       └── sample-queries.md
│   ├── deployment/                    # Deployment docs
│   │   ├── README.md                 # Deployment overview
│   │   ├── aws-setup.md              # From AWS_LAMBDA_SUMMARY.md
│   │   ├── database.md               # From DEPLOY_DATABASE_API.md
│   │   ├── lambda.md                 # Lambda deployment
│   │   ├── cloudfront.md             # CloudFront/S3 (legacy)
│   │   └── migration.md              # From AWS_MIGRATION_PLAN.md
│   ├── scraping/                      # Scraping documentation
│   │   ├── README.md                 # Scraping overview
│   │   ├── guide.md                  # From SCRAPING_GUIDE.md
│   │   ├── state-guides/             # State-specific guides
│   │   │   ├── arizona.md
│   │   │   ├── arkansas.md
│   │   │   ├── florida.md
│   │   │   └── ...
│   │   └── ec2-selenium.md           # From EC2_SELENIUM_SETUP.md
│   ├── development/                   # Development guides
│   │   ├── testing.md                # From TESTING_GUIDE.md
│   │   ├── data-structure.md         # Data models and schema
│   │   └── troubleshooting.md
│   └── notes/                         # Technical notes
│       ├── multi-state-zips.md       # From NOTES_ZIP_MULTI_STATE.md
│       ├── cors-security.md          # From CORS_SECURITY_NOTES.md
│       └── county-mapping.md         # From ZIP_COUNTY_MAPPING_NEEDS.md
│
├── src/                               # Source code organized by function
│   ├── scrapers/                      # Web scraping scripts
│   │   ├── __init__.py
│   │   ├── base_scraper.py           # Common scraping logic
│   │   ├── selenium_scraper.py       # From selenium_scraper.py
│   │   ├── state_scrapers/           # State-specific scrapers
│   │   │   ├── __init__.py
│   │   │   ├── arizona.py
│   │   │   ├── arkansas.py
│   │   │   ├── florida.py
│   │   │   └── ...
│   │   └── parsers/                  # HTML/content parsers
│   │       ├── __init__.py
│   │       ├── ar_parser.py          # From parse_ar_raw_content.py
│   │       ├── az_parser.py
│   │       └── ...
│   │
│   ├── builders/                      # API/data builders
│   │   ├── __init__.py
│   │   ├── static_api_builder.py     # From build_static_api.py
│   │   ├── state_api_builder.py      # From build_all_state_apis.py
│   │   ├── zip_mapping_builder.py    # From build_zip_county_mapping.py
│   │   └── county_cache_builder.py   # From build_county_caches.py
│   │
│   ├── api/                           # API server code
│   │   ├── __init__.py
│   │   ├── server.py                 # From api_server_v3.py (latest)
│   │   └── routes.py
│   │
│   ├── deploy/                        # Deployment scripts
│   │   ├── __init__.py
│   │   ├── deploy_api.py             # From deploy_api.py
│   │   ├── deploy_medicare_api.sh    # Shell deployment script
│   │   └── check_deployment.py       # From check_deployment_status.py
│   │
│   └── utils/                         # Utility functions
│       ├── __init__.py
│       ├── data_validation.py
│       └── file_helpers.py
│
├── scripts/                           # Standalone utility scripts
│   ├── analyze_all_states.py
│   ├── create_histogram.py
│   ├── investigate_api.py
│   ├── review_status.py
│   └── scraping_stats.py
│
├── tests/                             # All test files
│   ├── __init__.py
│   ├── test_api.py                   # From test_api_comprehensive.py
│   ├── test_scrapers.py              # From test_scraper_v2.py
│   ├── test_parsers.py               # From test_parser.py
│   ├── test_massachusetts.py
│   └── test_all_states_live.py
│
├── lambda/                            # AWS Lambda deployment (keep as-is)
│   ├── package/
│   ├── medicare_api.py
│   └── ...
│
├── database/                          # Database scripts (keep structure)
│   ├── schema.sql
│   ├── load_data_fast.py
│   ├── fix_duplicate_counties.py
│   └── ...
│
├── data/                              # Data files organized
│   ├── reference/                     # Reference data
│   │   ├── fips_to_county_name.json
│   │   ├── multi_state_zctas.json
│   │   └── unified_zip_to_fips.json
│   ├── mappings/                      # Generated mappings
│   │   ├── plan_county_mappings.json
│   │   └── zip_coverage_report.txt
│   ├── scraped/                       # Scraped plan data
│   │   └── ...                       # From scraped_data/
│   ├── state_data/                    # State-specific data
│   │   └── ...                       # From state_data/
│   └── output/                        # Build outputs
│       └── ...                       # From output/
│
├── config/                            # Configuration files
│   ├── openapi.yaml
│   ├── openapi-compact.yaml
│   ├── cors-config.json
│   ├── parallel_config.json
│   └── upload_metadata.json
│
└── archive/                           # Obsolete/deprecated files
    ├── old_scrapers/
    ├── old_api_versions/
    └── deprecated_docs/
```

## Migration Steps

### Phase 1: Create New Directory Structure
1. Create all new directories
2. Keep original files in place (safety)

### Phase 2: Consolidate Documentation (42 files → organized structure)
**API Documentation:**
- API_USER_GUIDE.md → docs/api/user-guide.md
- API_REFERENCE.md → docs/api/reference.md
- API_ARCHITECTURE.md → docs/api/architecture.md
- CHROME_EXTENSION_QUICK_START.md → docs/api/examples/chrome-extension.md
- 02108_ENDPOINTS.md, 29401_ENDPOINTS.md, 85001_ENDPOINTS.md → docs/api/examples/

**Deployment Documentation:**
- DEPLOYMENT_COMPLETE.md → docs/deployment/README.md (primary)
- API_DEPLOYMENT.md → docs/deployment/README.md (merge)
- DEPLOY_DATABASE_API.md → docs/deployment/database.md
- AWS_LAMBDA_SUMMARY.md → docs/deployment/lambda.md
- AWS_MIGRATION_PLAN.md → docs/deployment/migration.md
- DEPLOYMENT_GUIDE.md, DEPLOYMENT_INFO.md, DEPLOYMENT_PLAN_V2.md → Consolidate or archive

**Scraping Documentation:**
- SCRAPING_GUIDE.md → docs/scraping/guide.md
- ALL_STATES_SCRAPING_PLAN.md → docs/scraping/README.md
- ARIZONA_SCRAPING_PLAN.md → docs/scraping/state-guides/arizona.md
- ARKANSAS_SCRAPING_PLAN.md → docs/scraping/state-guides/arkansas.md
- FLORIDA_SCRAPING_PLAN.md → docs/scraping/state-guides/florida.md
- EC2_SELENIUM_SETUP.md → docs/scraping/ec2-selenium.md
- SUCCESSFUL_SCRAPING_PROCESS.md → docs/scraping/guide.md (merge)

**Status/Reference Docs:**
- QUICK_REFERENCE.md → Merge into main README.md
- API_STATUS.md → Merge into docs/api/README.md
- DEPLOYED_STATES_STATUS.md → docs/deployment/status.md
- FILE_GUIDE.md → Update for new structure

**Notes:**
- NOTES_ZIP_MULTI_STATE.md → docs/notes/multi-state-zips.md
- CORS_SECURITY_NOTES.md → docs/notes/cors-security.md
- ZIP_COUNTY_MAPPING_NEEDS.md → docs/notes/county-mapping.md

**Obsolete (Archive):**
- DEPLOYMENT_COMPLETE_MD.md (duplicate)
- DEPLOY_MINIFIED_MD.md (old minification approach)
- MINIFIED_ENDPOINT_GUIDE.md (old approach)
- S3_UPLOAD_GUIDE.md (superseded by database approach)
- CORS_SETUP.md (covered in deployment docs)
- API_SETUP_GUIDE.md (covered in deployment docs)

### Phase 3: Organize Python Scripts (72 files → organized structure)

**Scrapers (30+ files) → src/scrapers/**
- scrape_*.py files → src/scrapers/state_scrapers/
- selenium_scraper.py → src/scrapers/selenium_scraper.py
- parse_*_raw_content.py → src/scrapers/parsers/

**Builders (15+ files) → src/builders/**
- build_static_api.py → src/builders/static_api_builder.py
- build_*_standard.py → src/builders/
- build_zip_*.py → src/builders/

**API Servers → src/api/**
- api_server_v3.py → src/api/server.py (keep latest only)
- api_server.py, api_server_v2.py → archive/

**Deployment → src/deploy/**
- deploy_*.py → src/deploy/
- deploy_*.sh → src/deploy/

**Tests → tests/**
- test_*.py → tests/
- test_*.sh → tests/

**Utilities → scripts/**
- analyze_*.py → scripts/
- check_*.py → scripts/
- investigate_*.py → scripts/
- verify_*.py → scripts/
- upload_*.py → scripts/

### Phase 4: Organize Data Files
- Move scraped_data/ → data/scraped/
- Move state_data/ → data/state_data/
- Move output/ → data/output/
- Move zip_county_data/ → data/state_data/ (consolidate)
- Move reference JSON files → data/reference/

### Phase 5: Update Configuration
- Move *.json, *.yaml config files → config/
- Update .gitignore for new structure
- Update shell scripts with new paths

### Phase 6: Update Main README
- Clear project overview
- Quick start guide
- Directory structure explanation
- Links to organized docs
- Contribution guidelines

### Phase 7: Create New Documents
- CONTRIBUTING.md - How to contribute
- CHANGELOG.md - Version history
- docs/api/README.md - API overview hub
- docs/deployment/README.md - Deployment overview hub
- docs/scraping/README.md - Scraping overview hub

## Benefits

1. **Easier Navigation**: Clear separation of concerns
2. **Better Onboarding**: New contributors can find what they need
3. **Reduced Clutter**: 72 scripts → organized into ~6 directories
4. **Consolidated Docs**: 42 markdown files → logical hierarchy
5. **Maintainability**: Related files grouped together
6. **Professional Structure**: Standard Python project layout
7. **Preserved History**: Archive old files, don't delete

## Safety Measures

1. Create new structure alongside existing files first
2. Copy files to new locations (don't move yet)
3. Update imports and references
4. Test thoroughly
5. Only after verification, clean up old files
6. Git commit at each phase

## Timeline

- **Phase 1**: Create directories (5 minutes)
- **Phase 2**: Consolidate docs (30-45 minutes)
- **Phase 3**: Organize scripts (45-60 minutes)
- **Phase 4**: Organize data (15 minutes)
- **Phase 5**: Update configs (15 minutes)
- **Phase 6**: Update README (20 minutes)
- **Phase 7**: New documents (30 minutes)

**Total**: ~3-4 hours of careful reorganization

## Next Steps

1. Review and approve this plan
2. Create backup/branch for safety
3. Execute phases sequentially
4. Test after each phase
5. Update all documentation references
6. Commit changes with clear messages
