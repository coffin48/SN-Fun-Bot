"""
Test script untuk debug 'Hina' detection issue
"""
import pandas as pd
from patch.smart_detector import SmartKPopDetector

# Load database
KPOP_CSV_ID = "15SjsUKHLaYQ5wZHR013Lb38M4uY-tiVE"
KPOP_CSV_URL = f"https://drive.google.com/uc?export=download&id={KPOP_CSV_ID}"

try:
    kpop_df = pd.read_csv(KPOP_CSV_URL)
    print(f"Database loaded: {len(kpop_df)} entries")
    
    # Initialize detector
    detector = SmartKPopDetector(kpop_df)
    
    # Check if Hina exists in database
    hina_rows = kpop_df[kpop_df['Stage Name'].str.lower() == 'hina']
    print(f"\n'Hina' entries in database: {len(hina_rows)}")
    if len(hina_rows) > 0:
        for idx, row in hina_rows.iterrows():
            print(f"   - {row['Stage Name']} from {row['Group']}")
    
    # Check priority names
    print(f"\n'hina' in priority_kpop_names: {'hina' in detector.priority_kpop_names}")
    print(f"'hina' in member_names: {'hina' in detector.member_names}")
    
    # Test detection
    test_cases = ['Hina', 'hina', 'HINA', 'Hina QWER']
    
    for test in test_cases:
        result = detector.detect(test)
        print(f"\nTest: '{test}' -> {result}")

except Exception as e:
    print(f"Error: {e}")
