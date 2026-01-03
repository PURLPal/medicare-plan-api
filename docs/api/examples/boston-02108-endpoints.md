# ZIP 02108 (Boston, MA) API Endpoints

## Overview
All Medicare plan data for ZIP code 02108 in Boston, Massachusetts.

---

## 🌐 Regular Endpoints (Full Data)

### All Plans
**URL:** `https://medicare.purlpal-api.com/medicare/zip/02108.json`
- **Plans:** 63 total (52 MAPD, 11 PDP)
- **Size:** ~420 KB
- **Format:** Full JSON with readable keys and values

### MAPD Plans Only
**URL:** `https://medicare.purlpal-api.com/medicare/zip/02108_MAPD.json`
- **Plans:** 52 MAPD plans
- **Format:** Medicare Advantage plans with drug coverage

### PDP Plans Only
**URL:** `https://medicare.purlpal-api.com/medicare/zip/02108_PD.json`
- **Plans:** 11 Prescription Drug Plans
- **Format:** Standalone drug coverage

---

## 💾 Minified Endpoints (Compressed)

### All Plans (Minified)
**URL:** `https://medicare.purlpal-api.com/medicare/zip_minified/02108_minified.json`
- **Plans:** 63 total
- **Size:** ~390 KB (8% smaller)
- **Format:** Compressed keys/values

### MAPD Plans Only (Minified)
**URL:** `https://medicare.purlpal-api.com/medicare/zip_minified/02108_MAPD_minified.json`
- **Plans:** 52 MAPD plans
- **Size:** ~385 KB

### PDP Plans Only (Minified)
**URL:** `https://medicare.purlpal-api.com/medicare/zip_minified/02108_PD_minified.json`
- **Plans:** 11 PDP plans
- **Size:** ~5 KB (98% reduction!)

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
  "Humana": "o2",
  "Tufts": "o3"
}
```

---

## 📊 Endpoint Comparison

| Endpoint | Plans | Size | Use Case |
|----------|-------|------|----------|
| Regular | 63 | 420 KB | Full details, human-readable |
| Minified | 63 | 390 KB | Same data, 8% smaller |
| Minified MAPD | 52 | 385 KB | MAPD plans only |
| Minified PDP | 11 | 5 KB | PDP plans only, 99% smaller |

---

## 🎯 Sample Plans

### 1. NaviCare (HMO D-SNP)
- Monthly Premium: $0.00
- Health Deductible: $0.00
- Drug Deductible: $615.00
- Type: MAPD (Special Needs Plan)

### 2. AARP Medicare Advantage Patriot No Rx MA-MA01 (PPO)
- Monthly Premium: $0.00
- Health Deductible: $0.00
- Drug Deductible: N/A
- Type: MAPD

### 3. HealthSpring Assurance Rx (PDP)
- Monthly Premium: $139.30
- Health Deductible: N/A
- Drug Deductible: $615.00
- Type: PDP (Prescription Drug Plan)

---

## 💡 Usage Examples

### Fetch All Plans (JavaScript)
```javascript
const response = await fetch('https://medicare.purlpal-api.com/medicare/zip/02108.json');
const data = await response.json();
console.log(`Found ${data.plan_count} plans`);
```

### Filter MAPD Plans Only
```javascript
const response = await fetch('https://medicare.purlpal-api.com/medicare/zip/02108_MAPD.json');
const data = await response.json();
console.log(`MAPD plans: ${data.plan_count}`);
data.plans.forEach(plan => {
  const premium = plan.premiums['Total monthly premium'];
  console.log(`${plan.plan_info.name}: ${premium}`);
});
```

### Fetch Minified Data
```javascript
const response = await fetch('https://medicare.purlpal-api.com/medicare/zip_minified/02108_minified.json');
const minified = await response.json();
console.log(`Found ${minified.pc} plans`); // 'pc' = plan_count
```

### Find Zero Premium Plans
```javascript
const response = await fetch('https://medicare.purlpal-api.com/medicare/zip/02108.json');
const data = await response.json();
const zeroPremium = data.plans.filter(p => 
  p.premiums['Total monthly premium'] === '$0.00'
);
console.log(`Found ${zeroPremium.length} plans with $0 premium`);
```

---

## 📝 Notes

- All endpoints return JSON with CORS enabled
- CloudFront caching: 24 hours
- Data updated: December 22, 2025
- Coverage year: 2026
- Massachusetts has 649 ZIP codes with Medicare coverage
- All 63 plans have full structured data (premiums, deductibles, benefits)

---

## 🏥 Massachusetts Coverage

### ZIP Codes
- **Total MA ZIPs:** 649
- **Sample Boston ZIPs:** 02108, 02109, 02110, 02111, 02115, 02116

### Plan Types Available
- **MAPD (Medicare Advantage with Drug Coverage):** 52 plans
- **PDP (Prescription Drug Plans):** 11 plans
- **Major Carriers:** Tufts, Blue Cross Blue Shield, UnitedHealthcare, Humana

### Popular Plans in Boston Area
- Tufts Medicare Preferred HMO
- Medicare PPO Blue PlusRx
- AARP Medicare Advantage plans
- Senior Whole Health SCO (D-SNP)

---

## 🚀 Deployment Info

- **S3 Bucket:** `purlpal-medicare-api`
- **CloudFront Distribution:** `E3SHXUEGZALG4E`
- **Base URL:** `https://medicare.purlpal-api.com/medicare`
- **Last Deployed:** December 22, 2025
- **States Live:** 28 states including MA, SC, FL, CA, NY

---

## 🔗 Related Endpoints

### State Information
**URL:** `https://medicare.purlpal-api.com/medicare/state/MA/info.json`
- Massachusetts state-level information

### All MA Plans
**URL:** `https://medicare.purlpal-api.com/medicare/state/MA/plans.json`
- Complete list of all 114 Massachusetts plans

### Other Boston ZIP Codes
- `https://medicare.purlpal-api.com/medicare/zip/02109.json`
- `https://medicare.purlpal-api.com/medicare/zip/02115.json`
- `https://medicare.purlpal-api.com/medicare/zip/02116.json`

---

**Questions?** All endpoints are live and ready to use!
