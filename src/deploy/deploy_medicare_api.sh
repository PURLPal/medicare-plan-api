#!/bin/bash
# Deploy Medicare Plan API to medicare.purlpal-api.com
# Uses S3 + CloudFront with existing ACM wildcard certificate

set -e

# Configuration
BUCKET_NAME="purlpal-medicare-api"
REGION="us-east-1"
SUBDOMAIN="medicare.purlpal-api.com"
HOSTED_ZONE_ID="Z021251924IHQG0BSL35F"
WILDCARD_CERT_ARN="arn:aws:acm:us-east-1:677276098722:certificate/7b9433c5-c362-4901-9bb8-3b06d683f0fa"

echo "========================================"
echo "Medicare Plan API Deployment"
echo "Target: https://$SUBDOMAIN"
echo "========================================"
echo ""

# Step 1: Create S3 bucket
echo "Step 1: Creating S3 bucket..."
if aws s3api head-bucket --bucket "$BUCKET_NAME" 2>/dev/null; then
    echo "  ✓ Bucket $BUCKET_NAME already exists"
else
    aws s3api create-bucket \
        --bucket "$BUCKET_NAME" \
        --region "$REGION"
    echo "  ✓ Created bucket: $BUCKET_NAME"
fi

# Block public access
aws s3api put-public-access-block \
    --bucket "$BUCKET_NAME" \
    --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" 2>/dev/null || true
echo "  ✓ Public access blocked (CloudFront only)"
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

# Step 3: Create Origin Access Control
echo "Step 3: Setting up Origin Access Control..."
OAC_ID=$(aws cloudfront list-origin-access-controls \
    --query "OriginAccessControlList.Items[?Name=='purlpal-medicare-oac'].Id" \
    --output text 2>/dev/null || echo "")

if [ -z "$OAC_ID" ] || [ "$OAC_ID" == "None" ]; then
    OAC_RESULT=$(aws cloudfront create-origin-access-control \
        --origin-access-control-config '{
            "Name": "purlpal-medicare-oac",
            "Description": "OAC for Medicare API S3 bucket",
            "SigningProtocol": "sigv4",
            "SigningBehavior": "always",
            "OriginAccessControlOriginType": "s3"
        }' 2>/dev/null)
    OAC_ID=$(echo "$OAC_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['OriginAccessControl']['Id'])")
    echo "  ✓ Created OAC: $OAC_ID"
else
    echo "  ✓ Using existing OAC: $OAC_ID"
fi
echo ""

# Step 4: Check for existing CloudFront distribution
echo "Step 4: Setting up CloudFront distribution..."
DIST_ID=$(aws cloudfront list-distributions \
    --query "DistributionList.Items[?contains(Aliases.Items, '$SUBDOMAIN')].Id | [0]" \
    --output text 2>/dev/null || echo "")

if [ -n "$DIST_ID" ] && [ "$DIST_ID" != "None" ] && [ "$DIST_ID" != "null" ]; then
    echo "  ✓ Found existing distribution: $DIST_ID"
    CLOUDFRONT_DOMAIN=$(aws cloudfront get-distribution --id "$DIST_ID" \
        --query "Distribution.DomainName" --output text)
