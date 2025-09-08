"""
Commands Module - Menangani semua Discord commands
"""
from discord.ext import commands
import logger
from ai_handler import AIHandler
from data_fetcher import DataFetcher

class CommandsHandler:
    def __init__(self, bot_core):
        self.bot = bot_core.bot
        self.redis_client = bot_core.redis_client
        self.kpop_detector = bot_core.kpop_detector
        
        # Initialize handlers
        self.ai_handler = AIHandler()
        self.data_fetcher = DataFetcher()
        
        # Register commands
        self._register_commands()
    
    def _register_commands(self):
        """Register semua Discord commands"""
        @self.bot.command(name="sn")
        async def sn_command(ctx, *, user_input: str):
            await self._handle_sn_command(ctx, user_input)
    
    async def _handle_sn_command(self, ctx, user_input: str):
        """Handle command !sn"""
        async with ctx.typing():
            # Clear cache command
            if user_input.lower().startswith("clearcache"):
                await self._clear_cache(ctx)
                return
            
            # Deteksi K-pop member/group dengan SmartDetector
            category, detected_name, multiple_matches = self.kpop_detector.detect(user_input)
            logger.log_sn_command(ctx.author, user_input, category, detected_name)
            
            # Proses berdasarkan kategori
            if category == "MULTIPLE":
                await self._handle_multiple_matches(ctx, detected_name, multiple_matches)
            elif category in ["GROUP", "MEMBER", "MEMBER_GROUP"]:
                await self._handle_kpop_query(ctx, category, detected_name)
            elif category == "OBROLAN":
                await self._handle_casual_conversation(ctx, user_input)
            elif category == "REKOMENDASI":
                await self._handle_recommendation_request(ctx, user_input)
            else:
                await self._handle_general_query(ctx, user_input)
    
    async def _clear_cache(self, ctx):
        """Clear Redis cache"""
        self.redis_client.flushdb()
        await ctx.send("Redis cache berhasil dihapus.")
    
    async def _handle_kpop_query(self, ctx, category, detected_name):
        """Handle K-pop related queries"""
        cache_key = f"{category}:{detected_name.lower()}"
        
        # Cek cache terlebih dahulu
        cached_summary = self.redis_client.get(cache_key)
        if cached_summary:
            summary = cached_summary.decode("utf-8")
            logger.log_cache_hit(category, detected_name)
        else:
            # Enhanced query dengan group info untuk scraping yang lebih akurat
            enhanced_query = self._build_enhanced_query(category, detected_name)
            
            # Log mulai scraping untuk Railway log explorer
            logger.logger.info(f"🔍 Starting scraping process for {category}: {detected_name}")
            logger.logger.info(f"🎯 Enhanced query: {enhanced_query}")
            
            # Fetch info dari berbagai sumber dengan enhanced query
            info = await self.data_fetcher.fetch_kpop_info(enhanced_query)
            if not info.strip():
                logger.logger.warning(f"❌ No scraping data found for {category}: {detected_name}")
                await ctx.send("Maaf, info K-pop tidak ditemukan.")
                return
            
            logger.logger.info(f"✅ Scraping completed for {category}: {detected_name} - {len(info)} characters retrieved")
            
            # Generate AI summary
            try:
                summary = await self.ai_handler.generate_kpop_summary(category, info)
                
                # Simpan ke Redis cache
                self.redis_client.set(cache_key, summary, ex=86400)  # 24 jam
                logger.log_cache_set(category, detected_name)
                
            except Exception as e:
                logger.logger.error(f"Gagal membuat ringkasan: {e}")
                await ctx.send(f"Gagal membuat ringkasan: {e}")
                return
        
        # Kirim ke Discord (chunk <=2000 karakter)
        await self._send_chunked_message(ctx, summary)
    
    async def _handle_casual_conversation(self, ctx, user_input):
        """Handle obrolan casual"""
        try:
            summary = await self.ai_handler.handle_general_query(user_input)
            await ctx.send(summary)
            logger.logger.info(f"OBROLAN request processed: {user_input}")
        except Exception as e:
            logger.logger.error(f"Gagal memproses obrolan: {e}")
            await ctx.send(f"Maaf, terjadi error: {e}")
    
    async def _handle_recommendation_request(self, ctx, user_input):
        """Handle request rekomendasi - langsung AI tanpa cache"""
        try:
            # Langsung AI response dengan max_tokens terbatas
            summary = await self.ai_handler.chat_async(user_input, max_tokens=1500)
            
            # Kirim dalam chunks untuk menghindari Discord limit
            await self._send_chunked_message(ctx, summary)
            logger.logger.info(f"REKOMENDASI request processed: {user_input}")
        except Exception as e:
            logger.logger.error(f"Gagal memproses rekomendasi: {e}")
            await ctx.send(f"Maaf, terjadi error: {e}")
    
    async def _handle_general_query(self, ctx, user_input):
        """Handle pertanyaan umum lainnya"""
        try:
            summary = await self.ai_handler.handle_general_query(user_input)
            await ctx.send(summary)
            logger.logger.info(f"GENERAL request processed: {user_input}")
        except Exception as e:
            logger.logger.error(f"Gagal memproses pertanyaan umum: {e}")
            await ctx.send(f"Maaf, terjadi error: {e}")
    
    async def _handle_multiple_matches(self, ctx, detected_name, multiple_matches):
        """Handle multiple matches untuk nama ambiguous"""
        if len(multiple_matches) <= 1:
            return
        
        # Format pesan dengan pilihan
        message = f"Ada {len(multiple_matches)} {detected_name} nih! 🤔\n\n"
        for i, (name, category) in enumerate(multiple_matches, 1):
            message += f"{i}. {name}\n"
        
        message += f"\nKamu bisa spesifik dengan format: `!sn {detected_name} [nama grup]`"
        await ctx.send(message)
    
    def _build_enhanced_query(self, category, detected_name):
        """Build enhanced query dengan semua nama variations untuk scraping yang lebih komprehensif"""
        try:
            if category == "MEMBER":
                # Cari semua info dari database untuk member
                member_rows = self.kpop_df[self.kpop_df['Stage Name'].str.lower() == detected_name.lower()]
                if len(member_rows) > 0:
                    row = member_rows.iloc[0]
                    
                    # Kumpulkan semua nama variations
                    names = []
                    stage_name = str(row.get('Stage Name', '')).strip()
                    full_name = str(row.get('Full Name', '')).strip()
                    korean_name = str(row.get('Korean Stage Name', '')).strip()
                    group = str(row.get('Group', '')).strip()
                    
                    if stage_name:
                        names.append(stage_name)
                    if full_name and full_name != stage_name and full_name != 'nan':
                        names.append(full_name)
                    if korean_name and korean_name != stage_name and korean_name != 'nan':
                        names.append(korean_name)
                    
                    # Format: "Stage Name Full Name Korean Name from Group"
                    if group:
                        names_str = " ".join(names)
                        return f"{names_str} from {group}"
                    else:
                        return " ".join(names)
                        
            elif category == "GROUP":
                # Untuk group, scraping group saja
                return detected_name
                
            elif category == "MEMBER_GROUP":
                # Extract member name dari format "Member from Group"
                if " from " in detected_name:
                    member_part = detected_name.split(" from ")[0]
                    group_part = detected_name.split(" from ")[1]
                    
                    # Cari semua nama variations untuk member ini
                    member_rows = self.kpop_df[
                        (self.kpop_df['Stage Name'].str.lower() == member_part.lower()) &
                        (self.kpop_df['Group'].str.lower() == group_part.lower())
                    ]
                    
                    if len(member_rows) > 0:
                        row = member_rows.iloc[0]
                        
                        # Kumpulkan semua nama variations
                        names = []
                        stage_name = str(row.get('Stage Name', '')).strip()
                        full_name = str(row.get('Full Name', '')).strip()
                        korean_name = str(row.get('Korean Stage Name', '')).strip()
                        
                        if stage_name:
                            names.append(stage_name)
                        if full_name and full_name != stage_name and full_name != 'nan':
                            names.append(full_name)
                        # Include Korean name untuk scraping yang lebih komprehensif
                        if korean_name and korean_name != stage_name and korean_name != 'nan':
                            names.append(korean_name)
                        
                        names_str = " ".join(names)
                        return f"{names_str} from {group_part}"
                
                # Fallback ke detected_name original
                return detected_name
                
        except Exception as e:
            logger.logger.error(f"Error building enhanced query: {e}")
        
        # Fallback ke detected_name original
        return detected_name
    
    async def _send_chunked_message(self, ctx, message):
        """Kirim pesan dalam chunk <=2000 karakter"""
        chunk_size = 2000
        for i in range(0, len(message), chunk_size):
            chunk = message[i:i+chunk_size]
            await ctx.send(chunk)
