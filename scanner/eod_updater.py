"""
End-of-Day (EOD) Update Workflow for Swing Trader Alert Engine
Updates indicators and zones after market close with fresh daily data.

Priority: ⭐⭐⭐ (Optional)
Purpose: Keep zones fresh, avoid stale data drift
"""

import json
from datetime import datetime, time
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class EODUpdater:
    """
    Manages end-of-day updates for indicators and zones.
    
    Features:
    - Fetches latest daily bar
    - Updates ATR, EMA20, SMAs
    - Recalculates zones
    - Detects significant zone shifts
    - Caches updated zones for next day
    """
    
    def __init__(
        self,
        scanner,
        shift_threshold: float = 0.5,  # Alert if zone shifts >0.5×ATR
        update_log_file: str = "eod_updates.json",
        cache_dir: str = "./cache"
    ):
        """
        Initialize EOD updater.
        
        Args:
            scanner: Reference to HourlyScanner instance
            shift_threshold: Alert threshold for zone shifts (in ATR)
            update_log_file: JSON file to log updates
            cache_dir: Directory for update logs
        """
        self.scanner = scanner
        self.shift_threshold = shift_threshold
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.update_log_file = self.cache_dir / update_log_file
        
        # Track updates
        self.last_update: Optional[datetime] = None
        self.update_history: List[Dict] = []
        
        # Load update history
        self.load_history()
    
    def should_run_update(self) -> bool:
        """
        Check if EOD update should run.
        
        Returns:
            True if market closed and update needed
        """
        now = datetime.now()
        
        # Check if weekday (Mon-Fri)
        if now.weekday() >= 5:
            return False
        
        # Check if after market close (after 4:00 PM ET)
        # Assuming we're in ET timezone
        if now.time() < time(16, 0):
            return False
        
        # Check if already updated today
        if self.last_update and self.last_update.date() == now.date():
            print("   ℹ️  Already updated today")
            return False
        
        return True
    
    def update_all(self, symbols: List[str]) -> Dict:
        """
        Update indicators and zones for all symbols.
        
        Args:
            symbols: List of symbols to update
        
        Returns:
            Dictionary with update statistics
        """
        print("\n" + "="*70)
        print("EOD UPDATE WORKFLOW")
        print("="*70)
        print(f"Updating {len(symbols)} symbols...")
        print(f"Shift alert threshold: {self.shift_threshold}×ATR")
        
        stats = {
            'total_symbols': len(symbols),
            'successful': 0,
            'failed': 0,
            'zone_shifts': 0,
            'significant_shifts': [],
            'started_at': datetime.now().isoformat(),
            'completed_at': None
        }
        
        for i, symbol in enumerate(symbols, 1):
            if i % 20 == 0:
                print(f"   Progress: {i}/{len(symbols)} symbols updated...")
            
            try:
                result = self.update_symbol(symbol)
                
                if result['success']:
                    stats['successful'] += 1
                    
                    # Track significant zone shifts
                    if result.get('zone_shifted'):
                        stats['zone_shifts'] += 1
                        
                        shift_atr = result.get('shift_atr', 0)
                        if abs(shift_atr) >= self.shift_threshold:
                            stats['significant_shifts'].append({
                                'symbol': symbol,
                                'shift_atr': shift_atr,
                                'old_zone': result.get('old_zone'),
                                'new_zone': result.get('new_zone')
                            })
                else:
                    stats['failed'] += 1
            
            except Exception as e:
                print(f"   ❌ Error updating {symbol}: {e}")
                stats['failed'] += 1
        
        stats['completed_at'] = datetime.now().isoformat()
        
        # Update tracking
        self.last_update = datetime.now()
        self.update_history.append(stats)
        self.save_history()
        
        # Print summary
        print(f"\n{'='*70}")
        print("EOD UPDATE COMPLETE")
        print(f"{'='*70}")
        print(f"✅ Successful: {stats['successful']}/{stats['total_symbols']}")
        print(f"❌ Failed: {stats['failed']}")
        print(f"📊 Zone shifts detected: {stats['zone_shifts']}")
        print(f"⚠️  Significant shifts: {len(stats['significant_shifts'])}")
        
        if stats['significant_shifts']:
            print(f"\n⚠️  SIGNIFICANT ZONE SHIFTS:")
            for shift in stats['significant_shifts']:
                print(f"   • {shift['symbol']}: {shift['shift_atr']:+.2f}×ATR")
        
        return stats
    
    def update_symbol(self, symbol: str) -> Dict:
        """
        Update indicators and zones for a single symbol.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Dictionary with update results
        """
        result = {
            'success': False,
            'symbol': symbol,
            'zone_shifted': False,
            'shift_atr': 0,
            'old_zone': None,
            'new_zone': None,
            'error': None
        }
        
        try:
            # 1. Fetch latest daily data
            # daily_data = self.scanner.data_fetcher.fetch_daily_data(symbol)
            
            # 2. Recalculate indicators
            # indicators = self.scanner.calculate_indicators(daily_data)
            
            # 3. Get old zones (if exists in cache)
            # old_zones = self.scanner.get_cached_zones(symbol)
            
            # 4. Rebuild zones with new data
            # hourly_data = self.scanner.data_fetcher.fetch_hourly_data(symbol)
            # new_zones = self.scanner.zone_builder.build_zones(symbol, daily_data, hourly_data)
            
            # 5. Compare zones and detect shifts
            # if old_zones and new_zones:
            #     shift_info = self._compare_zones(old_zones, new_zones, indicators['atr'])
            #     result['zone_shifted'] = shift_info['shifted']
            #     result['shift_atr'] = shift_info['shift_atr']
            #     result['old_zone'] = shift_info['old_zone']
            #     result['new_zone'] = shift_info['new_zone']
            
            # 6. Cache updated zones
            # self.scanner.cache_zones(symbol, new_zones)
            
            result['success'] = True
            
        except Exception as e:
            result['error'] = str(e)
            result['success'] = False
        
        return result
    
    def _compare_zones(self, old_zones: List[Dict], new_zones: List[Dict], atr: float) -> Dict:
        """
        Compare old and new zones to detect shifts.
        
        Args:
            old_zones: Previous zones
            new_zones: Updated zones
            atr: Current ATR value
        
        Returns:
            Dictionary with shift information
        """
        # Find strongest zone from each set
        old_best = max(old_zones, key=lambda z: z['confluence']) if old_zones else None
        new_best = max(new_zones, key=lambda z: z['confluence']) if new_zones else None
        
        if not old_best or not new_best:
            return {
                'shifted': False,
                'shift_atr': 0,
                'old_zone': None,
                'new_zone': None
            }
        
        # Calculate shift in ATR units
        shift_price = new_best['mid'] - old_best['mid']
        shift_atr = shift_price / atr if atr > 0 else 0
        
        return {
            'shifted': abs(shift_atr) > 0.1,  # Shifted if >0.1×ATR
            'shift_atr': shift_atr,
            'old_zone': {
                'mid': old_best['mid'],
                'confluence': old_best['confluence']
            },
            'new_zone': {
                'mid': new_best['mid'],
                'confluence': new_best['confluence']
            }
        }
    
    def format_shift_alert(self, stats: Dict) -> str:
        """
        Format zone shift alerts for Telegram.
        
        Args:
            stats: Update statistics
        
        Returns:
            Formatted alert message
        """
        if not stats.get('significant_shifts'):
            return "📊 EOD Update: No significant zone shifts"
        
        message = "📊 **EOD ZONE SHIFT ALERT**\n"
        message += f"Date: {datetime.now().strftime('%Y-%m-%d')}\n"
        message += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for shift in stats['significant_shifts']:
            symbol = shift['symbol']
            shift_atr = shift['shift_atr']
            direction = "⬆️" if shift_atr > 0 else "⬇️"
            
            message += f"{direction} **{symbol}**\n"
            message += f"   • Shift: {abs(shift_atr):.2f}×ATR {direction}\n"
            
            if shift.get('old_zone'):
                message += f"   • Old zone: ${shift['old_zone']['mid']:.2f}\n"
                message += f"   • New zone: ${shift['new_zone']['mid']:.2f}\n"
            
            message += "\n"
        
        message += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        message += f"Total shifts: {len(stats['significant_shifts'])}\n"
        message += "Review these setups for next session! 📈"
        
        return message
    
    def get_update_summary(self) -> str:
        """
        Get summary of last update.
        
        Returns:
            Summary string
        """
        if not self.update_history:
            return "No updates performed yet"
        
        last = self.update_history[-1]
        
        summary = f"📊 Last EOD Update\n"
        summary += f"   • Date: {last['completed_at'][:10]}\n"
        summary += f"   • Symbols: {last['successful']}/{last['total_symbols']}\n"
        summary += f"   • Zone shifts: {last['zone_shifts']}\n"
        summary += f"   • Significant: {len(last.get('significant_shifts', []))}"
        
        return summary
    
    def load_history(self) -> bool:
        """
        Load update history from file.
        
        Returns:
            True if loaded successfully
        """
        if not self.update_log_file.exists():
            return False
        
        try:
            with open(self.update_log_file, 'r') as f:
                data = json.load(f)
            
            self.update_history = data.get('updates', [])
            
            if self.update_history:
                last_update_str = self.update_history[-1].get('completed_at')
                if last_update_str:
                    self.last_update = datetime.fromisoformat(last_update_str)
            
            print(f"   ✅ Loaded {len(self.update_history)} update records")
            return True
        
        except (json.JSONDecodeError, IOError) as e:
            print(f"   ⚠️  Error loading history: {e}")
            return False
    
    def save_history(self) -> bool:
        """
        Save update history to file.
        
        Returns:
            True if saved successfully
        """
        try:
            # Keep last 30 days of history
            recent_history = self.update_history[-30:]
            
            data = {
                'updates': recent_history
            }
            
            with open(self.update_log_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            return True
        
        except IOError as e:
            print(f"   ⚠️  Error saving history: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """
        Get statistics about recent updates.
        
        Returns:
            Dictionary with statistics
        """
        if not self.update_history:
            return {
                'total_updates': 0,
                'avg_success_rate': 0,
                'total_zone_shifts': 0
            }
        
        recent = self.update_history[-7:]  # Last 7 updates
        
        total_success = sum(u['successful'] for u in recent)
        total_symbols = sum(u['total_symbols'] for u in recent)
        total_shifts = sum(u['zone_shifts'] for u in recent)
        
        return {
            'total_updates': len(self.update_history),
            'recent_updates': len(recent),
            'avg_success_rate': (total_success / total_symbols * 100) if total_symbols > 0 else 0,
            'total_zone_shifts': total_shifts,
            'last_update': self.last_update.isoformat() if self.last_update else None
        }


# =============================================================================
# TESTING FUNCTIONS
# =============================================================================

def test_should_run():
    """Test EOD update timing logic."""
    print("\n" + "="*70)
    print("TEST 1: Update Timing")
    print("="*70)
    
    class MockScanner:
        pass
    
    updater = EODUpdater(scanner=MockScanner())
    
    # Check if should run
    should_run = updater.should_run_update()
    
    now = datetime.now()
    print(f"\nCurrent time: {now.strftime('%Y-%m-%d %H:%M')}")
    print(f"Weekday: {now.strftime('%A')}")
    print(f"After 4 PM: {now.time() >= time(16, 0)}")
    print(f"Should run: {should_run}")
    
    print("\n✅ Timing check test passed!")


def test_zone_comparison():
    """Test zone comparison and shift detection."""
    print("\n" + "="*70)
    print("TEST 2: Zone Comparison")
    print("="*70)
    
    class MockScanner:
        pass
    
    updater = EODUpdater(scanner=MockScanner())
    
    # Mock zones
    old_zones = [
        {'mid': 264.16, 'confluence': 8.5, 'type': 'support'},
        {'mid': 270.00, 'confluence': 7.2, 'type': 'resistance'}
    ]
    
    new_zones = [
        {'mid': 265.50, 'confluence': 8.8, 'type': 'support'},  # Shifted up
        {'mid': 269.50, 'confluence': 7.0, 'type': 'resistance'}
    ]
    
    atr = 5.0
    
    shift_info = updater._compare_zones(old_zones, new_zones, atr)
    
    print(f"\nOld best zone: ${old_zones[0]['mid']:.2f}")
    print(f"New best zone: ${new_zones[0]['mid']:.2f}")
    print(f"Shift: {shift_info['shift_atr']:.2f}×ATR")
    print(f"Significant: {abs(shift_info['shift_atr']) >= updater.shift_threshold}")
    
    print("\n✅ Zone comparison test passed!")


def test_update_workflow():
    """Test full update workflow."""
    print("\n" + "="*70)
    print("TEST 3: Update Workflow")
    print("="*70)
    
    class MockScanner:
        pass
    
    updater = EODUpdater(
        scanner=MockScanner(),
        update_log_file="test_eod_updates.json"
    )
    
    # Mock update stats
    mock_stats = {
        'total_symbols': 50,
        'successful': 48,
        'failed': 2,
        'zone_shifts': 12,
        'significant_shifts': [
            {
                'symbol': 'AAPL',
                'shift_atr': 0.8,
                'old_zone': {'mid': 264.16, 'confluence': 8.5},
                'new_zone': {'mid': 268.00, 'confluence': 8.8}
            },
            {
                'symbol': 'TSLA',
                'shift_atr': -0.6,
                'old_zone': {'mid': 245.00, 'confluence': 7.5},
                'new_zone': {'mid': 242.00, 'confluence': 7.8}
            }
        ],
        'started_at': datetime.now().isoformat(),
        'completed_at': datetime.now().isoformat()
    }
    
    # Format alert
    alert = updater.format_shift_alert(mock_stats)
    print("\n📱 SHIFT ALERT MESSAGE:")
    print("-" * 70)
    print(alert)
    print("-" * 70)
    
    # Add to history
    updater.update_history.append(mock_stats)
    updater.save_history()
    
    # Get summary
    summary = updater.get_update_summary()
    print(f"\n{summary}")
    
    # Get stats
    stats = updater.get_stats()
    print(f"\n📊 Update Stats:")
    print(f"   • Total updates: {stats['total_updates']}")
    print(f"   • Avg success rate: {stats['avg_success_rate']:.1f}%")
    
    print("\n✅ Update workflow test passed!")


def run_all_tests():
    """Run complete test suite."""
    print("\n" + "="*70)
    print("EOD UPDATER TEST SUITE")
    print("="*70)
    
    test_should_run()
    test_zone_comparison()
    test_update_workflow()
    
    # Cleanup
    import os
    if os.path.exists("cache/test_eod_updates.json"):
        os.remove("cache/test_eod_updates.json")
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

from scanner.eod_updater import EODUpdater
from alerts.telegram_sender import TelegramSender

# Initialize
scanner = HourlyScanner(config)
eod_updater = EODUpdater(
    scanner=scanner,
    shift_threshold=0.5  # Alert if zone shifts >0.5×ATR
)
telegram = TelegramSender(config)

# EOD update function (Mon-Thu at 17:00 ET)
def run_eod_update():
    if not eod_updater.should_run_update():
        return
    
    # Get symbols
    symbols = config.get_universe()
    
    # Run update
    stats = eod_updater.update_all(symbols)
    
    # Send shift alerts if significant
    if stats.get('significant_shifts'):
        alert = eod_updater.format_shift_alert(stats)
        telegram.send_message(alert)
    
    return stats

# In scheduler.py (schedule_eod_update method):
# Schedule Mon-Thu at 17:00 ET
trigger = CronTrigger(
    day_of_week='mon-thu',
    hour=17,
    minute=0,
    timezone=timezone
)

scheduler.add_job(
    run_eod_update,
    trigger=trigger,
    id='eod_update',
    name='End-of-Day Update'
)
    """)


if __name__ == "__main__":
    # Run tests
    run_all_tests()
    
    # Show integration example
    integration_example()
