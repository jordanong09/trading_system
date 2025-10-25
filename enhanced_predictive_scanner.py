# enhanced_predictive_scanner.py - MAS COMPLIANT v3.0
# STRICT GUARDRAILS: Alpha Vantage indicators only, cache-first, analysis-only alerts

import sys
import os
from datetime import datetime, timedelta
import pandas as pd
from typing import List, Dict, Optional
import time
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.alphavantage_client_optimized import OptimizedAlphaVantageClient, MarketScheduler
from modules.data_manager import DataManager
from modules.pattern_detector import PatternDetector
from modules.technical_indicators import TechnicalIndicators
from modules.chart_patterns import ChartPatterns
from telegram_sender import TelegramSender
import config_secure as config

# MAS COMPLIANCE: Forbidden words filter
FORBIDDEN_WORDS = {
    "buy", "sell", "enter", "exit", "target", "tp", "stop", 
    "sl", "stoploss", "guarantee", "will", "should", "must"
}

# Standard disclaimer
DISCLAIMER = (
    "This is market information and technical analysis for education and discussion. "
    "It is not financial advice and does not consider your personal objectives or "
    "financial situation. Past performance is not indicative of future results."
)

# Tech universe for QQQ indexing
TECH_UNIVERSE = {"AAPL", "MSFT", "NVDA", "META", "TSLA", "GOOGL", "AMZN", "NFLX"}


