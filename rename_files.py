#!/usr/bin/env python3
"""Rename files from underscore format to hyphen format"""

import os
from pathlib import Path

# Rename JSON files
json_dir = Path('scraped_json_all')
html_dir = Path('scraped_html_all')

renamed_count = 0

print("Renaming JSON files...")
for file in json_dir.glob('*_H*.json'):
    old_name = file.name
    # Replace first underscore with hyphen (State_H... -> State-H...)
    new_name = old_name.replace('_H', '-H', 1)

    if old_name != new_name:
        new_path = file.parent / new_name
        file.rename(new_path)
        print(f"  {old_name} -> {new_name}")
        renamed_count += 1

print(f"\nRenamed {renamed_count} JSON files")

renamed_count = 0
print("\nRenaming HTML files...")
for file in html_dir.glob('*_H*.html'):
    old_name = file.name
    # Replace first underscore with hyphen (State_H... -> State-H...)
    new_name = old_name.replace('_H', '-H', 1)

    if old_name != new_name:
        new_path = file.parent / new_name
        file.rename(new_path)
        print(f"  {old_name} -> {new_name}")
        renamed_count += 1

print(f"\nRenamed {renamed_count} HTML files")
print("\nDone!")
