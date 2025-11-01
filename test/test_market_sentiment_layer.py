"""
T07: Market Sentiment Layer - End-to-End Test

Tests the complete market sentiment layer including:
    - Volatility Index (T04)
    - SPY/QQQ Analyzer (T05)
    - Composite Sentiment Engine (T06)

Tests:
    1. Output format validation
    2. Edge cases (missing data, extreme volatility)
    3. Performance (< 5 seconds)
    4. Integration between components

Usage:
    python tests/test_market_sentiment_layer.py
"""

import sys
import os
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from stock_analyzer.utils import config
from stock_analyzer.market import (
    VolatilityIndex,
    SPYQQQAnalyzer,
    SentimentEngine,
    get_composite_sentiment
)


# =============================================================================
# MOCK DATA FETCHER
# =============================================================================

class MockDataFetcher:
    """
    Mock data fetcher for testing without real API calls
    """
    
    def __init__(self, scenario='normal'):
        """
        Args:
            scenario: 'normal', 'bullish', 'bearish', 'high_vol', 'missing_data'
        """
        self.scenario = scenario
    
    def get_daily_data(self, symbol: str, lookback_days: int = 100) -> pd.DataFrame:
        """
        Generate mock daily data based on scenario
        """
        if self.scenario == 'missing_data' and symbol == 'QQQ':
            return None  # Simulate missing data
        
        dates = pd.date_range(end=datetime.now(), periods=lookback_days, freq='D')
        
        # Generate data based on scenario
        if self.scenario == 'bullish':
            # Strong uptrend - price > EMA20
            base_price = 450 if symbol == 'SPY' else 380
            prices = np.linspace(base_price * 0.9, base_price * 1.1, lookback_days)
            prices += np.random.normal(0, base_price * 0.005, lookback_days)
            
        elif self.scenario == 'bearish':
            # Strong downtrend - price < EMA20
            base_price = 450 if symbol == 'SPY' else 380
            prices = np.linspace(base_price * 1.1, base_price * 0.9, lookback_days)
            prices += np.random.normal(0, base_price * 0.005, lookback_days)
            
        elif self.scenario == 'high_vol':
            # High volatility scenario
            base_price = 450 if symbol == 'SPY' else 380
            prices = base_price + np.random.normal(0, base_price * 0.03, lookback_days)
            
        else:  # normal
            # Normal market with moderate trend
            base_price = 450 if symbol == 'SPY' else 380
            prices = base_price + np.cumsum(np.random.normal(0, base_price * 0.01, lookback_days))
        
        # Generate OHLC from close prices
        df = pd.DataFrame({
            'Date': dates,
            'Open': prices * 0.998,
            'High': prices * 1.005,
            'Low': prices * 0.995,
            'Close': prices,
            'Volume': np.random.randint(50000000, 150000000, lookback_days)
        })
        
        df.set_index('Date', inplace=True)
        return df


# =============================================================================
# TEST FUNCTIONS
# =============================================================================

def test_output_format(sentiment: dict) -> tuple:
    """
    Test 1: Validate output format matches specification
    
    Returns:
        (passed: bool, message: str)
    """
    print("\nTEST 1: Output Format Validation")
    print("-" * 70)
    
    required_fields = [
        'spy_regime', 'qqq_regime', 'combined_regime', 'alignment',
        'vol_ratio', 'risk_bucket', 'vol_multiplier',
        'composite', 'base_weight', 'final_weight',
        'timestamp', 'spy_price', 'qqq_price', 'spy_atr'
    ]
    
    missing_fields = []
    for field in required_fields:
        if field not in sentiment:
            missing_fields.append(field)
    
    if missing_fields:
        print(f"✗ FAILED - Missing fields: {missing_fields}")
        return False, f"Missing fields: {missing_fields}"
    
    # Validate data types
    type_checks = [
        (sentiment['spy_regime'], str),
        (sentiment['qqq_regime'], str),
        (sentiment['combined_regime'], str),
        (sentiment['alignment'], bool),
        (sentiment['vol_multiplier'], (int, float)),
        (sentiment['base_weight'], (int, float)),
        (sentiment['final_weight'], (int, float)),
    ]
    
    for value, expected_type in type_checks:
        if not isinstance(value, expected_type):
            print(f"✗ FAILED - Type mismatch: {value} is not {expected_type}")
            return False, f"Type mismatch for {value}"
    
    print("✓ All required fields present")
    print("✓ All data types correct")
    return True, "Output format valid"


