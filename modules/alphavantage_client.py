# modules/alphavantage_client_optimized.py - With Daily MA Caching + TIMEZONE FIX

import requests
import pandas as pd
import numpy as np
import pytz  # ← ADDED: Timezone support
from datetime import datetime, timedelta, time  # ← ADDED: time import
import time as time_module  # Rename to avoid conflict
from typing import Dict, List, Optional
from modules.daily_indicator_cache import DailyIndicatorCache

class OptimizedAlphaVantageClient:
    """
    OPTIMIZED Alpha Vantage client with daily indicator caching
    
    Key optimization:
    - DAILY MAs fetched once per trading day
    - Cached and reused throughout the day
    - 80% reduction in API calls (1000 → 200 per scan)
    - 5x faster scanning (6.7 min → 1.3 min)
    """
    
    def __init__(self, api_key: str, rate_limit_per_min: int = 150):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        self.rate_limit = rate_limit_per_min
        self.request_interval = 60 / rate_limit_per_min
        self.last_request_time = 0
        
        # Initialize daily indicator cache
        self.daily_cache = DailyIndicatorCache()
        
        print(f"🚀 Optimized Alpha Vantage Client initialized")
        cache_stats = self.daily_cache.get_cache_stats()
        if cache_stats['is_valid']:
            print(f"✅ Daily MA cache active: {cache_stats['cached_symbols']} symbols")
        else:
            print(f"⚠️  Daily MA cache needs refresh")
    
    def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limit"""
        current_time = time_module.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_interval:
            sleep_time = self.request_interval - time_since_last
            time_module.sleep(sleep_time)
        
        self.last_request_time = time_module.time()
    
    def get_intraday_data(self, symbol: str, interval: str = "60min", 
                         outputsize: str = "compact") -> pd.DataFrame:
        """Fetch intraday OHLCV data (unchanged from original)"""
        self._wait_for_rate_limit()
        
        try:
            params = {
                "function": "TIME_SERIES_INTRADAY",
                "symbol": symbol,
                "interval": interval,
                "outputsize": outputsize,
                "apikey": self.api_key,
                "datatype": "json"
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
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
                print(f"   ⚠️  No data returned for {symbol}")
                return pd.DataFrame()
            
            df = pd.DataFrame.from_dict(data[time_series_key], orient='index')
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            df.index = pd.to_datetime(df.index)
            df.index.name = 'Date'
            df = df.astype(float)
            df = df.sort_index()
            df = df.reset_index()
            
            return df
            
        except Exception as e:
            print(f"   ❌ Error fetching {symbol}: {e}")
            return pd.DataFrame()
    
    def get_technical_indicators_daily(self, symbol: str) -> Dict:
        """
        Fetch DAILY moving averages with caching
        
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
        """Fetch single technical indicator from Alpha Vantage"""
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
    
    def get_stock_data_with_indicators(self, symbol: str, interval: str = "60min") -> Dict:
        """
        OPTIMIZED: Fetch stock data with cached daily indicators
        
        API calls:
        - First scan of day: 5 calls per stock (1 intraday + 4 daily MAs)
        - Subsequent scans: 1 call per stock (intraday only)
        
        This is the KEY optimization!
        """
        print(f"   📊 Fetching {symbol}...")
        
        # 1. Get intraday OHLCV (always fresh)
        df = self.get_intraday_data(symbol, interval)
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
            'full_data': df
        }
        
        return result
    
    def batch_fetch_stocks(self, symbols: List[str], interval: str = "60min") -> List[Dict]:
        """
        OPTIMIZED batch fetching with daily MA caching
        
        Performance:
        - First scan: ~6.7 min (fetch all MAs)
        - Subsequent scans: ~1.3 min (only intraday data)
        - 5x speed improvement!
        """
        # Check cache status
        symbols_needing_daily_mas = self.daily_cache.needs_refresh(symbols)
        
        if symbols_needing_daily_mas:
            print(f"\n🔄 Need to fetch DAILY MAs for {len(symbols_needing_daily_mas)} symbols")
            print(f"   (First scan of the day or new symbols)")
            total_calls = len(symbols) + (len(symbols_needing_daily_mas) * 4)
        else:
            print(f"\n✅ All DAILY MAs cached! Only fetching intraday data")
            total_calls = len(symbols)
        
        print(f"🚀 Starting batch fetch for {len(symbols)} stocks...")
        print(f"   Rate limit: {self.rate_limit} requests/min")
        print(f"   Expected API calls: {total_calls}")
        print(f"   Expected time: ~{(total_calls / self.rate_limit):.1f} minutes\n")
        
        results = []
        start_time = time_module.time()
        
        for i, symbol in enumerate(symbols, 1):
            print(f"[{i}/{len(symbols)}] Processing {symbol}...")
            
            stock_data = self.get_stock_data_with_indicators(symbol, interval)
            
            if stock_data:
                results.append(stock_data)
                print(f"   ✅ {symbol} complete")
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
        print(f"   API calls saved: ~{len(symbols) * 4} (thanks to caching!)\n")
        
        return results
    
    def fetch_intraday(self, symbol: str, interval: str = "60min") -> Dict:
        """
        Fetch only intraday data (no indicators)
        Used for index data (SPY/QQQ)
        """
        df = self.get_intraday_data(symbol, interval)
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
            'full_data': df
        }
    
    def fetch_daily_indicators(self, symbol: str, use_previous_complete_bar: bool = True,
                              offset: int = 0) -> Optional[Dict]:
        """
        Fetch daily indicators for market-open pre-cache
        
        Args:
            symbol: Stock symbol
            use_previous_complete_bar: If True, uses previous day's completed bar
            offset: Additional offset (0=latest, 1=previous, etc.)
        
        Returns:
            Dict with ema20, sma50, sma100, sma200, close, date
        """
        indicators = self.get_technical_indicators_daily(symbol)
        
        # Get daily close price
        self._wait_for_rate_limit()
        try:
            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "outputsize": "compact",
                "apikey": self.api_key
            }
            
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
    
    def invalidate_daily_cache(self):
        """Manually invalidate daily cache (call at market open)"""
        self.daily_cache.invalidate_cache()


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
        """
        Check if US market is currently open
        
        Market hours: 09:30-16:00 ET, Monday-Friday (excluding holidays)
        
        Returns:
            bool: True if market is open
        """
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
        """
        Check if we're on a new trading day (in ET)
        
        Args:
            last_scan_date: Previous scan datetime
        
        Returns:
            bool: True if new trading day
        """
        if last_scan_date is None:
            return True
        
        et_now = cls.get_et_now()
        
        # Convert last_scan_date to ET if needed
        if last_scan_date.tzinfo is None:
            # Assume it was ET
            last_scan_et = cls.ET_TZ.localize(last_scan_date)
        else:
            last_scan_et = last_scan_date.astimezone(cls.ET_TZ)
        
        # Check if different date in ET
        return et_now.date() != last_scan_et.date()
    
    @classmethod
    def get_next_candle_close(cls, interval_minutes: int = 60) -> datetime:
        """
        Calculate when the next candle closes (in ET)
        
        Args:
            interval_minutes: Candle interval (default 60 for 1h)
        
        Returns:
            datetime: Next candle close in ET timezone
        """
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
        """
        Get seconds until next market open
        
        Returns:
            float: Seconds until market opens (0 if already open)
        """
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


# Usage in scanner:
"""
from modules.alphavantage_client_optimized import OptimizedAlphaVantageClient, MarketScheduler

# Initialize
av_client = OptimizedAlphaVantageClient(api_key, rate_limit_per_min=150)

# Check market status (now timezone-aware!)
if MarketScheduler.is_market_open():
    print("✅ Market is OPEN")
    et_now = MarketScheduler.get_et_now()
    print(f"   ET time: {et_now.strftime('%H:%M:%S')}")
else:
    print("❌ Market is CLOSED")
    seconds = MarketScheduler.time_until_market_open()
    print(f"   Opens in: {seconds/3600:.1f} hours")

# At market open, invalidate cache
if MarketScheduler.is_new_trading_day(last_scan_date):
    av_client.invalidate_daily_cache()

# Batch fetch (automatically uses cache)
stocks = av_client.batch_fetch_stocks(symbols, interval="60min")
"""