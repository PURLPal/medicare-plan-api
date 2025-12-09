# Minified Data Endpoints Guide

## Overview
Minified endpoints reduce file sizes by ~52% using key and value compression, perfect for bandwidth-constrained clients like Chrome extensions.

## Maryland Minified Data (Created Dec 9, 2025)

**Status:** ✅ Generated 1,178 minified ZIP files for Maryland
- **Original size:** 106,684 KB
- **Minified size:** 51,670 KB  
- **Reduction:** 51.6%

## Endpoint Format

```
https://medicare.purlpal-api.com/medicare/zip_minified/{zipcode}_minified.json
```

### Examples
```bash
# Main endpoint (all plans)
curl https://medicare.purlpal-api.com/medicare/zip_minified/19973_minified.json

# Category-filtered endpoints
curl https://medicare.purlpal-api.com/medicare/zip_minified/19973_MAPD_minified.json
curl https://medicare.purlpal-api.com/medicare/zip_minified/19973_PD_minified.json
curl https://medicare.purlpal-api.com/medicare/zip_minified/19973_MA_minified.json
```

## Data Structure

### Minified Response
```json
{
  "z": "19973",           // zip_code
  "mc": false,            // multi_county
  "ms": true,             // multi_state
  "s": ["DE", "MD"],      // states
  "ps": "DE",             // primary_state
  "c": [                  // counties
    {
      "f": "10005",       // fips
      "n": "Sussex County", // name
      "s": "DE",          // state
      "r": 1.0,           // ratio
      "pa": true,         // plans_available
      "pc": 42            // plan_count
    }
  ],
  "p": [                  // plans
    {
      "id": "H3959_084_0",
      "category": "MAPD",
      "pt": "nt11",       // network type: HMO C-SNP
      "pi": {             // plan_info
        "n": "Aetna Medicare Chronic Care (HMO C-SNP)",
        "o": "o2",        // organization: Aetna Medicare
        "t": "MAPD",      // Medicare category
        "id": "H3959-084-0"
      },
      "pr": {             // premiums
        "tmp": "v40",     // Total monthly premium: $0.00
        "hp": "v40",      // Health premium: $0.00
        "dp": "v40",      // Drug premium: $0.00
        "spb": "v42",     // Standard Part B: $202.90
        "pbr": "v14"      // Part B reduction: Not offered
      },
      "ded": {            // deductibles
        "hd": "v40",      // Health deductible: $0.00
        "dd": "v41"       // Drug deductible: $615.00
      },
      "moop": { ... },    // maximum_out_of_pocket
      "b": { ... }        // benefits
    }
  ],
  "pc": 42               // plan_count
}
```

## Decoding Minified Values

Clients need to load mapping files once and cache them:

```javascript
// Load mappings (do this once on app startup)
const keyMap = await fetch('https://medicare.purlpal-api.com/medicare/mappings/key_mapping.json')
  .then(r => r.json());
const valueMap = await fetch('https://medicare.purlpal-api.com/medicare/mappings/value_mapping.json')
  .then(r => r.json());

// Decode a value
function decodeValue(val, valueMap) {
  if (typeof val !== 'string') return val;
  
  // Check value codes (v40 = $0.00, v41 = $615.00, etc.)
  if (val.startsWith('v') && valueMap.values[val]) {
    return valueMap.values[val];
  }
  
  // Check organization codes (o2 = Aetna Medicare, etc.)
  if (val.startsWith('o') && valueMap.organizations[val]) {
    return valueMap.organizations[val];
  }
  
  // Check plan type codes (t0 = Medicare Advantage with drug coverage, etc.)
  if (val.startsWith('t') && valueMap.plan_types[val]) {
    return valueMap.plan_types[val];
  }
  
  // Check network type codes (nt11 = HMO C-SNP, etc.)
  if (val.startsWith('nt') && valueMap.network_types[val]) {
    return valueMap.network_types[val];
  }
  
  return val; // Not encoded
}

// Example: decode premium
const totalPremium = decodeValue(plan.pr.tmp, valueMap);
// Returns: "$0.00"
```

## Common Value Codes

### Premiums
- `v40` = $0.00
- `v41` = $615.00
- `v42` = $202.90
- `v14` = Not offered

### Organizations
- `o0` = UnitedHealthcare
- `o1` = Humana
- `o2` = Aetna Medicare
- `o3` = Wellcare
- `o4` = HealthSpring
- `o5` = Cigna
- `o6` = Anthem
- `o7` = Kaiser Permanente

### Network Types
- `nt0` = PPO
- `nt1` = PDP
- `nt2` = HMO-POS
- `nt3` = HMO
- `nt11` = HMO C-SNP (Chronic Condition Special Needs Plan)

See full mappings at:
- https://medicare.purlpal-api.com/medicare/mappings/key_mapping.json
- https://medicare.purlpal-api.com/medicare/mappings/value_mapping.json

## Generate Minified Data for Other States

```bash
cd minification
python3 minify_state_endpoint.py AL   # Alabama
python3 minify_state_endpoint.py NY   # New York
python3 minify_state_endpoint.py CA   # California
```

## Deploy to Production

```bash
# Upload minified files
aws s3 sync static_api/medicare/zip_minified/ \
  s3://purlpal-medicare-api/medicare/zip_minified/ \
  --content-type "application/json" \
  --cache-control "public, max-age=3600"

# Upload mapping files
aws s3 sync static_api/medicare/mappings/ \
  s3://purlpal-medicare-api/medicare/mappings/ \
  --content-type "application/json" \
  --cache-control "public, max-age=86400"

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id E3SHXUEGZALG4E \
  --paths "/medicare/zip_minified/*" "/medicare/mappings/*"
```

## When to Use Minified vs Full Data

### Use Minified When:
- ✅ Building Chrome extensions (bandwidth limited)
- ✅ Mobile apps
- ✅ Need to fetch many ZIPs quickly
- ✅ Client can cache and decode mappings

### Use Full Data When:
- ✅ Server-side processing
- ✅ One-time queries
- ✅ Don't want decoding complexity
- ✅ Need human-readable debugging

## File Size Comparison

| ZIP Code | Full | Minified | Reduction |
|----------|------|----------|-----------|
| 19973 (42 plans) | 199 KB | 78 KB | 61% |
| 21201 (0 plans) | 342 B | 145 B | 58% |

**Average reduction:** ~52% for Maryland

## States Available (Minified)

Currently minified:
- ✅ Maryland (MD) - 1,178 ZIPs

To generate more states, run:
```bash
cd minification
python3 minify_state_endpoint.py <STATE_ABBREV>
```
