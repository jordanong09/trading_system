"""
Telegram Threading Support for Swing Trader Alert Engine
Groups related messages by symbol using Telegram's Topics/Forum feature.

Priority: ⭐⭐ (Optional UX improvement)
Purpose: Organize alerts by symbol for easier tracking
"""

from typing import Dict, Optional
import json
from pathlib import Path
from datetime import datetime


class TelegramThreading:
    """
    Manages Telegram message threading using Topics feature.
    
    Features:
    - Create topic (thread) per symbol
    - Track topic IDs
    - Send messages to specific topics
    - Automatic topic creation
    - Topic persistence across restarts
    
    Note: Requires Telegram group with Topics enabled (Supergroup)
    """
    
    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        topics_enabled: bool = True,
        topic_cache_file: str = "telegram_topics.json",
        cache_dir: str = "./cache"
    ):
        """
        Initialize Telegram threading manager.
        
        Args:
            bot_token: Telegram bot token
            chat_id: Telegram chat/group ID
            topics_enabled: Whether to use topics (requires Supergroup)
            topic_cache_file: JSON file to cache topic IDs
            cache_dir: Directory for cache
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.topics_enabled = topics_enabled
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.topic_cache_file = self.cache_dir / topic_cache_file
        
        # Topic cache: {symbol: topic_id}
        self.topics: Dict[str, int] = {}
        
        # Special topics
        self.general_topic_id = None
        self.watchlist_topic_id = None
        
        # Load cached topics
        self.load_topics()
    
    def get_topic_for_symbol(self, symbol: str, create_if_missing: bool = True) -> Optional[int]:
        """
        Get topic ID for a symbol.
        
        Args:
            symbol: Stock symbol
            create_if_missing: Create new topic if not exists
        
        Returns:
            Topic ID or None if topics disabled
        """
        if not self.topics_enabled:
            return None
        
        # Check cache
        if symbol in self.topics:
            return self.topics[symbol]
        
        # Create new topic if needed
        if create_if_missing:
            topic_id = self._create_topic(symbol)
            if topic_id:
                self.topics[symbol] = topic_id
                self.save_topics()
                return topic_id
        
        return None
    
    def _create_topic(self, symbol: str) -> Optional[int]:
        """
        Create a new topic for a symbol.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Topic ID or None if failed
        """
        if not self.topics_enabled:
            return None
        
        try:
            # In real implementation, call Telegram API
            # POST https://api.telegram.org/bot{token}/createForumTopic
            # body: {
            #     "chat_id": self.chat_id,
            #     "name": f"📊 {symbol}",
            #     "icon_color": 0x6FB9F0  # Blue
            # }
            
            # Mock implementation for template
            print(f"   📝 Creating topic for {symbol}")
            
            # Return mock topic ID (in real implementation, get from API response)
            # topic_id = response.json()['result']['message_thread_id']
            topic_id = hash(symbol) % 10000  # Mock ID
            
            print(f"   ✅ Created topic {topic_id} for {symbol}")
            return topic_id
        
        except Exception as e:
            print(f"   ⚠️  Error creating topic for {symbol}: {e}")
            return None
    
    def send_to_topic(
        self,
        symbol: str,
        message: str,
        create_topic_if_missing: bool = True
    ) -> bool:
        """
        Send message to symbol's topic.
        
        Args:
            symbol: Stock symbol
            message: Message text
            create_topic_if_missing: Create topic if doesn't exist
        
        Returns:
            True if sent successfully
        """
        if not self.topics_enabled:
            # Fall back to regular send
            return self._send_regular_message(message)
        
        # Get topic ID
        topic_id = self.get_topic_for_symbol(symbol, create_topic_if_missing)
        
        if not topic_id:
            # Fall back to regular send
            return self._send_regular_message(message)
        
        try:
            # In real implementation, call Telegram API with message_thread_id
            # POST https://api.telegram.org/bot{token}/sendMessage
            # body: {
            #     "chat_id": self.chat_id,
            #     "text": message,
            #     "message_thread_id": topic_id,
            #     "parse_mode": "Markdown"
            # }
            
            print(f"   📤 Sending to {symbol} topic {topic_id}")
            return True
        
        except Exception as e:
            print(f"   ⚠️  Error sending to topic: {e}")
            return False
    
    def _send_regular_message(self, message: str) -> bool:
        """
        Send message without threading (fallback).
        
        Args:
            message: Message text
        
        Returns:
            True if sent successfully
        """
        try:
            # Regular send without topic
            print(f"   📤 Sending regular message")
            return True
        
        except Exception as e:
            print(f"   ⚠️  Error sending message: {e}")
            return False
    
    def create_special_topics(self) -> Dict[str, int]:
        """
        Create special topics for system messages.
        
        Returns:
            Dictionary mapping topic name to ID
        """
        special_topics = {
            'general': '📢 General',
            'watchlist': '⭐ Watchlist',
            'system': '⚙️ System'
        }
        
        created = {}
        
        for key, name in special_topics.items():
            topic_id = self._create_special_topic(name)
            if topic_id:
                created[key] = topic_id
        
        # Cache special topics
        if 'general' in created:
            self.general_topic_id = created['general']
        if 'watchlist' in created:
            self.watchlist_topic_id = created['watchlist']
        
        self.save_topics()
        
        return created
    
    def _create_special_topic(self, name: str) -> Optional[int]:
        """
        Create a special topic with custom name.
        
        Args:
            name: Topic name
        
        Returns:
            Topic ID or None
        """
        try:
            print(f"   📝 Creating special topic: {name}")
            topic_id = hash(name) % 10000  # Mock ID
            print(f"   ✅ Created topic {topic_id}: {name}")
            return topic_id
        
        except Exception as e:
            print(f"   ⚠️  Error creating special topic: {e}")
            return None
    
    def organize_by_type(self, symbol: str, is_watchlist: bool = False) -> Optional[int]:
        """
        Get topic based on alert type.
        
        Args:
            symbol: Stock symbol
            is_watchlist: Whether from watchlist
        
        Returns:
            Topic ID or None
        """
        if is_watchlist and self.watchlist_topic_id:
            return self.watchlist_topic_id
        
        return self.get_topic_for_symbol(symbol)
    
    def load_topics(self) -> bool:
        """
        Load topic cache from file.
        
        Returns:
            True if loaded successfully
        """
        if not self.topic_cache_file.exists():
            print(f"   ℹ️  No topic cache found")
            return False
        
        try:
            with open(self.topic_cache_file, 'r') as f:
                data = json.load(f)
            
            self.topics = data.get('topics', {})
            self.general_topic_id = data.get('general_topic_id')
            self.watchlist_topic_id = data.get('watchlist_topic_id')
            
            print(f"   ✅ Loaded {len(self.topics)} topics from cache")
            return True
        
        except (json.JSONDecodeError, IOError) as e:
            print(f"   ⚠️  Error loading topics: {e}")
            return False
    
    def save_topics(self) -> bool:
        """
        Save topic cache to file.
        
        Returns:
            True if saved successfully
        """
        try:
            data = {
                'topics': self.topics,
                'general_topic_id': self.general_topic_id,
                'watchlist_topic_id': self.watchlist_topic_id,
                'updated_at': datetime.now().isoformat()
            }
            
            with open(self.topic_cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            return True
        
        except IOError as e:
            print(f"   ⚠️  Error saving topics: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """
        Get statistics about topics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            'total_topics': len(self.topics),
            'topics_enabled': self.topics_enabled,
            'has_general_topic': self.general_topic_id is not None,
            'has_watchlist_topic': self.watchlist_topic_id is not None
        }
    
    def list_topics(self) -> Dict[str, int]:
        """
        Get all symbol topics.
        
        Returns:
            Dictionary mapping symbol to topic ID
        """
        return self.topics.copy()
    
    def clear_topics(self) -> None:
        """
        Clear all topics (for testing).
        """
        self.topics = {}
        self.general_topic_id = None
        self.watchlist_topic_id = None
        print("   🔄 Topics cleared")


