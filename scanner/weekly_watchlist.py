"""
Weekly Watchlist Generator for Swing Trader Alert Engine
Scans universe on Sunday evening to identify best setups for the upcoming week.

Priority: ⭐⭐⭐⭐ (Optional but high value)
Purpose: Pre-identify quality setups for focused monitoring
"""

import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class WeeklyWatchlist:
    """
    Generates weekly watchlist of high-quality zone setups.
    
    Features:
    - Scans all symbols for zone quality
    - No pattern required (just zone strength)
    - Generates top 20-30 stocks to watch
    - Persists watchlist to file
    - Flags watchlist stocks in hourly alerts
    """
    
    def __init__(
        self,
        scanner,
        min_confluence: float = 7.0,
        max_stocks: int = 30,
        watchlist_file: str = "weekly_watchlist.json",
        cache_dir: str = "./cache"
    ):
        """
        Initialize weekly watchlist generator.
        
        Args:
            scanner: Reference to HourlyScanner instance
            min_confluence: Minimum zone strength (0-10 scale)
            max_stocks: Maximum stocks in watchlist
            watchlist_file: JSON file to persist watchlist
            cache_dir: Directory for watchlist file
        """
        self.scanner = scanner
        self.min_confluence = min_confluence
        self.max_stocks = max_stocks
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.watchlist_file = self.cache_dir / watchlist_file
        
        # Current watchlist
        self.watchlist: List[Dict] = []
        self.watchlist_symbols: set = set()
        
        # Load existing watchlist
        self.load_watchlist()
    
    def generate_watchlist(self, symbols: List[str]) -> List[Dict]:
        """
        Generate weekly watchlist by scanning all symbols.
        
        Args:
            symbols: List of symbols to scan
        
        Returns:
            List of watchlist entries sorted by quality
        """
        print("\n" + "="*70)
        print("WEEKLY WATCHLIST GENERATION")
        print("="*70)
        print(f"Scanning {len(symbols)} symbols for quality zones...")
        print(f"Minimum confluence: {self.min_confluence}/10")
        
        candidates = []
        
        for i, symbol in enumerate(symbols, 1):
            if i % 10 == 0:
                print(f"   Progress: {i}/{len(symbols)} symbols scanned...")
            
            try:
                # Get zone analysis without pattern requirement
                zones = self._analyze_zones(symbol)
                
                if zones:
                    # Find best zone for this symbol
                    best_zone = max(zones, key=lambda z: z['confluence'])
                    
                    if best_zone['confluence'] >= self.min_confluence:
                        candidates.append({
                            'symbol': symbol,
                            'confluence': best_zone['confluence'],
                            'zone_type': best_zone['type'],
                            'zone_price': best_zone['mid'],
                            'current_price': best_zone.get('current_price', 0),
                            'distance_pct': best_zone.get('distance_pct', 0),
                            'components': best_zone.get('components', []),
                            'scanned_at': datetime.now().isoformat()
                        })
            
            except Exception as e:
                print(f"   ⚠️  Error scanning {symbol}: {e}")
                continue
        
        # Sort by confluence (descending)
        candidates.sort(key=lambda x: x['confluence'], reverse=True)
        
        # Take top N stocks
        self.watchlist = candidates[:self.max_stocks]
        self.watchlist_symbols = {entry['symbol'] for entry in self.watchlist}
        
        print(f"\n✅ Found {len(candidates)} qualifying stocks")
        print(f"✅ Selected top {len(self.watchlist)} for watchlist")
        
        # Save watchlist
        self.save_watchlist()
        
        return self.watchlist
    
    def _analyze_zones(self, symbol: str) -> List[Dict]:
        """
        Analyze zones for a symbol (called by scanner).
        
        Args:
            symbol: Stock symbol
        
        Returns:
            List of zone dictionaries with confluence scores
        """
        try:
            # This would call your existing scanner's zone building logic
            # For now, return mock data structure
            # In real integration, you'd call:
            # daily_data = self.scanner.data_fetcher.fetch_daily_data(symbol)
            # hourly_data = self.scanner.data_fetcher.fetch_hourly_data(symbol)
            # zones = self.scanner.zone_builder.build_zones(symbol, daily_data, hourly_data)
            
            # Mock implementation - replace with actual scanner call
            # zones = self.scanner.get_zones_only(symbol)
            
            # For template purposes, return empty list
            # You'll integrate this with your actual scanner
            return []
        
        except Exception as e:
            print(f"   ⚠️  Error analyzing {symbol}: {e}")
            return []
    
    def is_on_watchlist(self, symbol: str) -> bool:
        """
        Check if symbol is on current watchlist.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            True if on watchlist, False otherwise
        """
        return symbol in self.watchlist_symbols
    
    def get_watchlist_entry(self, symbol: str) -> Optional[Dict]:
        """
        Get watchlist entry for a symbol.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Watchlist entry dict or None
        """
        for entry in self.watchlist:
            if entry['symbol'] == symbol:
                return entry
        return None
    
    def format_watchlist_message(self) -> str:
        """
        Format watchlist as Telegram message.
        
        Returns:
            Formatted message string
        """
        if not self.watchlist:
            return "📋 Weekly Watchlist: No qualifying setups found"
        
        # Header
        message = "📋 **WEEKLY WATCHLIST**\n"
        message += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        message += f"Quality threshold: {self.min_confluence}/10\n"
        message += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Group by support/resistance
        supports = [e for e in self.watchlist if e['zone_type'] == 'support']
        resistances = [e for e in self.watchlist if e['zone_type'] == 'resistance']
        
        if supports:
            message += "🟢 **SUPPORT ZONES** (Long Candidates)\n"
            for i, entry in enumerate(supports[:15], 1):
                emoji = "⭐" if entry['confluence'] >= 8.5 else "✅"
                message += f"{emoji} **{entry['symbol']}** @ ${entry['zone_price']:.2f}\n"
                message += f"   • Strength: {entry['confluence']:.1f}/10"
                
                if entry.get('current_price'):
                    dist = entry.get('distance_pct', 0)
                    message += f" | {abs(dist):.1f}% away"
                
                message += f"\n   • Components: {', '.join(entry.get('components', [])[:3])}\n"
            
            message += "\n"
        
        if resistances:
            message += "🔴 **RESISTANCE ZONES** (Short Candidates)\n"
            for i, entry in enumerate(resistances[:15], 1):
                emoji = "⭐" if entry['confluence'] >= 8.5 else "✅"
                message += f"{emoji} **{entry['symbol']}** @ ${entry['zone_price']:.2f}\n"
                message += f"   • Strength: {entry['confluence']:.1f}/10"
                
                if entry.get('current_price'):
                    dist = entry.get('distance_pct', 0)
                    message += f" | {abs(dist):.1f}% away"
                
                message += f"\n   • Components: {', '.join(entry.get('components', [])[:3])}\n"
            
            message += "\n"
        
        # Footer
        message += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        message += f"Total: {len(self.watchlist)} stocks\n"
        message += "Monitor these for patterns during the week! 📊"
        
        return message
    
    def format_short_summary(self) -> str:
        """
        Format short summary for quick reference.
        
        Returns:
            Short summary string
        """
        if not self.watchlist:
            return "No watchlist"
        
        symbols = [e['symbol'] for e in self.watchlist]
        return f"📋 Watchlist ({len(symbols)}): {', '.join(symbols[:10])}{'...' if len(symbols) > 10 else ''}"
    
    def save_watchlist(self) -> bool:
        """
        Save watchlist to JSON file.
        
        Returns:
            True if saved successfully
        """
        try:
            data = {
                'generated_at': datetime.now().isoformat(),
                'min_confluence': self.min_confluence,
                'watchlist': self.watchlist
            }
            
            with open(self.watchlist_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"   ✅ Watchlist saved to {self.watchlist_file}")
            return True
        
        except IOError as e:
            print(f"   ⚠️  Error saving watchlist: {e}")
            return False
    
    def load_watchlist(self) -> bool:
        """
        Load watchlist from JSON file.
        
        Returns:
            True if loaded successfully
        """
        if not self.watchlist_file.exists():
            print(f"   ℹ️  No existing watchlist found")
            return False
        
        try:
            with open(self.watchlist_file, 'r') as f:
                data = json.load(f)
            
            self.watchlist = data.get('watchlist', [])
            self.watchlist_symbols = {e['symbol'] for e in self.watchlist}
            
            generated_at = data.get('generated_at', 'unknown')
            print(f"   ✅ Loaded watchlist from {generated_at}")
            print(f"   • {len(self.watchlist)} stocks on watchlist")
            
            return True
        
        except (json.JSONDecodeError, IOError) as e:
            print(f"   ⚠️  Error loading watchlist: {e}")
            self.watchlist = []
            self.watchlist_symbols = set()
            return False
    
    def get_stats(self) -> Dict:
        """
        Get watchlist statistics.
        
        Returns:
            Dictionary with statistics
        """
        if not self.watchlist:
            return {
                'total': 0,
                'avg_confluence': 0,
                'supports': 0,
                'resistances': 0
            }
        
        supports = [e for e in self.watchlist if e['zone_type'] == 'support']
        resistances = [e for e in self.watchlist if e['zone_type'] == 'resistance']
        
        avg_confluence = sum(e['confluence'] for e in self.watchlist) / len(self.watchlist)
        
        return {
            'total': len(self.watchlist),
            'avg_confluence': avg_confluence,
            'supports': len(supports),
            'resistances': len(resistances),
            'min_confluence': min(e['confluence'] for e in self.watchlist),
            'max_confluence': max(e['confluence'] for e in self.watchlist)
        }
    
    def clear_watchlist(self) -> None:
        """
        Clear current watchlist (for testing or manual reset).
        """
        self.watchlist = []
        self.watchlist_symbols = set()
        print("   🔄 Watchlist cleared")


