# main.py - MVP 4.0 System Orchestrator (OPTIMIZED)
"""
Swing Trader Alert Engine - Main Entry Point

Commands:
- python main.py --scan-now          : Run immediate scan on all stocks
- python main.py --test AAPL         : Test scan on single stock
- python main.py --test-telegram     : Test Telegram configuration
- python main.py --universe          : Show stock universe
- python main.py --scheduled         : Run in automated mode
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import List

# Pandas for loading watchlist files
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("âš ï¸  pandas not installed - Excel/CSV loading limited")

# Import configuration
import config

# Import scanner
from scanner.hourly_scanner import Scanner

# P4.3, P4.4: Import optional modules
try:
    from scanner.weekly_watchlist import WeeklyWatchlist
    WATCHLIST_AVAILABLE = True
except ImportError:
    WATCHLIST_AVAILABLE = False

try:
    from scanner.eod_updater import EODUpdater
    EOD_AVAILABLE = True
except ImportError:
    EOD_AVAILABLE = False


def print_banner():
    """Print system banner"""
    print("\n" + "="*70)
    print("ðŸš€ SWING TRADER ALERT ENGINE - MVP 4.0 (OPTIMIZED)")
    print("="*70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")


def load_watchlist_from_file(filepath: str | Path) -> List[str]:
    """
    Load stock symbols from a file
    
    Supports:
    - CSV files (with 'Symbol' or 'symbol' column)
    - TXT files (one symbol per line)
    - Excel files (.xlsx, .xls) - requires pandas
    
    Args:
        filepath: Path to watchlist file
        
    Returns:
        List of stock symbols
    """
    filepath = Path(filepath)
    
    if not filepath.exists():
        return []
    
    print(f"ðŸ“‚ Loading watchlist from: {filepath}")
    
    try:
        if filepath.suffix.lower() == '.csv':
            if not PANDAS_AVAILABLE:
                with open(filepath, 'r') as f:
                    lines = f.readlines()
                    if lines and ',' in lines[0]:
                        symbols = [line.split(',')[0].strip().upper() for line in lines[1:]]
                    else:
                        symbols = [line.strip().upper() for line in lines]
            else:
                df = pd.read_csv(filepath)
                
                symbol_col = None
                for col in df.columns:
                    if col.lower() in ['symbol', 'ticker', 'stock', 'symbols']:
                        symbol_col = col
                        break
                
                if symbol_col:
                    symbols = df[symbol_col].dropna().astype(str).str.upper().tolist()
                else:
                    symbols = df.iloc[:, 0].dropna().astype(str).str.upper().tolist()
        
        elif filepath.suffix.lower() in ['.xlsx', '.xls']:
            if not PANDAS_AVAILABLE:
                print(f"   âš ï¸  pandas required for Excel files")
                return []
            
            df = pd.read_excel(filepath)
            
            symbol_col = None
            for col in df.columns:
                if col.lower() in ['symbol', 'ticker', 'stock', 'symbols']:
                    symbol_col = col
                    break
            
            if symbol_col:
                symbols = df[symbol_col].dropna().astype(str).str.upper().tolist()
            else:
                symbols = df.iloc[:, 0].dropna().astype(str).str.upper().tolist()
        
        elif filepath.suffix.lower() == '.txt':
            with open(filepath, 'r') as f:
                symbols = [line.strip().upper() for line in f if line.strip()]
        
        else:
            print(f"   âš ï¸  Unsupported file format: {filepath.suffix}")
            return []
        
        # Clean up symbols
        symbols = [s for s in symbols if s and len(s) <= 5 and s.isalpha()]
        symbols = list(dict.fromkeys(symbols))
        
        print(f"âœ… Loaded {len(symbols)} symbols")
        if len(symbols) > 0 and len(symbols) <= 10:
            print(f"   Symbols: {', '.join(symbols)}")
        elif len(symbols) > 10:
            print(f"   First 10: {', '.join(symbols[:10])} ... +{len(symbols)-10} more")
        
        return symbols
    
    except Exception as e:
        print(f"   âŒ Error loading watchlist: {e}")
        return []


def get_stock_universe() -> List[str]:
    """
    Get stock universe for scanning
    
    Priority:
    1. Load from storage/input/watchlist.csv (or .txt, .xlsx)
    2. Load from data/watchlist.csv (or .txt, .xlsx)
    3. Fall back to hardcoded list
    
    Returns:
        List of stock symbols
    """
    # Try loading from storage/input first
    storage_paths = [
        'storage/input/watchlist.csv',
        'storage/input/watchlist.txt',
        'storage/input/watchlist.xlsx',
        'storage/input/stocks.csv',
        'storage/input/stocks.txt',
        'storage/input/universe.csv',
    ]
    
    for path in storage_paths:
        symbols = load_watchlist_from_file(path)
        if symbols:
            return symbols
    
    # Try loading from data directory
    data_paths = [
        'data/watchlist.csv',
        'data/watchlist.txt',
        'data/watchlist.xlsx',
        'data/stocks.csv',
        'data/stocks.txt',
    ]
    
    for path in data_paths:
        symbols = load_watchlist_from_file(path)
        if symbols:
            return symbols
    
    # Fallback to hardcoded list
    print("No watchlist file found, using default universe")
    stocks = [
        # Tech Giants
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA',
        
        # Financial
        'JPM', 'BAC', 'WFC', 'GS', 'MS',
        
        # Healthcare
        'JNJ', 'UNH', 'PFE', 'ABBV', 'MRK',
        
        # Consumer
        'WMT', 'HD', 'DIS', 'NKE', 'MCD',
        
        # Industrial
        'BA', 'CAT', 'GE', 'UPS', 'MMM',
        
        # Energy
        'XOM', 'CVX', 'COP', 'SLB',
        
        # Communication
        'CMCSA', 'VZ', 'T', 'NFLX',
        
        # Other
        'IBM', 'INTC', 'AMD', 'ORCL', 'CSCO'
    ]
    
    initial_count = config.STOCK_UNIVERSE.get('initial_count', 50)
    return stocks[:initial_count]


def run_scan(scanner: Scanner, symbols: list):
    """
    Run scanning workflow
    
    Args:
        scanner: Scanner instance
        symbols: List of symbols to scan
    """
    print(f"Scanning {len(symbols)} stocks...\n")
    
    # Load universe
    scanner.load_stock_universe(symbols)
    
    # Run optimized parallel scan
    signals = scanner.run_scan(send_alerts=True)
    
    # Summary
    print(f"\n{'='*70}")
    print(f"FINAL SUMMARY")
    print(f"{'='*70}")
    print(f"Stocks scanned: {len(symbols)}")
    print(f"Signals generated: {len(signals)}")
    
    if signals:
        print(f"\nðŸŽ¯ ALERTS SENT:")
        for i, sig in enumerate(signals, 1):
            print(f"  {i}. {sig['symbol']}: {sig['side'].upper()} @ ${sig['price']:.2f}")
            print(f"     Quality: {sig['quality']} | Confluence: {sig['confluence']:.1f}/10")
    else:
        print("\nNo trading signals found")
    
    print(f"\n{'='*70}\n")


def test_stock(scanner: Scanner, symbol: str):
    """
    Test scanning on single stock
    
    Args:
        scanner: Scanner instance
        symbol: Stock symbol to test
    """
    scanner.test_single_stock(symbol, verbose=True)


def test_telegram(scanner: Scanner):
    """
    Test Telegram configuration
    
    Args:
        scanner: Scanner instance
    """
    print(f"\n{'='*70}")
    print(f"TESTING TELEGRAM CONFIGURATION")
    print(f"{'='*70}\n")
    
    if not scanner.telegram.is_configured():
        print("âŒ Telegram not configured")
        print("   Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in environment")
        return
    
    print("âœ… Telegram configured")
    print(f"   Bot Token: {scanner.telegram.bot_token[:10]}...")
    print(f"   Chat ID: {scanner.telegram.chat_id}")
    
    response = input("\nðŸ“¤ Send test message? (y/n): ")
    if response.lower() == 'y':
        test_message = (
            "ðŸ§ª <b>Test Message</b>\n\n"
            "This is a test from Swing Trader Alert Engine.\n"
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "If you can read this, Telegram is configured correctly!"
        )
        
        success = scanner.telegram._send_regular_message(test_message)
        
        if success:
            print("   Test message sent successfully!")
        else:
            print("   Failed to send test message")
    
    print(f"\n{'='*70}\n")


def show_universe():
    """Show stock universe"""
    symbols = get_stock_universe()
    
    print(f"\nSTOCK UNIVERSE ({len(symbols)} stocks)")
    print("="*70)
    
    print("\nStocks to scan:")
    for i, symbol in enumerate(symbols, 1):
        print(f"  {i:3d}. {symbol}", end="")
        if i % 5 == 0:
            print()
    
    if len(symbols) % 5 != 0:
        print()
    
    print(f"\n{'='*70}\n")


def main():
    """Main entry point"""
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="Swing Trader Alert Engine - MVP 4.0 (OPTIMIZED)")
    parser.add_argument('--scan-now', action='store_true', help='Run immediate scan')
    parser.add_argument('--test', type=str, metavar='SYMBOL', help='Test scan on single stock')
    parser.add_argument('--test-telegram', action='store_true', help='Test Telegram configuration')
    parser.add_argument('--universe', action='store_true', help='Show stock universe')
    parser.add_argument('--scheduled', action='store_true', help='Run in scheduled mode')
    parser.add_argument('--generate-watchlist', action='store_true', help='Generate weekly watchlist')

    args = parser.parse_args()
    
    # Print banner
    print_banner()
    
    # Validate configuration
    if not config.validate_configuration():
        print("Configuration issues detected - system in demo mode\n")
    
    # Initialize scanner
    print("Initializing optimized scanner...")
    scanner = Scanner({
        'ALPHA_VANTAGE_API_KEY': config.ALPHA_VANTAGE_API_KEY,
        'TELEGRAM_BOT_TOKEN': config.TELEGRAM_BOT_TOKEN,
        'TELEGRAM_CHAT_ID': config.TELEGRAM_CHAT_ID,
        'CACHE_DIRECTORY': config.CACHE_DIRECTORY,
        'ZONE_CONFIG': config.ZONE_CONFIG,
        'COMPONENT_WEIGHTS': config.COMPONENT_WEIGHTS,
        'CONFLUENCE_THRESHOLDS': config.CONFLUENCE_THRESHOLDS,
        'RV_REQUIREMENTS': config.RV_REQUIREMENTS,
        'MOMENTUM_CFG': config.MOMENTUM_CFG,
        'WEEKLY_WATCHLIST': config.WEEKLY_WATCHLIST,
        'EOD_UPDATE': config.EOD_UPDATE,
        'TELEGRAM_THREADING': config.TELEGRAM_THREADING,
        'MESSAGE_FORMATTING': config.MESSAGE_FORMATTING
    })
    print("Scanner ready (parallel mode: 10 workers)\n")
    
    # Execute command
    if args.scan_now:
        symbols = get_stock_universe()
        run_scan(scanner, symbols)
    
    elif args.test:
        test_stock(scanner, args.test.upper())
    
    elif args.test_telegram:
        test_telegram(scanner)
    
    elif args.universe:
        show_universe()

    elif args.generate_watchlist:
        # Generate weekly watchlist
        if scanner.watchlist_gen:
            symbols = get_stock_universe()
            
            print(f"\n📊 Generating watchlist for {len(symbols)} stocks...")
            print(f"   This may take a few minutes on first run (builds cache)\n")
            
            watchlist = scanner.watchlist_gen.generate_watchlist(symbols)
            
            if watchlist:
                # Display formatted message
                message = scanner.watchlist_gen.format_watchlist_message()
                print("\n" + "="*70)
                print("📋 WATCHLIST GENERATED")
                print("="*70)
                print(message)
                print("="*70)
                
                # Show statistics
                stats = scanner.watchlist_gen.get_stats()
                print(f"\n📊 STATISTICS:")
                print(f"   Total stocks: {stats['total']}")
                print(f"   Avg confluence: {stats['avg_confluence']:.1f}/10")
                print(f"   Support setups: {stats['supports']}")
                print(f"   Resistance setups: {stats['resistances']}")
                
                # Offer to send to Telegram
                if scanner.telegram.is_configured():
                    print()
                    response = input("📤 Send watchlist to Telegram? (y/n): ")
                    if response.lower() == 'y':
                        success = scanner.telegram._send_regular_message(message)
                        if success:
                            print("   ✅ Watchlist sent to Telegram!")
                        else:
                            print("   ❌ Failed to send to Telegram")
            else:
                print("\n⚠️  No stocks met the quality threshold")
                print("   Try lowering min_confluence in config.py")
        else:
            print("❌ Weekly watchlist not enabled")
            print("   Set WEEKLY_WATCHLIST['enabled'] = True in config.py")
    
    elif args.scheduled:
        print("🚀 Starting scheduled mode...")
        print("   Hourly scans will run Mon-Fri 10:30-15:30 ET")
        print("   Press Ctrl+C to stop\n")
        
        try:
            from utils.scheduler import TradingScheduler
            
            def scanner_callback():
                symbols = get_stock_universe()
                run_scan(scanner, symbols)
            
            scheduler = TradingScheduler(
                scanner_callback=scanner_callback,
                enable_eod=config.EOD_UPDATE.get('enabled', False),
                enable_weekly=config.WEEKLY_WATCHLIST.get('enabled', False)
            )
            
            # 🔧 FIX: Clear any existing jobs to prevent ID conflicts
            print("🔄 Clearing any existing scheduled jobs...")
            scheduler.remove_all_jobs()
            
            # start() internally calls schedule_all() and print_jobs()
            scheduler.start()
        
        except ImportError:
            print("❌ Scheduler module not available")
            print("   Run scans manually with --scan-now")
        except KeyboardInterrupt:
            print("\n\n⚠️  Scheduler stopped by user")
    
    else:
        # No arguments - show help
        parser.print_help()
        print("\n Quick start:")
        print("   python main.py --test AAPL         # Test on single stock")
        print("   python main.py --test-telegram     # Test Telegram")
        print("   python main.py --scan-now          # Run full parallel scan (FAST)")
        print("   python main.py --universe          # Show stock list")
        print("   python main.py --scheduled         # Run in automated mode")
        print("   python main.py --generate-watchlist # Generate weekly watchlist")
        print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)