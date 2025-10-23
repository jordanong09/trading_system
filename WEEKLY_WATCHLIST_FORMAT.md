# Weekly Watchlist Implementation Guide
## Enhanced Format with Timeframes, Trade Types, and Market Context

**Version:** 1.0  
**Date:** October 23, 2025

---

## Overview

This guide specifies the enhanced weekly watchlist message format that includes:
- **Prominent market context** (SPY/QQQ trending at top)
- **Timeframe indicators** for each pattern detected
- **Trade type classification** (Position vs Swing)
- **Bias indicators** (Bullish/Bearish with emojis)
- **Market alignment warnings** (counter-trend alerts)

---

## Message Structure

### 1. Header Section

```
🗓️ WEEKLY WATCHLIST
Week of [Start Date] - [End Date], [Year]
```

---

### 2. Market Backdrop Section (NEW - CRITICAL)

**Purpose:** Immediately show traders the market regime so they know which setups to favor.

**Format:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━
📊 MARKET BACKDROP - CRITICAL
━━━━━━━━━━━━━━━━━━━━━━━━━

🇺🇸 SPY (S&P 500): $[PRICE]
Trend: [EMOJI] [TREND_STRENGTH]
• Above EMA20 [✅/❌] ([+/-]X.X%)
• Above SMA50 [✅/❌] ([+/-]X.X%)
• Above SMA200 [✅/❌] ([+/-]X.X%)
Weekly: [+/-]X.X%

💻 QQQ (Nasdaq): $[PRICE]
Trend: [EMOJI] [TREND_STRENGTH]
• Above EMA20 [✅/❌] ([+/-]X.X%)
• Above SMA50 [✅/❌] ([+/-]X.X%)
• Above SMA200 [✅/❌] ([+/-]X.X%)
Weekly: [+/-]X.X%

⚠️ REGIME: [REGIME_STATUS]
Best focus: [GUIDANCE]
Avoid: [WARNING]

━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Trend Strength Rules:**

| MAs Above | Emoji | Trend Strength |
|-----------|-------|----------------|
| 3/3 (EMA20, SMA50, SMA200) | 🟢 | STRONG BULLISH |
| 2/3 | 🟡 | MODERATE BULLISH |
| 1/3 | 🟠 | WEAK BULLISH |
| 0/3 | 🔴 | BEARISH |

**Regime Status Rules:**

| SPY Trend | QQQ Trend | Regime Status | Best Focus | Avoid |
|-----------|-----------|---------------|------------|-------|
| 🟢 STRONG | 🟢 STRONG | BULLISH | Bullish setups with market | Counter-trend bearish plays |
| 🟢 STRONG | 🟡 MODERATE | BULLISH | Bullish setups, selective tech | Weak tech bearish plays |
| 🟡 MODERATE | 🟡 MODERATE | MIXED | Both setups, lower size | Aggressive swings |
| 🔴 BEARISH | 🔴 BEARISH | BEARISH | Bearish setups with market | Counter-trend bullish plays |

**Example - Bullish Market:**
```
🇺🇸 SPY (S&P 500): $585.40
Trend: 🟢 STRONG BULLISH
• Above EMA20 ✅ (+1.2%)
• Above SMA50 ✅ (+3.8%)
• Above SMA200 ✅ (+8.5%)
Weekly: +2.3%

💻 QQQ (Nasdaq): $495.20
Trend: 🟢 STRONG BULLISH
• Above EMA20 ✅ (+1.5%)
• Above SMA50 ✅ (+4.2%)
• Above SMA200 ✅ (+10.1%)
Weekly: +3.1%

⚠️ REGIME: BULLISH
Best focus: Bullish setups with market
Avoid: Counter-trend bearish plays
```

