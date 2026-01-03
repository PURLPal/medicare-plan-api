# ZIP 85001 (Phoenix, AZ) API Endpoints

## Overview
All Medicare plan data for ZIP code 85001 in Phoenix, Arizona.

---

## 🌐 Regular Endpoints (Full Data)

### All Plans
**URL:** `https://medicare.purlpal-api.com/medicare/zip/85001.json`
- **Plans:** 98 total (88 MAPD, 10 PDP)
- **Size:** ~567 KB
- **Format:** Full JSON with readable keys and values

### MAPD Plans Only
**URL:** `https://medicare.purlpal-api.com/medicare/zip/85001_MAPD.json`
- **Plans:** 88 MAPD plans
- **Format:** Medicare Advantage plans with drug coverage

### PDP Plans Only
**URL:** `https://medicare.purlpal-api.com/medicare/zip/85001_PD.json`
- **Plans:** 10 Prescription Drug Plans
- **Format:** Standalone drug coverage

---

## 💾 Minified Endpoints (Compressed)

### All Plans (Minified)
**URL:** `https://medicare.purlpal-api.com/medicare/zip_minified/85001_minified.json`
- **Plans:** 98 total
- **Size:** ~520 KB (8% smaller)
- **Format:** Compressed keys/values

### MAPD Plans Only (Minified)
**URL:** `https://medicare.purlpal-api.com/medicare/zip_minified/85001_MAPD_minified.json`
- **Plans:** 88 MAPD plans
- **Size:** ~510 KB

### PDP Plans Only (Minified)
**URL:** `https://medicare.purlpal-api.com/medicare/zip_minified/85001_PD_minified.json`
- **Plans:** 10 PDP plans
- **Size:** ~10 KB (98% reduction!)

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
  "Aetna": "o3"
}
```

---

## 📊 Endpoint Comparison

| Endpoint | Plans | Size | Use Case |
|----------|-------|------|----------|
| Regular | 98 | 567 KB | Full details, human-readable |
| Minified | 98 | 520 KB | Same data, 8% smaller |
| Minified MAPD | 88 | 510 KB | MAPD plans only |
| Minified PDP | 10 | 10 KB | PDP plans only, 98% smaller |

---

## 🎯 Sample Plans

### 1. Aetna Medicare Eagle (PPO)
- Monthly Premium: $0.00
- Health Premium: $0.00
- Drug Premium: Included
- Type: PPO

### 2. Blue Best Life Classic (HMO)
- Monthly Premium: $0.00
- Health Premium: $0.00
- Drug Premium: Included
- Type: HMO

### 3. Aetna Medicare Elite (PPO)
- Monthly Premium: $0.00
- Health Premium: $0.00
- Drug Premium: Included
- Type: PPO

---

## 💡 Usage Examples

### Fetch All Plans (JavaScript)
```javascript
const response = await fetch('https://medicare.purlpal-api.com/medicare/zip/85001.json');
const data = await response.json();
console.log(`Found ${data.plan_count} plans`);
```

### Filter MAPD Plans Only
```javascript
const response = await fetch('https://medicare.purlpal-api.com/medicare/zip/85001_MAPD.json');
const data = await response.json();
console.log(`MAPD plans: ${data.plan_count}`);
data.plans.forEach(plan => {
  const premium = plan.premiums['Total monthly premium'];
  console.log(`${plan.plan_info.name}: ${premium}`);
});
```

### Fetch Minified Data
```javascript
const response = await fetch('https://medicare.purlpal-api.com/medicare/zip_minified/85001_minified.json');
const minified = await response.json();
console.log(`Found ${minified.pc} plans`); // 'pc' = plan_count
```

### Find Zero Premium Plans
```javascript
const response = await fetch('https://medicare.purlpal-api.com/medicare/zip/85001.json');
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
- Arizona has 505 ZIP codes with Medicare coverage
- All 98 plans have full structured data (premiums, deductibles, benefits)

---

## 🏥 Arizona Coverage

### ZIP Codes
- **Total AZ ZIPs:** 505
- **Sample Phoenix ZIPs:** 85001, 85003, 85004, 85006, 85007, 85008
- **Other Major Cities:** Tucson (85701), Mesa (85201), Scottsdale (85250)

### Plan Types Available
- **MAPD (Medicare Advantage with Drug Coverage):** 88 plans
- **PDP (Prescription Drug Plans):** 10 plans
- **Major Carriers:** Aetna, UnitedHealthcare, Humana, Blue Cross Blue Shield

### Popular Plans in Phoenix Area
- Aetna Medicare Eagle (PPO)
- UnitedHealthcare Dual Complete (HMO D-SNP)
- Humana Gold Plus (HMO)
- Blue Medicare Advantage (HMO)

---

## 🚀 Deployment Info

- **S3 Bucket:** `purlpal-medicare-api`
- **CloudFront Distribution:** `E3SHXUEGZALG4E`
- **Base URL:** `https://medicare.purlpal-api.com/medicare`
- **Last Deployed:** December 22, 2025
- **States Live:** 29 states including AZ, MA, SC, FL, CA, NY

---

## 🔗 Related Endpoints

### State Information
**URL:** `https://medicare.purlpal-api.com/medicare/state/AZ/info.json`
- Arizona state-level information

### All AZ Plans
**URL:** `https://medicare.purlpal-api.com/medicare/state/AZ/plans.json`
- Complete list of all 143 Arizona plans

### Other Phoenix ZIP Codes
- `https://medicare.purlpal-api.com/medicare/zip/85003.json`
- `https://medicare.purlpal-api.com/medicare/zip/85006.json`
- `https://medicare.purlpal-api.com/medicare/zip/85007.json`

### Other Arizona Cities
- **Tucson:** `https://medicare.purlpal-api.com/medicare/zip/85701.json` (92 plans)
- **Mesa:** `https://medicare.purlpal-api.com/medicare/zip/85201.json`
- **Scottsdale:** `https://medicare.purlpal-api.com/medicare/zip/85250.json`
- **Flagstaff:** `https://medicare.purlpal-api.com/medicare/zip/86001.json`

---

**Questions?** All endpoints are live and ready to use!
