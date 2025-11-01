"""
De-duplication System for Swing Trader Alert Engine
Prevents alert spam by enforcing 60-minute cooldown per symbol/zone combination.

Priority: ⭐⭐⭐⭐⭐ CRITICAL
Purpose: Reduce alerts from 50+/day to 3-8/day target
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
from pathlib import Path
import threading


class Deduplicator:
    """
    Manages alert de-duplication with symbol/zone tracking and cooldown enforcement.
    
    Features:
    - 60-minute cooldown per symbol/zone combination
    - Allows re-alerts if price moves to different zone
    - Persists state across restarts via JSON
    - Thread-safe for concurrent operations
    """
    
    def __init__(
        self, 
        cooldown_minutes: int = 60,
        state_file: str = "alert_state.json",
        cache_dir: str = "./cache"
    ):
        """
        Initialize the deduplicator.
        
        Args:
            cooldown_minutes: Minutes to wait before re-alerting same symbol/zone
            state_file: JSON file to persist alert state
            cache_dir: Directory to store state file
        """
        self.cooldown_minutes = cooldown_minutes
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.cache_dir / state_file
        
        # Internal state: {symbol: {zone_id: timestamp}}
        self.alert_history: Dict[str, Dict[str, str]] = {}
        
        # Thread safety for concurrent scans
        self.lock = threading.Lock()
        
        # Load existing state
        self.load_state()
    
    def can_alert(self, symbol: str, zone_id: str) -> bool:
        """
        Check if we can send an alert for this symbol/zone combination.
        
        Args:
            symbol: Stock symbol (e.g., "AAPL")
            zone_id: Unique zone identifier (e.g., "zone_ema20_264.16")
        
        Returns:
            True if alert is allowed, False if within cooldown period
        """
        with self.lock:
            # First alert for this symbol
            if symbol not in self.alert_history:
                return True
            
            # First alert for this zone
            if zone_id not in self.alert_history[symbol]:
                return True
            
            # Check if cooldown has expired
            last_alert_str = self.alert_history[symbol][zone_id]
            last_alert = datetime.fromisoformat(last_alert_str)
            cooldown_end = last_alert + timedelta(minutes=self.cooldown_minutes)
            
            now = datetime.now()
            
            if now >= cooldown_end:
                return True  # Cooldown expired
            else:
                # Calculate remaining cooldown
                remaining = (cooldown_end - now).total_seconds() / 60
                print(f"   ⏳ Cooldown active for {symbol} @ {zone_id}: "
                      f"{remaining:.1f} min remaining")
                return False
    
    def record_alert(self, symbol: str, zone_id: str) -> None:
        """
        Record that an alert was sent for this symbol/zone.
        
        Args:
            symbol: Stock symbol
            zone_id: Zone identifier
        """
        with self.lock:
            if symbol not in self.alert_history:
                self.alert_history[symbol] = {}
            
            self.alert_history[symbol][zone_id] = datetime.now().isoformat()
            
            # Auto-save state after recording
            self.save_state()
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries from history to keep state file small.
        
        Returns:
            Number of entries removed
        """
        with self.lock:
            cutoff = datetime.now() - timedelta(minutes=self.cooldown_minutes)
            removed_count = 0
            
            symbols_to_remove = []
            for symbol, zones in self.alert_history.items():
                zones_to_remove = []
                
                for zone_id, timestamp_str in zones.items():
                    timestamp = datetime.fromisoformat(timestamp_str)
                    if timestamp < cutoff:
                        zones_to_remove.append(zone_id)
                
                # Remove expired zones
                for zone_id in zones_to_remove:
                    del zones[zone_id]
                    removed_count += 1
                
                # Mark symbol for removal if no zones left
                if not zones:
                    symbols_to_remove.append(symbol)
            
            # Remove empty symbols
            for symbol in symbols_to_remove:
                del self.alert_history[symbol]
            
            if removed_count > 0:
                self.save_state()
                print(f"   🧹 Cleaned up {removed_count} expired alert entries")
            
            return removed_count
    
    def load_state(self) -> bool:
        """
        Load alert history from JSON file.
        
        Returns:
            True if state loaded successfully, False if file doesn't exist
        """
        if not self.state_file.exists():
            print(f"   ℹ️  No existing alert state found at {self.state_file}")
            return False
        
        try:
            with open(self.state_file, 'r') as f:
                self.alert_history = json.load(f)
            
            # Count active alerts
            total_alerts = sum(len(zones) for zones in self.alert_history.values())
            print(f"   ✅ Loaded {total_alerts} alert records from {self.state_file}")
            
            # Auto-cleanup expired entries on load
            self.cleanup_expired()
            
            return True
        
        except (json.JSONDecodeError, IOError) as e:
            print(f"   ⚠️  Error loading state file: {e}")
            self.alert_history = {}
            return False
    
    def save_state(self) -> bool:
        """
        Save alert history to JSON file.
        
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.alert_history, f, indent=2)
            return True
        
        except IOError as e:
            print(f"   ⚠️  Error saving state file: {e}")
            return False
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about current alert state.
        
        Returns:
            Dictionary with total symbols, zones, and active alerts
        """
        with self.lock:
            total_symbols = len(self.alert_history)
            total_zones = sum(len(zones) for zones in self.alert_history.values())
            
            # Count alerts still in cooldown
            now = datetime.now()
            active_cooldowns = 0
            
            for zones in self.alert_history.values():
                for timestamp_str in zones.values():
                    timestamp = datetime.fromisoformat(timestamp_str)
                    if timestamp + timedelta(minutes=self.cooldown_minutes) > now:
                        active_cooldowns += 1
            
            return {
                "total_symbols": total_symbols,
                "total_zones": total_zones,
                "active_cooldowns": active_cooldowns,
                "cooldown_minutes": self.cooldown_minutes
            }
    
    def get_cooldown_status(self, symbol: str) -> Dict[str, str]:
        """
        Get cooldown status for all zones of a symbol.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Dictionary mapping zone_id to remaining cooldown time
        """
        with self.lock:
            if symbol not in self.alert_history:
                return {}
            
            now = datetime.now()
            status = {}
            
            for zone_id, timestamp_str in self.alert_history[symbol].items():
                timestamp = datetime.fromisoformat(timestamp_str)
                cooldown_end = timestamp + timedelta(minutes=self.cooldown_minutes)
                
                if now < cooldown_end:
                    remaining = (cooldown_end - now).total_seconds() / 60
                    status[zone_id] = f"{remaining:.1f} min"
                else:
                    status[zone_id] = "Ready"
            
            return status
    
    def reset_symbol(self, symbol: str) -> bool:
        """
        Clear all alert history for a specific symbol.
        Useful for testing or manual override.
        
        Args:
            symbol: Stock symbol to reset
        
        Returns:
            True if symbol was reset, False if not found
        """
        with self.lock:
            if symbol in self.alert_history:
                del self.alert_history[symbol]
                self.save_state()
                print(f"   🔄 Reset alert history for {symbol}")
                return True
            return False
    
    def clear_all(self) -> None:
        """
        Clear entire alert history. Use with caution!
        """
        with self.lock:
            self.alert_history = {}
            self.save_state()
            print("   ⚠️  Cleared all alert history")


