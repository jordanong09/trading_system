# Swing-Trader Alert Engine - MVP System Architecture v4.0

**Status:** Draft - Ready for Implementation  
**Last Updated:** October 25, 2025  
**Target:** Q4 2025 Launch

---

## 1. Product Overview

### 1.1 Purpose
Deliver actionable 1H entry alerts for 1-2 week swing trades using ATR-scaled S/R zones, EMA20 dynamic support/resistance, and index-aware confluence scoring.

### 1.2 Target User
Swing traders using 1H timeframe entries with 1-2 week hold periods.

### 1.3 Key Differentiators
- **ATR-scaled zones** (±0.30×ATR) instead of thin S/R lines
- **Daily EOD zone updates** - max 1-day stale data
- **EMA20 slope gate** - suppresses signals when EMA20 is flat/choppy
- **SPY/QQQ regime** awareness - mandatory market context
- **Dual alert system** - Watchlist (⭐) vs New Opportunities (🆕)
- **MAS-compliant** - educational analysis, not financial advice

---

## 2. System Requirements

### 2.1 Functional Requirements

| Req ID | Requirement | Priority | Status |
|--------|-------------|----------|--------|
| FR-01 | Calculate ATR(14D), EMA20(1D), SMA50/100/200(1D) for 200 stocks | P0 | ❌ Not Started |
| FR-02 | Build S/R zones: ±0.30×ATR bands around seeds | P0 | ❌ Not Started |
| FR-03 | Identify seeds: EMA20, swings, gaps, HVN, SMAs, round numbers | P0 | ❌ Not Started |
| FR-04 | Calculate 10-point confluence scoring | P0 | ❌ Not Started |
| FR-05 | Assess SPY/QQQ market regime (bullish/bearish/neutral) | P0 | ❌ Not Started |
| FR-06 | Daily EOD zone recalculation (Mon-Thu 17:00 ET) | P0 | ❌ Not Started |
| FR-07 | Weekly watchlist generation (Sunday 20:00 ET) | P0 | ❌ Not Started |
| FR-08 | Hourly scanner for all 200 stocks (Mon-Fri 10:30-15:30 ET) | P0 | ❌ Not Started |
| FR-09 | 1H candlestick pattern detection + relative volume | P0 | ❌ Not Started |
| FR-10 | Telegram alert delivery with threading | P0 | ❌ Not Started |
| FR-11 | Earnings date filtering (T-3 to T+2 suppression) | P1 | ❌ Not Started |
| FR-12 | De-duplication: 60-min cooldown per ticker/side | P1 | ❌ Not Started |
| FR-13 | Performance tracking: win rates by setup type | P2 | ❌ Not Started |

### 2.2 Non-Functional Requirements

| Req ID | Requirement | Target | Status |
|--------|-------------|--------|--------|
| NFR-01 | API calls/month | ≤35,000 | ❌ Not Started |
| NFR-02 | Hourly scan completion time | ≤3 minutes | ❌ Not Started |
| NFR-03 | Alert delivery latency | ≤30 seconds | ❌ Not Started |
| NFR-04 | System uptime during market hours | ≥99% | ❌ Not Started |
| NFR-05 | Data freshness | Max 1 day stale | ❌ Not Started |

### 2.3 Out of Scope (Post-MVP)
- Chart patterns (Cup & Handle, Triangles, Double Tops/Bottoms)
- 4H timeframe scanning
- Multi-asset support (crypto, forex, commodities)
- Backtesting engine
- Web dashboard
- Email alerts (Telegram only for MVP)

---

## 3. Data Architecture

### 3.1 Data Sources

**Primary:** Alpha Vantage API
- Daily OHLCV: 60 bars, adjusted for splits/dividends
- 1H OHLCV: 120 bars (30 trading days)
- Rate limit: 75 calls/min (Premium required)

### 3.2 Stock Universe

**Storage Location:** `storage/input/stock_universe.csv`

**Filter Criteria:**
- Exchange: NYSE, NASDAQ
- Price: ≥$10
- Average Daily Volume (30D): ≥$50M
- Count: ~200 stocks

**CSV Format:**
```csv
symbol,name,exchange,sector
AAPL,Apple Inc.,NASDAQ,Technology
MSFT,Microsoft Corp.,NASDAQ,Technology
...
```

**Loading:**
- System loads at startup via `config.load_stock_universe()`
- Manual updates require system restart
- Validate symbols before adding (must be supported by Alpha Vantage)

**Filter Criteria:**
- Exchange: NYSE, NASDAQ
- Price: ≥$10
- Average Daily Volume (30D): ≥$50M
- Count: ~200 stocks

**Exclusions:**
- HTB (hard-to-borrow) stocks for shorts where identifiable
- Penny stocks, illiquid names

### 3.3 Data Schemas