class EnhancedPredictiveScanner:
    """
    MAS-COMPLIANT ENHANCED PREDICTIVE SCANNER v3.0
    
    KEY FEATURES:
    - Alpha Vantage indicators only (NO local EMA/SMA computation)
    - Cache-first strategy: pre-cache at market open (09:30 ET)
    - Index-aware (SPY/QQQ) context
    - MAS-compliant language (analysis-only, no recommendations)
    - Strict T-5 predictive / T+1-3 confirmation timing
    
    TIMING:
    - 09:30 ET: Pre-cache daily indicators (all stocks + SPY + QQQ)
    - 10:25 ET: First predictive scan (T-5 before 10:30 close)
    - 10:31-33 ET: First confirmation scan (T+1-3 after 10:30 close)
    - Repeat hourly until 15:25/15:31-33 ET
    
    CACHE STRATEGY:
    - Build once at market open (09:30 ET)
    - Never refresh intra-day
    - Invalidate & rebuild next trading day
    - 210 x 1h candles history (~30 days)
    - Daily values from PREVIOUS trading day (latest completed bar)
    """
    
    def __init__(self, api_key: str, telegram_bot: str, telegram_chat: str):
        # Create cache directory
        cache_dir = "cache"
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            print(f"✅ Created cache directory: {cache_dir}\n")
        else:
            cache_files = [f for f in os.listdir(cache_dir) if f.endswith('.json')]
            if cache_files:
                print(f"📁 Found {len(cache_files)} cached files\n")
        
        # Initialize clients
        self.av_client = OptimizedAlphaVantageClient(api_key, rate_limit_per_min=150)
        self.data_manager = DataManager(cache_dir=cache_dir)
        self.telegram = TelegramSender(telegram_bot, telegram_chat)
        self.detector = PatternDetector(vars(config))
        self.chart_detector = ChartPatterns({'SYMBOL': 'UNKNOWN'})

        
        # Scanner state
        self.symbols = []
        self.reference_index = None  # SPY or QQQ
        self.tech_universe = TECH_UNIVERSE
        self.scan_lead_time_minutes = 5  # T-5
        self.last_scan_date = None
        self.pending_signals = []
        self.cache_dir = cache_dir
        self.daily_cache_valid = False
        
        print(f"\n{'='*80}")
        print(f"🚀 MAS-COMPLIANT ENHANCED PREDICTIVE SCANNER v3.0")
        print(f"{'='*80}")
        print(f"Configuration:")
        print(f"  ⚡ Pre-cache: Market open (09:30 ET)")
        print(f"  🔮 Predictive scan: T-5 (10:25, 11:25, ..., 15:25 ET)")
        print(f"  ✅ Confirmation scan: T+1-3 (closed bar only)")
        print(f"  💾 Cache lifecycle: Build once at open, use all day")
        print(f"  📊 Daily indicators: Previous day's completed bar")
        print(f"  📈 Intraday history: 210 x 1h candles (~30 days)")
        print(f"  🔒 Compliance: MAS-aware language + disclaimer")
        print(f"  📍 Index awareness: SPY/QQQ context")
        print(f"{'='*80}\n")
    
    def load_watchlist(self, file_path: str) -> List[str]:
        """Load symbols from Excel/CSV"""
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            symbols = df['Symbol'].dropna().str.upper().tolist()
            self.symbols = symbols[:200]
            
            # Determine reference index
            self.reference_index = self._determine_index(self.symbols)
            
            print(f"✅ Loaded {len(self.symbols)} symbols")
            print(f"📊 Reference index: {self.reference_index}")
            print()
            
            return self.symbols
            
        except Exception as e:
            print(f"❌ Error loading watchlist: {e}")
            return []
    
    def _determine_index(self, symbols: List[str]) -> str:
        """
        Determine reference index based on watchlist composition
        - QQQ for tech-heavy watchlist (>50% tech stocks)
        - SPY for general market
        """
        if not symbols:
            return "SPY"
        
        tech_count = sum(1 for s in symbols if s in self.tech_universe)
        tech_ratio = tech_count / len(symbols)
        
        if tech_ratio > 0.5:
            print(f"   Tech stocks: {tech_count}/{len(symbols)} ({tech_ratio*100:.0f}%) → Using QQQ")
            return "QQQ"
        else:
            print(f"   Tech stocks: {tech_count}/{len(symbols)} ({tech_ratio*100:.0f}%) → Using SPY")
            return "SPY"
    
    def precache_daily_indicators(self):
        """
        PRE-CACHE DAILY INDICATORS at MARKET OPEN (09:30 ET)
        
        Fetches from Alpha Vantage indicators API:
        - EMA20 (daily)
        - SMA50/100/200 (daily)
        - Daily close (for "near level" calculations)
        
        For: All watchlist stocks + SPY + QQQ (both indices cached)
        
        CRITICAL DATA FRESHNESS RULE:
        - Uses PREVIOUS trading day's completed bar
        - Ignores any partial "current day" bar (until 16:00 ET)
        - Implementation: Select most recent 1D bar where timestamp < today's session close
        
        INTRADAY HISTORY:
        - Ensures 210 x 1h candles (~30 days) per stock
        
        LIFECYCLE:
        - Build ONCE at market open (09:30 ET)
        - Never refresh intra-day
        - Invalidate & rebuild next trading day
        """
        # Get current ET time
        et_now = MarketScheduler.get_et_now()
        today = et_now.strftime("%Y-%m-%d")
        
        print(f"\n{'='*80}")
        print(f"💾 PRE-CACHING DAILY INDICATORS (MARKET OPEN)")
        print(f"   Time: {et_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"   Target: All watchlist + SPY + QQQ")
        print(f"   Data: Previous day's completed bars only")
        print(f"{'='*80}\n")
        
        if not self.symbols:
            print("❌ No symbols loaded, cannot pre-cache\n")
            return False
        
        # Cache BOTH SPY and QQQ (determine index usage later)
        all_symbols = self.symbols + ["SPY", "QQQ"]
        
        cached_count = 0
        failed_symbols = []
        
        for symbol in all_symbols:
            try:
                # Fetch from Alpha Vantage indicators (NOT local computation)
                # CRITICAL: Use previous trading day's completed bar
                indicators = self.av_client.fetch_daily_indicators(
                    symbol, 
                    use_previous_complete_bar=True  # Ignore partial current-day bar
                )
                
                if indicators:
                    # Validate we got previous day's data (not today's partial)
                    indicator_date = indicators.get('date')
                    if indicator_date == today:
                        print(f"   ⚠️  {symbol}: Got current day's partial bar, waiting for previous complete bar")
                        # Try to get explicitly previous bar
                        indicators = self.av_client.fetch_daily_indicators(
                            symbol,
                            use_previous_complete_bar=True,
                            offset=1  # Force previous bar
                        )
                    
                    # Cache with today's date key (even though data is from previous day)
                    cache_key = f"daily_{symbol}_{today}.json"
                    cache_path = os.path.join(self.cache_dir, cache_key)
                    
                    # Add metadata
                    indicators['cached_at'] = et_now.isoformat()
                    indicators['trading_day'] = today
                    indicators['data_from_previous_day'] = True
                    
                    with open(cache_path, 'w') as f:
                        json.dump(indicators, f, indent=2)
                    
                    cached_count += 1
                    ema20 = indicators.get('ema20')
                    close = indicators.get('close')
                    bar_date = indicators.get('date', 'N/A')
                    
                    # Format with proper conditional
                    ema20_str = f"{ema20:.2f}" if ema20 else "N/A"
                    close_str = f"{close:.2f}" if close else "N/A"
                    
                    print(f"   ✅ {symbol}: EMA20={ema20_str}, Close={close_str} (date: {bar_date})")
                else:
                    failed_symbols.append(symbol)
                    print(f"   ⚠️  {symbol}: No data returned")
                    
            except Exception as e:
                failed_symbols.append(symbol)
                print(f"   ❌ {symbol}: {e}")
        
        self.daily_cache_valid = True
        
        print(f"\n{'='*80}")
        print(f"✅ PRE-CACHE COMPLETE (MARKET OPEN)")
        print(f"   Cached: {cached_count}/{len(all_symbols)} symbols")
        print(f"   Using: Previous trading day's completed bars")
        if failed_symbols:
            print(f"   Failed: {', '.join(failed_symbols[:5])}")
        print(f"   Status: Ready for T-5 scans (zero indicator calls all day)")
        print(f"   Next refresh: Tomorrow's market open (09:30 ET)")
        print(f"{'='*80}\n")
        
        return cached_count > 0
    

    def precache_historical_data(self):
        """
        PRE-CACHE HISTORICAL INTRADAY DATA (1H candles)
        
        Fetches 210 bars of 1H data (~30 trading days) for:
        - All watchlist stocks
        - SPY and QQQ indices
        
        This ensures we have sufficient history for:
        - Chart pattern detection (needs 60+ bars)
        - Technical analysis
        - Support/resistance calculations
        
        Called at startup or when cache is invalid
        """
        et_now = MarketScheduler.get_et_now()
        today = et_now.strftime("%Y-%m-%d")
        
        print(f"\n{'='*80}")
        print(f"📊 PRE-CACHING HISTORICAL 1H DATA")
        print(f"   Time: {et_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"   Target: All watchlist + SPY + QQQ")
        print(f"   Bars: 210 x 1H candles (~30 trading days)")
        print(f"{'='*80}\n")
        
        if not self.symbols:
            print("❌ No symbols loaded, cannot pre-cache\n")
            return False
        
        all_symbols = self.symbols + ["SPY", "QQQ"]
        
        cached_count = 0
        failed_symbols = []
        
        for symbol in all_symbols:
            try:
                # Fetch 1H data with full history
                intraday_data = self.av_client.fetch_intraday(
                    symbol, 
                    interval='60min'  # Get maximum history
                )
                
                if intraday_data and 'full_data' in intraday_data:
                    df = intraday_data['full_data']
                    
                    # Keep last 210 bars
                    if len(df) > 210:
                        df = df.tail(210).reset_index(drop=True)
                    
                    # Cache the data
                    cache_key = f"intraday_1h_{symbol}_{today}.json"
                    cache_path = os.path.join(self.cache_dir, cache_key)
                    
                    # Convert DataFrame to dict for JSON serialization
                    # Convert timestamps to strings for JSON compatibility
                    df_json = df.copy()
                    df_json['Date'] = df_json['Date'].dt.strftime('%Y-%m-%d %H:%M:%S')
                    
                    cache_data = {
                        'symbol': symbol,
                        'interval': '60min',
                        'bars': len(df),
                        'cached_at': et_now.isoformat(),
                        'trading_day': today,
                        'data': df_json.to_dict('records'),
                        'latest_close': float(df.iloc[-1]['Close']) if len(df) > 0 else None
                    }
                    
                    with open(cache_path, 'w') as f:
                        json.dump(cache_data, f, indent=2)
                    
                    cached_count += 1
                    latest_close = cache_data['latest_close']
                    close_str = f"{latest_close:.2f}" if latest_close else "N/A"
                    print(f"   ✅ {symbol}: {len(df)} bars cached, Latest Close={close_str}")
                else:
                    failed_symbols.append(symbol)
                    print(f"   ⚠️  {symbol}: No data returned")
                    
            except Exception as e:
                failed_symbols.append(symbol)
                print(f"   ❌ {symbol}: {e}")
        
        print(f"\n{'='*80}")
        print(f"✅ HISTORICAL DATA CACHE COMPLETE")
        print(f"   Cached: {cached_count}/{len(all_symbols)} symbols")
        if failed_symbols:
            print(f"   Failed: {', '.join(failed_symbols)}")
        print(f"{'='*80}\n")
        
        return cached_count > 0


    def precache_daily_ohlcv_data(self):
        """
        PRE-CACHE DAILY OHLCV DATA (1D bars)
        
        Fetches 60 bars of daily data for:
        - All watchlist stocks
        - SPY and QQQ indices
        
        Uses 60min data aggregated to daily bars to ensure:
        - Consistent data source (no separate API endpoint needed)
        - Sufficient history for daily chart patterns (60 days)
        - No invalid API calls
        
        Called at startup or when cache is invalid
        """
        et_now = MarketScheduler.get_et_now()
        today = et_now.strftime("%Y-%m-%d")
        
        print(f"\n{'='*80}")
        print(f"📅 PRE-CACHING DAILY (1D) OHLCV DATA")
        print(f"   Time: {et_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"   Target: All watchlist + SPY + QQQ")
        print(f"   Bars: 60 daily bars (~60 trading days)")
        print(f"{'='*80}\n")
        
        if not self.symbols:
            print("❌ No symbols loaded, cannot pre-cache\n")
            return False
        
        all_symbols = self.symbols + ["SPY", "QQQ"]
        
        cached_count = 0
        failed_symbols = []
        
        for symbol in all_symbols:
            try:
                # Fetch 60min data with full history
                intraday_data = self.av_client.fetch_intraday(
                    symbol, 
                    interval='60min'  # Get maximum history
                )
                
                if intraday_data and 'full_data' in intraday_data:
                    df_hourly = intraday_data['full_data']
                    
                    # Aggregate hourly data to daily bars
                    df_hourly['Date_only'] = pd.to_datetime(df_hourly['Date']).dt.date
                    
                    df_daily = df_hourly.groupby('Date_only').agg({
                        'Open': 'first',
                        'High': 'max',
                        'Low': 'min',
                        'Close': 'last',
                        'Volume': 'sum'
                    }).reset_index()
                    
                    # Rename and format
                    df_daily['Date'] = pd.to_datetime(df_daily['Date_only'])
                    df_daily = df_daily.drop('Date_only', axis=1)
                    df_daily = df_daily.sort_values('Date').reset_index(drop=True)
                    
                    # Keep last 60 bars
                    if len(df_daily) > 60:
                        df_daily = df_daily.tail(60).reset_index(drop=True)
                    
                    # Cache the data
                    cache_key = f"daily_ohlcv_{symbol}_{today}.json"
                    cache_path = os.path.join(self.cache_dir, cache_key)
                    
                    # Convert DataFrame to dict for JSON serialization
                    # Convert timestamps to strings for JSON compatibility
                    df_daily_json = df_daily.copy()
                    df_daily_json['Date'] = df_daily_json['Date'].dt.strftime('%Y-%m-%d')
                    
                    cache_data = {
                        'symbol': symbol,
                        'interval': '1D',
                        'bars': len(df_daily),
                        'cached_at': et_now.isoformat(),
                        'trading_day': today,
                        'data': df_daily_json.to_dict('records'),
                        'latest_close': float(df_daily.iloc[-1]['Close']) if len(df_daily) > 0 else None
                    }
                    
                    with open(cache_path, 'w') as f:
                        json.dump(cache_data, f, indent=2)
                    
                    cached_count += 1
                    latest_close = cache_data['latest_close']
                    close_str = f"{latest_close:.2f}" if latest_close else "N/A"
                    print(f"   ✅ {symbol}: {len(df_daily)} daily bars cached, Latest Close={close_str}")
                else:
                    failed_symbols.append(symbol)
                    print(f"   ⚠️  {symbol}: No data returned")
                    
            except Exception as e:
                failed_symbols.append(symbol)
                print(f"   ❌ {symbol}: {e}")
        
        print(f"\n{'='*80}")
        print(f"✅ DAILY OHLCV CACHE COMPLETE")
        print(f"   Cached: {cached_count}/{len(all_symbols)} symbols")
        if failed_symbols:
            print(f"   Failed: {', '.join(failed_symbols)}")
        print(f"{'='*80}\n")
        
        return cached_count > 0

    def _read_cached_daily_indicators(self, symbol: str) -> Optional[Dict]:
        """
        Read cached daily indicators for a symbol
        Returns None if cache miss (no local computation fallback)
        """
        et_now = MarketScheduler.get_et_now()
        today = et_now.strftime("%Y-%m-%d")
        cache_key = f"daily_{symbol}_{today}.json"
        cache_path = os.path.join(self.cache_dir, cache_key)
        
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"   ⚠️  Cache read error for {symbol}: {e}")
                return None
        
        return None
    
    def _build_stock_context(self, stock_data: Dict, daily_indicators: Dict, current_close: float) -> Dict:
        """
        Build stock context using cached daily indicators
        
        Returns:
            {
                "price": float,
                "ema20": float,
                "sma50": float,
                "sma100": float,
                "sma200": float,
                "above_ema20": bool,
                "near_levels": [{"name", "value", "distance_pct", "label"}]
            }
        """
        if not daily_indicators:
            return {
                "price": current_close,
                "ema20": None,
                "sma50": None,
                "sma100": None,
                "sma200": None,
                "above_ema20": None,
                "near_levels": []
            }
        
        ema20 = daily_indicators.get('ema20')
        sma50 = daily_indicators.get('sma50')
        sma100 = daily_indicators.get('sma100')
        sma200 = daily_indicators.get('sma200')
        
        # Determine if price is near major levels (±1.0%)
        near_levels = []
        threshold_pct = 1.0
        
        for name, value in [("SMA50", sma50), ("SMA100", sma100), ("SMA200", sma200)]:
            if value:
                distance_pct = abs((current_close - value) / value * 100)
                if distance_pct <= threshold_pct:
                    label = "support" if current_close > value else "resistance"
                    near_levels.append({
                        "name": name,
                        "value": value,
                        "distance_pct": distance_pct,
                        "label": label
                    })
        
        return {
            "price": current_close,
            "ema20": ema20,
            "sma50": sma50,
            "sma100": sma100,
            "sma200": sma200,
            "above_ema20": current_close > ema20 if ema20 else None,
            "near_levels": near_levels
        }
    
    def _build_index_context(self, index_data: Dict, daily_indicators: Dict) -> Dict:
        """
        Build index context (SPY/QQQ) using cached daily indicators
        
        Returns:
            {
                "name": "SPY|QQQ",
                "close": float,
                "ema20": float,
                "sma50": float,
                "sma100": float,
                "sma200": float,
                "above_ema20": bool,  # "strength" if True, "weakness" if False
                "near_levels": [...]
            }
        """
        if not index_data or not daily_indicators:
            return {
                "name": self.reference_index,
                "close": None,
                "ema20": None,
                "sma50": None,
                "sma100": None,
                "sma200": None,
                "above_ema20": None,
                "near_levels": []
            }
        
        index_close = index_data.get('close')
        ema20 = daily_indicators.get('ema20')
        sma50 = daily_indicators.get('sma50')
        sma100 = daily_indicators.get('sma100')
        sma200 = daily_indicators.get('sma200')
        
        # Determine if index is near major levels
        near_levels = []
        threshold_pct = 1.0
        
        for name, value in [("SMA50", sma50), ("SMA100", sma100), ("SMA200", sma200)]:
            if value and index_close:
                distance_pct = abs((index_close - value) / value * 100)
                if distance_pct <= threshold_pct:
                    label = "support" if index_close > value else "resistance"
                    near_levels.append({
                        "name": name,
                        "value": value,
                        "distance_pct": distance_pct,
                        "label": label
                    })
        
        return {
            "name": self.reference_index,
            "close": index_close,
            "ema20": ema20,
            "sma50": sma50,
            "sma100": sma100,
            "sma200": sma200,
            "above_ema20": index_close > ema20 if (index_close and ema20) else None,
            "near_levels": near_levels
        }
    
    def _sanitize_message(self, message: str) -> str:
        """
        MAS COMPLIANCE: Check for forbidden words
        Raises ValueError if non-compliant language detected
        """
        message_lower = message.lower()
        
        for word in FORBIDDEN_WORDS:
            if word in message_lower:
                raise ValueError(f"Non-compliant language detected: '{word}'")
        
        return message
    
    def _format_compliant_alert(self, signal: Dict, status: str = "PENDING") -> str:
        """
        Format MAS-compliant Telegram alert
        Uses analysis-only language, includes disclaimer
        """
        symbol = signal['symbol']
        pattern = signal['pattern']
        stock_ctx = signal['stock_context']
        index_ctx = signal['index_context']
        
        # Build message with compliant language
        msg = f"<b>{symbol} — 1h Analysis</b>\n\n"
        
        # Status
        if status == "PENDING":
            msg += "⚠️ <b>PATTERN FORMING (PENDING CLOSE)</b>\n\n"
        elif status == "CONFIRMED":
            msg += "✅ <b>PATTERN CONFIRMED (CLOSED)</b>\n\n"
        elif status == "FAILED":
            msg += "❌ <b>PATTERN FAILED (CLOSED)</b>\n\n"
        
        # Pattern observation - SANITIZE the pattern name
        pattern_name = pattern.get('pattern', 'N/A')
        # Remove forbidden words from pattern name
        pattern_name = pattern_name.replace('target', 'projected')
        pattern_name = pattern_name.replace('Target', 'Projected')
        pattern_name = pattern_name.replace('TARGET', 'PROJECTED')
        
        msg += f"<b>Pattern Observed:</b> {self.telegram.escape(pattern_name)}\n"
        msg += f"<b>Bias:</b> {self.telegram.escape(pattern.get('bias', 'N/A'))}\n"
        msg += f"<b>Price:</b> ${stock_ctx['price']:.2f}\n\n"
        
        # Stock context (1h close vs daily EMA20)
        msg += "<b>Stock Context (Daily Indicators):</b>\n"
        if stock_ctx['ema20']:
            position = "above" if stock_ctx['above_ema20'] else "below"
            msg += f"• Close vs EMA20: {position} (${stock_ctx['ema20']:.2f})\n"
        
        # Near levels
        if stock_ctx['near_levels']:
            level = stock_ctx['near_levels'][0]
            msg += f"• Near {level['name']}: ${level['value']:.2f} ({level['label']})\n"
        
        msg += "\n"
        
        # Index context
        msg += f"<b>Index Context ({index_ctx['name']}, Daily):</b>\n"
        if index_ctx['close'] and index_ctx['ema20']:
            if index_ctx['above_ema20']:
                msg += f"• Close ${index_ctx['close']:.2f} > EMA20 ${index_ctx['ema20']:.2f}\n"
                msg += f"• Broader backdrop suggests supportive conditions for {pattern.get('bias', 'N/A').lower()} patterns\n"
            else:
                msg += f"• Close ${index_ctx['close']:.2f} < EMA20 ${index_ctx['ema20']:.2f}\n"
                msg += f"• Broader backdrop suggests unsupportive conditions for {pattern.get('bias', 'N/A').lower()} patterns\n"
        
        # Near index levels
        if index_ctx['near_levels']:
            level = index_ctx['near_levels'][0]
            msg += f"• Near {level['name']}: ${level['value']:.2f} ({level['label']} zone)\n"

        msg += "\n"

        # Add technical observations (MAS-compliant - no directives)
        msg += "<b>Technical Observations:</b>\n"

        # For bullish patterns
        if pattern.get('bias') == 'BULLISH':
            if stock_ctx.get('near_levels'):
                level = stock_ctx['near_levels'][0]
                msg += f"• Potential resistance zone observed: ${level['value']:.2f}\n"
            
            # Observed price levels (NOT "targets" or "stops")
            if index_ctx.get('sma50'):
                msg += f"• Notable level above: ${index_ctx['sma50']:.2f} (SMA50)\n"

        # For bearish patterns
        elif pattern.get('bias') == 'BEARISH':
            if stock_ctx.get('near_levels'):
                level = stock_ctx['near_levels'][0]
                msg += f"• Potential support zone observed: ${level['value']:.2f}\n"
            
            if index_ctx.get('sma50'):
                msg += f"• Notable level below: ${index_ctx['sma50']:.2f} (SMA50)\n"

        msg += "\n"
        msg += "─" * 40 + "\n"
        msg += f"<i>{DISCLAIMER}</i>"
        
        # Sanitize before sending
        return self._sanitize_message(msg)
    
    def scan_predictive_enhanced(self, minutes_before_close: int = 5):
        """
        PREDICTIVE SCAN - T-5 minutes before candle close
        NOW WITH CHART PATTERNS (18 total patterns)
        """
        et_now = MarketScheduler.get_et_now()
        
        print(f"\n{'='*80}")
        print(f"🔮 PREDICTIVE SCAN: {et_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"   T-{minutes_before_close} min before candle close")
        print(f"   Scanning for 18 patterns (12 candlestick + 6 chart)")
        print(f"{'='*80}\n")
        
        if not self.daily_cache_valid:
            print("⚠️  Daily cache not valid! Run precache_daily_indicators() first.\n")
            return
        
        # Fetch ONLY 1h OHLCV (no indicator calls)
        print(f"📊 Fetching 1h OHLCV for {len(self.symbols)} stocks...")
        all_stock_data = self.av_client.batch_fetch_stocks(self.symbols, interval="60min")
        
        # Fetch index 1h OHLCV
        print(f"📈 Fetching {self.reference_index} 1h OHLCV...")
        index_data = self.av_client.fetch_intraday(self.reference_index, interval="60min")
        
        if not all_stock_data:
            print("❌ No stock data retrieved\n")
            return
        
        # Read cached indicators (zero API calls)
        print(f"💾 Reading cached daily indicators...")
        index_daily = self._read_cached_daily_indicators(self.reference_index)
        
        cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.json')]
        print(f"📁 Cache: {len(cache_files)} files | Retrieved: {len(all_stock_data)} stocks\n")
        
        predicted_signals = []
        
        for stock_data in all_stock_data:
            try:
                symbol = stock_data['symbol']
                current_price = stock_data['close']
                
                # Read cached daily indicators (zero API calls)
                stock_daily = self._read_cached_daily_indicators(symbol)
                
                if not stock_daily:
                    print(f"   ⚠️  {symbol}: No cached indicators, skipping")
                    continue
                
                # Get enhanced data with S/R analysis (from intraday data)
                enhanced_data = self.data_manager.get_enhanced_stock_data(
                    symbol,
                    stock_data['full_data']
                )
                
                # ================================================================
                # PATTERN DETECTION - CANDLESTICK PATTERNS (1H timeframe)
                # ================================================================
                df_pattern = stock_data['full_data'].copy()
                recent_df = df_pattern.iloc[-10:].copy()
                patterns_found = []
                
                # Detect all 12 candlestick patterns
                candlestick_patterns = [
                    self.detector.detect_bullish_engulfing,
                    self.detector.detect_bearish_engulfing,
                    self.detector.detect_hammer,
                    self.detector.detect_shooting_star,
                    self.detector.detect_morning_star,
                    self.detector.detect_evening_star,
                    self.detector.detect_three_white_soldiers,
                    self.detector.detect_three_black_crows,
                    self.detector.detect_bullish_abandoned_baby,
                    self.detector.detect_bearish_abandoned_baby,
                    self.detector.detect_breakout,
                    self.detector.detect_bearish_breakdown
                ]
                
                for pattern_func in candlestick_patterns:
                    detections = pattern_func(recent_df)
                    if detections and detections[-1]['date'] == df_pattern.iloc[-1]['Date']:
                        pattern = detections[-1]
                        pattern['pattern_type'] = 'CANDLESTICK'
                        pattern['timeframe'] = '1H'
                        patterns_found.append(pattern)
                
                # ================================================================
                # PATTERN DETECTION - CHART PATTERNS (1H timeframe)
                # ================================================================
                if len(df_pattern) >= 60:  # Need sufficient data for chart patterns
                    print(f"   📊 {symbol}: Checking chart patterns...")
                    
                    # Update chart detector config with current symbol
                    self.chart_detector.config['SYMBOL'] = symbol
                    
                    # Detect all 6 chart patterns on 1H timeframe
                    chart_patterns_1h = self.chart_detector.detect_all_patterns(df_pattern, timeframe='1H')
                    
                    # Only include patterns detected on most recent bar
                    for chart_pattern in chart_patterns_1h:
                        # Check if pattern is recent (within last 5 bars)
                        pattern_date = chart_pattern['date']
                        if pattern_date >= df_pattern.iloc[-5]['Date']:
                            chart_pattern['pattern_type'] = 'CHART'
                            chart_pattern['timeframe'] = '1H'
                            patterns_found.append(chart_pattern)
                            print(f"      ✅ Found: {chart_pattern['pattern']}")
                
                # ================================================================
                # PATTERN DETECTION - CHART PATTERNS (DAILY timeframe)
                # ================================================================
                # For Daily chart patterns, use cached daily OHLCV data
                try:
                    # Load from cache (pre-cached at startup)
                    et_now = MarketScheduler.get_et_now()
                    today = et_now.strftime("%Y-%m-%d")
                    cache_key = f"daily_ohlcv_{symbol}_{today}.json"
                    cache_path = os.path.join(self.cache_dir, cache_key)
                    
                    df_daily = None
                    
                    if os.path.exists(cache_path):
                        # Load from cache
                        with open(cache_path, 'r') as f:
                            cache_data = json.load(f)
                        
                        # Convert back to DataFrame
                        df_daily = pd.DataFrame(cache_data['data'])
                        # Convert date strings back to datetime
                        if 'Date' in df_daily.columns:
                            df_daily['Date'] = pd.to_datetime(df_daily['Date'])
                        print(f"   📅 {symbol}: Using cached daily data ({len(df_daily)} bars)")
                    else:
                        # Fallback: aggregate from 60min if cache not available
                        print(f"   ⚠️  {symbol}: Daily cache not found, aggregating from 60min...")
                        daily_stock_data = self.av_client.fetch_intraday(symbol, interval='60min')
                        
                        if daily_stock_data and 'full_data' in daily_stock_data:
                            df_hourly = daily_stock_data['full_data']
                            
                            # Aggregate hourly data to daily bars
                            df_hourly['Date_only'] = pd.to_datetime(df_hourly['Date']).dt.date
                            
                            df_daily = df_hourly.groupby('Date_only').agg({
                                'Open': 'first',
                                'High': 'max',
                                'Low': 'min',
                                'Close': 'last',
                                'Volume': 'sum'
                            }).reset_index()
                            
                            df_daily['Date'] = pd.to_datetime(df_daily['Date_only'])
                            df_daily = df_daily.drop('Date_only', axis=1)
                            df_daily = df_daily.sort_values('Date').reset_index(drop=True)
                    
                    # Detect patterns if we have sufficient data
                    if df_daily is not None and len(df_daily) >= 60:
                        print(f"   📊 {symbol}: Checking DAILY chart patterns...")
                        
                        # Detect chart patterns on Daily timeframe
                        chart_patterns_daily = self.chart_detector.detect_all_patterns(df_daily, timeframe='Daily')
                        
                        # Only include recent patterns
                        for chart_pattern in chart_patterns_daily:
                            pattern_date = chart_pattern['date']
                            if pattern_date >= df_daily.iloc[-5]['Date']:
                                chart_pattern['pattern_type'] = 'CHART'
                                chart_pattern['timeframe'] = 'Daily'
                                patterns_found.append(chart_pattern)
                                print(f"      ✅ Found: {chart_pattern['pattern']} (Daily)")
                    elif df_daily is not None:
                        print(f"   ⚠️  {symbol}: Insufficient daily data ({len(df_daily)} bars, need 60+)")
                        
                except Exception as e:
                    print(f"   ❌ {symbol}: Error in daily pattern detection: {e}")
                
                if not patterns_found:
                    continue
                
                # Build contexts
                stock_context = self._build_stock_context(stock_data, stock_daily, current_price)
                index_context = self._build_index_context(index_data, index_daily)
                
                # ================================================================
                # EVALUATE EACH PATTERN WITH ENHANCED CONFLUENCE
                # ================================================================
                for pattern in patterns_found:
                    # Enhanced confluence with chart pattern awareness
                    confluence = self._evaluate_enhanced_confluence(
                        pattern['bias'],
                        pattern,
                        stock_context,
                        index_context,
                        enhanced_data['support_resistance'],
                        enhanced_data['breakout_analysis']
                    )
                    
                    if confluence['recommendation'] in ['STRONG_SIGNAL', 'GOOD_SIGNAL']:
                        signal = {
                            'symbol': symbol,
                            'pattern': pattern,
                            'stock_context': stock_context,
                            'index_context': index_context,
                            'confluence': confluence,
                            'support_resistance': enhanced_data['support_resistance'],
                            'breakout_analysis': enhanced_data['breakout_analysis'],
                            'status': 'PENDING',
                            'timestamp': MarketScheduler.get_et_now()
                        }
                        
                        predicted_signals.append(signal)
                        
                        pattern_label = f"{pattern['pattern']} ({pattern['pattern_type']}, {pattern['timeframe']})"
                        print(f"   🎯 {symbol}: {pattern_label}")
                        print(f"      Signal: {confluence['recommendation']} ({confluence['percentage']:.0f}%)")
                        
                        # Show chart pattern specific info
                        if pattern['pattern_type'] == 'CHART':
                            completion_rate = pattern.get('historical_completion_rate', 0) * 100
                            print(f"      Completion Rate: {completion_rate:.0f}%")
                            if 'measured_move_pct' in pattern:
                                print(f"      Measured Move: {pattern['measured_move_pct']:.1f}%")
            
            except Exception as e:
                print(f"   ❌ Error analyzing {stock_data.get('symbol', 'UNKNOWN')}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Send predictive alerts
        if predicted_signals:
            print(f"\n{'='*80}")
            print(f"📤 SENDING {len(predicted_signals)} PREDICTIVE ALERTS")
            print(f"{'='*80}\n")
            
            for signal in predicted_signals:
                try:
                    alert_msg = self._format_enhanced_compliant_alert(signal, status="PENDING")
                    self.telegram.send_message(alert_msg, parse_mode="HTML")
                except ValueError as e:
                    print(f"   ❌ {signal['symbol']}: Non-compliant message blocked - {e}")
                except Exception as e:
                    print(f"   ❌ {signal['symbol']}: Alert failed - {e}")
            
            self.pending_signals = predicted_signals
            print(f"\n✅ Predictive alerts sent!")
        else:
            print(f"\n📊 No qualifying signals in predictive scan.\n")
            self.pending_signals = []
    
    def _evaluate_index_aware_confluence(self, pattern_bias: str, stock_context: Dict,
                                        index_context: Dict, sr_levels: Dict, 
                                        breakout: Dict) -> Dict:
        """
        Enhanced confluence with index awareness
        Total: 8 points (added index alignment)
        """
        score = 0
        max_score = 8
        reasons = []
        
        # 1. Index backdrop alignment (2 points)
        if index_context['above_ema20'] is not None:
            index_strength = index_context['above_ema20']
            
            if pattern_bias == "BULLISH" and index_strength:
                score += 2
                reasons.append(f"✅ Index ({index_context['name']}) above EMA20 (supportive backdrop)")
            elif pattern_bias == "BEARISH" and not index_strength:
                score += 2
                reasons.append(f"✅ Index ({index_context['name']}) below EMA20 (supportive backdrop)")
            else:
                reasons.append(f"⚠️  Index backdrop unsupportive for {pattern_bias} pattern")
        
        # 2. Stock vs EMA20 alignment (2 points)
        if stock_context['above_ema20'] is not None:
            if pattern_bias == "BULLISH" and stock_context['above_ema20']:
                score += 2
                reasons.append(f"✅ Stock above daily EMA20 (${stock_context['ema20']:.2f})")
            elif pattern_bias == "BEARISH" and not stock_context['above_ema20']:
                score += 2
                reasons.append(f"✅ Stock below daily EMA20 (${stock_context['ema20']:.2f})")
        
        # 3. Near horizontal S/R level (2 points)
        if pattern_bias == "BULLISH":
            support_levels = sr_levels.get('support', [])
            if support_levels and support_levels[0]['distance_pct'] < 2:
                score += 2
                reasons.append(f"✅ Near support @ ${support_levels[0]['price']:.2f}")
        elif pattern_bias == "BEARISH":
            resistance_levels = sr_levels.get('resistance', [])
            if resistance_levels and resistance_levels[0]['distance_pct'] < 2:
                score += 2
                reasons.append(f"✅ Near resistance @ ${resistance_levels[0]['price']:.2f}")
        
        # 4. Breakout imminent (2 points)
        if breakout.get('breakout_imminent') and breakout['direction'] == pattern_bias:
            score += 2
            reasons.append(f"✅ Breakout imminent ({breakout['direction']})")
        
        # Calculate percentage and recommendation
        percentage = (score / max_score) * 100
        
        if percentage >= 75:  # 6/8 or better
            recommendation = "STRONG_SIGNAL"
        elif percentage >= 62:  # 5/8
            recommendation = "GOOD_SIGNAL"
        elif percentage >= 50:  # 4/8
            recommendation = "MODERATE_SIGNAL"
        else:
            recommendation = "WEAK_SIGNAL"
        
        return {
            'confluence_score': score,
            'max_score': max_score,
            'percentage': percentage,
            'recommendation': recommendation,
            'reasons': reasons
        }
    
    def _evaluate_enhanced_confluence(self, pattern_bias: str, pattern: Dict,
                                 stock_context: Dict, index_context: Dict, 
                                 sr_levels: Dict, breakout: Dict) -> Dict:
        """
        ENHANCED confluence with chart pattern awareness
        
        Total: 10 points (increased from 8)
        
        Scoring:
        - Index backdrop alignment (3 points) - INCREASED from 2
        - Stock vs EMA20 alignment (2 points)
        - Near horizontal S/R level (2 points)
        - Breakout imminent (1 point) - DECREASED from 2
        - Chart pattern completion rate (1 point) - NEW
        - Multi-timeframe alignment (1 point) - NEW
        """
        score = 0
        max_score = 10
        reasons = []
        
        # ====================================================================
        # FACTOR 1: Index backdrop alignment (3 points) - HIGHLY PREDICTIVE
        # ====================================================================
        if index_context['above_ema20'] is not None:
            index_strength = index_context['above_ema20']
            
            if pattern_bias == "BULLISH" and index_strength:
                score += 3
                reasons.append(f"✅ Index ({index_context['name']}) above EMA20 (strong support)")
            elif pattern_bias == "BEARISH" and not index_strength:
                score += 3
                reasons.append(f"✅ Index ({index_context['name']}) below EMA20 (strong support)")
            else:
                reasons.append(f"⚠️  Index backdrop unsupportive for {pattern_bias} pattern")
        
        # ====================================================================
        # FACTOR 2: Stock vs EMA20 alignment (2 points)
        # ====================================================================
        if stock_context['above_ema20'] is not None:
            if pattern_bias == "BULLISH" and stock_context['above_ema20']:
                score += 2
                reasons.append(f"✅ Stock above daily EMA20 (${stock_context['ema20']:.2f})")
            elif pattern_bias == "BEARISH" and not stock_context['above_ema20']:
                score += 2
                reasons.append(f"✅ Stock below daily EMA20 (${stock_context['ema20']:.2f})")
        
        # ====================================================================
        # FACTOR 3: Near horizontal S/R level (2 points)
        # ====================================================================
        if pattern_bias == "BULLISH":
            support_levels = sr_levels.get('support', [])
            if support_levels and support_levels[0]['distance_pct'] < 2:
                score += 2
                reasons.append(f"✅ Near support @ ${support_levels[0]['price']:.2f}")
        elif pattern_bias == "BEARISH":
            resistance_levels = sr_levels.get('resistance', [])
            if resistance_levels and resistance_levels[0]['distance_pct'] < 2:
                score += 2
                reasons.append(f"✅ Near resistance @ ${resistance_levels[0]['price']:.2f}")
        
        # ====================================================================
        # FACTOR 4: Breakout imminent (1 point) - REDUCED WEIGHT
        # ====================================================================
        if breakout.get('breakout_imminent') and breakout['direction'] == pattern_bias:
            score += 1
            reasons.append(f"✅ Breakout imminent ({breakout['direction']})")
        
        # ====================================================================
        # FACTOR 5: Chart pattern completion rate (1 point) - NEW
        # ====================================================================
        if pattern.get('pattern_type') == 'CHART':
            completion_rate = pattern.get('historical_completion_rate', 0)
            if completion_rate >= 0.70:  # 70%+ completion rate
                score += 1
                reasons.append(f"✅ High completion rate ({completion_rate*100:.0f}%)")
        
        # ====================================================================
        # FACTOR 6: Multi-timeframe alignment (1 point) - NEW
        # ====================================================================
        # This would require checking if BOTH Daily and 1H have aligned patterns
        # For now, we award this point if it's a Daily chart pattern (more reliable)
        if pattern.get('timeframe') == 'Daily' and pattern.get('pattern_type') == 'CHART':
            score += 1
            reasons.append(f"✅ Daily timeframe pattern (higher reliability)")
        
        # ====================================================================
        # Calculate final percentage and recommendation
        # ====================================================================
        percentage = (score / max_score) * 100
        
        if percentage >= 70:  # 7/10 or better
            recommendation = "STRONG_SIGNAL"
        elif percentage >= 60:  # 6/10
            recommendation = "GOOD_SIGNAL"
        elif percentage >= 50:  # 5/10
            recommendation = "MODERATE_SIGNAL"
        else:
            recommendation = "WEAK_SIGNAL"
        
        return {
            'confluence_score': score,
            'max_score': max_score,
            'percentage': percentage,
            'recommendation': recommendation,
            'reasons': reasons
        }
    

    def _format_enhanced_compliant_alert(self, signal: Dict, status: str = "PENDING") -> str:
        """
        Format MAS-compliant Telegram alert WITH CHART PATTERN SUPPORT
        """
        symbol = signal['symbol']
        pattern = signal['pattern']
        stock_ctx = signal['stock_context']
        index_ctx = signal['index_context']
        
        # Determine pattern type emoji
        if pattern.get('pattern_type') == 'CHART':
            pattern_emoji = "📊"
        else:
            pattern_emoji = "🕯️"
        
        # Build message with compliant language
        msg = f"<b>{symbol} — {pattern.get('timeframe', '1H')} Analysis</b>\n\n"
        
        # Status
        if status == "PENDING":
            msg += "⚠️ <b>PATTERN FORMING (PENDING CLOSE)</b>\n\n"
        elif status == "CONFIRMED":
            msg += "✅ <b>PATTERN CONFIRMED (CLOSED)</b>\n\n"
        elif status == "FAILED":
            msg += "❌ <b>PATTERN FAILED (CLOSED)</b>\n\n"
        
        # Pattern observation with type indicator
        pattern_name = self.telegram.escape(pattern.get('pattern', 'N/A'))
        pattern_type_label = pattern.get('pattern_type', 'CANDLESTICK')
        
        msg += f"<b>Pattern Observed:</b> {pattern_emoji} {pattern_name}\n"
        msg += f"<b>Type:</b> {pattern_type_label}\n"
        msg += f"<b>Timeframe:</b> {pattern.get('timeframe', '1H')}\n"
        msg += f"<b>Bias:</b> {self.telegram.escape(pattern.get('bias', 'N/A'))}\n"
        msg += f"<b>Price:</b> ${stock_ctx['price']:.2f}\n"
        
        # Chart pattern specific info
        if pattern.get('pattern_type') == 'CHART':
            completion_rate = pattern.get('historical_completion_rate', 0)
            if completion_rate > 0:
                msg += f"<b>Historical Completion:</b> {completion_rate*100:.0f}%\n"
            
            if 'measured_move_pct' in pattern:
                msg += f"<b>Measured Move:</b> {pattern['measured_move_pct']:.1f}%\n"
            
            if 'target_price' in pattern:
                msg += f"<b>Projected Completion Level:</b> ${pattern['target_price']:.2f}\n"
            
            # Additional chart pattern details
            if 'breakout_level' in pattern:
                msg += f"<b>Breakout Level:</b> ${pattern['breakout_level']:.2f}\n"
            elif 'resistance_level' in pattern:
                msg += f"<b>Key Level:</b> ${pattern.get('resistance_level', pattern.get('support_level')):.2f}\n"
        
        msg += "\n"
        
        # Stock context (1h close vs daily EMA20)
        msg += "<b>Stock Context (Daily Indicators):</b>\n"
        if stock_ctx['ema20']:
            position = "above" if stock_ctx['above_ema20'] else "below"
            msg += f"• Close vs EMA20: {position} (${stock_ctx['ema20']:.2f})\n"
        
        # Near levels
        if stock_ctx['near_levels']:
            level = stock_ctx['near_levels'][0]
            msg += f"• Near {level['name']}: ${level['value']:.2f} ({level['label']})\n"
        
        msg += "\n"
        
        # Index context
        msg += f"<b>Index Context ({index_ctx['name']}, Daily):</b>\n"
        if index_ctx['close'] and index_ctx['ema20']:
            if index_ctx['above_ema20']:
                msg += f"• Close ${index_ctx['close']:.2f} > EMA20 ${index_ctx['ema20']:.2f}\n"
                msg += f"• Broader backdrop suggests supportive conditions\n"
            else:
                msg += f"• Close ${index_ctx['close']:.2f} < EMA20 ${index_ctx['ema20']:.2f}\n"
                msg += f"• Broader backdrop suggests challenging conditions\n"
        
        msg += "\n"
        msg += "─" * 40 + "\n"
        msg += f"<i>{DISCLAIMER}</i>"
        
        # Sanitize before sending
        return self._sanitize_message(msg)
    
    def scan_confirmation(self):
        """
        CONFIRMATION SCAN - T+1 to T+3 minutes after candle close
        
        CLOSED BAR ONLY:
        - Runs 1-3 minutes after bar close (10:31-33, 11:31-33, etc.)
        - Only fetches CLOSED 1h bars for pending tickers
        - Still uses cached daily indicators from 09:30 ET
        - Emits MAS-safe alerts only for confirmed patterns
        """
        if not self.pending_signals:
            print(f"\n📊 No pending signals to confirm.\n")
            return
        
        et_now = MarketScheduler.get_et_now()
        
        print(f"\n{'='*80}")
        print(f"✅ CONFIRMATION SCAN: {et_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"   Validating {len(self.pending_signals)} pending patterns")
        print(f"   Using closed 1h bars only")
        print(f"{'='*80}\n")
        
        pending_symbols = list(set([s['symbol'] for s in self.pending_signals]))
        
        print(f"Re-scanning {len(pending_symbols)} stocks for confirmation...")
        
        # Fetch ONLY pending tickers' 1h OHLCV
        confirmed_data = self.av_client.batch_fetch_stocks(pending_symbols, interval="60min")
        
        if not confirmed_data:
            print("❌ Failed to fetch confirmation data\n")
            return
        
        confirmed_signals = []
        failed_signals = []
        
        for stock_data in confirmed_data:
            try:
                symbol = stock_data['symbol']
                
                # Read cached daily indicators (still valid)
                stock_daily = self._read_cached_daily_indicators(symbol)
                index_daily = self._read_cached_daily_indicators(self.reference_index)
                
                # Get enhanced data
                enhanced_data = self.data_manager.get_enhanced_stock_data(
                    symbol,
                    stock_data['full_data']
                )
                
                # Re-detect patterns with closed candle
                df_pattern = stock_data['full_data'].copy()
                recent_df = df_pattern.iloc[-10:].copy()
                patterns_found = []
                
                for pattern_func in [
                    self.detector.detect_bullish_engulfing,
                    self.detector.detect_bearish_engulfing,
                    self.detector.detect_hammer,
                    self.detector.detect_shooting_star,
                    self.detector.detect_breakout
                ]:
                    detections = pattern_func(recent_df)
                    if detections and detections[-1]['date'] == df_pattern.iloc[-1]['Date']:
                        patterns_found.append(detections[-1])
                
                if patterns_found:
                    # Pattern CONFIRMED
                    original = next((s for s in self.pending_signals 
                                   if s['symbol'] == symbol), None)
                    
                    if original:
                        original['status'] = 'CONFIRMED'
                        confirmed_signals.append(original)
                else:
                    # Pattern FAILED
                    original_signals = [s for s in self.pending_signals 
                                      if s['symbol'] == symbol]
                    for sig in original_signals:
                        sig['status'] = 'FAILED'
                    failed_signals.extend(original_signals)
                    
            except Exception as e:
                print(f"   ❌ Error confirming {stock_data.get('symbol', 'UNKNOWN')}: {e}")
        
        # Send confirmation alerts
        print(f"\n{'='*80}")
        print(f"📤 SENDING CONFIRMATION ALERTS")
        print(f"{'='*80}\n")
        
        if confirmed_signals:
            print(f"✅ {len(confirmed_signals)} patterns CONFIRMED:")
            for signal in confirmed_signals:
                print(f"   ✅ {signal['symbol']}: {signal['pattern']['pattern']}")
                try:
                    alert_msg = self._format_compliant_alert(signal, status="CONFIRMED")
                    self.telegram.send_message(alert_msg, parse_mode="HTML")
                except Exception as e:
                    print(f"      ❌ Alert failed: {e}")
        
        if failed_signals:
            print(f"\n❌ {len(failed_signals)} patterns FAILED:")
            for signal in failed_signals:
                print(f"   ❌ {signal['symbol']}: {signal['pattern']['pattern']}")
                # Optional: Send simple failure notification
                msg = f"❌ Pattern observation no longer valid: {signal['symbol']} - {signal['pattern']['pattern']}"
                self.telegram.send_message(msg, parse_mode=None, silent=True)
        
        self.pending_signals = []
        
        total = len(confirmed_signals) + len(failed_signals)
        if total > 0:
            conf_rate = len(confirmed_signals) / total * 100
            print(f"\n✅ Confirmation scan complete!")
            print(f"   Confirmation rate: {len(confirmed_signals)}/{total} ({conf_rate:.1f}%)\n")
    
    def run_continuous_enhanced(self, interval_minutes: int = 60):
        """
        Run DUAL-SCAN continuously with market-open pre-cache
        
        Schedule:
        - 09:30:00 ET: Pre-cache daily indicators (ONCE per trading day)
        - 10:25 ET: Predictive scan (T-5)
        - 10:31-33 ET: Confirmation scan (T+1-3, closed bar only)
        - 11:25 ET: Predictive scan
        - 11:31-33 ET: Confirmation scan
        - ... repeat until 15:25/15:31-33 ET
        
        Cache lifecycle:
        - Build once at market open (09:30 ET)
        - Never refresh intra-day
        - Invalidate & rebuild next trading day
        - If late start (after 09:30), pre-cache immediately
        """
        print(f"\n{'='*80}")
        print(f"🚀 STARTING MAS-COMPLIANT CONTINUOUS SCANNER")
        print(f"{'='*80}")
        print(f"Strategy: Market-open cache + T-5 Predictive + T+1-3 Confirmation")
        print(f"Watchlist: {len(self.symbols)} stocks")
        print(f"Reference index: {self.reference_index}")
        print(f"Scan interval: {interval_minutes} minutes")
        print(f"Cache policy: Build at 09:30 ET, use all day, rebuild next day")
        print(f"Compliance: MAS-aware (analysis-only, disclaimer)")
        print(f"{'='*80}\n")
        
        while True:
            try:
                et_now = MarketScheduler.get_et_now()
                
                # Check for new trading day
                if MarketScheduler.is_new_trading_day(self.last_scan_date):
                    print(f"\n🌅 NEW TRADING DAY DETECTED")
                    print(f"   Invalidating yesterday's cache...")
                    self.daily_cache_valid = False
                    self.last_scan_date = et_now
                
                # Check if market is open
                if not MarketScheduler.is_market_open():
                    print(f"⏸️  Market closed. Next check in 10 minutes...")
                    time.sleep(600)
                    continue
                
                # Pre-cache at market open (09:30 ET) or on late start
                market_open_time = et_now.replace(hour=9, minute=30, second=0, microsecond=0)
                is_market_open_window = (et_now >= market_open_time and 
                                        et_now <= market_open_time + timedelta(minutes=5))
                
                if not self.daily_cache_valid:
                    if is_market_open_window:
                        print(f"\n🕘 MARKET OPEN (09:30 ET) - Starting pre-cache...")
                        self.precache_daily_indicators()
                        self.precache_historical_data()
                        self.precache_daily_ohlcv_data()
                    else:
                        # Late start - pre-cache immediately
                        print(f"\n⚠️  Late start detected (after 09:30 ET)")
                        print(f"   Running pre-cache now...")
                        self.precache_daily_indicators()
                        self.precache_historical_data()
                        self.precache_daily_ohlcv_data()
                
                # Calculate next candle close
                next_close = MarketScheduler.get_next_candle_close(interval_minutes)
                
                # === PREDICTIVE SCAN at T-5 ===
                predictive_time = next_close - timedelta(minutes=self.scan_lead_time_minutes)
                wait_seconds = (predictive_time - et_now).total_seconds()
                
                if wait_seconds > 0:
                    print(f"\n⏰ Next predictive scan: {predictive_time.strftime('%H:%M:%S')} ET")
                    print(f"   (T-5 before {next_close.strftime('%H:%M:%S')} close)")
                    print(f"   Waiting {wait_seconds/60:.1f} minutes...\n")
                    time.sleep(wait_seconds)
                
                # Run predictive scan
                print(f"\n🔮 Starting PREDICTIVE scan...")
                self.scan_predictive_enhanced(self.scan_lead_time_minutes)
                
                # === WAIT FOR CANDLE CLOSE ===
                wait_until_close = (next_close - et_now).total_seconds()
                
                if wait_until_close > 0:
                    print(f"\n⏳ Waiting {wait_until_close:.0f}s for candle close...")
                    time.sleep(wait_until_close)
                
                # Wait additional 60-180 seconds for data availability (T+1 to T+3)
                print(f"\n⏳ Waiting 90s for closed bar data availability (T+1-3)...")
                time.sleep(90)
                
                # === CONFIRMATION SCAN at T+1-3 ===
                print(f"\n✅ Bar closed! Starting CONFIRMATION scan...")
                self.scan_confirmation()
                
                print(f"\n{'='*70}")
                print(f"✅ DUAL-SCAN CYCLE COMPLETE")
                print(f"   Next cycle: {(next_close + timedelta(minutes=interval_minutes)).strftime('%H:%M:%S')} ET")
                print(f"{'='*70}\n")
                
            except KeyboardInterrupt:
                print("\n⛔ Scanner stopped by user\n")
                break
            except Exception as e:
                print(f"\n❌ Error in scanner loop: {e}")
                import traceback
                traceback.print_exc()
                print(f"   Retrying in 5 minutes...\n")
                time.sleep(300)


def main():
    """Main execution"""
    
    print("\n" + "="*80)
    print("🚀 MAS-COMPLIANT ENHANCED PREDICTIVE SCANNER")
    print("="*80)
    print("Version: 3.0 (Market-open cache + Index-aware + Compliant)")
    print("="*80)
    print("\nKEY FEATURES:")
    print("✅ Pre-cache at market open (09:30 ET)")
    print("✅ Previous day's completed bars only (no partial current-day data)")
    print("✅ Zero indicator API calls during trading hours")
    print("✅ 210 x 1h candles history (~30 days)")
    print("✅ SPY/QQQ index awareness")
    print("✅ MAS-compliant language (analysis-only + disclaimer)")
    print("✅ T-5 predictive / T+1-3 confirmation (closed bars only)")
    print("="*80 + "\n")
    
    # Configuration
    API_KEY = config.ALPHA_VANTAGE_API_KEY
    TELEGRAM_BOT = config.TELEGRAM_BOT_TOKEN
    TELEGRAM_CHAT = config.TELEGRAM_CHAT_ID
    WATCHLIST_FILE = "data\\test_watchlist.csv"
    
    # Initialize scanner
    scanner = EnhancedPredictiveScanner(API_KEY, TELEGRAM_BOT, TELEGRAM_CHAT)
    
    # Load watchlist
    symbols = scanner.load_watchlist(WATCHLIST_FILE)
    
    if not symbols:
        print("❌ No symbols loaded. Exiting.")
        return
    
    # Run continuous dual-scan
    scanner.run_continuous_enhanced(interval_minutes=60)


if __name__ == "__main__":
    main()