"""
Bias Commands Handler - Fun interactive commands untuk bias detection
"""
import discord
from datetime import datetime
from logger import logger

class BiasCommandsHandler:
    def __init__(self, bias_detector, ai_handler, kpop_df):
        self.bias_detector = bias_detector
        self.ai_handler = ai_handler
        self.kpop_df = kpop_df
        self.user_preferences = {}
        self.command_cooldowns = {}
        self.cooldown_duration = 30  # 30 seconds
        self.user_member_cache = {}  # Cache for consistent results
        
    async def handle_bias_command(self, ctx, user_input: str):
        """Handle bias commands dari user input"""
        # Parse subcommand dari user input
        input_lower = user_input.lower().strip()
        
        if input_lower.startswith("bias") and not input_lower.startswith(("bias fortune", "bias match")):
            await self._handle_bias_detect(ctx, str(ctx.author.id), [])
        elif input_lower.startswith("bias fortune"):
            # Parse fortune type from input
            parts = user_input.split()
            fortune_type = parts[2] if len(parts) > 2 else 'general'
            await self._handle_fortune(ctx, str(ctx.author.id), [fortune_type])
        elif input_lower.startswith("bias match"):
            # Parse member name from input
            parts = user_input.split()
            member_name = parts[2] if len(parts) > 2 else None
            await self._handle_love_match(ctx, str(ctx.author.id), [member_name] if member_name else [])
        elif input_lower.startswith("match"):
            # Parse member name and group from input
            parts = user_input.split()
            args = parts[1:] if len(parts) > 1 else []
            await self._handle_love_match(ctx, str(ctx.author.id), args)
        elif input_lower.startswith(("fortune", "ramalan")):
            # Parse fortune type from input
            parts = user_input.split()
            fortune_type = parts[1] if len(parts) > 1 else 'general'
            await self._handle_fortune(ctx, str(ctx.author.id), [fortune_type])
        else:
            await ctx.send("❌ Command tidak dikenal. Gunakan: bias, match, fortune, atau ramalan")
    
    async def handle_bias_subcommand(self, ctx, subcommand: str, *args):
        """Handle semua bias-related commands"""
        user_id = str(ctx.author.id)
        
        # Check cooldown
        if not await self._check_cooldown(ctx, user_id, subcommand):
            return
        
        try:
            if subcommand == 'detect':
                await self._handle_bias_detect(ctx, user_id, args)
            elif subcommand == 'match':
                await self._handle_love_match(ctx, user_id, args)
            elif subcommand == 'fortune':
                await self._handle_fortune(ctx, user_id, args)
            elif subcommand == 'profile':
                await self._handle_member_profile(ctx, args)
            elif subcommand == 'preferences':
                await self._handle_set_preferences(ctx, user_id, args)
            else:
                await self._show_bias_help(ctx)
                
        except Exception as e:
            logger.error(f"Bias command error: {e}")
            await self._send_error_embed(ctx, "Terjadi error saat memproses command bias")
    
    async def _handle_bias_detect(self, ctx, user_id: str, args):
        """Handle !sn bias detect command"""
        # Show loading embed
        loading_embed = discord.Embed(
            title="🔮 Bias Detector Ajaib",
            description="Wah! AI lagi sibuk baca pikiran kamu nih... 🤭✨",
            color=0xFF1493
        )
        loading_embed.add_field(
            name="⏳ Lagi Proses Nih",
            value="Bentar ya, lagi nyocokkin sama ribuan idol K-pop... 💕",
            inline=False
        )
        loading_message = await ctx.send(embed=loading_embed)
        
        try:
            logger.info(f"🔍 Starting bias detection for user {user_id}")
            
            # Get user preferences
            preferences = self.user_preferences.get(user_id, {})
            logger.info(f"User preferences: {preferences}")
            
            # Detect bias using AI
            logger.info("Calling bias_detector.bias_detect...")
            bias_result = await self.bias_detector.bias_detect(user_id, preferences)
            logger.info(f"✅ Bias detection completed. Result type: {type(bias_result)}")
            logger.info(f"Bias result: {bias_result}")
            
            # Check if there's an error
            if isinstance(bias_result, dict) and bias_result.get('error'):
                logger.error(f"Bias detection returned error: {bias_result['error']}")
                await loading_message.edit(embed=self._create_error_embed(bias_result['error']))
                return
            
            # Extract member info from bias result
            member_name = bias_result.get('member_name')
            logger.info(f"Extracted member name: {member_name}")
            
            member_data = self.bias_detector.get_member_info(member_name)
            logger.info(f"Member data retrieved: {member_data}")
            
            if not member_data:
                logger.error(f"No member data found for: {member_name}")
                await loading_message.edit(embed=self._create_error_embed("Member data tidak ditemukan"))
                return
            
            # Create result embed
            result_embed = discord.Embed(
                title=f"🎯 Bias Kamu Ketemu Nih: {member_data['name']}! 💕",
                description=f"Yeay! AI udah nemuin jodoh hati kamu: **{member_data['name']}** dari **{bias_result.get('group_name', 'Unknown Group')}**! 🥰✨",
                color=member_data.get('color', 0xFF69B4)
            )
            
            result_embed.add_field(
                name=f"{member_data.get('emoji', '✨')} Info Si Doi",
                value=f"**Grup:** {bias_result.get('group_name', 'Unknown')}\n**Posisi:** {member_data.get('position', 'Unknown')}\n**Ultah:** {member_data.get('birthday', 'Unknown')}",
                inline=True
            )
            
            result_embed.add_field(
                name="🎯 Compatibility Score",
                value=f"**{bias_result.get('compatibility_score', 85)}%** - {bias_result.get('reason', 'Perfect match!')}",
                inline=True
            )
            
            result_embed.add_field(
                name="✨ AI Analysis",
                value=bias_result.get('ai_analysis', 'Kalian cocok banget! 💕'),
                inline=False
            )
            
            result_embed.add_field(
                name="🎪 Member Traits",
                value=f"Kepribadian: {', '.join(bias_result.get('member_traits', ['charming', 'talented'])[:3])} - amazing! 💯",
                inline=False
            )
            
            result_embed.add_field(
                name="💡 Mau Tau Seberapa Cocok?",
                value=f"Coba `!sn bias match {member_data['name'].lower()}` buat cek love compatibility! 😍",
                inline=False
            )
            
            result_embed.set_footer(text="K-pop Bias Detector • Dibuat dengan cinta 💕")
            
            logger.info("📤 Sending result embed to Discord...")
            await loading_message.edit(embed=result_embed)
            logger.info("✅ Result embed sent successfully!")
            
        except Exception as e:
            logger.error(f"❌ Bias detect error: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            await loading_message.edit(embed=self._create_error_embed("Bias detection gagal"))
    
    async def _handle_love_match(self, ctx, user_id: str, args):
        """Handle !sn bias match command"""
        if not args:
            await ctx.send("❌ Sebutkan nama member! Contoh: `!sn match jisoo`")
            return
        
        # Check if first argument is just a number (invalid input)
        if len(args) == 1 and args[0].isdigit():
            await ctx.send("❌ Format salah! Gunakan: `!sn match <nama_member>` atau `!sn match <nama_member> <grup>`")
            return
        
        # Check if user specified member with group (e.g., "jisoo blackpink")
        if len(args) >= 2:
            member_name_input = args[0].lower()
            group_name_input = ' '.join(args[1:]).lower()
            
            logger.info(f"🎯 Direct selection: '{member_name_input}' from '{group_name_input}'")
            
            # Try to find member by name and group
            direct_match = self.bias_detector._find_member_by_name_and_group(member_name_input, group_name_input)
            
            if direct_match:
                member_name = direct_match
                logger.info(f"✅ Found direct match: '{member_name}' for '{member_name_input}' from '{group_name_input}'")
                # Set flag to force direct match and bypass multiple choice
                force_direct = True
            else:
                logger.debug(f"Direct match failed for '{member_name_input}' from '{group_name_input}'")
                
                await ctx.send(f"❌ Tidak ditemukan member '{member_name_input}' dari grup '{group_name_input}'!\n💡 Coba: `!sn match {member_name_input}` untuk melihat pilihan yang tersedia.")
                return
        
        else:
            member_name = args[0].lower()
            force_direct = False
            
            # Validate member name is not just a number
            if member_name.isdigit():
                await ctx.send("❌ Nama member tidak boleh hanya angka! Contoh: `!sn match jisoo`")
                return
        
        # Show loading embed
        loading_embed = discord.Embed(
            title="💕 Cek Chemistry Yuk!",
            description="Wah seru nih! AI lagi ngitung seberapa cocok kalian... 🥰💫",
            color=0xFF69B4
        )
        loading_message = await ctx.send(embed=loading_embed)
        
        try:
            # Get love match analysis
            logger.info(f"💕 Love match analysis: {member_name} for user {user_id}")
            match_result = await self.bias_detector.love_match(user_id, member_name, force_direct_match=force_direct)
            
            # Check if it's a selection prompt (just show info, don't wait for selection)
            if isinstance(match_result, dict) and match_result.get('is_selection_prompt'):
                # Create informational embed showing available members
                info_embed = discord.Embed(
                    title="🔍 Ditemukan Beberapa Member",
                    description=match_result['selection_text'],
                    color=0xFF69B4
                )
                info_embed.set_footer(text="💡 Gunakan format: !sn match <nama> <grup> untuk analisis langsung")
                await loading_message.edit(embed=info_embed)
                return
            
            # Check if there's an error in the result
            if isinstance(match_result, dict) and match_result.get('error'):
                error_embed = self._create_error_embed(match_result['error'])
                await loading_message.edit(embed=error_embed)
                return
            
            # Validate match_result structure
            if not match_result or not isinstance(match_result, dict):
                logger.error(f"Invalid match_result: {match_result}")
                error_embed = self._create_error_embed("Gagal mendapatkan hasil analisis")
                await loading_message.edit(embed=error_embed)
                return
            
            member_name_display = match_result.get('member_name', 'Unknown')
            group_name_display = match_result.get('group_name', 'Unknown')
            score = match_result.get('score', 0)
            
            # Create compatibility embed
            compatibility_embed = discord.Embed(
                title=f"💖 Chemistry Kalian: Kamu & {member_name_display}",
                description=f"**Skor Kecocokan: {score}%** {self._get_score_emoji(score)} - Wah mantap nih! 🥳",
                color=0xFF69B4
            )
            
            compatibility_embed.add_field(
                name=f"💫 Si Doi Kamu",
                value=f"**{member_name_display}** dari **{group_name_display}**",
                inline=True
            )
            
            compatibility_embed.add_field(
                name="🔥 Level Kecocokan",
                value=self._get_compatibility_level(score, user_id, member_name_display),
                inline=True
            )
            
            compatibility_embed.add_field(
                name="🤖 Analisis AI",
                value=match_result.get('ai_analysis', 'Analisis tidak tersedia')[:200] + "..." if len(match_result.get('ai_analysis', '')) > 200 else match_result.get('ai_analysis', 'Analisis tidak tersedia'),
                inline=False
            )
            
            compatibility_embed.add_field(
                name="💫 Kenapa Kalian Cocok",
                value="\n".join([f"• {reason}" for reason in match_result.get('match_reasons', ['Chemistry yang bagus'])]),
                inline=False
            )
            
            compatibility_embed.add_field(
                name="🔮 Mau Ramalan Cinta?",
                value=f"Coba `!sn bias fortune love` buat tau nasib asmara kamu! 😘",
                inline=False
            )
            
            compatibility_embed.set_footer(text="K-pop Love Matcher • Cuma buat hiburan ya! 😄💕")
            
            await loading_message.edit(embed=compatibility_embed)
            
        except Exception as e:
            logger.error(f"Love match error: {e}")
            await loading_message.edit(embed=self._create_error_embed("Love match analysis gagal"))
    
    async def _handle_fortune(self, ctx, user_id: str, args):
        """Handle !sn bias fortune command"""
        fortune_type = args[0].lower() if args else 'general'
        valid_types = ['love', 'career', 'friendship', 'general']
        
        if fortune_type not in valid_types:
            fortune_type = 'general'
        
        # Show loading embed
        loading_embed = discord.Embed(
            title="🔮 Peramal Cinta K-pop",
            description="Wah! Energi kosmik lagi ngumpul nih... ✨🌙 Siap-siap ya!",
            color=0x9370DB
        )
        loading_message = await ctx.send(embed=loading_embed)
        
        try:
            # Get fortune reading
            fortune_result = await self.bias_detector.fortune_teller(user_id, fortune_type)
            guide_member = fortune_result['guide_member']
            
            # Create fortune embed
            fortune_embed = discord.Embed(
                title=f"🌟 Ramalan {fortune_type.title()} Kamu",
                description=fortune_result['fortune'],
                color=fortune_result['lucky_color']
            )
            
            fortune_embed.add_field(
                name=f"{guide_member['emoji']} Pemandu Spiritual",
                value=f"**{guide_member['name']}** lagi bantuin ramalin nasib kamu nih! 🥰",
                inline=True
            )
            
            fortune_embed.add_field(
                name="🍀 Angka Hoki",
                value=f"**{fortune_result['lucky_number']}** - Inget angka ini ya! 💫",
                inline=True
            )
            
            fortune_embed.add_field(
                name="🎨 Warna Beruntung",
                value=f"**Warna {guide_member['name']}** - Pakai warna ini biar makin hoki! ✨",
                inline=True
            )
            
            fortune_embed.add_field(
                name="✨ Pesan Kosmik",
                value="Percaya sama magic K-pop dan tetep positive thinking ya! 🌙💕",
                inline=False
            )
            
            fortune_embed.add_field(
                name="🔄 Mau Ramalan Lain?",
                value="Coba: `love` (cinta), `career` (karir), `friendship` (persahabatan), `general` (umum)",
                inline=False
            )
            
            fortune_embed.set_footer(text=f"Ramalan by {guide_member['name']} • K-pop Magic ✨")
            
            await loading_message.edit(embed=fortune_embed)
            
        except Exception as e:
            logger.error(f"Fortune error: {e}")
            await loading_message.edit(embed=self._create_error_embed("Fortune reading gagal"))
    
    async def _handle_member_profile(self, ctx, args):
        """Handle !sn bias profile command"""
        if not args:
            await self._show_all_members(ctx)
            return
        
        member_name = args[0].lower()
        member_data = self.bias_detector.get_member_info(member_name)
        
        if not member_data:
            await ctx.send("❌ Member tidak ditemukan! Coba: lea, dita, jinny, soodam, denise, minji, zuu")
            return
        
        # Create member profile embed
        profile_embed = discord.Embed(
            title=f"{member_data['emoji']} {member_data['name']} Profile",
            description=f"**{member_data['korean_name']}** • Secret Number",
            color=member_data['color']
        )
        
        profile_embed.add_field(
            name="🎭 Position",
            value=member_data['position'],
            inline=True
        )
        
        profile_embed.add_field(
            name="🎂 Birthday",
            value=member_data['birthday'],
            inline=True
        )
        
        profile_embed.add_field(
            name="🌍 Nationality",
            value=member_data['nationality'],
            inline=True
        )
        
        profile_embed.add_field(
            name="✨ Personality",
            value=member_data['personality'],
            inline=False
        )
        
        profile_embed.add_field(
            name="🎪 Traits",
            value=", ".join(member_data['traits']),
            inline=False
        )
        
        profile_embed.add_field(
            name="💕 Try Commands",
            value=f"`!sn bias match {member_name}` • `!sn bias detect`",
            inline=False
        )
        
        profile_embed.set_footer(text="Secret Number Member Profile")
        
        await ctx.send(embed=profile_embed)
    
    async def _handle_set_preferences(self, ctx, user_id: str, args):
        """Handle !sn bias preferences command"""
        if not args:
            await self._show_preferences_help(ctx)
            return
        
        # Parse preferences from args
        traits = [trait.lower() for trait in args if trait.lower() in ['leader', 'artistic', 'energetic', 'gentle', 'confident', 'playful', 'mysterious', 'multilingual']]
        
        if not traits:
            await ctx.send("❌ Traits tidak valid! Gunakan: leader, artistic, energetic, gentle, confident, playful, mysterious, multilingual")
            return
        
        # Save preferences
        self.user_preferences[user_id] = {'traits': traits}
        
        # Confirmation embed
        pref_embed = discord.Embed(
            title="✅ Preferences Updated!",
            description=f"Preferences kamu telah disimpan untuk bias detection yang lebih akurat.",
            color=0x00FF00
        )
        
        pref_embed.add_field(
            name="🎯 Your Traits",
            value=", ".join(traits),
            inline=False
        )
        
        pref_embed.add_field(
            name="🔮 Next Step",
            value="Try `!sn bias detect` dengan preferences baru!",
            inline=False
        )
        
        await ctx.send(embed=pref_embed)
    
    async def _show_all_members(self, ctx):
        """Show all Secret Number members"""
        members_embed = discord.Embed(
            title="🌟 Secret Number Members",
            description="Pilih member untuk melihat profile lengkap!",
            color=0xFF1493
        )
        
        for name, data in self.bias_detector.get_all_members().items():
            members_embed.add_field(
                name=f"{data['emoji']} {data['name']}",
                value=f"{data['korean_name']} • {data['position'].split(',')[0]}",
                inline=True
            )
        
        members_embed.add_field(
            name="💡 Usage",
            value="`!sn bias profile [member_name]`",
            inline=False
        )
        
        await ctx.send(embed=members_embed)
    
    async def _show_preferences_help(self, ctx):
        """Show preferences help"""
        help_embed = discord.Embed(
            title="🎯 Set Your Preferences",
            description="Customize bias detection dengan personality traits yang kamu suka!",
            color=0x9370DB
        )
        
        help_embed.add_field(
            name="Available Traits",
            value="leader, artistic, energetic, gentle, confident, playful, mysterious, multilingual",
            inline=False
        )
        
        help_embed.add_field(
            name="Usage",
            value="`!sn bias preferences confident artistic energetic`",
            inline=False
        )
        
        await ctx.send(embed=help_embed)
    
    async def _show_bias_help(self, ctx):
        """Show bias detector help"""
        help_embed = discord.Embed(
            title="🔮 K-pop Bias Detector Ajaib",
            description="AI canggih yang bisa nemuin bias perfect kamu! Seru banget deh! 🥰✨",
            color=0xFF1493
        )
        
        help_embed.add_field(
            name="🎯 Command Seru",
            value="`!sn bias detect` - Cari bias K-pop yang cocok banget sama kamu!\n"
                  "`!sn bias match <member>` - Cek chemistry sama idol favorit\n"
                  "`!sn bias fortune <type>` - Ramalan masa depan kamu\n"
                  "`!sn bias profile <member>` - Info lengkap member\n"
                  "`!sn bias pref <key> <value>` - Atur preferensi kamu",
            inline=False
        )
        
        help_embed.add_field(
            name="🔮 Jenis Ramalan",
            value="`love` - Ramalan cinta 💕\n"
                  "`career` - Panduan karir 💼\n"
                  "`friendship` - Hubungan pertemanan 👫\n"
                  "`general` - Ramalan umum ✨",
            inline=True
        )
        
        help_embed.add_field(
            name="⚙️ Preferensi Kamu",
            value="`age_range` - rentang umur yang disuka\n"
                  "`personality` - tipe kepribadian\n"
                  "`position` - posisi member\n"
                  "`group` - grup tertentu",
            inline=True
        )
        
        help_embed.set_footer(text="K-pop Bias Detector • Dibuat dengan cinta 💕")
        
        await ctx.send(embed=help_embed)
    
    async def _check_cooldown(self, ctx, user_id: str, command: str):
        """Check command cooldown"""
        now = datetime.now()
        # Simplified cooldown check
        if user_id in self.command_cooldowns:
            if (now - self.command_cooldowns[user_id]).total_seconds() < self.cooldown_duration:
                minutes = int(self.cooldown_duration - (now - self.command_cooldowns[user_id]).total_seconds()) // 60
                seconds = int(self.cooldown_duration - (now - self.command_cooldowns[user_id]).total_seconds()) % 60
                await ctx.send(f"⏰ Cooldown aktif! Coba lagi dalam {minutes}m {seconds}s")
                return False
        self.command_cooldowns[user_id] = now
        return True
    
    def _get_score_emoji(self, score: int):
        """Get emoji based on score"""
        if score >= 95:
            return "💯"
        elif score >= 90:
            return "🔥"
        elif score >= 80:
            return "💖"
        elif score >= 70:
            return "💕"
        elif score >= 60:
            return "💸"
        elif score >= 40:
            return "💪"
        elif score >= 20:
            return "😅"
        else:
            return "😭"
    
    def _get_compatibility_level(self, score: int, user_id: str, member_name: str):
        """Get compatibility level text with consistent messaging"""
        import random
        import hashlib
        
        # Create consistent hash for user-member combination
        cache_key = f"{user_id}:{member_name}"
        
        if score >= 95:
            messages = [
                "**Astaga! Kalian tuh literally jodoh dari planet lain!** 💯✨",
                "**OMG! Chemistry kalian bikin iri malaikat!** 💯🔥", 
                "**Perfect match banget! Udah kayak drama Korea!** 💯💕",
                "**Wah! Ini mah chemistry level dewa-dewi!** 💯🌟",
                "**Gila sih! Kalian tuh made for each other banget!** 💯💎"
            ]
        elif score >= 90:
            messages = [
                "**Soulmate level detected! Ini mah takdir!** 🔥💫",
                "**Wah, vibes kalian tuh harmonis banget kayak lagu ballad!** 🔥🎵",
                "**Chemistry premium nih! Bikin baper semua orang!** 🔥💖",
                "**Mantap! Kalian tuh power couple sejati!** 🔥👑",
                "**Epic match! Kayak main character di webtoon!** 🔥📚"
            ]
        elif score >= 80:
            messages = [
                "**Chemistry kalian kece badai! Bikin thunder!** 💖⚡",
                "**Cocok banget! Kayak peanut butter sama jelly!** 💖🥜",
                "**Mantap jiwa! Kalian tuh couple goals banget!** 💖👑",
                "**Wah seru! Vibes kalian tuh aesthetic banget!** 💖🎨",
                "**Chemistry solid! Kayak duo superhero!** 💖🦸‍♂️"
            ]
        elif score >= 70:
            messages = [
                "**Potensi gede banget! Tinggal poles dikit lagi!** 💕✨",
                "**Lumayan oke nih! Ada chemistry yang promising!** 💕🌟",
                "**Not bad! Kalian bisa jadi power couple!** 💕💪",
                "**Oke lah! Tinggal upgrade skill komunikasi!** 💕📱",
                "**Bagus! Chemistry kalian ada progress nih!** 💕📈"
            ]
        elif score >= 60:
            messages = [
                "**Wajahmu udah cukup tampan, mungkin dompetmu yang perlu di-upgrade** 💸😅",
                "**Secara fisik oke, tapi mungkin skill flirting-nya yang kurang** 💸🤭",
                "**Lumayan lah, cuma butuh sedikit magic dan duit lebih** 💸✨",
                "**Hmm, mungkin perlu invest di skincare premium** 💸🧴",
                "**Oke sih, tapi kayaknya butuh glow up budget** 💸💄"
            ]
        elif score >= 40:
            messages = [
                "**Ayo semangat! Rome wasn't built in a day!** 💪✨",
                "**Jangan nyerah! Setiap expert pernah jadi beginner!** 💪🌱",
                "**Keep fighting! Plot twist bisa datang kapan aja!** 💪🎬",
                "**Sabar ya! Character development butuh waktu!** 💪⏰",
                "**Tetep optimis! Main character energy!** 💪🌟"
            ]
        elif score >= 20:
            messages = [
                "**Hmm... mungkin perlu konsultasi sama beauty guru dulu** 😂💄",
                "**Kayaknya butuh glow up session yang intense nih** 😂✨",
                "**Sabar ya, everyone has their own timeline** 😂⏰",
                "**Mungkin saatnya belajar dari tutorial YouTube** 😂📺",
                "**Oke, time for major character development!** 😂📖"
            ]
        else:
            messages = [
                "**Waduh! Emergency skincare routine needed ASAP!** 🧴😭",
                "**Mungkin saatnya investasi di facial treatment** 🧴💆‍♂️",
                "**Plot twist: inner beauty is your secret weapon!** 🧴💎",
                "**Urgent! Butuh makeover total nih!** 🧴🔄",
                "**SOS! Time to call the beauty emergency hotline!** 🧴🚨"
            ]
        
        # Use hash to ensure consistent message for same user-member combo
        if cache_key not in self.user_member_cache:
            # Create deterministic selection based on user_id and member_name
            hash_input = f"{user_id}{member_name}".encode()
            hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
            selected_index = hash_value % len(messages)
            self.user_member_cache[cache_key] = selected_index
        
        return messages[self.user_member_cache[cache_key]]
    
    def _create_error_embed(self, message: str):
        """Create error embed"""
        return discord.Embed(
            title="❌ Error", 
            description=message,
            color=0xFF0000
        )
