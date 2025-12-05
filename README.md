# Medicare Plan API

AWS Lambda-based API for looking up Medicare Advantage plans by ZIP code. Supports Alaska, New Hampshire, Vermont, and Wyoming.

## Quick Start

### For Chrome Extension Developers

See **[CHROME_EXTENSION_QUICK_START.md](CHROME_EXTENSION_QUICK_START.md)** for integration guide.

### For Deployment

1. Deploy to AWS Lambda:
   ```bash
   ./deploy_lambda.sh
   ```

2. Test the deployed API:
   ```bash
   export LAMBDA_URL='https://your-url.lambda-url.us-east-1.on.aws'
   ./test_api.sh
   ```

## API Endpoints

- `GET /health` - Health check
- `GET /states` - List all supported states
- `GET /{state}/{zipCode}` - Get plans for ZIP code
- `GET /{state}/{zipCode}?details=0` - Get plan summaries (faster, smaller)
- `GET /{state}/plan/{planId}` - Get specific plan details
- `GET /{state}/counties` - List counties in a state

## Supported States

- Alaska (AK) - 1 plan
- New Hampshire (NH) - 25 plans
- Vermont (VT) - 14 plans
- Wyoming (WY) - 25 plans

## Data Coverage

- **610 plans** with full scraped details (97.6% coverage)
- **39 counties** across 4 states
- **854 ZIP codes** mapped to counties

## Documentation

- **[FILE_GUIDE.md](FILE_GUIDE.md)** - Index of all files
- **[CHROME_EXTENSION_QUICK_START.md](CHROME_EXTENSION_QUICK_START.md)** - Chrome Extension integration
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Complete deployment walkthrough
- **[AWS_LAMBDA_SUMMARY.md](AWS_LAMBDA_SUMMARY.md)** - Quick deployment reference
- **[CORS_SETUP.md](CORS_SETUP.md)** - CORS configuration details
- **[CORS_SECURITY_NOTES.md](CORS_SECURITY_NOTES.md)** - Why `AllowOrigins: ["*"]` is safe
- **[API_ARCHITECTURE.md](API_ARCHITECTURE.md)** - How the caching system works

## Example Usage

```javascript
const API_URL = 'https://your-url.lambda-url.us-east-1.on.aws';

// Get plans for a ZIP code (summary mode - fast)
const response = await fetch(`${API_URL}/nh/03462?details=0`);
const data = await response.json();

console.log(data);
// {
//   "zip_code": "03462",
//   "state": "New Hampshire",
//   "multi_county": false,
//   "counties": {
//     "Cheshire": {
//       "plan_count": 14,
//       "plans": [...]
//     }
//   }
// }
```

## CORS Support

API is configured with `AllowOrigins: ["*"]` for Chrome Extension compatibility. See [CORS_SECURITY_NOTES.md](CORS_SECURITY_NOTES.md) for details.

## Architecture

- **AWS Lambda** with Function URLs (no API Gateway needed)
- **Pre-computed county caches** bundled in deployment package (~2 MB)
- **Python 3.12** runtime
- **Serverless** - no servers to manage
- **Free tier eligible** - zero cost for typical usage

## Development

### Rebuild County Caches

After scraping new plan data:

```bash
python3 build_all_county_caches.py
```

### Test Locally

```bash
python3 lambda_function.py
```

### Deploy to AWS

```bash
./deploy_lambda.sh
```

## License

Public domain - Medicare plan data is publicly available from Medicare.gov.

## Questions?

See [FILE_GUIDE.md](FILE_GUIDE.md) for where to find specific documentation.