**Example - Bearish Market:**
```
🇺🇸 SPY (S&P 500): $565.20
Trend: 🔴 BEARISH
• Above EMA20 ❌ (-1.5%)
• Above SMA50 ❌ (-2.8%)
• Above SMA200 ✅ (+0.5%)
Weekly: -3.2%

💻 QQQ (Nasdaq): $475.80
Trend: 🔴 BEARISH
• Above EMA20 ❌ (-2.1%)
• Above SMA50 ❌ (-3.5%)
• Above SMA200 ❌ (-1.2%)
Weekly: -4.5%

⚠️ REGIME: BEARISH
Best focus: Bearish setups with market
Avoid: Counter-trend bullish plays
```

---

### 3. Bullish Setups Section

**Format:**
```
🟢 BULLISH SETUPS ([COUNT] stocks)

━━━━━━━━━━━━━━━━━━━━━━━━━
📈 [SYMBOL] - $[PRICE]
━━━━━━━━━━━━━━━━━━━━━━━━━
Type: 🎯 [TRADE_TYPE] ([DURATION])
Bias: 🟢 BULLISH

Patterns Detected:
• [Timeframe] [Pattern Type]: [Pattern Name] ([Details])
  → [Context/Success Rate]
• [Timeframe] [Pattern Type]: [Pattern Name] ([Details])
  → [Context/Success Rate]
• [Timeframe] [Pattern Type]: [Pattern Name] ([Details])
  → [Context/Success Rate]

Key Levels:
[Entry/Breakout info] | [Target info]

Confluence: [SCORE]/12 [STARS] [RATING]
```

**Trade Type Classification:**

Based on the **longest-duration** pattern detected:

| Pattern Timeframe | Trade Type | Duration | Emoji |
|-------------------|------------|----------|-------|
| Daily Chart Pattern | POSITION TRADE | 1-4 months | 🎯 |
| Daily Candlestick | SWING TRADE | 1-4 weeks | 🎯 |
| 1H Candlestick only | INTRADAY TRADE | Same day | ⚡ |

**Bias Indicators:**

| Bias | Emoji | Color |
|------|-------|-------|
| BULLISH | 🟢 | Green |
| BEARISH | 🔴 | Red |

**Pattern Timeframe Labels:**

| Data Used | Label Format | Example |
|-----------|-------------|---------|
| Daily Chart | "Daily Chart: [Pattern]" | Daily Chart: Cup & Handle |
| Daily Candlestick | "Daily Candle: [Pattern] (Friday)" | Daily Candle: Hammer at EMA20 (Friday) |
| 1H Candlestick | "1H Candle: [Pattern]" | 1H Candle: Three White Soldiers |

**Confluence Rating:**

| Score | Stars | Rating |
|-------|-------|--------|
| 9-12/12 | ⭐⭐ | EXCEPTIONAL |
| 8/12 | ⭐ | STRONG |
| 7/12 | ⭐ | GOOD |

**Example - Position Trade:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━
📈 AAPL - $185.40
━━━━━━━━━━━━━━━━━━━━━━━━━
Type: 🎯 POSITION TRADE (1-4 months)
Bias: 🟢 BULLISH

Patterns Detected:
• Daily Chart: Cup & Handle (95% complete)
  → Classic 1-4 month continuation pattern
• Daily Candle: Hammer at EMA20 (Friday)
  → 72% success rate at MA bounces
• 1H Candle: Three White Soldiers
  → Strong Friday close, institutional buying

Key Levels:
Breakout: $187.50 | Target: $197 (+6.2%)

Confluence: 9/12 ⭐⭐ EXCEPTIONAL
```

**Example - Swing Trade:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━
📈 MSFT - $415.20  
━━━━━━━━━━━━━━━━━━━━━━━━━
Type: 🎯 SWING TRADE (2-4 weeks)
Bias: 🟢 BULLISH

Patterns Detected:
• Daily Chart: Ascending Triangle
  → 72% success rate, 2-4 week pattern
• Daily Candle: Bullish Engulfing (Friday)
  → Strong reversal signal
• 1H Candle: Morning Star
  → Intraday confirmation

Key Levels:
Breakout: $420 | Target: $430 (+3.6%)

Confluence: 8/12 ⭐ STRONG
```