# =============================================================================
# TESTING FUNCTIONS
# =============================================================================

def test_topic_creation():
    """Test topic creation and caching."""
    print("\n" + "="*70)
    print("TEST 1: Topic Creation")
    print("="*70)
    
    threading = TelegramThreading(
        bot_token="test_token",
        chat_id="test_chat",
        topics_enabled=True,
        topic_cache_file="test_topics.json"
    )
    
    # Clear existing
    threading.clear_topics()
    
    # Create topics
    symbols = ['AAPL', 'TSLA', 'NVDA', 'GOOGL', 'MSFT']
    
    for symbol in symbols:
        topic_id = threading.get_topic_for_symbol(symbol)
        assert topic_id is not None, f"Topic should be created for {symbol}"
        print(f"✅ Created topic {topic_id} for {symbol}")
    
    # Verify cache
    assert len(threading.topics) == 5, "Should have 5 topics"
    print(f"\n✅ Cached {len(threading.topics)} topics")
    
    print("\n✅ Topic creation test passed!")


def test_special_topics():
    """Test special topic creation."""
    print("\n" + "="*70)
    print("TEST 2: Special Topics")
    print("="*70)
    
    threading = TelegramThreading(
        bot_token="test_token",
        chat_id="test_chat",
        topic_cache_file="test_topics.json"
    )
    
    # Create special topics
    special = threading.create_special_topics()
    
    print(f"\n📋 Special Topics Created:")
    for name, topic_id in special.items():
        print(f"   • {name}: {topic_id}")
    
    assert 'general' in special, "Should have general topic"
    assert 'watchlist' in special, "Should have watchlist topic"
    
    print("\n✅ Special topics test passed!")


