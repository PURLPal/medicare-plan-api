# Medicare Plan API - Complete Reference

## Base URL
- **Production:** https://medicare.purlpal-api.com/medicare/
- **CloudFront:** https://d11vrs9xl9u4t7.cloudfront.net/medicare/

## Quick Start

```bash
# Get all states
curl https://medicare.purlpal-api.com/medicare/states.json

# Get plans by ZIP code
curl https://medicare.purlpal-api.com/medicare/zip/03462.json

# Filter MAPD plans only
curl https://medicare.purlpal-api.com/medicare/zip/03462.json | \
  jq '.plans | map(select(.category == "MAPD"))'
```

## Plan Categories

Each plan has a `category` field:

| Category | Description | Type |
|----------|-------------|------|
| `MAPD` | Medicare Advantage with drug coverage | Part C + Part D |
| `MA` | Medicare Advantage without drug coverage | Part C only |
| `PD` | Prescription Drug plan only | Part D only |

## API Endpoints

### 1. List All States
```
GET /medicare/states.json
```

**Response:**
```json
{
  "generated_at": "2025-12-08T11:54:30.200254+00:00",
  "state_count": 14,
  "plan_count": 467,
  "states": [
    {
      "state_code": "AK",
      "state_name": "Alaska",
      "plan_count": 42,
      "county_count": 29
    }
  ]
}
```

### 2. State Information
```
GET /medicare/state/{STATE_CODE}/info.json
```

**Example:**
```bash
curl https://medicare.purlpal-api.com/medicare/state/NH/info.json
```

**Response:**
```json
{
  "state_code": "NH",
  "state_name": "New Hampshire",
  "plan_count": 14,
  "county_count": 10,
  "counties": [
    {
      "county_name": "Cheshire County",
      "fips": "33005",
      "plan_count": 14
    }
  ]
}
```

### 3. All Plans in State
```
GET /medicare/state/{STATE_CODE}/plans.json
```

**Example:**
```bash
curl https://medicare.purlpal-api.com/medicare/state/NH/plans.json
```

Returns all plans available anywhere in the state.

### 4. Plans by County
```
GET /medicare/state/{STATE_CODE}/county/{COUNTY_NAME}.json
```

**Example:**
```bash
curl https://medicare.purlpal-api.com/medicare/state/NH/county/Cheshire_County.json
```

**Note:** County names use underscores instead of spaces (e.g., `Cheshire_County`)

### 5. Plans by ZIP Code
```
GET /medicare/zip/{ZIPCODE}.json
```

**Example:**
```bash
curl https://medicare.purlpal-api.com/medicare/zip/03462.json
```

**Response:**
```json
{
  "zip_code": "03462",
  "multi_county": false,
  "multi_state": false,
  "states": ["NH"],
  "primary_state": "NH",
  "counties": [
    {
      "fips": "33005",
      "name": "Cheshire County",
      "state": "NH",
      "ratio": 1.0,
      "plans_available": true,
      "plan_count": 14
    }
  ],
  "plans": [...]
}
```

### 6. Individual Plan Details
```
GET /medicare/plan/{PLAN_ID}.json
```

**Example:**
```bash
curl https://medicare.purlpal-api.com/medicare/plan/S4802_075_0.json
```

**Response:**
```json
{
  "plan_id": "S4802_075_0",
  "category": "PD",
  "plan_type": "PDP",
  "plan_info": {
    "name": "HealthSpring Assurance Rx (PDP)",
    "organization": "HealthSpring",
    "type": "Drug plan (Part D)",
    "id": "S5617-003-0"
  },
  "premiums": {
    "Total monthly premium": "$0.00"
  },
  "deductibles": {
    "Drug deductible": "$615.00"
  },
  "benefits": {...}
}
```

## Filtering Examples

### Filter by Plan Category

#### MAPD Plans Only
```bash
curl https://medicare.purlpal-api.com/medicare/zip/03462.json | \
  jq '.plans | map(select(.category == "MAPD"))'
```

#### MA Plans Only
```bash
curl https://medicare.purlpal-api.com/medicare/zip/03462.json | \
  jq '.plans | map(select(.category == "MA"))'
```

#### Part D Drug Plans Only
```bash
curl https://medicare.purlpal-api.com/medicare/zip/03462.json | \
  jq '.plans | map(select(.category == "PD"))'
```

### Count by Category
```bash
curl https://medicare.purlpal-api.com/medicare/zip/03462.json | jq '{
  total: (.plans | length),
  mapd: (.plans | map(select(.category == "MAPD")) | length),
  ma: (.plans | map(select(.category == "MA")) | length),
  pd: (.plans | map(select(.category == "PD")) | length)
}'
```

### Filter by Premium

#### Zero Premium Plans
```bash
curl https://medicare.purlpal-api.com/medicare/zip/03462.json | \
  jq '.plans | map(select(.premiums["Total monthly premium"] == "$0.00"))'
```

