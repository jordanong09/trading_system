# modules/telegram_bot.py - MVP 4.0 Alert Delivery (Updated with P5.1, P5.2)
"""
Enhanced Telegram alert delivery for MVP 4.0
- Format alerts with zone info, confluence, pattern
- Support for watchlist vs new opportunity badges
- P5.1: Threading support (optional)
- P5.2: Message formatting (optional)
"""

import requests
from typing import Dict, Optional, Any
from datetime import datetime

# P5.1: Import threading module (conditional)
try:
    from alerts.telegram_threading import TelegramThreading
    THREADING_AVAILABLE = True
except ImportError:
    THREADING_AVAILABLE = False

# P5.2: Import message formatter (conditional)
try:
    from alerts.message_formatter import MessageFormatter
    FORMATTER_AVAILABLE = True
except ImportError:
    FORMATTER_AVAILABLE = False


class TelegramBot:
    """
    Send trading alerts to Telegram
    """
    
    def __init__(self, bot_token: Optional[str], chat_id: Optional[str], config: Optional[Dict] = None):
        """
        Initialize Telegram bot
        
        Args:
            bot_token: Telegram bot token
            chat_id: Telegram chat ID to send messages to
            config: Optional configuration dict with threading and formatting settings
        """
        self.bot_token = bot_token or ""   # coerce None → ""
        self.chat_id = chat_id or ""
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.config = config or {}
        
        # P5.1: Initialize threading (conditional)
        self.threading = None
        if THREADING_AVAILABLE and self.config.get('TELEGRAM_THREADING', {}).get('enabled', False):
            try:
                self.threading = TelegramThreading(
                    bot_token=bot_token or "",
                    chat_id=chat_id or "",
                    topics_enabled=True,
                    topic_cache_file=self.config['TELEGRAM_THREADING'].get('topic_cache_file', 'telegram_topics.json')
                )
                # Create special topics on startup
                self.threading.create_special_topics()
                print("✅ Telegram threading initialized")
            except Exception as e:
                print(f"⚠️  Could not initialize threading: {e}")
                self.threading = None
        
        # P5.2: Initialize formatter (conditional)
        self.formatter = None
        if FORMATTER_AVAILABLE:
            try:
                msg_config = self.config.get('MESSAGE_FORMATTING', {})
                self.formatter = MessageFormatter(
                    use_markdown=msg_config.get('use_markdown', True),
                    include_buttons=msg_config.get('include_buttons', True),
                    compact_mode=msg_config.get('compact_mode', False)
                )
                print("✅ Message formatter initialized")
            except Exception as e:
                print(f"⚠️  Could not initialize formatter: {e}")
                self.formatter = None
    
    def is_configured(self) -> bool:
        """Check if bot is properly configured"""
        return bool(self.bot_token) and bool(self.chat_id) and \
               self.bot_token != "test_token" and self.chat_id != "test_id"
    
    def format_alert(self, signal: Dict) -> str:
        """
        Format trading signal as Telegram message
        
        Args:
            signal: Signal dict with all trading information
            
        Returns:
            Formatted message string
        """
        symbol = signal['symbol']
        pattern = signal['pattern']
        side = signal['side']
        quality = signal['quality']
        price = signal['price']
        zone = signal['zone']
        confluence = signal['confluence']
        from_watchlist = signal.get('from_watchlist', False)
        
        # Header with badge
        badge = "⭐ FROM WATCHLIST" if from_watchlist else "🆕 NEW OPPORTUNITY"
        side_emoji = "🟢" if side == 'long' else "🔴"
        quality_text = quality.upper()
        
        message = f"{badge} | {side_emoji} {side.upper()} @ {zone['type'].upper()} ({quality_text})\n"
        message += f"*{symbol}* ${price:.2f}\n"
        
        # Timestamp
        timestamp = datetime.now().strftime("%H:%M ET")
        message += f"{timestamp}\n\n"
        
        # Zone info
        message += "─────────────────────\n"
        message += f"*ZONE ({confluence['total_score']:.1f}/10)*\n"
        message += "─────────────────────\n"
        message += f"{zone['type'].capitalize()}: ${zone['low']:.2f} - ${zone['high']:.2f}\n"
        
        # Components
        components_str = ", ".join(zone['components'])
        message += f"  • Components: {components_str}\n"
        
        # Distance
        distance_atr = zone.get('distance_atr', 0)
        message += f"  • Distance: {distance_atr:.2f}×ATR\n"
        
        # Pattern
        message += "\n─────────────────────\n"
        message += f"*TRIGGER (1H)*\n"
        message += "─────────────────────\n"
        message += f"Pattern: {pattern['pattern']}\n"
        message += f"Volume: RV {pattern['relative_volume']:.1f}x\n"
        
        # Market context
        message += "\n─────────────────────\n"
        message += "*MARKET*\n"
        message += "─────────────────────\n"
        
        index_context = signal.get('index_context', {})
        spy_regime = index_context.get('spy_regime', 'unknown')
        qqq_regime = index_context.get('qqq_regime', 'unknown')
        
        spy_emoji = "✅" if spy_regime == 'bullish' else "❌" if spy_regime == 'bearish' else "⚠️"
        qqq_emoji = "✅" if qqq_regime == 'bullish' else "❌" if qqq_regime == 'bearish' else "⚠️"
        
        message += f"SPY: {spy_regime.capitalize()} {spy_emoji}\n"
        message += f"QQQ: {qqq_regime.capitalize()} {qqq_emoji}\n"
        
        # Confluence breakdown
        message += "\n─────────────────────\n"
        message += "*CONFLUENCE*\n"
        message += "─────────────────────\n"
        message += f"Total: {confluence['total_score']:.1f}/10\n"
        message += f"  • Base: {confluence['base_strength']:.1f}/6\n"
        message += f"  • Index: {confluence['index_alignment_score']:.1f}/2\n"
        message += f"  • Trend: {confluence['trend_alignment_score']:.1f}/2\n"
        
        # Levels (if available)
        targets = signal.get('targets')
        if targets:
            message += "\n─────────────────────\n"
            message += "*LEVELS*\n"
            message += "─────────────────────\n"
            
            if side == 'long':
                message += f"Entry: ${price:.2f}\n"
                if 'next_resistance' in targets:
                    message += f"Target: ${targets['next_resistance']:.2f}\n"
                if 'stop_loss' in targets:
                    message += f"Stop: ${targets['stop_loss']:.2f}\n"
            else:
                message += f"Entry: ${price:.2f}\n"
                if 'next_support' in targets:
                    message += f"Target: ${targets['next_support']:.2f}\n"
                if 'stop_loss' in targets:
                    message += f"Stop: ${targets['stop_loss']:.2f}\n"
        
        # Footer
        if from_watchlist:
            message += "\n💡 From Sunday watchlist - confirmed\n"
        
        message += "\n📚 Educational analysis. Not advice.\n"
        
        # Chart link
        message += f"\n[View Chart](https://www.tradingview.com/chart/?symbol={symbol})"
        
        return message
    
    def send_alert(self, signal: Dict) -> bool:
        """
        Send trading alert to Telegram
        Enhanced with threading and formatting support
        
        Args:
            signal: Signal dict with trading information
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_configured():
            print("   ⚠️  Telegram not configured")
            return False
        
        try:
            symbol = signal['symbol']
            
            # P5.2: Use formatter if available
            if self.formatter:
                # Determine alert type
                alert_type = "watchlist" if signal.get('from_watchlist') else "new"
                message = self.formatter.format_signal(signal, alert_type)
                
                # Add inline buttons
                buttons = None
                if self.formatter.include_buttons:
                    buttons = self.formatter.generate_inline_buttons(symbol, signal)
            else:
                # Fallback to standard formatting
                message = self.format_alert(signal)
                buttons = None
            
            # P5.1: Use threading if available
            if self.threading and self.threading.topics_enabled:
                # Send to symbol-specific topic (threading module doesn't support reply_markup yet)
                success = self.threading.send_to_topic(symbol, message)
            else:
                # Send as regular message
                success = self._send_regular_message(message, reply_markup=buttons)
            
            if success:
                print(f"   ✅ Alert sent for {signal['symbol']}")
            else:
                print(f"   ⚠️  Failed to send alert for {signal['symbol']}")
            
            return success
        
        except Exception as e:
            print(f"   ❌ Error sending alert: {e}")
            return False
    
    def _send_regular_message(self, message: str, reply_markup: Optional[Any] = None) -> bool:
        """
        Send regular message (without threading)
        
        Args:
            message: Message text
            reply_markup: Optional inline keyboard markup (Dict or List of buttons)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }
            
            if reply_markup:
                payload["reply_markup"] = reply_markup
            
            response = requests.post(url, json=payload, timeout=10)
            
            return response.status_code == 200
        
        except Exception as e:
            print(f"   ❌ Error sending message: {e}")
            return False
    
    def send_watchlist(self, watchlist_message: str) -> bool:
        """
        Send weekly watchlist message
        Enhanced with threading support
        
        Args:
            watchlist_message: Formatted watchlist message
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_configured():
            print("   ⚠️  Telegram not configured")
            return False
        
        try:
            # P5.1: Send to watchlist topic if available
            if self.threading and self.threading.watchlist_topic_id:
                success = self.threading.send_to_topic(
                    "WATCHLIST",
                    watchlist_message
                )
            else:
                success = self._send_regular_message(watchlist_message)
            
            if success:
                print("   ✅ Watchlist sent")
            else:
                print("   ⚠️  Failed to send watchlist")
            
            return success
        
        except Exception as e:
            print(f"   ❌ Error sending watchlist: {e}")
            return False
    
    def send_test_message(self) -> bool:
        """
        Send a test message to verify bot configuration
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_configured():
            print("   ❌ Telegram not configured")
            return False
        
        try:
            message = "✅ *Swing Trader Alert Engine*\n\n"
            message += "Test message - bot is working!\n"
            message += f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                print("   ✅ Test message sent successfully")
                return True
            else:
                print(f"   ❌ Failed to send test message: {response.status_code}")
                return False
        
        except Exception as e:
            print(f"   ❌ Error sending test message: {e}")
            return False


