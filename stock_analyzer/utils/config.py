# config.py - MVP 4.0 Configuration (Updated with P4.3-P5.2)
"""
Configuration for Swing Trader Alert Engine
Includes new modules: Weekly Watchlist, EOD Updates, Telegram Threading, Message Formatting
"""

import os
from pathlib import Path
from typing import Optional

# ============================================================================
# SECURE API KEY LOADING FROM ENVIRONMENT VARIABLES
# ============================================================================

def get_env_variable(var_name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Load environment variable securely
    
    Args:
        var_name: Environment variable name
        default: Default value for testing (optional)
    
    Returns:
        Environment variable value or None
    """
    value = os.getenv(var_name, default)
    
    if value is None or value == "" or value == "your_key_here":
        if default is None:
            raise ValueError(
                f"âŒ ERROR: {var_name} not set in environment!\n"
                f"Set it with: export {var_name}='your_value'\n"
                f"Then restart terminal."
            )
    
    return value if value else default


# ============================================================================
# API KEYS - Loaded from Environment Variables (SECURE)
# ============================================================================

try:
    ALPHA_VANTAGE_API_KEY = get_env_variable('ALPHA_VANTAGE_API_KEY', 'demo')
    TELEGRAM_BOT_TOKEN = get_env_variable('TELEGRAM_BOT_TOKEN', 'test_token')
    TELEGRAM_CHAT_ID = get_env_variable('TELEGRAM_CHAT_ID', 'test_id')
    
    if ALPHA_VANTAGE_API_KEY != 'demo':
        print("âœ… API keys loaded securely from environment variables")
    else:
        print("âš ï¸  WARNING: Using demo/test mode")
        print("Set environment variables for production!\n")
    
except ValueError as e:
    print(f"\n{e}")
    print("\nâš ï¸  WARNING: Using demo/test mode")
    print("Set environment variables for production!\n")
    
    # Fallback for initial testing only
    ALPHA_VANTAGE_API_KEY = "demo"
    TELEGRAM_BOT_TOKEN = "test_token"
    TELEGRAM_CHAT_ID = "test_id"


# ============================================================================
# PATHS (Cross-platform compatible)
# ============================================================================

# Base storage directory structure (matches your architecture)
STORAGE_DIR = Path("storage")
CACHE_DIR = STORAGE_DIR / "cache"
INPUT_DIR = STORAGE_DIR / "input"
OUTPUT_DIR = STORAGE_DIR / "output"

# Cache subdirectories (for organized data storage)
CACHE_ZONES_DIR = CACHE_DIR / "zones"
CACHE_OHLCV_DIR = CACHE_DIR / "ohlcv"
CACHE_INDICATORS_DIR = CACHE_DIR / "indicators"

# Output subdirectories
OUTPUT_WATCHLISTS_DIR = OUTPUT_DIR / "watchlists"
OUTPUT_SIGNALS_DIR = OUTPUT_DIR / "signals"
OUTPUT_LOGS_DIR = OUTPUT_DIR / "logs"

# Legacy string paths (for backward compatibility with existing code)
CACHE_DIRECTORY = str(CACHE_DIR)
OUTPUT_DIRECTORY = str(OUTPUT_DIR)
LOG_DIRECTORY = str(OUTPUT_LOGS_DIR)
DATA_DIRECTORY = str(INPUT_DIR)

# Create all required directories
REQUIRED_DIRS = [
    INPUT_DIR,
    CACHE_DIR,
    CACHE_ZONES_DIR,
    CACHE_OHLCV_DIR,
    CACHE_INDICATORS_DIR,
    OUTPUT_DIR,
    OUTPUT_WATCHLISTS_DIR,
    OUTPUT_SIGNALS_DIR,
    OUTPUT_LOGS_DIR,
]

for directory in REQUIRED_DIRS:
    directory.mkdir(parents=True, exist_ok=True)

print(f"âœ… Storage structure created at: {STORAGE_DIR.absolute()}")


# ============================================================================
# STOCK UNIVERSE CONFIGURATION
# ============================================================================

STOCK_UNIVERSE = {
    'initial_count': 50,          # Start with 50 stocks for MVP
    'min_price': 10.0,            # Minimum stock price
    'min_adv': 50_000_000,        # Minimum average daily volume ($50M)
    'exchanges': ['NYSE', 'NASDAQ']
}


# ============================================================================
# ZONE CONFIGURATION
# ============================================================================

ZONE_CONFIG = {
    'atr_multiplier': 0.15,       # Â±0.15Ã—ATR for zone bands
    'max_distance_atr': 0.35,     # Max distance for trigger eligibility
    'ema20_slope_strong': 0.10,   # |slope| >= 0.10 â†’ strong
    'ema20_slope_moderate': 0.05, # 0.05-0.10 â†’ moderate
    'recent_touch_decay': 0.98,   # 0.98^days decay factor
    'stack_bonus': 0.5            # Points for aligned MAs
}


# ============================================================================
# COMPONENT WEIGHTS (for Base Strength calculation)
# ============================================================================

COMPONENT_WEIGHTS = {
    'ema20': 1.0,
    'sma50': 0.8,
    'sma100': 0.6,
    'sma200': 1.2,
    "round_number": 0.6,
    'swing_high': 1.0,
    'swing_low': 1.0,
    'gap_edge': 0.8,
    'hvn': 0.5,
    'lvn': 0.3
}


# ============================================================================
# CONFLUENCE THRESHOLDS
# ============================================================================

CONFLUENCE_THRESHOLDS = {
    # Thresholds for watchlist stocks (already tracked)
    'watchlist_high': 7.0,        # High quality from watchlist: â‰¥7/10
    'watchlist_medium': 5.0,      # Medium quality from watchlist: â‰¥5/10
    
    # Thresholds for new stocks (not on watchlist)
    'new_high': 8.0,              # High quality for new: â‰¥8/10
    'new_medium': 7.0             # Medium quality for new: â‰¥7/10
}


# ============================================================================
# RELATIVE VOLUME (RV) REQUIREMENTS
# ============================================================================

RV_REQUIREMENTS = {
    'minimum': 1.2,               # Minimum RV to consider pattern
    'high': 1.5,                  # RV >= 1.5 â†’ High quality signal
    'medium': 1.2,                # RV >= 1.2 â†’ Medium quality signal
    'lookback_periods': 10        # Periods for average volume calculation
}


# ============================================================================
# P4.3: WEEKLY WATCHLIST CONFIGURATION
# ============================================================================

WEEKLY_WATCHLIST = {
    'enabled': True,                          # Enable watchlist generation
    'min_confluence': 7.0,                    # Minimum zone strength for watchlist
    'max_stocks': 30,                         # Max stocks in watchlist
    'max_distance_atr': 1.0,                  # Max distance from zone for watchlist
    'watchlist_file': 'weekly_watchlist.json', # Cache file name
    'scan_day': 'sun',                        # Day to generate (Sunday)
    'scan_hour': 18,                          # Hour to generate (18:00 ET)
    'scan_minute': 0
}


# ============================================================================
# P4.4: EOD UPDATE CONFIGURATION
# ============================================================================

EOD_UPDATE = {
    'enabled': False,                         # Optional - set True to enable
    'shift_threshold': 0.5,                   # Alert if zone shifts >0.5Ã—ATR
    'update_days': 'mon-thu',                 # Days to run update
    'update_hour': 17,                        # Hour to run (17:00 ET)
    'update_minute': 0,
    'update_log_file': 'eod_updates.json'
}


# ============================================================================
# P5.1: TELEGRAM THREADING CONFIGURATION
# ============================================================================

TELEGRAM_THREADING = {
    'enabled': False,                         # Requires Telegram Supergroup with Topics
    'topic_cache_file': 'telegram_topics.json',
    'create_symbol_topics': True,             # Create topic per symbol
    'create_general_topic': True,             # Create general topic
    'create_watchlist_topic': True            # Create watchlist topic
}


# ============================================================================
# P5.2: MESSAGE FORMATTING CONFIGURATION
# ============================================================================

MESSAGE_FORMATTING = {
    'use_markdown': True,                     # Use Markdown formatting
    'include_buttons': True,                  # Inline buttons (View Chart, etc.)
    'compact_mode': False,                    # Use compact formatting
    'include_chart_link': True,               # Include TradingView link
    'include_levels': True,                   # Include entry/target/stop levels
    'include_confluence_breakdown': True      # Include detailed confluence
}


# ============================================================================
# SCANNING PARAMETERS
# ============================================================================

SCAN_INTERVAL_MINUTES = 60
MAX_STOCKS_PER_SCAN = 200
API_RATE_LIMIT_PER_MIN = 150

# Cache Configuration
ENABLE_DAILY_MA_CACHE = True
CACHE_EXPIRY_HOURS = 24
ENABLE_HISTORICAL_CACHE = True


# ============================================================================
# MARKET HOURS (US Eastern Time)
# ============================================================================

MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 30
MARKET_CLOSE_HOUR = 16
MARKET_CLOSE_MINUTE = 0

EXTENDED_HOURS_START = 4
EXTENDED_HOURS_END = 20
USE_EXTENDED_HOURS = False


# ============================================================================
# ALERT CONFIGURATION
# ============================================================================

ENABLE_TELEGRAM_ALERTS = True
INCLUDE_CHART_LINKS = True
INCLUDE_TRADE_PLAN = True


# ============================================================================
# LOGGING & OUTPUT
# ============================================================================

SAVE_SCAN_RESULTS = True
ENABLE_DETAILED_LOGGING = True
LOG_API_CALLS = False


# ============================================================================
# CONFIGURATION VALIDATION
# ============================================================================

def validate_configuration() -> bool:
    """Validate all settings"""
    issues = []
    
    # Check API keys
    if ALPHA_VANTAGE_API_KEY in ["demo", "test"]:
        issues.append("âš ï¸  Alpha Vantage API key not set")
    
    if TELEGRAM_BOT_TOKEN in ["test_token", "test"]:
        issues.append("âš ï¸  Telegram bot token not set")
    
    if TELEGRAM_CHAT_ID in ["test_id", "test"]:
        issues.append("âš ï¸  Telegram chat ID not set")
    
    # Check directories exist
    for directory in [CACHE_DIRECTORY, OUTPUT_DIRECTORY, LOG_DIRECTORY, DATA_DIRECTORY]:
        if not Path(directory).exists():
            Path(directory).mkdir(parents=True, exist_ok=True)
            print(f"ðŸ“ Created directory: {directory}")
    
    # Validate weekly watchlist config
    if WEEKLY_WATCHLIST['enabled']:
        if WEEKLY_WATCHLIST['min_confluence'] < 5.0:
            issues.append("âš ï¸  Weekly watchlist min_confluence should be >= 5.0")
    
    # Validate EOD config
    if EOD_UPDATE['enabled']:
        if EOD_UPDATE['shift_threshold'] <= 0:
            issues.append("âš ï¸  EOD shift_threshold must be > 0")
    
    # Validate Telegram threading config
    if TELEGRAM_THREADING['enabled']:
        print("â„¹ï¸  Telegram threading enabled - requires Supergroup with Topics")
    
    # Report issues
    if issues:
        print("\nâš ï¸  CONFIGURATION WARNINGS:")
        for issue in issues:
            print(f"   {issue}")
        print("\nSet environment variables for production use.\n")
        return False
    else:
        print("âœ… Configuration validated successfully")
        return True


# Auto-validate on import
if __name__ != "__main__":
    validate_configuration()