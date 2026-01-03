# Medicare Plan API - User Guide

**Base URL:** `https://medicare.purlpal-api.com/medicare/`

A simple, fast API to look up Medicare Advantage and Part D plans by ZIP code. No authentication required.

---

## Quick Examples

### Get plans for your ZIP code
```bash
curl "https://medicare.purlpal-api.com/medicare/zip/90210.json"
```

### Get only Medicare Advantage plans with drug coverage (MAPD)
```bash
curl "https://medicare.purlpal-api.com/medicare/zip/90210_MAPD.json"
```

### Get all available states
```bash
curl "https://medicare.purlpal-api.com/medicare/states.json"
```

---

## What Plans Are Available?

The API includes three types of Medicare plans:

| Type | Code | Description |
|------|------|-------------|
| **MAPD** | Medicare Advantage + Part D | Health coverage + prescription drugs |
| **MA** | Medicare Advantage only | Health coverage, no drug coverage |
| **PD** | Part D only | Prescription drug coverage only |

**Coverage:** All 50 states + DC • 5,804 plans • 39,298 ZIP codes • 98.6% coverage

---

## API Endpoints

### 1. Get Plans for a ZIP Code

**Endpoint:** `GET /zip/{zipcode}.json`

Returns all Medicare plans available in a ZIP code.

**Example:**
```bash
curl "https://medicare.purlpal-api.com/medicare/zip/02108.json"
```

**Response:**
```json
{
  "zip_code": "02108",
  "plan_count": 50,
  "plan_counts_by_category": {
    "MAPD": 44,
    "MA": 6,
    "PD": 0
  },
  "counties": [
    {
      "name": "Suffolk County",
      "state": "MA",
      "plan_count": 50,
      "plans": [...]
    }
  ],
  "plans": [
    {
      "plan_id": "H6851_001_0",
      "category": "MAPD",
      "plan_type": "HMO",
      "plan_info": {
        "name": "AARP Medicare Advantage (HMO)",
        "organization": "UnitedHealthcare"
      },
      "premiums": {
        "Total monthly premium": "$0.00"
      }
    }
  ]
}
```

---

### 2. Filter by Plan Category

Get only specific plan types:

**MAPD Plans (Medicare Advantage + Drugs):**
```bash
curl "https://medicare.purlpal-api.com/medicare/zip/02108_MAPD.json"
```

**MA Plans (Medicare Advantage only):**
```bash
curl "https://medicare.purlpal-api.com/medicare/zip/02108_MA.json"
```

**PD Plans (Part D drugs only):**
```bash
curl "https://medicare.purlpal-api.com/medicare/zip/02108_PD.json"
```

---

### 3. List All States

**Endpoint:** `GET /states.json`

**Example:**
```bash
curl "https://medicare.purlpal-api.com/medicare/states.json"
```

**Response:**
```json
{
  "state_count": 51,
  "total_plans": 5804,
  "states": [
    {
      "abbrev": "TX",
      "name": "Texas",
      "plan_count": 245
    }
  ]
}
```

---

### 4. Get State Information

**Endpoint:** `GET /state/{STATE}/info.json`

**Example:**
```bash
curl "https://medicare.purlpal-api.com/medicare/state/CA/info.json"
```

**Response:**
```json
{
  "state": "California",
  "state_abbrev": "CA",
  "plan_count": 315
}
```

---

### 5. Get Individual Plan Details

**Endpoint:** `GET /plan/{plan_id}.json`

**Example:**
```bash
curl "https://medicare.purlpal-api.com/medicare/plan/H6851_001_0.json"
```

Returns complete plan details including premiums, deductibles, benefits, and drug coverage.

---

## Understanding the Response

### Multi-County ZIP Codes

Some ZIP codes span multiple counties. For these, plans are grouped by county:

```json
{
  "zip_code": "01002",
  "multi_county": true,
  "counties": [
    {
      "name": "Hampshire County",
      "state": "MA",
      "ratio": 0.9933,
      "plan_count": 26,
      "plans": [...]
    },
    {
      "name": "Franklin County",
      "state": "MA",
      "ratio": 0.0067,
      "plan_count": 26,
      "plans": [...]
    }
  ]
}
```

The `ratio` field shows what percentage of the ZIP is in each county.

---

## Plan Data Structure

Each plan includes:

### Basic Info
- `plan_id` - Unique identifier
- `category` - MAPD, MA, or PD
- `plan_type` - HMO, PPO, PDP, etc.

### Plan Details
- `plan_info.name` - Plan name
- `plan_info.organization` - Insurance company

