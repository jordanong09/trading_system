# modules/confluence_scorer.py - 10-Point Confluence Scoring
"""
MVP 4.0 Confluence Scoring System
- Base Zone Strength: 0-6 points (from zone_engine)
- Index Alignment: 0-2 points (SPY/QQQ regime check)
- Stock-Index Trend Alignment: 0-2 points (trend concordance)
- Total: 10 points possible
- Quality thresholds: High (≥7 watchlist, ≥8 new) / Medium (≥5 watchlist, ≥7 new)
"""

from typing import Dict, Optional


class ConfluenceScorer:
    """
    Calculate 10-point confluence score for trading signals
    """
    
    def __init__(self, config: Dict):
        """
        Initialize confluence scorer
        
        Args:
            config: Configuration dict with thresholds
        """
        self.thresholds = config.get('confluence_thresholds', {
            'watchlist_high': 7,
            'watchlist_medium': 5,
            'new_high': 8,
            'new_medium': 7
        })
        
        self.rv_requirements = config.get('rv_requirements', {
            'high': 1.5,
            'medium': 1.2
        })
    
    def calculate_index_alignment_score(self, signal_side: str, 
                                       spy_regime: str, 
                                       qqq_regime: str) -> Dict:
        """
        Calculate index alignment score (0-2 points)
        
        Rules for LONG signals:
        - Both SPY and QQQ bullish: 2.0 points
        - One bullish: 1.0 point
        - Both bearish: 0.0 points (SUPPRESS ALERT)
        
        Rules for SHORT signals:
        - Both SPY and QQQ bearish: 2.0 points
        - One bearish: 1.0 point
        - Both bullish: 0.0 points (SUPPRESS ALERT)
        
        Args:
            signal_side: 'long' or 'short'
            spy_regime: 'bullish', 'bearish', or 'neutral'
            qqq_regime: 'bullish', 'bearish', or 'neutral'
            
        Returns:
            Dict with score and details
        """
        signal_side = signal_side.lower()
        
        if signal_side == 'long':
            # Count bullish indices
            bullish_count = 0
            if spy_regime == 'bullish':
                bullish_count += 1
            if qqq_regime == 'bullish':
                bullish_count += 1
            
            if bullish_count == 2:
                score = 2.0
                alignment = 'strong_with_trend'
            elif bullish_count == 1:
                score = 1.0
                alignment = 'partial_with_trend'
            else:
                score = 0.0
                alignment = 'against_trend'
        
        elif signal_side == 'short':
            # Count bearish indices
            bearish_count = 0
            if spy_regime == 'bearish':
                bearish_count += 1
            if qqq_regime == 'bearish':
                bearish_count += 1
            
            if bearish_count == 2:
                score = 2.0
                alignment = 'strong_with_trend'
            elif bearish_count == 1:
                score = 1.0
                alignment = 'partial_with_trend'
            else:
                score = 0.0
                alignment = 'against_trend'
        
        else:
            # Invalid signal side
            score = 0.0
            alignment = 'unknown'
        
        return {
            'score': score,
            'alignment': alignment,
            'spy_regime': spy_regime,
            'qqq_regime': qqq_regime,
            'suppress_alert': score == 0.0  # Suppress if against trend
        }
    
    def calculate_trend_alignment_score(self, stock_indicators: Dict, 
                                       index_trend: str) -> Dict:
        """
        Calculate stock-index trend alignment score (0-2 points)
        
        Stock trend determination:
        - Bullish if: Close > SMA50 AND SMA50 rising
        - Bearish otherwise
        
        Index trend: 'bullish' if SPY > SMA50, 'bearish' otherwise
        
        Scoring:
        - Same trend: 2.0 points
        - Different trend: 0.0 points
        
        Args:
            stock_indicators: Dict with stock's indicators
            index_trend: 'bullish' or 'bearish'
            
        Returns:
            Dict with score and details
        """
        current_price = stock_indicators.get('current_price')
        sma50 = stock_indicators.get('sma50')
        
        if current_price is None or sma50 is None:
            # Can't determine trend without SMA50
            return {
                'score': 0.0,
                'stock_trend': 'unknown',
                'index_trend': index_trend,
                'aligned': False,
                'reason': 'insufficient_data'
            }
        
        # Determine stock trend (simplified - not checking if SMA50 rising)
        stock_trend = 'bullish' if current_price > sma50 else 'bearish'
        
        # Check alignment
        aligned = (stock_trend == index_trend)
        score = 2.0 if aligned else 0.0
        
        return {
            'score': score,
            'stock_trend': stock_trend,
            'index_trend': index_trend,
            'aligned': aligned,
            'price_vs_sma50': current_price - sma50
        }
    
    def calculate_total_confluence(self, zone: Dict, 
                                   signal_side: str,
                                   stock_indicators: Dict,
                                   spy_regime: str,
                                   qqq_regime: str,
                                   index_trend: str) -> Dict:
        """
        Calculate total 10-point confluence score
        
        Components:
        1. Base Zone Strength (0-6) - from zone_engine
        2. Index Alignment (0-2) - SPY/QQQ regime
        3. Trend Alignment (0-2) - stock vs index trend
        
        Args:
            zone: Zone dict with 'strength' field
            signal_side: 'long' or 'short'
            stock_indicators: Stock's technical indicators
            spy_regime: 'bullish', 'bearish', or 'neutral'
            qqq_regime: 'bullish', 'bearish', or 'neutral'
            index_trend: Overall index trend ('bullish' or 'bearish')
            
        Returns:
            Dict with total score and breakdown
        """
        # Component 1: Base Zone Strength (0-6)
        base_strength = zone.get('strength', 0)
        
        # Component 2: Index Alignment (0-2)
        index_alignment = self.calculate_index_alignment_score(
            signal_side, spy_regime, qqq_regime
        )
        
        # Component 3: Trend Alignment (0-2)
        trend_alignment = self.calculate_trend_alignment_score(
            stock_indicators, index_trend
        )
        
        # Total score (out of 10)
        total_score = base_strength + index_alignment['score'] + trend_alignment['score']
        
        # Suppress if index alignment is 0
        suppress = index_alignment['suppress_alert']
        
        return {
            'total_score': total_score,
            'base_strength': base_strength,
            'index_alignment_score': index_alignment['score'],
            'trend_alignment_score': trend_alignment['score'],
            'breakdown': {
                'base': base_strength,
                'index': index_alignment,
                'trend': trend_alignment
            },
            'suppress_alert': suppress
        }
    
    def classify_signal_quality(self, confluence: Dict, 
                               from_watchlist: bool,
                               relative_volume: float) -> str:
        """
        Classify signal as High, Medium, or Low quality
        
        Requirements:
        - High: ≥7/10 (watchlist) or ≥8/10 (new) AND RV ≥1.5
        - Medium: ≥5/10 (watchlist) or ≥7/10 (new) AND RV ≥1.2
        - Low: Below thresholds or suppressed
        
        Args:
            confluence: Confluence score dict
            from_watchlist: Is this a watchlist stock?
            relative_volume: Relative volume ratio
            
        Returns:
            'High', 'Medium', or 'Low'
        """
        total_score = confluence['total_score']
        suppress = confluence['suppress_alert']
        
        # Check if suppressed
        if suppress:
            return 'Low'
        
        # Get thresholds
        if from_watchlist:
            high_threshold = self.thresholds['watchlist_high']
            medium_threshold = self.thresholds['watchlist_medium']
        else:
            high_threshold = self.thresholds['new_high']
            medium_threshold = self.thresholds['new_medium']
        
        # Check High quality
        if total_score >= high_threshold and relative_volume >= self.rv_requirements['high']:
            return 'High'
        
        # Check Medium quality
        if total_score >= medium_threshold and relative_volume >= self.rv_requirements['medium']:
            return 'Medium'
        
        # Otherwise Low
        return 'Low'
    
    def should_alert(self, quality: str, send_medium: bool = True) -> bool:
        """
        Determine if alert should be sent
        
        Args:
            quality: 'High', 'Medium', or 'Low'
            send_medium: Whether to send Medium quality alerts
            
        Returns:
            True if alert should be sent
        """
        if quality == 'High':
            return True
        
        if quality == 'Medium' and send_medium:
            return True
        
        return False
    
    def format_confluence_summary(self, confluence: Dict) -> str:
        """
        Format confluence breakdown as readable string
        
        Args:
            confluence: Confluence score dict
            
        Returns:
            Formatted string
        """
        lines = []
        lines.append(f"🎯 Confluence: {confluence['total_score']:.1f}/10")
        lines.append(f"   Base: {confluence['base_strength']:.1f}/6")
        lines.append(f"   Index: {confluence['index_alignment_score']:.1f}/2")
        lines.append(f"   Trend: {confluence['trend_alignment_score']:.1f}/2")
        
        return "\n".join(lines)


