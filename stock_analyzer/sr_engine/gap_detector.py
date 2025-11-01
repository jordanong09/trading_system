# indicators/gap_detector.py - Gap Edge Detection (UPDATED v5.0)
"""
Detect price gaps on HOURLY timeframe
- Gap up: This hour's low > Last hour's high
- Gap down: This hour's high < Last hour's low
- Track unfilled gaps (strong S/R magnets)
- V5.0: New thresholds (1.5% OR 0.3Ã—ATR) + decay for filled gaps
- Works on 130 hourly candles
"""

import pandas as pd
from typing import List, Dict, Optional


class GapDetector:
    """
    Detect price gaps on HOURLY data that create S/R zones
    V5.0: Enhanced with ATR-based detection and fill decay
    """
    
    def __init__(
        self, 
        min_gap_pct: Optional[float] = None,
        min_gap_atr_mult: Optional[float] = None,
        filled_decay: Optional[float] = None,
        max_gaps: int = 8,
        config=None
    ):
        """
        Initialize gap detector for HOURLY data
        
        Args:
            min_gap_pct: Minimum gap size as % (default: 1.5% from config)
            min_gap_atr_mult: Minimum gap size as ATR multiplier (default: 0.3)
            filled_decay: Weight decay for filled gaps (default: 0.7)
            max_gaps: Maximum gaps to return (default: 8)
            config: Configuration module with GAP_ settings
        """
        # Load from config if available
        if config:
            self.min_gap_pct = config.GAP_PCT_MIN if hasattr(config, 'GAP_PCT_MIN') else 0.015
            self.min_gap_atr_mult = config.GAP_SIZE_MIN_ATR if hasattr(config, 'GAP_SIZE_MIN_ATR') else 0.30
            self.filled_decay = config.GAP_DECAY_FILLED if hasattr(config, 'GAP_DECAY_FILLED') else 0.7
        else:
            self.min_gap_pct = min_gap_pct if min_gap_pct is not None else 0.015  # 1.5%
            self.min_gap_atr_mult = min_gap_atr_mult if min_gap_atr_mult is not None else 0.30
            self.filled_decay = filled_decay if filled_decay is not None else 0.7
        
        self.max_gaps = max_gaps
        self.base_weight = 2  # Base weight for gaps
    
    def detect_gaps(
        self, 
        df: pd.DataFrame, 
        current_price: float,
        atr: Optional[float] = None
    ) -> List[Dict]:
        """
        Detect all price gaps in HOURLY data
        
        V5.0: Uses dual threshold - gap detected if:
            - gap_pct >= 1.5% OR gap_size >= 0.3Ã—ATR
        
        Args:
            df: DataFrame with HOURLY OHLC data (130 bars)
            current_price: Current stock price
            atr: ATR for size threshold (optional, uses % only if None)
            
        Returns:
            List of gap dicts with gap edges, fill status, and weight
        """
        if len(df) < 2:
            return []
        
        gaps = []
        
        # Look through all hourly data
        for i in range(1, len(df)):
            prev_bar = df.iloc[i - 1]
            curr_bar = df.iloc[i]
            
            # Gap Up: This hour's low > Last hour's high
            if curr_bar['Low'] > prev_bar['High']:
                gap_size = curr_bar['Low'] - prev_bar['High']
                gap_pct = (gap_size / prev_bar['High'])
                gap_size_atr = gap_size / atr if atr else 0
                
                # V5.0: Dual threshold check
                threshold_met = gap_pct >= self.min_gap_pct
                if atr:
                    threshold_met = threshold_met or gap_size_atr >= self.min_gap_atr_mult
                
                if threshold_met:
                    gap_bottom = prev_bar['High']
                    gap_top = curr_bar['Low']
                    
                    # Check if gap filled (price went back into gap)
                    filled = False
                    fill_timestamp = None
                    
                    for j in range(i + 1, len(df)):
                        if df.iloc[j]['Low'] <= gap_top:
                            filled = True
                            fill_timestamp = df.iloc[j]['Date']
                            break
                    
                    # Calculate weight with decay for filled gaps
                    weight = self.base_weight
                    if filled:
                        weight = weight * self.filled_decay
                    
                    gaps.append({
                        'type': 'gap_up',
                        'gap_bottom': gap_bottom,
                        'gap_top': gap_top,
                        'gap_mid': (gap_bottom + gap_top) / 2,
                        'gap_size': gap_size,
                        'gap_pct': gap_pct * 100,  # Convert to percentage
                        'gap_size_atr': gap_size_atr,
                        'timestamp': curr_bar['Date'],
                        'filled': filled,
                        'fill_timestamp': fill_timestamp,
                        'bars_ago': len(df) - i - 1,
                        'above_current': gap_bottom > current_price,
                        'weight': weight  # V5.0: Added weight
                    })
            
            # Gap Down: This hour's high < Last hour's low
            elif curr_bar['High'] < prev_bar['Low']:
                gap_size = prev_bar['Low'] - curr_bar['High']
                gap_pct = (gap_size / prev_bar['Low'])
                gap_size_atr = gap_size / atr if atr else 0
                
                # V5.0: Dual threshold check
                threshold_met = gap_pct >= self.min_gap_pct
                if atr:
                    threshold_met = threshold_met or gap_size_atr >= self.min_gap_atr_mult
                
                if threshold_met:
                    gap_top = prev_bar['Low']
                    gap_bottom = curr_bar['High']
                    
                    # Check if gap filled (price went back into gap)
                    filled = False
                    fill_timestamp = None
                    
                    for j in range(i + 1, len(df)):
                        if df.iloc[j]['High'] >= gap_bottom:
                            filled = True
                            fill_timestamp = df.iloc[j]['Date']
                            break
                    
                    # Calculate weight with decay for filled gaps
                    weight = self.base_weight
                    if filled:
                        weight = weight * self.filled_decay
                    
                    gaps.append({
                        'type': 'gap_down',
                        'gap_bottom': gap_bottom,
                        'gap_top': gap_top,
                        'gap_mid': (gap_bottom + gap_top) / 2,
                        'gap_size': gap_size,
                        'gap_pct': gap_pct * 100,  # Convert to percentage
                        'gap_size_atr': gap_size_atr,
                        'timestamp': curr_bar['Date'],
                        'filled': filled,
                        'fill_timestamp': fill_timestamp,
                        'bars_ago': len(df) - i - 1,
                        'above_current': gap_bottom > current_price,
                        'weight': weight  # V5.0: Added weight
                    })
        
        # Sort: unfilled first, then by recency, then by size
        gaps.sort(key=lambda x: (not x['filled'], -x['bars_ago'], -x['gap_pct']))
        
        return gaps[:self.max_gaps]
    
    def get_gap_edges(
        self, 
        df: pd.DataFrame, 
        current_price: float,
        atr: Optional[float] = None
    ) -> Dict[str, List[float]]:
        """
        Get gap edges for zone creation
        
        Args:
            df: DataFrame with HOURLY OHLC data
            current_price: Current stock price
            atr: ATR for threshold calculation (optional)
            
        Returns:
            Dict with 'support' and 'resistance' gap edge prices
        """
        gaps = self.detect_gaps(df, current_price, atr)
        
        support_edges = []
        resistance_edges = []
        
        for gap in gaps:
            # Prioritize unfilled gaps
            if not gap['filled']:
                if gap['above_current']:
                    # Gap above price = resistance
                    resistance_edges.append(gap['gap_bottom'])  # Lower edge acts as resistance
                else:
                    # Gap below price = support
                    support_edges.append(gap['gap_top'])  # Upper edge acts as support
        
        return {
            'support': support_edges[:5],  # Top 5
            'resistance': resistance_edges[:5]  # Top 5
        }