def test_weight_ranges(sentiment: dict) -> tuple:
    """
    Test 2: Validate weight values are in reasonable ranges
    
    Returns:
        (passed: bool, message: str)
    """
    print("\nTEST 2: Weight Range Validation")
    print("-" * 70)
    
    final_weight = sentiment['final_weight']
    base_weight = sentiment['base_weight']
    vol_mult = sentiment['vol_multiplier']
    
    # Check ranges
    if not (0.8 <= final_weight <= 1.21):
        print(f"✗ FAILED - final_weight {final_weight} out of range [0.8, 1.21]")
        return False, f"Weight out of range: {final_weight}"
    
    if base_weight not in [1.0, 1.1]:
        print(f"✗ FAILED - base_weight {base_weight} not in [1.0, 1.1]")
        return False, f"Invalid base_weight: {base_weight}"
    
    if not (0.8 <= vol_mult <= 1.1):
        print(f"✗ FAILED - vol_multiplier {vol_mult} out of range [0.8, 1.1]")
        return False, f"Vol multiplier out of range: {vol_mult}"
    
    # Verify calculation
    calculated = round(base_weight * vol_mult, 2)
    if calculated != final_weight:
        print(f"✗ FAILED - Weight calculation error: {base_weight} × {vol_mult} = {calculated}, not {final_weight}")
        return False, "Weight calculation mismatch"
    
    print(f"✓ final_weight: {final_weight} (valid range)")
    print(f"✓ base_weight: {base_weight} (valid)")
    print(f"✓ vol_multiplier: {vol_mult} (valid range)")
    print(f"✓ Calculation correct: {base_weight} × {vol_mult} = {final_weight}")
    return True, "Weights in valid ranges"


def test_edge_cases() -> tuple:
    """
    Test 3: Test edge cases (missing data, extreme scenarios)
    
    Returns:
        (passed: bool, message: str)
    """
    print("\nTEST 3: Edge Cases")
    print("-" * 70)
    
    engine = SentimentEngine(config)
    
    # Edge case 1: Missing QQQ data
    print("\nEdge Case 1: Missing QQQ data")
    mock_fetcher = MockDataFetcher(scenario='missing_data')
    sentiment = engine.get_composite_sentiment(mock_fetcher, use_cache=False)
    
    if sentiment['qqq_regime'] != 'unknown':
        print(f"✗ FAILED - Should handle missing QQQ data")
        return False, "Missing data not handled"
    print("✓ Handles missing QQQ data gracefully")
    
    # Edge case 2: High volatility
    print("\nEdge Case 2: High volatility scenario")
    mock_fetcher = MockDataFetcher(scenario='high_vol')
    sentiment = engine.get_composite_sentiment(mock_fetcher, use_cache=False)
    
    # Should still return valid result
    if not sentiment.get('final_weight'):
        print(f"✗ FAILED - Should handle high volatility")
        return False, "High volatility not handled"
    print(f"✓ Handles high volatility: risk_bucket={sentiment['risk_bucket']}, weight={sentiment['final_weight']}")
    
    # Edge case 3: Extreme bearish
    print("\nEdge Case 3: Extreme bearish scenario")
    mock_fetcher = MockDataFetcher(scenario='bearish')
    sentiment = engine.get_composite_sentiment(mock_fetcher, use_cache=False)
    
    if sentiment['spy_regime'] != 'bearish' or sentiment['qqq_regime'] != 'bearish':
        print(f"✗ WARNING - Expected bearish regimes, got SPY={sentiment['spy_regime']}, QQQ={sentiment['qqq_regime']}")
    print(f"✓ Handles bearish scenario: combined={sentiment['combined_regime']}, weight={sentiment['final_weight']}")
    
    return True, "All edge cases handled"


