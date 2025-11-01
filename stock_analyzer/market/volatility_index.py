"""
Market Volatility Index Module (v5.0)

Internal volatility calculation replacing external VIX data.
Uses SPY ATR(14) ratio against its 50-day SMA to classify market risk.

Algorithm:
    1. Calculate SPY ATR(14) from daily data
    2. Calculate 50-day SMA of ATR(14)
    3. vol_ratio = current_ATR / SMA_ATR
    4. Classify into risk buckets (risk_on, neutral, caution, risk_off)
    5. Apply multiplier to adjust scanning parameters

Author: Stock Analyzer v5.0
Dependencies: pandas, numpy, technical_indicators
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from datetime import datetime, timedelta
import sys
import os

# Add project root to path for standalone execution
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Import configuration and technical indicators
from stock_analyzer.utils.technical_indicators import TechnicalIndicators


class VolatilityIndex:
    """
    Calculate internal volatility index from SPY/QQQ data
    Replaces external VIX dependency with ATR-based calculation
    """
    
    def __init__(self, config=None):
        """
        Initialize volatility index calculator
        
        Args:
            config: Configuration dict or module with VOLATILITY_CONFIG
        """
        # Load config or use defaults
        if config and hasattr(config, 'VOLATILITY_CONFIG'):
            self.config = config.VOLATILITY_CONFIG
        else:
            # Default fallback config if T03 not complete
            self.config = {
                'spy_atr_period': 14,
                'spy_atr_sma_period': 50,
                'risk_buckets': {
                    'risk_on': {'max': 0.9, 'mult': 1.10},
                    'neutral': {'min': 0.9, 'max': 1.2, 'mult': 1.00},
                    'caution': {'min': 1.2, 'max': 1.5, 'mult': 0.90},
                    'risk_off': {'min': 1.5, 'mult': 0.80}
                }
            }
        
        self.atr_period = self.config['spy_atr_period']
        self.sma_period = self.config['spy_atr_sma_period']
        self.risk_buckets = self.config['risk_buckets']
        
        # Cache for performance
        self._cache = {}
        self._cache_timestamp = None
        self._cache_duration = timedelta(hours=1)  # Cache for 1 hour
    
    def calculate_spy_atr_ratio(self, spy_daily_df: pd.DataFrame) -> Optional[float]:
        """
        Calculate SPY volatility ratio
        
        Formula: vol_ratio = ATR(14) / SMA(ATR(14), 50)
        
        Args:
            spy_daily_df: DataFrame with SPY daily OHLC data
                          Required columns: High, Low, Close
                          Must have at least (atr_period + sma_period) rows
        
        Returns:
            vol_ratio as float, or None if insufficient data
        
        Example:
            vol_ratio = 1.35 means current volatility is 35% above 50-day average
        """
        required_bars = self.atr_period + self.sma_period
        
        if spy_daily_df is None or len(spy_daily_df) < required_bars:
            print(f"âš ï¸  Insufficient data for volatility calc. Need {required_bars} bars, got {len(spy_daily_df) if spy_daily_df is not None else 0}")
            return None
        
        try:
            # Calculate ATR(14) for each day
            atr_values = []
            
            for i in range(self.atr_period, len(spy_daily_df) + 1):
                window = spy_daily_df.iloc[:i]
                atr = TechnicalIndicators.calculate_atr(window, period=self.atr_period)
                if atr is not None:
                    atr_values.append(atr)
            
            if len(atr_values) < self.sma_period:
                print(f"âš ï¸  Insufficient ATR values for SMA. Need {self.sma_period}, got {len(atr_values)}")
                return None
            
            # Convert to Series for easier calculation
            atr_series = pd.Series(atr_values)
            
            # Calculate current ATR (most recent)
            current_atr = atr_series.iloc[-1]
            
            # Calculate 50-day SMA of ATR
            sma_atr = atr_series.rolling(window=self.sma_period).mean().iloc[-1]
            
            if sma_atr == 0 or pd.isna(sma_atr):
                print("âš ï¸  Invalid SMA of ATR (zero or NaN)")
                return None
            
            # Calculate ratio
            vol_ratio = current_atr / sma_atr
            
            return round(vol_ratio, 3)
            
        except Exception as e:
            print(f"âŒ Error calculating SPY ATR ratio: {e}")
            return None
    
    def classify_risk_bucket(self, vol_ratio: Optional[float]) -> Dict:
        """
        Classify risk bucket based on volatility ratio
        
        Buckets:
            - risk_on:  vol_ratio < 0.9  (low volatility, bullish)
            - neutral:  0.9 <= vol_ratio < 1.2  (normal)
            - caution:  1.2 <= vol_ratio < 1.5  (elevated volatility)
            - risk_off: vol_ratio >= 1.5  (high volatility, defensive)
        
        Args:
            vol_ratio: Volatility ratio from calculate_spy_atr_ratio()
        
        Returns:
            Dict with:
                - bucket: str (risk_on|neutral|caution|risk_off)
                - multiplier: float (parameter adjustment)
                - vol_ratio: float (input ratio)
                - description: str (human-readable)
        
        Example:
            >>> classify_risk_bucket(1.35)
            {
                'bucket': 'caution',
                'multiplier': 0.90,
                'vol_ratio': 1.35,
                'description': 'Elevated volatility - trade cautiously'
            }
        """
        if vol_ratio is None:
            # Default to neutral if no data
            return {
                'bucket': 'neutral',
                'multiplier': 1.00,
                'vol_ratio': None,
                'description': 'Unable to determine - using neutral parameters'
            }
        
        # Classify based on thresholds
        bucket = None
        multiplier = 1.00
        
        if vol_ratio < self.risk_buckets['risk_on']['max']:
            bucket = 'risk_on'
            multiplier = self.risk_buckets['risk_on']['mult']
            description = 'Low volatility - aggressive parameters'
            
        elif vol_ratio < self.risk_buckets['neutral']['max']:
            bucket = 'neutral'
            multiplier = self.risk_buckets['neutral']['mult']
            description = 'Normal volatility - standard parameters'
            
        elif vol_ratio < self.risk_buckets['caution']['max']:
            bucket = 'caution'
            multiplier = self.risk_buckets['caution']['mult']
            description = 'Elevated volatility - trade cautiously'
            
        else:  # vol_ratio >= 1.5
            bucket = 'risk_off'
            multiplier = self.risk_buckets['risk_off']['mult']
            description = 'High volatility - defensive mode'
        
        return {
            'bucket': bucket,
            'multiplier': multiplier,
            'vol_ratio': vol_ratio,
            'description': description
        }
    
    def get_volatility_index(self, data_fetcher, use_cache: bool = True) -> Dict:
        """
        Main entry point - fetch SPY data, calculate ratio, classify bucket
        
        This is the primary function called by other modules.
        
        Args:
            data_fetcher: Data fetcher object with get_daily_data() method
            use_cache: Whether to use cached result (default True)
        
        Returns:
            Dict with complete volatility analysis:
                - bucket: str (risk level)
                - multiplier: float (parameter adjustment)
                - vol_ratio: float (ATR ratio)
                - description: str
                - timestamp: datetime (calculation time)
                - spy_atr: float (current SPY ATR)
                - spy_price: float (current SPY price)
        
        Example Usage:
            >>> from stock_analyzer.market.volatility_index import VolatilityIndex
            >>> from stock_analyzer.utils import config
            >>> vol_index = VolatilityIndex(config)
            >>> result = vol_index.get_volatility_index(data_fetcher)
            >>> print(f"Market: {result['bucket']} (mult: {result['multiplier']})")
        """
        # Check cache
        if use_cache and self._is_cache_valid():
            print("âœ… Using cached volatility index")
            return self._cache
        
        try:
            # Fetch SPY daily data
            print("Fetching SPY data for volatility calculation...")
            spy_daily_df = data_fetcher.get_daily_data('SPY', lookback_days=200)
            
            if spy_daily_df is None or len(spy_daily_df) == 0:
                print("âŒ Failed to fetch SPY data")
                return self._get_default_result()
            
            # Calculate volatility ratio
            vol_ratio = self.calculate_spy_atr_ratio(spy_daily_df)
            
            # Classify risk bucket
            classification = self.classify_risk_bucket(vol_ratio)
            
            # Get additional context
            current_atr = TechnicalIndicators.calculate_atr(spy_daily_df, self.atr_period)
            current_price = spy_daily_df['Close'].iloc[-1]
            
            # Build result
            result = {
                **classification,
                'timestamp': datetime.now(),
                'spy_atr': round(current_atr, 2) if current_atr else None,
                'spy_price': round(current_price, 2),
                'data_points': len(spy_daily_df)
            }
            
            # Cache result
            self._cache = result
            self._cache_timestamp = datetime.now()
            
            # Print summary
            print(f"âœ… Volatility Index: {result['bucket'].upper()} "
                  f"(ratio: {result['vol_ratio']}, mult: {result['multiplier']})")
            
            return result
            
        except Exception as e:
            print(f"âŒ Error getting volatility index: {e}")
            return self._get_default_result()
    
    def _is_cache_valid(self) -> bool:
        """Check if cached result is still valid"""
        if self._cache_timestamp is None or not self._cache:
            return False
        
        age = datetime.now() - self._cache_timestamp
        return age < self._cache_duration
    
    def _get_default_result(self) -> Dict:
        """Return neutral result when calculation fails"""
        return {
            'bucket': 'neutral',
            'multiplier': 1.00,
            'vol_ratio': None,
            'description': 'Unable to calculate - using neutral parameters',
            'timestamp': datetime.now(),
            'spy_atr': None,
            'spy_price': None,
            'data_points': 0
        }
    
    def clear_cache(self):
        """Clear cached volatility calculation"""
        self._cache = {}
        self._cache_timestamp = None


# =============================================================================
# STANDALONE USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    """
    Test the volatility index module standalone
    
    Usage:
        python stock_analyzer/market/volatility_index.py
    """
    print("="*70)
    print("VOLATILITY INDEX MODULE - STANDALONE TEST")
    print("="*70)
    
    # Test 1: Classification logic
    print("\nTEST 1: Classification Logic")
    print("-"*70)
    
    from stock_analyzer.utils import config
    vol_index = VolatilityIndex(config)
    
    test_ratios = [0.7, 0.95, 1.15, 1.35, 1.75]
    
    for ratio in test_ratios:
        result = vol_index.classify_risk_bucket(ratio)
        print(f"vol_ratio={ratio:.2f} â†' {result['bucket']:10s} "
              f"(mult: {result['multiplier']:.2f}) - {result['description']}")
    
    # Test 2: ATR calculation with sample data
    print("\nTEST 2: ATR Calculation (Sample Data)")
    print("-"*70)
    
    # Create sample SPY data
    dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
    sample_data = pd.DataFrame({
        'Date': dates,
        'High': np.random.uniform(450, 460, 100),
        'Low': np.random.uniform(440, 450, 100),
        'Close': np.random.uniform(445, 455, 100)
    })
    sample_data.set_index('Date', inplace=True)
    
    vol_ratio = vol_index.calculate_spy_atr_ratio(sample_data)
    print(f"Sample vol_ratio: {vol_ratio}")
    
    classification = vol_index.classify_risk_bucket(vol_ratio)
    print(f"Classification: {classification['bucket']} (mult: {classification['multiplier']})")
    
    print("\n" + "="*70)
    print("âœ… VOLATILITY INDEX MODULE TESTS COMPLETE")
    print("="*70)
    print("\nREADY FOR INTEGRATION:")
    print("  - Import: from stock_analyzer.market.volatility_index import VolatilityIndex")
    print("  - Usage: vol_index = VolatilityIndex(config)")
    print("  - Call: result = vol_index.get_volatility_index(data_fetcher)")
    print("="*70)