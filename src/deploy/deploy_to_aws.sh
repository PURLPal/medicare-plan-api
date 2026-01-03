#!/bin/bash
# Deploy static Medicare API to AWS S3 + CloudFront
# Domain: purlpal-api.com

set -e

# Configuration
BUCKET_NAME="purlpal-api-medicare"
REGION="us-east-1"
DOMAIN="purlpal-api.com"
CLOUDFRONT_COMMENT="Medicare Plan API"

echo "========================================"
echo "Medicare API - AWS Deployment"
echo "========================================"
echo ""

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install it first."
    exit 1
fi

# Check if logged in
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ Not logged into AWS. Run 'aws configure' first."
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "✓ Logged in as account: $ACCOUNT_ID"
echo ""

# Step 1: Create S3 bucket
echo "Step 1: Creating S3 bucket..."
if aws s3api head-bucket --bucket "$BUCKET_NAME" 2>/dev/null; then
    echo "  Bucket $BUCKET_NAME already exists"
else
    aws s3api create-bucket \
        --bucket "$BUCKET_NAME" \
        --region "$REGION" \
        2>/dev/null || true
    echo "  ✓ Created bucket: $BUCKET_NAME"
fi

# Block public access (CloudFront will access via OAC)
aws s3api put-public-access-block \
    --bucket "$BUCKET_NAME" \
    --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
echo "  ✓ Public access blocked"
echo ""

# Step 2: Upload files
echo "Step 2: Uploading static files..."
if [ ! -d "static_api/medicare" ]; then
    echo "❌ static_api/medicare not found. Run build_static_api.py first."
    exit 1
fi

aws s3 sync static_api/ s3://$BUCKET_NAME/ \
    --delete \
    --content-type "application/json" \
    --cache-control "max-age=86400"

FILE_COUNT=$(find static_api -type f | wc -l | tr -d ' ')
echo "  ✓ Uploaded $FILE_COUNT files"
echo ""

# Step 3: Check for existing CloudFront distribution
echo "Step 3: Setting up CloudFront..."
EXISTING_DIST=$(aws cloudfront list-distributions \
    --query "DistributionList.Items[?Comment=='$CLOUDFRONT_COMMENT'].Id" \
    --output text 2>/dev/null || echo "")

if [ -n "$EXISTING_DIST" ] && [ "$EXISTING_DIST" != "None" ]; then
    echo "  Found existing distribution: $EXISTING_DIST"
    DISTRIBUTION_ID=$EXISTING_DIST
else
    echo "  Creating new CloudFront distribution..."
    echo ""
    echo "  ⚠️  Manual steps required:"
    echo ""
    echo "  1. Go to AWS Console > CloudFront > Create Distribution"
    echo "  2. Origin domain: $BUCKET_NAME.s3.$REGION.amazonaws.com"
    echo "  3. Origin access: Origin access control settings (recommended)"
    echo "  4. Create new OAC for S3"
    echo "  5. Alternate domain name (CNAME): $DOMAIN"
    echo "  6. Custom SSL certificate: Request in ACM (us-east-1)"
    echo "  7. Default root object: states.json"
    echo "  8. After creation, copy the S3 bucket policy and apply it"
    echo ""
    echo "  Or use this AWS CLI command (requires OAC setup first):"
    echo ""
    cat << 'EOF'
    # First create OAC
    aws cloudfront create-origin-access-control \
        --origin-access-control-config '{
            "Name": "purlpal-api-oac",
            "SigningProtocol": "sigv4",
            "SigningBehavior": "always",
            "OriginAccessControlOriginType": "s3"
        }'
EOF
fi
echo ""

# Step 4: Check ACM certificate
echo "Step 4: Checking SSL certificate..."
CERT_ARN=$(aws acm list-certificates \
    --region us-east-1 \
    --query "CertificateSummaryList[?DomainName=='$DOMAIN'].CertificateArn" \
    --output text 2>/dev/null || echo "")

if [ -n "$CERT_ARN" ] && [ "$CERT_ARN" != "None" ]; then
    echo "  ✓ Found certificate: $CERT_ARN"
else
    echo "  ⚠️  No certificate found for $DOMAIN"
    echo ""
    echo "  Request one with:"
    echo "  aws acm request-certificate \\"
    echo "      --domain-name $DOMAIN \\"
    echo "      --validation-method DNS \\"
    echo "      --region us-east-1"
    echo ""
    echo "  Then validate via Route 53 DNS records"
fi
echo ""

# Step 5: Route 53 setup reminder
echo "Step 5: Route 53 DNS..."
HOSTED_ZONE=$(aws route53 list-hosted-zones-by-name \
    --dns-name "$DOMAIN" \
    --query "HostedZones[0].Id" \
    --output text 2>/dev/null || echo "")

if [ -n "$HOSTED_ZONE" ] && [ "$HOSTED_ZONE" != "None" ]; then
    echo "  ✓ Found hosted zone: $HOSTED_ZONE"
    echo ""
    echo "  After CloudFront is created, add A record:"
    echo "  - Name: $DOMAIN (or subdomain)"
    echo "  - Type: A"
    echo "  - Alias: Yes"
    echo "  - Target: CloudFront distribution domain"
else
    echo "  ⚠️  No hosted zone found for $DOMAIN"
fi
echo ""

# Summary
echo "========================================"
echo "DEPLOYMENT STATUS"
echo "========================================"
echo ""
echo "✓ S3 Bucket: s3://$BUCKET_NAME"
echo "✓ Files uploaded: $FILE_COUNT"
echo ""
echo "Manual steps remaining:"
echo "  1. Create/configure CloudFront distribution"
echo "  2. Request ACM certificate (if not exists)"
echo "  3. Validate certificate via DNS"
echo "  4. Add Route 53 A record pointing to CloudFront"
echo "  5. Update S3 bucket policy for CloudFront OAC"
echo ""
echo "Expected final URL: https://$DOMAIN/medicare/zip/03462.json"
echo ""
echo "========================================"
