"""
Auto-migration script yang dijalankan saat Railway startup
Script ini akan otomatis migrasi CSV ke PostgreSQL jika belum ada data
"""
import os
import sys
import logging
from migrate_csv_to_postgres import migrate_csv_to_postgres, create_indexes

# Setup logging untuk Railway
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_postgres_has_data():
    """Cek apakah PostgreSQL sudah memiliki data"""
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            return False
            
        from sqlalchemy import create_engine, text
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Cek apakah table kpop_members ada
            result = conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = 'kpop_members'
            """))
            
            table_exists = result.fetchone()[0] > 0
            
            if table_exists:
                # Table ada, cek jumlah data
                try:
                    result = conn.execute(text("SELECT COUNT(*) FROM kpop_members"))
                    row_count = result.fetchone()[0]
                    logger.info(f"PostgreSQL table exists with {row_count} records")
                    return row_count > 0
                except Exception as e:
                    logger.warning(f"Error checking table data: {e}")
                    return False
            else:
                logger.info("PostgreSQL table kpop_members does not exist")
                return False
                
    except Exception as e:
        logger.warning(f"Cannot check PostgreSQL data: {e}")
        return False

def auto_migrate_if_needed():
    """Auto-migrate jika PostgreSQL kosong atau belum ada"""
    logger.info("🔍 Checking if PostgreSQL migration is needed...")
    
    # Cek apakah PostgreSQL dependencies tersedia
    try:
        import psycopg2
        from sqlalchemy import create_engine
    except ImportError:
        logger.warning("PostgreSQL dependencies not available - skipping migration")
        return False
    
    # Cek apakah DATABASE_URL tersedia
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.warning("DATABASE_URL not found - skipping migration")
        return False
    
    # Cek apakah PostgreSQL sudah memiliki data
    if check_postgres_has_data():
        logger.info("✅ PostgreSQL already has data - skipping migration")
        return True
    
    # Jalankan migrasi
    logger.info("🚀 Starting automatic CSV to PostgreSQL migration...")
    
    try:
        if migrate_csv_to_postgres():
            logger.info("📊 Creating database indexes...")
            create_indexes()
            logger.info("✅ Auto-migration completed successfully!")
            return True
        else:
            logger.error("❌ Auto-migration failed!")
            return False
            
    except Exception as e:
        logger.error(f"❌ Auto-migration error: {e}")
        return False

if __name__ == "__main__":
    # Jalankan auto-migration
    success = auto_migrate_if_needed()
    
    if success:
        logger.info("🎉 Database ready for bot startup!")
        sys.exit(0)  # Success
    else:
        logger.warning("⚠️ Migration failed - bot will use CSV fallback")
        sys.exit(0)  # Don't fail startup, let bot use fallback
