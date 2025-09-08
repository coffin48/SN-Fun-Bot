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
        self.STATUS_CHANNEL_ID = os.getenv("STATUS_CHANNEL_ID")  # Single channel for status messages
        
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
        """Handle bot ready event with Discord status message"""
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
        
        # Log ke Railway
        logger.logger.info(f"🤖 Bot logged in as {self.bot.user}")
        logger.logger.info(f"📊 Database loaded: {len(self.kpop_df)} K-pop entries")
        logger.logger.info("🟢 Bot is ready and online!")
        
        # Kirim status message ke Discord
        try:
            if self.STATUS_CHANNEL_ID:
                # Kirim ke channel yang ditentukan
                channel = self.bot.get_channel(int(self.STATUS_CHANNEL_ID))
                if channel:
                    await channel.send(status_message)
                    logger.logger.info(f"✅ Status message sent to channel: {channel.name}")
                else:
                    logger.logger.warning(f"❌ Channel with ID {self.STATUS_CHANNEL_ID} not found")
                    # Fallback ke auto-detect
                    await self._send_to_any_channel(status_message)
            else:
                logger.logger.info("⚠️ No status channel configured, using auto-detect")
                await self._send_to_any_channel(status_message)
                
        except Exception as e:
            logger.logger.error(f"❌ Failed to send status message: {e}")
            print(status_message)  # Fallback ke console
    
    async def _send_to_any_channel(self, message):
        """Fallback method to send message to any available channel"""
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    await channel.send(message)
                    logger.logger.info(f"✅ Status message sent to {guild.name}#{channel.name}")
                    return
            else:
                continue
            break
    
    def run(self):
        """Start the Discord bot"""
        self.bot.run(self.DISCORD_TOKEN)
