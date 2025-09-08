"""
Test Scraping - Testing data fetcher functionality
"""
import asyncio
from data_fetcher import DataFetcher

async def test_scraping():
    """Test scraping functionality dengan contoh query"""
    fetcher = DataFetcher()
    
    test_queries = [
        "IU",
        "BTS", 
        "NewJeans",
        "Jisoo"
    ]
    
    print("🔍 Testing Scraping + CSE + NewsAPI Integration")
    print("=" * 60)
    
    for query in test_queries:
        print(f"\n📝 Testing query: '{query}'")
        try:
            info = await fetcher.fetch_kpop_info(query)
            
            if info.strip():
                print(f"✅ Data found: {len(info)} characters")
                print(f"📄 Preview: {info[:200]}...")
            else:
                print("❌ No data found")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 Scraping test completed!")

if __name__ == "__main__":
    asyncio.run(test_scraping())
