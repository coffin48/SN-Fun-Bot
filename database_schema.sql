-- Schema untuk database K-pop PostgreSQL - Updated untuk DATABASE KPOP IDOL.csv
CREATE TABLE IF NOT EXISTS kpop_members (
    id SERIAL PRIMARY KEY,
    group_name VARCHAR(255),
    fandom VARCHAR(255),
    stage_name VARCHAR(255) NOT NULL,
    korean_stage_name VARCHAR(255),
    korean_name VARCHAR(255),          -- NEW: Korean Name
    full_name VARCHAR(255),
    date_of_birth DATE,
    former_group VARCHAR(255),
    country VARCHAR(100),              -- NEW: Country
    height INTEGER,                    -- NEW: Height
    weight INTEGER,                    -- NEW: Weight
    birthplace VARCHAR(255),           -- NEW: Birthplace
    gender CHAR(1) CHECK (gender IN ('M', 'F', '')), -- NEW: Gender
    instagram VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index untuk pencarian cepat - Updated untuk DATABASE KPOP IDOL.csv
CREATE INDEX IF NOT EXISTS idx_stage_name ON kpop_members(stage_name);
CREATE INDEX IF NOT EXISTS idx_group_name ON kpop_members(group_name);
CREATE INDEX IF NOT EXISTS idx_full_name ON kpop_members(full_name);
CREATE INDEX IF NOT EXISTS idx_korean_stage_name ON kpop_members(korean_stage_name);
CREATE INDEX IF NOT EXISTS idx_korean_name ON kpop_members(korean_name);        -- NEW
CREATE INDEX IF NOT EXISTS idx_country ON kpop_members(country);                -- NEW
CREATE INDEX IF NOT EXISTS idx_gender ON kpop_members(gender);                  -- NEW

-- Index untuk fuzzy search (trigram)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS idx_stage_name_trgm ON kpop_members USING gin(stage_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_group_name_trgm ON kpop_members USING gin(group_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_korean_name_trgm ON kpop_members USING gin(korean_name gin_trgm_ops); -- NEW
