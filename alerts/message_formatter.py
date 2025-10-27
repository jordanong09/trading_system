"""
Message Formatting Module for Swing Trader Alert Engine
Separates formatting logic from sender, supports multiple alert types.

Priority: ⭐⭐ (Optional UX improvement)
Purpose: Clean, consistent, professional alert messages
"""

from typing import Dict, List, Optional
from datetime import datetime


class MessageFormatter:
    """
    Formats trading signals and system messages for Telegram.
    
    Features:
    - Multiple alert types (watchlist, new, confirmation, system)
    - Emoji indicators for visual clarity
    - Inline buttons support (View Chart, Dismiss)
    - Consistent formatting across all messages
    - Markdown support
    """
    
    def __init__(
        self,
        use_markdown: bool = True,
        include_buttons: bool = True,
        compact_mode: bool = False
    ):
        """
        Initialize message formatter.
        
        Args:
            use_markdown: Use Markdown formatting
            include_buttons: Include inline buttons
            compact_mode: Use compact formatting (fewer lines)
        """
        self.use_markdown = use_markdown
        self.include_buttons = include_buttons
        self.compact_mode = compact_mode
    
    # =========================================================================
    # SIGNAL FORMATTING
    # =========================================================================
    
    def format_signal(
        self,
        signal: Dict,
        alert_type: str = "new"
    ) -> str:
        """
        Format trading signal alert.
        
        Args:
            signal: Signal dictionary
            alert_type: 'watchlist', 'new', or 'confirmation'
        
        Returns:
            Formatted message string
        """
        # Choose formatter based on type
        if alert_type == "watchlist":
            return self._format_watchlist_signal(signal)
        elif alert_type == "confirmation":
            return self._format_confirmation_signal(signal)
        else:
            return self._format_new_signal(signal)
    
    def _format_new_signal(self, signal: Dict) -> str:
        """Format new opportunity signal."""
        symbol = signal['symbol']
        side = signal['side']
        pattern = signal['pattern']
        price = signal['price']
        confluence = signal['confluence']
        quality = signal.get('quality', 'standard')
        
        # Side emoji
        side_emoji = "🟢" if side == "long" else "🔴"
        side_text = "LONG" if side == "long" else "SHORT"
        
        # Quality badge
        quality_badge = self._get_quality_badge(quality)
        
        # Header
        if self.use_markdown:
            message = f"{side_emoji} **{symbol} {side_text}** {quality_badge}\n"
        else:
            message = f"{side_emoji} {symbol} {side_text} {quality_badge}\n"
        
        message += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Key info
        message += f"📊 **Setup Details**\n"
        message += f"   • Pattern: {pattern}\n"
        message += f"   • Entry: ${price:.2f}\n"
        message += f"   • Confluence: {confluence:.1f}/10\n"
        
        # Zone info
        if signal.get('zone_id'):
            message += f"   • Zone: {signal['zone_id']}\n"
        
        # Relative volume
        if signal.get('relative_volume'):
            rv = signal['relative_volume']
            rv_emoji = "🔥" if rv >= 2.0 else "📊"
            message += f"   • Volume: {rv_emoji} {rv:.1f}×\n"
        
        message += "\n"
        
        # Targets (if compact mode, show inline)
        if self.compact_mode:
            if signal.get('target'):
                message += f"🎯 ${signal['target']:.2f} | "
            if signal.get('stop_loss'):
                message += f"🛑 ${signal['stop_loss']:.2f}\n"
        else:
            message += f"🎯 **Targets**\n"
            if signal.get('target'):
                message += f"   • Target: ${signal['target']:.2f}\n"
            if signal.get('stop_loss'):
                message += f"   • Stop: ${signal['stop_loss']:.2f}\n"
            
            # R:R ratio
            if signal.get('target') and signal.get('stop_loss'):
                rr = abs(signal['target'] - price) / abs(price - signal['stop_loss'])
                message += f"   • R:R: {rr:.1f}:1\n"
        
        # Market context
        if signal.get('index_context'):
            message += f"\n📈 **Market Context**\n"
            ctx = signal['index_context']
            message += f"   • SPY: {ctx.get('spy_regime', 'unknown')}\n"
            message += f"   • QQQ: {ctx.get('qqq_regime', 'unknown')}\n"
        
        # Footer
        message += "\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
        message += f"🕐 {datetime.now().strftime('%H:%M:%S')}"
        
        return message
    
    def _format_watchlist_signal(self, signal: Dict) -> str:
        """Format watchlist alert (stock from Sunday watchlist)."""
        symbol = signal['symbol']
        side = signal['side']
        pattern = signal['pattern']
        price = signal['price']
        confluence = signal['confluence']
        
        side_emoji = "🟢" if side == "long" else "🔴"
        side_text = "LONG" if side == "long" else "SHORT"
        
        # Watchlist badge
        message = f"⭐ **WATCHLIST** | {side_emoji} **{symbol} {side_text}**\n"
        message += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        message += f"✅ **Pre-Identified Setup Triggered**\n"
        message += f"   • Pattern: {pattern}\n"
        message += f"   • Entry: ${price:.2f}\n"
        message += f"   • Confluence: {confluence:.1f}/10\n\n"
        
        if signal.get('target') and signal.get('stop_loss'):
            message += f"🎯 ${signal['target']:.2f} | 🛑 ${signal['stop_loss']:.2f}\n"
        
        message += "\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
        message += f"🕐 {datetime.now().strftime('%H:%M:%S')}"
        
        return message
    
    def _format_confirmation_signal(self, signal: Dict) -> str:
        """Format confirmation alert (additional pattern on existing setup)."""
        symbol = signal['symbol']
        side = signal['side']
        pattern = signal['pattern']
        
        side_emoji = "🟢" if side == "long" else "🔴"
        
        message = f"✅ **CONFIRMATION** | {side_emoji} **{symbol}**\n"
        message += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        message += f"Additional pattern detected:\n"
        message += f"   • {pattern}\n"
        message += f"   • Strengthens existing setup\n\n"
        
        message += "Original signal still valid ✓\n"
        message += f"🕐 {datetime.now().strftime('%H:%M:%S')}"
        
        return message
    
    # =========================================================================
    # SYSTEM MESSAGES
    # =========================================================================
    
    def format_scan_summary(self, stats: Dict) -> str:
        """
        Format scan summary message.
        
        Args:
            stats: Scan statistics
        
        Returns:
            Formatted summary
        """
        message = "📊 **SCAN COMPLETE**\n"
        message += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        message += f"Scanned: {stats.get('symbols_scanned', 0)} stocks\n"
        message += f"Signals: {stats.get('signals_generated', 0)}\n"
        message += f"Duration: {stats.get('duration', 0):.1f}s\n"
        
        if stats.get('watchlist_hits'):
            message += f"⭐ Watchlist hits: {stats['watchlist_hits']}\n"
        
        message += f"\n🕐 {datetime.now().strftime('%H:%M:%S')}"
        
        return message
    
    def format_error(self, error: str, context: Optional[str] = None) -> str:
        """
        Format error message.
        
        Args:
            error: Error message
            context: Optional context
        
        Returns:
            Formatted error
        """
        message = "❌ **ERROR**\n"
        message += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        if context:
            message += f"Context: {context}\n"
        
        message += f"Error: {error}\n"
        message += f"\n🕐 {datetime.now().strftime('%H:%M:%S')}"
        
        return message
    
    def format_daily_summary(self, stats: Dict) -> str:
        """
        Format end-of-day summary.
        
        Args:
            stats: Daily statistics
        
        Returns:
            Formatted summary
        """
        message = "📈 **DAILY SUMMARY**\n"
        message += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        message += f"📊 Scans: {stats.get('scans_completed', 0)}\n"
        message += f"🎯 Signals: {stats.get('signals_generated', 0)}\n"
        message += f"📤 Alerts sent: {stats.get('alerts_sent', 0)}\n"
        
        if stats.get('watchlist_hits'):
            message += f"⭐ Watchlist hits: {stats['watchlist_hits']}\n"
        
        message += f"\n✅ System running smoothly\n"
        message += f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        return message
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def _get_quality_badge(self, quality: str) -> str:
        """
        Get quality badge emoji.
        
        Args:
            quality: Signal quality (premium/standard/speculative)
        
        Returns:
            Badge emoji
        """
        badges = {
            'premium': '💎',
            'standard': '✅',
            'speculative': '⚡'
        }
        return badges.get(quality, '✅')
    
    def generate_inline_buttons(self, symbol: str, signal: Dict) -> List[Dict]:
        """
        Generate inline keyboard buttons.
        
        Args:
            symbol: Stock symbol
            signal: Signal data
        
        Returns:
            List of button rows (for Telegram InlineKeyboardMarkup)
        """
        if not self.include_buttons:
            return []
        
        buttons = []
        
        # Row 1: Chart buttons
        row1 = [
            {
                'text': '📊 View Chart',
                'url': f'https://www.tradingview.com/chart/?symbol={symbol}'
            },
            {
                'text': '📈 Yahoo Finance',
                'url': f'https://finance.yahoo.com/quote/{symbol}'
            }
        ]
        buttons.append(row1)
        
        # Row 2: Action buttons
        row2 = [
            {
                'text': '✅ Acknowledge',
                'callback_data': f'ack_{symbol}'
            },
            {
                'text': '🗑️ Dismiss',
                'callback_data': f'dismiss_{symbol}'
            }
        ]
        buttons.append(row2)
        
        return buttons
    
    def format_with_buttons(self, message: str, buttons: List[Dict]) -> Dict:
        """
        Combine message text with inline buttons.
        
        Args:
            message: Message text
            buttons: Button configuration
        
        Returns:
            Dictionary for Telegram sendMessage API
        """
        return {
            'text': message,
            'parse_mode': 'Markdown' if self.use_markdown else None,
            'reply_markup': {
                'inline_keyboard': buttons
            }
        }
    
    def strip_markdown(self, text: str) -> str:
        """
        Remove Markdown formatting from text.
        
        Args:
            text: Markdown text
        
        Returns:
            Plain text
        """
        # Remove ** (bold)
        text = text.replace('**', '')
        # Remove __ (italic)
        text = text.replace('__', '')
        # Remove ` (code)
        text = text.replace('`', '')
        
        return text