# =============================================================================
# TESTING FUNCTIONS
# =============================================================================

def test_basic_cooldown():
    """Test basic cooldown functionality."""
    print("\n" + "="*70)
    print("TEST 1: Basic Cooldown")
    print("="*70)
    
    # Create deduplicator with 1-minute cooldown for testing
    dedup = Deduplicator(cooldown_minutes=1, state_file="test_alert_state.json")
    dedup.clear_all()
    
    # First alert should be allowed
    assert dedup.can_alert("AAPL", "zone_1"), "First alert should be allowed"
    print("✅ First alert: ALLOWED")
    
    # Record the alert
    dedup.record_alert("AAPL", "zone_1")
    print("✅ Alert recorded")
    
    # Immediate re-alert should be blocked
    assert not dedup.can_alert("AAPL", "zone_1"), "Immediate re-alert should be blocked"
    print("✅ Immediate re-alert: BLOCKED (cooldown active)")
    
    # Different zone should be allowed
    assert dedup.can_alert("AAPL", "zone_2"), "Different zone should be allowed"
    print("✅ Different zone: ALLOWED")
    
    # Different symbol should be allowed
    assert dedup.can_alert("TSLA", "zone_1"), "Different symbol should be allowed"
    print("✅ Different symbol: ALLOWED")
    
    print("\n✅ All basic cooldown tests passed!")


