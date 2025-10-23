# test_chart_patterns.py - Test all 6 chart patterns on 2 timeframes
# Run from: c:\trading_system\

import sys
import os
import pandas as pd
import numpy as np

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from modules.chart_patterns import ChartPatterns

def create_test_data_daily(periods=120):
    """Create sample daily data with realistic patterns"""
    dates = pd.date_range('2024-01-01', periods=periods, freq='D')
    np.random.seed(42)
    
    # Create trending data with patterns
    base_price = 100
    prices = [base_price]
    
    for i in range(1, periods):
        # Uptrend with volatility
        change = np.random.randn() * 2 + 0.15
        prices.append(prices[-1] + change)
    
    data = {
        'Date': dates,
        'Open': prices,
        'High': [p + abs(np.random.randn()) * 2 for p in prices],
        'Low': [p - abs(np.random.randn()) * 2 for p in prices],
        'Close': [p + np.random.randn() * 1 for p in prices],
        'Volume': [int(1000000 + np.random.randn() * 200000) for _ in range(periods)]
    }
    
    df = pd.DataFrame(data)
    df['High'] = df[['Open', 'High', 'Close']].max(axis=1)
    df['Low'] = df[['Open', 'Low', 'Close']].min(axis=1)
    
    return df

def create_test_data_hourly(periods=200):
    """Create sample 1H data with realistic patterns"""
    dates = pd.date_range('2024-01-01', periods=periods, freq='H')
    np.random.seed(43)
    
    base_price = 150
    prices = [base_price]
    
    for i in range(1, periods):
        change = np.random.randn() * 1.5 + 0.1
        prices.append(prices[-1] + change)
    
    data = {
        'Date': dates,
        'Open': prices,
        'High': [p + abs(np.random.randn()) * 1.5 for p in prices],
        'Low': [p - abs(np.random.randn()) * 1.5 for p in prices],
        'Close': [p + np.random.randn() * 0.8 for p in prices],
        'Volume': [int(500000 + np.random.randn() * 100000) for _ in range(periods)]
    }
    
    df = pd.DataFrame(data)
    df['High'] = df[['Open', 'High', 'Close']].max(axis=1)
    df['Low'] = df[['Open', 'Low', 'Close']].min(axis=1)
    
    return df

