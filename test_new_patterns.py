# test_new_patterns.py - Test all 12 candlestick patterns
# Place this file in your project root (c:\trading_system\)

import sys
import os
import pandas as pd

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Now import from modules
from modules.pattern_detector import PatternDetector
import config_secure as config

def create_test_data():
    """Create sample data for testing patterns"""
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    
    # Create sample OHLCV data with some volatility
    import numpy as np
    np.random.seed(42)
    
    base_price = 100
    prices = [base_price]
    
    for i in range(1, 100):
        # Random walk with some trend
        change = np.random.randn() * 2 + 0.1
        prices.append(prices[-1] + change)
    
    data = {
        'Date': dates,
        'Open': prices,
        'High': [p + abs(np.random.randn()) * 1.5 for p in prices],
        'Low': [p - abs(np.random.randn()) * 1.5 for p in prices],
        'Close': [p + np.random.randn() * 0.5 for p in prices],
        'Volume': [int(1000000 + np.random.randn() * 200000) for _ in range(100)]
    }
    
    df = pd.DataFrame(data)
    
    # Ensure High is highest and Low is lowest
    df['High'] = df[['Open', 'High', 'Close']].max(axis=1)
    df['Low'] = df[['Open', 'Low', 'Close']].min(axis=1)
    
    return df

def test_all_patterns():
    """Test all 12 candlestick patterns"""
    
    print("\n" + "="*80)
    print("🧪 TESTING ALL 12 CANDLESTICK PATTERNS")
    print("="*80 + "\n")
    
    # Initialize detector
    detector = PatternDetector(vars(config))
    
    # Create test data
    df = create_test_data()
    print(f"✅ Test data created: {len(df)} candles")
    print(f"   Price range: ${df['Low'].min():.2f} - ${df['High'].max():.2f}\n")
    
    # List of all pattern detection methods
    patterns_to_test = [
        ('Bullish Engulfing', detector.detect_bullish_engulfing),
        ('Bearish Engulfing', detector.detect_bearish_engulfing),
        ('Hammer', detector.detect_hammer),
        ('Shooting Star', detector.detect_shooting_star),
        ('Morning Star', detector.detect_morning_star),
        ('Evening Star', detector.detect_evening_star),
        ('Three White Soldiers', detector.detect_three_white_soldiers),
        ('Three Black Crows', detector.detect_three_black_crows),
        ('Bullish Abandoned Baby', detector.detect_bullish_abandoned_baby),
        ('Bearish Abandoned Baby', detector.detect_bearish_abandoned_baby),
        ('Bullish Breakout', detector.detect_breakout),
        ('Bearish Breakdown', detector.detect_bearish_breakdown),
    ]
    
    results = []
    
    # Test each pattern
    for pattern_name, detect_func in patterns_to_test:
        try:
            detections = detect_func(df)
            status = "✅ PASS"
            count = len(detections)
            
            # Show sample if found
            sample = ""
            if detections:
                first = detections[0]
                completion_rate = first.get('historical_completion_rate', 'N/A')
                if completion_rate != 'N/A':
                    completion_rate = f"{completion_rate*100:.0f}%"
                sample = f" | Sample: {first['pattern']} @ ${first['price']:.2f} (Historical: {completion_rate})"
            
            results.append({
                'pattern': pattern_name,
                'status': status,
                'count': count,
                'sample': sample
            })
            
        except Exception as e:
            status = "❌ FAIL"
            results.append({
                'pattern': pattern_name,
                'status': status,
                'count': 0,
                'sample': f" | Error: {str(e)[:50]}"
            })
    
    # Print results
    print(f"{'Pattern':<30} {'Status':<10} {'Detections':<12} {'Details'}")
    print("-" * 100)
    
    for r in results:
        print(f"{r['pattern']:<30} {r['status']:<10} {r['count']:<12} {r['sample']}")
    
    # Summary
    passed = sum(1 for r in results if '✅' in r['status'])
    total = len(results)
    
    print("\n" + "="*80)
    print(f"📊 SUMMARY: {passed}/{total} patterns working correctly")
    print("="*80 + "\n")
    
    if passed == total:
        print("🎉 SUCCESS! All 12 candlestick patterns operational!\n")
        print("✅ Next steps:")
        print("   1. Test on real historical data (run main.py)")
        print("   2. Update enhanced_predictive_scanner.py with all 12 patterns")
        print("   3. Move to Week 1, Days 3-4: Chart Patterns\n")
    else:
        print("⚠️  Some patterns need debugging. Review errors above.\n")
        failed = [r for r in results if '❌' in r['status']]
        if failed:
            print("Failed patterns:")
            for r in failed:
                print(f"   ❌ {r['pattern']}: {r['sample']}")
            print()
    
    return passed == total

