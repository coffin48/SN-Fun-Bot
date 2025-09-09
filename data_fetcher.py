"""
Data Fetcher Module - Menangani scraping dan API calls untuk informasi K-pop
"""
import os
import requests
from bs4 import BeautifulSoup
import re
import logger
from analytics import analytics
import time

class DataFetcher:
    def __init__(self):
        self.NEWS_API_KEY = os.getenv("NEWS_API_KEY")
        self.CSE_API_KEYS = [os.getenv(f"CSE_API_KEY_{i}") for i in range(1, 4)]
        self.CSE_IDS = [os.getenv(f"CSE_ID_{i}") for i in range(1, 4)]
        
        # Daftar situs untuk scraping dengan strategi berbeda
        self.scraping_sites = [
            {"url": "https://kprofiles.com/{}-members-profile/", "selector": ".entry-content p", "type": "kprofile_group"},
            {"url": "https://kprofiles.com/{}-profile/", "selector": ".entry-content p", "type": "kprofile_solo1"},
            {"url": "https://kprofiles.com/{}-profile-facts/", "selector": ".entry-content p", "type": "kprofile_solo2"},
            {"url": "https://kprofiles.com/?s={}", "selector": ".post-title a", "type": "profile"},
            {"url": "https://en.wikipedia.org/wiki/{}", "selector": ".mw-parser-output p", "type": "wiki"},
            {"url": "https://www.soompi.com/?s={}", "selector": ".post-title a", "type": "news"},
            {"url": "https://www.allkpop.com/search/{}", "selector": ".akp_article_title a", "type": "news"},
            {"url": "https://www.dbkpop.com/?s={}", "selector": ".entry-title a", "type": "database"},
            {"url": "https://en.namu.wiki/w/{}", "selector": ".wiki-paragraph", "type": "namu_english"},
            {"url": "https://en.namu.wiki/w/{}", "selector": ".wiki-paragraph", "type": "namu_encoded"},
            {"url": "https://en.namu.wiki/w/{}", "selector": ".wiki-paragraph", "type": "namu_hangul"}
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
            "txt": "txt-tomorrow-x-together",
            "tomorrow x together": "txt-tomorrow-x-together",
            "enhypen": "enhypen",
            "nct": "nct",
            "exo": "exo",
            "shinee": "shinee",
            "super junior": "super-junior",
            "girls generation": "girls-generation-snsd",
            "snsd": "girls-generation-snsd"
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
        """Fetch informasi K-pop dari berbagai sumber"""
        logger.logger.info(f"Starting multi-source data fetch for: {query}")
        results = []
        
        # Scraping dari berbagai situs
        logger.logger.info(f"Scraping websites for: {query}")
        scrape_results = await self._scrape_websites(query)
        results.extend(scrape_results)
        logger.logger.info(f"Website scraping completed: {len(scrape_results)} results")
        
        # Google Custom Search Engine
        logger.logger.info(f"Fetching from Google CSE for: {query}")
        cse_results = await self._fetch_from_cse(query)
        results.extend(cse_results)
        logger.logger.info(f"Google CSE completed: {len(cse_results)} results")
        
        # NewsAPI
        logger.logger.info(f"Fetching from NewsAPI for: {query}")
        news_results = await self._fetch_from_newsapi(query)
        results.extend(news_results)
        logger.logger.info(f"NewsAPI completed: {len(news_results)} results")
        
        # Bersihkan dan gabungkan hasil
        clean_data = self._clean_text(results)
        logger.logger.info(f"Data cleaning completed: {len(clean_data)} characters final")
        
        return clean_data
    
    async def _scrape_websites(self, query):
        """Scraping dari daftar website K-pop"""
        results = []
        formatted_query = query.replace(' ', '+')
        
        for i, site in enumerate(self.scraping_sites, 1):
            try:
                # Format URL berdasarkan tipe situs
                if site.get("type") in ["kprofile_group", "kprofile_solo1", "kprofile_solo2"]:
                    # Format khusus untuk KProfiles direct: lowercase dan replace space dengan dash
                    formatted_name = query.lower().replace(' ', '-')
                    
                    # Cek apakah ada format extended untuk grup ini
                    if site.get("type") == "kprofile_group" and formatted_name in self.kprofile_extended_names:
                        # Coba format extended dulu (contoh: bts-bangtan-boys-members-profile)
                        extended_name = self.kprofile_extended_names[formatted_name]
                        url = site["url"].format(extended_name)
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
                
                logger.logger.info(f"Scraping site {i}/11: {url.split('/')[2]}")
                
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
                
                if site_type in ["kprofile_group", "kprofile_solo1", "kprofile_solo2"]:
                    # KProfiles direct: langsung ambil konten dari halaman profil
                    content_elements = soup.select(site["selector"])[:10]
                    site_results = [
                        el.get_text().strip() 
                        for el in content_elements 
                        if el.get_text().strip() and len(el.get_text().strip()) > 30
                    ]
                
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
                
                logger.logger.info(f"Site {i}/7 completed: {len(site_results)} results from {url.split('/')[2]}")
                
            except Exception as e:
                logger.logger.error(f"Scraping failed for site {i}/7 ({url.split('/')[2]}): {e}")
        
        return results
    
    async def _fetch_from_cse(self, query):
        """Fetch dari Google Custom Search Engine"""
        results = []
        
        for i, (key, cse_id) in enumerate(zip(self.CSE_API_KEYS, self.CSE_IDS), 1):
            if not key or not cse_id:
                logger.logger.debug(f"CSE API {i}: Keys not configured, skipping")
                continue
            
            try:
                logger.logger.info(f"Calling Google CSE API {i}/3 for: {query}")
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
                
                logger.logger.info(f"CSE API {i}/3 completed: {len(cse_results)} results")
                break  # Success, exit loop
                
            except requests.exceptions.HTTPError as e:
                cse_time = time.time() - cse_start if 'cse_start' in locals() else 0
                analytics.track_source_performance("google_cse", False, cse_time)
                
                if e.response.status_code == 429:
                    logger.logger.warning(f"CSE API {i}/3 rate limited (429), trying next key...")
                    continue  # Try next API key
                else:
                    logger.logger.error(f"CSE API {i}/3 HTTP error: {e}")
            except Exception as e:
                cse_time = time.time() - cse_start if 'cse_start' in locals() else 0
                analytics.track_source_performance("google_cse", False, cse_time)
                logger.logger.error(f"CSE API {i}/3 failed: {e}")
        
        return results
    
    async def _fetch_from_newsapi(self, query):
        """Fetch dari NewsAPI"""
        results = []
        
        if not self.NEWS_API_KEY:
            logger.logger.debug("NewsAPI: Key not configured, skipping")
            return results
            
        try:
            logger.logger.info(f"Calling NewsAPI for: {query}")
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
            
            logger.logger.info(f"NewsAPI completed: {len(news_results)} articles")
            
        except Exception as e:
            logger.logger.error(f"NewsAPI failed: {e}")
        
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