**Example - MA Bounce Setup (No Chart Pattern):**
```
━━━━━━━━━━━━━━━━━━━━━━━━━
📈 META - $565.30
━━━━━━━━━━━━━━━━━━━━━━━━━
Type: 🎯 SWING TRADE (1-2 weeks)
Bias: 🟢 BULLISH

Patterns Detected:
• Daily Candle: Hammer at EMA20
  → MA bounce setup, 60% success rate
• 1H Candle: Bullish Engulfing
  → Friday confirmation

Key Levels:
Support: $562 | Entry: $565-568

Confluence: 7/12 ⭐ GOOD
```

---

### 4. Bearish Setups Section (with Counter-Trend Warning)

**Format:**
```
🔴 BEARISH SETUPS ([COUNT] stocks)

━━━━━━━━━━━━━━━━━━━━━━━━━
📉 [SYMBOL] - $[PRICE]
━━━━━━━━━━━━━━━━━━━━━━━━━
Type: 🎯 [TRADE_TYPE] ([DURATION])
Bias: 🔴 BEARISH

[IF COUNTER-TREND]
⚠️ COUNTER-TREND: Market is [bullish/bearish]
[END IF]

Patterns Detected:
• [Timeframe] [Pattern Type]: [Pattern Name] ([Details])
  → [Context/Success Rate]
• [Timeframe] [Pattern Type]: [Pattern Name] ([Details])
  → [Context/Success Rate]

Key Levels:
[Breakdown info] | [Target info]

Confluence: [SCORE]/12 [STARS] [RATING]
[IF COUNTER-TREND]
Note: Wait for [SPY/QQQ] weakness for better odds
[END IF]
```

**Counter-Trend Detection:**

```python
# Pseudo-code
if (pattern_bias == "BEARISH" and market_regime == "BULLISH"):
    show_counter_trend_warning = True
    warning_text = "⚠️ COUNTER-TREND: Market is bullish"
    note_text = "Note: Wait for SPY weakness for better odds"

elif (pattern_bias == "BULLISH" and market_regime == "BEARISH"):
    show_counter_trend_warning = True
    warning_text = "⚠️ COUNTER-TREND: Market is bearish"
    note_text = "Note: Wait for SPY strength for better odds"
```

**Example - Bearish in Bullish Market:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━
📉 TSLA - $265.20
━━━━━━━━━━━━━━━━━━━━━━━━━
Type: 🎯 SWING TRADE (2-4 weeks)
Bias: 🔴 BEARISH

⚠️ COUNTER-TREND: Market is bullish

Patterns Detected:
• Daily Chart: Double Top forming
  → 79% success rate (very reliable)
• Daily Candle: Evening Star (Friday)
  → 69% success, reversal signal
• 1H Candle: Shooting Star
  → Friday rejection at resistance

Key Levels:
Breakdown: $258 | Target: $244 (-8.0%)

Confluence: 8/12 ⭐ STRONG
Note: Wait for SPY weakness for better odds
```

---

### 5. Summary Section

**Format:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━

📋 SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━

Stocks: [TOTAL] total ([BULLISH] bullish, [BEARISH] bearish)

By Quality:
• ⭐⭐ Exceptional (9-12/12): [COUNT] stocks
• ⭐ Strong (8/12): [COUNT] stocks
• ⭐ Good (7/12): [COUNT] stocks

By Trade Type:
• 🎯 Position Trades (1-4 months): [COUNT] stock(s)
• 🎯 Swing Trades (1-4 weeks): [COUNT] stocks

Market Alignment:
• With market ([bullish/bearish]): [COUNT] stocks ✅
• Counter-trend ([bearish/bullish]): [COUNT] stocks ⚠️

━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Example:**
```
📋 SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━

Stocks: 11 total (8 bullish, 3 bearish)

