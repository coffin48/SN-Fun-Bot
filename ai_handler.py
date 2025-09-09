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
        # Try to get API key from environment first, then from file
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        
        # Only use environment variable for Railway deployment
        if not self.GEMINI_API_KEY:
            logger.logger.error("GEMINI_API_KEY environment variable not found")
            self.GEMINI_API_KEY = None
        
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    
    async def chat_async(self, prompt, model="gemini-1.5-flash", max_tokens=2000):
        """Async wrapper untuk Gemini chat"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._chat_sync, prompt, model, max_tokens)
    
    def _chat_sync(self, prompt, model="gemini-1.5-flash", max_tokens=2000):
        """Synchronous Gemini API call"""
        # Validate API key
        if not self.GEMINI_API_KEY:
            logger.logger.error("Gemini API key not found")
            return self._get_fallback_response()
        
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
                "temperature": 0.7,
                "topP": 0.8,
                "topK": 40
            },
            "safetySettings": [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH", 
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                }
            ]
        }
        
        # Retry logic for API calls
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=data, timeout=30)
                response.raise_for_status()
                result = response.json()
                break  # Success, exit retry loop
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 503 and attempt < max_retries - 1:
                    # Service unavailable, retry with exponential backoff
                    wait_time = (2 ** attempt) + 1  # 2, 5, 9 seconds
                    logger.logger.warning(f"Gemini API 503 error, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    # Final attempt failed or non-503 error
                    logger.logger.error(f"Gemini API HTTP error: {e}")
                    return self._get_fallback_response()
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + 1
                    logger.logger.warning(f"Gemini API error, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.logger.error(f"Gemini API final error: {e}")
                    return self._get_fallback_response()
        else:
            # All retries failed
            logger.logger.error("All Gemini API retry attempts failed")
            return self._get_fallback_response()
        
        try:
            
            # Debug logging for troubleshooting
            logger.logger.debug(f"Gemini API full response: {result}")
            
            # Validate response structure
            if "candidates" not in result or not result["candidates"]:
                logger.logger.error(f"No candidates in API response: {result}")
                # Check if blocked by safety filters
                if "promptFeedback" in result:
                    feedback = result["promptFeedback"]
                    if "blockReason" in feedback:
                        logger.logger.warning(f"Content blocked by safety filter: {feedback['blockReason']}")
                        return "Maaf, pertanyaan ini tidak bisa dijawab karena kebijakan keamanan. Coba tanya yang lain ya! 🛡️"
                return self._get_fallback_response()
            
            candidate = result["candidates"][0]
            
            # Check if candidate was blocked by safety filters
            if "finishReason" in candidate and candidate["finishReason"] == "SAFETY":
                logger.logger.warning(f"Response blocked by safety filter: {candidate}")
                return "Maaf, respons diblokir karena kebijakan keamanan. Coba pertanyaan lain ya! 🛡️"
            
            if "content" not in candidate:
                logger.logger.error(f"No content in candidate: {candidate}")
                return self._get_fallback_response()
            
            content = candidate["content"]
            
            # Handle different content formats from Gemini API
            if "parts" not in content:
                # Check if content has 'role' only (empty response case)
                if content.get("role") == "model" and len(content) == 1:
                    logger.logger.warning(f"Empty model response from Gemini API: {content}")
                    return self._get_fallback_response()
                # Check for alternative response formats
                elif "text" in content:
                    text = content["text"]
                    if text and text.strip():
                        return text.strip()
                logger.logger.error(f"No parts in content and no alternative format: {content}")
                return self._get_fallback_response()
            
            if not content["parts"]:
                logger.logger.error(f"Empty parts array in content: {content}")
                return self._get_fallback_response()
            
            text = content["parts"][0].get("text", "")
            if not text.strip():
                logger.logger.warning("Empty text response from API")
                return self._get_fallback_response()
            
            return text.strip()
            
        except requests.exceptions.Timeout:
            logger.logger.error("Gemini API timeout")
            return "Maaf, AI sedang sibuk. Coba lagi sebentar ya! 😅"
        except requests.exceptions.ConnectionError:
            logger.logger.error("Gemini API connection error")
            return "Koneksi bermasalah. Tunggu sebentar ya! 🔄"
        except KeyError as e:
            logger.logger.error(f"Gemini API response format error: {e}")
            return self._get_fallback_response()
        except Exception as e:
            logger.logger.error(f"Gemini API unexpected error: {e}")
            return self._get_fallback_response()
    
    def create_member_summary_prompt(self, info):
        """Generate prompt untuk ringkasan member K-pop dengan input truncation"""
        # Truncate input jika terlalu panjang (max 8000 karakter untuk safety)
        max_input_length = 8000
        if len(info) > max_input_length:
            logger.logger.warning(f"Input too long ({len(info)} chars), truncating to {max_input_length}")
            info = info[:max_input_length] + "...[truncated]"
        
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
        """Generate prompt untuk ringkasan grup K-pop dengan input truncation"""
        # Truncate input jika terlalu panjang (max 8000 karakter untuk safety)
        max_input_length = 8000
        if len(info) > max_input_length:
            logger.logger.warning(f"Input too long ({len(info)} chars), truncating to {max_input_length}")
            info = info[:max_input_length] + "...[truncated]"
        
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
    
    def _get_fallback_response(self):
        """Generate fallback response when AI fails"""
        fallback_messages = [
            "Maaf, AI sedang istirahat sebentar. Coba lagi ya! 💫",
            "Lagi ada gangguan teknis nih. Tunggu sebentar ya! 🔧",
            "AI lagi loading... Coba query lain dulu ya! ⏳"
        ]
        import random
        return random.choice(fallback_messages)
    
    async def handle_general_query(self, user_input):
        """Handle pertanyaan umum non-K-pop"""
        return await self.chat_async(user_input, max_tokens=2000)
