"""
Script untuk migrasi CSV K-pop database ke PostgreSQL Railway
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
        # Priority 1: GitHub raw CSV (always latest)
        try:
            github_url = "https://raw.githubusercontent.com/coffin48/SN-Fun-Bot/main/Database/DATABASE_KPOP%20(1).csv"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(github_url, headers=headers)
            response.raise_for_status()
            df = pd.read_csv(StringIO(response.text))
            logger.info(f"✅ CSV loaded from GitHub: {len(df)} records")
            
        except Exception as github_error:
            logger.warning(f"GitHub CSV failed: {github_error}")
            
            # Priority 2: Environment variable source
            kpop_csv_id = os.getenv("KPOP_CSV_ID")
            if kpop_csv_id:
                logger.info(f"Fallback ke environment source: {kpop_csv_id}")
                try:
                    # Coba Google Drive
                    drive_url = f"https://drive.google.com/uc?id={kpop_csv_id}&export=download"
                    response = requests.get(drive_url, headers=headers)
                    
                    # Handle Google Drive virus scan warning
                    if 'virus scan warning' in response.text.lower():
                        confirm_token = re.search(r'confirm=([0-9A-Za-z_]+)', response.text)
                        if confirm_token:
                            confirm_url = f"{drive_url}&confirm={confirm_token.group(1)}"
                            response = requests.get(confirm_url, headers=headers)
                    
                    response.raise_for_status()
                    df = pd.read_csv(StringIO(response.text))
                    logger.info(f"✅ CSV loaded from Google Drive: {len(df)} records")
                    
                except Exception as drive_error:
                    logger.warning(f"Google Drive failed: {drive_error}")
                    # Fallback ke Google Sheets
                    try:
                        csv_url = f"https://docs.google.com/spreadsheets/d/{kpop_csv_id}/export?format=csv&gid=0"
                        response = requests.get(csv_url, headers=headers)
                        response.raise_for_status()
                        df = pd.read_csv(StringIO(response.text))
                        logger.info(f"✅ CSV loaded from Google Sheets: {len(df)} records")
                    except Exception as sheets_error:
                        logger.error(f"Environment sources failed: {sheets_error}")
                        raise
            else:
                # Priority 3: Local file
                logger.info("Fallback ke file lokal")
                df = pd.read_csv("Database/DATABASE_KPOP (1).csv")
                logger.info(f"Local CSV berhasil dibaca: {len(df)} rows")
        
        # Bersihkan data
        df = df.fillna('')  # Replace NaN dengan string kosong
        
        # Konversi Date of Birth ke format yang benar
        df['Date of Birth'] = pd.to_datetime(df['Date of Birth'], errors='coerce')
        
        # Rename kolom sesuai schema PostgreSQL
        df_renamed = df.rename(columns={
            'Group': 'group_name',
            'Fandom': 'fandom', 
            'Stage Name': 'stage_name',
            'Korean Stage Name': 'korean_stage_name',
            'Full Name': 'full_name',
            'Date of Birth': 'date_of_birth',
            'Former Group': 'former_group',
            'Instagram': 'instagram'
        })
        
        # Koneksi ke PostgreSQL
        engine = create_engine(database_url)
        logger.info("Koneksi PostgreSQL berhasil")
        
        # Create table schema terlebih dahulu
        with engine.connect() as conn:
            # Create table dengan schema yang benar
            create_table_sql = """
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
        
        -- Trigram indexes untuk fuzzy search
        CREATE EXTENSION IF NOT EXISTS pg_trgm;
        CREATE INDEX IF NOT EXISTS idx_stage_name_trgm ON kpop_members USING gin(stage_name gin_trgm_ops);
        CREATE INDEX IF NOT EXISTS idx_group_name_trgm ON kpop_members USING gin(group_name gin_trgm_ops);
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