else
    echo "  Creating new CloudFront distribution..."
    
    # Create distribution config
    cat > /tmp/cf-config.json << EOF
{
    "CallerReference": "medicare-api-$(date +%s)",
    "Comment": "Medicare Plan API - $SUBDOMAIN",
    "DefaultCacheBehavior": {
        "TargetOriginId": "S3-$BUCKET_NAME",
        "ViewerProtocolPolicy": "redirect-to-https",
        "AllowedMethods": {
            "Quantity": 2,
            "Items": ["GET", "HEAD"],
            "CachedMethods": {
                "Quantity": 2,
                "Items": ["GET", "HEAD"]
            }
        },
        "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
        "Compress": true
    },
    "Origins": {
        "Quantity": 1,
        "Items": [
            {
                "Id": "S3-$BUCKET_NAME",
                "DomainName": "$BUCKET_NAME.s3.$REGION.amazonaws.com",
                "OriginPath": "",
                "S3OriginConfig": {
                    "OriginAccessIdentity": ""
                },
                "OriginAccessControlId": "$OAC_ID"
            }
        ]
    },
    "Enabled": true,
    "Aliases": {
        "Quantity": 1,
        "Items": ["$SUBDOMAIN"]
    },
    "ViewerCertificate": {
        "ACMCertificateArn": "$WILDCARD_CERT_ARN",
        "SSLSupportMethod": "sni-only",
        "MinimumProtocolVersion": "TLSv1.2_2021"
    },
    "DefaultRootObject": "medicare/states.json",
    "CustomErrorResponses": {
        "Quantity": 1,
        "Items": [
            {
                "ErrorCode": 403,
                "ResponsePagePath": "/medicare/states.json",
                "ResponseCode": "404",
                "ErrorCachingMinTTL": 300
            }
        ]
    },
    "HttpVersion": "http2and3",
    "PriceClass": "PriceClass_100"
}
EOF

    DIST_RESULT=$(aws cloudfront create-distribution \
        --distribution-config file:///tmp/cf-config.json 2>&1)
    
    DIST_ID=$(echo "$DIST_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['Distribution']['Id'])" 2>/dev/null || echo "")
    
    if [ -z "$DIST_ID" ]; then
        echo "  ❌ Failed to create distribution"
        echo "$DIST_RESULT"
        exit 1
    fi
    
    CLOUDFRONT_DOMAIN=$(echo "$DIST_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['Distribution']['DomainName'])")
    echo "  ✓ Created distribution: $DIST_ID"
    echo "  ✓ CloudFront domain: $CLOUDFRONT_DOMAIN"
fi
echo ""

# Step 5: Update S3 bucket policy for CloudFront
echo "Step 5: Updating S3 bucket policy..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

cat > /tmp/bucket-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowCloudFrontServicePrincipal",
            "Effect": "Allow",
            "Principal": {
                "Service": "cloudfront.amazonaws.com"
            },
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::$BUCKET_NAME/*",
            "Condition": {
                "StringEquals": {
                    "AWS:SourceArn": "arn:aws:cloudfront::$ACCOUNT_ID:distribution/$DIST_ID"
                }
            }
        }
    ]
}
EOF

aws s3api put-bucket-policy \
    --bucket "$BUCKET_NAME" \
    --policy file:///tmp/bucket-policy.json
echo "  ✓ Bucket policy updated"
echo ""

# Step 6: Create Route 53 record
echo "Step 6: Setting up DNS..."
CLOUDFRONT_DOMAIN=$(aws cloudfront get-distribution --id "$DIST_ID" \
    --query "Distribution.DomainName" --output text)

cat > /tmp/route53-change.json << EOF
{
    "Changes": [
        {
            "Action": "UPSERT",
            "ResourceRecordSet": {
                "Name": "$SUBDOMAIN",
                "Type": "A",
                "AliasTarget": {
                    "HostedZoneId": "Z2FDTNDATAQYW2",
                    "DNSName": "$CLOUDFRONT_DOMAIN",
                    "EvaluateTargetHealth": false
                }
            }
        }
    ]
}
EOF

aws route53 change-resource-record-sets \
    --hosted-zone-id "$HOSTED_ZONE_ID" \
    --change-batch file:///tmp/route53-change.json > /dev/null
echo "  ✓ DNS record created/updated"
echo ""

# Cleanup
rm -f /tmp/cf-config.json /tmp/bucket-policy.json /tmp/route53-change.json

# Summary
echo "========================================"
echo "✓ DEPLOYMENT COMPLETE!"
echo "========================================"
echo ""
echo "CloudFront Distribution: $DIST_ID"
echo "CloudFront Domain: $CLOUDFRONT_DOMAIN"
echo ""
echo "API URL: https://$SUBDOMAIN"
echo ""
echo "Test endpoints:"
echo "  curl https://$SUBDOMAIN/medicare/states.json"
echo "  curl https://$SUBDOMAIN/medicare/zip/03462.json"
echo "  curl https://$SUBDOMAIN/medicare/state/NH/info.json"
echo ""
echo "Note: CloudFront may take 5-15 minutes to fully deploy."
echo "========================================"
