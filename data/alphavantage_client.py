# modules/alphavantage_client_optimized_v2.py - BULK QUOTES + FULL HISTORY

import requests
import pandas as pd
import numpy as np
import pytz
from datetime import datetime, timedelta, time
import time as time_module
from typing import Dict, List, Optional, Tuple
from modules.daily_indicator_cache import DailyIndicatorCache

class OptimizedAlphaVantageClient:
    """
    OPTIMIZED Alpha Vantage client with:
    - BULK QUOTE API (100 stocks per call for live prices)
    - TIME_SERIES_DAILY with outputsize=full (100 days)
    - TIME_SERIES_INTRADAY with outputsize=full (30+ days of 1H data)
    - Daily indicator caching
    
    Key optimization:
    - 1 bulk quote call for 100 stocks vs 100 individual calls
    - Full history for chart pattern detection (30+ days)
    - Daily MAs cached and reused throughout trading day
    """
    
    def __init__(self, api_key: str, rate_limit_per_min: int = 150, use_realtime: bool = True):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        self.rate_limit = rate_limit_per_min
        self.request_interval = 60 / rate_limit_per_min
        self.last_request_time = 0
        self.use_realtime = use_realtime  # Realtime US market data
        
        # Initialize daily indicator cache
        self.daily_cache = DailyIndicatorCache()
        
        print(f"🚀 Optimized Alpha Vantage Client v2.0 initialized")
        print(f"   ✅ Bulk quote API enabled (100 stocks/call)")
        print(f"   ✅ Full history mode (30+ days)")
        if self.use_realtime:
            print(f"   ✅ Realtime data ENABLED (US stocks)")
        cache_stats = self.daily_cache.get_cache_stats()
        if cache_stats['is_valid']:
            print(f"   ✅ Daily MA cache active: {cache_stats['cached_symbols']} symbols")
        else:
            print(f"   ⚠️  Daily MA cache needs refresh")
    
    def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limit"""
        current_time = time_module.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_interval:
            sleep_time = self.request_interval - time_since_last
            time_module.sleep(sleep_time)
        
        self.last_request_time = time_module.time()
    
    # ========================================================================
    # BULK QUOTE API - Get live prices for up to 100 stocks in 1 call
    # ========================================================================
    
    def get_bulk_quotes(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Get live quotes for multiple symbols using BATCH_STOCK_QUOTES
        
        Args:
            symbols: List of up to 100 stock symbols
        
        Returns:
            Dict mapping symbol to quote data:
            {
                'AAPL': {
                    'price': 187.50,
                    'volume': 45621000,
                    'timestamp': '2024-10-24 15:59:00'
                },
                ...
            }
        
        NOTE: Alpha Vantage free tier supports batches of 5.
        Premium tier supports batches of 100.
        This implementation chunks requests appropriately.
        """
        if not symbols:
            return {}
        
        all_quotes = {}
        
        # Alpha Vantage supports max 100 symbols per batch (premium)
        # Free tier: max 5 symbols per batch
        # Detect tier based on rate limit
        batch_size = 100 if self.rate_limit >= 150 else 5
        
        # Split into batches
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            batch_quotes = self._fetch_batch_quotes(batch)
            all_quotes.update(batch_quotes)
        
        return all_quotes
    
    def _fetch_batch_quotes(self, symbols: List[str]) -> Dict[str, Dict]:
        """Fetch single batch of quotes"""
        self._wait_for_rate_limit()
        
        try:
            # Join symbols with commas
            symbols_param = ','.join(symbols)
            
            params = {
                "function": "REALTIME_BULK_QUOTES",
                "symbol": symbols_param,
                "apikey": self.api_key
            }
            
            # Add realtime entitlement if enabled
            if self.use_realtime:
                params["entitlement"] = "realtime"
            
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "Error Message" in data:
                print(f"   ⚠️  Batch quote API error: {data['Error Message']}")
                # Fallback to individual GLOBAL_QUOTE calls
                return self._fallback_individual_quotes(symbols)
            
            if "Note" in data:
                print(f"   ⚠️  Rate limit message: {data['Note']}")
                time_module.sleep(60)
                return self._fetch_batch_quotes(symbols)
            
            # Parse batch quotes
            # CRITICAL FIX: REALTIME_BULK_QUOTES returns data under "data" key
            # with simple field names (not numbered like "1. symbol")
            quotes = {}
            stock_quotes = data.get("data", [])
            
            if not stock_quotes:
                print(f"   ⚠️  No data in response. Response keys: {list(data.keys())}")
                print(f"   ⚠️  Falling back to individual quotes...")
                return self._fallback_individual_quotes(symbols)
            
            print(f"   ✅ Received {len(stock_quotes)} quotes from bulk API")
            
            for quote in stock_quotes:
                symbol = quote.get("symbol")
                if symbol:
                    quotes[symbol] = {
                        'price': float(quote.get("close", 0)),
                        'volume': int(quote.get("volume", 0)),
                        'timestamp': quote.get("last_refreshed", ""),
                        'source': 'BULK_QUOTE'
                    }
            
            return quotes
        except Exception as e:
            print(f"   ❌ Batch quote error: {e}")
            # Fallback to individual calls
            return self._fallback_individual_quotes(symbols)
    
    def _fallback_individual_quotes(self, symbols: List[str]) -> Dict[str, Dict]:
        """Fallback to individual GLOBAL_QUOTE calls if batch fails"""
        quotes = {}
        
        for symbol in symbols:
            self._wait_for_rate_limit()
            
            try:
                params = {
                    "function": "GLOBAL_QUOTE",
                    "symbol": symbol,
                    "apikey": self.api_key
                }
                
                # Add realtime entitlement if enabled
                if self.use_realtime:
                    params["entitlement"] = "realtime"
                
                response = requests.get(self.base_url, params=params, timeout=10)
                data = response.json()
                
                quote = data.get("Global Quote", {})
                if quote:
                    quotes[symbol] = {
                        'price': float(quote.get("05. price", 0)),
                        'volume': int(quote.get("06. volume", 0)),
                        'timestamp': quote.get("07. latest trading day", ""),
                        'source': 'GLOBAL_QUOTE'
                    }
            
            except Exception as e:
                print(f"   ⚠️  Error fetching {symbol}: {e}")
                continue
        
        return quotes
    
    # ========================================================================
    # TIME_SERIES_INTRADAY - Full history (30+ days of 1H data)
    # ========================================================================
    
    def get_intraday_data(self, symbol: str, interval: str = "60min", 
                         outputsize: str = "full") -> pd.DataFrame:
        """
        Fetch intraday OHLCV data with FULL history
        
        Args:
            symbol: Stock symbol
            interval: "1min", "5min", "15min", "30min", "60min"
            outputsize: "compact" (100 bars) or "full" (30 days)
        
        Returns:
            DataFrame with Date, Open, High, Low, Close, Volume
        
        CRITICAL: outputsize="full" ensures 30+ days of data for chart patterns
        """
        self._wait_for_rate_limit()
        
        try:
            params = {
                "function": "TIME_SERIES_INTRADAY",
                "symbol": symbol,
                "interval": interval,
                "outputsize": outputsize,  # ← FULL for 30+ days
                "apikey": self.api_key,
                "extended_hours": "false",
                "adjusted": "false",
                "datatype": "json"
            }
            
            # Add realtime entitlement if enabled
            if self.use_realtime:
                params["entitlement"] = "realtime"
            
            response = requests.get(self.base_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if "Error Message" in data:
                print(f"   ⚠️  API Error for {symbol}: {data['Error Message']}")
                return pd.DataFrame()
            
            if "Note" in data:
                print(f"   ⚠️  Rate limit message: {data['Note']}")
                time_module.sleep(60)
                return self.get_intraday_data(symbol, interval, outputsize)
            
            time_series_key = f"Time Series ({interval})"
            if time_series_key not in data:
                print(f"   ⚠️  No intraday data for {symbol}")
                return pd.DataFrame()
            
            df = pd.DataFrame.from_dict(data[time_series_key], orient='index')
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            df.index = pd.to_datetime(df.index)
            df.index.name = 'Date'
            df = df.astype(float)
            df = df.sort_index()
            df = df.reset_index()
            
            # Validate we got enough data for chart patterns (target: 200+ bars)
            if len(df) < 200:
                print(f"   ⚠️  {symbol}: Only {len(df)} bars (need 200+ for patterns)")
            
            return df
            
        except Exception as e:
            print(f"   ❌ Error fetching intraday {symbol}: {e}")
            return pd.DataFrame()
    
    # ========================================================================
    # TIME_SERIES_DAILY - Full history (100+ days)
    # ========================================================================
    
    def get_daily_data(self, symbol: str, outputsize: str = "full") -> pd.DataFrame:
        """
        Fetch daily OHLCV data with FULL history
        
        Args:
            symbol: Stock symbol
            outputsize: "compact" (100 days) or "full" (20+ years)
        
        Returns:
            DataFrame with Date, Open, High, Low, Close, Volume
        
        CRITICAL: outputsize="full" ensures enough data for daily chart patterns
        """
        self._wait_for_rate_limit()
        
        try:
            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "outputsize": outputsize,  # ← FULL for 20+ years
                "apikey": self.api_key,
                "datatype": "json"
            }
            
            # Add realtime entitlement if enabled
            if self.use_realtime:
                params["entitlement"] = "realtime"
            
            response = requests.get(self.base_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if "Error Message" in data:
                print(f"   ⚠️  API Error for {symbol}: {data['Error Message']}")
                return pd.DataFrame()
            
            if "Note" in data:
                print(f"   ⚠️  Rate limit message: {data['Note']}")
                time_module.sleep(60)
                return self.get_daily_data(symbol, outputsize)
            
            if "Time Series (Daily)" not in data:
                print(f"   ⚠️  No daily data for {symbol}")
                return pd.DataFrame()
            
            df = pd.DataFrame.from_dict(data["Time Series (Daily)"], orient='index')
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            df.index = pd.to_datetime(df.index)
            df.index.name = 'Date'
            df = df.astype(float)
            df = df.sort_index()
            df = df.reset_index()
            
            # Validate we got enough data
            if len(df) < 100:
                print(f"   ⚠️  {symbol}: Only {len(df)} daily bars (need 100+ for patterns)")
            
            return df
            
        except Exception as e:
            print(f"   ❌ Error fetching daily {symbol}: {e}")
            return pd.DataFrame()
    
    # ========================================================================
    # Daily Indicators (cached) - Using TIME_SERIES_DAILY
    # ========================================================================
    
    def get_technical_indicators_daily(self, symbol: str) -> Dict:
        """
        Fetch DAILY moving averages with caching
        
        Uses indicator API endpoints:
        - EMA (Exponential Moving Average)
        - SMA (Simple Moving Average)
        
        OPTIMIZATION: Only fetches if not in cache or cache expired
        """
        # Check cache first
        cached = self.daily_cache.get_indicators(symbol)
        if cached:
            print(f"      📦 Using cached DAILY MAs for {symbol}")
            return cached
        
        # Not in cache, fetch from API
        print(f"      🔄 Fetching DAILY MAs for {symbol}...")
        
        indicators = {}
        interval = "daily"
        
        # Get EMA20
        ema20 = self._get_single_indicator(symbol, "EMA", 20, interval)
        if ema20 is not None:
            indicators['EMA_20'] = ema20
        
        # Get SMA50
        sma50 = self._get_single_indicator(symbol, "SMA", 50, interval)
        if sma50 is not None:
            indicators['SMA_50'] = sma50
        
        # Get SMA100
        sma100 = self._get_single_indicator(symbol, "SMA", 100, interval)
        if sma100 is not None:
            indicators['SMA_100'] = sma100
        
        # Get SMA200
        sma200 = self._get_single_indicator(symbol, "SMA", 200, interval)
        if sma200 is not None:
            indicators['SMA_200'] = sma200
        
        # Cache the results
        self.daily_cache.set_indicators(symbol, indicators)
        
        return indicators
    
    def _get_single_indicator(self, symbol: str, indicator: str, 
                              period: int, interval: str) -> Optional[float]:
        """Fetch single technical indicator"""
        self._wait_for_rate_limit()
        
        try:
            params = {
                "function": indicator,
                "symbol": symbol,
                "interval": interval,
                "time_period": period,
                "series_type": "close",
                "apikey": self.api_key
            }
            
            # Add realtime entitlement if enabled
            if self.use_realtime:
                params["entitlement"] = "realtime"
            
            response = requests.get(self.base_url, params=params, timeout=10)
            data = response.json()
            
            if "Technical Analysis: " + indicator in data:
                ta_data = data["Technical Analysis: " + indicator]
                latest_date = sorted(ta_data.keys(), reverse=True)[0]
                return float(ta_data[latest_date][indicator])
            
            return None
            
        except Exception as e:
            print(f"   ⚠️  Error getting {indicator}{period} for {symbol}: {e}")
            return None
    
    # ========================================================================
    # Unified Stock Data Fetch - With Bulk Quotes
    # ========================================================================
    
    def get_stock_data_with_indicators(self, symbol: str, interval: str = "60min") -> Dict:
        """
        OPTIMIZED: Fetch stock data with cached daily indicators
        
        Returns unified data structure with:
        - Latest price (from bulk quote or intraday)
        - Full intraday history (30+ days)
        - Cached daily indicators
        """
        print(f"   📊 Fetching {symbol}...")
        
        # 1. Get intraday OHLCV (always fresh, with FULL history)
        df = self.get_intraday_data(symbol, interval, outputsize="full")
        if df.empty:
            return None
        
        # 2. Get DAILY indicators (cached if available)
        indicators = self.get_technical_indicators_daily(symbol)
        
        # Get most recent candle
        latest = df.iloc[-1]
        
        result = {
            'symbol': symbol,
            'timestamp': latest['Date'],
            'open': latest['Open'],
            'high': latest['High'],
            'low': latest['Low'],
            'close': latest['Close'],
            'volume': latest['Volume'],
            'ema_20': indicators.get('EMA_20'),
            'sma_50': indicators.get('SMA_50'),
            'sma_100': indicators.get('SMA_100'),
            'sma_200': indicators.get('SMA_200'),
            'previous_candle': df.iloc[-2] if len(df) >= 2 else None,
            'full_data': df,
            'candle_count': len(df)
        }
        
        return result
    
    def batch_fetch_stocks(self, symbols: List[str], interval: str = "60min",
                          use_bulk_quotes: bool = True) -> List[Dict]:
        """
        OPTIMIZED batch fetching with:
        - Bulk quotes for live prices (1 call per 100 stocks)
        - Full intraday history (outputsize=full)
        - Daily MA caching
        
        Args:
            symbols: List of stock symbols
            interval: Intraday interval ("60min" recommended)
            use_bulk_quotes: Use bulk quote API (faster)
        
        Returns:
            List of stock data dictionaries
        """
        # Check cache status
        symbols_needing_daily_mas = self.daily_cache.needs_refresh(symbols)
        
        if symbols_needing_daily_mas:
            print(f"\n🔄 Need to fetch DAILY MAs for {len(symbols_needing_daily_mas)} symbols")
            total_calls = len(symbols) + (len(symbols_needing_daily_mas) * 4)
        else:
            print(f"\n✅ All DAILY MAs cached!")
            total_calls = len(symbols)
        
        # Get bulk quotes first (1 call per 100 stocks)
        bulk_quotes = {}
        if use_bulk_quotes:
            print(f"\n📊 Fetching bulk quotes for {len(symbols)} stocks...")
            bulk_quotes = self.get_bulk_quotes(symbols)
            print(f"   ✅ Retrieved {len(bulk_quotes)} quotes")
        
        print(f"\n🚀 Starting batch fetch for {len(symbols)} stocks...")
        print(f"   Rate limit: {self.rate_limit} requests/min")
        print(f"   Expected API calls: ~{total_calls}")
        print(f"   Expected time: ~{(total_calls / self.rate_limit):.1f} minutes\n")
        
        results = []
        start_time = time_module.time()
        
        for i, symbol in enumerate(symbols, 1):
            print(f"[{i}/{len(symbols)}] Processing {symbol}...")
            
            stock_data = self.get_stock_data_with_indicators(symbol, interval)
            
            if stock_data:
                # Optionally inject bulk quote price if available and more recent
                if symbol in bulk_quotes:
                    bulk_price = bulk_quotes[symbol]['price']
                    if bulk_price > 0:
                        stock_data['bulk_quote_price'] = bulk_price
                        stock_data['bulk_quote_volume'] = bulk_quotes[symbol]['volume']
                
                results.append(stock_data)
                candles = stock_data.get('candle_count', 0)
                print(f"   ✅ {symbol} complete ({candles} candles)")
            else:
                print(f"   ❌ {symbol} failed")
            
            # Progress update every 10 stocks
            if i % 10 == 0:
                elapsed = time_module.time() - start_time
                stocks_per_min = (i / elapsed) * 60
                remaining = len(symbols) - i
                eta = (remaining / stocks_per_min) if stocks_per_min > 0 else 0
                print(f"\n   📈 Progress: {i}/{len(symbols)} ({i/len(symbols)*100:.1f}%)")
                print(f"   ⏱️  Speed: {stocks_per_min:.1f} stocks/min")
                print(f"   🕐 ETA: {eta:.1f} minutes\n")
        
        # Save cache after batch
        self.daily_cache.bulk_update({})
        
        total_time = time_module.time() - start_time
        print(f"\n✅ Batch fetch complete!")
        print(f"   Total time: {total_time/60:.2f} minutes")
        print(f"   Success rate: {len(results)}/{len(symbols)} ({len(results)/len(symbols)*100:.1f}%)")
        
        if use_bulk_quotes:
            saved_calls = len(symbols) - len(symbols) // 100
            print(f"   🎯 Bulk quotes saved ~{saved_calls} API calls")
        
        print()
        
        return results
    
    # ========================================================================
    # Daily Data Fetch (for pre-caching at market open)
    # ========================================================================
    
    def fetch_daily_indicators(self, symbol: str, use_previous_complete_bar: bool = True,
                              offset: int = 0) -> Optional[Dict]:
        """
        Fetch daily indicators for market-open pre-cache
        Uses TIME_SERIES_DAILY to get close price
        
        Args:
            symbol: Stock symbol
            use_previous_complete_bar: If True, uses previous day's completed bar
            offset: Additional offset (0=latest, 1=previous, etc.)
        
        Returns:
            Dict with ema20, sma50, sma100, sma200, close, date
        """
        indicators = self.get_technical_indicators_daily(symbol)
        
        # Get daily close price using TIME_SERIES_DAILY
        self._wait_for_rate_limit()
        try:
            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "outputsize": "compact",  # Just need recent data
                "apikey": self.api_key
            }
            
            # Add realtime entitlement if enabled
            if self.use_realtime:
                params["entitlement"] = "realtime"
            
            response = requests.get(self.base_url, params=params, timeout=10)
            data = response.json()
            
            if "Time Series (Daily)" in data:
                daily_data = data["Time Series (Daily)"]
                dates = sorted(daily_data.keys(), reverse=True)
                
                # Get appropriate bar (previous complete bar if requested)
                if use_previous_complete_bar or offset > 0:
                    bar_index = offset if offset > 0 else 1  # Skip today's partial bar
                else:
                    bar_index = 0  # Use latest (might be partial)
                
                if bar_index < len(dates):
                    bar_date = dates[bar_index]
                    bar = daily_data[bar_date]
                    
                    return {
                        'ema20': indicators.get('EMA_20'),
                        'sma50': indicators.get('SMA_50'),
                        'sma100': indicators.get('SMA_100'),
                        'sma200': indicators.get('SMA_200'),
                        'close': float(bar['4. close']),
                        'date': bar_date
                    }
        except Exception as e:
            print(f"   ⚠️  Error fetching daily data for {symbol}: {e}")
        
        return None
    
    def fetch_intraday(self, symbol: str, interval: str = "60min") -> Dict:
        """
        Fetch only intraday data (no indicators)
        Used for index data (SPY/QQQ)
        """
        df = self.get_intraday_data(symbol, interval, outputsize="full")
        if df.empty:
            return None
        
        latest = df.iloc[-1]
        return {
            'symbol': symbol,
            'timestamp': latest['Date'],
            'close': latest['Close'],
            'open': latest['Open'],
            'high': latest['High'],
            'low': latest['Low'],
            'volume': latest['Volume'],
            'full_data': df,
            'candle_count': len(df)
        }
    
    def invalidate_daily_cache(self):
        """Manually invalidate daily cache (call at market open)"""
        self.daily_cache.invalidate_cache()


