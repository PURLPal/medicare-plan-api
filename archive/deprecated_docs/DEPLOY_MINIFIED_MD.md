# Deploy Maryland Minified Data

## Summary

✅ **Created:** 1,178 minified ZIP files for Maryland
- Original size: 106,684 KB (104 MB)
- Minified size: 51,670 KB (50 MB)
- **Reduction: 51.6%**

## Files Created

```
static_api/medicare/
├── zip_minified/
│   ├── 19973_minified.json
│   ├── 19973_MAPD_minified.json
│   ├── 19973_PD_minified.json
│   ├── 19973_MA_minified.json
│   ├── 20058_minified.json
│   └── ... (1,178 total ZIP files)
└── mappings/
    ├── key_mapping.json
    └── value_mapping.json
```

## Deployment Commands

### 1. Upload Minified ZIP Files
```bash
aws s3 sync static_api/medicare/zip_minified/ \
  s3://purlpal-medicare-api/medicare/zip_minified/ \
  --content-type "application/json" \
  --cache-control "public, max-age=3600" \
  --exclude "*.py" \
  --exclude "__pycache__/*"
```

### 2. Upload Mapping Files
```bash
aws s3 sync static_api/medicare/mappings/ \
  s3://purlpal-medicare-api/medicare/mappings/ \
  --content-type "application/json" \
  --cache-control "public, max-age=86400"
```

### 3. Invalidate CloudFront Cache
```bash
aws cloudfront create-invalidation \
  --distribution-id E3SHXUEGZALG4E \
  --paths "/medicare/zip_minified/*" "/medicare/mappings/*"
```

## Test After Deployment

```bash
# Test minified endpoint
curl https://medicare.purlpal-api.com/medicare/zip_minified/19973_minified.json

# Test mapping files
curl https://medicare.purlpal-api.com/medicare/mappings/key_mapping.json
curl https://medicare.purlpal-api.com/medicare/mappings/value_mapping.json

# Test category-filtered endpoint
curl https://medicare.purlpal-api.com/medicare/zip_minified/19973_MAPD_minified.json
```

## Example Response (19973_minified.json)

```json
{
  "z": "19973",
  "mc": false,
  "ms": true,
  "s": ["DE", "MD"],
  "ps": "DE",
  "c": [
    {
      "f": "10005",
      "n": "Sussex County",
      "s": "DE",
      "r": 1.0,
      "pa": true,
      "pc": 42
    }
  ],
  "p": [],
  "pc": 0
}
```

## Usage in Chrome Extension

```javascript
// Load mappings once at startup
const mappings = {
  keys: await fetch('https://medicare.purlpal-api.com/medicare/mappings/key_mapping.json')
    .then(r => r.json()),
  values: await fetch('https://medicare.purlpal-api.com/medicare/mappings/value_mapping.json')
    .then(r => r.json())
};

// Store in chrome.storage for offline use
chrome.storage.local.set({ mappings });

// Fetch minified data for a ZIP
const zipData = await fetch(`https://medicare.purlpal-api.com/medicare/zip_minified/${zip}_minified.json`)
  .then(r => r.json());

// Decode values
function decode(val, mappings) {
  if (typeof val !== 'string') return val;
  
  if (val.startsWith('v')) return mappings.values.values[val] || val;
  if (val.startsWith('o')) return mappings.values.organizations[val] || val;
  if (val.startsWith('t')) return mappings.values.plan_types[val] || val;
  if (val.startsWith('nt')) return mappings.values.network_types[val] || val;
  
  return val;
}

// Example: Get plan premium
const premium = decode(zipData.p[0].pr.tmp, mappings);
// Returns: "$0.00"
```

## Generate More States

To create minified data for other states:

```bash
cd minification

# Single state
python3 minify_state_endpoint.py NY

# Multiple states
for state in AL AZ CT DE HI IA ME MT ND NE NH RI SD UT VT WV WY; do
  python3 minify_state_endpoint.py $state
done
```

## Bandwidth Savings

For a typical Chrome extension user checking 5 ZIPs:
- **Full data:** 5 × 90 KB = 450 KB
- **Minified data:** 5 × 45 KB = 225 KB
- **Savings:** 225 KB (50%)

For power users checking 20 ZIPs:
- **Full data:** 20 × 90 KB = 1.8 MB
- **Minified data:** 20 × 45 KB = 900 KB
- **Savings:** 900 KB (50%)

Plus mappings load once: 7 KB total (cacheable for 24 hours)

## Next Steps

1. ✅ Deploy MD minified data (commands above)
2. Generate minified data for all GREAT states
3. Update Chrome extension to use minified endpoints
4. Monitor bandwidth savings in CloudFront metrics