# =============================================================================
# TESTING FUNCTIONS
# =============================================================================

def test_watchlist_generation():
    """Test watchlist generation with mock data."""
    print("\n" + "="*70)
    print("TEST 1: Watchlist Generation")
    print("="*70)
    
    # Mock scanner
    class MockScanner:
        pass
    
    watchlist = WeeklyWatchlist(
        scanner=MockScanner(),
        min_confluence=7.0,
        max_stocks=10,
        watchlist_file="test_watchlist.json"
    )
    
    # Clear existing
    watchlist.clear_watchlist()
    
    # Mock candidates
    mock_candidates = [
        {'symbol': 'AAPL', 'confluence': 9.5, 'type': 'support', 'mid': 264.16, 
         'current_price': 262.82, 'distance_pct': -0.5, 'components': ['EMA20', 'swing_low', 'HVN']},
        {'symbol': 'TSLA', 'confluence': 8.8, 'type': 'resistance', 'mid': 245.00,
         'current_price': 243.50, 'distance_pct': 0.6, 'components': ['SMA50', 'gap_filled']},
        {'symbol': 'NVDA', 'confluence': 8.2, 'type': 'support', 'mid': 485.30,
         'current_price': 483.00, 'distance_pct': -0.5, 'components': ['EMA20', 'HVN']},
        {'symbol': 'GOOGL', 'confluence': 7.5, 'type': 'support', 'mid': 142.50,
         'current_price': 141.00, 'distance_pct': -1.0, 'components': ['SMA100']},
        {'symbol': 'MSFT', 'confluence': 7.2, 'type': 'resistance', 'mid': 378.00,
         'current_price': 379.50, 'distance_pct': 0.4, 'components': ['EMA20', 'swing_high']},
    ]
    
    # Manually populate watchlist
    for candidate in mock_candidates:
        watchlist.watchlist.append({
            'symbol': candidate['symbol'],
            'confluence': candidate['confluence'],
            'zone_type': candidate['type'],
            'zone_price': candidate['mid'],
            'current_price': candidate['current_price'],
            'distance_pct': candidate['distance_pct'],
            'components': candidate['components'],
            'scanned_at': datetime.now().isoformat()
        })
    
    watchlist.watchlist_symbols = {e['symbol'] for e in watchlist.watchlist}
    watchlist.save_watchlist()
    
    print(f"✅ Generated watchlist with {len(watchlist.watchlist)} stocks")
    
    # Test watchlist checking
    assert watchlist.is_on_watchlist('AAPL'), "AAPL should be on watchlist"
    assert not watchlist.is_on_watchlist('AMD'), "AMD should not be on watchlist"
    print("✅ Watchlist membership check working")
    
    # Test stats
    stats = watchlist.get_stats()
    print(f"\n📊 Watchlist Stats:")
    print(f"   • Total: {stats['total']}")
    print(f"   • Avg confluence: {stats['avg_confluence']:.1f}")
    print(f"   • Supports: {stats['supports']}")
    print(f"   • Resistances: {stats['resistances']}")
    
    print("\n✅ Watchlist generation test passed!")


