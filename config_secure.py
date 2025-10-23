# config_secure.py - SECURE CONFIGURATION
import os
from pathlib import Path

# ============================================================================
# SECURE API KEY LOADING FROM ENVIRONMENT VARIABLES
# ============================================================================

def get_env_variable(var_name: str, default: str = None) -> str:
    """
    Load environment variable securely
    
    Args:
        var_name: Environment variable name
        default: Default value for testing (optional)
    
    Returns:
        Environment variable value
        
    Raises:
        ValueError: If variable not set and no default provided
    """
    value = os.getenv(var_name, default)
    
    if value is None or value == "" or value == "your_key_here":
        raise ValueError(
            f"❌ ERROR: {var_name} not set in environment!\n"
            f"Set it with: setx {var_name} \"your_value\"\n"
            f"Then restart terminal and VS Code."
        )
    
    return value


# ============================================================================
# API KEYS - Loaded from Environment Variables (SECURE)
# ============================================================================

try:
    ALPHA_VANTAGE_API_KEY = get_env_variable('ALPHA_VANTAGE_API_KEY')
    TELEGRAM_BOT_TOKEN = get_env_variable('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = get_env_variable('TELEGRAM_CHAT_ID')
    
    print("✅ API keys loaded securely from environment variables")
    
except ValueError as e:
    print(f"\n{e}")
    print("\n⚠️  WARNING: Using demo/test mode")
    print("Set environment variables for production!\n")
    
    # Fallback for initial testing only
    ALPHA_VANTAGE_API_KEY = "demo"
    TELEGRAM_BOT_TOKEN = "test_token"
    TELEGRAM_CHAT_ID = "test_id"


# ============================================================================
# PATHS (Windows-compatible)
# ============================================================================

WATCHLIST_FILE = "data\\watchlist.xlsx"
OUTPUT_FILE = "output\\scan_results.xlsx"
LOG_FILE = "logs\\scanner.log"
CACHE_DIRECTORY = "cache"
EXCEL_FILE = "data\\AAPL_60days.csv"

# ============================================================================
# SCANNING PARAMETERS (OPTIMIZED)
# ============================================================================

SCAN_INTERVAL_MINUTES = 60
MAX_STOCKS_PER_SCAN = 200
SYMBOL_COLUMN = "Symbol"

# T-5 Predictive Scanning
PREDICTIVE_LEAD_TIME_MINUTES = 5
ENABLE_CONFIRMATION_SCAN = True

# API Configuration
API_RATE_LIMIT_PER_MIN = 150

# ============================================================================
# CACHE CONFIGURATION
# ============================================================================

ENABLE_DAILY_MA_CACHE = True
CACHE_EXPIRY_HOURS = 24
ENABLE_HISTORICAL_CACHE = True
MAX_CACHED_CANDLES = 60

# ============================================================================
# PATTERN DETECTION PARAMETERS
# ============================================================================

# Support/Resistance
SR_LOOKBACK_CANDLES = 30
SR_CLUSTER_THRESHOLD = 0.005
MAX_SR_LEVELS = 3

# Breakout Detection
BREAKOUT_LOOKBACK = 20
BREAKOUT_DISTANCE_THRESHOLD = 0.01
BREAKOUT_VOLUME_MULTIPLIER = 1.2

# Candlestick Patterns
VOLUME_SURGE_MULTIPLIER = 1.5
HAMMER_WICK_RATIO = 2.0
SHOOTING_STAR_WICK_RATIO = 2.0

# Moving Average Configurations
MA_SR_PROXIMITY_PCT = 2.0
TREND_ALIGNMENT_MIN = 3
MIN_CONFLUENCE_FOR_ALERT = 3

# ============================================================================
# CONFLUENCE SCORING (7 POINTS)
# ============================================================================

MIN_CONFLUENCE_SCORE = 4
MIN_CONFLUENCE_PERCENTAGE = 57
SEND_STRONG_SIGNALS_ONLY = False

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

ENABLE_PREDICTIVE_ALERTS = True
PREDICTIVE_ALERT_PREFIX = "⚠️ PATTERN FORMING"

ENABLE_CONFIRMATION_ALERTS = True
CONFIRMATION_ALERT_PREFIX = "✅ PATTERN CONFIRMED"
FAILED_ALERT_PREFIX = "❌ PATTERN FAILED"

INCLUDE_CHART_LINKS = True
INCLUDE_TRADE_PLAN = True
INCLUDE_SR_LEVELS = True
INCLUDE_BREAKOUT_INFO = True

# ============================================================================
# LOGGING & OUTPUT
# ============================================================================

SAVE_SCAN_RESULTS = True
ENABLE_DETAILED_LOGGING = True
LOG_API_CALLS = True

TRACK_SCAN_METRICS = True
TRACK_CONFIRMATION_RATE = True
TRACK_WIN_RATE = False

# ============================================================================
# BACKTESTING
# ============================================================================

SHEET_NAME = "Sheet1"
SYMBOL = "AAPL"

# ============================================================================
# ADVANCED SETTINGS
# ============================================================================

MAX_RETRIES_PER_STOCK = 2
RETRY_DELAY_SECONDS = 5

ENABLE_PARALLEL_SCANNING = False
MAX_WORKER_THREADS = 4

VALIDATE_OHLC_DATA = True
MIN_VOLUME_THRESHOLD = 100000
MAX_PRICE_THRESHOLD = 10000


# ============================================================================
# CONFIGURATION VALIDATION
# ============================================================================

def validate_configuration() -> bool:
    """Validate all settings"""
    issues = []
    
    # Check API keys
    if ALPHA_VANTAGE_API_KEY in ["demo", "test"]:
        issues.append("⚠️  Alpha Vantage API key not set")
    
    if TELEGRAM_BOT_TOKEN in ["test_token", "test"]:
        issues.append("⚠️  Telegram bot token not set")
    
    if TELEGRAM_CHAT_ID in ["test_id", "test"]:
        issues.append("⚠️  Telegram chat ID not set")
    
    # Check directories exist
    for directory in [CACHE_DIRECTORY, "data", "output", "logs"]:
        if not Path(directory).exists():
            Path(directory).mkdir(parents=True, exist_ok=True)
            print(f"📁 Created directory: {directory}")
    
    # Report issues
    if issues:
        print("\n⚠️  CONFIGURATION WARNINGS:")
        for issue in issues:
            print(f"   {issue}")
        print("\nSet environment variables for production use.\n")
        return False
    else:
        print("✅ Configuration validated successfully")
        return True


# Auto-validate on import
if __name__ != "__main__":
    validate_configuration()