#### MAPD Plans with Zero Premium
```bash
curl https://medicare.purlpal-api.com/medicare/zip/03462.json | jq '
  .plans |
  map(select(.category == "MAPD" and .premiums["Total monthly premium"] == "$0.00"))
'
```

### Filter by Organization

#### UnitedHealthcare Plans Only
```bash
curl https://medicare.purlpal-api.com/medicare/zip/03462.json | \
  jq '.plans | map(select(.plan_info.organization == "UnitedHealthcare"))'
```

#### Humana Plans Only
```bash
curl https://medicare.purlpal-api.com/medicare/zip/03462.json | \
  jq '.plans | map(select(.plan_info.organization == "Humana"))'
```

### Filter by Plan Type

#### HMO Plans Only
```bash
curl https://medicare.purlpal-api.com/medicare/zip/03462.json | \
  jq '.plans | map(select(.plan_type == "HMO"))'
```

#### PPO Plans Only
```bash
curl https://medicare.purlpal-api.com/medicare/zip/03462.json | \
  jq '.plans | map(select(.plan_type == "PPO"))'
```

### Complex Filters

#### MAPD Plans with Zero Premium and HMO Type
```bash
curl https://medicare.purlpal-api.com/medicare/zip/03462.json | jq '
  .plans |
  map(select(
    .category == "MAPD" and
    .premiums["Total monthly premium"] == "$0.00" and
    .plan_type == "HMO"
  ))
'
```

#### Plans with Specific Benefits
```bash
# Find plans with dental coverage
curl https://medicare.purlpal-api.com/medicare/zip/03462.json | jq '
  .plans |
  map(select(.benefits["Preventive dental"] != null))
'
```

### Get Summary Information

#### List Just Plan Names and Premiums
```bash
curl https://medicare.purlpal-api.com/medicare/zip/03462.json | jq '
  .plans |
  map({
    name: .plan_info.name,
    category,
    premium: .premiums["Total monthly premium"]
  })
'
```

#### Compare Drug Coverage
```bash
curl https://medicare.purlpal-api.com/medicare/zip/03462.json | jq '
  .plans |
  map(select(.category == "MAPD" or .category == "PD")) |
  map({
    name: .plan_info.name,
    category,
    drug_deductible: .deductibles["Drug deductible"]
  })
'
```

## Plan Data Structure

Each plan contains the following fields:

### Core Fields
- `plan_id` - Unique plan identifier (e.g., "H6851_001_0")
- `category` - Plan category: MAPD, MA, or PD
- `plan_type` - Plan type: HMO, PPO, PDP, HMO-POS, etc.

### Plan Information
```json
"plan_info": {
  "name": "AARP Medicare Advantage from UHC NH-2 (HMO-POS)",
  "organization": "UnitedHealthcare",
  "type": "Medicare Advantage with drug coverage",
  "id": "H5253-207-0"
}
```

### Cost Information
```json
"premiums": {
  "Total monthly premium": "$0.00",
  "Health premium": "$0.00",
  "Drug premium": "$0.00",
  "Standard Part B premium": "$202.90",
  "Part B premium reduction": "Not offered"
}
```

```json
"deductibles": {
  "Health deductible": "$1,500\nIn-network",
  "Drug deductible": "$440.00"
}
```

```json
"maximum_out_of_pocket": {
  "Maximum you pay for health services...": "$6,700 In-network"
}
```

### Contact Information
```json
"contact_info": {
  "Plan address": "P.O. Box 30770\nSalt Lake City, UT 84130"
}
```

### Benefits
```json
"benefits": {
  "Doctor services": {
    "Primary doctor visit": "In-network: $0 copay",
    "Specialist visit": "In-network: $0-$45 copay"
  },
  "Pharmacies": {},
  "Costs by drug tier - Standard retail pharmacy drug cost for 1 month": {
    "Preferred Generic": "$0.00 copay",
    "Generic": "$12.00 copay"
  }
}
```

## Testing

Run the comprehensive test script:
```bash
./test_cloudfront_api.sh
```

This will test:
- State listing
- ZIP code lookups
- Plan filtering by category (MAPD, MA, PD)
- Plan details
- Multi-state/multi-county ZIP codes
- Category breakdown statistics

## CORS Support

The API supports CORS for client-side JavaScript applications:
- All origins allowed
- GET method supported
- Standard headers allowed

## Performance

- **Global CDN:** CloudFront edge locations worldwide
- **Latency:** ~50ms average response time
- **Caching:** 1 hour browser cache + CloudFront edge cache
- **Compression:** Automatic GZIP compression
- **Availability:** 99.9% uptime SLA

## Rate Limits

No rate limits currently enforced. Reasonable use expected.

## Updates

The API is updated when new Medicare plan data is scraped:
- Full rebuild: ~10-15 minutes
- Incremental update: ~30 seconds - 2 minutes
- CloudFront cache invalidation: 1-2 minutes to propagate

## Support

For issues or questions:
- Test the API: `./test_cloudfront_api.sh`
- Check deployment guide: `API_DEPLOYMENT.md`
- Check CloudFront status: `aws cloudfront get-distribution --id E3SHXUEGZALG4E`
