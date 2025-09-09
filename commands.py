"""
Commands Module - Menangani semua Discord commands
"""
import asyncio
import redis
import logger
import time
from ai_handler import AIHandler
from data_fetcher import DataFetcher
from analytics import analytics

class CommandsHandler:
    def __init__(self, bot_core):
        self.bot = bot_core.bot
        self.redis_client = bot_core.redis_client
        self.kpop_detector = bot_core.kpop_detector
        self.kpop_df = bot_core.kpop_df  # Add access to dataframe
        
        # Initialize handlers
        self.ai_handler = AIHandler()
        self.data_fetcher = DataFetcher(bot_core.kpop_df)  # Pass database untuk fallback
        
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
                
                # Deteksi K-pop member/group dengan SmartDetector
                category, detected_name, multiple_matches = self.kpop_detector.detect(user_input)
                logger.log_sn_command(ctx.author, user_input, category, detected_name)
                
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
        finally:
            # Remove from processing set when done
            self.processing_messages.discard(message_id)
    
    async def _clear_cache(self, ctx):
        """Clear Redis cache"""
        self.redis_client.flushdb()
        await ctx.send("Redis cache berhasil dihapus.")
    
    async def _handle_kpop_query(self, ctx, category, detected_name):
        """Handle K-pop related queries"""
        start_time = time.time()
        analytics.track_daily_usage()
        
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
            
            # Track scraping time
            scraping_start = time.time()
            
            # Fetch info dari berbagai sumber dengan enhanced query
            info = await self.data_fetcher.fetch_kpop_info(enhanced_query)
            
            # Fallback ke simple query jika enhanced query gagal
            enhanced_success = bool(info.strip())
            if not enhanced_success:
                logger.logger.warning(f"⚠️ Enhanced query failed, trying simple query: {detected_name}")
                simple_info = await self.data_fetcher.fetch_kpop_info(detected_name)
                simple_success = bool(simple_info.strip())
                
                if simple_success:
                    info = simple_info
                    logger.logger.info(f"✅ Simple query successful: {len(info)} characters")
                    analytics.track_query_success("simple", True, detected_name)
                else:
                    logger.logger.warning(f"❌ Both enhanced and simple queries failed for {category}: {detected_name}")
                    analytics.track_query_success("enhanced", False, detected_name)
                    analytics.track_query_success("simple", False, detected_name)
                    await ctx.send("Maaf, info K-pop tidak ditemukan.")
                    return
                
                analytics.track_query_success("enhanced", False, detected_name)
            else:
                analytics.track_query_success("enhanced", True, detected_name)
            
            scraping_time = time.time() - scraping_start
            analytics.track_response_time("scraping", scraping_time)
            
            logger.logger.info(f"✅ Scraping completed for {category}: {detected_name} - {len(info)} characters retrieved")
            
            # Generate AI summary
            ai_start = time.time()
            try:
                summary = await self.ai_handler.generate_kpop_summary(category, info)
                
                ai_time = time.time() - ai_start
                analytics.track_response_time("ai_generation", ai_time)
                
                # Simpan ke Redis cache
                self.redis_client.set(cache_key, summary, ex=86400)  # 24 jam
                logger.log_cache_set(category, detected_name)
                
            except Exception as e:
                logger.logger.error(f"Gagal membuat ringkasan: {e}")
                await ctx.send(f"Gagal membuat ringkasan: {e}")
                return
        
        # Track total response time
        total_time = time.time() - start_time
        analytics.track_response_time("total_response", total_time)
        
        # Kirim ke Discord (chunk <=2000 karakter)
        await self._send_chunked_message(ctx, summary)
    
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

    async def _handle_casual_conversation(self, ctx, user_input):
        """Handle obrolan casual dengan memory"""
        try:
            user_id = ctx.author.id
            
            # Dapatkan konteks percakapan
            conversation_context = self._get_conversation_context(user_id, user_input)
            
            # Generate response dengan konteks
            summary = await self.ai_handler.handle_general_query(conversation_context)
            
            # Validasi dan sanitasi response
            if not summary or not isinstance(summary, str):
                summary = "Maaf, saya tidak bisa memahami pertanyaan itu. Coba tanya yang lain ya! 😅"
            
            # Truncate jika terlalu panjang
            if len(summary) > 1900:
                summary = summary[:1900] + "..."
            
            # Simpan ke memory
            self._add_to_memory(user_id, "user", user_input)
            self._add_to_memory(user_id, "assistant", summary)
            
            # Kirim dengan chunked message untuk safety
            await self._send_chunked_message(ctx, summary)
            logger.logger.info(f"OBROLAN request processed with memory: {user_input}")
        except Exception as e:
            logger.logger.error(f"Gagal memproses obrolan: {e}")
            # Safe fallback response
            try:
                await ctx.send("Maaf, ada masalah teknis. Coba lagi ya! 🤖")
            except:
                logger.logger.error("Failed to send fallback message")
    
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
        """Handle general queries"""
        try:
            summary = await self.ai_handler.handle_general_query(user_input)
            await ctx.send(summary)
            logger.logger.info(f"General query processed: {user_input}")
        except Exception as e:
            logger.logger.error(f"Gagal memproses general query: {e}")
            await ctx.send(f"Gagal memproses query: {e}")
    
    async def _handle_help_command(self, ctx):
        """Handle !sn help command untuk menampilkan daftar commands"""
        help_message = """
🤖 **SN Fun Bot - K-pop Discord Bot**

**📋 Daftar Commands:**

**🎵 K-pop Queries:**
• `!sn [nama member]` - Info tentang member K-pop
• `!sn [nama grup]` - Info tentang grup K-pop
• `!sn [member] [grup]` - Info spesifik member dari grup

**💬 Conversational:**
• `!sn aku ingin info tentang [nama]` - Query natural
• `!sn berikan info tentang [nama]` - Query natural
• `!sn hai/halo` - Obrolan casual

**🎯 Rekomendasi:**
• `!sn rekomendasikan lagu K-pop` - Minta rekomendasi
• `!sn kasih saran [topik]` - Minta saran

**⚙️ Utility Commands:**
• `!sn help` - Tampilkan help ini
• `!sn analytics` - Lihat statistik bot
• `!sn clearcache` - Hapus cache Redis

**📝 Contoh Penggunaan:**
```
!sn Jisoo
!sn BTS
!sn Jisoo Blackpink
!sn aku mau info tentang NewJeans
!sn rekomendasikan lagu ballad K-pop
!sn analytics
```

**🔍 Bot akan otomatis mendeteksi:**
- Member K-pop individual
- Grup K-pop
- Percakapan casual
- Permintaan rekomendasi
- Multiple matches (nama ambiguous)

Selamat menggunakan SN Fun Bot! 🎉
"""
        await self._send_chunked_message(ctx, help_message)
        logger.logger.info("Help command requested")

    async def _handle_analytics_command(self, ctx):
        """Handle !analytics command untuk view statistics"""
        try:
            summary = analytics.get_analytics_summary()
            await self._send_chunked_message(ctx, summary)
            logger.logger.info("Analytics summary requested")
        except Exception as e:
            logger.logger.error(f"Error getting analytics: {e}")
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
            logger.logger.error(f"Error building enhanced query: {e}")
        
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
        logger.logger.info(f"Sending {len(chunks)} chunks to Discord")
        for i, chunk in enumerate(chunks):
            try:
                if i > 0:
                    await asyncio.sleep(1.0)  # Longer delay between chunks
                logger.logger.info(f"Sending chunk {i+1}/{len(chunks)} - {len(chunk)} characters")
                await ctx.send(chunk)
                logger.logger.info(f"Successfully sent chunk {i+1}/{len(chunks)}")
            except Exception as e:
                logger.logger.error(f"Failed to send chunk {i+1}/{len(chunks)}: {e}")
                # Try to send remaining chunks
                continue
