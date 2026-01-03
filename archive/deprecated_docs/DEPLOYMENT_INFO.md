# Deployment Information

## Lambda Function URL

```
https://thl4l5z7inky2smh6qte6ewfuy0gavym.lambda-url.us-east-1.on.aws
```

## Quick Test Commands

```bash
# Health check
curl "https://thl4l5z7inky2smh6qte6ewfuy0gavym.lambda-url.us-east-1.on.aws/health"

# List states
curl "https://thl4l5z7inky2smh6qte6ewfuy0gavym.lambda-url.us-east-1.on.aws/states"

# NH ZIP code
curl "https://thl4l5z7inky2smh6qte6ewfuy0gavym.lambda-url.us-east-1.on.aws/nh/03462?details=0"

# VT ZIP code
curl "https://thl4l5z7inky2smh6qte6ewfuy0gavym.lambda-url.us-east-1.on.aws/vt/05401?details=0"

# WY ZIP code
curl "https://thl4l5z7inky2smh6qte6ewfuy0gavym.lambda-url.us-east-1.on.aws/wy/82001?details=0"

# AK ZIP code
curl "https://thl4l5z7inky2smh6qte6ewfuy0gavym.lambda-url.us-east-1.on.aws/ak/99501?details=0"

# Specific plan details
curl "https://thl4l5z7inky2smh6qte6ewfuy0gavym.lambda-url.us-east-1.on.aws/nh/plan/S4802_075_0"
```

## Test Using test_api.sh

```bash
export LAMBDA_URL='https://thl4l5z7inky2smh6qte6ewfuy0gavym.lambda-url.us-east-1.on.aws'
./test_api.sh
```

Or:

```bash
./test_api.sh https://thl4l5z7inky2smh6qte6ewfuy0gavym.lambda-url.us-east-1.on.aws
```

## Deployment Details

- **Function Name**: medicare-plan-api
- **Region**: us-east-1
- **Runtime**: Python 3.12
- **Memory**: 512 MB
- **Timeout**: 30 seconds
- **Profile**: silverman
- **IAM Role**: lambda-medicare-api-role
- **CORS**: AllowOrigins: ["*"]

## Chrome Extension Integration

The `chrome_extension_example.js` file has been updated with this Lambda URL.

Just copy the file to your Chrome Extension and start using it!

## Deployed

- **Date**: December 5, 2025
- **AWS Account**: 677276098722
- **Package Size**: ~232 KB (zipped)

## Data

- 4 states (AK, NH, VT, WY)
- 884 ZIP codes
- 39 counties
- 625 plans (610 with full details - 97.6% coverage)
