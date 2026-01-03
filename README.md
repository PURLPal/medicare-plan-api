# Medicare Plan Database API

**Production database-backed API** for looking up Medicare Advantage plans by ZIP code. Live with 51 states and 5,804 plans.

## Quick Start

### For Your Teammate (Chrome Extension Developer)

See **[docs/development/testing.md](docs/development/testing.md)** for complete beginner walkthrough.

**Run tests now:**
```bash
./tests/test_medicare_api.sh
```

### For End Users

**Production API:** https://medicare.purlpal-api.com/medicare/

```bash
# Get plans for any ZIP code
curl "https://medicare.purlpal-api.com/medicare/zip/02108.json" | jq '.'

# Filter MAPD plans only
curl "https://medicare.purlpal-api.com/medicare/zip/02108_MAPD.json" | jq '.'

# Get all states
curl "https://medicare.purlpal-api.com/medicare/states.json" | jq '.'
```

## API Endpoints

### Primary Endpoints
- `GET /medicare/states.json` - List all states
- `GET /medicare/zip/{ZIP}.json` - Get plans for ZIP code (full details)
- `GET /medicare/plan/{PLAN_ID}.json` - Get specific plan details
- `GET /medicare/state/{ST}/info.json` - State information
- `GET /medicare/state/{ST}/plans.json` - All plans in state

### Filtered Endpoints (Pre-filtered by category)
- `GET /medicare/zip/{ZIP}_MAPD.json` - Medicare Advantage + Drug plans only
- `GET /medicare/zip/{ZIP}_MA.json` - Medicare Advantage only
- `GET /medicare/zip/{ZIP}_PD.json` - Part D drug plans only

## Current Coverage

### States (51)
All 50 states + DC

### Data Statistics (Updated: Dec 31, 2025)
- **5,804 Medicare plans** across all states
- **39,298 ZIP codes** with coverage data
- **6,266 unique counties** (after duplicate consolidation)
- **98.59% ZIP code coverage** (38,743/39,298 ZIPs have plans)
- **Real-time database queries** (no static files)
- **Full plan details** including benefits, premiums, deductibles

### Plan Categories
- **MAPD** - Medicare Advantage with drug coverage (Part C + Part D)
- **MA** - Medicare Advantage only (Part C, no drug coverage)
- **PD** - Part D drug plans only

## Documentation

### 📂 New Repository Organization

This repository was reorganized in January 2026 for better navigation. See **[DIRECTORY_STRUCTURE.md](DIRECTORY_STRUCTURE.md)** for complete layout.

### For API Users
- **[docs/api/user-guide.md](docs/api/user-guide.md)** - 📘 **Start here!** User-friendly guide with examples
- **[docs/api/reference.md](docs/api/reference.md)** - Complete API endpoint reference
- **[docs/api/README.md](docs/api/README.md)** - API overview and quick reference
- **[config/openapi-compact.yaml](config/openapi-compact.yaml)** - Compact OpenAPI 3.0 spec (~150 lines, LLM-friendly)
- **[config/openapi.yaml](config/openapi.yaml)** - Full OpenAPI spec with examples (~450 lines)

### For Developers
- **[docs/development/testing.md](docs/development/testing.md)** - Testing guide and test scripts
- **[docs/development/database-guide.md](docs/development/database-guide.md)** - Technical architecture and database schema
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - How to contribute to this project

### For DevOps
- **[docs/deployment/README.md](docs/deployment/README.md)** - Production deployment documentation
- **[docs/deployment/database.md](docs/deployment/database.md)** - Database deployment guide
- **[docs/deployment/lambda.md](docs/deployment/lambda.md)** - AWS Lambda deployment

### For Data Collection
- **[docs/scraping/guide.md](docs/scraping/guide.md)** - General scraping guide
- **[docs/scraping/README.md](docs/scraping/README.md)** - All-states scraping plan
- **[docs/scraping/state-guides/](docs/scraping/state-guides/)** - State-specific guides

## Example Usage

