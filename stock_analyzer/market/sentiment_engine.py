"""
Composite Sentiment Engine Module (v5.0)

Combines multiple market indicators into unified sentiment:
    1. Volatility Index (SPY ATR ratio)
    2. SPY/QQQ Regime Analysis (bullish/bearish)
    3. Combined Weight Calculation

This provides the primary market context for all trading decisions.

Author: Stock Analyzer v5.0
Dependencies: volatility_index, spy_qqq_analyzer
"""

from typing import Dict
from datetime import datetime, timedelta
import sys
import os

# Add project root to path for standalone execution
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from stock_analyzer.market.volatility_index import VolatilityIndex
from stock_analyzer.market.spy_qqq_analyzer import SPYQQQAnalyzer


class SentimentEngine:
    """
    Composite sentiment engine combining volatility and regime analysis
    
    Weight Calculation:
        - Aligned regimes (both bull/bear): base_weight = 1.1
        - Mixed regimes: base_weight = 1.0
        - Final weight = base_weight × vol_multiplier
    
    Example weights:
        - Bullish aligned + low vol (1.10): 1.1 × 1.10 = 1.21
        - Bearish aligned + high vol (0.80): 1.1 × 0.80 = 0.88
        - Mixed + neutral (1.00): 1.0 × 1.00 = 1.00
    """
    
    def __init__(self, config=None):
        """
        Initialize sentiment engine
        
        Args:
            config: Configuration dict or module
        """
        self.config = config
        self.volatility_index = VolatilityIndex(config)
        self.spy_qqq_analyzer = SPYQQQAnalyzer(config)
        
        # Cache for performance
        self._cache = {}
        self._cache_timestamp = None
        self._cache_duration = timedelta(hours=1)  # Cache for 1 hour
    
    def get_composite_sentiment(self, data_fetcher, use_cache: bool = True) -> Dict:
        """
        Calculate complete market sentiment
        
        Combines:
            - Volatility Index (risk bucket + multiplier)
            - SPY/QQQ Regime Analysis (bullish/bearish/mixed)
            - Composite Weight (for signal adjustments)
        
        Args:
            data_fetcher: Data fetcher object with get_daily_data() method
            use_cache: Whether to use cached result (default True)
        
        Returns:
            Dict with complete sentiment:
                - spy_regime: str (bullish/bearish/unknown)
                - qqq_regime: str (bullish/bearish/unknown)
                - combined_regime: str (bullish/bearish/mixed/unknown)
                - alignment: bool (SPY/QQQ agree)
                - vol_ratio: float (ATR ratio)
                - risk_bucket: str (risk_on/neutral/caution/risk_off)
                - vol_multiplier: float (0.80-1.10)
                - composite: str (overall sentiment description)
                - base_weight: float (1.0 or 1.1)
                - final_weight: float (base × vol_multiplier)
                - timestamp: datetime
                - spy_price: float
                - qqq_price: float
                - spy_atr: float
        
        Example Usage:
            >>> from stock_analyzer.market.sentiment_engine import SentimentEngine
            >>> from stock_analyzer.utils import config
            >>> engine = SentimentEngine(config)
            >>> sentiment = engine.get_composite_sentiment(data_fetcher)
            >>> print(f"Market: {sentiment['composite']} (weight: {sentiment['final_weight']})")
        """
        # Check cache
        if use_cache and self._is_cache_valid():
            print("Using cached composite sentiment")
            return self._cache
        
        print("\n" + "="*70)
        print("CALCULATING COMPOSITE MARKET SENTIMENT")
        print("="*70)
        
        try:
            # Step 1: Get SPY/QQQ regime analysis
            print("\n[1/2] Analyzing SPY/QQQ Regimes...")
            regime_analysis = self.spy_qqq_analyzer.analyze_market_regime(
                data_fetcher, 
                use_cache=use_cache
            )
            
            # Step 2: Get volatility index
            print("\n[2/2] Calculating Volatility Index...")
            vol_index = self.volatility_index.get_volatility_index(
                data_fetcher,
                use_cache=use_cache
            )
            
            # Step 3: Calculate composite weight
            base_weight = self._calculate_base_weight(regime_analysis['combined'])
            vol_multiplier = vol_index['multiplier']
            final_weight = round(base_weight * vol_multiplier, 2)
            
            # Step 4: Determine composite sentiment description
            composite_desc = self._generate_composite_description(
                regime_analysis['combined'],
                vol_index['bucket']
            )
            
            # Build complete result
            result = {
                # Regime components
                'spy_regime': regime_analysis['spy']['regime'],
                'qqq_regime': regime_analysis['qqq']['regime'],
                'combined_regime': regime_analysis['combined'],
                'alignment': regime_analysis['alignment'],
                
                # Volatility components
                'vol_ratio': vol_index['vol_ratio'],
                'risk_bucket': vol_index['bucket'],
                'vol_multiplier': vol_multiplier,
                
                # Composite calculation
                'composite': composite_desc,
                'base_weight': base_weight,
                'final_weight': final_weight,
                
                # Additional context
                'timestamp': datetime.now(),
                'spy_price': regime_analysis['spy']['close'],
                'qqq_price': regime_analysis['qqq']['close'],
                'spy_atr': vol_index['spy_atr'],
                
                # Full details (for debugging)
                '_regime_details': regime_analysis,
                '_vol_details': vol_index
            }
            
            # Cache result
            self._cache = result
            self._cache_timestamp = datetime.now()
            
            # Print summary
            print("\n" + "="*70)
            print("COMPOSITE SENTIMENT SUMMARY")
            print("="*70)
            print(f"Market Regime: {result['combined_regime'].upper()}")
            print(f"  SPY: {result['spy_regime']} (${result['spy_price']})")
            print(f"  QQQ: {result['qqq_regime']} (${result['qqq_price']})")
            print(f"  Aligned: {result['alignment']}")
            print(f"\nVolatility: {result['risk_bucket'].upper()}")
            print(f"  Vol Ratio: {result['vol_ratio']}")
            print(f"  Multiplier: {result['vol_multiplier']}x")
            print(f"\nComposite: {result['composite']}")
            print(f"  Base Weight: {result['base_weight']}")
            print(f"  Final Weight: {result['final_weight']}x")
            print("="*70 + "\n")
            
            return result
            
        except Exception as e:
            print(f"Error calculating composite sentiment: {e}")
            import traceback
            traceback.print_exc()
            return self._get_default_result()
    
    def _calculate_base_weight(self, combined_regime: str) -> float:
        """
        Calculate base weight based on regime alignment
        
        Logic:
            - Aligned (bullish or bearish): 1.1 (bonus for clarity)
            - Mixed: 1.0 (standard weight)
            - Unknown: 1.0 (neutral)
        
        Args:
            combined_regime: Combined regime from SPY/QQQ analysis
        
        Returns:
            Base weight (1.0 or 1.1)
        """
        if combined_regime in ['bullish', 'bearish']:
            return 1.1  # Aligned regimes get bonus
        else:
            return 1.0  # Mixed or unknown = neutral
    
    def _generate_composite_description(self, regime: str, risk_bucket: str) -> str:
        """
        Generate human-readable composite sentiment description
        
        Args:
            regime: Combined regime (bullish/bearish/mixed/unknown)
            risk_bucket: Risk bucket (risk_on/neutral/caution/risk_off)
        
        Returns:
            Composite description string
        """
        # Map regime + risk to description
        descriptions = {
            ('bullish', 'risk_on'): 'Strong Bullish - Low Vol (Optimal)',
            ('bullish', 'neutral'): 'Bullish - Normal Vol',
            ('bullish', 'caution'): 'Bullish - Elevated Vol (Careful)',
            ('bullish', 'risk_off'): 'Bullish - High Vol (Defensive)',
            
            ('bearish', 'risk_on'): 'Bearish - Low Vol',
            ('bearish', 'neutral'): 'Bearish - Normal Vol',
            ('bearish', 'caution'): 'Bearish - Elevated Vol',
            ('bearish', 'risk_off'): 'Strong Bearish - High Vol (Risk Off)',
            
            ('mixed', 'risk_on'): 'Mixed/Choppy - Low Vol',
            ('mixed', 'neutral'): 'Mixed/Choppy - Normal Vol',
            ('mixed', 'caution'): 'Mixed/Choppy - Elevated Vol',
            ('mixed', 'risk_off'): 'Mixed/Choppy - High Vol',
        }
        
        key = (regime, risk_bucket)
        return descriptions.get(key, f'{regime.title()} - {risk_bucket.replace("_", " ").title()}')
    
    def _is_cache_valid(self) -> bool:
        """Check if cached result is still valid"""
        if self._cache_timestamp is None or not self._cache:
            return False
        
        age = datetime.now() - self._cache_timestamp
        return age < self._cache_duration
    
    def _get_default_result(self) -> Dict:
        """Return neutral result when calculation fails"""
        return {
            'spy_regime': 'unknown',
            'qqq_regime': 'unknown',
            'combined_regime': 'unknown',
            'alignment': False,
            'vol_ratio': None,
            'risk_bucket': 'neutral',
            'vol_multiplier': 1.00,
            'composite': 'Unknown - Using Neutral Parameters',
            'base_weight': 1.0,
            'final_weight': 1.0,
            'timestamp': datetime.now(),
            'spy_price': None,
            'qqq_price': None,
            'spy_atr': None
        }
    
    def clear_cache(self):
        """Clear all caches"""
        self._cache = {}
        self._cache_timestamp = None
        self.volatility_index.clear_cache()
        self.spy_qqq_analyzer.clear_cache()