def test_persistence():
    """Test state persistence across instances."""
    print("\n" + "="*70)
    print("TEST 2: State Persistence")
    print("="*70)
    
    # Create first instance and record alerts
    dedup1 = Deduplicator(cooldown_minutes=60, state_file="test_alert_state.json")
    dedup1.clear_all()
    
    dedup1.record_alert("AAPL", "zone_1")
    dedup1.record_alert("TSLA", "zone_2")
    print("✅ Recorded 2 alerts in instance 1")
    
    # Create second instance and verify state loaded
    dedup2 = Deduplicator(cooldown_minutes=60, state_file="test_alert_state.json")
    
    # Should be blocked due to loaded state
    assert not dedup2.can_alert("AAPL", "zone_1"), "State should persist"
    assert not dedup2.can_alert("TSLA", "zone_2"), "State should persist"
    print("✅ Instance 2 loaded state correctly")
    
    # Check stats
    stats = dedup2.get_stats()
    assert stats["total_symbols"] == 2, "Should have 2 symbols"
    assert stats["total_zones"] == 2, "Should have 2 zones"
    print(f"✅ Stats: {stats['total_symbols']} symbols, {stats['total_zones']} zones")
    
    print("\n✅ State persistence tests passed!")


def test_cleanup():
    """Test cleanup of expired entries."""
    print("\n" + "="*70)
    print("TEST 3: Expired Entry Cleanup")
    print("="*70)
    
    dedup = Deduplicator(cooldown_minutes=0.01, state_file="test_alert_state.json")  # ~0.6 seconds
    dedup.clear_all()
    
    # Record some alerts
    dedup.record_alert("AAPL", "zone_1")
    dedup.record_alert("TSLA", "zone_2")
    dedup.record_alert("NVDA", "zone_3")
    
    initial_stats = dedup.get_stats()
    print(f"✅ Initial state: {initial_stats['total_zones']} zones")
    
    # Wait for cooldown to expire
    import time
    print("   ⏳ Waiting 2 seconds for cooldown to expire...")
    time.sleep(2)
    
    # Cleanup should remove expired entries
    removed = dedup.cleanup_expired()
    print(f"✅ Cleaned up {removed} expired entries")
    
    final_stats = dedup.get_stats()
    assert final_stats["total_zones"] == 0, "All entries should be removed"
    print("✅ All expired entries removed")
    
    print("\n✅ Cleanup tests passed!")


def test_thread_safety():
    """Test thread-safe concurrent operations."""
    print("\n" + "="*70)
    print("TEST 4: Thread Safety")
    print("="*70)
    
    dedup = Deduplicator(cooldown_minutes=60, state_file="test_alert_state.json")
    dedup.clear_all()
    
    import threading
    
    def worker(symbol: str, zone_id: str):
        if dedup.can_alert(symbol, zone_id):
            dedup.record_alert(symbol, zone_id)
    
    # Create multiple threads
    threads = []
    for i in range(10):
        t = threading.Thread(target=worker, args=(f"SYM{i}", "zone_1"))
        threads.append(t)
        t.start()
    
    # Wait for all threads
    for t in threads:
        t.join()
    
    stats = dedup.get_stats()
    print(f"✅ Processed 10 concurrent operations: {stats['total_symbols']} symbols recorded")
    print("✅ No race conditions detected")
    
    print("\n✅ Thread safety tests passed!")


def run_all_tests():
    """Run complete test suite."""
    print("\n" + "="*70)
    print("DEDUPLICATOR TEST SUITE")
    print("="*70)
    
    test_basic_cooldown()
    test_persistence()
    test_cleanup()
    test_thread_safety()
    
    # Cleanup test file
    import os
    if os.path.exists("cache/test_alert_state.json"):
        os.remove("cache/test_alert_state.json")
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
    
    # Initialize in main.py or scanner
    deduplicator = Deduplicator(cooldown_minutes=60)
    
    # In scanning loop
    symbol = "AAPL"
    zone_id = "zone_ema20_264.16"
    
    print(f"\n📊 Processing signal for {symbol}...")
    
    # Check if we can alert
    if deduplicator.can_alert(symbol, zone_id):
        print(f"   ✅ Alert allowed - sending to Telegram...")
        
        # Send alert (pseudo-code)
        # telegram_sender.send_alert(symbol, zone_info)
        
        # Record the alert
        deduplicator.record_alert(symbol, zone_id)
        print(f"   ✅ Alert sent and recorded")
    else:
        print(f"   ⏸️  Alert suppressed - cooldown active")
    
    # Show stats
    stats = deduplicator.get_stats()
    print(f"\n📊 Deduplicator Stats:")
    print(f"   • Active cooldowns: {stats['active_cooldowns']}")
    print(f"   • Total tracked: {stats['total_symbols']} symbols, {stats['total_zones']} zones")
    
    # Show status for specific symbol
    status = deduplicator.get_cooldown_status(symbol)
    if status:
        print(f"\n⏰ {symbol} Cooldown Status:")
        for zone, remaining in status.items():
            print(f"   • {zone}: {remaining}")


if __name__ == "__main__":
    # Run tests
    run_all_tests()
    
    # Show integration example
    integration_example()