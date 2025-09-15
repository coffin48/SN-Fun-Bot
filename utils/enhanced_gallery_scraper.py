#!/usr/bin/env python3
"""
Enhanced gallery scraper dengan support untuk multiple sections dan offset
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
import random
from typing import List, Dict

class EnhancedGalleryScraper:
    """Enhanced scraper untuk Fandom gallery dengan section support"""
    
    def __init__(self):
        self.session = None
    
    async def scrape_gallery_with_sections(self, member_name: str, group_name: str, max_photos: int = 20) -> Dict:
        """Scrape gallery dari multiple sections dengan variasi"""
        try:
            # Generate base gallery URL
            gallery_url = self._generate_gallery_url(member_name, group_name)
            if not gallery_url:
                return {"error": "Could not generate gallery URL", "images": []}
            
            # Define gallery sections untuk scraping
            sections_to_scrape = [
                "Promotional",
                "Concept_Photos", 
                "Music_Videos",
                "Live_Performances",
                "Photoshoots",
                "Events",
                "Behind_the_Scenes",
                "Social_Media",
                "Magazine",
                "Airport"
            ]
            
            all_images = []
            
            # Scrape dari multiple sections
            for section in sections_to_scrape:
                section_url = f"{gallery_url}#{section}"
                section_images = await self._scrape_single_section(section_url, section, member_name)
                
                if section_images:
                    # Add section info ke setiap image
                    for img in section_images:
                        img['section'] = section
                    
                    all_images.extend(section_images)
                    
                    # Stop jika sudah cukup foto
                    if len(all_images) >= max_photos * 3:  # Buffer untuk filtering
                        break
                
                # Small delay between sections
                await asyncio.sleep(0.5)
            
            # Filter dan randomize
            filtered_images = self._filter_and_randomize_images(all_images, max_photos)
            
            return {
                "success": True,
                "images": filtered_images,
                "total_found": len(all_images),
                "sections_scraped": len([s for s in sections_to_scrape if any(img.get('section') == s for img in all_images)]),
                "url": gallery_url,
                "member": member_name,
                "group": group_name
            }
            
        except Exception as e:
            return {"error": str(e), "images": []}
    
    async def _scrape_single_section(self, section_url: str, section_name: str, member_name: str) -> List[Dict]:
        """Scrape single gallery section"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.get(section_url, timeout=10) as response:
                if response.status != 200:
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                images = []
                
                # Multiple selectors untuk comprehensive scraping
                selectors = [
                    '.wikia-gallery-item img',
                    '.gallery img', 
                    '.thumbinner img',
                    '.gallerybox img',
                    'img[src*="static.wikia"]'
                ]
                
                for selector in selectors:
                    items = soup.select(selector)
                    
                    for img in items:
                        src = img.get('src') or img.get('data-src')
                        if src and self._is_valid_wikia_image(src):
                            clean_src = self._clean_image_url(src)
                            
                            # Avoid duplicates
                            if not any(existing['url'] == clean_src for existing in images):
                                images.append({
                                    'url': clean_src,
                                    'alt': img.get('alt', ''),
                                    'type': f'{section_name}_image',
                                    'selector': selector
                                })
                
                return images[:50]  # Limit per section
                
        except Exception as e:
            print(f"Error scraping section {section_name}: {e}")
            return []
    
    def _filter_and_randomize_images(self, images: List[Dict], max_photos: int) -> List[Dict]:
        """Filter dan randomize images untuk variasi maksimal"""
        if not images:
            return []
        
        # Remove duplicates berdasarkan URL
        unique_images = []
        seen_urls = set()
        
        for img in images:
            if img['url'] not in seen_urls:
                unique_images.append(img)
                seen_urls.add(img['url'])
        
        # Group by section untuk distribusi merata
        sections = {}
        for img in unique_images:
            section = img.get('section', 'unknown')
            if section not in sections:
                sections[section] = []
            sections[section].append(img)
        
        # Ambil foto dari berbagai section secara merata
        selected_images = []
        section_names = list(sections.keys())
        
        while len(selected_images) < max_photos and any(sections.values()):
            for section_name in section_names:
                if len(selected_images) >= max_photos:
                    break
                
                if sections[section_name]:
                    # Random pick dari section ini
                    img = random.choice(sections[section_name])
                    selected_images.append(img)
                    sections[section_name].remove(img)
        
        # Final shuffle untuk randomness
        random.shuffle(selected_images)
        
        return selected_images[:max_photos]
    
    def _generate_gallery_url(self, member_name: str, group_name: str) -> str:
        """Generate gallery URL berdasarkan member dan grup"""
        # Simplified version - bisa diperluas sesuai kebutuhan
        if group_name and group_name.lower() == 'aespa':
            return f"https://aespa.fandom.com/wiki/{member_name.title()}/Gallery"
        else:
            return f"https://kpop.fandom.com/wiki/{member_name.title()}/Gallery"
    
    def _is_valid_wikia_image(self, src: str) -> bool:
        """Check if image URL is valid Wikia image"""
        if not src:
            return False
        
        # Must be Wikia image
        if 'static.wikia' not in src and 'vignette.wikia' not in src:
            return False
        
        # Skip logos, icons, etc
        skip_patterns = [
            'site-logo',
            'favicon',
            'icon',
            'logo.png',
            'avatar',
            'user-avatar'
        ]
        
        src_lower = src.lower()
        for pattern in skip_patterns:
            if pattern in src_lower:
                return False
        
        return True
    
    def _clean_image_url(self, src: str) -> str:
        """Clean image URL dari revision dan query parameters"""
        # Remove revision path
        clean_src = re.sub(r'/revision/.*?/', '/', src)
        # Remove query parameters
        clean_src = re.sub(r'\?.*$', '', clean_src)
        return clean_src
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
            self.session = None

# Test function
async def test_enhanced_scraper():
    """Test enhanced scraper"""
    scraper = EnhancedGalleryScraper()
    
    try:
        result = await scraper.scrape_gallery_with_sections("karina", "aespa", 10)
        
        if result.get('success'):
            print(f"Success: {result['total_found']} total images, {len(result['images'])} selected")
            print(f"Sections scraped: {result['sections_scraped']}")
            
            for i, img in enumerate(result['images'][:5], 1):
                print(f"{i}. {img['section']}: {img['url'][:80]}...")
        else:
            print(f"Failed: {result.get('error')}")
    
    finally:
        await scraper.cleanup()

if __name__ == "__main__":
    asyncio.run(test_enhanced_scraper())
