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
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math
import tempfile
import logging
from design_kartu import *

# Setup logger
logger = logging.getLogger(__name__)

class KpopGachaSystem:
    def __init__(self, json_path="Path Foto_Fixed.json", database_path="Database/DATABASE_KPOP (1).csv"):
        """
        Initialize Kpop Gacha System
        
        Args:
            json_path: Path ke JSON mapping foto yang sudah diperbaiki
            database_path: Path ke database K-pop CSV (backup)
        """
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
        
        # Load database sebagai backup
        self._load_database()
        
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
            self.df = pd.read_csv(self.database_path)
            logger.info(f"Backup database loaded: {len(self.df)} members")
        except Exception as e:
            logger.error(f"Failed to load backup database: {e}")
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
            
            # Load font
            try:
                font = ImageFont.truetype(font_path, font_size)
            except:
                font = ImageFont.load_default()
                logger.warning("Using default font, Gill Sans not found")
            
            if rarity != "FullArt":
                # Generate kartu normal dengan border dan background
                template = Image.new("RGBA", (CARD_W, CARD_H), (255,255,255,255))
                draw = ImageDraw.Draw(template)
                
                # Gradient border
                draw_gradient_border(draw, [0,0,CARD_W,CARD_H], 
                                   BORDER_WIDTH, rarity_gradients[rarity])
                
                # Background termasuk area teks rarity
                template = draw_rectangular_radial_bg(template,
                    [BG_XY[0], BG_XY[1], BG_XY[0]+BG_W, BG_XY[1]+BG_H+TEXT_HEIGHT],
                    bg_colors[rarity][0], bg_colors[rarity][1])
                
                # Paste area art
                idol_photo = resize_cover(idol_photo_original, ART_W, ART_H)
                template.paste(idol_photo, ART_XY, idol_photo)
                
                # Tulis teks rarity
                if rarity in ["Common", "Rare"]:
                    # Bawah kiri
                    text_x = ART_XY[0] + 5
                    text_y = ART_XY[1] + ART_H + 5
                else:
                    # Atas kanan
                    bbox = font.getbbox(rarity)
                    text_w = bbox[2] - bbox[0]
                    text_x = CARD_W - text_w - 10
                    text_y = 10
                
                draw.text((text_x, text_y), rarity, fill=(255,255,255), font=font)
                
            else:
                # Full Art: holo + sparkle overlay
                template = resize_cover(idol_photo_original, CARD_W, CARD_H)
                template = template.convert("RGBA")
                template = add_fullart_final(template)
            
            return template
            
        except Exception as e:
            logger.error(f"Error generating card: {e}")
            return None
    
    def gacha_random(self):
        """Gacha random member dari semua grup"""
        if not self.members_data:
            return None, "Data member tidak tersedia"
        
        # Pilih member random dari JSON
        member_key = random.choice(self._get_all_member_keys())
        member_info = self.members_data[member_key]
        
        member_name = member_info.get('name', 'Unknown')
        group_name = member_info.get('group', 'Unknown')
        
        # Generate kartu
        card = self.generate_card(member_name, group_name)
        
        if card:
            return card, f"🎴 Kamu mendapat kartu **{member_name}** dari **{group_name}**!"
        else:
            return None, f"❌ Gagal generate kartu {member_name} dari {group_name}"
    
    def gacha_by_group(self, group_name):
        """Gacha member dari grup tertentu"""
        if not self.members_data:
            return None, "Data member tidak tersedia"
        
        # Cari member dari grup
        group_member_keys = self._get_member_keys_by_group(group_name)
        
        if not group_member_keys:
            return None, f"❌ Grup **{group_name}** tidak ditemukan di database"
        
        # Pilih member random dari grup
        member_key = random.choice(group_member_keys)
        member_info = self.members_data[member_key]
        
        member_name = member_info.get('name', 'Unknown')
        
        # Generate kartu
        card = self.generate_card(member_name, group_name)
        
        if card:
            return card, f"🎴 Kamu mendapat kartu **{member_name}** dari **{group_name}**!"
        else:
            return None, f"❌ Gagal generate kartu {member_name} dari {group_name}"
    
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
    
    def save_card_temp(self, card_image):
        """
        Save kartu ke temporary file untuk Discord
        
        Returns:
            Path ke temporary file
        """
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            card_image.save(temp_file.name, 'PNG')
            return temp_file.name
        except Exception as e:
            logger.error(f"Error saving temp card: {e}")
            return None
