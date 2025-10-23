# test_live_small.py - Test with 5 real stocks

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_predictive_scanner import EnhancedPredictiveScanner
import config_secure as config


def test_live_small():
    """Test scanner with 5 real stocks"""
    
    print("\n🧪 Testing scanner with 5 real stocks...\n")
    
    scanner = EnhancedPredictiveScanner(
        config.ALPHA_VANTAGE_API_KEY,
        config.TELEGRAM_BOT_TOKEN,
        config.TELEGRAM_CHAT_ID
    )
    
    # Create tiny test watchlist
    import pandas as pd
    test_symbols = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'TSLA']
    test_df = pd.DataFrame({'Symbol': test_symbols})
    test_file = 'data/test_tiny_watchlist.csv'
    test_df.to_csv(test_file, index=False)
    
    scanner.load_watchlist(test_file)
    
    # Pre-cache
    scanner.precache_daily_indicators()
    
    # Run one predictive scan
    scanner.scan_predictive_enhanced(minutes_before_close=5)
    
    print("\n✅ Live test complete!\n")


if __name__ == "__main__":
    test_live_small()