# Quick test function
def test_telegram_bot():
    """Test Telegram bot"""
    import config
    
    print("🧪 Testing Telegram Bot")
    print("=" * 60)
    
    # Initialize bot
    bot = TelegramBot(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
    
    # Check configuration
    print(f"\n🔧 Bot configured: {bot.is_configured()}")
    
    if not bot.is_configured():
        print("   ⚠️  Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in environment")
        print("   Skipping send test")
        return
    
    # Create test signal
    signal = {
        'symbol': 'AAPL',
        'side': 'long',
        'quality': 'High',
        'price': 184.50,
        'pattern': {
            'pattern': 'Bullish Engulfing',
            'relative_volume': 1.8
        },
        'zone': {
            'zone_id': 'AAPL_zn_support_0_20251026',
            'type': 'support',
            'low': 183.23,
            'mid': 184.12,
            'high': 185.01,
            'components': ['ema20', 'swing_low'],
            'distance_atr': 0.12
        },
        'confluence': {
            'total_score': 7.2,
            'base_strength': 5.2,
            'index_alignment_score': 2.0,
            'trend_alignment_score': 0.0
        },
        'index_context': {
            'spy_regime': 'bullish',
            'qqq_regime': 'bullish'
        },
        'targets': {
            'next_resistance': 189.00,
            'stop_loss': 181.50
        },
        'from_watchlist': True
    }
    
    # Format message (preview)
    print("\n📝 Formatted message preview:")
    print("-" * 60)
    message = bot.format_alert(signal)
    print(message)
    print("-" * 60)
    
    # Send test alert
    print("\n📤 Sending test alert...")
    success = bot.send_alert(signal)
    
    if success:
        print("   ✅ Alert sent successfully!")
    else:
        print("   ❌ Failed to send alert")
    
    print("\n✅ Telegram bot test complete!")


if __name__ == "__main__":
    test_telegram_bot()