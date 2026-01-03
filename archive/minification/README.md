# Medicare Plan Data Minification

This system reduces JSON file sizes by ~56% using key and value mappings, while preserving all data.

## Overview

The minification approach:
1. **Key compression**: Long keys like `plan_info.organization` become `pi.o`
2. **Value compression**: Repeated values like `"$0.00"` become `"v40"`
3. **Structure flattening**: Top-level keys are shortened (`zip_code` → `z`, `plans` → `p`)

## Files

| File | Purpose |
|------|---------|
| `key_mapping.json` | Maps verbose keys to short codes |
| `value_mapping.json` | Maps repeated string values to codes |
| `minify_plans.py` | Script to minify ZIP files for a state |

## Usage

```bash
cd minification
python3 minify_plans.py NH    # Minify New Hampshire
python3 minify_plans.py DC    # Minify District of Columbia
```

Output goes to `static_api_minified/medicare/zip/`.

## Consistency Across States

**Yes, the mappings are consistent for all states.** The same codes always mean the same thing:

- `v40` always means `"$0.00"`
- `o0` always means `"UnitedHealthcare"`
- `pi.n` always means `plan_info.name`

This is guaranteed because:
1. All states use the same `key_mapping.json` and `value_mapping.json`
2. The mappings are based on Medicare.gov's standardized data structure
3. New values that don't have a mapping are kept as-is (no data loss)

## Data Structure

### Original Format
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
  "plans": [
    {
      "plan_id": "H6851_001_0",
      "plan_info": {
        "name": "AARP Medicare Advantage from UHC NH-2 (HMO-POS)",
        "organization": "UnitedHealthcare",
        "type": "Medicare Advantage with drug coverage"
      },
      "premiums": {
        "Total monthly premium": "$0.00",
        "Health premium": "$0.00"
      },
      "benefits": {
        "Doctor services": {
          "Primary doctor visit": "In-network: $0 copay",
          "Specialist visit": "In-network: $0-$45 copay"
        }
      }
    }
  ]
}
```

### Minified Format
```json
{
  "z": "03462",
  "mc": false,
  "ms": false,
  "s": ["NH"],
  "ps": "NH",
  "c": [
    {
      "f": "33005",
      "n": "Cheshire County",
      "s": "NH",
      "r": 1.0,
      "pa": true,
      "pc": 14
    }
  ],
  "p": [
    {
      "id": "H6851_001_0",
      "pi": {
        "n": "AARP Medicare Advantage from UHC NH-2 (HMO-POS)",
        "o": "o0",
        "t": "t0"
      },
      "pr": {
        "tmp": "v40",
        "hp": "v40"
      },
      "b": {
        "doc": {
          "pv": "v1",
          "sv": "v31"
        }
      }
    }
  ]
}
```

## Key Mappings Reference

### Top-Level Keys
| Original | Minified | Description |
|----------|----------|-------------|
| `zip_code` | `z` | ZIP code |
| `multi_county` | `mc` | Spans multiple counties |
| `multi_state` | `ms` | Spans multiple states |
| `states` | `s` | List of state abbreviations |
| `primary_state` | `ps` | Primary state |
| `counties` | `c` | County data array |
| `plans` | `p` | Plans array |
| `plan_count` | `pc` | Number of plans |

### County Keys
| Original | Minified |
|----------|----------|
| `fips` | `f` |
| `name` | `n` |
| `state` | `s` |
| `ratio` | `r` |
| `plans_available` | `pa` |
| `plan_count` | `pc` |

### Plan Keys
| Original | Minified |
|----------|----------|
| `plan_id` | `id` |
| `plan_info` | `pi` |
| `premiums` | `pr` |
| `deductibles` | `ded` |
| `maximum_out_of_pocket` | `moop` |
| `contact_info` | `ci` |
| `benefits` | `b` |
| `drug_coverage` | `dc` |
| `extra_benefits` | `eb` |

### Plan Info Keys
| Original | Minified |
|----------|----------|
| `name` | `n` |
| `organization` | `o` |
| `type` | `t` |
| `plan_type` | `pt` |

**Note:** `plan_type` is extracted from the plan name (e.g., "HMO-POS" from "AARP Medicare Advantage (HMO-POS)"). This field is added during minification and doesn't exist in the original scraped data.

### Premium Keys
| Original | Minified |
|----------|----------|
| `Total monthly premium` | `tmp` |
| `Health premium` | `hp` |
| `Drug premium` | `dp` |
| `Standard Part B premium` | `spb` |
| `Part B premium reduction` | `pbr` |

### Benefit Category Keys
| Original | Minified |
|----------|----------|
| `Doctor services` | `doc` |
| `Primary doctor visit` | `pv` |
| `Specialist visit` | `sv` |
| `Tests, labs, & imaging` | `tli` |
| `Hospital services` | `hosp` |
| `Preventive services` | `prev` |
| `Vision` | `vis` |
| `Hearing` | `hear` |
| `Preventive dental` | `pdent` |
| `Comprehensive dental` | `cdent` |

See `key_mapping.json` for the complete list.

## Value Mappings Reference

### Common Cost Values
| Code | Value |
|------|-------|
| `v0` | Not covered |
| `v1` | In-network: $0 copay |
| `v2` | In-network: $0 copay, Out-of-network: $0 copay |
| `v4` | In-network: 20% coinsurance |
| `v7` | 25% coinsurance |
| `v40` | $0.00 |
| `v41` | $615.00 |

### Organization Codes
| Code | Organization |
|------|--------------|
| `o0` | UnitedHealthcare |
| `o1` | Humana |
| `o2` | Aetna Medicare |
| `o3` | Wellcare |
| `o4` | HealthSpring |
| `o5` | Cigna |
| `o6` | Anthem |
| `o7` | Kaiser Permanente |

### Plan Type Codes (Medicare Category)
| Code | Type |
|------|------|
| `t0` | Medicare Advantage with drug coverage |
| `t1` | Drug plan (Part D) |
| `t2` | Medicare Advantage (without drug coverage) |

### Network Type Codes (Plan Structure)
| Code | Type |
|------|------|
| `nt0` | PPO |
| `nt1` | PDP |
| `nt2` | HMO-POS |
| `nt3` | HMO |
| `nt4` | HMO D-SNP |
| `nt5` | PPO D-SNP |
| `nt6` | HMO-POS D-SNP |
| `nt7` | Cost |
| `nt8` | HMO-POS C-SNP |
| `nt9` | HMO I-SNP |
| `nt10` | PPO I-SNP |
| `nt11` | HMO C-SNP |
| `nt12` | PPO C-SNP |
| `nt13` | PFFS |
| `nt14` | Regional PPO |
| `nt15` | HMO-POS I-SNP |

**SNP Types:**
- **D-SNP**: Dual Eligible Special Needs Plan (Medicare + Medicaid)
- **C-SNP**: Chronic Condition Special Needs Plan
- **I-SNP**: Institutional Special Needs Plan (nursing homes)

See `value_mapping.json` for the complete list.

## Client-Side Expansion

To use minified data, the client must:

1. **Load mapping files once** (cache them):
   ```javascript
   const keyMap = await fetch('/medicare/mappings/key_mapping.json').then(r => r.json());
   const valueMap = await fetch('/medicare/mappings/value_mapping.json').then(r => r.json());
   ```

2. **Expand minified data**:
   ```javascript
   function expandValue(val, valueMap) {
     if (typeof val !== 'string') return val;
     if (val.startsWith('v') && valueMap.values[val]) return valueMap.values[val];
     if (val.startsWith('o') && valueMap.organizations[val]) return valueMap.organizations[val];
     if (val.startsWith('t') && valueMap.plan_types[val]) return valueMap.plan_types[val];
     return val;
   }
   
   function expandPlan(minPlan, keyMap, valueMap) {
     // Recursively expand keys and values
     // ... implementation depends on your needs
   }
   ```

3. **Or use minified data directly** if you build a UI that understands the short codes.

## Size Comparison

| State | Original | Minified | Reduction |
|-------|----------|----------|-----------|
| NH (276 ZIPs) | 17,093 KB | 7,485 KB | 56.2% |

## Adding New Mappings

If new values appear frequently in scraped data:

1. Run analysis to find common values:
   ```bash
   python3 -c "... analyze script ..."
   ```

2. Add new entries to `value_mapping.json`

3. Re-run minification for affected states

**Important**: Never change existing mappings - only add new ones. This ensures backward compatibility.

## API Endpoints

When deployed, both formats will be available:

- **Full data**: `https://medicare.purlpal-api.com/medicare/zip/{zip}.json`
- **Minified**: `https://medicare.purlpal-api.com/medicare-min/zip/{zip}.json`
- **Mappings**: `https://medicare.purlpal-api.com/medicare-min/mappings/`

