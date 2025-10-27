"""
Production Logging System for Swing Trader Alert Engine
Structured logging with rotation, performance tracking, and separate log streams.

Priority: ⭐⭐⭐⭐
Purpose: Professional logging, debugging, and audit trail
"""

import logging
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import json
import sys


class TradingLogger:
    """
    Centralized logging system for trading operations.
    
    Features:
    - Separate log files: scanner, alerts, errors
    - Daily rotation with 30-day retention
    - Performance metrics tracking
    - Structured logging (JSON option)
    - Console + file output
    """
    
    def __init__(
        self,
        log_dir: str = "./logs",
        console_output: bool = True,
        json_format: bool = False
    ):
        """
        Initialize logging system.
        
        Args:
            log_dir: Directory for log files
            console_output: Also log to console
            json_format: Use JSON formatting (for log aggregation)
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.console_output = console_output
        self.json_format = json_format
        
        # Create separate loggers
        self.scanner_logger = self._setup_logger('scanner', 'scanner.log')
        self.alerts_logger = self._setup_logger('alerts', 'alerts.log')
        self.errors_logger = self._setup_logger('errors', 'errors.log', level=logging.ERROR)
        self.performance_logger = self._setup_logger('performance', 'performance.log')
        
        # Track metrics
        self.metrics: Dict[str, Any] = {
            'scans_completed': 0,
            'signals_generated': 0,
            'alerts_sent': 0,
            'errors_occurred': 0,
            'total_scan_time': 0.0
        }
    
    def _setup_logger(
        self,
        name: str,
        log_file: str,
        level: int = logging.INFO
    ) -> logging.Logger:
        """
        Setup individual logger with file and console handlers.
        
        Args:
            name: Logger name
            log_file: Log file name
            level: Logging level
        
        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(name)
        logger.setLevel(level)
        
        # Remove existing handlers to avoid duplicates
        logger.handlers.clear()
        
        # File handler with daily rotation
        file_path = self.log_dir / log_file
        file_handler = TimedRotatingFileHandler(
            filename=file_path,
            when='midnight',
            interval=1,
            backupCount=30,  # Keep 30 days
            encoding='utf-8'
        )
        file_handler.suffix = '%Y-%m-%d'
        file_handler.setLevel(level)
        
        # Format
        if self.json_format:
            formatter = JsonFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Console handler (optional)
        if self.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        return logger
    
    # =========================================================================
    # SCANNER LOGGING
    # =========================================================================
    
    def log_scan_start(self, symbol_count: int, symbols: Optional[list] = None) -> None:
        """
        Log start of scanning operation.
        
        Args:
            symbol_count: Number of symbols to scan
            symbols: Optional list of symbols
        """
        self.scanner_logger.info("="*70)
        self.scanner_logger.info(f"SCAN START - {symbol_count} symbols")
        if symbols:
            self.scanner_logger.info(f"Symbols: {', '.join(symbols[:10])}...")
        self.scanner_logger.info("="*70)
    
    def log_scan_complete(
        self,
        duration: float,
        signal_count: int,
        symbols_scanned: int
    ) -> None:
        """
        Log completion of scanning operation.
        
        Args:
            duration: Scan duration in seconds
            signal_count: Number of signals generated
            symbols_scanned: Number of symbols processed
        """
        self.scanner_logger.info("-"*70)
        self.scanner_logger.info(f"SCAN COMPLETE")
        self.scanner_logger.info(f"Duration: {duration:.2f}s")
        self.scanner_logger.info(f"Symbols scanned: {symbols_scanned}")
        self.scanner_logger.info(f"Signals generated: {signal_count}")
        self.scanner_logger.info(f"Avg per symbol: {duration/symbols_scanned:.2f}s")
        self.scanner_logger.info("="*70)
        
        # Update metrics
        self.metrics['scans_completed'] += 1
        self.metrics['total_scan_time'] += duration
        self.metrics['signals_generated'] += signal_count
    
    def log_symbol_scan(
        self,
        symbol: str,
        price: float,
        zones_found: int,
        pattern: Optional[str] = None
    ) -> None:
        """
        Log individual symbol scan.
        
        Args:
            symbol: Stock symbol
            price: Current price
            zones_found: Number of zones detected
            pattern: Pattern detected (if any)
        """
        msg = f"📊 {symbol}: ${price:.2f} | {zones_found} zones"
        if pattern:
            msg += f" | Pattern: {pattern}"
        self.scanner_logger.info(msg)
    
    def log_signal_generated(
        self,
        symbol: str,
        side: str,
        pattern: str,
        confluence: float,
        price: float,
        zone_id: str
    ) -> None:
        """
        Log signal generation.
        
        Args:
            symbol: Stock symbol
            side: 'long' or 'short'
            pattern: Pattern name
            confluence: Confluence score
            price: Signal price
            zone_id: Zone identifier
        """
        emoji = "🟢" if side == "long" else "🔴"
        self.scanner_logger.info(
            f"{emoji} SIGNAL: {symbol} | {side.upper()} | {pattern} | "
            f"Confluence: {confluence:.1f}/10 | ${price:.2f} @ {zone_id}"
        )
    
    # =========================================================================
    # ALERT LOGGING
    # =========================================================================
    
    def log_alert_sent(
        self,
        symbol: str,
        success: bool,
        quality: str,
        message_preview: Optional[str] = None
    ) -> None:
        """
        Log alert delivery.
        
        Args:
            symbol: Stock symbol
            success: Whether alert was sent successfully
            quality: Signal quality (premium/standard/speculative)
            message_preview: First line of alert message
        """
        status = "✅ SENT" if success else "❌ FAILED"
        self.alerts_logger.info(
            f"{status} | {symbol} | {quality.upper()} | {message_preview or 'N/A'}"
        )
        
        if success:
            self.metrics['alerts_sent'] += 1
    
    def log_alert_suppressed(
        self,
        symbol: str,
        reason: str
    ) -> None:
        """
        Log suppressed alert (cooldown, earnings, etc).
        
        Args:
            symbol: Stock symbol
            reason: Suppression reason
        """
        self.alerts_logger.info(f"⏸️  SUPPRESSED | {symbol} | Reason: {reason}")
    
    # =========================================================================
    # ERROR LOGGING
    # =========================================================================
    
    def log_error(
        self,
        error: Exception,
        context: str,
        symbol: Optional[str] = None
    ) -> None:
        """
        Log error with context.
        
        Args:
            error: Exception object
            context: What was happening when error occurred
            symbol: Optional symbol being processed
        """
        symbol_str = f"[{symbol}] " if symbol else ""
        self.errors_logger.error(
            f"❌ {symbol_str}{context}: {type(error).__name__}: {error}",
            exc_info=True
        )
        
        self.metrics['errors_occurred'] += 1
    
    def log_warning(self, message: str, symbol: Optional[str] = None) -> None:
        """
        Log warning message.
        
        Args:
            message: Warning message
            symbol: Optional symbol context
        """
        symbol_str = f"[{symbol}] " if symbol else ""
        self.scanner_logger.warning(f"⚠️  {symbol_str}{message}")
    
    # =========================================================================
    # PERFORMANCE LOGGING
    # =========================================================================
    
    def log_performance(
        self,
        operation: str,
        duration: float,
        symbol: Optional[str] = None,
        details: Optional[Dict] = None
    ) -> None:
        """
        Log performance metrics.
        
        Args:
            operation: Operation name
            duration: Duration in seconds
            symbol: Optional symbol
            details: Optional additional details
        """
        symbol_str = f"[{symbol}] " if symbol else ""
        details_str = f" | {details}" if details else ""
        
        self.performance_logger.info(
            f"{symbol_str}{operation}: {duration:.3f}s{details_str}"
        )
    
    def log_api_call(
        self,
        service: str,
        endpoint: str,
        duration: float,
        status: str
    ) -> None:
        """
        Log API call performance.
        
        Args:
            service: Service name (e.g., 'AlphaVantage')
            endpoint: API endpoint
            duration: Request duration
            status: 'success' or 'failed'
        """
        status_emoji = "✅" if status == "success" else "❌"
        self.performance_logger.info(
            f"{status_emoji} API | {service} | {endpoint} | {duration:.3f}s"
        )
    
    # =========================================================================
    # METRICS & REPORTING
    # =========================================================================
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current metrics.
        
        Returns:
            Dictionary of metrics
        """
        return self.metrics.copy()
    
    def log_daily_summary(self) -> None:
        """
        Log daily summary (call at end of trading day).
        """
        self.scanner_logger.info("\n" + "="*70)
        self.scanner_logger.info("DAILY SUMMARY")
        self.scanner_logger.info("="*70)
        self.scanner_logger.info(f"Scans completed: {self.metrics['scans_completed']}")
        self.scanner_logger.info(f"Signals generated: {self.metrics['signals_generated']}")
        self.scanner_logger.info(f"Alerts sent: {self.metrics['alerts_sent']}")
        self.scanner_logger.info(f"Errors occurred: {self.metrics['errors_occurred']}")
        
        if self.metrics['scans_completed'] > 0:
            avg_time = self.metrics['total_scan_time'] / self.metrics['scans_completed']
            self.scanner_logger.info(f"Avg scan time: {avg_time:.2f}s")
        
        self.scanner_logger.info("="*70 + "\n")
    
    def reset_daily_metrics(self) -> None:
        """
        Reset daily metrics (call at start of new trading day).
        """
        self.metrics = {
            'scans_completed': 0,
            'signals_generated': 0,
            'alerts_sent': 0,
            'errors_occurred': 0,
            'total_scan_time': 0.0
        }
        self.scanner_logger.info("🔄 Daily metrics reset")
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def info(self, message: str, logger_name: str = 'scanner') -> None:
        """Generic info log."""
        logger = getattr(self, f'{logger_name}_logger')
        logger.info(message)
    
    def debug(self, message: str, logger_name: str = 'scanner') -> None:
        """Generic debug log."""
        logger = getattr(self, f'{logger_name}_logger')
        logger.debug(message)
    
    def get_log_files(self) -> Dict[str, Path]:
        """
        Get paths to all log files.
        
        Returns:
            Dictionary mapping log type to file path
        """
        return {
            'scanner': self.log_dir / 'scanner.log',
            'alerts': self.log_dir / 'alerts.log',
            'errors': self.log_dir / 'errors.log',
            'performance': self.log_dir / 'performance.log'
        }


class JsonFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    Useful for log aggregation systems (ELK, Splunk, etc).
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record
        
        Returns:
            JSON string
        """
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def setup_logger(
    name: str = 'trading',
    log_file: Optional[str] = None,
    level: int = logging.INFO,
    log_dir: str = './logs'
) -> logging.Logger:
    """
    Quick setup for a single logger (backward compatibility).
    
    Args:
        name: Logger name
        log_file: Log file name
        level: Logging level
        log_dir: Log directory
    
    Returns:
        Configured logger
    """
    log_dir_path = Path(log_dir)
    log_dir_path.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()
    
    # File handler
    if log_file:
        file_path = log_dir_path / log_file
        handler = TimedRotatingFileHandler(
            filename=file_path,
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        handler.suffix = '%Y-%m-%d'
        handler.setLevel(level)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    )
    logger.addHandler(console_handler)
    
    return logger


