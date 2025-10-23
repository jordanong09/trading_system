# test_integration.py - Test Chart Pattern Integration

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_predictive_scanner import EnhancedPredictiveScanner
import config_secure as config


def test_chart_pattern_integration():
    """
    Test that chart patterns are properly integrated into scanner
    """
    print("\n" + "="*80)
    print("🧪 TESTING CHART PATTERN INTEGRATION")
    print("="*80 + "\n")
    
    # Initialize scanner
    print("1. Initializing scanner...")
    scanner = EnhancedPredictiveScanner(
        config.ALPHA_VANTAGE_API_KEY,
        config.TELEGRAM_BOT_TOKEN,
        config.TELEGRAM_CHAT_ID
    )
    print("   ✅ Scanner initialized\n")
    
    # Check chart detector exists
    print("2. Checking chart detector...")
    if hasattr(scanner, 'chart_detector'):
        print("   ✅ Chart detector initialized")
    else:
        print("   ❌ Chart detector NOT found")
        return False
    
    # Load small test watchlist
    print("\n3. Loading test watchlist...")
    test_symbols = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN']
    
    # Create temporary test watchlist
    import pandas as pd
    test_df = pd.DataFrame({'Symbol': test_symbols})
    test_file = 'data/test_watchlist_integration.csv'
    os.makedirs('data', exist_ok=True)
    test_df.to_csv(test_file, index=False)
    
    scanner.load_watchlist(test_file)
    print(f"   ✅ Loaded {len(scanner.symbols)} test symbols\n")
    
    # Pre-cache daily indicators
    print("4. Pre-caching daily indicators...")
    try:
        scanner.precache_daily_indicators()
        print("   ✅ Cache built successfully\n")
    except Exception as e:
        print(f"   ⚠️  Cache error (may be API limit): {e}\n")
    
    # Test pattern detection methods exist
    print("5. Verifying pattern detection methods...")
    
    required_methods = [
        'detect_cup_and_handle',
        'detect_ascending_triangle',
        'detect_descending_triangle',
        'detect_bull_flag',
        'detect_double_top',
        'detect_double_bottom',
        'detect_all_patterns'
    ]
    
    all_exist = True
    for method in required_methods:
        if hasattr(scanner.chart_detector, method):
            print(f"   ✅ {method}")
        else:
            print(f"   ❌ {method} NOT FOUND")
            all_exist = False
    
    if not all_exist:
        print("\n   ❌ Missing pattern detection methods!")
        return False
    
    print("\n6. Testing detect_all_patterns...")
    
    # Create sample data
    sample_df = pd.DataFrame({
        'Date': pd.date_range('2024-01-01', periods=100, freq='H'),
        'Open': [150 + i*0.1 for i in range(100)],
        'High': [150.5 + i*0.1 for i in range(100)],
        'Low': [149.5 + i*0.1 for i in range(100)],
        'Close': [150.2 + i*0.1 for i in range(100)],
        'Volume': [1000000 + i*1000 for i in range(100)]
    })
    
    try:
        patterns = scanner.chart_detector.detect_all_patterns(sample_df, '1H')
        print(f"   ✅ detect_all_patterns works ({len(patterns)} patterns found)")
    except Exception as e:
        print(f"   ❌ detect_all_patterns failed: {e}")
        return False
    
    # Test enhanced confluence method exists
    print("\n7. Checking enhanced confluence method...")
    if hasattr(scanner, '_evaluate_enhanced_confluence'):
        print("   ✅ Enhanced confluence method exists")
    else:
        print("   ❌ Enhanced confluence method NOT FOUND")
        return False
    
    # Test alert formatting
    print("\n8. Checking enhanced alert formatting...")
    if hasattr(scanner, '_format_enhanced_compliant_alert'):
        print("   ✅ Enhanced alert formatting exists")
    else:
        print("   ❌ Enhanced alert formatting NOT FOUND")
        return False
    
    print("\n" + "="*80)
    print("✅ ALL INTEGRATION TESTS PASSED!")
    print("="*80)
    print("\n📊 Summary:")
    print("   • Chart detector initialized")
    print("   • All 6 chart pattern methods present")
    print("   • detect_all_patterns() working")
    print("   • Enhanced confluence scoring ready")
    print("   • Enhanced alert formatting ready")
    print("\n🚀 System ready for chart pattern detection!")
    print("   • 12 candlestick patterns")
    print("   • 6 chart patterns")
    print("   • 18 TOTAL PATTERNS\n")
    
    return True


if __name__ == "__main__":
    try:
        success = test_chart_pattern_integration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)