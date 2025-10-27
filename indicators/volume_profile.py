# indicators/volume_profile.py - Volume Profile (HOURLY)
"""
Calculate volume profile on HOURLY timeframe
- HVN (High Volume Nodes): Strong S/R where institutions accumulated
- LVN (Low Volume Nodes): Weak zones, breakout areas
- Works on 130 hourly candles
- Bins price into levels and sums volume at each level
"""

import pandas as pd
import numpy as np
from typing import List, Dict


class VolumeProfile:
    """
    Calculate volume profile on HOURLY data for HVN/LVN detection
    """
    
    def __init__(self, num_bins: int = 30, hvn_threshold_pct: float = 80, max_hvn: int = 5):
        """
        Initialize volume profile calculator
        
        Args:
            num_bins: Number of price bins (default: 30 for hourly)
            hvn_threshold_pct: Percentile for HVN (default: 80th percentile)
            max_hvn: Maximum HVN levels to return (default: 5)
        """
        self.num_bins = num_bins
        self.hvn_threshold_pct = hvn_threshold_pct
        self.max_hvn = max_hvn
    
    def calculate_profile(self, df: pd.DataFrame) -> Dict:
        """
        Calculate volume profile from HOURLY data
        
        Args:
            df: DataFrame with HOURLY OHLC data (130 bars)
            
        Returns:
            Dict with profile data, HVN levels, LVN levels
        """
        if len(df) < 10:
            return {'hvn': [], 'lvn': [], 'profile': []}
        
        # Get price range
        price_min = df['Low'].min()
        price_max = df['High'].max()
        price_range = price_max - price_min
        
        if price_range == 0:
            return {'hvn': [], 'lvn': [], 'profile': []}
        
        # Create price bins
        bin_size = price_range / self.num_bins
        bins = [price_min + i * bin_size for i in range(self.num_bins + 1)]
        
        # Initialize volume per bin
        volume_per_bin = [0.0] * self.num_bins
        
        # Distribute volume across bins for each bar
        for _, row in df.iterrows():
            bar_low = row['Low']
            bar_high = row['High']
            bar_volume = row['Volume']
            
            # Find which bins this bar touches
            for i in range(self.num_bins):
                bin_low = bins[i]
                bin_high = bins[i + 1]
                
                # Check if bar overlaps this bin
                if bar_high >= bin_low and bar_low <= bin_high:
                    # Calculate overlap
                    overlap_low = max(bar_low, bin_low)
                    overlap_high = min(bar_high, bin_high)
                    overlap_pct = (overlap_high - overlap_low) / (bar_high - bar_low) if bar_high > bar_low else 1.0
                    
                    # Distribute volume proportionally
                    volume_per_bin[i] += bar_volume * overlap_pct
        
        # Create profile data
        profile = []
        for i in range(self.num_bins):
            profile.append({
                'price_low': bins[i],
                'price_high': bins[i + 1],
                'price_mid': (bins[i] + bins[i + 1]) / 2,
                'volume': volume_per_bin[i],
                'bin_index': i
            })
        
        # Calculate HVN threshold
        volumes = [p['volume'] for p in profile]
        hvn_threshold = np.percentile(volumes, self.hvn_threshold_pct)
        
        # Identify HVN (High Volume Nodes)
        hvn_levels = []
        for p in profile:
            if p['volume'] >= hvn_threshold:
                hvn_levels.append({
                    'price': p['price_mid'],
                    'volume': p['volume'],
                    'type': 'hvn'
                })
        
        # Sort HVN by volume (highest first)
        hvn_levels.sort(key=lambda x: x['volume'], reverse=True)
        
        # Identify LVN (Low Volume Nodes) - bottom 20th percentile
        lvn_threshold = np.percentile(volumes, 20)
        lvn_levels = []
        for p in profile:
            if p['volume'] <= lvn_threshold and p['volume'] > 0:
                lvn_levels.append({
                    'price': p['price_mid'],
                    'volume': p['volume'],
                    'type': 'lvn'
                })
        
        return {
            'hvn': hvn_levels[:self.max_hvn],
            'lvn': lvn_levels[:self.max_hvn],
            'profile': profile,
            'hvn_threshold': hvn_threshold,
            'lvn_threshold': lvn_threshold
        }
    
    def get_hvn_levels(self, df: pd.DataFrame, current_price: float) -> Dict[str, List[float]]:
        """
        Get HVN levels for zone creation
        
        Args:
            df: DataFrame with HOURLY OHLC data
            current_price: Current stock price
            
        Returns:
            Dict with 'support' and 'resistance' HVN prices
        """
        profile = self.calculate_profile(df)
        
        support_hvn = []
        resistance_hvn = []
        
        for hvn in profile['hvn']:
            if hvn['price'] < current_price:
                support_hvn.append(hvn['price'])
            else:
                resistance_hvn.append(hvn['price'])
        
        return {
            'support': support_hvn,
            'resistance': resistance_hvn
        }


