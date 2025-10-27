# indicators/swing_detector.py - Swing High/Low Detection (HOURLY)
"""
Detect swing highs and lows on HOURLY timeframe for S/R zones
- Works on 130 hourly candles (~5-6 trading days)
- Swing high: High with N lower highs on each side
- Swing low: Low with N higher lows on each side
- Optimized for intraday/swing trading levels
"""

import pandas as pd
from typing import List, Dict


class SwingDetector:
    """
    Detect swing pivot points in HOURLY price data
    """
    
    def __init__(self, lookback: int = 5, max_swings: int = 10):
        """
        Initialize swing detector for HOURLY data
        
        Args:
            lookback: Hours to check on each side (default: 5)
            max_swings: Maximum swings to return (default: 10)
        """
        self.lookback = lookback
        self.max_swings = max_swings
    
    def detect_swing_highs(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect swing highs in HOURLY data
        
        A swing high occurs when:
        - Current high > N hours before high
        - Current high > N hours after high
        
        Args:
            df: DataFrame with HOURLY OHLC data (130 bars)
            
        Returns:
            List of swing high dicts with price, timestamp, bars_ago
        """
        if len(df) < self.lookback * 2 + 1:
            return []
        
        swing_highs = []
        
        # Check each bar (excluding edges)
        for i in range(self.lookback, len(df) - self.lookback):
            current_high = df.iloc[i]['High']
            is_swing_high = True
            
            # Check left side (before)
            for j in range(i - self.lookback, i):
                if df.iloc[j]['High'] >= current_high:
                    is_swing_high = False
                    break
            
            if not is_swing_high:
                continue
            
            # Check right side (after)
            for j in range(i + 1, i + self.lookback + 1):
                if df.iloc[j]['High'] >= current_high:
                    is_swing_high = False
                    break
            
            if is_swing_high:
                # Calculate strength
                left_highs = [df.iloc[j]['High'] for j in range(i - self.lookback, i)]
                right_highs = [df.iloc[j]['High'] for j in range(i + 1, i + self.lookback + 1)]
                surrounding_avg = (sum(left_highs) + sum(right_highs)) / (len(left_highs) + len(right_highs))
                
                strength_pct = ((current_high - surrounding_avg) / surrounding_avg * 100) if surrounding_avg > 0 else 0
                
                swing_highs.append({
                    'price': current_high,
                    'timestamp': df.iloc[i]['Date'],
                    'bars_ago': len(df) - i - 1,  # How many bars ago
                    'strength_pct': strength_pct,
                    'type': 'swing_high'
                })
        
        # Sort by recency first, then by strength
        swing_highs.sort(key=lambda x: (-x['bars_ago'], -x['strength_pct']))
        
        # Return most recent and strongest
        return swing_highs[:self.max_swings]
    
    def detect_swing_lows(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect swing lows in HOURLY data
        
        A swing low occurs when:
        - Current low < N hours before low
        - Current low < N hours after low
        
        Args:
            df: DataFrame with HOURLY OHLC data (130 bars)
            
        Returns:
            List of swing low dicts with price, timestamp, bars_ago
        """
        if len(df) < self.lookback * 2 + 1:
            return []
        
        swing_lows = []
        
        # Check each bar (excluding edges)
        for i in range(self.lookback, len(df) - self.lookback):
            current_low = df.iloc[i]['Low']
            is_swing_low = True
            
            # Check left side (before)
            for j in range(i - self.lookback, i):
                if df.iloc[j]['Low'] <= current_low:
                    is_swing_low = False
                    break
            
            if not is_swing_low:
                continue
            
            # Check right side (after)
            for j in range(i + 1, i + self.lookback + 1):
                if df.iloc[j]['Low'] <= current_low:
                    is_swing_low = False
                    break
            
            if is_swing_low:
                # Calculate strength
                left_lows = [df.iloc[j]['Low'] for j in range(i - self.lookback, i)]
                right_lows = [df.iloc[j]['Low'] for j in range(i + 1, i + self.lookback + 1)]
                surrounding_avg = (sum(left_lows) + sum(right_lows)) / (len(left_lows) + len(right_lows))
                
                strength_pct = ((surrounding_avg - current_low) / surrounding_avg * 100) if surrounding_avg > 0 else 0
                
                swing_lows.append({
                    'price': current_low,
                    'timestamp': df.iloc[i]['Date'],
                    'bars_ago': len(df) - i - 1,  # How many bars ago
                    'strength_pct': strength_pct,
                    'type': 'swing_low'
                })
        
        # Sort by recency first, then by strength
        swing_lows.sort(key=lambda x: (-x['bars_ago'], -x['strength_pct']))
        
        # Return most recent and strongest
        return swing_lows[:self.max_swings]
    
    def detect_all_swings(self, df: pd.DataFrame) -> Dict[str, List[Dict]]:
        """
        Detect both swing highs and lows on HOURLY data
        
        Args:
            df: DataFrame with HOURLY OHLC data (130 bars)
            
        Returns:
            Dict with 'swing_highs' and 'swing_lows' lists
        """
         # DEBUG: What data is swing detector seeing?
        print(f"      🔍 SWING DETECTOR INPUT:")
        print(f"         Bars: {len(df)}")
        print(f"         Price range: ${df['Low'].min():.2f} - ${df['High'].max():.2f}")
        print(f"         First date: {df.iloc[0]['Date']}")
        print(f"         Last date: {df.iloc[-1]['Date']}")
        return {
            'swing_highs': self.detect_swing_highs(df),
            'swing_lows': self.detect_swing_lows(df)
        }


def test_swing_detector():
    """Test swing detector with sample HOURLY data"""
    import pandas as pd
    from datetime import datetime, timedelta
    
    print("🧪 Testing Swing Detector (HOURLY)")
    print("=" * 60)
    
    # Create 130 hours of sample data (~5.4 trading days)
    timestamps = [datetime.now() - timedelta(hours=i) for i in range(130, -1, -1)]
    
    # Create realistic hourly price pattern with swings
    base = 100
    prices = []
    for i in range(131):
        # Add some variation to create swings
        if i < 30:
            price = base + i * 0.5  # Uptrend
        elif i < 40:
            price = base + 15 - (i - 30) * 0.8  # Peak and decline (swing high around 115)
        elif i < 70:
            price = base + 7 - (i - 40) * 0.3  # Downtrend
        elif i < 80:
            price = base - 2 + (i - 70) * 0.5  # Bottom and bounce (swing low around 98)
        elif i < 110:
            price = base + 3 + (i - 80) * 0.3  # Recovery
        else:
            price = base + 12 + (i - 110) * 0.2  # Current uptrend
        
        prices.append(price)
    
    df = pd.DataFrame({
        'Date': timestamps,
        'Open': prices,
        'High': [p + 0.5 for p in prices],
        'Low': [p - 0.5 for p in prices],
        'Close': prices,
        'Volume': [100000] * len(prices)
    })
    
    # Initialize detector (5-hour lookback for hourly data)
    detector = SwingDetector(lookback=5, max_swings=8)
    
    # Detect swings
    print(f"\n🔍 Detecting Swings on {len(df)} hourly bars...")
    swings = detector.detect_all_swings(df)
    
    print(f"\n📈 SWING HIGHS ({len(swings['swing_highs'])}):")
    for i, swing in enumerate(swings['swing_highs'], 1):
        hours_ago = swing['bars_ago']
        print(f"   {i}. ${swing['price']:.2f}")
        print(f"      {hours_ago} hours ago ({hours_ago/6.5:.1f} trading days)")
        print(f"      Strength: {swing['strength_pct']:.2f}%")
    
    print(f"\n📉 SWING LOWS ({len(swings['swing_lows'])}):")
    for i, swing in enumerate(swings['swing_lows'], 1):
        hours_ago = swing['bars_ago']
        print(f"   {i}. ${swing['price']:.2f}")
        print(f"      {hours_ago} hours ago ({hours_ago/6.5:.1f} trading days)")
        print(f"      Strength: {swing['strength_pct']:.2f}%")
    
    print("\n✅ Swing detector test complete!")


if __name__ == "__main__":
    test_swing_detector()
