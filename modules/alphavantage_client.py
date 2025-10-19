# modules/alphavantage_client.py - Optimized Real-time Data Fetcher

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
from typing import Dict, List, Optional
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import json

class AlphaVantageClient:
    """
    Optimized Alpha Vantage client for high-throughput scanning
    Handles 150 requests/min rate limit efficiently
    """
    
    def __init__(self, api_key: str, rate_limit_per_min: int = 150):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        self.rate_limit = rate_limit_per_min
        self.request_interval = 60 / rate_limit_per_min  # Seconds between requests
        self.last_request_time = 0
        self.request_queue = []
        
    def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limit"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_interval:
            sleep_time = self.request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def get_intraday_data(self, symbol: str, interval: str = "60min", 
                         outputsize: str = "compact") -> pd.DataFrame:
        """
        Fetch intraday OHLCV data
        For 60min interval, compact returns 100 most recent bars
        """
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
            
            # Check for errors
            if "Error Message" in data:
                print(f"   ⚠️  API Error for {symbol}: {data['Error Message']}")
                return pd.DataFrame()
            
            if "Note" in data:
                print(f"   ⚠️  Rate limit message: {data['Note']}")
                time.sleep(60)  # Wait a minute if we hit rate limit
                return self.get_intraday_data(symbol, interval, outputsize)
            
            time_series_key = f"Time Series ({interval})"
            if time_series_key not in data:
                print(f"   ⚠️  No data returned for {symbol}")
                return pd.DataFrame()
            
            # Parse into DataFrame
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
        Fetch DAILY moving averages (NOT hourly)
        This is the correct timeframe for trend analysis
        
        CRITICAL: Uses daily interval for proper MA values
        - EMA20 (daily) = 20 trading days
        - SMA50 (daily) = 50 trading days
        - SMA100 (daily) = 100 trading days
        - SMA200 (daily) = 200 trading days
        
        Returns: Dictionary with EMA20, SMA50, SMA100, SMA200 from DAILY chart
        """
        indicators = {}
        interval = "daily"  # FIXED: Always use daily for moving averages
        
        print(f"      Fetching DAILY MAs for {symbol}...")
        
        # Get EMA20 (daily)
        ema20 = self._get_single_indicator(symbol, "EMA", 20, interval)
        if ema20 is not None:
            indicators['EMA_20'] = ema20
        
        # Get SMA50 (daily)
        sma50 = self._get_single_indicator(symbol, "SMA", 50, interval)
        if sma50 is not None:
            indicators['SMA_50'] = sma50
        
        # Get SMA100 (daily)
        sma100 = self._get_single_indicator(symbol, "SMA", 100, interval)
        if sma100 is not None:
            indicators['SMA_100'] = sma100
        
        # Get SMA200 (daily)
        sma200 = self._get_single_indicator(symbol, "SMA", 200, interval)
        if sma200 is not None:
            indicators['SMA_200'] = sma200
        
        return indicators
    
    def _get_single_indicator(self, symbol: str, indicator: str, 
                              period: int, interval: str) -> Optional[float]:
        """
        Fetch single technical indicator from Alpha Vantage
        Returns most recent value
        """
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
                # Get most recent value
                latest_date = sorted(ta_data.keys(), reverse=True)[0]
                return float(ta_data[latest_date][indicator])
            
            return None
            
        except Exception as e:
            print(f"   ⚠️  Error getting {indicator}{period} for {symbol}: {e}")
            return None
    
    def get_stock_data_with_indicators(self, symbol: str, interval: str = "60min") -> Dict:
        """
        OPTIMIZED: Fetch OHLCV + all DAILY indicators for ONE stock
        
        IMPORTANT: Moving averages are from DAILY chart (proper trend analysis)
        Total API calls: 5 (1 intraday OHLCV + 4 daily indicators)
        Time: ~2 seconds per stock (with rate limiting)
        """
        print(f"   📊 Fetching {symbol}...")
        
        # 1. Get intraday OHLCV data (1 API call) - for pattern detection
        df = self.get_intraday_data(symbol, interval)
        if df.empty:
            return None
        
        # 2. Get DAILY indicators (4 API calls) - for trend analysis
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
            'ema_20': indicators.get('EMA_20'),  # DAILY EMA20
            'sma_50': indicators.get('SMA_50'),  # DAILY SMA50
            'sma_100': indicators.get('SMA_100'),  # DAILY SMA100
            'sma_200': indicators.get('SMA_200'),  # DAILY SMA200
            'previous_candle': df.iloc[-2] if len(df) >= 2 else None,
            'full_data': df
        }
        
        return result
    
    def batch_fetch_stocks(self, symbols: List[str], interval: str = "60min") -> List[Dict]:
        """
        OPTIMIZED BATCH FETCHING for multiple stocks
        
        Strategy:
        - 200 stocks × 5 API calls each = 1000 total calls
        - 150 calls/min = 6.67 minutes to scan all 200 stocks
        - Well within 3-minute candle close window
        """
        print(f"\n🚀 Starting batch fetch for {len(symbols)} stocks...")
        print(f"   Rate limit: {self.rate_limit} requests/min")
        print(f"   Expected time: ~{(len(symbols) * 5 / self.rate_limit):.1f} minutes\n")
        
        results = []
        start_time = time.time()
        
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
                elapsed = time.time() - start_time
                stocks_per_min = (i / elapsed) * 60
                remaining = len(symbols) - i
                eta = (remaining / stocks_per_min) if stocks_per_min > 0 else 0
                print(f"\n   📈 Progress: {i}/{len(symbols)} ({i/len(symbols)*100:.1f}%)")
                print(f"   ⏱️  Speed: {stocks_per_min:.1f} stocks/min")
                print(f"   🕐 ETA: {eta:.1f} minutes\n")
        
        total_time = time.time() - start_time
        print(f"\n✅ Batch fetch complete!")
        print(f"   Total time: {total_time/60:.2f} minutes")
        print(f"   Success rate: {len(results)}/{len(symbols)} ({len(results)/len(symbols)*100:.1f}%)\n")
        
        return results


class MarketScheduler:
    """Handle market hours and candle close detection"""
    
    @staticmethod
    def is_market_open() -> bool:
        """Check if US market is currently open (9:30 AM - 4:00 PM ET)"""
        now = datetime.now()  # Assumes server is in ET timezone
        
        # Check if weekend
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Check market hours (9:30 AM - 4:00 PM ET)
        market_open = now.replace(hour=9, minute=30, second=0)
        market_close = now.replace(hour=16, minute=0, second=0)
        
        return market_open <= now <= market_close
    
    @staticmethod
    def get_next_candle_close(interval_minutes: int = 60) -> datetime:
        """
        Calculate when the next candle closes
        For 60min candles: 10:30, 11:30, 12:30, 13:30, 14:30, 15:30
        """
        now = datetime.now()
        
        # Round up to next hour close
        if interval_minutes == 60:
            next_close = now.replace(minute=30, second=0, microsecond=0)
            if now.minute >= 30:
                next_close += timedelta(hours=1)
        else:
            # For other intervals, round to next interval boundary
            minutes_past = now.minute % interval_minutes
            if minutes_past > 0:
                next_close = now + timedelta(minutes=interval_minutes - minutes_past)
            else:
                next_close = now + timedelta(minutes=interval_minutes)
            next_close = next_close.replace(second=0, microsecond=0)
        
        return next_close
    
    @staticmethod
    def wait_for_candle_close(interval_minutes: int = 60):
        """Wait until the next candle closes, then add 1 min buffer"""
        next_close = MarketScheduler.get_next_candle_close(interval_minutes)
        now = datetime.now()
        
        wait_seconds = (next_close - now).total_seconds()
        
        if wait_seconds > 0:
            print(f"\n⏰ Next candle closes at {next_close.strftime('%H:%M:%S')}")
            print(f"   Waiting {wait_seconds/60:.1f} minutes...")
            time.sleep(wait_seconds)
            
            # Add 1-minute buffer for data to be available
            print(f"   ⏳ Adding 1-minute buffer for data availability...")
            time.sleep(60)
            print(f"   ✅ Candle closed! Starting scan...\n")


# Usage: from modules.alphavantage_client import AlphaVantageClient, MarketScheduler