# Quick test function
def test_confluence_scorer():
    """Test confluence scoring system"""
    
    print("🧪 Testing Confluence Scorer")
    print("=" * 60)
    
    # Configuration
    config = {
        'confluence_thresholds': {
            'watchlist_high': 7,
            'watchlist_medium': 5,
            'new_high': 8,
            'new_medium': 7
        },
        'rv_requirements': {
            'high': 1.5,
            'medium': 1.2
        }
    }
    
    # Initialize scorer
    scorer = ConfluenceScorer(config)
    
    # Test scenario 1: Strong bullish setup
    print("\n📊 Test 1: Strong Bullish Setup")
    print("-" * 60)
    
    zone = {'strength': 5.5}  # Strong zone
    stock_indicators = {'current_price': 150, 'sma50': 145}
    
    confluence = scorer.calculate_total_confluence(
        zone=zone,
        signal_side='long',
        stock_indicators=stock_indicators,
        spy_regime='bullish',
        qqq_regime='bullish',
        index_trend='bullish'
    )
    
    print(scorer.format_confluence_summary(confluence))
    
    quality = scorer.classify_signal_quality(confluence, from_watchlist=True, relative_volume=1.8)
    print(f"Quality: {quality}")
    print(f"Should Alert: {scorer.should_alert(quality)}")
    
    # Test scenario 2: Counter-trend setup (should suppress)
    print("\n📊 Test 2: Counter-Trend Setup (Suppressed)")
    print("-" * 60)
    
    confluence2 = scorer.calculate_total_confluence(
        zone=zone,
        signal_side='long',
        stock_indicators=stock_indicators,
        spy_regime='bearish',
        qqq_regime='bearish',
        index_trend='bearish'
    )
    
    print(scorer.format_confluence_summary(confluence2))
    print(f"Suppressed: {confluence2['suppress_alert']}")
    
    quality2 = scorer.classify_signal_quality(confluence2, from_watchlist=True, relative_volume=1.8)
    print(f"Quality: {quality2}")
    print(f"Should Alert: {scorer.should_alert(quality2)}")
    
    # Test scenario 3: Medium quality
    print("\n📊 Test 3: Medium Quality Setup")
    print("-" * 60)
    
    zone3 = {'strength': 3.0}  # Weaker zone
    
    confluence3 = scorer.calculate_total_confluence(
        zone=zone3,
        signal_side='long',
        stock_indicators=stock_indicators,
        spy_regime='bullish',
        qqq_regime='neutral',
        index_trend='bullish'
    )
    
    print(scorer.format_confluence_summary(confluence3))
    
    quality3 = scorer.classify_signal_quality(confluence3, from_watchlist=True, relative_volume=1.3)
    print(f"Quality: {quality3}")
    print(f"Should Alert: {scorer.should_alert(quality3)}")
    
    print("\n✅ Confluence scorer test complete!")


if __name__ == "__main__":
    test_confluence_scorer()
