"""
Gacha Commands Handler - Menangani semua command gacha trading card
Terintegrasi dengan sistem command yang sudah ada tanpa mengubah file lama
"""

import discord
import asyncio
from logger import logger
from kpop_gacha import KpopGachaSystem

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
            await self._handle_gacha_help(ctx)
        elif subcommand == "group":
            group_name = " ".join(args[1:]) if len(args) > 1 else None
            await self._handle_gacha_by_group(ctx, group_name)
        elif subcommand == "member":
            member_name = " ".join(args[1:]) if len(args) > 1 else None
            await self._handle_gacha_by_member(ctx, member_name)
        elif subcommand == "stats":
            await self._handle_gacha_stats(ctx)
        else:
            await ctx.send(f"❌ Subcommand `{subcommand}` tidak dikenali. Gunakan `!sn gacha help` untuk bantuan.")
    
    async def _handle_gacha_random(self, ctx):
        """Handle gacha random member"""
        try:
            async with ctx.typing():
                loading_msg = await ctx.send("🎴 Membuka pack gacha...")
                
                # Generate random gacha
                card_image, message = self.gacha_system.gacha_random()
                
                if card_image:
                    # Save kartu ke temporary file
                    temp_path = self.gacha_system.save_card_temp(card_image)
                    
                    if temp_path:
                        # Kirim kartu sebagai file
                        with open(temp_path, 'rb') as f:
                            file = discord.File(f, filename="gacha_card.png")
                            await loading_msg.edit(content=message, attachments=[file])
                        
                        # Cleanup temporary file
                        import os
                        try:
                            os.unlink(temp_path)
                        except:
                            pass
                    else:
                        await loading_msg.edit(content="❌ Gagal menyimpan kartu gacha.")
                else:
                    await loading_msg.edit(content=message)
                    
        except Exception as e:
            logger.error(f"Error in gacha random: {e}")
            await ctx.send("❌ Gagal melakukan gacha random.")
    
    async def _handle_gacha_by_group(self, ctx, group_name):
        """Handle gacha by group"""
        if not group_name:
            await ctx.send("❌ Nama grup tidak boleh kosong. Contoh: `!sn gacha group BLACKPINK`")
            return
        
        try:
            async with ctx.typing():
                loading_msg = await ctx.send(f"🎴 Membuka pack gacha {group_name}...")
                
                # Generate gacha by group
                card_image, message = self.gacha_system.gacha_by_group(group_name)
                
                if card_image:
                    # Save kartu ke temporary file
                    temp_path = self.gacha_system.save_card_temp(card_image)
                    
                    if temp_path:
                        # Kirim kartu sebagai file
                        with open(temp_path, 'rb') as f:
                            file = discord.File(f, filename="gacha_card.png")
                            await loading_msg.edit(content=message, attachments=[file])
                        
                        # Cleanup temporary file
                        import os
                        try:
                            os.unlink(temp_path)
                        except:
                            pass
                    else:
                        await loading_msg.edit(content="❌ Gagal menyimpan kartu gacha.")
                else:
                    await loading_msg.edit(content=message)
                    
        except Exception as e:
            logger.error(f"Error in gacha by group: {e}")
            await ctx.send(f"❌ Gagal melakukan gacha untuk grup {group_name}.")
    
    async def _handle_gacha_by_member(self, ctx, member_name):
        """Handle gacha by member"""
        if not member_name:
            await ctx.send("❌ Nama member tidak boleh kosong. Contoh: `!sn gacha member Jennie`")
            return
        
        try:
            async with ctx.typing():
                loading_msg = await ctx.send(f"🎴 Membuka pack gacha {member_name}...")
                
                # Generate gacha by member
                card_image, message = self.gacha_system.gacha_by_member(member_name)
                
                if card_image:
                    # Save kartu ke temporary file
                    temp_path = self.gacha_system.save_card_temp(card_image)
                    
                    if temp_path:
                        # Kirim kartu sebagai file
                        with open(temp_path, 'rb') as f:
                            file = discord.File(f, filename="gacha_card.png")
                            await loading_msg.edit(content=message, attachments=[file])
                        
                        # Cleanup temporary file
                        import os
                        try:
                            os.unlink(temp_path)
                        except:
                            pass
                    else:
                        await loading_msg.edit(content="❌ Gagal menyimpan kartu gacha.")
                else:
                    await loading_msg.edit(content=message)
                    
        except Exception as e:
            logger.error(f"Error in gacha by member: {e}")
            await ctx.send(f"❌ Gagal melakukan gacha untuk member {member_name}.")
    
    async def _handle_gacha_help(self, ctx):
        """Handle gacha help command"""
        try:
            embed = discord.Embed(
                title="🎴 Gacha Trading Card System",
                description="Sistem gacha K-pop trading card dengan berbagai rarity!",
                color=0xFF6B9D  # Pink color
            )
            
            # Commands section
            commands_text = """• `!sn gacha` 🎲 Random gacha
• `!sn gacha group [nama]` 🎵 Gacha dari grup
• `!sn gacha member [nama]` 👤 Gacha member spesifik
• `!sn gacha stats` 📊 Statistik gacha"""
            
            embed.add_field(
                name="🎯 Commands",
                value=commands_text,
                inline=False
            )
            
            # Rarity section
            rarity_text = """• **Common** (50%) 🥈 Silver gradient border
• **Rare** (30%) 💙 Blue gradient border  
• **Epic** (15%) 💜 Purple gradient border
• **Legendary** (4%) ❤️ Ruby red gradient border
• **FullArt** (1%) 🌈 Holographic rainbow + sparkles"""
            
            embed.add_field(
                name="✨ Rarity System",
                value=rarity_text,
                inline=False
            )
            
            # Examples
            examples_text = """```
!sn gacha
!sn gacha group BLACKPINK
!sn gacha member Jennie
!sn gacha stats
```"""
            
            embed.add_field(
                name="📝 Contoh Commands",
                value=examples_text,
                inline=False
            )
            
            # Database info
            if self.gacha_system and self.gacha_system.members_data:
                total_members = len(self.gacha_system.members_data)
                total_photos = sum(len(member.get('photos', [])) for member in self.gacha_system.members_data.values())
                
                db_info = f"""📊 **Database:**
• {total_members:,} members tersedia
• {total_photos:,} foto total
• 317 K-pop groups
• Google Drive integration"""
                
                embed.add_field(
                    name="💾 Database Info",
                    value=db_info,
                    inline=False
                )
            
            embed.set_footer(text="SN Fun Bot • Gacha Trading Card System")
            
            await ctx.send(embed=embed)
            logger.info("Gacha help command executed")
            
        except Exception as e:
            logger.error(f"Error in gacha help: {e}")
            await ctx.send("❌ Gagal menampilkan help gacha.")
    
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
            
            # Rarity rates
            rarity_rates = """• **Common:** 50% chance
• **Rare:** 30% chance
• **Epic:** 15% chance
• **Legendary:** 4% chance
• **FullArt:** 1% chance"""
            
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
