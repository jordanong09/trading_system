"""
Earnings Blackout Filter for Swing Trader Alert Engine
Blocks signals T-3 days before and T+2 days after earnings to avoid volatility.

Priority: ⭐⭐⭐
Purpose: Prevent signals during unpredictable earnings periods
"""

import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import time


class EarningsFilter:
    """
    Filters out trading signals during earnings blackout periods.
    
    Blackout Window: T-3 days before to T+2 days after earnings
    
    Features:
    - Fetch earnings dates from multiple sources
    - Cache earnings data (quarterly refresh)
    - Graceful degradation if API unavailable
    - Batch updates for efficiency
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_file: str = "earnings_cache.json",
        cache_dir: str = "./cache",
        blackout_days_before: int = 3,
        blackout_days_after: int = 2
    ):
        """
        Initialize earnings filter.
        
        Args:
            api_key: API key for earnings data service (optional)
            cache_file: JSON file to cache earnings dates
            cache_dir: Directory for cache file
            blackout_days_before: Days before earnings to block signals
            blackout_days_after: Days after earnings to block signals
        """
        self.api_key = api_key
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / cache_file
        
        self.blackout_days_before = blackout_days_before
        self.blackout_days_after = blackout_days_after
        
        # Cache structure: {symbol: {next_earnings: "YYYY-MM-DD", last_updated: "ISO8601"}}
        self.earnings_cache: Dict[str, Dict[str, str]] = {}
        
        # Load existing cache
        self.load_cache()
        
        # Track API availability
        self.api_available = True
    
    def fetch_earnings_date(self, symbol: str, force_refresh: bool = False) -> Optional[str]:
        """
        Fetch next earnings date for a symbol.
        
        Args:
            symbol: Stock symbol
            force_refresh: Force API call even if cached
        
        Returns:
            Next earnings date as "YYYY-MM-DD" or None if unavailable
        """
        # Check cache first (if not forcing refresh)
        if not force_refresh and symbol in self.earnings_cache:
            cached_data = self.earnings_cache[symbol]
            last_updated = datetime.fromisoformat(cached_data["last_updated"])
            
            # Cache valid for 90 days (quarterly refresh)
            if datetime.now() - last_updated < timedelta(days=90):
                earnings_date = cached_data.get("next_earnings")
                if earnings_date:
                    print(f"   📅 {symbol}: Cached earnings date {earnings_date}")
                    return earnings_date
        
        # Try to fetch from API
        earnings_date = self._fetch_from_api(symbol)
        
        if earnings_date:
            # Update cache
            self.earnings_cache[symbol] = {
                "next_earnings": earnings_date,
                "last_updated": datetime.now().isoformat()
            }
            self.save_cache()
            print(f"   ✅ {symbol}: Fetched earnings date {earnings_date}")
            return earnings_date
        else:
            # No earnings data available
            print(f"   ⚠️  {symbol}: No earnings data available")
            return None
    
    def _fetch_from_api(self, symbol: str) -> Optional[str]:
        """
        Fetch earnings date from API (multiple sources with fallback).
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Earnings date as "YYYY-MM-DD" or None
        """
        if not self.api_available:
            return None
        
        # Try Alpha Vantage (if API key provided)
        if self.api_key:
            earnings_date = self._fetch_alpha_vantage(symbol)
            if earnings_date:
                return earnings_date
        
        # Fallback: Try Yahoo Finance (no API key needed)
        earnings_date = self._fetch_yahoo_finance(symbol)
        if earnings_date:
            return earnings_date
        
        return None
    
    def _fetch_alpha_vantage(self, symbol: str) -> Optional[str]:
        """
        Fetch from Alpha Vantage EARNINGS_CALENDAR endpoint.
        Note: Requires Premium API key.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Next earnings date or None
        """
        try:
            url = f"https://www.alphavantage.co/query"
            params = {
                "function": "EARNINGS_CALENDAR",
                "symbol": symbol,
                "apikey": self.api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                # Alpha Vantage returns CSV format
                lines = response.text.strip().split('\n')
                if len(lines) > 1:
                    # Parse CSV (symbol,fiscalDateEnding,reportDate,...)
                    header = lines[0].split(',')
                    data = lines[1].split(',')
                    
                    if len(data) > 2:
                        report_date = data[2]  # reportDate column
                        return report_date
            
            return None
        
        except Exception as e:
            print(f"   ⚠️  Alpha Vantage error for {symbol}: {e}")
            return None
    
    def _fetch_yahoo_finance(self, symbol: str) -> Optional[str]:
        """
        Fetch from Yahoo Finance (web scraping fallback).
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Next earnings date or None
        """
        try:
            # Yahoo Finance API endpoint
            url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
            params = {
                "modules": "calendarEvents"
            }
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Navigate to earnings date
                result = data.get("quoteSummary", {}).get("result", [])
                if result:
                    calendar = result[0].get("calendarEvents", {})
                    earnings = calendar.get("earnings", {})
                    earnings_date = earnings.get("earningsDate", [{}])[0].get("fmt")
                    
                    if earnings_date:
                        # Convert to YYYY-MM-DD format
                        try:
                            date_obj = datetime.strptime(earnings_date, "%Y-%m-%d")
                            return date_obj.strftime("%Y-%m-%d")
                        except:
                            pass
            
            return None
        
        except Exception as e:
            print(f"   ⚠️  Yahoo Finance error for {symbol}: {e}")
            return None
    
    def is_earnings_week(self, symbol: str) -> bool:
        """
        Check if symbol is in earnings blackout period.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            True if in blackout window (T-3 to T+2), False otherwise
        """
        earnings_date = self.fetch_earnings_date(symbol)
        
        if not earnings_date:
            # No earnings data - allow signal (fail open)
            return False
        
        try:
            earnings_dt = datetime.strptime(earnings_date, "%Y-%m-%d")
            today = datetime.now()
            
            # Calculate blackout window
            blackout_start = earnings_dt - timedelta(days=self.blackout_days_before)
            blackout_end = earnings_dt + timedelta(days=self.blackout_days_after)
            
            # Check if today is in blackout window
            if blackout_start <= today <= blackout_end:
                days_until = (earnings_dt - today).days
                print(f"   📅 {symbol}: Earnings in {days_until} days - BLACKOUT ACTIVE")
                return True
            
            return False
        
        except ValueError:
            print(f"   ⚠️  Invalid earnings date format for {symbol}: {earnings_date}")
            return False
    
    def should_block_signal(self, symbol: str) -> bool:
        """
        Main filter function - determines if signal should be blocked.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            True if signal should be blocked, False if allowed
        """
        return self.is_earnings_week(symbol)
    
    def refresh_cache(self, symbols: List[str], max_requests: int = 100) -> Dict[str, bool]:
        """
        Batch refresh earnings dates for multiple symbols.
        Useful for weekly maintenance.
        
        Args:
            symbols: List of stock symbols to refresh
            max_requests: Maximum API requests to make (rate limiting)
        
        Returns:
            Dictionary mapping symbol to success status
        """
        results = {}
        requests_made = 0
        
        print(f"\n🔄 Refreshing earnings cache for {len(symbols)} symbols...")
        
        for symbol in symbols:
            if requests_made >= max_requests:
                print(f"   ⚠️  Hit rate limit ({max_requests} requests), stopping refresh")
                break
            
            try:
                earnings_date = self.fetch_earnings_date(symbol, force_refresh=True)
                results[symbol] = earnings_date is not None
                requests_made += 1
                
                # Rate limiting - 1 request per second
                time.sleep(1)
            
            except Exception as e:
                print(f"   ❌ Error refreshing {symbol}: {e}")
                results[symbol] = False
        
        # Save updated cache
        self.save_cache()
        
        success_count = sum(1 for v in results.values() if v)
        print(f"   ✅ Successfully refreshed {success_count}/{len(results)} symbols")
        
        return results
    
    def load_cache(self) -> bool:
        """
        Load earnings cache from JSON file.
        
        Returns:
            True if loaded successfully, False if file doesn't exist
        """
        if not self.cache_file.exists():
            print(f"   ℹ️  No existing earnings cache found")
            return False
        
        try:
            with open(self.cache_file, 'r') as f:
                self.earnings_cache = json.load(f)
            
            print(f"   ✅ Loaded {len(self.earnings_cache)} earnings records from cache")
            return True
        
        except (json.JSONDecodeError, IOError) as e:
            print(f"   ⚠️  Error loading earnings cache: {e}")
            self.earnings_cache = {}
            return False
    
    def save_cache(self) -> bool:
        """
        Save earnings cache to JSON file.
        
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.earnings_cache, f, indent=2)
            return True
        
        except IOError as e:
            print(f"   ⚠️  Error saving earnings cache: {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, any]:
        """
        Get statistics about earnings cache.
        
        Returns:
            Dictionary with cache statistics
        """
        if not self.earnings_cache:
            return {
                "total_symbols": 0,
                "oldest_update": None,
                "newest_update": None
            }
        
        dates = []
        for data in self.earnings_cache.values():
            if "last_updated" in data:
                dates.append(datetime.fromisoformat(data["last_updated"]))
        
        return {
            "total_symbols": len(self.earnings_cache),
            "oldest_update": min(dates).strftime("%Y-%m-%d") if dates else None,
            "newest_update": max(dates).strftime("%Y-%m-%d") if dates else None
        }
    
    def add_manual_earnings(self, symbol: str, earnings_date: str) -> None:
        """
        Manually add earnings date for a symbol.
        Useful for testing or when API is unavailable.
        
        Args:
            symbol: Stock symbol
            earnings_date: Earnings date as "YYYY-MM-DD"
        """
        self.earnings_cache[symbol] = {
            "next_earnings": earnings_date,
            "last_updated": datetime.now().isoformat()
        }
        self.save_cache()
        print(f"   ✅ Manually added earnings date for {symbol}: {earnings_date}")
    
    def get_upcoming_earnings(self, days: int = 7) -> List[Tuple[str, str]]:
        """
        Get list of symbols with earnings in next N days.
        
        Args:
            days: Number of days to look ahead
        
        Returns:
            List of (symbol, earnings_date) tuples
        """
        upcoming = []
        today = datetime.now()
        cutoff = today + timedelta(days=days)
        
        for symbol, data in self.earnings_cache.items():
            earnings_date_str = data.get("next_earnings")
            if earnings_date_str:
                try:
                    earnings_date = datetime.strptime(earnings_date_str, "%Y-%m-%d")
                    if today <= earnings_date <= cutoff:
                        upcoming.append((symbol, earnings_date_str))
                except ValueError:
                    pass
        
        # Sort by date
        upcoming.sort(key=lambda x: x[1])
        return upcoming


# =============================================================================
# TESTING FUNCTIONS
# =============================================================================

def test_blackout_window():
    """Test earnings blackout window logic."""
    print("\n" + "="*70)
    print("TEST 1: Blackout Window Logic")
    print("="*70)
    
    ef = EarningsFilter(cache_file="test_earnings_cache.json")
    
    # Mock earnings date: 5 days from now
    future_date = datetime.now() + timedelta(days=5)
    earnings_date = future_date.strftime("%Y-%m-%d")
    
    ef.add_manual_earnings("AAPL", earnings_date)
    
    # Should be in blackout (T-3 to T+2, earnings in 5 days)
    assert not ef.is_earnings_week("AAPL"), "Should NOT be in blackout (earnings in 5 days)"
    print(f"✅ Earnings in 5 days: NOT in blackout")
    
    # Mock earnings date: 2 days from now
    near_date = datetime.now() + timedelta(days=2)
    earnings_date = near_date.strftime("%Y-%m-%d")
    
    ef.add_manual_earnings("TSLA", earnings_date)
    
    # Should be in blackout
    assert ef.is_earnings_week("TSLA"), "Should be in blackout (earnings in 2 days)"
    print(f"✅ Earnings in 2 days: IN BLACKOUT")
    
    # Mock past earnings: 1 day ago
    past_date = datetime.now() - timedelta(days=1)
    earnings_date = past_date.strftime("%Y-%m-%d")
    
    ef.add_manual_earnings("NVDA", earnings_date)
    
    # Should still be in blackout (T+2)
    assert ef.is_earnings_week("NVDA"), "Should be in blackout (earnings 1 day ago)"
    print(f"✅ Earnings 1 day ago: IN BLACKOUT (T+2)")
    
    # Mock old earnings: 5 days ago
    old_date = datetime.now() - timedelta(days=5)
    earnings_date = old_date.strftime("%Y-%m-%d")
    
    ef.add_manual_earnings("GOOGL", earnings_date)
    
    # Should NOT be in blackout
    assert not ef.is_earnings_week("GOOGL"), "Should NOT be in blackout (earnings 5 days ago)"
    print(f"✅ Earnings 5 days ago: NOT in blackout")
    
    print("\n✅ Blackout window tests passed!")


def test_should_block_signal():
    """Test main filtering function."""
    print("\n" + "="*70)
    print("TEST 2: Signal Blocking")
    print("="*70)
    
    ef = EarningsFilter(cache_file="test_earnings_cache.json")
    
    # Add test earnings dates
    near_earnings = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
    far_earnings = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
    
    ef.add_manual_earnings("BLOCK_ME", near_earnings)
    ef.add_manual_earnings("ALLOW_ME", far_earnings)
    
    # Test blocking
    assert ef.should_block_signal("BLOCK_ME"), "Should block signal"
    print("✅ Near earnings: Signal BLOCKED")
    
    assert not ef.should_block_signal("ALLOW_ME"), "Should allow signal"
    print("✅ Far earnings: Signal ALLOWED")
    
    # No earnings data - should allow (fail open)
    assert not ef.should_block_signal("UNKNOWN"), "Should allow when no data"
    print("✅ No earnings data: Signal ALLOWED (fail open)")
    
    print("\n✅ Signal blocking tests passed!")


def test_cache_persistence():
    """Test cache persistence."""
    print("\n" + "="*70)
    print("TEST 3: Cache Persistence")
    print("="*70)
    
    # Create first instance and clear existing cache
    ef1 = EarningsFilter(cache_file="test_earnings_cache.json")
    ef1.earnings_cache = {}  # Clear any existing data
    ef1.save_cache()
    print("   🧹 Cleared existing cache")
    
    # Add fresh test data
    ef1.add_manual_earnings("AAPL", "2025-11-05")
    ef1.add_manual_earnings("TSLA", "2025-11-10")
    
    # Create second instance and verify cache loaded
    ef2 = EarningsFilter(cache_file="test_earnings_cache.json")
    
    assert "AAPL" in ef2.earnings_cache, "Cache should persist"
    assert "TSLA" in ef2.earnings_cache, "Cache should persist"
    print("✅ Cache persisted across instances")
    
    # Check stats
    stats = ef2.get_cache_stats()
    assert stats["total_symbols"] == 2, "Should have exactly 2 symbols"
    print(f"✅ Cache stats: {stats['total_symbols']} symbols")
    
    print("\n✅ Cache persistence tests passed!")


def test_upcoming_earnings():
    """Test upcoming earnings listing."""
    print("\n" + "="*70)
    print("TEST 4: Upcoming Earnings List")
    print("="*70)
    
    ef = EarningsFilter(cache_file="test_earnings_cache.json")
    
    # Add various earnings dates
    ef.add_manual_earnings("SOON", (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d"))
    ef.add_manual_earnings("MEDIUM", (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d"))
    ef.add_manual_earnings("LATER", (datetime.now() + timedelta(days=20)).strftime("%Y-%m-%d"))
    
    # Get earnings in next 7 days
    upcoming = ef.get_upcoming_earnings(days=7)
    
    assert len(upcoming) == 2, "Should find 2 earnings in next 7 days"
    print(f"✅ Found {len(upcoming)} earnings in next 7 days:")
    for symbol, date in upcoming:
        print(f"   • {symbol}: {date}")
    
    print("\n✅ Upcoming earnings tests passed!")


def run_all_tests():
    """Run complete test suite."""
    print("\n" + "="*70)
    print("EARNINGS FILTER TEST SUITE")
    print("="*70)
    
    test_blackout_window()
    test_should_block_signal()
    test_cache_persistence()
    test_upcoming_earnings()
    
    # Cleanup test file
    import os
    if os.path.exists("cache/test_earnings_cache.json"):
        os.remove("cache/test_earnings_cache.json")
        print("\n🧹 Cleaned up test files")
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED!")
    print("="*70)


# =============================================================================
# INTEGRATION EXAMPLE
# =============================================================================

def integration_example():
    """
    Example of how to integrate with scanner/hourly_scanner.py
    """
    print("\n" + "="*70)
    print("INTEGRATION EXAMPLE")
    print("="*70)
    
    # Initialize in main.py
    earnings_filter = EarningsFilter(api_key="your_api_key_here")
    
    # In scanning loop
    symbol = "AAPL"
    
    print(f"\n📊 Processing {symbol}...")
    
    # Check earnings filter BEFORE generating signal
    if earnings_filter.should_block_signal(symbol):
        print(f"   ⏸️  Signal suppressed - earnings blackout active")
    else:
        print(f"   ✅ Earnings check passed - proceed with signal")
        # Continue with pattern detection, zone analysis, etc.
    
    # Weekly maintenance (Sunday)
    print(f"\n🔄 Weekly Cache Refresh:")
    symbols = ["AAPL", "TSLA", "NVDA", "GOOGL", "MSFT"]
    earnings_filter.refresh_cache(symbols, max_requests=10)
    
    # Check upcoming earnings
    upcoming = earnings_filter.get_upcoming_earnings(days=7)
    if upcoming:
        print(f"\n📅 Upcoming Earnings (Next 7 Days):")
        for symbol, date in upcoming:
            print(f"   • {symbol}: {date}")


if __name__ == "__main__":
    # Run tests
    run_all_tests()
    
    # Show integration example
    integration_example()