The client can choose which format to use based on bandwidth/performance needs.

## Category-Filtered Endpoints

Plans are categorized into three types:

| Code | Full Name |
|------|-----------|
| `MAPD` | Medicare Advantage with drug coverage |
| `PD` | Drug plan (Part D) |
| `MA` | Medicare Advantage (without drug coverage) |

### Filtered Endpoints

```
/medicare/zip/{zip}.json        # All plans
/medicare/zip/{zip}_MAPD.json   # Medicare Advantage + Drug only
/medicare/zip/{zip}_PD.json     # Drug plans only
/medicare/zip/{zip}_MA.json     # Medicare Advantage (no drug) only
```

### Response Structure

The main endpoint includes category counts:

```json
{
  "zip_code": "03462",
  "plan_count": 14,
  "plan_counts_by_category": {
    "MAPD": 4,
    "PD": 9,
    "MA": 1
  },
  "plans": [
    {
      "plan_id": "H6851_001_0",
      "category": "MAPD",
      "plan_type": "HMO-POS",
      "plan_info": { ... }
    }
  ]
}
```

## Generating Static API Files

Run `build_static_api.py` to generate all static JSON files:

```bash
python3 build_static_api.py
```

This generates:
- `/static_api/medicare/zip/{zip}.json` - All plans for each ZIP
- `/static_api/medicare/zip/{zip}_MAPD.json` - MAPD plans only
- `/static_api/medicare/zip/{zip}_PD.json` - PD plans only  
- `/static_api/medicare/zip/{zip}_MA.json` - MA plans only
- `/static_api/medicare/state/{ST}/info.json` - State info
- `/static_api/medicare/state/{ST}/plans.json` - All plans in state
- `/static_api/medicare/plan/{plan_id}.json` - Individual plan details
- `/static_api/medicare/states.json` - Index of all states

## Deployment

Upload to S3:
```bash
aws s3 sync static_api/ s3://purlpal-medicare-api/ --content-type "application/json"
```

Invalidate CloudFront cache:
```bash
aws cloudfront create-invalidation --distribution-id E3SHXUEGZALG4E --paths "/medicare/*"
```
