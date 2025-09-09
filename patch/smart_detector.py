# patch/smart_detector.py
from rapidfuzz import fuzz
from patch.stopwordlist import STOPWORDS
import re

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
            'woah': 'WOOAH'
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
    
    def detect(self, user_input):
        """
        Deteksi K-pop dengan kategorisasi spesifik
        Returns: (category, detected_name, multiple_matches)
        Categories: MEMBER, GROUP, MEMBER_GROUP, OBROLAN, REKOMENDASI, MULTIPLE
        """
        input_norm = user_input.strip()
        input_lower = input_norm.lower()
        
        # Debug logging
        import logging
        logging.debug(f"🔍 Detecting: '{input_norm}' (lower: '{input_lower}')")
        logging.debug(f"📊 Priority names contains '{input_lower}': {input_lower in self.priority_kpop_names}")
        
        # Prioritas 1: Deteksi REKOMENDASI
        if self._is_recommendation_request(input_lower):
            logging.debug("✅ Detected as REKOMENDASI")
            return "REKOMENDASI", input_norm, []
        
        
        # Prioritas 2: Deteksi MEMBER_GROUP (nama member + grup) - cek dulu sebelum single member
        member_group_result = self._detect_member_group(input_norm)
        if member_group_result:
            return member_group_result
        
        # Prioritas 3: Quick check untuk K-pop names yang ada di database
        if input_lower in self.priority_kpop_names:
            logging.debug(f"🎯 Found '{input_lower}' in priority K-pop names")
            # Cek GROUP dulu, baru MEMBER (grup prioritas lebih tinggi)
            result = self._check_exact_groups(input_lower)
            if result:
                logging.debug(f"✅ Exact group match: {result}")
                return result
            result = self._check_exact_members(input_lower)
            if result:
                logging.debug(f"✅ Exact member match: {result}")
                return result
        
        # Prioritas 4: Deteksi OBROLAN (casual conversation) - hanya jika bukan K-pop name
        if input_lower not in self.priority_kpop_names and self._is_casual_conversation(input_lower):
            logging.debug("✅ Detected as OBROLAN (casual conversation)")
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
    
    def _is_recommendation_request(self, input_lower):
        """Deteksi request rekomendasi"""
        recommendation_keywords = [
            'rekomendasikan', 'rekomendasi', 'sarankan', 'saran', 'suggest',
            'recommend', 'kasih tau', 'kasih tahu', 'beri tau', 'beri tahu',
            'minta saran', 'minta rekomendasi', 'tolong kasih', 'tolong beri'
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
        words = input_norm.split()
        if len(words) < 2:
            return None
        
        detected_members = []
        detected_groups = []
        
        # Cek setiap kata untuk member dan group
        for word in words:
            word_lower = word.lower()
            
            # Cek apakah kata ini adalah member
            if word_lower in self.member_names:
                for member_name, idx in self.member_names[word_lower]:
                    detected_members.append((member_name, idx))
            
            # Cek apakah kata ini adalah group
            if word_lower in self.group_names:
                for group_name, idx in self.group_names[word_lower]:
                    detected_groups.append((group_name, idx))
        
        # Jika ada member dan group dalam input yang sama
        if detected_members and detected_groups:
            # Cari member yang benar-benar dari group yang disebutkan
            for member_name, member_idx in detected_members:
                member_row = self.kpop_df.iloc[member_idx]
                member_group = str(member_row.get('Group', '')).strip()
                
                for group_name, group_idx in detected_groups:
                    if member_group.lower() == group_name.lower():
                        # Member dan group cocok - return format untuk scraping
                        combined_name = f"{member_name} from {group_name}"
                        import logging
                        logging.debug(f"🎯 MEMBER_GROUP detected: {combined_name}")
                        return "MEMBER_GROUP", combined_name, []
            
            # Jika tidak ada yang cocok, ambil yang pertama
            member_name = detected_members[0][0]
            group_name = detected_groups[0][0]
            combined_name = f"{member_name} from {group_name}"
            import logging
            logging.debug(f"🎯 MEMBER_GROUP detected (fallback): {combined_name}")
            return "MEMBER_GROUP", combined_name, []
        
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
    
    def _extract_kpop_from_context(self, user_input):
        """Extract K-pop name from mixed context"""
        words = user_input.split()
        
        # Filter kata-kata umum yang bukan K-pop names
        common_words = {'aku', 'saya', 'kamu', 'dia', 'info', 'tentang', 'soal', 'dari', 'untuk', 'dengan', 'yang', 'ini', 'itu', 'dan', 'atau', 'beri', 'kasih', 'minta', 'ingin', 'mau', 'pengen', 'baik', 'saja', 'juga', 'lagi', 'apa', 'dong', 'nih'}
        
        # Cek setiap kata untuk K-pop names - prioritas grup dulu
        for word in words:
            word_clean = re.sub(r'[^\w]', '', word).strip()
            word_lower = word_clean.lower()
            
            # Skip kata-kata umum
            if word_lower in common_words or len(word_clean) <= 1:
                continue
                
            # Try exact match grup dulu (prioritas tinggi)
            result = self._check_exact_groups(word_lower)
            if result:
                return result
        
        # Kemudian cek member jika tidak ada grup yang cocok
        for word in words:
            word_clean = re.sub(r'[^\w]', '', word).strip()
            word_lower = word_clean.lower()
            
            # Skip kata-kata umum
            if word_lower in common_words or len(word_clean) <= 1:
                continue
                
            result = self._check_exact_members(word_lower)
            if result:
                return result
        
        # Jika tidak ada exact match, coba fuzzy matching - prioritas grup dulu
        for word in words:
            word_clean = re.sub(r'[^\w]', '', word).strip()
            word_lower = word_clean.lower()
            
            # Skip kata-kata umum dan pendek
            if word_lower in common_words or len(word_clean) <= 2:
                continue
                
            # Fuzzy match untuk groups dulu
            for _, row in self.kpop_df.iterrows():
                group_name = str(row.get("Group", "")).strip()
                if group_name:
                    score = fuzz.ratio(word_lower, group_name.lower())
                    if score >= 85:  # High threshold untuk context extraction
                        return "GROUP", group_name, []
        
        # Kemudian fuzzy match untuk members
        for word in words:
            word_clean = re.sub(r'[^\w]', '', word).strip()
            word_lower = word_clean.lower()
            
            # Skip kata-kata umum, pendek, dan blacklisted
            if word_lower in common_words or len(word_clean) <= 2 or word_lower in self.member_name_blacklist:
                continue
                
            for _, row in self.kpop_df.iterrows():
                for col in ["Stage Name", "Korean Stage Name", "Full Name"]:
                    member_name = str(row.get(col, "")).strip()
                    if member_name and member_name.lower() not in self.member_name_blacklist:
                        score = fuzz.ratio(word_lower, member_name.lower())
                        if score >= 85:  # High threshold untuk context extraction
                            return "MEMBER", member_name, []
        
        return "NON-KPOP", None, []
