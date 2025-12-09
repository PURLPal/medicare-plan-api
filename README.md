# Medicare Plan API

CloudFront + S3 static API for looking up Medicare Advantage plans by ZIP code. Production-ready with 26 states and full plan details.

## Quick Start

### For Your Teammate (Chrome Extension Developer)

See **[TESTING_GUIDE.md](TESTING_GUIDE.md)** for complete beginner walkthrough.

**Run tests now:**
```bash
./test_medicare_api.sh
```

### For End Users

**Production API:** https://medicare.purlpal-api.com/medicare/

```bash
# Get plans for any ZIP code
curl "https://medicare.purlpal-api.com/medicare/zip/03462.json" | jq '.'

# Filter MAPD plans only
curl "https://medicare.purlpal-api.com/medicare/zip/03462.json" | \
  jq '.plans | map(select(.category == "MAPD"))'
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

## Currently Supported

### States (26 + DC)
AK, CA, CT, DC, DE, FL, HI, IA, MD, ME, MI, MT, NC, ND, NE, NH, NY, OR, RI, SC, SD, UT, VT, WA, WV, WY

### Data Coverage
- **2,861 plans** scraped and ready
- **467 plans** currently deployed (26 states)
- **57,000+ static JSON files** (~2.5 GB)
- **Full plan details** including benefits, premiums, deductibles

### Plan Categories
- **MAPD** - Medicare Advantage with drug coverage (Part C + Part D)
- **MA** - Medicare Advantage only (Part C, no drug coverage)
- **PD** - Part D drug plans only

## Documentation

### For Developers
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Beginner-friendly testing guide
- **[API_REFERENCE.md](API_REFERENCE.md)** - Complete API reference with filtering examples
- **[API_DEPLOYMENT.md](API_DEPLOYMENT.md)** - Deployment and update guide

### For DevOps
- **[API_DEPLOYMENT.md](API_DEPLOYMENT.md)** - How to deploy updates
- **[API_ARCHITECTURE.md](API_ARCHITECTURE.md)** - System architecture (deprecated Lambda info)

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

- **CloudFront + S3** - Static JSON files served via CDN
- **57,000+ files** - Pre-generated for instant access
- **2.5 GB data** - Complete plan details
- **1 hour cache** - Browser + CloudFront caching
- **Cost effective** - ~$1.50/month for all states

### Why CloudFront Instead of Lambda?
- ✅ Scales to all 50 states (no 250 MB package limit)
- ✅ Faster (~50ms vs ~200ms)
- ✅ Cheaper (~$1.50/month vs ~$5/month)
- ✅ Simpler updates (just upload JSON files)

## Deployment

### Quick Update (After Scraping New Data)
```bash
./incremental_update.sh
```
**Time:** 30 seconds - 2 minutes

### Full Rebuild
```bash
./update_api.sh
```
**Time:** 10-15 minutes (builds all files + uploads to S3)

### What Gets Updated
1. Build static JSON files (`python3 build_static_api.py`)
2. Sync to S3 (`aws s3 sync`)
3. Invalidate CloudFront cache

**Logs saved to:**
- `/tmp/build_api.log` - Build process
- `/tmp/s3_sync.log` - S3 upload details

## Development

### Scrape New States
```bash
python3 scrape_all_remaining.py
```

### Rebuild API Files
```bash
python3 build_static_api.py
```

### Deploy to Production
```bash
./update_api.sh
```

### Test Locally
```bash
./test_medicare_api.sh
```

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

- **Latency:** ~50ms average (CloudFront edge caching)
- **Availability:** 99.9% uptime SLA
- **Scalability:** Unlimited (CloudFront CDN)
- **Cost:** ~$1.50/month for all states

## Monitoring

Check API status:
```bash
curl "https://medicare.purlpal-api.com/medicare/states.json" | jq '{
  states: .state_count,
  generated: .generated_at
}'
```

Check CloudFront distribution:
```bash
aws cloudfront get-distribution --id E3SHXUEGZALG4E \
  --query 'Distribution.Status' --output text
```

## Troubleshooting

### API returning old data?
Run invalidation:
```bash
aws cloudfront create-invalidation \
  --distribution-id E3SHXUEGZALG4E \
  --paths "/medicare/*"
```

### Need to rebuild everything?
```bash
rm -rf static_api/
./update_api.sh
```

### Test scripts not working?
Make sure you have `jq` installed:
```bash
brew install jq  # macOS
```

## Migration Notes

### Lambda API Deprecated
The old Lambda API was removed in favor of CloudFront + S3 because:
- Lambda had 250 MB deployment limit (couldn't scale past ~15 states)
- CloudFront is faster, cheaper, and scales infinitely
- Static files are simpler to manage

## License

Public domain - Medicare plan data is publicly available from Medicare.gov.

## Questions?

- **For testing:** See [TESTING_GUIDE.md](TESTING_GUIDE.md)
- **For API usage:** See [API_REFERENCE.md](API_REFERENCE.md)
- **For deployment:** See [API_DEPLOYMENT.md](API_DEPLOYMENT.md)

## Quick Reference

**API URL:** https://medicare.purlpal-api.com/medicare/

**Test Script:** `./test_medicare_api.sh`

**Update API:** `./incremental_update.sh`

**Full Rebuild:** `./update_api.sh`

**States:** 26 + DC (more coming soon)

**Total Plans:** 2,861 scraped, 467 deployed
