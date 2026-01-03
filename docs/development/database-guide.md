# Medicare Plan Database API - Deployment Guide

## 🎉 Deployment Status: **LIVE**

**API Base URL:** `https://yvc5tid01h.execute-api.us-east-1.amazonaws.com/prod`

---

## Architecture Overview

### Components
- **Database:** AWS RDS PostgreSQL 15.8 (db.t3.micro, 20GB)
- **API Layer:** AWS Lambda (Python 3.11, pg8000 driver)
- **Gateway:** AWS API Gateway HTTP API
- **Region:** us-east-1

### Data Loaded
- **5,804 plans** across 56 states/territories
- **39,298 ZIP codes** with geographic mappings
- **9,245 counties** with plan coverage data
- **132,002 plan-county relationships**
- **54,389 ZIP-county relationships**

---

## API Endpoints

### 1. List All States
```
GET /medicare/states.json
```

**Example:**
```bash
curl https://yvc5tid01h.execute-api.us-east-1.amazonaws.com/prod/medicare/states.json
```

**Response:**
```json
{
  "state_count": 51,
  "total_plans": 5734,
  "states": [
    {
      "abbrev": "AL",
      "name": "Alabama",
      "plan_count": 110,
      "info_url": "/medicare/state/AL/info.json",
      "plans_url": "/medicare/state/AL/plans.json"
    }
  ]
}
```

---

### 2. State Information
```
GET /medicare/state/{STATE}/info.json
```

**Example:**
```bash
curl https://yvc5tid01h.execute-api.us-east-1.amazonaws.com/prod/medicare/state/MA/info.json
```

**Response:**
```json
{
  "state": "Massachusetts",
  "state_abbrev": "MA",
  "plan_count": 94
}
```

---

### 3. State Plans (Summary)
```
GET /medicare/state/{STATE}/plans.json
```

**Example:**
```bash
curl https://yvc5tid01h.execute-api.us-east-1.amazonaws.com/prod/medicare/state/MA/plans.json
```

---

### 4. Plans by ZIP Code
```
GET /medicare/zip/{ZIP}.json
GET /medicare/zip/{ZIP}_{CATEGORY}.json
```

**Categories:** `MAPD`, `PD`, `MA`

**Example:**
```bash
# All plans for ZIP 02108 (Boston)
curl https://yvc5tid01h.execute-api.us-east-1.amazonaws.com/prod/medicare/zip/02108.json

# Only MAPD plans
curl https://yvc5tid01h.execute-api.us-east-1.amazonaws.com/prod/medicare/zip/02108_MAPD.json
```

**Response:**
```json
{
  "zip_code": "02108",
  "multi_county": false,
  "multi_state": false,
  "states": ["MA"],
  "primary_state": "MA",
  "counties": [
    {
      "id": 8146,
      "name": "Suffolk County",
      "fips": "25025",
      "state": "MA",
      "ratio": 1.0
    }
  ],
  "plans": [
    {
      "plan_id": "H0777_001_0",
      "category": "MAPD",
      "plan_type": "HMO",
      "plan_info": {...},
      "premiums": {...},
      "deductibles": {...},
      "benefits": {...}
    }
  ],
  "plan_count": 50,
  "plan_counts_by_category": {
    "MAPD": 45,
    "PD": 0,
    "MA": 5
  }
}
```

---

### 5. Individual Plan Details
```
GET /medicare/plan/{PLAN_ID}.json
```

**Example:**
```bash
curl https://yvc5tid01h.execute-api.us-east-1.amazonaws.com/prod/medicare/plan/H0777_001_0.json
```

---

## Database Schema

### Tables

#### `states`
- `abbrev` (PK) - 2-letter state code
- `name` - Full state name
- `plan_count` - Number of plans in state