### Costs
- `premiums` - Monthly premium amounts
- `deductibles` - Health and drug deductibles
- `out_of_pocket` - Maximum out-of-pocket costs

### Coverage
- `benefits` - Doctor visits, hospital, dental, vision, etc.
- `drug_coverage` - Pharmacy tiers and copays
- `extra_benefits` - Additional benefits offered

---

## Usage Examples

### JavaScript (Web or Chrome Extension)

```javascript
// Get plans for ZIP code
fetch('https://medicare.purlpal-api.com/medicare/zip/90210.json')
  .then(response => response.json())
  .then(data => {
    console.log(`Found ${data.plan_count} plans`);
    
    // Filter $0 premium MAPD plans
    const freePlans = data.plans.filter(plan =>
      plan.category === 'MAPD' &&
      plan.premiums['Total monthly premium'] === '$0.00'
    );
    
    console.log(`${freePlans.length} free MAPD plans available`);
  });
```

### Python

```python
import requests

# Get plans for ZIP code
response = requests.get('https://medicare.purlpal-api.com/medicare/zip/90210.json')
data = response.json()

print(f"Found {data['plan_count']} plans")

# Filter MAPD plans
mapd_plans = [p for p in data['plans'] if p['category'] == 'MAPD']
print(f"{len(mapd_plans)} MAPD plans available")
```

### cURL with jq (Command Line)

```bash
# Get plan count by category
curl -s "https://medicare.purlpal-api.com/medicare/zip/90210.json" | \
  jq '.plan_counts_by_category'

# List plan names and premiums
curl -s "https://medicare.purlpal-api.com/medicare/zip/90210.json" | \
  jq '.plans[] | {name: .plan_info.name, premium: .premiums["Total monthly premium"]}'

# Find $0 premium plans
curl -s "https://medicare.purlpal-api.com/medicare/zip/90210.json" | \
  jq '.plans[] | select(.premiums["Total monthly premium"] == "$0.00") | .plan_info.name'
```

---

## Performance

- **Response Time:** 290-400ms average (warm requests)
- **Cold Start:** ~1.3 seconds (first request after idle)
- **Availability:** 100% uptime target
- **Rate Limits:** None (reasonable use expected)

---

## CORS Support

The API supports CORS for client-side JavaScript and Chrome extensions:

- ✅ All origins allowed (`*`)
- ✅ Works from `chrome-extension://` URLs
- ✅ No authentication required

---

## API Specification

**Live OpenAPI Spec:** `https://medicare.purlpal-api.com/medicare/openapi.yaml`

Use this URL to:
- Import directly into Postman, Insomnia, or other API tools
- Generate client libraries automatically
- View in Swagger UI or similar documentation tools

**Local files:**
- [`openapi-compact.yaml`](./openapi-compact.yaml) - Compact version (~150 lines)
- [`openapi.yaml`](./openapi.yaml) - Full version with examples (~450 lines)

---

## Coverage & Limitations

### Geographic Coverage
- ✅ All 50 states + DC
- ✅ 98.6% of ZIP codes have plans (38,743/39,298)
- ⚠️ 1.4% of ZIPs have no plans (mostly rural/remote areas)
- ℹ️ Vermont plans not yet available in database

### Plan Types
- ✅ Medicare Advantage (MA)
- ✅ Medicare Advantage + Part D (MAPD)
- ✅ Part D Prescription Drug Plans (PDP)

---

## Troubleshooting

### No plans returned for my ZIP
Some rural/remote ZIP codes may legitimately have no Medicare plans. Try:
1. Check a nearby ZIP code
2. Verify the ZIP code exists: `curl "https://medicare.purlpal-api.com/medicare/zip/{ZIP}.json"`
3. Contact us if you believe plans should be available

### Slow response times
First request after Lambda idle may take ~1.3s (cold start). Subsequent requests are 290-400ms.

### CORS errors in browser
The API supports all origins. If you're getting CORS errors:
1. Verify you're using `https://medicare.purlpal-api.com` (not the API Gateway URL)
2. Check browser console for specific error
3. Ensure you're making a GET request

---

## Updates

The API is updated when new Medicare plan data is available. Changes are reflected immediately - no cache clearing needed.

---

## Support

- **Technical Documentation:** [`README.md`](./README.md)
- **API Reference:** [`API_REFERENCE.md`](./API_REFERENCE.md)
- **OpenAPI Spec:** [`openapi.yaml`](./openapi.yaml)
- **Test Script:** `python3 test_api_comprehensive.py`

---

## License

Public domain - Medicare plan data is publicly available from Medicare.gov.
