# modules/technical_indicators.py - Moving Averages & Indicators

import pandas as pd
import numpy as np
from typing import Dict, Tuple

class TechnicalIndicators:
    """Calculate technical indicators for confluence-based trading signals"""
    
    @staticmethod
    def calculate_ema(data: pd.Series, period: int) -> pd.Series:
        """
        Calculate Exponential Moving Average (EMA)
        More weight on recent prices - good for trend detection
        """
        return data.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_sma(data: pd.Series, period: int) -> pd.Series:
        """
        Calculate Simple Moving Average (SMA)
        Equal weight on all prices - good for support/resistance
        """
        return data.rolling(window=period).mean()
    
    @staticmethod
    def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all moving averages for the dataframe
        Requires columns: Date, Open, High, Low, Close, Volume
        """
        if len(df) < 200:
            print(f"   ⚠️  Warning: Only {len(df)} rows available. SMA200 may be incomplete.")
        
        # Calculate moving averages on Close price
        df['EMA_20'] = TechnicalIndicators.calculate_ema(df['Close'], 20)
        df['SMA_50'] = TechnicalIndicators.calculate_sma(df['Close'], 50)
        df['SMA_100'] = TechnicalIndicators.calculate_sma(df['Close'], 100)
        df['SMA_200'] = TechnicalIndicators.calculate_sma(df['Close'], 200)
        
        return df
    
    @staticmethod
    def get_trend_analysis(df: pd.DataFrame, index: int = -1) -> Dict:
        """
        Analyze trend based on price position relative to moving averages
        index: Row index to analyze (default -1 = most recent)
        """
        if index < 0:
            index = len(df) + index
        
        if index < 0 or index >= len(df):
            return {}
        
        current = df.iloc[index]
        price = current['Close']
        
        # Check if indicators exist
        if 'EMA_20' not in df.columns:
            return {}
        
        analysis = {
            'price': price,
            'ema_20': current.get('EMA_20', np.nan),
            'sma_50': current.get('SMA_50', np.nan),
            'sma_100': current.get('SMA_100', np.nan),
            'sma_200': current.get('SMA_200', np.nan),
            
            # Trend signals
            'above_ema_20': price > current.get('EMA_20', 0) if not pd.isna(current.get('EMA_20')) else None,
            'above_sma_50': price > current.get('SMA_50', 0) if not pd.isna(current.get('SMA_50')) else None,
            'above_sma_100': price > current.get('SMA_100', 0) if not pd.isna(current.get('SMA_100')) else None,
            'above_sma_200': price > current.get('SMA_200', 0) if not pd.isna(current.get('SMA_200')) else None,
            
            # Distance from moving averages (%)
            'distance_ema_20_pct': ((price - current.get('EMA_20', price)) / price * 100) if not pd.isna(current.get('EMA_20')) else None,
            'distance_sma_50_pct': ((price - current.get('SMA_50', price)) / price * 100) if not pd.isna(current.get('SMA_50')) else None,
            'distance_sma_100_pct': ((price - current.get('SMA_100', price)) / price * 100) if not pd.isna(current.get('SMA_100')) else None,
            'distance_sma_200_pct': ((price - current.get('SMA_200', price)) / price * 100) if not pd.isna(current.get('SMA_200')) else None,
        }
        
        # Overall trend determination
        analysis['primary_trend'] = TechnicalIndicators.determine_primary_trend(analysis)
        analysis['ma_support_resistance'] = TechnicalIndicators.find_nearest_support_resistance(analysis)
        
        return analysis
    
    @staticmethod
    def determine_primary_trend(analysis: Dict) -> str:
        """
        Determine primary trend based on EMA20 position
        EMA20 is the main trend indicator
        """
        if analysis.get('above_ema_20') is None:
            return "UNKNOWN"
        
        if analysis['above_ema_20']:
            return "BULLISH"  # Price above EMA20 = Long bias
        else:
            return "BEARISH"  # Price below EMA20 = Short bias
    
    @staticmethod
    def find_nearest_support_resistance(analysis: Dict) -> Dict:
        """
        Find nearest SMA acting as support (below) or resistance (above)
        These SMAs act as key levels for position trades
        """
        price = analysis['price']
        
        # Collect all SMAs with their values
        smas = []
        for ma in ['sma_50', 'sma_100', 'sma_200']:
            if analysis.get(ma) and not pd.isna(analysis[ma]):
                smas.append({
                    'name': ma.upper(),
                    'value': analysis[ma],
                    'distance': abs(price - analysis[ma]),
                    'position': 'below' if analysis[ma] < price else 'above'
                })
        
        if not smas:
            return {'nearest_support': None, 'nearest_resistance': None}
        
        # Find nearest support (MA below price)
        supports = [s for s in smas if s['position'] == 'below']
        nearest_support = min(supports, key=lambda x: x['distance']) if supports else None
        
        # Find nearest resistance (MA above price)
        resistances = [s for s in smas if s['position'] == 'above']
        nearest_resistance = min(resistances, key=lambda x: x['distance']) if resistances else None
        
        return {
            'nearest_support': nearest_support,
            'nearest_resistance': nearest_resistance
        }
    
    @staticmethod
    def evaluate_pattern_confluence(pattern_bias: str, trend_analysis: Dict) -> Dict:
        """
        Evaluate if candlestick pattern aligns with moving average trend
        
        pattern_bias: "BULLISH" or "BEARISH" from pattern detection
        trend_analysis: Output from get_trend_analysis()
        
        Returns: Confluence score and recommendation
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
                'reasons': ['Not enough data for indicators']
            }
        
        # 1. EMA20 alignment (most important - 2 points)
        if pattern_bias == primary_trend:
            score += 2
            reasons.append(f"✅ Pattern aligns with {primary_trend} trend (EMA20)")
        else:
            reasons.append(f"❌ Pattern conflicts with {primary_trend} trend (EMA20)")
        
        # 2. Price relative to SMA200 (1 point)
        if trend_analysis.get('above_sma_200') is not None:
            if pattern_bias == "BULLISH" and trend_analysis['above_sma_200']:
                score += 1
                reasons.append("✅ Price above SMA200 (long-term bullish)")
            elif pattern_bias == "BEARISH" and not trend_analysis['above_sma_200']:
                score += 1
                reasons.append("✅ Price below SMA200 (long-term bearish)")
            else:
                reasons.append("⚠️  Price position conflicts with SMA200")
        
        # 3. Support/Resistance proximity (1 point)
        ma_levels = trend_analysis.get('ma_support_resistance', {})
        
        if pattern_bias == "BULLISH":
            if ma_levels.get('nearest_support'):
                support = ma_levels['nearest_support']
                distance_pct = (trend_analysis['price'] - support['value']) / trend_analysis['price'] * 100
                if distance_pct < 2:  # Within 2% of support
                    score += 1
                    reasons.append(f"✅ Near {support['name']} support (${support['value']:.2f})")
        
        elif pattern_bias == "BEARISH":
            if ma_levels.get('nearest_resistance'):
                resistance = ma_levels['nearest_resistance']
                distance_pct = (resistance['value'] - trend_analysis['price']) / trend_analysis['price'] * 100
                if distance_pct < 2:  # Within 2% of resistance
                    score += 1
                    reasons.append(f"✅ Near {resistance['name']} resistance (${resistance['value']:.2f})")
        
        # 4. Multiple MA alignment (1 point)
        bullish_mas = sum([
            trend_analysis.get('above_ema_20', False),
            trend_analysis.get('above_sma_50', False),
            trend_analysis.get('above_sma_100', False),
            trend_analysis.get('above_sma_200', False)
        ])
        
        if pattern_bias == "BULLISH" and bullish_mas >= 3:
            score += 1
            reasons.append(f"✅ Price above {bullish_mas}/4 moving averages (strong uptrend)")
        elif pattern_bias == "BEARISH" and bullish_mas <= 1:
            score += 1
            reasons.append(f"✅ Price below {4-bullish_mas}/4 moving averages (strong downtrend)")
        
        # Calculate percentage and recommendation
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
            'reasons': reasons
        }
    
    @staticmethod
    def format_indicator_summary(trend_analysis: Dict) -> str:
        """Format indicator summary for display"""
        if not trend_analysis:
            return "No indicator data available"
        
        summary = []
        summary.append(f"📊 Price: ${trend_analysis['price']:.2f}")
        summary.append(f"📈 Trend: {trend_analysis['primary_trend']}")
        
        # Moving averages
        if not pd.isna(trend_analysis.get('ema_20')):
            ema_symbol = "↑" if trend_analysis['above_ema_20'] else "↓"
            summary.append(f"   EMA20: ${trend_analysis['ema_20']:.2f} {ema_symbol}")
        
        if not pd.isna(trend_analysis.get('sma_50')):
            sma50_symbol = "↑" if trend_analysis['above_sma_50'] else "↓"
            summary.append(f"   SMA50: ${trend_analysis['sma_50']:.2f} {sma50_symbol}")
        
        if not pd.isna(trend_analysis.get('sma_100')):
            sma100_symbol = "↑" if trend_analysis['above_sma_100'] else "↓"
            summary.append(f"   SMA100: ${trend_analysis['sma_100']:.2f} {sma100_symbol}")
        
        if not pd.isna(trend_analysis.get('sma_200')):
            sma200_symbol = "↑" if trend_analysis['above_sma_200'] else "↓"
            summary.append(f"   SMA200: ${trend_analysis['sma_200']:.2f} {sma200_symbol}")
        
        # Support/Resistance
        ma_levels = trend_analysis.get('ma_support_resistance', {})
        if ma_levels.get('nearest_support'):
            support = ma_levels['nearest_support']
            summary.append(f"🟢 Support: {support['name']} @ ${support['value']:.2f}")
        
        if ma_levels.get('nearest_resistance'):
            resistance = ma_levels['nearest_resistance']
            summary.append(f"🔴 Resistance: {resistance['name']} @ ${resistance['value']:.2f}")
        
        return "\n".join(summary)


# Usage: from modules.technical_indicators import TechnicalIndicators