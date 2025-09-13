"""
Social Media Monitor - Memantau update dari berbagai platform social media
"""
import asyncio
import aiohttp
import json
import os
import re
import requests
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from core.logger import core.logger
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
        
        logger.info("🔍 Social Media Monitor initialized for Secret Number")
    
    async def start_monitoring(self):
        """Start continuous monitoring loop"""
        logger.info("🚀 Starting Secret Number social media monitoring...")
        
        while True:
            try:
                await self.check_all_platforms()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"❌ Monitoring error: {e}")
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
                        logger.info(f"🔍 Instagram check status: {response.status}")
                        
        except Exception as e:
            logger.error(f"Instagram monitoring error: {e}")
    
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
                        logger.info(f"🔍 Twitter check status: {response.status}")
                        
        except Exception as e:
            logger.error(f"Twitter monitoring error: {e}")
    
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
                        logger.info(f"🔍 YouTube check status: {response.status}")
                        
        except Exception as e:
            logger.error(f"YouTube monitoring error: {e}")
    
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
                        logger.info(f"🔍 TikTok check status: {response.status}")
                        
        except Exception as e:
            logger.error(f"TikTok monitoring error: {e}")
    
    # New methods for getting latest content (for commands)
    async def get_latest_twitter_post(self):
        """Get latest Twitter post data using optimized APIFlash screenshot"""
        try:
            # Try to get actual tweet data first, then add screenshot
            tweet_data = await self._try_get_latest_tweet_data()
            screenshot_url = await self._get_social_media_screenshot('twitter')
            
            if screenshot_url:
                result = {
                    'text': tweet_data.get('text', '📸 Screenshot terbaru dari Twitter @5ecretnumber'),
                    'url': tweet_data.get('url', 'https://twitter.com/5ecretnumber'),
                    'image_url': screenshot_url,
                    'likes': tweet_data.get('likes', 0),
                    'retweets': tweet_data.get('retweets', 0),
                    'is_screenshot': True,
                    'timestamp': tweet_data.get('created_at', 'Just now')
                }
                logger.info(f"✅ Twitter screenshot dengan data: {result['text'][:50]}...")
                return result
            else:
                logger.warning("⚠️ Twitter screenshot failed")
                return tweet_data if tweet_data else None
                
        except Exception as e:
            logger.error(f"Get latest Twitter error: {e}")
            return None
    
    async def _try_get_latest_tweet_data(self):
        """Try to get actual tweet data from various sources"""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                # Try RSS feeds first (most reliable for basic data)
                rss_urls = [
                    'https://rsshub.app/twitter/user/5ecretnumber',
                    'https://nitter.net/5ecretnumber/rss',
                    'https://nitter.privacydev.net/5ecretnumber/rss'
                ]
                
                for rss_url in rss_urls:
                    try:
                        async with session.get(rss_url, headers=headers, timeout=10) as response:
                            if response.status == 200:
                                content = await response.text()
                                tweet_data = await self.parse_twitter_rss_for_latest(content)
                                if tweet_data:
                                    logger.info(f"✅ Tweet data dari RSS: {rss_url}")
                                    return tweet_data
                    except Exception as e:
                        logger.warning(f"RSS {rss_url} failed: {e}")
                        continue
                
                # If RSS fails, return basic fallback data
                return {
                    'text': 'Tweet terbaru dari Secret Number - lihat screenshot untuk detail',
                    'url': 'https://twitter.com/5ecretnumber',
                    'created_at': 'Recent',
                    'likes': 0,
                    'retweets': 0
                }
                        
        except Exception as e:
            logger.error(f"Get tweet data failed: {e}")
            return None
    
    async def _try_direct_twitter_approach(self, session, headers):
        """Try direct Twitter approach as fallback"""
        try:
            # Try Twitter's public API endpoints (limited)
            url = "https://api.twitter.com/1.1/statuses/user_timeline.json"
            params = {
                'screen_name': '5ecretnumber',
                'count': 1,
                'include_rts': False,
                'exclude_replies': True
            }
            
            async with session.get(url, headers=headers, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and len(data) > 0:
                        tweet = data[0]
                        return {
                            'text': tweet.get('text', 'No content'),
                            'url': f"https://twitter.com/5ecretnumber/status/{tweet.get('id_str', '')}",
                            'created_at': tweet.get('created_at', 'Unknown'),
                            'likes': tweet.get('favorite_count', 0),
                            'retweets': tweet.get('retweet_count', 0)
                        }
                        
        except Exception as e:
            logger.error(f"Direct Twitter approach failed: {e}")
        
        # Final fallback - return mock data indicating the issue
        return {
            'text': '⚠️ Unable to fetch latest tweets. Twitter API access limited. Please check @5ecretnumber directly.',
            'url': 'https://x.com/5ecretnumber',
            'created_at': 'Unknown',
            'likes': 0,
            'retweets': 0
        }
    
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
            logger.error(f"Get latest YouTube error: {e}")
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
            logger.error(f"Get latest TikTok error: {e}")
            return None
    
    async def get_latest_instagram_post(self):
        """Get latest Instagram post data using APIFlash screenshot"""
        try:
            # Use APIFlash screenshot instead of scraping
            screenshot_url = await self._get_social_media_screenshot('instagram')
            
            if screenshot_url:
                return {
                    'caption': '📸 Screenshot terbaru dari Instagram @secretnumber.official',
                    'url': 'https://www.instagram.com/secretnumber.official/',
                    'image_url': screenshot_url,
                    'likes': 0,
                    'comments': 0,
                    'is_screenshot': True,
                    'timestamp': 'Just now'
                }
            else:
                logger.warning("⚠️ Instagram screenshot failed")
                return None
                
        except Exception as e:
            logger.error(f"Get latest Instagram error: {e}")
            return None
    
    async def parse_instagram_rss(self, rss_content):
        """Parse Instagram RSS feed"""
        try:
            import re
            
            # Extract from RSS
            title_pattern = r'<title><!\[CDATA\[(.*?)\]\]></title>'
            link_pattern = r'<link>([^<]+)</link>'
            desc_pattern = r'<description><!\[CDATA\[(.*?)\]\]></description>'
            
            titles = re.findall(title_pattern, rss_content, re.DOTALL)
            links = re.findall(link_pattern, rss_content)
            descriptions = re.findall(desc_pattern, rss_content, re.DOTALL)
            
            if len(titles) > 1 and len(links) > 1:  # Skip channel title
                return {
                    'caption': descriptions[1] if len(descriptions) > 1 else titles[1],
                    'url': links[1],
                    'image_url': None,  # RSS biasanya gak ada direct image
                    'likes': 0,
                    'comments': 0
                }
            return None
            
        except Exception as e:
            logger.error(f"Instagram RSS parsing error: {e}")
            return None
    
    async def parse_instagram_html(self, html_content):
        """Parse Instagram from HTML scraping sites"""
        try:
            import re
            
            # Extract post data from HTML
            caption_pattern = r'<div[^>]*class="[^"]*caption[^"]*"[^>]*>(.*?)</div>'
            image_pattern = r'<img[^>]*src="([^"]*)"[^>]*alt="[^"]*post[^"]*"'
            
            captions = re.findall(caption_pattern, html_content, re.DOTALL | re.IGNORECASE)
            images = re.findall(image_pattern, html_content, re.IGNORECASE)
            
            if captions or images:
                caption = captions[0] if captions else "Latest post from Secret Number"
                caption = re.sub(r'<[^>]+>', '', caption).strip()  # Remove HTML tags
                
                return {
                    'caption': caption[:300],  # Limit length
                    'url': 'https://www.instagram.com/secretnumber.official/',
                    'image_url': images[0] if images else None,
                    'likes': 0,
                    'comments': 0
                }
            return None
            
        except Exception as e:
            logger.error(f"Instagram HTML parsing error: {e}")
            return None
    
    async def _create_instagram_fallback(self):
        """Create fallback Instagram data when scraping fails"""
        # Try to get screenshot as fallback
        screenshot_url = await self._get_social_media_screenshot('instagram')
        
        return {
            'caption': '📸 Screenshot terbaru dari Instagram @secretnumber.official',
            'url': 'https://www.instagram.com/secretnumber.official/',
            'image_url': screenshot_url,
            'likes': 0,
            'comments': 0,
            'is_screenshot': True
        }
    
    async def _get_social_media_screenshot(self, platform: str):
        """Get screenshot of social media page with platform-specific optimizations"""
        import os
        import aiohttp
        
        try:
            # Get APIFlash key from environment
            apiflash_key = os.getenv('APIFLASH_KEY')
            if not apiflash_key:
                logger.warning("APIFLASH_KEY not found in environment variables")
                return await self._fallback_screenshot_service(platform)
            
            platform_urls = {
                'instagram': 'https://www.instagram.com/secretnumber.official/',
                'twitter': 'https://twitter.com/5ecretnumber',
                'tiktok': 'https://www.tiktok.com/@secretnumber.official',
                'youtube': 'https://www.youtube.com/@SECRETNUMBER_official'
            }
            
            target_url = platform_urls.get(platform)
            if not target_url:
                logger.warning(f"No URL configured for platform: {platform}")
                return None
            
            # Platform-specific screenshot parameters
            if platform == 'twitter':
                # Twitter-specific: Focus on timeline area, crop to show latest tweets
                screenshot_url = f"https://api.apiflash.com/v1/urltoimage?access_key={apiflash_key}&url={target_url}&format=png&width=1200&height=1200&crop_width=600&crop_height=800&crop_x=0&crop_y=100&delay=5&wait_until=page_loaded&element=[data-testid='primaryColumn']"
            elif platform == 'instagram':
                # Instagram-specific: Focus on posts area
                screenshot_url = f"https://api.apiflash.com/v1/urltoimage?access_key={apiflash_key}&url={target_url}&format=png&width=1200&height=1200&crop_width=600&crop_height=800&crop_x=0&crop_y=150&delay=5&wait_until=page_loaded"
            else:
                # Default screenshot for other platforms
                screenshot_url = f"https://api.apiflash.com/v1/urltoimage?access_key={apiflash_key}&url={target_url}&format=png&width=1200&height=800&crop_width=600&crop_height=400&delay=3&wait_until=page_loaded"
            
            # Test if APIFlash is working
            async with aiohttp.ClientSession() as session:
                async with session.head(screenshot_url, timeout=10) as response:
                    if response.status == 200:
                        logger.info(f"✅ APIFlash screenshot ready for {platform} with optimized settings")
                        return screenshot_url
                    else:
                        logger.warning(f"APIFlash returned status {response.status} for {platform}")
                        return await self._fallback_screenshot_service(platform)
        except Exception as e:
            logger.error(f"APIFlash screenshot failed for {platform}: {e}")
            return await self._fallback_screenshot_service(platform)
    
    async def _fallback_screenshot_service(self, platform: str):
        """Fallback to free screenshot services"""
        import aiohttp
        
        platform_urls = {
            'instagram': 'https://www.instagram.com/secretnumber.official/',
            'twitter': 'https://twitter.com/5ecretnumber',
            'tiktok': 'https://www.tiktok.com/@secretnumber.official',
            'youtube': 'https://www.youtube.com/@SECRETNUMBER_official'
        }
        
        target_url = platform_urls.get(platform)
        if not target_url:
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                # Try s-shot.ru (free service)
                # Security note: Only use for public social media pages
                if target_url.startswith(('https://www.instagram.com/', 'https://twitter.com/', 'https://www.tiktok.com/', 'https://www.youtube.com/')):
                    simple_url = f"https://mini.s-shot.ru/600x400/PNG/600/Z100/?{target_url}"
                    try:
                        async with session.get(simple_url, timeout=15) as response:
                            if response.status == 200:
                                logger.info(f"✅ Screenshot captured from s-shot.ru for {platform}")
                                return simple_url
                    except Exception as e:
                        logger.warning(f"Free screenshot service failed: {e}")
                else:
                    logger.warning(f"⚠️ Screenshot blocked for non-whitelisted URL: {target_url}")
            
            return None
            
        except Exception as e:
            logger.error(f"Fallback screenshot service failed: {e}")
            return None
    
    # Helper methods for parsing content data
    async def parse_twitter_rss_for_latest(self, rss_content):
        """Parse Twitter RSS for latest tweet data"""
        try:
            import re
            from datetime import datetime, timedelta
            
            # Check if RSS content is valid
            if not rss_content or len(rss_content) < 100:
                logger.warning("⚠️ RSS content too short or empty")
                return None
            
            # Extract tweet data from RSS with more robust patterns
            title_pattern = r'<title><!\[CDATA\[(.*?)\]\]></title>'
            link_pattern = r'<link>([^<]+)</link>'
            pubdate_pattern = r'<pubDate>([^<]+)</pubDate>'
            description_pattern = r'<description><!\[CDATA\[(.*?)\]\]></description>'
            
            titles = re.findall(title_pattern, rss_content, re.DOTALL)
            links = re.findall(link_pattern, rss_content)
            dates = re.findall(pubdate_pattern, rss_content)
            descriptions = re.findall(description_pattern, rss_content, re.DOTALL)
            
            logger.info(f"📊 RSS parsing results: {len(titles)} titles, {len(links)} links, {len(dates)} dates")
            
            # Skip the first item (usually channel title) and get actual tweets
            if len(titles) > 1 and len(links) > 1:
                # Get the first actual tweet (index 1, not 0)
                tweet_title = titles[1] if len(titles) > 1 else titles[0]
                tweet_link = links[1] if len(links) > 1 else links[0]
                tweet_date = dates[1] if len(dates) > 1 else (dates[0] if dates else 'Unknown')
                tweet_desc = descriptions[1] if len(descriptions) > 1 else (descriptions[0] if descriptions else tweet_title)
                
                # Clean up the tweet text
                tweet_text = tweet_desc if tweet_desc else tweet_title
                tweet_text = re.sub(r'<[^>]+>', '', tweet_text)  # Remove HTML tags
                tweet_text = tweet_text.strip()
                
                # Parse date to check if it's recent (within 24 hours)
                try:
                    from dateutil import parser as date_parser
                    tweet_datetime = date_parser.parse(tweet_date)
                    now = datetime.now(tweet_datetime.tzinfo)
                    time_diff = now - tweet_datetime
                    
                    if time_diff.days > 1:
                        logger.info(f"⏰ Tweet is {time_diff.days} days old")
                    else:
                        logger.info(f"⏰ Tweet is {time_diff.seconds // 3600} hours old")
                        
                except Exception as date_error:
                    logger.warning(f"⚠️ Date parsing error: {date_error}")
                
                result = {
                    'text': tweet_text[:500],  # Limit length
                    'url': tweet_link,
                    'created_at': tweet_date,
                    'likes': 0,  # RSS doesn't provide stats
                    'retweets': 0
                }
                
                logger.info(f"✅ Parsed tweet: {tweet_text[:100]}...")
                return result
            
            logger.warning("⚠️ No valid tweets found in RSS")
            return None
            
        except Exception as e:
            logger.error(f"Twitter RSS parsing error: {e}")
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
            logger.error(f"YouTube data formatting error: {e}")
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
            logger.error(f"TikTok HTML parsing error: {e}")
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
            logger.error(f"Instagram data parsing error: {e}")
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
            logger.error(f"Instagram data processing error: {e}")
    
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
            logger.error(f"Twitter RSS processing error: {e}")
    
    async def process_youtube_data(self, data):
        """Process YouTube API response"""
        try:
            if 'items' in data and data['items']:
                latest_video = data['items'][0]
                video_id = latest_video['id']['videoId']
                
                if await self.is_new_content('youtube', video_id):
                    await self.send_youtube_notification(latest_video)
                    
        except Exception as e:
            logger.error(f"YouTube data processing error: {e}")
    
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
            logger.error(f"TikTok data processing error: {e}")
    
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
            logger.info("📸 Sent Instagram notification")
            
        except Exception as e:
            logger.error(f"Instagram notification error: {e}")
    
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
            logger.info("🐦 Sent Twitter notification")
            
        except Exception as e:
            logger.error(f"Twitter notification error: {e}")
    
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
            logger.info("📺 Sent YouTube notification")
            
        except Exception as e:
            logger.error(f"YouTube notification error: {e}")
    
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
            logger.info("🎵 Sent TikTok notification")
            
        except Exception as e:
            logger.error(f"TikTok notification error: {e}")
    
    async def send_notification(self, embed):
        """Send notification to Discord channel"""
        try:
            if not self.notification_channel_id:
                logger.info("🔍 No SECRET_NUMBER_CHANNEL_ID set for notifications")
                return
            
            channel = self.bot.get_channel(int(self.notification_channel_id))
            if not channel:
                logger.error(f"Channel {self.notification_channel_id} not found")
                return
            
            await channel.send(embed=discord.Embed.from_dict(embed))
            
        except Exception as e:
            logger.error(f"Discord notification error: {e}")
    
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
