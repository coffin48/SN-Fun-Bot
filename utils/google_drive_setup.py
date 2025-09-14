"""
Google Drive API Setup dan Upload Script untuk SN Fun Bot
Menggunakan Google Drive API untuk upload foto dan generate file ID mapping
"""

import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
import mimetypes
from pathlib import Path

# Scopes yang dibutuhkan untuk Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive.file']

class GoogleDriveUploader:
    def __init__(self, credentials_file='credentials.json', token_file='token.json'):
        """
        Initialize Google Drive API client
        
        Args:
            credentials_file: Path ke credentials.json dari Google Cloud Console
            token_file: Path untuk menyimpan token authentication
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.authenticate()
    
    def authenticate(self):
        """Authenticate dengan Google Drive API"""
        creds = None
        
        # Load existing token jika ada
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        
        # Jika tidak ada valid credentials, lakukan OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials untuk next run
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('drive', 'v3', credentials=creds)
        print("✅ Google Drive API authenticated successfully!")
    
    def create_folder(self, folder_name, parent_folder_id=None):
        """
        Buat folder di Google Drive
        
        Args:
            folder_name: Nama folder yang akan dibuat
            parent_folder_id: ID parent folder (None untuk root)
            
        Returns:
            folder_id: ID folder yang baru dibuat
        """
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            folder = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            print(f"✅ Folder '{folder_name}' created with ID: {folder_id}")
            
            # Set folder permission to public
            self.make_public(folder_id)
            
            return folder_id
            
        except HttpError as error:
            print(f"❌ Error creating folder: {error}")
            return None
    
    def make_public(self, file_id):
        """Make file/folder public (anyone with link can view)"""
        try:
            permission = {
                'role': 'reader',
                'type': 'anyone'
            }
            
            self.service.permissions().create(
                fileId=file_id,
                body=permission
            ).execute()
            
            print(f"✅ File {file_id} made public")
            
        except HttpError as error:
            print(f"❌ Error making file public: {error}")
    
    def upload_file(self, file_path, folder_id=None, make_public=True):
        """
        Upload file ke Google Drive
        
        Args:
            file_path: Path ke file yang akan diupload
            folder_id: ID folder tujuan (None untuk root)
            make_public: Apakah file dibuat public
            
        Returns:
            file_id: ID file yang diupload
        """
        try:
            file_name = os.path.basename(file_path)
            mime_type, _ = mimetypes.guess_type(file_path)
            
            file_metadata = {'name': file_name}
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            media = MediaFileUpload(file_path, mimetype=mime_type)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            
            if make_public:
                self.make_public(file_id)
            
            print(f"✅ Uploaded: {file_name} -> ID: {file_id}")
            return file_id
            
        except HttpError as error:
            print(f"❌ Error uploading {file_path}: {error}")
            return None
    
    def upload_photos_batch(self, photos_directory, output_json='drive_photo_mapping.json'):
        """
        Upload semua foto dari directory dan generate JSON mapping
        
        Args:
            photos_directory: Path ke directory yang berisi foto
            output_json: Path output file JSON mapping
        """
        print(f"🚀 Starting batch upload from: {photos_directory}")
        
        # Create main folder untuk SN Fun Bot photos
        main_folder_id = self.create_folder("SN-Fun-Bot-Photos")
        if not main_folder_id:
            print("❌ Failed to create main folder")
            return
        
        photo_mapping = {
            "base_url": "https://drive.google.com/uc?export=view&id=",
            "main_folder_id": main_folder_id,
            "members": {}
        }
        
        photos_dir = Path(photos_directory)
        
        # Process setiap subdirectory (grup/member)
        for member_dir in photos_dir.iterdir():
            if member_dir.is_dir():
                member_name = member_dir.name
                print(f"\n📁 Processing member: {member_name}")
                
                # Create folder untuk member ini
                member_folder_id = self.create_folder(member_name, main_folder_id)
                if not member_folder_id:
                    continue
                
                photo_mapping["members"][member_name] = {
                    "folder_id": member_folder_id,
                    "photos": []
                }
                
                # Upload semua foto di folder member
                photo_files = []
                for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.webp']:
                    photo_files.extend(member_dir.glob(ext))
                
                for photo_file in photo_files:
                    file_id = self.upload_file(str(photo_file), member_folder_id)
                    if file_id:
                        photo_mapping["members"][member_name]["photos"].append({
                            "filename": photo_file.name,
                            "file_id": file_id,
                            "url": f"https://drive.google.com/uc?export=view&id={file_id}"
                        })
        
        # Save mapping ke JSON file
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(photo_mapping, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Batch upload completed!")
        print(f"📄 Photo mapping saved to: {output_json}")
        print(f"📊 Total members processed: {len(photo_mapping['members'])}")
        
        # Print summary
        total_photos = sum(len(member['photos']) for member in photo_mapping['members'].values())
        print(f"📸 Total photos uploaded: {total_photos}")
        
        return photo_mapping

def main():
    """Main function untuk testing"""
    print("🚀 Google Drive Photo Uploader untuk SN Fun Bot")
    print("=" * 50)
    
    # Initialize uploader
    uploader = GoogleDriveUploader()
    
    # Example usage - ganti dengan path directory foto Anda
    photos_directory = "Databse Foto Idol Kpop"  # Sesuaikan dengan struktur folder Anda
    
    if os.path.exists(photos_directory):
        mapping = uploader.upload_photos_batch(photos_directory)
        print("\n🎉 Upload selesai! Check file 'drive_photo_mapping.json'")
    else:
        print(f"❌ Directory tidak ditemukan: {photos_directory}")
        print("💡 Sesuaikan path directory di main() function")

if __name__ == "__main__":
    main()
