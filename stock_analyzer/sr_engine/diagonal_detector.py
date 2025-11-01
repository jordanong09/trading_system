"""
Diagonal Detector Module (v5.0)

Detects diagonal trendlines (ascending/descending) by connecting swing points.
Validates trendlines by ensuring no candle body closes through them.
Creates S/R zones along valid trendlines near current price.

Author: Stock Analyzer v5.0
Dependencies: swing_detector
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import sys
import os

# Add project root to path for standalone execution
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class DiagonalDetector:
    """
    Detect and validate diagonal trendlines
    
    Trendline Types:
        - Ascending: Connects swing lows (support)
        - Descending: Connects swing highs (resistance)
    
    Validation:
        - No candle body (open/close) closes through the line
        - Line must touch at least 2 swing points
        - Slope must be reasonable (not too steep/flat)
    """
    
    def __init__(self, config=None):
        """
        Initialize diagonal detector
        
        Args:
            config: Configuration module
        """
        # Load config or use defaults
        if config and hasattr(config, 'DIAGONAL_CONFIG'):
            diag_config = config.DIAGONAL_CONFIG
            self.min_touches = diag_config.get('min_touches', 2)
            self.touch_tolerance_atr = diag_config.get('touch_tolerance_atr', 0.15)
            self.lookback_bars = diag_config.get('lookback_bars', 100)
            self.max_slope_deg = diag_config.get('max_slope_deg', 45)
            self.min_slope_deg = diag_config.get('min_slope_deg', 5)
        else:
            self.min_touches = 2
            self.touch_tolerance_atr = 0.15
            self.lookback_bars = 100
            self.max_slope_deg = 45
            self.min_slope_deg = 5
        
        # Zone width from config
        if config and hasattr(config, 'ZONE_ATR_MULTIPLIER'):
            self.zone_width_multiplier = config.ZONE_ATR_MULTIPLIER
        else:
            self.zone_width_multiplier = 0.15
        
        # Weight from config
        if config and hasattr(config, 'WEIGHTS'):
            self.weight = config.WEIGHTS.get('Diagonal', 2)
        else:
            self.weight = 2
    
    def detect_diagonals(
        self,
        daily_df: pd.DataFrame,
        swing_highs: List[Dict],
        swing_lows: List[Dict],
        current_price: float,
        atr: float,
        lookback_bars: Optional[int] = None
    ) -> List[Dict]:
        """
        Detect diagonal trendlines from swing points
        
        Algorithm:
            1. Try connecting swing lows (ascending support)
            2. Try connecting swing highs (descending resistance)
            3. Validate: no candle body closes through line
            4. Sample points along line near current price
            5. Create zones at sample points (±0.15×ATR)
        
        Args:
            daily_df: Daily OHLC DataFrame
            swing_highs: List of swing high dicts
            swing_lows: List of swing low dicts
            current_price: Current price
            atr: ATR value
            lookback_bars: Bars to look back (default: config value)
        
        Returns:
            List of diagonal zone dicts
        """
        if lookback_bars is None:
            lookback_bars = self.lookback_bars
        
        zones = []
        
        # Detect ascending trendlines (support)
        ascending_zones = self._detect_ascending_lines(
            daily_df,
            swing_lows,
            current_price,
            atr,
            lookback_bars
        )
        zones.extend(ascending_zones)
        
        # Detect descending trendlines (resistance)
        descending_zones = self._detect_descending_lines(
            daily_df,
            swing_highs,
            current_price,
            atr,
            lookback_bars
        )
        zones.extend(descending_zones)
        
        return zones
    
    def _detect_ascending_lines(
        self,
        df: pd.DataFrame,
        swing_lows: List[Dict],
        current_price: float,
        atr: float,
        lookback_bars: int
    ) -> List[Dict]:
        """
        Detect ascending trendlines (connecting swing lows)
        
        Returns:
            List of ascending support zones
        """
        if len(swing_lows) < 2:
            return []
        
        zones = []
        df_recent = df.iloc[-lookback_bars:]
        
        # Try connecting pairs of swing lows
        for i in range(len(swing_lows) - 1):
            for j in range(i + 1, min(i + 4, len(swing_lows))):  # Try next 3 swings
                point1_idx = len(df) - swing_lows[i]['bars_ago'] - 1
                point2_idx = len(df) - swing_lows[j]['bars_ago'] - 1
                
                # Ensure both points in recent window
                if point1_idx < len(df) - lookback_bars or point2_idx < len(df) - lookback_bars:
                    continue
                
                # Create trendline
                start_point = (point2_idx, swing_lows[j]['price'])  # Older point
                end_point = (point1_idx, swing_lows[i]['price'])    # Newer point
                
                # Check if ascending
                if end_point[1] <= start_point[1]:
                    continue
                
                # Calculate slope
                slope = (end_point[1] - start_point[1]) / (end_point[0] - start_point[0])
                slope_deg = np.degrees(np.arctan(slope * len(df) / (df['Close'].max() - df['Close'].min())))
                
                # Check slope is reasonable
                if slope_deg < self.min_slope_deg or slope_deg > self.max_slope_deg:
                    continue
                
                # Validate trendline
                if not self._validate_trendline(df_recent, start_point, end_point, 'support'):
                    continue
                
                # Project line to current bar
                current_idx = len(df) - 1
                current_line_value = self._project_line(start_point, end_point, current_idx)
                
                # Only include if line is near current price (within 20%)
                if abs(current_line_value - current_price) / current_price > 0.20:
                    continue
                
                # Create zone at current price
                zone_width = self.zone_width_multiplier * atr
                zones.append({
                    'type': 'support',
                    'low': current_line_value - zone_width,
                    'mid': current_line_value,
                    'high': current_line_value + zone_width,
                    'source': 'Diagonal',
                    'weight': self.weight,
                    'direction': 'ascending',
                    'start_point': start_point,
                    'end_point': end_point,
                    'slope': slope
                })
        
        return zones
    
    def _detect_descending_lines(
        self,
        df: pd.DataFrame,
        swing_highs: List[Dict],
        current_price: float,
        atr: float,
        lookback_bars: int
    ) -> List[Dict]:
        """
        Detect descending trendlines (connecting swing highs)
        
        Returns:
            List of descending resistance zones
        """
        if len(swing_highs) < 2:
            return []
        
        zones = []
        df_recent = df.iloc[-lookback_bars:]
        
        # Try connecting pairs of swing highs
        for i in range(len(swing_highs) - 1):
            for j in range(i + 1, min(i + 4, len(swing_highs))):  # Try next 3 swings
                point1_idx = len(df) - swing_highs[i]['bars_ago'] - 1
                point2_idx = len(df) - swing_highs[j]['bars_ago'] - 1
                
                # Ensure both points in recent window
                if point1_idx < len(df) - lookback_bars or point2_idx < len(df) - lookback_bars:
                    continue
                
                # Create trendline
                start_point = (point2_idx, swing_highs[j]['price'])  # Older point
                end_point = (point1_idx, swing_highs[i]['price'])    # Newer point
                
                # Check if descending
                if end_point[1] >= start_point[1]:
                    continue
                
                # Calculate slope
                slope = (end_point[1] - start_point[1]) / (end_point[0] - start_point[0])
                slope_deg = abs(np.degrees(np.arctan(slope * len(df) / (df['Close'].max() - df['Close'].min()))))
                
                # Check slope is reasonable
                if slope_deg < self.min_slope_deg or slope_deg > self.max_slope_deg:
                    continue
                
                # Validate trendline
                if not self._validate_trendline(df_recent, start_point, end_point, 'resistance'):
                    continue
                
                # Project line to current bar
                current_idx = len(df) - 1
                current_line_value = self._project_line(start_point, end_point, current_idx)
                
                # Only include if line is near current price (within 20%)
                if abs(current_line_value - current_price) / current_price > 0.20:
                    continue
                
                # Create zone at current price
                zone_width = self.zone_width_multiplier * atr
                zones.append({
                    'type': 'resistance',
                    'low': current_line_value - zone_width,
                    'mid': current_line_value,
                    'high': current_line_value + zone_width,
                    'source': 'Diagonal',
                    'weight': self.weight,
                    'direction': 'descending',
                    'start_point': start_point,
                    'end_point': end_point,
                    'slope': slope
                })
        
        return zones
    
    def _validate_trendline(
        self,
        df: pd.DataFrame,
        start_point: Tuple[int, float],
        end_point: Tuple[int, float],
        line_type: str
    ) -> bool:
        """
        Validate trendline by checking if any candle body closes through it
        
        Args:
            df: Recent DataFrame (lookback window)
            start_point: (index, price) tuple
            end_point: (index, price) tuple
            line_type: 'support' or 'resistance'
        
        Returns:
            True if valid (no body closes through), False otherwise
        """
        # Get bars between start and end points
        start_idx = start_point[0]
        end_idx = end_point[0]
        
        # Calculate line slope
        slope = (end_point[1] - start_point[1]) / (end_point[0] - start_point[0])
        
        # Check each bar between the points
        for idx in range(start_idx + 1, end_idx):
            # Project line value at this bar
            line_value = self._project_line(start_point, end_point, idx)
            
            # Get candle data
            bar = df.iloc[idx]
            body_high = max(bar['Open'], bar['Close'])
            body_low = min(bar['Open'], bar['Close'])
            
            # Check if body closes through line
            if line_type == 'support':
                # For support, no body should close below line
                if body_low < line_value:
                    return False
            else:  # resistance
                # For resistance, no body should close above line
                if body_high > line_value:
                    return False
        
        return True
    
    def _project_line(
        self,
        start_point: Tuple[int, float],
        end_point: Tuple[int, float],
        target_idx: int
    ) -> float:
        """
        Project trendline value at target index
        
        Args:
            start_point: (index, price) tuple
            end_point: (index, price) tuple
            target_idx: Target bar index
        
        Returns:
            Projected price at target_idx
        """
        slope = (end_point[1] - start_point[1]) / (end_point[0] - start_point[0])
        intercept = start_point[1] - (slope * start_point[0])
        return slope * target_idx + intercept


# =============================================================================
# STANDALONE USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    """
    Test the diagonal detector module standalone
    
    Usage:
        python stock_analyzer.sr_engine.diagonal_detector.py
    """
    print("="*70)
    print("DIAGONAL DETECTOR MODULE - STANDALONE TEST")
    print("="*70)
    
    # Create sample data with ascending trendline
    dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='D')
    
    # Ascending trend with swing lows
    base_trend = np.linspace(95, 105, 100)
    noise = np.sin(np.linspace(0, 4*np.pi, 100)) * 3
    prices = base_trend + noise
    
    df = pd.DataFrame({
        'Date': dates,
        'Open': prices - 0.5,
        'High': prices + 1,
        'Low': prices - 1,
        'Close': prices,
    })
    df.set_index('Date', inplace=True)
    
    current_price = prices[-1]
    atr = 2.0
    
    # Sample swing lows (ascending)
    swing_lows = [
        {'price': 98.0, 'bars_ago': 10, 'timestamp': dates[-11]},
        {'price': 96.0, 'bars_ago': 30, 'timestamp': dates[-31]},
        {'price': 94.0, 'bars_ago': 50, 'timestamp': dates[-51]},
    ]
    
    # Sample swing highs (for descending test)
    swing_highs = [
        {'price': 106.0, 'bars_ago': 5, 'timestamp': dates[-6]},
        {'price': 104.0, 'bars_ago': 20, 'timestamp': dates[-21]},
    ]
    
    print(f"\nINPUT DATA:")
    print(f"  Current Price: ${current_price:.2f}")
    print(f"  ATR: ${atr:.2f}")
    print(f"  Swing Lows: {len(swing_lows)}")
    print(f"  Swing Highs: {len(swing_highs)}")
    print(f"  DataFrame: {len(df)} bars")
    
    # Initialize detector
    detector = DiagonalDetector()
    
    # Detect diagonals
    print(f"\nDETECTING DIAGONAL TRENDLINES...")
    zones = detector.detect_diagonals(
        df,
        swing_highs,
        swing_lows,
        current_price,
        atr
    )
    
    print(f"\nDIAGONAL ZONES ({len(zones)} zones):")
    print("="*70)
    
    for i, zone in enumerate(zones, 1):
        print(f"\n{i}. {zone['type'].upper()} @ ${zone['mid']:.2f}")
        print(f"   Range: ${zone['low']:.2f} - ${zone['high']:.2f}")
        print(f"   Direction: {zone['direction']}")
        print(f"   Slope: {zone['slope']:.4f}")
        print(f"   Weight: {zone['weight']}")
        print(f"   Start point: (idx={zone['start_point'][0]}, price=${zone['start_point'][1]:.2f})")
        print(f"   End point: (idx={zone['end_point'][0]}, price=${zone['end_point'][1]:.2f})")
    
    print("\n" + "="*70)
    print("✅ DIAGONAL DETECTOR MODULE TESTS COMPLETE")
    print("="*70)
    print("\nREADY FOR INTEGRATION:")
    print("  - Import: from stock_analyzer.sr_engine.diagonal_detector import DiagonalDetector")
    print("  - Usage: detector = DiagonalDetector(config)")
    print("  - Call: zones = detector.detect_diagonals(df, highs, lows, price, atr)")
    print("="*70)