By Quality:
• ⭐⭐ Exceptional (9-12/12): 3 stocks
• ⭐ Strong (8/12): 5 stocks
• ⭐ Good (7/12): 3 stocks

By Trade Type:
• 🎯 Position Trades (1-4 months): 1 stock
• 🎯 Swing Trades (1-4 weeks): 10 stocks

Market Alignment:
• With market (bullish): 8 stocks ✅
• Counter-trend (bearish): 3 stocks ⚠️
```

---

### 6. Usage Instructions Section

**Format:**
```
⚠️ HOW TO USE THIS WATCHLIST
━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ ADD TO YOUR WATCHLIST
   Set price alerts at breakout levels

2️⃣ UNDERSTAND TIMEFRAMES
   • Daily Chart = Weeks to months hold
   • Daily Candle = Days to weeks setup
   • 1H Candle = Intraday confirmation

3️⃣ FAVOR MARKET ALIGNMENT
   With bullish market: Focus on 🟢 setups
   Avoid: Fighting the trend (🔴 counter-trend)

4️⃣ WAIT FOR CONFIRMATION
   These are WATCHLIST stocks, not trades yet
   Our intraday scanner will confirm when ready

5️⃣ BE PATIENT
   Not all will trigger this week
   Best setups take time to develop

━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### 7. Educational Note Section

**Format:**
```
💡 EDUCATIONAL NOTE

Pattern + Timeframe = Trade Duration:
• Daily Chart patterns → Position trades (weeks-months)
• Daily Candlesticks → Swing trades (days-weeks)
• 1H Candlesticks → Intraday confirmation only

Market regime matters:
• Bullish regime → Bullish setups easier, higher success
• Bearish regime → Bearish setups easier, higher success
• Counter-trend → Higher risk, wait for market shift

Trade type determines holding period:
• Position Trade: 1-4 months, fewer trades, larger moves
• Swing Trade: 1-4 weeks, moderate frequency
• Avoid mixing: Don't exit position trade after 3 days

━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### 8. Disclaimer Section

**Format:**
```
🔒 DISCLAIMER

This is market information and technical 
analysis for education and discussion. It is 
not financial advice and does not consider 
your personal objectives or financial situation. 
Past performance is not indicative of future 
results.

━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Implementation Code Structure

### Python Implementation

