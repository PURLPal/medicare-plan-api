-- Comprehensive fix for duplicate county records
-- Problem: "Dallas County" (has ZIPs) and "Dallas" (has plans) are separate records
-- Solution: Merge all relationships to one county, delete the duplicate

BEGIN;

-- Step 1: Identify all duplicate counties and pick primary for each
CREATE TEMP TABLE county_merges AS
WITH normalized AS (
    SELECT 
        id,
        state_abbrev,
        county_name,
        REPLACE(REPLACE(LOWER(county_name), ' county', ''), ' ', '') as normalized_name,
        (SELECT COUNT(*) FROM zip_counties WHERE county_id = counties.id) as zip_count,
        (SELECT COUNT(*) FROM plan_counties WHERE county_id = counties.id) as plan_count
    FROM counties
),
duplicate_groups AS (
    SELECT 
        state_abbrev,
        normalized_name,
        array_agg(id ORDER BY (zip_count + plan_count) DESC, id ASC) as county_ids,
        array_agg(county_name ORDER BY (zip_count + plan_count) DESC, id ASC) as county_names,
        array_agg(zip_count ORDER BY (zip_count + plan_count) DESC, id ASC) as zip_counts,
        array_agg(plan_count ORDER BY (zip_count + plan_count) DESC, id ASC) as plan_counts
    FROM normalized
    GROUP BY state_abbrev, normalized_name
    HAVING COUNT(*) > 1
)
SELECT 
    state_abbrev,
    normalized_name,
    county_ids[1] as primary_id,
    county_names[1] as primary_name,
    array_length(county_ids, 1) as duplicate_count,
    county_ids[2:array_length(county_ids,1)] as duplicate_ids,
    county_names[2:array_length(county_names,1)] as duplicate_names,
    zip_counts[1] as primary_zip_count,
    plan_counts[1] as primary_plan_count
FROM duplicate_groups;

-- Show what we're about to fix
SELECT 
    'DUPLICATE COUNTY GROUPS TO MERGE' as action,
    COUNT(*) as group_count,
    SUM(duplicate_count - 1) as total_duplicates_to_remove
FROM county_merges;

-- Step 2: Merge zip_counties to primary
-- For each duplicate county, move its ZIPs to the primary
DO $$
DECLARE
    merge_rec RECORD;
    dup_id INTEGER;
    moved INTEGER := 0;
    skipped INTEGER := 0;
BEGIN
    FOR merge_rec IN SELECT * FROM county_merges LOOP
        -- Process each duplicate in this group
        FOREACH dup_id IN ARRAY merge_rec.duplicate_ids LOOP
            -- Move ZIPs that aren't already linked to primary
            UPDATE zip_counties 
            SET county_id = merge_rec.primary_id
            WHERE county_id = dup_id
              AND zip_code NOT IN (
                  SELECT zip_code FROM zip_counties WHERE county_id = merge_rec.primary_id
              );
            
            GET DIAGNOSTICS moved = ROW_COUNT;
            
            -- Delete duplicate ZIP links (where primary already has the ZIP)
            DELETE FROM zip_counties 
            WHERE county_id = dup_id;
            
            GET DIAGNOSTICS skipped = ROW_COUNT;
            
            IF moved > 0 OR skipped > 0 THEN
                RAISE NOTICE '% - %: moved % ZIPs, removed % duplicate ZIP links from %', 
                    merge_rec.state_abbrev, 
                    merge_rec.primary_name, 
                    moved, 
                    skipped,
                    (SELECT county_name FROM counties WHERE id = dup_id);
            END IF;
        END LOOP;
    END LOOP;
END $$;

-- Step 3: Merge plan_counties to primary
DO $$
DECLARE
    merge_rec RECORD;
    dup_id INTEGER;
    moved INTEGER := 0;
    skipped INTEGER := 0;
BEGIN
    FOR merge_rec IN SELECT * FROM county_merges LOOP
        FOREACH dup_id IN ARRAY merge_rec.duplicate_ids LOOP
            -- Move plans that aren't already linked to primary
            UPDATE plan_counties 
            SET county_id = merge_rec.primary_id
            WHERE county_id = dup_id
              AND plan_id NOT IN (
                  SELECT plan_id FROM plan_counties WHERE county_id = merge_rec.primary_id
              );
            
            GET DIAGNOSTICS moved = ROW_COUNT;
            
            -- Delete duplicate plan links
            DELETE FROM plan_counties 
            WHERE county_id = dup_id;
            
            GET DIAGNOSTICS skipped = ROW_COUNT;
            
            IF moved > 0 OR skipped > 0 THEN
                RAISE NOTICE '% - %: moved % plans, removed % duplicate plan links from %', 
                    merge_rec.state_abbrev, 
                    merge_rec.primary_name, 
                    moved, 
                    skipped,
                    (SELECT county_name FROM counties WHERE id = dup_id);
            END IF;
        END LOOP;
    END LOOP;
END $$;

-- Step 4: Delete duplicate county records (now empty)
DO $$
DECLARE
    merge_rec RECORD;
    dup_id INTEGER;
    total_deleted INTEGER := 0;
BEGIN
    FOR merge_rec IN SELECT * FROM county_merges LOOP
        FOREACH dup_id IN ARRAY merge_rec.duplicate_ids LOOP
            DELETE FROM counties WHERE id = dup_id;
            total_deleted := total_deleted + 1;
        END LOOP;
    END LOOP;
    
    RAISE NOTICE 'Deleted % duplicate county records', total_deleted;
END $$;

-- Step 5: Show results
SELECT 
    'RESULTS' as summary,
    (SELECT COUNT(*) FROM counties) as counties_after,
    (SELECT COUNT(DISTINCT state_abbrev || normalized_name) 
     FROM (
         SELECT state_abbrev, 
                REPLACE(REPLACE(LOWER(county_name), ' county', ''), ' ', '') as normalized_name
         FROM counties
     ) sub) as unique_counties,
    (SELECT COUNT(*) FROM zip_counties) as zip_county_links,
    (SELECT COUNT(*) FROM plan_counties) as plan_county_links;

COMMIT;

-- Verify the fix with a sample
\echo ''
\echo 'VERIFICATION - Sample ZIPs should now have plans:'

SELECT 
    z.zip_code,
    z.primary_state as state,
    COUNT(DISTINCT c.county_name) as counties,
    COUNT(DISTINCT p.plan_id) as plans
FROM zip_codes z
JOIN zip_counties zc ON z.zip_code = zc.zip_code
JOIN counties c ON zc.county_id = c.id
LEFT JOIN plan_counties pc ON c.id = pc.county_id
LEFT JOIN plans p ON pc.plan_id = p.plan_id
WHERE z.zip_code IN ('75001', '90210', '10001', '19102', '60601', '30301')
GROUP BY z.zip_code, z.primary_state
ORDER BY z.zip_code;
