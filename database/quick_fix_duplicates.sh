#!/bin/bash
# Quick batch fix for duplicate counties - processes in small batches

PGPASSWORD='VpWFqae6cnQ6TEnRvsweq2pPg'
export PGPASSWORD

HOST="medicare-plans-db.cc98ea006lul.us-east-1.rds.amazonaws.com"
DB="medicare_plans"
USER="medicare_admin"

echo "Finding and fixing duplicate counties..."

# Get count before
BEFORE=$(psql -h $HOST -U $USER -d $DB -t -c "SELECT COUNT(*) FROM counties;")
echo "Counties before: $BEFORE"

# Process duplicates in batches of 100 states
psql -h $HOST -U $USER -d $DB << 'EOF'
DO $$
DECLARE
    dup RECORD;
    updates INT := 0;
    deletes INT := 0;
BEGIN
    FOR dup IN 
        SELECT 
            c1.id as keep_id,
            c2.id as dup_id,
            c1.county_name as keep_name,
            c2.county_name as dup_name,
            c1.state_abbrev
        FROM counties c1
        JOIN counties c2 ON 
            c1.state_abbrev = c2.state_abbrev 
            AND c1.id < c2.id
            AND REPLACE(REPLACE(LOWER(c1.county_name), ' county', ''), ' ', '') = 
                REPLACE(REPLACE(LOWER(c2.county_name), ' county', ''), ' ', '')
        WHERE (SELECT COUNT(*) FROM plan_counties WHERE county_id = c1.id) > 0
          AND (SELECT COUNT(*) FROM plan_counties WHERE county_id = c2.id) = 0
        LIMIT 500
    LOOP
        -- Move ZIPs from duplicate to primary (skip if already exists)
        UPDATE zip_counties 
        SET county_id = dup.keep_id
        WHERE county_id = dup.dup_id
          AND zip_code NOT IN (
              SELECT zip_code FROM zip_counties WHERE county_id = dup.keep_id
          );
        
        updates := updates + 1;
        
        -- Delete remaining ZIP links to duplicate
        DELETE FROM zip_counties WHERE county_id = dup.dup_id;
        
        -- Delete the duplicate county
        DELETE FROM counties WHERE id = dup.dup_id;
        deletes := deletes + 1;
        
        IF deletes % 50 = 0 THEN
            RAISE NOTICE 'Processed % duplicates...', deletes;
        END IF;
    END LOOP;
    
    RAISE NOTICE 'Fixed % duplicate counties', deletes;
END $$;
EOF

# Get count after
AFTER=$(psql -h $HOST -U $USER -d $DB -t -c "SELECT COUNT(*) FROM counties;")
echo "Counties after: $AFTER"
echo "Removed: $((BEFORE - AFTER))"
