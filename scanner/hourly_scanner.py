# modules/scanner.py - MVP 4.0 Hourly Scanner
"""
1H Scanning Engine - integrates all modules
- Fetches daily + hourly data
- Calculates indicators
- Builds zones
- Detects patterns
- Scores confluence
- Generates signals
- Sends alerts
"""

from typing import List, Dict, Optional
from datetime import datetime
import time

# Import all our modules
from indicators.technical_indicators import TechnicalIndicators
from zones.zone_builder import ZoneEngine
from zones.confluence_scorer import ConfluenceScorer
from data.data_fetcher import AlphaVantageAPI
from data.cache_manager import CacheManager
from context.index_analyzer import IndexRegime
from patterns.candlestick_detector import PatternDetector
from alerts.telegram_sender import TelegramBot

# P4.3: Import weekly watchlist module (conditional)
try:
    from scanner.weekly_watchlist import WeeklyWatchlist
    WATCHLIST_AVAILABLE = True
except ImportError:
    WATCHLIST_AVAILABLE = False
    print("ℹ️  Weekly watchlist module not available")


class Scanner:
    """
    Main 1H scanning engine
    """
    
    def __init__(self, config: Dict):
        """
        Initialize scanner with all dependencies
        
        Args:
            config: Configuration dict
        """
        self.config = config
        
        # Initialize modules
        self.api = AlphaVantageAPI(
            api_key=config['ALPHA_VANTAGE_API_KEY'],
            cache_dir=config['CACHE_DIRECTORY']
        )
        
        self.cache_mgr = CacheManager(cache_dir=config['CACHE_DIRECTORY'])
        
        self.zone_engine = ZoneEngine({
            'atr_multiplier': config['ZONE_CONFIG']['atr_multiplier'],
            'max_distance_atr': config['ZONE_CONFIG']['max_distance_atr'],
            'stack_bonus': config['ZONE_CONFIG']['stack_bonus'],
            'component_weights': config['COMPONENT_WEIGHTS']
        })
        
        self.confluence_scorer = ConfluenceScorer({
            'confluence_thresholds': config['CONFLUENCE_THRESHOLDS'],
            'rv_requirements': config['RV_REQUIREMENTS']
        })
        
        self.index_regime = IndexRegime(self.api, self.cache_mgr)
        
        self.pattern_detector = PatternDetector({
            'rv_requirements': config['RV_REQUIREMENTS']
        })
        
        self.telegram = TelegramBot(
            bot_token=config['TELEGRAM_BOT_TOKEN'],
            chat_id=config['TELEGRAM_CHAT_ID']
        )
        
        # Stock universe
        self.stock_universe = []
        
        # P4.3: Initialize weekly watchlist (conditional)
        self.watchlist_gen = None
        if WATCHLIST_AVAILABLE and config.get('WEEKLY_WATCHLIST', {}).get('enabled', False):
            try:
                self.watchlist_gen = WeeklyWatchlist(
                    scanner=self,
                    min_confluence=config['WEEKLY_WATCHLIST']['min_confluence'],
                    max_stocks=config['WEEKLY_WATCHLIST']['max_stocks'],
                    watchlist_file=config['WEEKLY_WATCHLIST']['watchlist_file']
                )
                print("✅ Weekly watchlist module initialized")
            except Exception as e:
                print(f"⚠️  Could not initialize weekly watchlist: {e}")
                self.watchlist_gen = None
        else:
            print("ℹ️  Weekly watchlist disabled")
        
        # Watchlist (for backward compatibility)
        self.watchlist = []
    
    def load_stock_universe(self, symbols: List[str]):
        """
        Load stock universe
        
        Args:
            symbols: List of stock symbols to scan
        """
        self.stock_universe = symbols
        print(f"✅ Loaded {len(symbols)} symbols to scan")
    
    def scan_stock(self, symbol: str, market_regime: Dict) -> Optional[Dict]:
        """
        Scan a single stock for trading signals
        
        Args:
            symbol: Stock symbol
            market_regime: Market regime from index_regime module
            
        Returns:
            Signal dict if qualified, None otherwise
        """
        # Step 5: Fetch hourly data (for pattern detection)
        hourly_df = self.cache_mgr.get_or_fetch_hourly(
            symbol,
            lambda s: self.api.fetch_hourly_data(s)
        )

        if hourly_df is None or len(hourly_df) < 2:
            print(f"   ⚠️  Insufficient hourly data")
            return None

        try:
            print(f"\n📊 Scanning {symbol}...")
            
            # Step 1: Fetch daily data (for indicators and zones)
            daily_df = self.cache_mgr.get_or_fetch_daily(
                symbol,
                lambda s: self.api.fetch_daily_data(s)
            )
            
            if daily_df is None or len(daily_df) < 60:
                print(f"   ⚠️  Insufficient daily data")
                return None
            
            # DEBUG: Check daily data range
            print(f"\n   🔍 DAILY DATA DEBUG:")
            print(f"      Bars: {len(daily_df)}")
            print(f"      Price range: ${daily_df['Low'].min():.2f} - ${daily_df['High'].max():.2f}")
            print(f"      Date range: {daily_df.iloc[0]['Date']} to {daily_df.iloc[-1]['Date']}")
            
            # Step 2: Calculate indicators
            indicators = TechnicalIndicators.calculate_all_indicators(daily_df)
            
            # Add missing fields that zone_engine might expect
            current_price = indicators.get('current_price', 0)
            
            # Add round numbers (psychological levels) if missing
            if 'round_number' not in indicators:
                round_numbers = []
                for base in [5, 10, 25, 50, 100]:
                    rounded = round(current_price / base) * base
                    if abs(rounded - current_price) <= current_price * 0.1:  # Within 10%
                        round_numbers.append(rounded)
                indicators['round_number'] = sorted(set(round_numbers)) if round_numbers else []
            
            # Add empty lists for other potential fields if missing
            # These would normally be calculated by separate modules
            if 'swing_highs' not in indicators:
                indicators['swing_highs'] = []
            if 'swing_lows' not in indicators:
                indicators['swing_lows'] = []
            if 'gap_edges' not in indicators:
                indicators['gap_edges'] = []
            if 'hvn' not in indicators:
                indicators['hvn'] = []
            if 'lvn' not in indicators:
                indicators['lvn'] = []
            
            # DEBUG: Check if daily indicators are corrupted
            print(f"\n   🔍 DAILY INDICATORS DEBUG:")
            print(f"      Current Price: ${indicators['current_price']:.2f}")
            print(f"      EMA20: ${indicators.get('ema20', 0):.2f}")
            print(f"      SMA50: ${indicators.get('sma50', 0):.2f}")
            print(f"      SMA100: ${indicators.get('sma100', 0):.2f}")
            print(f"      SMA200: ${indicators.get('sma200', 0):.2f}")
            print(f"      ATR: ${indicators['atr14d']:.2f}")
            if indicators.get('error'):
                print(f"   ⚠️  Indicator error: {indicators['error']}")
                return None
            
            current_price = indicators['current_price']
            atr = indicators['atr14d']
            
            print(f"   Price: ${current_price:.2f}, ATR: ${atr:.2f}")
            
            # Step 3: Build zones
            zones = self.zone_engine.build_zones(
                symbol=symbol,
                indicators=indicators,
                current_price=current_price,
                atr=atr,
                hourly_df=hourly_df  # P1: Pass hourly data for swing/gap/HVN detection
            )
            
            if not zones:
                print(f"   ⚠️  No zones generated")
                return None
            
            print(f"   ✅ Generated {len(zones)} zones")
            
            # Step 4: Check if price near any zone
            nearby_zones = self.zone_engine.get_zones_near_price(
                zones=zones,
                current_price=current_price,
                atr=atr
            )
            
            if not nearby_zones:
                print(f"   ⚠️  No zones within range")
                return  None
                            
                        
            
            print(f"   ✅ Found {len(nearby_zones)} nearby zones")
            
            # Step 5: Fetch hourly data (for pattern detection)
            hourly_df = self.cache_mgr.get_or_fetch_hourly(
                symbol,
                lambda s: self.api.fetch_hourly_data(s)
            )
            
            if hourly_df is None or len(hourly_df) < 2:
                print(f"   ⚠️  Insufficient hourly data")
                return None
            
            # Step 6: Detect patterns
            pattern = self.pattern_detector.detect_patterns(hourly_df)
            
            if not pattern:
                print(f"   ⚠️  No pattern detected")
                return None
            
            print(f"   ✅ Pattern: {pattern['pattern']}, RV: {pattern['relative_volume']:.2f}x")
            
            # Step 7: Find best zone for this signal
            signal_side = pattern['side']
            
            # Filter zones by type matching signal
            target_type = 'support' if signal_side == 'long' else 'resistance'
            matching_zones = [z for z in nearby_zones if z['type'] == target_type]
            
            if not matching_zones:
                print(f"   ⚠️  No {target_type} zones nearby")
                return None
            
            # Use closest zone
            best_zone = matching_zones[0]
            
            print(f"   ✅ Using {best_zone['type']} zone: ${best_zone['mid']:.2f}")
            
            # Step 8: Calculate confluence
            spy_regime = market_regime['spy']['regime']
            qqq_regime = market_regime['qqq']['regime']
            index_trend = 'bullish' if spy_regime == 'bullish' else 'bearish'
            
            confluence = self.confluence_scorer.calculate_total_confluence(
                zone=best_zone,
                signal_side=signal_side,
                stock_indicators=indicators,
                spy_regime=spy_regime,
                qqq_regime=qqq_regime,
                index_trend=index_trend
            )
            
            # Check if suppressed
            if confluence['suppress_alert']:
                print(f"   ⚠️  Signal suppressed (against market)")
                return None
            
            print(f"   ✅ Confluence: {confluence['total_score']:.1f}/10")
            
            # Step 9: Classify signal quality
            # P4.3: Check if stock is on weekly watchlist
            from_watchlist = False
            if self.watchlist_gen and self.watchlist_gen.is_on_watchlist(symbol):
                from_watchlist = True
                print(f"   ⭐ Stock is on weekly watchlist!")
            elif symbol in self.watchlist:  # Fallback to old watchlist
                from_watchlist = True
            
            quality = self.confluence_scorer.classify_signal_quality(
                confluence=confluence,
                from_watchlist=from_watchlist,
                relative_volume=pattern['relative_volume']
            )
            
            print(f"   ✅ Quality: {quality}")
            
            # Check if meets threshold
            if quality == 'Low':
                print(f"   ⚠️  Quality too low")
                return None
            
             # Step 10: Build signal
            signal = {
                'symbol': symbol,
                'side': signal_side,
                'price': current_price,
                'quality': quality,
                'from_watchlist': from_watchlist,  # P4.3: Add watchlist flag
                'pattern': {
                    'pattern': pattern['pattern'],
                    'relative_volume': pattern['relative_volume'],
                    'bias': pattern['bias'],
                    'price': pattern['price'],
                    'quality': pattern.get('quality', 'medium')
                },
                'zone': {
                    'zone_id': best_zone.get('zone_id', f"{symbol}_{best_zone['type']}"),
                    'type': best_zone['type'],
                    'mid': best_zone['mid'],
                    'low': best_zone['low'],
                    'high': best_zone['high'],
                    'strength': best_zone['strength'],
                    'components': best_zone['components'],
                    'distance_atr': abs(current_price - best_zone['mid']) / atr
                },
                'confluence': {
                    'total_score': confluence['total_score'],
                    'base_strength': confluence['base_strength'],
                    'index_alignment_score': confluence['index_alignment_score'],
                    'trend_alignment_score': confluence['trend_alignment_score']
                },
                'index_context': {
                    'spy_regime': spy_regime,
                    'qqq_regime': qqq_regime
                },
                'timestamp': datetime.now().isoformat()
            }
            
            # Add targets if we have them
            if signal_side == 'long':
                resistance_zones = [z for z in zones if z['type'] == 'resistance' 
                                  and z['mid'] > current_price]
                support_zones = [z for z in zones if z['type'] == 'support' 
                               and z['mid'] < current_price]
                
                if resistance_zones:
                    resistance_zones.sort(key=lambda x: x['mid'])
                    signal['targets'] = {
                        'next_resistance': resistance_zones[0]['mid'],
                        'stop_loss': best_zone['low'] * 0.995
                    }
            else:
                support_zones = [z for z in zones if z['type'] == 'support' 
                               and z['mid'] < current_price]
                resistance_zones = [z for z in zones if z['type'] == 'resistance' 
                                  and z['mid'] > current_price]
                
                if support_zones:
                    support_zones.sort(key=lambda x: x['mid'], reverse=True)
                    signal['targets'] = {
                        'next_support': support_zones[0]['mid'],
                        'stop_loss': best_zone['high'] * 1.005
                    }
            
            return signal
            
        except Exception as e:
            print(f"   ❌ Error scanning {symbol}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def run_scan(self, symbols: Optional[List[str]] = None, 
                 send_alerts: bool = True) -> List[Dict]:
        """
        Run complete scan on stock universe
        
        Args:
            symbols: Optional list of symbols (uses stock_universe if None)
            send_alerts: Whether to send Telegram alerts
            
        Returns:
            List of qualified signals
        """
        if symbols is None:
            symbols = self.stock_universe
        
        if not symbols:
            print("❌ No symbols to scan")
            return []
        
        print(f"\n{'='*60}")
        print(f"🚀 STARTING SCAN - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        print(f"Symbols: {len(symbols)}")
        
        # Get market regime once
        print("\n📊 Fetching market regime...")
        market_regime = self.index_regime.get_market_regime()
        print(self.index_regime.format_regime_summary(market_regime))
        
        # Scan all stocks
        signals = []
        
        for i, symbol in enumerate(symbols, 1):
            print(f"\n[{i}/{len(symbols)}] ", end="")
            
            signal = self.scan_stock(symbol, market_regime)
            
            if signal:
                signals.append(signal)
                print(f"   ✅ SIGNAL GENERATED: {signal['quality']} quality")
                
                # Send alert if enabled
                if send_alerts:
                    success = self.telegram.send_alert(signal)
                    if not success:
                        print(f"   ⚠️  Failed to send alert")
            
            # Rate limiting - small delay between stocks
            if i < len(symbols):
                time.sleep(1)
        
        # Summary
        print(f"\n{'='*60}")
        print(f"📈 SCAN COMPLETE")
        print(f"{'='*60}")
        print(f"Symbols scanned: {len(symbols)}")
        print(f"Signals generated: {len(signals)}")
        
        if signals:
            print(f"\n🎯 SIGNALS:")
            for sig in signals:
                print(f"   {sig['symbol']}: {sig['side'].upper()} @ ${sig['price']:.2f} ({sig['quality']})")
        else:
            print("\n⚠️  No signals generated")
        
        return signals

    def test_single_stock(self, symbol: str, verbose: bool = True) -> None:
        """
        Test scanning on a single symbol with detailed output
        
        Args:
            symbol: Stock symbol to test
            verbose: If True, show all zones (default: True for testing)
        """
        print(f"\n{'='*60}")
        print(f"🧪 Testing: {symbol}")
        print(f"{'='*60}\n")
        market_regime = self.index_regime.get_market_regime()
        result = self.scan_stock(symbol,market_regime)
        
        if result is None:
            print("❌ No result generated")
            return
        
        # Display basic info
        print(f"\n📊 SCAN RESULTS:")
        print(f"   Symbol: {result['symbol']}")
        print(f"   Price: ${result['current_price']:.2f}")
        print(f"   ATR: ${result['atr']:.2f}")
        print(f"   Proximity threshold: ±${0.35 * result['atr']:.2f} (0.35×ATR)")
        
        # Show ALL zones (not just nearby)
        all_zones = result.get('all_zones', [])
        if all_zones:
            print(f"\n🎯 ALL ZONES ({len(all_zones)}):")
            
            # Separate support and resistance
            support_zones = [z for z in all_zones if z['type'] == 'support']
            resistance_zones = [z for z in all_zones if z['type'] == 'resistance']
            
            # Sort by price
            support_zones.sort(key=lambda x: x['mid'], reverse=True)
            resistance_zones.sort(key=lambda x: x['mid'])
            
            # Display support zones
            if support_zones:
                print(f"\n   📉 SUPPORT ZONES ({len(support_zones)}):")
                for i, zone in enumerate(support_zones, 1):
                    distance = result['current_price'] - zone['mid']
                    distance_atr = distance / result['atr']
                    in_range = "✅" if abs(distance_atr) <= 0.35 else "  "
                    
                    print(f"   {in_range} S{i}: ${zone['mid']:.2f} (${zone['low']:.2f}-${zone['high']:.2f})")
                    print(f"        Distance: ${distance:.2f} ({distance_atr:.2f}×ATR)")
                    print(f"        Components: {', '.join(zone['components'])}")
                    print(f"        Strength: {zone['strength']:.1f}/10")
            
            # Display resistance zones
            if resistance_zones:
                print(f"\n   📈 RESISTANCE ZONES ({len(resistance_zones)}):")
                for i, zone in enumerate(resistance_zones, 1):
                    distance = zone['mid'] - result['current_price']
                    distance_atr = distance / result['atr']
                    in_range = "✅" if abs(distance_atr) <= 0.35 else "  "
                    
                    print(f"   {in_range} R{i}: ${zone['mid']:.2f} (${zone['low']:.2f}-${zone['high']:.2f})")
                    print(f"        Distance: ${distance:.2f} ({distance_atr:.2f}×ATR)")
                    print(f"        Components: {', '.join(zone['components'])}")
                    print(f"        Strength: {zone['strength']:.1f}/10")
        else:
            print(f"\n⚠️  No zones generated")
        
        # Show nearby zones (if any)
        nearby_zones = result.get('nearby_zones', [])
        if nearby_zones:
            print(f"\n✅ ZONES IN RANGE ({len(nearby_zones)} within 0.35×ATR):")
            for zone in nearby_zones:
                print(f"   • {zone['type'].upper()}: ${zone['mid']:.2f} - {zone['strength']:.1f}/10")
        else:
            print(f"\n⚠️  No zones within 0.35×ATR range")
        
        # Show pattern
        pattern = result.get('pattern')
        if pattern:
            print(f"\n📊 PATTERN DETECTED:")
            print(f"   Type: {pattern['pattern']}")
            print(f"   Bias: {pattern['bias'].upper()}")
            print(f"   Price: ${pattern['price']:.2f}")
            print(f"   RV: {pattern['relative_volume']:.2f}x")
            print(f"   Quality: {pattern['quality'].upper()}")
        else:
            print(f"\n⚠️  No pattern detected on latest candle")
        
        # Show signal status
        if result.get('signal_generated'):
            print(f"\n✅ SIGNAL GENERATED")
            print(f"   Quality: {result.get('signal_quality', 'N/A')}")
            print(f"   Alert would be sent to Telegram")
        else:
            print(f"\n❌ No signal generated")
            reasons = []
            if not pattern:
                reasons.append("No pattern detected")
            if not nearby_zones:
                reasons.append("Price not near any zones")
            if reasons:
                print(f"   Reasons: {', '.join(reasons)}")


# Quick test function
def test_scanner():
    """Test scanner with sample stocks"""
    import config
    
    print("🧪 Testing Scanner")
    print("=" * 60)
    
    # Initialize scanner
    scanner = Scanner({
        'ALPHA_VANTAGE_API_KEY': config.ALPHA_VANTAGE_API_KEY,
        'TELEGRAM_BOT_TOKEN': config.TELEGRAM_BOT_TOKEN,
        'TELEGRAM_CHAT_ID': config.TELEGRAM_CHAT_ID,
        'CACHE_DIRECTORY': config.CACHE_DIRECTORY,
        'ZONE_CONFIG': config.ZONE_CONFIG,
        'COMPONENT_WEIGHTS': config.COMPONENT_WEIGHTS,
        'CONFLUENCE_THRESHOLDS': config.CONFLUENCE_THRESHOLDS,
        'RV_REQUIREMENTS': config.RV_REQUIREMENTS
    })
    
    # Test with a few stocks (use demo-friendly symbols)
    test_symbols = ['IBM', 'AAPL', 'MSFT']
    
    print(f"\n📊 Testing with symbols: {test_symbols}")
    print("   (Using first 3 for speed)")
    
    # Run scan (without sending alerts in test)
    signals = scanner.run_scan(symbols=test_symbols[:3], send_alerts=False)
    
    print(f"\n✅ Scanner test complete!")
    print(f"   Signals found: {len(signals)}")


if __name__ == "__main__":
    test_scanner()