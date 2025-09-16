"""
Script untuk migrasi DATABASE KPOP IDOL.csv ke PostgreSQL Railway
Updated untuk menggunakan DATABASE KPOP IDOL.csv dengan semua kolom lengkap
"""
import os
import pandas as pd
import logging
import requests
import re
from io import StringIO
from sqlalchemy import create_engine, text
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_csv_to_postgres():
    """Migrasi CSV ke PostgreSQL dengan error handling"""
    
    # Database connection
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable tidak ditemukan")
        return False
    
    try:
        # Priority 1: Local DATABASE KPOP IDOL.csv (target file)
        local_csv_path = "Database/DATABASE KPOP IDOL.csv"
        
        if os.path.exists(local_csv_path):
            logger.info(f"Loading target CSV: {local_csv_path}")
            df = pd.read_csv(local_csv_path)
            logger.info(f"✅ CSV loaded from local file: {len(df)} records")
        else:
            logger.error(f"Target CSV file not found: {local_csv_path}")
            
            # Fallback: Try GitHub raw CSV - DATABASE KPOP IDOL.csv
            try:
                github_url = "https://raw.githubusercontent.com/coffin48/SN-Fun-Bot/main/Database/DATABASE%20KPOP%20IDOL.csv"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                logger.info(f"Fallback: Loading from GitHub - {github_url}")
                response = requests.get(github_url, headers=headers)
                response.raise_for_status()
                df = pd.read_csv(StringIO(response.text))
                logger.info(f"✅ DATABASE KPOP IDOL.csv loaded from GitHub: {len(df)} records")
                
            except Exception as github_error:
                logger.error(f"GitHub CSV fallback failed: {github_error}")
                raise Exception("No CSV source available")
        
        # Bersihkan data
        df = df.fillna('')  # Replace NaN dengan string kosong
        
        # Konversi Date of Birth ke format yang benar
        df['Date of Birth'] = pd.to_datetime(df['Date of Birth'], errors='coerce')
        
        # Rename kolom sesuai schema PostgreSQL untuk DATABASE KPOP IDOL.csv
        df_renamed = df.rename(columns={
            'Group': 'group_name',
            'Fandom': 'fandom', 
            'Stage Name': 'stage_name',
            'Korean Stage Name': 'korean_stage_name',
            'Korean Name': 'korean_name',
            'Full Name': 'full_name',
            'Date of Birth': 'date_of_birth',
            'Former Group': 'former_group',
            'Country': 'country',
            'Height': 'height',
            'Weight': 'weight',
            'Birthplace': 'birthplace',
            'Gender': 'gender',
            'Instagram': 'instagram'
        })
        
        # Koneksi ke PostgreSQL
        engine = create_engine(database_url)
        logger.info("Koneksi PostgreSQL berhasil")
        
        # Create table schema terlebih dahulu
        with engine.connect() as conn:
            # Create table dengan schema yang benar untuk DATABASE KPOP IDOL.csv
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS kpop_members (
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
            logger.info("✅ Table kpop_members created/verified")
        
        # Clear existing data untuk fresh import
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM kpop_members"))
            conn.commit()
            logger.info("✅ Cleared existing data for fresh import")
        
        # Import data ke PostgreSQL
        df_renamed.to_sql(
            'kpop_members', 
            engine, 
            if_exists='append',  # Append data ke table yang sudah ada
            index=False,
            method='multi'
        )
        
        logger.info(f"✅ Berhasil import {len(df_renamed)} records ke PostgreSQL")
        
        # Verifikasi data
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM kpop_members"))
            count = result.fetchone()[0]
            logger.info(f"✅ Verifikasi: {count} records di database")
            
            # Sample data
            sample = conn.execute(text("SELECT stage_name, group_name FROM kpop_members LIMIT 5"))
            logger.info("Sample data:")
            for row in sample:
                logger.info(f"  - {row[0]} ({row[1]})")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error migrasi: {e}")
        return False

def create_indexes():
    """Buat indexes untuk performa query"""
    database_url = os.getenv("DATABASE_URL")
    
    try:
        engine = create_engine(database_url)
        
        indexes_sql = """
        CREATE INDEX IF NOT EXISTS idx_stage_name ON kpop_members(stage_name);
        CREATE INDEX IF NOT EXISTS idx_group_name ON kpop_members(group_name);
        CREATE INDEX IF NOT EXISTS idx_full_name ON kpop_members(full_name);
        CREATE INDEX IF NOT EXISTS idx_korean_stage_name ON kpop_members(korean_stage_name);
        CREATE INDEX IF NOT EXISTS idx_korean_name ON kpop_members(korean_name);
        CREATE INDEX IF NOT EXISTS idx_gender ON kpop_members(gender);
        CREATE INDEX IF NOT EXISTS idx_country ON kpop_members(country);
        
        -- Trigram indexes untuk fuzzy search
        CREATE EXTENSION IF NOT EXISTS pg_trgm;
        CREATE INDEX IF NOT EXISTS idx_stage_name_trgm ON kpop_members USING gin(stage_name gin_trgm_ops);
        CREATE INDEX IF NOT EXISTS idx_group_name_trgm ON kpop_members USING gin(group_name gin_trgm_ops);
        CREATE INDEX IF NOT EXISTS idx_korean_name_trgm ON kpop_members USING gin(korean_name gin_trgm_ops);
        """
        
        with engine.connect() as conn:
            conn.execute(text(indexes_sql))
            conn.commit()
        
        logger.info("✅ Indexes berhasil dibuat")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error membuat indexes: {e}")
        return False

if __name__ == "__main__":
    logger.info("🚀 Memulai migrasi CSV ke PostgreSQL...")
    
    if migrate_csv_to_postgres():
        logger.info("📊 Membuat indexes...")
        create_indexes()
        logger.info("✅ Migrasi selesai!")
    else:
        logger.error("❌ Migrasi gagal!")
