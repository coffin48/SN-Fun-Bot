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

# Try to import PIL with error handling
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: Pillow (PIL) not installed. Gacha system will not work.")

# Try to import design_kartu with error handling
try:
    from design_kartu import *
    DESIGN_KARTU_AVAILABLE = True
except ImportError:
    DESIGN_KARTU_AVAILABLE = False
    print("Warning: design_kartu module not available.")

# Setup logger
logger = logging.getLogger(__name__)

class KpopGachaSystem:
    def __init__(self, json_path="Path_Foto_DriveIDs_Real.json", database_path="Database/DATABASE_KPOP (1).csv"):
        """
        Initialize Kpop Gacha System
        
        Args:
            json_path: Path ke JSON mapping foto yang sudah diperbaiki
            database_path: Path ke database K-pop CSV (backup)
        """
        # Check dependencies first
        if not PIL_AVAILABLE:
            raise ImportError("Pillow (PIL) is required for gacha system. Install with: pip install Pillow")
        
        if not DESIGN_KARTU_AVAILABLE:
            raise ImportError("design_kartu module is required for gacha system.")
        
        self.json_path = json_path
        self.database_path = database_path
        self.font_path = "Gill Sans/Gill Sans Bold Italic.otf"
        
        # Load JSON data
        self.members_data = {}
        self.base_url = ""
        self._load_json_data()
        
        # Sistem probabilitas rarity
        self.RARITY_RATES = {
            "Common": 50,      # 50%
            "Rare": 30,        # 30%
            "Epic": 15,        # 15%
            "Legendary": 4,    # 4%
            "FullArt": 1       # 1%
        }
        
        # Load data
        self._load_json_data()
        self._load_database()
        self._integrate_csv_data()
        
    def _load_json_data(self):
        """Load JSON mapping foto yang sudah diperbaiki"""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.members_data = data.get('members', {})
            self.base_url = data.get('base_url', '')
            
            logger.info(f"JSON data loaded: {len(self.members_data)} members")
            
        except Exception as e:
            logger.error(f"Failed to load JSON data: {e}")
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
        else:
            photo_url = photo_filename
        
        return photo_url, photo_filename
    
    def _download_image_from_url(self, url):
        """
        Download image dari URL (Google Drive)
        
        Args:
            url: URL foto
            
        Returns:
            PIL Image object atau None jika gagal
        """
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            image = Image.open(BytesIO(response.content))
            return image.convert("RGBA")
            
        except Exception as e:
            logger.error(f"Failed to download image from {url}: {e}")
            return None
    
    def _get_all_member_keys(self):
        """Get semua member keys dari JSON data"""
        return list(self.members_data.keys())
    
    def _get_member_keys_by_group(self, group_name):
        """Get member keys dari grup tertentu"""
        group_lower = group_name.lower()
        matching_keys = []
        
        for member_key, member_info in self.members_data.items():
            if member_info.get('group', '').lower() == group_lower:
                matching_keys.append(member_key)
        
        return matching_keys
    
    def _find_member_key(self, member_name):
        """Find member key berdasarkan nama"""
        member_lower = member_name.lower()
        matching_keys = []
        
        for member_key, member_info in self.members_data.items():
            if member_info.get('name', '').lower() == member_lower:
                matching_keys.append(member_key)
        
        return matching_keys
    
    
    def generate_card(self, member_name, group_name, rarity=None, photo_num=None):
        """
        Generate kartu trading untuk member
        
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
            
            # Cari member key
            member_key = f"{member_name.lower().replace(' ', '_')}_{group_name.lower().replace(' ', '_')}"
            
            # Load foto member dari URL
            photo_url, photo_filename = self._get_member_photo_url(member_key, photo_num)
            
            if not photo_url:
                logger.error(f"Photo not found for member: {member_key}")
                return None
            
            # Download foto
            if 'drive.google.com' in photo_url:
                idol_photo_original = self._download_image_from_url(photo_url)
            else:
                # Local file fallback
                if os.path.exists(photo_url):
                    idol_photo_original = Image.open(photo_url).convert("RGBA")
                else:
                    idol_photo_original = None
            
            if idol_photo_original is None:
                logger.error(f"Failed to load photo: {photo_url}")
                return None
            
            # Import design functions
            from design_kartu import generate_card_template
            
            # Generate template kartu menggunakan fungsi dari design_kartu
            template = generate_card_template(idol_photo_original, rarity)
            
            return template
            
        except Exception as e:
            logger.error(f"Error generating card: {e}")
            return None
    
    def gacha_random(self):
        """Gacha random member dari semua grup"""
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
            
            # Get rarity
            rarity = self._get_random_rarity()
            
            # Generate card using design_kartu
            card_image = self.generate_card(member_name, group_name, rarity)
            
            if card_image:
                success_msg = f"🎴 **{member_name}** dari **{group_name}**\n"
                success_msg += f"✨ **Rarity:** {rarity}\n"
                success_msg += f"📸 **Photo:** Google Drive\n"
                success_msg += f"🎯 **Random Gacha**"
                
                return card_image, success_msg
            else:
                return None, f"❌ Gagal generate kartu {member_name} dari {group_name}"
                
        except Exception as e:
            logger.error(f"Error in gacha_random: {e}")
            return None, f"❌ Error saat random gacha: {str(e)}"
    
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
            
            # Guaranteed rarity distribution
            guaranteed_rarities = [
                "Common", "Common",           # 2 Common
                "Rare", "Epic",              # 2 Rare/Epic
                random.choice(["Legendary", "FullArt"])  # 1 Legendary/FullArt
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
    
    def gacha_by_group(self, group_name):
        """Gacha member dari grup tertentu"""
        if not self.members_data:
            return None, "❌ Data member tidak tersedia"
        
        try:
            # Cari member dari grup
            group_member_keys = self._get_member_keys_by_group(group_name)
            
            if not group_member_keys:
                return None, f"❌ Grup **{group_name}** tidak ditemukan di database"
            
            # Pilih member random dari grup
            member_key = random.choice(group_member_keys)
            member_info = self.members_data[member_key]
            
            member_name = member_info.get('name', 'Unknown')
            
            # Get photo URL
            photo_url, _ = self._get_member_photo_url(member_key)
            
            if not photo_url:
                return None, f"❌ Foto untuk {member_name} tidak dapat diakses!"
            
            # Get rarity
            rarity = self._get_random_rarity()
            
            # Generate card using design_kartu
            card_image = self.generate_card(member_name, group_name, rarity)
            
            if card_image:
                success_msg = f"🎴 **{member_name}** dari **{group_name}**\n"
                success_msg += f"✨ **Rarity:** {rarity}\n"
                success_msg += f"📸 **Photo:** Google Drive\n"
                success_msg += f"🎯 **Group Gacha:** {group_name}"
                
                return card_image, success_msg
            else:
                return None, f"❌ Gagal generate kartu {member_name} dari {group_name}"
                
        except Exception as e:
            logger.error(f"Error in gacha_by_group: {e}")
            return None, f"❌ Error saat group gacha: {str(e)}"
    
    def gacha_by_member(self, member_name):
        """Gacha kartu member tertentu"""
        if not self.members_data:
            return None, "Data member tidak tersedia"
        
        # Cari member
        member_keys = self._find_member_key(member_name)
        
        if not member_keys:
            return None, f"❌ Member **{member_name}** tidak ditemukan di database"
        
        # Jika ada multiple member dengan nama sama, pilih random
        member_key = random.choice(member_keys)
        member_info = self.members_data[member_key]
        
        group_name = member_info.get('group', 'Unknown')
        
        # Generate kartu
        card = self.generate_card(member_name, group_name)
        
        if card:
            return card, f"🎴 Kamu mendapat kartu **{member_name}** dari **{group_name}**!"
        else:
            return None, f"❌ Gagal generate kartu {member_name} dari {group_name}"
    
    def save_card_temp(self, card_image, prefix="gacha_card"):
        """
        Save kartu ke temporary file untuk Discord
        
        Args:
            card_image: PIL Image object
            prefix: Prefix untuk filename
            
        Returns:
            str: Path ke temporary file atau None jika gagal
        """
        try:
            import tempfile
            import os
            
            # Create temporary file - kembali ke PNG seperti semula
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png', prefix=f"{prefix}_")
            temp_path = temp_file.name
            temp_file.close()
            
            # Save image tanpa optimasi berlebihan - kartu sudah 350x540px
            card_image.save(temp_path, 'PNG')
            
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
                group = str(row.get('Group', '')).strip()
                stage_name = str(row.get('Stage Name', '')).strip()
                full_name = str(row.get('Full Name', '')).strip()
                korean_name = str(row.get('Korean Stage Name', '')).strip()
                
                if not group or not stage_name:
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
                
                if full_name:
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
    
    # Wrapper methods for compatibility with test scripts
    def search_member(self, member_name):
        """Search for members by name using both JSON and CSV data"""
        results = []
        search_name = member_name.lower().strip()
        
        # First try stage name mapping from CSV
        if hasattr(self, 'stage_name_mapping') and search_name in self.stage_name_mapping:
            csv_info = self.stage_name_mapping[search_name]
            member_key = csv_info['member_key']
            
            # Check if member exists in JSON data (has photos)
            if member_key in self.members_data:
                results.append({
                    'member_key': member_key,
                    'name': csv_info['stage_name'],
                    'full_name': csv_info['full_name'],
                    'korean_name': csv_info['korean_name'],
                    'group': csv_info['group']
                })
        
        # Try full name mapping from CSV
        if hasattr(self, 'full_name_mapping') and search_name in self.full_name_mapping:
            csv_info = self.full_name_mapping[search_name]
            member_key = csv_info['member_key']
            
            # Check if not already added and exists in JSON
            if member_key in self.members_data and not any(r['member_key'] == member_key for r in results):
                results.append({
                    'member_key': member_key,
                    'name': csv_info['stage_name'],
                    'full_name': csv_info['full_name'],
                    'korean_name': csv_info['korean_name'],
                    'group': csv_info['group']
                })
        
        # Fallback to original JSON-based search
        if not results:
            member_keys = self._find_member_key(member_name)
            for member_key in member_keys:
                member_info = self.members_data[member_key]
                results.append({
                    'member_key': member_key,
                    'name': member_info.get('stage_name', member_info.get('name', 'Unknown')),
                    'full_name': member_info.get('full_name', ''),
                    'korean_name': member_info.get('korean_name', ''),
                    'group': member_info.get('group', 'Unknown')
                })
        
        return results
    
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
