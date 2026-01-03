# ZIP 29401 (Charleston, SC) API Endpoints

## Overview
All Medicare plan data for ZIP code 29401 in Charleston, South Carolina.

---

## 🌐 Regular Endpoints (Full Data)

### All Plans
**URL:** `https://medicare.purlpal-api.com/medicare/zip/29401.json`
- **Plans:** 69 total (66 MAPD, 3 MA)
- **Size:** 459 KB
- **Format:** Full JSON with readable keys and values

### Priority Plans Only (Custom "Ebony" Endpoint)
**URL:** `https://medicare.purlpal-api.com/medicare/zip/29401_ebony.json`
- **Plans:** 3 curated plans
- **Size:** 11 KB
- **Plans included:**
  1. H5322-043-000: $0.00/month premium
  2. H5322-044-000: $45.00/month premium  
  3. R2604-005-000: $0.00/month premium

---

## 💾 Minified Endpoints (Compressed)

### All Plans (Minified)
**URL:** `https://medicare.purlpal-api.com/medicare/zip_minified/29401_minified.json`
- **Plans:** 69 total
- **Size:** 423 KB (8% smaller)
- **Format:** Compressed keys/values

### MAPD Plans Only (Minified)
**URL:** `https://medicare.purlpal-api.com/medicare/zip_minified/29401_MAPD_minified.json`
- **Plans:** 66 MAPD plans
- **Size:** 418 KB

### MA Plans Only (Minified)
**URL:** `https://medicare.purlpal-api.com/medicare/zip_minified/29401_MA_minified.json`
- **Plans:** 3 MA plans
- **Size:** 5.3 KB (98.8% reduction!)

---

## 🔑 Minification Mappings

To decode minified data, use these mapping files:

**Key Mapping:**  
`https://medicare.purlpal-api.com/medicare/mappings/key_mapping.json`

**Value Mapping:**  
`https://medicare.purlpal-api.com/medicare/mappings/value_mapping.json`

### Common Key Mappings:
```json
{
  "plan_count": "pc",
  "plan_id": "id",
  "plans": "p",
  "premiums": "pr",
  "deductibles": "ded",
  "benefits": "b",
  "plan_info": "pi",
  "Total monthly premium": "tmp",
  "Health premium": "hp",
  "Drug premium": "dp"
}
```

### Common Value Mappings:
```json
{
  "$0.00": "v1",
  "Not offered": "v5",
  "UnitedHealthcare": "o1",
  "Humana": "o2"
}
```

---

## 📊 Endpoint Comparison

| Endpoint | Plans | Size | Use Case |
|----------|-------|------|----------|
| Regular | 69 | 459 KB | Full details, human-readable |
| Ebony Custom | 3 | 11 KB | Priority plans comparison |
| Minified | 69 | 423 KB | Same data, 8% smaller |
| Minified MAPD | 66 | 418 KB | MAPD plans only |
| Minified MA | 3 | 5.3 KB | MA plans only, 99% smaller |

---

## 🎯 Priority Plans Details

### 1. H5322-043-000
**AARP Medicare Advantage Patriot No Rx SC-MA01 (HMO-POS)**
- Monthly Premium: $0.00
- Health Deductible: $0.00
- Drug Deductible: N/A
- Type: MAPD

### 2. H5322-044-000
**AARP Medicare Advantage from UHC SC-0006 (HMO-POS)**
- Monthly Premium: $45.00
- Health Deductible: $0.00
- Drug Deductible: $440.00
- Type: MAPD

### 3. R2604-005-000
**UHC Medicare Advantage Patriot No Rx GS-MA01 (Regional PPO)**
- Monthly Premium: $0.00
- Health Deductible: $0.00
- Drug Deductible: N/A
- Type: MAPD

---

## 💡 Usage Examples

### Fetch All Plans (JavaScript)
```javascript
const response = await fetch('https://medicare.purlpal-api.com/medicare/zip/29401.json');
const data = await response.json();
console.log(`Found ${data.plan_count} plans`);
```

### Fetch Priority Plans Only
```javascript
const response = await fetch('https://medicare.purlpal-api.com/medicare/zip/29401_ebony.json');
const data = await response.json();
console.log(`Priority plans: ${data.plan_count}`);
data.plans.forEach(plan => {
  console.log(`${plan.plan_id}: ${plan.premiums['Total monthly premium']}`);
});
```

### Fetch Minified Data
```javascript
const response = await fetch('https://medicare.purlpal-api.com/medicare/zip_minified/29401_minified.json');
const minified = await response.json();
console.log(`Found ${minified.pc} plans`); // 'pc' = plan_count
```

---

## 📝 Notes

- All endpoints return JSON with CORS enabled
- CloudFront caching: 24 hours
- Data updated: December 9, 2025
- Coverage year: 2026
- All 3 priority plans have full structured data (premiums, deductibles, benefits)

---

## 🚀 Deployment Info

- **S3 Bucket:** `purlpal-medicare-api`
- **CloudFront Distribution:** `E3SHXUEGZALG4E`
- **Base URL:** `https://medicare.purlpal-api.com/medicare`
- **Last Deployed:** December 9, 2025

---

**Questions?** All endpoints are live and ready to use!