# =============================================================================
# TESTING FUNCTIONS
# =============================================================================

def test_basic_logging():
    """Test basic logging functionality."""
    print("\n" + "="*70)
    print("TEST 1: Basic Logging")
    print("="*70)
    
    logger = TradingLogger(log_dir="./test_logs")
    
    # Test scan logging
    logger.log_scan_start(5, ["AAPL", "TSLA", "NVDA", "GOOGL", "MSFT"])
    logger.log_symbol_scan("AAPL", 264.82, 12, "hammer")
    logger.log_signal_generated("AAPL", "long", "hammer", 9.5, 264.82, "zone_ema20_264.16")
    logger.log_scan_complete(45.2, 3, 5)
    
    # Test alert logging
    logger.log_alert_sent("AAPL", True, "premium", "🟢 AAPL LONG SIGNAL")
    logger.log_alert_suppressed("TSLA", "cooldown active")
    
    # Test error logging
    try:
        raise ValueError("Test error")
    except Exception as e:
        logger.log_error(e, "Testing error handling", "NVDA")
    
    logger.log_warning("Test warning message", "GOOGL")
    
    # Test performance logging
    logger.log_performance("Zone calculation", 1.234, "MSFT")
    logger.log_api_call("AlphaVantage", "TIME_SERIES_DAILY", 0.856, "success")
    
    print("\n✅ Basic logging test complete")
    print(f"   Check logs in: {logger.log_dir}")