# =============================================================================
# CONVENIENCE FUNCTION (For backward compatibility and ease of use)
# =============================================================================

def get_composite_sentiment(data_fetcher, config=None, use_cache: bool = True) -> Dict:
    """
    Convenience function to get composite sentiment without instantiating class
    
    Args:
        data_fetcher: Data fetcher object
        config: Optional config (will load from stock_analyzer.utils.config if None)
        use_cache: Whether to use caching
    
    Returns:
        Composite sentiment dict
    
    Example:
        >>> from stock_analyzer.market.sentiment_engine import get_composite_sentiment
        >>> sentiment = get_composite_sentiment(data_fetcher)
        >>> print(sentiment['final_weight'])
    """
    if config is None:
        from stock_analyzer.utils import config
    
    engine = SentimentEngine(config)
    return engine.get_composite_sentiment(data_fetcher, use_cache=use_cache)


# =============================================================================
# STANDALONE USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    """
    Test the composite sentiment engine standalone
    
    Usage:
        python stock_analyzer/market/sentiment_engine.py
    """
    print("="*70)
    print("COMPOSITE SENTIMENT ENGINE - STANDALONE TEST")
    print("="*70)
    
    from stock_analyzer.utils import config
    
    # Test 1: Weight calculation logic
    print("\nTEST 1: Weight Calculation Logic")
    print("-"*70)
    
    engine = SentimentEngine(config)
    
    test_cases = [
        # (regime, vol_mult, expected_base, expected_final, description)
        ('bullish', 1.10, 1.1, 1.21, 'Bullish aligned + low vol'),
        ('bearish', 0.80, 1.1, 0.88, 'Bearish aligned + high vol'),
        ('mixed', 1.00, 1.0, 1.00, 'Mixed + neutral vol'),
        ('bullish', 1.00, 1.1, 1.10, 'Bullish aligned + neutral vol'),
        ('mixed', 0.90, 1.0, 0.90, 'Mixed + elevated vol'),
    ]
    
    for regime, vol_mult, exp_base, exp_final, desc in test_cases:
        base = engine._calculate_base_weight(regime)
        final = round(base * vol_mult, 2)
        
        base_ok = "✓" if base == exp_base else "✗"
        final_ok = "✓" if final == exp_final else "✗"
        
        print(f"{base_ok}{final_ok} {desc}")
        print(f"   Regime: {regime:8s} → base={base:.2f} (expect {exp_base:.2f})")
        print(f"   Vol mult: {vol_mult:.2f} → final={final:.2f} (expect {exp_final:.2f})")
    
    # Test 2: Composite descriptions
    print("\nTEST 2: Composite Descriptions")
    print("-"*70)
    
    test_descriptions = [
        ('bullish', 'risk_on', 'Strong Bullish - Low Vol (Optimal)'),
        ('bearish', 'risk_off', 'Strong Bearish - High Vol (Risk Off)'),
        ('mixed', 'neutral', 'Mixed/Choppy - Normal Vol'),
    ]
    
    for regime, risk, expected in test_descriptions:
        result = engine._generate_composite_description(regime, risk)
        status = "✓" if result == expected else "✗"
        print(f"{status} {regime}/{risk} → {result}")
    
    print("\n" + "="*70)
    print("COMPOSITE SENTIMENT ENGINE TESTS COMPLETE")
    print("="*70)
    print("\nREADY FOR INTEGRATION:")
    print("  - Import: from stock_analyzer.market.sentiment_engine import get_composite_sentiment")
    print("  - Usage: sentiment = get_composite_sentiment(data_fetcher)")
    print("  - Or: engine = SentimentEngine(config)")
    print("        sentiment = engine.get_composite_sentiment(data_fetcher)")
    print("="*70)