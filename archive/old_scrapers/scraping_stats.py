#!/usr/bin/env python3
"""
Track scraping statistics and timing for all states
"""
import json
import os
from datetime import datetime
from pathlib import Path

def analyze_scraping_stats():
    """Analyze all scraped data and generate statistics"""
    
    # Count scraped plans by state
    scraped_files = os.listdir('scraped_json_all')
    state_counts = {}
    
    for f in scraped_files:
        if f.endswith('.json') and '-' in f:
            state = f.split('-')[0]
            state_counts[state] = state_counts.get(state, 0) + 1
    
    # Load expected counts from state_data
    state_data_dir = Path('state_data')
    expected_counts = {}
    
    for state_file in state_data_dir.glob('*.json'):
        state_name = state_file.stem
        with open(state_file) as f:
            plans = json.load(f)
            expected_counts[state_name] = len(plans)
    
    # Calculate statistics
    stats = {
        'timestamp': datetime.now().isoformat(),
        'total_scraped': len(scraped_files),
        'by_state': {},
        'summary': {
            'complete_states': 0,
            'partial_states': 0,
            'not_started': 0,
            'total_expected': sum(expected_counts.values()),
            'completion_percentage': 0
        }
    }
    
    # Analyze each state
    for state, expected in sorted(expected_counts.items()):
        actual = state_counts.get(state, 0)
        pct = (actual / expected * 100) if expected > 0 else 0
        
        status = 'complete' if actual == expected else ('partial' if actual > 0 else 'not_started')
        
        stats['by_state'][state] = {
            'scraped': actual,
            'expected': expected,
            'percentage': round(pct, 1),
            'missing': expected - actual,
            'status': status
        }
        
        if status == 'complete':
            stats['summary']['complete_states'] += 1
        elif status == 'partial':
            stats['summary']['partial_states'] += 1
        else:
            stats['summary']['not_started'] += 1
    
    stats['summary']['completion_percentage'] = round(
        (stats['total_scraped'] / stats['summary']['total_expected'] * 100), 2
    )
    
    return stats

def print_stats_report(stats):
    """Print a formatted report"""
    print('='*80)
    print('SCRAPING STATISTICS REPORT')
    print(f'Generated: {stats["timestamp"]}')
    print('='*80)
    print()
    
    print(f"📊 OVERALL PROGRESS:")
    print(f"   Total Plans: {stats['total_scraped']}/{stats['summary']['total_expected']} ({stats['summary']['completion_percentage']}%)")
    print(f"   Complete States: {stats['summary']['complete_states']}")
    print(f"   Partial States: {stats['summary']['partial_states']}")
    print(f"   Not Started: {stats['summary']['not_started']}")
    print()
    
    print("📈 BY STATE STATUS:")
    print(f"   {'State':<30} {'Scraped':<10} {'Expected':<10} {'%':<8} {'Status':<12}")
    print("   " + "-"*70)
    
    complete = []
    partial = []
    not_started = []
    
    for state, data in sorted(stats['by_state'].items()):
        if data['status'] == 'complete':
            complete.append((state, data))
        elif data['status'] == 'partial':
            partial.append((state, data))
        else:
            not_started.append((state, data))
    
    # Show complete states
    if complete:
        print(f"\n   ✅ COMPLETE ({len(complete)} states):")
        for state, data in complete:
            print(f"   {state:<30} {data['scraped']:<10} {data['expected']:<10} {data['percentage']:<8.1f} ✅")
    
    # Show partial states
    if partial:
        print(f"\n   🔄 IN PROGRESS ({len(partial)} states):")
        for state, data in partial:
            print(f"   {state:<30} {data['scraped']:<10} {data['expected']:<10} {data['percentage']:<8.1f} ({data['missing']} left)")
    
    # Show not started
    if not_started:
        print(f"\n   ⏸️  NOT STARTED ({len(not_started)} states):")
        for state, data in not_started[:10]:  # Show first 10
            print(f"   {state:<30} {data['scraped']:<10} {data['expected']:<10} {data['percentage']:<8.1f}")
        if len(not_started) > 10:
            print(f"   ... and {len(not_started) - 10} more states")
    
    print()
    print('='*80)

def save_stats(stats, filename='scraping_stats.json'):
    """Save stats to JSON file"""
    with open(filename, 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"💾 Stats saved to: {filename}")

if __name__ == '__main__':
    stats = analyze_scraping_stats()
    print_stats_report(stats)
    save_stats(stats)
