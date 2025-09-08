"""
Bot Core Module - Inisialisasi dan konfigurasi Discord bot
"""
import discord
from discord.ext import commands
import os
import pandas as pd
import redis
import logger
from patch.smart_detector import SmartKPopDetector

class BotCore:
    def __init__(self):
        # Environment Variables
        self.DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
        self.KPOP_CSV_ID = os.getenv("KPOP_CSV_ID")
        self.REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
        
        # Redis connection
        self.redis_client = redis.from_url(self.REDIS_URL)
        
        # Load K-pop database
        self.kpop_df = self._load_kpop_database()
        
        # Initialize K-pop detector
        self.kpop_detector = SmartKPopDetector(self.kpop_df)
        
        # Initialize Discord bot
        self.bot = self._create_bot()
    
    def _load_kpop_database(self):
        """Load K-pop database from CSV"""
        KPOP_CSV_URL = f"https://drive.google.com/uc?export=download&id={self.KPOP_CSV_ID}"
        try:
            kpop_df = pd.read_csv(KPOP_CSV_URL)
            logger.log_csv_loaded(kpop_df)
            return kpop_df
        except Exception as e:
            logger.logger.error(f"Gagal load CSV K-pop: {e}")
            return pd.DataFrame()
    
    def _create_bot(self):
        """Create and configure Discord bot"""
        intents = discord.Intents.default()
        intents.message_content = True
        return commands.Bot(
            command_prefix="!", 
            intents=intents, 
            description="SN Fun Bot K-pop Hybrid"
        )
    
    def run(self):
        """Start the Discord bot"""
        self.bot.run(self.DISCORD_TOKEN)