### JavaScript (Chrome Extension)
```javascript
// Fetch plans for a ZIP code
fetch('https://medicare.purlpal-api.com/medicare/zip/03462.json')
  .then(response => response.json())
  .then(data => {
    // Filter MAPD plans with zero premium
    const freeMAPD = data.plans.filter(plan =>
      plan.category === 'MAPD' &&
      plan.premiums['Total monthly premium'] === '$0.00'
    );

    console.log(`Found ${freeMAPD.length} free MAPD plans`);
  });
```

### Bash (Command Line)
```bash
# Get all states
curl "https://medicare.purlpal-api.com/medicare/states.json" | jq '.'

# Get plans for ZIP 03462
curl "https://medicare.purlpal-api.com/medicare/zip/03462.json" | jq '.'

# Filter by category
curl "https://medicare.purlpal-api.com/medicare/zip/03462.json" | \
  jq '.plans | map(select(.category == "MAPD"))'

# Count plans by category
curl "https://medicare.purlpal-api.com/medicare/zip/03462.json" | jq '{
  total: (.plans | length),
  mapd: (.plans | map(select(.category == "MAPD")) | length),
  ma: (.plans | map(select(.category == "MA")) | length),
  pd: (.plans | map(select(.category == "PD")) | length)
}'
```

## Features

✅ **CORS enabled** - Works with Chrome extensions
✅ **Custom domain** - medicare.purlpal-api.com
✅ **Global CDN** - ~50ms latency worldwide via CloudFront
✅ **Full plan data** - All benefits, premiums, deductibles
✅ **Filter by category** - MAPD, MA, PD
✅ **No authentication** - Public API
✅ **No rate limits** - Use responsibly

## Architecture

- **AWS RDS PostgreSQL 15.8** - Source of truth database (db.t3.micro, 20GB)
- **AWS Lambda (Python 3.11)** - API layer with pg8000 driver
- **AWS API Gateway HTTP API** - RESTful interface
- **Route 53 + Custom Domain** - medicare.purlpal-api.com
- **Cost effective** - ~$15-25/month for all states

### Database-Backed Benefits
- ✅ **Real-time updates** - No need to regenerate 40K files
- ✅ **Dynamic queries** - Filter by category, state, county
- ✅ **Data integrity** - Single source of truth
- ✅ **Easier maintenance** - Update database, API updates automatically
- ✅ **Multi-county ZIP support** - Plans grouped by county

## Deployment & Updates

### Update Data (After Scraping)
```bash
# Load new data into database
python3 database/load_data_fast.py "host=medicare-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com dbname=medicare_plans user=medicare_admin password=..."
```
**Time:** 2-5 minutes (batch loading)

### Update Lambda Code
```bash
cd lambda
cp medicare_api.py package/
cd package
zip -r ../medicare-api.zip .
aws lambda update-function-code --function-name MedicareAPI --zip-file fileb://medicare-api.zip --profile silverman --region us-east-1
```
**Time:** 10-30 seconds

### No Cache Invalidation Needed
Database updates are reflected immediately - no CloudFront cache to invalidate!

## Development

### Scrape New States
```bash
# Use state-specific scrapers
python3 src/scrapers/state_scrapers/scrape_<state>.py
```

### Rebuild API Files
```bash
python3 src/builders/build_static_api.py
```

### Deploy to Production
```bash
./scripts/update_api.sh
```

### Test Locally
```bash
./tests/test_medicare_api.sh
```

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for detailed development workflow.

## Data Structure

Each plan includes:
- `plan_id` - Unique identifier
- `category` - MAPD, MA, or PD
- `plan_type` - HMO, PPO, PDP, etc.
- `plan_info` - Name, organization, type
- `premiums` - All premium details
- `deductibles` - Health and drug deductibles
- `maximum_out_of_pocket` - Cost limits
- `benefits` - Complete benefit breakdown
- `contact_info` - Plan address
- `drug_coverage` - Pharmacy and tier info
- `extra_benefits` - Additional benefits

## Performance

- **Latency:** 290-400ms average (warm requests with connection pooling)
- **Cold Start:** ~1.3s (first request after Lambda idle)
- **Availability:** 100% test success rate
- **Scalability:** Lambda auto-scaling + connection pooling
- **Cost:** ~$15-25/month for all states
- **Test Coverage:** Comprehensive test suite with configurable ZIP sampling

