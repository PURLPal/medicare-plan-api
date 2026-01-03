#!/usr/bin/env python3
"""
Minify Arkansas ZIP endpoints using the proven minification approach.
Reduces file size by 60-80% for bandwidth-constrained clients.
"""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent / 'minification'))

from minify_plans import minify_key, minify_value, minify_object

INPUT_DIR = Path('static_api/medicare/zip')
OUTPUT_DIR = Path('static_api/medicare/zip_minified')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def minify_arkansas_zips():
    """Minify all Arkansas ZIP files (71xxx-72xxx)."""
    print("\n" + "="*80)
    print("ARKANSAS MINIFICATION")
    print("="*80)
    
    # Find all Arkansas main ZIP files (71xxx-72xxx), exclude category variants
    ar_files = []
    for zip_file in INPUT_DIR.glob('7[12]*.json'):
        # Skip category-specific files (_MAPD.json, _MA.json, _PD.json)
        if not any(cat in zip_file.name for cat in ['_MAPD', '_MA', '_PD']):
            ar_files.append(zip_file)
    
    print(f"\nFound {len(ar_files)} Arkansas ZIP files to minify")
    
    total_original = 0
    total_minified = 0
    count = 0
    
    for zip_file in sorted(ar_files):
        with open(zip_file) as f:
            data = json.load(f)
        
        # Minify the data
        minified = minify_object(data)
        
        # Write minified version
        output_file = OUTPUT_DIR / f'{zip_file.stem}_minified.json'
        with open(output_file, 'w') as f:
            json.dump(minified, f, separators=(',', ':'))
        
        # Track sizes
        original_size = zip_file.stat().st_size
        minified_size = output_file.stat().st_size
        total_original += original_size
        total_minified += minified_size
        
        count += 1
        if count % 100 == 0:
            print(f"  Minified {count}/{len(ar_files)} files...")
    
    reduction = ((total_original - total_minified) / total_original) * 100
    
    print(f"\n{'='*80}")
    print("MINIFICATION COMPLETE!")
    print(f"{'='*80}")
    print(f"✅ Minified {count} Arkansas ZIP files")
    print(f"📊 Original size: {total_original/1024/1024:.2f} MB")
    print(f"📊 Minified size: {total_minified/1024/1024:.2f} MB")
    print(f"📉 Reduction: {reduction:.1f}%")
    print(f"📁 Output: {OUTPUT_DIR}")
    print(f"{'='*80}\n")
    
    return count

if __name__ == '__main__':
    minify_arkansas_zips()
