# modules/chart_patterns.py
"""
Chart Pattern Detection Module - MPIS
Detects 6 high-reliability chart patterns on Daily and 1H timeframes

Patterns:
- Cup & Handle (68% completion)
- Ascending Triangle (72% completion)
- Descending Triangle (72% completion)
- Bull Flag (63% completion)
- Double Top (79% completion)
- Double Bottom (79% completion)
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from scipy.signal import find_peaks
from datetime import datetime


class ChartPatterns:
    """Detect institutional chart patterns across timeframes"""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
    
    # ============================================================================
    # 1. CUP & HANDLE PATTERN (Bullish Continuation - 68% completion)
    # ============================================================================
    
    def detect_cup_and_handle(self, df: pd.DataFrame, timeframe: str = 'Daily') -> List[Dict]:
        """
        Detect Cup & Handle pattern (Bullish Continuation)
        
        Historical completion rate: 68%
        
        Args:
            df: DataFrame with OHLC data
            timeframe: 'Daily' or '1H'
        
        Formation:
        - U-shaped cup (20-60 periods for Daily, 20-60 hours for 1H)
        - Cup depth: 12-33% from cup high to cup low
        - Handle: 5-20 periods, retraces 10-50% of cup depth
        - Volume: Declining in handle
        - Breakout: Above cup/handle high on volume
        """
        detections = []
        
        # Adjust parameters by timeframe
        if timeframe == '1H':
            min_cup_periods, max_cup_periods = 20, 60  # 20-60 hours
            min_handle_periods, max_handle_periods = 5, 20
        else:  # Daily
            min_cup_periods, max_cup_periods = 20, 60  # 20-60 days
            min_handle_periods, max_handle_periods = 5, 20
        
        if len(df) < max_cup_periods + max_handle_periods:
            return detections
        
        # Scan for cup & handle patterns
        for i in range(max_cup_periods + max_handle_periods, len(df)):
            lookback_data = df.iloc[i - (max_cup_periods + max_handle_periods):i + 1]
            
            try:
                # Find potential cup formation
                cup_high_idx = lookback_data['High'].idxmax()
                cup_high = lookback_data.loc[cup_high_idx, 'High']
                
                # Find cup low (should be after initial high)
                cup_low_idx = lookback_data.loc[cup_high_idx:, 'Low'].idxmin()
                cup_low = lookback_data.loc[cup_low_idx, 'Low']
                
                # Calculate cup depth
                cup_depth_pct = ((cup_high - cup_low) / cup_high) * 100
                
                # Validate cup depth (12-33%)
                if not (12 <= cup_depth_pct <= 33):
                    continue
                
                # Check for U-shape (not V-shape)
                # Cup should take at least min_cup_periods to form
                cup_duration = lookback_data.loc[cup_high_idx:cup_low_idx].shape[0]
                if cup_duration < min_cup_periods:
                    continue
                
                # Look for handle formation after cup low
                handle_data = lookback_data.loc[cup_low_idx:]
                
                if len(handle_data) < min_handle_periods:
                    continue
                
                # Handle should retrace 10-50% of cup depth
                handle_high = handle_data['High'].max()
                handle_low = handle_data['Low'].min()
                
                handle_retracement_pct = ((handle_high - handle_low) / cup_depth_pct) * 100
                
                if not (10 <= handle_retracement_pct <= 50):
                    continue
                
                # Handle duration check
                handle_duration = len(handle_data)
                if not (min_handle_periods <= handle_duration <= max_handle_periods):
                    continue
                
                # Volume declining in handle (optional but preferred)
                volume_declining = self._check_volume_decline(handle_data)
                
                # Current price near handle high (potential breakout)
                current_price = df.iloc[i]['Close']
                breakout_level = handle_high
                
                if current_price >= breakout_level * 0.98:  # Within 2% of breakout
                    # Calculate measured move target
                    measured_move = cup_depth_pct
                    target_price = breakout_level * (1 + measured_move / 100)
                    
                    detections.append({
                        'date': df.iloc[i]['Date'],
                        'symbol': self.config.get('SYMBOL', 'UNKNOWN'),
                        'pattern': 'CUP_AND_HANDLE',
                        'bias': 'BULLISH',
                        'timeframe': timeframe,
                        'price': current_price,
                        'volume': df.iloc[i]['Volume'],
                        'breakout_level': breakout_level,
                        'cup_depth_pct': cup_depth_pct,
                        'target_price': target_price,
                        'measured_move_pct': measured_move,
                        'pattern_duration_periods': cup_duration + handle_duration,
                        'volume_declining': volume_declining,
                        'historical_completion_rate': 0.68,
                        'pattern_type': 'CONTINUATION',
                        'hold_period': '1-4 months' if timeframe == 'Daily' else '3-10 days'
                    })
            
            except Exception:
                continue
        
        return detections
    
    # ============================================================================
    # 2. ASCENDING TRIANGLE (Bullish Continuation - 72% completion)
    # ============================================================================
    
    def detect_ascending_triangle(self, df: pd.DataFrame, timeframe: str = 'Daily') -> List[Dict]:
        """
        Detect Ascending Triangle pattern (Bullish Continuation)
        
        Historical completion rate: 72%
        
        Formation:
        - Flat resistance: 3+ touches at same level (±0.5%)
        - Rising support: Higher lows forming uptrend line
        - Duration: 15-40 periods
        - Breakout: Above resistance on volume
        """
        detections = []
        
        # Adjust parameters by timeframe
        if timeframe == '1H':
            min_periods, max_periods = 15, 40
        else:  # Daily
            min_periods, max_periods = 15, 40
        
        if len(df) < max_periods:
            return detections
        
        for i in range(max_periods, len(df)):
            window = df.iloc[i - max_periods:i + 1]
            
            try:
                # Find peaks (resistance touches)
                peaks_indices, _ = find_peaks(window['High'].values, distance=3)
                
                if len(peaks_indices) < 3:
                    continue
                
                peaks = window.iloc[peaks_indices]['High'].values
                
                # Check if peaks are at similar level (flat resistance)
                resistance_level = np.mean(peaks)
                peak_variance = np.std(peaks) / resistance_level
                
                if peak_variance > 0.005:  # More than 0.5% variance
                    continue
                
                # Find troughs (support touches)
                troughs_indices, _ = find_peaks(-window['Low'].values, distance=3)
                
                if len(troughs_indices) < 2:
                    continue
                
                troughs = window.iloc[troughs_indices]['Low'].values
                
                # Check for rising support (higher lows)
                if not self._check_rising_trend(troughs):
                    continue
                
                # Current price near resistance (potential breakout)
                current_price = df.iloc[i]['Close']
                
                if current_price >= resistance_level * 0.98:  # Within 2% of breakout
                    # Calculate target (triangle height projected up)
                    triangle_height = resistance_level - troughs[0]
                    target_price = resistance_level + triangle_height
                    measured_move_pct = (triangle_height / resistance_level) * 100
                    
                    detections.append({
                        'date': df.iloc[i]['Date'],
                        'symbol': self.config.get('SYMBOL', 'UNKNOWN'),
                        'pattern': 'ASCENDING_TRIANGLE',
                        'bias': 'BULLISH',
                        'timeframe': timeframe,
                        'price': current_price,
                        'volume': df.iloc[i]['Volume'],
                        'resistance_level': resistance_level,
                        'resistance_touches': len(peaks),
                        'support_touches': len(troughs),
                        'target_price': target_price,
                        'measured_move_pct': measured_move_pct,
                        'pattern_duration_periods': len(window),
                        'historical_completion_rate': 0.72,
                        'pattern_type': 'CONTINUATION',
                        'hold_period': '3-8 weeks' if timeframe == 'Daily' else '2-7 days'
                    })
            
            except Exception:
                continue
        
        return detections
    
    # ============================================================================
    # 3. DESCENDING TRIANGLE (Bearish Continuation - 72% completion)
    # ============================================================================
    
    def detect_descending_triangle(self, df: pd.DataFrame, timeframe: str = 'Daily') -> List[Dict]:
        """
        Detect Descending Triangle pattern (Bearish Continuation)
        
        Historical completion rate: 72%
        
        Formation:
        - Flat support: 3+ touches at same level (±0.5%)
        - Declining resistance: Lower highs forming downtrend line
        - Duration: 15-40 periods
        - Breakdown: Below support on volume
        """
        detections = []
        
        # Adjust parameters by timeframe
        if timeframe == '1H':
            min_periods, max_periods = 15, 40
        else:  # Daily
            min_periods, max_periods = 15, 40
        
        if len(df) < max_periods:
            return detections
        
        for i in range(max_periods, len(df)):
            window = df.iloc[i - max_periods:i + 1]
            
            try:
                # Find troughs (support touches)
                troughs_indices, _ = find_peaks(-window['Low'].values, distance=3)
                
                if len(troughs_indices) < 3:
                    continue
                
                troughs = window.iloc[troughs_indices]['Low'].values
                
                # Check if troughs are at similar level (flat support)
                support_level = np.mean(troughs)
                trough_variance = np.std(troughs) / support_level
                
                if trough_variance > 0.005:  # More than 0.5% variance
                    continue
                
                # Find peaks (resistance touches)
                peaks_indices, _ = find_peaks(window['High'].values, distance=3)
                
                if len(peaks_indices) < 2:
                    continue
                
                peaks = window.iloc[peaks_indices]['High'].values
                
                # Check for declining resistance (lower highs)
                if not self._check_declining_trend(peaks):
                    continue
                
                # Current price near support (potential breakdown)
                current_price = df.iloc[i]['Close']
                
                if current_price <= support_level * 1.02:  # Within 2% of breakdown
                    # Calculate target (triangle height projected down)
                    triangle_height = peaks[0] - support_level
                    target_price = support_level - triangle_height
                    measured_move_pct = (triangle_height / support_level) * 100
                    
                    detections.append({
                        'date': df.iloc[i]['Date'],
                        'symbol': self.config.get('SYMBOL', 'UNKNOWN'),
                        'pattern': 'DESCENDING_TRIANGLE',
                        'bias': 'BEARISH',
                        'timeframe': timeframe,
                        'price': current_price,
                        'volume': df.iloc[i]['Volume'],
                        'support_level': support_level,
                        'support_touches': len(troughs),
                        'resistance_touches': len(peaks),
                        'target_price': target_price,
                        'measured_move_pct': measured_move_pct,
                        'pattern_duration_periods': len(window),
                        'historical_completion_rate': 0.72,
                        'pattern_type': 'CONTINUATION',
                        'hold_period': '3-8 weeks' if timeframe == 'Daily' else '2-7 days'
                    })
            
            except Exception:
                continue
        
        return detections
    
    # ============================================================================
    # 4. BULL FLAG (Bullish Continuation - 63% completion)
    # ============================================================================
    
    def detect_bull_flag(self, df: pd.DataFrame, timeframe: str = 'Daily') -> List[Dict]:
        """
        Detect Bull Flag pattern (Bullish Continuation)
        
        Historical completion rate: 63%
        
        Formation:
        - Strong pole: 15%+ upward move in 5-15 periods
        - Flag: Tight consolidation, slight downward drift or flat
        - Flag duration: 5-15 periods
        - Volume: Declining in flag
        - Breakout: Above flag high on volume
        """
        detections = []
        
        # Adjust parameters by timeframe
        if timeframe == '1H':
            min_pole_periods, max_pole_periods = 5, 15
            min_flag_periods, max_flag_periods = 5, 15
        else:  # Daily
            min_pole_periods, max_pole_periods = 5, 15
            min_flag_periods, max_flag_periods = 5, 15
        
        min_pole_move_pct = 15.0  # Minimum 15% move for pole
        
        if len(df) < max_pole_periods + max_flag_periods:
            return detections
        
        for i in range(max_pole_periods + max_flag_periods, len(df)):
            try:
                # Look for pole (strong upward move)
                pole_start_idx = i - (max_pole_periods + max_flag_periods)
                pole_end_idx = i - min_flag_periods
                
                pole_data = df.iloc[pole_start_idx:pole_end_idx + 1]
                
                if len(pole_data) < min_pole_periods:
                    continue
                
                # Find pole low and high
                pole_low = pole_data['Low'].min()
                pole_high = pole_data['High'].max()
                pole_move_pct = ((pole_high - pole_low) / pole_low) * 100
                
                # Validate pole strength (15%+ move)
                if pole_move_pct < min_pole_move_pct:
                    continue
                
                # Look for flag (consolidation after pole)
                flag_data = df.iloc[pole_end_idx:i + 1]
                
                if len(flag_data) < min_flag_periods:
                    continue
                
                # Flag should be relatively tight (< 10% range)
                flag_high = flag_data['High'].max()
                flag_low = flag_data['Low'].min()
                flag_range_pct = ((flag_high - flag_low) / flag_high) * 100
                
                if flag_range_pct > 10:  # Too wide to be a flag
                    continue
                
                # Volume should decline in flag
                volume_declining = self._check_volume_decline(flag_data)
                
                # Current price near flag high (potential breakout)
                current_price = df.iloc[i]['Close']
                breakout_level = flag_high
                
                if current_price >= breakout_level * 0.98:  # Within 2% of breakout
                    # Target: Pole height added to breakout level
                    target_price = breakout_level + (pole_high - pole_low)
                    measured_move_pct = pole_move_pct
                    
                    detections.append({
                        'date': df.iloc[i]['Date'],
                        'symbol': self.config.get('SYMBOL', 'UNKNOWN'),
                        'pattern': 'BULL_FLAG',
                        'bias': 'BULLISH',
                        'timeframe': timeframe,
                        'price': current_price,
                        'volume': df.iloc[i]['Volume'],
                        'pole_move_pct': pole_move_pct,
                        'flag_range_pct': flag_range_pct,
                        'breakout_level': breakout_level,
                        'target_price': target_price,
                        'measured_move_pct': measured_move_pct,
                        'volume_declining': volume_declining,
                        'pattern_duration_periods': len(pole_data) + len(flag_data),
                        'historical_completion_rate': 0.63,
                        'pattern_type': 'CONTINUATION',
                        'hold_period': '2-6 weeks' if timeframe == 'Daily' else '1-5 days'
                    })
            
            except Exception:
                continue
        
        return detections
    
    # ============================================================================
    # 5. DOUBLE TOP (Bearish Reversal - 79% completion)
    # ============================================================================
    
    def detect_double_top(self, df: pd.DataFrame, timeframe: str = 'Daily') -> List[Dict]:
        """
        Detect Double Top pattern (Bearish Reversal)
        
        Historical completion rate: 79%
        
        Formation:
        - Two peaks at approximately same level (±2%)
        - Valley between peaks (10%+ retracement from peaks)
        - Duration: 20-60 periods total
        - Breakdown: Close below valley support
        - Target: Peak-to-valley distance projected down
        """
        detections = []
        
        # Adjust parameters by timeframe
        if timeframe == '1H':
            min_periods, max_periods = 20, 60
        else:  # Daily
            min_periods, max_periods = 20, 60
        
        if len(df) < max_periods:
            return detections
        
        for i in range(max_periods, len(df)):
            window = df.iloc[i - max_periods:i + 1]
            
            try:
                # Find peaks
                peaks_indices, _ = find_peaks(window['High'].values, distance=5)
                
                if len(peaks_indices) < 2:
                    continue
                
                # Look at last 2 peaks
                if len(peaks_indices) >= 2:
                    peak1_idx = peaks_indices[-2]
                    peak2_idx = peaks_indices[-1]
                    
                    peak1_price = window.iloc[peak1_idx]['High']
                    peak2_price = window.iloc[peak2_idx]['High']
                    
                    # Peaks should be within 2% of each other
                    peak_diff_pct = abs(peak1_price - peak2_price) / peak1_price * 100
                    
                    if peak_diff_pct > 2.0:
                        continue
                    
                    # Find valley between peaks
                    valley_data = window.iloc[peak1_idx:peak2_idx + 1]
                    valley_price = valley_data['Low'].min()
                    
                    # Valley should be 10%+ below peaks
                    valley_retracement_pct = ((peak1_price - valley_price) / peak1_price) * 100
                    
                    if valley_retracement_pct < 10:
                        continue
                    
                    # Check if current price broke below valley (confirmation)
                    current_price = df.iloc[i]['Close']
                    
                    if current_price <= valley_price * 1.02:  # Within 2% of valley breakdown
                        # Calculate target
                        pattern_height = peak1_price - valley_price
                        target_price = valley_price - pattern_height
                        measured_move_pct = (pattern_height / peak1_price) * 100
                        
                        detections.append({
                            'date': df.iloc[i]['Date'],
                            'symbol': self.config.get('SYMBOL', 'UNKNOWN'),
                            'pattern': 'DOUBLE_TOP',
                            'bias': 'BEARISH',
                            'timeframe': timeframe,
                            'price': current_price,
                            'volume': df.iloc[i]['Volume'],
                            'peak1_price': peak1_price,
                            'peak2_price': peak2_price,
                            'valley_price': valley_price,
                            'valley_retracement_pct': valley_retracement_pct,
                            'target_price': target_price,
                            'measured_move_pct': measured_move_pct,
                            'pattern_duration_periods': peak2_idx - peak1_idx,
                            'historical_completion_rate': 0.79,
                            'pattern_type': 'REVERSAL',
                            'hold_period': '3-8 weeks' if timeframe == 'Daily' else '2-8 days'
                        })
            
            except Exception:
                continue
        
        return detections
    
    # ============================================================================
    # 6. DOUBLE BOTTOM (Bullish Reversal - 79% completion)
    # ============================================================================
    
    def detect_double_bottom(self, df: pd.DataFrame, timeframe: str = 'Daily') -> List[Dict]:
        """
        Detect Double Bottom pattern (Bullish Reversal)
        
        Historical completion rate: 79%
        
        Formation:
        - Two troughs at approximately same level (±2%)
        - Peak between troughs (10%+ rally from troughs)
        - Duration: 20-60 periods total
        - Breakout: Close above peak resistance
        - Target: Trough-to-peak distance projected up
        """
        detections = []
        
        # Adjust parameters by timeframe
        if timeframe == '1H':
            min_periods, max_periods = 20, 60
        else:  # Daily
            min_periods, max_periods = 20, 60
        
        if len(df) < max_periods:
            return detections
        
        for i in range(max_periods, len(df)):
            window = df.iloc[i - max_periods:i + 1]
            
            try:
                # Find troughs
                troughs_indices, _ = find_peaks(-window['Low'].values, distance=5)
                
                if len(troughs_indices) < 2:
                    continue
                
                # Look at last 2 troughs
                if len(troughs_indices) >= 2:
                    trough1_idx = troughs_indices[-2]
                    trough2_idx = troughs_indices[-1]
                    
                    trough1_price = window.iloc[trough1_idx]['Low']
                    trough2_price = window.iloc[trough2_idx]['Low']
                    
                    # Troughs should be within 2% of each other
                    trough_diff_pct = abs(trough1_price - trough2_price) / trough1_price * 100
                    
                    if trough_diff_pct > 2.0:
                        continue
                    
                    # Find peak between troughs
                    peak_data = window.iloc[trough1_idx:trough2_idx + 1]
                    peak_price = peak_data['High'].max()
                    
                    # Peak should be 10%+ above troughs
                    peak_rally_pct = ((peak_price - trough1_price) / trough1_price) * 100
                    
                    if peak_rally_pct < 10:
                        continue
                    
                    # Check if current price broke above peak (confirmation)
                    current_price = df.iloc[i]['Close']
                    
                    if current_price >= peak_price * 0.98:  # Within 2% of peak breakout
                        # Calculate target
                        pattern_height = peak_price - trough1_price
                        target_price = peak_price + pattern_height
                        measured_move_pct = (pattern_height / trough1_price) * 100
                        
                        detections.append({
                            'date': df.iloc[i]['Date'],
                            'symbol': self.config.get('SYMBOL', 'UNKNOWN'),
                            'pattern': 'DOUBLE_BOTTOM',
                            'bias': 'BULLISH',
                            'timeframe': timeframe,
                            'price': current_price,
                            'volume': df.iloc[i]['Volume'],
                            'trough1_price': trough1_price,
                            'trough2_price': trough2_price,
                            'peak_price': peak_price,
                            'peak_rally_pct': peak_rally_pct,
                            'target_price': target_price,
                            'measured_move_pct': measured_move_pct,
                            'pattern_duration_periods': trough2_idx - trough1_idx,
                            'historical_completion_rate': 0.79,
                            'pattern_type': 'REVERSAL',
                            'hold_period': '3-8 weeks' if timeframe == 'Daily' else '2-8 days'
                        })
            
            except Exception:
                continue
        
        return detections
    
    # ============================================================================
    # HELPER METHODS
    # ============================================================================
    
    def _check_volume_decline(self, df: pd.DataFrame) -> bool:
        """Check if volume is generally declining over period"""
        if len(df) < 3:
            return False
        
        try:
            volumes = df['Volume'].values
            # Simple check: is last third lower than first third?
            first_third = volumes[:len(volumes)//3].mean()
            last_third = volumes[-len(volumes)//3:].mean()
            return last_third < first_third * 0.8  # 20% decline
        except:
            return False
    
    def _check_rising_trend(self, values: np.ndarray) -> bool:
        """Check if values show rising trend (higher lows)"""
        if len(values) < 2:
            return False
        
        for i in range(1, len(values)):
            if values[i] <= values[i-1]:
                return False
        return True
    
    def _check_declining_trend(self, values: np.ndarray) -> bool:
        """Check if values show declining trend (lower highs)"""
        if len(values) < 2:
            return False
        
        for i in range(1, len(values)):
            if values[i] >= values[i-1]:
                return False
        return True
    
    # ============================================================================
    # BATCH DETECTION (All patterns at once)
    # ============================================================================
    
    def detect_all_patterns(self, df: pd.DataFrame, timeframe: str = 'Daily') -> List[Dict]:
        """
        Detect all 6 chart patterns on given timeframe
        
        Returns: Combined list of all detected patterns
        """
        all_detections = []
        
        # Run all 6 pattern detectors
        all_detections.extend(self.detect_cup_and_handle(df, timeframe))
        all_detections.extend(self.detect_ascending_triangle(df, timeframe))
        all_detections.extend(self.detect_descending_triangle(df, timeframe))
        all_detections.extend(self.detect_bull_flag(df, timeframe))
        all_detections.extend(self.detect_double_top(df, timeframe))
        all_detections.extend(self.detect_double_bottom(df, timeframe))
        
        # Sort by date
        all_detections = sorted(all_detections, key=lambda x: x['date'])
        
        return all_detections


# Usage example:
if __name__ == "__main__":
    # Example usage
    detector = ChartPatterns()
    
    # Detect on daily data
    # daily_patterns = detector.detect_all_patterns(daily_df, timeframe='Daily')
    
    # Detect on 1H data
    # hourly_patterns = detector.detect_all_patterns(hourly_df, timeframe='1H')
    
    print("Chart Patterns module loaded successfully")
    print("6 patterns × 2 timeframes = 12 total detectors")