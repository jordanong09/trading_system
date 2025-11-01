"""
Confluence Merger Module (v5.0)

Merges overlapping S/R zones and calculates confluence scores.
Implements proximity-based merging and weighted scoring.

Author: Stock Analyzer v5.0
Dependencies: None (standalone)
"""

import pandas as pd
from typing import List, Dict, Optional


class ConfluenceMerger:
    """
    Merge overlapping zones and calculate confluence scores
    
    Process:
        1. Sort zones by mid price
        2. Merge zones within 0.10×ATR of each other
        3. Combine sources and sum weights
        4. Calculate weighted average mid price
        5. Apply proximity boost
        6. Apply index alignment bonus
        7. Apply volatility multiplier
    """
    
    def __init__(self, config=None):
        """
        Initialize confluence merger
        
        Args:
            config: Configuration module
        """
        self.config = config
        
        # Merge threshold (zones within this distance get merged)
        self.merge_threshold = 0.10  # ×ATR
        
        # Proximity threshold for bonus scoring
        self.proximity_threshold = 0.30  # ×ATR
        
        # Load weights from config
        if config and hasattr(config, 'WEIGHTS'):
            self.weights = config.WEIGHTS
        else:
            # Default weights
            self.weights = {
                'Fib_core': 3,      # 0.5, 0.618, 0.786
                'Fib_other': 2,     # 0.382, 0.236
                'Swing': 2,
                'Diagonal': 2,
                'SMA': 2,
                'EMA20_SR': 1,
                'GapEdge': 2
            }
    
    def merge_zones(
        self,
        zones: List[Dict],
        atr: float,
        current_price: float
    ) -> List[Dict]:
        """
        Merge overlapping zones
        
        Algorithm:
            1. Sort zones by mid price
            2. For each zone, check if it overlaps with previous zones
            3. If |mid1 - mid2| ≤ merge_threshold×ATR, merge them
            4. Combine sources and sum weights
            5. Calculate weighted average mid price
        
        Args:
            zones: List of zone dicts
            atr: ATR value
            current_price: Current stock price
        
        Returns:
            List of merged zones
        """
        if not zones:
            return []
        
        # Sort zones by mid price
        sorted_zones = sorted(zones, key=lambda z: z['mid'])
        
        merged = []
        current_cluster = None
        
        for zone in sorted_zones:
            if current_cluster is None:
                # Start first cluster
                current_cluster = self._init_cluster(zone)
            else:
                # Check if this zone should merge with current cluster
                distance = abs(zone['mid'] - current_cluster['weighted_mid'])
                merge_distance = self.merge_threshold * atr
                
                if distance <= merge_distance:
                    # Merge into current cluster
                    current_cluster = self._merge_into_cluster(current_cluster, zone)
                else:
                    # Finalize current cluster and start new one
                    merged.append(self._finalize_cluster(current_cluster, current_price, atr))
                    current_cluster = self._init_cluster(zone)
        
        # Don't forget the last cluster
        if current_cluster is not None:
            merged.append(self._finalize_cluster(current_cluster, current_price, atr))
        
        return merged
    
    def _init_cluster(self, zone: Dict) -> Dict:
        """Initialize a new cluster from a single zone"""
        return {
            'zones': [zone],
            'sources': [zone['source']],
            'weights': [zone['weight']],
            'weighted_mid': zone['mid'],
            'total_weight': zone['weight'],
            'type': zone['type']
        }
    
    def _merge_into_cluster(self, cluster: Dict, zone: Dict) -> Dict:
        """Merge a zone into an existing cluster"""
        cluster['zones'].append(zone)
        cluster['sources'].append(zone['source'])
        cluster['weights'].append(zone['weight'])
        cluster['total_weight'] += zone['weight']
        
        # Recalculate weighted average mid
        total_weighted = sum(
            z['mid'] * z['weight'] 
            for z in cluster['zones']
        )
        cluster['weighted_mid'] = total_weighted / cluster['total_weight']
        
        return cluster
    
    def _finalize_cluster(
        self,
        cluster: Dict,
        current_price: float,
        atr: float
    ) -> Dict:
        """Convert cluster to final zone format"""
        mid = cluster['weighted_mid']
        zone_width = 0.15 * atr  # ±0.15×ATR zone bands
        
        return {
            'type': cluster['type'],
            'low': mid - zone_width,
            'mid': mid,
            'high': mid + zone_width,
            'sources': cluster['sources'],
            'weights': cluster['weights'],
            'base_score': cluster['total_weight'],
            'distance_from_price': abs(mid - current_price),
            'distance_atr': abs(mid - current_price) / atr if atr > 0 else 0
        }
    
    def score_all_zones(
        self,
        zones: List[Dict],
        current_price: float,
        atr: float,
        market_sentiment: Optional[Dict] = None,
        stock_regime: Optional[str] = None
    ) -> List[Dict]:
        """
        Calculate final confluence scores for all zones
        
        Args:
            zones: List of merged zones
            current_price: Current stock price
            atr: ATR value
            market_sentiment: Market sentiment dict (optional)
            stock_regime: Stock regime 'bullish'/'bearish' (optional)
        
        Returns:
            List of zones with final_score field added, sorted by score
        """
        scored_zones = []
        
        for zone in zones:
            final_score = self.calculate_confluence_score(
                zone,
                current_price,
                atr,
                market_sentiment,
                stock_regime
            )
            
            zone['final_score'] = final_score
            scored_zones.append(zone)
        
        # Sort by score (descending)
        scored_zones.sort(key=lambda z: z['final_score'], reverse=True)
        
        return scored_zones
    
    def calculate_confluence_score(
        self,
        zone: Dict,
        current_price: float,
        atr: float,
        market_sentiment: Optional[Dict] = None,
        stock_regime: Optional[str] = None
    ) -> float:
        """
        Calculate final confluence score for a zone
        
        Components:
            1. Base score (sum of source weights)
            2. Proximity boost (+2 if ≤0.30×ATR from price)
            3. Index alignment (+2 if aligned)
            4. Volatility multiplier (0.8 to 1.1)
        
        Args:
            zone: Zone dict
            current_price: Current stock price
            atr: ATR value
            market_sentiment: Market sentiment dict (optional)
            stock_regime: Stock regime (optional)
        
        Returns:
            Final confluence score (0-20+ scale)
        """
        # 1. Base score
        score = zone['base_score']
        
        # 2. Proximity boost
        proximity_distance = self.proximity_threshold * atr
        if zone['distance_from_price'] <= proximity_distance:
            score += 2
            zone['proximity_boost'] = True
        else:
            zone['proximity_boost'] = False
        
        # 3. Index alignment bonus
        if self._is_index_aligned(zone, current_price, market_sentiment, stock_regime):
            score += 2
            zone['index_aligned'] = True
        else:
            zone['index_aligned'] = False
        
        # 4. Volatility multiplier
        if market_sentiment and 'vol_multiplier' in market_sentiment:
            score *= market_sentiment['vol_multiplier']
        
        return score
    
    def _is_index_aligned(
        self,
        zone: Dict,
        current_price: float,
        market_sentiment: Optional[Dict],
        stock_regime: Optional[str]
    ) -> bool:
        """
        Check if zone is aligned with market and stock regime
        
        Alignment logic:
            - Resistance zone + bearish market + bearish stock = aligned
            - Support zone + bullish market + bullish stock = aligned
        
        Returns:
            True if aligned, False otherwise
        """
        if not market_sentiment or not stock_regime:
            return False
        
        market_regime = market_sentiment.get('combined_regime', 'neutral')
        
        # Determine if zone is support or resistance relative to price
        is_support = zone['mid'] < current_price
        is_resistance = zone['mid'] > current_price
        
        # Check alignment
        if is_resistance:
            # Resistance benefits from bearish sentiment
            return market_regime == 'bearish' and stock_regime == 'bearish'
        elif is_support:
            # Support benefits from bullish sentiment
            return market_regime == 'bullish' and stock_regime == 'bullish'
        
        return False
    
    def get_zone_summary(self, zone: Dict) -> str:
        """
        Get human-readable summary of a zone
        
        Args:
            zone: Zone dict
        
        Returns:
            String summary
        """
        sources_str = ', '.join(zone['sources'])
        return (
            f"{zone['type'].upper()} @ ${zone['mid']:.2f} "
            f"(${zone['low']:.2f}-${zone['high']:.2f}) | "
            f"Sources: {sources_str} | "
            f"Score: {zone['final_score']:.2f}"
        )


