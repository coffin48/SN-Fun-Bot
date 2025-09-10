#!/usr/bin/env python3
"""
Social Media Commands Handler untuk Secret Number
Menangani semua command social media: twitter, youtube, tiktok, instagram
"""

import discord
from logger import logger

class SocialMediaCommandsHandler:
    """Handler untuk social media commands"""
    
    def __init__(self, social_monitor):
        self.social_monitor = social_monitor
        
        # Platform configuration
        self.platform_info = {
            'twitter': {
                'name': '🐦 Twitter/X',
                'username': '@5ecretnumber',
                'url': 'https://x.com/5ecretnumber',
                'emoji': '🐦',
                'color': 0x1DA1F2
            },
            'youtube': {
                'name': '📺 YouTube',
                'username': 'Secret Number Official',
                'url': 'https://www.youtube.com/channel/UCIhPBu7gVRi1tnre0ZfXadg',
                'emoji': '📺',
                'color': 0xFF0000
            },
            'tiktok': {
                'name': '🎵 TikTok',
                'username': '@secretnumber.official',
                'url': 'https://www.tiktok.com/@secretnumber.official',
                'emoji': '🎵',
                'color': 0x000000
            },
            'instagram': {
                'name': '📸 Instagram',
                'username': '@secretnumber.official',
                'url': 'https://www.instagram.com/secretnumber.official/',
                'emoji': '📸',
                'color': 0xE4405F
            }
        }
    
    async def handle_platform_command(self, ctx, platform: str):
        """Handle command untuk platform social media tertentu"""
        try:
            # Validate platform
            if platform not in self.platform_info:
                await ctx.send("❌ Platform tidak dikenali")
                return
            
            # Check if social monitor exists
            if not self.social_monitor:
                await ctx.send("❌ Social media monitor tidak tersedia")
                return
            
            info = self.platform_info[platform]
            
            # Create loading embed
            loading_embed = discord.Embed(
                title=f"{info['emoji']} Checking {info['name']}...",
                description=f"Mencari post terbaru dari {info['username']}",
                color=info['color']
            )
            loading_embed.set_footer(text="Secret Number Bot • Loading...")
            loading_message = await ctx.send(embed=loading_embed)
            
            try:
                # Call the appropriate check method and get latest content
                latest_content = await self._call_platform_check(platform)
                
                # Create content embed based on platform and content
                if latest_content:
                    content_embed = await self._create_content_embed(platform, info, latest_content)
                else:
                    content_embed = await self._create_no_content_embed(platform, info)
                
                # Update the loading message
                await loading_message.edit(embed=content_embed)
                
            except Exception as check_error:
                # Create error embed
                error_embed = await self._create_error_embed(platform, info, str(check_error))
                await loading_message.edit(embed=error_embed)
                
        except Exception as e:
            logger.error(f"Social media command error ({platform}): {e}")
            await ctx.send(f"❌ Error: {e}")
    
    async def _call_platform_check(self, platform: str):
        """Call appropriate social media check method and return latest content"""
        if platform == 'twitter':
            return await self.social_monitor.get_latest_twitter_post()
        elif platform == 'youtube':
            return await self.social_monitor.get_latest_youtube_video()
        elif platform == 'tiktok':
            return await self.social_monitor.get_latest_tiktok_post()
        elif platform == 'instagram':
            return await self.social_monitor.get_latest_instagram_post()
        return None
    
    async def _create_content_embed(self, platform: str, info: dict, content: dict):
        """Create embed with actual latest content"""
        if platform == 'twitter':
            return await self._create_twitter_embed(info, content)
        elif platform == 'youtube':
            return await self._create_youtube_embed(info, content)
        elif platform == 'tiktok':
            if is_screenshot:
                embed.description = f"📸 **Screenshot dari TikTok**\n{content_data.get('description', 'Tampilan terbaru dari @secretnumber.official')}"
            else:
                embed.description = f"🎵 **Latest TikTok**\n{content_data.get('description', 'No description available')}"
            
            if content_data.get('likes', 0) > 0:
                embed.add_field(name="❤️ Likes", value=f"{content_data.get('likes', 0):,}", inline=True)
                
        elif platform == 'instagram':
            if is_screenshot:
                embed.description = f"📸 **Screenshot dari Instagram**\n{content_data.get('caption', 'Tampilan terbaru dari @secretnumber.official')}"
            else:
                embed.description = f"📸 **Latest Post**\n{content_data.get('caption', 'No caption available')}"
            
            if content_data.get('likes', 0) > 0:
                embed.add_field(name="❤️ Likes", value=f"{content_data.get('likes', 0):,}", inline=True)
        
        # Add image/screenshot
        image_url = content_data.get('image_url')
        if image_url:
            if is_screenshot:
                # For screenshots, use as main image
                embed.set_image(url=image_url)
                embed.add_field(
                    name="📸 Screenshot Info", 
                    value="Gambar diambil otomatis karena konten tidak bisa di-scrape langsung", 
                    inline=False
                )
            elif await self._is_valid_image_url(image_url):
                # For regular content, use as thumbnail
                embed.set_thumbnail(url=image_url)
        
        # Add timestamp if available
        if content_data.get('timestamp'):
            embed.add_field(name="🕒 Posted", value=content_data['timestamp'], inline=True)
        
        # Different footer for screenshots
        if is_screenshot:
            embed.add_field(
                name="🔗 Lihat Langsung",
                value=f"[Buka {info['name']}]({content_data.get('url', info['url'])}) untuk konten real-time",
                inline=False
            )
            embed.set_footer(text="Secret Number Bot • Screenshot Fallback")
        else:
            embed.add_field(
                name="🔗 View Original",
                value=f"[Open {info['name']}]({content_data.get('url', info['url'])})",
                inline=False
            )
            embed.set_footer(text="Secret Number Bot • Latest Content")
        
        return embed
    
    async def _create_twitter_embed(self, info: dict, tweet_data: dict):
        """Create Twitter embed with latest tweet"""
        embed = discord.Embed(
            title=f"{info['emoji']} Latest Tweet - Secret Number",
            color=info['color'],
            url=tweet_data.get('url', info['url'])
        )
        
        # Tweet content
        tweet_text = tweet_data.get('text', 'No content available')
        if len(tweet_text) > 1024:
            tweet_text = tweet_text[:1021] + "..."
        
        embed.add_field(
            name="📝 Tweet Content",
            value=tweet_text,
            inline=False
        )
        
        # Tweet info
        created_at = tweet_data.get('created_at', 'Unknown time')
        likes = tweet_data.get('likes', 0)
        retweets = tweet_data.get('retweets', 0)
        
        embed.add_field(
            name="📊 Stats",
            value=f"❤️ {likes:,} likes • 🔄 {retweets:,} retweets",
            inline=True
        )
        
        embed.add_field(
            name="🕒 Posted",
            value=created_at,
            inline=True
        )
        
        embed.set_footer(text="Secret Number Bot • Latest Tweet")
        
        return embed
    
    async def _create_youtube_embed(self, info: dict, video_data: dict):
        """Create YouTube embed with latest video"""
        embed = discord.Embed(
            title=f"{info['emoji']} Latest Video - Secret Number",
            description=video_data.get('title', 'No title available'),
            color=info['color'],
            url=video_data.get('url', info['url'])
        )
        
        # Video thumbnail
        thumbnail_url = video_data.get('thumbnail')
        if thumbnail_url:
            embed.set_image(url=thumbnail_url)
        
        # Video info
        published_at = video_data.get('published_at', 'Unknown time')
        views = video_data.get('views', 0)
        duration = video_data.get('duration', 'Unknown')
        
        embed.add_field(
            name="📊 Stats",
            value=f"👀 {views:,} views • ⏱️ {duration}",
            inline=True
        )
        
        embed.add_field(
            name="🕒 Published",
            value=published_at,
            inline=True
        )
        
        embed.set_footer(text="Secret Number Bot • Latest Video")
        
        return embed
    
    async def _create_tiktok_embed(self, info: dict, tiktok_data: dict):
        """Create TikTok embed with latest video"""
        embed = discord.Embed(
            title=f"{info['emoji']} Latest TikTok - Secret Number",
            color=info['color'],
            url=tiktok_data.get('url', info['url'])
        )
        
        # TikTok description
        description = tiktok_data.get('description', 'No description available')
        if len(description) > 1024:
            description = description[:1021] + "..."
        
        embed.add_field(
            name="📝 Description",
            value=description,
            inline=False
        )
        
        # TikTok stats
        likes = tiktok_data.get('likes', 0)
        views = tiktok_data.get('views', 0)
        shares = tiktok_data.get('shares', 0)
        
        embed.add_field(
            name="📊 Stats",
            value=f"❤️ {likes:,} likes • 👀 {views:,} views • 📤 {shares:,} shares",
            inline=False
        )
        
        # Video thumbnail
        thumbnail_url = tiktok_data.get('thumbnail')
        if thumbnail_url:
            embed.set_image(url=thumbnail_url)
        
        embed.set_footer(text="Secret Number Bot • Latest TikTok")
        
        return embed
    
    async def _create_instagram_embed(self, info: dict, post_data: dict):
        """Create Instagram embed with latest post"""
        embed = discord.Embed(
            title=f"{info['emoji']} Latest Post - Secret Number",
            color=info['color'],
            url=post_data.get('url', info['url'])
        )
        
        # Instagram caption
        caption = post_data.get('caption', 'No caption available')
        if len(caption) > 1024:
            caption = caption[:1021] + "..."
        
        embed.add_field(
            name="📝 Caption",
            value=caption,
            inline=False
        )
        
        # Instagram stats
        likes = post_data.get('likes', 0)
        comments = post_data.get('comments', 0)
        
        embed.add_field(
            name="📊 Stats",
            value=f"❤️ {likes:,} likes • 💬 {comments:,} comments",
            inline=True
        )
        
        # Post image
        image_url = post_data.get('image_url')
        if image_url:
            embed.set_image(url=image_url)
        
        embed.set_footer(text="Secret Number Bot • Latest Instagram Post")
        
        return embed
    
    def _is_valid_image_url(self, url):
        """Validate if URL is a valid image URL"""
        if not url:
            return False
        
        # Check if URL has valid image extensions
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        url_lower = url.lower()
        
        # Check for direct image URLs
        if any(ext in url_lower for ext in valid_extensions):
            return True
        
        # Check for common image hosting patterns
        image_hosts = ['imgur.com', 'i.redd.it', 'pbs.twimg.com', 'img.youtube.com']
        if any(host in url_lower for host in image_hosts):
            return True
            
        return False
    
    def _extract_youtube_video_id(self, url):
        """Extract YouTube video ID from URL"""
        import re
        
        if not url:
            return None
            
        # YouTube URL patterns
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
            r'youtube\.com/v/([a-zA-Z0-9_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    async def _create_no_content_embed(self, platform: str, info: dict):
        """Create embed when no content is found"""
        embed = discord.Embed(
            title=f"{info['emoji']} {info['name']} - Secret Number",
            description=f"✅ Berhasil mengecek {info['username']}",
            color=info['color'],
            url=info['url']
        )
        
        # Platform-specific messages
        if platform == 'twitter':
            status_msg = "⚠️ Twitter/X membatasi akses otomatis. Nitter servers mungkin sedang down."
            tips = "💡 **Tips**: Coba lagi nanti atau cek langsung di X/Twitter"
        elif platform == 'instagram':
            status_msg = "⚠️ Instagram membatasi scraping otomatis untuk melindungi privasi user."
            tips = "💡 **Tips**: Instagram Stories dan post terbaru bisa dilihat langsung di app"
        else:
            status_msg = "Tidak ada post baru ditemukan atau belum ada konten tersedia."
            tips = "💡 **Tips**: Coba lagi dalam beberapa menit"
        
        embed.add_field(
            name="ℹ️ Status",
            value=status_msg,
            inline=False
        )
        
        embed.add_field(
            name="🔗 Akses Langsung",
            value=f"[Buka {info['name']}]({info['url']}) • [Secret Number Official](https://linktr.ee/secretnumber_official)",
            inline=False
        )
        
        embed.add_field(
            name=tips.split(':')[0],
            value=tips.split(': ')[1] if ': ' in tips else tips,
            inline=False
        )
        
        embed.set_footer(text="Secret Number Bot • Social Media Check")
        
        return embed
    
    async def _create_error_embed(self, platform: str, info: dict, error_msg: str):
        """Create error embed for platform check"""
        embed = discord.Embed(
            title=f"❌ Error checking {info['name']}",
            description=f"Gagal mengecek {info['username']}",
            color=0xff0000
        )
        
        embed.add_field(
            name="🚨 Error Details",
            value=f"```{error_msg}```",
            inline=False
        )
        
        embed.add_field(
            name="🔗 Manual Check",
            value=f"Silakan cek manual: [Kunjungi {info['name']}]({info['url']})",
            inline=False
        )
        
        embed.add_field(
            name="💡 Troubleshooting",
            value="• Pastikan internet connection stabil\n• Coba lagi dalam beberapa menit\n• Gunakan `!sn monitor status` untuk check system",
            inline=False
        )
        
        embed.set_footer(text="Secret Number Bot • Error Handler")
        
        return embed
    
    def get_available_platforms(self):
        """Get list of available platforms"""
        return list(self.platform_info.keys())
    
    def get_platform_info(self, platform: str):
        """Get platform information"""
        return self.platform_info.get(platform, None)
    
    async def show_all_platforms(self, ctx):
        """Show all available social media platforms"""
        embed = discord.Embed(
            title="📱 Secret Number Social Media",
            description="Pilih platform untuk mengecek post terbaru:",
            color=0x00ff00
        )
        
        for platform, info in self.platform_info.items():
            embed.add_field(
                name=f"{info['emoji']} {info['name']}",
                value=f"**Command**: `!sn {platform}`\n**Account**: {info['username']}\n**URL**: [Visit]({info['url']})",
                inline=True
            )
        
        embed.add_field(
            name="🔄 Monitoring Commands",
            value="`!sn monitor start` - Start auto monitoring\n`!sn monitor status` - Check monitoring status\n`!sn monitor check` - Manual check all platforms",
            inline=False
        )
        
        embed.set_footer(text="Secret Number Bot • Social Media Hub")
        
        await ctx.send(embed=embed)
