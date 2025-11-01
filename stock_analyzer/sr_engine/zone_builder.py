"""
Zone Builder Module (v5.0)

Orchestrates all S/R seed detectors and builds comprehensive zone list.
Coordinates: Swings, Fibonacci, Diagonals, Gaps, Moving Averages.
Returns merged zones with confluence scores.

Author: Stock Analyzer v5.0
Dependencies: All S/R detectors, confluence_merger
"""

import pandas as pd
from typing import List, Dict, Optional
import sys
import os

# Add project root to path for standalone execution
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from stock_analyzer.sr_engine.swing_detector import SwingDetector
from stock_analyzer.sr_engine.fibonacci_builder import FibonacciBuilder
from stock_analyzer.sr_engine.diagonal_detector import DiagonalDetector
from stock_analyzer.sr_engine.gap_detector import GapDetector
from stock_analyzer.sr_engine.confluence_merger import ConfluenceMerger
from stock_analyzer.utils.technical_indicators import TechnicalIndicators


class ZoneBuilder:
    """
    Orchestrate all S/R seed detectors to build comprehensive zone list
    
    Process:
        1. Detect swing points (swing_detector)
        2. Build Fibonacci zones (fibonacci_builder)
        3. Detect diagonal trendlines (diagonal_detector)
        4. Detect gap zones (gap_detector)
        5. Add moving average zones (SMA/EMA)
        6. Merge overlapping zones (confluence_merger)
        7. Calculate final confluence scores
    """
    
    def __init__(self, config=None):
        """
        Initialize zone builder with all detectors
        
        Args:
            config: Configuration module
        """
        self.config = config
        
        # Initialize all detectors
        self.swing_detector = SwingDetector()
        self.fibonacci_builder = FibonacciBuilder(config)
        self.diagonal_detector = DiagonalDetector(config)
        self.gap_detector = GapDetector(config=config)
        self.confluence_merger = ConfluenceMerger(config)
        
        # Load weights from config
        if config and hasattr(config, 'WEIGHTS'):
            self.weights = config.WEIGHTS
        else:
            self.weights = {
                'Fib_core': 3,
                'Fib_other': 2,
                'Swing': 2,
                'Diagonal': 2,
                'SMA': 2,
                'EMA20_SR': 1,
                'GapEdge': 2
            }
    
    def build_all_zones(
        self,
        symbol: str,
        daily_df: pd.DataFrame,
        hourly_df: Optional[pd.DataFrame],
        current_price: float,
        atr: float,
        market_sentiment: Optional[Dict] = None,
        stock_regime: Optional[str] = None
    ) -> List[Dict]:
        """
        Build zones from all sources
        
        Process:
            1. Detect swings
            2. Build Fibonacci zones
            3. Detect diagonals
            4. Detect gaps
            5. Add MA zones
            6. Merge overlapping zones
            7. Calculate final scores
        
        Args:
            symbol: Stock symbol
            daily_df: Daily OHLC DataFrame
            hourly_df: Hourly OHLC DataFrame (optional, for gaps)
            current_price: Current stock price
            atr: ATR(14) value
            market_sentiment: Market sentiment dict (optional)
            stock_regime: Stock regime 'bullish'/'bearish' (optional)
        
        Returns:
            List of merged zones with confluence scores
        """
        print(f"\n{'='*70}")
        print(f"BUILDING S/R ZONES FOR {symbol}")
        print(f"{'='*70}")
        print(f"Current Price: ${current_price:.2f}")
        print(f"ATR: ${atr:.2f}")
        
        all_zones = []
        
        # Step 1: Detect swings
        print("\n[1/6] Detecting swing points...")
        swing_highs = self.swing_detector.detect_swing_highs(daily_df)
        swing_lows = self.swing_detector.detect_swing_lows(daily_df)
        print(f"  Found {len(swing_highs)} swing highs, {len(swing_lows)} swing lows")
        
        # Add swing zones directly
        swing_zones = self._build_swing_zones(swing_highs, swing_lows, current_price, atr)
        all_zones.extend(swing_zones)
        print(f"  Created {len(swing_zones)} swing zones")
        
        # Step 2: Build Fibonacci zones
        print("\n[2/6] Building Fibonacci zones...")
        fib_zones = self.fibonacci_builder.build_fibonacci_zones(
            daily_df,
            swing_highs,
            swing_lows,
            current_price,
            atr
        )
        all_zones.extend(fib_zones)
        print(f"  Created {len(fib_zones)} Fibonacci zones")
        
        # Step 3: Detect diagonals
        print("\n[3/6] Detecting diagonal trendlines...")
        diagonal_zones = self.diagonal_detector.detect_diagonals(
            daily_df,
            swing_highs,
            swing_lows,
            current_price,
            atr
        )
        all_zones.extend(diagonal_zones)
        print(f"  Created {len(diagonal_zones)} diagonal zones")
        
        # Step 4: Detect gaps (if hourly data available)
        if hourly_df is not None and len(hourly_df) > 0:
            print("\n[4/6] Detecting gap zones...")
            gap_zones = self._build_gap_zones(hourly_df, current_price, atr)
            all_zones.extend(gap_zones)
            print(f"  Created {len(gap_zones)} gap zones")
        else:
            print("\n[4/6] Skipping gaps (no hourly data)")
        
        # Step 5: Add MA zones
        print("\n[5/6] Building moving average zones...")
        ma_zones = self._build_ma_zones(daily_df, current_price, atr)
        all_zones.extend(ma_zones)
        print(f"  Created {len(ma_zones)} MA zones")
        
        # Step 6: Merge overlapping zones
        print(f"\n[6/6] Merging zones (threshold: {self.confluence_merger.merge_threshold}×ATR)...")
        print(f"  Input: {len(all_zones)} zones")
        
        merged_zones = self.confluence_merger.merge_zones(
            all_zones,
            atr,
            current_price
        )
        print(f"  Output: {len(merged_zones)} merged zones")
        
        # Step 7: Calculate final scores
        print("\nCalculating confluence scores...")
        scored_zones = self.confluence_merger.score_all_zones(
            merged_zones,
            current_price,
            atr,
            market_sentiment,
            stock_regime
        )
        
        # Add symbol to each zone
        for zone in scored_zones:
            zone['symbol'] = symbol
            zone['zone_id'] = f"{symbol}_{zone['type']}_{zone['mid']:.2f}"
        
        print(f"\n{'='*70}")
        print(f"ZONE BUILDING COMPLETE: {len(scored_zones)} zones")
        print(f"{'='*70}")
        
        return scored_zones
    
    def _build_swing_zones(
        self,
        swing_highs: List[Dict],
        swing_lows: List[Dict],
        current_price: float,
        atr: float
    ) -> List[Dict]:
        """
        Build zones from swing highs and lows
        """
        zones = []
        zone_width = 0.15 * atr  # ±0.15×ATR
        
        # Add swing high zones (resistance)
        for swing in swing_highs[:5]:  # Top 5
            if abs(swing['price'] - current_price) / current_price <= 0.20:  # Within 20%
                zones.append({
                    'type': 'resistance' if swing['price'] > current_price else 'support',
                    'low': swing['price'] - zone_width,
                    'mid': swing['price'],
                    'high': swing['price'] + zone_width,
                    'source': 'Swing',
                    'weight': self.weights.get('Swing', 2)
                })
        
        # Add swing low zones (support)
        for swing in swing_lows[:5]:  # Top 5
            if abs(swing['price'] - current_price) / current_price <= 0.20:  # Within 20%
                zones.append({
                    'type': 'support' if swing['price'] < current_price else 'resistance',
                    'low': swing['price'] - zone_width,
                    'mid': swing['price'],
                    'high': swing['price'] + zone_width,
                    'source': 'Swing',
                    'weight': self.weights.get('Swing', 2)
                })
        
        return zones
    
    def _build_gap_zones(
        self,
        hourly_df: pd.DataFrame,
        current_price: float,
        atr: float
    ) -> List[Dict]:
        """
        Build zones from gap edges
        """
        zones = []
        zone_width = 0.15 * atr
        
        # Detect gaps
        gaps = self.gap_detector.detect_gaps(hourly_df, current_price, atr)
        
        # Create zones at gap edges
        for gap in gaps[:8]:  # Top 8 gaps
            # Only use unfilled or recently filled gaps
            if not gap['filled'] or gap['bars_ago'] < 50:
                # Gap edge zone
                gap_mid = gap['gap_mid']
                
                zones.append({
                    'type': 'support' if gap_mid < current_price else 'resistance',
                    'low': gap_mid - zone_width,
                    'mid': gap_mid,
                    'high': gap_mid + zone_width,
                    'source': 'GapEdge',
                    'weight': gap.get('weight', self.weights.get('GapEdge', 2))
                })
        
        return zones
    
    def _build_ma_zones(
        self,
        daily_df: pd.DataFrame,
        current_price: float,
        atr: float
    ) -> List[Dict]:
        """
        Build zones from moving averages (EMA20, SMA50, SMA100, SMA200)
        """
        zones = []
        zone_width = 0.15 * atr
        
        if len(daily_df) < 200:
            return zones
        
        # EMA20
        ema20_series = TechnicalIndicators.calculate_ema(daily_df, period=20)
        ema20 = ema20_series.iloc[-1]
        
        if abs(ema20 - current_price) / current_price <= 0.20:
            zones.append({
                'type': 'support' if ema20 < current_price else 'resistance',
                'low': ema20 - zone_width,
                'mid': ema20,
                'high': ema20 + zone_width,
                'source': 'EMA20_SR',
                'weight': self.weights.get('EMA20_SR', 1)
            })
        
        # SMA50, SMA100, SMA200
        for period in [50, 100, 200]:
            if len(daily_df) < period:
                continue
            
            sma_series = TechnicalIndicators.calculate_sma(daily_df, period=period)
            sma = sma_series.iloc[-1]
            
            if abs(sma - current_price) / current_price <= 0.20:
                zones.append({
                    'type': 'support' if sma < current_price else 'resistance',
                    'low': sma - zone_width,
                    'mid': sma,
                    'high': sma + zone_width,
                    'source': f'SMA{period}' if period != 50 else 'SMA',
                    'weight': self.weights.get('SMA', 2)
                })
        
        return zones
    
    def get_nearest_zones(
        self,
        zones: List[Dict],
        current_price: float,
        max_zones: int = 5
    ) -> Dict[str, List[Dict]]:
        """
        Get nearest support and resistance zones
        
        Args:
            zones: List of all zones
            current_price: Current price
            max_zones: Max zones per type to return
        
        Returns:
            Dict with 'support' and 'resistance' zone lists
        """
        support_zones = [z for z in zones if z['mid'] < current_price and z['type'] == 'support']
        resistance_zones = [z for z in zones if z['mid'] > current_price and z['type'] == 'resistance']
        
        # Sort by distance
        support_zones.sort(key=lambda z: current_price - z['mid'])
        resistance_zones.sort(key=lambda z: z['mid'] - current_price)
        
        return {
            'support': support_zones[:max_zones],
            'resistance': resistance_zones[:max_zones]
        }


