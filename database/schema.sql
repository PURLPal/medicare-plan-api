-- Medicare Plan Database Schema
-- RDS PostgreSQL

-- States
CREATE TABLE states (
    abbrev VARCHAR(2) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    plan_count INTEGER DEFAULT 0
);

-- Plans
CREATE TABLE plans (
    plan_id VARCHAR(50) PRIMARY KEY,
    state_abbrev VARCHAR(2) REFERENCES states(abbrev),
    plan_name TEXT NOT NULL,
    plan_type VARCHAR(100),
    category VARCHAR(10), -- MAPD, PD, MA
    organization TEXT,
    
    -- Premiums
    monthly_premium_display VARCHAR(200),
    monthly_premium_value DECIMAL(10,2),
    health_premium DECIMAL(10,2),
    drug_premium DECIMAL(10,2),
    
    -- Deductibles
    health_deductible_display VARCHAR(200),
    health_deductible_value DECIMAL(10,2),
    drug_deductible_display VARCHAR(200),
    drug_deductible_value DECIMAL(10,2),
    
    -- Out of Pocket
    max_out_of_pocket_display VARCHAR(200),
    max_out_of_pocket_value DECIMAL(10,2),
    
    -- Full JSON data for complete details
    plan_info JSONB,
    premiums JSONB,
    deductibles JSONB,
    out_of_pocket JSONB,
    benefits JSONB,
    drug_coverage JSONB,
    extra_benefits JSONB,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Counties
CREATE TABLE counties (
    id SERIAL PRIMARY KEY,
    state_abbrev VARCHAR(2) REFERENCES states(abbrev),
    county_name VARCHAR(100) NOT NULL,
    fips VARCHAR(5) NOT NULL,
    UNIQUE(state_abbrev, county_name)
);

-- Plan-County Junction (which plans serve which counties)
CREATE TABLE plan_counties (
    plan_id VARCHAR(50) REFERENCES plans(plan_id),
    county_id INTEGER REFERENCES counties(id),
    all_counties BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (plan_id, county_id)
);

-- ZIP Codes
CREATE TABLE zip_codes (
    zip_code VARCHAR(5) PRIMARY KEY,
    multi_county BOOLEAN DEFAULT FALSE,
    multi_state BOOLEAN DEFAULT FALSE,
    primary_state VARCHAR(2),
    states TEXT[] -- Array of state abbreviations
);

-- ZIP-County Junction (which counties each ZIP touches)
CREATE TABLE zip_counties (
    zip_code VARCHAR(5) REFERENCES zip_codes(zip_code),
    county_id INTEGER REFERENCES counties(id),
    state_abbrev VARCHAR(2),
    ratio DECIMAL(5,4) DEFAULT 1.0, -- Percentage of ZIP in this county
    PRIMARY KEY (zip_code, county_id)
);

-- Indexes for fast queries
CREATE INDEX idx_plans_state ON plans(state_abbrev);
CREATE INDEX idx_plans_category ON plans(category);
CREATE INDEX idx_plans_premium ON plans(monthly_premium_value);
CREATE INDEX idx_plan_counties_plan ON plan_counties(plan_id);
CREATE INDEX idx_plan_counties_county ON plan_counties(county_id);
CREATE INDEX idx_counties_state ON counties(state_abbrev);
CREATE INDEX idx_zip_counties_zip ON zip_counties(zip_code);
CREATE INDEX idx_zip_counties_county ON zip_counties(county_id);

-- Function to get plans by ZIP code
CREATE OR REPLACE FUNCTION get_plans_by_zip(
    p_zip_code VARCHAR(5),
    p_category VARCHAR(10) DEFAULT NULL
)
RETURNS TABLE (
    plan_id VARCHAR(50),
    plan_name TEXT,
    category VARCHAR(10),
    monthly_premium VARCHAR(50),
    health_deductible VARCHAR(50),
    drug_deductible VARCHAR(50),
    plan_data JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT
        p.plan_id,
        p.plan_name,
        p.category,
        p.monthly_premium_display,
        p.health_deductible_display,
        p.drug_deductible_display,
        jsonb_build_object(
            'plan_id', p.plan_id,
            'category', p.category,
            'plan_type', p.plan_type,
            'plan_info', p.plan_info,
            'premiums', p.premiums,
            'deductibles', p.deductibles,
            'out_of_pocket', p.out_of_pocket,
            'benefits', p.benefits,
            'drug_coverage', p.drug_coverage,
            'extra_benefits', p.extra_benefits
        ) as plan_data
    FROM plans p
    INNER JOIN plan_counties pc ON p.plan_id = pc.plan_id
    INNER JOIN zip_counties zc ON pc.county_id = zc.county_id
    WHERE zc.zip_code = p_zip_code
        AND (p_category IS NULL OR p.category = p_category)
    ORDER BY p.category, p.monthly_premium_value NULLS LAST;
END;
$$ LANGUAGE plpgsql;
