"""
Gallery Expansion Service - Safe Implementation
Module terpisah untuk expand database foto gacha dari gallery scraping
TIDAK mengubah existing functionality, hanya menambah fitur baru
"""

import os
import json
import asyncio
import requests
import shutil
from datetime import datetime
from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple

# Import existing modules - tidak modify
from utils.data_fetcher import DataFetcher
from utils.google_drive_setup import GoogleDriveUploader
from core.logger import logger

# Import untuk hybrid authentication
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

class GalleryExpansionService:
    """Safe gallery expansion service dengan hybrid authentication"""
    
    def __init__(self, test_mode=False):
        """
        Initialize expansion service dengan hybrid authentication
        
        Args:
            test_mode: Jika True, gunakan test database dan folder
        """
        self.test_mode = test_mode
        self.enabled = os.getenv('GALLERY_EXPANSION_ENABLED', 'false').lower() == 'true'
        
        # Initialize existing components - tidak modify
        self.data_fetcher = DataFetcher()
        
        # Setup paths - berbeda untuk test mode dan production mode
        if test_mode:
            self.json_path = 'data/member_data/test_Path_Foto_DriveIDs.json'
            self.gdrive_folder = os.getenv('TEST_GDRIVE_FOLDER_ID', '1Rh-XYIdDW0XYlZ8ardZZctukOk1WY_-n')
            self.backup_prefix = 'test_backup'
        else:
            # Production mode - gunakan production JSON dan folder
            self.json_path = os.getenv('GALLERY_JSON_PATH', 'data/member_data/Path_Foto_DriveIDs_Real.json')
            self.gdrive_folder = os.getenv('PRODUCTION_GDRIVE_FOLDER_ID', '1QFqeP5zdY4UcDGRz329wOCP9evIuhgvt')
            self.backup_prefix = 'backup'
        
        # JSON backup folder sama untuk semua mode
        self.json_gdrive_folder = os.getenv('JSON_GDRIVE_FOLDER_ID', '1bmsKpmToFSQiW8Hg03-4kmK6QiwPvgPm')
        
        # Hybrid authentication setup
        self.auth_method = os.getenv('GALLERY_EXPANSION_AUTH_METHOD', 'hybrid').lower()
        self.drive_service = None
        self.gdrive_uploader = None
        
        if self.enabled:
            self._initialize_hybrid_auth()
        else:
            logger.info("⚠️ Gallery expansion service disabled (GALLERY_EXPANSION_ENABLED=false)")
    
    def _initialize_hybrid_auth(self):
        """Initialize hybrid authentication (OAuth + Service Account)"""
        scopes = ['https://www.googleapis.com/auth/drive.file']
        
        # Method 1: Try OAuth first (untuk development)
        if self.auth_method in ['oauth', 'hybrid']:
            try:
                oauth_success = self._setup_oauth_auth(scopes)
                if oauth_success:
                    logger.info("✅ OAuth authentication berhasil")
                    return
            except Exception as e:
                logger.warning(f"⚠️ OAuth authentication gagal: {e}")
        
        # Method 2: Try Service Account (untuk production)
        if self.auth_method in ['service_account', 'hybrid']:
            try:
                sa_success = self._setup_service_account_auth(scopes)
                if sa_success:
                    logger.info("✅ Service Account authentication berhasil")
                    return
            except Exception as e:
                logger.warning(f"⚠️ Service Account authentication gagal: {e}")
        
        # Method 3: Fallback ke existing GoogleDriveUploader
        try:
            self.gdrive_uploader = GoogleDriveUploader()
            logger.info("✅ Fallback ke GoogleDriveUploader berhasil")
        except Exception as e:
            logger.error(f"❌ Semua authentication method gagal: {e}")
            self.enabled = False
    
    def _setup_oauth_auth(self, scopes) -> bool:
        """Setup OAuth authentication dengan environment variables support"""
        try:
            creds = None
            
            # Method 1: Try environment variables first (untuk Railway deployment)
            client_id = os.getenv('GOOGLE_OAUTH_CLIENT_ID')
            client_secret = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET')
            refresh_token = os.getenv('GOOGLE_OAUTH_REFRESH_TOKEN')
            
            if client_id and client_secret and refresh_token:
                logger.info("🔑 Using OAuth credentials from environment variables")
                
                # Create credentials dari environment variables
                token_data = {
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'refresh_token': refresh_token,
                    'token_uri': 'https://oauth2.googleapis.com/token'
                }
                
                creds = Credentials.from_authorized_user_info(token_data, scopes)
                
                # Refresh token jika expired
                if creds.expired:
                    creds.refresh(Request())
                    logger.info("🔄 OAuth token refreshed successfully")
                
                # Build service
                self.drive_service = build('drive', 'v3', credentials=creds)
                logger.info("✅ OAuth authentication berhasil dengan environment variables")
                return True
            
            # Method 2: Fallback ke file lokal (untuk development)
            logger.info("🔍 Fallback ke OAuth file lokal...")
            
            # Load existing token
            if os.path.exists('token.json'):
                creds = Credentials.from_authorized_user_file('token.json', scopes)
            
            # Refresh or get new credentials
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists('credentials.json'):
                        logger.warning("⚠️ credentials.json tidak ditemukan")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'credentials.json', scopes)
                    creds = flow.run_local_server(port=0, open_browser=False)
                    
                    # Save token
                    with open('token.json', 'w') as token:
                        token.write(creds.to_json())
            
            # Build service
            self.drive_service = build('drive', 'v3', credentials=creds)
            logger.info("✅ OAuth authentication berhasil dengan file lokal")
            return True
            
        except Exception as e:
            logger.error(f"OAuth setup error: {e}")
            return False
    
    def _setup_service_account_auth(self, scopes) -> bool:
        """Setup Service Account authentication"""
        try:
            # Try environment variable first
            sa_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
            if sa_json:
                sa_info = json.loads(sa_json)
                creds = service_account.Credentials.from_service_account_info(
                    sa_info, scopes=scopes
                )
            else:
                # Try service account file
                sa_file = 'sn-fun-bot-06bff108efa3.json'
                if not os.path.exists(sa_file):
                    return False
                
                creds = service_account.Credentials.from_service_account_file(
                    sa_file, scopes=scopes
                )
            
            # Build service
            self.drive_service = build('drive', 'v3', credentials=creds)
            return True
            
        except Exception as e:
            logger.error(f"Service Account setup error: {e}")
            return False
    
    def is_enabled(self) -> bool:
        """Check if expansion service is enabled"""
        return self.enabled and (self.drive_service is not None or self.gdrive_uploader is not None)
    
    async def expand_member_photos(self, member_name: str, group_name: str, test_mode: bool = False, max_photos: int = 5) -> Dict:
        """
        Expand member photos - main entry point for gallery expansion
        
        Args:
            member_name: Nama member
            group_name: Nama group  
            test_mode: Jika True, gunakan test mode untuk expansion ini
            max_photos: Maximum photos to add
            
        Returns:
            Dict dengan hasil expansion
        """
        # Override test mode jika diperlukan
        original_test_mode = self.test_mode
        if test_mode:
            self.test_mode = True
            self.json_path = 'data/member_data/test_Path_Foto_DriveIDs.json'
            self.gdrive_folder = os.getenv('TEST_GDRIVE_FOLDER_ID', 'test_folder')
            self.backup_prefix = 'test_backup'
        
        try:
            result = await self.expand_member_safely(member_name, group_name, max_photos)
            return result
        finally:
            # Restore original test mode - TIDAK reset test data
            if test_mode:
                self.test_mode = original_test_mode
                if original_test_mode:
                    self.json_path = 'data/member_data/test_Path_Foto_DriveIDs.json'
                    self.gdrive_folder = os.getenv('TEST_GDRIVE_FOLDER_ID', 'test_folder')
                    self.backup_prefix = 'test_backup'
                else:
                    self.json_path = 'data/member_data/Path_Foto_DriveIDs_Real.json'
                    self.gdrive_folder = "1l5WQcYQu93oN3LQoLdj6hchWELy9hdfI"
                    self.backup_prefix = 'backup'
            
            # NOTE: Test data TIDAK di-clear untuk mempertahankan incremental filename

    async def expand_member_safely(self, member_name: str, group_name: str, max_photos: int = 5) -> Dict:
        """
        Safe member expansion - tidak affect existing system
        
        Args:
            member_name: Nama member
            group_name: Nama group
            max_photos: Maximum photos to add (default 5)
            
        Returns:
            Dict dengan hasil expansion
        """
        if not self.is_enabled():
            return {
                "success": False,
                "error": "Gallery expansion service is disabled",
                "reason": "GALLERY_EXPANSION_ENABLED=false or Google Drive not configured"
            }
        
        try:
            logger.info(f"🚀 Starting safe expansion for {member_name} ({group_name})")
            
            # Step 1: Scrape gallery photos
            gallery_data = await self._scrape_gallery_safely(member_name, group_name)
            if not gallery_data.get('success'):
                return gallery_data
            
            # Step 2: Filter quality photos (safer limit)
            safe_limit = min(max_photos, 5)  # Max 5 photos untuk safety
            quality_photos = self._filter_quality_photos(gallery_data['images'], safe_limit)
            logger.info(f"📊 Filtered {len(quality_photos)} quality photos from {len(gallery_data['images'])} total")
            
            if not quality_photos:
                return {
                    "success": False,
                    "error": "No quality photos found for expansion"
                }
            
            # Step 3: Download and upload photos
            uploaded_files = await self._process_photos_safely(
                quality_photos, member_name, group_name
            )
            
            if not uploaded_files:
                logger.error(f"❌ CRITICAL: No photos uploaded successfully for {member_name}")
                logger.error(f"📊 SUMMARY: Processed {len(quality_photos)} quality photos, 0 uploaded")
                logger.error(f"🔧 DEBUG: Check Railway logs above for detailed error messages")
                return {
                    "success": False,
                    "error": f"Failed to upload any photos. Processed {len(quality_photos)} photos but all uploads failed. Check Google Drive credentials and folder permissions."
                }
            
            # Step 4: Update JSON database safely
            update_result = await self._update_json_safely(
                member_name, group_name, uploaded_files
            )
            
            if not update_result['success']:
                return update_result
            
            logger.info(f"✅ Safe expansion completed for {member_name}")
            return {
                "success": True,
                "member": member_name,
                "group": group_name,
                "new_photos": len(uploaded_files),
                "drive_ids": [f['file_id'] for f in uploaded_files],
                "sections": list(set(f['section'] for f in uploaded_files)),
                "test_mode": self.test_mode
            }
            
        except Exception as e:
            logger.error(f"❌ Safe expansion failed for {member_name}: {e}")
            return {
                "success": False,
                "error": f"Expansion failed: {str(e)}",
                "member": member_name,
                "group": group_name
            }
    
    async def _scrape_gallery_safely(self, member_name: str, group_name: str) -> Dict:
        """Safe gallery scraping dengan error isolation dan enhanced section support"""
        try:
            # Enhanced scraping untuk test mode - scrape dari multiple sections
            if self.test_mode:
                from utils.enhanced_gallery_scraper import EnhancedGalleryScraper
                
                enhanced_scraper = EnhancedGalleryScraper()
                try:
                    gallery_data = await enhanced_scraper.scrape_gallery_with_sections(
                        member_name, group_name, max_photos=50
                    )
                    await enhanced_scraper.cleanup()
                    
                    if gallery_data.get('success'):
                        logger.info(f"🎯 Enhanced scraping: {gallery_data['total_found']} total, {gallery_data['sections_scraped']} sections")
                        return gallery_data
                    else:
                        logger.warning(f"Enhanced scraping failed: {gallery_data.get('error')}")
                        # Fallback to regular scraping
                except Exception as e:
                    logger.warning(f"Enhanced scraping error: {e}, falling back to regular scraping")
                    await enhanced_scraper.cleanup()
            
            # Regular scraping (production mode atau fallback)
            gallery_data = await self.data_fetcher.scrape_member_gallery(
                member_name, group_name
            )
            
            if gallery_data.get('error'):
                return {
                    "success": False,
                    "error": f"Gallery scraping failed: {gallery_data['error']}"
                }
            
            if not gallery_data.get('images'):
                return {
                    "success": False,
                    "error": "No images found in gallery"
                }
            
            logger.info(f"📸 Found {len(gallery_data['images'])} images for {member_name}")
            return {
                "success": True,
                "images": gallery_data['images'],
                "sections": gallery_data.get('sections', [])
            }
            
        except Exception as e:
            logger.error(f"Gallery scraping error for {member_name}: {e}")
            return {
                "success": False,
                "error": f"Gallery scraping exception: {str(e)}"
            }
    
    def _filter_quality_photos(self, images: List[Dict], max_photos: int) -> List[Dict]:
        """Filter photos berdasarkan quality dan priority"""
        quality_photos = []
        
        # Priority keywords untuk section detection
        priority_keywords = {
            'concept': ['concept', 'teaser', 'promotional'],
            'pictorial': ['pictorial', 'magazine', 'photoshoot'],
            'official': ['official', 'press', 'event'],
            'misc': ['behind', 'candid', 'misc']
        }
        
        for img in images:
            # Skip thumbnails dan low quality
            if ('thumb' in img['url'] or 
                'revision' in img['url'] or
                len(img['url']) < 50):
                continue
            
            # Categorize by alt text atau URL
            section = 'misc'  # default
            alt_text = img.get('alt', '').lower()
            
            for section_name, keywords in priority_keywords.items():
                if any(keyword in alt_text for keyword in keywords):
                    section = section_name
                    break
            
            quality_photos.append({
                'url': img['url'],
                'alt': img.get('alt', ''),
                'section': section,
                'type': img.get('type', 'unknown')
            })
        
        # Sort by priority (concept > pictorial > official > misc)
        priority_order = ['concept', 'pictorial', 'official', 'misc']
        quality_photos.sort(key=lambda x: priority_order.index(x['section']))
        
        # Limit photos
        return quality_photos[:max_photos]
    
    async def _process_photos_safely(self, photos: List[Dict], member_name: str, group_name: str) -> List[Dict]:
        """Process dan upload photos dengan error handling dan duplicate detection"""
        uploaded_files = []
        temp_dir = Path("temp_expansion")
        temp_dir.mkdir(exist_ok=True)
        
        # Load existing URLs untuk duplicate detection
        existing_urls = await self._get_existing_urls(member_name, group_name)
        processed_urls = set()  # Track URLs dalam batch ini
        
        # Track next index per section untuk incremental naming
        section_counters = {}
        
        # Randomize photo order untuk test mode agar tidak selalu foto yang sama
        if self.test_mode:
            import random
            photos = photos.copy()  # Don't modify original list
            random.shuffle(photos)
            logger.info(f"🎲 Test mode: Randomized photo order untuk variasi")
        
        try:
            logger.info(f"🔄 Memulai proses {len(photos)} foto...")
            logger.info(f"📊 Found {len(existing_urls)} existing URLs untuk duplicate check")
            
            for i, photo in enumerate(photos):
                try:
                    # Lewati URL yang tidak valid
                    if not self._is_valid_image_url(photo['url']):
                        logger.warning(f"WARNING: Melewati URL tidak valid: {photo['url'][:100]}...")
                        continue
                    
                    # Convert thumbnail URL to full image URL
                    full_url = self._convert_to_full_image_url(photo['url'])
                    
                    # Debug logging untuk URL comparison
                    logger.info(f"DEBUG: Original URL: {photo['url'][:80]}...")
                    logger.info(f"DEBUG: Full URL: {full_url[:80]}...")
                    
                    # Check duplicate dengan existing URLs
                    if full_url in existing_urls:
                        logger.info(f"SKIP: URL sudah ada di database: {full_url[:80]}...")
                        continue
                    
                    # Check duplicate dengan original URL juga
                    if photo['url'] in existing_urls:
                        logger.info(f"SKIP: Original URL sudah ada di database: {photo['url'][:80]}...")
                        continue
                    
                    # Check duplicate dalam batch ini
                    if full_url in processed_urls:
                        logger.info(f"SKIP: URL duplikat dalam batch ini: {full_url[:80]}...")
                        continue
                    
                    # Add ke processed URLs (both original and full)
                    processed_urls.add(full_url)
                    processed_urls.add(photo['url'])
                    
                    # Log URL yang sedang diproses
                    logger.info(f"PROCESSING: Memproses foto {i+1}: {full_url[:80]}...")
                    
                    # Download foto dengan penanganan error yang lebih baik
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    response = requests.get(full_url, timeout=30, headers=headers)
                    response.raise_for_status()
                    
                    # Cek apakah response benar-benar gambar
                    content_type = response.headers.get('content-type', '')
                    if not content_type.startswith('image/'):
                        logger.warning(f"⚠️ Melewati konten bukan gambar: {content_type}")
                        continue
                    
                    # Get next incremental index untuk section ini
                    section = photo['section']
                    if section not in section_counters:
                        section_counters[section] = self._get_next_file_index(member_name, group_name, section)
                    
                    next_index = section_counters[section]
                    section_counters[section] += 1  # Increment untuk foto berikutnya
                    
                    # Generate nama file dengan incremental counter
                    filename = self._generate_filename(
                        member_name, group_name, section, next_index, photo['url']
                    )
                    
                    temp_path = temp_dir / filename
                    
                    # Save temporary file
                    with open(temp_path, 'wb') as f:
                        f.write(response.content)
                    
                    # Upload to Google Drive dengan hybrid method
                    try:
                        file_id = await self._upload_file_hybrid(str(temp_path), filename)
                        
                        if file_id:
                            uploaded_files.append({
                                'file_id': file_id,
                                'filename': filename,
                                'section': photo['section'],
                                'url': full_url,  # Store full URL untuk tracking
                                'original_url': photo['url']  # Store original URL juga
                            })
                            logger.info(f"SUCCESS: Upload berhasil - {filename} ({file_id})")
                        else:
                            logger.error(f"FAILED: Upload gagal - {filename}")
                    
                    except Exception as upload_error:
                        logger.error(f"UPLOAD ERROR: {filename} - {upload_error}")
                    
                    finally:
                        # Cleanup temporary file
                        if temp_path.exists():
                            temp_path.unlink()
                
                except Exception as photo_error:
                    logger.error(f"PHOTO ERROR {i+1}: {photo_error}")
                    continue
        
        except Exception as e:
            logger.error(f"❌ Process photos error: {e}")
        
        finally:
            # Cleanup temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
        
        logger.info(f"📊 SUMMARY: {len(uploaded_files)} foto berhasil diupload dari {len(photos)} foto")
        return uploaded_files
    
    async def _get_existing_urls(self, member_name: str, group_name: str) -> set:
        """Get existing URLs untuk duplicate detection"""
        existing_urls = set()
        
        try:
            if not os.path.exists(self.json_path):
                logger.info(f"DEBUG: JSON file tidak ditemukan: {self.json_path}")
                return existing_urls
            
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            member_key = self._generate_member_key(member_name, group_name)
            logger.info(f"DEBUG: Checking member_key: {member_key}")
            
            if member_key in data.get('members', {}):
                member_data = data['members'][member_key]
                logger.info(f"DEBUG: Member data found: {member_key}")
                
                # Method 1: Check photo_metadata untuk URL yang sudah ada (new format)
                if 'photo_metadata' in member_data:
                    photo_metadata = member_data['photo_metadata']
                    logger.info(f"DEBUG: Found {len(photo_metadata)} photo metadata entries")
                    
                    for photo_info in photo_metadata:
                        # Add both original URL dan converted URL
                        if 'url' in photo_info:
                            existing_urls.add(photo_info['url'])
                        if 'original_url' in photo_info:
                            existing_urls.add(photo_info['original_url'])
                    
                    logger.info(f"DEBUG: Loaded {len(existing_urls)} existing URLs from photo_metadata")
                
                # Method 2: Check photos array untuk Google Drive IDs (old format)
                elif 'photos' in member_data and isinstance(member_data['photos'], list):
                    photos = member_data['photos']
                    logger.info(f"DEBUG: Found {len(photos)} Google Drive file IDs (old format)")
                    
                    # Convert Google Drive IDs ke URLs untuk comparison
                    base_url = data.get('base_url', 'https://drive.google.com/uc?export=view&id=')
                    for file_id in photos:
                        if isinstance(file_id, str):
                            drive_url = f"{base_url}{file_id}"
                            existing_urls.add(drive_url)
                    
                    logger.info(f"DEBUG: Converted {len(existing_urls)} Google Drive URLs from file IDs")
                else:
                    logger.info(f"DEBUG: No photo data found for {member_key}")
            else:
                logger.info(f"DEBUG: Member not found: {member_key}")
            
            logger.info(f"DEBUG: Total existing URLs found: {len(existing_urls)}")
            return existing_urls
            
        except Exception as e:
            logger.error(f"Error loading existing URLs: {e}")
            return existing_urls
    
    async def _upload_file_hybrid(self, file_path: str, filename: str) -> Optional[str]:
        """Upload file menggunakan hybrid authentication"""
        try:
            # Method 1: Try direct Drive API jika tersedia
            if self.drive_service:
                return self._upload_with_drive_api(file_path, filename)
            
            # Method 2: Fallback ke GoogleDriveUploader
            elif self.gdrive_uploader:
                return self.gdrive_uploader.upload_file(file_path, self.gdrive_folder)
            
            else:
                logger.error("❌ No authentication method available for upload")
                return None
                
        except Exception as e:
            logger.error(f"❌ Hybrid upload error: {e}")
            return None
    
    def _upload_with_drive_api(self, file_path: str, filename: str) -> Optional[str]:
        """Upload file menggunakan Google Drive API langsung dengan folder structure Group > Member"""
        try:
            # Extract group dan member dari filename untuk folder structure
            # Format filename: group_member_index.ext
            parts = filename.split('_')
            if len(parts) >= 2:
                group_name = parts[0].upper()  # Convert ke uppercase untuk consistency
                member_name = parts[1].capitalize()  # Capitalize first letter
            else:
                # Fallback jika format tidak sesuai
                group_name = "UNKNOWN"
                member_name = "UNKNOWN"
            
            # Validate root folder exists first
            try:
                self.drive_service.files().get(fileId=self.gdrive_folder).execute()
            except HttpError as folder_error:
                logger.error(f"❌ Target folder not accessible: {self.gdrive_folder}")
                logger.error(f"❌ Folder error: {folder_error}")
                return None
            
            # Create/find Group folder
            group_folder_id = self._create_or_find_folder(group_name, self.gdrive_folder)
            if not group_folder_id:
                logger.error(f"❌ Failed to create/find group folder: {group_name}")
                return None
            
            # Create/find Member folder inside Group folder
            member_folder_id = self._create_or_find_folder(member_name, group_folder_id)
            if not member_folder_id:
                logger.error(f"❌ Failed to create/find member folder: {member_name}")
                return None
            
            logger.info(f"📁 Upload structure: {group_name}/{member_name}/{filename}")
            
            # Upload file to Member folder
            file_metadata = {
                'name': filename,
                'parents': [member_folder_id]
            }
            
            media = MediaFileUpload(file_path, resumable=True)
            
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            return file.get('id')
            
        except HttpError as e:
            if "storageQuotaExceeded" in str(e):
                logger.error(f"❌ Storage quota exceeded: {e}")
            else:
                logger.error(f"❌ Drive API upload error: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Upload error: {e}")
            return None
    
    def _create_or_find_folder(self, folder_name: str, parent_folder_id: str) -> Optional[str]:
        """Create folder jika belum ada, atau return existing folder ID"""
        try:
            # Search for existing folder
            query = f"name='{folder_name}' and '{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            
            results = self.drive_service.files().list(
                q=query,
                fields='files(id, name)'
            ).execute()
            
            folders = results.get('files', [])
            
            if folders:
                # Folder sudah ada, return ID
                folder_id = folders[0]['id']
                logger.info(f"📁 Found existing folder: {folder_name} (ID: {folder_id})")
                return folder_id
            else:
                # Create new folder
                folder_metadata = {
                    'name': folder_name,
                    'parents': [parent_folder_id],
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                
                folder = self.drive_service.files().create(
                    body=folder_metadata,
                    fields='id'
                ).execute()
                
                folder_id = folder.get('id')
                logger.info(f"📁 Created new folder: {folder_name} (ID: {folder_id})")
                return folder_id
                
        except HttpError as e:
            logger.error(f"❌ Error creating/finding folder {folder_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error with folder {folder_name}: {e}")
            return None
    
    async def _upload_json_backup(self, json_data: dict, filename: str) -> Optional[str]:
        """Upload JSON backup ke folder khusus di Google Drive"""
        if not self.drive_service or not self.json_gdrive_folder:
            return None
        
        try:
            import tempfile
            import json
            from googleapiclient.http import MediaFileUpload
            
            # Create temp JSON file dengan proper cleanup
            temp_fd, temp_path = tempfile.mkstemp(suffix='.json', text=True)
            try:
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as temp_file:
                    json.dump(json_data, temp_file, indent=2, ensure_ascii=False)
                
                # Validate JSON folder exists first
                try:
                    self.drive_service.files().get(fileId=self.json_gdrive_folder).execute()
                except HttpError as folder_error:
                    logger.error(f"❌ JSON folder not accessible: {self.json_gdrive_folder}")
                    logger.error(f"❌ JSON folder error: {folder_error}")
                    return None
                
                # Upload to JSON folder
                file_metadata = {
                    'name': filename,
                    'parents': [self.json_gdrive_folder]
                }
                
                media = MediaFileUpload(temp_path, mimetype='application/json')
                
                file = self.drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                
            finally:
                # Cleanup temp file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            
            file_id = file.get('id')
            logger.info(f"JSON backup uploaded: {filename} -> {file_id}")
            return file_id
            
        except Exception as e:
            logger.error(f"Failed to upload JSON backup: {e}")
            return None
    
    def _convert_to_full_image_url(self, url: str) -> str:
        """Convert thumbnail/scaled URL to full image URL"""
        if not url:
            return url
            
        # Convert Wikia/Fandom thumbnail URLs to full size
        if '/scale-to-width-down/' in url:
            # Remove the scaling part
            url = url.split('/scale-to-width-down/')[0]
        
        if '/thumb/' in url:
            # Remove thumb directory
            url = url.replace('/thumb/', '/')
        
        # Remove size prefixes
        import re
        url = re.sub(r'/\d+px-', '/', url)
        
        return url
    
    def _is_valid_image_url(self, url: str) -> bool:
        """Check if URL is valid for image download"""
        if not url or not isinstance(url, str):
            return False
        
        # Skip data URLs (base64 encoded images)
        if url.startswith('data:'):
            return False
        
        # Skip very short URLs
        if len(url) < 10:
            return False
        
        # Must be HTTP/HTTPS
        if not url.startswith(('http://', 'https://')):
            return False
        
        # Skip URLs ending with .... (truncated)
        if url.endswith('....'):
            return False
        
        # Convert thumbnail URL to full URL and check again
        full_url = self._convert_to_full_image_url(url)
        
        # Now allow the converted URL
        return True

    def _generate_filename(self, member_name: str, group_name: str, section: str, next_index: int, url: str) -> str:
        """Generate incremental filename yang melanjutkan dari counter terakhir dengan uniqueness check"""
        # Clean names
        clean_member = re.sub(r'[^\w\-_]', '', member_name.lower())
        clean_group = re.sub(r'[^\w\-_]', '', group_name.lower().replace(' ', ''))
        clean_section = re.sub(r'[^\w\-_]', '', section.lower())
        
        # Extract extension
        ext = 'jpg'
        if '.' in url:
            ext = url.split('.')[-1].split('?')[0].lower()
            if ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                ext = 'jpg'
        
        # Generate base filename sesuai format database lama: Group_Member_Index.jpg
        base_filename = f"{clean_group}_{clean_member}_{next_index}.{ext}"
        
        # Check for uniqueness dalam existing filenames
        if self._is_filename_unique(base_filename, member_name, group_name):
            return base_filename
        
        # Jika tidak unique, cari index yang available
        for attempt in range(next_index, next_index + 100):  # Try up to 100 indices
            candidate_filename = f"{clean_group}_{clean_member}_{attempt}.{ext}"
            if self._is_filename_unique(candidate_filename, member_name, group_name):
                logger.info(f"🔄 Filename conflict resolved: {base_filename} -> {candidate_filename}")
                return candidate_filename
        
        # Fallback dengan timestamp jika masih conflict
        import time
        timestamp = int(time.time() * 1000) % 10000  # Last 4 digits of timestamp
        fallback_filename = f"{clean_group}_{clean_member}_{next_index}_{timestamp}.{ext}"
        logger.warning(f"⚠️ Using timestamp fallback: {fallback_filename}")
        return fallback_filename
    
    def _is_filename_unique(self, filename: str, member_name: str, group_name: str) -> bool:
        """Check if filename is unique dalam existing photo metadata"""
        try:
            if not os.path.exists(self.json_path):
                return True
            
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            member_key = self._generate_member_key(member_name, group_name)
            
            if member_key not in data.get('members', {}):
                return True
            
            # Check existing filenames dalam photo_metadata
            if 'photo_metadata' in data['members'][member_key]:
                existing_filenames = [
                    photo_info.get('filename', '') 
                    for photo_info in data['members'][member_key]['photo_metadata']
                ]
                return filename not in existing_filenames
            
            return True
            
        except Exception as e:
            logger.warning(f"WARNING: Error checking filename uniqueness: {e}")
            return True  # Assume unique jika error
    
    def _get_next_file_index(self, member_name: str, group_name: str, section: str) -> int:
        """Get next incremental index dengan smart logic: folder kosong = reset ke 1, folder ada isi = melanjutkan existing"""
        try:
            # Debug logging untuk troubleshooting
            logger.info(f"🔍 Getting next index for {member_name} {group_name} {section}")
            logger.info(f"🔍 JSON path: {self.json_path}")
            logger.info(f"🔍 Test mode: {self.test_mode}")
            
            if not os.path.exists(self.json_path):
                logger.info(f"🔍 JSON file tidak ada, return index 1")
                return 1
            
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            member_key = self._generate_member_key(member_name, group_name)
            logger.info(f"🔍 Member key: {member_key}")
            
            if member_key not in data.get('members', {}):
                logger.info(f"🔍 Member key tidak ada di JSON, return index 1")
                return 1
            
            # Clean section name untuk matching
            import re
            clean_section = re.sub(r'[^\w\-_]', '', section.lower())
            logger.info(f"🔍 Clean section: {clean_section}")
            
            # SMART LOGIC: Check existing files via JSON metadata (untuk GitHub/Railway deployment)
            existing_files_count = self._count_existing_physical_files(member_name, group_name, clean_section)
            logger.info(f"🔍 Existing files found in metadata: {existing_files_count}")
            
            # Jika tidak ada existing files di JSON metadata, reset ke 1
            if existing_files_count == 0:
                logger.info(f"🔄 No existing files in metadata, resetting index to 1")
                return 1
            
            # Jika ada file fisik, melanjutkan dari JSON metadata
            max_index = 0
            photo_count = 0
            
            if 'photo_metadata' in data['members'][member_key]:
                photo_count = len(data['members'][member_key]['photo_metadata'])
                logger.info(f"🔍 Found {photo_count} existing photos in metadata")
                
                for photo_info in data['members'][member_key]['photo_metadata']:
                    filename = photo_info.get('filename', '')
                    
                    # Extract index dari filename format database lama: Group_Member_XXX.ext
                    # Cari pattern _XXX. di akhir filename (support any digits)
                    match = re.search(r'_(\d+)\.[^.]+$', filename)
                    if match:
                        index = int(match.group(1))
                        max_index = max(max_index, index)
                        logger.info(f"🔍 Found existing index {index} in {filename}")
            else:
                logger.info(f"🔍 No photo_metadata found, return index 1")
                return 1
            
            next_index = max_index + 1
            logger.info(f"🔍 Max index: {max_index}, Next index: {next_index}")
            
            return next_index
            
        except Exception as e:
            logger.warning(f"WARNING: Error getting next index: {e}")
            return 1
    
    def _count_existing_physical_files(self, member_name: str, group_name: str, section: str) -> int:
        """Count existing files - untuk GitHub/Railway deployment, check via Google Drive API"""
        try:
            # Generate pattern untuk matching files
            import re
            clean_member = re.sub(r'[^\w\-_]', '', member_name.lower())
            clean_group = re.sub(r'[^\w\-_]', '', group_name.lower())
            clean_section = re.sub(r'[^\w\-_]', '', section.lower())
            
            pattern = f"{clean_member}_{clean_group}_{clean_section}_"
            
            # Untuk GitHub/Railway deployment, check existing files via JSON metadata
            # Karena file tersimpan di Google Drive, bukan local filesystem
            if not os.path.exists(self.json_path):
                logger.info(f"🔍 No JSON file, assuming no existing files")
                return 0
            
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            member_key = self._generate_member_key(member_name, group_name)
            
            if member_key not in data.get('members', {}):
                logger.info(f"🔍 No member data, assuming no existing files")
                return 0
            
            # Count files yang match pattern dari JSON metadata
            count = 0
            if 'photo_metadata' in data['members'][member_key]:
                for photo_info in data['members'][member_key]['photo_metadata']:
                    filename = photo_info.get('filename', '')
                    # Check if filename contains the section and matches pattern
                    if pattern in filename and clean_section in filename:
                        count += 1
                        logger.info(f"🔍 Counted file: {filename}")
            
            logger.info(f"🔍 Found {count} existing files in JSON metadata matching pattern {pattern}")
            return count
                
        except Exception as e:
            logger.warning(f"WARNING: Error counting existing files: {e}")
            return 0  # Default ke 0 untuk safety (akan reset ke index 1)
    
    async def _update_json_safely(self, member_name: str, group_name: str, uploaded_files: List[Dict]) -> Dict:
        """Update JSON database dengan backup dan rollback"""
        try:
            # Pastikan folder JSON ada
            json_dir = Path(self.json_path).parent
            json_dir.mkdir(parents=True, exist_ok=True)
            
            # Create backup first (hanya jika file sudah ada)
            backup_path = ""
            if os.path.exists(self.json_path):
                backup_path = self._create_backup()
                logger.info(f"📄 Backup created: {backup_path}")
            else:
                logger.info(f"📝 Creating new JSON file: {self.json_path}")
            
            # Load existing JSON atau create new jika tidak ada
            if os.path.exists(self.json_path):
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                # Create new JSON structure
                data = {
                    "total_members": 0,
                    "total_files": 0,
                    "last_updated": "",
                    "members": {}
                }
            
            # Generate member key
            member_key = self._generate_member_key(member_name, group_name)
            
            # Update atau create member entry
            if member_key not in data['members']:
                data['members'][member_key] = {
                    "name": member_name,
                    "korean_name": "",
                    "full_name": "",
                    "birth_date": "",
                    "group": group_name,
                    "photos": []
                }
                data['total_members'] = data.get('total_members', 0) + 1
            
            # Add new Google Drive IDs dan URL metadata
            existing_photos = data['members'][member_key]['photos']
            new_drive_ids = [f['file_id'] for f in uploaded_files]
            unique_new_ids = [id for id in new_drive_ids if id not in existing_photos]
            
            data['members'][member_key]['photos'].extend(unique_new_ids)
            
            # Add photo metadata untuk duplicate detection
            if 'photo_metadata' not in data['members'][member_key]:
                data['members'][member_key]['photo_metadata'] = []
            
            # Add metadata untuk uploaded files
            for file_info in uploaded_files:
                if file_info['file_id'] in unique_new_ids:
                    metadata = {
                        'file_id': file_info['file_id'],
                        'filename': file_info['filename'],
                        'section': file_info['section'],
                        'url': file_info['url'],
                        'original_url': file_info['original_url'],
                        'upload_date': datetime.now().isoformat()
                    }
                    data['members'][member_key]['photo_metadata'].append(metadata)
            
            # Update metadata
            data['total_files'] = data.get('total_files', 0) + len(unique_new_ids)
            data['last_updated'] = datetime.now().isoformat()
            
            # Save updated JSON
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Upload JSON backup to Google Drive
            backup_filename = f"gallery_backup_{member_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            backup_file_id = await self._upload_json_backup(data, backup_filename)
            
            logger.info(f"✅ JSON updated: Added {len(unique_new_ids)} photos for {member_key}")
            logger.info(f"📄 Backup created: {backup_path}")
            if backup_file_id:
                logger.info(f"☁️ JSON backup uploaded to Drive: {backup_file_id}")
            
            return {
                "success": True,
                "added_photos": len(unique_new_ids),
                "backup_path": backup_path,
                "gdrive_backup_id": backup_file_id
            }
            
        except Exception as e:
            # Rollback on error
            if 'backup_path' in locals():
                try:
                    shutil.copy2(backup_path, self.json_path)
                    logger.info(f"🔄 Rolled back to backup: {backup_path}")
                except:
                    pass
            
            logger.error(f"❌ JSON update failed: {e}")
            return {
                "success": False,
                "error": f"JSON update failed: {str(e)}"
            }
    
    def _create_backup(self) -> str:
        """Create backup of JSON file dengan error handling"""
        try:
            # Pastikan folder backup ada
            backup_dir = Path("data/member_data")
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Pastikan source file ada
            if not os.path.exists(self.json_path):
                logger.warning(f"⚠️ Source JSON file tidak ditemukan: {self.json_path}")
                return ""
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{self.backup_prefix}_Path_Foto_DriveIDs_{timestamp}.json"
            backup_path = backup_dir / backup_filename
            
            # Copy file dengan error handling
            shutil.copy2(self.json_path, str(backup_path))
            logger.info(f"📄 Backup created: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"❌ Backup creation failed: {e}")
            return ""
    
    def _generate_member_key(self, member_name: str, group_name: str) -> str:
        """Generate consistent member key"""
        clean_member = member_name.lower().replace(' ', '_')
        clean_group = group_name.lower().replace(' ', '_')
        return f"{clean_member}_{clean_group}"
    
    def get_expansion_stats(self) -> Dict:
        """Get expansion service statistics"""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return {
                "enabled": self.is_enabled(),
                "test_mode": self.test_mode,
                "total_members": data.get('total_members', 0),
                "total_photos": data.get('total_files', 0),
                "last_updated": data.get('last_updated', 'Unknown'),
                "json_path": self.json_path
            }
        except Exception as e:
            return {
                "enabled": self.is_enabled(),
                "test_mode": self.test_mode,
                "error": f"Failed to load stats: {e}"
            }
