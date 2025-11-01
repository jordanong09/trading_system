"""
Weekly Watchlist Generator for Swing Trader Alert Engine
Scans universe on Sunday evening to identify best setups for the upcoming week.

FULLY INTEGRATED VERSION - Uses scanner infrastructure with caching
"""

import json
from datetime import datetime
from typing import List, Dict, Optional
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
    - Uses cache to minimize API calls
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
        print(f"Using cache: ✅ (reduces API calls)")
        
        candidates = []
        processed = 0
        errors = 0
        
        for i, symbol in enumerate(symbols, 1):
            # Progress update every 10 symbols
            if i % 10 == 0:
                print(f"   Progress: {i}/{len(symbols)} symbols scanned... "
                      f"({processed} qualified, {errors} errors)")
            
            try:
                # Get zone analysis with scanner integration
                zones = self._analyze_zones(symbol)
                
                if zones:
                    # Find best zone for this symbol
                    best_zone = max(zones, key=lambda z: z['strength'])
                    
                    if best_zone['strength'] >= self.min_confluence:
                        candidates.append({
                            'symbol': symbol,
                            'confluence': best_zone['strength'],
                            'zone_type': best_zone['type'],
                            'zone_price': best_zone['mid'],
                            'current_price': best_zone.get('current_price', 0),
                            'distance_pct': best_zone.get('distance_pct', 0),
                            'components': best_zone.get('components', []),
                            'scanned_at': datetime.now().isoformat()
                        })
                        processed += 1
            
            except Exception as e:
                errors += 1
                if errors <= 5:  # Only show first 5 errors
                    print(f"   ⚠️  Error scanning {symbol}: {str(e)[:60]}")
        
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
        Analyze zones for a symbol using scanner's infrastructure.
        
        This is the key integration point - uses existing scanner components
        with caching to minimize API calls.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            List of zone dictionaries with confluence scores
        """
        try:
            # Import here to avoid circular imports
            from indicators.technical_indicators import TechnicalIndicators
            
            # Step 1: Fetch daily data (uses cache if available)
            daily_df = self.scanner.cache_mgr.get_or_fetch_daily(
                symbol,
                lambda s: self.scanner.api.fetch_daily_data(s)
            )
            
            if daily_df is None or len(daily_df) < 60:
                return []
            
            # Step 2: Calculate indicators
            indicators = TechnicalIndicators.calculate_all_indicators(daily_df)
            
            if indicators.get('error'):
                return []
            
            current_price = indicators['current_price']
            atr = indicators['atr14d']
            
            # Add missing indicator fields that zone_engine expects
            if 'round_number' not in indicators:
                round_numbers = []
                for base in [5, 10, 25, 50, 100]:
                    rounded = round(current_price / base) * base
                    if abs(rounded - current_price) <= current_price * 0.1:
                        round_numbers.append(rounded)
                indicators['round_number'] = sorted(set(round_numbers)) if round_numbers else []
            
            for field in ['swing_highs', 'swing_lows', 'gap_edges', 'hvn', 'lvn']:
                if field not in indicators:
                    indicators[field] = []
            
            # Step 3: Check if zones are already cached (< 24 hours old)
            zones = self.scanner.cache_mgr.load_cached_zones(symbol, max_age_hours=24)
            
            if not zones:
                # Cache miss - fetch hourly data and build zones
                hourly_df = self.scanner.cache_mgr.get_or_fetch_hourly(
                    symbol,
                    lambda s: self.scanner.api.fetch_hourly_data(s)
                )
                
                if hourly_df is None:
                    return []
                
                # Build zones using scanner's zone engine
                zones = self.scanner.zone_engine.build_zones(
                    symbol=symbol,
                    indicators=indicators,
                    current_price=current_price,
                    atr=atr,
                    hourly_df=hourly_df
                )
                
                # Cache zones for future use (saves API calls)
                if zones:
                    self.scanner.cache_mgr.save_zones(symbol, zones)
            
            # Step 4: Filter zones within reasonable distance
            # For watchlist, we want zones that are tradeable soon
            max_distance_atr = 1.0  # Within 1 ATR of current price
            
            nearby_zones = []
            for zone in zones:
                distance_atr = abs(zone['mid'] - current_price) / atr if atr > 0 else 999
                
                if distance_atr <= max_distance_atr:
                    # Enhance zone with current price context
                    zone['current_price'] = current_price
                    zone['distance_pct'] = ((zone['mid'] - current_price) / current_price) * 100
                    zone['distance_atr'] = distance_atr
                    nearby_zones.append(zone)
            
            return nearby_zones
        
        except Exception as e:
            # Silently fail for individual stocks
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
        message += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
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
                
                # Show top 3 components
                components = entry.get('components', [])[:3]
                if components:
                    message += f"\n   • Components: {', '.join(components)}\n"
                else:
                    message += "\n"
            
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
                
                # Show top 3 components
                components = entry.get('components', [])[:3]
                if components:
                    message += f"\n   • Components: {', '.join(components)}\n"
                else:
                    message += "\n"
            
            message += "\n"
        
        # Footer
        message += "━━━━━━━━━━━━━━━━━━━━━━━\n"
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
            return False
        
        try:
            with open(self.watchlist_file, 'r') as f:
                data = json.load(f)
            
            self.watchlist = data.get('watchlist', [])
            self.watchlist_symbols = {e['symbol'] for e in self.watchlist}
            
            generated_at = data.get('generated_at', 'unknown')
            if self.watchlist:
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
# STANDALONE GENERATION SCRIPT
# =============================================================================

def generate_weekly_watchlist_standalone():
    """
    Standalone function to generate watchlist.
    Can be called from main.py or run directly.
    """
    import config
    from scanner.hourly_scanner import Scanner
    
    print("\n" + "="*70)
    print("📋 WEEKLY WATCHLIST GENERATOR")
    print("="*70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Initialize scanner
    print("🔧 Initializing scanner...")
    scanner = Scanner({
        'ALPHA_VANTAGE_API_KEY': config.ALPHA_VANTAGE_API_KEY,
        'TELEGRAM_BOT_TOKEN': config.TELEGRAM_BOT_TOKEN,
        'TELEGRAM_CHAT_ID': config.TELEGRAM_CHAT_ID,
        'CACHE_DIRECTORY': config.CACHE_DIRECTORY,
        'ZONE_CONFIG': config.ZONE_CONFIG,
        'COMPONENT_WEIGHTS': config.COMPONENT_WEIGHTS,
        'CONFLUENCE_THRESHOLDS': config.CONFLUENCE_THRESHOLDS,
        'RV_REQUIREMENTS': config.RV_REQUIREMENTS,
        'WEEKLY_WATCHLIST': config.WEEKLY_WATCHLIST
    })
    
    # Check if watchlist module is enabled
    if not scanner.watchlist_gen:
        print("❌ Weekly watchlist not enabled in config.py")
        print("   Set WEEKLY_WATCHLIST['enabled'] = True")
        return None
    
    # Get stock universe
    from main import get_stock_universe
    symbols = get_stock_universe()
    
    print(f"📊 Stock universe: {len(symbols)} symbols")
    print(f"   Min confluence: {config.WEEKLY_WATCHLIST['min_confluence']}/10")
    print(f"   Max stocks: {config.WEEKLY_WATCHLIST['max_stocks']}")
    print(f"   Cache enabled: ✅ (24-hour expiry)\n")
    
    # Estimate API calls
    print(f"💡 Estimated API calls:")
    print(f"   If cache empty: ~{len(symbols) * 2} calls (daily + hourly)")
    print(f"   If cache valid: ~0 calls (uses cached data)")
    print()
    
    # Generate watchlist
    watchlist = scanner.watchlist_gen.generate_watchlist(symbols)
    
    if watchlist:
        # Display formatted message
        message = scanner.watchlist_gen.format_watchlist_message()
        print("\n" + "="*70)
        print("📋 WATCHLIST PREVIEW")
        print("="*70)
        print(message)
        print("="*70)
        
        # Show statistics
        stats = scanner.watchlist_gen.get_stats()
        print(f"\n📊 STATISTICS:")
        print(f"   Total stocks: {stats['total']}")
        print(f"   Avg confluence: {stats['avg_confluence']:.1f}/10")
        print(f"   Support setups: {stats['supports']}")
        print(f"   Resistance setups: {stats['resistances']}")
        print(f"   Best confluence: {stats['max_confluence']:.1f}/10")
        print(f"   Weakest confluence: {stats['min_confluence']:.1f}/10")
        
        # Offer to send to Telegram
        if scanner.telegram.is_configured():
            print()
            response = input("📤 Send watchlist to Telegram? (y/n): ")
            if response.lower() == 'y':
                success = scanner.telegram._send_regular_message(message)
                if success:
                    print("   ✅ Watchlist sent to Telegram!")
                else:
                    print("   ❌ Failed to send to Telegram")
        else:
            print("\n⚠️  Telegram not configured - watchlist saved locally only")
        
        return watchlist
    else:
        print("\n⚠️  No stocks met the quality threshold")
        print("   Try lowering min_confluence in config.py")
        return None


if __name__ == "__main__":
    generate_weekly_watchlist_standalone()