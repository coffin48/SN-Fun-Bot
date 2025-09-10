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
            
            # Get AI response
            ai_response = await self.ai_handler.get_ai_response(prompt)
            
            # Parse AI response to get recommended member
            recommended_member = self._parse_ai_bias_response(ai_response)
            
            return recommended_member
            
        except Exception as e:
            logger.error(f"Bias detection error: {e}")
            # Fallback to random selection
            return random.choice(list(self.members.keys()))
    
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
            
            member_data = self.members[member_name]
            
            # Generate AI prompt for love match
            prompt = self._create_love_match_prompt(user_id, member_data)
            
            # Get AI response
            ai_response = await self.ai_handler.get_ai_response(prompt)
            
            # Calculate compatibility score (10-100%)
            score = random.randint(10, 100)  # Always positive for fun
            
            return {
                'member': member_data,
                'compatibility_score': score,
                'ai_analysis': ai_response,
                'match_reasons': self._generate_match_reasons(member_data, score)
            }
            
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
            f"- {data['name']} from {data.get('group', 'Unknown')}: {data.get('position', 'Member')}, {data['personality']}"
            for data in sample_members.values()
        ])
        
        pref_text = ""
        if preferences:
            pref_text = f"User preferences: {', '.join(preferences.get('traits', []))}"
        
        member_keys = list(sample_members.keys())
        
        return f"""
        You are a K-pop bias detector AI. Based on K-pop member profiles, recommend the best bias match.
        
        Available Members:
        {member_info}
        
        {pref_text}
        
        Analyze personality compatibility and recommend ONE member key from this list:
        {', '.join(member_keys[:10])}...
        
        Respond with just the member key (e.g., "hyuna_4minute" or "jimin_bts").
        """
    
    def _create_love_match_prompt(self, user_id: str, member_data: dict):
        """Create AI prompt for love compatibility"""
        return f"""
        Kamu adalah AI analis kompatibilitas cinta yang seru dan lucu! Buat analisis chemistry yang fun dan positif dalam bahasa Indonesia yang natural dan menggemaskan.
        
        Member: {member_data['name']} ({member_data.get('korean_name', '')})
        Posisi: {member_data['position']}
        Kepribadian: {member_data['personality']}
        Traits: {', '.join(member_data['traits'])}
        
        Buat analisis kompatibilitas romantis (2-3 kalimat) yang menjelaskan kenapa ini match yang sempurna banget.
        Gunakan bahasa Indonesia yang santai, lucu, dan penuh emoji. Sebutkan traits kepribadian spesifik dan alasan kenapa cocok.
        
        Contoh gaya: "Wah, kalian tuh chemistry-nya kece badai! Si {member_data['name']} yang [trait] banget cocok sama kamu yang [personality]. Dijamin deh, vibes kalian bakal klop abis! 💕"
        
        Bikin yang wholesome, fun, dan bikin baper! 🥰
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
        
        # Check if any member name is in the response
        for member_name in self.members.keys():
            if member_name in ai_response:
                return member_name
        
        # Fallback to random
        return random.choice(list(self.members.keys()))
    
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
