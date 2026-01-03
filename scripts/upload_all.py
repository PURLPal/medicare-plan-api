#!/usr/bin/env python3
import json
import subprocess
import sys

instances = {
    1: "98.93.143.194",
    2: "3.80.153.143",
    3: "34.227.157.205",
    4: "54.209.99.214",
    5: "18.208.137.130",
    6: "34.239.111.98",
    7: "54.157.48.138",
    8: "13.222.239.138"
}

with open('parallel_config.json') as f:
    config = json.load(f)

for i in range(1, 9):
    ip = instances[i]
    group = [g for g in config['groups'] if g['instance_id'] == i][0]
    states = group['states']
    
    print(f"Instance {i} ({ip})...")
    
    # Create directory
    subprocess.run([
        "ssh", "-i", "~/.ssh/purlpal-demo-key.pem", f"ubuntu@{ip}",
        "mkdir -p state_data"
    ], check=True)
    
    # Upload core scripts
    subprocess.run([
        "scp", "-i", "~/.ssh/purlpal-demo-key.pem", "-q",
        "parse_ri_html.py", "scrape_parallel.py", "parallel_config.json",
        f"ubuntu@{ip}:~/"
    ], check=True)
    
    # Upload each state file
    for state in states:
        subprocess.run([
            "scp", "-i", "~/.ssh/purlpal-demo-key.pem", "-q",
            f"state_data/{state}.json",
            f"ubuntu@{ip}:~/state_data/"
        ], check=True)
    
    print(f"  ✅ Instance {i} complete ({len(states)} states)")

print("\n✅ All uploads complete!")
