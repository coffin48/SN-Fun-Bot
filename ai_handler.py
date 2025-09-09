"""
AI Handler Module - Menangani integrasi dengan Google Gemini AI
"""
import os
import asyncio
import requests
import logger
from analytics import analytics
import time

class AIHandler:
    def __init__(self):
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    
    async def chat_async(self, prompt, model="gemini-1.5-flash", max_tokens=2000):
        """Async wrapper untuk Gemini chat"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._chat_sync, prompt, model, max_tokens)
    
    def _chat_sync(self, prompt, model="gemini-1.5-flash", max_tokens=2000):
        """Synchronous Gemini API call"""
        url = f"{self.base_url}?key={self.GEMINI_API_KEY}"
        headers = {
            "Content-Type": "application/json"
        }
        data = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": 0.7
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            return result["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            logger.logger.error(f"Gemini API error: {e}")
            raise
    
    def create_member_summary_prompt(self, info):
        """Generate prompt untuk ringkasan member K-pop"""
        return f"""
Rangkum konten berikut menjadi informasi penting tentang member/idol K-pop.
Fokus pada: Profile (Nama, Ultah, Social Media), Fun Fact, Rumor.
Gunakan bahasa indonesia santai, natural, dan fun, tambahkan emoticon secukupnya agar lebih emosional.
**Hanya ringkasan dari konten yang diberikan, jangan menambahkan informasi baru.**
Jangan pakai tabel, <br>, atau garis.

Konten:
{info}
"""
    
    def create_group_summary_prompt(self, info):
        """Generate prompt untuk ringkasan grup K-pop"""
        return f"""
Rangkum konten berikut menjadi informasi penting tentang grup K-pop.
Fokus pada: Debut, Nama-nama member, Discography, Prestasi, Fandom.
Gunakan bahasa indonesia santai, natural, dan fun, tambahkan emoticon secukupnya agar lebih emosional.
**Hanya ringkasan dari konten yang diberikan, jangan menambahkan informasi baru.**
Jangan pakai tabel, <br>, atau garis.

Konten:
{info}
"""
    
    async def generate_kpop_summary(self, category, info):
        """Generate ringkasan K-pop berdasarkan kategori"""
        if category == "MEMBER":
            prompt = self.create_member_summary_prompt(info)
        else:  # GROUP
            prompt = self.create_group_summary_prompt(info)
        
        return await self.chat_async(prompt, max_tokens=2000)
    
    async def handle_general_query(self, user_input):
        """Handle pertanyaan umum non-K-pop"""
        return await self.chat_async(user_input, max_tokens=2000)
