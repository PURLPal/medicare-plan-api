#!/usr/bin/env python3
"""
Configuration for 8-instance parallel scraping
Divides 56 states across 8 instances
"""
import json
from pathlib import Path

STATE_DATA_DIR = Path('state_data')

# Get all states and their plan counts
all_states = []
state_files = sorted(STATE_DATA_DIR.glob('*.json'))

for state_file in state_files:
    with open(state_file) as f:
        plans = json.load(f)
    all_states.append({
        'name': state_file.stem,
        'plan_count': len(plans)
    })

total_plans = sum(s['plan_count'] for s in all_states)
print(f"Total states: {len(all_states)}")
print(f"Total plans: {total_plans}")
print(f"Target per instance: {total_plans // 8}")

# Distribute states across 8 instances to balance plan counts
# Sort by plan count descending to distribute large states first
all_states.sort(key=lambda x: x['plan_count'], reverse=True)

# Initialize 8 groups
groups = [{'states': [], 'plan_count': 0} for _ in range(8)]

# Greedy assignment: assign each state to the group with fewest plans
for state in all_states:
    # Find group with minimum plans
    min_group = min(groups, key=lambda g: g['plan_count'])
    min_group['states'].append(state['name'])
    min_group['plan_count'] += state['plan_count']

# Sort states within each group alphabetically for easier tracking
for group in groups:
    group['states'].sort()

# Display assignments
print(f"\n{'='*80}")
print("STATE ASSIGNMENTS BY INSTANCE")
print(f"{'='*80}\n")

for i, group in enumerate(groups, 1):
    print(f"Instance {i}: {group['plan_count']:,} plans ({len(group['states'])} states)")
    for state in group['states']:
        state_info = next(s for s in all_states if s['name'] == state)
        print(f"  - {state:30} ({state_info['plan_count']:4} plans)")
    print()

# Save configuration
config = {
    'total_states': len(all_states),
    'total_plans': total_plans,
    'num_instances': 8,
    'groups': [
        {
            'instance_id': i,
            'states': group['states'],
            'plan_count': group['plan_count']
        }
        for i, group in enumerate(groups, 1)
    ]
}

with open('parallel_config.json', 'w') as f:
    json.dump(config, f, indent=2)

print(f"✅ Configuration saved to parallel_config.json")
