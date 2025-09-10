"""
Bias Detector Module - AI-powered love match & fortune teller untuk Secret Number
"""
import discord
import random
import asyncio
from datetime import datetime
from logger import logger
from ai_handler import AIHandler

class BiasDetector:
    def __init__(self, ai_handler, kpop_df=None):
        self.ai_handler = ai_handler
        self.kpop_df = kpop_df
        
        # Cache for consistent match results
        # Format: {user_id: {member_name: {'result': match_result, 'count': usage_count}}}
        self.match_cache = {}
        
        # Secret Number member data (fallback)
        self.sn_members = {
            'lea': {
                'name': 'Lea',
                'korean_name': '이아',
                'position': 'Leader, Main Vocalist',
                'birthday': '1995-08-12',
                'nationality': 'Japanese-American',
                'personality': 'Charismatic, caring leader, strong vocals, multilingual',
                'color': 0xFF69B4,
                'emoji': '👑',
                'traits': ['leadership', 'caring', 'multilingual', 'strong', 'charismatic']
            },
            'dita': {
                'name': 'Dita',
                'korean_name': '디타',
                'position': 'Main Dancer, Vocalist, Visual',
                'birthday': '1999-12-25',
                'nationality': 'Indonesian',
                'personality': 'Elegant dancer, sweet personality, Christmas baby',
                'color': 0x87CEEB,
                'emoji': '💃',
                'traits': ['elegant', 'sweet', 'graceful', 'artistic', 'gentle']
            },
            'jinny': {
                'name': 'Jinny',
                'korean_name': '지니',
                'position': 'Main Rapper, Vocalist',
                'birthday': '2000-04-16',
                'nationality': 'Korean-American',
                'personality': 'Cool rapper, confident, bilingual, trendy',
                'color': 0x9370DB,
                'emoji': '🎤',
                'traits': ['confident', 'cool', 'trendy', 'bilingual', 'charismatic']
            },
            'soodam': {
                'name': 'Soodam',
                'korean_name': '수담',
                'position': 'Vocalist, Visual',
                'birthday': '2002-03-09',
                'nationality': 'Korean',
                'personality': 'Bright smile, cheerful, pure visual, energetic',
                'color': 0xFFB6C1,
                'emoji': '😊',
                'traits': ['cheerful', 'bright', 'pure', 'energetic', 'optimistic']
            },
            'denise': {
                'name': 'Denise',
                'korean_name': '데니스',
                'position': 'Vocalist, Maknae',
                'birthday': '2003-01-11',
                'nationality': 'Korean',
                'personality': 'Cute maknae, playful, youngest member energy',
                'color': 0x98FB98,
                'emoji': '🌸',
                'traits': ['playful', 'cute', 'youthful', 'energetic', 'adorable']
            },
            'minji': {
                'name': 'Minji',
                'korean_name': '민지',
                'position': 'Vocalist, Dancer',
                'birthday': '2001-05-05',
                'nationality': 'Korean',
                'personality': 'Talented all-rounder, hardworking, versatile',
                'color': 0xDDA0DD,
                'emoji': '✨',
                'traits': ['versatile', 'hardworking', 'talented', 'dedicated', 'balanced']
            },
            'zuu': {
                'name': 'Zuu',
                'korean_name': '주',
                'position': 'Vocalist, Dancer',
                'birthday': '2002-10-25',
                'nationality': 'Korean',
                'personality': 'Unique charm, mysterious aura, artistic soul',
                'color': 0x20B2AA,
                'emoji': '🌙',
                'traits': ['mysterious', 'unique', 'artistic', 'charming', 'creative']
            }
        }
        
        # Load members from database or fallback to Secret Number
        self.members = {}
        try:
            self.load_members_from_database()
        except Exception as e:
            logger.error(f"Error loading members from database: {e}")
            # Use Secret Number fallback if database loading fails
            self.members = self.sn_members.copy()
    
    def load_members_from_database(self):
        """Load all K-pop members from database"""
        try:
            if self.kpop_df is not None and not self.kpop_df.empty:
                logger.info(f"Loading {len(self.kpop_df)} members from K-pop database")
                
                # Process each member from database
                for _, row in self.kpop_df.iterrows():
                    member_key = self._create_member_key(row['Stage Name'], row['Group'])
                    
                    # Generate personality traits based on available data
                    traits = self._generate_member_traits(row)
                    personality = self._generate_personality_description(row, traits)
                    
                    self.members[member_key] = {
                        'name': row['Stage Name'],
                        'korean_name': row.get('Korean Stage Name', ''),
                        'full_name': row.get('Full Name', ''),
                        'group': row['Group'],
                        'birthday': row.get('Date of Birth', ''),
                        'position': self._guess_position_from_name(row['Stage Name']),
                        'personality': personality,
                        'color': self._generate_member_color(row['Stage Name']),
                        'emoji': self._generate_member_emoji(traits),
                        'traits': traits,
                        'instagram': row.get('Instagram', '')
                    }
                
                logger.info(f"✅ Loaded {len(self.members)} members from database")
            else:
                logger.warning("⚠️ No K-pop database available, using Secret Number fallback")
                self.members = self.sn_members.copy()
                
        except Exception as e:
            logger.error(f"Error loading members from database: {e}")
            logger.info("Using Secret Number fallback members")
            self.members = self.sn_members.copy()
    
    def _create_member_key(self, stage_name, group):
        """Create unique key for member"""
        # Use only stage name for key to avoid confusion
        return stage_name.lower().replace(' ', '_')
    
    def _generate_member_traits(self, row):
        """Generate personality traits based on member data"""
        traits = []
        
        # Trait generation based on name patterns and group
        name = row['Stage Name'].lower()
        group = row['Group'].lower()
        
        # Name-based traits
        if any(x in name for x in ['min', 'ji', 'yu']):
            traits.append('gentle')
        if any(x in name for x in ['hyun', 'jun', 'chan']):
            traits.append('charismatic')
        if any(x in name for x in ['young', 'hae', 'da']):
            traits.append('energetic')
        if any(x in name for x in ['soo', 'eun', 'ye']):
            traits.append('sweet')
        
        # Group-based traits
        if 'secret' in group:
            traits.extend(['mysterious', 'elegant'])
        elif any(x in group for x in ['twice', 'red velvet', 'blackpink']):
            traits.extend(['confident', 'trendy'])
        elif any(x in group for x in ['bts', 'exo', 'seventeen']):
            traits.extend(['charismatic', 'talented'])
        
        # Default traits if none generated
        if not traits:
            traits = random.sample(['sweet', 'charming', 'talented', 'bright', 'caring'], 3)
        
        return traits[:5]  # Max 5 traits
    
    def _generate_personality_description(self, row, traits):
        """Generate personality description"""
        trait_descriptions = {
            'gentle': 'gentle and caring',
            'charismatic': 'charismatic and confident',
            'energetic': 'energetic and lively',
            'sweet': 'sweet and adorable',
            'mysterious': 'mysterious and intriguing',
            'elegant': 'elegant and graceful',
            'confident': 'confident and bold',
            'trendy': 'trendy and stylish',
            'talented': 'talented and skilled',
            'bright': 'bright and cheerful',
            'caring': 'caring and warm'
        }
        
        descriptions = [trait_descriptions.get(trait, trait) for trait in traits[:3]]
        return f"{row['Stage Name']} from {row['Group']} - {', '.join(descriptions)}"
    
    def _guess_position_from_name(self, name):
        """Guess member position based on name patterns"""
        name_lower = name.lower()
        
        if any(x in name_lower for x in ['leader', 'cap']):
            return 'Leader'
        elif any(x in name_lower for x in ['main', 'lead']):
            return 'Main Vocalist'
        elif any(x in name_lower for x in ['rap', 'mc']):
            return 'Rapper'
        elif any(x in name_lower for x in ['dance', 'move']):
            return 'Dancer'
        else:
            positions = ['Vocalist', 'Dancer', 'Visual', 'Vocalist, Dancer']
            return random.choice(positions)
    
    def _generate_member_color(self, name):
        """Generate color based on name hash"""
        colors = [
            0xFF69B4, 0x87CEEB, 0x9370DB, 0xFFB6C1, 0x98FB98, 
            0xDDA0DD, 0x20B2AA, 0xFF1493, 0x00CED1, 0xBA55D3,
            0xFF6347, 0x40E0D0, 0xEE82EE, 0x90EE90, 0xF0E68C
        ]
        return colors[hash(name) % len(colors)]
    
    def _generate_member_emoji(self, traits):
        """Generate emoji based on traits"""
        emoji_map = {
            'gentle': '🌸',
            'charismatic': '⭐',
            'energetic': '⚡',
            'sweet': '🍯',
            'mysterious': '🌙',
            'elegant': '💎',
            'confident': '🔥',
            'trendy': '✨',
            'talented': '🎭',
            'bright': '☀️',
            'caring': '💕'
        }
        
        for trait in traits:
            if trait in emoji_map:
                return emoji_map[trait]
        
        return '🌟'  # Default emoji
    
    async def detect_bias(self, user_id: str, preferences: dict = None):
        """AI-powered bias detection based on user preferences"""
        try:
            # Generate AI prompt for bias detection
            prompt = self._create_bias_detection_prompt(user_id, preferences)
            logger.info(f"Generated bias detection prompt: {prompt[:200]}...")
            
            # Get AI response
            ai_response = await self.ai_handler.get_ai_response(prompt)
            logger.info(f"AI response received: {ai_response}")
            
            # Parse AI response to get recommended member
            recommended_member = self._parse_ai_bias_response(ai_response)
            
            return recommended_member
            
        except Exception as e:
            logger.error(f"Bias detection error: {e}")
            # Fallback to random selection
            fallback = random.choice(list(self.members.keys()))
            logger.warning(f"Using fallback member: {fallback}")
            return fallback
    
    async def love_match(self, user_id: str, member_name: str = None):
        """AI-powered love compatibility dengan Secret Number member"""
        try:
            if not member_name:
                member_name = await self.detect_bias(user_id)
            
            member_name = member_name.lower()
            
            # Try exact match first
            if member_name in self.members:
                pass  # Found exact match
            else:
                # Try fuzzy matching for similar names
                best_match = None
                best_score = 0
                
                for key in self.members.keys():
                    # Extract just the name part (before underscore if exists)
                    key_name = key.split('_')[0] if '_' in key else key
                    
                    # Simple similarity check
                    if member_name in key_name or key_name in member_name:
                        score = len(member_name) / max(len(key_name), len(member_name))
                        if score > best_score:
                            best_score = score
                            best_match = key
                
                if best_match and best_score > 0.5:
                    member_name = best_match
                    logger.info(f"Fuzzy matched '{member_name}' to '{best_match}'")
                else:
                    # No good match found, use random
                    member_name = random.choice(list(self.members.keys()))
                    logger.warning(f"No match for original input, using random: {member_name}")
            
            # Check cache for consistent results (first 5 uses)
            cache_key = f"{user_id}_{member_name}"
            if user_id in self.match_cache and member_name in self.match_cache[user_id]:
                cached_data = self.match_cache[user_id][member_name]
                if cached_data['count'] < 5:
                    # Return cached result and increment count
                    cached_data['count'] += 1
                    logger.info(f"Returning cached match result for {user_id}-{member_name} (use #{cached_data['count']}/5)")
                    return cached_data['result']
                else:
                    # After 5 uses, generate new result but don't cache it
                    logger.info(f"Cache limit reached for {user_id}-{member_name}, generating new result")
            
            member_data = self.members[member_name]
            
            # Calculate compatibility score (10-100%)
            score = random.randint(10, 100)  # Always positive for fun
            
            # Generate AI prompt for love match with score context
            prompt = self._create_love_match_prompt(user_id, member_data, score)
            
            # Get AI response
            ai_response = await self.ai_handler.get_ai_response(prompt)
            
            result = {
                'member': member_data,
                'compatibility_score': score,
                'ai_analysis': ai_response,
                'match_reasons': self._generate_match_reasons(member_data, score)
            }
            
            # Cache the result for first-time users or after cache expiry
            if user_id not in self.match_cache:
                self.match_cache[user_id] = {}
            
            if member_name not in self.match_cache[user_id] or self.match_cache[user_id][member_name]['count'] >= 5:
                self.match_cache[user_id][member_name] = {
                    'result': result,
                    'count': 1
                }
                logger.info(f"Cached new match result for {user_id}-{member_name}")
            
            return result
            
        except Exception as e:
            logger.error(f"Love match error: {e}")
            return self._fallback_love_match(member_name)
    
    async def fortune_teller(self, user_id: str, question_type: str = 'general'):
        """AI fortune teller dengan Secret Number theme"""
        try:
            # Generate AI prompt for fortune telling
            prompt = self._create_fortune_prompt(user_id, question_type)
            
            # Get AI response
            ai_response = await self.ai_handler.get_ai_response(prompt)
            
            # Select random member as fortune guide
            guide_member = random.choice(list(self.members.values()))
            
            return {
                'fortune': ai_response,
                'guide_member': guide_member,
                'fortune_type': question_type,
                'lucky_number': random.randint(1, 7),  # 7 members
                'lucky_color': guide_member['color']
            }
            
        except Exception as e:
            logger.error(f"Fortune teller error: {e}")
            return self._fallback_fortune(question_type)
    
    def _create_bias_detection_prompt(self, user_id: str, preferences: dict):
        """Create AI prompt for bias detection"""
        # Limit to random sample if too many members
        sample_members = dict(random.sample(list(self.members.items()), min(50, len(self.members))))
        
        member_info = "\n".join([
            f"- {data['name']} from {data.get('group', 'Solo Artist' if not data.get('group') else data.get('group'))}: {data.get('position', 'Member')}, {data['personality']}"
            for data in sample_members.values()
        ])
        
        pref_text = ""
        if preferences:
            pref_text = f"User preferences: {', '.join(preferences.get('traits', []))}"
        
        member_keys = list(sample_members.keys())
        
        return f"""You are a K-pop bias detector AI. Based on K-pop member profiles, recommend the best bias match.

Available Members:
{member_info}

{pref_text}

IMPORTANT: You must respond with EXACTLY ONE member key from this list:
{', '.join(member_keys)}

Choose the best match and respond with ONLY the member key, nothing else.
Example valid responses: "iu", "jimin_bts", "taeyeon_girls_generation"

Your response:"""
    
    def _create_love_match_prompt(self, user_id: str, member_data: dict, compatibility_score: int):
        """Create AI prompt for love compatibility based on score"""
        import random
        import hashlib
        
        # Create consistent hash for user-member combination to ensure same response
        hash_input = f"{user_id}{member_data['name']}".encode()
        hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
        
        # Adjust tone based on compatibility score with multiple variations
        if compatibility_score >= 80:
            examples = [
                f"Wah, kalian tuh chemistry-nya kece badai! Si {member_data['name']} yang [trait] banget cocok sama kamu yang [personality]. Dijamin deh, vibes kalian bakal klop abis! 💕",
                f"OMG! Perfect match banget nih! {member_data['name']} yang [trait] tuh literally soulmate kamu! Chemistry kalian bikin iri semua orang! 🔥✨",
                f"Astaga! Kalian tuh kayak dibuat satu sama lain! Si {member_data['name']} yang [trait] bakal bikin hidup kamu makin berwarna! Love is in the air! 💖🌟",
                f"Wuih! Chemistry level maksimal detected! {member_data['name']} yang [trait] tuh complement kamu dengan sempurna! Ini mah jodoh dari surga! 👑💕",
                f"Gila sih! Kalian tuh match-nya epic banget! Si {member_data['name']} yang [trait] bakal jadi partner in crime terbaik kamu! Relationship goals! 🚀💫"
            ]
        elif compatibility_score >= 60:
            examples = [
                f"Chemistry kalian cukup menarik nih! Si {member_data['name']} yang [trait] bisa jadi match yang oke sama kamu. Dengan sedikit usaha, hubungan kalian bisa berkembang! 😊",
                f"Hmm, ada potensi bagus nih! {member_data['name']} yang [trait] sama kamu punya chemistry yang promising. Tinggal dikembangkan aja! 💪😄",
                f"Not bad! Kalian punya foundation yang solid. Si {member_data['name']} yang [trait] bisa jadi teman yang asik, mungkin lebih! 🌸💕",
                f"Interesting combo! {member_data['name']} yang [trait] sama kamu bisa create something beautiful. Slow but steady wins the race! 🐢✨",
                f"Ada spark nih! Si {member_data['name']} yang [trait] sama kamu punya chemistry yang bisa diexplore. Worth the try! 🔍💖"
            ]
        elif compatibility_score >= 40:
            examples = [
                f"Hmm, kalian punya chemistry yang unik! Si {member_data['name']} yang [trait] mungkin butuh waktu buat connect sama kamu. Tapi hey, opposites attract kan? 😅",
                f"Challenging tapi menarik! {member_data['name']} yang [trait] sama kamu kayak puzzle yang rumit. Butuh patience tapi bisa jadi seru! 🧩😊",
                f"Plot twist! Kalian beda banget tapi siapa tau justru itu yang bikin chemistry-nya unique. Si {member_data['name']} yang [trait] bisa surprise kamu! 🎭💫",
                f"Tricky situation nih! {member_data['name']} yang [trait] sama kamu butuh effort ekstra. Tapi love conquers all, right? 💪❤️",
                f"Unexpected combo! Si {member_data['name']} yang [trait] sama kamu kayak eksperimen chemistry. Risky tapi potentially rewarding! ⚗️✨"
            ]
        else:
            examples = [
                f"Maaf, mungkin {member_data['name']} aja ga tau kalo kamu hidup 😭💔 Chemistry kalian tuh kayak air sama minyak - susah nyatu!",
                f"Waduh... {member_data['name']} yang [trait] sama kamu tuh kayak kutub utara ketemu kutub selatan. Jauh banget! 🥶😢",
                f"Brutal honesty time: Si {member_data['name']} mungkin lebih cocok sama ghost daripada sama kamu. Sorry not sorry! 👻💀",
                f"Yikes! Chemistry kalian minus banget. {member_data['name']} yang [trait] sama kamu kayak mencampur air sama api. Disaster! 🔥💧😵",
                f"Oof... {member_data['name']} mungkin butuh kacamata buat bisa notice kamu. Chemistry kalian invisible level! 👓😭"
            ]
        
        # Select consistent example based on hash
        selected_example = examples[hash_value % len(examples)]
        
        return f"""
        Kamu adalah AI analis kompatibilitas cinta yang brutally honest! Skor kompatibilitas: {compatibility_score}%
        
        Member: {member_data['name']} ({member_data.get('korean_name', '')})
        Posisi: {member_data['position']}
        Kepribadian: {member_data['personality']}
        Traits: {', '.join(member_data['traits'])}
        
        Buat analisis kompatibilitas romantis (2-3 kalimat) yang sesuai dengan skor {compatibility_score}%.
        Gunakan bahasa Indonesia yang santai, lucu, dan penuh emoji. Sebutkan traits kepribadian spesifik.
        Untuk skor rendah, jangan takut brutal dan menohok tapi tetap entertaining!
        
        Contoh gaya untuk skor ini: "{selected_example}"
        
        Bikin yang honest dan entertaining sesuai skor! 🎭
        """
    
    def _create_fortune_prompt(self, user_id: str, question_type: str):
        """Create AI prompt for fortune telling"""
        fortune_themes = {
            'love': 'hubungan romantis dan kehidupan cinta',
            'career': 'pekerjaan, studi, dan prospek karir', 
            'friendship': 'persahabatan dan koneksi sosial',
            'general': 'kehidupan secara umum dan masa depan dekat'
        }
        
        theme = fortune_themes.get(question_type, 'kehidupan umum')
        
        return f"""
        Kamu adalah peramal mistik dengan kekuatan magis K-pop yang super kece! 
        
        Buat ramalan yang positif dan menyemangati tentang {theme}.
        
        Gaya: Mistik tapi optimis, 2-3 kalimat, sebutkan energi kosmik atau magic K-pop.
        Sertakan: saran spesifik, prediksi positif, dan pesan yang bikin semangat.
        
        Contoh gaya: "Wah, energi kosmik lagi berpihak sama kamu nih! Bintang-bintang bilang kalau [prediksi positif]. Inget ya, tetep percaya sama diri sendiri dan magic K-pop bakal bantuin kamu! ✨💫"
        
        Bikin yang fun, uplifting, dan penuh magic K-pop! 🔮💕
        """
    
    def _parse_ai_bias_response(self, ai_response: str):
        """Parse AI response to extract member name"""
        ai_response = ai_response.lower().strip()
        
        # Debug logging
        logger.info(f"AI Response for bias detection: {ai_response}")
        logger.info(f"Available members: {list(self.members.keys())[:10]}...")
        
        # Clean up AI response - remove quotes, extra text
        cleaned_response = ai_response.replace('"', '').replace("'", "").strip()
        
        # Try exact match first
        if cleaned_response in self.members:
            logger.info(f"Found exact member match: {cleaned_response}")
            return cleaned_response
        
        # Try partial match - check if any member key is contained in response
        for member_name in self.members.keys():
            if member_name in cleaned_response or cleaned_response in member_name:
                logger.info(f"Found partial member match: {member_name}")
                return member_name
        
        # Try matching just the stage name part (before underscore)
        for member_key in self.members.keys():
            stage_name = member_key.split('_')[0] if '_' in member_key else member_key
            if stage_name in cleaned_response or cleaned_response in stage_name:
                logger.info(f"Found stage name match: {member_key}")
                return member_key
        
        # Fallback to random
        fallback_member = random.choice(list(self.members.keys()))
        logger.warning(f"No member found in AI response '{cleaned_response}', using fallback: {fallback_member}")
        return fallback_member
    
    def _generate_match_reasons(self, member_data: dict, score: int):
        """Generate match reasons based on compatibility score"""
        reasons = []
        
        if score >= 90:
            reasons.append(f"Harmoni kepribadian yang sempurna sama {member_data['name']}")
            reasons.append("Alignment kosmik terdeteksi! ✨")
        elif score >= 80:
            reasons.append(f"Koneksi yang kuat sama energi {member_data['name']}")
            reasons.append("Potensi kompatibilitas yang kece!")
        elif score >= 60:
            reasons.append(f"Chemistry yang manis sama {member_data['name']}")
            reasons.append("Potensi match yang menggemaskan!")
        elif score >= 40:
            reasons.append(f"Ada spark chemistry sama {member_data['name']}")
            reasons.append("Butuh sedikit effort tapi bisa kok!")
        else:
            reasons.append(f"Masih ada harapan sama {member_data['name']}")
            reasons.append("Inner beauty is the key! 💎")
        
        # Add trait-based reason
        trait = random.choice(member_data['traits'])
        reasons.append(f"Kalian berdua punya vibes {trait} yang sama")
        
        return reasons
    
    def _fallback_love_match(self, member_name: str):
        """Fallback love match when AI fails"""
        if member_name not in self.members:
            member_name = random.choice(list(self.members.keys()))
        
        member_data = self.members[member_name]
        score = random.randint(10, 100)  # Updated to match new range
        
        return {
            'member': member_data,
            'compatibility_score': score,
            'ai_analysis': f"Wah! Kamu sama {member_data['name']} tuh chemistry-nya kece banget! Kepribadian kalian saling melengkapi dengan sempurna! 💕",
            'match_reasons': self._generate_match_reasons(member_data, score)
        }
    
    def clear_match_cache(self, user_id: str = None, member_name: str = None):
        """Clear match cache for specific user/member or all cache"""
        if user_id and member_name:
            # Clear specific user-member combination
            if user_id in self.match_cache and member_name in self.match_cache[user_id]:
                del self.match_cache[user_id][member_name]
                logger.info(f"Cleared cache for {user_id}-{member_name}")
        elif user_id:
            # Clear all cache for specific user
            if user_id in self.match_cache:
                del self.match_cache[user_id]
                logger.info(f"Cleared all cache for user {user_id}")
        else:
            # Clear all cache
            self.match_cache.clear()
            logger.info("Cleared all match cache")
    
    def get_match_cache_info(self, user_id: str):
        """Get cache information for a user"""
        if user_id not in self.match_cache:
            return {}
        
        cache_info = {}
        for member_name, data in self.match_cache[user_id].items():
            cache_info[member_name] = {
                'usage_count': data['count'],
                'remaining_consistent_uses': max(0, 5 - data['count'])
            }
        
        return cache_info
    
    def _fallback_fortune(self, question_type: str):
        """Fallback fortune when AI fails"""
        fortunes = {
            'love': "Wah! Cinta lagi menghampiri kamu nih! Magic K-pop bawa peluang romantis yang seru. Stay open sama koneksi baru ya! 💕",
            'career': "Sukses lagi nunggu kamu! Kayak perjalanan idol K-pop, kerja keras kamu bakal terbayar. Keep fighting! 🌟",
            'friendship': "Persahabatan baru bakal mekar kayak chemistry member grup! Koneksi sosial bakal bawa kebahagiaan dan support. 🌸",
            'general': "Energi positif lagi ngulilingin kamu! Magic K-pop nuntun kamu menuju kebahagiaan dan kesuksesan. Trust the process! ✨"
        }
        
        guide_member = random.choice(list(self.members.values()))
        
        return {
            'fortune': fortunes.get(question_type, fortunes['general']),
            'guide_member': guide_member,
            'fortune_type': question_type,
            'lucky_number': random.randint(1, 7),
            'lucky_color': guide_member['color']
        }
    
    def get_member_info(self, member_name: str):
        """Get detailed member information"""
        member_name = member_name.lower()
        return self.members.get(member_name)
    
    def get_all_members(self):
        """Get all member data"""
        return self.members