def test_metrics():
    """Test metrics tracking."""
    print("\n" + "="*70)
    print("TEST 2: Metrics Tracking")
    print("="*70)
    
    logger = TradingLogger(log_dir="./test_logs")
    
    # Simulate some operations
    logger.log_scan_start(10)
    logger.log_scan_complete(30.5, 5, 10)
    logger.log_alert_sent("AAPL", True, "premium")
    logger.log_alert_sent("TSLA", True, "standard")
    logger.log_alert_sent("NVDA", False, "premium")
    
    try:
        raise RuntimeError("Test error")
    except Exception as e:
        logger.log_error(e, "Test context")
    
    # Get metrics
    metrics = logger.get_metrics()
    print("\n📊 Metrics:")
    for key, value in metrics.items():
        print(f"   • {key}: {value}")
    
    # Log daily summary
    logger.log_daily_summary()
    
    print("\n✅ Metrics tracking test complete")


def test_json_logging():
    """Test JSON formatted logging."""
    print("\n" + "="*70)
    print("TEST 3: JSON Logging")
    print("="*70)
    
    logger = TradingLogger(log_dir="./test_logs", json_format=True, console_output=False)
    
    logger.log_scan_start(5)
    logger.log_signal_generated("AAPL", "long", "hammer", 9.5, 264.82, "zone_1")
    logger.log_alert_sent("AAPL", True, "premium")
    
    print("✅ JSON logging test complete")
    print(f"   Check JSON logs in: {logger.log_dir}")


