#!/usr/bin/env python3
import csv

input_file = './CY2026_Landscape_202511/CY2026_Landscape_202511.csv'

states = set()

with open(input_file, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        state_name = row['State Territory Name']
        if state_name:
            states.add(state_name)

states_sorted = sorted(states)

print(f"Total unique states/territories: {len(states_sorted)}\n")
print("States/Territories found:")
for state in states_sorted:
    print(f"  - {state}")

# List of 50 US states
us_50_states = {
    'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado',
    'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho',
    'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana',
    'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota',
    'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada',
    'New Hampshire', 'New Jersey', 'New Mexico', 'New York',
    'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon',
    'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota',
    'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington',
    'West Virginia', 'Wisconsin', 'Wyoming'
}

states_in_data = set(states_sorted)
missing_states = us_50_states - states_in_data
extra_territories = states_in_data - us_50_states

print(f"\n50 US States coverage: {len(us_50_states & states_in_data)}/50")

if missing_states:
    print(f"\nMissing states ({len(missing_states)}):")
    for state in sorted(missing_states):
        print(f"  - {state}")

if extra_territories:
    print(f"\nAdditional territories ({len(extra_territories)}):")
    for territory in sorted(extra_territories):
        print(f"  - {territory}")
