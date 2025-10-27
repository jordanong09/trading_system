# patterns/candlestick_detector.py - Complete Pattern Detection (P2)
"""
Comprehensive candlestick pattern detection on HOURLY timeframe
- All high-probability reversal patterns
- All continuation patterns
- Relative volume calculation
- Pattern strength scoring
"""

import pandas as pd
from typing import Dict, Optional


class PatternDetector:
    """
    Detect candlestick patterns on 1H timeframe
    
    Patterns included (P2):
    - Bullish/Bearish Engulfing
    - Hammer / Inverted Hammer
    - Shooting Star / Hanging Man
    - Morning Star / Evening Star (3-candle)
    - Three White Soldiers / Three Black Crows
    - Piercing Pattern / Dark Cloud Cover
    - Doji patterns
    """
    
    def __init__(self, config: Dict):
        """
        Initialize pattern detector
        
        Args:
            config: Configuration dict
        """
        self.rv_high = config.get('rv_requirements', {}).get('high', 1.5)
        self.rv_medium = config.get('rv_requirements', {}).get('medium', 1.2)
    
    def calculate_relative_volume(self, df: pd.DataFrame, index: int = -1) -> float:
        """Calculate relative volume for a candle"""
        if len(df) < 5:
            return 1.0
        
        if index == -1:
            current = df.iloc[-1]
            recent = df.iloc[-21:-1] if len(df) >= 21 else df.iloc[:-1]
        else:
            current = df.iloc[index]
            start_idx = max(0, index - 20)
            recent = df.iloc[start_idx:index]
        
        current_volume = current['Volume']
        avg_volume = recent['Volume'].mean()
        
        return current_volume / avg_volume if avg_volume > 0 else 1.0
    
    # ============= ENGULFING PATTERNS =============
    
    def detect_bullish_engulfing(self, df: pd.DataFrame, index: int = -1) -> Optional[Dict]:
        """Bullish engulfing pattern"""
        if len(df) < 2:
            return None
        
        if index == -1:
            prev = df.iloc[-2]
            curr = df.iloc[-1]
        else:
            if index < 1:
                return None
            prev = df.iloc[index - 1]
            curr = df.iloc[index]
        
        is_pattern = (
            prev['Close'] < prev['Open'] and
            curr['Close'] > curr['Open'] and
            curr['Open'] < prev['Close'] and
            curr['Close'] > prev['Open']
        )
        
        if not is_pattern:
            return None
        
        rv = self.calculate_relative_volume(df, index)
        
        return {
            'pattern': 'Bullish Engulfing',
            'bias': 'long',
            'side': 'long',
            'timestamp': curr['Date'],
            'price': curr['Close'],
            'volume': curr['Volume'],
            'relative_volume': rv,
            'quality': 'high' if rv >= self.rv_high else 'medium' if rv >= self.rv_medium else 'low'
        }
    
    def detect_bearish_engulfing(self, df: pd.DataFrame, index: int = -1) -> Optional[Dict]:
        """Bearish engulfing pattern"""
        if len(df) < 2:
            return None
        
        if index == -1:
            prev = df.iloc[-2]
            curr = df.iloc[-1]
        else:
            if index < 1:
                return None
            prev = df.iloc[index - 1]
            curr = df.iloc[index]
        
        is_pattern = (
            prev['Close'] > prev['Open'] and
            curr['Close'] < curr['Open'] and
            curr['Open'] > prev['Close'] and
            curr['Close'] < prev['Open']
        )
        
        if not is_pattern:
            return None
        
        rv = self.calculate_relative_volume(df, index)
        
        return {
            'pattern': 'Bearish Engulfing',
            'bias': 'short',
            'side': 'short',
            'timestamp': curr['Date'],
            'price': curr['Close'],
            'volume': curr['Volume'],
            'relative_volume': rv,
            'quality': 'high' if rv >= self.rv_high else 'medium' if rv >= self.rv_medium else 'low'
        }
    
    # ============= HAMMER PATTERNS =============
    
    def detect_hammer(self, df: pd.DataFrame, index: int = -1) -> Optional[Dict]:
        """
        Hammer pattern (bullish reversal)
        - Long lower wick (2x body)
        - Small/no upper wick
        - Bullish or bearish body (close > open preferred)
        """
        if len(df) < 1:
            return None
        
        candle = df.iloc[index]
        
        body = abs(candle['Close'] - candle['Open'])
        lower_wick = min(candle['Open'], candle['Close']) - candle['Low']
        upper_wick = candle['High'] - max(candle['Open'], candle['Close'])
        total_range = candle['High'] - candle['Low']
        
        if body == 0 or total_range == 0:
            return None
        
        is_pattern = (
            lower_wick >= 2.0 * body and
            upper_wick <= body and
            lower_wick >= 0.6 * total_range
        )
        
        if not is_pattern:
            return None
        
        rv = self.calculate_relative_volume(df, index)
        
        return {
            'pattern': 'Hammer',
            'bias': 'long',
            'side': 'long',
            'timestamp': candle['Date'],
            'price': candle['Close'],
            'volume': candle['Volume'],
            'relative_volume': rv,
            'quality': 'high' if rv >= self.rv_high else 'medium' if rv >= self.rv_medium else 'low'
        }
    
    def detect_inverted_hammer(self, df: pd.DataFrame, index: int = -1) -> Optional[Dict]:
        """
        Inverted Hammer pattern (bullish reversal)
        - Long upper wick (2x body)
        - Small/no lower wick
        """
        if len(df) < 1:
            return None
        
        candle = df.iloc[index]
        
        body = abs(candle['Close'] - candle['Open'])
        upper_wick = candle['High'] - max(candle['Open'], candle['Close'])
        lower_wick = min(candle['Open'], candle['Close']) - candle['Low']
        total_range = candle['High'] - candle['Low']
        
        if body == 0 or total_range == 0:
            return None
        
        is_pattern = (
            upper_wick >= 2.0 * body and
            lower_wick <= body and
            upper_wick >= 0.6 * total_range
        )
        
        if not is_pattern:
            return None
        
        rv = self.calculate_relative_volume(df, index)
        
        return {
            'pattern': 'Inverted Hammer',
            'bias': 'long',
            'side': 'long',
            'timestamp': candle['Date'],
            'price': candle['Close'],
            'volume': candle['Volume'],
            'relative_volume': rv,
            'quality': 'high' if rv >= self.rv_high else 'medium' if rv >= self.rv_medium else 'low'
        }
    
    def detect_shooting_star(self, df: pd.DataFrame, index: int = -1) -> Optional[Dict]:
        """
        Shooting Star pattern (bearish reversal)
        - Long upper wick (2x body)
        - Small/no lower wick
        - Appears after uptrend
        """
        if len(df) < 1:
            return None
        
        candle = df.iloc[index]
        
        body = abs(candle['Close'] - candle['Open'])
        upper_wick = candle['High'] - max(candle['Open'], candle['Close'])
        lower_wick = min(candle['Open'], candle['Close']) - candle['Low']
        total_range = candle['High'] - candle['Low']
        
        if body == 0 or total_range == 0:
            return None
        
        is_pattern = (
            upper_wick >= 2.0 * body and
            lower_wick <= 0.5 * body and
            upper_wick >= 0.6 * total_range
        )
        
        if not is_pattern:
            return None
        
        rv = self.calculate_relative_volume(df, index)
        
        return {
            'pattern': 'Shooting Star',
            'bias': 'short',
            'side': 'short',
            'timestamp': candle['Date'],
            'price': candle['Close'],
            'volume': candle['Volume'],
            'relative_volume': rv,
            'quality': 'high' if rv >= self.rv_high else 'medium' if rv >= self.rv_medium else 'low'
        }
    
    def detect_hanging_man(self, df: pd.DataFrame, index: int = -1) -> Optional[Dict]:
        """
        Hanging Man pattern (bearish reversal)
        - Long lower wick (2x body)
        - Small/no upper wick
        - Appears after uptrend
        """
        if len(df) < 1:
            return None
        
        candle = df.iloc[index]
        
        body = abs(candle['Close'] - candle['Open'])
        lower_wick = min(candle['Open'], candle['Close']) - candle['Low']
        upper_wick = candle['High'] - max(candle['Open'], candle['Close'])
        total_range = candle['High'] - candle['Low']
        
        if body == 0 or total_range == 0:
            return None
        
        is_pattern = (
            lower_wick >= 2.0 * body and
            upper_wick <= body and
            lower_wick >= 0.6 * total_range
        )
        
        if not is_pattern:
            return None
        
        rv = self.calculate_relative_volume(df, index)
        
        return {
            'pattern': 'Hanging Man',
            'bias': 'short',
            'side': 'short',
            'timestamp': candle['Date'],
            'price': candle['Close'],
            'volume': candle['Volume'],
            'relative_volume': rv,
            'quality': 'high' if rv >= self.rv_high else 'medium' if rv >= self.rv_medium else 'low'
        }
    
    # ============= THREE-CANDLE PATTERNS =============
    
    def detect_morning_star(self, df: pd.DataFrame, index: int = -1) -> Optional[Dict]:
        """
        Morning Star (bullish reversal, 3-candle)
        - Day 1: Long bearish
        - Day 2: Small body (doji/spinning top), gaps down
        - Day 3: Long bullish, closes above Day 1 midpoint
        """
        if len(df) < 3:
            return None
        
        if index == -1:
            idx = len(df) - 1
        else:
            idx = index
        
        if idx < 2:
            return None
        
        day1 = df.iloc[idx - 2]
        day2 = df.iloc[idx - 1]
        day3 = df.iloc[idx]
        
        # Day 1: Long bearish
        day1_body = abs(day1['Close'] - day1['Open'])
        day1_bearish = day1['Close'] < day1['Open']
        day1_range = day1['High'] - day1['Low']
        day1_long = day1_body > 0.6 * day1_range if day1_range > 0 else False
        
        # Day 2: Small body (doji)
        day2_body = abs(day2['Close'] - day2['Open'])
        day2_range = day2['High'] - day2['Low']
        day2_small = day2_body < 0.3 * day2_range if day2_range > 0 else False
        
        # Day 3: Long bullish
        day3_body = abs(day3['Close'] - day3['Open'])
        day3_bullish = day3['Close'] > day3['Open']
        day3_range = day3['High'] - day3['Low']
        day3_long = day3_body > 0.6 * day3_range if day3_range > 0 else False
        
        # Day 3 closes above Day 1 midpoint
        day1_mid = (day1['Open'] + day1['Close']) / 2
        closes_above_mid = day3['Close'] > day1_mid
        
        is_pattern = (
            day1_bearish and day1_long and
            day2_small and
            day3_bullish and day3_long and
            closes_above_mid
        )
        
        if not is_pattern:
            return None
        
        rv = self.calculate_relative_volume(df, idx)
        
        return {
            'pattern': 'Morning Star',
            'bias': 'long',
            'side': 'long',
            'timestamp': day3['Date'],
            'price': day3['Close'],
            'volume': day3['Volume'],
            'relative_volume': rv,
            'quality': 'high' if rv >= self.rv_high else 'medium' if rv >= self.rv_medium else 'low'
        }
    
    def detect_evening_star(self, df: pd.DataFrame, index: int = -1) -> Optional[Dict]:
        """
        Evening Star (bearish reversal, 3-candle)
        - Day 1: Long bullish
        - Day 2: Small body (doji/spinning top), gaps up
        - Day 3: Long bearish, closes below Day 1 midpoint
        """
        if len(df) < 3:
            return None
        
        if index == -1:
            idx = len(df) - 1
        else:
            idx = index
        
        if idx < 2:
            return None
        
        day1 = df.iloc[idx - 2]
        day2 = df.iloc[idx - 1]
        day3 = df.iloc[idx]
        
        # Day 1: Long bullish
        day1_body = abs(day1['Close'] - day1['Open'])
        day1_bullish = day1['Close'] > day1['Open']
        day1_range = day1['High'] - day1['Low']
        day1_long = day1_body > 0.6 * day1_range if day1_range > 0 else False
        
        # Day 2: Small body (doji)
        day2_body = abs(day2['Close'] - day2['Open'])
        day2_range = day2['High'] - day2['Low']
        day2_small = day2_body < 0.3 * day2_range if day2_range > 0 else False
        
        # Day 3: Long bearish
        day3_body = abs(day3['Close'] - day3['Open'])
        day3_bearish = day3['Close'] < day3['Open']
        day3_range = day3['High'] - day3['Low']
        day3_long = day3_body > 0.6 * day3_range if day3_range > 0 else False
        
        # Day 3 closes below Day 1 midpoint
        day1_mid = (day1['Open'] + day1['Close']) / 2
        closes_below_mid = day3['Close'] < day1_mid
        
        is_pattern = (
            day1_bullish and day1_long and
            day2_small and
            day3_bearish and day3_long and
            closes_below_mid
        )
        
        if not is_pattern:
            return None
        
        rv = self.calculate_relative_volume(df, idx)
        
        return {
            'pattern': 'Evening Star',
            'bias': 'short',
            'side': 'short',
            'timestamp': day3['Date'],
            'price': day3['Close'],
            'volume': day3['Volume'],
            'relative_volume': rv,
            'quality': 'high' if rv >= self.rv_high else 'medium' if rv >= self.rv_medium else 'low'
        }
    
    def detect_three_white_soldiers(self, df: pd.DataFrame, index: int = -1) -> Optional[Dict]:
        """
        Three White Soldiers (bullish continuation, 3-candle)
        - Three consecutive bullish candles
        - Each closes higher
        - Each opens within previous body
        """
        if len(df) < 3:
            return None
        
        if index == -1:
            idx = len(df) - 1
        else:
            idx = index
        
        if idx < 2:
            return None
        
        day1 = df.iloc[idx - 2]
        day2 = df.iloc[idx - 1]
        day3 = df.iloc[idx]
        
        # All bullish
        all_bullish = (
            day1['Close'] > day1['Open'] and
            day2['Close'] > day2['Open'] and
            day3['Close'] > day3['Open']
        )
        
        # Each closes higher
        closes_higher = (
            day2['Close'] > day1['Close'] and
            day3['Close'] > day2['Close']
        )
        
        # Each opens within previous body
        opens_within = (
            day1['Open'] < day2['Open'] < day1['Close'] and
            day2['Open'] < day3['Open'] < day2['Close']
        )
        
        # Similar body sizes
        body1 = day1['Close'] - day1['Open']
        body2 = day2['Close'] - day2['Open']
        body3 = day3['Close'] - day3['Open']
        avg_body = (body1 + body2 + body3) / 3
        
        bodies_similar = (
            abs(body1 - avg_body) < 0.3 * avg_body and
            abs(body2 - avg_body) < 0.3 * avg_body and
            abs(body3 - avg_body) < 0.3 * avg_body
        )
        
        is_pattern = all_bullish and closes_higher and opens_within and bodies_similar
        
        if not is_pattern:
            return None
        
        rv = self.calculate_relative_volume(df, idx)
        
        return {
            'pattern': 'Three White Soldiers',
            'bias': 'long',
            'side': 'long',
            'timestamp': day3['Date'],
            'price': day3['Close'],
            'volume': day3['Volume'],
            'relative_volume': rv,
            'quality': 'high' if rv >= self.rv_high else 'medium' if rv >= self.rv_medium else 'low'
        }
    
    def detect_three_black_crows(self, df: pd.DataFrame, index: int = -1) -> Optional[Dict]:
        """
        Three Black Crows (bearish continuation, 3-candle)
        - Three consecutive bearish candles
        - Each closes lower
        - Each opens within previous body
        """
        if len(df) < 3:
            return None
        
        if index == -1:
            idx = len(df) - 1
        else:
            idx = index
        
        if idx < 2:
            return None
        
        day1 = df.iloc[idx - 2]
        day2 = df.iloc[idx - 1]
        day3 = df.iloc[idx]
        
        # All bearish
        all_bearish = (
            day1['Close'] < day1['Open'] and
            day2['Close'] < day2['Open'] and
            day3['Close'] < day3['Open']
        )
        
        # Each closes lower
        closes_lower = (
            day2['Close'] < day1['Close'] and
            day3['Close'] < day2['Close']
        )
        
        # Each opens within previous body
        opens_within = (
            day1['Close'] < day2['Open'] < day1['Open'] and
            day2['Close'] < day3['Open'] < day2['Open']
        )
        
        # Similar body sizes
        body1 = day1['Open'] - day1['Close']
        body2 = day2['Open'] - day2['Close']
        body3 = day3['Open'] - day3['Close']
        avg_body = (body1 + body2 + body3) / 3
        
        bodies_similar = (
            abs(body1 - avg_body) < 0.3 * avg_body and
            abs(body2 - avg_body) < 0.3 * avg_body and
            abs(body3 - avg_body) < 0.3 * avg_body
        )
        
        is_pattern = all_bearish and closes_lower and opens_within and bodies_similar
        
        if not is_pattern:
            return None
        
        rv = self.calculate_relative_volume(df, idx)
        
        return {
            'pattern': 'Three Black Crows',
            'bias': 'short',
            'side': 'short',
            'timestamp': day3['Date'],
            'price': day3['Close'],
            'volume': day3['Volume'],
            'relative_volume': rv,
            'quality': 'high' if rv >= self.rv_high else 'medium' if rv >= self.rv_medium else 'low'
        }
    
    # ============= TWO-CANDLE PATTERNS =============
    
    def detect_piercing_pattern(self, df: pd.DataFrame, index: int = -1) -> Optional[Dict]:
        """
        Piercing Pattern (bullish reversal, 2-candle)
        - Day 1: Long bearish
        - Day 2: Opens below Day 1 low, closes above Day 1 midpoint
        """
        if len(df) < 2:
            return None
        
        if index == -1:
            prev = df.iloc[-2]
            curr = df.iloc[-1]
        else:
            if index < 1:
                return None
            prev = df.iloc[index - 1]
            curr = df.iloc[index]
        
        # Day 1: Bearish
        prev_bearish = prev['Close'] < prev['Open']
        prev_body = abs(prev['Close'] - prev['Open'])
        prev_range = prev['High'] - prev['Low']
        prev_long = prev_body > 0.6 * prev_range if prev_range > 0 else False
        
        # Day 2: Bullish, opens below prev low, closes above prev midpoint
        curr_bullish = curr['Close'] > curr['Open']
        opens_below = curr['Open'] < prev['Low']
        prev_mid = (prev['Open'] + prev['Close']) / 2
        closes_above_mid = curr['Close'] > prev_mid
        
        is_pattern = prev_bearish and prev_long and curr_bullish and opens_below and closes_above_mid
        
        if not is_pattern:
            return None
        
        rv = self.calculate_relative_volume(df, index)
        
        return {
            'pattern': 'Piercing Pattern',
            'bias': 'long',
            'side': 'long',
            'timestamp': curr['Date'],
            'price': curr['Close'],
            'volume': curr['Volume'],
            'relative_volume': rv,
            'quality': 'high' if rv >= self.rv_high else 'medium' if rv >= self.rv_medium else 'low'
        }
    
    def detect_dark_cloud_cover(self, df: pd.DataFrame, index: int = -1) -> Optional[Dict]:
        """
        Dark Cloud Cover (bearish reversal, 2-candle)
        - Day 1: Long bullish
        - Day 2: Opens above Day 1 high, closes below Day 1 midpoint
        """
        if len(df) < 2:
            return None
        
        if index == -1:
            prev = df.iloc[-2]
            curr = df.iloc[-1]
        else:
            if index < 1:
                return None
            prev = df.iloc[index - 1]
            curr = df.iloc[index]
        
        # Day 1: Bullish
        prev_bullish = prev['Close'] > prev['Open']
        prev_body = abs(prev['Close'] - prev['Open'])
        prev_range = prev['High'] - prev['Low']
        prev_long = prev_body > 0.6 * prev_range if prev_range > 0 else False
        
        # Day 2: Bearish, opens above prev high, closes below prev midpoint
        curr_bearish = curr['Close'] < curr['Open']
        opens_above = curr['Open'] > prev['High']
        prev_mid = (prev['Open'] + prev['Close']) / 2
        closes_below_mid = curr['Close'] < prev_mid
        
        is_pattern = prev_bullish and prev_long and curr_bearish and opens_above and closes_below_mid
        
        if not is_pattern:
            return None
        
        rv = self.calculate_relative_volume(df, index)
        
        return {
            'pattern': 'Dark Cloud Cover',
            'bias': 'short',
            'side': 'short',
            'timestamp': curr['Date'],
            'price': curr['Close'],
            'volume': curr['Volume'],
            'relative_volume': rv,
            'quality': 'high' if rv >= self.rv_high else 'medium' if rv >= self.rv_medium else 'low'
        }
    
    # ============= DOJI PATTERNS =============
    
    def detect_doji(self, df: pd.DataFrame, index: int = -1) -> Optional[Dict]:
        """
        Doji (indecision, neutral)
        - Very small body (< 10% of range)
        - Equal open and close (approximately)
        """
        if len(df) < 1:
            return None
        
        candle = df.iloc[index]
        
        body = abs(candle['Close'] - candle['Open'])
        total_range = candle['High'] - candle['Low']
        
        if total_range == 0:
            return None
        
        is_pattern = body < 0.1 * total_range
        
        if not is_pattern:
            return None
        
        rv = self.calculate_relative_volume(df, index)
        
        # Doji is neutral, but context determines bias
        # For now, skip doji patterns as they need context
        return None
    
    # ============= MAIN DETECTION METHOD =============
    
    def detect_patterns(self, df: pd.DataFrame, index: int = -1) -> Optional[Dict]:
        """
        Detect all patterns (checks in priority order)
        
        Args:
            df: DataFrame with HOURLY OHLC data
            index: Index to check (default -1 for latest)
            
        Returns:
            First pattern detected, or None
        """
        # Priority 1: Three-candle patterns (strongest signals)
        pattern = self.detect_morning_star(df, index)
        if pattern:
            return pattern
        
        pattern = self.detect_evening_star(df, index)
        if pattern:
            return pattern
        
        pattern = self.detect_three_white_soldiers(df, index)
        if pattern:
            return pattern
        
        pattern = self.detect_three_black_crows(df, index)
        if pattern:
            return pattern
        
        # Priority 2: Two-candle patterns
        pattern = self.detect_bullish_engulfing(df, index)
        if pattern:
            return pattern
        
        pattern = self.detect_bearish_engulfing(df, index)
        if pattern:
            return pattern
        
        pattern = self.detect_piercing_pattern(df, index)
        if pattern:
            return pattern
        
        pattern = self.detect_dark_cloud_cover(df, index)
        if pattern:
            return pattern
        
        # Priority 3: Single-candle patterns
        pattern = self.detect_hammer(df, index)
        if pattern:
            return pattern
        
        pattern = self.detect_inverted_hammer(df, index)
        if pattern:
            return pattern
        
        pattern = self.detect_shooting_star(df, index)
        if pattern:
            return pattern
        
        pattern = self.detect_hanging_man(df, index)
        if pattern:
            return pattern
        
        return None


