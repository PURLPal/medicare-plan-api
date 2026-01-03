#!/bin/bash
# Efficient update script for Medicare Plan API
# Only rebuilds changed states and syncs to S3

set -e

BUCKET_NAME="purlpal-medicare-api"
CLOUDFRONT_ID="E3SHXUEGZALG4E"
OUTPUT_DIR="./static_api"

echo "========================================"
echo "Medicare API Quick Update"
echo "========================================"
echo ""

# Step 1: Build static API (only changed files)
echo "Step 1: Building static API..."
echo "  (This may take 2-5 minutes...)"
echo ""
START_BUILD=$(date +%s)
python3 build_static_api.py 2>&1 | tee /tmp/build_api.log
END_BUILD=$(date +%s)
BUILD_TIME=$((END_BUILD - START_BUILD))
echo ""
echo "  ✓ Build completed in ${BUILD_TIME}s"
echo ""

# Step 2: Sync to S3 (only changed files)
echo "Step 2: Syncing to S3..."
FILE_COUNT=$(find "$OUTPUT_DIR" -type f | wc -l | tr -d ' ')
TOTAL_SIZE=$(du -sh "$OUTPUT_DIR" | cut -f1)
echo "  Files to check: $FILE_COUNT"
echo "  Total size: $TOTAL_SIZE"
echo "  (This may take 5-10 minutes for large updates...)"
echo ""

START_TIME=$(date +%s)
aws s3 sync "$OUTPUT_DIR/" "s3://$BUCKET_NAME/" \
    --delete \
    --size-only \
    --content-type "application/json" \
    --cache-control "max-age=3600" 2>&1 | tee /tmp/s3_sync.log

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
echo ""
echo "  ✓ S3 sync completed in ${ELAPSED}s"
echo "  ✓ Synced $FILE_COUNT files to S3"
echo ""

# Step 3: Invalidate CloudFront cache (only changed paths)
echo "Step 3: Creating CloudFront invalidation..."
INVALIDATION_ID=$(aws cloudfront create-invalidation \
    --distribution-id "$CLOUDFRONT_ID" \
    --paths "/medicare/*" \
    --query 'Invalidation.Id' \
    --output text)

echo "  ✓ Invalidation created: $INVALIDATION_ID"
echo ""

echo "========================================"
echo "✅ Update Complete!"
echo "========================================"
echo ""
echo "API URLs:"
echo "  CloudFront: https://d11vrs9xl9u4t7.cloudfront.net/medicare/"
echo "  Custom:     https://medicare.purlpal-api.com/medicare/"
echo ""
echo "Test:"
echo "  curl https://d11vrs9xl9u4t7.cloudfront.net/medicare/states.json"
echo ""
echo "Note: Invalidation takes 1-2 minutes to propagate"
