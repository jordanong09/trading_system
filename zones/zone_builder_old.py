"""
MVP 4.0 Zone Engine
- Builds ATR-scaled zones (±0.30×ATR bands)
- Detects multiple seed types (EMA20, SMAs, round numbers)
- Merges overlapping zones
- Calculates base strength with EMA20 slope gating
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import math

from indicators.swing_detector import SwingDetector
from indicators.gap_detector import GapDetector
from indicators.volume_profile import VolumeProfile


class ZoneEngine:
    """
    Constructs support/resistance zones using ATR-scaled bands
    """
    
    def __init__(self, config: Dict):
        """
        Initialize zone engine with configuration
        
        Args:
            config: Dict with zone parameters
                - atr_multiplier: Band width (default 0.30)
                - max_distance_atr: Max trigger distance (default 0.35)
                - component_weights: Dict of seed type weights
        """
        self.atr_multiplier = config.get('atr_multiplier', 0.30)
        self.max_distance_atr = config.get('max_distance_atr', 0.35)
        self.stack_bonus = config.get('stack_bonus', 0.5)
        self.swing_detector = SwingDetector(lookback=5, max_swings=10)
        self.gap_detector = GapDetector(min_gap_pct=0.2, max_gaps=8)
        self.volume_profile = VolumeProfile(num_bins=30, hvn_threshold_pct=80, max_hvn=5)
        
        # Component weights for confluence scoring
        self.weights = config.get('component_weights', {
            'ema20': 2.0,
            'sma50': 0.8,
            'sma100': 0.8,
            'sma200': 0.8,
            'round_number': 0.3,
            'swing_high': 1.5,
            'swing_low': 1.5,
            'gap_edge': 1.2,
            'hvn': 1.3
        })

    def _collect_p1_seeds(self, hourly_df: pd.DataFrame, current_price: float) -> List[Dict]:
        """
        Collect P1 feature seeds from hourly data
        
        Args:
            hourly_df: Hourly OHLCV data (130 bars)
            current_price: Current stock price
            
        Returns:
            List of seed dicts
        """
        
        # CRITICAL: Filter hourly data to remove outliers FIRST
        # Only keep bars within ±15% of current price
        price_lower = current_price * 0.85
        price_upper = current_price * 1.15
        
        print(f"\n   🔍 P1 FILTERING:")
        print(f"      Valid range: ${price_lower:.2f} - ${price_upper:.2f} (±15%)")
        
        hourly_df_filtered = hourly_df[
            (hourly_df['Low'] >= price_lower) & 
            (hourly_df['High'] <= price_upper)
        ].copy()
        
        print(f"      Before filter: {len(hourly_df)} bars (${hourly_df['Low'].min():.2f}-${hourly_df['High'].max():.2f})")
        print(f"      After filter: {len(hourly_df_filtered)} bars (${hourly_df_filtered['Low'].min():.2f}-${hourly_df_filtered['High'].max():.2f})")
        
        if len(hourly_df_filtered) < 20:
            print(f"      ⚠️  Too few bars after filtering, skipping P1")
            return []
        
        p1_seeds = []
        
        # P1: Swing highs/lows
        if len(hourly_df_filtered) >= 20:
            try:
                swings = self.swing_detector.detect_all_swings(hourly_df_filtered)
                
                valid_highs = 0
                valid_lows = 0
                
                for swing_high in swings['swing_highs']:
                    # Validate: within 10% of current price
                    distance_pct = abs(swing_high['price'] - current_price) / current_price
                    if distance_pct <= 0.10:
                        p1_seeds.append({
                            'price': swing_high['price'],
                            'type': 'swing_high',
                            'weight': self.weights.get('swing_high', 1.5)
                        })
                        valid_highs += 1
                
                for swing_low in swings['swing_lows']:
                    # Validate: within 10% of current price
                    distance_pct = abs(swing_low['price'] - current_price) / current_price
                    if distance_pct <= 0.10:
                        p1_seeds.append({
                            'price': swing_low['price'],
                            'type': 'swing_low',
                            'weight': self.weights.get('swing_low', 1.5)
                        })
                        valid_lows += 1
                
                if valid_highs > 0 or valid_lows > 0:
                    print(f"      ✅ Valid swings: {valid_highs} highs, {valid_lows} lows")
                
            except Exception as e:
                print(f"      ⚠️  Swing detection error: {e}")
        
        # P1: Gap edges
        if len(hourly_df_filtered) >= 10:
            try:
                gap_edges = self.gap_detector.get_gap_edges(hourly_df_filtered, current_price)
                
                valid_gaps = 0
                for gap_support in gap_edges['support']:
                    if abs(gap_support - current_price) / current_price <= 0.10:
                        p1_seeds.append({
                            'price': gap_support,
                            'type': 'gap_edge',
                            'weight': self.weights.get('gap_edge', 1.2)
                        })
                        valid_gaps += 1
                
                for gap_resistance in gap_edges['resistance']:
                    if abs(gap_resistance - current_price) / current_price <= 0.10:
                        p1_seeds.append({
                            'price': gap_resistance,
                            'type': 'gap_edge',
                            'weight': self.weights.get('gap_edge', 1.2)
                        })
                        valid_gaps += 1
                
                if valid_gaps > 0:
                    print(f"      ✅ Valid gaps: {valid_gaps}")
                    
            except Exception as e:
                print(f"      ⚠️  Gap detection error: {e}")
        
        # P1: High Volume Nodes
        if len(hourly_df_filtered) >= 30:
            try:
                hvn_levels = self.volume_profile.get_hvn_levels(hourly_df_filtered, current_price)
                
                valid_hvn = 0
                for hvn_support in hvn_levels['support']:
                    if abs(hvn_support - current_price) / current_price <= 0.10:
                        p1_seeds.append({
                            'price': hvn_support,
                            'type': 'hvn',
                            'weight': self.weights.get('hvn', 1.3)
                        })
                        valid_hvn += 1
                
                for hvn_resistance in hvn_levels['resistance']:
                    if abs(hvn_resistance - current_price) / current_price <= 0.10:
                        p1_seeds.append({
                            'price': hvn_resistance,
                            'type': 'hvn',
                            'weight': self.weights.get('hvn', 1.3)
                        })
                        valid_hvn += 1
                
                if valid_hvn > 0:
                    print(f"      ✅ Valid HVN: {valid_hvn}")
                    
            except Exception as e:
                print(f"      ⚠️  HVN detection error: {e}")
        
        return p1_seeds
    
    
    def identify_seeds(self, indicators: Dict, current_price: float) -> List[Dict]:
        """
        Identify all potential zone seeds from daily indicators
        
        For Monday MVP, we focus on:
        - EMA20 (primary dynamic S/R)
        - SMA50/100/200 (trend-based S/R)
        - Round numbers ($5/$10 increments)
        
        Args:
            indicators: Dict from TechnicalIndicators.calculate_all_indicators()
            current_price: Current stock price
            
        Returns:
            List of seed dicts with {price, type, weight}
        """
        seeds = []
        
        # EMA20 - Primary dynamic S/R
        if indicators.get('ema20') is not None:
            ema20 = indicators['ema20']
            # Validate: reject if >30% from current price
            if abs(ema20 - current_price) / current_price <= 0.30:
                seeds.append({
                    'price': ema20,
                    'type': 'ema20',
                    'weight': self.weights['ema20'],
                    'metadata': indicators.get('ema20_slope', {})
                })
            else:
                print(f"      ⚠️ Rejected EMA20 ${ema20:.2f} (too far from price)")
        
        # SMA50
        if indicators.get('sma50') is not None:
            sma50 = indicators['sma50']
            # Validate: reject if >30% from current price
            if abs(sma50 - current_price) / current_price <= 0.30:
                seeds.append({
                    'price': sma50,
                    'type': 'sma50',
                    'weight': self.weights['sma50'],
                    'metadata': {}
                })
            else:
                print(f"      ⚠️ Rejected SMA50 ${sma50:.2f} (too far from price)")
        
        # SMA100
        if indicators.get('sma100') is not None:
            sma100 = indicators['sma100']
            # Validate: reject if >30% from current price
            if abs(sma100 - current_price) / current_price <= 0.30:
                seeds.append({
                    'price': sma100,
                    'type': 'sma100',
                    'weight': self.weights['sma100'],
                    'metadata': {}
                })
            else:
                print(f"      ⚠️ Rejected SMA100 ${sma100:.2f} (too far from price)")
        
        # SMA200
        if indicators.get('sma200') is not None:
            sma200 = indicators['sma200']
            # Validate: reject if >30% from current price
            if abs(sma200 - current_price) / current_price <= 0.30:
                seeds.append({
                    'price': sma200,
                    'type': 'sma200',
                    'weight': self.weights['sma200'],
                    'metadata': {}
                })
            else:
                print(f"      ⚠️ Rejected SMA200 ${sma200:.2f} (too far from price)")
        
        # Round numbers - $5 increments for stocks under $100, $10 above
        round_seeds = self._identify_round_numbers(current_price)
        seeds.extend(round_seeds)
        
        return seeds
    
    def _identify_round_numbers(self, current_price: float) -> List[Dict]:
        """
        Identify nearby round number levels
        
        Args:
            current_price: Current stock price
            
        Returns:
            List of round number seeds
        """
        seeds = []
        
        # Determine increment based on price
        if current_price < 50:
            increment = 5
            range_multiplier = 3  # Check ±3 increments
        elif current_price < 100:
            increment = 5
            range_multiplier = 2
        else:
            increment = 10
            range_multiplier = 2
        
        # Find round numbers within range
        base = (current_price // increment) * increment
        
        for i in range(-range_multiplier, range_multiplier + 1):
            round_price = base + (i * increment)
            
            if round_price > 0:  # Only positive prices
                # Only include if within reasonable distance (±10% of price, stricter)
                distance_pct = abs(round_price - current_price) / current_price
                if distance_pct <= 0.10:
                    seeds.append({
                        'price': round_price,
                        'type': 'round_number',
                        'weight': self.weights['round_number'],
                        'metadata': {'increment': increment}
                    })
        
        return seeds
    
    def create_zone_bands(self, seed: Dict, atr: float) -> Dict:
        """
        Create ATR-scaled band around seed price
        
        Zone width = ±0.30 × ATR(14D)
        
        Args:
            seed: Seed dict with price, type, weight
            atr: ATR(14D) value
            
        Returns:
            Zone dict with low, mid, high, components
        """
        seed_price = seed['price']
        half_width = self.atr_multiplier * atr
        
        zone = {
            'low': seed_price - half_width,
            'mid': seed_price,
            'high': seed_price + half_width,
            'components': [seed['type']],
            'component_weights': {seed['type']: seed['weight']},
            'metadata': seed.get('metadata', {})
        }
        
        return zone
    
    def merge_overlapping_zones(self, zones: List[Dict]) -> List[Dict]:
        """
        Merge zones that overlap
        
        Merging rules:
        1. If two zones overlap, merge them
        2. Union their components
        3. New mid = weighted average based on component weights
        4. New bands = mid ± 0.30×ATR
        
        Args:
            zones: List of zone dicts
            
        Returns:
            List of merged zones
        """
        if len(zones) <= 1:
            return zones
        
        # Sort zones by mid price
        zones = sorted(zones, key=lambda z: z['mid'])
        
        merged = []
        current = zones[0].copy()
        
        for next_zone in zones[1:]:
            # Check if zones overlap
            if self._zones_overlap(current, next_zone):
                # Merge zones
                current = self._merge_two_zones(current, next_zone)
            else:
                # No overlap, save current and move to next
                merged.append(current)
                current = next_zone.copy()
        
        # Don't forget the last zone
        merged.append(current)
        
        return merged
    
    def _zones_overlap(self, zone1: Dict, zone2: Dict) -> bool:
        """Check if two zones overlap"""
        return not (zone1['high'] < zone2['low'] or zone2['high'] < zone1['low'])
    
    def _merge_two_zones(self, zone1: Dict, zone2: Dict) -> Dict:
        """
        Merge two overlapping zones with FIXED weight calculation
        
        This prevents merged zones from exploding to unrealistic prices
        """
        # Combine components
        all_components = list(set(zone1['components'] + zone2['components']))
        
        # Combine weights - take max weight per component type
        combined_weights = zone1['component_weights'].copy()
        for comp, weight in zone2['component_weights'].items():
            if comp in combined_weights:
                combined_weights[comp] = max(combined_weights[comp], weight)
            else:
                combined_weights[comp] = weight
        
        # FIXED: Calculate weighted average with matching numerator/denominator
        w1 = sum(zone1['component_weights'].values())  # Total weight of zone1
        w2 = sum(zone2['component_weights'].values())  # Total weight of zone2
        total_weight = w1 + w2  # Use sum of per-zone weights (matches numerator)
        
        weighted_sum = zone1['mid'] * w1 + zone2['mid'] * w2
        new_mid = weighted_sum / total_weight
        
        # SAFETY RAIL 1: Clamp merged midpoint between input zones
        # This prevents arithmetic errors from creating zones outside valid range
        min_mid = min(zone1['mid'], zone2['mid'])
        max_mid = max(zone1['mid'], zone2['mid'])
        new_mid = max(min_mid, min(new_mid, max_mid))
        
        # Recalculate bands (use average of the two ATR widths)
        avg_width = ((zone1['high'] - zone1['low']) + (zone2['high'] - zone2['low'])) / 4
        
        # Merge metadata (prefer zone1's metadata if conflict)
        merged_metadata = zone1.get('metadata', {}).copy()
        merged_metadata.update(zone2.get('metadata', {}))
        merged_metadata['merged_from'] = [
            f"{zone1['mid']:.2f}",
            f"{zone2['mid']:.2f}"
        ]
        
        return {
            'low': new_mid - avg_width,
            'mid': new_mid,
            'high': new_mid + avg_width,
            'components': all_components,
            'component_weights': combined_weights,
            'metadata': merged_metadata
        }
    
    def calculate_base_strength(self, zone: Dict, indicators: Dict, 
                                atr: float, current_price: float) -> float:
        """
        Calculate base zone strength (0-6 points)
        
        Base strength formula:
        1. Sum component weights
        2. Apply EMA20 slope factor (if EMA20 in components)
        3. Add stack bonus if MAs aligned
        4. Clamp to 0-6 range
        
        Args:
            zone: Zone dict with components and weights
            indicators: Technical indicators
            atr: ATR(14D)
            current_price: Current price
            
        Returns:
            Base strength score (0-6)
        """
        # Start with sum of component weights
        base_strength = sum(zone['component_weights'].values())
        
        # Apply EMA20 slope factor
        if 'ema20' in zone['components']:
            ema20_slope = indicators.get('ema20_slope', {})
            slope_factor = ema20_slope.get('slope_factor', 1.0)
            
            # Find EMA20 weight and apply factor
            ema20_weight = zone['component_weights'].get('ema20', 0)
            adjusted_ema20_weight = ema20_weight * slope_factor
            
            # Replace original EMA20 weight with adjusted
            base_strength = base_strength - ema20_weight + adjusted_ema20_weight
        
        # Add stack bonus if MAs aligned
        if indicators.get('stack_aligned', False):
            base_strength += self.stack_bonus
        
        # Clamp to 0-6 range
        base_strength = max(0, min(6, base_strength))
        
        return base_strength
    
    def determine_zone_type(self, zone: Dict, current_price: float) -> str:
        """
        Determine if zone is support or resistance
        
        Args:
            zone: Zone dict
            current_price: Current price
            
        Returns:
            'support' or 'resistance'
        """
        if zone['mid'] < current_price:
            return 'support'
        else:
            return 'resistance'
    
    
    
    def build_zones(self, symbol: str, indicators: Dict, current_price: float, atr: float, 
                hourly_df: pd.DataFrame = None) -> List[Dict]: # type: ignore
        """
        Main zone construction pipeline
        
        Steps:
        1. Identify seeds (daily indicators + P1 hourly features)
        2. Create ATR-scaled bands
        3. Merge overlapping zones
        4. Filter outlier zones (post-merge safety)
        5. Calculate base strength
        6. Determine support/resistance type
        
        Args:
            symbol: Stock symbol
            indicators: Technical indicators dict
            current_price: Current stock price
            atr: ATR(14D) value
            hourly_df: Hourly OHLCV data for P1 features (optional)
        
        Returns:
            List of constructed zones
        """
        if atr is None or atr <= 0:
            return []
        
        # Step 1: Identify seeds from daily indicators
        seeds = self.identify_seeds(indicators, current_price)
        
        if not seeds:
            seeds = []  # Initialize empty list if no daily seeds
        
        # Step 1b: Add P1 seeds from hourly data
        if hourly_df is not None:
            p1_seeds = self._collect_p1_seeds(hourly_df, current_price)
            seeds.extend(p1_seeds)
            print(f"   ✅ Added {len(p1_seeds)} P1 seeds from hourly data")
        
        if not seeds:
            return []
        
        # Step 2: Create bands
        zones = []
        for seed in seeds:
            zone = self.create_zone_bands(seed, atr)
            zones.append(zone)
        
        # Step 3: Merge overlapping zones
        merged_zones = self.merge_overlapping_zones(zones)
        
        # SAFETY RAIL 2: Filter out merged zones that drifted too far from price
        print(f"   🔍 Filtering merged zones...")
        valid_zones = []
        rejected_count = 0
        for zone in merged_zones:
            distance_pct = abs(zone['mid'] - current_price) / current_price
            if distance_pct <= 0.25:  # Within 25% of current price
                valid_zones.append(zone)
            else:
                rejected_count += 1
                if rejected_count <= 3:  # Only show first 3 rejections
                    print(f"      ❌ Rejected merged zone ${zone['mid']:.2f} ({distance_pct*100:.1f}% from price)")
        
        if rejected_count > 3:
            print(f"      ❌ ... and {rejected_count - 3} more rejected zones")
        
        merged_zones = valid_zones
        print(f"   ✅ {len(merged_zones)} zones after outlier filter")
        
        # Step 4: Calculate strength and finalize
        final_zones = []
        
        for i, zone in enumerate(merged_zones):
            base_strength = self.calculate_base_strength(zone, indicators, atr, current_price)
            zone_type = self.determine_zone_type(zone, current_price)
            
            # Create final zone object
            zone_id = f"{symbol}_zn_{zone_type}_{i}_{datetime.now().strftime('%Y%m%d')}"
            
            final_zone = {
                'zone_id': zone_id,
                'symbol': symbol,
                'type': zone_type,
                'low': zone['low'],
                'mid': zone['mid'],
                'high': zone['high'],
                'components': zone['components'],
                'strength': base_strength,
                'metadata': {
                    'atr14d': atr,
                    'ema20_slope': indicators.get('ema20_slope', {}),
                    'stack_aligned': indicators.get('stack_aligned', False),
                    'component_weights': zone['component_weights']
                },
                'created_at': datetime.now().isoformat()
            }
            
            final_zones.append(final_zone)
        
        return final_zones
    
    def get_zones_near_price(self, zones: List[Dict], current_price: float, 
                            atr: float) -> List[Dict]:
        """
        Filter zones that are within trigger distance of current price
        
        Max distance = 0.35 × ATR(14D)
        
        Args:
            zones: List of all zones
            current_price: Current price
            atr: ATR(14D)
            
        Returns:
            Zones within trigger range
        """
        max_distance = self.max_distance_atr * atr
        
        nearby_zones = []
        
        for zone in zones:
            # Calculate distance to zone
            if current_price < zone['low']:
                # Price below zone
                distance = zone['low'] - current_price
            elif current_price > zone['high']:
                # Price above zone
                distance = current_price - zone['high']
            else:
                # Price inside zone
                distance = 0
            
            # Check if within range
            distance_atr = distance / atr
            
            if distance_atr <= self.max_distance_atr:
                zone_copy = zone.copy()
                zone_copy['distance_atr'] = distance_atr
                zone_copy['distance_price'] = distance
                nearby_zones.append(zone_copy)
        
        # Sort by distance (closest first)
        nearby_zones = sorted(nearby_zones, key=lambda z: z['distance_atr'])
        
        return nearby_zones


# Test function
def test_zone_engine():
    """Test zone engine with sample data"""
    
    print("🧪 Testing Zone Engine")
    print("=" * 60)
    
    # Sample indicators
    indicators = {
        'current_price': 150.00,
        'atr14d': 3.50,
        'ema20': 148.50,
        'ema20_slope': {
            'slope_atr': 0.08,
            'slope_factor': 1.0,
            'slope_state': 'MODERATE',
            'direction': 'BULLISH'
        },
        'sma50': 145.00,
        'sma100': 142.00,
        'sma200': 140.00,
        'stack_aligned': True
    }
    
    # Configuration
    config = {
        'atr_multiplier': 0.30,
        'max_distance_atr': 0.35,
        'stack_bonus': 0.5,
        'component_weights': {
            'ema20': 2.0,
            'sma50': 0.8,
            'sma100': 0.8,
            'sma200': 0.8,
            'round_number': 0.3
        }
    }
    
    # Initialize engine
    engine = ZoneEngine(config)
    
    # Build zones
    zones = engine.build_zones('AAPL', indicators, indicators['current_price'], indicators['atr14d'])
    
    print(f"\n📊 Generated {len(zones)} zones:")
    print()
    
    for zone in zones:
        print(f"   Zone: {zone['zone_id']}")
        print(f"   Type: {zone['type'].upper()}")
        print(f"   Range: ${zone['low']:.2f} - ${zone['high']:.2f} (mid: ${zone['mid']:.2f})")
        print(f"   Components: {', '.join(zone['components'])}")
        print(f"   Base Strength: {zone['strength']:.2f}/6")
        print()
    
    # Test nearby zones
    nearby = engine.get_zones_near_price(zones, indicators['current_price'], indicators['atr14d'])
    
    print(f"🎯 Zones near current price (${indicators['current_price']:.2f}):")
    for zone in nearby:
        print(f"   {zone['type'].upper()}: ${zone['mid']:.2f} (distance: {zone['distance_atr']:.3f} ATR)")
    
    print("\n✅ Zone engine test complete!")


if __name__ == "__main__":
    test_zone_engine()