"""
Unified data acquisition orchestrator
Manages MT5, FRED, and News data collection
"""
from acquisition.mt5_collector import collect_mt5_data
from acquisition.fred_collector import collect_fred_data
from acquisition.news_collector import collect_news_data


def run_full_acquisition():
    """Run all data acquisition tasks"""
    
    print("=" * 60)
    print("STARTING FULL DATA ACQUISITION")
    print("=" * 60)
    
    # 1. Collect MT5 price data
    print("\n[1/3] Collecting MT5 Price Data...")
    try:
        collect_mt5_data()
        print("✅ MT5 data collection completed")
    except Exception as e:
        print(f"❌ MT5 collection failed: {e}")
    
    # 2. Collect FRED macro data
    print("\n[2/3] Collecting FRED Macro Data...")
    try:
        collect_fred_data()
        print("✅ FRED data collection completed")
    except Exception as e:
        print(f"❌ FRED collection failed: {e}")
    
    # 3. Collect news data
    print("\n[3/3] Collecting News Data...")
    try:
        collect_news_data()
        print("✅ News data collection completed")
    except Exception as e:
        print(f"❌ News collection failed: {e}")
    
    print("\n" + "=" * 60)
    print("DATA ACQUISITION COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    run_full_acquisition()