# =============================================================================
# STANDALONE USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    """
    Test the zone builder module standalone
    
    Usage:
        python stock_analyzer/sr_engine/zone_builder.py
    """
    print("="*70)
    print("ZONE BUILDER MODULE - STANDALONE TEST")
    print("="*70)
    
    from stock_analyzer.utils import config
    import numpy as np
    from datetime import datetime, timedelta
    
    # Create sample daily data
    print("\nGenerating sample data...")
    dates = pd.date_range(end=datetime.now(), periods=200, freq='D')
    
    # Uptrend with swings
    trend = np.linspace(90, 110, 200)
    noise = np.random.normal(0, 2, 200)
    swings = 5 * np.sin(np.linspace(0, 4*np.pi, 200))
    closes = trend + swings + noise
    
    daily_df = pd.DataFrame({
        'Date': dates,
        'Open': closes * 0.99,
        'High': closes * 1.01,
        'Low': closes * 0.98,
        'Close': closes,
        'Volume': np.random.randint(1000000, 5000000, 200)
    })
    daily_df.set_index('Date', inplace=True)
    
    current_price = closes[-1]
    atr = TechnicalIndicators.calculate_atr(daily_df, period=14)
    
    # Test zone building
    builder = ZoneBuilder(config)
    
    zones = builder.build_all_zones(
        symbol='TEST',
        daily_df=daily_df,
        hourly_df=None,  # Skip gaps for this test
        current_price=current_price,
        atr=atr,
        market_sentiment={'combined_regime': 'bullish', 'vol_multiplier': 1.1},
        stock_regime='bullish'
    )
    
    # Display results
    print(f"\nTOP 10 ZONES (by score):")
    print("-"*70)
    
    for i, zone in enumerate(zones[:10], 1):
        print(f"\n{i}. {zone['type'].upper()} @ ${zone['mid']:.2f}")
        print(f"   Range: ${zone['low']:.2f} - ${zone['high']:.2f}")
        print(f"   Sources: {', '.join(zone['sources'])}")
        print(f"   Score: {zone['final_score']:.2f}")
        print(f"   Distance: ${zone['distance_from_price']:.2f} ({zone['distance_atr']:.2f}×ATR)")
        
        if zone.get('proximity_boost'):
            print(f"   ✓ Proximity boost")
        if zone.get('index_aligned'):
            print(f"   ✓ Index aligned")
    
    # Get nearest zones
    nearest = builder.get_nearest_zones(zones, current_price, max_zones=3)
    
    print(f"\n{'='*70}")
    print("NEAREST ZONES")
    print("="*70)
    
    print(f"\nSupport (below ${current_price:.2f}):")
    for zone in nearest['support']:
        print(f"  ${zone['mid']:.2f} (score: {zone['final_score']:.2f})")
    
    print(f"\nResistance (above ${current_price:.2f}):")
    for zone in nearest['resistance']:
        print(f"  ${zone['mid']:.2f} (score: {zone['final_score']:.2f})")
    
    print("\n" + "="*70)
    print("✓ ZONE BUILDER MODULE TESTS COMPLETE")
    print("="*70)
    print("\nREADY FOR INTEGRATION:")
    print("  - Import: from stock_analyzer.sr_engine.zone_builder import ZoneBuilder")
    print("  - Usage: builder = ZoneBuilder(config)")
    print("  - Call: zones = builder.build_all_zones(...)")
    print("="*70)
