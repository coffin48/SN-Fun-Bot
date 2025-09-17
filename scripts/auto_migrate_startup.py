"""
Auto-migration script yang dijalankan saat Railway startup
Script ini akan otomatis migrasi DATABASE KPOP IDOL.csv ke PostgreSQL jika belum ada data
Updated untuk menggunakan DATABASE KPOP IDOL.csv dengan semua kolom lengkap
"""
import os
import sys
import logging

# Fix import path untuk Railway deployment
try:
    from scripts.migrate_csv_to_postgres import migrate_csv_to_postgres, create_indexes
except ImportError:
    # Fallback untuk Railway deployment
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
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
                    logger.warning(f"Table exists but error checking data: {e}")
                    # Table exists but has issues, trigger migration
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
    force_migration = os.getenv("FORCE_MIGRATION", "false").lower() == "true"
    
    if check_postgres_has_data() and not force_migration:
        logger.info("✅ PostgreSQL already has data - skipping migration")
        logger.info("💡 Set FORCE_MIGRATION=true to force re-migration")
        return True
    
    if force_migration:
        logger.debug("🔄 FORCE_MIGRATION enabled - will re-migrate data")
    
    # Jalankan migrasi
    logger.debug("🚀 Starting automatic CSV to PostgreSQL migration...")
    
    try:
        # Check if schema needs update first
        if not _check_schema_compatibility():
            logger.info("🔄 Schema incompatible, updating schema first...")
            if not _update_schema():
                logger.error("❌ Schema update failed!")
                return False
        
        if migrate_csv_to_postgres():
            logger.debug("📊 Creating database indexes...")
            create_indexes()
            logger.debug("✅ Auto-migration completed successfully!")
            return True
        else:
            logger.error("❌ Auto-migration failed!")
            return False
            
    except Exception as e:
        logger.error(f"❌ Auto-migration error: {e}")
        return False

def _check_schema_compatibility():
    """Check if PostgreSQL schema has korean_name column"""
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            return False
            
        from sqlalchemy import create_engine, text
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Check if korean_name column exists
            result = conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.columns 
                WHERE table_name = 'kpop_members' 
                AND column_name = 'korean_name'
            """))
            
            has_korean_name = result.fetchone()[0] > 0
            logger.info(f"Schema compatibility check: korean_name exists = {has_korean_name}")
            return has_korean_name
            
    except Exception as e:
        logger.warning(f"Schema compatibility check failed: {e}")
        return False

def _update_schema():
    """Update PostgreSQL schema to include new columns"""
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            return False
            
        from sqlalchemy import create_engine, text
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            logger.info("🔄 Updating PostgreSQL schema...")
            
            # Drop and recreate table with new schema
            conn.execute(text("DROP TABLE IF EXISTS kpop_members CASCADE;"))
            
            # Create new table with all columns
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
            
            logger.info("✅ Schema updated successfully")
            return True
            
    except Exception as e:
        logger.error(f"Schema update failed: {e}")
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
