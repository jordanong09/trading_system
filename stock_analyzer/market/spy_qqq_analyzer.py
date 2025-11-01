"""
SPY/QQQ Regime Analyzer Module (v5.0)

Analyzes SPY and QQQ to determine current market regime:
- Bullish: Price > EMA20
- Bearish: Price < EMA20
- Combined: Agreement between both indices

This provides context for adjusting signal strength and filtering.

Author: Stock Analyzer v5.0
Dependencies: pandas, technical_indicators
"""

import pandas as pd
from typing import Dict, Optional
from datetime import datetime, timedelta
import sys
import os

# Add project root to path for standalone execution
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from stock_analyzer.utils.technical_indicators import TechnicalIndicators


class SPYQQQAnalyzer:
    """
    Analyze SPY and QQQ to determine market regime
    
    Regime Classification:
        - Bullish: Price > EMA20 (uptrend)
        - Bearish: Price < EMA20 (downtrend)
        - Combined: Both indices agreement
    """
    
    def __init__(self, config=None):
        """
        Initialize SPY/QQQ analyzer
        
        Args:
            config: Configuration dict or module with SPY_QQQ_CONFIG
        """
        # Load config or use defaults
        if config and hasattr(config, 'SPY_QQQ_CONFIG'):
            self.config = config.SPY_QQQ_CONFIG
        else:
            # Default config
            self.config = {
                'ema_short': 20,
                'ema_long': 50,
                'lookback_strength': 20
            }
        
        self.ema_period = self.config.get('ema_short', 20)
        
        # Cache for performance
        self._cache = {}
        self._cache_timestamp = None
        self._cache_duration = timedelta(hours=1)  # Cache for 1 hour
    
    def get_spy_regime(self, spy_daily_df: pd.DataFrame) -> Dict:
        """
        Determine SPY market regime
        
        Logic:
            - If Close > EMA20: Bullish
            - If Close < EMA20: Bearish
        
        Args:
            spy_daily_df: DataFrame with SPY daily OHLC data
                          Required columns: Close
                          Must have at least 20+ rows for EMA20
        
        Returns:
            Dict with:
                - regime: str ('bullish' or 'bearish')
                - close: float (current SPY price)
                - ema20: float (EMA20 value)
                - distance: float (price - EMA20)
                - distance_pct: float ((price - EMA20) / EMA20 * 100)
                - timestamp: datetime
        
        Example:
            >>> regime = analyzer.get_spy_regime(spy_df)
            >>> print(regime['regime'])  # 'bullish' or 'bearish'
        """
        if spy_daily_df is None or len(spy_daily_df) < self.ema_period:
            return {
                'regime': 'unknown',
                'close': None,
                'ema20': None,
                'distance': None,
                'distance_pct': None,
                'timestamp': datetime.now()
            }
        
        try:
            # Calculate EMA20
            ema20_series = TechnicalIndicators.calculate_ema(
                spy_daily_df, 
                period=self.ema_period
            )
            
            # Get current values
            current_close = spy_daily_df['Close'].iloc[-1]
            current_ema20 = ema20_series.iloc[-1]
            
            # Determine regime
            if current_close > current_ema20:
                regime = 'bullish'
            else:
                regime = 'bearish'
            
            # Calculate distance metrics
            distance = current_close - current_ema20
            distance_pct = (distance / current_ema20) * 100
            
            return {
                'regime': regime,
                'close': round(current_close, 2),
                'ema20': round(current_ema20, 2),
                'distance': round(distance, 2),
                'distance_pct': round(distance_pct, 2),
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            print(f"Error analyzing SPY regime: {e}")
            return {
                'regime': 'unknown',
                'close': None,
                'ema20': None,
                'distance': None,
                'distance_pct': None,
                'timestamp': datetime.now()
            }
    
    def get_qqq_regime(self, qqq_daily_df: pd.DataFrame) -> Dict:
        """
        Determine QQQ market regime
        
        Logic:
            - If Close > EMA20: Bullish
            - If Close < EMA20: Bearish
        
        Args:
            qqq_daily_df: DataFrame with QQQ daily OHLC data
                          Required columns: Close
                          Must have at least 20+ rows for EMA20
        
        Returns:
            Dict with same structure as get_spy_regime()
        
        Example:
            >>> regime = analyzer.get_qqq_regime(qqq_df)
            >>> print(regime['regime'])  # 'bullish' or 'bearish'
        """
        if qqq_daily_df is None or len(qqq_daily_df) < self.ema_period:
            return {
                'regime': 'unknown',
                'close': None,
                'ema20': None,
                'distance': None,
                'distance_pct': None,
                'timestamp': datetime.now()
            }
        
        try:
            # Calculate EMA20
            ema20_series = TechnicalIndicators.calculate_ema(
                qqq_daily_df, 
                period=self.ema_period
            )
            
            # Get current values
            current_close = qqq_daily_df['Close'].iloc[-1]
            current_ema20 = ema20_series.iloc[-1]
            
            # Determine regime
            if current_close > current_ema20:
                regime = 'bullish'
            else:
                regime = 'bearish'
            
            # Calculate distance metrics
            distance = current_close - current_ema20
            distance_pct = (distance / current_ema20) * 100
            
            return {
                'regime': regime,
                'close': round(current_close, 2),
                'ema20': round(current_ema20, 2),
                'distance': round(distance, 2),
                'distance_pct': round(distance_pct, 2),
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            print(f"Error analyzing QQQ regime: {e}")
            return {
                'regime': 'unknown',
                'close': None,
                'ema20': None,
                'distance': None,
                'distance_pct': None,
                'timestamp': datetime.now()
            }
    
    def get_combined_regime(self, spy_regime: str, qqq_regime: str) -> str:
        """
        Combine SPY and QQQ regimes into overall market assessment
        
        Logic:
            - Both bullish → 'bullish'
            - Both bearish → 'bearish'  
            - Mixed → 'mixed'
        
        Args:
            spy_regime: SPY regime ('bullish', 'bearish', or 'unknown')
            qqq_regime: QQQ regime ('bullish', 'bearish', or 'unknown')
        
        Returns:
            Combined regime: 'bullish', 'bearish', 'mixed', or 'unknown'
        
        Example:
            >>> combined = analyzer.get_combined_regime('bullish', 'bullish')
            >>> print(combined)  # 'bullish'
            
            >>> combined = analyzer.get_combined_regime('bullish', 'bearish')
            >>> print(combined)  # 'mixed'
        """
        # Handle unknown regimes
        if spy_regime == 'unknown' or qqq_regime == 'unknown':
            return 'unknown'
        
        # Both agree
        if spy_regime == qqq_regime:
            return spy_regime  # 'bullish' or 'bearish'
        
        # Disagreement
        return 'mixed'
    
    def analyze_market_regime(self, data_fetcher, use_cache: bool = True) -> Dict:
        """
        Main entry point - analyze both SPY and QQQ, return complete assessment
        
        This is the primary function called by other modules.
        
        Args:
            data_fetcher: Data fetcher object with get_daily_data() method
            use_cache: Whether to use cached result (default True)
        
        Returns:
            Dict with complete regime analysis:
                - spy: Dict (SPY regime details)
                - qqq: Dict (QQQ regime details)
                - combined: str (overall market regime)
                - alignment: bool (whether SPY/QQQ agree)
                - timestamp: datetime
        
        Example Usage:
            >>> from stock_analyzer.market.spy_qqq_analyzer import SPYQQQAnalyzer
            >>> from stock_analyzer.utils import config
            >>> analyzer = SPYQQQAnalyzer(config)
            >>> result = analyzer.analyze_market_regime(data_fetcher)
            >>> print(f"Market: {result['combined']}")
            >>> print(f"SPY: {result['spy']['regime']}, QQQ: {result['qqq']['regime']}")
        """
        # Check cache
        if use_cache and self._is_cache_valid():
            print("Using cached SPY/QQQ regime analysis")
            return self._cache
        
        try:
            # Fetch SPY data
            print("Fetching SPY data for regime analysis...")
            spy_df = data_fetcher.get_daily_data('SPY', lookback_days=50)
            
            # Fetch QQQ data
            print("Fetching QQQ data for regime analysis...")
            qqq_df = data_fetcher.get_daily_data('QQQ', lookback_days=50)
            
            # Analyze individual regimes
            spy_regime = self.get_spy_regime(spy_df)
            qqq_regime = self.get_qqq_regime(qqq_df)
            
            # Combine regimes
            combined = self.get_combined_regime(
                spy_regime['regime'], 
                qqq_regime['regime']
            )
            
            # Check alignment
            alignment = spy_regime['regime'] == qqq_regime['regime']
            
            # Build result
            result = {
                'spy': spy_regime,
                'qqq': qqq_regime,
                'combined': combined,
                'alignment': alignment,
                'timestamp': datetime.now()
            }
            
            # Cache result
            self._cache = result
            self._cache_timestamp = datetime.now()
            
            # Print summary
            print(f"Market Regime: {combined.upper()} "
                  f"(SPY: {spy_regime['regime']}, QQQ: {qqq_regime['regime']}, "
                  f"Aligned: {alignment})")
            
            return result
            
        except Exception as e:
            print(f"Error analyzing market regime: {e}")
            return self._get_default_result()
    
    def _is_cache_valid(self) -> bool:
        """Check if cached result is still valid"""
        if self._cache_timestamp is None or not self._cache:
            return False
        
        age = datetime.now() - self._cache_timestamp
        return age < self._cache_duration
    
    def _get_default_result(self) -> Dict:
        """Return unknown result when calculation fails"""
        return {
            'spy': {
                'regime': 'unknown',
                'close': None,
                'ema20': None,
                'distance': None,
                'distance_pct': None,
                'timestamp': datetime.now()
            },
            'qqq': {
                'regime': 'unknown',
                'close': None,
                'ema20': None,
                'distance': None,
                'distance_pct': None,
                'timestamp': datetime.now()
            },
            'combined': 'unknown',
            'alignment': False,
            'timestamp': datetime.now()
        }
    
    def clear_cache(self):
        """Clear cached regime analysis"""
        self._cache = {}
        self._cache_timestamp = None


# =============================================================================
# STANDALONE USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    """
    Test the SPY/QQQ analyzer module standalone
    
    Usage:
        python stock_analyzer/market/spy_qqq_analyzer.py
    """
    print("="*70)
    print("SPY/QQQ REGIME ANALYZER - STANDALONE TEST")
    print("="*70)
    
    # Test 1: Combined regime logic
    print("\nTEST 1: Combined Regime Logic")
    print("-"*70)
    
    from stock_analyzer.utils import config
    analyzer = SPYQQQAnalyzer(config)
    
    test_cases = [
        ('bullish', 'bullish', 'bullish'),
        ('bearish', 'bearish', 'bearish'),
        ('bullish', 'bearish', 'mixed'),
        ('bearish', 'bullish', 'mixed'),
        ('unknown', 'bullish', 'unknown'),
    ]
    
    for spy, qqq, expected in test_cases:
        result = analyzer.get_combined_regime(spy, qqq)
        status = "✓" if result == expected else "✗"
        print(f"{status} SPY={spy:8s} + QQQ={qqq:8s} → {result:8s} (expected: {expected})")
    
    # Test 2: Regime detection with sample data
    print("\nTEST 2: Regime Detection (Sample Data)")
    print("-"*70)
    
    import numpy as np
    
    # Create sample data - bullish scenario (price > EMA)
    dates = pd.date_range(end=datetime.now(), periods=50, freq='D')
    
    # Bullish: prices trending up
    bullish_prices = np.linspace(100, 110, 50) + np.random.normal(0, 0.5, 50)
    spy_bullish = pd.DataFrame({
        'Date': dates,
        'Close': bullish_prices,
        'High': bullish_prices + 1,
        'Low': bullish_prices - 1,
        'Open': bullish_prices
    })
    spy_bullish.set_index('Date', inplace=True)
    
    spy_regime = analyzer.get_spy_regime(spy_bullish)
    print(f"SPY Sample: {spy_regime['regime']} "
          f"(Price: ${spy_regime['close']:.2f}, EMA20: ${spy_regime['ema20']:.2f}, "
          f"Distance: {spy_regime['distance_pct']:.2f}%)")
    
    # Bearish: prices trending down
    bearish_prices = np.linspace(110, 100, 50) + np.random.normal(0, 0.5, 50)
    qqq_bearish = pd.DataFrame({
        'Date': dates,
        'Close': bearish_prices,
        'High': bearish_prices + 1,
        'Low': bearish_prices - 1,
        'Open': bearish_prices
    })
    qqq_bearish.set_index('Date', inplace=True)
    
    qqq_regime = analyzer.get_qqq_regime(qqq_bearish)
    print(f"QQQ Sample: {qqq_regime['regime']} "
          f"(Price: ${qqq_regime['close']:.2f}, EMA20: ${qqq_regime['ema20']:.2f}, "
          f"Distance: {qqq_regime['distance_pct']:.2f}%)")
    
    combined = analyzer.get_combined_regime(spy_regime['regime'], qqq_regime['regime'])
    print(f"\nCombined Regime: {combined.upper()}")
    
    print("\n" + "="*70)
    print("SPY/QQQ ANALYZER MODULE TESTS COMPLETE")
    print("="*70)
    print("\nREADY FOR INTEGRATION:")
    print("  - Import: from stock_analyzer.market.spy_qqq_analyzer import SPYQQQAnalyzer")
    print("  - Usage: analyzer = SPYQQQAnalyzer(config)")
    print("  - Call: result = analyzer.analyze_market_regime(data_fetcher)")
    print("="*70)