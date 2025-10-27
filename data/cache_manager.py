# modules/cache_manager.py - Data Cache Management
"""
MVP 4.0 Cache Manager
- Manages historical data cache for stocks
- Maintains 30+ days of 1H candles
- 24-hour expiry for daily data
- Merge new data with cached data
"""

import pandas as pd
import pickle
import os
from datetime import datetime, timedelta
from typing import Optional


class CacheManager:
    """
    Manages data caching for the system
    """
    
    def __init__(self, cache_dir: str = "cache"):
        """
        Initialize cache manager
        
        Args:
            cache_dir: Directory for cache files
        """
        self.cache_dir = cache_dir
        self.max_candles = 200  # Keep 200 bars (enough for indicators)
        os.makedirs(cache_dir, exist_ok=True)
    
    def get_cache_file(self, symbol: str, timeframe: str = 'daily') -> str:
        """
        Get cache file path for symbol and timeframe
        
        Args:
            symbol: Stock symbol
            timeframe: 'daily' or 'hourly'
            
        Returns:
            Full path to cache file
        """
        return os.path.join(self.cache_dir, f"{symbol}_{timeframe}_data.pkl")
    
    def load_cached_data(self, symbol: str, timeframe: str = 'daily', 
                        max_age_hours: int = 24) -> Optional[pd.DataFrame]:
        """
        Load cached data if available and fresh
        
        Args:
            symbol: Stock symbol
            timeframe: 'daily' or 'hourly'
            max_age_hours: Maximum cache age in hours
            
        Returns:
            DataFrame if cache valid, None otherwise
        """
        cache_file = self.get_cache_file(symbol, timeframe)
        
        if not os.path.exists(cache_file):
            return None
        
        try:
            # Check cache age
            cache_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_file))
            
            if cache_age > timedelta(hours=max_age_hours):
                return None
            
            # Load cached data
            with open(cache_file, 'rb') as f:
                df = pickle.load(f)
                MAX_DAYS = 200
                if df is not None and len(df) > MAX_DAYS:
                    df = df.sort_values('Date').tail(MAX_DAYS).reset_index(drop=True)
            return df
            
        except Exception as e:
            print(f"   ⚠️  Error loading cache for {symbol}: {e}")
            return None
    
    def save_cached_data(self, symbol: str, df: pd.DataFrame, timeframe: str = 'daily'):
        """
        Save data to cache
        
        Args:
            symbol: Stock symbol
            df: DataFrame to cache
            timeframe: 'daily' or 'hourly'
        """
        cache_file = self.get_cache_file(symbol, timeframe)
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(df, f)
        except Exception as e:
            print(f"   ⚠️  Error saving cache for {symbol}: {e}")
    
    def merge_new_data(self, symbol: str, new_df: pd.DataFrame, 
                      cached_df: Optional[pd.DataFrame],
                      timeframe: str = 'daily') -> pd.DataFrame:
        """
        Merge new data with cached data
        
        For daily: Keep last 60 bars
        For hourly: Keep last 120 bars
        
        Args:
            symbol: Stock symbol
            new_df: Newly fetched DataFrame
            cached_df: Previously cached DataFrame (or None)
            timeframe: 'daily' or 'hourly'
            
        Returns:
            Merged DataFrame
        """
        if cached_df is None or cached_df.empty:
            # No cache, return new data limited to max candles
            max_bars = 120 if timeframe == 'hourly' else 200
            return new_df.tail(max_bars).reset_index(drop=True)
        
        # Combine and remove duplicates
        combined = pd.concat([cached_df, new_df])
        combined = combined.drop_duplicates(subset=['Date'], keep='last')
        combined = combined.sort_values('Date').reset_index(drop=True)
        
        # Keep only most recent bars
        max_bars = 120 if timeframe == 'hourly' else 200
        return combined.tail(max_bars).reset_index(drop=True)
    
    def get_or_fetch_daily(self, symbol: str, fetch_func, force_refresh: bool = False) -> Optional[pd.DataFrame]:
        """
        Get daily data from cache or fetch if needed
        
        Args:
            symbol: Stock symbol
            fetch_func: Function to call if cache miss (should return DataFrame)
            force_refresh: Force fetch even if cache valid
            
        Returns:
            DataFrame with daily data or None
        """
        if not force_refresh:
            # Try cache first
            cached_df = self.load_cached_data(symbol, 'daily', max_age_hours=24)
            if cached_df is not None:
                return cached_df
        
        # Cache miss or force refresh - fetch new data
        new_df = fetch_func(symbol)
        
        if new_df is None or new_df.empty:
            return None
        
        # Merge with any existing cache
        cached_df = self.load_cached_data(symbol, 'daily', max_age_hours=999999)  # Get even stale cache
        merged_df = self.merge_new_data(symbol, new_df, cached_df, 'daily')
        
        # Save to cache
        self.save_cached_data(symbol, merged_df, 'daily')
        
        return merged_df
    
    def get_or_fetch_hourly(self, symbol: str, fetch_func, force_refresh: bool = False) -> Optional[pd.DataFrame]:
        """
        Get hourly data from cache or fetch if needed
        
        Args:
            symbol: Stock symbol
            fetch_func: Function to call if cache miss (should return DataFrame)
            force_refresh: Force fetch even if cache valid
            
        Returns:
            DataFrame with hourly data or None
        """
        if not force_refresh:
            # Try cache first (4 hour expiry for hourly data)
            cached_df = self.load_cached_data(symbol, 'hourly', max_age_hours=4)
            if cached_df is not None:
                return cached_df
        
        # Cache miss or force refresh - fetch new data
        new_df = fetch_func(symbol)
        
        if new_df is None or new_df.empty:
            return None
        
        # Merge with any existing cache
        cached_df = self.load_cached_data(symbol, 'hourly', max_age_hours=999999)  # Get even stale cache
        merged_df = self.merge_new_data(symbol, new_df, cached_df, 'hourly')
        
        # Save to cache
        self.save_cached_data(symbol, merged_df, 'hourly')
        
        return merged_df
    
    def clear_cache(self, symbol: Optional[str] = None, timeframe: Optional[str] = None):
        """
        Clear cache files
        
        Args:
            symbol: Clear specific symbol (or all if None)
            timeframe: Clear specific timeframe (or all if None)
        """
        if symbol and timeframe:
            # Clear specific file
            cache_file = self.get_cache_file(symbol, timeframe)
            if os.path.exists(cache_file):
                os.remove(cache_file)
                print(f"   🗑️  Cleared cache for {symbol} {timeframe}")
        
        elif symbol:
            # Clear all timeframes for symbol
            for tf in ['daily', 'hourly']:
                cache_file = self.get_cache_file(symbol, tf)
                if os.path.exists(cache_file):
                    os.remove(cache_file)
            print(f"   🗑️  Cleared all cache for {symbol}")
        
        else:
            # Clear entire cache directory
            import shutil
            if os.path.exists(self.cache_dir):
                shutil.rmtree(self.cache_dir)
                os.makedirs(self.cache_dir)
                print(f"   🗑️  Cleared entire cache directory")
    
    def get_cache_info(self) -> dict:
        """
        Get information about cached files
        
        Returns:
            Dict with cache statistics
        """
        cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.pkl')]
        
        total_size = 0
        for f in cache_files:
            file_path = os.path.join(self.cache_dir, f)
            total_size += os.path.getsize(file_path)
        
        return {
            'total_files': len(cache_files),
            'total_size_mb': total_size / (1024 * 1024),
            'cache_dir': self.cache_dir
        }