```python
class WeeklyWatchlistFormatter:
    """Format weekly watchlist with enhanced timeframe indicators"""
    
    def format_market_backdrop(self, spy_data, qqq_data):
        """Format prominent market context section"""
        spy_trend = self._calculate_trend_strength(spy_data)
        qqq_trend = self._calculate_trend_strength(qqq_data)
        regime = self._determine_regime(spy_trend, qqq_trend)
        
        msg = "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "📊 MARKET BACKDROP - CRITICAL\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # SPY section
        msg += f"🇺🇸 SPY (S&P 500): ${spy_data['close']:.2f}\n"
        msg += f"Trend: {spy_trend['emoji']} {spy_trend['strength']}\n"
        msg += f"• Above EMA20 {spy_trend['above_ema20_icon']} ({spy_trend['ema20_dist']:+.1f}%)\n"
        msg += f"• Above SMA50 {spy_trend['above_sma50_icon']} ({spy_trend['sma50_dist']:+.1f}%)\n"
        msg += f"• Above SMA200 {spy_trend['above_sma200_icon']} ({spy_trend['sma200_dist']:+.1f}%)\n"
        msg += f"Weekly: {spy_data['weekly_change']:+.1f}%\n\n"
        
        # QQQ section
        msg += f"💻 QQQ (Nasdaq): ${qqq_data['close']:.2f}\n"
        msg += f"Trend: {qqq_trend['emoji']} {qqq_trend['strength']}\n"
        msg += f"• Above EMA20 {qqq_trend['above_ema20_icon']} ({qqq_trend['ema20_dist']:+.1f}%)\n"
        msg += f"• Above SMA50 {qqq_trend['above_sma50_icon']} ({qqq_trend['sma50_dist']:+.1f}%)\n"
        msg += f"• Above SMA200 {qqq_trend['above_sma200_icon']} ({qqq_trend['sma200_dist']:+.1f}%)\n"
        msg += f"Weekly: {qqq_data['weekly_change']:+.1f}%\n\n"
        
        # Regime guidance
        msg += f"⚠️ REGIME: {regime['status']}\n"
        msg += f"Best focus: {regime['best_focus']}\n"
        msg += f"Avoid: {regime['avoid']}\n\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        return msg
    
    def _calculate_trend_strength(self, index_data):
        """Calculate trend strength from MA positions"""
        above_ema20 = index_data['close'] > index_data['ema20']
        above_sma50 = index_data['close'] > index_data['sma50']
        above_sma200 = index_data['close'] > index_data['sma200']
        
        mas_above = sum([above_ema20, above_sma50, above_sma200])
        
        if mas_above == 3:
            emoji = "🟢"
            strength = "STRONG BULLISH"
        elif mas_above == 2:
            emoji = "🟡"
            strength = "MODERATE BULLISH"
        elif mas_above == 1:
            emoji = "🟠"
            strength = "WEAK BULLISH"
        else:
            emoji = "🔴"
            strength = "BEARISH"
        
        return {
            'emoji': emoji,
            'strength': strength,
            'above_ema20': above_ema20,
            'above_ema20_icon': "✅" if above_ema20 else "❌",
            'ema20_dist': (index_data['close'] - index_data['ema20']) / index_data['ema20'] * 100,
            'above_sma50': above_sma50,
            'above_sma50_icon': "✅" if above_sma50 else "❌",
            'sma50_dist': (index_data['close'] - index_data['sma50']) / index_data['sma50'] * 100,
            'above_sma200': above_sma200,
            'above_sma200_icon': "✅" if above_sma200 else "❌",
            'sma200_dist': (index_data['close'] - index_data['sma200']) / index_data['sma200'] * 100,
        }
    
    def _determine_regime(self, spy_trend, qqq_trend):
        """Determine market regime from both indices"""
        spy_bullish = "BULLISH" in spy_trend['strength']
        qqq_bullish = "BULLISH" in qqq_trend['strength']
        
        if spy_bullish and qqq_bullish:
            return {
                'status': 'BULLISH',
                'best_focus': 'Bullish setups with market',
                'avoid': 'Counter-trend bearish plays'
            }
        elif not spy_bullish and not qqq_bullish:
            return {
                'status': 'BEARISH',
                'best_focus': 'Bearish setups with market',
                'avoid': 'Counter-trend bullish plays'
            }
        else:
            return {
                'status': 'MIXED',
                'best_focus': 'Both setups, lower position size',
                'avoid': 'Aggressive swings'
            }
    
    def format_stock_entry(self, stock, market_regime):
        """Format individual stock entry with timeframe indicators"""
        msg = "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"{'📈' if stock['bias'] == 'BULLISH' else '📉'} {stock['symbol']} - ${stock['price']:.2f}\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        # Trade type classification
        trade_type = self._classify_trade_type(stock['patterns'])
        msg += f"Type: 🎯 {trade_type['name']} ({trade_type['duration']})\n"
        msg += f"Bias: {'🟢 BULLISH' if stock['bias'] == 'BULLISH' else '🔴 BEARISH'}\n\n"
        
        # Counter-trend warning
        is_counter_trend = self._is_counter_trend(stock['bias'], market_regime)
        if is_counter_trend:
            msg += f"⚠️ COUNTER-TREND: Market is {market_regime.lower()}\n\n"
        
        # Patterns with timeframe labels
        msg += "Patterns Detected:\n"
        for pattern in stock['patterns']:
            timeframe_label = self._get_timeframe_label(pattern['timeframe'], pattern['type'])
            msg += f"• {timeframe_label}: {pattern['name']} ({pattern['details']})\n"
            msg += f"  → {pattern['context']}\n"
        
        # Key levels
        msg += f"\nKey Levels:\n"
        msg += f"{stock['key_levels']}\n\n"
        
        # Confluence
        stars = "⭐⭐" if stock['confluence']['score'] >= 9 else "⭐"
        msg += f"Confluence: {stock['confluence']['score']}/12 {stars} {stock['confluence']['rating']}\n"
        
        if is_counter_trend:
            index_name = "SPY" if "tech" not in stock['symbol'].lower() else "QQQ"
            direction = "weakness" if stock['bias'] == "BEARISH" else "strength"
            msg += f"Note: Wait for {index_name} {direction} for better odds\n"
        
        msg += "\n"
        return msg
    
    def _classify_trade_type(self, patterns):
        """Classify trade type based on longest-duration pattern"""
        has_chart_pattern = any(p['type'] == 'chart' for p in patterns)
        has_daily_candle = any(p['type'] == 'candlestick' and p['timeframe'] == '1D' for p in patterns)
        
        if has_chart_pattern:
            return {'name': 'POSITION TRADE', 'duration': '1-4 months'}
        elif has_daily_candle:
            return {'name': 'SWING TRADE', 'duration': '1-4 weeks'}
        else:
            return {'name': 'SWING TRADE', 'duration': '1-2 weeks'}
    
    def _get_timeframe_label(self, timeframe, pattern_type):
        """Get proper timeframe label for pattern"""
        if pattern_type == 'chart':
            return "Daily Chart"
        elif timeframe == '1D':
            return "Daily Candle"
        elif timeframe == '1H':
            return "1H Candle"
        else:
            return f"{timeframe} Candle"
    
    def _is_counter_trend(self, pattern_bias, market_regime):
        """Check if pattern is counter-trend to market"""
        if pattern_bias == "BEARISH" and market_regime == "BULLISH":
            return True
        elif pattern_bias == "BULLISH" and market_regime == "BEARISH":
            return True
        return False
```

