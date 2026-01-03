#!/bin/bash
# Super fast incremental update - only processes new scraped plans
# Checks scraped_json_all/ for files newer than last deployment

set -e

BUCKET_NAME="purlpal-medicare-api"
CLOUDFRONT_ID="E3SHXUEGZALG4E"
OUTPUT_DIR="./static_api"
TIMESTAMP_FILE=".last_build_timestamp"

echo "========================================"
echo "Medicare API Incremental Update"
echo "========================================"
echo ""

# Find new scraped files since last build
if [ -f "$TIMESTAMP_FILE" ]; then
    LAST_BUILD=$(cat "$TIMESTAMP_FILE")
    echo "Last build: $(date -r $LAST_BUILD)"
    NEW_FILES=$(find scraped_json_all/ -type f -newer "$TIMESTAMP_FILE" | wc -l | tr -d ' ')
    echo "New scraped files: $NEW_FILES"
    echo ""

    if [ "$NEW_FILES" -eq 0 ]; then
        echo "✅ No new data to deploy!"
        exit 0
    fi
else
    echo "⚠️  No previous build found. Running full build..."
    echo ""
fi

# Full rebuild (fast with only changed states)
echo "Step 1: Rebuilding API..."
time python3 build_static_api.py
echo ""

# Sync only changed files
echo "Step 2: Syncing changes to S3..."
aws s3 sync "$OUTPUT_DIR/" "s3://$BUCKET_NAME/" \
    --delete \
    --size-only \
    --exclude "*" \
    --include "medicare/*" \
    --content-type "application/json" \
    --cache-control "max-age=3600" \
    --quiet

echo "  ✓ S3 sync complete"
echo ""

# Invalidate CloudFront
echo "Step 3: Invalidating CloudFront cache..."
aws cloudfront create-invalidation \
    --distribution-id "$CLOUDFRONT_ID" \
    --paths "/medicare/*" \
    --output text > /dev/null

echo "  ✓ Cache invalidated"
echo ""

# Update timestamp
date +%s > "$TIMESTAMP_FILE"

echo "✅ Incremental update complete!"
echo ""
echo "Test: curl https://d11vrs9xl9u4t7.cloudfront.net/medicare/states.json"
