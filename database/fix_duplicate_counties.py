#!/usr/bin/env python3
"""
Fix duplicate county entries in the database.
Example: "Dallas County" (has ZIPs) vs "Dallas" (has plans)
Strategy: Keep one county per normalized name, merge all relationships to it.
"""

import psycopg2
import psycopg2.extras
from collections import defaultdict

def normalize_county_name(name):
    """Normalize county name for comparison."""
    return name.lower().replace(' county', '').replace(' ', '').strip()

def fix_duplicate_counties(db_config):
    print("Connecting to database...")
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    try:
        # Find all counties
        print("\nFinding duplicate counties...")
        cur.execute("""
            SELECT id, county_name, state_abbrev,
                   (SELECT COUNT(*) FROM plan_counties WHERE county_id = counties.id) as plan_count,
                   (SELECT COUNT(*) FROM zip_counties WHERE county_id = counties.id) as zip_count
            FROM counties
            ORDER BY state_abbrev, county_name
        """)
        
        all_counties = cur.fetchall()
        
        # Group by normalized name within each state
        county_groups = defaultdict(list)
        for county in all_counties:
            key = (county['state_abbrev'], normalize_county_name(county['county_name']))
            county_groups[key].append(dict(county))
        
        # Find duplicates
        duplicates = {k: v for k, v in county_groups.items() if len(v) > 1}
        
        print(f"Found {len(duplicates)} sets of duplicate counties across {len(set(k[0] for k in duplicates))} states")
        
        if not duplicates:
            print("No duplicates to fix!")
            return
        
        # For each duplicate set, choose primary (prefer one with plans)
        total_removed = 0
        total_zips_updated = 0
        total_plans_updated = 0
        
        for (state, normalized), counties in duplicates.items():
            # Sort by: plan_count desc, zip_count desc, id asc
            counties.sort(key=lambda c: (-c['plan_count'], -c['zip_count'], c['id']))
            primary = counties[0]
            duplicates_list = counties[1:]
            
            duplicate_ids = [c['id'] for c in duplicates_list]
            
            print(f"\n{state} - {primary['county_name']} (ID {primary['id']})")
            print(f"  Primary: {primary['plan_count']} plans, {primary['zip_count']} ZIPs")
            print(f"  Merging {len(duplicates_list)} duplicates: {[c['county_name'] for c in duplicates_list]}")
            
            # Update zip_counties
            for dup_id in duplicate_ids:
                # Delete duplicates where primary already has the ZIP
                cur.execute("""
                    DELETE FROM zip_counties 
                    WHERE county_id = %s 
                    AND zip_code IN (
                        SELECT zip_code FROM zip_counties WHERE county_id = %s
                    )
                """, (dup_id, primary['id']))
                deleted = cur.rowcount
                
                # Move remaining ZIPs to primary
                cur.execute("""
                    UPDATE zip_counties 
                    SET county_id = %s 
                    WHERE county_id = %s
                """, (primary['id'], dup_id))
                updated = cur.rowcount
                total_zips_updated += updated
                if deleted > 0 or updated > 0:
                    print(f"    ZIPs: deleted {deleted} duplicates, moved {updated}")
            
            # Update plan_counties
            for dup_id in duplicate_ids:
                # Delete duplicates where primary already has the plan
                cur.execute("""
                    DELETE FROM plan_counties 
                    WHERE county_id = %s 
                    AND plan_id IN (
                        SELECT plan_id FROM plan_counties WHERE county_id = %s
                    )
                """, (dup_id, primary['id']))
                deleted = cur.rowcount
                
                # Move remaining plans to primary
                cur.execute("""
                    UPDATE plan_counties 
                    SET county_id = %s 
                    WHERE county_id = %s
                """, (primary['id'], dup_id))
                updated = cur.rowcount
                total_plans_updated += updated
                if deleted > 0 or updated > 0:
                    print(f"    Plans: deleted {deleted} duplicates, moved {updated}")
            
            # Delete duplicate counties
            cur.execute("""
                DELETE FROM counties 
                WHERE id = ANY(%s)
            """, (duplicate_ids,))
            total_removed += len(duplicates_list)
        
        conn.commit()
        
        print("\n" + "="*70)
        print(f"SUMMARY: Fixed {len(duplicates)} duplicate county sets")
        print(f"  Removed {total_removed} duplicate counties")
        print(f"  Updated {total_zips_updated} ZIP relationships")
        print(f"  Updated {total_plans_updated} plan relationships")
        print("="*70)
        
        # Test Dallas County
        print("\nVerifying Dallas County fix...")
        cur.execute("""
            SELECT 
                z.zip_code,
                c.county_name,
                c.state_abbrev,
                COUNT(DISTINCT pc.plan_id) as plan_count
            FROM zip_codes z
            JOIN zip_counties zc ON z.zip_code = zc.zip_code
            JOIN counties c ON zc.county_id = c.id
            LEFT JOIN plan_counties pc ON c.id = pc.county_id
            WHERE z.zip_code = '75001'
            GROUP BY z.zip_code, c.county_name, c.state_abbrev
        """)
        
        result = cur.fetchone()
        if result:
            print(f"  ✅ ZIP 75001 ({result['county_name']}, {result['state_abbrev']}): {result['plan_count']} plans")
        else:
            print("  ⚠️  ZIP 75001 not found")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 fix_duplicate_counties.py '<connection_string>'")
        sys.exit(1)
    
    # Parse connection string
    conn_str = sys.argv[1]
    db_config = {}
    for part in conn_str.split():
        if '=' in part:
            key, value = part.split('=', 1)
            db_config[key] = value
    
    fix_duplicate_counties(db_config)