# ============================================================================
# MARKET SCHEDULER (unchanged)
# ============================================================================

class MarketScheduler:
    """
    TIMEZONE-AWARE Market Hours Scheduler
    Handles US market hours in Eastern Time (ET)
    """
    
    # US Eastern Time timezone
    ET_TZ = pytz.timezone('America/New_York')
    
    # Market hours (ET)
    MARKET_OPEN = time(9, 30)   # 09:30 ET
    MARKET_CLOSE = time(16, 0)  # 16:00 ET
    
    # US Market Holidays 2024-2025
    HOLIDAYS = {
        '2024-01-01',  # New Year's Day
        '2024-01-15',  # MLK Day
        '2024-02-19',  # Presidents' Day
        '2024-03-29',  # Good Friday
        '2024-05-27',  # Memorial Day
        '2024-06-19',  # Juneteenth
        '2024-07-04',  # Independence Day
        '2024-09-02',  # Labor Day
        '2024-11-28',  # Thanksgiving
        '2024-12-25',  # Christmas
        '2025-01-01',  # New Year's Day 2025
        '2025-01-20',  # MLK Day 2025
        '2025-02-17',  # Presidents' Day 2025
        '2025-04-18',  # Good Friday 2025
        '2025-05-26',  # Memorial Day 2025
        '2025-06-19',  # Juneteenth 2025
        '2025-07-04',  # Independence Day 2025
        '2025-09-01',  # Labor Day 2025
        '2025-11-27',  # Thanksgiving 2025
        '2025-12-25',  # Christmas 2025
    }
    
    @classmethod
    def get_et_now(cls) -> datetime:
        """Get current time in Eastern Time"""
        return datetime.now(cls.ET_TZ)
    
    @classmethod
    def is_market_open(cls) -> bool:
        """Check if US market is currently open"""
        et_now = cls.get_et_now()
        
        # Check if weekend
        if et_now.weekday() >= 5:  # Saturday=5, Sunday=6
            return False
        
        # Check if holiday
        date_str = et_now.strftime('%Y-%m-%d')
        if date_str in cls.HOLIDAYS:
            return False
        
        # Check if within market hours
        current_time = et_now.time()
        return cls.MARKET_OPEN <= current_time <= cls.MARKET_CLOSE
    
    @classmethod
    def is_new_trading_day(cls, last_scan_date: Optional[datetime]) -> bool:
        """Check if we're on a new trading day (in ET)"""
        if last_scan_date is None:
            return True
        
        et_now = cls.get_et_now()
        
        # Convert last_scan_date to ET if needed
        if last_scan_date.tzinfo is None:
            last_scan_et = cls.ET_TZ.localize(last_scan_date)
        else:
            last_scan_et = last_scan_date.astimezone(cls.ET_TZ)
        
        # Check if different date in ET
        return et_now.date() != last_scan_et.date()
    
    @classmethod
    def get_next_candle_close(cls, interval_minutes: int = 60) -> datetime:
        """Calculate when the next candle closes (in ET)"""
        et_now = cls.get_et_now()
        
        # Calculate next interval boundary
        if interval_minutes == 60:
            # For 1h candles, close at :30 of each hour
            next_close = et_now.replace(minute=30, second=0, microsecond=0)
            if et_now.minute >= 30:
                next_close += timedelta(hours=1)
        else:
            # For other intervals, round up to next boundary
            minutes = (et_now.minute // interval_minutes + 1) * interval_minutes
            
            if minutes >= 60:
                next_close = et_now.replace(
                    hour=et_now.hour + 1, 
                    minute=0, 
                    second=0, 
                    microsecond=0
                )
            else:
                next_close = et_now.replace(
                    minute=minutes, 
                    second=0, 
                    microsecond=0
                )
        
        return next_close
    
    @classmethod
    def get_market_open_time(cls) -> datetime:
        """Get today's market open time (09:30 ET)"""
        et_now = cls.get_et_now()
        return et_now.replace(hour=9, minute=30, second=0, microsecond=0)
    
    @classmethod
    def time_until_market_open(cls) -> float:
        """Get seconds until next market open"""
        if cls.is_market_open():
            return 0
        
        et_now = cls.get_et_now()
        next_open = cls.get_market_open_time()
        
        # If past today's open, use tomorrow
        if et_now >= next_open:
            next_open += timedelta(days=1)
        
        # Skip weekends
        while next_open.weekday() >= 5:
            next_open += timedelta(days=1)
        
        # Skip holidays
        while next_open.strftime('%Y-%m-%d') in cls.HOLIDAYS:
            next_open += timedelta(days=1)
        
        return (next_open - et_now).total_seconds()
    
    @classmethod
    def wait_for_candle_close(cls, interval_minutes: int = 60):
        """Wait until next candle closes"""
        next_close = cls.get_next_candle_close(interval_minutes)
        et_now = cls.get_et_now()
        
        wait_seconds = (next_close - et_now).total_seconds()
        
        if wait_seconds > 0:
            print(f"\n⏰ Next candle closes at {next_close.strftime('%H:%M:%S')} ET")
            print(f"   Waiting {wait_seconds/60:.1f} minutes...")
            time_module.sleep(wait_seconds)
            
            print(f"   ⏳ Adding 1-minute buffer...")
            time_module.sleep(60)
            print(f"   ✅ Candle closed! Starting scan...\n")


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

"""
EXAMPLE 1: Bulk Quotes (100 stocks in 1 call)
-----------------------------------------------
from modules.alphavantage_client_optimized_v2 import OptimizedAlphaVantageClient

av_client = OptimizedAlphaVantageClient(api_key, rate_limit_per_min=150)

symbols = ['AAPL', 'MSFT', 'GOOGL', ..., '100 symbols']
quotes = av_client.get_bulk_quotes(symbols)

# Result: 1 API call vs 100 individual calls


EXAMPLE 2: Full History for Chart Patterns
-------------------------------------------
# Get 30+ days of 1H data (200+ candles)
intraday_df = av_client.get_intraday_data('AAPL', interval='60min', outputsize='full')

# Get 100+ days of daily data
daily_df = av_client.get_daily_data('AAPL', outputsize='full')


EXAMPLE 3: Batch Fetch with All Optimizations
----------------------------------------------
symbols = ['AAPL', 'MSFT', 'GOOGL', ..., '200 symbols']

# Uses:
# - Bulk quotes (1-2 calls for all prices)
# - Full intraday history (30+ days per stock)
# - Cached daily indicators
stocks = av_client.batch_fetch_stocks(symbols, interval='60min', use_bulk_quotes=True)


EXAMPLE 4: Market Hours & Pre-Cache
------------------------------------
from modules.alphavantage_client_optimized_v2 import MarketScheduler

# Check market status
if MarketScheduler.is_market_open():
    print("✅ Market is OPEN")
else:
    seconds = MarketScheduler.time_until_market_open()
    print(f"❌ Market opens in {seconds/3600:.1f} hours")

# At market open, pre-cache daily indicators
if MarketScheduler.is_new_trading_day(last_scan_date):
    av_client.invalidate_daily_cache()
    # Then fetch all symbols...
"""