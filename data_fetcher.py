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
        results = []
        
        # Scraping dari berbagai situs
        results.extend(await self._scrape_websites(query))
        
        # Google Custom Search Engine
        results.extend(await self._fetch_from_cse(query))
        
        # NewsAPI
        results.extend(await self._fetch_from_newsapi(query))
        
        # Bersihkan dan gabungkan hasil
        return self._clean_text(results)
    
    async def _scrape_websites(self, query):
        """Scraping dari daftar website K-pop"""
        results = []
        formatted_query = query.replace(' ', '+')
        
        for site in self.scraping_sites:
            try:
                url = site["url"].format(formatted_query)
                if "allkpop" in url:
                    url = site["url"].format(query.replace(' ', '-'))
                
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
                
            except Exception as e:
                logger.logger.error(f"Scraping gagal untuk {url}: {e}")
        
        return results
    
    async def _fetch_from_cse(self, query):
        """Fetch dari Google Custom Search Engine"""
        results = []
        
        for key, cse_id in zip(self.CSE_API_KEYS, self.CSE_IDS):
            if not key or not cse_id:
                continue
                
            try:
                url = f"https://www.googleapis.com/customsearch/v1"
                params = {
                    "q": query,
                    "key": key,
                    "cx": cse_id,
                    "num": 3
                }
                
                response = requests.get(url, params=params, timeout=5)
                response.raise_for_status()
                
                items = response.json().get("items", [])
                cse_results = [
                    f"{item['title']} - {item.get('link', '')}" 
                    for item in items
                ]
                results.extend(cse_results)
                
            except Exception as e:
                logger.logger.error(f"CSE request gagal: {e}")
        
        return results
    
    async def _fetch_from_newsapi(self, query):
        """Fetch dari NewsAPI"""
        results = []
        
        if not self.NEWS_API_KEY:
            return results
            
        try:
            url = "https://newsapi.org/v2/everything"
            params = {
                "q": query,
                "pageSize": 3,
                "apiKey": self.NEWS_API_KEY
            }
            
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            
            articles = response.json().get("articles", [])
            news_results = [
                f"{article['title']} - {article['url']}" 
                for article in articles
            ]
            results.extend(news_results)
            
        except Exception as e:
            logger.logger.error(f"NewsAPI request gagal: {e}")
        
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
