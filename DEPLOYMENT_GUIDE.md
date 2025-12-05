
# Medicare Plan API - AWS Lambda Deployment Guide

## Overview

Fully serverless Medicare plan lookup API deployed to AWS Lambda with Function URLs.

**Coverage:**
- ✅ Alaska (AK) - 1 plan scraped
- ✅ New Hampshire (NH) - 25/28 plans (89% coverage)
- ✅ Vermont (VT) - 14/14 plans (100% coverage)
- ✅ Wyoming (WY) - 25/25 plans (100% coverage)
- **Overall: 610/625 plans (97.6% coverage)**

## Architecture

```
User/Chrome Extension
    ↓
AWS Lambda Function URL (HTTPS)
    ↓
Lambda loads county caches from disk
    ↓
Returns JSON response
```

**Why Lambda?**
- ✅ Everything pre-computed (no database needed)
- ✅ Small payload (~2 MB total)
- ✅ Fast cold starts (<500ms)
- ✅ Cheap (likely free tier)
- ✅ Auto-scaling
- ✅ HTTPS included
- ✅ CORS support for Chrome Extensions

## Files

### Core Lambda Function
- `lambda_function.py` - Main Lambda handler (supports AK, NH, VT, WY)

### Data Files (bundled in deployment)
- `mock_api/AK/zip_to_county_multi.json` - Alaska ZIP mappings
- `mock_api/NH/zip_to_county_multi.json` - New Hampshire ZIP mappings
- `mock_api/VT/zip_to_county_multi.json` - Vermont ZIP mappings
- `mock_api/WY/zip_to_county_multi.json` - Wyoming ZIP mappings
- `mock_api/{STATE}/counties/*.json` - Pre-computed county caches with plan details

### Deployment Scripts
- `deploy_lambda.sh` - Automated deployment script
- `build_all_county_caches.py` - Rebuild caches when new data scraped

### Testing
- `test_api_curl.sh` - Test all endpoints with curl
- `chrome_extension_example.js` - Chrome Extension integration example

## API Endpoints

All endpoints support CORS including `chrome-extension://` origins.

### GET /health
Health check

**Response:**
```json
{
  "status": "healthy",
  "states_loaded": 4,
  "zip_codes_loaded": 884,
  "counties_loaded": 39
}
```

### GET /states
List all available states

**Response:**
```json
{
  "states": [
    {"key": "ak", "name": "Alaska", "abbr": "AK", "zip_codes": 142, "counties": 0},
    {"key": "nh", "name": "New Hampshire", "abbr": "NH", "zip_codes": 241, "counties": 10}
  ],
  "total_states": 4
}
```

### GET /{state}/{zip_code}
Get all plans for a ZIP code

**Parameters:**
- `state` - State key (ak, nh, vt, wy)
- `zip_code` - ZIP code
- `details` - Include full plan details (default: 1). Set to 0 for summary only (11x smaller, faster)

**Examples:**
- `/nh/03462` - Full details
- `/nh/03462?details=0` - Summary only (faster, recommended for lists)
- `/vt/05401` - Vermont ZIP
- `/wy/82001?details=0` - Wyoming ZIP, summary

**Response (summary mode):**
```json
{
  "zip_code": "03462",
  "state": "New Hampshire",
  "state_abbr": "NH",
  "multi_county": false,
  "primary_county": "Cheshire",
  "counties": {
    "Cheshire": {
      "fips": "33005",
      "plan_count": 14,
      "scraped_details_available": 12,
      "plans": [
        {
          "contract_plan_segment_id": "S4802_075_0",
          "plan_name": "Wellcare Classic (PDP)",
          "plan_type": "PDP",
          "organization": "Wellcare",
          "has_scraped_details": true
        }
      ]
    }
  }
}
```

**Multi-county ZIP example:**
```json
{
  "zip_code": "03602",
  "multi_county": true,
  "primary_county": "Cheshire",
  "counties": {
    "Cheshire": {
      "percentage": 68.3,
      "plan_count": 14
    },
    "Sullivan": {
      "percentage": 31.7,
      "plan_count": 12
    }
  }
}
```

### GET /{state}/plan/{plan_id}
Get details for a specific plan

**Example:** `/nh/plan/S4802_075_0`

**Response:**
```json
{
  "plan_id": "S4802_075_0",
  "state": "New Hampshire",
  "county": "Cheshire",
  "summary": {
    "plan_name": "Wellcare Classic (PDP)",
    "organization": "Wellcare",
    "part_c_premium": "Not Applicable",
    "part_d_total_premium": "$0.00",
    "overall_star_rating": "3.5"
  },
  "details": {
    "plan_info": {...},
    "premiums": {"Total monthly premium": "$0.00"},
    "deductibles": {"Drug deductible": "$615.00"},
    "contact_info": {"Plan address": "P O Box 269005\nWeston, FL 33326"},
    "benefits": {...}
  },
  "has_scraped_details": true
}
```

### GET /{state}/counties
List all counties in a state

