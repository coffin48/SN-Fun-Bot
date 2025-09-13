"""
Bot Core Module - Menangani inisialisasi bot dan konfigurasi utama
"""
import os
import discord
from discord.ext import commands
import pandas as pd
import redis
from core.logger import logger
from patch.smart_detector import SmartKPopDetector
from features.analytics.analytics import BotAnalytics
from features.analytics.database_manager import DatabaseManager
from features.social_media.social_media_monitor import SocialMediaMonitor

class BotCore:
    def __init__(self):
        # Environment Variables
        self.DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
        self.KPOP_CSV_ID = os.getenv("KPOP_CSV_ID")
        self.REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.STATUS_CHANNEL_ID = os.getenv("STATUS_CHANNEL_ID")  # Single channel for status messages
        
        # Redis connection
        self.redis_client = redis.from_url(self.REDIS_URL)
        
        # Initialize Database Manager (PostgreSQL + CSV fallback)
        self.db_manager = DatabaseManager()
        
        # Load K-pop database (fallback untuk compatibility)
        self.kpop_df = self._get_legacy_dataframe()
        
        # Initialize K-pop detector
        self.kpop_detector = SmartKPopDetector(self.kpop_df)
        
        # Initialize Discord bot
        self.bot = self._create_bot()
        
        # Initialize Social Media Monitor
        self.social_monitor = SocialMediaMonitor(self)
        self.social_monitor.redis_client = self.redis_client
    
    def _get_legacy_dataframe(self):
        """Get legacy DataFrame format untuk compatibility dengan SmartKPopDetector"""
        # Prioritas: CSV fallback dari DatabaseManager
        if hasattr(self.db_manager, 'kpop_df') and self.db_manager.kpop_df is not None and not self.db_manager.kpop_df.empty:
            logger.info(f"Using CSV DataFrame: {len(self.db_manager.kpop_df)} records")
            return self.db_manager.kpop_df
        
        # Jika PostgreSQL, convert ke DataFrame format
        try:
            members = self.db_manager.search_members("", limit=10000)  # Get all members
            if members:
                df_data = []
                for member in members:
                    df_data.append({
                        'Stage Name': member.get('stage_name', ''),
                        'Group': member.get('group_name', ''),
                        'Korean Stage Name': member.get('korean_stage_name', ''),
                        'Full Name': member.get('full_name', ''),
                        'Date of Birth': member.get('date_of_birth', ''),
                        'Instagram': member.get('instagram', '')
                    })
                df = pd.DataFrame(df_data)
                logger.info(f"Converted PostgreSQL to DataFrame: {len(df)} records")
                return df
        except Exception as e:
            logger.error(f"Error converting PostgreSQL to DataFrame: {e}")
        
        # Emergency fallback - GitHub CSV
        try:
            github_url = "https://raw.githubusercontent.com/coffin48/SN-Fun-Bot/main/Database/DATABASE_KPOP%20(1).csv"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            import requests
            from io import StringIO
            response = requests.get(github_url, headers=headers)
            response.raise_for_status()
            df = pd.read_csv(StringIO(response.text))
            logger.info(f"Emergency GitHub CSV fallback: {len(df)} records")
            return df
        except Exception as e:
            logger.error(f"Emergency GitHub CSV fallback failed: {e}")
        
        # Environment variable fallback
        try:
            if self.KPOP_CSV_ID:
                csv_url = f"https://docs.google.com/spreadsheets/d/{self.KPOP_CSV_ID}/export?format=csv&gid=0"
                response = requests.get(csv_url, headers=headers)
                response.raise_for_status()
                df = pd.read_csv(StringIO(response.text))
                logger.info(f"Environment CSV fallback: {len(df)} records")
                return df
        except Exception as e:
            logger.error(f"Environment CSV fallback failed: {e}")
        
        # Final fallback - local CSV file
        try:
            df = pd.read_csv("Database/DATABASE_KPOP (1).csv")
            logger.info(f"Local CSV emergency fallback: {len(df)} records")
            return df
        except Exception as e:
            logger.error(f"Local CSV emergency fallback failed: {e}")
        
        logger.warning("No data source available - using empty DataFrame")
        return pd.DataFrame()
    
    def _load_kpop_database(self):
        """Legacy method - kept for compatibility"""
        return self._get_legacy_dataframe()
    
    def _create_bot(self):
        """Create and configure Discord bot"""
        intents = discord.Intents.default()
        intents.message_content = True
        bot = commands.Bot(
            command_prefix="!", 
            intents=intents, 
            description="SN Fun Bot K-pop Hybrid"
        )
        
        # Add on_ready event
        @bot.event
        async def on_ready():
            await self._on_bot_ready()
        
        return bot
    
    async def _on_bot_ready(self):
        """Handle bot ready event with Discord status message"""
        try:
            import random
            
            # Variasi pesan bot ready
            ready_messages = [
                "🟢 **Bot Ready!** SN Fun Bot siap melayani K-pop lovers! 🎵",
                "✅ **Online!** Bot K-pop terfavorit sudah aktif! 🌟",
                "🚀 **Ready to Rock!** SN Fun Bot siap dengan database K-pop terbaru! 💫",
                "🎯 **Bot Active!** Siap kasih info K-pop terlengkap! 🔥",
                "💚 **All Systems Go!** Bot K-pop hybrid sudah standby! ⚡",
                "🌈 **Bot Online!** Ready untuk adventure K-pop bareng kalian! 🎪",
                "⭐ **Status: Ready!** SN Fun Bot loaded dengan 5-category detection! 🤖"
            ]
            
            # Pilih pesan random
            status_message = random.choice(ready_messages)
            
            # Log basic ready info first
            logger.info(f"🤖 Bot logged in as {self.bot.user}")
            logger.info("🟢 Bot is ready and online!")
            
            # Get database stats safely
            try:
                db_stats = self.db_manager.get_database_stats()
                logger.info(f"📊 Database: {db_stats['source']} - {db_stats['total_members']} members, {db_stats['total_groups']} groups")
            except Exception as db_error:
                logger.warning(f"⚠️ Could not get database stats: {db_error}")
                logger.info("📊 Database: Using fallback mode")
            
            # Kirim status message ke Discord
            try:
                if self.STATUS_CHANNEL_ID:
                    # Kirim ke channel yang ditentukan
                    channel = self.bot.get_channel(int(self.STATUS_CHANNEL_ID))
                    if channel:
                        await channel.send(status_message)
                        logger.info(f"✅ Status message sent to channel: {channel.name}")
                    else:
                        logger.warning(f"❌ Channel with ID {self.STATUS_CHANNEL_ID} not found")
                        # Fallback ke auto-detect
                        await self._send_to_any_channel(status_message)
                else:
                    logger.info("⚠️ No status channel configured, using auto-detect")
                    await self._send_to_any_channel(status_message)
                    
            except Exception as discord_error:
                logger.error(f"❌ Failed to send Discord status message: {discord_error}")
                print(status_message)  # Fallback ke console
                
        except Exception as e:
            logger.error(f"❌ Critical error in _on_bot_ready: {e}")
            logger.info("🟢 Bot startup completed despite errors")
    
    async def _send_to_any_channel(self, message):
        """Fallback method to send message to any available channel"""
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    await channel.send(message)
                    logger.info(f"✅ Status message sent to {guild.name}#{channel.name}")
                    return
            else:
                continue
            break
    
    def run(self):
        """Start the Discord bot"""
        self.bot.run(self.DISCORD_TOKEN)
