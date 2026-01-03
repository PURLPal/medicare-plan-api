#!/bin/bash
echo "Waiting for Florida scraper to complete..."

while true; do
    if ! pgrep -f "scrape_florida.py" > /dev/null; then
        echo "Florida scraper completed!"
        break
    fi
    sleep 60
done

echo "Starting Washington & Oregon scraper..."
cd /Users/andy/medicare_overview_test
nohup python3 scrape_wa_or.py > wa_or_output.log 2>&1 &
echo "WA/OR scraper started! PID: $!"

echo "Waiting for WA/OR scraper to complete..."
while true; do
    if ! pgrep -f "scrape_wa_or.py" > /dev/null; then
        echo "WA/OR scraper completed!"
        break
    fi
    sleep 60
done

echo "Starting big states scraper..."
nohup python3 scrape_big_states.py > big_states_output.log 2>&1 &
echo "Big states scraper started! PID: $!"
