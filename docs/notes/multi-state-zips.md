# Multi-State ZIP Code Handling

## Summary

ZIP codes can span multiple states. We identified **137 multi-state ZIPs** that need special handling.

## Data Sources

### HUD USPS Crosswalk (downloaded_data/ZIP_COUNTY_062025.xlsx)
- Based on USPS delivery areas (administrative boundaries)
- Only shows **3 multi-state ZIPs**
- Good for: ZIP to county mapping with residential ratios

### Census ZCTA Data (downloaded_data/zcta_county_2020.txt)
- Based on Census block geography (where people live)
- Shows **137 multi-state ZCTAs**
- Good for: Identifying geographic boundaries that cross state lines

## Why the Difference?

- **USPS ZIP codes** are for mail delivery - administrative
- **Census ZCTAs** are geographic approximations based on Census blocks
- A ZIP code's "primary state" for mail may differ from where residents actually live

## Current Implementation

We merged both sources into `unified_zip_to_fips.json`:
- 39,298 total ZIPs
- 137 multi-state ZIPs
- 11,301+ multi-county ZIPs

## Multi-State ZIP Distribution

Top border regions:
- ND/SD: 19 ZIPs
- MN/SD: 9 ZIPs  
- KS/NE: 8 ZIPs
- NE/SD: 7 ZIPs
- KY/TN: 5 ZIPs
- CA/NV: 5 ZIPs

## API Behavior

The `/api/zip/<zip_code>` endpoint:
1. Looks up all counties for the ZIP (from unified mapping)
2. For each county, finds the state
3. Returns plans from ALL applicable states
4. Shows `plans_available: false` for unscraped states

## Files

- `unified_zip_to_fips.json` - Main ZIP to FIPS mapping (39,298 ZIPs)
- `multi_state_zctas.json` - Reference file with 137 multi-state ZCTAs
- `zip_county_data/*.json` - Per-state ZIP mappings from HUD
- `downloaded_data/zcta_county_2020.txt` - Census ZCTA source

## Future Considerations

1. **Re-verify periodically** - ZIP/ZCTA boundaries change
2. **Census updates** - New ZCTA data released after each Census
3. **HUD updates** - Quarterly updates to ZIP crosswalk
4. **Edge cases** - Some ZIPs may have different plans available in different parts

## References

- HUD USPS Crosswalk: https://www.huduser.gov/portal/datasets/usps_crosswalk.html
- Census ZCTA: https://www.census.gov/programs-surveys/geography/guidance/geo-areas/zctas.html
- Multi-state analysis: https://peter-horton.com/2022/12/30/zip-codes-zctas-and-zctas-that-cross-state-boundaries/

---
*Created: 2025-12-08*