#### 3.3.1 Daily Bar Schema
```json
{
  "symbol": "AAPL",
  "date": "2025-10-24",
  "open": 185.10,
  "high": 187.50,
  "low": 184.80,
  "close": 186.40,
  "volume": 52000000,
  "adjusted_close": 186.40
}
```

#### 3.3.2 Zone Schema
```json
{
  "zone_id": "AAPL_zn_ema20_20251024",
  "symbol": "AAPL",
  "type": "support|resistance",
  "low": 183.23,
  "mid": 184.12,
  "high": 185.01,
  "components": ["ema20", "swing_low", "hvn"],
  "strength": 7.2,
  "confluence_breakdown": {
    "base_score": 5.2,
    "index_score": 2.0,
    "alignment_score": 0.0
  },
  "metadata": {
    "atr14d": 2.95,
    "ema20_slope": 0.15,
    "slope_factor": 1.2,
    "recent_touches": 3,
    "stack_bonus": true
  },
  "created_at": "2025-10-24T17:00:00Z"
}
```

#### 3.3.3 Signal Schema
```json
{
  "signal_id": "AAPL_20251025_113000",
  "symbol": "AAPL",
  "timestamp": "2025-10-25T11:30:00Z",
  "side": "long|short",
  "quality": "High|Medium",
  "price": 184.50,
  "zone_id": "AAPL_zn_ema20_20251024",
  "zone_range": [183.23, 185.01],
  "distance_atr": 0.12,
  "pattern": "Bullish Engulfing",
  "relative_volume": 1.62,
  "confluence": 7.2,
  "from_watchlist": true,
  "index_context": {
    "spy_regime": "bullish",
    "qqq_regime": "bullish",
    "alignment": "with_trend"
  },
  "targets": {
    "next_resistance": 189.00,
    "stop_loss": 181.50
  }
}
```

---

## 4. S/R Zone Engine

### 4.1 Zone Seeds (Components)

| Seed Type | Weight | Description | Implementation Status |
|-----------|--------|-------------|----------------------|
| **EMA20(1D)** | 2.0 × slope_factor | Primary dynamic S/R | ❌ Not Started |
| **Swing High/Low** | 1.5 | Pivot points (k=3-5 bars) | ❌ Not Started |
| **Gap Edges** | 1.2 | Prior day high/low for gaps ≥2% | ❌ Not Started |
| **HVN (High Volume Nodes)** | 1.0 | Volume-by-price clusters (6-12m data) | ❌ Not Started |
| **SMA50** | 0.8 | Slower trend mean | ❌ Not Started |
| **SMA100** | 0.8 | Intermediate trend | ❌ Not Started |
| **SMA200** | 0.8 | Long-term trend | ❌ Not Started |
| **Round Numbers** | 0.3 | $5/$10 increments | ❌ Not Started |

### 4.2 EMA20 Slope Gate

**Purpose:** Suppress EMA20 signals when price is choppy/ranging.

**Implementation:**
```python
slope_atr = (EMA20_today - EMA20_yesterday) / ATR(14D)

if abs(slope_atr) >= 0.10:
    slope_factor = 1.2    # Strong trend
elif 0.05 <= abs(slope_atr) < 0.10:
    slope_factor = 1.0    # Moderate trend
else:  # < 0.05
    slope_factor = 0.5    # Choppy/flat - reduce weight
```

**Apply to:** Zones containing EMA20 component only

**Status:** ❌ Not Started

### 4.3 Zone Construction Algorithm

**Step 1: Generate Bands**
```python
for each seed_price in seeds:
    half_width = 0.30 × ATR(14D)
    zone = {
        "low": seed_price - half_width,
        "mid": seed_price,
        "high": seed_price + half_width,
        "components": [seed_type]
    }
```

**Step 2: Merge Overlapping Zones**
```python
# If two zones overlap, merge them
# Union their components
# New mid = weighted average based on component strengths
```

**Step 3: Calculate Base Strength (0-6 points)**
```python
base_strength = sum(component_weights) × (1 + 0.05 × recent_touch_score)

if has_stack_bonus:  # Px > EMA20 > SMA50 or Px < EMA20 < SMA50
    base_strength += 0.5

if "ema20" in components:
    base_strength × = slope_factor

clamp(base_strength, 0, 6)
```

**Status:** ❌ Not Started

---

## 5. Confluence Scoring System

### 5.1 10-Point Scoring Breakdown

**Base Zone Strength (0-6 points):**
- Component confluence (EMA20, swings, gaps, HVN, SMAs)
- Recent touches bonus
- Stack bonus
- EMA20 slope factor

**Index Alignment (0-2 points):**
```python
if signal_side == "long":
    if SPY > EMA20 and QQQ > EMA20:
        index_score = 2.0
    elif SPY > EMA20 or QQQ > EMA20:
        index_score = 1.0
    else:  # Both below EMA20
        index_score = 0.0  # Suppress alert

if signal_side == "short":
    if SPY < EMA20 and QQQ < EMA20:
        index_score = 2.0
    elif SPY < EMA20 or QQQ < EMA20:
        index_score = 1.0
    else:  # Both above EMA20
        index_score = 0.0  # Suppress alert
```