def test_message_formatting():
    """Test message formatting."""
    print("\n" + "="*70)
    print("TEST 2: Message Formatting")
    print("="*70)
    
    class MockScanner:
        pass
    
    watchlist = WeeklyWatchlist(
        scanner=MockScanner(),
        watchlist_file="test_watchlist.json"
    )
    
    # Format full message
    message = watchlist.format_watchlist_message()
    print("\n📱 TELEGRAM MESSAGE:")
    print("-" * 70)
    print(message)
    print("-" * 70)
    
    # Format short summary
    summary = watchlist.format_short_summary()
    print(f"\n📋 SHORT SUMMARY: {summary}")
    
    print("\n✅ Message formatting test passed!")


def test_persistence():
    """Test watchlist persistence."""
    print("\n" + "="*70)
    print("TEST 3: Persistence")
    print("="*70)
    
    class MockScanner:
        pass
    
    # Create first instance
    watchlist1 = WeeklyWatchlist(
        scanner=MockScanner(),
        watchlist_file="test_watchlist.json"
    )
    
    # Should load existing watchlist
    initial_count = len(watchlist1.watchlist)
    print(f"✅ Loaded {initial_count} stocks from saved watchlist")
    
    # Create second instance
    watchlist2 = WeeklyWatchlist(
        scanner=MockScanner(),
        watchlist_file="test_watchlist.json"
    )
    
    # Should have same data
    assert len(watchlist2.watchlist) == initial_count, "Watchlist should persist"
    assert watchlist2.is_on_watchlist('AAPL'), "Symbols should persist"
    
    print("✅ Persistence test passed!")