# Quick test function
def test_cache_manager():
    """Test cache manager"""
    import pandas as pd
    from datetime import datetime, timedelta
    
    print("🧪 Testing Cache Manager")
    print("=" * 60)
    
    # Initialize cache manager
    cache_mgr = CacheManager(cache_dir="cache_test")
    
    # Create sample data
    dates = pd.date_range(end=datetime.now(), periods=200, freq='D')
    sample_df = pd.DataFrame({
        'Date': dates,
        'Open': [100 + i for i in range(200)],
        'High': [102 + i for i in range(200)],
        'Low': [98 + i for i in range(200)],
        'Close': [101 + i for i in range(200)],
        'Volume': [1000000] * 200
    })
    
    symbol = 'TEST'
    
    # Test save
    print(f"\n💾 Saving test data for {symbol}...")
    cache_mgr.save_cached_data(symbol, sample_df, 'daily')
    print("   ✅ Saved")
    
    # Test load
    print(f"\n📂 Loading cached data for {symbol}...")
    loaded_df = cache_mgr.load_cached_data(symbol, 'daily')
    
    if loaded_df is not None:
        print(f"   ✅ Loaded {len(loaded_df)} rows")
        print(f"   Date range: {loaded_df['Date'].min()} to {loaded_df['Date'].max()}")
    else:
        print("   ❌ Failed to load")
    
    # Test merge
    print(f"\n🔀 Testing merge with new data...")
    new_dates = pd.date_range(start=dates[-1] + timedelta(days=1), periods=5, freq='D')
    new_df = pd.DataFrame({
        'Date': new_dates,
        'Open': [160 + i for i in range(5)],
        'High': [162 + i for i in range(5)],
        'Low': [158 + i for i in range(5)],
        'Close': [161 + i for i in range(5)],
        'Volume': [1000000] * 5
    })
    
    merged_df = cache_mgr.merge_new_data(symbol, new_df, loaded_df, 'daily')
    print(f"   ✅ Merged: {len(loaded_df)} + {len(new_df)} → {len(merged_df)} rows") # type: ignore
    
    # Test cache info
    print(f"\n📊 Cache statistics:")
    info = cache_mgr.get_cache_info()
    print(f"   Files: {info['total_files']}")
    print(f"   Size: {info['total_size_mb']:.2f} MB")
    
    # Cleanup
    cache_mgr.clear_cache()
    print(f"\n🗑️  Test cache cleaned up")
    
    print("\n✅ Cache manager test complete!")


if __name__ == "__main__":
    test_cache_manager()