**Stock-Index Trend Alignment (0-2 points):**
```python
stock_trend = "bullish" if Close > SMA50 and SMA50_rising else "bearish"
index_trend = "bullish" if SPY > SMA50 else "bearish"

if stock_trend == index_trend:
    alignment_score = 2.0
else:  # Counter-trend
    alignment_score = 0.0
```

**Total: 10 points possible**

**Status:** ❌ Not Started

### 5.2 Quality Thresholds

| Alert Quality | Watchlist Stock | Non-Watchlist Stock | RV Requirement |
|---------------|-----------------|---------------------|----------------|
| **High** | ≥7/10 | ≥8/10 | ≥1.5 |
| **Medium** | ≥5/10 | ≥7/10 | ≥1.2 |
| **No Alert** | <5/10 | <7/10 | <1.2 |

**Rationale:**
- Watchlist stocks already vetted Sunday → lower threshold
- Non-watchlist must be exceptional → higher threshold
- Limits spam to 3-8 alerts/day

**Status:** ❌ Not Started

---

## 6. Entry Timing System

### 6.1 1H Candlestick Patterns

**Bullish Patterns (at support zones):**
- Hammer
- Bullish Engulfing
- Piercing Pattern
- Morning Star (3-bar)

**Bearish Patterns (at resistance zones):**
- Shooting Star
- Bearish Engulfing
- Dark Cloud Cover
- Evening Star (3-bar)

**Status:** ❌ Not Started

### 6.2 Volume Confirmation

**Relative Volume (RV):**
```python
RV = current_bar_volume / SMA(volume, 20 bars on 1H)

# Requirements
High Quality: RV >= 1.5
Medium Quality: RV >= 1.2
No Signal: RV < 1.2
```

**Status:** ❌ Not Started

### 6.3 Trigger Rules

**LONG Signal Requirements:**
1. Price inside/touching support zone OR within 0.35×ATR of zone mid
2. Bullish candlestick pattern on 1H
3. RV ≥ 1.2 (1.5 for High quality)
4. Confluence ≥ 5/10 (watchlist) or ≥7/10 (non-watchlist)
5. Not in earnings blackout (T-3 to T+2)
6. No alert for same ticker/side in last 60 minutes

**SHORT Signal Requirements:**
1. Price inside/touching resistance zone OR within 0.35×ATR of zone mid
2. Bearish candlestick pattern on 1H
3. RV ≥ 1.2 (1.5 for High quality)
4. Confluence ≥ 5/10 (watchlist) or ≥7/10 (non-watchlist)
5. Not in earnings blackout (T-3 to T+2)
6. No alert for same ticker/side in last 60 minutes

**Status:** ❌ Not Started

---

## 7. System Workflows

### 7.1 Sunday Evening Workflow (Weekly Watchlist)

**Schedule:** Sunday 20:00 ET

**Steps:**
1. Fetch daily OHLCV for 200 stocks (60 bars each)
2. Fetch SPY/QQQ daily data
3. Calculate indicators: ATR(14D), EMA20, SMA50/100/200
4. Identify seeds: swings, gaps, HVN, MAs, round numbers
5. Build zones: ±0.30×ATR bands, merge overlaps
6. Calculate 10-point confluence for each zone
7. Assess SPY/QQQ regime
8. Filter: Keep stocks with ≥5/10 confluence + proximity ≤1.0×ATR
9. Rank by confluence score
10. Select top 15-20 stocks
11. Format watchlist message
12. Send to Telegram

**API Calls:** ~202 calls  
**Duration:** ~5 minutes  
**Status:** ❌ Not Started

### 7.2 Daily EOD Update Workflow (Mon-Thu)

**Schedule:** Mon-Thu 17:00 ET (after market close)

**Steps:**
1. Fetch new daily bar for 200 stocks (incremental)
2. Fetch SPY/QQQ daily update
3. Update indicators: ATR(14D), EMA20, SMA50/100/200
4. Recalculate swings, gaps (if new ones formed)
5. Rebuild zones with fresh data
6. Recalculate 10-point confluence
7. Update cached zones for next trading day
8. (Optional) Send zone update alerts if material shift (>0.5×ATR)

**API Calls:** ~202 calls  
**Duration:** ~3 minutes  
**Status:** ❌ Not Started

### 7.3 Hourly Scanning Workflow (Mon-Fri)

**Schedule:** Mon-Fri 10:30, 11:30, 12:30, 13:30, 14:30, 15:30 ET

