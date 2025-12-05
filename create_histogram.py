#!/usr/bin/env python3
import json
import matplotlib.pyplot as plt

# Load the data
with open('./data_analysis/state_plans_analysis.json', 'r') as f:
    data = json.load(f)

# Extract state names and plan counts
states = []
plan_counts = []

for state, info in data.items():
    states.append(state)
    plan_counts.append(info['total_unique_plans'])

# Sort by plan count for rankings
sorted_data = sorted(zip(states, plan_counts), key=lambda x: x[1], reverse=True)
sorted_states, sorted_counts = zip(*sorted_data)

# Top 10 and bottom 10
top_10 = sorted_data[:10]
bottom_10 = sorted_data[-10:]

print("="*60)
print("TOP 10 STATES WITH MOST UNIQUE PLANS")
print("="*60)
for i, (state, count) in enumerate(top_10, 1):
    print(f"{i:2}. {state:30} {count:4} plans")

print("\n" + "="*60)
print("TOP 10 STATES WITH LEAST UNIQUE PLANS")
print("="*60)
for i, (state, count) in enumerate(bottom_10, 1):
    print(f"{i:2}. {state:30} {count:4} plans")

# Create histogram
plt.figure(figsize=(14, 8))
plt.hist(plan_counts, bins=30, edgecolor='black', alpha=0.7, color='steelblue')
plt.xlabel('Number of Unique Plans', fontsize=12)
plt.ylabel('Number of States/Territories', fontsize=12)
plt.title('Distribution of Unique Medicare Plans Across States/Territories (CY2026)', fontsize=14, fontweight='bold')
plt.grid(axis='y', alpha=0.3)

# Add some statistics to the plot
mean_plans = sum(plan_counts) / len(plan_counts)
median_plans = sorted(plan_counts)[len(plan_counts)//2]
plt.axvline(mean_plans, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_plans:.1f}')
plt.axvline(median_plans, color='green', linestyle='--', linewidth=2, label=f'Median: {median_plans}')
plt.legend()

plt.tight_layout()
plt.savefig('./data_analysis/unique_plans_histogram.png', dpi=300, bbox_inches='tight')
print(f"\n{'='*60}")
print(f"Histogram saved to: ./data_analysis/unique_plans_histogram.png")
print(f"{'='*60}")
print(f"\nStatistics:")
print(f"  Mean:   {mean_plans:.1f} plans")
print(f"  Median: {median_plans} plans")
print(f"  Min:    {min(plan_counts)} plans ({sorted_data[-1][0]})")
print(f"  Max:    {max(plan_counts)} plans ({sorted_data[0][0]})")