### Recent Performance Improvements (Jan 1, 2026)
- **85% faster:** Implemented connection pooling to reuse database connections
- **Before:** 4-5 seconds per request (fresh SSL connection each time)
- **After:** 290-400ms per request (connection reused across invocations)

## Monitoring

Check API status:
```bash
curl "https://medicare.purlpal-api.com/medicare/states.json" | jq '{
  states: .state_count,
  generated: .generated_at
}'
```

Check Lambda function status:
```bash
aws lambda get-function --function-name MedicareAPI \
  --profile silverman --region us-east-1 \
  --query 'Configuration.LastUpdateStatus' --output text
```

## Data Quality Fixes (Dec 31, 2025)

### Critical Issues Resolved

**1. Duplicate County Records (MAJOR FIX)**
- **Problem:** 2,977 duplicate county records (e.g., "Dallas County" vs "Dallas")
- **Impact:** ZIPs linked to one version, plans to another → 42% false "no plans" rate
- **Solution:** Consolidated duplicates, merged all ZIP-county and plan-county relationships
- **Result:** Coverage improved from 58% → **98.59%**

**2. Missing State Mappings**
- **Problem:** LA, CT, AK missing from plan_county_mappings.json
- **Impact:** 1,330 ZIPs had no plans despite plans existing in database
- **Solution:** Linked statewide PDP plans to all counties in each state
- **Result:** Louisiana (666 ZIPs), Connecticut (402 ZIPs), Alaska (262 ZIPs) now have coverage

### Current Coverage Reality
- **38,743 ZIPs with plans** (98.59%)
- **555 ZIPs with no plans** (1.41%) - mostly rural/remote areas
- Vermont (305 ZIPs) has no plans in database (not scraped)

## Troubleshooting

### Check API Status
```bash
curl "https://medicare.purlpal-api.com/medicare/states.json" | jq '{states: .state_count, plans: .total_plans}'
```

### Run Comprehensive Tests
```bash
# Test 5 ZIPs per state (default)
python3 tests/test_api_comprehensive.py

# Test 10 ZIPs per state
python3 tests/test_api_comprehensive.py 10
```

**Test Coverage:**
- Tests all three plan categories: MAPD, MA, and PD
- Verifies multi-county ZIP handling
- Validates category filtering endpoints
- Measures response times and success rates

### Check Database Connection
```bash
PGPASSWORD='...' psql -h medicare-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com -U medicare_admin -d medicare_plans -c "SELECT COUNT(*) FROM plans;"
```

## Migration Notes

### From S3/CloudFront to Database-Backed API
Migrated from static files to database in December 2025 because:
- ✅ **Real-time updates** - No need to regenerate 40K files for each data change
- ✅ **Dynamic queries** - Can filter, search, and aggregate in real-time
- ✅ **Data integrity** - Single source of truth eliminates sync issues
- ✅ **County-level granularity** - Proper multi-county ZIP support
- ✅ **Easier maintenance** - Update database, API reflects changes instantly

**Trade-off:** Slightly slower (520ms vs 50ms) but negligible for user experience

## License

Public domain - Medicare plan data is publicly available from Medicare.gov.

## Questions?

- **For testing:** See [docs/development/testing.md](docs/development/testing.md)
- **For API usage:** See [docs/api/user-guide.md](docs/api/user-guide.md)
- **For deployment:** See [docs/deployment/README.md](docs/deployment/README.md)
- **For contributing:** See [CONTRIBUTING.md](CONTRIBUTING.md)
- **For directory structure:** See [DIRECTORY_STRUCTURE.md](DIRECTORY_STRUCTURE.md)

## Quick Reference

**API URL:** https://medicare.purlpal-api.com/medicare/

**Test Script:** `./tests/test_medicare_api.sh`

**Update API:** `./scripts/incremental_update.sh`

**Full Rebuild:** `./scripts/update_api.sh`

**States:** All 50 + DC (51 total)

**Total Plans:** 5,804 plans

**Coverage:** 98.59% of ZIP codes