#### `plans`
- `plan_id` (PK) - CMS plan identifier
- `state_abbrev` (FK) - State code
- `plan_name` - Plan display name
- `plan_type` - PPO, HMO, etc.
- `category` - MAPD, PD, MA
- `monthly_premium_display` - Premium text
- `monthly_premium_value` - Numeric premium
- `health_deductible_display/value` - Deductibles
- `drug_deductible_display/value`
- `max_out_of_pocket_display/value` - MOOP
- `plan_info` (JSONB) - Complete plan details
- `premiums` (JSONB) - All premium info
- `deductibles` (JSONB) - All deductible info
- `benefits` (JSONB) - Benefit details
- `drug_coverage` (JSONB) - Drug coverage
- `extra_benefits` (JSONB) - Supplemental benefits

#### `counties`
- `id` (PK, auto-increment)
- `state_abbrev` (FK)
- `county_name`
- `fips` - FIPS code

#### `plan_counties`
- `plan_id` (FK) + `county_id` (FK) - Composite PK
- `all_counties` - Boolean flag

#### `zip_codes`
- `zip_code` (PK)
- `multi_county` - Boolean
- `multi_state` - Boolean
- `primary_state`
- `states` - Array of state codes

#### `zip_counties`
- `zip_code` (FK) + `county_id` (FK) - Composite PK
- `state_abbrev`
- `ratio` - Population ratio for multi-county ZIPs

---

## Deployment Details

### RDS Database
- **Instance:** medicare-plans-db
- **Endpoint:** `medicare-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com:5432`
- **Database:** medicare_plans
- **User:** medicare_admin
- **SSL:** Required (enabled)
- **Public Access:** Disabled (Lambda access only)

### Lambda Function
- **Name:** MedicareAPI
- **Runtime:** Python 3.11
- **Handler:** medicare_api.lambda_handler
- **Memory:** 512 MB
- **Timeout:** 30 seconds
- **Package:** pg8000 (pure Python PostgreSQL driver)

### API Gateway
- **Type:** HTTP API
- **API ID:** yvc5tid01h
- **Stage:** prod
- **CORS:** Enabled (all origins)

---

## Cost Estimates

### Monthly Costs (Assuming Moderate Usage)
- **RDS db.t3.micro (20GB):** ~$14/month
- **Lambda:** ~$0-5/month (depends on traffic)
- **API Gateway HTTP API:** ~$1/million requests
- **Data Transfer:** Minimal (in-region)

**Total:** ~$15-25/month

### Cost Optimization
- Database can be stopped when not in use
- Lambda scales to zero when idle
- HTTP API is much cheaper than REST API

---

## Deployment Scripts

### Full Deployment
```bash
cd database
./deploy_complete.sh
```

### Individual Steps

#### 1. Create RDS Instance
```bash
./deploy_rds.sh
```

#### 2. Create Schema
```bash
PGPASSWORD='<password>' psql -h <endpoint> -U medicare_admin -d medicare_plans -f schema.sql
```

#### 3. Load Data (Fast)
```bash
python3 load_data_fast.py "host=<endpoint> dbname=medicare_plans user=medicare_admin password=<password>"
```

#### 4. Package Lambda
```bash
cd lambda
pip3 install pg8000==1.30.3 -t package/
cp medicare_api.py package/
cd package && zip -r ../medicare-api.zip .
```

#### 5. Deploy Lambda
```bash
aws lambda create-function \
  --function-name MedicareAPI \
  --runtime python3.11 \
  --role <role-arn> \
  --handler medicare_api.lambda_handler \
  --zip-file fileb://medicare-api.zip \
  --timeout 30 \
  --memory-size 512 \
  --environment "Variables={DB_HOST=<endpoint>,DB_NAME=medicare_plans,DB_USER=medicare_admin,DB_PASSWORD=<password>}" \
  --profile silverman \
  --region us-east-1
```

