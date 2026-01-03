-- Fix duplicate county entries that break ZIP queries
-- Example: "Dallas County" (has ZIPs) vs "Dallas" (has plans)

BEGIN;

-- Create temporary table to track duplicates
CREATE TEMP TABLE county_consolidation AS
SELECT 
    c1.id as keep_id,
    c1.county_name as keep_name,
    c2.id as duplicate_id,
    c2.county_name as duplicate_name,
    c1.state_abbrev,
    (SELECT COUNT(*) FROM plan_counties WHERE county_id = c1.id) as keep_plans,
    (SELECT COUNT(*) FROM plan_counties WHERE county_id = c2.id) as duplicate_plans,
    (SELECT COUNT(*) FROM zip_counties WHERE county_id = c1.id) as keep_zips,
    (SELECT COUNT(*) FROM zip_counties WHERE county_id = c2.id) as duplicate_zips
FROM counties c1
JOIN counties c2 ON c1.state_abbrev = c2.state_abbrev 
  AND c1.id < c2.id
  AND (
    REPLACE(REPLACE(LOWER(c1.county_name), ' county', ''), ' ', '') = 
    REPLACE(REPLACE(LOWER(c2.county_name), ' county', ''), ' ', '')
  );

-- Show what will be consolidated
SELECT 
    state_abbrev,
    keep_name || ' (ID:' || keep_id || ', Plans:' || keep_plans || ', ZIPs:' || keep_zips || ')' as primary,
    duplicate_name || ' (ID:' || duplicate_id || ', Plans:' || duplicate_plans || ', ZIPs:' || duplicate_zips || ')' as will_merge
FROM county_consolidation
ORDER BY state_abbrev, keep_name;

-- For each duplicate pair, decide which to keep based on what has more data
-- Strategy: Keep the one with plans, merge ZIPs to it

-- Update zip_counties to point to the county with plans
UPDATE zip_counties zc
SET county_id = (
    SELECT CASE 
        WHEN cc.keep_plans >= cc.duplicate_plans THEN cc.keep_id
        ELSE cc.duplicate_id
    END
    FROM county_consolidation cc
    WHERE zc.county_id IN (cc.keep_id, cc.duplicate_id)
    LIMIT 1
)
WHERE county_id IN (
    SELECT keep_id FROM county_consolidation WHERE keep_plans < duplicate_plans
    UNION
    SELECT duplicate_id FROM county_consolidation WHERE keep_plans >= duplicate_plans
);

-- Update plan_counties to point to the kept county
UPDATE plan_counties pc
SET county_id = (
    SELECT CASE 
        WHEN cc.keep_plans >= cc.duplicate_plans THEN cc.keep_id
        ELSE cc.duplicate_id
    END
    FROM county_consolidation cc
    WHERE pc.county_id IN (cc.keep_id, cc.duplicate_id)
    LIMIT 1
)
WHERE county_id IN (
    SELECT keep_id FROM county_consolidation WHERE keep_plans < duplicate_plans
    UNION
    SELECT duplicate_id FROM county_consolidation WHERE keep_plans >= duplicate_plans
);

-- Delete the now-unused duplicate counties
DELETE FROM counties
WHERE id IN (
    SELECT keep_id FROM county_consolidation WHERE keep_plans < duplicate_plans
    UNION
    SELECT duplicate_id FROM county_consolidation WHERE keep_plans >= duplicate_plans
);

-- Show results
SELECT 
    'Consolidated ' || COUNT(DISTINCT state_abbrev) || ' states, ' ||
    COUNT(*) || ' duplicate counties' as summary
FROM county_consolidation;

COMMIT;
