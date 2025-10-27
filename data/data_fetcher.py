# modules/data_fetcher.py - Alpha Vantage API Integration
"""
MVP 4.0 Data Fetcher
- Fetches daily OHLCV (60 bars)
- Fetches 1H OHLCV (120 bars)
- Rate limiting (75 calls/min for Premium)
- Automatic caching (24h expiry)
- Error handling & retries
"""

import requests
import pandas as pd
import time
import json
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import os


class AlphaVantageAPI:
    """
    Alpha Vantage API client with rate limiting and caching
    """
    
    def __init__(self, api_key: str, cache_dir: str = "cache"):
        """
        Initialize API client
        
        Args:
            api_key: Alpha Vantage API key
            cache_dir: Directory for caching responses
        """
        self.api_key = api_key
        self.cache_dir = cache_dir
        self.base_url = "https://www.alphavantage.co/query"
        
        # Rate limiting
        self.calls_per_minute = 150  # Premium tier
        self.call_times = []
        
        # Ensure cache directory exists
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_cache_path(self, symbol: str, timeframe: str) -> str:
        """Get cache file path for symbol and timeframe"""
        return os.path.join(self.cache_dir, f"{symbol}_{timeframe}.json")
    
    def _is_cache_valid(self, cache_path: str, max_age_hours: int = 24) -> bool:
        """Check if cache file exists and is fresh"""
        if not os.path.exists(cache_path):
            return False
        
        # Check age
        file_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
        age = datetime.now() - file_time
        
        return age < timedelta(hours=max_age_hours)
    
    def _load_from_cache(self, cache_path: str) -> Optional[Dict]:
        """Load data from cache file"""
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(f"   ⚠️  Cache read error: {e}")
            return None
    
    def _save_to_cache(self, cache_path: str, data: Dict):
        """Save data to cache file"""
        try:
            with open(cache_path, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"   ⚠️  Cache write error: {e}")
    
    def _rate_limit_check(self):
        """
        Enforce rate limiting
        Wait if necessary to stay under 150 calls/minute
        """
        now = time.time()
        
        # Remove calls older than 60 seconds
        self.call_times = [t for t in self.call_times if now - t < 60]
        
        # If at limit, wait
        if len(self.call_times) >= self.calls_per_minute:
            oldest_call = min(self.call_times)
            wait_time = 60 - (now - oldest_call) + 1
            
            if wait_time > 0:
                print(f"   ⏳ Rate limit reached, waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
                
                # Clear old calls after waiting
                now = time.time()
                self.call_times = [t for t in self.call_times if now - t < 60]
        
        # Record this call
        self.call_times.append(time.time())
    
    def _make_request(self, params: Dict, max_retries: int = 3) -> Optional[Dict]:
        """
        Make API request with retries
        
        Args:
            params: API parameters
            max_retries: Maximum retry attempts
            
        Returns:
            API response as dict or None if failed
        """
        params['apikey'] = self.api_key
        
        for attempt in range(max_retries):
            try:
                # Rate limit check
                self._rate_limit_check()
                
                # Make request
                response = requests.get(self.base_url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                # Check for API errors
                if "Error Message" in data:
                    print(f"   ❌ API Error: {data['Error Message']}")
                    return None
                
                if "Note" in data:  # Rate limit message
                    print(f"   ⚠️  API Note: {data['Note']}")
                    if attempt < max_retries - 1:
                        time.sleep(60)  # Wait 1 minute
                        continue
                    return None
                
                return data
                
            except requests.exceptions.RequestException as e:
                print(f"   ⚠️  Request error (attempt {attempt+1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    time.sleep(5)  # Wait before retry
                    continue
                
                return None
        
        return None
    
    def fetch_daily_data(self, symbol: str, outputsize: str = 'full') -> Optional[pd.DataFrame]:
        """
        Fetch daily OHLCV data
        
        Args:
            symbol: Stock symbol
            outputsize: 'compact' (100 bars) or 'full' (20+ years)
            
        Returns:
            DataFrame with daily OHLCV data or None
        """
        cache_path = self._get_cache_path(symbol, 'daily')
        
        # Check cache first (24h expiry for daily data)
        if self._is_cache_valid(cache_path, max_age_hours=24):
            cached_data = self._load_from_cache(cache_path)
            if cached_data:
                print(f"   📦 Loaded {symbol} daily data from cache")
                return self._parse_daily_data(cached_data)
        
        # Fetch from API
        print(f"   🌐 Fetching {symbol} daily data from Alpha Vantage...")
        
        params = {
            'function': 'TIME_SERIES_DAILY',
            'symbol': symbol,
            'outputsize': outputsize
        }
        
        data = self._make_request(params)
        
        if data is None:
            return None
        
        # Save to cache
        self._save_to_cache(cache_path, data)
        
        # Parse and return
        return self._parse_daily_data(data)
    
    def _parse_daily_data(self, data: Dict) -> Optional[pd.DataFrame]:
        """Parse daily data response into DataFrame"""
        try:
            time_series = data.get('Time Series (Daily)', {})
            
            if not time_series:
                print("   ❌ No time series data in response")
                return None
            
            # Convert to DataFrame
            df_data = []
            for date_str, values in time_series.items():
                # Handle different volume key formats
                volume = None
                if '6. volume' in values:
                    volume = int(values['6. volume'])
                elif '5. volume' in values:
                    volume = int(values['5. volume'])
                elif 'volume' in values:
                    volume = int(values['volume'])
                elif 'Volume' in values:
                    volume = int(values['Volume'])
                else:
                    volume = 0  # Default if not found
                
                df_data.append({
                    'Date': pd.to_datetime(date_str),
                    'Open': float(values.get('1. open', values.get('open', values.get('Open', 0)))),
                    'High': float(values.get('2. high', values.get('high', values.get('High', 0)))),
                    'Low': float(values.get('3. low', values.get('low', values.get('Low', 0)))),
                    'Close': float(values.get('4. close', values.get('close', values.get('Close', 0)))),
                    'Volume': volume
                })
            
            df = pd.DataFrame(df_data)
            df = df.sort_values('Date').reset_index(drop=True)
            if df is not None and len(df) > 200:
                df = df.tail(200).reset_index(drop=True)
            
            return df
            
        except Exception as e:
            print(f"   ❌ Error parsing daily data: {e}")
            return None
    
    def fetch_hourly_data(self, symbol: str, outputsize: str = 'full') -> Optional[pd.DataFrame]:
        """
        Fetch 1H OHLCV data
        
        Args:
            symbol: Stock symbol
            outputsize: 'compact' (100 bars) or 'full' (trailing 30 days of the most recent intraday data)
            
        Returns:
            DataFrame with hourly OHLCV data or None
        """
        cache_path = self._get_cache_path(symbol, 'hourly')
        
        # Check cache first (4h expiry for hourly data - more frequent)
        if self._is_cache_valid(cache_path, max_age_hours=4):
            cached_data = self._load_from_cache(cache_path)
            if cached_data:
                print(f"   📦 Loaded {symbol} hourly data from cache")
                return self._parse_hourly_data(cached_data)
        
        # Fetch from API
        print(f"   🌐 Fetching {symbol} hourly data from Alpha Vantage...")
        
        params = {
            'function': 'TIME_SERIES_INTRADAY',
            'symbol': symbol,
            'interval': '60min',
            'outputsize': outputsize,
            'adjusted': 'false',
            "extended_hours": "false"
        }
        
        data = self._make_request(params)
        
        if data is None:
            return None
        
        # Save to cache
        self._save_to_cache(cache_path, data)
        
        # Parse and return
        return self._parse_hourly_data(data)
    
    def _parse_hourly_data(self, data: Dict) -> Optional[pd.DataFrame]:
        """Parse hourly data response into DataFrame"""
        try:
            time_series = data.get('Time Series (60min)', {})
            
            if not time_series:
                print("   ❌ No time series data in response")
                return None
            
            # Convert to DataFrame
            df_data = []
            for datetime_str, values in time_series.items():
                df_data.append({
                    'Date': pd.to_datetime(datetime_str),
                    'Open': float(values['1. open']),
                    'High': float(values['2. high']),
                    'Low': float(values['3. low']),
                    'Close': float(values['4. close']),
                    'Volume': int(values['5. volume'])
                })
            
            df = pd.DataFrame(df_data)
            df = df.sort_values('Date').reset_index(drop=True)
            
            return df
            
        except Exception as e:
            print(f"   ❌ Error parsing hourly data: {e}")
            return None
    
    def fetch_both_timeframes(self, symbol: str) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """
        Fetch both daily and hourly data for a symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Tuple of (daily_df, hourly_df)
        """
        daily_df = self.fetch_daily_data(symbol)
        hourly_df = self.fetch_hourly_data(symbol)
        
        return daily_df, hourly_df
    
    def get_api_usage_stats(self) -> Dict:
        """Get current API usage statistics"""
        now = time.time()
        recent_calls = [t for t in self.call_times if now - t < 60]
        
        return {
            'calls_last_minute': len(recent_calls),
            'calls_per_minute_limit': self.calls_per_minute,
            'remaining_capacity': self.calls_per_minute - len(recent_calls)
        }


# Quick test function
def test_data_fetcher():
    """Test data fetcher with demo key"""
    import config
    
    print("🧪 Testing Data Fetcher")
    print("=" * 60)
    
    # Initialize API
    api = AlphaVantageAPI(config.ALPHA_VANTAGE_API_KEY)
    
    # Test with IBM (always works with demo key)
    symbol = 'IBM'
    
    print(f"\n📊 Fetching data for {symbol}...")
    
    # Fetch daily data
    daily_df = api.fetch_daily_data(symbol)
    
    if daily_df is not None:
        print(f"\n✅ Daily data fetched:")
        print(f"   Rows: {len(daily_df)}")
        print(f"   Date range: {daily_df['Date'].min()} to {daily_df['Date'].max()}")
        print(f"   Latest close: ${daily_df.iloc[-1]['Close']:.2f}")
    else:
        print("\n❌ Failed to fetch daily data")
    
    # Fetch hourly data
    hourly_df = api.fetch_hourly_data(symbol)
    
    if hourly_df is not None:
        print(f"\n✅ Hourly data fetched:")
        print(f"   Rows: {len(hourly_df)}")
        print(f"   Date range: {hourly_df['Date'].min()} to {hourly_df['Date'].max()}")
        print(f"   Latest close: ${hourly_df.iloc[-1]['Close']:.2f}")
    else:
        print("\n❌ Failed to fetch hourly data")
    
    # Show API usage
    stats = api.get_api_usage_stats()
    print(f"\n📈 API Usage:")
    print(f"   Calls in last minute: {stats['calls_last_minute']}/{stats['calls_per_minute_limit']}")
    print(f"   Remaining capacity: {stats['remaining_capacity']}")
    
    print("\n✅ Data fetcher test complete!")


if __name__ == "__main__":
    test_data_fetcher()
