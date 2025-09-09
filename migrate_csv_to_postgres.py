"""
Script untuk migrasi CSV K-pop database ke PostgreSQL Railway
"""
import os
import pandas as pd
import psycopg2
from sqlalchemy import create_engine
import logging
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
        # Baca CSV file - prioritas Google Sheets untuk data terbaru
        kpop_csv_id = os.getenv("KPOP_CSV_ID")
        
        if kpop_csv_id:
            # Load dari Google Sheets (data terbaru)
            csv_url = f"https://docs.google.com/spreadsheets/d/{kpop_csv_id}/export?format=csv"
            logger.info(f"Membaca CSV dari Google Sheets: {kpop_csv_id}")
            df = pd.read_csv(csv_url)
            logger.info(f"Google Sheets CSV berhasil dibaca: {len(df)} rows")
        else:
            # Fallback ke file lokal jika ada
            csv_path = "Database/DATABASE_KPOP (1).csv"
            logger.info(f"Membaca CSV dari file lokal: {csv_path}")
            df = pd.read_csv(csv_path)
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
        
        # Import data ke PostgreSQL
        df_renamed.to_sql(
            'kpop_members', 
            engine, 
            if_exists='replace',  # Replace table jika sudah ada
            index=False,
            method='multi'
        )
        
        logger.info(f"✅ Berhasil import {len(df_renamed)} records ke PostgreSQL")
        
        # Verifikasi data
        with engine.connect() as conn:
            result = conn.execute("SELECT COUNT(*) FROM kpop_members")
            count = result.fetchone()[0]
            logger.info(f"✅ Verifikasi: {count} records di database")
            
            # Sample data
            sample = conn.execute("SELECT stage_name, group_name FROM kpop_members LIMIT 5")
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
            conn.execute(indexes_sql)
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
