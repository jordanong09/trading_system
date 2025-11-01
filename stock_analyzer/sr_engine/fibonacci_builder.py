"""
Fibonacci Builder Module (v5.0)

Builds Fibonacci retracement zones from swing points.
Identifies swing context (high→low or low→high) and calculates key Fib levels.

Author: Stock Analyzer v5.0
Dependencies: swing_detector
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
import sys
import os

# Add project root to path for standalone execution
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class FibonacciBuilder:
    """
    Build Fibonacci retracement zones from swing points
    
    Fibonacci Levels:
        - 0.236 (23.6%) - Weak retracement
        - 0.382 (38.2%) - Moderate retracement
        - 0.500 (50.0%) - Key level (not true Fib, but important)
        - 0.618 (61.8%) - Golden ratio (strongest)
        - 0.786 (78.6%) - Deep retracement
    
    Zone Weights:
        - Fib_core (0.5, 0.618, 0.786): weight = 3
        - Fib_other (0.382, 0.236): weight = 2
    """
    
    def __init__(self, config=None):
        """
        Initialize Fibonacci builder
        
        Args:
            config: Configuration module with WEIGHTS and ZONE_ATR_MULTIPLIER
        """
        # Load weights from config
        if config and hasattr(config, 'WEIGHTS'):
            self.weight_core = config.WEIGHTS.get('Fib_core', 3)
            self.weight_other = config.WEIGHTS.get('Fib_other', 2)
        else:
            self.weight_core = 3
            self.weight_other = 2
        
        # Zone width from config
        if config and hasattr(config, 'ZONE_ATR_MULTIPLIER'):
            self.zone_width_multiplier = config.ZONE_ATR_MULTIPLIER
        else:
            self.zone_width_multiplier = 0.15
        
        # Fibonacci levels to calculate
        self.fib_levels = {
            0.236: 'Fib_0.236',
            0.382: 'Fib_0.382',
            0.500: 'Fib_0.5',
            0.618: 'Fib_0.618',
            0.786: 'Fib_0.786'
        }
        
        # Core levels (stronger)
        self.core_levels = {0.500, 0.618, 0.786}
    
    def build_fibonacci_zones(
        self,
        daily_df: pd.DataFrame,
        swing_highs: List[Dict],
        swing_lows: List[Dict],
        current_price: float,
        atr: float,
        max_distance_pct: float = 0.20
    ) -> List[Dict]:
        """
        Build Fibonacci zones from swing points
        
        Algorithm:
            1. Find most recent significant swing (high→low or low→high)
            2. Calculate Fib retracement levels
            3. Create zones around each level (±0.15×ATR)
            4. Only return zones within 20% of current price
        
        Args:
            daily_df: Daily OHLC DataFrame
            swing_highs: List of swing high dicts from SwingDetector
            swing_lows: List of swing low dicts from SwingDetector
            current_price: Current stock price
            atr: ATR(14) value
            max_distance_pct: Max distance from price (default 20%)
        
        Returns:
            List of Fibonacci zone dicts
        """
        if not swing_highs or not swing_lows:
            return []
        
        zones = []
        
        # Try recent swings (last 3 of each type)
        for i in range(min(3, len(swing_highs), len(swing_lows))):
            # Context 1: High → Low (bullish retracement)
            if i < len(swing_highs) and i < len(swing_lows):
                swing_high = swing_highs[i]
                swing_low = swing_lows[i]
                
                # Only consider if high came before low (chronologically)
                if swing_high['bars_ago'] > swing_low['bars_ago']:
                    fib_zones = self._calculate_fib_zones(
                        swing_start=swing_high['price'],
                        swing_end=swing_low['price'],
                        context='high_to_low',
                        current_price=current_price,
                        atr=atr,
                        max_distance_pct=max_distance_pct
                    )
                    zones.extend(fib_zones)
            
            # Context 2: Low → High (bearish retracement)
            if i < len(swing_lows) and i < len(swing_highs):
                swing_low = swing_lows[i]
                swing_high = swing_highs[i]
                
                # Only consider if low came before high (chronologically)
                if swing_low['bars_ago'] > swing_high['bars_ago']:
                    fib_zones = self._calculate_fib_zones(
                        swing_start=swing_low['price'],
                        swing_end=swing_high['price'],
                        context='low_to_high',
                        current_price=current_price,
                        atr=atr,
                        max_distance_pct=max_distance_pct
                    )
                    zones.extend(fib_zones)
        
        # Remove duplicate zones (same mid price within 0.05×ATR)
        zones = self._deduplicate_zones(zones, atr)
        
        return zones
    
    def _calculate_fib_zones(
        self,
        swing_start: float,
        swing_end: float,
        context: str,
        current_price: float,
        atr: float,
        max_distance_pct: float
    ) -> List[Dict]:
        """
        Calculate Fibonacci zones for a specific swing
        
        Args:
            swing_start: Starting price of swing
            swing_end: Ending price of swing
            context: 'high_to_low' or 'low_to_high'
            current_price: Current price
            atr: ATR value
            max_distance_pct: Max distance from current price
        
        Returns:
            List of Fib zone dicts
        """
        zones = []
        swing_range = abs(swing_end - swing_start)
        
        # Calculate each Fib level
        for fib_ratio, fib_name in self.fib_levels.items():
            # Calculate retracement price
            if context == 'high_to_low':
                # Retracing back up from low
                fib_price = swing_end + (swing_range * fib_ratio)
                zone_type = 'resistance' if fib_price > current_price else 'support'
            else:  # low_to_high
                # Retracing back down from high
                fib_price = swing_end - (swing_range * fib_ratio)
                zone_type = 'support' if fib_price < current_price else 'resistance'
            
            # Only include zones within max_distance_pct of current price
            distance_pct = abs(fib_price - current_price) / current_price
            if distance_pct > max_distance_pct:
                continue
            
            # Determine weight (core levels are stronger)
            weight = self.weight_core if fib_ratio in self.core_levels else self.weight_other
            
            # Create zone
            zone_width = self.zone_width_multiplier * atr
            zones.append({
                'type': zone_type,
                'low': fib_price - zone_width,
                'mid': fib_price,
                'high': fib_price + zone_width,
                'source': fib_name,
                'weight': weight,
                'context': context,
                'swing_start': swing_start,
                'swing_end': swing_end,
                'fib_ratio': fib_ratio
            })
        
        return zones
    
    def _deduplicate_zones(
        self,
        zones: List[Dict],
        atr: float,
        threshold_multiplier: float = 0.05
    ) -> List[Dict]:
        """
        Remove duplicate Fib zones (same price within threshold)
        
        Args:
            zones: List of zones
            atr: ATR value
            threshold_multiplier: Deduplication threshold (×ATR)
        
        Returns:
            Deduplicated list of zones
        """
        if not zones:
            return []
        
        # Sort by mid price
        zones.sort(key=lambda z: z['mid'])
        
        deduplicated = [zones[0]]
        threshold = threshold_multiplier * atr
        
        for zone in zones[1:]:
            # Check if too close to any existing zone
            is_duplicate = False
            for existing in deduplicated:
                if abs(zone['mid'] - existing['mid']) <= threshold:
                    # Keep the one with higher weight
                    if zone['weight'] > existing['weight']:
                        deduplicated.remove(existing)
                        deduplicated.append(zone)
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                deduplicated.append(zone)
        
        return deduplicated


# =============================================================================
# STANDALONE USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    """
    Test the Fibonacci builder module standalone
    
    Usage:
        python stock_analyzer/sr_engine/fibonacci_builder.py
    """
    print("="*70)
    print("FIBONACCI BUILDER MODULE - STANDALONE TEST")
    print("="*70)
    
    # Sample swing data (simulating SwingDetector output)
    swing_highs = [
        {'price': 110.0, 'bars_ago': 5, 'timestamp': '2024-10-25'},
        {'price': 108.5, 'bars_ago': 15, 'timestamp': '2024-10-15'},
        {'price': 112.0, 'bars_ago': 30, 'timestamp': '2024-09-30'},
    ]
    
    swing_lows = [
        {'price': 100.0, 'bars_ago': 2, 'timestamp': '2024-10-28'},
        {'price': 102.0, 'bars_ago': 10, 'timestamp': '2024-10-20'},
        {'price': 98.0, 'bars_ago': 25, 'timestamp': '2024-10-05'},
    ]
    
    current_price = 105.0
    atr = 2.5
    
    print(f"\nINPUT DATA:")
    print(f"  Current Price: ${current_price:.2f}")
    print(f"  ATR: ${atr:.2f}")
    print(f"  Recent Swing Highs: {len(swing_highs)}")
    print(f"  Recent Swing Lows: {len(swing_lows)}")
    
    # Most recent swing context: High ($110) → Low ($100) = bullish retracement
    print(f"\nSWING CONTEXT:")
    print(f"  Most recent: ${swing_highs[0]['price']:.2f} (high) → ${swing_lows[0]['price']:.2f} (low)")
    print(f"  Swing range: ${swing_highs[0]['price'] - swing_lows[0]['price']:.2f}")
    
    # Initialize builder
    builder = FibonacciBuilder()
    
    # Create dummy dataframe (not used in this example)
    daily_df = pd.DataFrame()
    
    # Build Fibonacci zones
    print(f"\nBUILDING FIBONACCI ZONES...")
    fib_zones = builder.build_fibonacci_zones(
        daily_df,
        swing_highs,
        swing_lows,
        current_price,
        atr
    )
    
    print(f"\nFIBONACCI ZONES ({len(fib_zones)} zones):")
    print("="*70)
    
    # Expected Fib levels for $110 → $100 swing:
    # 0.236: $100 + ($10 × 0.236) = $102.36
    # 0.382: $100 + ($10 × 0.382) = $103.82
    # 0.500: $100 + ($10 × 0.500) = $105.00 ← near current price!
    # 0.618: $100 + ($10 × 0.618) = $106.18
    # 0.786: $100 + ($10 × 0.786) = $107.86
    
    for i, zone in enumerate(fib_zones, 1):
        print(f"\n{i}. {zone['type'].upper()} @ ${zone['mid']:.2f}")
        print(f"   Range: ${zone['low']:.2f} - ${zone['high']:.2f}")
        print(f"   Source: {zone['source']} (ratio: {zone['fib_ratio']:.3f})")
        print(f"   Weight: {zone['weight']}")
        print(f"   Context: {zone['context']}")
        print(f"   Swing: ${zone['swing_start']:.2f} → ${zone['swing_end']:.2f}")
        
        distance = abs(zone['mid'] - current_price)
        distance_pct = (distance / current_price) * 100
        print(f"   Distance from price: ${distance:.2f} ({distance_pct:.1f}%)")
    
    # Test validation
    print("\n" + "="*70)
    print("VALIDATION CHECKS:")
    print("="*70)
    
    # Check 0.5 level calculation
    expected_fib_50 = swing_lows[0]['price'] + (swing_highs[0]['price'] - swing_lows[0]['price']) * 0.5
    fib_50_zone = [z for z in fib_zones if z['source'] == 'Fib_0.5']
    
    if fib_50_zone:
        actual = fib_50_zone[0]['mid']
        print(f"✓ Fib 0.5 Level:")
        print(f"  Expected: ${expected_fib_50:.2f}")
        print(f"  Actual: ${actual:.2f}")
        print(f"  Match: {abs(actual - expected_fib_50) < 0.01}")
    
    # Check zone width
    zone_width = builder.zone_width_multiplier * atr
    print(f"\n✓ Zone Width:")
    print(f"  ATR multiplier: {builder.zone_width_multiplier}")
    print(f"  Expected width: ±${zone_width:.2f}")
    if fib_zones:
        actual_width = fib_zones[0]['high'] - fib_zones[0]['mid']
        print(f"  Actual width: ±${actual_width:.2f}")
        print(f"  Match: {abs(actual_width - zone_width) < 0.01}")
    
    # Check weights
    core_zones = [z for z in fib_zones if z['fib_ratio'] in builder.core_levels]
    other_zones = [z for z in fib_zones if z['fib_ratio'] not in builder.core_levels]
    
    print(f"\n✓ Weight Assignment:")
    print(f"  Core levels (0.5, 0.618, 0.786): {len(core_zones)} zones, weight={builder.weight_core}")
    print(f"  Other levels (0.236, 0.382): {len(other_zones)} zones, weight={builder.weight_other}")
    
    print("\n" + "="*70)
    print("✅ FIBONACCI BUILDER MODULE TESTS COMPLETE")
    print("="*70)
    print("\nREADY FOR INTEGRATION:")
    print("  - Import: from stock_analyzer.sr_engine.fibonacci_builder import FibonacciBuilder")
    print("  - Usage: builder = FibonacciBuilder(config)")
    print("  - Call: zones = builder.build_fibonacci_zones(df, highs, lows, price, atr)")
    print("="*70)