def test_volume_profile():
    """Test volume profile with sample HOURLY data"""
    import pandas as pd
    from datetime import datetime, timedelta
    
    print("🧪 Testing Volume Profile (HOURLY)")
    print("=" * 60)
    
    # Create 130 hours of sample data with varying volume
    timestamps = [datetime.now() - timedelta(hours=i) for i in range(130, -1, -1)]
    
    prices = []
    volumes = []
    for i in range(131):
        # Create price pattern
        if i < 40:
            price = 100 + i * 0.3
            volume = 80000 + i * 500  # Increasing volume
        elif i < 60:
            price = 112 - (i - 40) * 0.2  # Consolidation around 108-112
            volume = 150000 + (i % 5) * 20000  # High volume (accumulation)
        elif i < 100:
            price = 108 + (i - 60) * 0.25
            volume = 90000 + i * 300
        else:
            price = 118 + (i - 100) * 0.2
            volume = 100000 + i * 400
        
        prices.append(price)
        volumes.append(volume)
    
    df = pd.DataFrame({
        'Date': timestamps,
        'Open': prices,
        'High': [p + 0.5 for p in prices],
        'Low': [p - 0.5 for p in prices],
        'Close': prices,
        'Volume': volumes
    })
    
    current_price = prices[-1]
    
    # Initialize volume profile
    vp = VolumeProfile(num_bins=30, hvn_threshold_pct=80, max_hvn=5)
    
    # Calculate profile
    print(f"\n🔍 Calculating Volume Profile on {len(df)} hourly bars...")
    print(f"   Current Price: ${current_price:.2f}\n")
    
    profile_data = vp.calculate_profile(df)
    
    print(f"📊 HIGH VOLUME NODES (HVN) - {len(profile_data['hvn'])}:")
    print(f"   Threshold: {profile_data['hvn_threshold']:.0f} volume")
    for i, hvn in enumerate(profile_data['hvn'], 1):
        position = "above" if hvn['price'] > current_price else "below"
        print(f"\n   {i}. ${hvn['price']:.2f} ({position} price)")
        print(f"      Volume: {hvn['volume']:.0f}")
    
    print(f"\n📊 LOW VOLUME NODES (LVN) - {len(profile_data['lvn'])}:")
    print(f"   Threshold: {profile_data['lvn_threshold']:.0f} volume")
    for i, lvn in enumerate(profile_data['lvn'], 1):
        position = "above" if lvn['price'] > current_price else "below"
        print(f"\n   {i}. ${lvn['price']:.2f} ({position} price)")
        print(f"      Volume: {lvn['volume']:.0f}")
    
    # Get HVN levels for zones
    hvn_levels = vp.get_hvn_levels(df, current_price)
    
    print(f"\n🎯 HVN LEVELS FOR ZONES:")
    print(f"   Support HVN: {len(hvn_levels['support'])}")
    for price in hvn_levels['support']:
        print(f"      ${price:.2f}")
    
    print(f"   Resistance HVN: {len(hvn_levels['resistance'])}")
    for price in hvn_levels['resistance']:
        print(f"      ${price:.2f}")
    
    print("\n✅ Volume profile test complete!")


if __name__ == "__main__":
    test_volume_profile()
