# Directory Structure Guide

Complete guide to the Medicare Plan API repository organization.

## Overview

This repository follows a standard Python project structure with clear separation of concerns.

## Directory Layout

### `/docs/` - Documentation

All project documentation organized by topic.

#### `/docs/api/` - API Documentation
- `README.md` - API overview and quick reference
- `user-guide.md` - Complete user guide with examples
- `reference.md` - Full endpoint reference
- `architecture.md` - Technical architecture details
- `examples/` - Example usage and integrations
  - `chrome-extension.md` - Chrome extension integration
  - `boston-02108-endpoints.md` - Boston ZIP example
  - `charleston-29401-endpoints.md` - Charleston ZIP example
  - `phoenix-85001-endpoints.md` - Phoenix ZIP example

#### `/docs/deployment/` - Deployment Documentation
- `README.md` - Deployment overview (production setup)
- `database.md` - Database deployment guide
- `lambda.md` - AWS Lambda deployment
- `migration.md` - Migration from S3/CloudFront to database
- `api-deployment.md` - API Gateway deployment
- `status.md` - Deployment status and monitoring

#### `/docs/scraping/` - Scraping Documentation
- `README.md` - Scraping overview and all-states plan
- `guide.md` - General scraping guide
- `successful-process.md` - Proven scraping workflow
- `ec2-selenium.md` - EC2 Selenium setup
- `state-guides/` - State-specific scraping guides
  - `arizona.md`, `arkansas.md`, `florida.md`, etc.

#### `/docs/development/` - Development Documentation
- `testing.md` - Testing guide and procedures
- `database-guide.md` - Database schema and usage

#### `/docs/notes/` - Technical Notes
- `multi-state-zips.md` - Multi-state ZIP code handling
- `cors-security.md` - CORS configuration notes
- `county-mapping.md` - County mapping requirements

### `/src/` - Source Code

Production source code organized by function.

#### `/src/scrapers/` - Web Scraping Code
- `selenium_scraper.py` - Selenium-based scraper
- `state_scrapers/` - State-specific scrapers
  - Individual scraper for each state
- `parsers/` - HTML/content parsers
  - State-specific parsing logic

#### `/src/builders/` - API/Data Builders
- `build_static_api.py` - Main static API builder
- `build_all_state_apis.py` - Multi-state builder
- `build_zip_county_mapping.py` - ZIP to county mapping
- `build_county_caches.py` - County cache builder
- State-specific builders (Arkansas, New Jersey, etc.)

#### `/src/api/` - API Server
- `server.py` - API server (latest version)

#### `/src/deploy/` - Deployment Scripts
- `deploy_api.py` - API deployment script
- `deploy_medicare_api.sh` - Medicare API deployment shell script
- `deploy_lambda.sh` - Lambda deployment
- `check_deployment.py` - Deployment status checker

#### `/src/utils/` - Utilities
Common utility functions (to be populated as needed)

### `/tests/` - Test Files

All test scripts and test utilities.

- `test_api_comprehensive.py` - Comprehensive API tests
- `test_all_states_live.py` - Live state tests
- `test_medicare_api.sh` - Main API test script
- `test_api.py`, `test_api_curl.sh`, etc. - Various API tests
- `test_scraper*.py` - Scraper tests
- `test_parser.py` - Parser tests
- State-specific tests

### `/scripts/` - Utility Scripts

Standalone utility scripts for analysis, verification, and maintenance.

- `analyze_all_states.py` - State data analysis
- `verify_all_states.py` - Data verification
- `scraping_stats.py` - Scraping statistics
- `investigate_api.py` - API investigation tools
- `review_status.py` - Status review
- `upload_*.py` - Upload utilities
- `extract_*.py` - Data extraction tools
- `minify_*.py` - Minification tools

### `/lambda/` - AWS Lambda Deployment

AWS Lambda function code and deployment artifacts.

- `package/` - Lambda deployment package
- `medicare_api.py` - Lambda function handler
- Various deployment files

### `/database/` - Database Scripts

Database schema, migrations, and data loading scripts.

- `schema.sql` - Database schema
- `load_data_fast.py` - Fast data loader
- `fix_duplicate_counties.py` - Data quality fixes
- `deploy_rds.sh` - RDS deployment
- SQL migration scripts

### `/data/` - Data Files

Organized data storage.

#### `/data/reference/` - Reference Data
- `fips_to_county_name.json` - FIPS to county mapping
- `multi_state_zctas.json` - Multi-state ZIP codes
- `unified_zip_to_fips.json` - ZIP to FIPS mapping

#### `/data/mappings/` - Generated Mappings
- `plan_county_mappings.json` - Plan to county mappings
- `zip_coverage_report.txt` - Coverage analysis

#### `/data/scraped/` - Scraped Data
Raw scraped plan data (from `scraped_data/` directory)

#### `/data/state_data/` - State-Specific Data
State-level data files

#### `/data/output/` - Build Outputs
Generated API files and build artifacts

### `/config/` - Configuration Files

Project configuration files.

- `openapi.yaml` - Full OpenAPI specification
- `openapi-compact.yaml` - Compact OpenAPI spec
- `cors-config.json` - CORS configuration
- `parallel_config.json` - Parallel scraping config
- `upload_metadata.json` - Upload metadata
- `chrome_extension_example.js` - Chrome extension example

### `/archive/` - Archive

Deprecated and obsolete files preserved for reference.

#### `/archive/old_scrapers/` - Old Scraping Scripts
Historical scraping scripts and batch processors

#### `/archive/old_api_versions/` - Old API Versions
Previous API server versions

#### `/archive/deprecated_docs/` - Deprecated Documentation
Outdated documentation files

## File Naming Conventions

- **Scrapers**: `scrape_<state>.py` or `scrape_<specific_purpose>.py`
- **Parsers**: `parse_<state>_raw_content.py` or `<state>_parser.py`
- **Builders**: `build_<what_it_builds>.py`
- **Tests**: `test_<what_it_tests>.py`
- **Documentation**: `kebab-case.md` for multi-word names

## Migration Notes

This structure was reorganized in January 2026 to:
- Separate concerns clearly (scraping, building, testing, deployment)
- Consolidate scattered documentation
- Archive obsolete files while preserving history
- Follow Python project best practices
- Improve navigability for new contributors

Original files remain in place temporarily for safety. Once verified, they can be removed.

## Quick Navigation

- **Using the API?** → Start with `docs/api/user-guide.md`
- **Deploying?** → See `docs/deployment/README.md`
- **Scraping data?** → Read `docs/scraping/guide.md`
- **Testing?** → Check `docs/development/testing.md`
- **Contributing?** → See `CONTRIBUTING.md`
