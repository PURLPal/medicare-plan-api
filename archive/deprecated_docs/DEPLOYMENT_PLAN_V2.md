# Medicare API Deployment Plan v2

## Architecture: Static JSON + CloudFront + Custom Domain

```
Browser Extension
    ↓
https://purlpal-api.com/medicare/zip/03462.json
    ↓
CloudFront (CDN - caches globally)
    ↓
S3 Bucket (static JSON files)
```

## URL Structure

Base URL: `https://medicare.purlpal-api.com/medicare`

### Endpoints

| Endpoint | Description | Example |
|----------|-------------|---------|
| `/zip/{zip}.json` | Plans for ZIP code | `/zip/03462.json` |
| `/states.json` | List of available states | `/states.json` |
| `/state/{ST}/info.json` | State info & stats | `/state/NH/info.json` |
| `/state/{ST}/plans.json` | All plans in state | `/state/NH/plans.json` |
| `/plan/{plan_id}.json` | Individual plan details | `/plan/S4802_075_0.json` |

### Example Response: `/zip/03462.json`

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
      "state": "NH"
    }
  ],
  "plans": [
    {
      "plan_id": "S4802_075_0",
      "plan_name": "Wellcare Classic (PDP)",
      "organization": "Wellcare",
      "type": "PDP",
      "monthly_premium": "$0.00",
      "drug_deductible": "$615.00",
      "star_rating": "3.5",
      "details_url": "/plan/S4802_075_0.json"
    }
  ],
  "plan_count": 14,
  "generated_at": "2025-12-08T10:00:00Z"
}
```

## AWS Setup

### 1. S3 Bucket
- Bucket name: `purlpal-api-medicare` (or similar)
- Region: us-east-1 (required for CloudFront)
- Public access: Blocked (CloudFront only)
- Structure:
  ```
  /medicare/
    /zip/
      03462.json
      03461.json
      ...
    /state/
      /NH/
        info.json
        plans.json
      /VT/
        ...
    /plan/
      S4802_075_0.json
      ...
    states.json
  ```

### 2. CloudFront Distribution
- Origin: S3 bucket
- Custom domain: `purlpal-api.com`
- SSL Certificate: ACM (free, auto-renew)
- Cache behavior:
  - Default TTL: 86400 (24 hours)
  - Max TTL: 604800 (7 days)
- CORS: Enabled for browser extension

### 3. Route 53
- A record: `purlpal-api.com` → CloudFront distribution
- (or subdomain like `api.purlpal-api.com`)

### 4. ACM Certificate
- Domain: `purlpal-api.com` (and `*.purlpal-api.com`)
- Region: us-east-1 (required for CloudFront)
- Validation: DNS (add CNAME to Route 53)

## File Generation

### Total Files to Generate
- ZIP files: ~39,298 (one per ZIP code)
- State files: ~100 (info + plans per state)
- Plan files: ~500+ (one per unique plan)
- Index: 1 (states.json)

**Total: ~40,000 files, ~200-300 MB**

### Generation Script
`build_static_api.py` will:
1. Load unified ZIP mapping
2. Load all scraped plan data
3. Generate JSON for each ZIP
4. Generate state index files
5. Generate individual plan files
6. Upload to S3

## Browser Extension Integration

```javascript
const API_BASE = 'https://purlpal-api.com/medicare';

async function getPlansForZip(zipCode) {
  const response = await fetch(`${API_BASE}/zip/${zipCode}.json`);
  if (!response.ok) {
    if (response.status === 404) {
      return { error: 'ZIP not found or state not yet covered' };
    }
    throw new Error(`API error: ${response.status}`);
  }
  return await response.json();
}

// Usage
const data = await getPlansForZip('03462');
console.log(`Found ${data.plan_count} plans in ${data.primary_state}`);
```

## Costs (Estimated)

| Service | Cost |
|---------|------|
| S3 Storage (300 MB) | ~$0.01/month |
| S3 Requests | ~$0.0004/1000 GET |
| CloudFront (1M requests) | ~$0.85/month |
| CloudFront (data transfer) | ~$0.085/GB |
| Route 53 | ~$0.50/month |
| ACM Certificate | FREE |

**Estimated total: $1-5/month** for moderate traffic

## Deployment Steps

1. [ ] Create S3 bucket
2. [ ] Request ACM certificate for purlpal-api.com
3. [ ] Validate certificate via Route 53
4. [ ] Create CloudFront distribution
5. [ ] Configure Route 53 A record
6. [ ] Run build_static_api.py to generate files
7. [ ] Upload files to S3
8. [ ] Test endpoints
9. [ ] Update browser extension API_BASE

## Update Process

When new plans are scraped:
1. Run `build_static_api.py`
2. Sync to S3: `aws s3 sync ./static_api/ s3://bucket/medicare/`
3. Invalidate CloudFront cache (optional, or wait for TTL)

## Advantages

- ✅ No Lambda cold starts
- ✅ Global CDN caching (fast everywhere)
- ✅ Extremely cheap at scale
- ✅ Simple to update (just upload new JSON)
- ✅ Custom domain with HTTPS
- ✅ Works perfectly with browser extensions
- ✅ No server to maintain

## Limitations

- Static data (no real-time queries)
- Updates require regenerating files
- No complex filtering (client-side only)

---

## Deployed Infrastructure

| Resource | Value |
|----------|-------|
| S3 Bucket | `purlpal-medicare-api` |
| CloudFront Distribution | `E3SHXUEGZALG4E` |
| CloudFront Domain | `d11vrs9xl9u4t7.cloudfront.net` |
| Custom Domain | `medicare.purlpal-api.com` |
| ACM Certificate | `*.purlpal-api.com` (wildcard) |
| Route 53 Zone | `Z021251924IHQG0BSL35F` |

---
*Created: 2025-12-08*