# =============================================================================
# STANDALONE USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    """
    Test the confluence merger module standalone
    
    Usage:
        python stock_analyzer/sr_engine/confluence_merger.py
    """
    print("="*70)
    print("CONFLUENCE MERGER MODULE - STANDALONE TEST")
    print("="*70)
    
    # Sample zones (simulating output from seed detectors)
    sample_zones = [
        {'type': 'resistance', 'low': 99.5, 'mid': 100.0, 'high': 100.5, 'source': 'Fib_0.618', 'weight': 3},
        {'type': 'resistance', 'low': 99.8, 'mid': 100.3, 'high': 100.8, 'source': 'Swing', 'weight': 2},
        {'type': 'resistance', 'low': 99.6, 'mid': 100.1, 'high': 100.6, 'source': 'SMA50', 'weight': 2},
        {'type': 'support', 'low': 94.5, 'mid': 95.0, 'high': 95.5, 'source': 'Fib_0.5', 'weight': 3},
        {'type': 'support', 'low': 94.3, 'mid': 94.8, 'high': 95.3, 'source': 'Diagonal', 'weight': 2},
        {'type': 'support', 'low': 89.5, 'mid': 90.0, 'high': 90.5, 'source': 'SMA200', 'weight': 2},
    ]
    
    current_price = 97.5
    atr = 2.0
    
    # Market sentiment (simulating from market layer)
    market_sentiment = {
        'combined_regime': 'bullish',
        'vol_multiplier': 1.05
    }
    stock_regime = 'bullish'
    
    # Test merging
    print("\nINPUT ZONES:")
    print("-"*70)
    for i, zone in enumerate(sample_zones, 1):
        print(f"{i}. {zone['type']} @ ${zone['mid']:.2f} | Source: {zone['source']}")
    
    # Initialize merger
    merger = ConfluenceMerger()
    
    # Merge zones
    print(f"\nMERGING (threshold: {merger.merge_threshold}×ATR = ${merger.merge_threshold * atr:.2f})...")
    merged_zones = merger.merge_zones(sample_zones, atr, current_price)
    
    print(f"\nMERGED ZONES ({len(merged_zones)} zones):")
    print("-"*70)
    for i, zone in enumerate(merged_zones, 1):
        print(f"\n{i}. {zone['type'].upper()} @ ${zone['mid']:.2f}")
        print(f"   Range: ${zone['low']:.2f} - ${zone['high']:.2f}")
        print(f"   Sources: {', '.join(zone['sources'])}")
        print(f"   Base score: {zone['base_score']:.1f}")
        print(f"   Distance: ${zone['distance_from_price']:.2f} ({zone['distance_atr']:.2f}×ATR)")
    
    # Score zones
    print("\nCALCULATING CONFLUENCE SCORES...")
    scored_zones = merger.score_all_zones(
        merged_zones,
        current_price,
        atr,
        market_sentiment,
        stock_regime
    )
    
    print(f"\nFINAL SCORED ZONES:")
    print("="*70)
    for i, zone in enumerate(scored_zones, 1):
        print(f"\n{i}. {merger.get_zone_summary(zone)}")
        if zone.get('proximity_boost'):
            print(f"   ✓ Proximity boost (+2)")
        if zone.get('index_aligned'):
            print(f"   ✓ Index aligned (+2)")
    
    print("\n" + "="*70)
    print("✅ CONFLUENCE MERGER MODULE TESTS COMPLETE")
    print("="*70)
    print("\nREADY FOR INTEGRATION:")
    print("  - Import: from stock_analyzer.sr_engine.confluence_merger import ConfluenceMerger")
    print("  - Usage: merger = ConfluenceMerger(config)")
    print("  - Call: merged_zones = merger.merge_zones(zones, atr, current_price)")
    print("="*70)