---

## Benefits of Enhanced Format

### 1. Immediate Market Context
- Users see SPY/QQQ status **first** (most important info)
- Clear regime guidance (favor with-trend trades)
- Reduces counter-trend mistakes

### 2. Timeframe Clarity
- Users understand **why** different hold periods
- Daily Chart = months (position trade)
- Daily Candle = weeks (swing trade)
- 1H Candle = confirmation only

### 3. Trade Type Classification
- Clear expectations for hold duration
- Position trades: 1-4 months (rare, big moves)
- Swing trades: 1-4 weeks (common, moderate moves)

### 4. Counter-Trend Warnings
- Explicit warning when fighting market
- Suggestion to wait for regime shift
- Reduces losses from counter-trend trades

### 5. Educational Value
- Pattern + Timeframe = Duration relationship
- Market regime importance
- When to avoid certain setups

---

## Message Length Considerations

**Telegram Limits:**
- Max message length: 4096 characters
- Recommended target: <3500 characters for safety

**Per-Stock Breakdown:**
- Header + Market backdrop: ~600 chars
- Per bullish stock: ~350-400 chars
- Per bearish stock: ~400-450 chars (includes warning)
- Summary + footer: ~500 chars

**Recommended Stock Count:**
- 10-12 stocks total to stay under 3500 chars
- If more signals, prioritize highest confluence scores

---

## Testing Checklist

- [ ] Market backdrop shows correct trend emoji
- [ ] All MAs show correct ✅/❌ icons
- [ ] Weekly percentage change calculated correctly
- [ ] Regime status matches SPY/QQQ trends
- [ ] Trade type correctly classified per patterns
- [ ] Timeframe labels match pattern source
- [ ] Counter-trend warnings appear when applicable
- [ ] Confluence stars match score (9-12=⭐⭐, 7-8=⭐)
- [ ] Summary counts match actual stocks
- [ ] Total message length < 3500 characters
- [ ] All emojis render correctly in Telegram
- [ ] Disclaimer present at bottom

---

**End of Implementation Guide**