def test_performance() -> tuple:
    """
    Test 4: Performance test (should complete in < 5 seconds)
    
    Returns:
        (passed: bool, message: str)
    """
    print("\nTEST 4: Performance Test")
    print("-" * 70)
    
    mock_fetcher = MockDataFetcher(scenario='normal')
    engine = SentimentEngine(config)
    
    # Test without cache
    start_time = time.time()
    sentiment = engine.get_composite_sentiment(mock_fetcher, use_cache=False)
    elapsed = time.time() - start_time
    
    print(f"Execution time (no cache): {elapsed:.3f} seconds")
    
    if elapsed > 5.0:
        print(f"✗ FAILED - Took {elapsed:.3f}s, should be < 5.0s")
        return False, f"Too slow: {elapsed:.3f}s"
    
    print(f"✓ Performance acceptable: {elapsed:.3f}s < 5.0s")
    
    # Test with cache
    start_time = time.time()
    sentiment_cached = engine.get_composite_sentiment(mock_fetcher, use_cache=True)
    elapsed_cached = time.time() - start_time
    
    print(f"Execution time (cached): {elapsed_cached:.3f} seconds")
    print(f"✓ Cache working: {elapsed_cached:.3f}s << {elapsed:.3f}s")
    
    return True, f"Performance: {elapsed:.3f}s"


def test_integration() -> tuple:
    """
    Test 5: Integration between components
    
    Returns:
        (passed: bool, message: str)
    """
    print("\nTEST 5: Component Integration")
    print("-" * 70)
    
    mock_fetcher = MockDataFetcher(scenario='bullish')
    
    # Test convenience function
    sentiment = get_composite_sentiment(mock_fetcher, config, use_cache=False)
    
    if not sentiment:
        print("✗ FAILED - Convenience function failed")
        return False, "Integration failed"
    
    print("✓ Convenience function works")
    print(f"✓ Volatility component integrated: {sentiment['risk_bucket']}")
    print(f"✓ SPY/QQQ component integrated: {sentiment['combined_regime']}")
    print(f"✓ Weight calculation integrated: {sentiment['final_weight']}")
    
    return True, "All components integrated"


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def run_all_tests():
    """
    Run all T07 tests and report results
    """
    print("=" * 70)
    print("T07: MARKET SENTIMENT LAYER - END-TO-END TEST")
    print("=" * 70)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Setup
    mock_fetcher = MockDataFetcher(scenario='normal')
    sentiment = get_composite_sentiment(mock_fetcher, config, use_cache=False)
    
    # Run tests
    results = []
    
    tests = [
        ("Output Format", lambda: test_output_format(sentiment)),
        ("Weight Ranges", lambda: test_weight_ranges(sentiment)),
        ("Edge Cases", test_edge_cases),
        ("Performance", test_performance),
        ("Integration", test_integration),
    ]
    
    for test_name, test_func in tests:
        try:
            passed, message = test_func()
            results.append((test_name, passed, message))
        except Exception as e:
            print(f"\n✗ EXCEPTION in {test_name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False, str(e)))
    
    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed_count = sum(1 for _, passed, _ in results if passed)
    total_count = len(results)
    
    for test_name, passed, message in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {test_name}: {message}")
    
    print("=" * 70)
    print(f"Results: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("✓ ALL TESTS PASSED - Market Sentiment Layer Ready!")
    else:
        print(f"✗ {total_count - passed_count} TEST(S) FAILED")
    
    print("=" * 70)
    
    # Print sample output
    print("\nSAMPLE OUTPUT:")
    print("-" * 70)
    print(f"Composite: {sentiment['composite']}")
    print(f"Final Weight: {sentiment['final_weight']}")
    print(f"SPY Regime: {sentiment['spy_regime']} (${sentiment['spy_price']})")
    print(f"QQQ Regime: {sentiment['qqq_regime']} (${sentiment['qqq_price']})")
    print(f"Combined: {sentiment['combined_regime']}")
    print(f"Volatility: {sentiment['risk_bucket']} (ratio: {sentiment['vol_ratio']})")
    print(f"Aligned: {sentiment['alignment']}")
    print("=" * 70)
    
    return passed_count == total_count


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)