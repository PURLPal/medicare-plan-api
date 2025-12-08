# Medicare Plan API - Deployment Guide

## Current Architecture

**Production API:** CloudFront + S3 (Static JSON)
**URL:** https://medicare.purlpal-api.com/medicare/
**Alternate:** https://d11vrs9xl9u4t7.cloudfront.net/medicare/

### Why CloudFront?
- ✅ Scales to all 50 states + territories
- ✅ Global CDN edge caching (~50ms latency worldwide)
- ✅ Simple updates (just sync new JSON files)
- ✅ Cost-effective (~$1-2/month for typical usage)
- ✅ No deployment package size limits

## Quick Update (Recommended)

After scraping new plan data:

```bash
./incremental_update.sh
```

This will:
1. Detect new scraped files since last build
2. Rebuild only changed states (fast!)
3. Sync only changed files to S3
4. Invalidate CloudFront cache
5. Track timestamp for next incremental update

**Time:** ~30 seconds - 2 minutes (vs 10+ minutes for full rebuild)

## Full Rebuild

To rebuild everything from scratch:

```bash
./update_api.sh
```

**Time:** ~10-15 minutes for all states

## Manual Steps

### 1. Build Static API

```bash
python3 build_static_api.py
```

Generates `./static_api/medicare/` with:
- 39,000+ JSON files
- States, counties, ZIP codes, plans
- ~1 GB total

### 2. Deploy to S3

```bash
aws s3 sync static_api/ s3://purlpal-medicare-api/ \
    --delete \
    --content-type "application/json" \
    --cache-control "max-age=3600"
```

### 3. Invalidate CloudFront Cache

```bash
aws cloudfront create-invalidation \
    --distribution-id E3SHXUEGZALG4E \
    --paths "/medicare/*"
```

## API Endpoints

### List All States
```
GET /medicare/states.json
```

### State Information
```
GET /medicare/state/{ST}/info.json
GET /medicare/state/NH/info.json
```

### All Plans in State
```
GET /medicare/state/{ST}/plans.json
GET /medicare/state/NH/plans.json
```

### Plans by County
```
GET /medicare/state/{ST}/county/{COUNTY}.json
GET /medicare/state/NH/county/Cheshire.json
```

### Plans by ZIP Code
```
GET /medicare/zip/{ZIPCODE}.json
GET /medicare/zip/03462.json
```

### Individual Plan Details
```
GET /medicare/plan/{PLAN_ID}.json
GET /medicare/plan/S4802_075_0.json
```

## Optimizations

### S3 Sync
- Uses `--size-only` to skip identical files
- Uses `--delete` to remove old files
- Sets `Cache-Control: max-age=3600` (1 hour browser cache)

### CloudFront
- Global edge locations
- Automatic GZIP compression
- HTTPS with wildcard certificate
- Custom domain with Route53

### Build Process
- Incremental updates track timestamp
- Only rebuilds states with new scraped data
- Parallel processing where possible

## Monitoring

### Test Endpoints
```bash
# List states
curl https://medicare.purlpal-api.com/medicare/states.json

# Get NH plans
curl https://medicare.purlpal-api.com/medicare/state/NH/plans.json

# Get specific ZIP
curl https://medicare.purlpal-api.com/medicare/zip/03462.json
```

### Check CloudFront Status
```bash
aws cloudfront get-distribution --id E3SHXUEGZALG4E \
    --query 'Distribution.Status' --output text
```

### Check S3 Sync Status
```bash
aws s3 ls s3://purlpal-medicare-api/medicare/ | head -10
```

## Cost Estimate

**Monthly costs for all 50 states:**
- S3 storage (2 GB): ~$0.05
- S3 requests (100k): ~$0.04
- CloudFront bandwidth (10 GB): ~$0.85
- Route53 hosted zone: $0.50
- **Total: ~$1.50/month**

## Troubleshooting

### CloudFront not updating?
Wait 1-2 minutes for invalidation to propagate, or check:
```bash
aws cloudfront get-invalidation \
    --distribution-id E3SHXUEGZALG4E \
    --id <INVALIDATION_ID>
```

### Build taking too long?
Use incremental update instead:
```bash
./incremental_update.sh
```

### DNS not resolving?
Custom domain DNS can take 24-48 hours to propagate. Use CloudFront URL in the meantime:
```
https://d11vrs9xl9u4t7.cloudfront.net/medicare/
```