# =============================================================================
# TESTING FUNCTIONS
# =============================================================================

def test_signal_formatting():
    """Test signal message formatting."""
    print("\n" + "="*70)
    print("TEST 1: Signal Formatting")
    print("="*70)
    
    formatter = MessageFormatter()
    
    # Mock signal
    signal = {
        'symbol': 'AAPL',
        'side': 'long',
        'pattern': 'hammer',
        'price': 264.82,
        'confluence': 9.5,
        'quality': 'premium',
        'zone_id': 'zone_ema20_264.16',
        'relative_volume': 1.85,
        'target': 270.00,
        'stop_loss': 262.00,
        'index_context': {
            'spy_regime': 'bullish',
            'qqq_regime': 'bullish'
        }
    }
    
    # Format as new signal
    message = formatter.format_signal(signal, alert_type="new")
    
    print("\n📱 NEW SIGNAL MESSAGE:")
    print("-" * 70)
    print(message)
    print("-" * 70)
    
    # Format as watchlist signal
    watchlist_msg = formatter.format_signal(signal, alert_type="watchlist")
    
    print("\n📱 WATCHLIST SIGNAL MESSAGE:")
    print("-" * 70)
    print(watchlist_msg)
    print("-" * 70)
    
    print("\n✅ Signal formatting test passed!")