#### 6. Create API Gateway
```bash
# Create API
aws apigatewayv2 create-api --name MedicareAPI --protocol-type HTTP

# Create integration
aws apigatewayv2 create-integration --api-id <api-id> \
  --integration-type AWS_PROXY \
  --integration-uri <lambda-arn> \
  --payload-format-version 2.0

# Create route
aws apigatewayv2 create-route --api-id <api-id> \
  --route-key 'GET /medicare/{proxy+}' \
  --target integrations/<integration-id>

# Create stage
aws apigatewayv2 create-stage --api-id <api-id> \
  --stage-name prod --auto-deploy

# Grant permissions
aws lambda add-permission --function-name MedicareAPI \
  --statement-id apigateway-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:us-east-1:<account>:<api-id>/*/*"
```

---

## Testing

### Quick Test
```bash
# Test states endpoint
curl https://yvc5tid01h.execute-api.us-east-1.amazonaws.com/prod/medicare/states.json | jq .

# Test ZIP lookup
curl https://yvc5tid01h.execute-api.us-east-1.amazonaws.com/prod/medicare/zip/02108.json | jq '.plan_count'
```

### Expected Results
- States endpoint should return 51 states
- ZIP 02108 should return ~50 plans (45 MAPD, 5 MA)

---

## Troubleshooting

### Connection Issues
- **Error:** "Can't create a connection"
  - **Fix:** Check RDS security group allows Lambda access
  - **Fix:** Verify database endpoint is correct

### SSL/TLS Issues
- **Error:** "no pg_hba.conf entry"
  - **Fix:** Enable SSL in pg8000 connection: `ssl_context=True`

### No Plans Returned
- **Issue:** County name mismatches
  - **Fix:** Normalize county names ("Suffolk" vs "Suffolk County")
  - **Query:** Check plan_counties and zip_counties join on same county IDs

### Performance
- **Slow queries:** Add indexes (already included in schema.sql)
- **Cold starts:** Consider provisioned concurrency for Lambda
- **High RDS costs:** Use Aurora Serverless v2 for variable workloads

---

## Data Updates

### Updating Plan Data

1. **Scrape new data** (when CMS releases updates)
2. **Rebuild mappings:**
   ```bash
   python3 build_plan_county_mappings.py
   ```
3. **Truncate tables:**
   ```sql
   TRUNCATE zip_counties, zip_codes, plan_counties, counties, plans, states CASCADE;
   ```
4. **Reload data:**
   ```bash
   python3 load_data_fast.py "<connection-string>"
   ```

### Schema Changes
```bash
psql -h <endpoint> -U medicare_admin -d medicare_plans -f schema_updates.sql
```

---

## Maintenance

### Database Backups
- Automated daily snapshots enabled (7-day retention)
- Manual snapshot: `aws rds create-db-snapshot`

### Monitoring
- CloudWatch Logs: `/aws/lambda/MedicareAPI`
- RDS Metrics: Database connections, CPU, storage

### Security
- ✅ SSL/TLS required for database connections
- ✅ No public internet access to RDS
- ✅ IAM roles for Lambda execution
- ✅ API Gateway throttling enabled

---

## Migration from Static S3 API

### Advantages of Database API
1. **Dynamic queries** - Filter by category, county, etc.
2. **Smaller footprint** - No 40,000 static JSON files
3. **Easier updates** - Reload data without rebuilding all files
4. **Lower latency** - Direct database queries vs S3 GET
5. **Cost effective** - ~$15/mo vs S3 + CloudFront

### Keeping Both
You can run both APIs simultaneously:
- **S3/CloudFront:** https://medicare.purlpal-api.com (existing)
- **RDS/Lambda:** https://yvc5tid01h.execute-api.us-east-1.amazonaws.com/prod (new)

---

## Support & Documentation

### Files
- `schema.sql` - Database schema
- `load_data_fast.py` - Optimized data loader
- `medicare_api.py` - Lambda function code
- `api_deployment.json` - Deployment configuration
- `DEPLOY_DATABASE_API.md` - Original deployment guide

### Credentials
Stored in: `database/db_credentials.json`

---

**Deployed:** December 30, 2025  
**Status:** ✅ Production Ready
