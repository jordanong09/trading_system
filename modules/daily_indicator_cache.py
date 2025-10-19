# modules/daily_indicator_cache.py - Optimized Daily MA Caching

import pandas as pd
import pickle
import os
from datetime import datetime, date
from typing import Dict, Optional, List
import json

class DailyIndicatorCache:
    """
    Caches DAILY moving averages to avoid redundant API calls
    
    Key insight: DAILY MAs only update once per day (after market close)
    - Fetch once at market open
    - Reuse throughout entire trading day
    - Reduces API calls by 80%
    """
    
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, "daily_indicators.pkl")
        self.metadata_file = os.path.join(cache_dir, "daily_indicators_meta.json")
        os.makedirs(cache_dir, exist_ok=True)
        
        self.indicators_cache = {}  # {symbol: {ema_20, sma_50, sma_100, sma_200}}
        self.cache_date = None
        
        self._load_cache()
    
    def _load_cache(self):
        """Load cached daily indicators from disk"""
        try:
            if os.path.exists(self.cache_file) and os.path.exists(self.metadata_file):
                # Load metadata
                with open(self.metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                cache_date_str = metadata.get('date')
                if cache_date_str:
                    self.cache_date = datetime.strptime(cache_date_str, '%Y-%m-%d').date()
                
                # Load indicators
                with open(self.cache_file, 'rb') as f:
                    self.indicators_cache = pickle.load(f)
                
                print(f"📦 Loaded daily indicator cache from {cache_date_str}")
                print(f"   Cached symbols: {len(self.indicators_cache)}")
        
        except Exception as e:
            print(f"⚠️  Could not load cache: {e}")
            self.indicators_cache = {}
            self.cache_date = None
    
    def _save_cache(self):
        """Save cached daily indicators to disk"""
        try:
            # Save indicators
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.indicators_cache, f)
            
            # Save metadata
            metadata = {
                'date': self.cache_date.strftime('%Y-%m-%d') if self.cache_date else None,
                'symbol_count': len(self.indicators_cache),
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"✅ Saved daily indicator cache ({len(self.indicators_cache)} symbols)")
        
        except Exception as e:
            print(f"⚠️  Could not save cache: {e}")
    
    def is_cache_valid_for_today(self) -> bool:
        """Check if cache is valid for current trading day"""
        today = date.today()
        
        if self.cache_date is None:
            return False
        
        # Cache is valid if it's from today
        return self.cache_date == today
    
    def get_indicators(self, symbol: str) -> Optional[Dict]:
        """
        Get cached daily indicators for symbol
        Returns None if not in cache
        """
        return self.indicators_cache.get(symbol)
    
    def set_indicators(self, symbol: str, indicators: Dict):
        """
        Cache daily indicators for symbol
        indicators: {ema_20, sma_50, sma_100, sma_200}
        """
        self.indicators_cache[symbol] = indicators
        
        # Update cache date if not set
        if self.cache_date is None:
            self.cache_date = date.today()
    
    def invalidate_cache(self):
        """Clear cache (call at market open of new trading day)"""
        self.indicators_cache = {}
        self.cache_date = None
        print("🔄 Daily indicator cache invalidated for new trading day")
    
    def bulk_update(self, indicators_dict: Dict[str, Dict]):
        """
        Bulk update cache with multiple symbols
        indicators_dict: {symbol: {ema_20, sma_50, sma_100, sma_200}}
        """
        self.indicators_cache.update(indicators_dict)
        self.cache_date = date.today()
        self._save_cache()
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            'cache_date': self.cache_date.strftime('%Y-%m-%d') if self.cache_date else None,
            'cached_symbols': len(self.indicators_cache),
            'is_valid': self.is_cache_valid_for_today(),
            'symbols': list(self.indicators_cache.keys())
        }
    
    def needs_refresh(self, symbols: List[str]) -> List[str]:
        """
        Check which symbols need daily indicator refresh
        Returns list of symbols that need fetching
        """
        if not self.is_cache_valid_for_today():
            # Cache expired, need to refresh all
            return symbols
        
        # Check which symbols are missing
        missing = [s for s in symbols if s not in self.indicators_cache]
        return missing


# Usage example:
"""
# Initialize cache
cache = DailyIndicatorCache()

# Check if we need to fetch indicators
symbols = ['AAPL', 'MSFT', 'GOOGL']
symbols_to_fetch = cache.needs_refresh(symbols)

if symbols_to_fetch:
    print(f"Need to fetch daily MAs for {len(symbols_to_fetch)} symbols")
    
    # Fetch from API (only for missing symbols)
    for symbol in symbols_to_fetch:
        indicators = av_client.get_technical_indicators_daily(symbol)
        cache.set_indicators(symbol, indicators)
    
    cache.bulk_update({})  # Save cache
else:
    print("All daily indicators cached, using cache")

# Retrieve from cache
indicators = cache.get_indicators('AAPL')
"""