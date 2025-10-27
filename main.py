# main.py - MVP 4.0 System Orchestrator
"""
Swing Trader Alert Engine - Main Entry Point

Commands:
- python main.py --scan-now          : Run immediate scan on all stocks
- python main.py --test AAPL         : Test scan on single stock
- python main.py --test-telegram     : Test Telegram configuration
- python main.py --universe          : Show stock universe
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
    print("⚠️  pandas not installed - Excel/CSV loading limited")

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
    print("🚀 SWING TRADER ALERT ENGINE - MVP 4.0")
    print("="*70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Configuration: Loading stock universe...")
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
    
    print(f"📂 Loading watchlist from: {filepath}")
    
    try:
        # Determine file type and load accordingly
        if filepath.suffix.lower() == '.csv':
            if not PANDAS_AVAILABLE:
                # Fallback: manual CSV parsing
                with open(filepath, 'r') as f:
                    lines = f.readlines()
                    # Skip header if present
                    if lines and ',' in lines[0]:
                        symbols = [line.split(',')[0].strip().upper() for line in lines[1:]]
                    else:
                        symbols = [line.strip().upper() for line in lines]
            else:
                # Load CSV file with pandas
                df = pd.read_csv(filepath)
                
                # Try to find symbol column (case-insensitive)
                symbol_col = None
                for col in df.columns:
                    if col.lower() in ['symbol', 'ticker', 'stock', 'symbols']:
                        symbol_col = col
                        break
                
                if symbol_col:
                    symbols = df[symbol_col].dropna().astype(str).str.upper().tolist()
                else:
                    # Assume first column is symbols
                    symbols = df.iloc[:, 0].dropna().astype(str).str.upper().tolist()
        
        elif filepath.suffix.lower() in ['.xlsx', '.xls']:
            if not PANDAS_AVAILABLE:
                print(f"   ⚠️  pandas required for Excel files - install with: pip install pandas openpyxl")
                return []
            
            # Load Excel file
            df = pd.read_excel(filepath)
            
            # Try to find symbol column (case-insensitive)
            symbol_col = None
            for col in df.columns:
                if col.lower() in ['symbol', 'ticker', 'stock', 'symbols']:
                    symbol_col = col
                    break
            
            if symbol_col:
                symbols = df[symbol_col].dropna().astype(str).str.upper().tolist()
            else:
                # Assume first column is symbols
                symbols = df.iloc[:, 0].dropna().astype(str).str.upper().tolist()
        
        elif filepath.suffix.lower() == '.txt':
            # Load text file (one symbol per line)
            with open(filepath, 'r') as f:
                symbols = [line.strip().upper() for line in f if line.strip()]
        
        else:
            print(f"   ⚠️  Unsupported file format: {filepath.suffix}")
            return []
        
        # Clean up symbols (remove empty strings, duplicates)
        symbols = [s for s in symbols if s and len(s) <= 5 and s.isalpha()]
        symbols = list(dict.fromkeys(symbols))  # Remove duplicates while preserving order
        
        print(f"✅ Loaded {len(symbols)} symbols from {filepath.name}")
        
        if len(symbols) > 0:
            print(f"   First 10: {', '.join(symbols[:10])}")
            if len(symbols) > 10:
                print(f"   ... and {len(symbols) - 10} more")
        
        return symbols
    
    except Exception as e:
        print(f"   ❌ Error loading watchlist: {e}")
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
        'storage/input/watchlist.xls',
        'storage/input/stocks.csv',
        'storage/input/stocks.txt',
        'storage/input/universe.csv',
        'storage/input/universe.txt',
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
    print("ℹ️  No watchlist file found, using default universe")
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
    
    # Limit to initial_count from config
    initial_count = config.STOCK_UNIVERSE.get('initial_count', 50)
    return stocks[:initial_count]


def run_scan(scanner: Scanner, symbols: list):
    """
    Run scanning workflow
    
    Args:
        scanner: Scanner instance
        symbols: List of symbols to scan
    """
    print(f"📊 Running scan on {len(symbols)} stocks...\n")
    
    # Load universe
    scanner.load_stock_universe(symbols)
    
    # Run scan with alerts
    signals = scanner.run_scan(send_alerts=True)
    
    # Summary
    print(f"\n{'='*70}")
    print(f"📈 SCAN SUMMARY")
    print(f"{'='*70}")
    print(f"Total stocks scanned: {len(symbols)}")
    print(f"Signals generated: {len(signals)}")
    
    if signals:
        print(f"\n🎯 QUALIFIED SIGNALS:")
        for sig in signals:
            watchlist_badge = "⭐" if sig['from_watchlist'] else "🆕"
            print(f"  {watchlist_badge} {sig['symbol']}: {sig['side'].upper()} @ ${sig['price']:.2f}")
            print(f"     Pattern: {sig['pattern']['pattern']}")
            print(f"     Quality: {sig['quality']} ({sig['confluence']['total_score']:.1f}/10)")
            print(f"     Zone: {sig['zone']['type']} ${sig['zone']['mid']:.2f}")
            print()
    else:
        print("\n⚠️  No qualified signals found")
        print("    This is normal - not every scan produces signals")
    
    print(f"{'='*70}\n")


def test_stock(scanner: Scanner, symbol: str):
    """
    Test scan on a single stock
    
    Args:
        scanner: Scanner instance
        symbol: Stock symbol to test
    """
    print(f"🔍 Testing scan on {symbol}...\n")
    
    # Get market regime
    market_regime = scanner.index_regime.get_market_regime()
    print(scanner.index_regime.format_regime_summary(market_regime))
    
    # Scan stock
    signal = scanner.scan_stock(symbol, market_regime)
    
    if signal:
        print(f"\n✅ SIGNAL GENERATED!")
        sym = signal.get("symbol", "N/A")
        side = (signal.get("side")
                or signal.get("direction")
                or signal.get("signal_side")
                or "UNKNOWN")
        price = signal.get("price")
        quality = signal.get("quality", "N/A")
        patt = (signal.get("pattern", {}) or {}).get("pattern", "N/A")
        rv = (signal.get("pattern", {}) or {}).get("relative_volume")
        conf = (signal.get("confluence", {}) or {}).get("total_score")
        zone_type = (signal.get("zone", {}) or {}).get("type", "N/A")
        zone_mid = (signal.get("zone", {}) or {}).get("mid")

        print(f"   Symbol: {sym}")
        print(f"   Side: {side.upper()}")
        print(f"   Quality: {quality}")
        print(f"   Price: ${price:.2f}" if isinstance(price, (int, float)) else f"   Price: {price}")
        print(f"   Pattern: {patt}")
        print(f"   RV: {rv:.2f}x" if isinstance(rv, (int, float)) else f"   RV: {rv}")
        print(f"   Confluence: {conf:.1f}/10" if isinstance(conf, (int, float)) else f"   Confluence: {conf}")
        print(f"   Zone: {zone_type} ${zone_mid:.2f}" if isinstance(zone_mid, (int, float)) else f"   Zone: {zone_type} {zone_mid}")

        
        # Ask if user wants to send alert
        response = input("\n📤 Send Telegram alert? (y/n): ")
        if response.lower() == 'y':
            success = scanner.telegram.send_alert(signal)
            if success:
                print("   ✅ Alert sent!")
            else:
                print("   ❌ Failed to send alert")
    else:
        print(f"\n⚠️  No signal generated for {symbol}")
        print("    Possible reasons:")
        print("    - No patterns detected")
        print("    - Price not near any zones")
        print("    - Quality threshold not met")
        print("    - Signal suppressed by market regime")


def test_telegram(scanner: Scanner):
    """
    Test Telegram configuration
    
    Args:
        scanner: Scanner instance
    """
    print("📱 Testing Telegram configuration...\n")
    
    if not scanner.telegram.is_configured():
        print("❌ Telegram not configured")
        print("\nPlease set environment variables:")
        print("  export TELEGRAM_BOT_TOKEN='your_bot_token'")
        print("  export TELEGRAM_CHAT_ID='your_chat_id'")
        return
    
    print("✅ Telegram configured")
    print(f"   Bot Token: {scanner.telegram.bot_token[:20]}...")
    print(f"   Chat ID: {scanner.telegram.chat_id}")
    
    # Send test message
    print("\n📤 Sending test message...")
    success = scanner.telegram.send_test_message()
    
    if success:
        print("✅ Test message sent successfully!")
        print("   Check your Telegram app")
    else:
        print("❌ Failed to send test message")
        print("   Check bot token and chat ID")



def run_weekly_watchlist(scanner: Scanner):
    """
    P4.3: Generate weekly watchlist (Sunday evening)
    
    Args:
        scanner: Scanner instance
    """
    if not WATCHLIST_AVAILABLE:
        print("❌ Weekly watchlist module not available")
        print("   Install it to use this feature")
        return
    
    if not scanner.watchlist_gen:
        print("❌ Weekly watchlist not enabled in config")
        print("   Set WEEKLY_WATCHLIST['enabled'] = True")
        return
    
    print(f"\n{'='*70}")
    print(f"📋 GENERATING WEEKLY WATCHLIST")
    print(f"{'='*70}\n")
    
    # Get universe
    symbols = get_stock_universe()
    
    # Generate watchlist
    print(f"📊 Scanning {len(symbols)} symbols for best setups...")
    watchlist = scanner.watchlist_gen.generate_watchlist(symbols)
    
    # Format message
    message = scanner.watchlist_gen.format_watchlist_message()
    
    # Send to Telegram
    if scanner.telegram.is_configured():
        response = input("\n📤 Send watchlist to Telegram? (y/n): ")
        if response.lower() == 'y':
            success = scanner.telegram.send_watchlist(message)
            if success:
                print("   ✅ Watchlist sent!")
            else:
                print("   ❌ Failed to send watchlist")
    
    # Summary
    print(f"\n{'='*70}")
    print(f"✅ WATCHLIST GENERATED")
    print(f"{'='*70}")
    print(f"Total qualifying stocks: {len(watchlist)}")
    if watchlist:
        print(f"\n📋 WATCHLIST:")
        for i, stock in enumerate(watchlist, 1):
            print(f"  {i:2d}. {stock['symbol']}: {stock['zone_type']} @ ${stock['zone_mid']:.2f}")
            print(f"      Confluence: {stock['confluence']:.1f}/10")
    
    print(f"\n{'='*70}\n")


def run_eod_update(scanner: Scanner):
    """
    P4.4: Run end-of-day update (Mon-Thu 17:00 ET)
    
    Args:
        scanner: Scanner instance
    """
    if not EOD_AVAILABLE:
        print("❌ EOD updater module not available")
        print("   Install it to use this feature")
        return
    
    print(f"\n{'='*70}")
    print(f"🔄 RUNNING EOD UPDATE")
    print(f"{'='*70}\n")
    
    # Initialize EOD updater
    eod_updater = EODUpdater(
        scanner=scanner,
        shift_threshold=config.EOD_UPDATE.get('shift_threshold', 0.5)
    )
    
    # Check if should run
    if not eod_updater.should_run_update():
        print("⚠️  EOD update should not run now")
        print("   Run on Mon-Thu after market close")
        return
    
    # Get universe
    symbols = get_stock_universe()
    
    # Run update
    print(f"📊 Updating {len(symbols)} symbols...")
    stats = eod_updater.update_all(symbols)
    
    # Send shift alerts if significant
    if stats.get('significant_shifts'):
        alert = eod_updater.format_shift_alert(stats)
        if scanner.telegram.is_configured():
            response = input("\n📤 Send shift alerts to Telegram? (y/n): ")
            if response.lower() == 'y':
                scanner.telegram._send_regular_message(alert)
    
    # Summary
    print(f"\n{'='*70}")
    print(f"✅ EOD UPDATE COMPLETE")
    print(f"{'='*70}")
    print(f"Updated: {stats.get('updated', 0)}/{len(symbols)}")
    print(f"Significant shifts: {stats.get('significant_shifts', 0)}")
    print(f"\n{'='*70}\n")


def show_universe():
    """Show stock universe"""
    symbols = get_stock_universe()
    
    print(f"📊 STOCK UNIVERSE ({len(symbols)} stocks)")
    print("="*70)
    
    # Group by sector (simplified)
    print("\nStocks to scan:")
    for i, symbol in enumerate(symbols, 1):
        print(f"  {i:2d}. {symbol}", end="")
        if i % 5 == 0:
            print()
    
    if len(symbols) % 5 != 0:
        print()
    
    print(f"\n{'='*70}\n")


def main():
    """Main entry point"""
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="Swing Trader Alert Engine - MVP 4.0")
    parser.add_argument('--scan-now', action='store_true', help='Run immediate scan')
    parser.add_argument('--test', type=str, metavar='SYMBOL', help='Test scan on single stock')
    parser.add_argument('--test-telegram', action='store_true', help='Test Telegram configuration')
    parser.add_argument('--universe', action='store_true', help='Show stock universe')
    parser.add_argument('--verbose', action='store_true', help='Verbose output (show all zones, indicators)')
    
    # P4.3, P4.4: New commands
    parser.add_argument('--generate-watchlist', action='store_true', help='Generate weekly watchlist (P4.3)')
    parser.add_argument('--eod-update', action='store_true', help='Run end-of-day update (P4.4)')
    parser.add_argument('--scheduled', action='store_true', help='Run in scheduled mode (all features)')

    args = parser.parse_args()
    
    # Print banner
    print_banner()
    
    # Validate configuration
    if not config.validate_configuration():
        print("\n⚠️  Configuration issues detected")
        print("System will work in demo mode\n")
    
    # Initialize scanner
    print("🔧 Initializing scanner...")
    scanner = Scanner({
        'ALPHA_VANTAGE_API_KEY': config.ALPHA_VANTAGE_API_KEY,
        'TELEGRAM_BOT_TOKEN': config.TELEGRAM_BOT_TOKEN,
        'TELEGRAM_CHAT_ID': config.TELEGRAM_CHAT_ID,
        'CACHE_DIRECTORY': config.CACHE_DIRECTORY,
        'ZONE_CONFIG': config.ZONE_CONFIG,
        'COMPONENT_WEIGHTS': config.COMPONENT_WEIGHTS,
        'CONFLUENCE_THRESHOLDS': config.CONFLUENCE_THRESHOLDS,
        'RV_REQUIREMENTS': config.RV_REQUIREMENTS,
        # P4.3, P4.4, P5.1, P5.2: New configurations
        'WEEKLY_WATCHLIST': config.WEEKLY_WATCHLIST,
        'EOD_UPDATE': config.EOD_UPDATE,
        'TELEGRAM_THREADING': config.TELEGRAM_THREADING,
        'MESSAGE_FORMATTING': config.MESSAGE_FORMATTING
    })
    print("✅ Scanner initialized\n")
    
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
    
    # P4.3: Generate weekly watchlist
    elif args.generate_watchlist:
        run_weekly_watchlist(scanner)
    
    # P4.4: Run EOD update
    elif args.eod_update:
        run_eod_update(scanner)
    
    # Run scheduled mode (with all features)
    elif args.scheduled:
        print("🚀 Starting scheduled mode...")
        print("   This will run hourly scans, EOD updates, and weekly watchlist")
        print("   Press Ctrl+C to stop\n")
        
        try:
            from utils.scheduler import TradingScheduler
            
            def scanner_callback():
                """Callback for scheduled scans"""
                symbols = get_stock_universe()
                run_scan(scanner, symbols)
            
            # Create scheduler
            scheduler = TradingScheduler(
                scanner_callback=scanner_callback,
                enable_eod=config.EOD_UPDATE.get('enabled', False),
                enable_weekly=config.WEEKLY_WATCHLIST.get('enabled', False)
            )
            
            # Schedule all jobs
            scheduler.schedule_all()
            
            # Print schedule
            scheduler.print_jobs()
            
            # Start scheduler (blocking)
            scheduler.start()
        
        except ImportError:
            print("❌ Scheduler module not available")
            print("   Run scans manually with --scan-now")
        except KeyboardInterrupt:
            print("\n\n⚠️  Scheduler stopped by user")
    
    else:
        # No arguments - show help
        parser.print_help()
        print("\n💡 Quick start:")
        print("   python main.py --test AAPL              # Test on single stock")
        print("   python main.py --test-telegram          # Test Telegram")
        print("   python main.py --scan-now               # Run full scan")
        print("   python main.py --generate-watchlist     # Generate weekly watchlist (P4.3)")
        print("   python main.py --eod-update             # Run EOD update (P4.4)")
        print("   python main.py --scheduled              # Run in automated mode")
        print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Scan interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)