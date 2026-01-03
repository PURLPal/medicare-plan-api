-- Fix duplicate county entries by consolidating them properly
-- Handle duplicate relationships before merging

BEGIN;

-- Identify duplicate counties
CREATE TEMP TABLE county_duplicates AS
WITH normalized_counties AS (
    SELECT 
        id,
        county_name,
        state_abbrev,
        REPLACE(REPLACE(LOWER(county_name), ' county', ''), ' ', '') as normalized_name
    FROM counties
),
county_groups AS (
    SELECT 
        normalized_name,
        state_abbrev,
        json_agg(json_build_object('id', id, 'name', county_name) ORDER BY 
            (SELECT COUNT(*) FROM plan_counties WHERE county_id = id) DESC,
            id ASC
        ) as county_ids
    FROM normalized_counties
    GROUP BY normalized_name, state_abbrev
    HAVING COUNT(*) > 1
)
SELECT 
    state_abbrev,
    normalized_name,
    (county_ids->0->>'id')::integer as primary_id,
    (county_ids->0->>'name') as primary_name,
    array_remove(
        array_agg((county_ids->i->>'id')::integer),
        (county_ids->0->>'id')::integer
    ) as duplicate_ids
FROM county_groups, generate_series(0, json_array_length(county_ids)-1) as i
GROUP BY state_abbrev, normalized_name, county_ids;

-- For zip_counties: delete duplicates, keep one link per ZIP
DELETE FROM zip_counties 
WHERE id IN (
    SELECT zc1.id
    FROM zip_counties zc1
    JOIN county_duplicates cd ON zc1.county_id = ANY(cd.duplicate_ids)
    WHERE EXISTS (
        SELECT 1 FROM zip_counties zc2
        WHERE zc2.zip_code = zc1.zip_code
        AND zc2.county_id = cd.primary_id
    )
);

-- Move remaining zip_counties from duplicate counties to primary
UPDATE zip_counties
SET county_id = (
    SELECT primary_id 
    FROM county_duplicates cd
    WHERE county_id = ANY(cd.duplicate_ids)
    LIMIT 1
)
WHERE county_id IN (
    SELECT unnest(duplicate_ids) FROM county_duplicates
);

-- For plan_counties: delete exact duplicates first
DELETE FROM plan_counties
WHERE id IN (
    SELECT pc1.id
    FROM plan_counties pc1
    JOIN county_duplicates cd ON pc1.county_id = ANY(cd.duplicate_ids)
    WHERE EXISTS (
        SELECT 1 FROM plan_counties pc2
        WHERE pc2.plan_id = pc1.plan_id
        AND pc2.county_id = cd.primary_id
    )
);

-- Move remaining plan_counties from duplicate counties to primary
UPDATE plan_counties
SET county_id = (
    SELECT primary_id 
    FROM county_duplicates cd
    WHERE county_id = ANY(cd.duplicate_ids)
    LIMIT 1
)
WHERE county_id IN (
    SELECT unnest(duplicate_ids) FROM county_duplicates
);

-- Delete the duplicate county records
DELETE FROM counties
WHERE id IN (
    SELECT unnest(duplicate_ids) FROM county_duplicates
);

-- Show summary
SELECT 
    COUNT(*) as duplicate_county_sets_fixed,
    SUM(array_length(duplicate_ids, 1)) as total_duplicates_removed
FROM county_duplicates;

COMMIT;

-- Verify Dallas County fix
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
GROUP BY z.zip_code, c.county_name, c.state_abbrev;
