# Chrome Extension Quick Start - Medicare Plan API

## For Your Teammate (In a Hurry!)

### 1. Get the API URL

After deployment, you'll have a URL like:
```
https://abc123xyz.lambda-url.us-east-1.on.aws
```

Save this as your `API_BASE_URL`.

### 2. Copy This Code Into Your Extension

**File: `chrome_extension_example.js`** (in this directory)

The complete example is ready to use! Just:

1. Copy `chrome_extension_example.js` to your extension folder
2. Update line 11:
   ```javascript
   const API_BASE_URL = 'https://YOUR-ACTUAL-URL.lambda-url.us-east-1.on.aws';
   ```
3. Import it in your extension code

### 3. Minimal Working Example

If you want the absolute minimum code:

```javascript
// medicare-api.js
const API_URL = 'https://YOUR-URL.lambda-url.us-east-1.on.aws';

async function getPlansForZip(state, zipCode) {
  const response = await fetch(`${API_URL}/${state}/${zipCode}?details=0`);
  if (!response.ok) throw new Error(`API Error: ${response.status}`);
  return await response.json();
}

// Usage
const plans = await getPlansForZip('nh', '03462');
console.log(plans);
```

That's it! No special CORS headers, no auth, just fetch.

### 4. API Endpoints Cheat Sheet

```javascript
// List all states
GET /states

// Get plans for a ZIP (summary - fast)
GET /{state}/{zipCode}?details=0

// Get plans with full details (slower, bigger)
GET /{state}/{zipCode}

// Get specific plan details
GET /{state}/plan/{planId}

// List counties in a state
GET /{state}/counties
```

### 5. Example Usage Patterns

#### Pattern 1: User enters ZIP code

```javascript
async function handleZipInput(zipCode) {
  // Step 1: Get summary (fast)
  const data = await fetch(`${API_URL}/nh/${zipCode}?details=0`)
    .then(r => r.json());

  // Step 2: Check if multi-county
  if (data.multi_county) {
    // Show user: "Pick your county"
    displayCountyChoices(data.counties);
  } else {
    // Single county - show plans
    const county = Object.keys(data.counties)[0];
    displayPlans(data.counties[county].plans);
  }
}
```

#### Pattern 2: Show plan details on click

```javascript
async function showPlanDetails(planId) {
  const plan = await fetch(`${API_URL}/nh/plan/${planId}`)
    .then(r => r.json());

  // Show in modal/popup
  document.getElementById('plan-name').textContent = plan.summary.plan_name;
  document.getElementById('premium').textContent = plan.details.premiums['Total monthly premium'];
  document.getElementById('address').textContent = plan.details.contact_info['Plan address'];
}
```

### 6. States Available

- `ak` - Alaska (1 plan)
- `nh` - New Hampshire (25 plans)
- `vt` - Vermont (14 plans)
- `wy` - Wyoming (25 plans)

### 7. Response Structure

**Summary mode** (`?details=0`):
```json
{
  "zip_code": "03462",
  "state": "New Hampshire",
  "multi_county": false,
  "counties": {
    "Cheshire": {
      "plan_count": 14,
      "plans": [
        {
          "contract_plan_segment_id": "S4802_075_0",
          "plan_name": "Wellcare Classic (PDP)",
          "organization": "Wellcare",
          "has_scraped_details": true
        }
      ]
    }
  }
}
```

**Full details mode**:
Same structure but each plan includes:
```json
{
  "summary": {...},
  "details": {
    "premiums": {...},
    "deductibles": {...},
    "contact_info": {"Plan address": "..."},
    "benefits": {...}
  }
}
```

### 8. Multi-County ZIP Example

Some ZIPs span multiple counties. Show user a choice:

```json
{
  "zip_code": "03602",
  "multi_county": true,
  "counties": {
    "Cheshire": {
      "percentage": 68.3,
      "plan_count": 14
    },
    "Sullivan": {
      "percentage": 31.7,
      "plan_count": 12
    }
  }
}
```

UI: "Your ZIP code is in multiple counties. Which county do you live in?"
- ⚪ Cheshire (14 plans)
- ⚪ Sullivan (12 plans)

### 9. Error Handling

```javascript
async function getPlans(state, zipCode) {
  try {
    const response = await fetch(`${API_URL}/${state}/${zipCode}?details=0`);

    if (response.status === 404) {
      return { error: 'ZIP code not found' };
    }

    if (!response.ok) {
      return { error: `API Error: ${response.status}` };
    }

    return await response.json();
  } catch (error) {
    console.error('Network error:', error);
    return { error: 'Network error' };
  }
}
```

### 10. Manifest Requirements

Your `manifest.json` needs permission to call the API:

```json
{
  "manifest_version": 3,
  "name": "Medicare Helper",
  "version": "1.0",
  "host_permissions": [
    "https://*.lambda-url.us-east-1.on.aws/*"
  ]
}
```

That's it! No special CORS setup needed on your end.

## File Locations

All examples are in:
```
medicare_overview_test/
├── chrome_extension_example.js    ← FULL EXAMPLE (copy this!)
├── CHROME_EXTENSION_QUICK_START.md ← This file
├── CORS_SETUP.md                   ← Technical CORS details
└── lambda_function.py              ← The Lambda function (deployed to AWS)
```

## Quick Test

Once deployed, test it:

```bash
# Replace with your actual URL
API_URL="https://your-url.lambda-url.us-east-1.on.aws"

# Test health
curl "$API_URL/health"

# Test NH ZIP
curl "$API_URL/nh/03462?details=0" | jq .

# Test plan detail
curl "$API_URL/nh/plan/S4802_075_0" | jq .
```

## Questions?

- **CORS issues?** See `CORS_SETUP.md` - but you shouldn't have any!
- **Deployment?** See `DEPLOYMENT_GUIDE.md`
- **More examples?** See `chrome_extension_example.js` (400+ lines of examples)

---

**TL;DR:**
1. Copy `chrome_extension_example.js`
2. Update `API_BASE_URL`
3. Use `fetch()` - that's it!