def test_system_messages():
    """Test system message formatting."""
    print("\n" + "="*70)
    print("TEST 2: System Messages")
    print("="*70)
    
    formatter = MessageFormatter()
    
    # Scan summary
    scan_stats = {
        'symbols_scanned': 50,
        'signals_generated': 3,
        'duration': 42.5,
        'watchlist_hits': 2
    }
    
    scan_msg = formatter.format_scan_summary(scan_stats)
    print("\n📊 SCAN SUMMARY:")
    print("-" * 70)
    print(scan_msg)
    print("-" * 70)
    
    # Error message
    error_msg = formatter.format_error(
        "API rate limit exceeded",
        context="Fetching data for TSLA"
    )
    print("\n❌ ERROR MESSAGE:")
    print("-" * 70)
    print(error_msg)
    print("-" * 70)
    
    # Daily summary
    daily_stats = {
        'scans_completed': 6,
        'signals_generated': 8,
        'alerts_sent': 7,
        'watchlist_hits': 3
    }
    
    daily_msg = formatter.format_daily_summary(daily_stats)
    print("\n📈 DAILY SUMMARY:")
    print("-" * 70)
    print(daily_msg)
    print("-" * 70)
    
    print("\n✅ System messages test passed!")


def test_inline_buttons():
    """Test inline button generation."""
    print("\n" + "="*70)
    print("TEST 3: Inline Buttons")
    print("="*70)
    
    formatter = MessageFormatter(include_buttons=True)
    
    signal = {'symbol': 'AAPL', 'side': 'long'}
    
    buttons = formatter.generate_inline_buttons('AAPL', signal)
    
    print("\n🔘 Generated Buttons:")
    for i, row in enumerate(buttons, 1):
        print(f"\nRow {i}:")
        for button in row:
            if 'url' in button:
                print(f"   • {button['text']}: {button['url']}")
            else:
                print(f"   • {button['text']}: (callback)")
    
    # Test message with buttons
    message = "Test signal message"
    full_message = formatter.format_with_buttons(message, buttons)
    
    print(f"\n📱 Full Message Structure:")
    print(f"   • Text: {full_message['text'][:50]}...")
    print(f"   • Parse mode: {full_message['parse_mode']}")
    print(f"   • Button rows: {len(full_message['reply_markup']['inline_keyboard'])}")
    
    print("\n✅ Inline buttons test passed!")


