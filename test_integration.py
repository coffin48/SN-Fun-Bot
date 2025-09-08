"""
Test Integration - Testing semua kategori SmartKPopDetector
"""
import pandas as pd
from patch.smart_detector import SmartKPopDetector

def test_categories():
    """Test semua kategori detection"""
    # Load database lokal untuk testing
    try:
        df = pd.read_csv(r"G:\Windsurf\Sn Fun Bot\Database\DATABASE_KPOP (1).csv")
        detector = SmartKPopDetector(df)
        print(f"✅ Database loaded: {len(df)} rows")
    except Exception as e:
        print(f"❌ Database error: {e}")
        return
    
    # Test cases untuk setiap kategori
    test_cases = [
        # K-pop Categories
        ("Jisoo", "MEMBER"),
        ("BTS", "GROUP"), 
        ("TXT", "GROUP"),
        ("Secret Number", "GROUP"),
        ("Jisoo Blackpink", "MEMBER_GROUP"),
        ("Soodam Secret Number", "MEMBER_GROUP"),
        
        # Non K-pop Categories  
        ("hai", "OBROLAN"),
        ("halo", "OBROLAN"),
        ("apa kabar?", "OBROLAN"),
        ("hujan nih", "OBROLAN"),
        ("siapa namamu?", "OBROLAN"),
        ("rekomendasikan aku lagu", "REKOMENDASI"),
        ("rekomendasikan aku resep", "REKOMENDASI"),
        ("kasih saran dong", "REKOMENDASI"),
        
        # Edge cases
        ("iu", "MEMBER"),  # Short name exception
        ("cl", "MEMBER"),  # Short name exception
        ("a", "OBROLAN"),  # Too short
    ]
    
    print("\n🧪 Testing Categories:")
    print("=" * 60)
    
    for input_text, expected_category in test_cases:
        category, detected_name, multiple_matches = detector.detect(input_text)
        
        status = "✅" if category == expected_category else "❌"
        print(f"{status} '{input_text}' → {category} (expected: {expected_category})")
        
        if detected_name and category in ["MEMBER", "GROUP", "MEMBER_GROUP"]:
            print(f"    Target: {detected_name}")
        
        if multiple_matches:
            print(f"    Multiple: {len(multiple_matches)} matches")
    
    print("\n" + "=" * 60)
    print("🎯 Integration test completed!")

if __name__ == "__main__":
    test_categories()
