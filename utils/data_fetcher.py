"""
Data Fetcher Module - Menangani scraping dan API calls untuk informasi K-pop
"""
import os
import requests
from bs4 import BeautifulSoup
import re
from core.logger import logger
from features.analytics.analytics import BotAnalytics
import time
import asyncio
import aiohttp
import redis
from typing import List, Dict, Optional
import json
from datetime import datetime, timedelta
from io import BytesIO

class DataFetcher:
    def __init__(self, kpop_df=None):
        self.NEWS_API_KEY = os.getenv("NEWS_API_KEY")
        self.CSE_API_KEYS = [os.getenv(f"CSE_API_KEY_{i}") for i in range(1, 4)]
        self.CSE_IDS = [os.getenv(f"CSE_ID_{i}") for i in range(1, 4)]
        self.kpop_df = kpop_df  # Database untuk fallback info
        
        # Redis cache setup
        self.redis_client = None
        try:
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
        except Exception as e:
            logger.warning(f"Redis cache not available: {e}")
        
        # Performance tracking
        self.site_performance = {}
        self.session = None
        
        # Site configuration dengan prioritas dan timeout
        self.scraping_sites = [
            {"url": "https://kprofiles.com/{}-members-profile/", "selector": ".entry-content p", "type": "kprofile_group", "priority": 0.95, "timeout": 8},
            {"url": "https://kprofiles.com/{}-discography/", "selector": ".entry-content", "type": "kprofile_discography", "priority": 0.93, "timeout": 8},
            {"url": "https://kprofiles.com/{}-profile/", "selector": ".entry-content p", "type": "kprofile_solo1", "priority": 0.90, "timeout": 8},
            {"url": "https://kprofiles.com/{}-profile-facts/", "selector": ".entry-content p", "type": "kprofile_solo2", "priority": 0.90, "timeout": 8},
            {"url": "https://kprofiles.com/{}-profile/", "selector": ".entry-content p", "type": "kprofile_member", "priority": 0.88, "timeout": 8},
            {"url": "https://kprofiles.com/{}-profile-and-facts/", "selector": ".entry-content p", "type": "kprofile_member_facts", "priority": 0.88, "timeout": 8},
            {"url": "https://en.wikipedia.org/wiki/{}_discography", "selector": ".mw-parser-output", "type": "wiki_discography", "priority": 0.87, "timeout": 6},
            {"url": "https://en.wikipedia.org/wiki/{}", "selector": ".mw-parser-output p", "type": "wiki", "priority": 0.85, "timeout": 6},
            {"url": "https://id.wikipedia.org/wiki/{}", "selector": ".mw-parser-output p", "type": "wiki", "priority": 0.83, "timeout": 6},
            {"url": "https://en.namu.wiki/w/{}", "selector": ".wiki-paragraph", "type": "namu_english", "priority": 0.75, "timeout": 7},
            {"url": "https://en.namu.wiki/w/{}", "selector": ".wiki-paragraph", "type": "namu_encoded", "priority": 0.75, "timeout": 7},
            {"url": "https://en.namu.wiki/w/{}", "selector": ".wiki-paragraph", "type": "namu_hangul", "priority": 0.75, "timeout": 7},
            {"url": "https://kprofiles.com/?s={}", "selector": ".post-title a", "type": "profile", "priority": 0.70, "timeout": 6},
            {"url": "https://www.dbkpop.com/?s={}", "selector": ".entry-title a", "type": "database", "priority": 0.65, "timeout": 5},
            {"url": "https://www.soompi.com/?s={}", "selector": ".post-title a", "type": "news", "priority": 0.60, "timeout": 5},
            {"url": "https://www.allkpop.com/search/{}", "selector": ".akp_article_title a", "type": "news", "priority": 0.55, "timeout": 5}
        ]
        
        # Mapping grup dengan nama lengkap untuk format extended KProfiles
        self.kprofile_extended_names = {
            "bts": "bts-bangtan-boys",
            "blackpink": "blackpink",
            "twice": "twice",
            "red velvet": "red-velvet",
            "itzy": "itzy",
            "aespa": "aespa",
            "newjeans": "newjeans",
            "ive": "ive",
            "le sserafim": "le-sserafim",
            "gidle": "g-i-dle",
            "(g)i-dle": "g-i-dle",
            "stray kids": "stray-kids",
            "seventeen": "seventeen",
            "secret number": "secret-number",
            "fifty fifty": "fifty-fifty",
            "fiftyfifty": "fifty-fifty",
            "txt": "txt-tomorrow-x-together",
            "tomorrow x together": "txt-tomorrow-x-together",
            "enhypen": "enhypen",
            "nct": "nct",
            "exo": "exo",
            "qwer": "qwer",
            "hearts2hearts": "hearts2hearts"
        }
        
        # Wikipedia URL mapping untuk grup-grup tertentu
        self.wikipedia_mappings = {
            # English Wikipedia
            "secret number": "Secret_Number",
            "secretnumber": "Secret_Number", 
            "aespa": "Aespa",
            "newjeans": "NewJeans",
            "ive": "IVE_(group)",
            "itzy": "Itzy",
            "twice": "Twice_(group)",
            "blackpink": "Blackpink",
            "red velvet": "Red_Velvet_(group)",
            "gidle": "(G)I-dle",
            "(g)i-dle": "(G)I-dle",
            "stray kids": "Stray_Kids",
            "bts": "BTS",
            "seventeen": "Seventeen_(South_Korean_band)",
            "txt": "Tomorrow_X_Together",
            "tomorrow x together": "Tomorrow_X_Together",
            "enhypen": "Enhypen",
            "le sserafim": "Le_Sserafim",
            "fifty fifty": "Fifty_Fifty_(group)",
            "fiftyfifty": "Fifty_Fifty_(group)",
            
            # Indonesian Wikipedia (id.wikipedia.org)
            "aespa_id": "Aespa_(grup_musik)",
            "fifty fifty_id": "Fifty_Fifty", 
            "fiftyfifty_id": "Fifty_Fifty",
            "newjeans_id": "NewJeans",
            "ive_id": "IVE_(grup_musik)",
            "itzy_id": "Itzy",
            "twice_id": "Twice",
            "blackpink_id": "Blackpink",
            "bts_id": "BTS",
            
            # Member individual Wikipedia ID mappings
            "giselle_id": "Giselle_(penyanyi)",
            "lee soodam_id": "Lee_Soodam",
            "soodam_id": "Lee_Soodam",
            "ningning_id": "Ningning"
        }
        
        # Mapping untuk member individual format: {member-name}-{group-name}-profile/
        self.member_group_mappings = {
            # aespa members
            "karina": "karina-aespa",
            "winter": "winter-aespa", 
            "giselle": "giselle-aespa",
            "ningning": "ningning-aespa",
            # QWER members
            "chodan": "chodan-qwer",
            "magenta": "magenta-qwer",
            "siyeon": "siyeon-qwer", 
            "hina": "hina-qwer",
            # SECRET NUMBER members
            "soodam": "soodam-secret-number",
            "dita": "dita-secret-number",
            "jinny": "jinny-secret-number",
            "denise": "denise-secret-number",
            "lea": "lea-secret-number",
            "zuu": "zuu-secret-number",
            # WOOAH members
            "nana": "nana-wooah",
            "wooyeon": "wooyeon-wooah",
            "sora": "sora-wooah",
            "lucy": "lucy-wooah",
            "minseo": "minseo-wooah"
        }
        
        # Mapping grup untuk Namu Wiki dengan berbagai format
        self.namu_wiki_mappings = {
            # Format Hangul (Korean)
            "bts": "%EB%B0%A9%ED%83%84%EC%86%8C%EB%85%84%EB%8B%A8",  # 방탄소년단
            "blackpink": "%EB%B8%94%EB%9E%99%ED%95%91%ED%81%AC",  # 블랙핑크
            "twice": "%ED%8A%B8%EC%99%80%EC%9D%B4%EC%8A%A4",  # 트와이스
            "red velvet": "%EB%A0%88%EB%93%9C%EB%B2%A8%EB%B2%B3",  # 레드벨벳
            "itzy": "%EC%9E%87%EC%A7%80",  # 있지
            "aespa": "%EC%97%90%EC%8A%A4%ED%8C%8C",  # 에스파
            "newjeans": "%EB%89%B4%EC%A7%84%EC%8A%A4",  # 뉴진스
            "ive": "%EC%95%84%EC%9D%B4%EB%B8%8C",  # 아이브
            "le sserafim": "%EB%A5%B4%EC%84%B8%EB%9D%BC%ED%95%8C",  # 르세라핌
            "gidle": "%EC%97%AC%EC%9E%90%EC%95%84%EC%9D%B4%EB%93%A4",  # 여자아이들
            "(g)i-dle": "%EC%97%AC%EC%9E%90%EC%95%84%EC%9D%B4%EB%93%A4",  # 여자아이들
            "stray kids": "%EC%8A%A4%ED%8A%B8%EB%A0%88%EC%9D%B4%ED%82%A4%EC%A6%88",  # 스트레이키즈
            "seventeen": "%EC%84%B8%EB%B8%90%ED%8B%B4",  # 세븐틴
            "txt": "%ED%88%AC%EB%AA%A8%EB%A1%9C%EC%9A%B0%EB%B0%94%EC%9D%B4%ED%88%AC%EA%B2%8C%EB%8D%94",  # 투모로우바이투게더
            "tomorrow x together": "%ED%88%AC%EB%AA%A8%EB%A1%9C%EC%9A%B0%EB%B0%94%EC%9D%B4%ED%88%AC%EA%B2%8C%EB%8D%94",
            "enhypen": "%EC%97%94%ED%95%98%EC%9D%B4%ED%94%88",  # 엔하이픈
            "nct": "%EC%97%94%EC%8B%9C%ED%8B%B0",  # 엔시티
            "exo": "%EC%97%91%EC%86%8C",  # 엑소
            "qwer": "QWER",  # English format
            "secret number": "SECRET%20NUMBER",  # URL encoded space
            "hearts2hearts": "%EC%8A%A4%ED%85%94%EB%9D%BC(Hearts2Hearts)"  # Mixed format
        }
    
    async def fetch_kpop_info(self, query):
        """Fetch comprehensive K-pop information with optimized caching and async processing"""
        logger.info(f"Starting optimized data fetch for: {query}")
        
        # Check cache first
        cache_key = f"kpop_info:{query.lower()}"
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logger.info(f"Cache hit for query: {query}")
            return cached_result
        
        start_time = time.time()
        all_results = []
        
        # Sort sites by priority (highest first)
        sorted_sites = sorted(self.scraping_sites, key=lambda x: x.get('priority', 0.5), reverse=True)
        
        # 1. Async website scraping with early termination
        website_results = await self._scrape_websites_async(query, sorted_sites)
        all_results.extend(website_results)
        logger.info(f"Async scraping completed: {len(website_results)} results")
        
        # Always try to get more sources untuk akurasi maksimal
        # 2. Google Custom Search
        cse_results = await self._fetch_from_cse(query)
        all_results.extend(cse_results)
        
        # 3. NewsAPI
        news_results = await self._fetch_from_newsapi(query)
        all_results.extend(news_results)
        
        # 4. Database fallback info
        database_info = self._get_database_info(query)
        if database_info:
            all_results.append(database_info)
            logger.info(f"Database fallback added: {len(database_info)} characters")
        
        # Clean and combine results
        final_text = self._clean_text(all_results)
        
        # Enhance with discography information if needed
        final_text = self._enhance_discography_content(final_text, query)
        
        # Cache the result
        self._save_to_cache(cache_key, final_text)
        
        total_time = time.time() - start_time
        logger.info(f"Optimized fetch completed in {total_time:.2f}s: {len(final_text)} characters")
        
        return final_text
    
    async def _scrape_websites_async(self, query, sorted_sites):
        """Optimized async scraping dengan concurrent requests dan early termination"""
        results = []
        
        # Create aiohttp session if not exists
        if not self.session:
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=3)
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        
        # Create semaphore untuk limit concurrent requests
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests
        
        # Create tasks for high priority sites first
        high_priority_sites = [site for site in sorted_sites if site.get('priority', 0) >= 0.8]
        medium_priority_sites = [site for site in sorted_sites if 0.6 <= site.get('priority', 0) < 0.8]
        low_priority_sites = [site for site in sorted_sites if site.get('priority', 0) < 0.6]
        
        # Process high priority sites first
        high_priority_results = await self._process_sites_batch(query, high_priority_sites, semaphore)
        results.extend(high_priority_results)
        
        # Check if we have sufficient data from high priority sources
        if self._is_sufficient_data(results):
            logger.info(f"Sufficient data from high priority sites: {len(results)} items")
            return results
        
        # Process medium priority sites
        medium_priority_results = await self._process_sites_batch(query, medium_priority_sites, semaphore)
        results.extend(medium_priority_results)
        
        # Check again
        if self._is_sufficient_data(results):
            logger.info(f"Sufficient data after medium priority: {len(results)} items")
            return results
        
        # Process low priority sites only if still needed
        low_priority_results = await self._process_sites_batch(query, low_priority_sites, semaphore)
        results.extend(low_priority_results)
        
        return results
    
    async def _process_sites_batch(self, query, sites, semaphore):
        """Process a batch of sites concurrently"""
        tasks = []
        for site in sites:
            task = self._scrape_single_site(query, site, semaphore)
            tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and flatten results
        valid_results = []
        for result in results:
            if isinstance(result, list):
                valid_results.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Site scraping failed: {result}")
        
        return valid_results
    
    async def _scrape_single_site(self, query, site, semaphore):
        """Scrape a single site with async/await"""
        async with semaphore:
            try:
                # Format URL berdasarkan tipe situs
                url = self._format_site_url(query, site)
                if not url:
                    return []
                
                site_timeout = site.get('timeout', 5)
                
                async with self.session.get(
                    url, 
                    timeout=aiohttp.ClientTimeout(total=site_timeout),
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                ) as response:
                    if response.status != 200:
                        return []
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")
                    
                    # Extract content berdasarkan site type
                    site_results = self._extract_site_content(soup, site, url, query)
                    
                    # Track performance
                    site_domain = url.split('/')[2]
                    self._update_site_performance(site_domain, True, len(site_results))
                    
                    return site_results
                    
            except Exception as e:
                site_domain = url.split('/')[2] if 'url' in locals() else 'unknown'
                self._update_site_performance(site_domain, False, 0)
                logger.error(f"Async scraping failed for {site_domain}: {e}")
                return []
    
    def _format_site_url(self, query, site):
        """Format URL berdasarkan tipe situs"""
        try:
            formatted_query = query.replace(' ', '+')
            
            if site.get("type") in ["kprofile_group", "kprofile_solo1", "kprofile_solo2", "kprofile_member", "kprofile_member_facts"]:
                # Format khusus untuk KProfiles direct
                formatted_name = query.lower().replace(' ', '-')
                
                if site.get("type") == "kprofile_group" and formatted_name in self.kprofile_extended_names:
                    extended_name = self.kprofile_extended_names[formatted_name]
                    return site["url"].format(extended_name)
                elif site.get("type") in ["kprofile_member", "kprofile_member_facts"] and formatted_name in self.member_group_mappings:
                    member_format = self.member_group_mappings[formatted_name]
                    return site["url"].format(member_format)
                else:
                    return site["url"].format(formatted_name)
                    
            elif site.get("type") in ["namu_english", "namu_encoded", "namu_hangul"]:
                # Format khusus untuk Namu Wiki
                query_lower = query.lower()
                
                if site.get("type") == "namu_english":
                    formatted_name = query.upper() if len(query) <= 4 else query.replace(' ', '%20')
                    return site["url"].format(formatted_name)
                elif site.get("type") == "namu_encoded":
                    formatted_name = query.replace(' ', '%20')
                    return site["url"].format(formatted_name)
                elif site.get("type") == "namu_hangul":
                    if query_lower in self.namu_wiki_mappings:
                        formatted_name = self.namu_wiki_mappings[query_lower]
                        return site["url"].format(formatted_name)
                    else:
                        return None  # Skip jika tidak ada mapping
                        
            elif "allkpop" in site["url"]:
                return site["url"].format(query.replace(' ', '-'))
            else:
                return site["url"].format(formatted_query)
                
        except Exception as e:
            logger.error(f"URL formatting failed: {e}")
            return None
    
    def _extract_site_content(self, soup, site, url, query):
        """Extract content dari soup berdasarkan site type"""
        site_type = site.get("type", "default")
        site_results = []
        
        try:
            if site_type in ["kprofile_group", "kprofile_solo1", "kprofile_solo2", "kprofile_member", "kprofile_member_facts"]:
                # KProfiles direct
                content_elements = soup.select(site["selector"])[:10]
                site_results = [
                    el.get_text().strip() 
                    for el in content_elements 
                    if el.get_text().strip() and len(el.get_text().strip()) > 30
                ]
            
            elif site_type == "wiki":
                # Wikipedia dengan URL mapping
                query_lower = query.lower()
                is_id_wiki = "id.wikipedia.org" in url
                
                # Re-fetch jika ada mapping
                if not is_id_wiki and query_lower in self.wikipedia_mappings:
                    # English Wikipedia mapping sudah dihandle di URL formatting
                    pass
                elif is_id_wiki and f"{query_lower}_id" in self.wikipedia_mappings:
                    # Indonesian Wikipedia mapping sudah dihandle di URL formatting  
                    pass
                
                wiki_paragraphs = soup.select(site["selector"])[:5]
                for p in wiki_paragraphs:
                    text = p.get_text().strip()
                    if (text and len(text) > 50 and 
                        not text.startswith("Coordinates:") and
                        not text.startswith("From Wikipedia") and
                        "disambiguation" not in text.lower()):
                        site_results.append(text)
            
            elif site_type == "profile":
                # KProfiles search
                profile_links = soup.select(site["selector"])[:2]
                for link in profile_links:
                    if link.get('href'):
                        # Simplified - just get title for now to avoid nested requests
                        site_results.append(link.get_text().strip())
            
            else:
                # Default extraction
                elements = soup.select(site["selector"])[:3]
                site_results = [
                    el.get_text().strip() 
                    for el in elements 
                    if el.get_text().strip()
                ]
                
        except Exception as e:
            logger.error(f"Content extraction failed for {site_type}: {e}")
        
        return site_results
    
    def _is_sufficient_data(self, results):
        """Check if we have sufficient quality data to stop scraping"""
        if not results:
            return False
        
        combined_text = " ".join(results)
        text_length = len(combined_text)
        
        # Enhanced quality thresholds untuk akurasi lebih baik
        min_length = 1500  # Turunkan threshold untuk member individual
        quality_keywords = [
            'profile', 'member', 'group', 'debut', 'agency', 'birthday', 'position',
            'instagram', 'full name', 'korean', 'born', 'vocalist', 'rapper', 'dancer'
        ]
        
        # Count quality indicators dengan weight
        quality_score = 0
        for keyword in quality_keywords:
            if keyword.lower() in combined_text.lower():
                if keyword in ['instagram', 'birthday', 'full name']:
                    quality_score += 2  # Higher weight untuk info penting
                else:
                    quality_score += 1
        
        # Lebih permissive untuk member individual
        has_basic_info = any(word in combined_text.lower() for word in ['birthday', 'instagram', 'full name', 'korean'])
        
        # Sufficient jika ada basic info ATAU cukup panjang dengan quality score
        return (text_length >= min_length and quality_score >= 4) or (has_basic_info and text_length >= 800)
    
    def _get_from_cache(self, cache_key):
        """Get data from Redis cache"""
        if not self.redis_client:
            return None
        
        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                return cached_data
        except Exception as e:
            logger.error(f"Cache read error: {e}")
        
        return None
    
    def _save_to_cache(self, cache_key, data, ttl=3600):
        """Save data to Redis cache with TTL"""
        if not self.redis_client or not data:
            return
        
        try:
            # Different TTL based on data type
            if "Database Info:" in data:
                ttl = 86400  # 24 hours for database info
            elif "Wikipedia" in data or "KProfiles" in data:
                ttl = 21600  # 6 hours for reliable sources
            else:
                ttl = 3600   # 1 hour for news/other sources
            
            self.redis_client.setex(cache_key, ttl, data)
            logger.debug(f"Cached data for {cache_key} with TTL {ttl}s")
        except Exception as e:
            logger.error(f"Cache write error: {e}")
    
    def _update_site_performance(self, site_domain, success, result_count):
        """Track site performance for optimization"""
        if site_domain not in self.site_performance:
            self.site_performance[site_domain] = {
                'success_count': 0,
                'fail_count': 0,
                'total_results': 0,
                'avg_results': 0
            }
        
        stats = self.site_performance[site_domain]
        
        if success:
            stats['success_count'] += 1
            stats['total_results'] += result_count
            stats['avg_results'] = stats['total_results'] / stats['success_count']
        else:
            stats['fail_count'] += 1
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _scrape_websites(self, query):
        """Legacy method - kept for backward compatibility"""
        results = []
        formatted_query = query.replace(' ', '+')
        
        for i, site in enumerate(self.scraping_sites, 1):
            try:
                # Format URL berdasarkan tipe situs
                if site.get("type") in ["kprofile_group", "kprofile_solo1", "kprofile_solo2", "kprofile_member", "kprofile_member_facts"]:
                    # Format khusus untuk KProfiles direct: lowercase dan replace space dengan dash
                    formatted_name = query.lower().replace(' ', '-')
                    
                    # Cek apakah ada format extended untuk grup ini
                    if site.get("type") == "kprofile_group" and formatted_name in self.kprofile_extended_names:
                        # Coba format extended dulu (contoh: bts-bangtan-boys-members-profile)
                        extended_name = self.kprofile_extended_names[formatted_name]
                        url = site["url"].format(extended_name)
                    elif site.get("type") in ["kprofile_member", "kprofile_member_facts"] and formatted_name in self.member_group_mappings:
                        # Format member individual: karina-aespa-profile
                        member_format = self.member_group_mappings[formatted_name]
                        url = site["url"].format(member_format)
                    else:
                        url = site["url"].format(formatted_name)
                elif site.get("type") in ["namu_english", "namu_encoded", "namu_hangul"]:
                    # Format khusus untuk Namu Wiki dengan berbagai format
                    query_lower = query.lower()
                    
                    if site.get("type") == "namu_english":
                        # Format English: QWER, TXT, etc.
                        formatted_name = query.upper() if len(query) <= 4 else query.replace(' ', '%20')
                        url = site["url"].format(formatted_name)
                    elif site.get("type") == "namu_encoded":
                        # Format URL encoded: SECRET%20NUMBER
                        formatted_name = query.replace(' ', '%20')
                        url = site["url"].format(formatted_name)
                    elif site.get("type") == "namu_hangul":
                        # Format Hangul: mapping ke Korean names
                        if query_lower in self.namu_wiki_mappings:
                            formatted_name = self.namu_wiki_mappings[query_lower]
                            url = site["url"].format(formatted_name)
                        else:
                            # Skip jika tidak ada mapping Hangul
                            continue
                elif "allkpop" in site["url"]:
                    url = site["url"].format(query.replace(' ', '-'))
                else:
                    url = site["url"].format(formatted_query)
                
                logger.info(f"Scraping site {i}/11: {url.split('/')[2]}")
                
                response = requests.get(
                    url, 
                    timeout=5, 
                    headers={"User-Agent": "Mozilla/5.0"}
                )
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Strategi scraping berdasarkan tipe situs
                site_type = site.get("type", "default")
                site_results = []
                
                if site_type in ["kprofile_group", "kprofile_solo1", "kprofile_solo2", "kprofile_member", "kprofile_member_facts"]:
                    # KProfiles direct: langsung ambil konten dari halaman profil
                    content_elements = soup.select(site["selector"])[:10]
                    site_results = [
                        el.get_text().strip() 
                        for el in content_elements 
                        if el.get_text().strip() and len(el.get_text().strip()) > 30
                    ]
                
                elif site_type == "wiki":
                    # Wikipedia: ambil paragraf utama dengan URL mapping
                    query_lower = query.lower()
                    
                    # Tentukan apakah ini Wikipedia EN atau ID berdasarkan URL
                    is_id_wiki = "id.wikipedia.org" in url
                    
                    # Gunakan mapping Wikipedia jika tersedia
                    if not is_id_wiki and query_lower in self.wikipedia_mappings:
                        # English Wikipedia
                        wiki_title = self.wikipedia_mappings[query_lower]
                        url = f"https://en.wikipedia.org/wiki/{wiki_title}"
                    elif is_id_wiki and f"{query_lower}_id" in self.wikipedia_mappings:
                        # Indonesian Wikipedia
                        wiki_title = self.wikipedia_mappings[f"{query_lower}_id"]
                        url = f"https://id.wikipedia.org/wiki/{wiki_title}"
                    
                    # Re-fetch dengan URL yang sudah di-map
                    if 'wiki_title' in locals():
                        try:
                            response = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
                            soup = BeautifulSoup(response.text, "html.parser")
                        except:
                            pass  # Fallback ke URL original
                    
                    # Extract content dari Wikipedia
                    wiki_paragraphs = soup.select(site["selector"])[:5]
                    site_results = []
                    
                    for p in wiki_paragraphs:
                        text = p.get_text().strip()
                        # Filter paragraf yang relevan dan cukup panjang
                        if (text and len(text) > 50 and 
                            not text.startswith("Coordinates:") and
                            not text.startswith("From Wikipedia") and
                            "disambiguation" not in text.lower()):
                            site_results.append(text)
                
                elif site_type == "profile":
                    # KProfiles search: cari halaman profil langsung
                    profile_links = soup.select(site["selector"])[:2]
                    for link in profile_links:
                        if link.get('href'):
                            profile_url = link.get('href')
                            if not profile_url.startswith('http'):
                                profile_url = "https://kprofiles.com" + profile_url
                            
                            # Scrape halaman profil
                            try:
                                profile_response = requests.get(profile_url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
                                profile_soup = BeautifulSoup(profile_response.text, "html.parser")
                                profile_content = profile_soup.select(".entry-content p")[:8]
                                
                                profile_text = [
                                    p.get_text().strip() 
                                    for p in profile_content 
                                    if p.get_text().strip() and len(p.get_text().strip()) > 30
                                ]
                                site_results.extend(profile_text)
                            except:
                                # Fallback ke judul saja
                                site_results.append(link.get_text().strip())
                
                elif site_type in ["wiki", "namu_english", "namu_encoded", "namu_hangul"]:
                    # Wikipedia/Namu Wiki: ambil konten paragraf
                    if "wikipedia" in url or "namu.wiki" in url:
                        content_elements = soup.select(".mw-parser-output p")[:4]
                    else:
                        content_elements = soup.select(".wiki-paragraph, .wiki-content p")[:4]
                    
                    site_results = [
                        el.get_text().strip() 
                        for el in content_elements 
                        if el.get_text().strip() and len(el.get_text().strip()) > 50
                    ]
                
                elif site_type == "search":
                    # Naver search: ambil snippet hasil pencarian
                    search_results = soup.select(".total_wrap .total_tit, .total_wrap .total_dsc")[:6]
                    site_results = [
                        el.get_text().strip() 
                        for el in search_results 
                        if el.get_text().strip() and len(el.get_text().strip()) > 20
                    ]
                
                else:
                    # Default: judul artikel/berita
                    elements = soup.select(site["selector"])[:3]
                    site_results = [
                        el.get_text().strip() 
                        for el in elements 
                        if el.get_text().strip()
                    ]
                
                results.extend(site_results)
                
                logger.info(f"Site {i}/7 completed: {len(site_results)} results from {url.split('/')[2]}")
                
            except Exception as e:
                logger.error(f"Scraping failed for site {i}/7 ({url.split('/')[2]}): {e}")
        
        return results
    
    async def _fetch_from_cse(self, query):
        """Fetch dari Google Custom Search Engine"""
        results = []
        
        for i, (key, cse_id) in enumerate(zip(self.CSE_API_KEYS, self.CSE_IDS), 1):
            if not key or not cse_id:
                logger.debug(f"CSE API {i}: Keys not configured, skipping")
                continue
            
            try:
                logger.info(f"Calling Google CSE API {i}/3 for: {query}")
                cse_start = time.time()
                
                url = f"https://www.googleapis.com/customsearch/v1?key={key}&cx={cse_id}&q={query}"
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                
                data = response.json()
                items = data.get("items", [])[:3]
                
                cse_results = [
                    f"{item['title']}: {item.get('snippet', '')}"
                    for item in items
                ]
                results.extend(cse_results)
                
                cse_time = time.time() - cse_start
                analytics.track_source_performance("google_cse", True, cse_time)
                
                logger.info(f"CSE API {i}/3 completed: {len(cse_results)} results")
                break  # Success, exit loop
                
            except requests.exceptions.HTTPError as e:
                cse_time = time.time() - cse_start if 'cse_start' in locals() else 0
                analytics.track_source_performance("google_cse", False, cse_time)
                
                if e.response.status_code == 429:
                    logger.warning(f"CSE API {i}/3 rate limited (429), trying next key...")
                    continue  # Try next API key
                else:
                    logger.error(f"CSE API {i}/3 HTTP error: {e}")
            except Exception as e:
                cse_time = time.time() - cse_start if 'cse_start' in locals() else 0
                analytics.track_source_performance("google_cse", False, cse_time)
                logger.error(f"CSE API {i}/3 failed: {e}")
        
        return results
    
    async def _fetch_from_newsapi(self, query):
        """Fetch dari NewsAPI"""
        results = []
        
        if not self.NEWS_API_KEY:
            logger.debug("NewsAPI: Key not configured, skipping")
            return results
            
        try:
            logger.info(f"Calling NewsAPI for: {query}")
            url = f"https://newsapi.org/v2/everything?q={query}+kpop&apiKey={self.NEWS_API_KEY}&pageSize=3"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            articles = data.get("articles", [])
            
            news_results = [
                f"{article['title']}: {article.get('description', '')}"
                for article in articles
                if article.get('title') and article.get('description')
            ]
            results.extend(news_results)
            
            logger.info(f"NewsAPI completed: {len(news_results)} articles")
            
        except Exception as e:
            logger.error(f"NewsAPI failed: {e}")
        
        return results
    
    def _clean_text(self, results):
        """Bersihkan dan gabungkan teks hasil scraping"""
        combined_text = " ".join(results)
        
        # Hapus URL
        clean_text = re.sub(r"http\S+", "", combined_text)
        
        # Hapus HTML tags
        clean_text = re.sub(r"<.*?>", "", clean_text)
        
        # Normalisasi whitespace
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        
        return clean_text
    
    def _get_database_info(self, query):
        """Ambil informasi dari database sebagai fallback"""
        if self.kpop_df is None:
            return ""
        
        database_info = []
        query_lower = query.lower()
        
        # Search for group matches with discography enhancement
        group_matches = self.kpop_df[self.kpop_df['Group'].str.lower() == query_lower]
        if not group_matches.empty:
            group_name = group_matches.iloc[0]['Group']
            members = group_matches['Stage Name'].tolist()
            
            # Add discography placeholder for groups with emoji pointers
            group_info = f"""
Database Info for {group_name}:
👥 Members: {', '.join(members)}
👥 Total Members: {len(members)}
🎵 Discography: Check latest albums and singles from official sources
🎵 Popular Songs: Search for hit tracks and chart performance
            """.strip()
            
            database_info.append(group_info)
        
        # Search for individual member matches
        member_matches = self.kpop_df[self.kpop_df['Stage Name'].str.lower() == query_lower]
        for idx, member in member_matches.iterrows():
            stage_name = member.get('Stage Name', '')
            full_name = member.get('Full Name', '')
            korean_name = member.get('Korean Stage Name', '')
            group = member.get('Group', '')
            
            member_info = f"👤 {stage_name}"
            if full_name and str(full_name).strip() and full_name != 'N/A':
                member_info += f" (Full Name: {full_name})"
            if korean_name and str(korean_name).strip() and korean_name != 'N/A':
                member_info += f" (Korean: {korean_name})"
            if group:
                member_info += f" from {group}"
            
            database_info.append(member_info)
        
        return '\n\n'.join(database_info)
    
    def _enhance_discography_content(self, content, query):
        """Enhance content with discography-specific information"""
        discography_keywords = [
            'album', 'single', 'ep', 'discography', 'track', 'song',
            'release', 'chart', 'billboard', 'music', 'comeback'
        ]
        
        # Check if content already contains discography info
        content_lower = content.lower()
        has_discography = any(keyword in content_lower for keyword in discography_keywords)
        
        if not has_discography:
            # Add discography search suggestion with emoji pointers
            enhancement = f"""

🎵 Discography Information:
For complete {query} discography including albums, singles, and chart performance, 
check official music platforms and databases like:
🎵 Spotify, Apple Music for streaming
🎵 MelOn, Genie for Korean charts
🎵 Billboard for international charts
🎵 Official artist websites and social media
            """.strip()
            
            content += enhancement
        
        return content
    
    async def scrape_kpop_image(self, query):
        """Scrape foto K-pop dari berbagai sumber dengan multiple fallback strategies"""
        # Enhanced image sources dengan lebih banyak fallback
        image_sources = [
            # KProfiles - Primary source
            {"url": "https://kprofiles.com/{}-profile/", "selector": ".wp-image, .entry-content img, .profile-image", "type": "kprofile"},
            {"url": "https://kprofiles.com/{}-members-profile/", "selector": ".wp-image, .entry-content img, .group-image", "type": "kprofile_group"},
            {"url": "https://kprofiles.com/{}-profile-facts/", "selector": ".wp-image, .entry-content img", "type": "kprofile_facts"},
            
            # Wikipedia - Secondary source
            {"url": "https://en.wikipedia.org/wiki/{}", "selector": ".infobox img, .thumbimage, .mw-file-element", "type": "wiki"},
            {"url": "https://id.wikipedia.org/wiki/{}", "selector": ".infobox img, .thumbimage, .mw-file-element", "type": "wiki_id"},
            
            # Google Images via Custom Search (if available)
            {"type": "google_images"},
            
            # Namu Wiki
            {"url": "https://en.namu.wiki/w/{}", "selector": ".wiki-image, .file-wrapper img", "type": "namu"},
            
            # AllKPop
            {"url": "https://www.allkpop.com/search?keyword={}", "selector": ".article-image img, .content img", "type": "allkpop"}
        ]
        
        formatted_query = query.lower().replace(' ', '-')
        
        for source in image_sources:
            try:
                # Handle Google Images search
                if source["type"] == "google_images":
                    image_data = await self._search_google_images(query)
                    if image_data:
                        return image_data
                    continue
                
                # Format URL berdasarkan tipe
                if source["type"] in ["kprofile", "kprofile_group", "kprofile_facts"]:
                    url = source["url"].format(formatted_query)
                elif source["type"] in ["wiki", "wiki_id"]:
                    url = source["url"].format(query.replace(' ', '_'))
                elif source["type"] == "namu":
                    url = source["url"].format(query.replace(' ', '%20'))
                elif source["type"] == "allkpop":
                    url = source["url"].format(query.replace(' ', '+'))
                else:
                    continue
                
                logger.info(f"🖼️ Scraping image from: {url}")
                
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            soup = BeautifulSoup(await response.text(), 'html.parser')
                            
                            # Cari image dengan selector
                            img_tags = soup.select(source["selector"])
                            
                            for img in img_tags[:3]:  # Try first 3 images
                                img_url = img.get('src') or img.get('data-src')
                                if not img_url:
                                    continue
                                
                                # Enhanced image filtering for accuracy
                                skip_patterns = ['icon', 'logo', 'avatar', 'thumb', 'banner', 'header', 'footer', 
                                               'sidebar', 'menu', 'button', 'ad', 'advertisement', 'sponsor']
                                if any(skip in img_url.lower() for skip in skip_patterns):
                                    continue
                                
                                # Skip images that are too generic or unrelated
                                if any(generic in img_url.lower() for generic in ['default', 'placeholder', 'sample']):
                                    continue
                                
                                # Make URL absolute
                                if img_url.startswith('//'):
                                    img_url = 'https:' + img_url
                                elif img_url.startswith('/'):
                                    from urllib.parse import urljoin
                                    img_url = urljoin(url, img_url)
                                
                                # Download image
                                try:
                                    async with session.get(img_url) as img_response:
                                        if img_response.status == 200:
                                            image_data = await img_response.read()
                                            
                                            # Check if image is valid size (> 10KB, < 5MB)
                                            if 10000 < len(image_data) < 5000000:
                                                logger.info(f"✅ Image found: {len(image_data)} bytes from {source['type']}")
                                                return BytesIO(image_data)
                                                
                                except Exception as e:
                                    logger.debug(f"Failed to download image {img_url}: {e}")
                                    continue
                                    
            except Exception as e:
                logger.debug(f"Failed to scrape from {source['type']}: {e}")
                continue
        
        # Final fallback: Try alternative name formats including full names
        alternative_queries = [
            query.replace(' ', ''),  # "New Jeans" -> "NewJeans"
            query.replace('-', ' '),  # "new-jeans" -> "new jeans"
            query.title(),           # "newjeans" -> "Newjeans"
            query.upper(),           # "txt" -> "TXT"
        ]
        
        # Add database-based alternatives for ambiguous names
        ambiguous_names = self._get_ambiguous_name_alternatives(query)
        if ambiguous_names:
            alternative_queries.extend(ambiguous_names)
        
        # Enhanced accuracy with context-aware alternatives
        context_alternatives = self._get_context_aware_alternatives(query)
        if context_alternatives:
            # Insert at beginning for higher priority
            for i, alt in enumerate(context_alternatives):
                alternative_queries.insert(i, alt)
        
        for alt_query in alternative_queries:
            if alt_query != query:  # Skip if same as original
                logger.info(f"🔄 Trying alternative query: {alt_query}")
                result = await self._try_basic_sources(alt_query)
                if result:
                    return result
        
        logger.info(f"❌ No suitable image found for: {query}")
        return None
    
    def _get_ambiguous_name_alternatives(self, query):
        """Generate alternative queries for ambiguous names based on database"""
        if self.kpop_df is None:
            return []
        
        query_lower = query.lower()
        alternatives = []
        
        # Find all members with same stage name
        matches = self.kpop_df[self.kpop_df['Stage Name'].str.lower() == query_lower]
        
        if len(matches) > 1:  # Multiple members with same name
            # Sort by group popularity (prioritize well-known groups)
            popular_groups = ['BLACKPINK', 'IZ*ONE', 'TWICE', 'Red Velvet', 'ITZY', 'aespa', 
                            'VIVIZ', 'Dreamcatcher', 'MAMAMOO', 'Girls Generation', 'SNSD']
            
            # Create alternatives with full names and group context
            for _, member in matches.iterrows():
                stage_name = member.get('Stage Name', '')
                full_name = member.get('Full Name', '')
                group = member.get('Group', '')
                
                if full_name and str(full_name).strip() and full_name != 'N/A':
                    alternatives.append(full_name)
                    alternatives.append(full_name.replace(' ', '-'))
                
                if group:
                    alternatives.append(f"{stage_name} {group}")
                    alternatives.append(f"{stage_name}-{group.lower()}")
                    alternatives.append(f"{group} {stage_name}")
                    
                    # Add specific format for popular groups
                    if group in popular_groups:
                        alternatives.insert(0, f"{stage_name} {group}")  # Prioritize popular groups
        
        # Also check for real names that might match stage names
        real_name_matches = self.kpop_df[
            (self.kpop_df['Full Name'].str.contains(query, case=False, na=False)) |
            (self.kpop_df['Korean Stage Name'].str.contains(query, case=False, na=False))
        ]
        
        for _, member in real_name_matches.iterrows():
            stage_name = member.get('Stage Name', '')
            group = member.get('Group', '')
            if stage_name and group:
                alternatives.append(f"{stage_name} {group}")
                alternatives.append(f"{stage_name}-{group.lower()}")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_alternatives = []
        for alt in alternatives:
            if alt and alt.lower() not in seen:
                seen.add(alt.lower())
                unique_alternatives.append(alt)
        
        return unique_alternatives[:10]  # Limit to top 10 alternatives
    
    def _get_context_aware_alternatives(self, query):
        """Generate context-aware alternatives with popularity and accuracy focus"""
        if self.kpop_df is None:
            return []
        
        query_lower = query.lower()
        alternatives = []
        
        # Find exact match in database
        exact_match = self.kpop_df[self.kpop_df['Stage Name'].str.lower() == query_lower]
        
        if not exact_match.empty:
            # Get the most popular/recent group for this name
            member = exact_match.iloc[0]  # Take first match
            stage_name = member.get('Stage Name', '')
            full_name = member.get('Full Name', '')
            group = member.get('Group', '')
            
            # Priority alternatives based on popularity
            popular_groups = {
                'BLACKPINK': ['Lisa', 'Jennie', 'Jisoo', 'Rosé'],
                'TWICE': ['Nayeon', 'Jeongyeon', 'Momo', 'Sana', 'Jihyo', 'Mina', 'Dahyun', 'Chaeyoung', 'Tzuyu'],
                'IZ*ONE': ['Eunbi', 'Sakura', 'Hyewon', 'Yena', 'Chaeyeon', 'Chaewon', 'Minju', 'Nako', 'Hitomi', 'Yuri', 'Yujin', 'Wonyoung'],
                'aespa': ['Karina', 'Giselle', 'Winter', 'Ningning'],
                'ITZY': ['Yeji', 'Lia', 'Ryujin', 'Chaeryeong', 'Yuna'],
                'Red Velvet': ['Irene', 'Seulgi', 'Wendy', 'Joy', 'Yeri'],
                'VIVIZ': ['Eunha', 'SinB', 'Umji'],
                'Dreamcatcher': ['JiU', 'SuA', 'Siyeon', 'Handong', 'Yoohyeon', 'Dami', 'Gahyeon']
            }
            
            # Check if this member belongs to a popular group
            for pop_group, members in popular_groups.items():
                if stage_name in members:
                    alternatives.extend([
                        f"{stage_name} {pop_group}",
                        f"{stage_name}-{pop_group.lower()}",
                        f"{pop_group} {stage_name}",
                    ])
                    
                    # Add full name if available
                    if full_name and str(full_name).strip() and full_name != 'N/A':
                        alternatives.extend([
                            full_name,
                            f"{full_name} {pop_group}",
                            full_name.replace(' ', '-')
                        ])
                    break
            
            # If not in popular groups, use database group info
            if not alternatives and group:
                alternatives.extend([
                    f"{stage_name} {group}",
                    f"{stage_name}-{group.lower()}",
                    f"{group} {stage_name}"
                ])
                
                if full_name and str(full_name).strip() and full_name != 'N/A':
                    alternatives.extend([
                        full_name,
                        f"{full_name} {group}"
                    ])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_alternatives = []
        for alt in alternatives:
            if alt and alt.lower() not in seen:
                seen.add(alt.lower())
                unique_alternatives.append(alt)
        
        return unique_alternatives[:5]  # Top 5 most relevant alternatives
    
    async def _search_google_images(self, query):
        """Search Google Images using Custom Search API (if configured)"""
        try:
            # Check if Google Custom Search is configured
            google_api_key = os.getenv('GOOGLE_API_KEY')
            google_cx = os.getenv('GOOGLE_SEARCH_CX')
            
            if not google_api_key or not google_cx:
                logger.debug("Google Custom Search not configured, skipping")
                return None
            
            search_url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': google_api_key,
                'cx': google_cx,
                'q': f"{query} kpop idol profile photo",
                'searchType': 'image',
                'num': 5,
                'imgSize': 'medium',
                'imgType': 'photo',
                'safe': 'active'
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(search_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for item in data.get('items', []):
                            img_url = item.get('link')
                            if img_url:
                                try:
                                    async with session.get(img_url) as img_response:
                                        if img_response.status == 200:
                                            image_data = await img_response.read()
                                            
                                            # Validate image size
                                            if 10000 < len(image_data) < 5000000:
                                                logger.info(f"✅ Google Images: {len(image_data)} bytes")
                                                return BytesIO(image_data)
                                except Exception as e:
                                    logger.debug(f"Failed Google image download: {e}")
                                    continue
                                    
        except Exception as e:
            logger.debug(f"Google Images search failed: {e}")
            
        return None
    
    async def _try_basic_sources(self, query):
        """Try basic KProfiles and Wikipedia sources with alternative query"""
        basic_sources = [
            {"url": "https://kprofiles.com/{}-profile/", "selector": ".wp-image, .entry-content img", "type": "kprofile"},
            {"url": "https://en.wikipedia.org/wiki/{}", "selector": ".infobox img, .thumbimage", "type": "wiki"}
        ]
        
        formatted_query = query.lower().replace(' ', '-')
        
        for source in basic_sources:
            try:
                if source["type"] == "kprofile":
                    url = source["url"].format(formatted_query)
                else:
                    url = source["url"].format(query.replace(' ', '_'))
                
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            soup = BeautifulSoup(await response.text(), 'html.parser')
                            img_tags = soup.select(source["selector"])
                            
                            for img in img_tags[:2]:  # Try first 2 images only
                                img_url = img.get('src') or img.get('data-src')
                                if not img_url:
                                    continue
                                
                                # Skip unwanted images
                                if any(skip in img_url.lower() for skip in ['icon', 'logo', 'avatar']):
                                    continue
                                
                                # Make URL absolute
                                if img_url.startswith('//'):
                                    img_url = 'https:' + img_url
                                elif img_url.startswith('/'):
                                    from urllib.parse import urljoin
                                    img_url = urljoin(url, img_url)
                                
                                try:
                                    async with session.get(img_url) as img_response:
                                        if img_response.status == 200:
                                            image_data = await img_response.read()
                                            if 10000 < len(image_data) < 5000000:
                                                logger.info(f"✅ Alternative query success: {query}")
                                                return BytesIO(image_data)
                                except Exception:
                                    continue
                                    
            except Exception:
                continue
                
        return None
