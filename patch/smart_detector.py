# patch/smart_detector.py
from rapidfuzz import fuzz
from patch.stopwordlist import STOPWORDS
import re

# Import logger at module level to avoid circular imports
try:
    from logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

class SmartKPopDetector:
    def __init__(self, kpop_df, threshold=85):
        self.threshold = threshold
        self.kpop_df = kpop_df
        
        # Exception list untuk nama K-pop pendek yang valid
        self.short_name_exceptions = ['iu', 'cl', 'gd', 'top', 'key', 'joy', 'kai', 'jin', 'rm', 'jb', 'hina', 'txt']
        
        # Hardcoded groups yang belum ada di database
        self.additional_groups = {
            'wooah': 'WOOAH',
            'woo!ah!': 'WOOAH', 
            'woah': 'WOOAH',
            'qwer': 'QWER',
            'blackpink': 'BLACKPINK',
            'bp': 'BLACKPINK',
            'bts': 'BTS',
            'twice': 'TWICE',
            'newjeans': 'NewJeans',
            'ive': 'IVE',
            'aespa': 'aespa',
            'itzy': 'ITZY',
            'gidle': '(G)I-DLE',
            'g-idle': '(G)I-DLE',
            'lesserafim': 'LE SSERAFIM',
            'le_sserafim': 'LE SSERAFIM',
            'nmixx': 'NMIXX',
            'stayc': 'STAYC'
        }
        
        # Blacklist untuk nama member yang terlalu umum atau problematik
        self.member_name_blacklist = ['u', 'n', 'i']
        
        # Priority K-pop names yang harus dicek dulu sebelum casual conversation
        self.priority_kpop_names = set()
        
        # Pre-build indexes untuk performa
        self._build_indexes()
    
    def _build_indexes(self):
        """Build indexes untuk pencarian cepat"""
        self.member_names = {}
        self.group_names = {}
        self.aliases = {}
        self.priority_kpop_names = set()
        
        # First pass: Build group names index
        for idx, row in self.kpop_df.iterrows():
            group = str(row.get("Group", "")).strip()
            if group:
                group_lower = group.lower()
                if group_lower not in self.group_names:
                    self.group_names[group_lower] = []
                self.group_names[group_lower].append((group, idx))
                # Tambahkan grup ke priority names dengan prioritas tinggi
                self.priority_kpop_names.add(group_lower)
        
        # Add hardcoded additional groups
        for group_key, group_name in self.additional_groups.items():
            if group_key not in self.group_names:
                self.group_names[group_key] = []
            self.group_names[group_key].append((group_name, -1))  # -1 untuk hardcoded groups
            self.priority_kpop_names.add(group_key)
        
        # Second pass: Build member names, avoiding conflicts with group names
        for idx, row in self.kpop_df.iterrows():
            if "Stage Name" in row and str(row["Stage Name"]).strip():
                name = str(row["Stage Name"]).strip()
                name_lower = name.lower()
                
                # Skip jika nama ini sudah ada sebagai grup atau dalam blacklist
                if name_lower in self.group_names or name_lower in self.member_name_blacklist:
                    continue
                    
                if name_lower not in self.member_names:
                    self.member_names[name_lower] = []
                self.member_names[name_lower].append((name, idx))
                self.priority_kpop_names.add(name_lower)
            
            # Full Name sebagai alias - skip blacklisted names
            if "Full Name" in row and str(row["Full Name"]).strip():
                full_name = str(row["Full Name"]).strip()
                full_name_lower = full_name.lower()
                
                # Skip jika dalam blacklist atau konflik dengan grup
                if full_name_lower in self.member_name_blacklist or full_name_lower in self.group_names:
                    continue
                    
                if full_name_lower not in self.aliases:
                    self.aliases[full_name_lower] = []
                self.aliases[full_name_lower].append((full_name, idx, "MEMBER"))
                # Tambahkan ke priority names
                self.priority_kpop_names.add(full_name_lower)
            
            # Korean Stage Name sebagai alias - skip blacklisted names
            if "Korean Stage Name" in row and str(row["Korean Stage Name"]).strip():
                korean_name = str(row["Korean Stage Name"]).strip()
                korean_name_lower = korean_name.lower()
                
                # Skip jika dalam blacklist atau konflik dengan grup
                if korean_name_lower in self.member_name_blacklist or korean_name_lower in self.group_names:
                    continue
                    
                if korean_name_lower not in self.aliases:
                    self.aliases[korean_name_lower] = []
                self.aliases[korean_name_lower].append((korean_name, idx, "MEMBER"))
                # Tambahkan ke priority names
                self.priority_kpop_names.add(korean_name_lower)
    
    def detect(self, user_input, conversation_context=None):
        """
        Deteksi K-pop dengan kategorisasi spesifik dan context-aware transitions
        Returns: (category, detected_name, multiple_matches)
        Categories: MEMBER, GROUP, MEMBER_GROUP, OBROLAN, REKOMENDASI, MULTIPLE
        """
        # Check additional groups first
        input_lower = user_input.lower().strip()
        try:
            logger.debug(f"🔍 Checking additional_groups for '{input_lower}'")
            logger.debug(f"📋 Available additional_groups: {list(self.additional_groups.keys())}")
        except:
            pass  # Skip debug if logger not available
        
        if input_lower in self.additional_groups:
            try:
                logger.debug(f"✅ Found in additional_groups: {self.additional_groups[input_lower]}")
            except:
                pass
            return "GROUP", self.additional_groups[input_lower], []
        
        input_norm = user_input.strip()
        input_lower = input_norm.lower()
        
        # Debug logging
        try:
            logger.debug(f"🔍 Detecting: '{input_norm}' (lower: '{input_lower}')")
            logger.debug(f"📊 Priority names contains '{input_lower}': {input_lower in self.priority_kpop_names}")
        except:
            pass  # Skip debug if logger not available
        
        # Context-aware transition detection
        if conversation_context:
            transition_result = self._detect_context_transition(input_lower, conversation_context)
            if transition_result:
                return transition_result
        
        # Prioritas 1: Deteksi REKOMENDASI
        if self._is_recommendation_request(input_lower):
            logger.debug("✅ Detected as REKOMENDASI")
            return "REKOMENDASI", input_norm, []
        
        
        # Prioritas 2: Deteksi MEMBER_GROUP (nama member + grup) - cek dulu sebelum single member
        member_group_result = self._detect_member_group(input_norm)
        if member_group_result:
            return member_group_result
        
        # Prioritas 3: Quick check untuk K-pop names yang ada di database
        if input_lower in self.priority_kpop_names:
            logger.debug(f"🎯 Found '{input_lower}' in priority K-pop names")
            # Cek GROUP dulu, baru MEMBER (grup prioritas lebih tinggi)
            result = self._check_exact_groups(input_lower)
            if result:
                logger.debug(f"✅ Exact group match: {result}")
                return result
            result = self._check_exact_members(input_lower)
            if result:
                logger.debug(f"✅ Exact member match: {result}")
                return result
        
        # Prioritas 4: Deteksi OBROLAN (casual conversation) - hanya jika bukan K-pop name
        if input_lower not in self.priority_kpop_names and self._is_casual_conversation(input_lower):
            logger.debug("✅ Detected as OBROLAN (casual conversation)")
            return "OBROLAN", input_norm, []
        
        # Length filter dengan exception untuk nama K-pop valid
        if len(input_norm) <= 3 and input_lower not in self.short_name_exceptions:
            return "OBROLAN", input_norm, []
        
        # Strategy 1: Alias detection
        result = self._check_aliases(input_lower)
        if result:
            return result
        
        # Strategy 2: Exact group match
        result = self._check_exact_groups(input_lower)
        if result:
            return result
        
        # Strategy 3: Exact member match
        result = self._check_exact_members(input_lower)
        if result:
            return result
        
        # Strategy 4: AI context detection untuk mixed queries (prioritas tinggi)
        if self._has_kpop_context(user_input):
            context_result = self._extract_kpop_from_context(user_input)
            if context_result[0] != "NON-KPOP":
                return context_result
        
        # Strategy 5: Fuzzy matching (fallback)
        result = self._fuzzy_match(input_norm)
        if result:
            return result
        
        # Default: OBROLAN untuk input yang tidak terdeteksi
        return "OBROLAN", input_norm, []
    
    def _detect_context_transition(self, input_lower, conversation_context):
        """Detect smooth transitions between categories based on conversation context"""
        
        # Transition patterns untuk OBROLAN → KPOP
        kpop_transition_patterns = [
            # Direct mention dengan context
            r'(iya|ya|betul|benar).*(blackpink|twice|bts|newjeans|ive|aespa)',
            r'(gimana|bagaimana).*(tentang|soal|dengan).*(blackpink|twice|bts)',
            r'(kalau|kalo).*(blackpink|twice|bts|newjeans)',
            r'(suka|demen|seneng).*(blackpink|twice|bts|newjeans)',
            
            # Follow-up questions
            r'(siapa|apa).*(member|anggota|personil)',
            r'(kapan|when).*(debut|mulai)',
            r'(lagu|song).*(favorit|bagus|hits)',
            
            # Comparison patterns
            r'(lebih|more).*(bagus|baik|keren|suka)',
            r'(atau|or|vs)',
            r'(dibanding|compared|versus)'
        ]
        
        # Transition patterns untuk KPOP → REKOMENDASI  
        recommendation_transition_patterns = [
            r'(ada|punya).*(rekomendasi|saran|suggest)',
            r'(yang lain|lainnya|other)',
            r'(mirip|similar|seperti|kayak)',
            r'(genre|style|tipe).*(sama|similar)',
            r'(selain|besides|except)',
            r'(recommend|rekomen|saranin)'
        ]
        
        # Check for K-pop names in context
        for pattern in kpop_transition_patterns:
            if re.search(pattern, input_lower):
                # Extract K-pop name from input
                extracted_name = self._extract_kpop_from_transition(input_lower)
                if extracted_name:
                    return extracted_name
        
        # Check for recommendation transition
        for pattern in recommendation_transition_patterns:
            if re.search(pattern, input_lower):
                return "REKOMENDASI", input_lower, []
        
        # Context-based K-pop detection
        if self._has_kpop_context_transition(input_lower, conversation_context):
            context_result = self._extract_kpop_from_context(input_lower, conversation_context)
            if context_result[0] != "NON-KPOP":
                return context_result
        
        return None
    
    def _extract_kpop_from_transition(self, input_lower):
        """Extract K-pop name from transition patterns with priority: GROUP > MEMBER"""
        
        # Strategy 1: Exact group matches - prioritize longer matches
        best_group_match = None
        best_group_length = 0
        
        for group_key, group_data in self.group_names.items():
            if group_key in input_lower and len(group_key) > best_group_length:
                best_group_match = ("GROUP", group_data[0][0], [])
                best_group_length = len(group_key)
        
        if best_group_match:
            return best_group_match
        
        # Strategy 2: Exact member matches - prioritize longer matches
        best_member_match = None
        best_member_length = 0
        
        for member_key, member_data in self.member_names.items():
            if member_key in input_lower and len(member_key) > best_member_length:
                best_member_match = ("MEMBER", member_data[0][0], [])
                best_member_length = len(member_key)
        
        if best_member_match:
            return best_member_match
        
        # Strategy 3: Fuzzy matching - Groups first
        words = input_lower.split()
        for word in words:
            if len(word) > 2:  # Skip very short words
                # Check groups with fuzzy matching
                for group_key, group_data in self.group_names.items():
                    if fuzz.ratio(word, group_key) >= 85:  # Higher threshold for better accuracy
                        return "GROUP", group_data[0][0], []
        
        # Strategy 4: Fuzzy matching - Members second
        for word in words:
            if len(word) > 2:
                # Check members with fuzzy matching
                for member_key, member_data in self.member_names.items():
                    if fuzz.ratio(word, member_key) >= 85:
                        return "MEMBER", member_data[0][0], []
        
        return None
    
    def _has_kpop_context_transition(self, input_lower, conversation_context):
        """Check if input has K-pop context for smooth transition"""
        if not conversation_context:
            return False
            
        # Context indicators for pronoun references
        pronoun_indicators = [
            'mereka', 'dia', 'itu', 'tersebut', 'yang tadi', 'sebelumnya',
            'grup itu', 'member itu', 'lagu itu', 'album itu'
        ]
        
        # Question indicators that suggest K-pop context
        question_indicators = [
            'debut kapan', 'kapan debut', 'mulai kapan', 'kapan mulai',
            'member siapa', 'siapa member', 'anggota siapa', 'siapa anggota',
            'lagu apa', 'apa lagu', 'album apa', 'apa album',
            'mereka debut', 'debut mereka'
        ]
        
        # Check if recent context mentioned K-pop
        recent_context = conversation_context.lower()
        has_kpop_in_context = any(name in recent_context for name in self.priority_kpop_names)
        
        # Also check group names directly in context
        if not has_kpop_in_context:
            has_kpop_in_context = any(group_key in recent_context for group_key in self.group_names.keys())
        
        # Also check member names in context
        if not has_kpop_in_context:
            has_kpop_in_context = any(member_key in recent_context for member_key in self.member_names.keys())
        
        # Check for pronoun references
        has_pronoun_reference = any(indicator in input_lower for indicator in pronoun_indicators)
        
        # Check for K-pop related questions
        has_kpop_question = any(indicator in input_lower for indicator in question_indicators)
        
        return has_kpop_in_context and (has_pronoun_reference or has_kpop_question)
    
    def _extract_kpop_from_context(self, input_lower, conversation_context=None):
        """Extract K-pop information from context when pronoun references are used"""
        # For context-based queries with pronouns, we need to maintain the context
        # but classify it appropriately based on the question type
        
        # Check if it's asking about group information (debut, members, etc.)
        group_question_patterns = [
            'debut kapan', 'kapan debut', 'mulai kapan', 'kapan mulai',
            'member siapa', 'siapa member', 'anggota siapa', 'siapa anggota',
            'berapa member', 'jumlah member', 'ada berapa',
            'mereka debut', 'debut mereka'
        ]
        
        # Check if it's asking about member information
        member_question_patterns = [
            'dia main drama', 'main drama', 'acting', 'akting',
            'umur berapa', 'berapa umur', 'lahir kapan', 'kapan lahir'
        ]
        
        # Determine the type based on question pattern
        for pattern in group_question_patterns:
            if pattern in input_lower:
                # This is a group-related question, return GROUP category
                # The actual group name will be handled by the AI with context
                return "GROUP", input_lower, []
        
        for pattern in member_question_patterns:
            if pattern in input_lower:
                # This is a member-related question, return MEMBER category
                return "MEMBER", input_lower, []
        
        # Default to OBROLAN for other context-based queries
        return "OBROLAN", input_lower, []
    
    def _is_recommendation_request(self, input_lower):
        """Deteksi request rekomendasi"""
        recommendation_keywords = [
            'rekomendasikan', 'rekomendasi', 'sarankan', 'saran', 'suggest',
            'recommend', 'kasih tau', 'kasih tahu', 'beri tau', 'beri tahu',
            'minta saran', 'minta rekomendasi', 'tolong kasih', 'tolong beri',
            'rekomen', 'rekomen lagu', 'lagu bagus', 'lagu baru', 'musik bagus',
            'musik baru', 'apa lagu', 'lagu apa', 'musik apa', 'apa musik'
        ]
        
        return any(keyword in input_lower for keyword in recommendation_keywords)
    
    def _is_casual_conversation(self, input_lower):
        """Deteksi obrolan casual"""
        # Stopwords check
        if input_lower in STOPWORDS:
            return True
        
        # Greeting patterns
        greeting_patterns = [
            r'^(hai|halo|hi|hello|hey|yo)',
            r'(apa kabar|gimana kabar|how are you)',
            r'(selamat pagi|selamat siang|selamat sore|selamat malam)',
            r'(good morning|good afternoon|good evening|good night)'
        ]
        
        # Weather/daily patterns
        daily_patterns = [
            r'(hari ini|kemarin|besok|tadi|nanti)',
            r'(hujan|panas|dingin|mendung|cerah)',
            r'(capek|lelah|ngantuk|lapar|kenyang)',
            r'(lagi ngapain|sedang apa|gimana|bagaimana|kenapa)',
            r'(saya baik|aku baik|baik-baik saja|baik saja|alhamdulillah baik)',
            r'(terima kasih|makasih|thanks|thank you)',
            r'(kuku kakek|kaku kaku|tongue twister|pantun|puisi)',
            r'(lagu baru|musik baru|karena lagu)',
            r'(ingin merokok|mau merokok|pengen merokok|smoking)',
            r'(aku ingin|aku mau|aku pengen|saya ingin|saya mau)'
        ]
        
        # Question patterns
        question_patterns = [
            r'(siapa namamu|nama kamu|kamu siapa)',
            r'(umur berapa|berapa umur)',
            r'(pakai bahasa|gunakan bahasa|berbahasa|bahasa natural)',
            r'(natural saja|santai saja|biasa saja|casual saja)',
            r'\?$'  # Questions ending with ?
        ]
        
        all_patterns = greeting_patterns + daily_patterns + question_patterns
        
        for pattern in all_patterns:
            if re.search(pattern, input_lower):
                return True
        
        return False
    
    def _detect_member_group(self, input_norm):
        """Deteksi kombinasi member + group (contoh: Jisoo Blackpink, Hina QWER)"""
        input_lower = input_norm.lower()
        words = input_norm.split()
        if len(words) < 2:
            return None
        
        from logger import logger
        logger.debug(f"🔍 _detect_member_group: Processing '{input_norm}' -> words: {words}")
        
        # Coba semua kombinasi kata untuk mencari member + group
        for i in range(len(words)):
            # Coba kombinasi 1 kata member + 1 kata group
            if i < len(words) - 1:
                member_part = ' '.join(words[:i+1])
                group_part = ' '.join(words[i+1:])
                
                logger.debug(f"🔍 Trying: member='{member_part}' + group='{group_part}'")
                
                # Cek apakah group_part adalah nama grup yang valid
                group_matches = []
                for group_key, group_data in self.group_names.items():
                    if group_part.lower() == group_key.lower():
                        group_matches.append((group_data[0][0], group_data[0][1]))  # (group_name, idx)
                        logger.debug(f"✅ Found group match: {group_data[0][0]}")
                
                # Jika group_part adalah grup yang valid, cari member-nya
                if group_matches:
                    group_name, group_idx = group_matches[0]  # Ambil yang pertama
                    
                    # Cari member dengan nama yang cocok DAN bagian dari grup ini
                    valid_member_found = False
                    for member_key, member_data in self.member_names.items():
                        if member_part.lower() == member_key.lower():
                            logger.debug(f"🔍 Found member key match: {member_key}")
                            for member_name, idx in member_data:
                                member_row = self.kpop_df.iloc[idx]
                                member_group = str(member_row.get('Group', '')).strip()
                                
                                logger.debug(f"🔍 Checking member: {member_name} from {member_group} vs target group: {group_name}")
                                
                                # Cek apakah member ini bagian dari grup yang dimaksud
                                if member_group.lower() == group_name.lower():
                                    logger.debug(f"✅ PERFECT MATCH: {member_name} from {group_name}")
                                    return "MEMBER_GROUP", f"{member_name} from {group_name}", []
                    
                    # PENTING: Jika tidak ditemukan member yang valid dari grup tersebut, 
                    # JANGAN kembalikan fallback - lanjutkan ke kombinasi lain
                    logger.debug(f"❌ No valid member found for {member_part} in group {group_name}")
        
        # Fallback: Jika tidak ditemukan kombinasi member + group yang valid
        # Cek apakah ada member dengan nama yang cocok (tanpa grup spesifik)
        for word in words:
            word_lower = word.lower()
            if word_lower in self.member_names:
                member_data = self.member_names[word_lower]
                if len(member_data) == 1:
                    # Hanya satu member dengan nama ini
                    member_name, idx = member_data[0]
                    logger.debug(f"✅ Single member fallback: {member_name}")
                    return "MEMBER", member_name, []
                else:
                    # Multiple members dengan nama yang sama
                    multiple_matches = []
                    for member_name, idx in member_data:
                        member_row = self.kpop_df.iloc[idx]
                        member_group = str(member_row.get('Group', '')).strip()
                        multiple_matches.append((f"{member_name} ({member_group})", "MEMBER"))
                    logger.debug(f"✅ Multiple member matches: {multiple_matches}")
                    return "MULTIPLE", word_lower, multiple_matches
        
        # Cek apakah ada grup dengan nama yang cocok
        for word in words:
            word_lower = word.lower()
            if word_lower in self.group_names:
                group_data = self.group_names[word_lower]
                group_name = group_data[0][0]
                logger.debug(f"✅ Group fallback: {group_name}")
                return "GROUP", group_name, []
        
        logger.debug("❌ No matches found in _detect_member_group")
        return None
    
    def _check_aliases(self, input_lower):
        """Check alias matches"""
        if input_lower in self.aliases:
            matches = self.aliases[input_lower]
            if len(matches) == 1:
                name, idx, category = matches[0]
                return category, name, []
            else:
                # Multiple aliases
                return "MULTIPLE", input_lower, [(name, category) for name, idx, category in matches]
        return None

    def _check_exact_groups(self, input_lower):
        """Check exact group matches"""
        if input_lower in self.group_names:
            matches = self.group_names[input_lower]

            # Deduplikasi berdasarkan nama grup yang sama
            unique_groups = {}
            for group_name, idx in matches:
                if group_name not in unique_groups:
                    unique_groups[group_name] = (group_name, idx)

            unique_matches = list(unique_groups.values())

            if len(unique_matches) == 1:
                group_name, idx = unique_matches[0]
                return "GROUP", group_name, []
            else:
                # Multiple groups dengan nama berbeda
                return "MULTIPLE", input_lower, [(name, "GROUP") for name, idx in unique_matches]
        return None

    def _fuzzy_match(self, input_norm):
        """Fuzzy matching dengan confidence scoring - skip blacklisted names dan prevent substring false positives"""
        best_score = 0
        best_match = None
        best_category = None

        input_lower = input_norm.lower()

        # Skip jika input dalam blacklist
        if input_lower in self.member_name_blacklist:
            return None
        
        # TODO: Implement fuzzy matching logic
        return None
    
    def _check_aliases(self, input_lower):
        """Check alias matches"""
        if input_lower in self.aliases:
            matches = self.aliases[input_lower]
            if len(matches) == 1:
                name, idx, category = matches[0]
                return category, name, []
            else:
                # Multiple aliases
                return "MULTIPLE", input_lower, [(name, category) for name, idx, category in matches]
        return None
    
    def _check_exact_groups(self, input_lower):
        """Check exact group matches"""
        if input_lower in self.group_names:
            matches = self.group_names[input_lower]
            
            # Deduplikasi berdasarkan nama grup yang sama
            unique_groups = {}
            for group_name, idx in matches:
                if group_name not in unique_groups:
                    unique_groups[group_name] = (group_name, idx)
            
            unique_matches = list(unique_groups.values())
            
            if len(unique_matches) == 1:
                group_name, idx = unique_matches[0]
                return "GROUP", group_name, []
            else:
                # Multiple groups dengan nama berbeda
                return "MULTIPLE", input_lower, [(name, "GROUP") for name, idx in unique_matches]
        return None
        
    def _check_exact_members(self, input_lower):
        """Check exact member matches"""
        if input_lower in self.member_names:
            matches = self.member_names[input_lower]
            if len(matches) == 1:
                member_name, idx = matches[0]
                return "MEMBER", member_name, []
            else:
                # Multiple members dengan nama sama (contoh: Siyeon dari Dreamcatcher vs QWER)
                multiple_matches = []
                for member_name, idx in matches:
                    row = self.kpop_df.iloc[idx]
                    group = str(row.get("Group", "")).strip()
                    multiple_matches.append((f"{member_name} ({group})", "MEMBER"))
                return "MULTIPLE", input_lower, multiple_matches
        return None

    def _fuzzy_match(self, input_norm):
        """Fuzzy matching dengan confidence scoring - skip blacklisted names dan prevent substring false positives"""
        best_score = 0
        best_match = None
        best_category = None

        input_lower = input_norm.lower()
        
        # Skip jika input dalam blacklist
        if input_lower in self.member_name_blacklist:
            return None
        
        # Skip fuzzy matching untuk casual conversation patterns
        casual_patterns = [
            'enak', 'mie', 'goreng', 'rebus', 'atau', 'apa', 'bagaimana', 'kenapa', 'dimana', 'kapan',
            'makanan', 'minuman', 'cuaca', 'hari', 'hujan', 'panas', 'dingin', 'baik', 'buruk'
        ]
        
        # Jika input mengandung kata casual, skip fuzzy matching
        for pattern in casual_patterns:
            if pattern in input_lower:
                return None
        
        for idx, row in self.kpop_df.iterrows():
            # Group fuzzy matching
            group_name = str(row.get("Group", "")).strip()
            if group_name:
                # Use ratio instead of partial_ratio untuk exact matching yang lebih ketat
                score = fuzz.ratio(input_lower, group_name.lower())
                if score > best_score and score >= self.threshold:
                    best_match = group_name
                    best_category = "GROUP"
                    best_score = score
            
            # Member fuzzy matching - skip blacklisted names dan gunakan matching yang lebih ketat
            for col in ["Stage Name", "Korean Stage Name", "Full Name"]:
                member_name = str(row.get(col, "")).strip()
                if member_name and member_name.lower() not in self.member_name_blacklist:
                    # Gunakan ratio untuk exact matching, bukan partial_ratio
                    score = fuzz.ratio(input_lower, member_name.lower())
                    # Tambahan check: jika member name sangat pendek (<=3 char), butuh exact match
                    if len(member_name) <= 3 and score < 100:
                        continue
                    if score > best_score and score >= self.threshold:
                        best_match = member_name
                        best_category = "MEMBER"
                        best_score = score
        
        if best_match:
            return best_category, best_match, []
        return None
    
    def _has_kpop_context(self, user_input):
        """Detect if text has K-pop context mixed with casual words"""
        kpop_indicators = [
            'info tentang', 'ceritain tentang', 'siapa itu', 'member', 'grup', 'idol',
            'debut', 'comeback', 'album', 'mv', 'choreography', 'fandom',
            'aku ingin info', 'kasih info', 'beri info', 'minta info', 'tolong info',
            'pengen tau', 'pengen tahu', 'ingin tau', 'ingin tahu', 'mau tau', 'mau tahu',
            'cerita dong', 'ceritain dong', 'kasih tau dong', 'beri tau dong',
            'berikan info', 'berikan informasi', 'kasih informasi', 'beri informasi',
            'mau info', 'aku mau info', 'pengen info', 'butuh info'
        ]
        
        input_lower = user_input.lower()
        return any(indicator in input_lower for indicator in kpop_indicators)
    
