# patch/smart_detector.py
from rapidfuzz import fuzz
from patch.stopwordlist import STOPWORDS
import re

class SmartKPopDetector:
    def __init__(self, kpop_df, threshold=85):
        self.threshold = threshold
        self.kpop_df = kpop_df
        
        # Exception list untuk nama K-pop pendek yang valid
        self.short_name_exceptions = ['iu', 'cl', 'gd', 'top', 'key', 'joy', 'kai', 'jin', 'rm', 'jb']
        
        # Pre-build indexes untuk performa
        self._build_indexes()
    
    def _build_indexes(self):
        """Build indexes untuk exact matching dan alias detection"""
        self.member_names = {}  # name -> [(original_name, row_index)]
        self.group_names = {}   # name -> [(original_name, row_index)]
        self.aliases = {}       # alias -> [(original_name, row_index, type)]
        
        for idx, row in self.kpop_df.iterrows():
            # Group names
            group = str(row.get("Group", "")).strip()
            if group:
                group_lower = group.lower()
                if group_lower not in self.group_names:
                    self.group_names[group_lower] = []
                self.group_names[group_lower].append((group, idx))
            
            # Member names
            for col in ["Stage Name", "Korean Stage Name", "Full Name"]:
                name = str(row.get(col, "")).strip()
                if name:
                    name_lower = name.lower()
                    if name_lower not in self.member_names:
                        self.member_names[name_lower] = []
                    self.member_names[name_lower].append((name, idx))
            
            # Aliases (jika ada kolom alias)
            if "Aliases" in row and str(row["Aliases"]).strip():
                aliases = str(row["Aliases"]).split(",")
                for alias in aliases:
                    alias = alias.strip().lower()
                    if alias:
                        if alias not in self.aliases:
                            self.aliases[alias] = []
                        self.aliases[alias].append((name, idx, "MEMBER"))
    
    def detect(self, user_input):
        """
        Deteksi K-pop dengan kategorisasi spesifik
        Returns: (category, detected_name, multiple_matches)
        Categories: MEMBER, GROUP, MEMBER_GROUP, OBROLAN, REKOMENDASI, MULTIPLE
        """
        input_norm = user_input.strip()
        input_lower = input_norm.lower()
        
        # Prioritas 1: Deteksi REKOMENDASI
        if self._is_recommendation_request(input_lower):
            return "REKOMENDASI", input_norm, []
        
        # Prioritas 2: Deteksi OBROLAN (casual conversation)
        if self._is_casual_conversation(input_lower):
            return "OBROLAN", input_norm, []
        
        # Prioritas 3: Deteksi MEMBER_GROUP (nama member + grup)
        member_group_result = self._detect_member_group(input_norm)
        if member_group_result:
            return member_group_result
        
        # Length filter dengan exception untuk nama K-pop valid
        if len(input_norm) <= 2 and input_lower not in self.short_name_exceptions:
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
        
        # Strategy 4: Fuzzy matching
        result = self._fuzzy_match(input_norm)
        if result:
            return result
        
        # Strategy 5: AI context detection untuk mixed queries
        if self._has_kpop_context(user_input):
            return self._extract_kpop_from_context(user_input)
        
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
            r'(lagi ngapain|sedang apa|gimana|bagaimana|kenapa)'
        ]
        
        # Question patterns
        question_patterns = [
            r'(siapa namamu|nama kamu|kamu siapa)',
            r'(umur berapa|berapa umur)',
            r'\?$'  # Questions ending with ?
        ]
        
        all_patterns = greeting_patterns + daily_patterns + question_patterns
        
        for pattern in all_patterns:
            if re.search(pattern, input_lower):
                return True
        
        return False
    
    def _detect_member_group(self, input_norm):
        """Deteksi kombinasi member + group (contoh: Jisoo Blackpink)"""
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
            # Ambil member pertama dan group pertama
            member_name = detected_members[0][0]
            group_name = detected_groups[0][0]
            combined_name = f"{member_name} ({group_name})"
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
            if len(matches) == 1:
                group_name, idx = matches[0]
                return "GROUP", group_name, []
            else:
                # Multiple groups dengan nama sama
                return "MULTIPLE", input_lower, [(name, "GROUP") for name, idx in matches]
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
        """Fuzzy matching dengan confidence scoring"""
        best_score = 0
        best_match = None
        best_category = None
        
        input_lower = input_norm.lower()
        
        for idx, row in self.kpop_df.iterrows():
            # Group fuzzy matching
            group_name = str(row.get("Group", "")).strip()
            if group_name:
                score = fuzz.partial_ratio(input_lower, group_name.lower())
                if score > best_score and score >= self.threshold:
                    best_match = group_name
                    best_category = "GROUP"
                    best_score = score
            
            # Member fuzzy matching
            for col in ["Stage Name", "Korean Stage Name", "Full Name"]:
                member_name = str(row.get(col, "")).strip()
                if member_name:
                    score = fuzz.partial_ratio(input_lower, member_name.lower())
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
            'debut', 'comeback', 'album', 'mv', 'choreography', 'fandom'
        ]
        
        input_lower = user_input.lower()
        return any(indicator in input_lower for indicator in kpop_indicators)
    
    def _extract_kpop_from_context(self, user_input):
        """Extract K-pop name from mixed context"""
        words = user_input.split()
        
        for word in words:
            word_clean = re.sub(r'[^\w]', '', word).strip()
            if len(word_clean) > 2:
                # Try exact match pada word ini
                result = self._check_exact_groups(word_clean.lower())
                if result:
                    return result
                
                result = self._check_exact_members(word_clean.lower())
                if result:
                    return result
        
        return "NON-KPOP", None, []
