"""
Gacha Commands Handler - Menangani semua command gacha trading card
Terintegrasi dengan sistem command yang sudah ada tanpa mengubah file lama
"""

import discord
import asyncio
from core.logger import logger
from features.gacha_system.kpop_gacha import KpopGachaSystem

class GachaCommandsHandler:
    def __init__(self):
        """Initialize Gacha Commands Handler"""
        self.gacha_system = None
        self._initialize_gacha_system()
    
    def _initialize_gacha_system(self):
        """Initialize gacha system dengan error handling"""
        try:
            self.gacha_system = KpopGachaSystem()
            logger.info("✅ Gacha system initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize gacha system: {e}")
            self.gacha_system = None
    
    async def handle_gacha_command(self, ctx, user_input):
        """
        Handle semua gacha commands
        
        Args:
            ctx: Discord context
            user_input: Input dari user setelah !sn
        """
        if not self.gacha_system:
            await ctx.send("❌ **Sistem gacha tidak tersedia!**\n"
                          "🔧 **Penyebab:** Missing dependency `Pillow`\n"
                          "💡 **Solusi:** Install dengan `pip install Pillow`\n"
                          "📋 **Atau:** `pip install -r requirements.txt`")
            return
        
        try:
            # Parse command gacha
            parts = user_input.lower().split()
            command = parts[0] if parts else ""
            
            if command == "gacha":
                await self._handle_gacha_subcommand(ctx, parts[1:] if len(parts) > 1 else [])
            else:
                await ctx.send("❌ Command gacha tidak dikenali. Gunakan `!sn gacha help` untuk bantuan.")
                
        except Exception as e:
            logger.error(f"Error in gacha command: {e}")
            await ctx.send("❌ Terjadi error saat memproses command gacha.")
    
    async def _handle_gacha_subcommand(self, ctx, args):
        """Handle subcommand gacha"""
        if not args:
            # Default gacha random
            await self._handle_gacha_random(ctx)
            return
        
        subcommand = args[0].lower()
        
        if subcommand == "help":
            await self._handle_gacha_info(ctx)
        elif subcommand == "info":
            await self._handle_gacha_info(ctx)
        elif subcommand == "group":
            group_name = " ".join(args[1:]) if len(args) > 1 else None
            await self._handle_gacha_by_group(ctx, group_name)
        elif subcommand == "member":
            member_name = " ".join(args[1:]) if len(args) > 1 else None
            await self._handle_gacha_by_member(ctx, member_name)
        elif subcommand == "stats":
            await self._handle_gacha_stats(ctx)
        else:
            # Try to interpret as direct member name or group name
            search_term = " ".join(args)
            await self._handle_smart_gacha(ctx, search_term)
    
    def _get_card_back_path(self, rarity):
        """Get appropriate card back based on rarity"""
        if rarity == "SAR":
            return "assets/templates/Back_SAR.png"
        elif rarity in ["DR", "SR"]:
            return "assets/templates/Back_DRSR.png"
        else:  # Common, Rare
            return "assets/templates/Back.png"
    
    async def _card_flip_animation(self, ctx, card):
        """Card flip animation dengan custom card backs"""
        try:
            import os
            
            # Get appropriate card back
            card_back_path = self._get_card_back_path(card['rarity'])
            
            # Check if card back exists
            if not os.path.exists(card_back_path):
                card_back_path = "assets/templates/Back.png"  # Fallback
            
            # Phase 1: Show card back
            back_embed = discord.Embed(
                title="🎴 Mystery Card",
                description="🔮 **Detecting rarity...**",
                color=0x808080
            )
            
            if os.path.exists(card_back_path):
                back_embed.set_image(url="attachment://card_back.png")
                with open(card_back_path, 'rb') as f:
                    back_file = discord.File(f, "card_back.png")
                    msg = await ctx.send(embed=back_embed, file=back_file)
            else:
                # ASCII fallback if no card back file
                back_embed.description = "🎴 ┌─────────┐\n│  ░░░░░  │\n│  ░SN░   │\n│  ░░░░░  │\n└─────────┘"
                msg = await ctx.send(embed=back_embed)
            
            # Phase 2: Rarity hint
            await asyncio.sleep(1.5)
            rarity_color = self._get_rarity_color(card['rarity'])
            
            if card['rarity'] == "SAR":
                hint_desc = "🌈 **RAINBOW GLOW DETECTED!**\n✨ Something legendary..."
            elif card['rarity'] in ["SR", "DR"]:
                hint_desc = "🥇 **RARE AURA!**\n⭐ High rarity incoming..."
            else:
                hint_desc = "💫 **Card is glowing...**\n🔍 Almost ready..."
            
            hint_embed = discord.Embed(
                title="🔄 Flipping Card...",
                description=hint_desc,
                color=rarity_color
            )
            await msg.edit(embed=hint_embed, attachments=[])
            
            # Phase 3: Final reveal
            await asyncio.sleep(2)
            final_embed = discord.Embed(
                title=f"✨ {card['rarity']} Card Revealed!",
                description=f"**{card['member_name']}** dari **{card['group_name']}**",
                color=rarity_color
            )
            
            # Save and attach final card
            temp_path = self.gacha_system.save_card_temp(card['image'], f"revealed_card")
            if temp_path:
                with open(temp_path, 'rb') as f:
                    final_file = discord.File(f, "revealed_card.png")
                    final_embed.set_image(url="attachment://revealed_card.png")
                    await msg.edit(embed=final_embed, attachments=[final_file])
                
                # Cleanup
                try:
                    os.unlink(temp_path)
                except:
                    pass
            else:
                await msg.edit(embed=final_embed)
                
        except Exception as e:
            logger.error(f"Card flip animation error: {e}")
            # Fallback to simple reveal
            simple_embed = discord.Embed(
                title=f"🎴 {card['member_name']}",
                description=f"✨ **{card['rarity']}** • {card['group_name']}",
                color=self._get_rarity_color(card['rarity'])
            )
            await ctx.send(embed=simple_embed)
    
    async def _handle_gacha_random(self, ctx):
        """Handle gacha pack 5 kartu dengan guaranteed rarity"""
        try:
            async with ctx.typing():
                # Initial suspense message
                suspense_embed = discord.Embed(
                    title="🎴 Opening Gacha Pack...",
                    description="🌟 **Something magical is happening...**\n✨ Shuffling the cards...",
                    color=0x9932cc
                )
                loading_msg = await ctx.send(embed=suspense_embed)
                
                # Add suspense delay
                await asyncio.sleep(2)
                
                # Update to rarity reveal
                rarity_embed = discord.Embed(
                    title="🎴 Revealing Pack Contents...",
                    description="🎯 **Generous Rates Active!** Higher chance for rare cards\n⏳ Generating your cards...",
                    color=0xffd700
                )
                await loading_msg.edit(embed=rarity_embed)
                
                # Another small delay for anticipation
                await asyncio.sleep(1.5)
                
                # Generate 5-card pack
                cards, pack_summary = self.gacha_system.gacha_pack_5()
                
                if cards and len(cards) == 5:
                    # Sort cards by rarity (lowest to highest)
                    rarity_order = {"Common": 1, "Rare": 2, "DR": 3, "SR": 4, "SAR": 5}
                    sorted_cards = sorted(cards, key=lambda x: rarity_order.get(x['rarity'], 0))
                    
                    # Group cards: first 4 in pairs, last (highest rarity) separate
                    card_pairs = []
                    for i in range(0, 4, 2):
                        if i + 1 < len(sorted_cards):
                            card_pairs.append([sorted_cards[i], sorted_cards[i + 1]])
                        else:
                            card_pairs.append([sorted_cards[i]])
                    
                    # Last card (highest rarity) separate
                    highest_rarity_card = sorted_cards[4] if len(sorted_cards) == 5 else None
                    
                    # Send pairs of cards
                    for pair_num, pair in enumerate(card_pairs, 1):
                        pair_embed = discord.Embed(
                            title=f"🎴 Pack Opening - Cards {pair_num*2-1}-{min(pair_num*2, 4)}",
                            description=f"✨ **Revealing cards in rarity order...**",
                            color=0x9932cc
                        )
                        
                        files = []
                        for i, card in enumerate(pair):
                            # Add card info to embed
                            rarity_emoji = self._get_rarity_emoji(card['rarity'])
                            pair_embed.add_field(
                                name=f"Card {(pair_num-1)*2 + i + 1}: {rarity_emoji} {card['rarity']}",
                                value=f"**{card['member_name']}**\n{card['group_name']}",
                                inline=True
                            )
                            
                            # Save card image
                            temp_path = self.gacha_system.save_card_temp(card['image'], f"pair_{pair_num}_card_{i+1}")
                            if temp_path:
                                files.append(discord.File(temp_path, f"card_{(pair_num-1)*2 + i + 1}.png"))
                        
                        if files:
                            await ctx.send(embed=pair_embed, files=files)
                        
                        # Cleanup temp files
                        import os
                        for i in range(len(pair)):
                            try:
                                temp_path = f"temp_pair_{pair_num}_card_{i+1}.png"
                                if os.path.exists(temp_path):
                                    os.unlink(temp_path)
                            except:
                                pass
                        
                        await asyncio.sleep(1.2)  # Delay antar pair
                    
                    # Show highest rarity card last with special treatment
                    if highest_rarity_card:
                        await asyncio.sleep(0.5)
                        
                        special_embed = discord.Embed(
                            title="🌟 SPECIAL REVEAL - Highest Rarity!",
                            description="✨ **The crown jewel of your pack!**",
                            color=self._get_rarity_color(highest_rarity_card['rarity'])
                        )
                        
                        rarity_emoji = self._get_rarity_emoji(highest_rarity_card['rarity'])
                        special_embed.add_field(
                            name=f"🎯 {rarity_emoji} {highest_rarity_card['rarity']} CARD",
                            value=f"**{highest_rarity_card['member_name']}**\n{highest_rarity_card['group_name']}\n\n{self._get_luck_message(highest_rarity_card['rarity'])}",
                            inline=False
                        )
                        
                        # Save special card
                        temp_path = self.gacha_system.save_card_temp(highest_rarity_card['image'], "special_card")
                        if temp_path:
                            special_file = discord.File(temp_path, "special_card.png")
                            await ctx.send(embed=special_embed, file=special_file)
                            
                            # Cleanup
                            import os
                            try:
                                os.unlink(temp_path)
                            except:
                                pass
                        
                        await asyncio.sleep(1.5)  # Pause before final summary
                    
                    # Final summary embed with all cards
                    final_embed = discord.Embed(
                        title="🎉 Pack Complete - Final Summary",
                        description="✨ **Your complete 5-card gacha pack!**",
                        color=0x00FF00
                    )
                    
                    # Count rarities for display
                    rarity_counts = {}
                    for card in cards:
                        rarity = card['rarity']
                        rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1
                    
                    # Add rarity summary
                    rarity_summary = ""
                    for rarity, count in rarity_counts.items():
                        emoji = self._get_rarity_emoji(rarity)
                        rarity_summary += f"{emoji} **{rarity}:** {count}x\n"
                    
                    final_embed.add_field(
                        name="📊 Rarity Distribution",
                        value=rarity_summary,
                        inline=True
                    )
                    
                    # Add pack contents (in original order)
                    pack_contents = ""
                    for i, card in enumerate(cards, 1):
                        emoji = self._get_rarity_emoji(card['rarity'])
                        pack_contents += f"{i}. {emoji} **{card['member_name']}** ({card['group_name']})\n"
                    
                    final_embed.add_field(
                        name="📦 Pack Contents",
                        value=pack_contents,
                        inline=True
                    )
                    
                    # Calculate total luck
                    total_luck = self._calculate_pack_luck(cards)
                    final_embed.add_field(
                        name="🍀 Pack Luck",
                        value=total_luck,
                        inline=True
                    )
                    
                    final_embed.set_footer(
                        text=f"SN Fun Bot • Requested by {ctx.author.display_name}",
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else None
                    )
                    
                    # Send final summary
                    await ctx.send(embed=final_embed)
                else:
                    error_embed = discord.Embed(
                        title="❌ Pack Generation Failed",
                        description=pack_summary,
                        color=0xff0000
                    )
                    await loading_msg.edit(embed=error_embed)
                    
        except Exception as e:
            logger.error(f"Error in gacha pack: {e}")
            error_embed = discord.Embed(
                title="❌ System Error",
                description="Gagal melakukan gacha pack.",
                color=0xff0000
            )
            await ctx.send(embed=error_embed)
    
    async def _handle_gacha_by_group(self, ctx, group_name):
        """Handle gacha by group"""
        if not group_name:
            await ctx.send("❌ Nama grup tidak boleh kosong. Contoh: `!sn gacha group BLACKPINK`")
            return
        
        try:
            async with ctx.typing():
                # Initial suspense for group gacha
                suspense_embed = discord.Embed(
                    title=f"🎴 Searching {group_name} Members...",
                    description="🔍 **Scanning member database...**\n✨ Who will you get?",
                    color=0x9932cc
                )
                loading_msg = await ctx.send(embed=suspense_embed)
                
                # Add suspense delay
                await asyncio.sleep(1.5)
                
                # Update to generation message
                loading_embed = discord.Embed(
                    title=f"🎴 Generating {group_name} Card...",
                    description="🎨 **Creating your trading card...**\n⏳ Rendering in progress...",
                    color=0x00ff00
                )
                await loading_msg.edit(embed=loading_embed)
                
                # Small delay for rendering anticipation
                await asyncio.sleep(1)
                
                # Generate gacha by group
                card_image, card_data = self.gacha_system.gacha_by_group(group_name)
                
                if card_image:
                    # Parse card data untuk card flip animation
                    lines = card_data.split('\n')
                    member_info = lines[0].replace('🎴 **', '').replace('**', '').split(' dari ')
                    member_name = member_info[0]
                    actual_group = member_info[1] if len(member_info) > 1 else group_name
                    rarity = lines[1].replace('✨ **Rarity:** ', '') if len(lines) > 1 else "Unknown"
                    
                    # Create card object for animation
                    card = {
                        'member_name': member_name,
                        'group_name': actual_group,
                        'rarity': rarity,
                        'image': card_image
                    }
                    
                    # Show card flip animation
                    await self._card_flip_animation(ctx, card)
                    return
                else:
                    error_embed = discord.Embed(
                        title="❌ Group Gacha Failed",
                        description=card_data,
                        color=0xff0000
                    )
                    await loading_msg.edit(embed=error_embed)
                    
        except Exception as e:
            logger.error(f"Error in gacha by group: {e}")
            error_embed = discord.Embed(
                title="❌ System Error",
                description=f"Gagal melakukan gacha untuk grup {group_name}.",
                color=0xff0000
            )
            await ctx.send(embed=error_embed)
    
    async def _handle_gacha_by_member(self, ctx, member_name):
        """Handle gacha by member"""
        if not member_name:
            await ctx.send("❌ Nama member tidak boleh kosong. Contoh: `!sn gacha member Jennie`")
            return
        
        try:
            async with ctx.typing():
                # Initial suspense for member gacha
                suspense_embed = discord.Embed(
                    title=f"🎴 Searching for {member_name}...",
                    description="🔍 **Locating member in database...**\n✨ Preparing something special...",
                    color=0x9932cc
                )
                loading_msg = await ctx.send(embed=suspense_embed)
                
                # Add suspense delay
                await asyncio.sleep(1.5)
                
                # Update to card generation
                generation_embed = discord.Embed(
                    title=f"🎴 Creating {member_name}'s Card...",
                    description="🎨 **Rendering trading card...**\n⏳ Adding final touches...",
                    color=0x00ff00
                )
                await loading_msg.edit(embed=generation_embed)
                
                # Small delay for rendering anticipation
                await asyncio.sleep(1)
                
                # Generate gacha by member
                card_image, card_data = self.gacha_system.gacha_by_member(member_name)
                
                if card_image:
                    # Parse card data untuk card flip animation
                    lines = card_data.split('\n')
                    member_info = lines[0].replace('🎴 **', '').replace('**', '').split(' dari ')
                    actual_member = member_info[0]
                    group_name = member_info[1] if len(member_info) > 1 else "Unknown"
                    rarity = lines[1].replace('✨ **Rarity:** ', '') if len(lines) > 1 else "Unknown"
                    
                    # Create card object for animation
                    card = {
                        'member_name': actual_member,
                        'group_name': group_name,
                        'rarity': rarity,
                        'image': card_image
                    }
                    
                    # Show card flip animation
                    await self._card_flip_animation(ctx, card)
                    return
                else:
                    error_embed = discord.Embed(
                        title="❌ Member Gacha Failed",
                        description=card_data,
                        color=0xff0000
                    )
                    await loading_msg.edit(embed=error_embed)
                    
        except Exception as e:
            logger.error(f"Error in gacha by member: {e}")
            error_embed = discord.Embed(
                title="❌ System Error",
                description=f"Gagal melakukan gacha untuk member {member_name}.",
                color=0xff0000
            )
            await ctx.send(embed=error_embed)
    
    async def _handle_gacha_info(self, ctx):
        """Handle gacha info command - comprehensive gacha system information"""
        try:
            embed = discord.Embed(
                title="🎴 K-pop Gacha Trading Cards",
                description="Sistem gacha K-pop dengan **Generous Rates** untuk engagement maksimal!",
                color=0xFF6B9D  # Pink color
            )
            
            # Database Statistics
            if self.gacha_system and self.gacha_system.members_data:
                total_members = len(self.gacha_system.members_data)
                total_photos = sum(len(member.get('photos', [])) for member in self.gacha_system.members_data.values())
                
                # Count unique groups
                groups = set()
                for member_data in self.gacha_system.members_data.values():
                    if 'group' in member_data:
                        groups.add(member_data['group'])
                total_groups = len(groups)
                
                stats_text = f"""📊 **{total_groups:,}** K-pop Groups
👥 **{total_members:,}** Total Idols  
📸 **{total_photos:,}** Available Photos
🎴 **350x540px** Card Resolution"""
                
                embed.add_field(
                    name="📈 Database Statistics",
                    value=stats_text,
                    inline=True
                )
            
            # Probability Rates (GENEROUS MODE)
            probability_text = """🟢 **Common:** 35%
🔵 **Rare:** 35%
🟣 **DR:** 20%
🟠 **SR:** 8%
🔴 **SAR:** 2%

✨ **Generous Mode Active!**"""
            
            embed.add_field(
                name="🎲 Probability Rates",
                value=probability_text,
                inline=True
            )
            
            # Available Commands
            commands_text = """• `!sn gacha` 🎲 Random 5-card pack
• `!sn gacha [group]` 🎵 Group gacha
• `!sn gacha [member]` 👤 Member gacha"""
            
            embed.add_field(
                name="🎯 Available Commands",
                value=commands_text,
                inline=False
            )
            
            # Tips & Features
            tips_text = """💡 **Progressive Loading** untuk mobile
🎨 **Unique Design** per rarity level
🚀 **Optimized Performance** dengan caching
📱 **Discord Mobile** compatible"""
            
            embed.add_field(
                name="💡 Features & Tips",
                value=tips_text,
                inline=False
            )
            
            embed.set_footer(text="SN Fun Bot • Generous rates untuk better engagement! 🎉")
            
            await ctx.send(embed=embed)
            logger.info("Gacha info command executed")
            
        except Exception as e:
            logger.error(f"Error in gacha info: {e}")
            await ctx.send("❌ Gagal menampilkan info gacha.")
    
    async def _handle_gacha_stats(self, ctx):
        """Handle gacha stats command"""
        try:
            if not self.gacha_system or not self.gacha_system.members_data:
                await ctx.send("❌ Data gacha tidak tersedia.")
                return
            
            # Calculate statistics
            total_members = len(self.gacha_system.members_data)
            total_photos = sum(len(member.get('photos', [])) for member in self.gacha_system.members_data.values())
            
            # Group statistics
            groups = {}
            for member_info in self.gacha_system.members_data.values():
                group = member_info.get('group', 'Unknown')
                if group not in groups:
                    groups[group] = {'members': 0, 'photos': 0}
                groups[group]['members'] += 1
                groups[group]['photos'] += len(member_info.get('photos', []))
            
            # Top groups by photos
            top_groups = sorted(groups.items(), key=lambda x: x[1]['photos'], reverse=True)[:5]
            
            embed = discord.Embed(
                title="📊 Gacha System Statistics",
                description="Statistik lengkap sistem gacha trading card",
                color=0x00FF7F  # Green color
            )
            
            # General stats
            general_stats = f"""• **Total Members:** {total_members:,}
• **Total Photos:** {total_photos:,}
• **Total Groups:** {len(groups):,}
• **Avg Photos/Member:** {total_photos/total_members:.1f}"""
            
            embed.add_field(
                name="🎯 General Statistics",
                value=general_stats,
                inline=False
            )
            
            # Top groups
            top_groups_text = ""
            for i, (group, stats) in enumerate(top_groups, 1):
                top_groups_text += f"{i}. **{group}** - {stats['members']} members, {stats['photos']} photos\n"
            
            embed.add_field(
                name="🏆 Top 5 Groups (by photos)",
                value=top_groups_text,
                inline=False
            )
            
            # Card specifications
            specs_text = """📐 **Ukuran Kartu:** 350x540px
🖼️ **Area Foto:** 290x440px (pre-cropped)
🎨 **Border:** 15px gradient dengan radial background
📝 **Font:** Gill Sans Bold Italic
✨ **FullArt:** Rainbow holo overlay + sparkle effects
🎯 **Rarity Text:** Posisi dinamis (Common/Rare: bawah kiri, Epic/Legendary: atas kanan)"""
            
            embed.add_field(
                name="📈 Card Specifications",
                value=specs_text,
                inline=False
            )
            
            # Rarity rates (NEW SYSTEM)
            rarity_rates = """• **Common:** 50% chance
• **Rare:** 30% chance
• **DR:** 15% chance
• **SR:** 4% chance
• **SAR:** 1% chance"""
            
            embed.add_field(
                name="✨ Rarity Rates",
                value=rarity_rates,
                inline=True
            )
            
            # System info
            system_info = """• **Source:** Google Drive
• **Format:** 350x540px cards
• **Effects:** Gradients, holo, sparkles
• **Cache:** Redis integration"""
            
            embed.add_field(
                name="⚙️ System Info",
                value=system_info,
                inline=True
            )
            
            embed.set_footer(text="SN Fun Bot • Real-time statistics")
            
            await ctx.send(embed=embed)
            logger.info("Gacha stats command executed")
            
        except Exception as e:
            logger.error(f"Error in gacha stats: {e}")
            await ctx.send("❌ Gagal menampilkan statistik gacha.")
    
    async def _handle_smart_gacha(self, ctx, search_term):
        """Handle smart gacha - detect if member name or group name"""
        try:
            async with ctx.typing():
                loading_msg = await ctx.send(f"🔍 Mencari {search_term}...")
                
                # First try as member name
                member_result = self.gacha_system.search_member(search_term)
                
                if member_result:
                    # Found member, generate member card
                    card_image, card_data = self.gacha_system.generate_member_card(search_term)
                    
                    if card_image:
                        # Parse card data from message
                        lines = card_data.split('\n')
                        member_info = lines[0].replace('🎴 **', '').replace('**', '').split(' dari ')
                        member_name = member_info[0]
                        group_name = member_info[1] if len(member_info) > 1 else "Unknown"
                        rarity = lines[1].replace('✨ **Rarity:** ', '') if len(lines) > 1 else "Unknown"
                        
                        # Create beautiful embed
                        embed = discord.Embed(
                            title=f"🎴 {search_term} Gacha Result",
                            color=self._get_rarity_color(rarity)
                        )
                        
                        embed.add_field(
                            name="👤 Member",
                            value=f"**{member_name}**",
                            inline=True
                        )
                        
                        embed.add_field(
                            name="🎵 Group", 
                            value=f"**{group_name}**",
                            inline=True
                        )
                        
                        embed.add_field(
                            name="✨ Rarity",
                            value=f"**{rarity}**",
                            inline=True
                        )
                        
                        
                        
                        embed.add_field(
                            name="🎲 Luck",
                            value=self._get_luck_message(rarity),
                            inline=True
                        )
                        
                        embed.set_footer(
                            text=f"SN Fun Bot • Requested by {ctx.author.display_name}",
                            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
                        )
                        
                        # Save kartu ke temporary file
                        temp_path = self.gacha_system.save_card_temp(card_image)
                        
                        if temp_path:
                            # Kirim kartu sebagai file dengan embed
                            with open(temp_path, 'rb') as f:
                                file = discord.File(f, filename="gacha_card.png")
                                embed.set_image(url="attachment://gacha_card.png")
                                await loading_msg.edit(embed=embed, attachments=[file])
                            
                            # Cleanup temporary file
                            import os
                            try:
                                os.unlink(temp_path)
                            except:
                                pass
                        else:
                            await loading_msg.edit(embed=discord.Embed(
                                title="❌ Error",
                                description="Gagal menyimpan kartu gacha.",
                                color=0xff0000
                            ))
                    else:
                        error_embed = discord.Embed(
                            title="❌ Member Card Failed",
                            description=card_data,
                            color=0xff0000
                        )
                        await loading_msg.edit(embed=error_embed)
                else:
                    # Try as group name
                    card_image, card_data = self.gacha_system.gacha_by_group(search_term)
                    
                    if card_image:
                        # Parse card data from message
                        lines = card_data.split('\n')
                        member_info = lines[0].replace('🎴 **', '').replace('**', '').split(' dari ')
                        member_name = member_info[0]
                        group_name = member_info[1] if len(member_info) > 1 else search_term
                        rarity = lines[1].replace('✨ **Rarity:** ', '') if len(lines) > 1 else "Unknown"
                        
                        # Create beautiful embed
                        embed = discord.Embed(
                            title=f"🎴 {search_term} Group Gacha Result",
                            color=self._get_rarity_color(rarity)
                        )
                        
                        embed.add_field(
                            name="👤 Member",
                            value=f"**{member_name}**",
                            inline=True
                        )
                        
                        embed.add_field(
                            name="🎵 Group", 
                            value=f"**{group_name}**",
                            inline=True
                        )
                        
                        embed.add_field(
                            name="✨ Rarity",
                            value=f"**{rarity}**",
                            inline=True
                        )
                        
                        
                        
                        embed.add_field(
                            name="🎲 Luck",
                            value=self._get_luck_message(rarity),
                            inline=True
                        )
                        
                        embed.set_footer(
                            text=f"SN Fun Bot • Requested by {ctx.author.display_name}",
                            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
                        )
                        
                        # Save kartu ke temporary file
                        temp_path = self.gacha_system.save_card_temp(card_image)
                        
                        if temp_path:
                            # Kirim kartu sebagai file dengan embed
                            with open(temp_path, 'rb') as f:
                                file = discord.File(f, filename="gacha_card.png")
                                embed.set_image(url="attachment://gacha_card.png")
                                await loading_msg.edit(embed=embed, attachments=[file])
                            
                            # Cleanup temporary file
                            import os
                            try:
                                os.unlink(temp_path)
                            except:
                                pass
                        else:
                            await loading_msg.edit(embed=discord.Embed(
                                title="❌ Error",
                                description="Gagal menyimpan kartu gacha.",
                                color=0xff0000
                            ))
                    else:
                        # Neither member nor group found
                        error_embed = discord.Embed(
                            title="❌ Search Failed",
                            description=f"**Member atau grup '{search_term}' tidak ditemukan!**",
                            color=0xff0000
                        )
                        
                        error_embed.add_field(
                            name="💡 Tips",
                            value=f"• Coba `!sn gacha member {search_term}` untuk member spesifik\n"
                                  f"• Coba `!sn gacha group {search_term}` untuk grup spesifik\n"
                                  f"• Gunakan `!sn gacha help` untuk bantuan lengkap",
                            inline=False
                        )
                        
                        await loading_msg.edit(embed=error_embed)
                    
        except Exception as e:
            logger.error(f"Error in smart gacha: {e}")
            error_embed = discord.Embed(
                title="❌ System Error",
                description=f"Gagal memproses gacha untuk '{search_term}'.",
                color=0xff0000
            )
            await loading_msg.edit(embed=error_embed)
    
    def _get_rarity_color(self, rarity):
        """Get Discord embed color untuk rarity (NEW SYSTEM)"""
        rarity_colors = {
            "Common": 0x808080,      # Gray
            "Rare": 0x0099ff,        # Blue  
            "DR": 0x9932cc,          # Purple (Double Rare)
            "SR": 0xff0000,          # Red (Super Rare)
            "SAR": 0xffd700          # Gold (Special Art Rare)
        }
        return rarity_colors.get(rarity, 0x00ff00)  # Default green
    
    def _get_luck_message(self, rarity):
        """Get luck message berdasarkan rarity (NEW SYSTEM)"""
        luck_messages = {
            "Common": "🍀 Biasa aja",
            "Rare": "✨ Lumayan beruntung!",
            "DR": "🌟 Wah beruntung banget!",      # Double Rare
            "SR": "💎 SUPER LUCKY!!!",           # Super Rare
            "SAR": "🏆 JACKPOT LEGENDARY!!!"     # Special Art Rare
        }
        return luck_messages.get(rarity, "🎲 Unknown")
    
    def _get_rarity_emoji(self, rarity):
        """Get emoji untuk rarity (NEW SYSTEM)"""
        emojis = {
            "Common": "🥈",
            "Rare": "💙", 
            "DR": "💜",      # Double Rare
            "SR": "❤️",      # Super Rare
            "SAR": "🌈"      # Special Art Rare
        }
        return emojis.get(rarity, "⭐") 
    
    def _calculate_pack_luck(self, cards):
        """Calculate overall pack luck based on rarities"""
        luck_scores = {
            "Common": 1,
            "Rare": 3,
            "DR": 5,        # Double Rare
            "SR": 8,        # Super Rare
            "SAR": 10       # Special Art Rare
        }
        
        total_score = sum(luck_scores.get(card['rarity'], 0) for card in cards)
        
        if total_score >= 25:
            return "🏆 INCREDIBLE LUCK!"
        elif total_score >= 20:
            return "💎 AMAZING LUCK!"
        elif total_score >= 15:
            return "🌟 GREAT LUCK!"
        elif total_score >= 10:
            return "✨ GOOD LUCK!"
        else:
            return "🍀 NORMAL LUCK"
