#!/bin/bash
echo "Waiting for batch 6 to complete..."

while true; do
    # Check if batch6 process is still running
    if ! pgrep -f "scrape_batch_6.py" > /dev/null; then
        echo "Batch 6 completed!"
        break
    fi
    sleep 30
done

echo "Starting Florida scraper..."
cd /Users/andy/medicare_overview_test
nohup python3 scrape_florida.py > florida_output.log 2>&1 &
echo "Florida scraper started! PID: $!"
echo "Monitor with: tail -f florida_output.log"