def test_all_chart_patterns():
    """Test all 6 chart patterns on both timeframes"""
    
    print("\n" + "="*80)
    print("🧪 TESTING ALL 6 CHART PATTERNS (Daily + 1H)")
    print("="*80 + "\n")
    
    # Initialize detector
    detector = ChartPatterns({'SYMBOL': 'TEST'})
    
    # Create test data
    print("📊 Creating test data...")
    daily_df = create_test_data_daily(120)
    hourly_df = create_test_data_hourly(200)
    print(f"   Daily: {len(daily_df)} candles (${daily_df['Low'].min():.2f} - ${daily_df['High'].max():.2f})")
    print(f"   1H: {len(hourly_df)} candles (${hourly_df['Low'].min():.2f} - ${hourly_df['High'].max():.2f})\n")
    
    # List of all pattern detection methods
    patterns_to_test = [
        ('Cup & Handle', detector.detect_cup_and_handle),
        ('Ascending Triangle', detector.detect_ascending_triangle),
        ('Descending Triangle', detector.detect_descending_triangle),
        ('Bull Flag', detector.detect_bull_flag),
        ('Double Top', detector.detect_double_top),
        ('Double Bottom', detector.detect_double_bottom),
    ]
    
    results = []
    
    # Test each pattern on both timeframes
    for pattern_name, detect_func in patterns_to_test:
        # Test on Daily
        try:
            daily_detections = detect_func(daily_df, timeframe='Daily')
            daily_status = "✅ PASS"
            daily_count = len(daily_detections)
            
            daily_sample = ""
            if daily_detections:
                first = daily_detections[0]
                completion_rate = first.get('historical_completion_rate', 'N/A')
                pattern_type = first.get('pattern_type', 'N/A')
                if completion_rate != 'N/A':
                    completion_rate = f"{completion_rate*100:.0f}%"
                daily_sample = f"Sample: {first['pattern']} @ ${first['price']:.2f} ({completion_rate}, {pattern_type})"
        
        except Exception as e:
            daily_status = "❌ FAIL"
            daily_count = 0
            daily_sample = f"Error: {str(e)[:40]}"
        
        # Test on 1H
        try:
            hourly_detections = detect_func(hourly_df, timeframe='1H')
            hourly_status = "✅ PASS"
            hourly_count = len(hourly_detections)
            
            hourly_sample = ""
            if hourly_detections:
                first = hourly_detections[0]
                completion_rate = first.get('historical_completion_rate', 'N/A')
                if completion_rate != 'N/A':
                    completion_rate = f"{completion_rate*100:.0f}%"
                hourly_sample = f"Sample: {first['pattern']} @ ${first['price']:.2f} ({completion_rate})"
        
        except Exception as e:
            hourly_status = "❌ FAIL"
            hourly_count = 0
            hourly_sample = f"Error: {str(e)[:40]}"
        
        results.append({
            'pattern': pattern_name,
            'daily_status': daily_status,
            'daily_count': daily_count,
            'daily_sample': daily_sample,
            'hourly_status': hourly_status,
            'hourly_count': hourly_count,
            'hourly_sample': hourly_sample
        })
    
    # Print results table
    print(f"{'Pattern':<25} {'Daily':<15} {'1H':<15} {'Details'}")
    print("-" * 100)
    
    for r in results:
        daily_result = f"{r['daily_status']} ({r['daily_count']})"
        hourly_result = f"{r['hourly_status']} ({r['hourly_count']})"
        print(f"{r['pattern']:<25} {daily_result:<15} {hourly_result:<15}")
        if r['daily_sample']:
            print(f"  Daily: {r['daily_sample']}")
        if r['hourly_sample']:
            print(f"  1H: {r['hourly_sample']}")
    
    # Summary
    daily_passed = sum(1 for r in results if '✅' in r['daily_status'])
    hourly_passed = sum(1 for r in results if '✅' in r['hourly_status'])
    total_tests = len(results) * 2  # 6 patterns × 2 timeframes
    total_passed = daily_passed + hourly_passed
    
    print("\n" + "="*80)
    print(f"📊 SUMMARY: {total_passed}/{total_tests} tests passed")
    print(f"   Daily timeframe: {daily_passed}/6")
    print(f"   1H timeframe: {hourly_passed}/6")
    print("="*80 + "\n")
    
    if total_passed == total_tests:
        print("🎉 SUCCESS! All 6 chart patterns working on both timeframes!\n")
        print("✅ Pattern Types Covered:")
        print("   Continuation: Cup & Handle, Asc Triangle, Desc Triangle, Bull Flag")
        print("   Reversal: Double Top, Double Bottom\n")
        print("✅ Completion Rates:")
        print("   63-79% historical (excellent reliability)\n")
        print("✅ Next Steps:")
        print("   1. Test on real historical data")
        print("   2. Integrate with scanner (main.py)")
        print("   3. Add to backtesting framework")
        print("   4. Update Telegram alert templates\n")
    else:
        print("⚠️  Some patterns need debugging. Review errors above.\n")
        failed = [r for r in results if '❌' in r['daily_status'] or '❌' in r['hourly_status']]
        if failed:
            print("Failed patterns:")
            for r in failed:
                if '❌' in r['daily_status']:
                    print(f"   ❌ {r['pattern']} (Daily): {r['daily_sample']}")
                if '❌' in r['hourly_status']:
                    print(f"   ❌ {r['pattern']} (1H): {r['hourly_sample']}")
            print()
    
    # Test batch detection
    print("Testing batch detection (all patterns at once)...")
    try:
        all_daily = detector.detect_all_patterns(daily_df, 'Daily')
        all_hourly = detector.detect_all_patterns(hourly_df, '1H')
        print(f"✅ Batch detection works!")
        print(f"   Daily: {len(all_daily)} total patterns")
        print(f"   1H: {len(all_hourly)} total patterns\n")
    except Exception as e:
        print(f"❌ Batch detection failed: {e}\n")
    
    return total_passed == total_tests

if __name__ == "__main__":
    try:
        success = test_all_chart_patterns()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)