**Example:** `/nh/counties`

**Response:**
```json
{
  "state": "New Hampshire",
  "state_abbr": "NH",
  "county_count": 10,
  "counties": [
    {"name": "Belknap", "plan_count": 15, "scraped_details_available": 13},
    {"name": "Carroll", "plan_count": 11, "scraped_details_available": 11}
  ]
}
```

## Deployment Steps

### Prerequisites

1. **AWS CLI installed and configured**
   ```bash
   aws configure
   ```

2. **Python 3.12** (or adjust RUNTIME in deploy_lambda.sh)

3. **jq** (for testing)
   ```bash
   brew install jq  # macOS
   ```

### Step 1: Build County Caches

If you've scraped new plans:

```bash
python3 build_all_county_caches.py
```

This generates `mock_api/{STATE}/counties/*.json` files.

### Step 2: Create IAM Role (First Time Only)

```bash
# Create Lambda execution role
aws iam create-role --role-name lambda-medicare-api-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach basic execution policy
aws iam attach-role-policy \
  --role-name lambda-medicare-api-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Get the role ARN (save this)
aws iam get-role --role-name lambda-medicare-api-role --query 'Role.Arn' --output text
```

### Step 3: Deploy

```bash
chmod +x deploy_lambda.sh
./deploy_lambda.sh
```

The script will:
1. Create deployment package with all data files
2. Create/update Lambda function
3. Configure Function URL with CORS
4. Output the public URL

**Expected output:**
```
================================
✓ Deployment Complete!
================================

Function URL: https://abc123.lambda-url.us-east-1.on.aws/

Test it:
  curl https://abc123.lambda-url.us-east-1.on.aws/health
  curl https://abc123.lambda-url.us-east-1.on.aws/nh/03462
```

### Step 4: Test

```bash
# Update test script with your Function URL
export FUNCTION_URL="https://your-url.lambda-url.us-east-1.on.aws"

# Run tests
chmod +x test_api_curl.sh
./test_api_curl.sh $FUNCTION_URL
```

## Chrome Extension Integration

See `chrome_extension_example.js` for complete examples.

**Quick Example:**
```javascript
const API_URL = 'https://your-url.lambda-url.us-east-1.on.aws';

async function getPlans(state, zipCode) {
  const response = await fetch(`${API_URL}/${state}/${zipCode}?details=0`);
  return await response.json();
}

// Usage
const plans = await getPlans('nh', '03462');
console.log(`Found ${plans.counties.Cheshire.plan_count} plans`);
```

**CORS is pre-configured** - no special headers needed from Chrome Extension.

## Performance

### Response Sizes
- Health check: ~200 bytes
- States list: ~400 bytes
- ZIP summary: ~2-5 KB
- ZIP full details: ~20-50 KB
- Plan detail: ~5-10 KB

### Latency (warm Lambda)
- Health check: ~50ms
- ZIP summary: ~100ms
- ZIP full details: ~150ms

### Cold Start
- First request: ~500ms
- All data loaded into memory
- Subsequent requests: ~50-150ms

### Costs (estimated)
- **Free tier**: 1M requests/month, 400K GB-seconds
- **This API**: ~0.1s per request, 512 MB memory
- **Expected**: FREE for <100K requests/month

## Updating Data

When new plans are scraped:

```bash
# 1. Rebuild county caches
python3 build_all_county_caches.py

# 2. Redeploy
./deploy_lambda.sh

# 3. Test
./test_api_curl.sh $FUNCTION_URL
```

## Monitoring

View logs:
```bash
aws logs tail /aws/lambda/medicare-plan-api --follow
```

## Troubleshooting

### Function URL not working
```bash
# Add public access permission
aws lambda add-permission \
  --function-name medicare-plan-api \
  --statement-id FunctionURLAllowPublicAccess \
  --action lambda:InvokeFunctionUrl \
  --principal "*" \
  --function-url-auth-type NONE
```

### CORS errors from Chrome Extension
Check headers in response:
```bash
curl -i https://your-url.lambda-url.us-east-1.on.aws/health | grep -i access-control
```

Should see:
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization, X-Requested-With
```

### Payload too large error
Use `?details=0` for summary mode (11x smaller).

## Next Steps

- [ ] Add more states (need ZIP→county mappings + scraping)
- [ ] Set up CloudWatch alarms
- [ ] Add API Gateway for rate limiting/API keys
- [ ] Add caching headers for CDN
- [ ] Complete scraping remaining 15 NH plans
- [ ] Add state auto-detection from ZIP code

## Security

- ✅ No sensitive data (all public Medicare info)
- ✅ Read-only API
- ✅ No authentication needed (public data)
- ✅ CORS enabled for Chrome Extensions
- ✅ HTTPS enforced (Lambda Function URL)
- ⚠️ Rate limiting: Consider API Gateway if needed

## Support

Issues or questions:
1. Check CloudWatch Logs
2. Test locally: `python3 lambda_function.py`
3. Verify data files exist in deployment package
