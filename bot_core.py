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
        """Handle bot ready event with status message"""
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
        
        # Log ke console dan Railway
        logger.logger.info(f"🤖 Bot logged in as {self.bot.user}")
        logger.logger.info(f"📊 Database loaded: {len(self.kpop_df)} K-pop entries")
        logger.logger.info("🟢 Bot is ready and online!")
        
        # Kirim ke channel umum (opsional - bisa diatur channel ID tertentu)
        # Untuk sekarang hanya log, nanti bisa ditambah channel notification
        print(status_message)
    
    def run(self):
        """Start the Discord bot"""
        self.bot.run(self.DISCORD_TOKEN)
