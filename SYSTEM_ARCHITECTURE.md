# Trading System Architecture v3.1
## MAS-Compliant Enhanced Predictive Scanner with Weekly Watchlist

**Last Updated:** October 23, 2025  
**Version:** 3.1 (Market-open cache + Index-aware + Weekly Watchlist + Compliant)

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Core Architecture](#core-architecture)
3. [Component Specifications](#component-specifications)
4. [Data Flow](#data-flow)
5. [Feature Matrix](#feature-matrix)
6. [Technical Stack](#technical-stack)
7. [Integration Points](#integration-points)
8. [Compliance Framework](#compliance-framework)

---

## System Overview

### Purpose
A comprehensive trading pattern detection system that provides MAS-compliant technical analysis alerts for intraday and swing trading opportunities across 200 stocks, including week-ahead preparation via Sunday evening watchlist.

### Key Capabilities
- **Real-time Pattern Detection**: 18 total patterns (12 candlestick + 6 chart patterns)
- **Dual-Scan Architecture**: T-5 predictive + T+1-3 confirmation scanning
- **Weekly Watchlist**: Sunday evening week-ahead preparation scan
- **Multi-Timeframe Detection**: Daily (1D) + 1H candlestick patterns + Daily chart patterns
- **Market-Open Caching**: Zero indicator API calls during trading hours
- **Index Awareness**: SPY/QQQ context for pattern validation
- **MAS Compliance**: Analysis-only language with disclaimers

---

## Core Architecture

### 1. System Components

```
┌─────────────────────────────────────────────────────────────────┐
│            ENHANCED PREDICTIVE SCANNER + WEEKLY WATCHLIST        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌───────────────┐  ┌────────────────┐  ┌──────────────────┐   │
│  │   Scheduler   │  │  Data Manager  │  │  Cache Manager   │   │
│  │   (Market +   │→ │  (Historical   │→ │  (Daily MAs +    │   │
│  │   Weekly)     │  │   + S/R)       │  │   1D/1H Data)    │   │
│  └───────────────┘  └────────────────┘  └──────────────────┘   │
│         ↓                   ↓                      ↓             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Alpha Vantage Client                        │   │
│  │  (Rate-limited API calls: 150/min, cache-first)         │   │
│  └─────────────────────────────────────────────────────────┘   │
│         ↓                   ↓                      ↓             │
│  ┌───────────────┐  ┌────────────────┐  ┌──────────────────┐   │
│  │   Pattern     │  │  Technical     │  │  Confluence      │   │
│  │   Detector    │  │  Indicators    │  │  Engine          │   │
│  │   (18 types)  │  │  (MAs + S/R)   │  │  (8/12-point)    │   │
│  │   1D + 1H     │  │                │  │                  │   │
│  └───────────────┘  └────────────────┘  └──────────────────┘   │
│         ↓                                        ↓               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Telegram Alert System                       │   │
│  │  (MAS-compliant: Intraday + Weekly Watchlist)           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Scanning Architecture

#### A. Dual-Scan Workflow (Intraday)

```
Timeline:        09:30 ET           10:25 ET          10:30 ET        10:31-33 ET
                    │                  │                 │                │
                    ▼                  ▼                 ▼                ▼
              ┌──────────┐      ┌──────────┐      ┌──────────┐    ┌──────────┐
              │  Market  │      │Predictive│      │  Candle  │    │Confirma- │
              │   Open   │──────│  Scan    │──────│  Close   │────│tion Scan │
              │  Cache   │      │  (T-5)   │      │          │    │ (T+1-3)  │
              └──────────┘      └──────────┘      └──────────┘    └──────────┘
                    │                  │                                │
                    │                  ▼                                ▼
              ┌──────────┐      ┌──────────┐                    ┌──────────┐
              │ Pre-cache│      │ Pattern  │                    │ Pattern  │
              │ Daily MAs│      │ Forming  │                    │Confirmed │
              │ 200 stks │      │  Alert   │                    │  Alert   │
              │ + SPY/QQQ│      │(Pending) │                    │(Execute) │
              └──────────┘      └──────────┘                    └──────────┘
                    │
                    ▼
              Used all day
              (no refresh)
```

#### B. Weekly Watchlist Workflow (Week-Ahead Preparation)

```
Timeline:        Sunday 7:30 PM          Sunday 8:00 PM         Monday-Friday
                       │                        │                      │
                       ▼                        ▼                      ▼
                 ┌──────────┐            ┌──────────┐          ┌──────────┐
                 │  Fetch   │            │ Generate │          │ Intraday │
                 │  Daily   │────────────│  Weekly  │──────────│ Scans    │
                 │  OHLCV   │            │Watchlist │          │ Confirm  │
                 │ (60 bars)│            │ Message  │          │ Patterns │
                 └──────────┘            └──────────┘          └──────────┘
                       │                        │
                       ▼                        ▼
                 ┌──────────┐            ┌──────────┐
                 │  Detect  │            │  Top 10-15│
                 │  Daily   │            │   Stocks  │
                 │Patterns  │            │ Concise   │
                 │1D + 1H   │            │  Format   │
                 └──────────┘            └──────────┘
```

**Key Differences:**

| Aspect | Intraday Dual-Scan | Weekly Watchlist |
|--------|-------------------|------------------|
| **Timing** | Market hours (09:30-16:00 ET) | Sunday 8:00 PM ET |
| **Purpose** | Execute trades same day | Prepare for week ahead |
| **Timeframes** | 1H candlesticks + Daily MAs | 1D candlesticks + Daily charts |
| **Confluence** | 8-point scale | 12-point scale (stricter) |
| **Stocks** | All qualifying signals | Top 10-15 only |
| **Message** | Detailed per alert | Ultra-concise 2-3 lines |
| **Follow-up** | T+1-3 confirmation | Monday's intraday scans |
| **API Calls** | 200/scan (1H data) | 200 total (1D data) |

#### B. Cache Strategy

**Market Open (09:30 ET)**
- Pre-cache ALL daily indicators (EMA20, SMA50/100/200)
- For: Watchlist (200 stocks) + SPY + QQQ
- Data: Previous trading day's completed bars
- Lifecycle: Valid until next market open
- API Calls: ~1,000 (one-time cost)

**Intraday Scans (10:25, 11:25, ..., 15:25 ET)**
- Fetch ONLY 1H OHLCV data
- Read daily indicators from cache
- API Calls: ~200 per scan (80% reduction)
- Speed: ~1.3 minutes per scan (5x faster)

**Daily Savings**
- Without cache: 7,000 API calls/day
- With cache: 2,200 API calls/day (69% reduction)

#### C. Weekly Watchlist Strategy

**Timing:** Sunday 8:00 PM ET (once per week)

**Purpose:** Week-ahead preparation watchlist highlighting 10-15 stocks with highest-probability setups for the upcoming trading week (Monday-Friday).

**Data Required:**
- **Daily OHLCV**: 60 bars per stock (for daily candlestick + chart pattern detection)
- **1H OHLCV**: Already cached from Friday's scans (no additional calls)
- **Daily Indicators**: Already cached from Friday (EMA20, SMA50/100/200)

**New API Calls:** ~200 (200 stocks × 1 daily OHLCV call)
- Run during non-rush hours (Sunday 7:30-8:00 PM window)
- One-time weekly cost

**Pattern Detection:**
1. **Daily Candlestick Patterns** (12 types on 1D timeframe)
   - Bullish/Bearish Engulfing (1D)
   - Hammer/Shooting Star (1D)
   - Morning/Evening Star (1D)
   - Three White Soldiers/Black Crows (1D)
   - Bullish/Bearish Abandoned Baby (1D)
   - Bullish Breakout/Bearish Breakdown (1D)

2. **Daily Chart Patterns** (6 types on 1D timeframe)
   - Cup & Handle
   - Ascending/Descending Triangle
   - Bull Flag
   - Double Top/Bottom

3. **MA Proximity Analysis**
   - Identify stocks within 2% of key MA levels (EMA20, SMA50/100/200)

**Confluence Scoring:** 12-point scale (stricter than intraday 8-point)
- **Factor 1:** Daily candlestick pattern quality (0-3 pts)
- **Factor 2:** Daily chart pattern presence (0-3 pts)
- **Factor 3:** 1H candlestick confirmation (0-2 pts)
- **Factor 4:** MA proximity (0-2 pts)
- **Factor 5:** Index alignment (0-2 pts)

**Filtering:**
- Minimum confluence: 7/12 (58%)
- Maximum stocks: Top 15 highest scores
- Pattern quality: ≥65% historical completion rate

**Message Format:** Ultra-concise (2-3 lines per stock)
```
📈 AAPL - $185.40
Cup & Handle + Hammer at EMA20
Breakout: $187.50 | Target: $197
```

---

## Component Specifications

### 1. Data Management Layer

#### A. AlphaVantageClient (Optimized)

**File:** `modules/alphavantage_client.py`

**Responsibilities:**
- API communication with rate limiting (150 calls/min)
- Daily indicator caching (market-open strategy)
- Intraday OHLCV fetching
- Batch processing for 200 stocks

**Key Methods:**
```python
class OptimizedAlphaVantageClient:
    def get_intraday_data(symbol, interval="60min")
        # Fetch 1H OHLCV (always fresh)
        # Returns: 210 candles (~30 days history)
    
    def get_technical_indicators_daily(symbol)
        # Fetch OR retrieve cached daily MAs
        # Cache-first: checks DailyIndicatorCache
        # Returns: {ema_20, sma_50, sma_100, sma_200}
    
    def fetch_daily_indicators(symbol, use_previous_complete_bar=True)
        # For market-open pre-cache
        # CRITICAL: Uses previous day's completed bar
        # Returns: {ema20, sma50, sma100, sma200, close, date}
    
    def batch_fetch_stocks(symbols, interval="60min")
        # Optimized batch fetching
        # First scan: ~6.7 min (fetch all MAs)
        # Subsequent scans: ~1.3 min (intraday only)
```

**Data Freshness Rule:**
- Daily indicators: Previous trading day's completed bar
- Never use partial current-day bars (until 16:00 ET)
- Ensures data consistency and accuracy

#### B. DailyIndicatorCache

**File:** `modules/daily_indicator_cache.py`

**Responsibilities:**
- Persistent caching of daily MAs
- Automatic cache invalidation at market open
- Validation and expiry management

**Key Methods:**
```python
class DailyIndicatorCache:
    def is_cache_valid_for_today()
        # Check if cache is from current trading day
    
    def get_indicators(symbol)
        # Retrieve cached indicators (or None)
    
    def set_indicators(symbol, indicators)
        # Cache new indicator values
    
    def invalidate_cache()
        # Clear cache for new trading day
    
    def needs_refresh(symbols)
        # Return list of symbols needing API fetch
```

**Storage:**
- Format: Pickle (binary) + JSON metadata
- Location: `/cache/daily_indicators.pkl`
- Metadata: `/cache/daily_indicators_meta.json`
- Auto-save: On bulk updates

#### C. DataManager

**File:** `modules/data_manager.py`

**Responsibilities:**
- Historical data management (30+ days)
- Support/resistance level calculation
- Breakout detection
- Enhanced stock data aggregation

**Key Methods:**
```python
class DataManager:
    def get_enhanced_stock_data(symbol, new_data)
        # Returns complete enhanced package:
        # - Historical data (30+ candles)
        # - Support/resistance levels (top 3 each)
        # - Breakout analysis
        # - Latest candle snapshot
    
    def identify_support_resistance(df, lookback=30)
        # Horizontal S/R detection:
        # 1. Find swing highs/lows
        # 2. Cluster nearby levels (±0.5%)
        # 3. Rank by touches
        # 4. Return top 3 levels
    
    def detect_breakout_potential(df, support_resistance)
        # Detect imminent breakouts:
        # - Within 1% of S/R level
        # - Volume surge (>1.2x avg)
        # - Directional momentum
```

**Support/Resistance Algorithm:**
```
Input: 30-day 1H candles
Step 1: Find swing highs/lows (peaks/troughs)
Step 2: Cluster within 0.5% tolerance
Step 3: Count touches per level
Step 4: Filter by price position (support < price < resistance)
Step 5: Sort by touches (strength)
Output: Top 3 support + top 3 resistance levels
```

### 2. Pattern Detection Layer

#### A. PatternDetector (Candlestick)

**File:** `modules/pattern_detector.py`

**Patterns Detected (12 total × 2 timeframes = 24 detections):**

**Note:** All 12 candlestick patterns can be detected on BOTH 1D (daily) and 1H timeframes:
- **1D (Daily)**: For swing/position trades, weekly watchlist
- **1H (Hourly)**: For intraday trades, intraday scanning

| Pattern | Type | Bias | Completion Rate | Timeframes |
|---------|------|------|----------------|------------|
| Bullish Engulfing | Reversal | Bullish | ~67% | 1D, 1H |
| Bearish Engulfing | Reversal | Bearish | ~63% | 1D, 1H |
| Hammer | Reversal | Bullish | ~60% | 1D, 1H |
| Shooting Star | Reversal | Bearish | ~59% | 1D, 1H |
| Morning Star | Reversal | Bullish | ~65% | 1D, 1H |
| Evening Star | Reversal | Bearish | ~69% | 1D, 1H |
| Three White Soldiers | Continuation | Bullish | **82%** | 1D, 1H |
| Three Black Crows | Continuation | Bearish | **78%** | 1D, 1H |
| Bullish Abandoned Baby | Reversal | Bullish | 66% (rare) | 1D, 1H |
| Bearish Abandoned Baby | Reversal | Bearish | 78% (rare) | 1D, 1H |
| Bullish Breakout | Momentum | Bullish | Variable | 1D, 1H |
| Bearish Breakdown | Momentum | Bearish | Variable | 1D, 1H |

**Key Implementation:**
- **Same detection algorithms** work on both timeframes
- **Input:** DataFrame with Date, OHLC, Volume columns
- **Timeframe agnostic:** Works on any bar size (1D, 1H, 5min, etc.)
- **Weekly Watchlist:** Use 1D data (60 bars minimum)
- **Intraday Scanning:** Use 1H data (210 bars for 30-day history)

**Key Methods:**
```python
class PatternDetector:
    # 2-candle patterns
    def detect_bullish_engulfing(df)  # Works on 1D or 1H
    def detect_bearish_engulfing(df)  # Works on 1D or 1H
    
    # 1-candle patterns
    def detect_hammer(df)  # Works on 1D or 1H
    def detect_shooting_star(df)  # Works on 1D or 1H
    
    # 3-candle patterns
    def detect_morning_star(df)  # Works on 1D or 1H
    def detect_evening_star(df)  # Works on 1D or 1H
    def detect_three_white_soldiers(df)  # Works on 1D or 1H
    def detect_three_black_crows(df)  # Works on 1D or 1H
    def detect_bullish_abandoned_baby(df)  # Works on 1D or 1H
    def detect_bearish_abandoned_baby(df)  # Works on 1D or 1H
    
    # Momentum patterns
    def detect_breakout(df)  # Works on 1D or 1H
    def detect_bearish_breakdown(df)  # Works on 1D or 1H
    
    # Confluence analysis
    def analyze_confluence(df, index=-1)
        # Returns: 20-period MA, volume surge, volatility
```

**Usage Examples:**
```python
# For weekly watchlist (daily patterns)
daily_df = av_client.get_daily_data(symbol, bars=60)
daily_patterns = detector.detect_bullish_engulfing(daily_df)

# For intraday scanning (hourly patterns)
hourly_df = av_client.get_intraday_data(symbol, interval="60min")
hourly_patterns = detector.detect_bullish_engulfing(hourly_df)
```

#### B. ChartPatterns

**File:** `modules/chart_patterns.py`

**Patterns Detected (6 total):**

| Pattern | Type | Bias | Completion Rate | Timeframes |
|---------|------|------|----------------|------------|
| Cup & Handle | Continuation | Bullish | 68% | Daily, 1H |
| Ascending Triangle | Continuation | Bullish | 72% | Daily, 1H |
| Descending Triangle | Continuation | Bearish | 72% | Daily, 1H |
| Bull Flag | Continuation | Bullish | 63% | Daily, 1H |
| Double Top | Reversal | Bearish | **79%** | Daily, 1H |
| Double Bottom | Reversal | Bullish | **79%** | Daily, 1H |

**Key Methods:**
```python
class ChartPatterns:
    # Continuation patterns
    def detect_cup_and_handle(df, timeframe)
        # U-shaped cup + handle consolidation
        # Measured move: Cup depth projected up
    
    def detect_ascending_triangle(df, timeframe)
        # Flat resistance + rising support
        # Measured move: Triangle height projected up
    
    def detect_descending_triangle(df, timeframe)
        # Flat support + declining resistance
        # Measured move: Triangle height projected down
    
    def detect_bull_flag(df, timeframe)
        # Strong pole + tight flag
        # Measured move: Pole height projected up
    
    # Reversal patterns
    def detect_double_top(df, timeframe)
        # Two peaks + valley breakdown
        # Measured move: Peak-to-valley down
    
    def detect_double_bottom(df, timeframe)
        # Two troughs + peak breakout
        # Measured move: Trough-to-peak up
    
    # Batch detection
    def detect_all_patterns(df, timeframe)
        # Run all 6 detectors, return combined list
```

**Pattern Recognition Algorithms:**

Each pattern uses specific mathematical criteria:

```python
# Example: Ascending Triangle
- Find peaks (resistance touches): ≥3 required
- Validate flat resistance: Peak variance < 0.5%
- Find troughs (support touches): ≥2 required
- Validate rising support: Higher lows
- Duration: 15-40 periods
- Breakout: Price within 2% of resistance
- Target: Triangle height projected up
```

### 3. Analysis Layer

#### A. TechnicalIndicators

**File:** `modules/technical_indicators.py`

**Responsibilities:**
- Moving average calculations (for local analysis)
- Trend determination
- Support/resistance from MAs
- Pattern confluence evaluation

**Key Methods:**
```python
class TechnicalIndicators:
    def calculate_ema(data, period)
        # Exponential MA for trend detection
    
    def calculate_sma(data, period)
        # Simple MA for S/R levels
    
    def get_trend_analysis(df, index=-1)
        # Comprehensive trend analysis:
        # - Price vs all MAs (above/below)
        # - Distance percentages
        # - Primary trend (bullish/bearish)
        # - Nearest S/R from MAs
    
    def evaluate_pattern_confluence(pattern_bias, trend_analysis)
        # 5-point confluence scoring:
        # 1. EMA20 alignment (2 pts)
        # 2. SMA200 position (1 pt)
        # 3. S/R proximity (1 pt)
        # 4. Multiple MA alignment (1 pt)
        # Output: Score, percentage, recommendation
```

#### B. MovingAverages

**File:** `modules/moving_averages.py`

**Responsibilities:**
- Analysis of Alpha Vantage MA data (no calculation)
- Trend strength assessment
- MA-based S/R identification
- Confluence evaluation

**Key Methods:**
```python
class MovingAverages:
    def get_trend_analysis(stock_data)
        # Analyze MA data from Alpha Vantage:
        # - Price position relative to each MA
        # - Distance percentages
        # - Trend strength (very strong → very weak)
        # - Bullish/bearish MA count
    
    def get_ma_support_resistance(trend_analysis)
        # Identify MAs as S/R:
        # - Nearest support (MA below price)
        # - Nearest resistance (MA above price)
        # - All levels ranked by distance
    
    def evaluate_pattern_confluence(pattern_bias, trend_analysis)
        # 5-point confluence (same as TechnicalIndicators)
        # For patterns detected on cached MA data
    
    def validate_ma_data(stock_data)
        # Validate Alpha Vantage data quality
        # Check for missing/unreasonable values
```

### 4. Scheduling & Market Awareness

#### A. MarketScheduler

**File:** `modules/alphavantage_client.py`

**Responsibilities:**
- Timezone-aware market hours (US Eastern Time)
- Holiday calendar management
- Trading day detection
- Candle close timing

**Key Methods:**
```python
class MarketScheduler:
    ET_TZ = pytz.timezone('America/New_York')
    MARKET_OPEN = time(9, 30)    # 09:30 ET
    MARKET_CLOSE = time(16, 0)   # 16:00 ET
    HOLIDAYS = {...}              # 2024-2025 US market holidays
    
    def get_et_now()
        # Current time in Eastern Time
    
    def is_market_open()
        # Check if market is currently open
        # Monday-Friday, 09:30-16:00 ET
        # Excluding holidays
    
    def is_new_trading_day(last_scan_date)
        # Detect if we're on a new trading day (in ET)
    
    def get_next_candle_close(interval_minutes=60)
        # Calculate next 1H candle close time
        # For 1H: closes at :30 of each hour
    
    def time_until_market_open()
        # Seconds until next market open
        # (0 if already open)
    
    def wait_for_candle_close(interval_minutes=60)
        # Smart sleep until next candle closes
        # Includes 1-minute data buffer
```

**Holiday Calendar:**
- New Year's Day
- MLK Day
- Presidents' Day
- Good Friday
- Memorial Day
- Juneteenth
- Independence Day
- Labor Day
- Thanksgiving
- Christmas

### 5. Alert System

#### A. TelegramSender

**File:** `telegram_sender.py`

**Responsibilities:**
- MAS-compliant message formatting
- HTML escaping for safe formatting
- Enhanced vs simple alerts
- Duplicate prevention

**Key Methods:**
```python
class TelegramSender:
    def send_enhanced_alert(symbol, detection)
        # Full predictive alert:
        # - Pattern details
        # - Signal strength (confluence score)
        # - Daily MA analysis
        # - Horizontal S/R levels (30-day)
        # - Breakout analysis (if applicable)
        # - Trading plan (entry/stop/target)
        # - R:R ratio
        # - Chart link
    
    def send_simple_alert(symbol, pattern, price, bias, volume)
        # Backward-compatible simple alert
        # For backtesting or basic notifications
    
    def test_connection()
        # Test Telegram bot connectivity
    
    def escape(text)
        # HTML escaping for safe formatting
```

**Alert Types:**

1. **Predictive Alert (T-5 min)**
```
🟢 ENHANCED PREDICTIVE SIGNAL 🔮 🟢

⚠️ PENDING CANDLE CLOSE ⚠️

Symbol: AAPL
Pattern: BULLISH_ENGULFING
Bias: BULLISH
Signal: STRONG_SIGNAL (86%)

Current Price: $150.75

DAILY Moving Averages (Trend):
📈 Primary Trend: BULLISH
• EMA20: $148.50 ✅
• SMA50: $145.00 ✅
• SMA100: $142.00 ✅
• SMA200: $140.00 ✅

Horizontal Support/Resistance (30-day):
🟢 S1: $148.00 (4 touches, 1.8% below)
🔴 R1: $152.50 (5 touches, 1.2% above)

⚡ BREAKOUT ALERT ⚡
Direction: BULLISH
Target: $152.50
Distance: 1.2%
Volume: Surging ✅

Confluence (6/7):
✅ Pattern aligns with BULLISH trend
✅ Price above SMA200
✅ Near support

💡 Trading Plan:
1️⃣ Prepare limit order now
2️⃣ Entry: $150.75
3️⃣ Stop: $147.01 (below support)
4️⃣ Target: $152.50 (resistance)

✅ High probability BULLISH setup
```

2. **Confirmation Alert (T+1-3 min)**
```
✅ PATTERN CONFIRMED ✅ 🚀

Symbol: AAPL
Pattern: BULLISH_ENGULFING
Close Price: $150.89 📈

✅ Pattern confirmed at candle close
✅ Signal: STRONG_SIGNAL (86%)
✅ Execute order now
```

3. **Failed Pattern Alert**
```
❌ PATTERN FAILED ❌

Symbol: AAPL
Pattern: BULLISH_ENGULFING

❌ Pattern did NOT confirm at close
⚠️ Do NOT enter this trade
🚫 Cancel order immediately
```

### 6. Main Scanner (Orchestrator)

#### A. EnhancedPredictiveScanner

**File:** `enhanced_predictive_scanner.py`

**Responsibilities:**
- Orchestrate entire scanning workflow
- Manage watchlist (200 stocks)
- Execute dual-scan strategy
- Handle index awareness (SPY/QQQ)
- Ensure MAS compliance
- Track pending signals

**Key Methods:**
```python
class EnhancedPredictiveScanner:
    def __init__(api_key, telegram_bot, telegram_chat)
        # Initialize all sub-components
        # Create cache directory
        # Load configuration
    
    def load_watchlist(file_path)
        # Load from Excel/CSV
        # Determine reference index (SPY vs QQQ)
        # Based on tech stock ratio
    
    def precache_daily_indicators()
        # Market-open pre-cache (09:30 ET)
        # Fetch daily MAs for all stocks + indices
        # Uses PREVIOUS day's completed bars
        # Valid until next market open
    
    def scan_predictive_enhanced(minutes_before_close=5)
        # T-5 predictive scan
        # Fetch 1H OHLCV only
        # Read daily MAs from cache
        # Detect patterns
        # Evaluate confluence (8-point with index)
        # Send predictive alerts
        # Store pending signals
    
    def scan_confirmation()
        # T+1-3 confirmation scan
        # Re-scan pending tickers only
        # Validate pattern on closed bar
        # Send confirmation/failure alerts
        # Clear pending signals
    
    def run_continuous_enhanced(interval_minutes=60)
        # Main loop:
        # 1. Check for new trading day
        # 2. Pre-cache at market open
        # 3. Wait until T-5 (predictive time)
        # 4. Run predictive scan
        # 5. Wait for candle close
        # 6. Wait T+1-3 for data
        # 7. Run confirmation scan
        # 8. Repeat
    
    def _build_stock_context(stock_data, daily_indicators, current_close)
        # Build stock-specific context:
        # - Price vs daily MAs
        # - Near major levels (±1%)
        # Returns: Dict with price, MAs, positions, near_levels
    
    def _build_index_context(index_data, daily_indicators)
        # Build index context (SPY/QQQ):
        # - Index vs daily MAs
        # - Strength/weakness indicator
        # Returns: Dict with index stats
    
    def _evaluate_index_aware_confluence(pattern_bias, stock_ctx, 
                                         index_ctx, sr_levels, breakout)
        # Enhanced 8-point confluence:
        # 1. Index backdrop (2 pts)
        # 2. Stock vs EMA20 (2 pts)
        # 3. Near S/R (2 pts)
        # 4. Breakout imminent (2 pts)
        # Returns: Score, percentage, recommendation, reasons
    
    def _sanitize_message(message)
        # MAS compliance check
        # Forbidden words: buy, sell, enter, exit, target, 
        #                  tp, sl, stop, guarantee, will, should, must
        # Raises ValueError if non-compliant
    
    def _format_compliant_alert(signal, status)
        # Format MAS-compliant alert:
        # - Analysis-only language
        # - No recommendations
        # - Includes disclaimer
        # - Pending/Confirmed/Failed status
```

**Watchlist Management:**
```python
# Auto-determine reference index:
tech_ratio = tech_stocks / total_stocks
if tech_ratio > 0.5:
    reference_index = "QQQ"  # Tech-heavy
else:
    reference_index = "SPY"  # General market
```

**Index-Aware Confluence (8 points):**
```
1. Index Backdrop Alignment (2 pts)
   - Bullish pattern + Index above EMA20 = +2
   - Bearish pattern + Index below EMA20 = +2

2. Stock vs EMA20 Alignment (2 pts)
   - Bullish pattern + Stock above EMA20 = +2
   - Bearish pattern + Stock below EMA20 = +2

3. Near Horizontal S/R Level (2 pts)
   - Bullish + Near support (<2% away) = +2
   - Bearish + Near resistance (<2% away) = +2

4. Breakout Imminent (2 pts)
   - Breakout detected + Direction matches bias = +2

Scoring:
- 75%+ (6-8 pts): STRONG_SIGNAL
- 62%+ (5 pts):   GOOD_SIGNAL
- 50%+ (4 pts):   MODERATE_SIGNAL
- <50%:           WEAK_SIGNAL
```

---

### 7. Weekly Watchlist Scanner

#### A. WeeklyWatchlistScanner

**File:** `weekly_watchlist.py` (to be created)

**Responsibilities:**
- Generate concise weekly watchlist for week-ahead preparation
- Detect patterns on daily (1D) timeframe
- Apply stricter confluence filtering (12-point scale)
- Format ultra-concise Telegram messages
- Schedule Sunday evening scans

**Key Methods:**
```python
class WeeklyWatchlistScanner:
    def __init__(av_client, telegram, detector, config)
        # Initialize with tighter criteria
        # min_confluence_score = 7/12 (58%)
        # max_stocks = 15
        # min_pattern_quality = 0.65 (65%+ historical success)
    
    def run_sunday_scan(symbols)
        # Main Sunday evening scan
        # 1. Fetch Friday's daily data (60 bars/stock)
        # 2. Get market context (SPY/QQQ)
        # 3. Detect patterns on 1D + 1H timeframes
        # 4. Calculate 12-point confluence
        # 5. Filter top 10-15 stocks
        # 6. Format concise message
        # 7. Send via Telegram
    
    def _fetch_daily_data(symbols, bars=60)
        # Fetch daily OHLCV for all stocks
        # 200 stocks × 1 API call = 200 total
        # Run during 7:30-8:00 PM window
    
    def _detect_patterns_daily(df)
        # Run all 12 candlestick detectors on 1D data
        # Returns: patterns from Friday's bar
    
    def _detect_chart_patterns_daily(df)
        # Run all 6 chart pattern detectors on 1D data
        # Returns: patterns near completion (last 5 days)
    
    def _detect_ma_proximity(df, symbol)
        # Check if price within 2% of key MAs
        # EMA20, SMA50, SMA100, SMA200
        # Returns: list of proximity setups
    
    def _evaluate_weekly_confluence(symbol, daily_cs, daily_chart, 
                                    hourly_cs, ma_setups, index_data)
        # 12-point confluence scoring:
        # - Daily candlestick (0-3 pts)
        # - Daily chart pattern (0-3 pts)
        # - 1H candlestick confirmation (0-2 pts)
        # - MA proximity (0-2 pts)
        # - Index alignment (0-2 pts)
        # Returns: score, percentage, recommendation, reasons
    
    def _format_concise_watchlist(watchlist, market_context)
        # Ultra-concise message format:
        # Header: Market context (SPY/QQQ status)
        # Body: 2-3 lines per stock
        # Footer: Summary + usage instructions
        # Total: <3000 chars (fits 1 Telegram message)
    
    def _format_stock_entry(stock)
        # Ultra-concise per-stock format:
        # Line 1: Symbol + Price
        # Line 2: Pattern combination
        # Line 3: Key levels (breakout/support/target)
```

**Concise Message Template:**
```
🗓️ WEEKLY WATCHLIST
Week of Oct 28 - Nov 1, 2024

📊 MARKET CONTEXT:
SPY: $585.40 | Above all MAs ✅
QQQ: $495.20 | Above all MAs ✅
Regime: Bullish

━━━━━━━━━━━━━━━━━━━━━━━━━

🟢 BULLISH SETUPS (8)

📈 AAPL - $185.40
Cup & Handle + Hammer at EMA20
Breakout: $187.50 | Target: $197

📈 MSFT - $415.20  
Ascending Triangle forming
Breakout: $420 | Target: $430

... (8 more bullish stocks)

━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 BEARISH SETUPS (3)

📉 TSLA - $265.20
Double Top + Evening Star
Breakdown: $244 | Target: $222

... (2 more bearish stocks)

━━━━━━━━━━━━━━━━━━━━━━━━━

📋 SUMMARY:
• Bullish: 8 stocks (73%)
• Bearish: 3 stocks (27%)
• Exceptional setups: 3
• Strong setups: 8

⚠️ USAGE:
1. Add these to YOUR watchlist
2. Set price alerts at breakout levels
3. Wait for our INTRADAY confirmations
4. Not all will trigger this week

💡 Remember: Watchlist ≠ Trade list
Let patterns develop naturally!

🔒 Educational analysis only. Not advice.
```

**Scheduling:**
```python
# Add to scheduler
scheduler.add_job(
    func=weekly_scanner.run_sunday_scan,
    trigger='cron',
    day_of_week='sun',  # Sunday
    hour=20,            # 8:00 PM
    minute=0,
    timezone='America/New_York',
    args=[symbols]
)
```

**Benefits:**
1. **Preparation Time:** Full Sunday evening + Monday morning to research
2. **Reduced Stress:** Know what to watch before market opens
3. **No FOMO:** Already on radar, no rushed decisions
4. **Educational:** Practice spotting setups before they trigger
5. **Community Building:** Everyone watching same stocks
6. **Professional Habit:** Mimics institutional trader workflows

**Integration with Intraday Scanner:**
- Weekly watchlist provides "watch these" guidance
- Intraday scanner provides "execute now" confirmations
- Two-stage approach: Preparation → Execution
- Reduces false positives (weekly filter + intraday confirmation)

---

## Data Flow

### 1. Market Open Flow (09:30 ET)

```
User starts scanner
       ↓
Check if new trading day
       ↓
Invalidate yesterday's cache
       ↓
Wait for market open (09:30 ET)
       ↓
┌─────────────────────────────────┐
│   PRE-CACHE DAILY INDICATORS    │
├─────────────────────────────────┤
│ For each stock + SPY + QQQ:     │
│   1. Fetch daily EMA20          │
│   2. Fetch daily SMA50          │
│   3. Fetch daily SMA100         │
│   4. Fetch daily SMA200         │
│   5. Fetch previous day's close │
│   6. Cache to disk              │
└─────────────────────────────────┘
       ↓
Cache valid until tomorrow 09:30 ET
       ↓
Ready for intraday scans
```

### 2. Predictive Scan Flow (T-5)

```
Wait until 10:25 ET (T-5 for 10:30 close)
       ↓
┌─────────────────────────────────┐
│    FETCH 1H OHLCV DATA          │
├─────────────────────────────────┤
│ For each stock in watchlist:    │
│   - Get 210 x 1H candles        │
│   - API call: ~200 total        │
│   - Time: ~1.3 minutes          │
└─────────────────────────────────┘
       ↓
┌─────────────────────────────────┐
│   READ CACHED DAILY MAs         │
├─────────────────────────────────┤
│ For each stock:                 │
│   - Read from cache (no API)    │
│   - EMA20, SMA50/100/200        │
│   - Previous day's values       │
└─────────────────────────────────┘
       ↓
┌─────────────────────────────────┐
│   PATTERN DETECTION             │
├─────────────────────────────────┤
│ On 1H data:                     │
│   - Detect all 18 patterns      │
│   - Check last 10 candles       │
│   - Filter recent patterns only │
└─────────────────────────────────┘
       ↓
┌─────────────────────────────────┐
│   ENHANCED DATA ANALYSIS        │
├─────────────────────────────────┤
│ For each stock with pattern:    │
│   - Calculate S/R (30-day)      │
│   - Detect breakouts            │
│   - Build stock context         │
│   - Build index context         │
└─────────────────────────────────┘
       ↓
┌─────────────────────────────────┐
│   CONFLUENCE EVALUATION         │
├─────────────────────────────────┤
│ 8-point index-aware scoring:    │
│   - Index backdrop (2 pts)      │
│   - Stock vs EMA20 (2 pts)      │
│   - S/R proximity (2 pts)       │
│   - Breakout potential (2 pts)  │
└─────────────────────────────────┘
       ↓
Filter: STRONG_SIGNAL or GOOD_SIGNAL only
       ↓
┌─────────────────────────────────┐
│   SEND PREDICTIVE ALERTS        │
├─────────────────────────────────┤
│ For each qualifying signal:     │
│   - Format MAS-compliant msg    │
│   - Include trading plan        │
│   - Send via Telegram           │
│   - Store as pending signal     │
└─────────────────────────────────┘
       ↓
Wait for candle close
```

### 3. Confirmation Scan Flow (T+1-3)

```
Candle closes at 10:30 ET
       ↓
Wait 90 seconds (T+1-3 for data)
       ↓
┌─────────────────────────────────┐
│   FETCH UPDATED 1H DATA         │
├─────────────────────────────────┤
│ For pending signals only:       │
│   - Get latest 1H candles       │
│   - Includes closed 10:30 bar   │
│   - API calls: ~10-50           │
└─────────────────────────────────┘
       ↓
┌─────────────────────────────────┐
│   RE-DETECT PATTERNS            │
├─────────────────────────────────┤
│ On closed bar:                  │
│   - Run same pattern detectors  │
│   - Check if pattern confirmed  │
│   - Compare with prediction     │
└─────────────────────────────────┘
       ↓
┌─────────────────────────────────┐
│   SEND CONFIRMATION ALERTS      │
├─────────────────────────────────┤
│ For each pending signal:        │
│   ✅ Confirmed: Execute alert   │
│   ❌ Failed: Cancel alert       │
│   - Clear pending signals       │
└─────────────────────────────────┘
       ↓
Repeat cycle for next hour (11:25 ET)
```

### 4. Weekly Watchlist Flow (Sunday Evening)

```
Sunday 7:30 PM ET
       ↓
┌─────────────────────────────────┐
│   FETCH FRIDAY'S DATA           │
├─────────────────────────────────┤
│ For all 200 stocks:             │
│   - Daily OHLCV (60 bars)       │
│   - API calls: 200              │
│   - Time: ~1.5 minutes          │
└─────────────────────────────────┘
       ↓
┌─────────────────────────────────┐
│   READ CACHED DATA              │
├─────────────────────────────────┤
│ From Friday's scans:            │
│   - 1H OHLCV (already cached)   │
│   - Daily MAs (already cached)  │
│   - No additional API calls     │
└─────────────────────────────────┘
       ↓
┌─────────────────────────────────┐
│   DETECT PATTERNS (MULTI-TF)    │
├─────────────────────────────────┤
│ For each stock:                 │
│   1. Daily candlestick (1D)     │
│   2. Daily chart patterns (1D)  │
│   3. Hourly candlestick (1H)    │
│   4. MA proximity analysis      │
└─────────────────────────────────┘
       ↓
┌─────────────────────────────────┐
│   CALCULATE CONFLUENCE          │
├─────────────────────────────────┤
│ 12-point scoring system:        │
│   - Daily candlestick (0-3)     │
│   - Daily chart pattern (0-3)   │
│   - 1H confirmation (0-2)       │
│   - MA proximity (0-2)          │
│   - Index alignment (0-2)       │
└─────────────────────────────────┘
       ↓
┌─────────────────────────────────┐
│   FILTER & RANK                 │
├─────────────────────────────────┤
│ Apply criteria:                 │
│   - Min confluence: 7/12 (58%)  │
│   - Max stocks: Top 15          │
│   - Min pattern quality: 65%    │
│   - Sort by confluence score    │
└─────────────────────────────────┘
       ↓
┌─────────────────────────────────┐
│   FORMAT CONCISE MESSAGE        │
├─────────────────────────────────┤
│ For top 10-15 stocks:           │
│   - Market context (SPY/QQQ)    │
│   - 2-3 lines per stock         │
│   - Bullish/bearish separation  │
│   - Summary + usage guide       │
│   - Total: <3000 chars          │
└─────────────────────────────────┘
       ↓
Sunday 8:00 PM ET
       ↓
┌─────────────────────────────────┐
│   SEND WEEKLY WATCHLIST         │
├─────────────────────────────────┤
│ Via Telegram:                   │
│   - Single message              │
│   - Week-ahead preparation      │
│   - Educational + MAS-compliant │
└─────────────────────────────────┘
       ↓
Week begins Monday 9:30 AM ET
       ↓
Intraday scans confirm watchlist patterns
```

---