if __name__ == "__main__":
    try:
        success = test_all_patterns()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def test_all_patterns():
    """Test all 12 candlestick patterns"""
    
    print("\n" + "="*80)
    print("🧪 TESTING ALL 12 CANDLESTICK PATTERNS")
    print("="*80 + "\n")
    
    # Initialize detector
    detector = PatternDetector(vars(config))
    
    # Create test data
    df = create_test_data()
    print(f"✅ Test data created: {len(df)} candles\n")
    
    # List of all pattern detection methods
    patterns_to_test = [
        ('Bullish Engulfing', detector.detect_bullish_engulfing),
        ('Bearish Engulfing', detector.detect_bearish_engulfing),
        ('Hammer', detector.detect_hammer),
        ('Shooting Star', detector.detect_shooting_star),
        ('Morning Star', detector.detect_morning_star),
        ('Evening Star', detector.detect_evening_star),
        ('Three White Soldiers', detector.detect_three_white_soldiers),
        ('Three Black Crows', detector.detect_three_black_crows),
        ('Bullish Abandoned Baby', detector.detect_bullish_abandoned_baby),
        ('Bearish Abandoned Baby', detector.detect_bearish_abandoned_baby),
        ('Bullish Breakout', detector.detect_breakout),
        ('Bearish Breakdown', detector.detect_bearish_breakdown),
    ]
    
    results = []
    
    # Test each pattern
    for pattern_name, detect_func in patterns_to_test:
        try:
            detections = detect_func(df)
            status = "✅ PASS"
            count = len(detections)
            
            # Show sample if found
            sample = ""
            if detections:
                first = detections[0]
                completion_rate = first.get('historical_completion_rate', 'N/A')
                if completion_rate != 'N/A':
                    completion_rate = f"{completion_rate*100:.0f}%"
                sample = f" | Sample: {first['pattern']} @ ${first['price']:.2f} (Historical: {completion_rate})"
            
            results.append({
                'pattern': pattern_name,
                'status': status,
                'count': count,
                'sample': sample
            })
            
        except Exception as e:
            status = "❌ FAIL"
            results.append({
                'pattern': pattern_name,
                'status': status,
                'count': 0,
                'sample': f" | Error: {str(e)}"
            })
    
    # Print results
    print(f"{'Pattern':<30} {'Status':<10} {'Detections':<12} {'Details'}")
    print("-" * 100)
    
    for r in results:
        print(f"{r['pattern']:<30} {r['status']:<10} {r['count']:<12} {r['sample']}")
    
    # Summary
    passed = sum(1 for r in results if '✅' in r['status'])
    total = len(results)
    
    print("\n" + "="*80)
    print(f"📊 SUMMARY: {passed}/{total} patterns working correctly")
    print("="*80 + "\n")
    
    if passed == total:
        print("🎉 SUCCESS! All 12 candlestick patterns operational!\n")
        print("Next steps:")
        print("1. Update main.py to include all new patterns")
        print("2. Test on real historical data")
        print("3. Move to Week 1, Days 3-4: Chart Patterns\n")
    else:
        print("⚠️  Some patterns need debugging. Review errors above.\n")
    
    return passed == total

if __name__ == "__main__":
    success = test_all_patterns()
    sys.exit(0 if success else 1)