**Steps:**
1. Fetch 1H OHLCV for all 200 stocks (last 2 bars)
2. Fetch SPY/QQQ 1H data
3. Load cached zones from yesterday's EOD update (or today if available)
4. For each stock:
   a. Check if price near any quality zone (≤0.35×ATR)
   b. Detect 1H candlestick pattern
   c. Calculate relative volume (RV)
   d. Evaluate trigger rules
   e. Calculate current 10-point confluence
   f. If triggered + quality threshold met → generate signal
5. Check if stock on Sunday's watchlist (add ⭐ badge)
6. Apply de-duplication (60-min cooldown)
7. Format alert message
8. Send to Telegram

**API Calls:** ~202 calls/hour  
**Duration:** ~2 minutes  
**Status:** ❌ Not Started

---

## 8. Module Specifications

### 8.1 Module Structure

```
swing_trader_engine/
├── main.py                          # Entry point, scheduler
├── config.py                        # Configuration, environment variables
├── requirements.txt                 # Python dependencies
│
├── data/                            # Data layer
│   ├── alphavantage_client.py       # API client with rate limiting
│   ├── data_fetcher.py              # Fetch daily/1H OHLCV
│   └── cache_manager.py             # Disk cache for zones, indicators
│
├── indicators/                      # Indicator calculation
│   ├── technical_indicators.py      # ATR, EMA, SMA calculations
│   ├── swing_detector.py            # Find swing highs/lows
│   ├── gap_detector.py              # Identify gap edges
│   └── volume_profile.py            # HVN/LVN detection
│
├── zones/                           # S/R zone engine
│   ├── seed_finder.py               # Identify all seed types
│   ├── zone_builder.py              # Create ±0.30×ATR bands, merge
│   ├── confluence_scorer.py         # Calculate 10-point score
│   └── ema20_slope_gate.py          # Apply slope filter
│
├── context/                         # Market context
│   ├── index_analyzer.py            # SPY/QQQ regime assessment
│   └── trend_classifier.py          # Stock trend vs index alignment
│
├── patterns/                        # Pattern detection
│   ├── candlestick_detector.py      # 1H patterns (8 types)
│   └── volume_analyzer.py           # Relative volume (RV)
│
├── scanner/                         # Scanning logic
│   ├── weekly_watchlist.py          # Sunday evening scan
│   ├── eod_updater.py               # Mon-Thu 17:00 zone recalc
│   ├── hourly_scanner.py            # Mon-Fri 10:30-15:30
│   └── trigger_evaluator.py         # Entry trigger rules
│
├── alerts/                          # Alert system
│   ├── telegram_sender.py           # Send messages with threading
│   ├── message_formatter.py         # Format alert cards
│   └── deduplicator.py              # 60-min cooldown logic
│
├── filters/                         # Guardrails
│   ├── earnings_filter.py           # T-3 to T+2 blackout
│   └── liquidity_filter.py          # Price/ADV thresholds
│
└── utils/                           # Utilities
│   ├── scheduler.py                 # Cron-like scheduling
│   ├── logger.py                    # Logging configuration
│   └── mas_compliance.py            # Sanitize messages for MAS
├── storage/                         # NEW: Data storage (files)
│   ├── input/                       # Static input files
│   │   ├── stock_universe.csv       # ← YOUR 200 STOCKS GO HERE
│   │   └── earnings_calendar.csv    # (Optional for Phase 9)
│   │
│   ├── cache/                       # System-generated cache
│   │   ├── zones/                   # Cached zone data
│   │   ├── indicators/              # Cached ATR, EMA, SMA
│   │   └── ohlcv/                   # Cached price data
│   │
│   └── output/                      # System outputs
│       ├── watchlists/              # Sunday watchlist archives
│       ├── signals/                 # Alert history
│       └── logs/                    # System logs
```

### 8.2 Key Module Requirements

#### 8.2.1 `data/alphavantage_client.py`
**Status:** ❌ Not Started

**Requirements:**
- Rate limiting: 150 calls/min
- Retry logic with exponential backoff
- Error handling for API failures
- Environment variable for API key

**Functions:**
```python
def fetch_daily_ohlcv(symbol: str, outputsize: str = "full") -> pd.DataFrame
def fetch_intraday_ohlcv(symbol: str, interval: str = "60min") -> pd.DataFrame
def fetch_ema(symbol: str, interval: str = "daily", time_period: int = 20) -> pd.DataFrame
def fetch_sma(symbol: str, interval: str = "daily", time_period: int = 50) -> pd.DataFrame
```

#### 8.2.2 `zones/zone_builder.py`
**Status:** ❌ Not Started

**Requirements:**
- Create ±0.30×ATR bands around seeds
- Merge overlapping zones
- Weighted average for merged zone mid-points
- Support/resistance classification

**Functions:**
```python
def create_zone_band(seed_price: float, atr: float, components: List[str]) -> Zone
def merge_overlapping_zones(zones: List[Zone]) -> List[Zone]
def classify_zone_type(zone: Zone, current_price: float) -> str  # "support" or "resistance"
```

