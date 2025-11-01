# modules/cache_manager.py - Data Cache Management
"""
MVP 4.0 Cache Manager - OPTIMIZED
- Manages historical data cache for stocks
- Zone caching for EOD updates
- Maintains 30+ days of 1H candles
- 24-hour expiry for daily data
"""

import pandas as pd
import pickle
import json
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from pathlib import Path


class CacheManager:
    """
    Manages data caching for the system
    """
    
    def __init__(self, cache_dir: str = "storage/cache"):
        """
        Initialize cache manager
        
        Args:
            cache_dir: Directory for cache files (default: storage/cache)
        """
        self.cache_dir = Path(cache_dir)
        self.zones_dir = self.cache_dir / "zones"
        self.ohlcv_dir = self.cache_dir / "ohlcv"
        self.indicators_dir = self.cache_dir / "indicators"
        self.max_candles = 200  # Keep 200 bars (enough for indicators)
        
        # Create all subdirectories
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.zones_dir.mkdir(parents=True, exist_ok=True)
        self.ohlcv_dir.mkdir(parents=True, exist_ok=True)
        self.indicators_dir.mkdir(parents=True, exist_ok=True)
    
    def get_cache_file(self, symbol: str, timeframe: str = 'daily') -> str:
        """Get cache file path for symbol and timeframe - stores in ohlcv subdirectory"""
        return str(self.ohlcv_dir / f"{symbol}_{timeframe}_data.pkl")
    
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
                if df is not None and len(df) > self.max_candles:
                    df = df.sort_values('Date').tail(self.max_candles).reset_index(drop=True)
            
            return df
            
        except Exception:
            return None
    
    def save_cached_data(self, symbol: str, df: pd.DataFrame, timeframe: str = 'daily'):
        """Save data to cache"""
        cache_file = self.get_cache_file(symbol, timeframe)
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(df, f)
        except Exception:
            pass  # Silent fail for cache writes
    
    def merge_new_data(self, symbol: str, new_df: pd.DataFrame, 
                      cached_df: Optional[pd.DataFrame],
                      timeframe: str = 'daily') -> pd.DataFrame:
        """
        Merge new data with cached data
        
        Args:
            symbol: Stock symbol
            new_df: Newly fetched DataFrame
            cached_df: Previously cached DataFrame (or None)
            timeframe: 'daily' or 'hourly'
            
        Returns:
            Merged DataFrame
        """
        if cached_df is None or cached_df.empty:
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
            cached_df = self.load_cached_data(symbol, 'daily', max_age_hours=24)
            if cached_df is not None:
                return cached_df
        
        # Cache miss - fetch new data
        new_df = fetch_func(symbol)
        
        if new_df is None or new_df.empty:
            return None
        
        # Merge with any existing cache
        cached_df = self.load_cached_data(symbol, 'daily', max_age_hours=999999)
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
            cached_df = self.load_cached_data(symbol, 'hourly', max_age_hours=4)
            if cached_df is not None:
                return cached_df
        
        # Cache miss - fetch new data
        new_df = fetch_func(symbol)
        
        if new_df is None or new_df.empty:
            return None
        
        # Merge with any existing cache
        cached_df = self.load_cached_data(symbol, 'hourly', max_age_hours=999999)
        merged_df = self.merge_new_data(symbol, new_df, cached_df, 'hourly')
        
        # Save to cache
        self.save_cached_data(symbol, merged_df, 'hourly')
        
        return merged_df
    
    # ========================================================================
    # ZONE CACHING - NEW OPTIMIZATION
    # ========================================================================
    
    def load_cached_zones(self, symbol: str, max_age_hours: int = 24) -> Optional[List[Dict]]:
        """
        Load cached zones for symbol
        
        Args:
            symbol: Stock symbol
            max_age_hours: Maximum cache age in hours (default 24h)
        
        Returns:
            List of zone dicts if cache valid, None otherwise
        """
        zone_file = self.zones_dir / f"{symbol}_zones.json"
        
        if not zone_file.exists():
            return None
        
        try:
            # Check cache age
            cache_age = datetime.now() - datetime.fromtimestamp(zone_file.stat().st_mtime)
            
            if cache_age > timedelta(hours=max_age_hours):
                return None
            
            # Load zones
            with open(zone_file, 'r') as f:
                zones = json.load(f)
            
            return zones
            
        except Exception:
            return None
    
    def save_zones(self, symbol: str, zones: List[Dict]):
        """
        Save zones to cache
        
        Args:
            symbol: Stock symbol
            zones: List of zone dictionaries to cache
        """
        zone_file = self.zones_dir / f"{symbol}_zones.json"
        
        try:
            with open(zone_file, 'w') as f:
                json.dump(zones, f, indent=2)
        except Exception:
            pass  # Silent fail for cache writes
    
    def clear_zone_cache(self, symbol: Optional[str] = None):
        """
        Clear zone cache files
        
        Args:
            symbol: Clear specific symbol (or all if None)
        """
        if symbol:
            zone_file = self.zones_dir / f"{symbol}_zones.json"
            if zone_file.exists():
                zone_file.unlink()
        else:
            # Clear all zone files
            for zone_file in self.zones_dir.glob("*_zones.json"):
                zone_file.unlink()
    
    # ========================================================================
    # CACHE MANAGEMENT
    # ========================================================================
    
    def clear_cache(self, symbol: Optional[str] = None, timeframe: Optional[str] = None):
        """
        Clear cache files
        
        Args:
            symbol: Clear specific symbol (or all if None)
            timeframe: Clear specific timeframe (or all if None)
        """
        if symbol and timeframe:
            cache_file = self.get_cache_file(symbol, timeframe)
            if os.path.exists(cache_file):
                os.remove(cache_file)
        
        elif symbol:
            for tf in ['daily', 'hourly']:
                cache_file = self.get_cache_file(symbol, tf)
                if os.path.exists(cache_file):
                    os.remove(cache_file)
        
        else:
            # Clear entire cache directory
            import shutil
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                # Recreate all subdirectories
                self.cache_dir.mkdir(parents=True)
                self.zones_dir.mkdir(parents=True)
                self.ohlcv_dir.mkdir(parents=True)
                self.indicators_dir.mkdir(parents=True)
    
    def get_cache_info(self) -> dict:
        """
        Get information about cached files
        
        Returns:
            Dict with cache statistics
        """
        ohlcv_files = list(self.ohlcv_dir.glob("*.pkl"))
        zone_files = list(self.zones_dir.glob("*_zones.json"))
        indicator_files = list(self.indicators_dir.glob("*.pkl")) + list(self.indicators_dir.glob("*.json"))
        
        total_size = sum(f.stat().st_size for f in ohlcv_files + zone_files + indicator_files)
        
        return {
            'ohlcv_files': len(ohlcv_files),
            'zone_files': len(zone_files),
            'indicator_files': len(indicator_files),
            'total_files': len(ohlcv_files) + len(zone_files) + len(indicator_files),
            'total_size_mb': total_size / (1024 * 1024),
            'cache_dir': str(self.cache_dir),
            'subdirs': {
                'ohlcv': str(self.ohlcv_dir),
                'zones': str(self.zones_dir),
                'indicators': str(self.indicators_dir)
            }
        }