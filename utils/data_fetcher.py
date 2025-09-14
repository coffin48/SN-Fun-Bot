"""
Data Fetcher Module - Menangani scraping dan API calls untuk informasi K-pop
"""
import os
import requests
from bs4 import BeautifulSoup
import re
import time
import asyncio
import aiohttp
import redis
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from io import BytesIO
from urllib.parse import urljoin
from core.logger import logger

try:
    from features.analytics.analytics import BotAnalytics
    analytics = BotAnalytics()
except ImportError:
    class BotAnalytics:
        def track_source_performance(self, source, success, time_taken): pass
        def track_daily_usage(self): pass
    analytics = BotAnalytics()

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
        
        # Site configuration dengan prioritas dan timeout - TOP 3 MAIN SOURCES PRIORITIZED
        self.scraping_sites = [
            # TOP 3 MAIN SOURCES - Prioritas tertinggi untuk info, trivia, facts
            {"url": "https://kprofiles.com/{}-members-profile/", "selector": ".entry-content p", "type": "kprofile_group", "priority": 1.0, "timeout": 10, "main_source": True},
            {"url": "https://{}.fandom.com/wiki/{}", "selector": ".portable-infobox, .infobox, .mw-parser-output p", "type": "fandom_infobox", "priority": 0.98, "timeout": 10, "main_source": True},
            {"url": "https://kpopping.com/profiles/idol/{}", "selector": ".profile-content, .profile-info", "type": "kpopping_idol", "priority": 0.96, "timeout": 10, "main_source": True},
            
            # SECONDARY SOURCES - Hanya digunakan jika TOP 3 gagal
            {"url": "https://kprofiles.com/{}-discography/", "selector": ".entry-content", "type": "kprofile_discography", "priority": 0.85, "timeout": 8, "main_source": False},
            {"url": "https://kprofiles.com/{}-profile/", "selector": ".entry-content p", "type": "kprofile_solo1", "priority": 0.83, "timeout": 8, "main_source": False},
            {"url": "https://kprofiles.com/{}-profile-facts/", "selector": ".entry-content p", "type": "kprofile_solo2", "priority": 0.83, "timeout": 8, "main_source": False},
            {"url": "https://kprofiles.com/{}-profile/", "selector": ".entry-content p", "type": "kprofile_member", "priority": 0.81, "timeout": 8, "main_source": False},
            {"url": "https://kprofiles.com/{}-profile-and-facts/", "selector": ".entry-content p", "type": "kprofile_member_facts", "priority": 0.81, "timeout": 8, "main_source": False},
            {"url": "https://kpopping.com/profiles/group/{}", "selector": ".profile-content, .profile-info", "type": "kpopping_group", "priority": 0.80, "timeout": 7, "main_source": False},
            {"url": "https://kpopping.com/profiles/soloist/{}", "selector": ".profile-content, .profile-info", "type": "kpopping_solo", "priority": 0.80, "timeout": 7, "main_source": False},
            {"url": "https://kpop.fandom.com/wiki/{}", "selector": ".mw-parser-output p, .portable-infobox", "type": "fandom_wiki", "priority": 0.78, "timeout": 7, "main_source": False},
            
            # FALLBACK SOURCES - Digunakan sebagai last resort
            {"url": "https://en.wikipedia.org/wiki/{}_discography", "selector": ".mw-parser-output", "type": "wiki_discography", "priority": 0.70, "timeout": 6, "main_source": False},
            {"url": "https://en.wikipedia.org/wiki/{}", "selector": ".mw-parser-output p", "type": "wiki", "priority": 0.68, "timeout": 6, "main_source": False},
            {"url": "https://id.wikipedia.org/wiki/{}", "selector": ".mw-parser-output p", "type": "wiki", "priority": 0.66, "timeout": 6, "main_source": False},
            {"url": "https://dbkpop.com/db/{}", "selector": ".artist-info, .group-info, .content", "type": "dbkpop_main", "priority": 0.65, "timeout": 6, "main_source": False},
            {"url": "https://en.namu.wiki/w/{}", "selector": ".wiki-paragraph", "type": "namu_english", "priority": 0.60, "timeout": 7, "main_source": False},
            {"url": "https://en.namu.wiki/w/{}", "selector": ".wiki-paragraph", "type": "namu_encoded", "priority": 0.60, "timeout": 7, "main_source": False},
            {"url": "https://en.namu.wiki/w/{}", "selector": ".wiki-paragraph", "type": "namu_hangul", "priority": 0.60, "timeout": 7, "main_source": False},
            {"url": "https://kprofiles.com/?s={}", "selector": ".post-title a", "type": "profile", "priority": 0.50, "timeout": 6, "main_source": False},
            {"url": "https://kpopping.com/search?keyword={}", "selector": ".search-result, .profile-card", "type": "kpopping_search", "priority": 0.48, "timeout": 6, "main_source": False},
            {"url": "https://www.dbkpop.com/?s={}", "selector": ".entry-title a", "type": "database", "priority": 0.45, "timeout": 5, "main_source": False},
            {"url": "https://www.soompi.com/?s={}", "selector": ".post-title a", "type": "news", "priority": 0.40, "timeout": 5, "main_source": False},
            {"url": "https://www.allkpop.com/search/{}", "selector": ".akp_article_title a", "type": "news", "priority": 0.35, "timeout": 5, "main_source": False}
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
        
        # KPopping.com URL mappings untuk grup-grup populer
        self.kpopping_mappings = {
            "bts": "BTS",
            "blackpink": "BLACKPINK",
            "twice": "TWICE",
            "red velvet": "Red-Velvet",
            "itzy": "ITZY",
            "aespa": "aespa",
            "newjeans": "NewJeans",
            "ive": "IVE",
            "le sserafim": "LE-SSERAFIM",
            "gidle": "G-I-DLE",
            "(g)i-dle": "G-I-DLE",
            "stray kids": "Stray-Kids",
            "seventeen": "SEVENTEEN",
            "txt": "TXT",
            "tomorrow x together": "TXT",
            "enhypen": "ENHYPEN",
            "nct": "NCT",
            "exo": "EXO",
            "secret number": "SECRET-NUMBER",
            "fifty fifty": "FIFTY-FIFTY",
            "fiftyfifty": "FIFTY-FIFTY",
            "qwer": "QWER",
            "hearts2hearts": "Hearts2Hearts",
            "weeekly": "Weeekly",
            "purple kiss": "Purple-Kiss",
            "rocket punch": "Rocket-Punch",
            "weki meki": "Weki-Meki",
            "fromis_9": "fromis-9",
            "everglow": "EVERGLOW",
            "dreamcatcher": "Dreamcatcher",
            "nct dream": "NCT-Dream",
            "nct 127": "NCT-127",
            "nct u": "NCT-U",
            "wayv": "WayV",
            "red velvet irene seulgi": "Red-Velvet-Irene-Seulgi",
            "girls generation taetiseo": "Girls-Generation-TaeTiSeo",
            "exo cbx": "EXO-CBX",
            "exo sc": "EXO-SC",
            "super junior d&e": "Super-Junior-D-E",
            "tri.be": "TRI.BE",
            "hot issue": "HOT-ISSUE",
            "class:y": "CLASS-y",
            "bugaboo": "bugAboo",
            "ichillin": "ICHILLIN",
            "lapillus": "Lapillus",
            "young posse": "YOUNG-POSSE",
            "unis": "UNIS",
            "artms": "ARTMS",
            "loossemble": "LOOSSEMBLE",
            "odd eye circle": "ODD-EYE-CIRCLE",
            # Individual members/Solo artists mappings (for /profiles/idol/ endpoint)
            "blackpink rosé": "Rose",
            "blackpink rose": "Rose",
            "rosé": "Rose",
            "rose": "Rose",
            "bts rm": "RM",
            "rm": "RM",
            "twice nayeon": "Nayeon",
            "nayeon": "Nayeon",
            "red velvet irene": "Irene",
            "irene": "Irene",
            "seventeen woozi": "Woozi",
            "woozi": "Woozi",
            "jisoo": "Jisoo",
            "blackpink jisoo": "Jisoo",
            "chodan": "Chodan",
            "qwer chodan": "Chodan",
            "soodam": "Soodam",
            "secret number soodam": "Soodam",
            "iu": "IU",
            "lee ji-eun": "IU",
            # Additional case sensitivity fixes
            "dreamcatcher": "Dreamcatcher",
            "everglow": "EVERGLOW",
            "fromis_9": "fromis_9",
            "nct dream": "NCT-Dream",
            "nct 127": "NCT-127",
            "nct u": "NCT-U",
            "wayv": "WayV",
            "exo cbx": "EXO-CBX",
            "exo sc": "EXO-SC",
            "tri.be": "TRI.BE",
            "hot issue": "HOT-ISSUE",
            "class:y": "CLASS-y",
            "bugaboo": "bugAboo",
            "ichillin": "ICHILLIN",
            "young posse": "YOUNG-POSSE",
            "unis": "UNIS",
            "artms": "ARTMS",
            "loossemble": "LOOSSEMBLE"
        }
        
        # DBKpop.com URL mappings
        self.dbkpop_mappings = {
            # Group mappings (DBKpop uses lowercase with hyphens)
            "bts": "bts",
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
            "txt": "tomorrow-x-together",
            "tomorrow x together": "tomorrow-x-together",
            "enhypen": "enhypen",
            "nct": "nct",
            "exo": "exo",
            "secret number": "secret-number",
            "fifty fifty": "fifty-fifty",
            "fiftyfifty": "fifty-fifty",
            "qwer": "qwer"
        }
        
        # Fandom.com (K-pop Wiki) URL mappings
        self.fandom_mappings = {
            # Group mappings (Fandom uses various patterns)
            "bts": "BTS",
            "blackpink": "BLACKPINK",
            "twice": "TWICE",
            "red velvet": "Red_Velvet",
            "itzy": "ITZY",
            "aespa": "Aespa",
            "newjeans": "NewJeans",
            "ive": "IVE",
            "le sserafim": "LE_SSERAFIM",
            "gidle": "(G)I-DLE",
            "(g)i-dle": "(G)I-DLE",
            "stray kids": "Stray_Kids",
            "seventeen": "SEVENTEEN",
            "txt": "TXT",
            "tomorrow x together": "TXT",
            "enhypen": "ENHYPEN",
            "nct": "NCT",
            "exo": "EXO",
            # Special cases based on sample URLs
            "secret number": "SECRET_NUMBER_(group)",  # Has (group) suffix
            "iz*one": "IZ*ONE",  # Special characters preserved
            "izone": "IZ*ONE",
            "girls generation": "Girls%27_Generation",  # URL encoded apostrophe
            "girls' generation": "Girls%27_Generation",
            "snsd": "Girls%27_Generation",
            "fifty fifty": "FIFTY_FIFTY",
            "fiftyfifty": "FIFTY_FIFTY",
            "artbeat": "ARTBEAT_v",
            "qwer": "QWER",
            "hearts2hearts": "Hearts2Hearts",
            "weeekly": "Weeekly",
            # Individual member mappings
            "chodan": "Chodan",  # QWER member
            "magenta": "Magenta_(QWER)",  # QWER member with group disambiguation
            "soodam": "Soodam",  # Secret Number member
            "xiumin": "Xiumin",  # EXO member
            "chen": "Chen_(EXO)",  # EXO member with group disambiguation
            "irene": "Irene_(Red_Velvet)",  # Red Velvet member with group disambiguation
            "yeri": "Yeri_(Red_Velvet)",  # Red Velvet member with group disambiguation
            "jisoo": "Jisoo_(BLACKPINK)",  # BLACKPINK member with group disambiguation
            "tiffany": "Tiffany",  # Girls' Generation member
            "siyeon": "Siyeon",  # Dreamcatcher member
            "hyein": "Hyein",  # NewJeans member
            "nayeon": "Nayeon",  # TWICE member
            "karina": "Karina",  # aespa member
            "minji": "Minji_(NewJeans)",  # NewJeans member with group disambiguation
            # Special subdomain cases
            "taeyeon": "Taeyeon",  # Note: uses girls-generation.fandom.com subdomain
            "qwer chodan": "Chodan",
            "qwer magenta": "Magenta_(QWER)",
            "secret number soodam": "Soodam",
            "exo xiumin": "Xiumin",
            "exo chen": "Chen_(EXO)",
            "red velvet irene": "Irene_(Red_Velvet)",
            "red velvet yeri": "Yeri_(Red_Velvet)",
            "blackpink jisoo": "Jisoo_(BLACKPINK)",
            "girls generation tiffany": "Tiffany",
            "girls generation taeyeon": "Taeyeon",
            # Additional group+member combinations
            "dreamcatcher siyeon": "Siyeon",
            "newjeans hyein": "Hyein",
            "twice nayeon": "Nayeon",
            "aespa karina": "Karina",
            "newjeans minji": "Minji_(NewJeans)"
        }
    
    async def fetch_kpop_info(self, query):
        """Fetch comprehensive K-pop information with optimized caching and async processing"""
        try:
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
            try:
                website_results = await self._scrape_websites_async(query, sorted_sites)
                all_results.extend(website_results)
                logger.info(f"Async scraping completed: {len(website_results)} results")
            except Exception as e:
                logger.error(f"Website scraping failed: {e}")
            
            # Always try to get more sources untuk akurasi maksimal
            # 2. Google Custom Search
            try:
                cse_results = await self._fetch_from_cse(query)
                all_results.extend(cse_results)
            except Exception as e:
                logger.error(f"CSE fetch failed: {e}")
            
            # 3. NewsAPI
            try:
                news_results = await self._fetch_from_newsapi(query)
                all_results.extend(news_results)
            except Exception as e:
                logger.error(f"NewsAPI fetch failed: {e}")
            
            # 4. Database fallback info
            try:
                database_info = self._get_database_info(query)
                if database_info:
                    all_results.append(database_info)
                    logger.info(f"Database fallback added: {len(database_info)} characters")
            except Exception as e:
                logger.error(f"Database fallback failed: {e}")
            
            # Enhanced trivia/facts extraction untuk semua member
            try:
                if len(all_results) > 0:  # Only if we have some results
                    trivia_results = await self.scrape_member_trivia(query, self._extract_group_name_from_query(query))
                    if trivia_results.get('success') and trivia_results.get('facts'):
                        # Ambil 1-4 facts terbaik
                        selected_facts = trivia_results['facts'][:4]
                        facts_text = "\n\n🎭 **Fun Facts & Trivia:**\n" + "\n".join([f"• {fact}" for fact in selected_facts])
                        all_results.append(facts_text)
                        logger.info(f"Added {len(selected_facts)} trivia facts for {query}")
            except Exception as e:
                logger.error(f"Trivia extraction failed: {e}")
            
            # Clean and combine results
            final_text = self._clean_text(all_results)
            
            # Enhanced birth date extraction dari hasil scraping
            final_text = self._enhance_birth_date_extraction(final_text, query)
            
            # Enhance with discography information if needed
            final_text = self._enhance_discography_content(final_text, query)
            
            # Cache the result
            self._save_to_cache(cache_key, final_text)
            
            total_time = time.time() - start_time
            logger.info(f"Optimized fetch completed in {total_time:.2f}s: {len(final_text)} characters")
            
            return final_text
            
        except Exception as e:
            logger.error(f"Critical error in fetch_kpop_info: {e}")
            # Return fallback response
            return f"**{query}**\n\nMaaf, terjadi kesalahan saat mengambil informasi. Silakan coba lagi nanti."
    
    async def _scrape_websites_async(self, query, sorted_sites):
        """Optimized async scraping dengan TOP 3 MAIN SOURCES prioritas tertinggi"""
        results = []
        
        # Create aiohttp session if not exists
        if not self.session:
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=3)
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        
        # Create semaphore untuk limit concurrent requests
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests
        
        # STEP 1: Process TOP 3 MAIN SOURCES first (main_source: True)
        main_sources = [site for site in sorted_sites if site.get('main_source', False)]
        logger.info(f"Processing TOP 3 MAIN SOURCES: {len(main_sources)} sites")
        
        if main_sources:
            main_results = await self._process_sites_batch(query, main_sources, semaphore)
            results.extend(main_results)
            logger.info(f"Main sources completed: {len(main_results)} results")
            
            # Check if main sources provide sufficient data
            if self._is_sufficient_data(results):
                logger.info(f"✅ Sufficient data from TOP 3 MAIN SOURCES: {len(results)} items")
                return results
        
        # STEP 2: Only if main sources insufficient, try secondary sources
        secondary_sources = [site for site in sorted_sites if not site.get('main_source', False) and site.get('priority', 0) >= 0.7]
        logger.info(f"Main sources insufficient, trying secondary sources: {len(secondary_sources)} sites")
        
        if secondary_sources:
            secondary_results = await self._process_sites_batch(query, secondary_sources, semaphore)
            results.extend(secondary_results)
            
            # Check again after secondary
            if self._is_sufficient_data(results):
                logger.info(f"✅ Sufficient data after secondary sources: {len(results)} items")
                return results
        
        # STEP 3: Last resort - fallback sources
        fallback_sources = [site for site in sorted_sites if not site.get('main_source', False) and site.get('priority', 0) < 0.7]
        logger.info(f"Still insufficient, trying fallback sources: {len(fallback_sources)} sites")
        
        if fallback_sources:
            fallback_results = await self._process_sites_batch(query, fallback_sources, semaphore)
            results.extend(fallback_results)
        
        logger.info(f"🏁 Final scraping completed: {len(results)} total results")
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
                    
            elif site.get("type") in ["kpopping_group", "kpopping_solo", "kpopping_idol", "kpopping_search"]:
                # Format khusus untuk KPopping.com (Enhanced with pattern analysis)
                query_lower = query.lower()
                
                if site.get("type") == "kpopping_search":
                    # Search endpoint
                    formatted_name = query.replace(' ', '+')
                    return site["url"].format(formatted_name)
                else:
                    # Direct profile endpoints dengan smart formatting
                    if query_lower in self.kpopping_mappings:
                        formatted_name = self.kpopping_mappings[query_lower]
                        return site["url"].format(formatted_name)
                    else:
                        # Enhanced fallback dengan pattern recognition
                        formatted_name = self._smart_kpopping_format(query)
                        return site["url"].format(formatted_name)
                        
            elif site.get("type") == "dbkpop_main":
                # Format khusus untuk DBKpop.com
                query_lower = query.lower()
                
                if query_lower in self.dbkpop_mappings:
                    formatted_name = self.dbkpop_mappings[query_lower]
                    return site["url"].format(formatted_name)
                else:
                    # Fallback to formatted query
                    formatted_name = query.lower().replace(' ', '-')
                    return site["url"].format(formatted_name)
                    
            elif site.get("type") == "fandom_infobox":
                # Format khusus untuk Fandom.com infobox scraping dengan universal parsing
                member_name, group_name = self._parse_member_group_query(query)
                
                # Generate subdomain and member name
                if group_name:
                    subdomain = self._format_group_to_subdomain(group_name)
                    formatted_member = member_name.replace(' ', '_')
                    return f"https://{subdomain}.fandom.com/wiki/{formatted_member}"
                else:
                    # Fallback to kpop.fandom.com
                    formatted_name = query.replace(' ', '_')
                    return f"https://kpop.fandom.com/wiki/{formatted_name}"
                    
            elif site.get("type") == "fandom_wiki":
                # Format khusus untuk Fandom.com (K-pop Wiki) dengan universal parsing
                member_name, group_name = self._parse_member_group_query(query)
                
                # Generate URL with subdomain if group detected
                if group_name:
                    subdomain = self._format_group_to_subdomain(group_name)
                    formatted_member = member_name.replace(' ', '_')
                    return f"https://{subdomain}.fandom.com/wiki/{formatted_member}"
                
                # Fallback to existing mappings
                query_lower = query.lower()
                if query_lower in self.fandom_mappings:
                    formatted_name = self.fandom_mappings[query_lower]
                    return site["url"].format(formatted_name)
                else:
                    # Enhanced fallback dengan pattern recognition
                    formatted_name = self._smart_fandom_format(query)
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
                
    def _smart_kpopping_format(self, query):
        """Smart formatting untuk KPopping.com berdasarkan pattern analysis"""
        query_lower = query.lower()
        
        # Pattern 1: Individual members/Solo artists → Use just the member name
        # KPopping.com uses /profiles/idol/{MemberName} for individual members
        # Check this FIRST before major groups pattern
        if ' ' in query:
            parts = query.split(' ')
            
            # Check if this looks like a "Group Member" pattern
            major_groups = ['bts', 'blackpink', 'twice', 'itzy', 'seventeen', 'enhypen', 'exo', 'red velvet', 'secret number', 'qwer']
            
            # Try to identify group + member pattern
            member_part = parts[-1]  # Last word is likely the member name
            group_part = ' '.join(parts[:-1]).lower()  # Everything except last word
            
            # Check if the group part matches any known groups
            if group_part in major_groups or any(major in group_part for major in major_groups):
                # For individual members, use just the member name in title case
                return member_part.title()
            else:
                # For sub-units or unknown patterns, use hyphenated format
                return query.title().replace(' ', '-')
        
        # Pattern 2: Major groups (single word) → UPPERCASE
        major_groups = ['bts', 'blackpink', 'twice', 'itzy', 'seventeen', 'enhypen', 'exo']
        if query_lower in major_groups:
            return query.upper()
        
        # Pattern 3: Special characters handling
        if any(char in query for char in ['(', ')', '*', '_']):
            # Handle specific cases
            if 'f(x)' in query_lower:
                return 'f-x'  # KPopping uses f-x for f(x)
            elif '*' in query:
                return query.replace('*', '').replace(' ', '-').title()
            elif '_' in query:
                # Keep underscores for groups like fromis_9
                return query.lower()
            elif '(' in query and ')' in query:
                # Remove parentheses and format
                clean_query = query.replace('(', '').replace(')', '')
                return clean_query.replace(' ', '-').title()
        
        # Pattern 4: Numbers in name → Keep original case but handle special cases
        if any(char.isdigit() for char in query):
            # Special handling for specific groups
            return query.title().replace(' ', '-')
        
        # Default fallback → Title case with hyphens
        return query.title().replace(' ', '-')

    def _smart_fandom_format(self, query):
        """Smart formatting untuk Fandom.com berdasarkan pattern analysis"""
        query_lower = query.lower()
        
        # Pattern 1: Special characters handling
        if '*' in query:
            # Keep asterisks for groups like IZ*ONE
            return query.upper()
        elif "'" in query or "'" in query:
            # URL encode apostrophes for groups like Girls' Generation
            return query.title().replace("'", "%27").replace("'", "%27").replace(' ', '_')
        
        # Pattern 2: Major groups → UPPERCASE
        major_groups = ['bts', 'blackpink', 'twice', 'itzy', 'seventeen', 'enhypen', 'exo']
        if query_lower in major_groups:
            return query.upper()
        
        # Pattern 3: Multi-word groups → Title_Case_With_Underscores
        if ' ' in query:
            return query.title().replace(' ', '_')
        
        # Default fallback → Title case
        return query.title()

    def _extract_site_content(self, soup, site, url, query):
        """Extract content dari soup berdasarkan site type"""
        site_type = site.get("type", "default")
        site_results = []
        
        try:
            if site_type in ["kprofile_group", "kprofile_solo1", "kprofile_solo2", "kprofile_member", "kprofile_member_facts"]:
                # KProfiles direct dengan enhanced extraction untuk birth date dan social media
                content_elements = soup.select(site["selector"])[:15]
                
                for el in content_elements:
                    text = el.get_text().strip()
                    if text and len(text) > 20:
                        # Universal birth date detection (works for any member)
                        if any(keyword in text.lower() for keyword in ['birthday:', 'birth name:', 'zodiac sign:', 'height:', 'blood type:', 'nationality:', 'position(s):']):
                            site_results.append(text)
                        # Universal social media detection (Instagram, TikTok, YouTube, Twitter/X, SNS)
                        elif any(keyword in text.lower() for keyword in ['instagram:', 'tiktok:', 'youtube:', 'twitter:', 'x:', 'sns:', 'soundcloud:', 'facebook:', 'threads:']):
                            site_results.append(text)
                        # Universal facts and trivia detection (gender-neutral)
                        elif any(keyword in text.lower() for keyword in ['facts:', 'favorite', 'hobby', 'role model', 'education:', 'religion:', 'nickname:', 'charming point']):
                            if len(text) > 30:
                                site_results.append(text)
                        # Universal member info detection
                        elif any(keyword in text.lower() for keyword in ['stage name:', 'real name:', 'korean name:', 'english name:', 'mbti type:', 'weight:']):
                            site_results.append(text)
                        # General content with universal filtering
                        elif len(text) > 30 and not any(skip in text.lower() for skip in ['copyright', 'kprofiles.com', 'note:', 'poll:', 'related:']):
                            site_results.append(text)
            
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
            
            elif site_type in ["kpopping_group", "kpopping_solo", "kpopping_idol"]:
                # KPopping.com direct profiles (Enhanced extraction)
                # Extract from multiple sections
                intro_section = soup.select(".profile-intro, .group-intro")[:2]
                member_section = soup.select(".member-list, .profile-members")[:1]
                info_section = soup.select(".profile-info, .group-info")[:3]
                
                # Process introduction
                for section in intro_section:
                    text = section.get_text().strip()
                    if text and len(text) > 50:
                        site_results.append(f"Introduction: {text}")
                
                # Process member info
                for section in member_section:
                    text = section.get_text().strip()
                    if text and len(text) > 30:
                        site_results.append(f"Members: {text}")
                
                # Process general info
                for section in info_section:
                    text = section.get_text().strip()
                    if text and len(text) > 20 and "profile" not in text.lower():
                        site_results.append(text)
                
                # Fallback to original selector if no specific sections found
                if not site_results:
                    content_elements = soup.select(site["selector"])[:8]
                    for el in content_elements:
                        text = el.get_text().strip()
                        if text and len(text) > 20 and "profile" not in text.lower():
                            site_results.append(text)
                        
            elif site_type == "kpopping_search":
                # KPopping.com search results
                search_elements = soup.select(site["selector"])[:3]
                for el in search_elements:
                    text = el.get_text().strip()
                    if text and len(text) > 15:
                        site_results.append(text)
                        
            elif site_type == "dbkpop_main":
                # DBKpop.com main content
                content_elements = soup.select(site["selector"])[:6]
                for el in content_elements:
                    text = el.get_text().strip()
                    if text and len(text) > 25 and not text.startswith("Search"):
                        site_results.append(text)
                        
            elif site_type == "fandom_infobox":
                # Fandom.com infobox scraping untuk General Information
                # Extract structured data from infobox dengan multiple selectors
                infobox_selectors = [
                    ".portable-infobox .pi-data-value",
                    ".infobox td",
                    ".infobox-data-value", 
                    ".wikitable td",
                    ".mw-parser-output .infobox tr td"
                ]
                
                # Universal extraction untuk semua member K-pop
                birth_info = []
                personal_info = []
                social_media = []
                
                for selector in infobox_selectors:
                    infobox_elements = soup.select(selector)[:15]
                    for element in infobox_elements:
                        text = element.get_text().strip()
                        parent_text = element.parent.get_text().strip() if element.parent else ""
                        
                        # Universal filtering untuk semua member
                        if text and len(text) > 2 and len(text) < 150:
                            lower_parent = parent_text.lower()
                            lower_text = text.lower()
                            
                            # Universal birth date detection
                            if any(keyword in lower_parent for keyword in ['birth', 'born', 'birthday', 'date of birth']):
                                if any(char.isdigit() for char in text):
                                    birth_info.append(f"Birth Date: {text}")
                            
                            # Universal name detection  
                            elif any(keyword in lower_parent for keyword in ['birth name', 'real name', 'full name', 'korean name', 'stage name']):
                                if not any(char.isdigit() for char in text) and len(text) > 2:
                                    personal_info.append(f"Name: {text}")
                            
                            # Universal location detection
                            elif any(keyword in lower_parent for keyword in ['birth place', 'birthplace', 'hometown', 'nationality', 'origin']):
                                personal_info.append(f"Origin: {text}")
                            
                            # Universal physical info detection
                            elif any(keyword in lower_parent for keyword in ['blood type', 'blood']):
                                if len(text) <= 5:
                                    personal_info.append(f"Blood Type: {text}")
                            elif any(keyword in lower_parent for keyword in ['height']):
                                if 'cm' in text or any(char.isdigit() for char in text):
                                    personal_info.append(f"Height: {text}")
                            elif any(keyword in lower_parent for keyword in ['weight']):
                                if 'kg' in text or any(char.isdigit() for char in text):
                                    personal_info.append(f"Weight: {text}")
                            
                            # Universal social media detection
                            elif any(keyword in lower_parent for keyword in ['instagram', 'twitter', 'tiktok', 'youtube', 'sns', 'social']):
                                if '@' in text or 'http' in text or len(text) > 3:
                                    social_media.append(f"Social Media: {text}")
                            
                            # Universal position/role detection
                            elif any(keyword in lower_parent for keyword in ['position', 'role', 'occupation']):
                                personal_info.append(f"Position: {text}")
                
                # Combine results dengan prioritas universal
                site_results.extend(birth_info)
                site_results.extend(personal_info)
                site_results.extend(social_media)
                
                # Fallback ke paragraph jika infobox kosong
                if not site_results:
                    wiki_paragraphs = soup.select(".mw-parser-output p")[:3]
                    for p in wiki_paragraphs:
                        text = p.get_text().strip()
                        if (text and len(text) > 40 and 
                            any(keyword in text.lower() for keyword in ['born', 'birth', 'birthday'])):
                            site_results.append(text)
            
            elif site_type == "fandom_wiki":
                # Fandom.com (K-pop Wiki)
                # Extract from both paragraphs and infobox
                wiki_paragraphs = soup.select(".mw-parser-output p")[:4]
                infobox_data = soup.select(".portable-infobox .pi-data-value")[:6]
                
                # Process paragraphs
                for p in wiki_paragraphs:
                    text = p.get_text().strip()
                    if (text and len(text) > 40 and 
                        not text.startswith("This article") and
                        not text.startswith("For other uses") and
                        "disambiguation" not in text.lower()):
                        site_results.append(text)
                        
                # Process infobox data
                for data in infobox_data:
                    text = data.get_text().strip()
                    if text and len(text) > 5 and len(text) < 200:
                        site_results.append(f"Info: {text}")
            
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
        
        try:
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
                    try:
                        analytics.track_source_performance("google_cse", True, cse_time)
                    except Exception:
                        pass  # Ignore analytics errors
                    
                    logger.info(f"CSE API {i}/3 completed: {len(cse_results)} results")
                    break  # Success, exit loop
                    
                except requests.exceptions.HTTPError as e:
                    cse_time = time.time() - cse_start if 'cse_start' in locals() else 0
                    try:
                        analytics.track_source_performance("google_cse", False, cse_time)
                    except Exception:
                        pass  # Ignore analytics errors
                    
                    if e.response.status_code == 429:
                        logger.warning(f"CSE API {i}/3 rate limited (429), trying next key...")
                        continue  # Try next API key
                    else:
                        logger.error(f"CSE API {i}/3 HTTP error: {e}")
                except Exception as e:
                    cse_time = time.time() - cse_start if 'cse_start' in locals() else 0
                    try:
                        analytics.track_source_performance("google_cse", False, cse_time)
                    except Exception:
                        pass  # Ignore analytics errors
                    logger.error(f"CSE API {i}/3 failed: {e}")
                    
        except Exception as e:
            logger.error(f"Critical error in _fetch_from_cse: {e}")
        
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
    
    def _extract_group_name_from_query(self, query):
        """Extract group name from query string with universal parsing"""
        query_lower = query.lower()
        
        # Universal parsing untuk format "Member Group" atau "Member from Group"
        member_name, group_name = self._parse_member_group_query(query)
        if group_name:
            return group_name
        
        # Direct group name detection
        group_patterns = {
            'qwer': 'QWER',
            'lightsum': 'Lightsum',
            'light sum': 'Lightsum',
            'secret number': 'Secret Number',
            'newjeans': 'NewJeans',
            'new jeans': 'NewJeans',
            'blackpink': 'BLACKPINK',
            'twice': 'TWICE',
            'aespa': 'aespa',
            'dreamcatcher': 'Dreamcatcher',
            'iz*one': 'IZ*ONE',
            'izone': 'IZ*ONE',
            "tahiti": "Tahiti",
            "hinapia": "Hinapia"
        }
        
        # Check if query contains group name
        for pattern, group in group_patterns.items():
            if pattern in query_lower:
                return group
        
        # Database-driven group extraction untuk akurasi maksimal
        return self._get_group_from_database(query)
    
    def _clean_member_name_from_query(self, query):
        """Clean member name dari query yang mungkin mengandung format 'Member From Group'"""
        query_lower = query.lower()
        
        # Pattern untuk mendeteksi format "Member From Group" atau "Member Group"
        patterns_to_clean = [
            r'\s+from\s+\w+',     # "Hina From Qwer" -> "Hina"
            r'\s+qwer$',          # "Hina Qwer" -> "Hina"
            r'\s+lightsum$',      # "Hina Lightsum" -> "Hina"
            r'\s+light\s+sum$',   # "Hina Light Sum" -> "Hina"
            r'\s+secret\s+number$',  # "Soodam Secret Number" -> "Soodam"
            r'\s+newjeans$',   # "Minji NewJeans" -> "Minji"
            r'\s+blackpink$',  # "Jisoo BLACKPINK" -> "Jisoo"
            r'\s+twice$',      # "Nayeon TWICE" -> "Nayeon"
            r'\s+aespa$'       # "Karina aespa" -> "Karina"
        ]
        
        cleaned_query = query
        for pattern in patterns_to_clean:
            cleaned_query = re.sub(pattern, '', cleaned_query, flags=re.IGNORECASE)
        
        return cleaned_query.strip()
    
    def _parse_member_group_query(self, query):
        """Universal parser untuk format 'Member Group' atau 'Member from Group'"""
        query = query.strip()
        
        # Pattern 1: "Member from Group" (explicit)
        if " from " in query.lower():
            parts = query.split(" from ", 1)
            member_name = parts[0].strip()
            group_name = parts[1].strip()
            return member_name, group_name
        
        # Pattern 2: "Member Group" (space-separated, 2 words)
        words = query.split()
        if len(words) == 2:
            potential_member = words[0]
            potential_group = words[1]
            
            # Database-driven group detection untuk akurasi
            resolved_group = self._resolve_ambiguous_group(potential_member, potential_group)
            if resolved_group:
                return potential_member, resolved_group
            
            # Fallback: Check if second word looks like a group name
            if (potential_group[0].isupper() or 
                potential_group.lower() in ['qwer', 'tahiti', 'lightsum', 'aespa', 'twice', 'blackpink', 'newjeans', 'dreamcatcher', 'iz*one', 'izone']):
                return potential_member, potential_group
        
        # Pattern 3: "Group Member" (reverse order detection)
        elif len(words) == 2:
            potential_group = words[0]
            potential_member = words[1]
            
            # Database-driven group detection
            resolved_group = self._resolve_ambiguous_group(potential_member, potential_group)
            if resolved_group:
                return potential_member, resolved_group
            
            # Fallback: Check if first word is a known group
            if potential_group.lower() in ['qwer', 'tahiti', 'lightsum', 'blackpink', 'twice', 'newjeans', 'aespa', 'dreamcatcher', 'hinapia']:
                return potential_member, potential_group
        
        # No clear member/group separation found
        return query, None
    
    def _resolve_ambiguous_group(self, member_name, group_hint):
        """Resolve ambiguous group names using database context"""
        if self.kpop_df is None:
            return None
        
        group_hint_lower = group_hint.lower()
        member_name_lower = member_name.lower()
        
        # Handle "secret" ambiguity: SECRET vs SECRET NUMBER
        if group_hint_lower == 'secret':
            # Check if member exists in either SECRET or SECRET NUMBER
            secret_members = self.kpop_df[self.kpop_df['Group'] == 'SECRET']['Stage Name'].str.lower().tolist()
            secret_number_members = self.kpop_df[self.kpop_df['Group'] == 'SECRET NUMBER']['Stage Name'].str.lower().tolist()
            
            if member_name_lower in secret_members:
                return 'SECRET'
            elif member_name_lower in secret_number_members:
                return 'SECRET NUMBER'
            else:
                # Default to more recent/popular group if member not found
                return 'SECRET NUMBER'
        
        # Handle other potential ambiguities
        # Check if group_hint matches any group in database (case-insensitive)
        matching_groups = self.kpop_df[self.kpop_df['Group'].str.lower().str.contains(group_hint_lower, na=False)]['Group'].unique()
        
        if len(matching_groups) == 1:
            return matching_groups[0]
        elif len(matching_groups) > 1:
            # Multiple matches - check which one contains the member
            for group in matching_groups:
                group_members = self.kpop_df[self.kpop_df['Group'] == group]['Stage Name'].str.lower().tolist()
                if member_name_lower in group_members:
                    return group
            
            # If no member match, return first (alphabetically)
            return sorted(matching_groups)[0]
        
        return None
    
    def _get_group_from_database(self, query):
        """Get group from database dengan context-aware disambiguation"""
        if self.kpop_df is None:
            return None
        
        query_lower = query.lower().strip()
        
        # Try to find member in database
        matches = self.kpop_df[self.kpop_df['Stage Name'].str.lower() == query_lower]
        
        if matches.empty:
            return None
        elif len(matches) == 1:
            # Single match - return the group
            return matches.iloc[0]['Group']
        else:
            # Multiple matches - use popularity/recency priority
            groups = matches['Group'].unique()
            
            # Priority groups (more popular/recent first)
            priority_groups = [
                'TWICE', 'BLACKPINK', 'NewJeans', 'aespa', 'IZ*ONE', 'Red Velvet', 
                'ITZY', 'ENHYPEN', 'Stray Kids', 'NCT', 'QWER', 'SECRET NUMBER',
                'LIGHTSUM', 'Dreamcatcher', 'VIVIZ', 'MAMAMOO'
            ]
            
            # Return first priority group found
            for priority_group in priority_groups:
                if priority_group in groups:
                    return priority_group
            
            # If no priority group, return first alphabetically
            return sorted(groups)[0]
    
    def _extract_member_name_from_query(self, query):
        """Extract member name from query (for use with group context)"""
        member_name, group_name = self._parse_member_group_query(query)
        return member_name
    
    def _enhance_birth_date_extraction(self, text, query):
        """Enhanced birth date extraction dari text hasil scraping"""
        try:
            # Pattern untuk birth date detection yang lebih komprehensif
            birth_patterns = [
                r'(?:birthday|birth date|born|date of birth)\s*:?\s*([^\n\r]+?)(?:\n|\r|$)',
                r'([A-Za-z]+ \d{1,2},? \d{4})',  # Format: January 1, 2000
                r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})',  # Format: 01/01/2000
                r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',  # Format: 2000/01/01
                r'(?:lahir|birth)\s*:?\s*([^\n\r]+?)(?:\n|\r|$)'  # Indonesian format
            ]
            
            birth_date_found = None
            
            for pattern in birth_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    # Clean up the match
                    cleaned_match = re.sub(r'[()\[\]{}]', '', match).strip()
                    if len(cleaned_match) > 4 and any(char.isdigit() for char in cleaned_match):
                        birth_date_found = cleaned_match
                        break
                if birth_date_found:
                    break
            
            # Jika birth date ditemukan, replace placeholder text
            if birth_date_found:
                # Remove common placeholder text
                text = re.sub(
                    r'Tanggal Lahir: \(Informasi tidak tersedia di sumber yang diberikan, jadi saya tidak bisa memberikan tanggal lahir yang akurat\)',
                    f'Tanggal Lahir: {birth_date_found}',
                    text
                )
                
                # Also add if not present
                if 'Tanggal Lahir:' not in text and 'Birth Date:' not in text:
                    text = f"**{query}**\n\nTanggal Lahir: {birth_date_found}\n\n" + text
                
                logger.info(f"Enhanced birth date found for {query}: {birth_date_found}")
            
            return text
            
        except Exception as e:
            logger.error(f"Birth date enhancement failed: {e}")
            return text
    
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
    
    async def scrape_member_gallery(self, member_name, group_name=None):
        """Scrape gallery images dari Fandom.com untuk member K-pop"""
        try:
            gallery_url = self._generate_gallery_url(member_name, group_name)
            if not gallery_url:
                return {"error": "Could not generate gallery URL", "images": []}
            
            logger.info(f"Scraping gallery for {member_name}: {gallery_url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(gallery_url, timeout=10) as response:
                    if response.status != 200:
                        return {"error": f"HTTP {response.status}", "images": []}
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    images = []
                    
                    # Pattern 1: Gallery thumbnails
                    gallery_items = soup.select('.wikia-gallery-item img, .gallery img')
                    for img in gallery_items:
                        src = img.get('src') or img.get('data-src')
                        if src:
                            clean_src = re.sub(r'/revision/.*?/', '/', src)
                            clean_src = re.sub(r'\?.*$', '', clean_src)
                            images.append({
                                'url': clean_src,
                                'alt': img.get('alt', ''),
                                'type': 'gallery_thumbnail'
                            })
                    
                    # Pattern 2: Lightbox images
                    lightbox_images = soup.select('.lightbox img, .image img')
                    for img in lightbox_images:
                        src = img.get('src') or img.get('data-src')
                        if src and src not in [i['url'] for i in images]:
                            clean_src = re.sub(r'/revision/.*?/', '/', src)
                            clean_src = re.sub(r'\?.*$', '', clean_src)
                            images.append({
                                'url': clean_src,
                                'alt': img.get('alt', ''),
                                'type': 'lightbox_image'
                            })
                    
                    # Pattern 3: Direct images
                    direct_images = soup.select('img[src*="static.wikia"], img[src*="vignette.wikia"]')
                    for img in direct_images:
                        src = img.get('src')
                        if src and src not in [i['url'] for i in images]:
                            clean_src = re.sub(r'/revision/.*?/', '/', src)
                            clean_src = re.sub(r'\?.*$', '', clean_src)
                            images.append({
                                'url': clean_src,
                                'alt': img.get('alt', ''),
                                'type': 'direct_image'
                            })
                    
                    logger.info(f"Found {len(images)} images in gallery for {member_name}")
                    
                    return {
                        "success": True,
                        "total_images": len(images),
                        "images": images[:50],  # Limit to first 50 images
                        "gallery_url": gallery_url,
                        "member": member_name,
                        "group": group_name
                    }
                    
        except Exception as e:
            logger.error(f"Gallery scraping failed for {member_name}: {e}")
            return {"error": str(e), "images": []}
    
    async def scrape_member_trivia(self, member_name, group_name=None):
        """Scrape trivia/facts dari halaman member di Fandom.com dengan fallback URLs"""
        
        # Generate multiple URL attempts untuk fallback
        urls_to_try = []
        
        # Primary URL dari mapping
        primary_url = self._generate_trivia_url(member_name, group_name)
        urls_to_try.append(primary_url)
        
        # Universal fallback URLs untuk semua grup
        if group_name:
            subdomain = self._format_group_to_subdomain(group_name)
            
            # Add universal fallback patterns
            urls_to_try.extend([
                # Try /Facts endpoint on group subdomain
                f"https://{subdomain}.fandom.com/wiki/{member_name.title()}/Facts",
                # Try main kpop.fandom.com with /Facts
                f"https://kpop.fandom.com/wiki/{member_name.title()}/Facts",
                # Try main kpop.fandom.com with /Trivia
                f"https://kpop.fandom.com/wiki/{member_name.title()}/Trivia"
            ])
        
        # Try each URL until one works
        for trivia_url in urls_to_try:
            logger.info(f"Scraping trivia for {member_name}: {trivia_url}")
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(trivia_url, timeout=10) as response:
                        if response.status == 200:
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            facts = []
                            
                            # Extract facts dari list items dengan filtering yang lebih ketat
                            fact_items = soup.select('li')
                            
                            for item in fact_items:
                                text = item.get_text(strip=True)
                                
                                # Enhanced filtering untuk menghindari noise dan ambil facts berkualitas
                                if (text and len(text) > 20 and len(text) < 300 and
                                    not text.startswith(('History', 'Purge', 'Edit', 'View', 'Talk', 'Read', 
                                                       'Category', 'Template', 'File', 'Special', 'Help',
                                                       'Main Page', 'Recent changes', 'Random page', 'Navigation',
                                                       'Community', 'Explore', 'Fandom', 'Games', 'Movies')) and
                                    not any(skip in text.lower() for skip in ['fandom.com', 'wiki', 'edit', 'source', 
                                                                              'citation', 'reference', 'external link']) and
                                    not text.lower().startswith(('about', 'movies', 'filmography', 'shows', 'the following')) and
                                    # Prioritas facts dengan personal pronouns dan informasi personal
                                    (any(keyword in text.lower() for keyword in ['her', 'she', 'his', 'he', 'born', 'age', 
                                                                                 'favorite', 'favourite', 'like', 'love', 
                                                                                 'hobby', 'blood type', 'height', 'weight',
                                                                                 'nickname', 'education', 'family', 'sibling',
                                                                                 'pet', 'color', 'food', 'song', 'movie',
                                                                                 'actor', 'actress', 'model', 'idol']) or
                                     # Facts dengan angka (birth date, measurements, dll)
                                     any(char.isdigit() for char in text))):
                                    
                                    facts.append(text)
                            
                            # Jika tidak ada facts dari list, coba extract dari paragraf
                            if not facts:
                                paragraphs = soup.select('p')
                                for p in paragraphs:
                                    text = p.get_text(strip=True)
                                    if (text and len(text) > 30 and len(text) < 300 and
                                        ('her' in text.lower() or 'she' in text.lower() or
                                         'his' in text.lower() or 'he' in text.lower())):
                                        facts.append(text)
                            
                            if facts:  # If we found facts, return success dengan quality filtering
                                # Sort facts by quality (longer and more informative first)
                                quality_facts = sorted(facts, key=lambda x: (
                                    len(x),  # Length priority
                                    sum(1 for keyword in ['favorite', 'hobby', 'born', 'blood', 'height'] if keyword in x.lower()),  # Keyword relevance
                                    -x.count('.')  # Prefer complete sentences
                                ), reverse=True)
                                
                                # Limit to best 1-4 facts
                                selected_facts = quality_facts[:4]
                                logger.info(f"Found {len(facts)} total facts, selected {len(selected_facts)} best for {member_name}")
                                
                                return {
                                    "success": True,
                                    "total_facts": len(facts),
                                    "facts": selected_facts,
                                    "trivia_url": trivia_url,
                                    "member": member_name,
                                    "group": group_name
                                }
                        
                        # If no facts found or HTTP error, try next URL
                        continue
                        
            except Exception as e:
                logger.error(f"Error scraping trivia from {trivia_url}: {str(e)}")
                continue
        
        # If all URLs failed
        return {"error": f"No trivia found after trying {len(urls_to_try)} URLs", "facts": []}
    
    async def scrape_group_discography(self, group_name):
        """Scrape discography dari Fandom.com untuk grup K-pop dengan dual URL fallback"""
        try:
            # Try multiple URL patterns for discography
            urls_to_try = []
            
            # Pattern 1: Dedicated discography page {group}.fandom.com/wiki/{group}/Discography
            discography_url = self._generate_discography_url(group_name)
            if discography_url:
                urls_to_try.append(discography_url)
            
            # Pattern 2: Main group page with discography section {group}.fandom.com/wiki/{group}
            subdomain = self._format_group_to_subdomain(group_name)
            main_page_url = f"https://{subdomain}.fandom.com/wiki/{group_name.replace(' ', '_')}"
            urls_to_try.append(main_page_url)
            
            # Pattern 3: Fallback to kpop.fandom.com main page
            fallback_url = f"https://kpop.fandom.com/wiki/{group_name.replace(' ', '_')}"
            urls_to_try.append(fallback_url)
            
            logger.info(f"Trying {len(urls_to_try)} URLs for {group_name} discography")
            
            for url in urls_to_try:
                logger.info(f"Attempting discography scrape: {url}")
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=10) as response:
                        if response.status != 200:
                            logger.warning(f"HTTP {response.status} for {url}")
                            continue
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    albums = []
                    
                    # Extract album information from structured content
                    # Look for album titles and track lists with enhanced album type detection
                    album_keywords = ['album', 'discography', 'single', 'ep', 'mini', 'studio', 'compilation', 'repackage', 'special']
                    album_sections = soup.find_all(['h2', 'h3', 'div'], 
                        class_=lambda x: x and any(keyword in x.lower() for keyword in album_keywords))
                    
                    # Alternative approach: look for common discography patterns
                    content_text = soup.get_text()
                    lines = content_text.split('\n')
                    
                    current_album = None
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                            
                        # Detect album titles and types with enhanced pattern matching
                        album_type_patterns = [
                            'Title:', 'Album:', 'Single:', 'EP:', 'Mini Album:', 'Studio Album:', 
                            'Compilation Album:', 'Repackage Album:', 'Special Album:', 'Digital Single:'
                        ]
                        
                        detected_type = None
                        for pattern in album_type_patterns:
                            if line.startswith(pattern) and len(line) > len(pattern) + 3:
                                detected_type = pattern.replace(':', '').strip()
                                if current_album:
                                    albums.append(current_album)
                                current_album = {
                                    'title': line.replace(pattern, '').strip(),
                                    'type': detected_type,
                                    'tracks': [],
                                    'release_date': '',
                                    'genre': '',
                                    'length': ''
                                }
                                break
                        
                        if line.startswith('Release Date:') and current_album:
                            current_album['release_date'] = line.replace('Release Date:', '').strip()
                        elif line.startswith('Genre:') and current_album:
                            current_album['genre'] = line.replace('Genre:', '').strip()
                        elif line.startswith('Length:') and current_album:
                            current_album['length'] = line.replace('Length:', '').strip()
                        elif current_album and line and len(line) < 100:
                            # Potential track name (numbered or simple title)
                            if (line[0].isdigit() and '.' in line[:5]) or len(line.split()) <= 5:
                                current_album['tracks'].append(line)
                    
                    # Add the last album
                    if current_album:
                        albums.append(current_album)
                    
                    # If we found albums, return success
                    if albums:
                        logger.info(f"Found {len(albums)} albums for {group_name} from {url}")
                        return {
                            "success": True,
                            "total_albums": len(albums),
                            "albums": albums,
                            "discography_url": url,
                            "group": group_name
                        }
                    else:
                        logger.warning(f"No albums found in {url}, trying next URL...")
                        continue
            
            # If all URLs failed to find albums
            return {"error": f"No discography found after trying {len(urls_to_try)} URLs", "albums": []}
                    
        except Exception as e:
            logger.error(f"Error scraping discography for {group_name}: {e}")
            return {"error": str(e), "albums": []}
    
    def _generate_gallery_url(self, member_name, group_name=None):
        """Generate gallery URL berdasarkan member dan grup"""
        
        # Gallery mappings untuk subdomain dan format URL
        gallery_mappings = {
            # QWER members
            "hina qwer": "https://qwer.fandom.com/wiki/Hina/Gallery",
            "qwer hina": "https://qwer.fandom.com/wiki/Hina/Gallery",
            "chodan": "https://qwer.fandom.com/wiki/Chodan/Gallery",
            "magenta": "https://qwer.fandom.com/wiki/Magenta/Gallery",
            "siyeon": "https://qwer.fandom.com/wiki/Siyeon/Gallery",
            # Lightsum members - using kpop.fandom.com as fallback
            "hina lightsum": "https://kpop.fandom.com/wiki/Hina_(Lightsum)/Gallery",
            "lightsum hina": "https://kpop.fandom.com/wiki/Hina_(Lightsum)/Gallery",
            "siyeon qwer": "https://qwer.fandom.com/wiki/Siyeon/Gallery",
            
            # Red Velvet members (redvelvet.fandom.com)
            "irene": "https://redvelvet.fandom.com/wiki/Irene/Gallery",
            "yeri": "https://redvelvet.fandom.com/wiki/Yeri/Gallery",
            "seulgi": "https://redvelvet.fandom.com/wiki/Seulgi/Gallery",
            "wendy": "https://redvelvet.fandom.com/wiki/Wendy/Gallery",
            "joy": "https://redvelvet.fandom.com/wiki/Joy/Gallery",
            
            # Secret Number members (secretnumber.fandom.com)
            "soodam": "https://secretnumber.fandom.com/wiki/Soodam/Gallery",
            "lea": "https://secretnumber.fandom.com/wiki/Lea/Gallery",
            "jinny": "https://secretnumber.fandom.com/wiki/Jinny/Gallery",
            "denise": "https://secretnumber.fandom.com/wiki/Denise/Gallery",
            "dita": "https://secretnumber.fandom.com/wiki/Dita/Gallery",
            "zuu": "https://secretnumber.fandom.com/wiki/Zuu/Gallery",
            
            # IZ*ONE members (iz-one.fandom.com)
            "sakura": "https://iz-one.fandom.com/wiki/Sakura/Gallery",
            "chaeyeon": "https://iz-one.fandom.com/wiki/Chaeyeon/Gallery",
            "chaewon": "https://iz-one.fandom.com/wiki/Chaewon/Gallery",
            "minju": "https://iz-one.fandom.com/wiki/Minju/Gallery",
            "yujin": "https://iz-one.fandom.com/wiki/Yujin/Gallery",
            "wonyoung": "https://iz-one.fandom.com/wiki/Wonyoung/Gallery",
            
            # Dreamcatcher members (dreamcatcher.fandom.com)
            "siyeon": "https://dreamcatcher.fandom.com/wiki/Siyeon/Gallery",
            "jiu": "https://dreamcatcher.fandom.com/wiki/JiU/Gallery",
            "sua": "https://dreamcatcher.fandom.com/wiki/SuA/Gallery",
            "yoohyeon": "https://dreamcatcher.fandom.com/wiki/Yoohyeon/Gallery",
            "dami": "https://dreamcatcher.fandom.com/wiki/Dami/Gallery",
            "handong": "https://dreamcatcher.fandom.com/wiki/Handong/Gallery",
            "gahyeon": "https://dreamcatcher.fandom.com/wiki/Gahyeon/Gallery",
            
            # NewJeans members (newjeans.fandom.com)
            "minji": "https://newjeans.fandom.com/wiki/Minji/Gallery",
            "hanni": "https://newjeans.fandom.com/wiki/Hanni/Gallery",
            "danielle": "https://newjeans.fandom.com/wiki/Danielle/Gallery",
            "haerin": "https://newjeans.fandom.com/wiki/Haerin/Gallery",
            "hyein": "https://newjeans.fandom.com/wiki/Hyein/Gallery",
            
            # TWICE members (twice.fandom.com)
            "nayeon": "https://twice.fandom.com/wiki/Nayeon/Gallery",
            "jeongyeon": "https://twice.fandom.com/wiki/Jeongyeon/Gallery",
            "momo": "https://twice.fandom.com/wiki/Momo/Gallery",
            "sana": "https://twice.fandom.com/wiki/Sana/Gallery",
            "jihyo": "https://twice.fandom.com/wiki/Jihyo/Gallery",
            "mina": "https://twice.fandom.com/wiki/Mina/Gallery",
            "dahyun": "https://twice.fandom.com/wiki/Dahyun/Gallery",
            "chaeyoung": "https://twice.fandom.com/wiki/Chaeyoung/Gallery",
            "tzuyu": "https://twice.fandom.com/wiki/Tzuyu/Gallery",
            
            # aespa members (aespa.fandom.com)
            "karina": "https://aespa.fandom.com/wiki/Karina/Gallery",
            "giselle": "https://aespa.fandom.com/wiki/Giselle/Gallery",
            "winter": "https://aespa.fandom.com/wiki/Winter/Gallery",
            "ningning": "https://aespa.fandom.com/wiki/NingNing/Gallery",
            
            # Main kpop.fandom.com dengan disambiguation
            "jisoo": "https://kpop.fandom.com/wiki/Jisoo_(BLACKPINK)/Gallery",
            "jennie": "https://kpop.fandom.com/wiki/Jennie/Gallery",
            "rose": "https://kpop.fandom.com/wiki/Ros%C3%A9/Gallery",
            "lisa": "https://kpop.fandom.com/wiki/Lisa/Gallery",
            "xiumin": "https://kpop.fandom.com/wiki/Xiumin/Gallery",
            "chen": "https://kpop.fandom.com/wiki/Chen_(EXO)/Gallery",
            "tiffany": "https://kpop.fandom.com/wiki/Tiffany/Gallery",
            "taeyeon": "https://girls-generation.fandom.com/wiki/Taeyeon/Gallery",
        }
        
        member_lower = member_name.lower()
        
        # Create search key with group context for ambiguous names
        search_key = member_lower
        if group_name:
            search_key_with_group = f"{member_lower} {group_name.lower()}"
            group_member_key = f"{group_name.lower()} {member_lower}"
            
            # Check group-specific mappings first
            if search_key_with_group in gallery_mappings:
                return gallery_mappings[search_key_with_group]
            elif group_member_key in gallery_mappings:
                return gallery_mappings[group_member_key]
        
        # Check direct mapping
        if search_key in gallery_mappings:
            return gallery_mappings[search_key]
        
        # Universal pattern: try {group}.fandom.com/wiki/{member}/Gallery first
        if group_name:
            # Convert group name to subdomain format
            subdomain = self._format_group_to_subdomain(group_name)
            
            # Try group-specific subdomain with /Gallery endpoint first
            return f"https://{subdomain}.fandom.com/wiki/{member_name.title()}/Gallery"
        
        # Default fallback to main kpop.fandom.com
        return f"https://kpop.fandom.com/wiki/{member_name.title()}/Gallery"
    
    def _generate_trivia_url(self, member_name, group_name=None):
        """Generate trivia/facts URL berdasarkan member dan grup dengan support /Facts dan /Trivia"""
        
        # Trivia mappings untuk subdomain dan format URL
        trivia_mappings = {
            # QWER members (qwer.fandom.com)
            "chodan": "https://qwer.fandom.com/wiki/Chodan/Trivia",
            "magenta": "https://qwer.fandom.com/wiki/Magenta/Trivia",
            
            # Secret Number members (secretnumber.fandom.com) - uses /Facts
            "soodam": "https://secretnumber.fandom.com/wiki/Soodam/Facts",
            "lea": "https://secretnumber.fandom.com/wiki/Lea/Facts",
            "jinny": "https://secretnumber.fandom.com/wiki/Jinny/Facts",
            "denise": "https://secretnumber.fandom.com/wiki/Denise/Facts",
            "dita": "https://secretnumber.fandom.com/wiki/Dita/Facts",
            "zuu": "https://secretnumber.fandom.com/wiki/Zuu/Facts",
            
            # IZ*ONE members (iz-one.fandom.com)
            "sakura": "https://iz-one.fandom.com/wiki/Sakura/Trivia",
            "chaeyeon": "https://iz-one.fandom.com/wiki/Chaeyeon/Trivia",
            "chaewon": "https://iz-one.fandom.com/wiki/Chaewon/Trivia",
            "minju": "https://iz-one.fandom.com/wiki/Minju/Trivia",
            "yujin": "https://iz-one.fandom.com/wiki/Yujin/Trivia",
            "wonyoung": "https://iz-one.fandom.com/wiki/Wonyoung/Trivia",
            
            # BLACKPINK members - use blackpink.fandom.com subdomain
            "jisoo": "https://blackpink.fandom.com/wiki/Jisoo/Trivia",
            "jennie": "https://blackpink.fandom.com/wiki/Jennie/Trivia",
            "rose": "https://blackpink.fandom.com/wiki/Ros%C3%A9/Trivia",
            "lisa": "https://blackpink.fandom.com/wiki/Lisa/Trivia",
            
            # Dreamcatcher members - try main kpop.fandom.com
            "siyeon": "https://kpop.fandom.com/wiki/Siyeon/Trivia",
            "jiu": "https://kpop.fandom.com/wiki/JiU/Trivia",
            "sua": "https://kpop.fandom.com/wiki/SuA/Trivia",
            "yoohyeon": "https://kpop.fandom.com/wiki/Yoohyeon/Trivia",
            "dami": "https://kpop.fandom.com/wiki/Dami/Trivia",
            "handong": "https://kpop.fandom.com/wiki/Handong/Trivia",
            "gahyeon": "https://kpop.fandom.com/wiki/Gahyeon/Trivia",
            
            # NewJeans members - use newjeans.fandom.com subdomain
            "minji": "https://newjeans.fandom.com/wiki/Minji/Trivia",
            "hanni": "https://newjeans.fandom.com/wiki/Hanni/Trivia",
            "danielle": "https://newjeans.fandom.com/wiki/Danielle/Trivia",
            "haerin": "https://newjeans.fandom.com/wiki/Haerin/Trivia",
            "hyein": "https://newjeans.fandom.com/wiki/Hyein/Trivia",
            
            # TWICE members - use twice.fandom.com with /Facts endpoint
            "nayeon": "https://twice.fandom.com/wiki/Nayeon/Facts",
            "jeongyeon": "https://twice.fandom.com/wiki/Jeongyeon/Facts",
            "momo": "https://twice.fandom.com/wiki/Momo/Facts",
            "sana": "https://twice.fandom.com/wiki/Sana/Facts",
            "jihyo": "https://twice.fandom.com/wiki/Jihyo/Facts",
            "mina": "https://twice.fandom.com/wiki/Mina/Facts",
            "dahyun": "https://twice.fandom.com/wiki/Dahyun/Facts",
            "chaeyoung": "https://twice.fandom.com/wiki/Chaeyoung/Facts",
            "tzuyu": "https://twice.fandom.com/wiki/Tzuyu/Facts",
            
            # aespa members - try main kpop.fandom.com
            "karina": "https://kpop.fandom.com/wiki/Karina/Trivia",
            "giselle": "https://kpop.fandom.com/wiki/Giselle/Trivia",
            "winter": "https://kpop.fandom.com/wiki/Winter_(aespa)/Trivia",
            "ningning": "https://kpop.fandom.com/wiki/NingNing/Trivia",
        }
        
        member_lower = member_name.lower()
        
        # Check direct mapping first
        if member_lower in trivia_mappings:
            return trivia_mappings[member_lower]
        
        # Generate based on group subdomain pattern
        if group_name:
            group_lower = group_name.lower()
            
            # Universal pattern: try {group}.fandom.com/wiki/{member}/Trivia first
            # Convert group name to subdomain format
            subdomain = self._format_group_to_subdomain(group_name)
            
            # Try group-specific subdomain with /Trivia endpoint first
            return f"https://{subdomain}.fandom.com/wiki/{member_name.title()}/Trivia"
        
        # Default fallback to main kpop.fandom.com
        return f"https://kpop.fandom.com/wiki/{member_name.title()}/Trivia"
    
    def _format_group_to_subdomain(self, group_name):
        """Convert group name to fandom subdomain format"""
        group_lower = group_name.lower()
        
        # Special subdomain mappings
        subdomain_mappings = {
            "secret number": "secretnumber",
            "iz*one": "iz-one",
            "izone": "iz-one",
            "girls generation": "girls-generation",
            "girls' generation": "girls-generation",
            "snsd": "girls-generation",
            "red velvet": "redvelvet",
            "oh my girl": "oh-my-girl",
            "weki meki": "weki-meki",
            "rocket punch": "rocket-punch",
            "cherry bullet": "cherry-bullet",
            "purple kiss": "purple-kiss",
            "itzy": "itzy",
            "stray kids": "stray-kids",
            "txt": "tomorrow-x-together",
            "tomorrow x together": "tomorrow-x-together",
            "enhypen": "enhypen",
            "le sserafim": "le-sserafim",
            "ive": "ive",
            "nmixx": "nmixx",
            "kep1er": "kep1er",
            "class:y": "classy",
            "classy": "classy"
        }
        
        # Check direct mapping first
        if group_lower in subdomain_mappings:
            return subdomain_mappings[group_lower]
        
        # QWER special case
        if group_lower == "qwer":
            return "qwer"
        
        # Default: convert spaces to nothing and make lowercase
        return group_lower.replace(" ", "").replace("'", "").replace(":", "").replace("*", "")
    
    def _generate_discography_url(self, group_name):
        """Generate discography URL berdasarkan grup"""
        
        # Discography mappings untuk subdomain dan format URL
        discography_mappings = {
            # Groups with specific subdomain
            "qwer": "https://qwer.fandom.com/wiki/QWER/Discography",
            "blackpink": "https://blackpink.fandom.com/wiki/Discography",
            "red velvet": "https://redvelvet.fandom.com/wiki/Red_Velvet/Discography",
            "secret number": "https://kpop.fandom.com/wiki/Secret_Number/Discography",
            "iz*one": "https://iz-one.fandom.com/wiki/IZ*ONE/Discography",
            "izone": "https://iz-one.fandom.com/wiki/IZ*ONE/Discography",
            "dreamcatcher": "https://dreamcatcher.fandom.com/wiki/Dreamcatcher/Discography",
            "newjeans": "https://kpop.fandom.com/wiki/NewJeans/Discography",
            "twice": "https://kpop.fandom.com/wiki/Twice/Discography",
            "aespa": "https://kpop.fandom.com/wiki/Aespa/Discography",
            "girls generation": "https://girls-generation.fandom.com/wiki/Girls%27_Generation/Discography",
            "girls' generation": "https://girls-generation.fandom.com/wiki/Girls%27_Generation/Discography",
            "snsd": "https://girls-generation.fandom.com/wiki/Girls%27_Generation/Discography",
        }
        
        group_lower = group_name.lower()
        
        # Check direct mapping first
        if group_lower in discography_mappings:
            return discography_mappings[group_lower]
        
        # Universal pattern: try {group}.fandom.com/wiki/{group}/Discography
        subdomain = self._format_group_to_subdomain(group_name)
        return f"https://{subdomain}.fandom.com/wiki/{group_name.replace(' ', '_')}/Discography"

    async def scrape_kpop_image(self, query, group_name=None):
        """Scrape foto K-pop dari berbagai sumber dengan multiple fallback strategies"""
        # Clean query untuk menghindari format seperti "Hina From Qwer"
        clean_query = self._clean_member_name_from_query(query)
        
        # Enhanced image sources dengan lebih banyak fallback
        image_sources = [
            # Fandom Gallery - NEW: Primary source for member photos
            {"type": "fandom_gallery"},
            
            # KProfiles - Secondary source
            {"url": "https://kprofiles.com/{}-profile/", "selector": ".wp-image, .entry-content img, .profile-image", "type": "kprofile"},
            {"url": "https://kprofiles.com/{}-members-profile/", "selector": ".wp-image, .entry-content img, .group-image", "type": "kprofile_group"},
            {"url": "https://kprofiles.com/{}-profile-facts/", "selector": ".wp-image, .entry-content img", "type": "kprofile_facts"},
            
            # Wikipedia - Tertiary source
            {"url": "https://en.wikipedia.org/wiki/{}", "selector": ".infobox img, .thumbimage, .mw-file-element", "type": "wiki"},
            {"url": "https://id.wikipedia.org/wiki/{}", "selector": ".infobox img, .thumbimage, .mw-file-element", "type": "wiki_id"},
            
            # Google Images via Custom Search (if available)
            {"type": "google_images"},
            
            # Namu Wiki
            {"url": "https://en.namu.wiki/w/{}", "selector": ".wiki-image, .file-wrapper img", "type": "namu"},
            
            # AllKPop
            {"url": "https://www.allkpop.com/search?keyword={}", "selector": ".article-image img, .content img", "type": "allkpop"}
        ]
        
        formatted_query = clean_query.lower().replace(' ', '-')
        
        for source in image_sources:
            try:
                # Handle Fandom Gallery search - NEW
                if source["type"] == "fandom_gallery":
                    gallery_url = self._generate_gallery_url(clean_query, group_name)
                    if gallery_url:
                        logger.info(f"🖼️ Scraping image from Fandom Gallery: {gallery_url}")
                        
                        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                            async with session.get(gallery_url) as response:
                                if response.status == 200:
                                    soup = BeautifulSoup(await response.text(), 'html.parser')
                                    
                                    # Fandom gallery image selectors
                                    gallery_selectors = [
                                        ".wikia-gallery img",
                                        ".gallery img", 
                                        ".mw-gallery-traditional img",
                                        ".thumb img",
                                        ".image img",
                                        "img[data-src*='static.wikia']",
                                        "img[src*='static.wikia']"
                                    ]
                                    
                                    for selector in gallery_selectors:
                                        img_tags = soup.select(selector)
                                        if img_tags:
                                            for img in img_tags[:5]:  # Try first 5 images
                                                img_url = img.get('data-src') or img.get('src')
                                                if img_url and 'static.wikia' in img_url:
                                                    # Make URL absolute if needed
                                                    if img_url.startswith('//'):
                                                        img_url = 'https:' + img_url
                                                    elif img_url.startswith('/'):
                                                        img_url = urljoin(gallery_url, img_url)
                                                    
                                                    # Download and return first valid image
                                                    try:
                                                        async with session.get(img_url) as img_response:
                                                            if img_response.status == 200:
                                                                image_data = await img_response.read()
                                                                
                                                                # Check if image is valid size (> 10KB, < 5MB)
                                                                if 10000 < len(image_data) < 5000000:
                                                                    logger.info(f"✅ Found image from Fandom Gallery: {gallery_url}")
                                                                    return BytesIO(image_data)
                                                    except Exception as e:
                                                        logger.debug(f"Failed to download Fandom image {img_url}: {e}")
                                                        continue
                                else:
                                    logger.warning(f"HTTP {response.status} for Fandom Gallery: {gallery_url}")
                    continue
                
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
                                if any(skip in img_url.lower() for skip in ['icon', 'logo', 'avatar', 'gif']):
                                    continue

                                # Make URL absolute
                                if img_url.startswith('//'):
                                    img_url = 'https:' + img_url
                                elif img_url.startswith('/'):
                                    img_url = urljoin(url, img_url)

                                try:
                                    async with session.get(img_url) as img_response:
                                        if img_response.status == 200:
                                            image_data = await img_response.read()
                                            
                                            # Validate image size
                                            if 10000 < len(image_data) < 5000000:
                                                logger.info(f"✅ Alternative query success: {query}")
                                                return BytesIO(image_data)
                                except Exception:
                                    continue
                                    
            except Exception:
                continue
                
        return None
