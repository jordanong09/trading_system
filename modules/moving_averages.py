# modules/moving_averages.py
"""
Moving Averages Module for MPIS - AlphaVantage API Version
Analyzes MA data fetched from AlphaVantage API (no local calculation needed)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class MovingAverages:
    """
    Analyze moving averages for pattern confluence
    
    NOTE: This module does NOT calculate MAs. It expects MA values
    to be provided from AlphaVantage API via alphavantage_client.py
    """
    
    def __init__(self, config: dict):
        """
        Initialize with configuration
        
        Args:
            config: Dictionary with MA settings (thresholds, not periods)
        """
        self.config = config
        
        # Confluence thresholds (configurable)
        self.sr_proximity_pct = config.get('MA_SR_PROXIMITY_PCT', 2.0)  # Within 2%
        self.trend_alignment_min = config.get('TREND_ALIGNMENT_MIN', 3)  # 3 of 4 MAs
        
        # MA names (for reference only - AlphaVantage provides these)
        self.ma_names = ['EMA_20', 'SMA_50', 'SMA_100', 'SMA_200']
    
    # ========================================================================
    # TREND ANALYSIS - Works with AlphaVantage data
    # ========================================================================
    
    def get_trend_analysis(self, stock_data: Dict) -> Dict:
        """
        Analyze trend based on price position relative to MAs
        
        Args:
            stock_data: Dictionary from alphavantage_client.get_stock_data_with_indicators()
                Expected keys: 'close', 'ema_20', 'sma_50', 'sma_100', 'sma_200'
            
        Returns:
            Dictionary with comprehensive trend analysis
        """
        
        # Extract price and MA values from AlphaVantage data
        price = stock_data.get('close')
        ema_20 = stock_data.get('ema_20')
        sma_50 = stock_data.get('sma_50')
        sma_100 = stock_data.get('sma_100')
        sma_200 = stock_data.get('sma_200')
        
        # Validation
        if price is None:
            return {'error': 'No price data available'}
        
        # Check for missing MAs
        missing_mas = []
        if ema_20 is None:
            missing_mas.append('EMA_20')
        if sma_50 is None:
            missing_mas.append('SMA_50')
        if sma_100 is None:
            missing_mas.append('SMA_100')
        if sma_200 is None:
            missing_mas.append('SMA_200')
        
        if missing_mas:
            return {
                'error': f'Missing MA data: {missing_mas}',
                'primary_trend': 'UNKNOWN'
            }
        
        # Price position relative to each MA
        above_ema_20 = price > ema_20
        above_sma_50 = price > sma_50
        above_sma_100 = price > sma_100
        above_sma_200 = price > sma_200
        
        # Calculate distance from MAs (percentage)
        dist_ema_20 = ((price - ema_20) / ema_20 * 100)
        dist_sma_50 = ((price - sma_50) / sma_50 * 100)
        dist_sma_100 = ((price - sma_100) / sma_100 * 100)
        dist_sma_200 = ((price - sma_200) / sma_200 * 100)
        
        # Determine primary trend (based on EMA20 - most reactive)
        primary_trend = 'BULLISH' if above_ema_20 else 'BEARISH'
        
        # Count bullish alignments
        bullish_mas = sum([above_ema_20, above_sma_50, above_sma_100, above_sma_200])
        
        # Trend strength
        if bullish_mas >= 4:
            trend_strength = 'VERY_STRONG_BULL'
        elif bullish_mas == 3:
            trend_strength = 'STRONG_BULL'
        elif bullish_mas == 2:
            trend_strength = 'NEUTRAL'
        elif bullish_mas == 1:
            trend_strength = 'STRONG_BEAR'
        else:
            trend_strength = 'VERY_STRONG_BEAR'
        
        return {
            'symbol': stock_data.get('symbol'),
            'price': price,
            'timestamp': stock_data.get('timestamp'),
            
            # MA values (from AlphaVantage)
            'ema_20': ema_20,
            'sma_50': sma_50,
            'sma_100': sma_100,
            'sma_200': sma_200,
            
            # Position relative to MAs
            'above_ema_20': above_ema_20,
            'above_sma_50': above_sma_50,
            'above_sma_100': above_sma_100,
            'above_sma_200': above_sma_200,
            
            # Distance from MAs (%)
            'distance_ema_20_pct': dist_ema_20,
            'distance_sma_50_pct': dist_sma_50,
            'distance_sma_100_pct': dist_sma_100,
            'distance_sma_200_pct': dist_sma_200,
            
            # Trend assessment
            'primary_trend': primary_trend,
            'trend_strength': trend_strength,
            'bullish_ma_count': bullish_mas,
            'bearish_ma_count': 4 - bullish_mas
        }
    
    # ========================================================================
    # SUPPORT/RESISTANCE LEVELS
    # ========================================================================
    
    def get_ma_support_resistance(self, trend_analysis: Dict) -> Dict:
        """
        Identify which MAs are acting as support or resistance
        
        Args:
            trend_analysis: Output from get_trend_analysis()
            
        Returns:
            Dictionary with nearest support and resistance levels
        """
        price = trend_analysis.get('price')
        if price is None:
            return {'nearest_support': None, 'nearest_resistance': None}
        
        # Collect all MAs with their positions
        mas = []
        for ma_name in ['ema_20', 'sma_50', 'sma_100', 'sma_200']:
            ma_value = trend_analysis.get(ma_name)
            if ma_value is not None and not pd.isna(ma_value):
                mas.append({
                    'name': ma_name.upper(),
                    'value': ma_value,
                    'distance': abs(price - ma_value),
                    'distance_pct': abs(price - ma_value) / price * 100,
                    'position': 'below' if ma_value < price else 'above'
                })
        
        if not mas:
            return {'nearest_support': None, 'nearest_resistance': None}
        
        # Find nearest support (MA below price)
        supports = [m for m in mas if m['position'] == 'below']
        nearest_support = min(supports, key=lambda x: x['distance']) if supports else None
        
        # Find nearest resistance (MA above price)
        resistances = [m for m in mas if m['position'] == 'above']
        nearest_resistance = min(resistances, key=lambda x: x['distance']) if resistances else None
        
        return {
            'nearest_support': nearest_support,
            'nearest_resistance': nearest_resistance,
            'all_supports': sorted(supports, key=lambda x: x['distance']) if supports else [],
            'all_resistances': sorted(resistances, key=lambda x: x['distance']) if resistances else []
        }
    
    # ========================================================================
    # CONFLUENCE SCORING - Core Logic
    # ========================================================================
    
    def evaluate_pattern_confluence(
        self, 
        pattern_bias: str, 
        trend_analysis: Dict
    ) -> Dict:
        """
        Evaluate if pattern aligns with MA-based trend
        This is the CORE confluence scoring for MAs
        
        Args:
            pattern_bias: "BULLISH" or "BEARISH" from pattern detection
            trend_analysis: Output from get_trend_analysis()
            
        Returns:
            Dictionary with confluence score and detailed reasons
        """
        score = 0
        max_score = 5
        reasons = []
        
        primary_trend = trend_analysis.get('primary_trend', 'UNKNOWN')
        
        if primary_trend == 'UNKNOWN':
            return {
                'confluence_score': 0,
                'max_score': max_score,
                'percentage': 0,
                'recommendation': 'INSUFFICIENT_DATA',
                'reasons': ['Not enough MA data from AlphaVantage']
            }
        
        # ====================================================================
        # FACTOR 1: EMA20 Alignment (Most Important - 2 points)
        # ====================================================================
        if pattern_bias == primary_trend:
            score += 2
            reasons.append(f"✅ Pattern aligns with {primary_trend} trend (EMA20)")
        else:
            reasons.append(f"❌ Pattern conflicts with {primary_trend} trend (EMA20)")
        
        # ====================================================================
        # FACTOR 2: SMA200 Position (Long-term context - 1 point)
        # ====================================================================
        above_sma_200 = trend_analysis.get('above_sma_200')
        if above_sma_200 is not None:
            if pattern_bias == "BULLISH" and above_sma_200:
                score += 1
                reasons.append("✅ Price above SMA200 (long-term bullish)")
            elif pattern_bias == "BEARISH" and not above_sma_200:
                score += 1
                reasons.append("✅ Price below SMA200 (long-term bearish)")
            else:
                reasons.append("⚠️  Price position conflicts with SMA200")
        
        # ====================================================================
        # FACTOR 3: Support/Resistance Proximity (1 point)
        # ====================================================================
        ma_levels = self.get_ma_support_resistance(trend_analysis)
        
        if pattern_bias == "BULLISH":
            if ma_levels.get('nearest_support'):
                support = ma_levels['nearest_support']
                distance_pct = support['distance_pct']
                
                if distance_pct < self.sr_proximity_pct:
                    score += 1
                    reasons.append(
                        f"✅ Near {support['name']} support "
                        f"(${support['value']:.2f}, {distance_pct:.1f}% away)"
                    )
        
        elif pattern_bias == "BEARISH":
            if ma_levels.get('nearest_resistance'):
                resistance = ma_levels['nearest_resistance']
                distance_pct = resistance['distance_pct']
                
                if distance_pct < self.sr_proximity_pct:
                    score += 1
                    reasons.append(
                        f"✅ Near {resistance['name']} resistance "
                        f"(${resistance['value']:.2f}, {distance_pct:.1f}% away)"
                    )
        
        # ====================================================================
        # FACTOR 4: Multiple MA Alignment (Trend strength - 1 point)
        # ====================================================================
        bullish_mas = trend_analysis.get('bullish_ma_count', 0)
        
        if pattern_bias == "BULLISH" and bullish_mas >= self.trend_alignment_min:
            score += 1
            reasons.append(
                f"✅ Price above {bullish_mas}/4 moving averages (strong uptrend)"
            )
        elif pattern_bias == "BEARISH" and bullish_mas <= (4 - self.trend_alignment_min):
            score += 1
            bearish_count = 4 - bullish_mas
            reasons.append(
                f"✅ Price below {bearish_count}/4 moving averages (strong downtrend)"
            )
        else:
            reasons.append(f"⚠️  Mixed MA alignment ({bullish_mas}/4 bullish)")
        
        # ====================================================================
        # Calculate final percentage and recommendation
        # ====================================================================
        percentage = (score / max_score) * 100
        
        if percentage >= 80:
            recommendation = "STRONG_SIGNAL"
        elif percentage >= 60:
            recommendation = "GOOD_SIGNAL"
        elif percentage >= 40:
            recommendation = "MODERATE_SIGNAL"
        else:
            recommendation = "WEAK_SIGNAL"
        
        return {
            'confluence_score': score,
            'max_score': max_score,
            'percentage': percentage,
            'recommendation': recommendation,
            'reasons': reasons,
            'ma_contribution': score
        }
    
    # ========================================================================
    # BATCH ANALYSIS - For multiple stocks
    # ========================================================================
    
    def analyze_batch(self, stock_data_list: List[Dict]) -> List[Dict]:
        """
        Analyze MA confluence for batch of stocks from AlphaVantage
        
        Args:
            stock_data_list: List of dicts from alphavantage_client.batch_fetch_stocks()
            
        Returns:
            List of trend analysis results
        """
        results = []
        
        for stock_data in stock_data_list:
            symbol = stock_data.get('symbol', 'UNKNOWN')
            
            try:
                trend = self.get_trend_analysis(stock_data)
                
                if 'error' not in trend:
                    results.append(trend)
                else:
                    print(f"⚠️  {symbol}: {trend['error']}")
                    
            except Exception as e:
                print(f"❌ Error analyzing {symbol}: {e}")
                continue
        
        return results
    
    # ========================================================================
    # FORMATTING & DISPLAY
    # ========================================================================
    
    def format_trend_summary(self, trend_analysis: Dict) -> str:
        """
        Format trend analysis for display in alerts
        
        Args:
            trend_analysis: Output from get_trend_analysis()
            
        Returns:
            Formatted string for Telegram/console output
        """
        if not trend_analysis or 'error' in trend_analysis:
            return "No trend data available"
        
        lines = []
        
        # Header
        price = trend_analysis['price']
        trend = trend_analysis['primary_trend']
        strength = trend_analysis['trend_strength']
        
        lines.append(f"📊 Price: ${price:.2f}")
        lines.append(f"📈 Trend: {trend} ({strength})")
        lines.append("")
        
        # Moving averages with position indicators
        mas = [
            ('EMA20', 'ema_20', 'above_ema_20'),
            ('SMA50', 'sma_50', 'above_sma_50'),
            ('SMA100', 'sma_100', 'above_sma_100'),
            ('SMA200', 'sma_200', 'above_sma_200')
        ]
        
        for label, value_key, position_key in mas:
            ma_value = trend_analysis.get(value_key)
            if ma_value is not None:
                above = trend_analysis.get(position_key)
                symbol = "↑" if above else "↓"
                distance = abs(trend_analysis.get(f'distance_{value_key}_pct', 0))
                lines.append(f"   {label}: ${ma_value:.2f} {symbol} ({distance:.1f}%)")
        
        # Support/Resistance
        ma_levels = self.get_ma_support_resistance(trend_analysis)
        
        if ma_levels.get('nearest_support'):
            support = ma_levels['nearest_support']
            lines.append("")
            lines.append(
                f"🟢 Support: {support['name']} @ ${support['value']:.2f} "
                f"({support['distance_pct']:.1f}% below)"
            )
        
        if ma_levels.get('nearest_resistance'):
            resistance = ma_levels['nearest_resistance']
            lines.append(
                f"🔴 Resistance: {resistance['name']} @ ${resistance['value']:.2f} "
                f"({resistance['distance_pct']:.1f}% above)"
            )
        
        return "\n".join(lines)
    
    # ========================================================================
    # VALIDATION
    # ========================================================================
    
    def validate_ma_data(self, stock_data: Dict) -> Dict:
        """
        Validate that AlphaVantage provided all required MA data
        
        Args:
            stock_data: Dictionary from AlphaVantage API
            
        Returns:
            Dictionary with validation results
        """
        issues = []
        warnings = []
        
        # Check for required fields
        required_fields = ['close', 'ema_20', 'sma_50', 'sma_100', 'sma_200']
        missing = [field for field in required_fields if stock_data.get(field) is None]
        
        if missing:
            issues.append(f"Missing fields from AlphaVantage: {missing}")
            return {'valid': False, 'issues': issues, 'warnings': warnings}
        
        # Check for reasonable values (MAs shouldn't be 0 or extremely different from price)
        price = stock_data.get('close')
        for ma_field in ['ema_20', 'sma_50', 'sma_100', 'sma_200']:
            ma_value = stock_data.get(ma_field)
            if ma_value == 0:
                warnings.append(f"{ma_field.upper()} is zero (unusual)")
            elif abs(ma_value - price) / price > 0.5:  # More than 50% away
                warnings.append(f"{ma_field.upper()} is {abs(ma_value - price) / price * 100:.1f}% from price (unusual)")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'data_source': 'AlphaVantage API',
            'all_mas_present': len(missing) == 0
        }


# ============================================================================
# USAGE EXAMPLE with AlphaVantage Client
# ============================================================================

if __name__ == "__main__":
    """
    Example usage with AlphaVantage API
    """
    
    # Sample configuration
    config = {
        'MA_SR_PROXIMITY_PCT': 2.0,
        'TREND_ALIGNMENT_MIN': 3
    }
    
    # Initialize
    ma = MovingAverages(config)
    
    # Example data structure from AlphaVantage
    # (This would come from alphavantage_client.get_stock_data_with_indicators())
    sample_stock_data = {
        'symbol': 'AAPL',
        'timestamp': '2024-10-21 15:00:00',
        'close': 187.50,
        'ema_20': 185.20,   # From AlphaVantage
        'sma_50': 180.50,   # From AlphaVantage
        'sma_100': 175.30,  # From AlphaVantage
        'sma_200': 170.00   # From AlphaVantage
    }
    
    print("MovingAverages module loaded successfully!")
    print("Works with AlphaVantage API - no local MA calculation needed")
    print("\nConfiguration:")
    print(f"  S/R Proximity: {ma.sr_proximity_pct}%")
    print(f"  Trend Alignment Minimum: {ma.trend_alignment_min}/4 MAs")
    print("\n✅ Ready to integrate with your AlphaVantage client!")