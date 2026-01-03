#!/usr/bin/env python3
"""Test script to verify address parsing works correctly"""

from bs4 import BeautifulSoup
import re

# Sample HTML with address containing <br> tag
html_sample = '''
<td class="ds-u-text-align--left mct-c-table__cell">
    <address class="ds-u-font-style--normal">5255 E Williams Circle, Suite 2050<br>Tucson, AZ 85711</address>
</td>
'''

print("Testing address parsing...")
print("\n1. Testing current approach (replace_with + get_text(separator='\\n')):")
soup1 = BeautifulSoup(html_sample, 'html.parser')
for br in soup1.find_all('br'):
    br.replace_with('\n')

cell = soup1.find('td')
cell_text = cell.get_text(separator='\n').strip()
cell_text = re.sub(r'\n\s*\n', '\n', cell_text)
print(f"Result: '{cell_text}'")
print(f"Repr: {repr(cell_text)}")
print(f"Has newline: {chr(10) in cell_text}")

print("\n2. Testing improved approach (decompose + NavigableString):")
from bs4 import NavigableString

soup2 = BeautifulSoup(html_sample, 'html.parser')
for br in soup2.find_all('br'):
    br.replace_with(NavigableString('\n'))

cell2 = soup2.find('td')
cell_text2 = cell2.get_text(separator='\n').strip()
cell_text2 = re.sub(r'\n\s*\n', '\n', cell_text2)
print(f"Result: '{cell_text2}'")
print(f"Repr: {repr(cell_text2)}")
print(f"Has newline: {chr(10) in cell_text2}")

print("\n3. Alternative approach - using get_text directly with separator:")
soup3 = BeautifulSoup(html_sample, 'html.parser')
# Don't replace br tags, just use get_text with separator
cell3 = soup3.find('td')
# First pass: replace br with newline marker
for br in cell3.find_all('br'):
    br.replace_with('\n')
cell_text3 = cell3.get_text().strip()
print(f"Result: '{cell_text3}'")
print(f"Repr: {repr(cell_text3)}")
print(f"Has newline: {chr(10) in cell_text3}")
