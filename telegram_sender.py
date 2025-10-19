#!/usr/bin/env python3
"""
telegram_sender.py - Safe Telegram Message Sender
Handles all formatting, escaping, and error logging correctly
"""

import os
import html
import requests
from typing import Dict, Optional
from datetime import datetime


class TelegramSender:
    """
    Safe Telegram sender with proper HTML escaping
    Logs all errors with full response details
    """
    
    def __init__(self, bot_token: str = None, chat_id: str = None):
        """
        Initialize Telegram sender
        
        Args:
            bot_token: Telegram bot token (or uses env TELEGRAM_BOT_TOKEN)
            chat_id: Telegram chat ID (or uses env TELEGRAM_CHAT_ID)
        """
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = str(chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")).strip()
        
        if not self.bot_token or not self.chat_id:
            raise ValueError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
        
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.alerts_sent = set()
    
    @staticmethod
    def escape(text) -> str:
        """HTML-escape text for safe formatting"""
        return html.escape("" if text is None else str(text), quote=False)
    
    def is_configured(self) -> bool:
        """Check if sender is properly configured"""
        return bool(self.bot_token and self.chat_id)
    
    def send_message(self, text: str, parse_mode: str = "HTML", 
                     silent: bool = False) -> bool:
        """
        Send message to Telegram
        
        Args:
            text: Message text (already formatted/escaped if using HTML)
            parse_mode: "HTML", "Markdown", or None for plain text
            silent: If True, sends without notification sound
        
        Returns:
            True if sent successfully, False otherwise
        """
        url = f"{self.base_url}/sendMessage"
        
        payload = {
            "chat_id": self.chat_id,
            "text": text
        }
        
        if parse_mode:
            payload["parse_mode"] = parse_mode
        
        if silent:
            payload["disable_notification"] = True
        
        try:
            response = requests.post(url, json=payload, timeout=15)
            
            # Always log the result
            if response.ok:
                print(f"✅ Telegram message sent (HTTP {response.status_code})")
                return True
            else:
                print(f"❌ Telegram FAILED (HTTP {response.status_code})")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Telegram exception: {e}")
            return False
    
    def send_enhanced_alert(self, symbol: str, detection: Dict) -> bool:
        """
        Send enhanced trading alert
        
        Args:
            symbol: Stock symbol (e.g., "AAPL")
            detection: Dict with pattern, trend_analysis, confluence, etc.
        
        Returns:
            True if sent successfully
        """
        try:
            # Create unique alert ID to prevent duplicates
            pattern = detection.get('pattern', {})
            pattern_name = pattern.get('pattern', 'UNKNOWN')
            alert_id = f"{symbol}_{pattern_name}_{datetime.now().strftime('%Y%m%d%H%M')}"
            
            if alert_id in self.alerts_sent:
                print(f"⏭️  Skipping duplicate alert: {alert_id}")
                return False
            
            # Extract data
            pattern_name = pattern.get('pattern', 'UNKNOWN')
            bias = pattern.get('bias', 'UNKNOWN')
            price = pattern.get('price', 0)
            
            trend = detection.get('trend_analysis', {})
            conf = detection.get('confluence', {})
            sr = detection.get('support_resistance', {})
            bo = detection.get('breakout_analysis', {})
            
            # Build message with safe HTML escaping
            e = self.escape  # Shorthand
            
            # Signal strength emoji
            signal_strength = conf.get('recommendation', 'UNKNOWN')
            emoji = "🟢" if signal_strength == 'STRONG_SIGNAL' else "🟡"
            
            msg = f"""<b>{emoji} ENHANCED PREDICTIVE SIGNAL 🔮 {emoji}</b>

⚠️ <b>PENDING CANDLE CLOSE</b> ⚠️

<b>Symbol:</b> {e(symbol)}
<b>Pattern:</b> {e(pattern_name)}
<b>Bias:</b> {e(bias)}
<b>Signal:</b> {e(signal_strength)} ({conf.get('percentage', 0):.0f}%)

<b>Current Price:</b> ${price:.2f}

<b>DAILY Moving Averages (Trend):</b>
📈 Primary Trend: {e(trend.get('primary_trend', 'UNKNOWN'))}
"""
            
            # Add moving averages
            for ma_name, ma_key in [
                ('EMA20', 'ema_20'),
                ('SMA50', 'sma_50'),
                ('SMA100', 'sma_100'),
                ('SMA200', 'sma_200')
            ]:
                ma_value = trend.get(ma_key)
                above_key = f"above_{ma_key}"
                is_above = trend.get(above_key)
                
                if ma_value:
                    check = "✅" if is_above else "❌"
                    msg += f"• {ma_name}: ${ma_value:.2f} {check}\n"
            
            # Add horizontal S/R levels
            msg += "\n<b>Horizontal Support/Resistance (30-day):</b>\n"
            
            support_levels = sr.get('support', [])
            for i, level in enumerate(support_levels[:2], 1):
                msg += (f"🟢 S{i}: ${level['price']:.2f} "
                       f"({level['touches']} touches, {level['distance_pct']:.1f}% below)\n")
            
            resistance_levels = sr.get('resistance', [])
            for i, level in enumerate(resistance_levels[:2], 1):
                msg += (f"🔴 R{i}: ${level['price']:.2f} "
                       f"({level['touches']} touches, {level['distance_pct']:.1f}% above)\n")
            
            # Add breakout analysis if present
            if bo.get('breakout_imminent'):
                msg += f"\n<b>⚡ BREAKOUT ALERT ⚡</b>\n"
                msg += f"Direction: {e(bo['direction'])}\n"
                msg += f"Target: ${bo['target_level']:.2f}\n"
                msg += f"Distance: {bo['distance_pct']:.2f}%\n"
                msg += f"Volume: {'Surging ✅' if bo.get('volume_surge') else 'Normal'}\n"
            
            # Add confluence reasons
            msg += f"\n<b>Confluence ({conf['confluence_score']}/{conf['max_score']}):</b>\n"
            for reason in conf.get('reasons', [])[:5]:
                msg += f"{reason}\n"
            
            # Add trading plan
            msg += "\n<b>💡 Trading Plan:</b>\n"
            msg += f"1️⃣ Prepare limit order now\n"
            msg += f"2️⃣ Entry: ${price:.2f}\n"
            
            if bias == 'BULLISH':
                if support_levels:
                    stop_level = support_levels[0]['price'] * 0.995
                    msg += f"3️⃣ Stop: ${stop_level:.2f} (below support)\n"
                if resistance_levels:
                    target_level = resistance_levels[0]['price']
                    msg += f"4️⃣ Target: ${target_level:.2f} (resistance)\n"
            else:
                if resistance_levels:
                    stop_level = resistance_levels[0]['price'] * 1.005
                    msg += f"3️⃣ Stop: ${stop_level:.2f} (above resistance)\n"
                if support_levels:
                    target_level = support_levels[0]['price']
                    msg += f"4️⃣ Target: ${target_level:.2f} (support)\n"
            
            msg += f"\n✅ High probability {bias} setup"
            
            # Send the message
            success = self.send_message(msg, parse_mode="HTML", silent=False)
            
            if success:
                self.alerts_sent.add(alert_id)
                print(f"   ✅ Enhanced alert sent: {symbol}")
            else:
                print(f"   ⚠️  Alert failed: {symbol}")
            
            return success
            
        except Exception as e:
            print(f"   ❌ Error building alert for {symbol}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def send_simple_alert(self, symbol: str, pattern: str, price: float,
                         bias: str = "UNKNOWN", volume: int = None) -> bool:
        """
        Send simple trading alert (backward compatible)
        
        Args:
            symbol: Stock symbol
            pattern: Pattern name (e.g., "BULLISH_ENGULFING")
            price: Current price
            bias: "BULLISH" or "BEARISH"
            volume: Optional volume
        
        Returns:
            True if sent successfully
        """
        e = self.escape
        
        msg = f"""<b>🚨 TRADING ALERT 🚨</b>

<b>Symbol:</b> {e(symbol)}
<b>Pattern:</b> {e(pattern)}
<b>Bias:</b> {e(bias)}
<b>Price:</b> ${price:.2f}
"""
        
        if volume:
            msg += f"<b>Volume:</b> {volume:,}\n"
        
        msg += f"\n<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return self.send_message(msg, parse_mode="HTML")
    
    def test_connection(self) -> bool:
        """
        Test Telegram connection with a simple message
        
        Returns:
            True if test message sent successfully
        """
        test_msg = f"🔔 Test message from trading scanner\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return self.send_message(test_msg, parse_mode=None, silent=True)


# ============================================================================
# STANDALONE USAGE
# ============================================================================
if __name__ == "__main__":
    """Test the sender when run directly"""
    print("\n🔧 Testing Telegram Sender...\n")
    
    try:
        sender = TelegramSender()
        
        # Test 1: Connection
        print("Test 1: Connection test")
        if sender.test_connection():
            print("✅ Connection successful\n")
        else:
            print("❌ Connection failed\n")
            exit(1)
        
        # Test 2: Simple alert
        print("Test 2: Simple alert")
        sender.send_simple_alert(
            symbol="TEST",
            pattern="BULLISH_ENGULFING",
            price=150.25,
            bias="BULLISH",
            volume=1000000
        )
        
        # Test 3: Full enhanced alert (mock data)
        print("\nTest 3: Enhanced alert")
        mock_detection = {
            'symbol': 'TEST',
            'pattern': {
                'pattern': 'BULLISH_ENGULFING',
                'bias': 'BULLISH',
                'price': 150.75
            },
            'trend_analysis': {
                'primary_trend': 'BULLISH',
                'ema_20': 148.50,
                'sma_50': 145.00,
                'sma_100': 142.00,
                'sma_200': 140.00,
                'above_ema_20': True,
                'above_sma_50': True,
                'above_sma_100': True,
                'above_sma_200': True
            },
            'confluence': {
                'confluence_score': 6,
                'max_score': 7,
                'percentage': 86,
                'recommendation': 'STRONG_SIGNAL',
                'reasons': [
                    '✅ Pattern aligns with BULLISH trend',
                    '✅ Price above SMA200',
                    '✅ Near support'
                ]
            },
            'support_resistance': {
                'support': [
                    {'price': 148.00, 'touches': 4, 'distance_pct': 1.8}
                ],
                'resistance': [
                    {'price': 152.50, 'touches': 5, 'distance_pct': 1.2}
                ]
            },
            'breakout_analysis': {
                'breakout_imminent': True,
                'direction': 'BULLISH',
                'target_level': 152.50,
                'distance_pct': 1.2,
                'volume_surge': True
            }
        }
        
        sender.send_enhanced_alert('TEST', mock_detection)
        
        print("\n✅ All tests complete!\n")
        
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("   Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables")
        exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)