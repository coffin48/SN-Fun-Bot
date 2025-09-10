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
        
        # Cache for consistent match results with 5-cycle system
        # Format: {user_id: {member_name: {'result': match_result, 'count': usage_count, 'cycle': cycle_number}}}
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
                # Find all members with similar names
                similar_members = self._find_similar_members(member_name)
                
                if len(similar_members) > 1:
                    # Multiple matches found, return selection prompt
                    return self._create_member_selection_prompt(similar_members, member_name)
                elif len(similar_members) == 1:
                    # Single match found
                    member_name = similar_members[0]
                    logger.info(f"Found single match for '{member_name}': {similar_members[0]}")
                else:
                    # No good match found, use random
                    member_name = random.choice(list(self.members.keys()))
                    logger.warning(f"No match for original input, using random: {member_name}")
            
            # Check cache for consistent results with 5-cycle system
            if user_id in self.match_cache and member_name in self.match_cache[user_id]:
                cached_data = self.match_cache[user_id][member_name]
                current_cycle = (cached_data['count'] - 1) // 5  # Which 5-cycle we're in (0, 1, 2, ...)
                cycle_position = (cached_data['count'] - 1) % 5  # Position within current cycle (0-4)
                
                if cycle_position < 4:  # Still within current 5-cycle (positions 0-3, need one more)
                    # Return cached result and increment count
                    cached_data['count'] += 1
                    logger.info(f"Returning cached match result for {user_id}-{member_name} (use #{cached_data['count']}, cycle {current_cycle + 1}, position {cycle_position + 2}/5)")
                    return cached_data['result']
                else:
                    # End of 5-cycle, need to generate new result for next cycle
                    logger.info(f"End of cycle {current_cycle + 1} for {user_id}-{member_name}, generating new result")
            
            member_data = self.members[member_name]
            
            # Calculate compatibility score based on cycle number for variation
            import hashlib
            
            # Determine current cycle number
            if user_id in self.match_cache and member_name in self.match_cache[user_id]:
                current_cycle = self.match_cache[user_id][member_name]['count'] // 5
            else:
                current_cycle = 0
            
            # Generate score based on user + member + cycle for different results per cycle
            score_seed = f"{user_id}_{member_name}_cycle_{current_cycle}".encode()
            score_hash = int(hashlib.md5(score_seed).hexdigest(), 16)
            score = (score_hash % 91) + 10  # Range 10-100, different per cycle
            
            # Generate AI prompt for love match with score context (include cycle for variation)
            prompt = self._create_love_match_prompt(user_id, member_data, score, current_cycle)
            
            # Get AI response
            ai_response = await self.ai_handler.get_ai_response(prompt)
            
            result = {
                'member': member_data,
                'compatibility_score': score,
                'ai_analysis': ai_response,
                'match_reasons': self._generate_match_reasons(member_data, score, user_id, current_cycle)
            }
            
            # Cache the result for first-time users or after cache expiry
            if user_id not in self.match_cache:
                self.match_cache[user_id] = {}
            
            # Update cache with new result and count
            if member_name not in self.match_cache[user_id]:
                # First time for this user-member combination
                self.match_cache[user_id][member_name] = {
                    'result': result,
                    'count': 1,
                    'cycle': 0
                }
                logger.info(f"Cached new match result for {user_id}-{member_name} (cycle 1, use 1/5)")
            else:
                # Update existing cache with new cycle result
                self.match_cache[user_id][member_name]['result'] = result
                self.match_cache[user_id][member_name]['count'] += 1
                new_cycle = (self.match_cache[user_id][member_name]['count'] - 1) // 5
                self.match_cache[user_id][member_name]['cycle'] = new_cycle
                logger.info(f"Updated cache for {user_id}-{member_name} (cycle {new_cycle + 1}, use {((self.match_cache[user_id][member_name]['count'] - 1) % 5) + 1}/5)")
            
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
    
    def _create_love_match_prompt(self, user_id: str, member_data: dict, compatibility_score: int, cycle: int = 0):
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
        
        # Select user-specific example based on user_id + cycle hash for variation per cycle
        example_seed = f"{user_id}_{member_data['name']}_cycle_{cycle}_example".encode()
        example_hash = int(hashlib.md5(example_seed).hexdigest(), 16)
        selected_example = examples[example_hash % len(examples)]
        
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
    
    def _generate_match_reasons(self, member_data: dict, score: int, user_id: str = None, cycle: int = 0):
        """Generate match reasons based on compatibility score"""
        reasons = []
        
        if score >= 90:
            reason_options = [
                f"Harmoni kepribadian yang sempurna sama {member_data['name']}",
                f"Vibes kosmik kalian dengan {member_data['name']} sync banget!",
                f"Chemistry level maksimal terdeteksi dengan {member_data['name']}!"
            ]
            secondary_options = [
                "Alignment kosmik terdeteksi! ✨",
                "Ini mah jodoh dari langit! 👑",
                "Perfect match energy! 💫"
            ]
        elif score >= 80:
            reason_options = [
                f"Koneksi yang kuat sama energi {member_data['name']}",
                f"Chemistry yang solid dengan {member_data['name']}",
                f"Kompatibilitas tinggi sama {member_data['name']} detected!"
            ]
            secondary_options = [
                "Potensi kompatibilitas yang kece!",
                "Strong connection vibes! 🔥",
                "High compatibility score! ⭐"
            ]
        elif score >= 60:
            reason_options = [
                f"Chemistry yang manis sama {member_data['name']}",
                f"Ada koneksi menarik dengan {member_data['name']}",
                f"Potensi bagus sama {member_data['name']} nih!"
            ]
            secondary_options = [
                "Potensi match yang menggemaskan!",
                "Sweet chemistry detected! 🌸",
                "Promising connection! 💕"
            ]
        elif score >= 40:
            reason_options = [
                f"Ada spark chemistry sama {member_data['name']}",
                f"Koneksi yang challenging tapi menarik dengan {member_data['name']}",
                f"Chemistry unik sama {member_data['name']} detected!"
            ]
            secondary_options = [
                "Butuh sedikit effort tapi bisa kok!",
                "Opposites attract situation! 🎭",
                "Unique chemistry vibes! ⚡"
            ]
        else:
            reason_options = [
                f"Masih ada harapan sama {member_data['name']}",
                f"Plot twist potential dengan {member_data['name']}",
                f"Unexpected chemistry dengan {member_data['name']} mungkin?"
            ]
            secondary_options = [
                "Inner beauty is the key! 💎",
                "Miracle bisa terjadi! 🌟",
                "Never say never! 🤞"
            ]
        
        # Select user-specific reasons if user_id provided (include cycle for variation)
        if user_id:
            import hashlib
            reason_seed = f"{user_id}_{member_data['name']}_cycle_{cycle}_reason".encode()
            reason_hash = int(hashlib.md5(reason_seed).hexdigest(), 16)
            
            reasons.append(reason_options[reason_hash % len(reason_options)])
            reasons.append(secondary_options[(reason_hash + 1) % len(secondary_options)])
            
            # Add user-specific trait-based reason (also cycle-dependent)
            trait_hash = int(hashlib.md5(f"{user_id}_{member_data['name']}_cycle_{cycle}_trait".encode()).hexdigest(), 16)
            trait = member_data['traits'][trait_hash % len(member_data['traits'])]
            reasons.append(f"Kalian berdua punya vibes {trait} yang sama")
        else:
            # Fallback to random selection
            reasons.append(random.choice(reason_options))
            reasons.append(random.choice(secondary_options))
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
    
    def _find_similar_members(self, search_name: str):
        """Find all members with similar names"""
        similar_members = []
        search_name = search_name.lower()
        
        for member_key, member_data in self.members.items():
            # Check stage name
            stage_name = member_data['name'].lower()
            if search_name in stage_name or stage_name in search_name:
                similar_members.append(member_key)
                continue
            
            # Check if member_key contains the search term
            if search_name in member_key or member_key in search_name:
                similar_members.append(member_key)
                continue
                
            # Check Korean name if available
            korean_name = member_data.get('korean_name', '').lower()
            if korean_name and (search_name in korean_name or korean_name in search_name):
                similar_members.append(member_key)
        
        return similar_members
    
    def _create_member_selection_prompt(self, similar_members: list, search_name: str):
        """Create selection prompt when multiple members found"""
        selection_text = f"🔍 Ditemukan beberapa member dengan nama '{search_name}':\n\n"
        
        for i, member_key in enumerate(similar_members[:10], 1):  # Limit to 10 options
            member_data = self.members[member_key]
            group_name = member_data.get('group', 'Solo Artist')
            korean_name = member_data.get('korean_name', '')
            korean_display = f" ({korean_name})" if korean_name else ""
            
            selection_text += f"**{i}.** {member_data['name']}{korean_display} - {group_name}\n"
        
        selection_text += f"\n💡 Ketik `!sn match {search_name} [nomor]` untuk memilih!\n"
        selection_text += f"Contoh: `!sn match {search_name} 1`"
        
        return {
            'is_selection_prompt': True,
            'selection_text': selection_text,
            'similar_members': similar_members,
            'search_name': search_name
        }
    
    def handle_member_selection(self, user_id: str, search_name: str, selection_number: int):
        """Handle user's member selection by number"""
        similar_members = self._find_similar_members(search_name)
        
        if 1 <= selection_number <= len(similar_members):
            selected_member = similar_members[selection_number - 1]
            logger.info(f"User {user_id} selected member #{selection_number}: {selected_member}")
            return selected_member
        else:
            logger.warning(f"Invalid selection number {selection_number} for {search_name}")
            return None
