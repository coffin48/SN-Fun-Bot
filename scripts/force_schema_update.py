#!/usr/bin/env python3
"""
Force Schema Update Script
Drop old table dan create new schema untuk DATABASE KPOP IDOL.csv
"""

import os
import logging
from sqlalchemy import create_engine, text

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def force_schema_update():
    """Force update PostgreSQL schema untuk DATABASE KPOP IDOL.csv"""
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable tidak ditemukan")
        return False
    
    try:
        engine = create_engine(database_url)
        logger.info("Connected to PostgreSQL")
        
        with engine.connect() as conn:
            # Step 1: Drop existing table
            logger.info("🗑️ Dropping old kpop_members table...")
            conn.execute(text("DROP TABLE IF EXISTS kpop_members CASCADE;"))
            conn.commit()
            logger.info("✅ Old table dropped")
            
            # Step 2: Create new schema with all columns
            logger.info("🏗️ Creating new schema for DATABASE KPOP IDOL.csv...")
            
            create_table_sql = """
            CREATE TABLE kpop_members (
                id SERIAL PRIMARY KEY,
                group_name VARCHAR(255),
                fandom VARCHAR(255),
                stage_name VARCHAR(255) NOT NULL,
                korean_stage_name VARCHAR(255),
                korean_name VARCHAR(255),
                full_name VARCHAR(255),
                date_of_birth DATE,
                former_group VARCHAR(255),
                country VARCHAR(100),
                height INTEGER,
                weight INTEGER,
                birthplace VARCHAR(255),
                gender CHAR(1) CHECK (gender IN ('M', 'F', '')),
                instagram VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            conn.execute(text(create_table_sql))
            conn.commit()
            logger.info("✅ New table created with all columns")
            
            # Step 3: Create indexes
            logger.info("📊 Creating indexes...")
            
            indexes_sql = """
            -- Basic indexes
            CREATE INDEX idx_stage_name ON kpop_members(stage_name);
            CREATE INDEX idx_group_name ON kpop_members(group_name);
            CREATE INDEX idx_full_name ON kpop_members(full_name);
            CREATE INDEX idx_korean_stage_name ON kpop_members(korean_stage_name);
            CREATE INDEX idx_korean_name ON kpop_members(korean_name);
            CREATE INDEX idx_country ON kpop_members(country);
            CREATE INDEX idx_gender ON kpop_members(gender);
            
            -- Trigram indexes for fuzzy search
            CREATE EXTENSION IF NOT EXISTS pg_trgm;
            CREATE INDEX idx_stage_name_trgm ON kpop_members USING gin(stage_name gin_trgm_ops);
            CREATE INDEX idx_group_name_trgm ON kpop_members USING gin(group_name gin_trgm_ops);
            CREATE INDEX idx_korean_name_trgm ON kpop_members USING gin(korean_name gin_trgm_ops);
            """
            
            conn.execute(text(indexes_sql))
            conn.commit()
            logger.info("✅ Indexes created")
            
            # Step 4: Verify schema
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'kpop_members' 
                ORDER BY ordinal_position
            """))
            
            columns = result.fetchall()
            logger.info("✅ New schema verified:")
            for col_name, col_type in columns:
                logger.info(f"  - {col_name}: {col_type}")
            
            logger.info("🎉 Schema update completed successfully!")
            logger.info("💡 Now run migration script to populate data")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Schema update failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting force schema update...")
    
    if force_schema_update():
        logger.info("✅ Schema update completed!")
        logger.info("Next: Run migration script to populate data")
    else:
        logger.error("❌ Schema update failed!")
