"""
Commands Module - Menangani semua Discord commands
"""
import asyncio
import redis
from logger import logger
import time
import random
import discord
from ai_handler import AIHandler
from data_fetcher import DataFetcher
from analytics import analytics
from social_media_commands import SocialMediaCommandsHandler
from bias_commands import BiasCommandsHandler

class CommandsHandler:
    def __init__(self, bot_core):
        self.bot = bot_core.bot
        self.redis_client = bot_core.redis_client
        self.kpop_detector = bot_core.kpop_detector
        self.kpop_df = bot_core.kpop_df  # Add access to dataframe
        self.db_manager = bot_core.db_manager  # Add access to DatabaseManager
        self.social_monitor = bot_core.social_monitor  # Add access to social media monitor
        
        # Initialize handlers
        self.ai_handler = AIHandler()
        # DataFetcher will be lazy loaded when needed
        
        # Initialize social media commands handler
        self.social_media_handler = SocialMediaCommandsHandler(self.social_monitor)
        
        # Initialize bias detector first
        from bias_detector import BiasDetector
        self.bias_detector = BiasDetector(self.ai_handler, self.kpop_df)
        
        # Initialize bias commands handler
        self.bias_handler = BiasCommandsHandler(self.bias_detector, self.ai_handler, self.kpop_df)
        
        # Conversation memory untuk obrolan santai (per user)
        self.conversation_memory = {}  # {user_id: [messages]}
        self.max_memory_length = 3  # Simpan 3 pesan terakhir
        
        # Anti-duplicate response system
        self.processing_messages = set()  # Track messages being processed
        
        # Register commands
        self._register_commands()
    
    def _register_commands(self):
        """Register semua Discord commands"""
        @self.bot.command(name="sn")
        async def sn_command(ctx, *, user_input: str):
            await self._handle_sn_command(ctx, user_input)
    
    async def _handle_sn_command(self, ctx, user_input: str):
        """Handle command !sn"""
        # Create unique message ID untuk prevent duplicates
        message_id = f"{ctx.author.id}:{ctx.message.id}:{user_input}"
        
        # Check if already processing this message
        if message_id in self.processing_messages:
            return  # Skip duplicate processing
        
        # Add to processing set
        self.processing_messages.add(message_id)
        
        try:
            async with ctx.typing():
                try:
                    # Clear cache command
                    if user_input.lower().startswith("clearcache") or user_input.lower().startswith("clear cache"):
                        await self._clear_cache(ctx)
                        return
                    
                    # Help command
                    if user_input.lower().startswith("help"):
                        await self._handle_help_command(ctx)
                        return
                    
                    # Analytics command
                    if user_input.lower().startswith("analytics"):
                        await self._handle_analytics_command(ctx)
                        return
                    
                    # Database status command
                    if user_input.lower().startswith("db status") or user_input.lower().startswith("database"):
                        await self._handle_database_status(ctx)
                        return
                    
                    # Monitor command (social media monitoring)
                    if user_input.lower().startswith("monitor"):
                        # Parse monitor subcommand: "monitor start", "monitor stop", etc.
                        parts = user_input.split()
                        action = parts[1] if len(parts) > 1 else None
                        platform = parts[2] if len(parts) > 2 else None
                        await self._handle_monitor_command(ctx, action, platform)
                        return
                    
                    # Bias detector commands
                    if user_input.lower().startswith(("bias", "match", "fortune", "ramalan")):
                        await self.bias_handler.handle_bias_command(ctx, user_input)
                        return
                    
                    # Social media commands
                    if user_input.lower().startswith(("twitter", "youtube", "instagram", "tiktok", "sosmed")):
                        await self.social_media_handler.handle_social_command(ctx, user_input)
                        return
                    
                    # Deteksi K-pop member/group dengan SmartDetector (dengan conversation context)
                    start_time = time.time()
                    conversation_context = self._get_recent_conversation_context(ctx.author.id)
                    category, detected_name, multiple_matches = self.kpop_detector.detect(user_input, conversation_context)
                    detection_time = int((time.time() - start_time) * 1000)
                    
                    # Log dengan format yang rapi
                    from logger import log_sn_command, log_detection, log_performance, log_transition
                    log_sn_command(ctx.author, user_input, category, detected_name)
                    log_detection(user_input, category, detected_name)
                    log_performance("Detection", detection_time)
                    
                    # Log transition jika ada context
                    if conversation_context:
                        log_transition(conversation_context, user_input, category)
                    
                    # Proses berdasarkan kategori
                    if category == "MEMBER" or category == "GROUP" or category == "MEMBER_GROUP":
                        # Reset conversation memory untuk K-pop queries
                        self._clear_user_memory(ctx.author.id)
                        await self._handle_kpop_query(ctx, category, detected_name)
                    elif category == "MULTIPLE":
                        self._clear_user_memory(ctx.author.id)
                        await self._handle_multiple_matches(ctx, detected_name, multiple_matches)
                    elif category == "REKOMENDASI":
                        self._clear_user_memory(ctx.author.id)
                        await self._handle_recommendation_request(ctx, user_input)
                    elif category == "OBROLAN":
                        await self._handle_casual_conversation(ctx, user_input)
                    else:
                        await self._handle_general_query(ctx, user_input)
                        
                except Exception as e:
                    # Log error dengan detail lengkap
                    logger.error(f"❌ Error in _handle_sn_command: {e}")
                    logger.error(f"   User: {ctx.author} | Input: '{user_input}'")
                    import traceback
                    logger.error(f"   Traceback: {traceback.format_exc()}")
                    
                    # Send user-friendly error message
                    await ctx.send("❌ Maaf, terjadi error saat memproses command. Tim teknis sudah diberitahu! 🔧")
                    
                    # Log ke analytics untuk monitoring
                    analytics.log_error("SN_COMMAND_ERROR", str(e), user_input)
        finally:
            # Remove from processing set when done
            self.processing_messages.discard(message_id)
            
            # Cleanup processing messages if too many
            if len(self.processing_messages) > 50:
                await self._cleanup_processing_messages()
    
    async def _clear_cache(self, ctx):
        """Clear Redis cache"""
        self.redis_client.flushdb()
        await ctx.send("Redis cache berhasil dihapus.")
    
    async def _handle_kpop_query(self, ctx, category, detected_name):
        """Handle K-pop related queries"""
        start_time = time.time()
        analytics.track_daily_usage()
        
        # Enhanced cache key untuk akurasi lebih tinggi
        enhanced_query = self._build_enhanced_query(category, detected_name)
        cache_key = f"{category}:{detected_name.lower()}:{hash(enhanced_query)}"
        
        # Kirim loading message terlebih dahulu
        loading_msg = await self._send_loading_message(ctx)
            
        # Cek cache terlebih dahulu
        try:
            cached_summary = self.redis_client.get(cache_key)
            if cached_summary:
                summary = cached_summary.decode("utf-8")
                from logger import log_cache_hit
                log_cache_hit(category, detected_name)
                
                # Update loading message untuk cache hit
                await loading_msg.edit(content="⚡ Mengambil dari cache...")
                return await self._send_kpop_embed(ctx, loading_msg, category, detected_name, summary)
        except Exception as e:
            logger.error(f"Error accessing Redis cache: {e}")
            await loading_msg.edit(content="⚠️ Gagal mengakses cache. Mencoba mengambil data langsung...")
        
        # Initialize summary with default fallback value
        summary = f"**{detected_name}**\n\nInformasi tidak tersedia sementara."
        
        # Log scraping start dengan info lengkap
        scraping_start = time.time()
        logger.info(f"🔍 Scraping {category}: {detected_name} | Enhanced: {enhanced_query}")
        
        # Try enhanced query first
        if enhanced_query != detected_name:
            logger.info(f"🎯 Enhanced query: {enhanced_query}")
            info = await self.data_fetcher.fetch_kpop_info(enhanced_query)
            
            if not info.strip():
                # Fallback to simple query
                logger.info(f"⚠️ Enhanced query failed, trying simple query: {detected_name}")
                info = await self.data_fetcher.fetch_kpop_info(detected_name)
                
                if not info.strip():
                    logger.warning(f"❌ Both enhanced and simple queries failed for {category}: {detected_name}")
                    await self._handle_query_error(loading_msg, "not_found")
                    self._track_failed_query(category, detected_name)
                    return
                
                # Track as simple query success
                from logger import log_performance
                log_performance("QuerySuccess", 0, f"Simple query success: {detected_name}")
            else:
                # Track as enhanced query success
                from logger import log_performance
                log_performance("QuerySuccess", 0, f"Enhanced query success: {detected_name}")
        else:
            info = await self.data_fetcher.fetch_kpop_info(detected_name)
        
        # Calculate scraping time
        scraping_time = int((time.time() - scraping_start) * 1000)  # Convert to milliseconds
        
        logger.info(f"✅ Scraping completed for {category}: {detected_name} - {len(info)} characters retrieved")
        
        # Update loading message for AI processing
        await loading_msg.edit(content="🤖 Membuat ringkasan dengan AI...")
        
        # Generate AI summary with proper error handling
        ai_start = time.time()
        
        try:
            # First try to generate summary with AI
            ai_summary = await self.ai_handler.generate_kpop_summary(category, info)
            
            if ai_summary and ai_summary.strip():
                summary = ai_summary
            else:
                logger.warning("AI returned empty summary, using fallback")
                # Fallback to basic info if AI fails
                summary = f"**{detected_name}**\n\n"
                
                # Handle different categories
                if category == "MEMBER":
                    if isinstance(info, dict):
                        summary += f"Adalah member dari grup {info.get('group', 'tidak diketahui')}. "
                        summary += info.get('description', 'Tidak ada deskripsi tersedia.')
                    else:
                        summary += f"Informasi member {detected_name} tidak ditemukan."
                elif category == "GROUP":
                    if isinstance(info, str):
                        summary += info
                    else:
                        summary += f"Informasi grup {detected_name} tidak ditemukan."
                else:  # MEMBER_GROUP or others
                    summary += "Informasi tidak tersedia."
            
            ai_time = time.time() - ai_start
            analytics.track_response_time("ai_generation", ai_time)
            
            # Smart cache duration berdasarkan kategori
            try:
                cache_duration = self._get_cache_duration(category, len(str(summary)))
                self.redis_client.set(cache_key, summary, ex=cache_duration)
                from logger import log_cache_set
                log_cache_set(category, detected_name)
            except Exception as cache_error:
                logger.error(f"Gagal menyimpan ke cache: {cache_error}")
                
        except Exception as e:
            logger.error(f"Gagal membuat ringkasan: {e}")
            # Fallback to basic info on error
            summary = f"**{detected_name}**\n\n"
            
            # Handle different categories in error case
            try:
                if category == "MEMBER":
                    if isinstance(info, dict):
                        summary += f"Adalah member dari grup {info.get('group', 'tidak diketahui')}. "
                        summary += info.get('description', 'Tidak ada deskripsi tersedia.')
                    else:
                        summary += f"Informasi member {detected_name} tidak ditemukan."
                elif category == "GROUP":
                    if isinstance(info, str):
                        summary += info
                    else:
                        summary += f"Informasi grup {detected_name} tidak ditemukan."
                else:  # MEMBER_GROUP or others
                    summary += "Informasi tidak tersedia."
            except Exception as inner_e:
                logger.error(f"Error saat membuat fallback summary: {inner_e}")
                summary = f"**{detected_name}**\n\nMaaf, terjadi kesalahan saat memproses permintaan. Silakan coba lagi nanti."
            
            # Log the error but continue with fallback content
            await loading_msg.edit(content="⚠️ Sedang menggunakan data dasar...")
            await asyncio.sleep(1)  # Give user time to see the message
        
        # Track total response time
        total_time = time.time() - start_time
        analytics.track_response_time("total_response", total_time)
        
        # Scrape image untuk embed
        image_data = None
        try:
            await loading_msg.edit(content="🖼️ Mencari foto...")
            image_data = await self.data_fetcher.scrape_kpop_image(detected_name)
        except Exception as e:
            logger.debug(f"Image scraping failed: {e}")
        
        # Send dengan embed dan foto (tanpa URL link)
        await self._send_kpop_embed(ctx, loading_msg, category, detected_name, summary, image_data)
    
    @property
    def data_fetcher(self):
        """Lazy initialization of DataFetcher"""
        if not hasattr(self, '_data_fetcher'):
            self._data_fetcher = DataFetcher(self.kpop_df)
            logger.info("DataFetcher initialized lazily")
        return self._data_fetcher
    
    async def _send_loading_message(self, ctx):
        """Send random loading message and return message object"""
        messages = [
            "🔍 Mencari informasi K-pop...",
            "📊 Mengumpulkan data dari berbagai sumber...",
            "🎵 Sedang scraping info K-pop...",
            "⏳ Tunggu sebentar, sedang mencari info...",
            "🚀 Processing query K-pop..."
        ]
        return await ctx.send(random.choice(messages))
    
    async def _handle_query_error(self, loading_msg, error_type, error_details=None):
        """Centralized error handling with consistent messaging"""
        error_messages = {
            "not_found": "❌ Maaf, info K-pop tidak ditemukan.",
            "ai_failed": f"❌ Gagal membuat ringkasan: {error_details}",
            "scraping_failed": "❌ Gagal mengumpulkan data K-pop.",
            "network_error": "❌ Koneksi bermasalah, coba lagi nanti.",
            "timeout": "❌ Request timeout, coba query yang lebih spesifik."
        }
        message = error_messages.get(error_type, f"❌ Error: {error_details}")
        await loading_msg.edit(content=message)
    
    def _get_cache_duration(self, category, content_length):
        """Smart cache duration based on content type and size"""
        base_durations = {
            "GROUP": 86400,      # 24h - Group info stable
            "MEMBER": 43200,     # 12h - Member info semi-stable  
            "MEMBER_GROUP": 21600 # 6h - Specific queries change more
        }
        
        # Longer cache for comprehensive content
        if content_length > 3000:
            return base_durations.get(category, 21600) * 2
        
        return base_durations.get(category, 21600)
    
    def _track_failed_query(self, category, detected_name):
        """Track failed queries for analytics"""
        analytics.track_query_success("enhanced", False, detected_name)
        analytics.track_query_success("simple", False, detected_name)
    
    async def _cleanup_processing_messages(self):
        """Periodic cleanup of old processing messages"""
        if len(self.processing_messages) > 100:
            logger.info(f"Cleaning up {len(self.processing_messages)} processing messages")
            self.processing_messages.clear()
    
    async def _send_kpop_embed(self, ctx, loading_msg, category, detected_name, summary, image_data=None):
        """Send K-pop info dengan embed dan foto tanpa menampilkan URL"""
        # Emoji berdasarkan kategori
        emoji_map = {
            "MEMBER": "👤",
            "GROUP": "🎵", 
            "MEMBER_GROUP": "👥"
        }
        
        # Buat embed dengan warna K-pop theme
        embed = discord.Embed(
            title=f"{emoji_map.get(category, '🎤')} {detected_name}",
            description=summary,
            color=0xFF1493  # Deep pink untuk K-pop theme
        )
        
        # Footer dengan info bot
        embed.set_footer(text="SN Fun Bot • K-pop Information", icon_url=None)
        
        # Jika ada foto, kirim dengan attachment tanpa URL
        if image_data:
            try:
                # Reset BytesIO position
                image_data.seek(0)
                
                # Buat Discord File object dari BytesIO
                file = discord.File(image_data, filename="kpop_image.jpg")
                
                # Set image di embed menggunakan attachment://
                embed.set_thumbnail(url="attachment://kpop_image.jpg")
                
                # Edit loading message dengan embed + foto
                await loading_msg.edit(content="", embed=embed, attachments=[file])
                logger.info(f"✅ Sent embed with image for {detected_name}")
                
            except Exception as e:
                logger.error(f"Failed to send embed with image: {e}")
                # Fallback: kirim embed tanpa foto
                await loading_msg.edit(content="", embed=embed)
        else:
            # Kirim embed tanpa foto
            await loading_msg.edit(content="", embed=embed)
            logger.info(f"✅ Sent embed without image for {detected_name}")
    
    def _add_to_memory(self, user_id, role, message):
        """Tambahkan pesan ke conversation memory"""
        if user_id not in self.conversation_memory:
            self.conversation_memory[user_id] = []
        
        self.conversation_memory[user_id].append({"role": role, "content": message})
        
        # Batasi memory hanya 3 pesan terakhir
        if len(self.conversation_memory[user_id]) > self.max_memory_length * 2:  # *2 karena user+bot
            self.conversation_memory[user_id] = self.conversation_memory[user_id][-self.max_memory_length * 2:]
    
    def _clear_user_memory(self, user_id):
        """Hapus conversation memory untuk user tertentu"""
        if user_id in self.conversation_memory:
            del self.conversation_memory[user_id]
    
    def _get_conversation_context(self, user_id, current_message):
        """Dapatkan konteks percakapan untuk AI"""
        context_messages = []
        
        # Tambahkan pesan sebelumnya jika ada
        if user_id in self.conversation_memory:
            context_messages.extend(self.conversation_memory[user_id])
        
        # Tambahkan pesan saat ini
        context_messages.append({"role": "user", "content": current_message})
        
        # Format untuk AI prompt
        if len(context_messages) <= 1:
            return current_message
        
        # Buat konteks percakapan
        conversation_context = "Konteks percakapan sebelumnya:\n"
        for msg in context_messages[:-1]:  # Semua kecuali pesan terakhir
            role_label = "User" if msg["role"] == "user" else "Bot"
            conversation_context += f"{role_label}: {msg['content']}\n"
        
        conversation_context += f"\nPesan saat ini: {current_message}\n"
        conversation_context += "\nRespond secara natural dan konsisten dengan percakapan sebelumnya:"
        
        return conversation_context
    
    def _get_recent_conversation_context(self, user_id):
        """Get recent conversation context untuk transition detection"""
        if user_id not in self.conversation_memory:
            return None
        
        # Get last 3 messages untuk context
        recent_messages = self.conversation_memory[user_id][-3:]
        if not recent_messages:
            return None
        
        # Combine recent context
        context = ""
        for msg in recent_messages:
            context += f"{msg['content']} "
        
        return context.strip()

    async def _handle_casual_conversation(self, ctx, user_input):
        """Handle obrolan casual dengan memory dan caching"""
        try:
            user_id = ctx.author.id
            
            # Check cache untuk casual conversation
            cache_key = f"casual:{hash(user_input.lower())}"
            cached_response = self.redis_client.get(cache_key)
            
            if cached_response:
                from logger import log_cache_hit
                log_cache_hit("CASUAL", user_input[:30])
                await self._send_chunked_message(ctx, cached_response.decode('utf-8'))
                return
            else:
                from logger import log_cache_miss
                log_cache_miss("CASUAL", user_input[:30])
            
            # Generate response dengan AI (reduced max_tokens untuk speed)
            start_time = time.time()
            from logger import log_ai_request
            log_ai_request("CASUAL", len(user_input))
            summary = await self.ai_handler.chat_async(user_input, max_tokens=800, category="OBROLAN")
            ai_duration = int((time.time() - start_time) * 1000)
            from logger import log_ai_response
            log_ai_response("CASUAL", len(summary) if summary else 0, ai_duration)
            
            # Validasi dan sanitasi response
            if not summary or not isinstance(summary, str):
                summary = "Maaf, saya tidak bisa memahami pertanyaan itu. Coba tanya yang lain ya! 😅"
            
            # Truncate jika terlalu panjang
            if len(summary) > 1900:
                summary = summary[:1900] + "..."
            
            # Cache response untuk 1 jam
            self.redis_client.setex(cache_key, 3600, summary)
            from logger import log_cache_set
            log_cache_set("CASUAL", user_input[:30])
            
            # Kirim dengan chunked message untuk safety
            await self._send_chunked_message(ctx, summary)
            
        except Exception as e:
            logger.log_error("CASUAL_CONV", str(e), user_input)
            await ctx.send("Maaf, ada masalah teknis. Coba lagi nanti ya! 😅")
    
    async def _handle_recommendation_request(self, ctx, user_input):
        """Handle request rekomendasi - langsung AI tanpa cache"""
        try:
            start_time = time.time()
            from logger import log_ai_request
            log_ai_request("RECOMMENDATION", len(user_input))
            
            # Langsung AI response dengan max_tokens terbatas
            summary = await self.ai_handler.chat_async(user_input, max_tokens=1500, category="REKOMENDASI")
            ai_duration = int((time.time() - start_time) * 1000)
            logger.log_ai_response("RECOMMENDATION", len(summary) if summary else 0, ai_duration)
            
            # Kirim dalam chunks untuk menghindari Discord limit
            await self._send_chunked_message(ctx, summary)
            
        except Exception as e:
            logger.log_error("RECOMMENDATION", str(e), user_input)
            await ctx.send("Maaf, ada masalah dalam memberikan rekomendasi. Coba lagi nanti ya! 😅")
    
    async def _handle_general_query(self, ctx, user_input):
        """Handle general queries"""
        try:
            start_time = time.time()
            from logger import log_ai_request
            log_ai_request("GENERAL", len(user_input))
            
            summary = await self.ai_handler.handle_general_query(user_input)
            ai_duration = int((time.time() - start_time) * 1000)
            logger.log_ai_response("GENERAL", len(summary) if summary else 0, ai_duration)
            
            await ctx.send(summary)
            
        except Exception as e:
            logger.log_error("GENERAL_QUERY", str(e), user_input)
            await ctx.send(f"Gagal memproses query: {e}")
    
    async def _handle_help_command(self, ctx):
        """Handle !sn help command untuk menampilkan daftar commands"""
        help_message = """🤖 **SN Fun Bot - K-pop Info** ✨

**🎯 K-pop Info:**
• `!sn [nama]` 🎤 Info K-pop (member/grup)
• `!sn [member] [grup]` 🎭 Info spesifik
• `!sn hai` 💬 Chat casual
• `!sn rekomen lagu` 🎵 Minta rekomendasi

**📝 Contoh K-pop:**
```
!sn QWER
!sn Blackpink  
!sn Hina QWER
!sn rekomen ballad
```

**💕 Bias Detector:**
• `!sn bias` 🎯 Deteksi bias kamu
• `!sn match` 💖 Love matching
• `!sn fortune` 🔮 Ramalan cinta
• `!sn ramalan` ✨ Fortune telling

**📱 Social Media:**
• `!sn twitter` 🐦 Latest tweets
• `!sn youtube` 📺 Latest videos
• `!sn instagram` 📸 Latest posts
• `!sn tiktok` 🎵 Latest TikToks
• `!sn sosmed` 📱 All platforms

**⚙️ Utility:**
• `!sn help` 📋 Help ini
• `!sn analytics` 📊 Statistik bot
• `!sn monitor start/stop` 🔍 Social monitoring
• `!sn db status` 💾 Database status

Bot otomatis deteksi member, grup, atau chat biasa! 🎵✨"""
        await self._send_chunked_message(ctx, help_message)
        logger.info("Help command requested")

    async def _handle_analytics_command(self, ctx):
        """Handle !analytics command untuk view statistics"""
        try:
            summary = analytics.get_analytics_summary()
            await self._send_chunked_message(ctx, summary)
            logger.info("Analytics summary requested")
        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            await ctx.send(f"Error getting analytics: {e}")
    
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
            logger.error(f"Error building enhanced query: {e}")
        
        # Fallback ke detected_name original
        return detected_name
    
    async def _send_chunked_message(self, ctx, message):
        """Kirim pesan dalam chunk <=2000 karakter dengan smart splitting"""
        chunk_size = 1900  # Buffer untuk safety
        
        if len(message) <= chunk_size:
            await ctx.send(message)
            return
        
        # Simple splitting by character count with word boundary respect
        chunks = []
        words = message.split(' ')
        current_chunk = ""
        
        for word in words:
            # Check if adding this word would exceed limit
            test_chunk = current_chunk + ' ' + word if current_chunk else word
            
            if len(test_chunk) <= chunk_size:
                current_chunk = test_chunk
            else:
                # Save current chunk and start new one
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = word
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(current_chunk)
        
        # Send all chunks with logging
        logger.info(f"Sending {len(chunks)} chunks to Discord")
        for i, chunk in enumerate(chunks):
            try:
                if i > 0:
                    await asyncio.sleep(1.0)  # Longer delay between chunks
                logger.info(f"Sending chunk {i+1}/{len(chunks)} - {len(chunk)} characters")
                await ctx.send(chunk)
                logger.info(f"Successfully sent chunk {i+1}/{len(chunks)}")
            except Exception as e:
                logger.error(f"Failed to send chunk {i+1}/{len(chunks)}: {e}")
                # Try to send remaining chunks
                continue
    
    async def _handle_database_status(self, ctx):
        """Handle database status command"""
        try:
            db_stats = self.db_manager.get_database_stats()
            
            status_emoji = {
                'connected': '🟢',
                'fallback': '🟡', 
                'error': '🔴'
            }
            
            emoji = status_emoji.get(db_stats['status'], '⚪')
            
            status_message = f"""
{emoji} **Database Status**

📊 **Source**: {db_stats['source']}
👥 **Total Members**: {db_stats['total_members']:,}
🎵 **Total Groups**: {db_stats['total_groups']:,}
⚡ **Status**: {db_stats['status'].title()}

{self._get_database_performance_info()}
            """.strip()
            
            await ctx.send(status_message)
            
        except Exception as e:
            logger.error(f"Database status error: {e}")
            await ctx.send("❌ Error retrieving database status")
    
    def _get_database_performance_info(self):
        """Get database performance information"""
        if hasattr(self.db_manager, 'engine') and self.db_manager.engine:
            return "🚀 **Performance**: PostgreSQL optimized queries with indexes"
        else:
            return "📊 **Performance**: CSV fallback mode"
    
    async def _handle_monitor_command(self, ctx, action: str = None, platform: str = None):
        """Handle social media monitoring commands"""
        try:
            if not action:
                # Show monitor status
                embed = discord.Embed(
                    title="📱 Secret Number Social Media Monitor",
                    description="Monitor status dan kontrol untuk social media Secret Number",
                    color=0x00ff00
                )
                
                embed.add_field(
                    name="📊 Platforms Monitored",
                    value="• 📸 Instagram (@secretnumber.official)\n• 🐦 Twitter (@5ecretnumber)\n• 📺 YouTube (Secret Number Official)\n• 🎵 TikTok (@secretnumber.official)",
                    inline=False
                )
                
                embed.add_field(
                    name="⚙️ Commands",
                    value="`!monitor start` - Start monitoring\n`!monitor stop` - Stop monitoring\n`!monitor check` - Manual check all\n`!monitor check instagram` - Check specific platform\n`!monitor status` - Show detailed status",
                    inline=False
                )
                
                await ctx.send(embed=embed)
                return
            
            if action.lower() == "start":
                # Start monitoring
                if hasattr(self.social_monitor, 'monitoring_task') and not self.social_monitor.monitoring_task.done():
                    await ctx.send("⚠️ Monitoring sudah berjalan!")
                    return
                
                # Start monitoring task
                self.social_monitor.monitoring_task = asyncio.create_task(self.social_monitor.start_monitoring())
                await ctx.send("✅ Social media monitoring started! Bot akan check update setiap 5 menit.")
                
            elif action.lower() == "stop":
                # Stop monitoring
                if hasattr(self.social_monitor, 'monitoring_task'):
                    self.social_monitor.monitoring_task.cancel()
                    await ctx.send("🛑 Social media monitoring stopped.")
                else:
                    await ctx.send("⚠️ Monitoring tidak sedang berjalan.")
                
            elif action.lower() == "check":
                # Manual check
                await ctx.send("🔍 Checking social media updates...")
                
                async with ctx.typing():
                    result = await self.social_monitor.manual_check(platform)
                    await ctx.send(f"✅ Manual check completed for {platform or 'all platforms'}")
                
            elif action.lower() == "status":
                # Show detailed status
                embed = discord.Embed(
                    title="📊 Monitor Status Detail",
                    color=0x0099ff
                )
                
                # Check if monitoring is running
                is_running = hasattr(self.social_monitor, 'monitoring_task') and not self.social_monitor.monitoring_task.done()
                status = "🟢 Running" if is_running else "🔴 Stopped"
                
                embed.add_field(name="Status", value=status, inline=True)
                embed.add_field(name="Check Interval", value="5 minutes", inline=True)
                embed.add_field(name="Notification Channel", value=f"<#{self.social_monitor.notification_channel_id}>" if self.social_monitor.notification_channel_id else "Not set", inline=True)
                
                # Show last check times from Redis cache
                if self.redis_client:
                    cache_info = []
                    for platform, cache_key in self.social_monitor.cache_keys.items():
                        last_id = self.redis_client.get(cache_key)
                        if last_id:
                            cache_info.append(f"• {platform.title()}: ✅ Cached")
                        else:
                            cache_info.append(f"• {platform.title()}: ⚪ No cache")
                    
                    embed.add_field(
                        name="Cache Status", 
                        value="\n".join(cache_info) if cache_info else "No cache data",
                        inline=False
                    )
                
                await ctx.send(embed=embed)
                
            else:
                await ctx.send("❌ Unknown action. Use: `start`, `stop`, `check`, `status`")
                
        except Exception as e:
            logger.error(f"Monitor command error: {e}")
            await ctx.send(f"❌ Error: {e}")
        else:
            return "📁 **Performance**: CSV fallback mode"