#### 8.2.3 `zones/confluence_scorer.py`
**Status:** ❌ Not Started

**Requirements:**
- Calculate base score (0-6) from components
- Add index alignment score (0-2)
- Add stock-index trend alignment (0-2)
- Apply EMA20 slope factor
- Recent touches decay: 0.98^days

**Functions:**
```python
def calculate_base_strength(zone: Zone, atr: float, slope_factor: float) -> float
def calculate_index_score(signal_side: str, spy_regime: str, qqq_regime: str) -> float
def calculate_alignment_score(stock_trend: str, index_trend: str) -> float
def calculate_total_confluence(zone: Zone, signal_side: str, spy_context: dict, qqq_context: dict) -> float
```

#### 8.2.4 `scanner/hourly_scanner.py`
**Status:** ❌ Not Started

**Requirements:**
- Scan all 200 stocks
- Load cached zones
- Detect 1H patterns
- Calculate RV
- Evaluate trigger rules
- Generate signals
- Check watchlist status

**Main Function:**
```python
def run_hourly_scan(
    timestamp: datetime,
    symbols: List[str],
    cached_zones: Dict[str, List[Zone]],
    watchlist: List[str]
) -> List[Signal]:
    """
    Returns list of triggered signals meeting quality threshold
    """
    pass
```

#### 8.2.5 `alerts/telegram_sender.py`
**Status:** ❌ Not Started

**Requirements:**
- Send formatted messages
- Threading support (group related messages)
- MAS compliance check before sending
- Rate limiting (avoid Telegram API limits)
- HTML formatting support

**Functions:**
```python
def send_alert(signal: Signal, from_watchlist: bool) -> bool
def send_watchlist(watchlist_data: dict) -> bool
def sanitize_message(text: str) -> str  # Remove forbidden words
```

---

## 9. Alert Message Formats

### 9.1 Weekly Watchlist Message

**Status:** ❌ Not Started

```
📗 WEEKLY WATCHLIST
Week of Oct 28 - Nov 1, 2025

─────────────────────
📊 MARKET BACKDROP
─────────────────────
🇺🇸 SPY: $585.40
Trend: 🟢 BULLISH
• Above EMA20 ✅ (+1.2%)
• Above SMA50 ✅ (+3.8%)
Weekly: +2.3%

💻 QQQ: $495.20
Trend: 🟢 BULLISH
• Above EMA20 ✅ (+1.5%)
• Above SMA50 ✅ (+4.2%)
Weekly: +3.1%

⚠️ REGIME: BULLISH
→ Favor: Long setups at support
→ Avoid: Counter-trend shorts

─────────────────────
🟢 LONG SETUPS (8)
─────────────────────

📈 AAPL - $185.40
Zone: EMA20 support @ $183-185 (7/10)
Setup: 0.18×ATR above zone
  • EMA20↑ + Swing low + HVN
  • Stack: Px > EMA20 > SMA50 ✅
Entry: Pullback to $183-185 + 1H bull signal
Target: R1 @ $189 (gap edge)

[... 7 more long setups ...]

─────────────────────
🔴 SHORT SETUPS (2)
─────────────────────
⚠️ Counter-trend (Market bullish)

[... 2 short setups ...]

─────────────────────
💡 HOW TO USE
─────────────────────
1️⃣ Set price alerts at zones
2️⃣ Wait for 1H signals from our scanner
3️⃣ Favor with-trend setups (8 longs vs 2 shorts)
4️⃣ Not all will trigger - be patient

📚 Educational analysis only. Not financial advice.
```

### 9.2 Hourly Alert (Watchlist Stock)

**Status:** ❌ Not Started

```
⭐ FROM WATCHLIST | 🟢 LONG @ EMA20 (High) | AAPL $184.50
11:30 ET / 23:30 SGT

─────────────────────
ZONE (7/10)
─────────────────────
EMA20 support: $183.23 - $185.01
  • EMA20↑ (slope: strong)
  • Swing low (Oct 20)
  • HVN (3 touches, 10d)
  • Stack: Px > EMA20 > SMA50 ✅

─────────────────────
TRIGGER (1H)
─────────────────────
Pattern: Bullish Engulfing
Volume: RV 1.6 (60% above avg)
Distance: 0.12×ATR from zone

─────────────────────
MARKET
─────────────────────
SPY: Above EMA20 ✅ (bullish)
QQQ: Above EMA20 ✅ (bullish)
Stock: Bullish (aligns)

─────────────────────
LEVELS
─────────────────────
Target: $189 (gap edge, 1.8×ATR)
Stop: $181.50 (below zone)

💡 From Sunday watchlist - confirmed

📚 Educational analysis. Not advice.
```

### 9.3 Hourly Alert (New Opportunity)

**Status:** ❌ Not Started

