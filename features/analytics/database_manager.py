"""
Database Manager - Menangani koneksi PostgreSQL dan fallback ke CSV
"""
import os
import pandas as pd
from core.logger import core.logger
from typing import Optional, List, Dict

# Optional PostgreSQL imports dengan graceful fallback
try:
    import psycopg2
    from sqlalchemy import create_engine, text
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    logger.warning("PostgreSQL dependencies not available - using CSV fallback only")

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
                logger.info("✅ PostgreSQL connection established")
                return
        except Exception as e:
            logger.warning(f"PostgreSQL unavailable: {e}")
        
        # Fallback ke CSV jika PostgreSQL gagal atau tidak tersedia
        self._load_csv_fallback()
    
    def _test_postgres_connection(self):
        """Test koneksi PostgreSQL"""
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM kpop_members"))
            count = result.fetchone()[0]
            logger.info(f"PostgreSQL ready: {count} K-pop members")
    
    def _load_csv_fallback(self):
        """Load CSV sebagai fallback"""
        try:
            # Priority 1: GitHub raw CSV (always latest)
            try:
                self._load_from_github()
                return
            except Exception as github_error:
                logger.warning(f"GitHub CSV failed: {github_error}")
            
            # Priority 2: Environment variable (Google Drive/Sheets)
            if self.kpop_csv_id:
                try:
                    self._load_from_google_drive()
                    return
                except Exception as drive_error:
                    logger.warning(f"Google Drive failed: {drive_error}")
                    try:
                        self._load_from_google_sheets()
                        return
                    except Exception as sheets_error:
                        logger.warning(f"Google Sheets failed: {sheets_error}")
            
            # Priority 3: Local file
            self.kpop_df = pd.read_csv("Database/DATABASE_KPOP (1).csv")
            logger.info(f"✅ Local CSV loaded: {len(self.kpop_df)} records")
            
        except Exception as e:
            logger.error(f"❌ All CSV sources failed: {e}")
            self.kpop_df = pd.DataFrame()
    
    def _load_from_github(self):
        """Load CSV dari GitHub raw URL"""
        import requests
        from io import StringIO
        
        # GitHub raw CSV URL
        github_url = "https://raw.githubusercontent.com/coffin48/SN-Fun-Bot/main/Database/DATABASE_KPOP%20(1).csv"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(github_url, headers=headers)
        response.raise_for_status()
        
        self.kpop_df = pd.read_csv(StringIO(response.text))
        logger.info(f"✅ CSV from GitHub loaded: {len(self.kpop_df)} records")
    
    def _is_google_drive_id(self, file_id: str) -> bool:
        """Deteksi apakah ID adalah Google Drive file atau Google Sheets"""
        # ID 15SjsUKHLaYQ5wZHR013Lb38M4uY-tiVE adalah Google Drive file
        # Coba Google Drive dulu, jika gagal fallback ke Sheets
        return True
    
    def _load_from_google_drive(self):
        """Load CSV dari Google Drive"""
        import requests
        from io import StringIO
        
        # Google Drive direct download URL
        drive_url = f"https://drive.google.com/uc?id={self.kpop_csv_id}&export=download"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(drive_url, headers=headers)
        
        # Handle Google Drive virus scan warning untuk file besar
        if 'virus scan warning' in response.text.lower():
            # Extract confirm token untuk bypass virus scan
            import re
            confirm_token = re.search(r'confirm=([0-9A-Za-z_]+)', response.text)
            if confirm_token:
                confirm_url = f"{drive_url}&confirm={confirm_token.group(1)}"
                response = requests.get(confirm_url, headers=headers)
        
        response.raise_for_status()
        self.kpop_df = pd.read_csv(StringIO(response.text))
        logger.info(f"✅ CSV from Google Drive loaded: {len(self.kpop_df)} records")
    
    def _load_from_google_sheets(self):
        """Load CSV dari Google Sheets"""
        import requests
        from io import StringIO
        
        # Google Sheets export URL
        sheets_url = f"https://docs.google.com/spreadsheets/d/{self.kpop_csv_id}/export?format=csv&gid=0"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(sheets_url, headers=headers)
        response.raise_for_status()
        
        self.kpop_df = pd.read_csv(StringIO(response.text))
        logger.info(f"✅ CSV from Google Sheets loaded: {len(self.kpop_df)} records")
    
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
            logger.error(f"PostgreSQL search error: {e}")
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
            logger.error(f"CSV search error: {e}")
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
                logger.error(f"PostgreSQL group search error: {e}")
        
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
                    # Check if table exists first
                    table_check = conn.execute(text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = 'kpop_members'
                        )
                    """)).fetchone()[0]
                    
                    if not table_check:
                        logger.warning("Table kpop_members does not exist in PostgreSQL")
                        # Fall through to CSV fallback
                    else:
                        total = conn.execute(text("SELECT COUNT(*) FROM kpop_members")).fetchone()[0]
                        groups = conn.execute(text("SELECT COUNT(DISTINCT group_name) FROM kpop_members")).fetchone()[0]
                        
                        return {
                            'source': 'PostgreSQL',
                            'total_members': total,
                            'total_groups': groups,
                            'status': 'connected'
                        }
            except Exception as e:
                logger.error(f"PostgreSQL stats error: {e}")
                # Fall through to CSV fallback
        
        # CSV fallback stats
        if self.kpop_df is not None and not self.kpop_df.empty:
            try:
                # Handle different possible column names
                group_column = None
                if 'Group' in self.kpop_df.columns:
                    group_column = 'Group'
                elif 'group_name' in self.kpop_df.columns:
                    group_column = 'group_name'
                
                total_groups = self.kpop_df[group_column].nunique() if group_column else 0
                
                return {
                    'source': 'CSV',
                    'total_members': len(self.kpop_df),
                    'total_groups': total_groups,
                    'status': 'fallback'
                }
            except Exception as e:
                logger.error(f"Error getting CSV stats: {e}")
                return {
                    'source': 'CSV',
                    'total_members': len(self.kpop_df) if self.kpop_df is not None else 0,
                    'total_groups': 0,
                    'status': 'error'
                }
        
        return {
            'source': 'none',
            'total_members': 0,
            'total_groups': 0,
            'status': 'error'
        }
