# Medicare Plan Lookup API - Architecture

## Overview
Hybrid caching approach: pre-compute county caches, serve by ZIP code

## Data Structure

### 1. ZIP to County Mapping
**File**: `mock_api/NH/zip_to_county_multi.json`
- 241 ZIP codes for New Hampshire
- 47 multi-county ZIPs (user must choose)
- 194 single-county ZIPs

### 2. County Caches (Pre-computed)
**Directory**: `mock_api/NH/counties/`
- 10 files (one per county)
- Each contains all plans for that county
- Plans include both CSV summary + scraped details

**Example**: `Cheshire.json`
```json
{
  "state": "New_Hampshire",
  "county": "Cheshire",
  "plan_count": 14,
  "all_counties_plan_count": 9,
  "county_specific_plan_count": 5,
  "scraped_details_available": 12,
  "plans": [
    {
      "summary": {
        "contract_plan_segment_id": "S4802_075_0",
        "plan_name": "Wellcare Classic (PDP)",
        "plan_type": "PDP",
        "organization": "Wellcare",
        ...
      },
      "details": {
        "plan_info": {...},
        "premiums": {...},
        "deductibles": {...},
        "contact_info": {...},
        "benefits": {...}
      },
      "has_scraped_details": true
    }
  ]
}
```

## API Endpoints

### `GET /api/nh/<zip_code>`
Returns all counties for a ZIP with their plans

**Parameters**:
- `include_details` (default: `true`) - Include full scraped details or summary only

**Response**:
```json
{
  "zip_code": "03602",
  "multi_county": true,
  "primary_county": "Cheshire",
  "counties": {
    "Cheshire": {
      "fips": "33005",
      "percentage": 68.3,
      "plan_count": 14,
      "scraped_details_available": 12,
      "plans": [...]
    },
    "Sullivan": {
      "fips": "33019",
      "percentage": 31.7,
      "plan_count": 12,
      "scraped_details_available": 12,
      "plans": [...]
    }
  }
}
```

### `GET /api/nh/plan/<plan_id>`
Get specific plan details

### `GET /api/nh/counties`
List all counties with plan counts

### `GET /health`
Health check

## Performance

### Response Sizes
- **Summary only**: ~2.6 KB per ZIP
- **Full details**: ~29 KB per ZIP
- **Ratio**: 11x larger with full details

### Recommendation
- Use `include_details=false` for initial listing
- Load full details on-demand when user clicks a plan

## Cache Strategy

### Current (for New Hampshire)
- **10 county cache files** (vs 241 ZIP files)
- **Disk space**: ~350 KB total for all counties
- **Load time**: All counties loaded at startup (~50ms)

### Invalidation
When new plan data is scraped:
1. Re-run `build_county_caches.py`
2. County files updated
3. Restart API server (or use hot-reload)

## Scaling to Other States

### For each new state:
1. Create `mock_api/{STATE}/zip_to_county_multi.json`
2. Run `build_county_caches.py` for that state
3. Creates `mock_api/{STATE}/counties/*.json`
4. Add state endpoint to API

### Example for Vermont:
```bash
python build_county_caches.py --state VT --state-name Vermont
```

## Files Generated

1. `build_zip_to_plans_mapping.py` - Creates ZIP → Plans mapping (deprecated, use county caches instead)
2. `build_county_caches.py` - **Main script** - Creates county cache files
3. `api_server.py` - Flask API server
4. `test_api.py` - Standalone test (no server needed)

## Next Steps

- [ ] Add Flask to requirements
- [ ] Create endpoint for multiple states
- [ ] Add CORS support
- [ ] Add rate limiting
- [ ] Deploy to cloud (AWS Lambda, Cloud Run, etc.)
- [ ] Complete scraping of remaining 6,229 plans
- [ ] Build caches for all states