```
🆕 NEW OPPORTUNITY | 🟢 LONG @ EMA20 (High) | NVDA $855.20
14:30 ET / 02:30+1 SGT

─────────────────────
ZONE (8/10)
─────────────────────
EMA20 support: $850 - $857
  • EMA20↑ (slope: very strong)
  • Swing low + Gap edge
  • HVN (5 touches) + SMA50
  • Stack: Px > EMA20 > SMA50 > SMA100 ✅✅

─────────────────────
TRIGGER (1H)
─────────────────────
Pattern: Morning Star (3-bar)
Volume: RV 1.7 (70% above avg)
Distance: 0.08×ATR from zone

─────────────────────
MARKET
─────────────────────
SPY: Above EMA20 ✅ (bullish)
QQQ: Above EMA20 ✅ (bullish)
Stock: Bullish (aligns)

─────────────────────
LEVELS
─────────────────────
Target: $890 (swing high, 4.1×ATR)
Stop: $847 (below zone + gap)

💡 Not on Sunday watchlist (was too far)
💡 Exceptional mid-week setup (8/10)

📚 Educational analysis. Not advice.
```

---

## 10. API Budget & Performance

### 10.1 API Call Budget

| Activity | Schedule | Calls/Event | Events/Week | Weekly Total |
|----------|----------|-------------|-------------|--------------|
| Sunday Watchlist | Sun 20:00 | 202 | 1 | 202 |
| EOD Updates | Mon-Thu 17:00 | 202 | 4 | 808 |
| Hourly Scans | Mon-Fri 10:30-15:30 | 202 | 30 | 6,060 |
| **Total** | | | | **7,070** |

**Monthly:** ~30,000 calls  
**Alpha Vantage Requirement:** Premium (75 calls/min) - MANDATORY

### 10.2 Performance Targets

| Metric | Target | Status |
|--------|--------|--------|
| Sunday watchlist generation | ≤5 minutes | ❌ Not Started |
| EOD zone update | ≤3 minutes | ❌ Not Started |
| Hourly scan completion | ≤2 minutes | ❌ Not Started |
| Alert delivery latency | ≤30 seconds | ❌ Not Started |
| System uptime (market hours) | ≥99% | ❌ Not Started |

### 10.3 Data Freshness

| Data Type | Max Staleness | Update Frequency |
|-----------|---------------|------------------|
| Zones | 1 day | EOD (Mon-Thu 17:00) |
| Daily indicators | 1 day | EOD (Mon-Thu 17:00) |
| 1H OHLCV | 1 hour | Hourly scans |
| SPY/QQQ context | 1 hour | Hourly scans |

---

## 11. Implementation Phases

### Phase 1: Core Infrastructure (Weeks 1-2)
**Status:** ❌ Not Started

- [ ] Setup project structure
- [ ] Alpha Vantage API client with rate limiting
- [ ] Data schemas (Zone, Signal, Bar)
- [ ] Cache manager for zones
- [ ] Basic logging system
- [ ] Environment configuration

**Deliverable:** Can fetch OHLCV data for 200 stocks

---

### Phase 2: Indicators & Seeds (Weeks 3-4)
**Status:** ❌ Not Started

- [ ] Technical indicators: ATR(14D), EMA20, SMA50/100/200
- [ ] Swing high/low detector
- [ ] Gap detector (≥2% gaps)
- [ ] Volume profile (HVN/LVN)
- [ ] Round number generator ($5/$10 increments)
- [ ] EMA20 slope calculator

**Deliverable:** Can identify all seed types for a stock

---

### Phase 3: Zone Engine (Weeks 5-6)
**Status:** ❌ Not Started

- [ ] Zone band creation (±0.30×ATR)
- [ ] Zone merging algorithm
- [ ] Base strength calculation (0-6)
- [ ] EMA20 slope gate application
- [ ] Recent touches decay logic
- [ ] Stack bonus detection

**Deliverable:** Can build complete zone map for a stock

---

### Phase 4: Market Context (Week 7)
**Status:** ❌ Not Started

- [ ] SPY/QQQ regime classifier
- [ ] Index alignment scoring (0-2)
- [ ] Stock trend classifier
- [ ] Stock-index alignment scoring (0-2)
- [ ] 10-point confluence aggregation

**Deliverable:** Can calculate full 10-point confluence

---

### Phase 5: Pattern Detection (Week 8)
**Status:** ❌ Not Started

- [ ] 1H candlestick patterns (8 types)
- [ ] Relative volume calculator
- [ ] Trigger rule evaluator
- [ ] Quality threshold logic

**Deliverable:** Can detect entry signals on 1H

---

### Phase 6: Weekly Watchlist (Week 9)
**Status:** ❌ Not Started

- [ ] Sunday evening scanner
- [ ] Zone proximity filter (≤1.0×ATR)
- [ ] Top 15-20 ranking logic
- [ ] Watchlist message formatter
- [ ] Telegram integration (basic send)

**Deliverable:** Can generate and send Sunday watchlist

---

