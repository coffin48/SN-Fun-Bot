"""
AI Handler Module - Menangani integrasi dengan Google Gemini AI
"""
import asyncio
import aiohttp
import json
import time
import random
import os
import requests
from logger import logger

# Optional monitoring - only import if available
try:
    from monitor_api_usage import log_api_usage
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False
    def log_api_usage(*args, **kwargs):
        pass  # No-op function if monitoring not available

class AIHandler:
    def __init__(self):
        # Multiple API keys for load balancing
        self.api_keys = []
        for i in range(1, 6):  # Support up to 5 API keys (including 2 backup keys)
            key = os.getenv(f"GEMINI_API_KEY_{i}")
            if not key and i == 1:
                key = os.getenv("GEMINI_API_KEY")  # Fallback for first key
            if key:
                self.api_keys.append(key)
        
        # Fallback to single key if no numbered keys found
        if not self.api_keys:
            single_key = os.getenv("GEMINI_API_KEY")
            if single_key:
                self.api_keys.append(single_key)
        
        if not self.api_keys:
            logger.error("No GEMINI_API_KEY found. Set GEMINI_API_KEY_1, GEMINI_API_KEY_2, GEMINI_API_KEY_3, GEMINI_API_KEY_4, GEMINI_API_KEY_5")
        else:
            logger.info(f"Loaded {len(self.api_keys)} Gemini API keys for load balancing (including backup keys)")
        
        # Multiple model options with Gemini 2.0 Flash as primary
        self.models = [
            "gemini-2.0-flash-exp",
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b"
        ]
        self.current_model_index = 0
        self.current_key_index = 0
        self.base_url_template = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        
        # Rate limiting tracking per API key
        self.last_request_times = [0] * len(self.api_keys) if self.api_keys else [0]
        self.last_request_time = 0  # Global rate limiting fallback
        self.min_request_interval = 1  # Reduced to 1 second with multiple keys
        
        # Category-specific API key assignment for optimal load distribution
        self.category_api_mapping = {
            "OBROLAN": 0,      # API Key 1 for casual conversation
            "KPOP": 1,         # API Key 2 for K-pop info
            "REKOMENDASI": 2   # API Key 3 for recommendations
        }
        
        # Backup keys (4 & 5) will be used in rotation for all categories
        # when primary keys fail or for load balancing
        
        # Fallback mapping if fewer keys available
        if len(self.api_keys) > 0:
            self.category_api_mapping = {
                "OBROLAN": 0 % len(self.api_keys),
                "KPOP": 1 % len(self.api_keys) if len(self.api_keys) > 1 else 0,
                "REKOMENDASI": 2 % len(self.api_keys) if len(self.api_keys) > 2 else 0
            }
    
    async def chat_async(self, prompt, model="gemini-2.0-flash-exp", max_tokens=2000, category=None):
        """Async wrapper untuk Gemini chat with category support"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._chat_sync, prompt, model, max_tokens, category)
    
    def _chat_sync(self, prompt, model=None, max_tokens=2000, category=None):
        """Synchronous Gemini API call with category-specific API key selection"""
        # Validate API keys
        if not self.api_keys:
            logger.error("Gemini API key not found")
            return self._get_fallback_response()
        
        # Determine preferred API key based on category
        preferred_key_index = None
        if category and category in self.category_api_mapping:
            preferred_key_index = self.category_api_mapping[category]
            if preferred_key_index < len(self.api_keys):
                logger.info(f"Using dedicated API key #{preferred_key_index + 1} for category: {category}")
        
        # Try all available models
        for model_attempt in range(len(self.models)):
            current_model = self.models[(self.current_model_index + model_attempt) % len(self.models)]
            
            # If we have a preferred key for this category, try it first
            if preferred_key_index is not None:
                current_key = self.api_keys[preferred_key_index]
                url = f"{self.base_url_template.format(model=current_model)}?key={current_key}"
                
                key_type = "primary" if preferred_key_index < 3 else "backup"
                logger.info(f"Trying model: {current_model} with {key_type} {category} API key #{preferred_key_index + 1}")
                
                result = self._try_model_request(url, prompt, max_tokens, current_model, preferred_key_index, category)
                
                if result != "MODEL_FAILED":
                    # Success with preferred key
                    self.current_model_index = (self.current_model_index + model_attempt) % len(self.models)
                    logger.info(f"✅ Success with {key_type} API key #{preferred_key_index + 1} for {category}")
                    return result
            
            # If preferred key failed or not available, try all other keys
            for key_attempt in range(len(self.api_keys)):
                current_key_index = (self.current_key_index + key_attempt) % len(self.api_keys)
                
                # Skip the preferred key if we already tried it
                if current_key_index == preferred_key_index:
                    continue
                    
                current_key = self.api_keys[current_key_index]
                url = f"{self.base_url_template.format(model=current_model)}?key={current_key}"
                
                key_type = "primary" if current_key_index < 3 else "backup"
                logger.info(f"Trying model: {current_model} with {key_type} fallback API key #{current_key_index + 1}")
                
                result = self._try_model_request(url, prompt, max_tokens, current_model, current_key_index, category)
                
                if result != "MODEL_FAILED":
                    # Success with fallback key
                    self.current_model_index = (self.current_model_index + model_attempt) % len(self.models)
                    self.current_key_index = current_key_index
                    logger.info(f"✅ Success with {key_type} fallback API key #{current_key_index + 1} for {category or 'GENERAL'}")
                    return result
            
        
        # All models and keys failed
        logger.error("All Gemini models and API keys failed")
        return self._get_fallback_response()
    
    def _try_model_request(self, url, prompt, max_tokens, model_name, api_key_index, category=None):
        """Try a single model request with retry logic and rate limiting"""
        # Rate limiting - ensure minimum interval between requests
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            logger.info(f"Rate limiting: waiting {sleep_time:.1f}s before request")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        
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
                "maxOutputTokens": min(max_tokens, 800),  # Limit tokens to reduce rate limiting
                "temperature": 0.3,  # Lower temperature for more predictable responses
                "topP": 0.8,         # Balanced creativity vs speed
                "topK": 40           # Balanced diversity vs speed
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
        request_start_time = time.time()
        
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=data, timeout=30)
                response.raise_for_status()
                result = response.json()
                
                # Log successful API call
                response_time_ms = int((time.time() - request_start_time) * 1000)
                log_api_usage(category or "GENERAL", api_key_index, response_time_ms, success=True)
                
                break  # Success, exit retry loop
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 503 and attempt < max_retries - 1:
                    # Service unavailable, retry with exponential backoff
                    wait_time = (2 ** attempt) + 1  # 2, 5, 9 seconds
                    logger.warning(f"Gemini API 503 error, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                elif e.response.status_code == 429 and attempt < max_retries - 1:
                    # Rate limit exceeded, wait longer before retry
                    wait_time = (2 ** (attempt + 2)) + 5  # 9, 21, 37 seconds
                    logger.warning(f"Gemini API rate limit (429), retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                elif e.response.status_code == 404:
                    # Model not found - try next model
                    logger.warning(f"Model {model_name} not found (404), trying next model")
                    return "MODEL_FAILED"
                else:
                    # Final attempt failed or other HTTP error
                    logger.error(f"Gemini API HTTP error for {model_name}: {e}")
                    # Log failed API call
                    response_time_ms = int((time.time() - request_start_time) * 1000)
                    log_api_usage(category or "GENERAL", api_key_index, response_time_ms, success=False)
                    return "MODEL_FAILED"
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + 1
                    logger.warning(f"Gemini API error, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Gemini API final error for {model_name}: {e}")
                    # Log failed API call
                    response_time_ms = int((time.time() - request_start_time) * 1000)
                    log_api_usage(category or "GENERAL", api_key_index, response_time_ms, success=False)
                    return "MODEL_FAILED"
        else:
            # All retries failed for this model
            logger.error(f"All retry attempts failed for model {model_name}")
            # Log failed API call
            response_time_ms = int((time.time() - request_start_time) * 1000)
            log_api_usage(category or "GENERAL", api_key_index, response_time_ms, success=False)
            return "MODEL_FAILED"
        
        try:
            
            # Debug logging for troubleshooting
            logger.debug(f"Gemini API full response: {result}")
            
            # Validate response structure
            if "candidates" not in result or not result["candidates"]:
                logger.error(f"No candidates in API response: {result}")
                # Check if blocked by safety filters
                if "promptFeedback" in result:
                    feedback = result["promptFeedback"]
                    if "blockReason" in feedback:
                        logger.warning(f"Content blocked by safety filter: {feedback['blockReason']}")
                        return "Maaf, pertanyaan ini tidak bisa dijawab karena kebijakan keamanan. Coba tanya yang lain ya! 🛡️"
                return "MODEL_FAILED"
            
            candidate = result["candidates"][0]
            
            # Check if candidate was blocked by safety filters
            if "finishReason" in candidate and candidate["finishReason"] == "SAFETY":
                logger.warning(f"Response blocked by safety filter: {candidate}")
                return "Maaf, respons diblokir karena kebijakan keamanan. Coba pertanyaan lain ya! 🛡️"
            
            if "content" not in candidate:
                logger.error(f"No content in candidate: {candidate}")
                return "MODEL_FAILED"
            
            content = candidate["content"]
            
            # Handle different content formats from Gemini API
            if "parts" not in content:
                # Check if content has 'role' only (empty response case)
                if content.get("role") == "model" and len(content) == 1:
                    logger.warning(f"Empty model response from Gemini API: {content}")
                    return "MODEL_FAILED"
                # Check for alternative response formats
                elif "text" in content:
                    text = content["text"]
                    if text and text.strip():
                        return text.strip()
                logger.error(f"No parts in content and no alternative format: {content}")
                return "MODEL_FAILED"
            
            if not content["parts"]:
                logger.error(f"Empty parts array in content: {content}")
                return "MODEL_FAILED"
            
            text = content["parts"][0].get("text", "")
            if not text.strip():
                logger.warning("Empty text response from API")
                return "MODEL_FAILED"
            
            return text.strip()
            
        except requests.exceptions.Timeout:
            logger.error(f"Gemini API timeout for model {model_name}")
            return "MODEL_FAILED"
        except requests.exceptions.ConnectionError:
            logger.error(f"Gemini API connection error for model {model_name}")
            return "MODEL_FAILED"
        except KeyError as e:
            logger.error(f"Gemini API response format error for {model_name}: {e}")
            return "MODEL_FAILED"
        except Exception as e:
            logger.error(f"Gemini API unexpected error for {model_name}: {e}")
            return "MODEL_FAILED"
    
    def create_member_summary_prompt(self, info):
        """Generate prompt untuk ringkasan member K-pop dengan input truncation"""
        # Truncate input jika terlalu panjang (max 8000 karakter untuk safety)
        max_input_length = 8000
        if len(info) > max_input_length:
            logger.warning(f"Input too long ({len(info)} chars), truncating to {max_input_length}")
            info = info[:max_input_length] + "...[truncated]"
        
        return f"""Buat info K-pop member berikut:
