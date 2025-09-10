"""
Bias Detector - AI-powered K-pop bias detection and love matching
"""
import discord
import random
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
        
        # Cache for pending member selections
        # Format: {user_id: {'search_name': str, 'similar_members': list, 'timestamp': datetime}}
        self.pending_selections = {}
        
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
                
                # Debug: Show some Jisoo members for debugging
                jisoo_members = {k: v for k, v in self.members.items() if 'jisoo' in k.lower()}
                logger.info(f"Jisoo members in database: {list(jisoo_members.keys())}")
            else:
                logger.warning("⚠️ No K-pop database available, using Secret Number fallback")
                self.members = self.sn_members.copy()
                
        except Exception as e:
            logger.error(f"Error loading members from database: {e}")
            logger.info("Using Secret Number fallback members")
            self.members = self.sn_members.copy()
    
    def _create_member_key(self, stage_name, group):
        """Create unique key for member"""
        # Use stage name + group to ensure uniqueness for members with same names
        clean_stage = stage_name.lower().replace(' ', '_')
        clean_group = group.lower().replace(' ', '_').replace('&', 'and')
        member_key = f"{clean_stage}_{clean_group}"
        logger.debug(f"Created member key: '{member_key}' from stage_name='{stage_name}', group='{group}'")
        return member_key
    
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
    
    async def bias_detect(self, user_id: str, preferences: dict = None):
        """AI-powered bias detection based on user preferences"""
        logger.info(f"🔍 Starting bias detection for user {user_id}")
        
        try:
            # Get random member from K-pop database
            if not self.members:
                logger.error("No K-pop database available for bias detection")
                return {
                    'error': 'Database tidak tersedia, coba lagi nanti ya! 🔍'
                }
            
            available_members = list(self.members.keys())
            selected_key = random.choice(available_members)
            member_data = self.members[selected_key]
            
            # Generate user-specific compatibility score
            score_seed = f"{user_id}_bias_detect_{selected_key}"
            compatibility_score = 75 + (hash(score_seed) % 25)  # 75-99%
            
            # Generate personality-based AI analysis for bias detection
            personality_traits = [
                "kreatif dan imajinatif", "loyal dan setia", "energik dan ceria", "tenang dan bijaksana",
                "spontan dan fun", "perfeksionis", "empati tinggi", "leadership natural",
                "artistic soul", "adventurous spirit", "caring dan nurturing", "confident dan bold"
            ]
            
            user_trait = personality_traits[hash(f"{user_id}_trait") % len(personality_traits)]
            member_trait = personality_traits[hash(f"{selected_key}_trait") % len(personality_traits)]
            
            ai_prompt = f"""
            BIAS DETECTOR ANALYSIS 🎯
            
            Kamu adalah AI personality analyzer yang ahli dalam MBTI dan astrologi K-pop!
            
            User personality: {user_trait}
            {member_data['name']} personality: {member_trait}
            Compatibility score: {compatibility_score}%
            
            Analisis mengapa {member_data['name']} dari {member_data.get('group', 'Secret Number')} cocok jadi bias kamu berdasarkan:
            1. Kecocokan personality traits
            2. Vibe dan energy yang match
            3. Alasan psikologis kenapa kalian klop
            
            Gunakan bahasa Indonesia yang fun, analytical tapi tetap cute. 3-4 kalimat.
            Fokus pada ANALISIS KEPRIBADIAN, bukan ramalan!
            """
            
            ai_analysis = await self.ai_handler.get_ai_response(ai_prompt)
            
            bias_result = {
                'member_name': member_data['name'],
                'group_name': member_data.get('group', 'Secret Number'),
                'compatibility_score': compatibility_score,
                'ai_analysis': ai_analysis,
                'member_traits': member_data.get('traits', ['charming', 'talented', 'beautiful']),
                'reason': f"Kepribadian kamu sangat cocok dengan vibe {member_data['name']}! ✨"
            }
            
            logger.info(f"✅ Bias detection completed for user {user_id}: {member_data['name']}")
            return bias_result
            
        except Exception as e:
            logger.error(f"❌ Bias detection error for user {user_id}: {e}")
            return {
                'error': 'Bias detection gagal, coba lagi ya! 💕'
            }
    
    async def love_match(self, user_id: str, member_name: str, force_direct_match: bool = False):
        """Generate love match result for user and member"""
        logger.info(f"💕 Love match request: {member_name} for user {user_id}")
        
        # If force_direct_match is True, skip multiple choice detection
        if force_direct_match:
            logger.debug(f"Force direct match enabled for: '{member_name}'")
            # Verify the member exists in database
            if member_name in self.members:
                similar_members = [member_name]
            else:
                logger.error(f"Force direct match requested but member '{member_name}' not found in database")
                return {
                    'is_selection_prompt': False,
                    'error': f"Member '{member_name}' tidak ditemukan!"
                }
        # Check if member_name contains underscore (member key format)
        elif '_' in member_name and member_name in self.members:
            logger.debug(f"Direct member key detected: '{member_name}'")
            similar_members = [member_name]
        else:
            # Find similar members
            similar_members = self._find_similar_members(member_name)
        
        logger.debug(f"Similar members found: {similar_members}")
        
        if len(similar_members) == 0:
            return {
                'is_selection_prompt': False,
                'error': f"Member '{member_name}' tidak ditemukan!"
            }
        elif len(similar_members) == 1:
            # Single member found, proceed with match
            selected_member = similar_members[0]
            logger.info(f"✅ Member selected: {selected_member}")
        else:
            # Multiple members found, show selection prompt
            logger.debug(f"Multiple members found for '{member_name}': {similar_members}, showing selection prompt")
            return self._create_member_selection_prompt(similar_members, member_name, user_id)
        
        # Check cache for consistent results with 5-cycle system
        if user_id in self.match_cache and selected_member in self.match_cache[user_id]:
            cached_data = self.match_cache[user_id][selected_member]
            current_cycle = (cached_data['count'] - 1) // 5  # Which 5-cycle we're in (0, 1, 2, ...)
            cycle_position = (cached_data['count'] - 1) % 5  # Position within current cycle (0-4)
            
            if cycle_position < 4:  # Still within current 5-cycle (positions 0-3, need one more)
                # Return cached result and increment count
                cached_data['count'] += 1
                logger.debug(f"Cache hit for user {user_id}, member {selected_member}: {cached_data['count']}/5 uses")
                return cached_data['result']
            else:
                # End of 5-cycle, need to generate new result for next cycle
                logger.debug(f"End of cycle {current_cycle + 1} for {user_id}-{selected_member}, generating new result")
        
        # Generate new match result
        logger.debug(f"Cache miss for user {user_id}, member {selected_member} - generating new result")
        
        # Get member data
        member_data = self.members.get(selected_member)
        if not member_data:
            logger.error(f"Member data not found for key: {selected_member}")
            return {
                'is_selection_prompt': False,
                'error': f"Data member tidak ditemukan!"
            }
        
        # Generate compatibility score (user-specific but consistent)
        score_seed = f"{user_id}_{selected_member}_score"
        score = 30 + (hash(score_seed) % 70)  # 30-99%
        
        # Generate AI analysis based on score threshold
        ai_analysis = self._generate_ai_analysis_by_score(score, member_data['name'], user_id)
        
        # Generate match reasons based on score threshold
        match_reasons = self._generate_match_reasons_by_score(score, user_id, selected_member)
        
        # Generate match result
        match_result = {
            'member_name': member_data['name'],
            'group_name': member_data.get('group', 'Solo Artist'),
            'score': score,
            'ai_analysis': ai_analysis,
            'match_reasons': match_reasons
        }
        
        # Cache the result
        if user_id not in self.match_cache:
            self.match_cache[user_id] = {}
        
        self.match_cache[user_id][selected_member] = {
            'result': match_result,
            'count': 1
        }
        
        logger.info(f"Generated new match result for {user_id}-{selected_member}: {score}%")
        return match_result

    def clear_match_cache(self, user_id: str = None, member_name: str = None):
        """Clear match cache for specific user/member or all cache"""
        if user_id and member_name:
            # Clear specific user-member combination
            if user_id in self.match_cache and member_name in self.match_cache[user_id]:
                del self.match_cache[user_id][member_name]
                logger.debug(f"Cache reset for user {user_id}, member {member_name} after 5 uses")
        elif user_id:
            # Clear all cache for specific user
            if user_id in self.match_cache:
                del self.match_cache[user_id]
                logger.info(f"Cleared all cache for user {user_id}")
        else:
            # Clear all cache
            self.match_cache.clear()
            logger.info("Cleared all match cache")

    def _find_member_by_name_and_group(self, member_name: str, group_name: str):
        """Find specific member by name and group"""
        member_name = member_name.lower().strip()
        group_name = group_name.lower().strip()
        
        logger.debug(f"Searching for member: '{member_name}' in group: '{group_name}'")
        
        # Clean group name variations
        group_variations = [
            group_name,
            group_name.replace(' ', ''),
            group_name.replace('-', ''),
            group_name.replace('&', 'and')
        ]
        
        for member_key, member_data in self.members.items():
            stage_name = member_data['name'].lower()
            member_group = member_data.get('group', '').lower()
            
            # Check if member name matches (exact match or starts with)
            name_match = member_name == stage_name or stage_name.startswith(member_name)
            
            if name_match:
                logger.debug(f"Name match found: '{stage_name}' in group '{member_group}' (key: {member_key})")
                
                # Check if group matches any variation
                for group_var in group_variations:
                    # More flexible group matching
                    group_match = (
                        group_var == member_group or  # Exact match
                        group_var in member_group or  # Contains
                        member_group.replace(' ', '') == group_var or  # No spaces match
                        member_group.replace(' ', '').replace('-', '') == group_var or  # No spaces/dashes
                        member_group.lower() == group_var.lower() or  # Case insensitive exact
                        group_var.lower() in member_group.lower()  # Case insensitive contains
                    )
                    
                    if group_match:
                        logger.info(f"✅ Found direct match: {member_key} for '{member_name}' from '{group_name}'")
                        return member_key
                
                logger.debug(f"Group mismatch for '{stage_name}': '{member_group}' doesn't match any of {group_variations}")
        
        logger.warning(f"❌ No direct match found for '{member_name}' from '{group_name}'")
        return None
    
    def _find_similar_members(self, search_name: str):
        """Find members with similar names"""
        search_name = search_name.lower().strip()
        similar_members = []
        
        for member_key, member_data in self.members.items():
            stage_name = member_data['name'].lower()
            korean_name = member_data.get('korean_name', '').lower()
            
            # Check various matching criteria
            if (search_name == stage_name or 
                stage_name.startswith(search_name) or
                search_name in stage_name or
                (korean_name and (search_name == korean_name or korean_name.startswith(search_name))) or
                search_name == member_key.lower()):
                similar_members.append(member_key)
        
        logger.debug(f"Found {len(similar_members)} similar members for '{search_name}': {similar_members}")
        return similar_members
    
    def _create_member_selection_prompt(self, similar_members: list, search_name: str, user_id: str):
        """Create selection prompt when multiple members found"""
        selection_text = f"🔍 Ditemukan beberapa member dengan nama '{search_name}':\n\n"
        
        for i, member_key in enumerate(similar_members[:10], 1):  # Limit to 10 options
            member_data = self.members[member_key]
            group_name = member_data.get('group', 'Solo Artist')
            korean_name = member_data.get('korean_name', '')
            korean_display = f" ({korean_name})" if korean_name else ""
            
            selection_text += f"**{i}.** {member_data['name']}{korean_display} - {group_name}\n"
        
        selection_text += f"\n💡 **Cara memilih:**\n"
        selection_text += f"Gunakan: `!sn match {search_name} [nama_grup]`\n"
        selection_text += f"Contoh: `!sn match {search_name} blackpink`, `!sn match {search_name} lovelyz`"
        
        # Store pending selection for this user
        self.pending_selections[user_id] = {
            'search_name': search_name,
            'similar_members': similar_members,
            'timestamp': datetime.now()
        }
        
        return {
            'is_selection_prompt': True,
            'selection_text': selection_text,
            'similar_members': similar_members,
            'search_name': search_name
        }
    
    def handle_member_selection(self, user_id: str, search_name: str, selection_number: int):
        """Handle user's member selection by number"""
        logger.info(f"handle_member_selection called: user_id={user_id}, search_name='{search_name}', selection_number={selection_number}")
        
        # Check if user has pending selection that matches
        if user_id in self.pending_selections:
            pending = self.pending_selections[user_id]
            logger.info(f"Found pending selection for user {user_id}: {pending}")
            
            # Check if this matches the pending selection (case insensitive)
            if pending['search_name'].lower() == search_name.lower():
                similar_members = pending['similar_members']
                logger.info(f"Matching pending selection found. Similar members: {similar_members}")
                
                if 1 <= selection_number <= len(similar_members):
                    selected_member = similar_members[selection_number - 1]
                    logger.info(f"User {user_id} selected member #{selection_number}: {selected_member} from pending selection")
                    
                    # Clear the pending selection
                    del self.pending_selections[user_id]
                    logger.info(f"Cleared pending selection for user {user_id}")
                    logger.info(f"Returning selected member: '{selected_member}' (type: {type(selected_member)})")
                    return selected_member
                else:
                    logger.warning(f"Invalid selection number {selection_number} for pending selection {search_name}")
                    return None
            else:
                logger.warning(f"Search name '{search_name}' doesn't match pending '{pending['search_name']}'")
        else:
            logger.warning(f"No pending selection found for user {user_id}")
            logger.info(f"Current pending_selections keys: {list(self.pending_selections.keys())}")
        
        # Fallback to fresh search if no pending selection
        logger.info(f"No pending selection found, doing fresh search for '{search_name}'")
        similar_members = self._find_similar_members(search_name)
        logger.info(f"Fresh search found {len(similar_members)} members: {similar_members}")
        
        if 1 <= selection_number <= len(similar_members):
            selected_member = similar_members[selection_number - 1]
            logger.info(f"User {user_id} selected member #{selection_number}: {selected_member} from fresh search")
            return selected_member
        else:
            logger.warning(f"Invalid selection number {selection_number} for {search_name} (available: 1-{len(similar_members)})")
            return None
    
    async def fortune_teller(self, user_id: str, fortune_type: str = 'general'):
        """Generate fortune reading for user"""
        logger.info(f"🔮 Starting fortune reading for user {user_id}, type: {fortune_type}")
        
        try:
            # Get random guide member from K-pop database
            if not self.members:
                logger.error("No K-pop database available for fortune telling")
                return {
                    'error': 'Database tidak tersedia, coba lagi nanti ya! 🔮'
                }
            
            available_members = list(self.members.keys())
            guide_key = random.choice(available_members)
            guide_member = self.members[guide_key]
            
            # Generate user-specific fortune elements
            fortune_seed = f"{user_id}_fortune_{fortune_type}"
            lucky_number = 1 + (hash(fortune_seed) % 99)
            
            # Fortune colors
            fortune_colors = [0xFF69B4, 0x87CEEB, 0x98FB98, 0xDDA0DD, 0xF0E68C, 0xFFB6C1]
            lucky_color = fortune_colors[hash(fortune_seed + "_color") % len(fortune_colors)]
            
            # Generate mystical fortune elements
            zodiac_signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
                           "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
            tarot_cards = ["The Star", "The Sun", "The Moon", "The Lovers", "The Empress", 
                          "The Magician", "Wheel of Fortune", "The World", "The Fool"]
            
            cosmic_sign = zodiac_signs[hash(f"{user_id}_zodiac") % len(zodiac_signs)]
            tarot_card = tarot_cards[hash(f"{user_id}_tarot") % len(tarot_cards)]
            
            # Generate fortune based on type with mystical elements
            fortune_prompts = {
                'love': f"🌹 RAMALAN CINTA KOSMIK 🌹\n\n{guide_member['name']} sebagai spiritual guide kamu melihat energi cinta di sekitar kamu! Kartu tarot: {tarot_card}, Pengaruh: {cosmic_sign}",
                'career': f"💼 RAMALAN KARIR & KESUKSESAN 💼\n\n{guide_member['name']} membaca aura kesuksesan kamu! Kartu tarot: {tarot_card}, Energi: {cosmic_sign}",
                'friendship': f"👥 RAMALAN PERSAHABATAN 👥\n\n{guide_member['name']} merasakan getaran sosial di sekitar kamu! Kartu tarot: {tarot_card}, Vibe: {cosmic_sign}",
                'general': f"✨ RAMALAN KOSMIK HARIAN ✨\n\n{guide_member['name']} menerima pesan dari alam semesta buat kamu! Kartu tarot: {tarot_card}, Energi: {cosmic_sign}"
            }
            
            ai_prompt = f"""
            FORTUNE TELLER MYSTICAL READING 🔮
            
            Kamu adalah peramal kosmik K-pop yang bisa melihat masa depan!
            
            {fortune_prompts.get(fortune_type, fortune_prompts['general'])}
            Angka hoki: {lucky_number}
            
            Buat PREDIKSI MASA DEPAN yang spesifik untuk {fortune_type}:
            1. Apa yang akan terjadi dalam 1-2 minggu ke depan
            2. Peluang dan tantangan yang akan dihadapi
            3. Saran mystical untuk memaksimalkan keberuntungan
            
            Gunakan bahasa Indonesia yang mystical, prophetic, tapi tetap fun dan optimis. 4-5 kalimat.
            Fokus pada PREDIKSI MASA DEPAN, bukan analisis personality!
            """
            
            fortune_text = await self.ai_handler.get_ai_response(ai_prompt)
            
            fortune_result = {
                'fortune': fortune_text,
                'guide_member': {
                    'name': guide_member['name'],
                    'emoji': guide_member.get('emoji', '✨')
                },
                'lucky_number': lucky_number,
                'lucky_color': lucky_color,
                'fortune_type': fortune_type
            }
            
            logger.info(f"✅ Fortune reading completed for user {user_id}")
            return fortune_result
            
        except Exception as e:
            logger.error(f"❌ Fortune reading error for user {user_id}: {e}")
            return {
                'error': 'Fortune reading gagal, coba lagi ya! 🔮'
            }
    
    async def ramalan_tradisional(self, user_id: str, ramalan_type: str = 'general'):
        """Generate traditional Indonesian fortune telling (ramalan tradisional)"""
        logger.debug(f"Generating ramalan tradisional for user {user_id}, type: {ramalan_type}")
        
        try:
            # Select a random K-pop member as the "dukun"
            if not self.members:
                logger.error("No K-pop database available for ramalan tradisional")
                return {
                    'error': 'Database tidak tersedia, coba lagi nanti ya! 🌙'
                }
            
            dukun_member_key = random.choice(list(self.members.keys()))
            dukun_member = self.members[dukun_member_key]
            
            # Generate user-specific seed for consistent fortune elements
            fortune_seed = f"{user_id}_{ramalan_type}_ramalan"
            random.seed(hash(fortune_seed) % (2**32))
            
            # Traditional Indonesian fortune elements
            weton_days = ['Legi', 'Pahing', 'Pon', 'Wage', 'Kliwon']
            primbon_elements = ['Api', 'Air', 'Tanah', 'Angin', 'Logam']
            lucky_numbers = [random.randint(1, 99) for _ in range(3)]
            weton = random.choice(weton_days)
            element = random.choice(primbon_elements)
            
            # Create AI prompt for traditional fortune telling
            ai_prompt = f"""
            Kamu adalah dukun tradisional Indonesia yang fun dan modern! Berikan ramalan tradisional untuk user dengan elemen:
            - Weton: {weton}
            - Elemen: {element}
            - Angka keberuntungan: {', '.join(map(str, lucky_numbers))}
            - Tipe ramalan: {ramalan_type}
            
            Buat ramalan yang:
            1. 95% bahasa Indonesia yang lucu, fun, dan modern (kayak anak muda zaman now)
            2. 5% bahasa Jawa untuk sentuhan tradisional (cuma 1-2 kata aja)
            3. Tone yang mystical tapi cheerful dan encouraging
            4. Panjang 3-4 kalimat yang engaging
            5. Pakai emoji dan bahasa yang relatable
            
            Contoh gaya: "Wah! Berdasarkan weton {weton} dan elemen {element}, nasib kamu bakal cerah banget nih! Rejeki nomplok dari arah yang nggak disangka-sangka. Sing sabar ya, waktunya belum tepat tapi pasti dateng! ✨"
            
            Jangan terlalu formal, bikin yang fun dan bikin pembaca happy!
            """
            
            # Get AI response
            fortune_text = await self.ai_handler.get_ai_response(ai_prompt)
            
            # Reset random seed
            random.seed()
            
            return {
                'fortune': fortune_text,
                'dukun_member': dukun_member,
                'weton': weton,
                'element': element,
                'lucky_numbers': lucky_numbers,
                'type': ramalan_type
            }
            
        except Exception as e:
            logger.error(f"Error in ramalan_tradisional: {e}")
            return {
                'error': 'Ramalan tradisional gagal, coba lagi ya! 🔮'
            }
    
    def analyze_match_probability(self, threshold: int):
        """Analyze probability of getting match score above threshold"""
        logger.debug(f"Analyzing match probability for threshold {threshold}%")
        
        # Match scores range from 30-99% (70 possible values)
        total_possible_scores = 70
        scores_above_threshold = max(0, 99 - threshold)
        
        if threshold <= 30:
            probability = 100.0
        else:
            probability = (scores_above_threshold / total_possible_scores) * 100
        
        return {
            'threshold': threshold,
            'probability': round(probability, 1),
            'scores_above': scores_above_threshold,
            'total_scores': total_possible_scores
        }
    
    def get_match_statistics(self):
        """Get comprehensive match statistics"""
        logger.debug("Getting match statistics")
        
        thresholds = [20, 50, 70, 80, 90, 95]
        statistics = {
            'score_range': '30-99%',
            'total_possible_scores': 70,
            'probabilities': {}
        }
        
        for threshold in thresholds:
            prob_data = self.analyze_match_probability(threshold)
            statistics['probabilities'][f'above_{threshold}'] = prob_data
        
        return statistics
    
    def get_member_info(self, member_name: str):
        """Get member information by name"""
        logger.debug(f"Getting member info for: {member_name}")
        
        # Search in full K-pop database first
        if self.members:
            for member_key, member_data in self.members.items():
                if (member_data['name'].lower() == member_name.lower() or
                    member_data.get('korean_name', '').lower() == member_name.lower() or
                    member_key.lower() == member_name.lower()):
                    logger.debug(f"Found member in database: {member_data['name']}")
                    return member_data
        
        
        logger.warning(f"Member not found: {member_name}")
        return None
    
    def _create_bias_detection_prompt(self, member_data: dict, user_preferences: dict = None):
        """Create AI prompt for bias detection"""
        member_name = member_data['name']
        group_name = member_data.get('group', 'Secret Number')
        personality = member_data.get('personality', 'Talented and charming K-pop idol')
        
        prompt = f"""
        Analisis mengapa {member_name} dari {group_name} cocok sebagai bias untuk user ini.
        
        Informasi member:
        - Nama: {member_name}
        - Group: {group_name}
        - Kepribadian: {personality}
        
        Buat analisis yang fun, personal, dan encouraging dalam bahasa Indonesia yang cute.
        Jelaskan mengapa member ini perfect match sebagai bias.
        Panjang sekitar 2-3 kalimat yang sweet dan engaging.
        """
        
        return prompt
    
    def _generate_ai_analysis_by_score(self, score: int, member_name: str, user_id: str):
        """Generate AI analysis based on compatibility score"""
        import hashlib
        
        # Create consistent hash for user-member combination
        hash_input = f"{user_id}{member_name}analysis".encode()
        hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
        
        if score >= 90:
            analyses = [
                f"OMG! Kamu dan {member_name} tuh literally perfect match banget! Chemistry kalian kayak main character di drama Korea yang bikin baper semua orang. Vibes kalian tuh harmonis banget, kayak udah ditakdirkan dari sono! 💯✨",
                f"Astaga! {member_name} dan kamu tuh soulmate level detected nih! Kepribadian kalian complement each other dengan sempurna. Ini mah bukan chemistry biasa, ini chemistry premium yang bikin iri malaikat! 🔥💕",
                f"Wah! Kalian berdua tuh made for each other banget! {member_name} kayaknya udah nunggu kamu dari dulu deh. Chemistry kalian tuh epic level, kayak power couple yang bakal trending di Twitter! 💎👑"
            ]
        elif score >= 70:
            analyses = [
                f"Chemistry kamu sama {member_name} tuh bagus banget nih! Kalian punya connection yang strong dan vibes yang cocok. Tinggal upgrade skill komunikasi dikit lagi, bakal jadi power couple deh! 🔥💫",
                f"{member_name} dan kamu tuh ada chemistry yang promising banget! Personality kalian complement each other dengan baik. Ada potensi besar buat jadi couple goals nih! 💖⚡",
                f"Mantap! Kamu sama {member_name} punya chemistry yang solid. Vibes kalian tuh aesthetic banget dan ada connection yang natural. Relationship goals banget! 🎨👑"
            ]
        elif score >= 50:
            analyses = [
                f"Chemistry kamu sama {member_name} lumayan oke nih! Ada potensi yang bisa dikembangkan. Mungkin butuh effort lebih buat building connection, tapi definitely ada chemistry di sana! 💕⚡",
                f"Not bad! Kamu dan {member_name} punya foundation yang decent. Tinggal upgrade skill flirting dan communication, bisa jadi something special kok! 💕🎨",
                f"Ada chemistry antara kamu sama {member_name}, tapi masih perlu dipoles dikit. Dengan effort yang tepat, kalian bisa jadi couple yang sweet! 💕📈"
            ]
        elif score >= 40:
            analyses = [
                f"Hmm, chemistry kamu sama {member_name} butuh effort lebih nih. Mungkin personality kalian agak clash, tapi hey, opposites attract kan? Coba approach yang beda deh! 💸😅",
                f"Secara fisik mungkin oke, tapi chemistry sama {member_name} masih kurang spark. Mungkin perlu invest di skill flirting atau upgrade glow up game kamu! 💸🤭",
                f"Chemistry sama {member_name} masih work in progress nih. Butuh sedikit magic dan maybe budget lebih buat impress dia. Don't give up! 💸✨"
            ]
        elif score >= 30:
            analyses = [
                f"Oke, jujur aja chemistry kamu sama {member_name} masih... challenging. Tapi hey, every expert was once a beginner! Character development arc kamu baru dimulai nih! 💪✨",
                f"Chemistry sama {member_name} butuh major improvement. Tapi jangan nyerah! Plot twist bisa datang kapan aja. Saatnya upgrade diri secara total! 💪🎬",
                f"Hmm, {member_name} mungkin belum ready buat chemistry level kamu. Atau sebaliknya? Either way, time for some serious character development! 💪⏰"
            ]
        else:
            analyses = [
                f"Waduh! Chemistry kamu sama {member_name} butuh emergency intervention ASAP! Tapi plot twist: inner beauty is your secret weapon. Time for major glow up! 🧴😭",
                f"Honestly, chemistry sama {member_name} masih... very challenging. Tapi hey, everyone has their own timeline! Mungkin saatnya konsultasi beauty guru? 🧴💆‍♂️",
                f"SOS! Chemistry level sama {member_name} butuh miracle. Tapi jangan worry, dengan effort yang tepat dan maybe facial treatment, anything is possible! 🧴🚨"
            ]
        
        selected_index = hash_value % len(analyses)
        return analyses[selected_index]
    
    def _generate_match_reasons_by_score(self, score: int, user_id: str, member_key: str):
        """Generate match reasons based on compatibility score"""
        import hashlib
        
        # Create consistent hash for user-member combination
        hash_input = f"{user_id}{member_key}reasons".encode()
        hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
        
        if score >= 90:
            reason_sets = [
                ["Kalian punya soul connection yang deep banget", "Vibes kalian tuh literally in sync", "Chemistry natural yang bikin iri semua orang"],
                ["Perfect personality match dari sono", "Komunikasi kalian flow banget tanpa effort", "Aesthetic couple goals yang trending"],
                ["Soulmate energy yang kelihatan banget", "Complement each other dengan sempurna", "Power couple vibes yang epic"]
            ]
        elif score >= 70:
            reason_sets = [
                ["Chemistry yang promising dan bisa dikembangkan", "Personality traits yang complement", "Connection yang strong dan meaningful"],
                ["Vibes yang cocok dan harmonis", "Communication style yang compatible", "Potensi relationship goals yang besar"],
                ["Foundation yang solid buat relationship", "Similar interests dan values", "Chemistry yang growing dengan baik"]
            ]
        elif score >= 50:
            reason_sets = [
                ["Ada chemistry tapi butuh effort lebih", "Personality yang bisa di-adjust", "Potensi yang perlu dikembangkan"],
                ["Foundation yang decent tapi perlu upgrade", "Communication yang bisa diperbaiki", "Chemistry yang work in progress"],
                ["Compatibility yang lumayan dengan effort", "Connection yang bisa dibangun", "Potential yang ada tapi hidden"]
            ]
        elif score >= 40:
            reason_sets = [
                ["Chemistry butuh major improvement", "Personality clash yang challenging", "Butuh effort extra buat connection"],
                ["Compatibility yang... questionable", "Communication gap yang significant", "Chemistry yang butuh miracle"],
                ["Foundation yang shaky tapi not impossible", "Butuh glow up game yang serious", "Challenge level: expert mode"]
            ]
        elif score >= 30:
            reason_sets = [
                ["Chemistry level: emergency mode", "Personality yang... very different", "Butuh character development arc"],
                ["Compatibility yang butuh major overhaul", "Communication yang challenging banget", "Chemistry yang butuh plot twist"],
                ["Foundation yang butuh total reconstruction", "Challenge level: nightmare mode", "Butuh miracle dan effort maksimal"]
            ]
        else:
            reason_sets = [
                ["Chemistry level: SOS emergency", "Personality yang clash total", "Butuh intervention dari beauty guru"],
                ["Compatibility yang... let's not talk about it", "Communication gap yang massive", "Chemistry yang butuh resurrection"],
                ["Foundation yang non-existent", "Challenge level: impossible mode", "Butuh miracle, doa, dan facial treatment"]
            ]
        
        selected_index = hash_value % len(reason_sets)
        return reason_sets[selected_index]