### Phase 7: Hourly Scanner (Week 10)
**Status:** ❌ Not Started

- [ ] Hourly scanning loop
- [ ] Cached zone loading
- [ ] Watchlist status checking
- [ ] Signal generation pipeline
- [ ] Alert message formatter (⭐/🆕 badges)
- [ ] Telegram threading support

**Deliverable:** Can scan hourly and send alerts

---

### Phase 8: EOD Updates (Week 11)
**Status:** ❌ Not Started

- [ ] Mon-Thu 17:00 scheduler
- [ ] Incremental daily bar fetching
- [ ] Indicator recalculation
- [ ] Zone rebuilding logic
- [ ] Cache update mechanism
- [ ] (Optional) Zone shift alerts

**Deliverable:** Zones stay fresh (max 1-day stale)

---

### Phase 9: Guardrails (Week 12)
**Status:** ❌ Not Started

- [ ] Earnings date fetcher
- [ ] T-3 to T+2 blackout filter
- [ ] De-duplication (60-min cooldown)
- [ ] Per-session alert cap (e.g., 20)
- [ ] MAS compliance checker
- [ ] Error handling & recovery

**Deliverable:** Production-ready system with safety

---

### Phase 10: Testing & Launch (Week 13-14)
**Status:** ❌ Not Started

- [ ] Unit tests (>80% coverage)
- [ ] Integration tests (end-to-end workflows)
- [ ] Paper trading validation (2 weeks)
- [ ] Performance optimization
- [ ] Documentation (user guide)
- [ ] Launch checklist

**Deliverable:** MVP live in production

---

## 12. Configuration

### 12.1 Environment Variables

```bash
# Required
ALPHA_VANTAGE_API_KEY=your_premium_key
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Optional
LOG_LEVEL=INFO
CACHE_DIR=/path/to/cache
ALERT_CAP_PER_SESSION=20
COOLDOWN_MINUTES=60
```

**Status:** ❌ Not Started

### 12.2 Stock Universe Configuration

```python
# config.py

STOCK_UNIVERSE = {
    "min_price": 10.0,
    "min_adv": 50_000_000,  # $50M
    "exchanges": ["NYSE", "NASDAQ"],
    "count": 200
}

# Will be populated from screener
# Example stocks: AAPL, MSFT, GOOGL, AMZN, NVDA, TSLA, META, ...
```

**Status:** ❌ Not Started

### 12.3 Zone Configuration

```python
# config.py

ZONE_CONFIG = {
    "atr_multiplier": 0.30,        # ±0.30×ATR
    "max_distance_atr": 0.35,      # Max distance for trigger
    "ema20_slope_strong": 0.10,    # |slope| >= 0.10 → strong
    "ema20_slope_moderate": 0.05,  # 0.05-0.10 → moderate
    "recent_touch_decay": 0.98,    # 0.98^days
    "stack_bonus": 0.5             # Points for aligned MAs
}
```

**Status:** ❌ Not Started

---

## 13. Testing Strategy

### 13.1 Unit Tests
**Status:** ❌ Not Started

- [ ] Indicator calculations (ATR, EMA, SMA accuracy)
- [ ] Pattern detection (candlestick recognition)
- [ ] Zone building (band creation, merging)
- [ ] Confluence scoring (10-point calculation)
- [ ] Trigger rules (entry conditions)

**Target Coverage:** >80%

### 13.2 Integration Tests
**Status:** ❌ Not Started

- [ ] End-to-end Sunday watchlist flow
- [ ] End-to-end hourly scanning flow
- [ ] EOD update workflow
- [ ] Alert delivery (mocked Telegram)
- [ ] Cache consistency

### 13.3 Paper Trading Validation
**Status:** ❌ Not Started

- [ ] Run system for 2 weeks without live trading
- [ ] Track all signals generated
- [ ] Measure:
  - Alerts per day (target: 3-8)
  - Watchlist hit rate (% of alerts from watchlist)
  - False positive rate
  - System uptime
- [ ] Validate against manual analysis

**Duration:** 2 weeks minimum before live use

---

## 14. Success Metrics

### 14.1 System Health Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Alerts per day | 3-8 | Count signals sent |
| Watchlist hit rate | ≥40% | (Watchlist alerts / Total alerts) |
| False positives | <30% | Manual review of alerts |
| System uptime | ≥99% | Monitoring logs |
| Alert latency | <30s | Timestamp diff (signal → Telegram) |
| API budget | <35k/month | Call counter |

**Status:** ❌ Not Started

### 14.2 Trading Performance Metrics (Post-Launch)

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Win rate (all signals) | ≥55% | Track outcomes manually |
| Win rate (watchlist signals) | ≥60% | Compare watchlist vs non-watchlist |
| Avg R:R ratio | ≥1.5:1 | (Avg win / Avg loss) |
| Max drawdown | <15% | Track equity curve |

**Status:** ❌ Not Started (requires live trading data)

