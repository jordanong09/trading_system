# main.py - RUN THIS FILE

import sys
import os

# Add modules to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.data_loader import DataLoader
from modules.pattern_detector import PatternDetector
from modules.telegram_handler import TelegramHandler
from modules.utils import ResultExporter, ReportGenerator
import config_secure as config

def main():
    """Main execution"""
    
    print("\n🚀 Starting Backtest Analysis...\n")
    
    # 1. Load data
    loader = DataLoader()
    df = loader.load_data_from_excel(config.EXCEL_FILE, config.SHEET_NAME)
    
    if df.empty:
        print("❌ Failed to load data")
        return
    
    # 2. Initialize detector
    detector = PatternDetector(vars(config))
    
    # 3. Detect patterns
    all_detections = []
    patterns = [
        detector.detect_bullish_engulfing(df),
        detector.detect_bearish_engulfing(df),
        detector.detect_hammer(df),
        detector.detect_breakout(df)
    ]
    
    for pattern_list in patterns:
        all_detections.extend(pattern_list)
    
    all_detections = sorted(all_detections, key=lambda x: x['date'])
    
    # 4. Generate report
    from datetime import datetime
    today = pd.Timestamp(datetime.now().date())
    today_detections = [d for d in all_detections if d['date'].date() == today]
    
    ReportGenerator.print_summary(all_detections, today_detections, config.SYMBOL)
    
    # 5. Send Telegram alerts (if configured)
    telegram = TelegramHandler(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
    
    if today_detections and telegram.is_configured():
        print(f"\n📤 Sending {len(today_detections)} Telegram alert(s)...\n")
        for detection in today_detections:
            row_idx = df[df['Date'] == detection['date']].index[0]
            confluence = detector.analyze_confluence(df, row_idx)
            telegram.send_alert(config.SYMBOL, detection, confluence)
    
    # 6. Export results
    ResultExporter.export_to_excel(all_detections, config.OUTPUT_FILE)
    
    print("\n✅ Analysis complete!\n")

if __name__ == "__main__":
    import pandas as pd
    main()