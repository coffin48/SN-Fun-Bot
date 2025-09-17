"""
K-pop Gacha Trading Card System
Sistem gacha untuk generate kartu trading K-pop dengan berbagai rarity
"""

import os
import json
import random
import requests
from io import BytesIO
import pandas as pd
import math
import tempfile
import logging
import hashlib
import time
from functools import wraps

# Try to import PIL with error handling
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: Pillow (PIL) not installed. Gacha system will not work.")

# Note: design_kartu import moved to method level to avoid circular imports
DESIGN_KARTU_AVAILABLE = True

# Setup logger
logger = logging.getLogger(__name__)

class KpopGachaSystem:
    def __init__(self, json_path="data/member_data/Path_Foto_DriveIDs_Real.json", database_path="Database/DATABASE KPOP IDOL.csv"):
        """
        Initialize Kpop Gacha System
        
        Args:
            json_path: Path ke JSON mapping foto yang sudah diperbaiki
            database_path: Path ke CSV database
        """
        # Check dependencies first
        if not PIL_AVAILABLE:
            raise ImportError("Pillow (PIL) is required for gacha system. Install with: pip install Pillow")
        
        if not DESIGN_KARTU_AVAILABLE:
            raise ImportError("design_kartu module is required for gacha system.")
        
        self.json_path = json_path
        self.database_path = database_path
        self.members_data = {}
        self.using_new_database = True  # Flag untuk track database yang digunakan
        
        # OLD GDrive folder IDs dari environment variables
        self.old_gdrive_folder_id = os.getenv('OLD_GDRIVE_FOLDER_ID') or os.getenv('GDRIVE_FOLDER_ID') or ''
        self.kpop_photo_folder_id = self.old_gdrive_folder_id  # Compatibility
        
        # Debug: Log environment variable status
        logger.info(f"🔍 Environment Variables Check:")
        logger.info(f"  OLD_GDRIVE_FOLDER_ID: {'✅ SET' if os.getenv('OLD_GDRIVE_FOLDER_ID') else '❌ NOT SET'}")
        logger.info(f"  GDRIVE_FOLDER_ID: {'✅ SET' if os.getenv('GDRIVE_FOLDER_ID') else '❌ NOT SET'}")
        logger.info(f"  Final old_gdrive_folder_id: '{self.old_gdrive_folder_id}'")
        
        # NEW DATABASE CONFIGURATION (PRIMARY) - from environment variables
        self.new_json_folder_id = os.getenv('NEW_GDRIVE_JSON_FOLDER_ID')
        self.new_photo_folder_id = os.getenv('NEW_GDRIVE_PHOTO_FOLDER_ID')
        self.new_json_url = f"https://drive.google.com/drive/folders/{self.new_json_folder_id}/Path_Foto_DriveIDs_Real.json" if self.new_json_folder_id else None
        
        # OLD DATABASE FALLBACK (from environment variables and local files)
        self.json_path = json_path
        self.database_path = database_path
        # OLD GDrive folder sudah di-set di atas, tidak perlu duplikasi
        self.old_base_url = f"https://drive.google.com/uc?export=view&id=" if self.old_gdrive_folder_id else ""
        # Font path untuk backward compatibility (tidak digunakan di new system)
        self.font_path = "assets/fonts/Gill Sans Bold Italic.otf"
        
        # Initialize data containers
        self.members_data = {}
        self.base_url = ""
        self.using_new_database = False  # Track which database is being used
        
        # Sistem probabilitas rarity (GENEROUS RATES untuk engagement)
        self.RARITY_RATES = {
            "Common": 35,      # 35% (reduced dari 50%)
            "Rare": 35,        # 35% (increased dari 30%)
            "DR": 20,          # 20% (increased dari 15%)
            "SR": 8,           # 8% (increased dari 4%)
            "SAR": 2           # 2% (doubled dari 1%)
        }
        
        # NEW: Image caching system
        self.image_cache = {}
        self.cache_dir = "cache/images"
        self._setup_cache_dir()
        
        # NEW: Retry configuration
        self.max_retries = 3
        self.retry_delay = 1.0
        
        # Load all data once with new database priority
        logger.info("🚀 Starting gacha system initialization...")
        self._load_new_json_data()
        logger.info(f"📊 After JSON load: {len(self.members_data) if self.members_data else 0} members")
        
        self._load_database()
        logger.info(f"📊 After CSV load: {len(self.database) if hasattr(self, 'database') and self.database is not None else 0} CSV records")
        
        self._integrate_csv_data()
        logger.info(f"📊 After integration: {len(self.stage_name_mapping) if hasattr(self, 'stage_name_mapping') else 0} stage mappings")
        logger.info("✅ Gacha system initialization completed")
        
        # Set global instance for design_kartu module
        import sys
        if 'features.gacha_system.kpop_gacha' in sys.modules:
            sys.modules['features.gacha_system.kpop_gacha'].current_gacha_instance = self
        
    def _load_new_json_data(self):
        # Load database - try new database first, fallback to old
        logger.info("🚀 RAILWAY LOG: Starting database initialization...")
        logger.info(f"🔧 Environment check - NEW_JSON_FOLDER_ID: {'SET' if self.new_json_folder_id else 'NOT SET'}")
        logger.info(f"🔧 Environment check - NEW_PHOTO_FOLDER_ID: {'SET' if self.new_photo_folder_id else 'NOT SET'}")
        
        if self.new_json_folder_id and self.new_photo_folder_id:
            logger.info("✅ RAILWAY LOG: NEW database environment variables detected")
            if not self._load_json_from_new_database():
                logger.warning("⚠️ RAILWAY LOG: NEW database failed, falling back to OLD database")
                self._load_json_data_fallback()
            else:
                logger.info("🎯 RAILWAY LOG: NEW database loaded successfully!")
                logger.info(f"📊 RAILWAY LOG: Database contains {len(self.members_data)} members")
                logger.info(f"🌐 RAILWAY LOG: Photo access configured with base URL: {self.base_url}")
        else:
            logger.info("📁 RAILWAY LOG: NEW database env variables not set, using OLD database")
            self._load_json_data_fallback()
        
        # If both failed, try fallback
        if not self.members_data:
            logger.warning("⚠️ RAILWAY LOG: All databases failed, using fallback")
            self._load_json_data_fallback()
        
        # Final status log
        if self.members_data:
            logger.info(f"✅ RAILWAY LOG: Database initialization complete - {len(self.members_data)} members available")
            logger.info(f"🎯 RAILWAY LOG: Using {'NEW' if self.using_new_database else 'OLD'} database system")
        else:
            logger.error("❌ RAILWAY LOG: Database initialization FAILED - no members loaded")
    
    def _load_json_from_new_database(self):
        """Load JSON dari database baru (PRIMARY) - GDrive folder baru"""
        try:
            # Try local file first (for development/testing)
            local_path = "data/member_data/New Json Update.json"
            if os.path.exists(local_path):
                logger.info(f"📁 Using local NEW database file: {local_path}")
                try:
                    with open(local_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Extract members data from the JSON structure
                    members_data = {}
                    for key, value in data.items():
                        if isinstance(value, dict) and 'name' in value and 'photos' in value:
                            members_data[key] = value
                    
                    self.members_data = members_data
                    self.base_url = data.get('base_url', "https://drive.google.com/uc?export=view&id=")
                    self.using_new_database = True
                    logger.info(f"✅ NEW database loaded from local file: {len(self.members_data)} members")
                    logger.info(f"📁 Base URL: {self.base_url}")
                    return True
                except Exception as e:
                    logger.error(f"Local NEW database failed: {e}")
            
            # Fallback: Try multiple possible URLs for new database
            logger.info("🌐 Attempting to access NEW database from Google Drive...")
            possible_urls = [
                # Priority 1: NEW Database JSON file (single source of truth)
                f"https://drive.google.com/uc?id=1h62KxYAHHs_ytO8dmW1MTxXNnvb2MI9k&export=download",
                # Priority 3: Fallback GDrive attempts
                f"https://drive.google.com/uc?id={self.new_json_folder_id}&export=download",
                f"https://docs.google.com/uc?id={self.new_json_folder_id}&export=download"
            ]
            
            for i, url in enumerate(possible_urls, 1):
                try:
                    logger.info(f"🔄 Trying NEW database URL {i}/{len(possible_urls)}: {url[:80]}...")
                    response = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
                    logger.info(f"📡 Response status: {response.status_code}, Content-Type: {response.headers.get('content-type', 'unknown')}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        self.members_data = data.get('members', {})
                        # Use new database base URL format
                        self.base_url = f"https://drive.google.com/uc?export=view&id="
                        self.using_new_database = True  # Mark as using new database
                        logger.info(f"✅ NEW database loaded successfully from GDrive!")
                        logger.info(f"📊 Members loaded: {len(self.members_data)}")
                        logger.info(f"📁 NEW photo folder ID: {self.new_photo_folder_id}")
                        logger.info(f"🌐 Base URL configured: {self.base_url}")
                        return True
                    else:
                        logger.warning(f"⚠️ HTTP {response.status_code} from URL {i}")
                except Exception as e:
                    logger.warning(f"❌ Failed NEW database URL {i}: {str(e)[:100]}")
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to load NEW database: {e}")
            return False
    
    def _load_json_data_fallback(self):
        """Load JSON mapping foto dari database lama (fallback)"""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.members_data = data.get('members', {})
            
            # Check if this is actually NEW database data (has environment variables set)
            if self.new_json_folder_id and self.new_photo_folder_id and len(self.members_data) > 1000:
                # This is NEW database loaded from local file
                self.base_url = f"https://drive.google.com/uc?export=view&id="
                self.using_new_database = True
                logger.info(f"✅ NEW database loaded from local fallback: {len(self.members_data)} members")
                logger.info(f"📁 NEW photo folder: {self.new_photo_folder_id}")
            else:
                # This is OLD database
                if self.old_gdrive_folder_id:
                    self.base_url = self.old_base_url  # From env variable
                    logger.info(f"📁 OLD database using env GDrive folder: {self.old_gdrive_folder_id}")
                else:
                    self.base_url = data.get('base_url', '')  # From local JSON
                    logger.info(f"📁 OLD database using local JSON base_url")
                
                self.using_new_database = False  # Mark as using old database
                logger.info(f"📁 OLD JSON data loaded: {len(self.members_data)} members")
                logger.info(f"📁 OLD base URL: {self.base_url}")
            
        except Exception as e:
            logger.error(f"Failed to load OLD JSON data: {e}")
            self.members_data = {}
            self.base_url = ""
    
    def _load_database(self):
        """Load database K-pop sebagai backup"""
        try:
            self.database = pd.read_csv(self.database_path)
            self.df = self.database  # Keep backward compatibility
            logger.info(f"Backup database loaded: {len(self.database)} members")
        except Exception as e:
            logger.error(f"Failed to load backup database: {e}")
            self.database = pd.DataFrame()
            self.df = pd.DataFrame()
    
    def _setup_cache_dir(self):
        """Setup cache directory untuk image caching"""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            logger.info(f"Cache directory setup: {self.cache_dir}")
        except Exception as e:
            logger.error(f"Failed to setup cache directory: {e}")
    
    def _get_cache_key(self, url):
        """Generate cache key dari URL"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def _get_cached_image_path(self, cache_key):
        """Get path untuk cached image"""
        return os.path.join(self.cache_dir, f"{cache_key}.png")
    
    def _is_image_cached(self, url):
        """Check apakah image sudah di-cache"""
        cache_key = self._get_cache_key(url)
        cache_path = self._get_cached_image_path(cache_key)
        return os.path.exists(cache_path)
    
    def _load_cached_image(self, url):
        """Load image dari cache"""
        try:
            cache_key = self._get_cache_key(url)
            cache_path = self._get_cached_image_path(cache_key)
            
            if os.path.exists(cache_path):
                image = Image.open(cache_path).convert("RGBA")
                logger.debug(f"Image loaded from cache: {cache_key}")
                return image
            return None
        except Exception as e:
            logger.error(f"Error loading cached image: {e}")
            return None
    
    def _save_image_to_cache(self, url, image):
        """Save image ke cache"""
        try:
            cache_key = self._get_cache_key(url)
            cache_path = self._get_cached_image_path(cache_key)
            
            # Save sebagai PNG untuk quality
            image.save(cache_path, 'PNG')
            logger.debug(f"Image saved to cache: {cache_key}")
        except Exception as e:
            logger.error(f"Error saving image to cache: {e}")
    
    def _download_with_retry(self, url, max_retries=None):
        """Download image dengan retry logic"""
        if max_retries is None:
            max_retries = self.max_retries
        
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                logger.debug(f"Download attempt {attempt + 1}/{max_retries + 1}: {url}")
                
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                
                image = Image.open(BytesIO(response.content)).convert("RGBA")
                logger.debug(f"Successfully downloaded image on attempt {attempt + 1}")
                return image
                
            except Exception as e:
                last_error = e
                logger.warning(f"Download attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries:
                    time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                    
        logger.error(f"All download attempts failed for {url}: {last_error}")
        return None
    
    def _get_random_rarity(self):
        """Generate random rarity berdasarkan probabilitas"""
        rand = random.randint(1, 100)
        cumulative = 0
        
        for rarity, rate in self.RARITY_RATES.items():
            cumulative += rate
            if rand <= cumulative:
                return rarity
        return "Common"  # fallback
    
    def _get_member_photo_url(self, member_key, photo_index=None):
        """
        Get URL foto member dari JSON data
        
        Args:
            member_key: Key member dalam JSON (format: name_group)
            photo_index: Index foto (jika None akan random)
            
        Returns:
            tuple: (photo_url, photo_filename)
        """
        if member_key not in self.members_data:
            return None, None
        
        member_info = self.members_data[member_key]
        photos = member_info.get('photos', [])
        
        if not photos:
            return None, None
        
        # Pilih foto
        if photo_index is None:
            photo_filename = random.choice(photos)
        else:
            photo_index = min(photo_index, len(photos) - 1)
            photo_filename = photos[photo_index]
        
        # Construct full URL
        if self.base_url and 'drive.google.com' in self.base_url:
            # Extract file ID from filename for Google Drive
            # Assuming filename format: GROUP_MEMBER_NUM.jpg
            photo_url = f"{self.base_url}{photo_filename}"
            print(f"📸 PHOTO SOURCE: NEW GDrive folder - {photo_url[:80]}...")
            print(f"📁 NEW FOLDER ID: {self.new_photo_folder_id}")
            logger.info(f"📸 RAILWAY LOG: Photo URL from NEW GDrive folder: {photo_url[:80]}...")
            logger.info(f"📁 RAILWAY LOG: Using NEW photo folder ID: {self.new_photo_folder_id}")
        else:
            photo_url = photo_filename
            print(f"📸 PHOTO SOURCE: Local/fallback path - {photo_url}")
            logger.info(f"📸 RAILWAY LOG: Photo from local/fallback path: {photo_url}")
        
        return photo_url, photo_filename
    
    def _download_image_from_url(self, url):
        """Download image dari Google Drive URL dengan caching dan retry"""
        try:
            # NEW: Check cache first
            if self._is_image_cached(url):
                cached_image = self._load_cached_image(url)
                if cached_image:
                    return cached_image
            
            # NEW: Download dengan retry logic
            image = self._download_with_retry(url)
            
            if image:
                # NEW: Save to cache
                self._save_image_to_cache(url, image)
                return image
            
            return None
            
        except Exception as e:
            logger.error(f"Error in enhanced image download from {url}: {e}")
            return None
    
    def _find_group_members(self, group_name):
        """Find all member keys untuk group tertentu dengan case insensitive"""
        group_lower = group_name.lower()
        matching_keys = []
        
        for member_key, member_info in self.members_data.items():
            if isinstance(member_info, dict) and 'group' in member_info:
                member_group = member_info.get('group', '')
                # Safe string conversion untuk handle NaN/None values
                if member_group and str(member_group).lower() == group_lower:
                    matching_keys.append(member_key)
        
        return matching_keys
    
    def _find_member_key(self, member_name):
        """Find member key berdasarkan nama dengan NEW JSON format"""
        member_lower = member_name.lower()
        matching_keys = []
        
        # NEW JSON Format: Direct key-value pairs (no "members" wrapper)
        # Structure: {"karina_aespa": {"name": "Karina", "group": "aespa"}}
        
        # Strategy 1: Exact name match
        for member_key, member_info in self.members_data.items():
            if isinstance(member_info, dict) and 'name' in member_info:
                member_name_val = member_info.get('name', '')
                # Safe string conversion untuk handle NaN/None values
                if member_name_val and str(member_name_val).lower() == member_lower:
                    matching_keys.append(member_key)
        
        # Strategy 2: Key-based search jika exact match tidak ditemukan
        if not matching_keys:
            for member_key, member_info in self.members_data.items():
                if isinstance(member_info, dict) and 'name' in member_info:
                    key_lower = member_key.lower()
                    if member_lower in key_lower or key_lower.startswith(member_lower):
                        matching_keys.append(member_key)
        
        return matching_keys
    
    def _find_member_key_old_format(self, member_name, old_data):
        """Find member key berdasarkan nama dengan OLD JSON format"""
        member_lower = member_name.lower()
        found_member = None
        
        # OLD JSON Format: Has "members" wrapper or direct structure
        # Structure: {"members": {"karina_aespa": {"name": "Karina", "group": "AESPA"}}}
        members_data = old_data.get('members', old_data)
        
        # Strategy 1: Exact name match
        logger.info(f"🔍 OLD FORMAT STRATEGY 1: Searching for exact name '{member_lower}'")
        for key, member_info in members_data.items():
            if isinstance(member_info, dict) and 'name' in member_info:
                name_in_db = member_info.get('name', '').lower()
                if name_in_db == member_lower:
                    logger.info(f"✅ OLD FORMAT EXACT MATCH: {key} -> {member_info.get('name')}")
                    found_member = (key, member_info)
                    break
        
        # Strategy 2: Partial name match (if exact match fails)
        if not found_member:
            logger.info(f"🔍 OLD FORMAT STRATEGY 2: Searching for partial name match")
            for key, member_info in members_data.items():
                if isinstance(member_info, dict) and 'name' in member_info:
                    name_in_db = member_info.get('name', '').lower()
                    if member_lower in name_in_db or name_in_db in member_lower:
                        logger.info(f"✅ OLD FORMAT PARTIAL MATCH: {key} -> {member_info.get('name')}")
                        found_member = (key, member_info)
                        break
        
        # Strategy 3: Key-based search (for cases like soodam -> soodam_secret_number)
        if not found_member:
            logger.info(f"🔍 OLD FORMAT STRATEGY 3: Searching in member keys")
            for key, member_info in members_data.items():
                if isinstance(member_info, dict) and 'name' in member_info:
                    key_lower = key.lower()
                    if member_lower in key_lower or key_lower.startswith(member_lower):
                        logger.info(f"✅ OLD FORMAT KEY MATCH: {key} -> {member_info.get('name')}")
                        found_member = (key, member_info)
                        break
        
        return found_member
    
    def _get_all_member_keys(self):
        """Get all available member keys from JSON data"""
        if not self.members_data:
            return []
        return list(self.members_data.keys())
    
    def generate_card(self, member_name, group_name, rarity=None, photo_num=None):
        """
        Generate kartu trading untuk member dengan flow yang jelas:
        1. Cek New JSON Update -> GDrive photos -> design -> return
        2. Fallback: Old JSON -> old database folder -> design -> return
        
        Args:
            member_name: Nama member
            group_name: Nama grup
            rarity: Rarity kartu (jika None akan random)
            photo_num: Nomor foto (1-5, jika None akan random)
            
        Returns:
            PIL Image object kartu yang sudah di-generate
        """
        try:
            # Tentukan rarity
            if rarity is None:
                rarity = self._get_random_rarity()
            
            # Step 1: Flow berdasarkan database yang digunakan
            if self.using_new_database:
                # FLOW 1: New JSON Update -> GDrive photos -> design -> return
                logger.info(f"🎯 Using NEW database flow for card generation: {member_name}")
                
                # Cari member key dari new database
                member_key = f"{member_name.lower().replace(' ', '_')}_{group_name.lower().replace(' ', '_')}"
                
                # Load foto member dari NEW database
                photo_url, photo_filename = self._get_member_photo_url(member_key, photo_num)
                
                if not photo_url:
                    logger.warning(f"⚠️ Photo not found in NEW database for {member_name}, trying fallback")
                    return self._generate_card_fallback_flow(member_name, group_name, rarity, photo_num)
                
                # Download foto dari NEW database (GDrive)
                if 'drive.google.com' in photo_url:
                    print(f"📸 DOWNLOADING: NEW GDrive folder - {photo_url[:80]}...")
                    print(f"📁 NEW FOLDER ID: {self.new_photo_folder_id}")
                    logger.info(f"📸 RAILWAY LOG: Downloading from NEW GDrive folder: {photo_url[:80]}...")
                    logger.info(f"📁 RAILWAY LOG: NEW photo folder ID: {self.new_photo_folder_id}")
                    idol_photo_original = self._download_image_from_url(photo_url)
                else:
                    # Local file fallback
                    print(f"📸 LOADING: NEW local path - {photo_url}")
                    logger.info(f"📸 RAILWAY LOG: Loading from NEW local path: {photo_url}")
                    if os.path.exists(photo_url):
                        idol_photo_original = Image.open(photo_url).convert("RGBA")
                    else:
                        idol_photo_original = None
                
                if idol_photo_original is None:
                    logger.warning(f"⚠️ Failed to load photo from NEW database for {member_name}, trying fallback")
                    return self._generate_card_fallback_flow(member_name, group_name, rarity, photo_num)
                
                # Generate card using NEW database
                template = self._generate_card_template(idol_photo_original, rarity, member_name, group_name)
                logger.info(f"✅ Card generated successfully using NEW database for {member_name}")
                return template
            
            else:
                # FLOW 2: Old JSON -> old database folder -> design -> return
                logger.info(f"📁 Using OLD database flow for card generation: {member_name}")
                return self._generate_card_fallback_flow(member_name, group_name, rarity, photo_num)
            
        except Exception as e:
            logger.error(f"Error generating card: {e}")
            return None
    
    def _generate_card_fallback_flow(self, member_name, group_name, rarity, photo_num=None):
        """Fallback flow untuk card generation: Old JSON -> old database folder -> design -> return"""
        try:
            logger.info(f"📂 Fallback card generation flow for {member_name}")
            
            # Try old database structure
            member_key = f"{member_name.lower().replace(' ', '_')}_{group_name.lower().replace(' ', '_')}"
            
            # Get photo from old database/fallback method
            photo_url, _ = self._get_member_photo_url_fallback(member_name, group_name)
            
            if not photo_url:
                logger.error(f"❌ Photo not found in any database for {member_name}")
                return None
            
            # Download foto dari old database
            if 'drive.google.com' in photo_url:
                print(f"📸 DOWNLOADING: OLD GDrive folder - {photo_url[:80]}...")
                print(f"📁 OLD FOLDER ID: {self.kpop_photo_folder_id}")
                logger.info(f"📸 RAILWAY LOG: Photo URL from OLD GDrive folder: {photo_url[:80]}...")
                logger.info(f"📁 RAILWAY LOG: Using OLD photo folder ID: {self.kpop_photo_folder_id}")
                idol_photo_original = self._download_image_from_url(photo_url)
            else:
                # Local file fallback
                print(f"📸 LOADING: OLD local database - {photo_url}")
                logger.info(f"📸 RAILWAY LOG: Photo from OLD local database: {photo_url}")
                if os.path.exists(photo_url):
                    idol_photo_original = Image.open(photo_url).convert("RGBA")
                else:
                    idol_photo_original = None
            
            if idol_photo_original is None:
                logger.error(f"❌ Failed to load photo from fallback for {member_name}")
                return None
            
            # Generate card using old database
            template = self._generate_card_template(idol_photo_original, rarity, member_name, group_name)
            logger.info(f"✅ Card generated successfully using fallback for {member_name}")
            return template
            
        except Exception as e:
            logger.error(f"Error in fallback card generation: {e}")
            return None
    
    def _generate_card_template(self, idol_photo_original, rarity, member_name, group_name):
        """Generate card template using design_kartu module"""
        try:
            # Import design functions at method level to avoid circular imports
            from features.gacha_system.design_kartu import generate_card_template, map_old_rarity
            
            # Map old rarity to new system if needed
            mapped_rarity = map_old_rarity(rarity)
            
            # Generate template kartu menggunakan fungsi dari design_kartu dengan info member
            template = generate_card_template(idol_photo_original, mapped_rarity, member_name, group_name)
            
            return template
            
        except Exception as e:
            logger.error(f"Error generating card template: {e}")
            return None
    
    def gacha_random(self):
        """
        Gacha random member dengan flow yang jelas:
        1. Cek New JSON Update -> GDrive photos -> design -> return
        2. Fallback: Old JSON -> old database folder -> design -> return
        """
        if not self.members_data:
            return None, "❌ Data member tidak tersedia"
        
        try:
            # Step 1: Pilih member random dari database yang tersedia
            member_key = random.choice(self._get_all_member_keys())
            member_info = self.members_data[member_key]
            
            member_name = member_info.get('name', 'Unknown')
            group_name = member_info.get('group', 'Unknown')
            
            # Step 2: Flow berdasarkan database yang digunakan
            if self.using_new_database:
                # FLOW 1: New JSON Update -> GDrive photos -> design -> Discord
                logger.info(f"🎯 Using NEW database flow for {member_name}")
                photo_url, _ = self._get_member_photo_url(member_key)
                
                if not photo_url:
                    logger.warning(f"⚠️ Photo not found in NEW database for {member_name}, trying fallback")
                    return self._gacha_fallback_flow(member_name, group_name)
                
                # Generate card using NEW database photos
                rarity = self._get_random_rarity()
                card_image = self.generate_card(member_name, group_name, rarity)
                
                if card_image:
                    success_msg = f"🎴 **{member_name}** dari **{group_name}**\n"
                    success_msg += f"✨ **Rarity:** {rarity}\n"
                    success_msg += f"📸 **Photo:** New GDrive Database\n"
                    success_msg += f"🎯 **Random Gacha**"
                    return card_image, success_msg
                else:
                    logger.warning(f"⚠️ Card generation failed in NEW flow for {member_name}, trying fallback")
                    return self._gacha_fallback_flow(member_name, group_name)
            
            else:
                # FLOW 2: Old JSON -> old database folder -> design -> Discord
                logger.info(f"📁 Using OLD database flow for {member_name}")
                return self._gacha_fallback_flow(member_name, group_name)
                
        except Exception as e:
            logger.error(f"Error in gacha_random: {e}")
            return None, f"❌ Error saat random gacha: {str(e)}"
    
    def _gacha_fallback_flow(self, member_name, group_name):
        """Fallback flow: Old JSON -> old database folder -> design -> Discord"""
        try:
            logger.info(f"📂 Fallback flow for {member_name} from {group_name}")
            
            # Get photo from old database
            photo_url, _ = self._get_member_photo_url_fallback(member_name, group_name)
            
            if not photo_url:
                return None, f"❌ Foto untuk {member_name} tidak dapat diakses di database manapun!"
            
            # Generate card using old database
            rarity = self._get_random_rarity()
            card_image = self.generate_card(member_name, group_name, rarity)
            
            if card_image:
                success_msg = f"🎴 **{member_name}** dari **{group_name}**\n"
                success_msg += f"✨ **Rarity:** {rarity}\n"
                success_msg += f"📸 **Photo:** Old Database (Fallback)\n"
                success_msg += f"🎯 **Random Gacha**"
                return card_image, success_msg
            else:
                return None, f"❌ Gagal generate kartu {member_name} dari {group_name}"
                
        except Exception as e:
            logger.error(f"Error in fallback flow: {e}")
            return None, f"❌ Error saat fallback gacha: {str(e)}"
    
    def _get_member_photo_url_fallback(self, member_name, group_name):
        """Get photo URL from OLD JSON database (GitHub source)"""
        try:
            logger.info(f"🔍 Getting photo from OLD database for {member_name} from {group_name}")
            
            # Search in OLD JSON for photos
            old_result = self._search_in_old_json(member_name.lower())
            if old_result and 'photos' in old_result:
                photos = old_result['photos']
                if photos and len(photos) > 0:
                    # Get random photo from available photos
                    import random
                    photo_id = random.choice(photos)
                    
                    # Construct Google Drive URL
                    photo_url = f"https://drive.google.com/uc?id={photo_id}"
                    logger.info(f"✅ OLD database photo found: {photo_url}")
                    return photo_url, f"{member_name}_{photo_id}.jpg"
                else:
                    logger.warning(f"⚠️ OLD database entry found but no photos for {member_name}")
            else:
                logger.warning(f"⚠️ No OLD database entry found for {member_name}")
            
            return None, None
            
        except Exception as e:
            logger.error(f"❌ Error getting OLD database photo URL: {e}")
            return None, None
    
    def gacha_pack_5(self):
        """
        Gacha pack 5 kartu dengan guaranteed rarity:
        - 2 Common
        - 2 Rare/Epic  
        - 1 Legendary/FullArt
        """
        if not self.members_data:
            return [], "❌ Data member tidak tersedia"
        
        try:
            cards = []
            all_member_keys = self._get_all_member_keys()
            
            if len(all_member_keys) < 5:
                return [], "❌ Tidak cukup member untuk pack 5 kartu"
            
            # Guaranteed rarity distribution (NEW SYSTEM)
            guaranteed_rarities = [
                "Common", "Common",           # 2 Common
                "Rare", "DR",                # 2 Rare/DR
                "SR"                         # 1 SR/SAR
            ]
            
            # Shuffle untuk random order
            random.shuffle(guaranteed_rarities)
            
            # Generate 5 unique members
            selected_members = random.sample(all_member_keys, 5)
            
            for i, member_key in enumerate(selected_members):
                member_info = self.members_data[member_key]
                member_name = member_info.get('name', 'Unknown')
                group_name = member_info.get('group', 'Unknown')
                rarity = guaranteed_rarities[i]
                
                # Get photo URL
                photo_url, _ = self._get_member_photo_url(member_key)
                
                if photo_url:
                    # Generate card
                    card_image = self.generate_card(member_name, group_name, rarity)
                    
                    if card_image:
                        card_data = {
                            'image': card_image,
                            'member_name': member_name,
                            'group_name': group_name,
                            'rarity': rarity,
                            'member_key': member_key
                        }
                        cards.append(card_data)
            
            if len(cards) == 5:
                # Create pack summary message
                rarity_counts = {}
                for card in cards:
                    rarity = card['rarity']
                    rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1
                
                summary = "🎴 **5-Card Gacha Pack Results:**\n"
                for rarity, count in rarity_counts.items():
                    summary += f"✨ **{rarity}:** {count}x\n"
                
                summary += f"\n📦 **Pack Contents:**\n"
                for i, card in enumerate(cards, 1):
                    summary += f"{i}. **{card['member_name']}** ({card['group_name']}) - {card['rarity']}\n"
                
                return cards, summary
            else:
                return [], f"❌ Gagal generate pack lengkap (hanya {len(cards)}/5 kartu)"
                
        except Exception as e:
            logger.error(f"Error in gacha_pack_5: {e}")
            return [], f"❌ Error saat generate pack: {str(e)}"
    
    def gacha_by_member(self, member_name):
        """
        DIRECT FLOW: Efficient member gacha with proper source handling
        1. Search NEW JSON -> Generate with NEW GDrive IDs
        2. Search OLD JSON -> Generate with OLD GDrive IDs
        """
        try:
            logger.info(f"🚀 DIRECT FLOW: Member gacha for '{member_name}'")
            
            # Direct search using new efficient method
            search_results = self.search_member(member_name)
            
            if not search_results:
                return None, f"❌ Member **{member_name}** tidak ditemukan di database manapun!"
            
            # Get first result
            member_result = search_results[0]
            member_key = member_result['member_key']
            actual_name = member_result['name']
            group_name = member_result['group']
            source = member_result['source']
            
            logger.info(f"✅ Found member: {actual_name} ({group_name}) from {source} database")
            
            # Generate card based on source
            rarity = self._get_random_rarity()
            
            if source == 'NEW':
                # Use NEW database photos (already loaded)
                photo_url, photo_filename = self._get_member_photo_url(member_key)
                
                if photo_url:
                    card_image = self.generate_card(actual_name, group_name, rarity)
                    
                    if card_image:
                        success_msg = f"🎴 **{actual_name}** dari **{group_name}**\n"
                        success_msg += f"✨ **Rarity:** {rarity}\n"
                        success_msg += f"📸 **Photo:** New Database (GDrive)\n"
                        success_msg += f"🎯 **Member Gacha**"
                        if actual_name.lower() != member_name.lower():
                            success_msg += f"\n🔍 **Searched for:** {member_name}"
                        return card_image, success_msg
                else:
                    # NEW database photo gagal, coba OLD database sebagai fallback
                    logger.warning(f"⚠️ NEW database photo failed for {actual_name}, trying OLD database fallback")
                    old_result = self._search_in_old_json(member_name.lower())
                    if old_result:
                        # Update ke OLD source dan coba lagi
                        source = 'OLD'
                        actual_name = old_result['name']
                        group_name = old_result['group']
                        logger.info(f"✅ Fallback successful: Using OLD database for {actual_name}")
                    else:
                        return None, f"❌ Gagal memuat foto untuk **{actual_name}** dari NEW dan OLD database"
            
            if source == 'OLD':
                # Use OLD database photos
                photo_url, _ = self._get_member_photo_url_fallback(actual_name, group_name)
                
                if photo_url:
                    card_image = self.generate_card(actual_name, group_name, rarity)
                    
                    if card_image:
                        success_msg = f"🎴 **{actual_name}** dari **{group_name}**\n"
                        success_msg += f"✨ **Rarity:** {rarity}\n"
                        success_msg += f"📸 **Photo:** Old Database (Fallback)\n"
                        success_msg += f"🎯 **Member Gacha**"
                        if actual_name.lower() != member_name.lower():
                            success_msg += f"\n🔍 **Searched for:** {member_name}"
                        return card_image, success_msg
            
            # If photo loading failed
            return None, f"❌ Gagal memuat foto untuk **{actual_name}**"
                    
        except Exception as e:
            logger.error(f"Error in gacha_by_member: {e}")
            return None, f"❌ Error saat member gacha: {str(e)}"
    
    def gacha_by_group(self, group_name):
        """
        DIRECT FLOW: Efficient group gacha with proper source handling
        1. Search group members in NEW JSON -> Generate with NEW GDrive IDs
        2. Search group members in OLD JSON -> Generate with OLD GDrive IDs
        """
        try:
            logger.info(f"🚀 DIRECT FLOW: Group gacha for '{group_name}'")
            
            # Step 1: Try to find group members in NEW JSON (currently loaded)
            group_members_new = self._find_group_members_in_new_json(group_name)
            
            if group_members_new:
                # Found members in NEW JSON, pick random member
                member_key = random.choice(group_members_new)
                member_info = self.members_data[member_key]
                actual_name = member_info.get('name', 'Unknown')
                
                logger.info(f"✅ Found group '{group_name}' in NEW JSON: {actual_name}")
                
                # Generate card using NEW database
                rarity = self._get_random_rarity()
                photo_url, _ = self._get_member_photo_url(member_key)
                
                if photo_url:
                    card_image = self.generate_card(actual_name, group_name, rarity)
                    
                    if card_image:
                        success_msg = f"🎴 **{actual_name}** dari **{group_name}**\n"
                        success_msg += f"✨ **Rarity:** {rarity}\n"
                        success_msg += f"📸 **Photo:** New Database (GDrive)\n"
                        success_msg += f"🎯 **Group Gacha**"
                        return card_image, success_msg
            
            # Step 2: Try to find group members in OLD JSON
            group_members_old = self._find_group_members_in_old_json(group_name)
            
            if group_members_old:
                # Found members in OLD JSON, pick random member
                member_info = random.choice(group_members_old)
                actual_name = member_info['name']
                
                logger.info(f"✅ Found group '{group_name}' in OLD JSON: {actual_name}")
                
                # Generate card using OLD database
                rarity = self._get_random_rarity()
                photo_url, _ = self._get_member_photo_url_fallback(actual_name, group_name)
                
                if photo_url:
                    card_image = self.generate_card(actual_name, group_name, rarity)
                    
                    if card_image:
                        success_msg = f"🎴 **{actual_name}** dari **{group_name}**\n"
                        success_msg += f"✨ **Rarity:** {rarity}\n"
                        success_msg += f"📸 **Photo:** Old Database (Fallback)\n"
                        success_msg += f"🎯 **Group Gacha**"
                        return card_image, success_msg
            
            # Group not found in either database
            return None, f"❌ Grup **{group_name}** tidak ditemukan di database manapun!"
                    
        except Exception as e:
            logger.error(f"Error in gacha_by_group: {e}")
            return None, f"❌ Error saat group gacha: {str(e)}"
    
    def _find_group_members_in_new_json(self, group_name):
        """Find group members in NEW JSON (currently loaded)"""
        group_lower = group_name.lower()
        matching_keys = []
        
        for member_key, member_info in self.members_data.items():
            if isinstance(member_info, dict) and 'group' in member_info:
                member_group = member_info.get('group', '')
                if member_group and str(member_group).lower() == group_lower:
                    matching_keys.append(member_key)
        
        logger.info(f"🔍 NEW JSON group search for '{group_name}': {len(matching_keys)} members found")
        return matching_keys
    
    def _find_group_members_in_old_json(self, group_name):
        """Find group members in OLD JSON (GitHub source)"""
        logger.info(f"🔍 Searching group '{group_name}' in OLD JSON from GitHub...")
        
        try:
            # Load OLD JSON from GitHub
            import requests
            old_json_url = "https://raw.githubusercontent.com/coffin48/SN-Fun-Bot/main/data/member_data/Path_Foto_DriveIDs_Real.json"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(old_json_url, headers=headers)
            response.raise_for_status()
            old_data = response.json()
            
            # Handle OLD JSON structure (with or without 'members' wrapper)
            if 'members' in old_data:
                members_data = old_data['members']
            else:
                members_data = old_data
            
            group_lower = group_name.lower()
            matching_members = []
            
            # Debug: Log beberapa sample untuk group search
            sample_count = 0
            for key, info in members_data.items():
                if sample_count < 3 and isinstance(info, dict):
                    logger.info(f"🔍 OLD JSON group sample {sample_count + 1}: {key} -> group: {info.get('group', 'NO_GROUP')}")
                    sample_count += 1
            
            # Search for group members in OLD JSON
            for member_key, member_info in members_data.items():
                if isinstance(member_info, dict):
                    member_group = member_info.get('group', '').lower()
                    if member_group == group_lower:
                        matching_members.append({
                            'member_key': member_key,
                            'name': member_info.get('name', 'Unknown'),
                            'group': member_info.get('group', group_name),
                            'photos': member_info.get('photos', [])
                        })
            
            logger.info(f"🔍 OLD JSON group search for '{group_name}': {len(matching_members)} members found")
            return matching_members
            
        except Exception as e:
            logger.error(f"❌ Error loading OLD JSON for group search: {e}")
            return []
    
    def _gacha_member_fallback_flow(self, member_name):
        """Universal fallback flow untuk ALL members: CSV -> NEW JSON -> OLD JSON -> design -> Discord"""
        logger.info(f"🔥🔥🔥 FALLBACK FLOW CALLED with: '{member_name}' 🔥🔥🔥")
        
        # STEP 1: Try optimized search first
        try:
            logger.info(f"🚀 STEP 1: Trying optimized CSV search for '{member_name}'")
            optimized_result = self.search_member_optimized(member_name)
            if optimized_result:
                logger.info(f"✅ Found in optimized search: {len(optimized_result)} results")
                return optimized_result[0]  # Return first result for fallback compatibility
        except Exception as e:
            logger.error(f"❌ Optimized search failed: {e}")
        
        # STEP 2: Original fallback flow
        try:
            logger.info(f"📂 STEP 2: Original fallback flow for {member_name}")
            
            # Load old JSON database dari GitHub untuk fallback search
            old_json_url = "https://raw.githubusercontent.com/coffin48/SN-Fun-Bot/main/data/member_data/Path_Foto_DriveIDs_Real.json"
            
            try:
                logger.info(f"📂 LOADING OLD DATABASE FROM GITHUB: {old_json_url}")
                import requests
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(old_json_url, headers=headers, timeout=30)
                response.raise_for_status()
                old_data = response.json()
                logger.info(f"📊 OLD DATABASE LOADED: {len(old_data.get('members', old_data))} members")
            except Exception as github_error:
                logger.warning(f"❌ GAGAL LOAD DARI GITHUB: {github_error}")
                # Fallback ke file lokal jika GitHub gagal
                old_json_path = "SN-Fun-Bot-main/data/member_data/Path_Foto_DriveIDs_Real.json"
                
                if os.path.exists(old_json_path):
                    logger.info(f"📂 LOADING OLD DATABASE LOCAL: {old_json_path}")
                    with open(old_json_path, 'r', encoding='utf-8') as f:
                        old_data = json.load(f)
                    logger.info(f"📊 OLD DATABASE LOADED: {len(old_data.get('members', old_data))} members")
                else:
                    logger.error("❌ TIDAK ADA DATABASE FALLBACK YANG TERSEDIA")
                    return None, f"❌ Member **{member_name}** tidak ditemukan - database fallback tidak tersedia"
            
            # Use OLD JSON format-specific search
            found_member = self._find_member_key_old_format(member_name, old_data)
            
            # Debug: Show some sample entries if no match found
            if not found_member:
                logger.warning(f"❌ NO MATCH FOUND for '{member_name}' in OLD JSON")
                logger.info("📋 Sample OLD JSON entries:")
                count = 0
                members_data = old_data.get('members', old_data)
                for key, member_info in members_data.items():
                    if isinstance(member_info, dict) and 'name' in member_info:
                        logger.info(f"  {key}: {member_info.get('name', 'Unknown')}")
                        count += 1
                        if count >= 5:
                            break
                
            if found_member:
                member_key, member_info = found_member
                group_name = member_info.get('group', 'Unknown')
                actual_name = member_info.get('name', member_name)
                
                logger.info(f"📸 FOUND IN OLD DATABASE: {member_name} -> {member_key}")
                logger.info(f"👤 ACTUAL NAME: {actual_name}")
                logger.info(f"📁 OLD DATABASE GROUP: {group_name}")
                
                # Get photo from old database
                photos = member_info.get('photos', [])
                if photos:
                    photo_id = random.choice(photos)
                    photo_url = f"https://drive.google.com/uc?export=view&id={photo_id}"
                    
                    logger.info(f"📸 OLD DATABASE PHOTO: {photo_url[:80]}...")
                    
                    # Generate card using old database with actual name
                    rarity = self._get_random_rarity()
                    card_image = self.generate_card(actual_name, group_name, rarity)
                    
                    if card_image:
                        success_msg = f"🎴 **{actual_name}** dari **{group_name}**\n"
                        success_msg += f"✨ **Rarity:** {rarity}\n"
                        success_msg += f"📸 **Photo:** Old Database (Fallback)\n"
                        success_msg += f"🎯 **Member Gacha**"
                        if actual_name.lower() != member_name.lower():
                            success_msg += f"\n🔍 **Searched for:** {member_name}"
                        return card_image, success_msg
            
            return None, f"❌ Member **{member_name}** tidak ditemukan di database manapun!"
                
        except Exception as e:
            logger.error(f"Error in universal fallback flow: {e}")
            return None, f"❌ Error saat fallback member gacha: {str(e)}"
    
    def save_card_temp(self, card_image, prefix="gacha_card"):
        """
        Save kartu ke temporary file untuk Discord dengan transparency support
        
        Args:
            card_image: PIL Image object (RGBA with transparency)
            prefix: Prefix untuk filename
            
        Returns:
            str: Path ke temporary file atau None jika gagal
        """
        try:
            import tempfile
            import os
            
            # Create temporary file - PNG untuk preserve transparency
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png', prefix=f"{prefix}_")
            temp_path = temp_file.name
            temp_file.close()
            
            # Save image dengan transparency preserved
            # Keep RGBA mode untuk preserve transparency
            if card_image.mode == 'RGBA':
                # Save langsung dengan transparency
                card_image.save(temp_path, 'PNG', optimize=True)
            else:
                # Convert ke RGBA jika belum
                rgba_image = card_image.convert('RGBA')
                rgba_image.save(temp_path, 'PNG', optimize=True)
            
            # Memory cleanup - close image if it's safe
            try:
                if hasattr(card_image, 'close') and card_image.filename != temp_path:
                    card_image.close()
            except:
                pass  # Safe to ignore cleanup errors
            
            return temp_path
            
        except Exception as e:
            logger.error(f"Error saving card to temp file: {e}")
            return None
    
    def _integrate_csv_data(self):
        """Integrate CSV database with JSON data for better member mapping"""
        try:
            if not hasattr(self, 'database') or self.database is None:
                logger.warning("CSV database not loaded, skipping integration")
                return
            
            # Create stage name to member key mapping
            self.stage_name_mapping = {}
            self.full_name_mapping = {}
            
            for _, row in self.database.iterrows():
                # Safe string conversion untuk handle NaN values
                group = str(row.get('Group', '') if pd.notna(row.get('Group', '')) else '').strip()
                stage_name = str(row.get('Stage Name', '') if pd.notna(row.get('Stage Name', '')) else '').strip()
                full_name = str(row.get('Full Name', '') if pd.notna(row.get('Full Name', '')) else '').strip()
                korean_name = str(row.get('Korean Stage Name', '') if pd.notna(row.get('Korean Stage Name', '')) else '').strip()
                
                if not group or not stage_name or group == 'nan' or stage_name == 'nan':
                    continue
                
                # Generate member key (same format as JSON)
                member_key = f"{stage_name.lower().replace(' ', '_')}_{group.lower().replace(' ', '_')}"
                
                # Store mappings
                self.stage_name_mapping[stage_name.lower()] = {
                    'member_key': member_key,
                    'stage_name': stage_name,
                    'full_name': full_name,
                    'korean_name': korean_name,
                    'group': group
                }
                
                if full_name and full_name != 'nan':
                    self.full_name_mapping[full_name.lower()] = {
                        'member_key': member_key,
                        'stage_name': stage_name,
                        'full_name': full_name,
                        'korean_name': korean_name,
                        'group': group
                    }
                
                # Update JSON member data with CSV info if member exists
                if member_key in self.members_data:
                    self.members_data[member_key].update({
                        'stage_name': stage_name,
                        'full_name': full_name,
                        'korean_name': korean_name,
                        'birth_date': str(row.get('Date of Birth', '')).strip(),
                        'instagram': str(row.get('Instagram', '')).strip()
                    })
            
            logger.info(f"CSV integration completed: {len(self.stage_name_mapping)} stage names mapped")
            
        except Exception as e:
            logger.error(f"Error integrating CSV data: {e}")
            self.stage_name_mapping = {}
            self.full_name_mapping = {}
    
    # OPTIMIZED FLOW: CSV Mapping -> NEW JSON -> OLD JSON search
    def search_member_optimized(self, member_name):
        """Optimized search: Use pre-loaded CSV mapping -> NEW JSON -> OLD JSON with proper source tracking"""
        logger.info(f"🚀🚀🚀 OPTIMIZED FLOW METHOD CALLED with: '{member_name}' 🚀🚀🚀")
        
        try:
            search_name = member_name.lower().strip()
            logger.info(f"🚀 OPTIMIZED FLOW: Searching for '{member_name}' (normalized: '{search_name}')")
            
            # Debug: Check if mappings exist
            has_stage_mapping = hasattr(self, 'stage_name_mapping') and self.stage_name_mapping
            has_full_mapping = hasattr(self, 'full_name_mapping') and self.full_name_mapping
            logger.info(f"🔍 CSV Mappings available - Stage: {has_stage_mapping}, Full: {has_full_mapping}")
            if has_stage_mapping:
                logger.info(f"🔍 Stage mapping size: {len(self.stage_name_mapping)}")
            if has_full_mapping:
                logger.info(f"🔍 Full mapping size: {len(self.full_name_mapping)}")
        except Exception as e:
            logger.error(f"❌ Error in search_member initialization: {e}")
            logger.error(f"❌ Exception type: {type(e)}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return []
        
        # Step 1: Check pre-loaded CSV mapping (most accurate)
        logger.info(f"🔍 STEP 1: Checking pre-loaded CSV mapping for '{search_name}'")
        
        # Try stage name mapping first
        if hasattr(self, 'stage_name_mapping') and search_name in self.stage_name_mapping:
            csv_info = self.stage_name_mapping[search_name]
            logger.info(f"✅ Found '{search_name}' in stage_name_mapping: {csv_info['group']}")
            logger.info(f"🔍 CSV Info: {csv_info}")
            
            # Check if member has photos in NEW or OLD JSON
            logger.info(f"🔍 Starting photo search for CSV member: {search_name}")
            member_with_photos = self._find_photos_for_csv_member(csv_info)
            if member_with_photos:
                logger.info(f"✅ CSV member with photos found, returning result")
                return [member_with_photos]
            else:
                logger.warning(f"⚠️ Member '{search_name}' found in CSV but no photos available - continuing to fallback")
        
        # Try full name mapping
        elif hasattr(self, 'full_name_mapping') and search_name in self.full_name_mapping:
            csv_info = self.full_name_mapping[search_name]
            logger.info(f"✅ Found '{search_name}' in full_name_mapping: {csv_info['group']}")
            
            # Check if member has photos in NEW or OLD JSON
            member_with_photos = self._find_photos_for_csv_member(csv_info)
            if member_with_photos:
                return [member_with_photos]
            else:
                logger.warning(f"⚠️ Member '{search_name}' found in CSV but no photos available")
        
        else:
            logger.info(f"❌ '{search_name}' not found in CSV mappings")
        
        # Step 2: Fallback to NEW JSON (current loaded data)
        logger.info(f"🔍 STEP 2: CSV failed, searching in NEW JSON for '{search_name}'")
        new_result = self._search_in_new_json(search_name)
        if new_result:
            logger.info(f"✅ Found '{search_name}' in NEW JSON database")
            return [new_result]
        
        # Step 3: Fallback to OLD JSON (GitHub source)
        logger.info(f"🔍 STEP 3: NEW JSON failed, searching in OLD JSON for '{search_name}'")
        old_result = self._search_in_old_json(search_name)
        if old_result:
            logger.info(f"✅ Found '{search_name}' in OLD JSON database")
            return [old_result]
        
        logger.info(f"❌ '{search_name}' not found in any database")
        return []
    
    def search_member(self, member_name):
        """FINAL SEARCH METHOD - DIRECT INTEGRATION"""
        logger.info(f"🌟🌟🌟 FINAL SEARCH METHOD CALLED with: '{member_name}' 🌟🌟🌟")
        
        # DIRECT INTEGRATION - No delegation, direct optimized flow
        search_name = member_name.lower().strip()
        logger.info(f"🚀 DIRECT OPTIMIZED FLOW: Searching for '{member_name}' (normalized: '{search_name}')")
        
        # Step 1: Check pre-loaded CSV mapping (most accurate)
        logger.info(f"🔍 STEP 1: Checking pre-loaded CSV mapping for '{search_name}'")
        
        # Try stage name mapping first
        if hasattr(self, 'stage_name_mapping') and search_name in self.stage_name_mapping:
            csv_info = self.stage_name_mapping[search_name]
            logger.info(f"✅ Found '{search_name}' in stage_name_mapping: {csv_info['group']}")
            
            # Check if member has photos in NEW or OLD JSON
            member_with_photos = self._find_photos_for_csv_member(csv_info)
            if member_with_photos:
                logger.info(f"✅ CSV member with photos found, returning result")
                return [member_with_photos]
        
        # Try full name mapping
        elif hasattr(self, 'full_name_mapping') and search_name in self.full_name_mapping:
            csv_info = self.full_name_mapping[search_name]
            logger.info(f"✅ Found '{search_name}' in full_name_mapping: {csv_info['group']}")
            
            # Check if member has photos in NEW or OLD JSON
            member_with_photos = self._find_photos_for_csv_member(csv_info)
            if member_with_photos:
                return [member_with_photos]
        
        # Step 2: Fallback to NEW JSON
        logger.info(f"🔍 STEP 2: CSV failed, searching in NEW JSON for '{search_name}'")
        new_result = self._search_in_new_json(search_name)
        if new_result:
            logger.info(f"✅ Found '{search_name}' in NEW JSON database")
            return [new_result]
        
        # Step 3: Fallback to OLD JSON
        logger.info(f"🔍 STEP 3: NEW JSON failed, searching in OLD JSON for '{search_name}'")
        old_result = self._search_in_old_json(search_name)
        if old_result:
            logger.info(f"✅ Found '{search_name}' in OLD JSON database")
            return [old_result]
        
        logger.info(f"❌ '{search_name}' not found in any database")
        return []
    
    def _find_photos_for_csv_member(self, csv_info):
        """Find photos for CSV member in NEW or OLD JSON"""
        member_key = csv_info['member_key']
        stage_name = csv_info['stage_name'].lower()
        
        logger.info(f"🔍 Looking for photos for CSV member: {stage_name} (key: {member_key})")
        logger.info(f"🔍 Available NEW JSON keys: {len(self.members_data)} total")
        
        # Try to find in NEW JSON first by key
        logger.info(f"🔍 Checking NEW JSON by key: {member_key}")
        if member_key in self.members_data:
            member_info = self.members_data[member_key]
            photos = member_info.get('photos', [])
            logger.info(f"🔍 Found key match in NEW JSON: {len(photos)} photos")
            if photos and len(photos) > 0:
                logger.info(f"✅ Found {len(photos)} photos in NEW JSON for {stage_name}")
                return {
                    'member_key': member_key,
                    'name': csv_info['stage_name'],
                    'group': csv_info['group'],
                    'full_name': csv_info['full_name'],
                    'korean_name': csv_info['korean_name'],
                    'source': 'NEW',
                    'photos': photos
                }
            else:
                logger.warning(f"⚠️ Key found in NEW JSON but no photos: {member_key}")
        else:
            logger.info(f"❌ Key not found in NEW JSON: {member_key}")
        
        # Try to find by name in NEW JSON
        logger.info(f"🔍 Checking NEW JSON by name: {stage_name}")
        for json_key, member_info in self.members_data.items():
            if isinstance(member_info, dict):
                json_name = member_info.get('name', '').lower()
                if json_name == stage_name:
                    photos = member_info.get('photos', [])
                    if photos and len(photos) > 0:
                        logger.info(f"✅ Found {len(photos)} photos in NEW JSON for {stage_name} (name match)")
                        return {
                            'member_key': member_key,
                            'name': csv_info['stage_name'],
                            'group': csv_info['group'],
                            'full_name': csv_info['full_name'],
                            'korean_name': csv_info['korean_name'],
                            'source': 'NEW',
                            'photos': photos
                        }
        
        # Try to find in OLD JSON
        logger.info(f"🔍 Not found in NEW JSON, checking OLD JSON for {stage_name}")
        logger.info(f"🔍 Calling _search_in_old_json for: {stage_name}")
        old_result = self._search_in_old_json(stage_name)
        if old_result:
            logger.info(f"✅ Found in OLD JSON for {stage_name}")
            logger.info(f"🔍 OLD JSON result: {old_result}")
            # Merge CSV info with OLD JSON photos
            result = {
                'member_key': member_key,
                'name': csv_info['stage_name'],
                'group': csv_info['group'],
                'full_name': csv_info['full_name'],
                'korean_name': csv_info['korean_name'],
                'source': 'OLD',
                'photos': old_result.get('photos', [])
            }
            logger.info(f"✅ Returning merged CSV+OLD result: {result}")
            return result
        else:
            logger.warning(f"❌ OLD JSON search also failed for: {stage_name}")
        
        logger.warning(f"❌ No photos found for CSV member: {stage_name}")
        return None
    
    def _search_in_new_json(self, search_name):
        """Search in NEW JSON database (currently loaded)"""
        logger.info(f"🔍 Searching in NEW JSON: {len(self.members_data)} members")
        
        # Direct search in loaded NEW JSON data
        for member_key, member_info in self.members_data.items():
            if isinstance(member_info, dict):
                member_name = member_info.get('name', '').lower()
                logger.debug(f"🔍 Checking NEW JSON: '{member_name}' vs '{search_name}'")
                if member_name == search_name:
                    photos = member_info.get('photos', [])
                    logger.info(f"🔍 FOUND MATCH in NEW JSON: {member_key} -> name: '{member_name}', photos: {len(photos)}")
                    # PENTING: Hanya return jika ada foto yang tersedia
                    if photos and len(photos) > 0:
                        logger.info(f"✅ Found '{search_name}' in NEW JSON with {len(photos)} photos")
                        return {
                            'member_key': member_key,
                            'name': member_info.get('name', 'Unknown'),
                            'group': member_info.get('group', 'Unknown'),
                            'source': 'NEW',
                            'photos': photos
                        }
                    else:
                        logger.warning(f"⚠️ Found '{search_name}' in NEW JSON but NO PHOTOS available - will try OLD JSON")
                        # JANGAN return None di sini, lanjutkan pencarian
        
        # Also try key-based search (EXACT match only)
        for member_key in self.members_data.keys():
            # Extract member name from key (e.g., "lia_itzy" -> "lia")
            key_member_name = member_key.split('_')[0].lower()
            logger.debug(f"🔍 Checking key-based: '{key_member_name}' vs '{search_name}'")
            if key_member_name == search_name:  # EXACT match only
                member_info = self.members_data[member_key]
                photos = member_info.get('photos', [])
                logger.info(f"🔍 FOUND KEY MATCH in NEW JSON: {member_key} -> name: '{key_member_name}', photos: {len(photos)}")
                # PENTING: Hanya return jika ada foto yang tersedia
                if photos and len(photos) > 0:
                    logger.info(f"✅ Found '{search_name}' in NEW JSON (key-based) with {len(photos)} photos")
                    return {
                        'member_key': member_key,
                        'name': member_info.get('name', 'Unknown'),
                        'group': member_info.get('group', 'Unknown'),
                        'source': 'NEW',
                        'photos': photos
                    }
                else:
                    logger.warning(f"⚠️ Found '{search_name}' in NEW JSON (key-based) but NO PHOTOS - will try OLD JSON")
        
        logger.info(f"❌ '{search_name}' not found in NEW JSON OR no photos available")
        return None
    
    def _search_in_old_json(self, search_name):
        """Search in OLD JSON database (GitHub source)"""
        logger.info(f"🔍 Searching in OLD JSON from GitHub...")
        
        try:
            # Load OLD JSON from GitHub
            import requests
            old_json_url = "https://raw.githubusercontent.com/coffin48/SN-Fun-Bot/main/data/member_data/Path_Foto_DriveIDs_Real.json"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(old_json_url, headers=headers)
            response.raise_for_status()
            old_data = response.json()
            
            logger.info(f"✅ OLD JSON loaded: {len(old_data)} entries")
            
            # Debug: Log struktur OLD JSON
            if old_data:
                first_key = list(old_data.keys())[0]
                first_item = old_data[first_key]
                logger.info(f"🔍 OLD JSON struktur sample - Key: {first_key}")
                logger.info(f"🔍 OLD JSON struktur sample - Value: {type(first_item)} - {first_item if isinstance(first_item, dict) else str(first_item)[:100]}")
            
            # Check if OLD JSON has 'members' wrapper
            if 'members' in old_data:
                logger.info("🔍 OLD JSON menggunakan wrapper 'members'")
                members_data = old_data['members']
            else:
                logger.info("🔍 OLD JSON format direct (tanpa wrapper)")
                members_data = old_data
            
            # Search in OLD JSON format
            for member_key, member_info in members_data.items():
                if isinstance(member_info, dict):
                    member_name = member_info.get('name', '').lower()
                    if member_name == search_name:
                        return {
                            'member_key': member_key,
                            'name': member_info.get('name', 'Unknown'),
                            'group': member_info.get('group', 'Unknown'),
                            'source': 'OLD',
                            'photos': member_info.get('photos', [])
                        }
            
            # Also try key-based search in OLD JSON
            for member_key in members_data.keys():
                if search_name in member_key.lower():
                    member_info = members_data[member_key]
                    return {
                        'member_key': member_key,
                        'name': member_info.get('name', 'Unknown'),
                        'group': member_info.get('group', 'Unknown'),
                        'source': 'OLD',
                        'photos': member_info.get('photos', [])
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error loading OLD JSON: {e}")
            return None
    
    def generate_random_card(self):
        """Generate random card (wrapper for gacha_random)"""
        try:
            # Get random member
            if not self.members_data:
                return None
            
            member_key = random.choice(self._get_all_member_keys())
            member_info = self.members_data[member_key]
            
            # Get photo URL
            photo_url, _ = self._get_member_photo_url(member_key)
            
            if not photo_url:
                return None
            
            # Get rarity
            rarity = self._get_random_rarity()
            
            return {
                'member_info': {
                    'name': member_info.get('name', 'Unknown'),
                    'group': member_info.get('group', 'Unknown'),
                    'member_key': member_key
                },
                'photo_url': photo_url,
                'rarity': rarity
            }
        except Exception as e:
            logger.error(f"Error generating random card: {e}")
            return None
    
    def generate_member_card(self, member_name):
        """Generate card for specific member by name"""
        try:
            # Search for member first
            search_results = self.search_member(member_name)
            
            if not search_results:
                return None, f"❌ Member '{member_name}' tidak ditemukan!"
            
            # Use first result
            member_data = search_results[0]
            member_key = member_data['member_key']
            
            if member_key not in self.members_data:
                return None, f"❌ Data foto untuk '{member_name}' tidak tersedia!"
            
            member_info = self.members_data[member_key]
            
            # Get photo URL
            photo_url, _ = self._get_member_photo_url(member_key)
            
            if not photo_url:
                return None, f"❌ Foto untuk '{member_name}' tidak dapat diakses!"
            
            # Get rarity
            rarity = self._get_random_rarity()
            
            # Generate card using design_kartu
            card_image = self.generate_card(
                member_data.get('name', member_info.get('name', 'Unknown')),
                member_data.get('group', member_info.get('group', 'Unknown')),
                rarity
            )
            
            if card_image:
                member_display_name = member_data.get('name', member_info.get('name', 'Unknown'))
                group_display_name = member_data.get('group', member_info.get('group', 'Unknown'))
                
                success_msg = f"🎴 **{member_display_name}** dari **{group_display_name}**\n"
                success_msg += f"✨ **Rarity:** {rarity}\n"
                success_msg += f"📸 **Photo:** Google Drive\n"
                success_msg += f"🎯 **Generated for:** {member_name}"
                
                return card_image, success_msg
            else:
                return None, f"❌ Gagal generate kartu untuk '{member_name}'"
            
        except Exception as e:
            logger.error(f"Error generating member card for '{member_name}': {e}")
            return None, f"❌ Error saat generate kartu: {str(e)}"
    
    def gacha_guaranteed_sar(self):
        """Admin command: Generate guaranteed SAR rarity card"""
        if not self.members_data:
            return None, "❌ Data member tidak tersedia"
        
        try:
            # Pilih member random dari JSON
            member_key = random.choice(self._get_all_member_keys())
            member_info = self.members_data[member_key]
            
            member_name = member_info.get('name', 'Unknown')
            group_name = member_info.get('group', 'Unknown')
            
            # Get photo URL
            photo_url, _ = self._get_member_photo_url(member_key)
            
            if not photo_url:
                return None, f"❌ Foto untuk {member_name} tidak dapat diakses!"
            
            # Force SAR rarity
            rarity = "SAR"
            
            # Generate card using design_kartu
            card_image = self.generate_card(member_name, group_name, rarity)
            
            if card_image:
                success_msg = f"🌟 **ADMIN GUARANTEED SAR** 🌟\n"
                success_msg += f"🎴 **{member_name}** dari **{group_name}**\n"
                success_msg += f"✨ **Rarity:** {rarity} (Guaranteed)\n"
                success_msg += f"📸 **Photo:** Google Drive\n"
                success_msg += f"🔑 **Admin Command**"
                
                return card_image, success_msg
            else:
                return None, f"❌ Gagal generate kartu SAR {member_name} dari {group_name}"
            
        except Exception as e:
            logger.error(f"Error in gacha_guaranteed_sar: {e}")
            return None, f"❌ Error saat generate SAR: {str(e)}"
    
    def gacha_by_member_guaranteed_sar(self, member_name):
        """Admin command: Generate guaranteed SAR card for specific member"""
        if not self.members_data:
            return None, "❌ Data member tidak tersedia"
        
        try:
            # Search for member
            search_results = self._search_member_in_json(member_name)
            
            if not search_results:
                return None, f"❌ Member '{member_name}' tidak ditemukan dalam database!"
            
            # Use first result
            member_data = search_results[0]
            member_key = member_data['member_key']
            
            if member_key not in self.members_data:
                return None, f"❌ Data foto untuk '{member_name}' tidak tersedia!"
            
            member_info = self.members_data[member_key]
            
            # Get photo URL
            photo_url, _ = self._get_member_photo_url(member_key)
            
            if not photo_url:
                return None, f"❌ Foto untuk '{member_name}' tidak dapat diakses!"
            
            # Force SAR rarity
            rarity = "SAR"
            
            # Generate card using design_kartu
            card_image = self.generate_card(
                member_data.get('name', member_info.get('name', 'Unknown')),
                member_data.get('group', member_info.get('group', 'Unknown')),
                rarity
            )
            
            if card_image:
                member_display_name = member_data.get('name', member_info.get('name', 'Unknown'))
                group_display_name = member_data.get('group', member_info.get('group', 'Unknown'))
                
                success_msg = f"🌟 **ADMIN GUARANTEED SAR** 🌟\n"
                success_msg += f"🎴 **{member_display_name}** dari **{group_display_name}**\n"
                success_msg += f"✨ **Rarity:** {rarity} (Guaranteed)\n"
                success_msg += f"📸 **Photo:** Google Drive\n"
                success_msg += f"🎯 **Generated for:** {member_name}\n"
                success_msg += f"🔑 **Admin Command**"
                
                return card_image, success_msg
            else:
                return None, f"❌ Gagal generate kartu SAR untuk '{member_name}'"
            
        except Exception as e:
            logger.error(f"Error generating guaranteed SAR for '{member_name}': {e}")
            return None, f"❌ Error saat generate SAR: {str(e)}"