def test_log_rotation():
    """Test log rotation setup."""
    print("\n" + "="*70)
    print("TEST 4: Log Rotation")
    print("="*70)
    
    logger = TradingLogger(log_dir="./test_logs")
    
    # Write many log entries
    for i in range(100):
        logger.scanner_logger.info(f"Test log entry {i}")
    
    log_files = logger.get_log_files()
    print("\n📁 Log Files:")
    for name, path in log_files.items():
        if path.exists():
            size = path.stat().st_size
            print(f"   • {name}: {path} ({size} bytes)")
    
    print("\n✅ Log rotation test complete")


def run_all_tests():
    """Run complete test suite."""
    print("\n" + "="*70)
    print("LOGGING SYSTEM TEST SUITE")
    print("="*70)
    
    test_basic_logging()
    test_metrics()
    test_json_logging()
    test_log_rotation()
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED!")
    print("="*70)
     # >>> add this <<<
     
    import logging, time
    logging.shutdown()          # flush & close all handlers
    time.sleep(0.1)             # tiny pause helps on Windows

    # Cleanup
    import shutil
    if Path("./test_logs").exists():
        shutil.rmtree("./test_logs")
        print("\n🧹 Cleaned up test files")


# =============================================================================
# INTEGRATION EXAMPLE
# =============================================================================

def integration_example():
    """
    Example of how to integrate with the trading system.
    """
    print("\n" + "="*70)
    print("INTEGRATION EXAMPLE")
    print("="*70)
    
    print("""
# In main.py:

from utils.logger import TradingLogger
import time

# Initialize logger
logger = TradingLogger(log_dir="./logs")

# Start scan
logger.log_scan_start(symbol_count=50)

start_time = time.time()

# Scan each symbol
for symbol in symbols:
    try:
        # Your scanning logic
        zones = build_zones(symbol)
        pattern = detect_pattern(symbol)
        
        logger.log_symbol_scan(symbol, price, len(zones), pattern)
        
        if has_signal:
            logger.log_signal_generated(
                symbol, side, pattern, confluence, price, zone_id
            )
            
            # Try to send alert
            success = send_telegram_alert(symbol, signal_data)
            logger.log_alert_sent(symbol, success, quality)
    
    except Exception as e:
        logger.log_error(e, "Scanning symbol", symbol)

# Complete scan
duration = time.time() - start_time
logger.log_scan_complete(duration, signal_count, len(symbols))

# End of day
logger.log_daily_summary()
logger.reset_daily_metrics()
    """)


if __name__ == "__main__":
    # Run tests
    run_all_tests()
    
    # Show integration example
    integration_example()
