#!/usr/bin/env python3
"""
Test script untuk context detection enhancement
Testing conversational queries seperti "aku ingin info tentang BTS donk"
"""

import pandas as pd
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from patch.smart_detector import SmartKPopDetector

def test_context_detection():
    """Test enhanced context detection"""
    
    # Load database
    try:
        kpop_df = pd.read_csv("Database/DATABASE_KPOP (1).csv")
        print(f"Database loaded: {len(kpop_df)} entries")
    except Exception as e:
        print(f"Error loading database: {e}")
        return
    
    # Initialize detector
    detector = SmartKPopDetector(kpop_df)
    
    # Test cases untuk conversational queries
    test_cases = [
        "aku ingin info tentang BTS donk",
        "kasih info tentang BLACKPINK dong",
        "mau tau tentang NewJeans nih",
        "pengen tahu info IU",
        "ceritain tentang TWICE dong",
        "beri info tentang Jisoo",
        "tolong info tentang ITZY ya",
        "aku pengen tau tentang Hina QWER",
        "kasih tau dong tentang LIGHTSUM",
        "minta info tentang RM BTS",
        # Non K-pop cases
        "aku ingin info tentang cuaca hari ini",
        "kasih info tentang resep masakan dong",
        "mau tau tentang berita politik",
        "hai apa kabar",
        "gimana hari ini"
    ]
    
    print("\n=== TESTING ENHANCED CONTEXT DETECTION ===\n")
    
    for i, test_input in enumerate(test_cases, 1):
        print(f"{i:2d}. Input: '{test_input}'")
        
        try:
            category, detected_name, multiple_matches = detector.detect(test_input)
            
            if category in ["MEMBER", "GROUP", "MEMBER_GROUP"]:
                print(f"    Result: {category} - '{detected_name}' ✅")
            elif category == "OBROLAN":
                print(f"    Result: {category} ❌")
            else:
                print(f"    Result: {category} - '{detected_name}'")
                
            if multiple_matches:
                print(f"    Multiple: {len(multiple_matches)} matches")
                
        except Exception as e:
            print(f"    ERROR: {e}")
        
        print()

if __name__ == "__main__":
    test_context_detection()
