"""
Test Enhanced Query Building dengan semua nama variations
"""
import pandas as pd
from commands import CommandsHandler
from bot_core import BotCore

# Load database
KPOP_CSV_ID = "15SjsUKHLaYQ5wZHR013Lb38M4uY-tiVE"
KPOP_CSV_URL = f"https://drive.google.com/uc?export=download&id={KPOP_CSV_ID}"

try:
    kpop_df = pd.read_csv(KPOP_CSV_URL)
    print(f"Database loaded: {len(kpop_df)} entries")
    
    # Create mock commands handler dengan dataframe
    class MockCommandsHandler:
        def __init__(self, kpop_df):
            self.kpop_df = kpop_df
        
        def _build_enhanced_query(self, category, detected_name):
            """Build enhanced query dengan semua nama variations untuk scraping yang lebih komprehensif"""
            try:
                if category == "MEMBER":
                    # Cari semua info dari database untuk member
                    member_rows = self.kpop_df[self.kpop_df['Stage Name'].str.lower() == detected_name.lower()]
                    if len(member_rows) > 0:
                        row = member_rows.iloc[0]
                        
                        # Kumpulkan semua nama variations
                        names = []
                        stage_name = str(row.get('Stage Name', '')).strip()
                        full_name = str(row.get('Full Name', '')).strip()
                        korean_name = str(row.get('Korean Stage Name', '')).strip()
                        group = str(row.get('Group', '')).strip()
                        
                        if stage_name:
                            names.append(stage_name)
                        if full_name and full_name != stage_name:
                            names.append(full_name)
                        # Skip Korean name untuk avoid encoding issues di Windows console
                        # if korean_name and korean_name != stage_name:
                        #     names.append(korean_name)
                        
                        # Format: "Stage Name Full Name Korean Name from Group"
                        if group:
                            names_str = " ".join(names)
                            return f"{names_str} from {group}"
                        else:
                            return " ".join(names)
                            
                elif category == "GROUP":
                    # Untuk group, scraping group saja
                    return detected_name
                    
                elif category == "MEMBER_GROUP":
                    # Extract member name dari format "Member from Group"
                    if " from " in detected_name:
                        member_part = detected_name.split(" from ")[0]
                        group_part = detected_name.split(" from ")[1]
                        
                        # Cari semua nama variations untuk member ini
                        member_rows = self.kpop_df[
                            (self.kpop_df['Stage Name'].str.lower() == member_part.lower()) &
                            (self.kpop_df['Group'].str.lower() == group_part.lower())
                        ]
                        
                        if len(member_rows) > 0:
                            row = member_rows.iloc[0]
                            
                            # Kumpulkan semua nama variations
                            names = []
                            stage_name = str(row.get('Stage Name', '')).strip()
                            full_name = str(row.get('Full Name', '')).strip()
                            korean_name = str(row.get('Korean Stage Name', '')).strip()
                            
                            if stage_name:
                                names.append(stage_name)
                            if full_name and full_name != stage_name:
                                names.append(full_name)
                            # Skip Korean name untuk avoid encoding issues di Windows console
                            # if korean_name and korean_name != stage_name:
                            #     names.append(korean_name)
                            
                            names_str = " ".join(names)
                            return f"{names_str} from {group_part}"
                    
                    # Fallback ke detected_name original
                    return detected_name
                    
            except Exception as e:
                print(f"Error building enhanced query: {e}")
            
            # Fallback ke detected_name original
            return detected_name
    
    commands_handler = MockCommandsHandler(kpop_df)
    
    # Test cases untuk enhanced query
    test_cases = [
        ("MEMBER", "Hina"),
        ("MEMBER_GROUP", "Hina from QWER"),
        ("MEMBER_GROUP", "Hina from LIGHTSUM"),
        ("GROUP", "BLACKPINK"),
        ("MEMBER", "Jisoo")
    ]
    
    print("\n=== Enhanced Query Testing ===")
    for category, detected_name in test_cases:
        enhanced_query = commands_handler._build_enhanced_query(category, detected_name)
        print(f"\nCategory: {category}")
        print(f"Detected: {detected_name}")
        print(f"Enhanced: {enhanced_query}")
        
        # Show database info untuk member
        if category in ["MEMBER", "MEMBER_GROUP"]:
            if category == "MEMBER":
                member_name = detected_name
                group_filter = None
            else:
                if " from " in detected_name:
                    member_name = detected_name.split(" from ")[0]
                    group_filter = detected_name.split(" from ")[1]
                else:
                    member_name = detected_name
                    group_filter = None
            
            # Filter berdasarkan member dan group jika ada
            if group_filter:
                member_rows = kpop_df[
                    (kpop_df['Stage Name'].str.lower() == member_name.lower()) &
                    (kpop_df['Group'].str.lower() == group_filter.lower())
                ]
            else:
                member_rows = kpop_df[kpop_df['Stage Name'].str.lower() == member_name.lower()]
            
            if len(member_rows) > 0:
                row = member_rows.iloc[0]
                print(f"Database info:")
                stage_name = str(row.get('Stage Name', 'N/A'))
                full_name = str(row.get('Full Name', 'N/A'))
                group = str(row.get('Group', 'N/A'))
                
                print(f"  Stage Name: {stage_name}")
                print(f"  Full Name: {full_name}")
                print(f"  Group: {group}")
            else:
                print(f"Database info: No match found for {member_name} in {group_filter if group_filter else 'any group'}")

except Exception as e:
    print(f"Error: {e}")