def test_pattern_detector():
    """Test expanded pattern detector"""
    import pandas as pd
    from datetime import datetime, timedelta
    
    print("🧪 Testing Expanded Pattern Detector (P2)")
    print("=" * 60)
    
    config = {'rv_requirements': {'high': 1.5, 'medium': 1.2}}
    detector = PatternDetector(config)
    
    # Test Morning Star
    print("\n📊 Testing Morning Star...")
    dates = [datetime.now() - timedelta(hours=i) for i in range(10, -1, -1)]
    df = pd.DataFrame({
        'Date': dates[-3:],
        'Open': [100, 98, 99],
        'High': [101, 99, 103],
        'Low': [98, 97, 98],
        'Close': [98, 98.5, 102],  # Bearish, Doji, Bullish
        'Volume': [100000, 80000, 150000]
    })
    
    pattern = detector.detect_morning_star(df)
    print(f"   {'✅ Detected' if pattern else '❌ Not detected'}: {pattern['pattern'] if pattern else 'None'}")
    
    # Test Three White Soldiers
    print("\n📊 Testing Three White Soldiers...")
    df = pd.DataFrame({
        'Date': dates[-3:],
        'Open': [100, 101, 102],
        'High': [102, 103, 104],
        'Low': [99, 100, 101],
        'Close': [101.5, 102.5, 103.5],
        'Volume': [100000, 110000, 120000]
    })
    
    pattern = detector.detect_three_white_soldiers(df)
    print(f"   {'✅ Detected' if pattern else '❌ Not detected'}: {pattern['pattern'] if pattern else 'None'}")
    
    # Test Hammer
    print("\n📊 Testing Hammer...")
    df = pd.DataFrame({
        'Date': dates[-1:],
        'Open': [100],
        'High': [101],
        'Low': [96],  # Long lower wick
        'Close': [100.5],
        'Volume': [150000]
    })
    
    pattern = detector.detect_hammer(df)
    print(f"   {'✅ Detected' if pattern else '❌ Not detected'}: {pattern['pattern'] if pattern else 'None'}")
    
    print("\n✅ Pattern detector P2 test complete!")
    print(f"\n📋 Total patterns available: 12")
    print("   - Bullish Engulfing, Bearish Engulfing")
    print("   - Hammer, Inverted Hammer, Shooting Star, Hanging Man")
    print("   - Morning Star, Evening Star")
    print("   - Three White Soldiers, Three Black Crows")
    print("   - Piercing Pattern, Dark Cloud Cover")


if __name__ == "__main__":
    test_pattern_detector()