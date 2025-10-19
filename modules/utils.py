# modules/utils.py

import pandas as pd
from typing import List, Dict
import os

class ResultExporter:
    """Export analysis results"""
    
    @staticmethod
    def export_to_excel(detections: List[Dict], output_file: str) -> bool:
        """Export detections to Excel"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            df = pd.DataFrame(detections)
            df.to_excel(output_file, index=False, sheet_name="Detections")
            print(f"✅ Results exported to {output_file}")
            return True
        except Exception as e:
            print(f"❌ Export error: {e}")
            return False

class ReportGenerator:
    """Generate analysis reports"""
    
    @staticmethod
    def print_summary(all_detections: List[Dict], today_detections: List[Dict], symbol: str):
        """Print formatted analysis summary"""
        print(f"\n{'='*70}")
        print(f"🔍 BACKTEST ANALYSIS: {symbol}")
        print(f"{'='*70}\n")
        
        # Pattern summary
        pattern_counts = {}
        for d in all_detections:
            pattern = d['pattern']
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        
        for pattern, count in pattern_counts.items():
            print(f"✅ {pattern}: {count} detected")
        
        print(f"\n📊 Total patterns: {len(all_detections)}")
        
        # Detailed table
        print(f"\n{'Date':<12} {'Pattern':<20} {'Bias':<8} {'Price':<10} {'Volume':<12}")
        print("-" * 70)
        
        for d in sorted(all_detections, key=lambda x: x['date']):
            print(f"{d['date'].strftime('%Y-%m-%d'):<12} "
                  f"{d['pattern']:<20} "
                  f"{d['bias']:<8} "
                  f"${d['price']:<9.2f} "
                  f"{d['volume']:<12,.0f}")
        
        # Today's focus
        print(f"\n{'='*70}")
        print(f"🎯 TODAY'S PATTERNS")
        print(f"{'='*70}\n")
        
        if today_detections:
            print(f"✅ {len(today_detections)} pattern(s) detected today!\n")
            for d in today_detections:
                print(f"  • {d['pattern']} ({d['bias']}) @ ${d['price']:.2f}")
        else:
            print(f"❌ No patterns detected today\n")

# Usage: from modules.utils import ResultExporter, ReportGenerator