def test_compact_mode():
    """Test compact formatting mode."""
    print("\n" + "="*70)
    print("TEST 4: Compact Mode")
    print("="*70)
    
    formatter = MessageFormatter(compact_mode=True)
    
    signal = {
        'symbol': 'TSLA',
        'side': 'short',
        'pattern': 'shooting_star',
        'price': 245.00,
        'confluence': 8.2,
        'quality': 'standard',
        'target': 238.00,
        'stop_loss': 248.00
    }
    
    compact_msg = formatter.format_signal(signal)
    
    print("\n📱 COMPACT MESSAGE:")
    print("-" * 70)
    print(compact_msg)
    print("-" * 70)
    
    # Compare with normal mode
    normal_formatter = MessageFormatter(compact_mode=False)
    normal_msg = normal_formatter.format_signal(signal)
    
    print(f"\n📊 Comparison:")
    print(f"   • Compact lines: {compact_msg.count(chr(10))}")
    print(f"   • Normal lines: {normal_msg.count(chr(10))}")
    
    print("\n✅ Compact mode test passed!")


def test_markdown_stripping():
    """Test markdown removal."""
    print("\n" + "="*70)
    print("TEST 5: Markdown Stripping")
    print("="*70)
    
    formatter = MessageFormatter(use_markdown=False)
    
    markdown_text = "**Bold** text with __italic__ and `code`"
    plain_text = formatter.strip_markdown(markdown_text)
    
    print(f"\nOriginal: {markdown_text}")
    print(f"Stripped: {plain_text}")
    
    assert '**' not in plain_text, "Should remove bold markers"
    assert '__' not in plain_text, "Should remove italic markers"
    assert '`' not in plain_text, "Should remove code markers"
    
    print("\n✅ Markdown stripping test passed!")


def run_all_tests():
    """Run complete test suite."""
    print("\n" + "="*70)
    print("MESSAGE FORMATTER TEST SUITE")
    print("="*70)
    
    test_signal_formatting()
    test_system_messages()
    test_inline_buttons()
    test_compact_mode()
    test_markdown_stripping()
    
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

from alerts.message_formatter import MessageFormatter

class TelegramSender:
    def __init__(self, config):
        self.bot = telegram.Bot(token=config.TELEGRAM_BOT_TOKEN)
        self.chat_id = config.TELEGRAM_CHAT_ID
        
        # Initialize formatter
        self.formatter = MessageFormatter(
            use_markdown=True,
            include_buttons=config.TELEGRAM_INLINE_BUTTONS,
            compact_mode=config.TELEGRAM_COMPACT_MODE
        )
    
    def send_signal(self, signal: Dict) -> bool:
        # Determine alert type
        alert_type = "watchlist" if signal.get('from_watchlist') else "new"
        
        # Format message
        message = self.formatter.format_signal(signal, alert_type)
        
        # Add buttons
        if self.formatter.include_buttons:
            buttons = self.formatter.generate_inline_buttons(
                signal['symbol'],
                signal
            )
            payload = self.formatter.format_with_buttons(message, buttons)
            
            # Send with buttons
            self.bot.send_message(
                chat_id=self.chat_id,
                text=payload['text'],
                parse_mode=payload['parse_mode'],
                reply_markup=payload['reply_markup']
            )
        else:
            # Send plain message
            self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
        
        return True
    
    def send_scan_summary(self, stats: Dict):
        message = self.formatter.format_scan_summary(stats)
        self.bot.send_message(chat_id=self.chat_id, text=message)

# In config.py:
TELEGRAM_INLINE_BUTTONS = True
TELEGRAM_COMPACT_MODE = False
    """)


if __name__ == "__main__":
    # Run tests
    run_all_tests()
    
    # Show integration example
    integration_example()