def test_message_sending():
    """Test sending messages to topics."""
    print("\n" + "="*70)
    print("TEST 3: Message Sending")
    print("="*70)
    
    threading = TelegramThreading(
        bot_token="test_token",
        chat_id="test_chat",
        topic_cache_file="test_topics.json"
    )
    
    # Send to topic
    success = threading.send_to_topic(
        symbol="AAPL",
        message="🟢 AAPL LONG SIGNAL\nPrice: $264.82\nConfluence: 9.5/10"
    )
    
    assert success, "Message should send successfully"
    print("✅ Message sent to AAPL topic")
    
    # Send watchlist message
    topic_id = threading.organize_by_type("TSLA", is_watchlist=True)
    print(f"✅ Watchlist topic ID: {topic_id}")
    
    print("\n✅ Message sending test passed!")


def test_persistence():
    """Test topic persistence."""
    print("\n" + "="*70)
    print("TEST 4: Persistence")
    print("="*70)
    
    # Create first instance
    threading1 = TelegramThreading(
        bot_token="test_token",
        chat_id="test_chat",
        topic_cache_file="test_topics.json"
    )
    
    initial_count = len(threading1.topics)
    print(f"Instance 1: {initial_count} topics")
    
    # Create second instance
    threading2 = TelegramThreading(
        bot_token="test_token",
        chat_id="test_chat",
        topic_cache_file="test_topics.json"
    )
    
    # Should load same topics
    assert len(threading2.topics) == initial_count, "Topics should persist"
    print(f"Instance 2: {len(threading2.topics)} topics (persisted)")
    
    # Get stats
    stats = threading2.get_stats()
    print(f"\n📊 Threading Stats:")
    print(f"   • Total topics: {stats['total_topics']}")
    print(f"   • Topics enabled: {stats['topics_enabled']}")
    
    print("\n✅ Persistence test passed!")


def test_disabled_threading():
    """Test behavior when threading is disabled."""
    print("\n" + "="*70)
    print("TEST 5: Disabled Threading")
    print("="*70)
    
    threading = TelegramThreading(
        bot_token="test_token",
        chat_id="test_chat",
        topics_enabled=False,  # Disabled
        topic_cache_file="test_topics.json"
    )
    
    # Should not create topics
    topic_id = threading.get_topic_for_symbol("AAPL")
    assert topic_id is None, "Should not create topic when disabled"
    print("✅ Topics disabled - no topic created")
    
    # Should fall back to regular send
    success = threading.send_to_topic("AAPL", "Test message")
    assert success, "Should fall back to regular send"
    print("✅ Falls back to regular send")
    
    print("\n✅ Disabled threading test passed!")


def run_all_tests():
    """Run complete test suite."""
    print("\n" + "="*70)
    print("TELEGRAM THREADING TEST SUITE")
    print("="*70)
    
    test_topic_creation()
    test_special_topics()
    test_message_sending()
    test_persistence()
    test_disabled_threading()
    
    # Cleanup
    import os
    if os.path.exists("cache/test_topics.json"):
        os.remove("cache/test_topics.json")
        print("\n🧹 Cleaned up test files")
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED!")
    print("="*70)


# =============================================================================
# INTEGRATION EXAMPLE
# =============================================================================

def integration_example():
    """
    Example of how to integrate with telegram_sender.py
    """
    print("\n" + "="*70)
    print("INTEGRATION EXAMPLE")
    print("="*70)
    
    print("""
# In alerts/telegram_sender.py:

from alerts.telegram_threading import TelegramThreading

class TelegramSender:
    def __init__(self, config):
        self.bot_token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        
        # Initialize threading
        self.threading = TelegramThreading(
            bot_token=self.bot_token,
            chat_id=self.chat_id,
            topics_enabled=config.TELEGRAM_TOPICS_ENABLED
        )
        
        # Create special topics on startup
        if config.TELEGRAM_TOPICS_ENABLED:
            self.threading.create_special_topics()
    
    def send_alert(self, signal: Dict) -> bool:
        symbol = signal['symbol']
        is_watchlist = signal.get('from_watchlist', False)
        
        # Format message
        message = self.format_signal(signal)
        
        # Send to appropriate topic
        success = self.threading.send_to_topic(
            symbol=symbol,
            message=message,
            create_topic_if_missing=True
        )
        
        return success
    
    def send_watchlist(self, watchlist_message: str) -> bool:
        # Send to watchlist topic
        if self.threading.watchlist_topic_id:
            return self.threading._send_to_specific_topic(
                topic_id=self.threading.watchlist_topic_id,
                message=watchlist_message
            )
        
        return self.threading._send_regular_message(watchlist_message)

# In config.py:
TELEGRAM_TOPICS_ENABLED = True  # Set False to disable threading
    """)


if __name__ == "__main__":
    # Run tests
    run_all_tests()
    
    # Show integration example
    integration_example()
