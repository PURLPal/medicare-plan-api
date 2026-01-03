#!/usr/bin/env python3
"""
Create minified versions for New Jersey and Washington ZIP files.
Uses the standard minification mappings.
"""
import json
from pathlib import Path
import sys

# Add minification directory to path
sys.path.insert(0, str(Path(__file__).parent / 'minification'))

from minify_plans import minify_object

def minify_state_zips(state_prefix, state_name):
    """Minify all ZIP files for a specific state."""
    print(f"\n{'='*80}")
    print(f"MINIFYING {state_name.upper()} ZIP FILES")
    print(f"{'='*80}")
    
    zip_dir = Path('static_api/medicare/zip')
    minified_dir = Path('static_api/medicare/zip_minified')
    minified_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all main ZIP files for this state (no category suffixes)
    zip_files = [f for f in zip_dir.glob(f'{state_prefix}*.json') 
                 if not any(cat in f.name for cat in ['_MAPD', '_MA', '_PD'])]
    
    print(f"\nFound {len(zip_files)} ZIP files to minify")
    
    success_count = 0
    error_count = 0
    total_original_size = 0
    total_minified_size = 0
    
    for zip_file in sorted(zip_files):
        try:
            with open(zip_file) as f:
                original_data = json.load(f)
            
            original_size = zip_file.stat().st_size
            
            # Minify the data
            minified_data = minify_object(original_data)
            
            # Write minified file
            minified_file = minified_dir / zip_file.name
            with open(minified_file, 'w') as f:
                json.dump(minified_data, f, separators=(',', ':'))
            
            minified_size = minified_file.stat().st_size
            
            total_original_size += original_size
            total_minified_size += minified_size
            
            reduction = ((original_size - minified_size) / original_size) * 100
            
            if success_count % 100 == 0 and success_count > 0:
                print(f"  Processed {success_count}/{len(zip_files)}...")
            
            success_count += 1
            
        except Exception as e:
            print(f"  ✗ Error minifying {zip_file.name}: {str(e)[:50]}")
            error_count += 1
    
    print(f"\n{'='*80}")
    print(f"{state_name.upper()} MINIFICATION COMPLETE")
    print(f"{'='*80}")
    print(f"✓ Success: {success_count}/{len(zip_files)}")
    print(f"✗ Errors: {error_count}")
    print(f"\n📊 Size Reduction:")
    print(f"   Original: {total_original_size / 1024 / 1024:.2f} MB")
    print(f"   Minified: {total_minified_size / 1024 / 1024:.2f} MB")
    print(f"   Savings: {((total_original_size - total_minified_size) / total_original_size) * 100:.1f}%")
    print(f"{'='*80}\n")
    
    return success_count

def main():
    print("\n" + "="*80)
    print("NEW JERSEY & WASHINGTON MINIFICATION")
    print("="*80)
    
    # Minify New Jersey (07xxx-08xxx)
    nj_count = minify_state_zips('07', 'New Jersey')
    nj_count += minify_state_zips('08', 'New Jersey')
    
    # Minify Washington (98xxx-99xxx)
    wa_count = minify_state_zips('98', 'Washington')
    wa_count += minify_state_zips('99', 'Washington')
    
    print("\n" + "="*80)
    print("OVERALL SUMMARY")
    print("="*80)
    print(f"New Jersey: {nj_count} ZIPs minified")
    print(f"Washington: {wa_count} ZIPs minified")
    print(f"Total: {nj_count + wa_count} ZIPs minified")
    print("="*80 + "\n")

if __name__ == '__main__':
    main()
