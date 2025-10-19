# realtime_scanner.py - Production Real-time Scanner

import sys
import os
from datetime import datetime
import pandas as pd
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.alphavantage_client import AlphaVantageClient, MarketScheduler
from modules.pattern_detector import PatternDetector
from modules.technical_indicators import TechnicalIndicators
from modules.telegram_handler import TelegramHandler
import config_secure as config


class RealtimeScanner:
    """
    Production-ready real-time scanner
    Optimized for 150 API calls/min, 200 stocks, 3-min alert window
    """
    
    def __init__(self, api_key: str, telegram_bot: str, telegram_chat: str):
        self.av_client = AlphaVantageClient(api_key, rate_limit_per_min=150)
        self.telegram = TelegramHandler(telegram_bot, telegram_chat)
        self.detector = PatternDetector(vars(config))
        self.symbols = []
        
    def load_watchlist(self, file_path: str) -> List[str]:
        """Load symbols from Excel/CSV"""
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            symbols = df['Symbol'].dropna().str.upper().tolist()
            self.symbols = symbols[:200]  # Limit to 200 for optimization
            
            print(f"✅ Loaded {len(self.symbols)} symbols from watchlist\n")
            return self.symbols
            
        except Exception as e:
            print(f"❌ Error loading watchlist: {e}")
            return []
    
    def analyze_stock(self, stock_data: Dict) -> Dict:
        """
        Analyze single stock for patterns and confluence
        Uses data from Alpha Vantage API (already has indicators)
        """
        try:
            # Build DataFrame for pattern detection
            df = stock_data['full_data'].copy()
            
            # Add indicators from API to DataFrame
            latest_idx = len(df) - 1
            df.loc[latest_idx, 'EMA_20'] = stock_data['ema_20']
            df.loc[latest_idx, 'SMA_50'] = stock_data['sma_50']
            df.loc[latest_idx, 'SMA_100'] = stock_data['sma_100']
            df.loc[latest_idx, 'SMA_200'] = stock_data['sma_200']
            
            # Detect patterns on latest 2 candles only (for speed)
            recent_df = df.iloc[-10:].copy()  # Only check last 10 candles
            
            # Check for patterns
            patterns_found = []
            
            # Bullish Engulfing
            engulfing_bull = self.detector.detect_bullish_engulfing(recent_df)
            if engulfing_bull and engulfing_bull[-1]['date'] == df.iloc[-1]['Date']:
                patterns_found.append(engulfing_bull[-1])
            
            # Bearish Engulfing
            engulfing_bear = self.detector.detect_bearish_engulfing(recent_df)
            if engulfing_bear and engulfing_bear[-1]['date'] == df.iloc[-1]['Date']:
                patterns_found.append(engulfing_bear[-1])
            
            # Hammer
            hammer = self.detector.detect_hammer(recent_df)
            if hammer and hammer[-1]['date'] == df.iloc[-1]['Date']:
                patterns_found.append(hammer[-1])
            
            # Shooting Star
            shooting = self.detector.detect_shooting_star(recent_df)
            if shooting and shooting[-1]['date'] == df.iloc[-1]['Date']:
                patterns_found.append(shooting[-1])
            
            # Breakout
            breakout = self.detector.detect_breakout(recent_df)
            if breakout and breakout[-1]['date'] == df.iloc[-1]['Date']:
                patterns_found.append(breakout[-1])
            
            if not patterns_found:
                return None
            
            # Analyze confluence for each pattern
            results = []
            for pattern in patterns_found:
                # Build trend analysis from API data
                trend_analysis = {
                    'price': stock_data['close'],
                    'ema_20': stock_data['ema_20'],
                    'sma_50': stock_data['sma_50'],
                    'sma_100': stock_data['sma_100'],
                    'sma_200': stock_data['sma_200'],
                    'above_ema_20': stock_data['close'] > stock_data['ema_20'] if stock_data['ema_20'] else None,
                    'above_sma_50': stock_data['close'] > stock_data['sma_50'] if stock_data['sma_50'] else None,
                    'above_sma_100': stock_data['close'] > stock_data['sma_100'] if stock_data['sma_100'] else None,
                    'above_sma_200': stock_data['close'] > stock_data['sma_200'] if stock_data['sma_200'] else None,
                }
                
                trend_analysis['primary_trend'] = TechnicalIndicators.determine_primary_trend(trend_analysis)
                trend_analysis['ma_support_resistance'] = TechnicalIndicators.find_nearest_support_resistance(trend_analysis)
                
                # Evaluate confluence
                confluence = TechnicalIndicators.evaluate_pattern_confluence(
                    pattern['bias'],
                    trend_analysis
                )
                
                # Only return STRONG or GOOD signals
                if confluence['recommendation'] in ['STRONG_SIGNAL', 'GOOD_SIGNAL']:
                    results.append({
                        'symbol': stock_data['symbol'],
                        'pattern': pattern,
                        'trend_analysis': trend_analysis,
                        'confluence': confluence
                    })
            
            return results if results else None
            
        except Exception as e:
            print(f"   ⚠️  Error analyzing {stock_data['symbol']}: {e}")
            return None
    
    def scan_all_stocks(self):
        """
        Main scanning loop - optimized for speed
        
        Timeline for 200 stocks:
        - Fetch data: ~6.7 minutes (200 stocks × 5 calls ÷ 150 calls/min)
        - Analyze: ~10 seconds (very fast, all local computation)
        - Total: ~7 minutes (well within 60-min candle window)
        """
        print(f"\n{'='*80}")
        print(f"📊 REAL-TIME SCAN: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")
        
        # 1. Fetch all stock data (bulk operation)
        all_stock_data = self.av_client.batch_fetch_stocks(self.symbols, interval="60min")
        
        if not all_stock_data:
            print("❌ No data retrieved. Check API key and rate limits.\n")
            return
        
        print(f"\n{'='*80}")
        print(f"🔍 ANALYZING {len(all_stock_data)} STOCKS FOR PATTERNS...")
        print(f"{'='*80}\n")
        
        # 2. Analyze each stock (very fast - all local)
        signals_found = []
        
        for stock_data in all_stock_data:
            results = self.analyze_stock(stock_data)
            
            if results:
                for result in results:
                    signals_found.append(result)
                    print(f"🎯 SIGNAL: {result['symbol']} - {result['pattern']['pattern']} "
                          f"({result['confluence']['recommendation']})")
        
        # 3. Send Telegram alerts immediately
        if signals_found:
            print(f"\n{'='*80}")
            print(f"📤 SENDING {len(signals_found)} TELEGRAM ALERTS...")
            print(f"{'='*80}\n")
            
            for signal in signals_found:
                detection = {
                    'date': signal['pattern']['date'],
                    'price': signal['pattern']['price'],
                    'volume': signal['pattern']['volume'],
                    'pattern': signal['pattern']['pattern'],
                    'bias': signal['pattern']['bias'],
                    'trend_analysis': signal['trend_analysis'],
                    'confluence': signal['confluence']
                }
                
                success = self.telegram.send_enhanced_alert(signal['symbol'], detection)
                
                if success:
                    print(f"   ✅ Alert sent: {signal['symbol']} - {signal['pattern']['pattern']}")
                else:
                    print(f"   ⚠️  Alert failed: {signal['symbol']}")
        else:
            print(f"\n📊 No qualifying signals found in this scan.\n")
        
        print(f"\n✅ Scan complete at {datetime.now().strftime('%H:%M:%S')}\n")
    
    def run_continuous(self, interval_minutes: int = 60):
        """
        Run scanner continuously during market hours
        Scans at candle close + 1 min buffer
        """
        print(f"\n{'='*80}")
        print(f"🚀 STARTING CONTINUOUS REAL-TIME SCANNER")
        print(f"{'='*80}")
        print(f"Watchlist: {len(self.symbols)} stocks")
        print(f"Interval: {interval_minutes} minutes")
        print(f"Rate limit: 150 API calls/min")
        print(f"Telegram: {'Enabled' if self.telegram.is_configured() else 'Disabled'}")
        print(f"{'='*80}\n")
        
        while True:
            try:
                # Check if market is open
                if not MarketScheduler.is_market_open():
                    print(f"⏸️  Market closed. Next check in 10 minutes...")
                    time.sleep(600)  # Check every 10 minutes
                    continue
                
                # Wait for candle close
                MarketScheduler.wait_for_candle_close(interval_minutes)
                
                # Run scan
                self.scan_all_stocks()
                
            except KeyboardInterrupt:
                print("\n⛔ Scanner stopped by user\n")
                break
            except Exception as e:
                print(f"\n❌ Error in scanner loop: {e}")
                print(f"   Retrying in 5 minutes...\n")
                time.sleep(300)


def main():
    """Main execution"""
    
    # Configuration
    API_KEY = config.ALPHA_VANTAGE_API_KEY
    TELEGRAM_BOT = config.TELEGRAM_BOT_TOKEN
    TELEGRAM_CHAT = config.TELEGRAM_CHAT_ID
    WATCHLIST_FILE = config.WATCHLIST_FILE
    
    # Initialize scanner
    scanner = RealtimeScanner(API_KEY, TELEGRAM_BOT, TELEGRAM_CHAT)
    
    # Load watchlist
    symbols = scanner.load_watchlist(WATCHLIST_FILE)
    
    if not symbols:
        print("❌ No symbols loaded. Exiting.")
        return
    
    # Run scanner
    scanner.run_continuous(interval_minutes=60)


if __name__ == "__main__":
    import time
    main()