---

## 15. Risk & Mitigation

| Risk | Impact | Mitigation | Status |
|------|--------|------------|--------|
| Alpha Vantage API downtime | System stops | Implement retry logic, cache fallback | ❌ Not Started |
| Rate limit exceeded | Delayed scans | Premium subscription, call optimization | ❌ Not Started |
| Telegram API failure | No alerts sent | Retry queue, fallback notification | ❌ Not Started |
| Earnings surprise | Bad signals around events | Earnings calendar filter (T-3 to T+2) | ❌ Not Started |
| Zone drift unnoticed | Stale data | Daily EOD updates + monitoring | ❌ Not Started |
| Over-alerting (spam) | User fatigue | Quality thresholds, de-duplication, cap | ❌ Not Started |
| MAS compliance breach | Legal issue | Automated message sanitizer, review logs | ❌ Not Started |

---

## 16. Maintenance & Monitoring

### 16.1 Daily Checks
**Status:** ❌ Not Started

- [ ] System uptime during market hours
- [ ] Alert count (should be 3-8/day)
- [ ] API call budget tracking
- [ ] Error log review

### 16.2 Weekly Checks
**Status:** ❌ Not Started

- [ ] Watchlist quality review (are stocks actually setting up?)
- [ ] Zone accuracy spot-check (manual validation)
- [ ] Win/loss tracking update
- [ ] Cache size monitoring

### 16.3 Monthly Checks
**Status:** ❌ Not Started

- [ ] API budget vs actual usage
- [ ] Performance metrics review (win rate, R:R)
- [ ] Stock universe update (add/remove stocks)
- [ ] System optimization opportunities

---

## 17. Documentation Requirements

### 17.1 Technical Documentation
**Status:** ❌ Not Started

- [ ] API documentation (all modules)
- [ ] Data schemas (JSON examples)
- [ ] Setup guide (installation, environment)
- [ ] Deployment guide (production setup)

### 17.2 User Documentation
**Status:** ❌ Not Started

- [ ] How to read alerts (interpret confluence, zones, etc.)
- [ ] How to use weekly watchlist
- [ ] Risk management guidelines
- [ ] MAS disclaimer & educational framing

---

## 18. Post-MVP Roadmap

### Phase 11: Advanced Features (Q1 2026)
**Status:** ❌ Not Planned

- [ ] Chart patterns (Cup & Handle, Triangles, Double Tops/Bottoms)
- [ ] 4H timeframe scanning
- [ ] Email alerts (in addition to Telegram)
- [ ] Web dashboard (view watchlist, historical alerts)
- [ ] Personalized watchlists (per user preferences)

### Phase 12: Analytics & Optimization (Q2 2026)
**Status:** ❌ Not Planned

- [ ] Backtesting engine (historical performance)
- [ ] Pattern outcome tracking (win rates by pattern type)
- [ ] Regime-based statistics (bull vs bear market performance)
- [ ] Machine learning for confluence weight optimization
- [ ] A/B testing framework for system improvements

### Phase 13: Scale & Expand (Q3 2026)
**Status:** ❌ Not Planned

- [ ] Multi-asset support (crypto, forex)
- [ ] Multiple timeframe strategies (day trading, position trading)
- [ ] Multi-user support (SaaS model)
- [ ] Mobile app (iOS/Android)
- [ ] API for third-party integrations

---

## 19. Appendix

### 19.1 Glossary

| Term | Definition |
|------|------------|
| **ATR** | Average True Range (14-day): Volatility measure |
| **EMA20** | 20-period Exponential Moving Average: Dynamic S/R |
| **SMA** | Simple Moving Average: Trend filter (50/100/200 periods) |
| **S/R Zone** | Support/Resistance zone: ATR-scaled price band |
| **Confluence** | Multiple technical factors aligning at same level |
| **RV** | Relative Volume: Current bar volume / 20-bar average |
| **HVN** | High Volume Node: Price level with heavy trading |
| **Slope Gate** | Filter to suppress EMA20 signals when flat/choppy |
| **Watchlist** | Sunday's top 15-20 setups for the week |
| **Index Regime** | SPY/QQQ market environment (bullish/bearish/neutral) |

### 19.2 References

- Alpha Vantage API Docs: https://www.alphavantage.co/documentation/
- Telegram Bot API: https://core.telegram.org/bots/api
- MAS Guidelines: (Singapore regulatory framework)
- Technical Analysis: Murphy's "Technical Analysis of Financial Markets"

---

**END OF DOCUMENT**

---

## Document Change Log

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| v4.0 | 2025-10-25 | Initial MVP architecture draft | System Architect |

---

**Next Steps:**
1. Review and approve this architecture
2. Set up development environment
3. Begin Phase 1: Core Infrastructure
4. Weekly progress reviews

**Estimated Timeline:** 14 weeks to MVP launch  
**Target Launch Date:** Q1 2026
