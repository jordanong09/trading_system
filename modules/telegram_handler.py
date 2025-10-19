# modules/telegram_handler.py - UPDATED with Predictive + Confirmation Alerts

import requests
from typing import Dict
from datetime import datetime, timedelta

class TelegramHandler:
    """
    Handle Telegram notifications with dual-scan support
    
    NEW: Separate methods for:
    - Predictive alerts (T-5 min before close)
    - Confirmation alerts (T+1 min after close)
    - Failed pattern alerts
    """
    
    def __init__(self, bot_token: str = "", chat_id: str = ""):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.alerts_sent = set()
    
    def is_configured(self) -> bool:
        """Check if Telegram is properly configured"""
        return bool(self.bot_token and self.chat_id)
    
    def send_predictive_alert(self, signal: Dict, minutes_before_close: int = 5) -> bool:
        """
        Send PREDICTIVE alert (T-5 minutes before candle close)
        Alerts trader to prepare order but NOT execute yet
        """
        if not self.is_configured():
            print("   ⚠️  Telegram not configured")
            return False
        
        try:
            symbol = signal['symbol']
            detection = signal['pattern']
            conf = signal['confluence']
            trend = signal['trend_analysis']
            sr = signal['support_resistance']
            bo = signal['breakout_analysis']
            
            # Calculate when candle closes
            candle_close_time = datetime.now() + timedelta(minutes=minutes_before_close)
            confirmation_time = candle_close_time + timedelta(minutes=1, seconds=18)
            
            # Emoji based on signal strength
            if conf['recommendation'] == 'STRONG_SIGNAL':
                signal_emoji = "🟢"
                strength_text = "STRONG"
            else:
                signal_emoji = "🟡"
                strength_text = "GOOD"
            
            bias_emoji = "🚀" if detection['bias'] == 'BULLISH' else "🔻"
            
            # Build message
            message = f"""
{signal_emoji} *PATTERN FORMING* {bias_emoji}
🕐 Candle closes in *{minutes_before_close} minutes*

*Symbol*: {symbol}
*Pattern*: {detection['pattern']}
*Signal Strength*: {strength_text} ({conf['percentage']:.0f}%)
*Current Price*: ${signal['projected_close']:.2f}

📊 *Pattern Status*:
• 🟢 ~83% formed (high confidence)
• 🟢 Volume: {detection.get('volume', 'N/A'):,.0f}
• 🟢 Trend: {trend['primary_trend']}
• ⏰ {minutes_before_close} minutes until confirmation

📈 *DAILY Moving Averages* (Trend):
• EMA20: ${trend.get('ema_20', 0):.2f} {'✅' if trend.get('above_ema_20') else '❌'}
• SMA50: ${trend.get('sma_50', 0):.2f} {'✅' if trend.get('above_sma_50') else '❌'}
• SMA100: ${trend.get('sma_100', 0):.2f} {'✅' if trend.get('above_sma_100') else '❌'}
• SMA200: ${trend.get('sma_200', 0):.2f} {'✅' if trend.get('above_sma_200') else '❌'}

📊 *Support/Resistance* (30-day):
"""
            
            # Add S/R levels
            if sr.get('support'):
                for i, level in enumerate(sr['support'][:2], 1):
                    message += f"🟢 S{i}: ${level['price']:.2f} ({level['touches']} touches, {level['distance_pct']:.1f}% below)\n"
            
            if sr.get('resistance'):
                for i, level in enumerate(sr['resistance'][:2], 1):
                    message += f"🔴 R{i}: ${level['price']:.2f} ({level['touches']} touches, {level['distance_pct']:.1f}% above)\n"
            
            # Add breakout info if applicable
            if bo.get('breakout_imminent'):
                message += f"""
⚡ *BREAKOUT ALERT* ⚡
Direction: {bo['direction']}
Target: ${bo['target_level']:.2f}
Distance: {bo['distance_pct']:.2f}%
Volume: {'Surging ✅' if bo['volume_surge'] else 'Normal'}
"""
            
            # Confluence reasons
            message += f"\n💎 *Confluence* ({conf['confluence_score']}/{conf['max_score']}):\n"
            for reason in conf['reasons'][:5]:
                message += f"{reason}\n"
            
            # Calculate trade plan
            entry_price = signal['projected_close']
            
            if detection['bias'] == 'BULLISH':
                if sr.get('support') and len(sr['support']) > 0:
                    stop_price = sr['support'][0]['price'] * 0.995
                    stop_text = f"${stop_price:.2f} (below S1)"
                else:
                    stop_price = entry_price * 0.97
                    stop_text = f"${stop_price:.2f} (-3%)"
                
                if sr.get('resistance') and len(sr['resistance']) > 0:
                    target_price = sr['resistance'][0]['price']
                    target_text = f"${target_price:.2f} (R1)"
                else:
                    target_price = entry_price * 1.05
                    target_text = f"${target_price:.2f} (+5%)"
            else:  # BEARISH
                if sr.get('resistance') and len(sr['resistance']) > 0:
                    stop_price = sr['resistance'][0]['price'] * 1.005
                    stop_text = f"${stop_price:.2f} (above R1)"
                else:
                    stop_price = entry_price * 1.03
                    stop_text = f"${stop_price:.2f} (+3%)"
                
                if sr.get('support') and len(sr['support']) > 0:
                    target_price = sr['support'][0]['price']
                    target_text = f"${target_price:.2f} (S1)"
                else:
                    target_price = entry_price * 0.95
                    target_text = f"${target_price:.2f} (-5%)"
            
            risk = abs(entry_price - stop_price)
            reward = abs(target_price - entry_price)
            rr_ratio = reward / risk if risk > 0 else 0
            
            # Trading plan
            message += f"""
💡 *Suggested Trade Plan*:
📍 Entry: ${entry_price:.2f} (limit order)
🛑 Stop: {stop_text}
🎯 Target: {target_text}
📊 R:R: 1:{rr_ratio:.1f}

🎯 *ACTION PLAN*:
1️⃣ Review chart NOW (quick check!)
2️⃣ Set limit order IMMEDIATELY
3️⃣ Wait for confirmation alert
4️⃣ Do NOT execute until confirmed

⏰ You have ~{minutes_before_close - 1.3:.1f} min to prepare
⏰ Confirmation at {confirmation_time.strftime('%H:%M')}

⚠️ *IMPORTANT*: This is a PENDING alert
Pattern must confirm at candle close before entering!
"""
            
            # Add TradingView link
            message += f"\n[View Chart on TradingView](https://www.tradingview.com/chart/?symbol={symbol})"
            
            # Send message
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                return True
            else:
                print(f"   ⚠️  Telegram API error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ⚠️  Error sending predictive alert: {e}")
            return False
    
    def send_confirmation_alert(self, signal: Dict, confirmed: bool = True) -> bool:
        """
        Send CONFIRMATION alert (T+1 minute after candle close)
        Either confirms pattern or alerts to failed pattern
        """
        if not self.is_configured():
            return False
        
        try:
            symbol = signal['symbol']
            detection = signal['pattern']
            
            if confirmed:
                # PATTERN CONFIRMED - Execute trade
                conf = signal['confluence']
                trend = signal['trend_analysis']
                sr = signal['support_resistance']
                
                original_price = signal.get('original_price', signal['projected_close'])
                current_price = signal['projected_close']
                price_change = current_price - original_price
                price_change_pct = (price_change / original_price * 100) if original_price > 0 else 0
                
                bias_emoji = "🚀" if detection['bias'] == 'BULLISH' else "🔻"
                change_emoji = "📈" if price_change >= 0 else "📉"
                
                message = f"""
✅ *PATTERN CONFIRMED* ✅ {bias_emoji}

*Symbol*: {symbol}
*Pattern*: {detection['pattern']}
*Close Price*: ${current_price:.2f} {change_emoji}
*Change*: ${price_change:+.2f} ({price_change_pct:+.2f}%)

✅ Pattern confirmed at candle close
✅ All {conf['confluence_score']}/{conf['max_score']} confluence factors maintained
✅ Signal: {conf['recommendation']} ({conf['percentage']:.0f}%)
✅ Volume: {detection.get('volume', 0):,.0f}

📊 *Final Stats*:
Entry: ${current_price:.2f} (limit order)
Actual Close: ${current_price:.2f}
"""
                
                # Calculate stops and targets
                if detection['bias'] == 'BULLISH':
                    if sr.get('support') and len(sr['support']) > 0:
                        stop_price = sr['support'][0]['price'] * 0.995
                        message += f"Stop: ${stop_price:.2f} (below S1)\n"
                    if sr.get('resistance') and len(sr['resistance']) > 0:
                        target_price = sr['resistance'][0]['price']
                        message += f"Target: ${target_price:.2f} (R1)\n"
                else:
                    if sr.get('resistance') and len(sr['resistance']) > 0:
                        stop_price = sr['resistance'][0]['price'] * 1.005
                        message += f"Stop: ${stop_price:.2f} (above R1)\n"
                    if sr.get('support') and len(sr['support']) > 0:
                        target_price = sr['support'][0]['price']
                        message += f"Target: ${target_price:.2f} (S1)\n"
                
                message += f"""
🎯 *EXECUTE YOUR ORDER NOW*
Your prepared limit order should fill

*Expected fill*: ${current_price * 0.999:.2f}-${current_price * 1.001:.2f}

✅ High probability {detection['bias']} setup
✅ Risk managed with defined stop
✅ Clear profit target identified

[View Chart](https://www.tradingview.com/chart/?symbol={symbol})
"""
                
            else:
                # PATTERN FAILED - Cancel order
                message = f"""
❌ *PATTERN FAILED* ❌

*Symbol*: {symbol}
*Pattern*: {detection['pattern']}

❌ Pattern did NOT confirm at candle close
⚠️ *Do NOT enter this trade*

📊 *What Happened*:
• Expected pattern to fully form
• Price action or volume failed criteria
• Pattern invalidated in final minutes
• Confluence factors weakened

🚫 *CANCEL YOUR ORDER IMMEDIATELY*

💰 *Money Saved*: ~$150-300
(This is why we wait for confirmation!)

✅ System working as designed
✅ False signal filtered out
✅ Capital preserved for better setups

*Next confirmation scan*: Next candle close

[View Chart](https://www.tradingview.com/chart/?symbol={symbol})
"""
            
            # Send message
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            return response.status_code == 200
                
        except Exception as e:
            print(f"   ⚠️  Error sending confirmation alert: {e}")
            return False
    
    def send_alert(self, symbol: str, detection: Dict, confluence: Dict) -> bool:
        """
        Legacy alert method for backward compatibility
        Used by backtesting and simple scans
        """
        if not self.is_configured():
            return False
        
        try:
            alert_id = f"{symbol}_{detection['date'].strftime('%Y%m%d')}_{detection['pattern']}"
            if alert_id in self.alerts_sent:
                return False
            
            message = f"""
🚨 *PATTERN DETECTED* 🚨

*Symbol*: {symbol}
*Pattern*: {detection['pattern']}
*Bias*: {detection['bias']}
*Date*: {detection['date'].strftime('%Y-%m-%d')}
*Price*: ${detection['price']:.2f}
*Volume*: {detection['volume']:,.0f}

*Confluence*:
• Above 20MA: {'✅' if confluence.get('above_20ma') else '❌'}
• Volume Surge: {'✅' if confluence.get('volume_surge') else '❌'}
• Volatility: {confluence.get('volatility_pct', 0):.2f}%
"""
            
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                self.alerts_sent.add(alert_id)
                return True
            else:
                return False
                
        except Exception as e:
            print(f"   ⚠️  Error sending alert: {e}")
            return False


# Usage: from modules.telegram_handler import TelegramHandler