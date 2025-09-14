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
        
        # Setup paths berdasarkan mode
        if test_mode:
            self.json_path = 'data/member_data/test_Path_Foto_DriveIDs.json'
            self.gdrive_folder = os.getenv('TEST_GDRIVE_FOLDER_ID', '1Oveb-cdjKRpanoSFaMFoi6z3X4I0F4mX')
            self.backup_prefix = 'test_backup'
        else:
            self.json_path = 'data/member_data/Path_Foto_DriveIDs_Real.json'
            self.gdrive_folder = "1l5WQcYQu93oN3LQoLdj6hchWELy9hdfI"
            self.backup_prefix = 'backup'
        
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
        """Setup OAuth authentication"""
        try:
            creds = None
            
            # Load existing token
            if os.path.exists('token.json'):
                creds = Credentials.from_authorized_user_file('token.json', scopes)
            
            # Refresh or get new credentials
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists('credentials.json'):
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'credentials.json', scopes)
                    creds = flow.run_local_server(port=0, open_browser=False)
                    
                    # Save token
                    with open('token.json', 'w') as token:
                        token.write(creds.to_json())
            
            # Build service
            self.drive_service = build('drive', 'v3', credentials=creds)
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
            # Restore original test mode
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
        """Safe gallery scraping dengan error isolation"""
        try:
            # Use existing scrape_member_gallery - tidak modify
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
        """Process dan upload photos dengan error handling"""
        uploaded_files = []
        temp_dir = Path("temp_expansion")
        temp_dir.mkdir(exist_ok=True)
        
        try:
            logger.info(f"🔄 Memulai proses {len(photos)} foto...")
            
            for i, photo in enumerate(photos):
                try:
                    # Lewati URL yang tidak valid
                    if not self._is_valid_image_url(photo['url']):
                        logger.warning(f"⚠️ Melewati URL tidak valid: {photo['url'][:100]}...")
                        continue
                    
                    # Log URL yang sedang diproses
                    logger.info(f"📥 Memproses foto {i+1}: {photo['url'][:80]}...")
                    
                    # Download foto dengan penanganan error yang lebih baik
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    response = requests.get(photo['url'], timeout=30, headers=headers)
                    response.raise_for_status()
                    
                    # Cek apakah response benar-benar gambar
                    content_type = response.headers.get('content-type', '')
                    if not content_type.startswith('image/'):
                        logger.warning(f"⚠️ Melewati konten bukan gambar: {content_type}")
                        continue
                    
                    # Generate nama file
                    filename = self._generate_filename(
                        member_name, group_name, photo['section'], i + 1, photo['url']
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
                                'original_url': photo['url']
                            })
                            logger.info(f"✅ Uploaded: {filename} -> {file_id}")
                        else:
                            logger.error(f"❌ Upload failed: No file ID returned for {filename}")
                    except Exception as upload_error:
                        logger.error(f"❌ Upload error for {filename}: {upload_error}")
                    
                    # Cleanup temp file
                    temp_path.unlink(missing_ok=True)
                    
                    # Rate limiting (increased for safety)
                    await asyncio.sleep(4)
                    
                except Exception as e:
                    logger.error(f"❌ Error memproses foto {i + 1}: {e}")
                    logger.error(f"🔗 URL yang gagal: {photo.get('url', 'Unknown')}")
                    continue
            
        finally:
            # Cleanup temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
        
        return uploaded_files
    
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
        """Upload file menggunakan Google Drive API langsung"""
        try:
            file_metadata = {
                'name': filename,
                'parents': [self.gdrive_folder]
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
        
        # Skip thumbnail/scaled versions that often 404
        skip_patterns = [
            '/scale-to-width-down/',
            '/thumb/',
            '/150px-',
            '/200px-',
            'data:image',
            '....'  # Skip truncated URLs ending with ....
        ]
        
        for pattern in skip_patterns:
            if pattern in url:
                return False
        
        return True

    def _generate_filename(self, member_name: str, group_name: str, section: str, index: int, url: str) -> str:
        """Generate consistent filename"""
        # Clean names
        clean_member = re.sub(r'[^\w\-_]', '', member_name)
        clean_group = re.sub(r'[^\w\-_]', '', group_name.replace(' ', ''))
        clean_section = re.sub(r'[^\w\-_]', '', section)
        
        # Extract extension
        ext = 'jpg'
        if '.' in url:
            ext = url.split('.')[-1].split('?')[0].lower()
            if ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                ext = 'jpg'
        
        # Format: MEMBER_GROUP_SECTION_INDEX.ext
        filename = f"{clean_member}_{clean_group}_{clean_section}_{index:03d}.{ext}"
        return filename
    
    async def _update_json_safely(self, member_name: str, group_name: str, uploaded_files: List[Dict]) -> Dict:
        """Update JSON database dengan backup dan rollback"""
        try:
            # Create backup first
            backup_path = self._create_backup()
            
            # Load existing JSON
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
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
            
            # Add new Google Drive IDs
            existing_photos = data['members'][member_key]['photos']
            new_drive_ids = [f['file_id'] for f in uploaded_files]
            unique_new_ids = [id for id in new_drive_ids if id not in existing_photos]
            
            data['members'][member_key]['photos'].extend(unique_new_ids)
            
            # Update metadata
            data['total_files'] = data.get('total_files', 0) + len(unique_new_ids)
            data['last_updated'] = datetime.now().isoformat()
            
            # Save updated JSON
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ JSON updated: Added {len(unique_new_ids)} photos for {member_key}")
            logger.info(f"📄 Backup created: {backup_path}")
            
            return {
                "success": True,
                "added_photos": len(unique_new_ids),
                "backup_path": backup_path
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
        """Create backup of JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{self.backup_prefix}_Path_Foto_DriveIDs_{timestamp}.json"
        backup_path = f"data/member_data/{backup_filename}"
        
        shutil.copy2(self.json_path, backup_path)
        return backup_path
    
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
