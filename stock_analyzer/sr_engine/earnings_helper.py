"""
Earnings Helper Module (T13)
============================

Manages earnings calendar data and blackout period detection.

Features:
- Fetches earnings calendar from Alpha Vantage
- Caches data for 24 hours to minimize API calls
- Checks if a symbol is in earnings blackout period (T-3 to T+2)

Author: Stock Analyzer v5.0
Date: November 2025
"""

import os
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from pathlib import Path
import json


class EarningsHelper:
    """
    Manages earnings calendar data and blackout period detection.
    """
    
    def __init__(self, api_key: str, cache_dir: str = "./cache"):
        """
        Initialize EarningsHelper.
        
        Args:
            api_key: Alpha Vantage API key
            cache_dir: Directory for caching earnings data
        """
        self.api_key = api_key
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "earnings_calendar.csv"
        self.cache_meta_file = self.cache_dir / "earnings_calendar_meta.json"
        self.cache_duration_hours = 24
        
    def fetch_earnings_calendar(self, force_refresh: bool = False) -> pd.DataFrame:
        """
        Fetch earnings calendar from Alpha Vantage.
        
        Uses cached data if available and less than 24 hours old.
        
        Args:
            force_refresh: If True, ignore cache and fetch fresh data
            
        Returns:
            DataFrame with columns: symbol, reportDate, fiscalDateEnding, estimate, currency
            
        Raises:
            requests.RequestException: If API call fails
        """
        # Check cache validity
        if not force_refresh and self._is_cache_valid():
            print("📦 Loading earnings calendar from cache...")
            return self._load_from_cache()
        
        # Fetch fresh data from API
        print("🌐 Fetching earnings calendar from Alpha Vantage...")
        
        url = "https://www.alphavantage.co/query"
        params = {
            'function': 'EARNINGS_CALENDAR',
            'horizon': '3month',
            'apikey': self.api_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            # Alpha Vantage returns CSV format
            # Parse the CSV content
            from io import StringIO
            csv_content = response.text
            
            # Read CSV into DataFrame
            df = pd.read_csv(StringIO(csv_content))
            
            # Validate expected columns
            required_columns = ['symbol', 'reportDate']
            if not all(col in df.columns for col in required_columns):
                raise ValueError(f"API response missing required columns. Got: {df.columns.tolist()}")
            
            # Convert reportDate to datetime
            df['reportDate'] = pd.to_datetime(df['reportDate'])
            
            # Save to cache
            self._save_to_cache(df)
            
            print(f"✅ Fetched {len(df)} earnings events")
            return df
            
        except requests.RequestException as e:
            print(f"❌ Error fetching earnings calendar: {e}")
            # Try to use cached data as fallback
            if self.cache_file.exists():
                print("⚠️  Using stale cache as fallback...")
                return self._load_from_cache()
            raise
            
    def is_in_blackout(
        self, 
        symbol: str, 
        check_date: Optional[datetime] = None,
        earnings_df: Optional[pd.DataFrame] = None
    ) -> Tuple[bool, Optional[datetime]]:
        """
        Check if a symbol is in earnings blackout period.
        
        Blackout period: T-3 to T+2 days from earnings report date
        (3 days before and 2 days after earnings)
        
        Args:
            symbol: Stock symbol to check
            check_date: Date to check (defaults to today)
            earnings_df: Pre-loaded earnings DataFrame (optional)
            
        Returns:
            Tuple of (is_blackout: bool, earnings_date: datetime or None)
            - is_blackout: True if symbol is in blackout period
            - earnings_date: The upcoming/recent earnings date (if found)
        """
        if check_date is None:
            check_date = datetime.now()
        
        # Normalize to midnight for date comparison (ignore time)
        check_date = check_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
        
        # Load earnings data if not provided
        if earnings_df is None:
            try:
                earnings_df = self.fetch_earnings_calendar()
            except Exception as e:
                print(f"⚠️  Warning: Could not fetch earnings data: {e}")
                return False, None
        
        # Filter for the specific symbol
        symbol_earnings = earnings_df[earnings_df['symbol'] == symbol.upper()]
        
        if symbol_earnings.empty:
            return False, None
        
        # Find earnings dates near the check_date
        for _, row in symbol_earnings.iterrows():
            earnings_date = row['reportDate']
            
            # Normalize earnings date to midnight
            if hasattr(earnings_date, 'replace'):
                earnings_date = earnings_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
            
            # Calculate blackout window: T-3 to T+2
            blackout_start = earnings_date - timedelta(days=3)
            blackout_end = earnings_date + timedelta(days=2)
            
            # Check if check_date falls within blackout period
            if blackout_start <= check_date <= blackout_end:
                return True, earnings_date
        
        return False, None
    
    def get_upcoming_earnings(
        self, 
        symbol: str,
        days_ahead: int = 30,
        earnings_df: Optional[pd.DataFrame] = None
    ) -> Optional[datetime]:
        """
        Get the next upcoming earnings date for a symbol.
        
        Args:
            symbol: Stock symbol
            days_ahead: How many days ahead to look
            earnings_df: Pre-loaded earnings DataFrame (optional)
            
        Returns:
            Next earnings date (datetime) or None if not found
        """
        if earnings_df is None:
            try:
                earnings_df = self.fetch_earnings_calendar()
            except Exception:
                return None
        
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff = today + timedelta(days=days_ahead)
        
        # Filter for symbol and future dates
        symbol_earnings = earnings_df[
            (earnings_df['symbol'] == symbol.upper()) &
            (earnings_df['reportDate'] >= today) &
            (earnings_df['reportDate'] <= cutoff)
        ]
        
        if symbol_earnings.empty:
            return None
        
        # Return the earliest upcoming date
        return symbol_earnings['reportDate'].min()
    
    def batch_check_blackout(
        self,
        symbols: list,
        check_date: Optional[datetime] = None
    ) -> Dict[str, Tuple[bool, Optional[datetime]]]:
        """
        Check blackout status for multiple symbols efficiently.
        
        Args:
            symbols: List of stock symbols
            check_date: Date to check (defaults to today)
            
        Returns:
            Dictionary mapping symbol to (is_blackout, earnings_date) tuple
        """
        # Fetch earnings data once
        try:
            earnings_df = self.fetch_earnings_calendar()
        except Exception as e:
            print(f"⚠️  Warning: Could not fetch earnings data: {e}")
            return {symbol: (False, None) for symbol in symbols}
        
        # Check each symbol
        results = {}
        for symbol in symbols:
            results[symbol] = self.is_in_blackout(
                symbol, 
                check_date=check_date,
                earnings_df=earnings_df
            )
        
        return results
    
    def _is_cache_valid(self) -> bool:
        """
        Check if cached data exists and is less than 24 hours old.
        
        Returns:
            True if cache is valid, False otherwise
        """
        if not self.cache_file.exists() or not self.cache_meta_file.exists():
            return False
        
        try:
            with open(self.cache_meta_file, 'r') as f:
                meta = json.load(f)
            
            cache_time = datetime.fromisoformat(meta['timestamp'])
            age_hours = (datetime.now() - cache_time).total_seconds() / 3600
            
            return age_hours < self.cache_duration_hours
            
        except (json.JSONDecodeError, KeyError, ValueError):
            return False
    
    def _load_from_cache(self) -> pd.DataFrame:
        """
        Load earnings data from cache.
        
        Returns:
            DataFrame with earnings data
        """
        df = pd.read_csv(self.cache_file)
        df['reportDate'] = pd.to_datetime(df['reportDate'])
        return df
    
    def _save_to_cache(self, df: pd.DataFrame) -> None:
        """
        Save earnings data to cache with timestamp.
        
        Args:
            df: Earnings DataFrame to cache
        """
        # Save DataFrame
        df.to_csv(self.cache_file, index=False)
        
        # Save metadata
        meta = {
            'timestamp': datetime.now().isoformat(),
            'records': len(df),
            'cache_duration_hours': self.cache_duration_hours
        }
        with open(self.cache_meta_file, 'w') as f:
            json.dump(meta, f, indent=2)
        
        print(f"💾 Cached {len(df)} earnings events")
    
    def clear_cache(self) -> None:
        """
        Clear the earnings calendar cache.
        """
        if self.cache_file.exists():
            self.cache_file.unlink()
        if self.cache_meta_file.exists():
            self.cache_meta_file.unlink()
        print("🗑️  Earnings cache cleared")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def check_symbol_blackout(
    symbol: str,
    api_key: str,
    cache_dir: str = "./cache"
) -> Tuple[bool, Optional[datetime]]:
    """
    Quick function to check if a symbol is in blackout.
    
    Args:
        symbol: Stock symbol
        api_key: Alpha Vantage API key
        cache_dir: Cache directory
        
    Returns:
        Tuple of (is_blackout, earnings_date)
    """
    helper = EarningsHelper(api_key, cache_dir)
    return helper.is_in_blackout(symbol)


def get_blackout_symbols(
    symbols: list,
    api_key: str,
    cache_dir: str = "./cache"
) -> list:
    """
    Get list of symbols currently in blackout period.
    
    Args:
        symbols: List of stock symbols to check
        api_key: Alpha Vantage API key
        cache_dir: Cache directory
        
    Returns:
        List of symbols in blackout period
    """
    helper = EarningsHelper(api_key, cache_dir)
    results = helper.batch_check_blackout(symbols)
    return [symbol for symbol, (in_blackout, _) in results.items() if in_blackout]


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Example usage (requires valid Alpha Vantage API key)
    
    # Initialize
    API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY', 'demo')
    helper = EarningsHelper(API_KEY)
    
    # Fetch earnings calendar
    try:
        df = helper.fetch_earnings_calendar()
        print(f"\n📊 Loaded {len(df)} earnings events")
        print("\nFirst 5 events:")
        print(df.head())
        
        # Check specific symbol
        test_symbol = 'AAPL'
        in_blackout, earnings_date = helper.is_in_blackout(test_symbol)
        
        print(f"\n🔍 {test_symbol} Blackout Check:")
        print(f"   In blackout: {in_blackout}")
        if earnings_date:
            print(f"   Earnings date: {earnings_date.strftime('%Y-%m-%d')}")
        
        # Get upcoming earnings
        next_earnings = helper.get_upcoming_earnings(test_symbol, days_ahead=60)
        if next_earnings:
            print(f"   Next earnings: {next_earnings.strftime('%Y-%m-%d')}")
        
        # Batch check
        test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'AMZN']
        results = helper.batch_check_blackout(test_symbols)
        
        print("\n📋 Batch Blackout Check:")
        for symbol, (in_blackout, earnings_date) in results.items():
            status = "⚠️  BLACKOUT" if in_blackout else "✅ Clear"
            date_str = earnings_date.strftime('%Y-%m-%d') if earnings_date else "N/A"
            print(f"   {symbol}: {status} (Earnings: {date_str})")
            
    except Exception as e:
        print(f"❌ Error: {e}")