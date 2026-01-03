# Deploy Medicare Database API

## Architecture
- **Database**: RDS Aurora PostgreSQL Serverless v2 (auto-scales 0.5-1 ACU)
- **API**: Lambda + API Gateway HTTP API
- **Data**: 6,402 plans, 39,298 ZIPs, accurate county-level coverage

## Quick Deploy (All-in-One)

```bash
cd /Users/andy/medicare_overview_test
./database/deploy_complete.sh
```

This will:
1. Create RDS Aurora cluster (~5 min)
2. Create database schema
3. Load all 6,402 plans + geographic data
4. Deploy Lambda function
5. Set up API Gateway

**Total time:** ~15-20 minutes

## API Endpoints

After deployment, you'll get an endpoint like:
`https://{api-id}.execute-api.us-east-1.amazonaws.com/prod`

### Endpoints:
- `GET /medicare/zip/{zip_code}.json` - Plans by ZIP
- `GET /medicare/zip/{zip_code}_MAPD.json` - Filtered by category
- `GET /medicare/state/{ST}/info.json` - State info
- `GET /medicare/state/{ST}/plans.json` - All plans in state
- `GET /medicare/plan/{plan_id}.json` - Individual plan
- `GET /medicare/states.json` - List all states

## Cost Estimate
- **RDS Aurora Serverless v2**: $10-15/month (scales to zero when idle)
- **Lambda**: $1-3/month (generous free tier)
- **API Gateway**: $3-5/month
- **Total**: ~$15-25/month

## Manual Steps (if you prefer)

### 1. Deploy Database Only
```bash
./database/deploy_rds.sh
```

### 2. Load Data
```bash
# After RDS is ready, get connection info from:
cat database/db_credentials.json

# Load schema
psql -h {endpoint} -U medicare_admin -d medicare_plans -f database/schema.sql

# Load data
python3 database/load_data.py "host={endpoint} dbname=medicare_plans user=medicare_admin password={password}"
```

### 3. Deploy Lambda
```bash
cd lambda
pip3 install -r requirements.txt -t package/
cp medicare_api.py package/
cd package && zip -r ../medicare-api.zip . && cd ../..

# Create function via AWS console or CLI
```

## Updating Data

To update with new CMS data:
```bash
# 1. Re-scrape (or download new plans)
# 2. Rebuild mappings
python3 build_plan_county_mappings.py

# 3. Reload database
python3 database/load_data.py "..."
```

## Advantages Over Static Files

✅ **Fast queries** - PostgreSQL indexes
✅ **Easy updates** - Change one plan instantly
✅ **No build step** - Direct data access
✅ **Complex queries** - Filter, sort, search
✅ **Smaller storage** - ~500MB vs 5GB
✅ **Atomic updates** - Transaction support

## Custom Domain (Optional)

After deployment, you can add a custom domain:
```bash
# Example: api.medicare.purlpal.com
# Configure in API Gateway -> Custom domains
```