def test_gap_detector():
    """Test gap detector with sample HOURLY data"""
    import pandas as pd
    from datetime import datetime, timedelta
    
    print("Ã°Å¸Â§Âª Testing Gap Detector (HOURLY)")
    print("=" * 60)
    
    # Create 130 hours of sample data with gaps
    timestamps = [datetime.now() - timedelta(hours=i) for i in range(130, -1, -1)]
    
    prices = []
    for i in range(131):
        if i < 50:
            price = 100 + i * 0.3
        elif i == 50:
            price = 117  # Gap up from ~115 to 117
        elif i < 90:
            price = 117 + (i - 50) * 0.2
        elif i == 90:
            price = 123  # Another gap up
        else:
            price = 123 + (i - 90) * 0.15
        
        prices.append(price)
    
    df = pd.DataFrame({
        'Date': timestamps,
        'Open': prices,
        'High': [p + 0.3 for p in prices],
        'Low': [p - 0.3 for p in prices],
        'Close': prices,
        'Volume': [100000] * len(prices)
    })
    
    current_price = prices[-1]
    
    # Initialize detector
    detector = GapDetector(min_gap_pct=0.2, max_gaps=8)
    
    # Detect gaps
    print(f"\nÃ°Å¸â€Â Detecting Gaps on {len(df)} hourly bars...")
    print(f"   Current Price: ${current_price:.2f}\n")
    
    gaps = detector.detect_gaps(df, current_price)
    
    print(f"Ã°Å¸â€œÅ  DETECTED GAPS ({len(gaps)}):")
    for i, gap in enumerate(gaps, 1):
        status = "UNFILLED" if not gap['filled'] else "filled"
        direction = "Ã¢â€ â€˜" if gap['type'] == 'gap_up' else "Ã¢â€ â€œ"
        position = "above" if gap['above_current'] else "below"
        
        print(f"\n   {i}. {gap['type'].upper()} {direction} [{status}]")
        print(f"      Range: ${gap['gap_bottom']:.2f} - ${gap['gap_top']:.2f}")
        print(f"      Size: ${gap['gap_size']:.2f} ({gap['gap_pct']:.2f}%)")
        print(f"      Position: {position} current price")
        print(f"      Bars ago: {gap['bars_ago']} hours")
    
    # Get gap edges
    edges = detector.get_gap_edges(df, current_price)
    
    print(f"\nÃ°Å¸Å½Â¯ GAP EDGES FOR ZONES:")
    print(f"   Support edges: {len(edges['support'])}")
    for price in edges['support']:
        print(f"      ${price:.2f}")
    
    print(f"   Resistance edges: {len(edges['resistance'])}")
    for price in edges['resistance']:
        print(f"      ${price:.2f}")
    
    print("\nÃ¢Å“â€¦ Gap detector test complete!")


if __name__ == "__main__":
    test_gap_detector()