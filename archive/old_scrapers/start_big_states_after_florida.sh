#!/bin/bash
echo "Waiting for Florida scraper to complete..."

while true; do
    # Check if Florida process is still running
    if ! pgrep -f "scrape_florida.py" > /dev/null; then
        echo "Florida scraper completed!"
        break
    fi
    sleep 60
done

echo "Starting big states scraper..."
cd /Users/andy/medicare_overview_test
nohup python3 scrape_big_states.py > big_states_output.log 2>&1 &
echo "Big states scraper started! PID: $!"
echo "Monitor with: tail -f big_states_output.log"
