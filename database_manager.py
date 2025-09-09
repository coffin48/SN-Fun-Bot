"""
Database Manager - Menangani koneksi PostgreSQL dan fallback ke CSV
"""
import os
import pandas as pd
import logger
from typing import Optional, List, Dict

# Optional PostgreSQL imports dengan graceful fallback
try:
    import psycopg2
    from sqlalchemy import create_engine, text
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    logger.logger.warning("PostgreSQL dependencies not available - using CSV fallback only")

class DatabaseManager:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        self.kpop_csv_id = os.getenv("KPOP_CSV_ID")
        self.engine = None
        self.kpop_df = None
        
        # Inisialisasi database
        self._initialize_database()
    
    def _initialize_database(self):
        """Inisialisasi database dengan fallback ke CSV"""
        try:
            # Coba koneksi PostgreSQL terlebih dahulu jika dependencies tersedia
            if POSTGRES_AVAILABLE and self.database_url:
                self.engine = create_engine(self.database_url)
                self._test_postgres_connection()
                logger.logger.info("✅ PostgreSQL connection established")
                return
        except Exception as e:
            logger.logger.warning(f"PostgreSQL unavailable: {e}")
        
        # Fallback ke CSV jika PostgreSQL gagal atau tidak tersedia
        self._load_csv_fallback()
    
    def _test_postgres_connection(self):
        """Test koneksi PostgreSQL"""
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM kpop_members"))
            count = result.fetchone()[0]
            logger.logger.info(f"PostgreSQL ready: {count} K-pop members")
    
    def _load_csv_fallback(self):
        """Load CSV sebagai fallback"""
        try:
            if self.kpop_csv_id:
                # Load dari Google Sheets
                csv_url = f"https://docs.google.com/spreadsheets/d/{self.kpop_csv_id}/export?format=csv"
                self.kpop_df = pd.read_csv(csv_url)
            else:
                # Load dari file lokal
                self.kpop_df = pd.read_csv("Database/DATABASE_KPOP (1).csv")
            
            logger.logger.info(f"✅ CSV fallback loaded: {len(self.kpop_df)} records")
        except Exception as e:
            logger.logger.error(f"❌ Failed to load CSV: {e}")
            self.kpop_df = pd.DataFrame()
    
    def search_members(self, query: str, limit: int = 10) -> List[Dict]:
        """Pencarian member dengan PostgreSQL atau CSV fallback"""
        if self.engine:
            return self._search_postgres(query, limit)
        else:
            return self._search_csv(query, limit)
    
    def _search_postgres(self, query: str, limit: int) -> List[Dict]:
        """Pencarian menggunakan PostgreSQL dengan fuzzy matching"""
        if not POSTGRES_AVAILABLE or not self.engine:
            return self._search_csv(query, limit)
            
        try:
            # Query dengan similarity search menggunakan trigram
            sql = text("""
                SELECT stage_name, group_name, korean_stage_name, full_name, 
                       date_of_birth, instagram,
                       GREATEST(
                           similarity(stage_name, :query),
                           similarity(group_name, :query),
                           similarity(full_name, :query),
                           similarity(korean_stage_name, :query)
                       ) as score
                FROM kpop_members 
                WHERE stage_name ILIKE :pattern 
                   OR group_name ILIKE :pattern
                   OR full_name ILIKE :pattern
                   OR korean_stage_name ILIKE :pattern
                   OR similarity(stage_name, :query) > 0.3
                   OR similarity(group_name, :query) > 0.3
                ORDER BY score DESC, stage_name ASC
                LIMIT :limit
            """)
            
            with self.engine.connect() as conn:
                result = conn.execute(sql, {
                    'query': query,
                    'pattern': f'%{query}%',
                    'limit': limit
                })
                
                return [dict(row._mapping) for row in result]
                
        except Exception as e:
            logger.logger.error(f"PostgreSQL search error: {e}")
            return self._search_csv(query, limit)
    
    def _search_csv(self, query: str, limit: int) -> List[Dict]:
        """Pencarian menggunakan CSV dengan pandas"""
        if self.kpop_df is None or self.kpop_df.empty:
            return []
        
        try:
            query_lower = query.lower()
            
            # Filter berdasarkan multiple columns
            mask = (
                self.kpop_df['Stage Name'].str.lower().str.contains(query_lower, na=False) |
                self.kpop_df['Group'].str.lower().str.contains(query_lower, na=False) |
                self.kpop_df['Full Name'].str.lower().str.contains(query_lower, na=False) |
                self.kpop_df['Korean Stage Name'].str.lower().str.contains(query_lower, na=False)
            )
            
            results = self.kpop_df[mask].head(limit)
            
            # Convert ke format dictionary
            return [{
                'stage_name': row['Stage Name'],
                'group_name': row['Group'],
                'korean_stage_name': row.get('Korean Stage Name', ''),
                'full_name': row.get('Full Name', ''),
                'date_of_birth': row.get('Date of Birth', ''),
                'instagram': row.get('Instagram', ''),
                'score': 1.0  # Default score untuk CSV
            } for _, row in results.iterrows()]
            
        except Exception as e:
            logger.logger.error(f"CSV search error: {e}")
            return []
    
    def get_member_by_name(self, stage_name: str) -> Optional[Dict]:
        """Ambil member spesifik berdasarkan stage name"""
        results = self.search_members(stage_name, limit=1)
        return results[0] if results else None
    
    def get_group_members(self, group_name: str) -> List[Dict]:
        """Ambil semua member dari grup tertentu"""
        if POSTGRES_AVAILABLE and self.engine:
            try:
                sql = text("""
                    SELECT stage_name, group_name, korean_stage_name, full_name, 
                           date_of_birth, instagram
                    FROM kpop_members 
                    WHERE group_name ILIKE :group_name
                    ORDER BY stage_name ASC
                """)
                
                with self.engine.connect() as conn:
                    result = conn.execute(sql, {'group_name': f'%{group_name}%'})
                    return [dict(row._mapping) for row in result]
                    
            except Exception as e:
                logger.logger.error(f"PostgreSQL group search error: {e}")
        
        # CSV fallback
        if self.kpop_df is not None:
            mask = self.kpop_df['Group'].str.lower().str.contains(group_name.lower(), na=False)
            results = self.kpop_df[mask]
            
            return [{
                'stage_name': row['Stage Name'],
                'group_name': row['Group'],
                'korean_stage_name': row.get('Korean Stage Name', ''),
                'full_name': row.get('Full Name', ''),
                'date_of_birth': row.get('Date of Birth', ''),
                'instagram': row.get('Instagram', '')
            } for _, row in results.iterrows()]
        
        return []
    
    def get_database_stats(self) -> Dict:
        """Statistik database untuk monitoring"""
        if POSTGRES_AVAILABLE and self.engine:
            try:
                with self.engine.connect() as conn:
                    total = conn.execute(text("SELECT COUNT(*) FROM kpop_members")).fetchone()[0]
                    groups = conn.execute(text("SELECT COUNT(DISTINCT group_name) FROM kpop_members")).fetchone()[0]
                    
                return {
                    'source': 'PostgreSQL',
                    'total_members': total,
                    'total_groups': groups,
                    'status': 'connected'
                }
            except Exception as e:
                logger.logger.error(f"Stats error: {e}")
        
        # CSV fallback stats
        if self.kpop_df is not None:
            return {
                'source': 'CSV',
                'total_members': len(self.kpop_df),
                'total_groups': self.kpop_df['Group'].nunique(),
                'status': 'fallback'
            }
        
        return {
            'source': 'none',
            'total_members': 0,
            'total_groups': 0,
            'status': 'error'
        }
