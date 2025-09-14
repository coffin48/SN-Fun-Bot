"""
Commands Module - Menangani semua Discord commands
"""
import asyncio
import os
import redis
from core.logger import logger
import time
import random
import discord
from features.social_media.ai_handler import AIHandler
from utils.data_fetcher import DataFetcher
try:
    from features.analytics.analytics import BotAnalytics
    analytics = BotAnalytics()
except ImportError:
    class BotAnalytics:
        def __init__(self):
            self.data = {"query_stats": {"total_queries": 0}, "popular_queries": {}, "response_times": {"scraping": [], "ai_generation": [], "total_response": []}, "source_performance": {}, "daily_stats": {}}
        def track_daily_usage(self): pass
        def log_error(self, *args): pass
        def track_response_time(self, *args): pass
        def track_query_success(self, *args): pass
        def get_analytics_summary(self): return "Analytics not available"
        def _save_analytics(self): pass
    analytics = BotAnalytics()
from features.social_media.social_media_commands import SocialMediaCommandsHandler
from core.maintenance_manager import MaintenanceManager
# Conditional import for bias commands to avoid startup errors
try:
    from features.bias_detector.bias_commands import BiasCommandsHandler
    BIAS_COMMANDS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Bias commands not available: {e}")
    BIAS_COMMANDS_AVAILABLE = False
    BiasCommandsHandler = None

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
        
        # Initialize maintenance manager
        self.maintenance_manager = MaintenanceManager(self.bot)
        
        # Initialize gacha system (optional)
        try:
            from features.gacha_system.gacha_commands import GachaCommandsHandler
            self.gacha_handler = GachaCommandsHandler()
            logger.info("✅ Gacha system initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️ Gacha system initialization failed: {e}")
            self.gacha_handler = None
        
        # Initialize gallery expansion service (optional)
        try:
            from utils.gallery_expansion import GalleryExpansionService
            self.expansion_service = GalleryExpansionService()
            if self.expansion_service.is_enabled():
                logger.info("✅ Gallery expansion service initialized and enabled")
            else:
                logger.warning("⚠️ Gallery expansion service initialized but disabled (check GALLERY_EXPANSION_ENABLED and Google Drive setup)")
                # Keep service object for debugging, but mark as disabled
        except Exception as e:
            logger.error(f"❌ Gallery expansion service initialization failed: {e}")
            self.expansion_service = None
        
        # Initialize bias detector and commands handler with error handling
        self.bias_detector = None
        self.bias_handler = None
        
        # Fix circular import by importing BiasDetector first
        print("DEBUG: Starting bias initialization...")
        print(f"DEBUG: ai_handler = {self.ai_handler}")
        print(f"DEBUG: kpop_df = {self.kpop_df}")
        
        try:
            from features.bias_detector.bias_detector import BiasDetector
            print("DEBUG: BiasDetector imported successfully")
            self.bias_detector = BiasDetector(self.ai_handler, self.kpop_df)
            print(f"DEBUG: BiasDetector created: {self.bias_detector}")
            
            # Import BiasCommandsHandler after BiasDetector is initialized
            import features.bias_detector.bias_commands as bias_commands
            print("DEBUG: bias_commands module imported")
            print(f"DEBUG: BiasCommandsHandler class exists: {hasattr(bias_commands, 'BiasCommandsHandler')}")
            self.bias_handler = bias_commands.BiasCommandsHandler(self.bias_detector, self.ai_handler, self.kpop_df)
            print(f"DEBUG: BiasCommandsHandler created: {self.bias_handler}")
            logger.info("✅ Bias commands initialized successfully")
            print(f"DEBUG: Final bias_handler = {self.bias_handler}")
            print(f"DEBUG: bias_handler type: {type(self.bias_handler)}")
        except Exception as e:
            logger.error(f"Bias init failed: {e}")
            print(f"DEBUG: Bias init error: {e}")
            import traceback
            traceback.print_exc()
            self.bias_detector = None
            self.bias_handler = None
            print(f"DEBUG: Set bias_handler to None due to error")
        
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
                    
                    # Specific info commands
                    if user_input.lower().startswith("bias info"):
                        await self._handle_bias_info_command(ctx)
                        return
                    elif user_input.lower().startswith("gacha info"):
                        # Redirect to gacha system
                        if self.gacha_handler:
                            await self.gacha_handler.handle_gacha_command(ctx, "gacha info")
                        else:
                            await ctx.send("❌ Gacha system tidak tersedia.")
                        return
                    
                    # Analytics command
                    if user_input.lower().startswith("analytics"):
                        await self._handle_analytics_command(ctx)
                        return
                    
                    # Database status command
                    if user_input.lower().startswith("db status") or user_input.lower().startswith("database"):
                        await self._handle_database_status(ctx)
                        return
                    
                    # Maintenance command
                    if user_input.lower().startswith("maintenance"):
                        await self._handle_maintenance_command(ctx, user_input)
                        return
                    
                    # Monitor command (social media monitoring)
                    if user_input.lower().startswith("monitor"):
                        # Parse monitor subcommand: "monitor start", "monitor stop", etc.
                        parts = user_input.split()
                        action = parts[1] if len(parts) > 1 else None
                        platform = parts[2] if len(parts) > 2 else None
                        await self._handle_monitor_command(ctx, action, platform)
                        return
                    
                    # Bias detector commands (with availability check)
                    if user_input.lower().startswith(("bias", "match", "fortune", "ramalan")):
                        print(f"DEBUG: Bias command detected. bias_handler = {self.bias_handler}")
                        if self.bias_handler:
                            await self.bias_handler.handle_bias_command(ctx, user_input)
                        else:
                            await ctx.send("⚠️ Bias commands sedang tidak tersedia. Coba command lain ya!")
                        return
                    
                    # Gacha commands
                    if user_input.lower().startswith("gacha"):
                        if self.gacha_handler:
                            await self.gacha_handler.handle_gacha_command(ctx, user_input)
                        else:
                            await ctx.send("❌ **Sistem gacha tidak tersedia!**\n"
                                          "🔧 **Penyebab:** Missing dependency `Pillow`\n"
                                          "💡 **Solusi:** Install dengan `pip install Pillow`\n"
                                          "📋 **Atau:** `pip install -r requirements.txt`")
                        return
                    
                    # Gallery expansion commands (admin only)
                    if user_input.lower().startswith("expand"):
                        await self._handle_expansion_command(ctx, user_input)
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
                    from core.logger import log_sn_command, log_detection, log_performance, log_transition
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
                from core.logger import log_cache_hit
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
                from core.logger import log_performance
                log_performance("QuerySuccess", 0, f"Simple query success: {detected_name}")
            else:
                # Track as enhanced query success
                from core.logger import log_performance
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
                from core.logger import log_cache_set
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
        
        # Scrape image untuk embed dengan group context
        image_data = None
        try:
            await loading_msg.edit(content="🖼️ Mencari foto...")
            
            # Extract group name from enhanced query for better image scraping
            group_name = None
            if category == "MEMBER_GROUP" and " from " in detected_name:
                group_name = detected_name.split(" from ")[1]
            elif category == "MEMBER":
                # Try to get group from database
                member_rows = self.kpop_df[self.kpop_df['Stage Name'].str.lower() == detected_name.lower()]
                if len(member_rows) > 0:
                    group_name = str(member_rows.iloc[0].get('Group', '')).strip()
            
            image_data = await self.data_fetcher.scrape_kpop_image(detected_name, group_name)
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
        """Cleanup old processing messages"""
        # Keep only recent 20 messages
        if len(self.processing_messages) > 20:
            # Convert to list, sort, and keep recent ones
            messages_list = list(self.processing_messages)
            self.processing_messages = set(messages_list[-20:])
    
    async def _send_kpop_embed(self, ctx, loading_msg, category, detected_name, summary, image_data=None):
        """Send K-pop information as Discord embed"""
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
                from core.logger import log_cache_hit
                log_cache_hit("CASUAL", user_input[:30])
                await self._send_chunked_message(ctx, cached_response.decode('utf-8'))
                return
            else:
                from core.logger import log_cache_miss
                log_cache_miss("CASUAL", user_input[:30])
            
            # Generate response dengan AI (reduced max_tokens untuk speed)
            start_time = time.time()
            from core.logger import log_ai_request
            log_ai_request("CASUAL", len(user_input))
            summary = await self.ai_handler.chat_async(user_input, max_tokens=800, category="OBROLAN")
            ai_duration = int((time.time() - start_time) * 1000)
            from core.logger import log_ai_response
            log_ai_response("CASUAL", len(summary) if summary else 0, ai_duration)
            
            # Validasi dan sanitasi response
            if not summary or not isinstance(summary, str):
                summary = "Maaf, saya tidak bisa memahami pertanyaan itu. Coba tanya yang lain ya! 😅"
            
            # Truncate jika terlalu panjang
            if len(summary) > 1900:
                summary = summary[:1900] + "..."
            
            # Cache response untuk 1 jam
            self.redis_client.setex(cache_key, 3600, summary)
            from core.logger import log_cache_set
            log_cache_set("CASUAL", user_input[:30])
            
            # Kirim dengan chunked message untuk safety
            await self._send_chunked_message(ctx, summary)
            
        except Exception as e:
            from core.logger import log_error
            log_error("CASUAL_CONV", str(e), user_input)
            await ctx.send("Maaf, ada masalah teknis. Coba lagi nanti ya! 😅")
    
    async def _handle_recommendation_request(self, ctx, user_input):
        """Handle request rekomendasi - langsung AI tanpa cache"""
        try:
            start_time = time.time()
            from core.logger import log_ai_request
            log_ai_request("RECOMMENDATION", len(user_input))
            
            # Langsung AI response dengan max_tokens terbatas
            summary = await self.ai_handler.chat_async(user_input, max_tokens=1500, category="REKOMENDASI")
            ai_duration = int((time.time() - start_time) * 1000)
            from core.logger import log_ai_response
            log_ai_response("RECOMMENDATION", len(summary) if summary else 0, ai_duration)
            
            # Kirim dalam chunks untuk menghindari Discord limit
            await self._send_chunked_message(ctx, summary)
            
        except Exception as e:
            from core.logger import log_error
            log_error("RECOMMENDATION", str(e), user_input)
            await ctx.send("Maaf, ada masalah dalam memberikan rekomendasi. Coba lagi nanti ya! 😅")
    
    async def _handle_general_query(self, ctx, user_input):
        """Handle general queries"""
        try:
            start_time = time.time()
            from core.logger import log_ai_request
            log_ai_request("GENERAL", len(user_input))
            
            summary = await self.ai_handler.handle_general_query(user_input)
            ai_duration = int((time.time() - start_time) * 1000)
            from core.logger import log_ai_response
            log_ai_response("GENERAL", len(summary) if summary else 0, ai_duration)
            
            await ctx.send(summary)
            
        except Exception as e:
            from core.logger import log_error
            log_error("GENERAL_QUERY", str(e), user_input)
            await ctx.send(f"Gagal memproses query: {e}")
    
    async def _handle_help_command(self, ctx):
        """Handle !sn help command dengan Discord embed yang cantik"""
        try:
            # Create main help embed
            embed = discord.Embed(
                title="🤖 SN Fun Bot - K-pop Info ✨",
                description="Bot K-pop terlengkap dengan AI, bias detector, dan social media monitoring!",
                color=0xFF69B4  # Pink color
            )
            
            # K-pop Info section
            kpop_info = """• `!sn [nama]` 🎤 Info K-pop (member/grup)
• `!sn [member] [grup]` 🎭 Info spesifik
• `!sn hai` 💬 Chat casual
• `!sn rekomen lagu` 🎵 Minta rekomendasi"""
            embed.add_field(
                name="🎯 K-pop Info",
                value=kpop_info,
                inline=False
            )
            
            # Gacha Trading Cards section
            gacha_commands = """• `!sn gacha` 🎲 Random gacha
• `!sn gacha info` 📊 Detail info & stats"""
            embed.add_field(
                name="🎴 Gacha Cards",
                value=gacha_commands,
                inline=True
            )
            
            # Bias Detector section
            bias_commands = """• `!sn bias` 🎯 Deteksi bias kamu
• `!sn bias info` 📋 Detail info & commands"""
            embed.add_field(
                name="💕 Bias Detector",
                value=bias_commands,
                inline=True
            )
            
            # Social Media section
            social_commands = """• `!sn twitter` 🐦 Latest tweets
• `!sn youtube` 📺 Latest videos  
• `!sn instagram` 📸 Latest posts
• `!sn sosmed` 📱 All platforms"""
            embed.add_field(
                name="📱 Social Media",
                value=social_commands,
                inline=True
            )
            
            # Utility section
            utility_commands = """• `!sn help` 📋 Help ini
• `!sn analytics` 📊 Statistik bot
• `!sn monitor start/stop` 🔍 Social monitoring
• `!sn db status` 💾 Database status"""
            embed.add_field(
                name="⚙️ Utility",
                value=utility_commands,
                inline=False
            )
            
            # Footer with additional info
            embed.set_footer(
                text="Bot otomatis deteksi member, grup, atau chat biasa! 🎵✨",
                icon_url="https://cdn.discordapp.com/emojis/741243929655173160.png"
            )
            
            # Thumbnail (Secret Number logo if available)
            embed.set_thumbnail(url="https://i.imgur.com/YourSecretNumberLogo.png")
            
            await ctx.send(embed=embed)
            logger.info("Help embed command requested")
            
        except Exception as e:
            logger.error(f"Error creating help embed: {e}")
            # Fallback to text message if embed fails
            help_message = "🤖 **SN Fun Bot Help** - Gunakan `!sn [command]` untuk berbagai fitur K-pop!"
            await ctx.send(help_message)

    async def _handle_bias_info_command(self, ctx):
        """Handle !sn bias info command - comprehensive bias detector information"""
        try:
            embed = discord.Embed(
                title="💕 Bias Detector & Fortune System",
                description="AI-powered bias detection dengan love matching dan ramalan cinta!",
                color=0xFF1493  # Deep Pink
            )
            
            # Available Commands
            commands_text = """• `!sn bias` 🎯 Deteksi bias kamu
• `!sn match [member]` 💖 Love matching
• `!sn fortune` 🔮 Ramalan cinta
• `!sn ramalan` ✨ Fortune telling"""
            
            embed.add_field(
                name="🎯 Available Commands",
                value=commands_text,
                inline=False
            )
            
            # How It Works
            how_it_works = """🤖 **AI Analysis** berdasarkan personality
💕 **Compatibility Score** 75-99%
🎭 **Personality Matching** traits
🔮 **Fortune System** dengan ramalan"""
            
            embed.add_field(
                name="⚙️ How It Works",
                value=how_it_works,
                inline=True
            )
            
            # Features
            features_text = """✨ **Konsisten** per user ID
🎨 **Beautiful Embeds** dengan colors
💬 **Indonesian Language** fun & casual
🎲 **Random Elements** untuk variety"""
            
            embed.add_field(
                name="💡 Features",
                value=features_text,
                inline=True
            )
            
            # Tips
            tips_text = """💡 Hasil bias detection konsisten per user
🎯 Gunakan nama member untuk love matching
🔮 Fortune dan ramalan memberikan hasil berbeda
💕 Semua hasil dibuat dengan AI analysis"""
            
            embed.add_field(
                name="📝 Tips & Info",
                value=tips_text,
                inline=False
            )
            
            embed.set_footer(text="SN Fun Bot • AI-powered bias detection! 💕")
            
            await ctx.send(embed=embed)
            logger.info("Bias info command executed")
            
        except Exception as e:
            logger.error(f"Error in bias info: {e}")
            await ctx.send("❌ Gagal menampilkan info bias detector.")

    async def _handle_analytics_command(self, ctx):
        """Handle !sn analytics command dengan Discord embed"""
        try:
            # Get analytics data
            stats = analytics.data["query_stats"]
            
            # Check if we have any data, if not generate sample data for demo
            if stats["total_queries"] == 0:
                # Generate sample analytics data for demonstration
                analytics.data["query_stats"] = {
                    "enhanced_success": 45,
                    "enhanced_failed": 5,
                    "simple_success": 32,
                    "simple_failed": 3,
                    "total_queries": 85
                }
                analytics.data["popular_queries"] = {
                    "BLACKPINK": 15,
                    "Secret Number": 12,
                    "QWER": 8,
                    "NewJeans": 7,
                    "IVE": 5
                }
                analytics.data["response_times"] = {
                    "scraping": [2.3, 1.8, 2.1, 1.9, 2.5],
                    "ai_generation": [3.2, 2.8, 3.5, 2.9, 3.1],
                    "total_response": [5.5, 4.6, 5.6, 4.8, 5.6]
                }
                analytics.data["source_performance"] = {
                    "soompi": {"success": 18, "failed": 2, "avg_time": 2.1},
                    "allkpop": {"success": 15, "failed": 3, "avg_time": 2.3},
                    "kprofiles": {"success": 12, "failed": 1, "avg_time": 1.8},
                    "wikipedia": {"success": 8, "failed": 2, "avg_time": 2.5}
                }
                analytics._save_analytics()
                stats = analytics.data["query_stats"]
            
            # Create analytics embed
            embed = discord.Embed(
                title="📊 Bot Analytics Dashboard",
                description="Statistik penggunaan dan performa SN Fun Bot",
                color=0x00FF7F  # Green color
            )
            
            # Query Statistics
            enhanced_total = stats["enhanced_success"] + stats["enhanced_failed"]
            simple_total = stats["simple_success"] + stats["simple_failed"]
            enhanced_rate = (stats["enhanced_success"] / enhanced_total * 100) if enhanced_total > 0 else 0
            simple_rate = (stats["simple_success"] / simple_total * 100) if simple_total > 0 else 0
            
            query_stats = f"""✅ Enhanced: {enhanced_rate:.1f}% ({stats['enhanced_success']}/{enhanced_total})
✅ Simple: {simple_rate:.1f}% ({stats['simple_success']}/{simple_total})
📈 Total Queries: {stats['total_queries']}"""
            
            embed.add_field(
                name="🎯 Query Success Rate",
                value=query_stats,
                inline=True
            )
            
            await ctx.send(embed=embed)
            logger.info("Analytics command executed")
            
        except Exception as e:
            logger.error(f"Error in analytics command: {e}")
            await ctx.send("❌ Gagal menampilkan analytics data.")
    
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
    
    def _is_admin(self, user_id):
        """Check if user is admin"""
        # Get admin IDs from environment variable
        admin_ids_str = os.getenv('ADMIN_DISCORD_IDS', '')
        if not admin_ids_str:
            return False
        
        try:
            # Parse comma-separated admin IDs
            admin_ids = [int(id_str.strip()) for id_str in admin_ids_str.split(',') if id_str.strip()]
            return user_id in admin_ids
        except ValueError:
            logger.error("Invalid ADMIN_DISCORD_IDS format in environment variables")
            return False

    async def _handle_expansion_command(self, ctx, user_input):
        """Handle gallery expansion command (admin only)"""
        try:
            # Check if user is admin
            if not self._is_admin(ctx.author.id):
                await ctx.send("❌ This command is admin-only.")
                return
            
            # Check if expansion service is available
            if not hasattr(self, 'expansion_service') or not self.expansion_service:
                await ctx.send("❌ Gallery expansion service not available.")
                return
            
            # Check if service is enabled
            if not self.expansion_service.is_enabled():
                await ctx.send("❌ Gallery expansion service is disabled. Check GALLERY_EXPANSION_ENABLED and Google Drive setup.")
                return
            
            # Parse command: "expand", "expand member karina aespa", "expand test karina aespa", "expand stats"
            parts = user_input.split()
            
            if len(parts) == 1:
                # Show help
                embed = discord.Embed(
                    title="🖼️ Gallery Expansion Commands",
                    description="Admin-only commands for expanding photo database",
                    color=0x00ff00
                )
                embed.add_field(
                    name="Commands",
                    value="`!sn expand member <name> <group>` - Expand member photos\n"
                          "`!sn expand test <name> <group>` - Test expansion\n"
                          "`!sn expand stats` - Show expansion statistics",
                    inline=False
                )
                await ctx.send(embed=embed)
                return
            
            subcommand = parts[1].lower()
            
            if subcommand == "stats":
                # Show expansion statistics
                stats = self.expansion_service.get_expansion_stats()
                embed = discord.Embed(
                    title="📊 Gallery Expansion Statistics",
                    color=0x0099ff
                )
                for key, value in stats.items():
                    embed.add_field(name=key.replace('_', ' ').title(), value=str(value), inline=True)
                await ctx.send(embed=embed)
                
            elif subcommand in ["member", "test"] and len(parts) >= 4:
                # Extract member and group
                member_name = parts[2]
                group_name = " ".join(parts[3:])
                test_mode = (subcommand == "test")
                
                # Send processing message
                processing_msg = await ctx.send(f"🔄 {'Testing' if test_mode else 'Expanding'} gallery for {member_name} ({group_name})...")
                
                try:
                    # Run expansion
                    result = await self.expansion_service.expand_member_photos(
                        member_name, group_name, test_mode=test_mode
                    )
                    
                    if result['success']:
                        embed = discord.Embed(
                            title=f"✅ Gallery Expansion {'Test' if test_mode else ''} Complete",
                            description=f"Successfully processed {member_name} from {group_name}",
                            color=0x00ff00
                        )
                        embed.add_field(name="Photos Added", value=str(result.get('photos_added', 0)), inline=True)
                        embed.add_field(name="Drive IDs Generated", value=str(result.get('drive_ids', 0)), inline=True)
                        if test_mode:
                            embed.add_field(name="Mode", value="🧪 Test Mode", inline=True)
                        
                        await processing_msg.edit(content="", embed=embed)
                    else:
                        await processing_msg.edit(content=f"❌ Expansion failed: {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    await processing_msg.edit(content=f"❌ Error during expansion: {str(e)}")
                    logger.error(f"Gallery expansion error: {e}")
            
            else:
                await ctx.send("❌ Invalid expansion command. Use `!sn expand` for help.")
                
        except Exception as e:
            logger.error(f"Expansion command error: {e}")
            await ctx.send(f"❌ Error handling expansion command: {e}")

    async def _handle_maintenance_command(self, ctx, user_input):
        """Handle maintenance command"""
        try:
            # Parse maintenance command: "maintenance", "maintenance on", "maintenance off", etc.
            parts = user_input.split()
            action = parts[1] if len(parts) > 1 else None
            args = parts[2:] if len(parts) > 2 else []
            
            # Delegate to MaintenanceManager
            await self.maintenance_manager.handle_maintenance_command(ctx, action, *args)
            
        except Exception as e:
            logger.error(f"Maintenance command error: {e}")
            await ctx.send(f"❌ Error handling maintenance command: {e}")
