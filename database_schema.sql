-- Schema untuk database K-pop PostgreSQL
CREATE TABLE IF NOT EXISTS kpop_members (
    id SERIAL PRIMARY KEY,
    group_name VARCHAR(255),
    fandom VARCHAR(255),
    stage_name VARCHAR(255) NOT NULL,
    korean_stage_name VARCHAR(255),
    full_name VARCHAR(255),
    date_of_birth DATE,
    former_group VARCHAR(255),
    instagram VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index untuk pencarian cepat
CREATE INDEX IF NOT EXISTS idx_stage_name ON kpop_members(stage_name);
CREATE INDEX IF NOT EXISTS idx_group_name ON kpop_members(group_name);
CREATE INDEX IF NOT EXISTS idx_full_name ON kpop_members(full_name);
CREATE INDEX IF NOT EXISTS idx_korean_stage_name ON kpop_members(korean_stage_name);

-- Index untuk fuzzy search (trigram)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS idx_stage_name_trgm ON kpop_members USING gin(stage_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_group_name_trgm ON kpop_members USING gin(group_name gin_trgm_ops);
