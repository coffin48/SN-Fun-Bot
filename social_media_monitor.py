"""
Social Media Monitor - Monitor Secret Number social media updates
"""
import asyncio
import aiohttp
import json
import time
import os
from datetime import datetime, timedelta
import hashlib
import logger
import discord

class SocialMediaMonitor:
    def __init__(self, bot_core):
        self.bot_core = bot_core
        self.bot = bot_core.bot
        self.redis_client = getattr(bot_core, 'redis_client', None)
        
        # Secret Number social media accounts (Updated with correct URLs)
        self.accounts = {
            'instagram': {
                'username': 'secretnumber.official',
                'url': 'https://www.instagram.com/secretnumber.official/',
                'api_endpoint': None  # Will use web scraping
            },
            'twitter': {
                'username': '5ecretnumber',
                'url': 'https://x.com/5ecretnumber',
                'api_endpoint': None  # Will use web scraping
            },
            'youtube': {
                'channel_id': 'UCIhPBu7gVRi1tnre0ZfXadg',
                'url': 'https://www.youtube.com/channel/UCIhPBu7gVRi1tnre0ZfXadg',
                'api_endpoint': 'https://www.googleapis.com/youtube/v3/search'
            },
            'tiktok': {
                'username': '@secretnumber.official',
                'url': 'https://www.tiktok.com/@secretnumber.official',
                'api_endpoint': None
            }
        }
        
        # Monitoring settings
        self.check_interval = 300  # 5 minutes
        self.notification_channel_id = os.getenv('SECRET_NUMBER_CHANNEL_ID')
        self.youtube_api_key = os.getenv('YOUTUBE_API_KEY')
        
        # Cache keys for tracking last posts
        self.cache_keys = {
            'instagram': 'sn_monitor:instagram:last_post',
            'twitter': 'sn_monitor:twitter:last_tweet', 
            'youtube': 'sn_monitor:youtube:last_video',
            'tiktok': 'sn_monitor:tiktok:last_post'
        }
        
        logger.logger.info("🔍 Social Media Monitor initialized for Secret Number")
    
    async def start_monitoring(self):
        """Start continuous monitoring loop"""
        logger.logger.info("🚀 Starting Secret Number social media monitoring...")
        
        while True:
            try:
                await self.check_all_platforms()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.logger.error(f"❌ Monitoring error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def check_all_platforms(self):
        """Check all social media platforms for updates"""
        tasks = []
        
        # Check Instagram
        tasks.append(self.check_instagram())
        
        # Check Twitter/X
        tasks.append(self.check_twitter())
        
        # Check YouTube (if API key available)
        if self.youtube_api_key:
            tasks.append(self.check_youtube())
        
        # Check TikTok
        tasks.append(self.check_tiktok())
        
        # Run all checks concurrently
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def check_instagram(self):
        """Monitor Instagram for new posts"""
        try:
            # Use web scraping approach for Instagram
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                # Instagram web endpoint (public posts)
                url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username=secretnumber.official"
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        await self.process_instagram_data(data)
                    else:
                        logger.logger.info(f"🔍 Instagram check status: {response.status}")
                        
        except Exception as e:
            logger.logger.error(f"Instagram monitoring error: {e}")
    
    async def check_twitter(self):
        """Monitor Twitter/X for new tweets"""
        try:
            # Use alternative Twitter scraping or RSS feed
            # For now, implement basic web scraping
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                # Use alternative Twitter scraping or RSS feed
                url = f"https://nitter.net/5ecretnumber/rss"  # Alternative Twitter frontend
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        content = await response.text()
                        await self.process_twitter_rss(content)
                    else:
                        logger.logger.info(f"🔍 Twitter check status: {response.status}")
                        
        except Exception as e:
            logger.logger.error(f"Twitter monitoring error: {e}")
    
    async def check_youtube(self):
        """Monitor YouTube for new videos"""
        try:
            if not self.youtube_api_key:
                return
                
            async with aiohttp.ClientSession() as session:
                # YouTube Data API v3
                url = f"https://www.googleapis.com/youtube/v3/search"
                params = {
                    'key': self.youtube_api_key,
                    'channelId': self.accounts['youtube']['channel_id'],
                    'part': 'snippet',
                    'order': 'date',
                    'maxResults': 5,
                    'type': 'video'
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        await self.process_youtube_data(data)
                    else:
                        logger.logger.info(f"🔍 YouTube check status: {response.status}")
                        
        except Exception as e:
            logger.logger.error(f"YouTube monitoring error: {e}")
    
    async def check_tiktok(self):
        """Monitor TikTok for new posts"""
        try:
            # TikTok is more challenging to scrape, implement basic approach
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                # Use TikTok web interface (limited)
                url = f"https://www.tiktok.com/@secretnumber.official"
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        content = await response.text()
                        await self.process_tiktok_data(content)
                    else:
                        logger.logger.info(f"🔍 TikTok check status: {response.status}")
                        
        except Exception as e:
            logger.logger.error(f"TikTok monitoring error: {e}")
    
    # New methods for getting latest content (for commands)
    async def get_latest_twitter_post(self):
        """Get latest Twitter post data for command display"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                # Use alternative Twitter scraping or RSS feed
                url = f"https://nitter.net/5ecretnumber/rss"
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        content = await response.text()
                        return await self.parse_twitter_rss_for_latest(content)
                    else:
                        return None
                        
        except Exception as e:
            logger.logger.error(f"Get latest Twitter error: {e}")
            return None
    
    async def get_latest_youtube_video(self):
        """Get latest YouTube video data for command display"""
        try:
            if not self.youtube_api_key:
                return None
                
            async with aiohttp.ClientSession() as session:
                url = f"https://www.googleapis.com/youtube/v3/search"
                params = {
                    'key': self.youtube_api_key,
                    'channelId': self.accounts['youtube']['channel_id'],
                    'part': 'snippet',
                    'order': 'date',
                    'maxResults': 1,
                    'type': 'video'
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'items' in data and data['items']:
                            video = data['items'][0]
                            return await self.format_youtube_data(video)
                    return None
                        
        except Exception as e:
            logger.logger.error(f"Get latest YouTube error: {e}")
            return None
    
    async def get_latest_tiktok_post(self):
        """Get latest TikTok post data for command display"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                url = f"https://www.tiktok.com/@secretnumber.official"
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        content = await response.text()
                        return await self.parse_tiktok_html_for_latest(content)
                    else:
                        return None
                        
        except Exception as e:
            logger.logger.error(f"Get latest TikTok error: {e}")
            return None
    
    async def get_latest_instagram_post(self):
        """Get latest Instagram post data for command display"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username=secretnumber.official"
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return await self.parse_instagram_data_for_latest(data)
                    else:
                        return None
                        
        except Exception as e:
            logger.logger.error(f"Get latest Instagram error: {e}")
            return None
    
    # Helper methods for parsing content data
    async def parse_twitter_rss_for_latest(self, rss_content):
        """Parse Twitter RSS for latest tweet data"""
        try:
            import re
            from datetime import datetime
            
            # Extract tweet data from RSS
            title_pattern = r'<title><!\[CDATA\[(.*?)\]\]></title>'
            link_pattern = r'<link>([^<]+)</link>'
            pubdate_pattern = r'<pubDate>([^<]+)</pubDate>'
            
            titles = re.findall(title_pattern, rss_content)
            links = re.findall(link_pattern, rss_content)
            dates = re.findall(pubdate_pattern, rss_content)
            
            if titles and links:
                return {
                    'text': titles[0],
                    'url': links[0],
                    'created_at': dates[0] if dates else 'Unknown',
                    'likes': 0,  # RSS doesn't provide stats
                    'retweets': 0
                }
            return None
            
        except Exception as e:
            logger.logger.error(f"Twitter RSS parsing error: {e}")
            return None
    
    async def format_youtube_data(self, video_data):
        """Format YouTube API data for display"""
        try:
            snippet = video_data['snippet']
            video_id = video_data['id']['videoId']
            
            return {
                'title': snippet['title'],
                'url': f"https://www.youtube.com/watch?v={video_id}",
                'thumbnail': snippet['thumbnails']['high']['url'],
                'published_at': snippet['publishedAt'],
                'views': 0,  # Would need additional API call for stats
                'duration': 'Unknown'  # Would need additional API call
            }
            
        except Exception as e:
            logger.logger.error(f"YouTube data formatting error: {e}")
            return None
    
    async def parse_tiktok_html_for_latest(self, html_content):
        """Parse TikTok HTML for latest video data"""
        try:
            import re
            
            # Extract video data from HTML (simplified approach)
            # This is a basic implementation - TikTok scraping is complex
            video_pattern = r'"id":"(\d+)".*?"desc":"([^"]*)"'
            matches = re.findall(video_pattern, html_content)
            
            if matches:
                video_id, description = matches[0]
                return {
                    'description': description,
                    'url': f"https://www.tiktok.com/@secretnumber.official/video/{video_id}",
                    'thumbnail': None,
                    'likes': 0,
                    'views': 0,
                    'shares': 0
                }
            return None
            
        except Exception as e:
            logger.logger.error(f"TikTok HTML parsing error: {e}")
            return None
    
    async def parse_instagram_data_for_latest(self, data):
        """Parse Instagram API data for latest post"""
        try:
            if 'data' in data and 'user' in data['data']:
                user_data = data['data']['user']
                if 'edge_owner_to_timeline_media' in user_data:
                    posts = user_data['edge_owner_to_timeline_media']['edges']
                    
                    if posts:
                        post = posts[0]['node']
                        
                        # Get caption
                        caption = ""
                        if 'edge_media_to_caption' in post:
                            captions = post['edge_media_to_caption']['edges']
                            if captions:
                                caption = captions[0]['node']['text']
                        
                        return {
                            'caption': caption,
                            'url': f"https://www.instagram.com/p/{post['shortcode']}/",
                            'image_url': post.get('display_url', ''),
                            'likes': post.get('edge_liked_by', {}).get('count', 0),
                            'comments': post.get('edge_media_to_comment', {}).get('count', 0)
                        }
            return None
            
        except Exception as e:
            logger.logger.error(f"Instagram data parsing error: {e}")
            return None
    
    async def process_instagram_data(self, data):
        """Process Instagram API response"""
        try:
            if 'data' in data and 'user' in data['data']:
                user_data = data['data']['user']
                if 'edge_owner_to_timeline_media' in user_data:
                    posts = user_data['edge_owner_to_timeline_media']['edges']
                    
                    if posts:
                        latest_post = posts[0]['node']
                        post_id = latest_post['id']
                        
                        # Check if this is a new post
                        if await self.is_new_content('instagram', post_id):
                            await self.send_instagram_notification(latest_post)
                            
        except Exception as e:
            logger.logger.error(f"Instagram data processing error: {e}")
    
    async def process_twitter_rss(self, rss_content):
        """Process Twitter RSS feed"""
        try:
            # Parse RSS content for latest tweets
            # This is a simplified implementation
            import re
            
            # Extract tweet IDs from RSS
            tweet_pattern = r'<guid[^>]*>([^<]+)</guid>'
            tweets = re.findall(tweet_pattern, rss_content)
            
            if tweets:
                latest_tweet_id = tweets[0]
                
                if await self.is_new_content('twitter', latest_tweet_id):
                    await self.send_twitter_notification(latest_tweet_id, rss_content)
                    
        except Exception as e:
            logger.logger.error(f"Twitter RSS processing error: {e}")
    
    async def process_youtube_data(self, data):
        """Process YouTube API response"""
        try:
            if 'items' in data and data['items']:
                latest_video = data['items'][0]
                video_id = latest_video['id']['videoId']
                
                if await self.is_new_content('youtube', video_id):
                    await self.send_youtube_notification(latest_video)
                    
        except Exception as e:
            logger.logger.error(f"YouTube data processing error: {e}")
    
    async def process_tiktok_data(self, html_content):
        """Process TikTok HTML content"""
        try:
            # Extract video data from HTML (simplified)
            import re
            
            # Look for video IDs in HTML
            video_pattern = r'"id":"(\d+)"'
            videos = re.findall(video_pattern, html_content)
            
            if videos:
                latest_video_id = videos[0]
                
                if await self.is_new_content('tiktok', latest_video_id):
                    await self.send_tiktok_notification(latest_video_id)
                    
        except Exception as e:
            logger.logger.error(f"TikTok data processing error: {e}")
    
    async def is_new_content(self, platform, content_id):
        """Check if content is new by comparing with cached ID"""
        if not self.redis_client:
            return True  # If no Redis, always treat as new
        
        cache_key = self.cache_keys[platform]
        last_id = self.redis_client.get(cache_key)
        
        if last_id and last_id.decode() == content_id:
            return False  # Same content, not new
        
        # Update cache with new content ID
        self.redis_client.set(cache_key, content_id, ex=86400)  # Cache for 24 hours
        return True
    
    async def send_instagram_notification(self, post_data):
        """Send Discord notification for new Instagram post"""
        try:
            caption = post_data.get('edge_media_to_caption', {}).get('edges', [])
            caption_text = caption[0]['node']['text'] if caption else "New post"
            
            # Truncate caption if too long
            if len(caption_text) > 200:
                caption_text = caption_text[:200] + "..."
            
            embed = {
                "title": "📸 Secret Number - New Instagram Post!",
                "description": caption_text,
                "color": 0xE4405F,  # Instagram color
                "url": f"https://www.instagram.com/p/{post_data['shortcode']}/",
                "thumbnail": {"url": post_data.get('display_url', '')},
                "footer": {"text": "Instagram • Secret Number"},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.send_notification(embed)
            logger.logger.info("📸 Sent Instagram notification")
            
        except Exception as e:
            logger.logger.error(f"Instagram notification error: {e}")
    
    async def send_twitter_notification(self, tweet_id, rss_content):
        """Send Discord notification for new Twitter post"""
        try:
            embed = {
                "title": "🐦 Secret Number - New Tweet!",
                "description": "Check out the latest tweet from Secret Number",
                "color": 0x1DA1F2,  # Twitter color
                "url": f"https://x.com/5ecretnumber/status/{tweet_id}",
                "footer": {"text": "Twitter/X • Secret Number"},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.send_notification(embed)
            logger.logger.info("🐦 Sent Twitter notification")
            
        except Exception as e:
            logger.logger.error(f"Twitter notification error: {e}")
    
    async def send_youtube_notification(self, video_data):
        """Send Discord notification for new YouTube video"""
        try:
            snippet = video_data['snippet']
            
            embed = {
                "title": "📺 Secret Number - New YouTube Video!",
                "description": snippet['title'],
                "color": 0xFF0000,  # YouTube color
                "url": f"https://www.youtube.com/watch?v={video_data['id']['videoId']}",
                "thumbnail": {"url": snippet['thumbnails']['medium']['url']},
                "footer": {"text": "YouTube • Secret Number"},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.send_notification(embed)
            logger.logger.info("📺 Sent YouTube notification")
            
        except Exception as e:
            logger.logger.error(f"YouTube notification error: {e}")
    
    async def send_tiktok_notification(self, video_id):
        """Send Discord notification for new TikTok video"""
        try:
            embed = {
                "title": "🎵 Secret Number - New TikTok!",
                "description": "Check out the latest TikTok from Secret Number",
                "color": 0x000000,  # TikTok color
                "url": f"https://www.tiktok.com/@secretnumber.official/video/{video_id}",
                "footer": {"text": "TikTok • Secret Number"},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.send_notification(embed)
            logger.logger.info("🎵 Sent TikTok notification")
            
        except Exception as e:
            logger.logger.error(f"TikTok notification error: {e}")
    
    async def send_notification(self, embed):
        """Send notification to Discord channel"""
        try:
            if not self.notification_channel_id:
                logger.logger.info("🔍 No SECRET_NUMBER_CHANNEL_ID set for notifications")
                return
            
            channel = self.bot.get_channel(int(self.notification_channel_id))
            if not channel:
                logger.logger.error(f"Channel {self.notification_channel_id} not found")
                return
            
            await channel.send(embed=discord.Embed.from_dict(embed))
            
        except Exception as e:
            logger.logger.error(f"Discord notification error: {e}")
    
    async def manual_check(self, platform=None):
        """Manually trigger check for specific platform or all platforms"""
        if platform:
            if platform == 'instagram':
                await self.check_instagram()
            elif platform == 'twitter':
                await self.check_twitter()
            elif platform == 'youtube':
                await self.check_youtube()
            elif platform == 'tiktok':
                await self.check_tiktok()
        else:
            await self.check_all_platforms()
        
        return "✅ Manual check completed"
