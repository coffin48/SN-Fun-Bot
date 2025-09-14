"""
Maintenance Manager - Sistem maintenance mode untuk bot
Mengelola status maintenance dan notifikasi yang tidak mengganggu channel utama
"""

import os
import json
import discord
from datetime import datetime, timezone
from core.logger import logger

class MaintenanceManager:
    def __init__(self, bot):
        """Initialize Maintenance Manager"""
        self.bot = bot
        self.maintenance_file = "data/maintenance_status.json"
        self.maintenance_channel_id = os.getenv("MAINTENANCE_CHANNEL_ID")  # Channel khusus maintenance
        self.admin_ids = [371695179909824541]  # Admin yang bisa toggle maintenance
        
        # Server configuration
        self.main_server_id = int(os.getenv("MAIN_SERVER_ID", "0"))  # Main production server
        self.test_server_id = int(os.getenv("TEST_SERVER_ID", "0"))  # Test/maintenance server
        
        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)
        
        # Load maintenance status
        self.maintenance_status = self._load_maintenance_status()
    
    def _load_maintenance_status(self):
        """Load maintenance status from file"""
        try:
            if os.path.exists(self.maintenance_file):
                with open(self.maintenance_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Default status
                default_status = {
                    "is_maintenance": False,
                    "maintenance_message": "🔧 Bot sedang dalam maintenance. Mohon tunggu sebentar ya!",
                    "start_time": None,
                    "estimated_end": None,
                    "reason": None,
                    "allowed_commands": ["maintenance", "status"],  # Commands yang masih bisa digunakan saat maintenance
                    "last_updated": None
                }
                self._save_maintenance_status(default_status)
                return default_status
        except Exception as e:
            logger.error(f"Error loading maintenance status: {e}")
            return {
                "is_maintenance": False,
                "maintenance_message": "🔧 Bot sedang dalam maintenance. Mohon tunggu sebentar ya!",
                "start_time": None,
                "estimated_end": None,
                "reason": None,
                "allowed_commands": ["maintenance", "status"],
                "last_updated": None
            }
    
    def _save_maintenance_status(self, status):
        """Save maintenance status to file"""
        try:
            with open(self.maintenance_file, 'w', encoding='utf-8') as f:
                json.dump(status, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving maintenance status: {e}")
    
    def is_maintenance_mode(self, guild_id=None):
        """Check if bot is in maintenance mode for specific server"""
        if not self.maintenance_status.get("is_maintenance", False):
            return False
        
        # If no guild_id provided, return general maintenance status
        if guild_id is None:
            return True
        
        # Main server: disabled during maintenance
        if guild_id == self.main_server_id:
            return True
        
        # Test server: always accessible during maintenance
        if guild_id == self.test_server_id:
            return False
        
        # Other servers: follow general maintenance mode
        return True
    
    def is_admin(self, user_id):
        """Check if user is admin"""
        return user_id in self.admin_ids
    
    def is_command_allowed(self, command_name, guild_id=None):
        """Check if command is allowed during maintenance for specific server"""
        if not self.is_maintenance_mode(guild_id):
            return True
        
        allowed_commands = self.maintenance_status.get("allowed_commands", ["maintenance", "status"])
        return command_name.lower() in [cmd.lower() for cmd in allowed_commands]
    
    async def enable_maintenance(self, reason=None, estimated_duration=None, admin_user_id=None):
        """Enable maintenance mode"""
        if admin_user_id and not self.is_admin(admin_user_id):
            return False, "❌ Hanya admin yang bisa mengaktifkan maintenance mode."
        
        current_time = datetime.now(timezone.utc).isoformat()
        
        self.maintenance_status.update({
            "is_maintenance": True,
            "start_time": current_time,
            "reason": reason or "Maintenance rutin",
            "estimated_end": estimated_duration,
            "last_updated": current_time
        })
        
        self._save_maintenance_status(self.maintenance_status)
        
        # Send maintenance notification
        await self._send_maintenance_notification("start", reason, estimated_duration)
        
        logger.info(f"🔧 Maintenance mode enabled by admin {admin_user_id}")
        return True, f"✅ Maintenance mode diaktifkan.\n🔧 **Main server** (ID: {self.main_server_id}) akan dinonaktifkan\n🧪 **Test server** (ID: {self.test_server_id}) tetap aktif untuk testing"
    
    async def disable_maintenance(self, admin_user_id=None):
        """Disable maintenance mode"""
        if admin_user_id and not self.is_admin(admin_user_id):
            return False, "❌ Hanya admin yang bisa menonaktifkan maintenance mode."
        
        if not self.is_maintenance_mode():
            return False, "ℹ️ Bot tidak sedang dalam maintenance mode."
        
        current_time = datetime.now(timezone.utc).isoformat()
        
        self.maintenance_status.update({
            "is_maintenance": False,
            "start_time": None,
            "estimated_end": None,
            "reason": None,
            "last_updated": current_time
        })
        
        self._save_maintenance_status(self.maintenance_status)
        
        # Send maintenance complete notification
        await self._send_maintenance_notification("end")
        
        logger.info(f"✅ Maintenance mode disabled by admin {admin_user_id}")
        return True, "✅ Maintenance mode dinonaktifkan. Bot kembali normal."
    
    async def _send_maintenance_notification(self, notification_type, reason=None, estimated_duration=None):
        """Send maintenance notification to designated channel"""
        try:
            # Prioritas 1: Channel maintenance khusus
            if self.maintenance_channel_id:
                channel = self.bot.get_channel(int(self.maintenance_channel_id))
                if channel:
                    embed = self._create_maintenance_embed(notification_type, reason, estimated_duration)
                    await channel.send(embed=embed)
                    logger.info(f"📢 Maintenance notification sent to maintenance channel: {channel.name}")
                    return
            
            # Prioritas 2: DM ke admin
            for admin_id in self.admin_ids:
                try:
                    admin_user = self.bot.get_user(admin_id)
                    if admin_user:
                        embed = self._create_maintenance_embed(notification_type, reason, estimated_duration)
                        await admin_user.send(embed=embed)
                        logger.info(f"📩 Maintenance notification sent to admin DM: {admin_user.name}")
                        return
                except Exception as dm_error:
                    logger.warning(f"Failed to send DM to admin {admin_id}: {dm_error}")
                    continue
            
            # Prioritas 3: Log only (tidak mengganggu channel utama)
            logger.info(f"🔧 Maintenance {notification_type}: {reason or 'No reason specified'}")
            
        except Exception as e:
            logger.error(f"Error sending maintenance notification: {e}")
    
    def _create_maintenance_embed(self, notification_type, reason=None, estimated_duration=None):
        """Create maintenance notification embed"""
        if notification_type == "start":
            embed = discord.Embed(
                title="🔧 Maintenance Mode Activated",
                description="Bot telah memasuki maintenance mode.",
                color=0xFFA500  # Orange
            )
            
            if reason:
                embed.add_field(name="📋 Alasan", value=reason, inline=False)
            
            if estimated_duration:
                embed.add_field(name="⏱️ Estimasi Durasi", value=estimated_duration, inline=False)
            
            embed.add_field(
                name="ℹ️ Info",
                value=f"• 🏭 **Main server** (ID: {self.main_server_id}) dinonaktifkan\n• 🧪 **Test server** (ID: {self.test_server_id}) tetap aktif\n• Command terbatas hanya untuk admin\n• Notifikasi ini tidak akan spam channel utama",
                inline=False
            )
            
        else:  # end
            embed = discord.Embed(
                title="✅ Maintenance Complete",
                description="Bot telah keluar dari maintenance mode dan kembali normal.",
                color=0x00FF00  # Green
            )
            
            embed.add_field(
                name="🎉 Status",
                value="Semua fitur bot sudah dapat digunakan kembali!",
                inline=False
            )
        
        embed.timestamp = datetime.now(timezone.utc)
        embed.set_footer(text="SN Fun Bot Maintenance System")
        
        return embed
    
    def get_maintenance_response_embed(self):
        """Get maintenance response embed for users"""
        embed = discord.Embed(
            title="🔧 Bot Sedang Maintenance",
            description=self.maintenance_status.get("maintenance_message", "Bot sedang dalam maintenance."),
            color=0xFFA500
        )
        
        if self.maintenance_status.get("reason"):
            embed.add_field(name="📋 Alasan", value=self.maintenance_status["reason"], inline=False)
        
        if self.maintenance_status.get("estimated_end"):
            embed.add_field(name="⏱️ Estimasi Selesai", value=self.maintenance_status["estimated_end"], inline=False)
        
        embed.add_field(
            name="💡 Info",
            value="Mohon tunggu hingga maintenance selesai. Terima kasih atas pengertiannya! 🙏",
            inline=False
        )
        
        embed.timestamp = datetime.now(timezone.utc)
        embed.set_footer(text="SN Fun Bot akan kembali segera!")
        
        return embed
    
    async def handle_maintenance_command(self, ctx, action=None, *args):
        """Handle maintenance command with server-specific behavior"""
        user_id = ctx.author.id
        guild_id = ctx.guild.id if ctx.guild else None
        
        # Determine server type
        is_main_server = guild_id == self.main_server_id
        is_test_server = guild_id == self.test_server_id
        is_control_server = is_test_server or (guild_id != self.main_server_id and guild_id != 0)
        
        # Main server behavior: Only show status, no control
        if is_main_server:
            await self._handle_main_server_status(ctx)
            return
        
        # Test/maintenance server behavior: Full control (admin only)
        if is_control_server:
            # Check admin permission for control commands
            if not self.is_admin(user_id):
                await ctx.send("❌ Command ini hanya untuk admin.")
                return
            
            await self._handle_control_server_maintenance(ctx, action, args, user_id)
            return
        
        # Other servers: Show status only
        await self._handle_other_server_status(ctx)
    
    async def _handle_main_server_status(self, ctx):
        """Handle maintenance command for main production server - status only"""
        status_embed = discord.Embed(
            title="🏭 SN Fun Bot Status",
            color=0xFFA500 if self.is_maintenance_mode() else 0x00FF00
        )
        
        # Bot status
        if self.is_maintenance_mode():
            status_value = "🔧 **MAINTENANCE MODE**"
            status_embed.add_field(
                name="📊 Bot Status",
                value=status_value,
                inline=False
            )
            
            # Maintenance details
            if self.maintenance_status.get("reason"):
                status_embed.add_field(name="📋 Alasan", value=self.maintenance_status["reason"], inline=False)
            
            if self.maintenance_status.get("estimated_end"):
                status_embed.add_field(name="⏱️ Estimasi Selesai", value=self.maintenance_status["estimated_end"], inline=True)
            
            status_embed.add_field(
                name="ℹ️ Info",
                value="Bot sedang dalam maintenance. Sebagian fitur mungkin tidak tersedia.",
                inline=False
            )
        else:
            status_value = "✅ **ONLINE**"
            status_embed.add_field(
                name="📊 Bot Status",
                value=status_value,
                inline=False
            )
            
            status_embed.add_field(
                name="🎉 Info",
                value="Bot berfungsi normal. Semua fitur tersedia!",
                inline=False
            )
        
        status_embed.add_field(
            name="🌐 Server Info",
            value="🏭 **MAIN PRODUCTION SERVER**\nServer utama untuk pengguna",
            inline=False
        )
        
        await ctx.send(embed=status_embed)
    
    async def _handle_control_server_maintenance(self, ctx, action, args, user_id):
        """Handle maintenance command for test/control servers - simplified control"""
        if not action:
            # Show simple status
            status_embed = discord.Embed(
                title="🧪 Maintenance Control",
                color=0xFFA500 if self.is_maintenance_mode() else 0x00FF00
            )
            
            status_embed.add_field(
                name="📊 Status",
                value="🔧 **MAINTENANCE MODE**" if self.is_maintenance_mode() else "✅ **NORMAL MODE**",
                inline=False
            )
            
            if self.is_maintenance_mode():
                if self.maintenance_status.get("reason"):
                    status_embed.add_field(name="📋 Alasan", value=self.maintenance_status["reason"], inline=False)
                
                if self.maintenance_status.get("start_time"):
                    status_embed.add_field(name="⏰ Dimulai", value=self.maintenance_status["start_time"], inline=True)
            
            status_embed.add_field(
                name="🛠️ Commands",
                value="`!sn maintenance on` - Masuk maintenance mode\n`!sn maintenance done` - Selesai maintenance",
                inline=False
            )
            
            await ctx.send(embed=status_embed)
            
        elif action.lower() == "on":
            # Simple maintenance enable
            reason = " ".join(args) if args else "Maintenance rutin"
            
            success, message = await self.enable_maintenance(reason, None, user_id)
            if success:
                await ctx.send("🔧 **Maintenance mode aktif!**\n"
                             f"📋 Alasan: {reason}\n"
                             f"🏭 Main server dinonaktifkan\n"
                             f"🧪 Test server tetap aktif")
            else:
                await ctx.send(message)
            
        elif action.lower() == "done":
            # Simple maintenance disable
            success, message = await self.disable_maintenance(user_id)
            if success:
                await ctx.send("✅ **Maintenance selesai!**\n"
                             "🎉 Semua server kembali normal\n"
                             "🏭 Main server aktif kembali")
            else:
                await ctx.send(message)
            
        else:
            await ctx.send("❌ Usage: `!sn maintenance on` atau `!sn maintenance done`")
    
    async def _handle_other_server_status(self, ctx):
        """Handle maintenance command for other servers - status only"""
        status_embed = discord.Embed(
            title="🌐 SN Fun Bot Status",
            color=0xFFA500 if self.is_maintenance_mode() else 0x00FF00
        )
        
        status_embed.add_field(
            name="📊 Bot Status",
            value="🔧 **MAINTENANCE MODE**" if self.is_maintenance_mode() else "✅ **ONLINE**",
            inline=False
        )
        
        if self.is_maintenance_mode():
            if self.maintenance_status.get("reason"):
                status_embed.add_field(name="📋 Alasan", value=self.maintenance_status["reason"], inline=False)
            
            status_embed.add_field(
                name="ℹ️ Info",
                value="Bot sedang dalam maintenance. Sebagian fitur mungkin tidak tersedia.",
                inline=False
            )
        else:
            status_embed.add_field(
                name="🎉 Info",
                value="Bot berfungsi normal. Semua fitur tersedia!",
                inline=False
            )
        
        await ctx.send(embed=status_embed)