Format:
- Nama: [nama lengkap]
- Tanggal Lahir: [tanggal lahir] 
- Fun Fact: [fakta menarik]
- Rumor: [rumor atau "Gak ada rumor yang kesebut di sini, aman!"]
- Social Media: [akun social media dengan emoji yang sesuai, contoh: "𝕏 @username, 📸 @username, 📺 YouTube Channel"]

Awali dengan intro singkat natural (contoh: "Ini info tentang [nama]" atau "Berikut data [nama]"), lalu langsung ke format. Natural + emoticon. Hindari intro berlebihan seperti "gaya santai dan fun". Hanya dari konten yang diberikan.

{info}"""
    
    def create_group_summary_prompt(self, info):
        """Generate prompt untuk ringkasan grup K-pop dengan input truncation"""
        # Truncate input jika terlalu panjang (max 8000 karakter untuk safety)
        max_input_length = 8000
        if len(info) > max_input_length:
            logger.warning(f"Input too long ({len(info)} chars), truncating to {max_input_length}")
            info = info[:max_input_length] + "...[truncated]"
        
        return f"""Buat info K-pop grup berikut:
Format:
- Debut: [tanggal debut dan agensi]
- Members: [Nama (1 posisi), contoh: "Jisoo (Visual), Jennie (Rapper)"]
- Discography: [album dan lagu hits]
- Prestasi: [penghargaan penting]
- Fandom: [nama fandom dan facts]
- Social Media: [akun official grup dengan emoji, contoh: "𝕏 @official_account, 📸 @official_account, 📺 YouTube Channel"]

Members: HANYA 1 posisi per nama. Awali dengan intro singkat natural (contoh: "Ini info tentang [nama grup]" atau "Berikut data [nama grup]"), lalu langsung ke format. Natural + emoticon. Hindari intro berlebihan seperti "gaya santai dan fun". Hanya dari konten yang diberikan.

{info}"""
    
    async def generate_kpop_summary(self, category, info):
        """Generate ringkasan K-pop berdasarkan kategori"""
        if category == "MEMBER" or category == "MEMBER_GROUP":
            prompt = self.create_member_summary_prompt(info)
        else:  # GROUP
            prompt = self.create_group_summary_prompt(info)
        
        return await self.chat_async(prompt, max_tokens=2000, category="KPOP")
    
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
        """Handle pertanyaan umum non-K-pop dengan optimasi"""
        # Reduced max_tokens untuk response time yang lebih cepat
        return await self.chat_async(user_input, max_tokens=800, category="OBROLAN")
