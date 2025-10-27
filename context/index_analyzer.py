# modules/index_regime.py - SPY/QQQ Market Regime Detection
"""
MVP 4.0 Index Regime Module
- Fetches SPY & QQQ data
- Calculates EMA20 & SMA50 for indices
- Determines regime (bullish/bearish/neutral)
- Provides market context for signal filtering
"""

import pandas as pd
from typing import Dict, Tuple
from indicators.technical_indicators import TechnicalIndicators


class IndexRegime:
    """
    Analyze SPY and QQQ to determine market regime
    """
    
    def __init__(self, data_fetcher, cache_manager=None):
        """
        Initialize index regime analyzer
        
        Args:
            data_fetcher: AlphaVantageAPI instance for fetching index data
        """
        self.data_fetcher = data_fetcher
        self.spy_symbol = 'SPY'
        self.qqq_symbol = 'QQQ'
        self.cache_manager = cache_manager  # NEW

        
        # Cache for index data (refresh every 4 hours)
        self.spy_data = None
        self.qqq_data = None
        self.last_refresh = None
    
    def fetch_index_data(self, force_refresh: bool = False) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Fetch daily data for SPY and QQQ
        
        Args:
            force_refresh: Force refresh even if cached
            
        Returns:
            Tuple of (spy_df, qqq_df)
        """
        if self.cache_manager:
                spy_df = self.cache_manager.get_or_fetch_daily(
                    self.spy_symbol,
                    lambda s: self.data_fetcher.fetch_daily_data(s),
                    force_refresh=force_refresh
                )
                qqq_df = self.cache_manager.get_or_fetch_daily(
                    self.qqq_symbol,
                    lambda s: self.data_fetcher.fetch_daily_data(s),
                    force_refresh=force_refresh
                )
        else:
                # Fallback to direct fetch (OLD way)
                spy_df = self.data_fetcher.fetch_daily_data(self.spy_symbol)
                qqq_df = self.data_fetcher.fetch_daily_data(self.qqq_symbol)
        
        # Cache the data
        self.spy_data = spy_df
        self.qqq_data = qqq_df
        
        return spy_df, qqq_df
    
    def calculate_regime(self, df: pd.DataFrame, symbol: str) -> Dict:
        """
        Calculate regime for an index
        
        Regime determination:
        - Bullish: Close > EMA20
        - Bearish: Close < EMA20
        - Neutral: Close within ±0.5% of EMA20
        
        Args:
            df: DataFrame with daily OHLCV data
            symbol: Index symbol (SPY or QQQ)
            
        Returns:
            Dict with regime information
        """
        if df is None or df.empty or len(df) < 20:
            return {
                'symbol': symbol,
                'regime': 'unknown',
                'current_price': None,
                'ema20': None,
                'sma50': None,
                'error': 'insufficient_data'
            }
        
        # Calculate indicators
        indicators = TechnicalIndicators.calculate_all_indicators(df)
        
        current_price = indicators['current_price']
        ema20 = indicators['ema20']
        sma50 = indicators['sma50']
        
        if ema20 is None:
            return {
                'symbol': symbol,
                'regime': 'unknown',
                'current_price': current_price,
                'ema20': None,
                'sma50': sma50,
                'error': 'ema20_calculation_failed'
            }
        
        # Determine regime based on EMA20
        distance_pct = ((current_price - ema20) / ema20) * 100
        
        if distance_pct > 0.5:
            regime = 'bullish'
        elif distance_pct < -0.5:
            regime = 'bearish'
        else:
            regime = 'neutral'
        
        # Determine trend based on SMA50
        if sma50 is not None:
            if current_price > sma50:
                trend = 'bullish'
            else:
                trend = 'bearish'
        else:
            trend = 'unknown'
        
        return {
            'symbol': symbol,
            'regime': regime,
            'trend': trend,
            'current_price': current_price,
            'ema20': ema20,
            'sma50': sma50,
            'distance_from_ema20': distance_pct,
            'above_ema20': current_price > ema20,
            'above_sma50': current_price > sma50 if sma50 else None
        }
    
    def get_market_regime(self, force_refresh: bool = False) -> Dict:
        """
        Get complete market regime analysis
        
        Returns:
            Dict with SPY and QQQ regimes plus overall assessment
        """
        # Fetch index data
        spy_df, qqq_df = self.fetch_index_data(force_refresh)
        
        # Calculate regimes
        spy_regime = self.calculate_regime(spy_df, 'SPY')
        qqq_regime = self.calculate_regime(qqq_df, 'QQQ')
        
        # Determine overall market regime
        overall_regime = self._determine_overall_regime(spy_regime, qqq_regime)
        
        return {
            'spy': spy_regime,
            'qqq': qqq_regime,
            'overall': overall_regime,
            'timestamp': pd.Timestamp.now().isoformat()
        }
    
    def _determine_overall_regime(self, spy: Dict, qqq: Dict) -> str:
        """
        Determine overall market regime from SPY and QQQ
        
        Logic:
        - Both bullish → 'bullish'
        - Both bearish → 'bearish'
        - Mixed → 'neutral'
        - Any unknown → 'unknown'
        
        Args:
            spy: SPY regime dict
            qqq: QQQ regime dict
            
        Returns:
            Overall regime string
        """
        spy_regime = spy.get('regime', 'unknown')
        qqq_regime = qqq.get('regime', 'unknown')
        
        if spy_regime == 'unknown' or qqq_regime == 'unknown':
            return 'unknown'
        
        if spy_regime == 'bullish' and qqq_regime == 'bullish':
            return 'bullish'
        
        if spy_regime == 'bearish' and qqq_regime == 'bearish':
            return 'bearish'
        
        return 'neutral'
    
    def check_index_alignment(self, signal_side: str, market_regime: Dict) -> Dict:
        """
        Check if signal aligns with market regime
        
        Used for confluence scoring
        
        Args:
            signal_side: 'long' or 'short'
            market_regime: Market regime dict from get_market_regime()
            
        Returns:
            Dict with alignment status
        """
        spy_regime = market_regime['spy']['regime']
        qqq_regime = market_regime['qqq']['regime']
        overall = market_regime['overall']
        
        signal_side = signal_side.lower()
        
        if signal_side == 'long':
            # For longs, prefer bullish indices
            aligned_count = 0
            if spy_regime == 'bullish':
                aligned_count += 1
            if qqq_regime == 'bullish':
                aligned_count += 1
            
            if aligned_count == 2:
                alignment = 'strong'
                score = 2.0
            elif aligned_count == 1:
                alignment = 'partial'
                score = 1.0
            else:
                alignment = 'against'
                score = 0.0
        
        elif signal_side == 'short':
            # For shorts, prefer bearish indices
            aligned_count = 0
            if spy_regime == 'bearish':
                aligned_count += 1
            if qqq_regime == 'bearish':
                aligned_count += 1
            
            if aligned_count == 2:
                alignment = 'strong'
                score = 2.0
            elif aligned_count == 1:
                alignment = 'partial'
                score = 1.0
            else:
                alignment = 'against'
                score = 0.0
        
        else:
            alignment = 'unknown'
            score = 0.0
        
        return {
            'alignment': alignment,
            'score': score,
            'spy_regime': spy_regime,
            'qqq_regime': qqq_regime,
            'overall_regime': overall,
            'suppress_alert': score == 0.0  # Suppress if against market
        }
    
    def format_regime_summary(self, market_regime: Dict) -> str:
        """
        Format market regime as readable string
        
        Args:
            market_regime: Market regime dict
            
        Returns:
            Formatted string
        """
        spy = market_regime['spy']
        qqq = market_regime['qqq']
        overall = market_regime['overall']
        
        lines = []
        lines.append(f"📊 Market Regime: {overall.upper()}")
        # Handle None values gracefully
        spy_price = spy['current_price'] if spy['current_price'] is not None else 0.0
        qqq_price = qqq['current_price'] if qqq['current_price'] is not None else 0.0

        lines.append(f"   SPY: {spy['regime'].upper()} (${spy_price:.2f})")
        lines.append(f"   QQQ: {qqq['regime'].upper()} (${qqq_price:.2f})")
        
        return "\n".join(lines)


# Quick test function
def test_index_regime():
    """Test index regime detector"""
    from data.data_fetcher import AlphaVantageAPI
    import config
    
    print("🧪 Testing Index Regime Detector")
    print("=" * 60)
    
    # Initialize API and regime detector
    api = AlphaVantageAPI(config.ALPHA_VANTAGE_API_KEY)
    regime_detector = IndexRegime(api)
    
    # Get market regime
    print("\n📊 Fetching market regime...")
    market_regime = regime_detector.get_market_regime()
    
    # Print summary
    print("\n" + regime_detector.format_regime_summary(market_regime))
    
    # Test alignment for long signal
    print("\n🔍 Testing alignment for LONG signal:")
    alignment = regime_detector.check_index_alignment('long', market_regime)
    print(f"   Alignment: {alignment['alignment'].upper()}")
    print(f"   Score: {alignment['score']}/2")
    print(f"   Suppress: {alignment['suppress_alert']}")
    
    # Test alignment for short signal
    print("\n🔍 Testing alignment for SHORT signal:")
    alignment = regime_detector.check_index_alignment('short', market_regime)
    print(f"   Alignment: {alignment['alignment'].upper()}")
    print(f"   Score: {alignment['score']}/2")
    print(f"   Suppress: {alignment['suppress_alert']}")
    
    # Detailed breakdown
    print("\n📈 Detailed SPY Analysis:")
    spy = market_regime['spy']
    print(f"   Price: ${spy['current_price']:.2f}")
    print(f"   EMA20: ${spy['ema20']:.2f}")
    print(f"   SMA50: ${spy['sma50']:.2f}" if spy['sma50'] else "   SMA50: N/A")
    print(f"   Distance from EMA20: {spy['distance_from_ema20']:+.2f}%")
    
    print("\n📈 Detailed QQQ Analysis:")
    qqq = market_regime['qqq']
    print(f"   Price: ${qqq['current_price']:.2f}")
    print(f"   EMA20: ${qqq['ema20']:.2f}")
    print(f"   SMA50: ${qqq['sma50']:.2f}" if qqq['sma50'] else "   SMA50: N/A")
    print(f"   Distance from EMA20: {qqq['distance_from_ema20']:+.2f}%")
    
    print("\n✅ Index regime test complete!")


if __name__ == "__main__":
    test_index_regime()