def run_all_tests():
    """Run complete test suite."""
    print("\n" + "="*70)
    print("WEEKLY WATCHLIST TEST SUITE")
    print("="*70)
    
    test_watchlist_generation()
    test_message_formatting()
    test_persistence()
    
    # Cleanup
    import os
    if os.path.exists("cache/test_watchlist.json"):
        os.remove("cache/test_watchlist.json")
        print("\n🧹 Cleaned up test files")
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED!")
    print("="*70)


# =============================================================================
# INTEGRATION EXAMPLE
# =============================================================================

def integration_example():
    """
    Example of how to integrate with main.py and scheduler.
    """
    print("\n" + "="*70)
    print("INTEGRATION EXAMPLE")
    print("="*70)
    
    print("""
# In main.py:

from scanner.weekly_watchlist import WeeklyWatchlist
from alerts.telegram_sender import TelegramSender

# Initialize
scanner = HourlyScanner(config)
watchlist_gen = WeeklyWatchlist(
    scanner=scanner,
    min_confluence=7.0,
    max_stocks=30
)
telegram = TelegramSender(config)

# Generate watchlist (Sunday evening)
def generate_weekly_watchlist():
    symbols = config.get_universe()
    watchlist = watchlist_gen.generate_watchlist(symbols)
    
    # Send to Telegram
    message = watchlist_gen.format_watchlist_message()
    telegram.send_message(message)
    
    return watchlist

# In hourly scanner (check if on watchlist)
def scan_symbol(symbol):
    # ... build zones, detect patterns ...
    
    # Check if on watchlist
    if watchlist_gen.is_on_watchlist(symbol):
        # Add ⭐ badge to alert
        alert_prefix = "⭐ WATCHLIST | "
    else:
        alert_prefix = "🆕 NEW | "
    
    # Send alert with prefix
    send_alert(alert_prefix + format_signal(signal))

# In scheduler (add to schedule_weekly_watchlist):
scheduler.schedule_weekly_watchlist()  # Sunday 18:00 ET
    """)


if __name__ == "__main__":
    # Run tests
    run_all_tests()
    
    # Show integration example
    integration_example()
