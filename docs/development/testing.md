# Medicare Plan API - Testing Guide for Beginners

## Quick Start (30 seconds)

### Run All Tests
```bash
./test_medicare_api.sh
```

That's it! The script will automatically test everything.

## What You'll See

The test script will show you:
- ✅ All available states and plan counts
- ✅ Plans for specific ZIP codes
- ✅ How to filter plans by category (MAPD, MA, PD)
- ✅ Detailed plan information
- ✅ Sample ZIP codes you can try

## Understanding Plan Categories

### MAPD (Medicare Advantage with Prescription Drugs)
- **What it is:** Combined health + drug coverage
- **Good for:** People who want everything in one plan
- **Example:** "AARP Medicare Advantage from UHC"

### MA (Medicare Advantage Only)
- **What it is:** Health coverage only, no drugs
- **Good for:** People who have separate drug coverage
- **Example:** "Humana USAA Honor Giveback"

### PD (Part D - Prescription Drug Plans)
- **What it is:** Drug coverage only
- **Good for:** People who want to add drug coverage
- **Example:** "HealthSpring Assurance Rx"

## Try Your Own ZIP Code

### Basic Request
```bash
curl "https://medicare.purlpal-api.com/medicare/zip/YOUR_ZIP.json" | jq '.'
```

Replace `YOUR_ZIP` with any 5-digit ZIP code.

### Filter for MAPD Plans Only
```bash
curl "https://medicare.purlpal-api.com/medicare/zip/03462.json" | \
  jq '.plans | map(select(.category == "MAPD"))'
```

### Find Zero Premium Plans
```bash
curl "https://medicare.purlpal-api.com/medicare/zip/03462.json" | \
  jq '.plans | map(select(.premiums["Total monthly premium"] == "$0.00"))'
```

### Count Plans by Category
```bash
curl "https://medicare.purlpal-api.com/medicare/zip/03462.json" | jq '{
  total: (.plans | length),
  mapd: (.plans | map(select(.category == "MAPD")) | length),
  ma: (.plans | map(select(.category == "MA")) | length),
  pd: (.plans | map(select(.category == "PD")) | length)
}'
```

## Sample ZIP Codes to Test

| ZIP Code | City | State | Plans |
|----------|------|-------|-------|
| 03462 | Keene | NH | 14 |
| 99801 | Juneau | AK | 42 |
| 05401 | Burlington | VT | ~20 |
| 82001 | Cheyenne | WY | ~15 |
| 59801 | Missoula | MT | ~25 |
| 03820 | Dover | NH | 14 |

## Using in Chrome Extension

### Simple Example
```javascript
// Fetch plans for a ZIP code
fetch('https://medicare.purlpal-api.com/medicare/zip/03462.json')
  .then(response => response.json())
  .then(data => {
    console.log('Total plans:', data.plans.length);

    // Filter MAPD plans
    const mapdPlans = data.plans.filter(plan => plan.category === 'MAPD');
    console.log('MAPD plans:', mapdPlans.length);
  });
```

### Filter and Display
```javascript
fetch('https://medicare.purlpal-api.com/medicare/zip/03462.json')
  .then(response => response.json())
  .then(data => {
    // Get zero premium MAPD plans
    const freeMAPD = data.plans.filter(plan =>
      plan.category === 'MAPD' &&
      plan.premiums['Total monthly premium'] === '$0.00'
    );

    // Display results
    freeMAPD.forEach(plan => {
      console.log(plan.plan_info.name);
      console.log('Provider:', plan.plan_info.organization);
      console.log('---');
    });
  });
```

## API Endpoints

### Get All States
```bash
curl "https://medicare.purlpal-api.com/medicare/states.json" | jq '.'
```

### Get Plans by ZIP
```bash
curl "https://medicare.purlpal-api.com/medicare/zip/03462.json" | jq '.'
```

### Get Specific Plan Details
```bash
curl "https://medicare.purlpal-api.com/medicare/plan/S4802_075_0.json" | jq '.'
```

### Get State Information
```bash
curl "https://medicare.purlpal-api.com/medicare/state/NH/info.json" | jq '.'
```

## Common Questions

### Q: What URL should I use?
**A:** Always use `https://medicare.purlpal-api.com/medicare/`

### Q: Does it work with Chrome extensions?
**A:** Yes! CORS is fully enabled.

### Q: How do I filter plans?
**A:** Use `jq` filters or JavaScript `.filter()` - see examples above.

### Q: What's the difference between MAPD and PD?
**A:** MAPD includes both health + drugs. PD is drugs only.

### Q: How often is data updated?
**A:** When new Medicare plan data is scraped and deployed.

### Q: Are there rate limits?
**A:** No rate limits currently. Use responsibly.

## Troubleshooting

### Error: "jq: command not found"
Install jq:
```bash
# Mac
brew install jq

# Linux
sudo apt-get install jq
```

### Error: "curl: command not found"
Curl should be pre-installed on Mac/Linux. On Windows, use Git Bash.

### Empty Response
- Check if the ZIP code is valid
- Make sure you're using the correct URL
- Try a known working ZIP: 03462

### CORS Error in Browser
- Make sure you're using: `medicare.purlpal-api.com`
- Not: `d11vrs9xl9u4t7.cloudfront.net`

## Next Steps

1. ✅ Run `./test_medicare_api.sh` to see it work
2. ✅ Try your own ZIP codes
3. ✅ Practice filtering by category
4. ✅ Integrate into your Chrome extension
5. ✅ Read `API_REFERENCE.md` for complete documentation

## Need Help?

- 📖 Full API Reference: `API_REFERENCE.md`
- 🚀 Deployment Guide: `API_DEPLOYMENT.md`
- 🧪 Test Script: `./test_medicare_api.sh`
- 📧 Questions? Check the documentation first!

## Summary

**API URL:** https://medicare.purlpal-api.com/medicare/

**Main Endpoints:**
- `/states.json` - All states
- `/zip/{ZIP}.json` - Plans by ZIP code
- `/plan/{PLAN_ID}.json` - Specific plan

**Plan Categories:**
- MAPD - Medicare Advantage + Drugs
- MA - Medicare Advantage only
- PD - Part D drug plans

**Features:**
- ✅ CORS enabled
- ✅ Global CDN
- ✅ Easy filtering
- ✅ No authentication needed
