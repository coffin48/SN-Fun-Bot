"""
Data Fetcher Module - Menangani scraping dan API calls untuk informasi K-pop
"""
import os
import requests
from bs4 import BeautifulSoup
import re
import logger

class DataFetcher:
    def __init__(self):
        self.NEWS_API_KEY = os.getenv("NEWS_API_KEY")
        self.CSE_API_KEYS = [os.getenv(f"CSE_API_KEY_{i}") for i in range(1, 4)]
        self.CSE_IDS = [os.getenv(f"CSE_ID_{i}") for i in range(1, 4)]
        
        # Daftar situs untuk scraping
        self.scraping_sites = [
            {"url": "https://www.soompi.com/?s={}", "selector": ".post-title a"},
            {"url": "https://www.allkpop.com/search/{}", "selector": ".akp_article_title a"},
            {"url": "https://www.dbkpop.com/?s={}", "selector": ".entry-title a"},
            {"url": "https://kprofiles.com/?s={}", "selector": ".post-title a"},
            {"url": "https://en.wikipedia.org/w/index.php?search={}", "selector": ".mw-search-result-heading a"},
            {"url": "https://namu.wiki/Search?query={}", "selector": ".wiki-search-result-link"},
            {"url": "https://search.naver.com/search.naver?query={}", "selector": ".api_txt_lines.total_tit"}
        ]
    
    async def fetch_kpop_info(self, query):
        """Fetch informasi K-pop dari berbagai sumber"""
        logger.logger.info(f"🌐 Starting multi-source data fetch for: {query}")
        results = []
        
        # Scraping dari berbagai situs
        logger.logger.info(f"📄 Scraping websites for: {query}")
        scrape_results = await self._scrape_websites(query)
        results.extend(scrape_results)
        logger.logger.info(f"📄 Website scraping completed: {len(scrape_results)} results")
        
        # Google Custom Search Engine
        logger.logger.info(f"🔍 Fetching from Google CSE for: {query}")
        cse_results = await self._fetch_from_cse(query)
        results.extend(cse_results)
        logger.logger.info(f"🔍 Google CSE completed: {len(cse_results)} results")
        
        # NewsAPI
        logger.logger.info(f"📰 Fetching from NewsAPI for: {query}")
        news_results = await self._fetch_from_newsapi(query)
        results.extend(news_results)
        logger.logger.info(f"📰 NewsAPI completed: {len(news_results)} results")
        
        # Bersihkan dan gabungkan hasil
        clean_data = self._clean_text(results)
        logger.logger.info(f"🧹 Data cleaning completed: {len(clean_data)} characters final")
        
        return clean_data
    
    async def _scrape_websites(self, query):
        """Scraping dari daftar website K-pop"""
        results = []
        formatted_query = query.replace(' ', '+')
        
        for i, site in enumerate(self.scraping_sites, 1):
            try:
                url = site["url"].format(formatted_query)
                if "allkpop" in url:
                    url = site["url"].format(query.replace(' ', '-'))
                
                logger.logger.info(f"🌐 Scraping site {i}/7: {url.split('/')[2]}")
                
                response = requests.get(
                    url, 
                    timeout=5, 
                    headers={"User-Agent": "Mozilla/5.0"}
                )
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "html.parser")
                elements = soup.select(site["selector"])[:3]
                
                site_results = [
                    el.get_text().strip() 
                    for el in elements 
                    if el.get_text().strip()
                ]
                results.extend(site_results)
                
                logger.logger.info(f"✅ Site {i}/7 completed: {len(site_results)} results from {url.split('/')[2]}")
                
            except Exception as e:
                logger.logger.error(f"❌ Scraping failed for site {i}/7 ({url.split('/')[2]}): {e}")
        
        return results
    
    async def _fetch_from_cse(self, query):
        """Fetch dari Google Custom Search Engine"""
        results = []
        
        for i, (key, cse_id) in enumerate(zip(self.CSE_API_KEYS, self.CSE_IDS), 1):
            if not key or not cse_id:
                logger.logger.info(f"⚠️ CSE API {i}: Keys not configured, skipping")
                continue
            
            try:
                logger.logger.info(f"🔍 Calling Google CSE API {i}/3 for: {query}")
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
                
                logger.logger.info(f"✅ CSE API {i}/3 completed: {len(cse_results)} results")
                
            except Exception as e:
                logger.logger.error(f"❌ CSE API {i}/3 failed: {e}")
        
        return results
    
    async def _fetch_from_newsapi(self, query):
        """Fetch dari NewsAPI"""
        results = []
        
        if not self.NEWS_API_KEY:
            logger.logger.info("⚠️ NewsAPI: Key not configured, skipping")
            return results
            
        try:
            logger.logger.info(f"📰 Calling NewsAPI for: {query}")
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
            
            logger.logger.info(f"✅ NewsAPI completed: {len(news_results)} articles")
            
        except Exception as e:
            logger.logger.error(f"❌ NewsAPI failed: {e}")
        
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
