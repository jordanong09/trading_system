# modules/scanner.py - MVP 4.0 Hourly Scanner (OPTIMIZED)
"""
1H Scanning Engine - OPTIMIZED FOR PERFORMANCE
- Parallel scanning with ThreadPoolExecutor (10x faster)
- Zone caching (loads from cache instead of rebuilding)
- Clean production-ready code
"""

from typing import List, Dict, Optional
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import pandas as pd

# Import all our modules
from indicators.technical_indicators import TechnicalIndicators
from zones.zone_builder import ZoneEngine
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


class Scanner:
    """
    Main 1H scanning engine - OPTIMIZED
    """
    
    @staticmethod
    def calculate_hourly_atr(df: pd.DataFrame, period: int = 14) -> Optional[float]:
        """
        Calculate ATR on hourly timeframe
        
        Args:
            df: DataFrame with hourly OHLC data
            period: ATR period (default 14 hours)
        
        Returns:
            ATR value on hourly timeframe
        """
        if len(df) < period + 1:
            return None
        
        high = df['High'].values
        low = df['Low'].values
        close = df['Close'].values
        
        tr = [0.0]  # First bar has no previous close
        
        for i in range(1, len(df)):
            hl = high[i] - low[i]
            hc = abs(high[i] - close[i-1])
            lc = abs(low[i] - close[i-1])
            tr.append(max(hl, hc, lc))
        
        # Calculate ATR as rolling average of TR
        tr_series = pd.Series(tr)
        atr = tr_series.rolling(window=period).mean().iloc[-1]
        
        return atr if not pd.isna(atr) else None
    
    @staticmethod
    def check_zone_breakout(
        candle_close: float,
        candle_open: float,
        zone: Dict,
        atr_daily: float,
        side: str,
        buffer_mult: float = 0.10,
        require_through_body: bool = True
    ) -> bool:
        """
        Check if a momentum candle broke through a zone
        
        Args:
            candle_close: Close price of momentum candle
            candle_open: Open price of momentum candle
            zone: Zone dict with 'high', 'low', 'mid'
            atr_daily: Daily ATR for buffer calculation
            side: 'bullish' or 'bearish'
            buffer_mult: Buffer as multiple of daily ATR (default 0.10)
            require_through_body: Require candle to open inside and close outside (stricter)
        
        Returns:
            True if zone was broken, False otherwise
        """
        buffer = buffer_mult * atr_daily
        
        if side == 'bullish':
            # Bullish breakout: close above zone.high + buffer
            closed_beyond = candle_close > zone['high'] + buffer
            
            # Optional: require candle opened below zone.high (drove through it)
            opened_through = candle_open <= zone['high']
            
            return closed_beyond and (opened_through if require_through_body else True)
        
        else:  # bearish
            # Bearish breakout: close below zone.low - buffer
            closed_beyond = candle_close < zone['low'] - buffer
            
            # Optional: require candle opened above zone.low (drove through it)
            opened_through = candle_open >= zone['low']
            
            return closed_beyond and (opened_through if require_through_body else True)
    
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
        
        # Parallel processing settings
        self.max_workers = 10  # Process 10 stocks simultaneously
        self.scan_lock = threading.Lock()  # Thread-safe operations
        
        # Momentum breakout config
        self.momentum_cfg = config.get('MOMENTUM_CFG', {
            'min_body_pct': 0.65,
            'max_wick_pct': 0.20,
            'min_range_atr_mult': 0.5,
            'min_rv': 1.5,
            'break_buffer_daily_atr': 0.10,
            'require_through_body': True
        })
        
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
            except Exception:
                self.watchlist_gen = None
        
        self.watchlist = []
    
    def load_stock_universe(self, symbols: List[str]):
        """Load stock universe"""
        self.stock_universe = symbols
        print(f"âœ… Loaded {len(symbols)} symbols to scan")
    
    def scan_stock(self, symbol: str, market_regime: Dict) -> Optional[Dict]:
        """
        Scan a single stock for trading signals - OPTIMIZED
        
        Args:
            symbol: Stock symbol
            market_regime: Market regime from index_regime module
            
        Returns:
            Signal dict if qualified, None otherwise
        """
        try:
            # Step 1: Fetch daily data
            daily_df = self.cache_mgr.get_or_fetch_daily(
                symbol,
                lambda s: self.api.fetch_daily_data(s)
            )
            
            if daily_df is None or len(daily_df) < 60:
                return None
            
            # Step 2: Calculate indicators
            indicators = TechnicalIndicators.calculate_all_indicators(daily_df)
            
            if indicators.get('error'):
                return None
            
            current_price = indicators['current_price']
            atr = indicators['atr14d']
            
            
            for field in ['swing_highs', 'swing_lows', 'gap_edges', 'hvn', 'lvn']:
                if field not in indicators:
                    indicators[field] = []
            
            # Step 3: LOAD ZONES FROM CACHE (OPTIMIZATION)
            zones = self.cache_mgr.load_cached_zones(symbol, max_age_hours=24)
            
            if not zones:
                # Cache miss - build zones and cache for next time
                hourly_df = self.cache_mgr.get_or_fetch_hourly(
                    symbol,
                    lambda s: self.api.fetch_hourly_data(s)
                )
                
                # Check if hourly_df was successfully fetched
                if hourly_df is not None:
                    zones = self.zone_engine.build_zones(
                        symbol=symbol,
                        indicators=indicators,
                        current_price=current_price,
                        atr=atr,
                        hourly_df=hourly_df
                    )
                    
                    if zones:
                        self.cache_mgr.save_zones(symbol, zones)
            
            if not zones:
                return None
            
            # Step 4: Fetch hourly data for pattern detection
            hourly_df = self.cache_mgr.get_or_fetch_hourly(
                symbol,
                lambda s: self.api.fetch_hourly_data(s)
            )
            
            if hourly_df is None or len(hourly_df) < 2:
                return None
            
            # Calculate hourly ATR for momentum detection
            atr_1h = self.calculate_hourly_atr(hourly_df, period=20)
            
            # Step 5: Detect patterns (try regular patterns first)
            pattern_result = self.pattern_detector.detect_patterns(hourly_df)
            
            # If no regular pattern, try momentum breakout
            is_momentum = False
            if not pattern_result and atr_1h is not None:
                # Try bullish momentum
                bull_momentum = self.pattern_detector.detect_momentum_break(
                    hourly_df,
                    atr_1h,
                    'bullish',
                    index=-1,
                    cfg=self.momentum_cfg
                )
                
                # Try bearish momentum
                bear_momentum = self.pattern_detector.detect_momentum_break(
                    hourly_df,
                    atr_1h,
                    'bearish',
                    index=-1,
                    cfg=self.momentum_cfg
                )
                
                pattern_result = bull_momentum or bear_momentum
                
                if pattern_result:
                    is_momentum = True
            
            if not pattern_result or not pattern_result.get('pattern'):
                return None
            
            pattern = pattern_result
            
            # Step 6: Match pattern with zones
            # For momentum patterns, require actual zone breakout
            if is_momentum:
                side = 'bullish' if pattern['bias'] == 'bullish' else 'bearish'
                
                # Filter zones by type (resistance for bullish breakout, support for bearish breakdown)
                candidate_zones = [
                    z for z in zones
                    if (side == 'bullish' and z['type'] == 'resistance') or
                       (side == 'bearish' and z['type'] == 'support')
                ]
                
                if not candidate_zones:
                    return None
                
                # Check which zones were actually broken
                current_candle = hourly_df.iloc[-1]
                breakout_zones = []
                
                for zone in candidate_zones:
                    if self.check_zone_breakout(
                        candle_close=current_candle['Close'],
                        candle_open=current_candle['Open'],
                        zone=zone,
                        atr_daily=atr,
                        side=side,
                        buffer_mult=self.momentum_cfg.get('break_buffer_daily_atr', 0.10),
                        require_through_body=self.momentum_cfg.get('require_through_body', True)
                    ):
                        breakout_zones.append(zone)
                
                if not breakout_zones:
                    return None
                
                # Get best broken zone
                best_zone = max(breakout_zones, key=lambda z: z['strength'])
                
            else:
                # Regular pattern - use existing proximity logic
                # Filter zones near current price
                nearby_zones = [
                    z for z in zones 
                    if abs(z['mid'] - current_price) <= 0.35 * atr
                ]
                
                if not nearby_zones:
                    return None
                
                # Match pattern bias with zone type
                matching_zones = [
                    z for z in nearby_zones
                    if (pattern['bias'] == 'bullish' and z['type'] == 'support') or
                       (pattern['bias'] == 'bearish' and z['type'] == 'resistance')
                ]
                
                if not matching_zones:
                    return None
                
                # Get best zone
                best_zone = max(matching_zones, key=lambda z: z['strength'])
            
            # Step 7: Score confluence using new API
            signal_side = 'long' if pattern['bias'] == 'bullish' else 'short'
            
            
            # Step 9: Generate signal
            signal = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'side': signal_side,
                'price': current_price,
                'pattern': pattern['pattern'],
                'pattern_quality': pattern['quality'],
                'relative_volume': pattern['relative_volume'],
                'is_momentum_breakout': is_momentum,
                'zone': {
                    'type': best_zone['type'],
                    'mid': best_zone['mid'],
                    'low': best_zone['low'],
                    'high': best_zone['high'],
                    'components': best_zone['components'],
                    'strength': best_zone['strength']
                },
        
                'market_regime': market_regime,
                'atr': atr,
                'from_watchlist': symbol in self.watchlist,
                # For test display
                'current_price': current_price,
                'all_zones': zones,
                'nearby_zones': breakout_zones if is_momentum else [z for z in zones if abs(z['mid'] - current_price) <= 0.35 * atr],
                'signal_generated': True,
            }
            
            # Add momentum metrics if available
            if is_momentum and 'momentum_metrics' in pattern:
                signal['momentum_metrics'] = pattern['momentum_metrics']
            
            return signal
            
        except Exception as e:
            print(f"   âŒ {symbol}: Error - {str(e)[:50]}")
            return None
    
    def run_scan(self, symbols: Optional[List[str]] = None, 
                 send_alerts: bool = True) -> List[Dict]:
        """
        Run complete scan on stock universe - PARALLEL OPTIMIZED
        
        Args:
            symbols: Optional list of symbols (uses stock_universe if None)
            send_alerts: Whether to send Telegram alerts
            
        Returns:
            List of qualified signals
        """
        if symbols is None:
            symbols = self.stock_universe
        
        if not symbols:
            print("âŒ No symbols to scan")
            return []
        
        print(f"\n{'='*70}")
        print(f"ðŸš€ STARTING PARALLEL SCAN - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}")
        print(f"Stocks: {len(symbols)} | Workers: {self.max_workers}")
        
        # Get market regime once
        market_regime = self.index_regime.get_market_regime()
        print(self.index_regime.format_regime_summary(market_regime))
        
        # Scan all stocks in parallel
        signals = []
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_symbol = {
                executor.submit(self.scan_stock, symbol, market_regime): symbol
                for symbol in symbols
            }
            
            # Process completed tasks
            completed = 0
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                completed += 1
                
                try:
                    signal = future.result()
                    
                    if signal:
                        with self.scan_lock:
                            signals.append(signal)
                        
                        print(f"[{completed}/{len(symbols)}] âœ… {symbol}: {signal['quality'].upper()}")
                        
                        # Send alert if enabled
                        if send_alerts:
                            success = self.telegram.send_alert(signal)
                            if not success:
                                print(f"   âš ï¸  Alert failed")
                    else:
                        # Silent success - no signal
                        pass
                
                except Exception as e:
                    print(f"[{completed}/{len(symbols)}] âŒ {symbol}: {str(e)[:50]}")
                
                # Progress update every 50 stocks
                if completed % 50 == 0:
                    elapsed = time.time() - start_time
                    rate = completed / elapsed if elapsed > 0 else 0
                    remaining = len(symbols) - completed
                    eta = remaining / rate if rate > 0 else 0
                    
                    print(f"\n   ðŸ“Š Progress: {completed}/{len(symbols)} ({completed/len(symbols)*100:.0f}%) | Rate: {rate:.1f}/sec | ETA: {eta:.0f}s\n")
        
        # Summary
        elapsed = time.time() - start_time
        print(f"\n{'='*70}")
        print(f"ðŸ“ˆ SCAN COMPLETE")
        print(f"{'='*70}")
        print(f"Scanned: {len(symbols)} stocks in {elapsed:.1f}s ({len(symbols)/elapsed:.1f} stocks/sec)")
        print(f"Signals: {len(signals)}")
        
        if signals:
            print(f"\nðŸŽ¯ SIGNALS:")
            for sig in signals:
                print(f"   {sig['symbol']}: {sig['side'].upper()} @ ${sig['price']:.2f} ({sig['quality']})")
        
        return signals

    def test_single_stock(self, symbol: str, verbose: bool = True) -> None:
        """
        Test scanning on a single symbol with detailed output
        
        Args:
            symbol: Stock symbol to test
            verbose: If True, show all zones (default: True for testing)
        """
        print(f"\n{'='*70}")
        print(f"ðŸ§ª Testing: {symbol}")
        print(f"{'='*70}\n")
        
        market_regime = self.index_regime.get_market_regime()
        result = self.scan_stock(symbol, market_regime)
        
        if result is None:
            print("âŒ No signal generated")
            return
        
        # Display results
        print(f"\nðŸ“Š SCAN RESULTS:")
        print(f"   Symbol: {result['symbol']}")
        print(f"   Price: ${result['current_price']:.2f}")
        print(f"   ATR: ${result['atr']:.2f}")
        print(f"   Proximity threshold: Â±${0.35 * result['atr']:.2f} (0.35Ã—ATR)")
        
        # Show ALL zones
        all_zones = result.get('all_zones', [])
        if all_zones:
            print(f"\nðŸŽ¯ ALL ZONES ({len(all_zones)}):")
            
            support_zones = sorted([z for z in all_zones if z['type'] == 'support'], 
                                  key=lambda x: x['mid'], reverse=True)
            resistance_zones = sorted([z for z in all_zones if z['type'] == 'resistance'], 
                                     key=lambda x: x['mid'])
            
            if support_zones:
                print(f"\n   ðŸ“‰ SUPPORT ZONES ({len(support_zones)}):")
                for i, zone in enumerate(support_zones, 1):
                    distance = result['current_price'] - zone['mid']
                    distance_atr = distance / result['atr']
                    in_range = "âœ…" if abs(distance_atr) <= 0.35 else "  "
                    
                    print(f"   {in_range} S{i}: ${zone['mid']:.2f} (${zone['low']:.2f}-${zone['high']:.2f})")
                    print(f"        Distance: ${distance:.2f} ({distance_atr:.2f}Ã—ATR)")
                    print(f"        Components: {', '.join(zone['components'])}")
                    print(f"        Strength: {zone['strength']:.1f}/10")
            
            if resistance_zones:
                print(f"\n   ðŸ“ˆ RESISTANCE ZONES ({len(resistance_zones)}):")
                for i, zone in enumerate(resistance_zones, 1):
                    distance = zone['mid'] - result['current_price']
                    distance_atr = distance / result['atr']
                    in_range = "âœ…" if abs(distance_atr) <= 0.35 else "  "
                    
                    print(f"   {in_range} R{i}: ${zone['mid']:.2f} (${zone['low']:.2f}-${zone['high']:.2f})")
                    print(f"        Distance: ${distance:.2f} ({distance_atr:.2f}Ã—ATR)")
                    print(f"        Components: {', '.join(zone['components'])}")
                    print(f"        Strength: {zone['strength']:.1f}/10")
        
        # Show nearby zones
        nearby_zones = result.get('nearby_zones', [])
        if nearby_zones:
            print(f"\nâœ… ZONES IN RANGE ({len(nearby_zones)} within 0.35Ã—ATR):")
            for zone in nearby_zones:
                print(f"   â€¢ {zone['type'].upper()}: ${zone['mid']:.2f} - {zone['strength']:.1f}/10")
        else:
            print(f"\nâš ï¸  No zones within 0.35Ã—ATR range")
        
        # Show pattern
        pattern = result.get('pattern')
        if pattern:
            print(f"\nðŸ“Š PATTERN DETECTED:")
            print(f"   Type: {pattern['pattern']}")
            print(f"   Bias: {pattern['bias'].upper()}")
            print(f"   Price: ${pattern['price']:.2f}")
            print(f"   RV: {pattern['relative_volume']:.2f}x")
            print(f"   Quality: {pattern['quality'].upper()}")
        
        # Show signal status
        if result.get('signal_generated'):
            print(f"\nâœ… SIGNAL GENERATED")
            print(f"   Quality: {result.get('signal_quality', 'N/A')}")
            print(f"   Confluence: {result.get('confluence', 0):.1f}/10")
        else:
            print(f"\nâŒ No signal generated")


# Quick test function
def test_scanner():
    """Test scanner with sample stocks"""
    import config
    
    print("ðŸ§ª Testing Scanner")
    print("=" * 70)
    
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
    
    test_symbols = ['IBM', 'AAPL', 'MSFT']
    signals = scanner.run_scan(symbols=test_symbols, send_alerts=False)
    
    print(f"\nâœ… Scanner test complete! Signals: {len(signals)}")


if __name__ == "__main__":
    test_scanner()