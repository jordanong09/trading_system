"""
MVP 4.0 Technical Indicators
- ATR(14D) for zone width calculation
- EMA20(1D) as primary dynamic S/R
- SMA50/100/200(1D) for trend and S/R seeds
- EMA20 slope gate (ATR-normalized)
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional


class TechnicalIndicators:
    """
    Calculate technical indicators for swing trading system
    All calculations use daily timeframe unless specified
    """
    
    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> float:
        """
        Calculate Average True Range (ATR)
        
        Args:
            df: DataFrame with OHLC data
            period: ATR period (default 14 days)
            
        Returns:
            Current ATR value
        """
        if len(df) < period + 1:
            return None
        
        # True Range = max(high-low, abs(high-prev_close), abs(low-prev_close))
        high = df['High'].values
        low = df['Low'].values
        close = df['Close'].values
        
        tr = np.zeros(len(df))
        
        for i in range(1, len(df)):
            hl = high[i] - low[i]
            hc = abs(high[i] - close[i-1])
            lc = abs(low[i] - close[i-1])
            tr[i] = max(hl, hc, lc)
        
        # ATR is the moving average of True Range
        atr = pd.Series(tr).rolling(window=period).mean().iloc[-1]
        
        return atr
    
    @staticmethod
    def calculate_ema(df: pd.DataFrame, period: int = 20, column: str = 'Close') -> pd.Series:
        """
        Calculate Exponential Moving Average
        
        Args:
            df: DataFrame with price data
            period: EMA period (default 20)
            column: Column to calculate EMA on (default 'Close')
            
        Returns:
            Series with EMA values
        """
        return df[column].ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_sma(df: pd.DataFrame, period: int, column: str = 'Close') -> pd.Series:
        """
        Calculate Simple Moving Average
        
        Args:
            df: DataFrame with price data
            period: SMA period (50, 100, 200)
            column: Column to calculate SMA on (default 'Close')
            
        Returns:
            Series with SMA values
        """
        return df[column].rolling(window=period).mean()
    
    @staticmethod
    def calculate_ema20_slope(df: pd.DataFrame, atr: float) -> Dict:
        """
        Calculate EMA20 slope normalized by ATR
        
        This is the "slope gate" that suppresses EMA20 signals when flat/choppy
        
        Formula:
            slope_atr = (EMA20_today - EMA20_yesterday) / ATR(14D)
            
        Categorization:
            |slope_atr| >= 0.10 → Strong trend (slope_factor = 1.2)
            0.05 <= |slope_atr| < 0.10 → Moderate trend (slope_factor = 1.0)
            |slope_atr| < 0.05 → Choppy/flat (slope_factor = 0.5)
        
        Args:
            df: DataFrame with daily OHLC data
            atr: ATR(14D) value
            
        Returns:
            Dict with slope metrics
        """
        if len(df) < 21 or atr is None or atr == 0:
            return {
                'ema20_current': None,
                'ema20_previous': None,
                'slope_points': None,
                'slope_atr': None,
                'slope_factor': 0.5,
                'slope_state': 'UNKNOWN'
            }
        
        ema20 = TechnicalIndicators.calculate_ema(df, period=20)
        
        ema20_today = ema20.iloc[-1]
        ema20_yesterday = ema20.iloc[-2]
        
        # Calculate slope in price points
        slope_points = ema20_today - ema20_yesterday
        
        # Normalize by ATR
        slope_atr = slope_points / atr
        
        # Determine slope factor
        abs_slope = abs(slope_atr)
        
        if abs_slope >= 0.10:
            slope_factor = 1.2
            slope_state = 'STRONG'
        elif abs_slope >= 0.05:
            slope_factor = 1.0
            slope_state = 'MODERATE'
        else:
            slope_factor = 0.5
            slope_state = 'CHOPPY'
        
        return {
            'ema20_current': ema20_today,
            'ema20_previous': ema20_yesterday,
            'slope_points': slope_points,
            'slope_atr': slope_atr,
            'slope_factor': slope_factor,
            'slope_state': slope_state,
            'direction': 'BULLISH' if slope_points > 0 else 'BEARISH' if slope_points < 0 else 'FLAT'
        }
    
    @staticmethod
    def calculate_all_indicators(df: pd.DataFrame) -> Dict:
        """
        Calculate all indicators needed for zone engine
        
        Args:
            df: DataFrame with daily OHLC data (minimum 60 bars recommended)
            
        Returns:
            Dict with all indicator values
        """
        if len(df) < 20:
            return {'error': 'Insufficient data', 'min_bars_needed': 20}
        
        # Current price
        current_price = df.iloc[-1]['Close']
        
        # ATR(14D)
        atr = TechnicalIndicators.calculate_atr(df, period=14)
        
        # EMA20(1D)
        ema20_series = TechnicalIndicators.calculate_ema(df, period=20)
        ema20 = ema20_series.iloc[-1] if len(ema20_series) > 0 else None
        
        # EMA20 slope
        ema20_slope = TechnicalIndicators.calculate_ema20_slope(df, atr)
        
        # SMAs
        sma50 = None
        sma100 = None
        sma200 = None
        
        if len(df) >= 50:
            sma50_series = TechnicalIndicators.calculate_sma(df, period=50)
            sma50 = sma50_series.iloc[-1]
        
        if len(df) >= 100:
            sma100_series = TechnicalIndicators.calculate_sma(df, period=100)
            sma100 = sma100_series.iloc[-1]
        
        if len(df) >= 200:
            sma200_series = TechnicalIndicators.calculate_sma(df, period=200)
            sma200 = sma200_series.iloc[-1]
        
        # Check MA stack alignment
        stack_aligned = False
        if all(v is not None for v in [ema20, sma50]):
            # Bullish stack: Price > EMA20 > SMA50
            if current_price > ema20 > sma50:
                stack_aligned = True
            # Bearish stack: Price < EMA20 < SMA50
            elif current_price < ema20 < sma50:
                stack_aligned = True
        
        return {
            'current_price': current_price,
            'atr14d': atr,
            'ema20': ema20,
            'ema20_slope': ema20_slope,
            'sma50': sma50,
            'sma100': sma100,
            'sma200': sma200,
            'stack_aligned': stack_aligned,
            'data_points': len(df)
        }
    
    @staticmethod
    def calculate_relative_volume(candle: pd.Series, recent_candles: pd.DataFrame) -> float:
        """
        Calculate relative volume for current candle
        
        RV = Current Volume / Average Volume (last 20 bars)
        
        Args:
            candle: Current candle (Series with Volume)
            recent_candles: Last 20 candles for average
            
        Returns:
            Relative volume ratio
        """
        if len(recent_candles) < 5:
            return 1.0
        
        current_volume = candle['Volume']
        avg_volume = recent_candles['Volume'].mean()
        
        if avg_volume == 0:
            return 1.0
        
        return current_volume / avg_volume
    
    @staticmethod
    def is_sma_rising(df: pd.DataFrame, period: int, lookback: int = 3) -> bool:
        """
        Check if SMA is rising over recent bars
        
        Args:
            df: DataFrame with daily data
            period: SMA period (50, 100, 200)
            lookback: Number of bars to check (default 3)
            
        Returns:
            True if SMA is rising
        """
        if len(df) < period + lookback:
            return False
        
        sma = TechnicalIndicators.calculate_sma(df, period)
        recent_sma = sma.iloc[-lookback:]
        
        # Check if generally rising
        return recent_sma.iloc[-1] > recent_sma.iloc[0]


# Quick test function
def test_indicators():
    """Test indicator calculations with sample data"""
    
    # Create sample data
    dates = pd.date_range('2025-09-01', periods=60, freq='D')
    np.random.seed(42)
    
    # Simulated price trend with volatility
    price = 100
    prices = [price]
    for _ in range(59):
        change = np.random.randn() * 2
        price = price + change
        prices.append(price)
    
    df = pd.DataFrame({
        'Date': dates,
        'Open': prices,
        'High': [p * 1.01 for p in prices],
        'Low': [p * 0.99 for p in prices],
        'Close': prices,
        'Volume': np.random.randint(1000000, 5000000, 60)
    })
    
    print("🧪 Testing Technical Indicators")
    print("=" * 60)
    
    indicators = TechnicalIndicators.calculate_all_indicators(df)
    
    print(f"\n📊 Results:")
    print(f"   Current Price: ${indicators['current_price']:.2f}")
    print(f"   ATR(14D): ${indicators['atr14d']:.2f}")
    print(f"   EMA20: ${indicators['ema20']:.2f}" if indicators['ema20'] else "   EMA20: N/A")
    print(f"   SMA50: ${indicators['sma50']:.2f}" if indicators['sma50'] else "   SMA50: N/A")
    print(f"   SMA100: ${indicators['sma100']:.2f}" if indicators['sma100'] else "   SMA100: N/A")
    print(f"   SMA200: ${indicators['sma200']:.2f}" if indicators['sma200'] else "   SMA200: N/A")
    
    print(f"\n📈 EMA20 Slope Analysis:")
    slope = indicators['ema20_slope']
    print(f"   Slope (ATR): {slope['slope_atr']:.4f}")
    print(f"   Slope Factor: {slope['slope_factor']}")
    print(f"   State: {slope['slope_state']}")
    print(f"   Direction: {slope['direction']}")
    
    print(f"\n✅ Stack Aligned: {indicators['stack_aligned']}")
    print(f"📏 Data Points: {indicators['data_points']}")
    
    print("\n✅ All indicators calculated successfully!")


if __name__ == "__main__":
    test_indicators()
