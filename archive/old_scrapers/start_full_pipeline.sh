#!/bin/bash
# Full scraping pipeline - runs all remaining scrapers in sequence

cd /Users/andy/medicare_overview_test

echo "=== MEDICARE SCRAPING PIPELINE ==="
echo "Started: $(date)"

# 1. Wait for Florida
echo ""
echo "[1/4] Waiting for Florida scraper..."
while pgrep -f "scrape_florida.py" > /dev/null; do
    sleep 60
done
echo "Florida complete!"

# 2. Run WA/OR
echo ""
echo "[2/4] Starting Washington & Oregon..."
python3 scrape_wa_or.py > wa_or_output.log 2>&1
echo "WA/OR complete!"

# 3. Run Big States
echo ""
echo "[3/4] Starting big states (TX, CA, PA, NY, OH, MI)..."
python3 scrape_big_states.py > big_states_output.log 2>&1
echo "Big states complete!"

# 4. Run All Remaining
echo ""
echo "[4/4] Starting all remaining states..."
python3 scrape_all_remaining.py > all_remaining_output.log 2>&1
echo "All remaining complete!"

echo ""
echo "=== PIPELINE COMPLETE ==="
echo "Finished: $(date)"

# Count total scraped
total=$(ls -1 scraped_json_all/*.json 2>/dev/null | wc -l)
echo "Total plans scraped: $total"
