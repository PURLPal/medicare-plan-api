#!/bin/bash

# Cleanup Script for Medicare Plan API Reorganization
# This script removes original files that have been copied to organized locations
# 
# WARNING: Only run this after verifying the new structure works!
# Recommended: Create a backup first with:
#   tar -czf ../medicare_backup_$(date +%Y%m%d).tar.gz .

set -e  # Exit on error

echo "=========================================="
echo "Medicare Plan API - Cleanup Original Files"
echo "=========================================="
echo ""
echo "This script will remove original files from the root directory."
echo "Files have been copied to organized subdirectories."
echo ""
echo "⚠️  WARNING: This action cannot be undone!"
echo ""

# Safety check
read -p "Have you tested the new structure? (yes/no): " response
if [ "$response" != "yes" ]; then
    echo "Cleanup cancelled. Please test first!"
    exit 1
fi

read -p "Have you created a backup? (yes/no): " response
if [ "$response" != "yes" ]; then
    echo "Cleanup cancelled. Please create a backup first!"
    exit 1
fi

read -p "Are you ABSOLUTELY SURE you want to delete original files? (yes/no): " response
if [ "$response" != "yes" ]; then
    echo "Cleanup cancelled."
    exit 1
fi

echo ""
echo "Starting cleanup..."
echo ""

# Counter for removed files
REMOVED=0

# Remove documentation files
echo "Removing documentation files..."
for file in API_*.md DEPLOYMENT_*.md DEPLOY_*.md SCRAPING_*.md \
            TESTING_GUIDE.md DATABASE_API_GUIDE.md NOTES_*.md \
            CORS_*.md ZIP_*.md QUICK_REFERENCE.md FILE_GUIDE.md \
            MINIFIED_*.md S3_*.md CHROME_*.md AWS_*.md SC_*.md \
            SUCCESSFUL_*.md EC2_*.md MA_*.md RHODE_*.md FLORIDA_*.md \
            ARIZONA_*.md ARKANSAS_*.md ALL_*.md 02108_ENDPOINTS.md \
            29401_ENDPOINTS.md 85001_ENDPOINTS.md; do
    if [ -f "$file" ]; then
        rm -f "$file"
        echo "  ✓ Removed $file"
        ((REMOVED++))
    fi
done

# Remove Python scripts
echo ""
echo "Removing Python scripts..."
for file in scrape_*.py parse_*.py build_*.py api_server*.py \
            deploy_*.py test_*.py analyze_*.py check_*.py verify_*.py \
            investigate_*.py review_*.py create_*.py extract_*.py \
            upload_*.py rename_*.py reprocess_*.py minify_*.py \
            parallel_scrape_config.py retry_*.py lambda_function.py \
            selenium_scraper.py; do
    if [ -f "$file" ]; then
        rm -f "$file"
        echo "  ✓ Removed $file"
        ((REMOVED++))
    fi
done

# Remove configuration files
echo ""
echo "Removing configuration files..."
for file in openapi.yaml openapi-compact.yaml cors-config.json \
            parallel_config.json upload_metadata.json \
            chrome_extension_example.js; do
    if [ -f "$file" ]; then
        rm -f "$file"
        echo "  ✓ Removed $file"
        ((REMOVED++))
    fi
done

# Remove data files
echo ""
echo "Removing data files from root..."
for file in fips_to_county_name.json multi_state_zctas.json \
            unified_zip_to_fips.json plan_county_mappings.json \
            zip_coverage_report.txt; do
    if [ -f "$file" ]; then
        rm -f "$file"
        echo "  ✓ Removed $file"
        ((REMOVED++))
    fi
done

# Remove shell scripts
echo ""
echo "Removing shell scripts..."
for file in incremental_update.sh update_api.sh deploy_medicare_api.sh \
            deploy_lambda.sh deploy_to_aws.sh test_*.sh start_*.sh; do
    if [ -f "$file" ]; then
        rm -f "$file"
        echo "  ✓ Removed $file"
        ((REMOVED++))
    fi
done

echo ""
echo "=========================================="
echo "Cleanup Complete!"
echo "=========================================="
echo ""
echo "Files removed: $REMOVED"
echo ""
echo "Remaining structure:"
echo "  ✓ docs/ - Organized documentation"
echo "  ✓ src/ - Organized source code"
echo "  ✓ tests/ - Test files"
echo "  ✓ scripts/ - Utility scripts"
echo "  ✓ config/ - Configuration files"
echo "  ✓ data/ - Data files"
echo "  ✓ lambda/ - AWS Lambda (unchanged)"
echo "  ✓ database/ - Database scripts (unchanged)"
echo "  ✓ archive/ - Deprecated files"
echo ""
echo "Next steps:"
echo "1. Run tests: ./tests/test_medicare_api.sh"
echo "2. Verify everything works"
echo "3. Commit changes: git add -A && git commit -m 'Reorganize repository structure'"
echo ""
