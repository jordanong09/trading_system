# modules/pattern_detector.py

import pandas as pd
import numpy as np
from typing import List, Dict
from datetime import datetime

class PatternDetector:
    """Detect all technical patterns"""
    
    def __init__(self, config: dict):
        self.config = config
    
    def detect_bullish_engulfing(self, df: pd.DataFrame) -> List[Dict]:
        """Detect bullish engulfing patterns"""
        detections = []
        
        for i in range(1, len(df)):
            prev = df.iloc[i-1]
            curr = df.iloc[i]
            
            is_bullish = (
                prev["Close"] < prev["Open"] and
                curr["Close"] > curr["Open"] and
                curr["Open"] < prev["Close"] and
                curr["Close"] > prev["Open"]
            )
            
            if is_bullish:
                detections.append({
                    "date": curr["Date"],
                    "price": curr["Close"],
                    "volume": curr["Volume"],
                    "pattern": "BULLISH_ENGULFING",
                    "bias": "BULLISH"
                })
        
        return detections
    
    def detect_bearish_engulfing(self, df: pd.DataFrame) -> List[Dict]:
        """Detect bearish engulfing patterns"""
        detections = []
        
        for i in range(1, len(df)):
            prev = df.iloc[i-1]
            curr = df.iloc[i]
            
            is_bearish = (
                prev["Close"] > prev["Open"] and
                curr["Close"] < curr["Open"] and
                curr["Open"] > prev["Close"] and
                curr["Close"] < prev["Open"]
            )
            
            if is_bearish:
                detections.append({
                    "date": curr["Date"],
                    "price": curr["Close"],
                    "volume": curr["Volume"],
                    "pattern": "BEARISH_ENGULFING",
                    "bias": "BEARISH"
                })
        
        return detections
    
    def detect_hammer(self, df: pd.DataFrame) -> List[Dict]:
        """Detect hammer patterns"""
        detections = []
        wick_ratio = self.config.get('HAMMER_WICK_RATIO', 2.0)
        
        for i in range(len(df)):
            candle = df.iloc[i]
            body = abs(candle["Close"] - candle["Open"])
            lower_wick = min(candle["Open"], candle["Close"]) - candle["Low"]
            upper_wick = candle["High"] - max(candle["Open"], candle["Close"])
            
            if body == 0:  # Skip if no body
                continue
            
            is_hammer = (
                lower_wick > wick_ratio * body and
                upper_wick < body and
                candle["Close"] > candle["Open"]
            )
            
            if is_hammer:
                detections.append({
                    "date": candle["Date"],
                    "price": candle["Close"],
                    "volume": candle["Volume"],
                    "pattern": "HAMMER",
                    "bias": "BULLISH"
                })
        
        return detections
    
    def detect_breakout(self, df: pd.DataFrame) -> List[Dict]:
        """Detect breakouts"""
        detections = []
        lookback = self.config.get('BREAKOUT_LOOKBACK', 20)
        vol_mult = self.config.get('VOLUME_SURGE_MULTIPLIER', 1.5)
        
        for i in range(lookback, len(df)):
            recent = df.iloc[i-lookback:i]
            current = df.iloc[i]
            
            resistance = recent["High"].max()
            support = recent["Low"].min()
            avg_volume = recent["Volume"].mean()
            
            if current["Close"] > resistance and current["Volume"] > avg_volume * vol_mult:
                detections.append({
                    "date": current["Date"],
                    "price": current["Close"],
                    "volume": current["Volume"],
                    "pattern": "BULLISH_BREAKOUT",
                    "bias": "BULLISH"
                })
            
            elif current["Close"] < support and current["Volume"] > avg_volume * vol_mult:
                detections.append({
                    "date": current["Date"],
                    "price": current["Close"],
                    "volume": current["Volume"],
                    "pattern": "BEARISH_BREAKDOWN",
                    "bias": "BEARISH"
                })
        
        return detections
    
    def analyze_confluence(self, df: pd.DataFrame, index: int = -1) -> Dict:
        """Calculate confluence filters"""
        if len(df) < 20:
            return {}
        
        recent = df.iloc[max(0, index-19):index+1]
        current = df.iloc[index]
        
        current_price = current["Close"]
        avg_price_20 = recent["Close"].mean()
        current_volume = current["Volume"]
        avg_volume_20 = recent["Volume"].mean()
        volatility = recent["Close"].std() / avg_price_20 * 100 if avg_price_20 > 0 else 0
        
        return {
            "current_price": current_price,
            "above_20ma": current_price > avg_price_20,
            "volume_surge": current_volume > avg_volume_20 * 1.5,
            "avg_volume_20": avg_volume_20,
            "current_volume": current_volume,
            "volatility_pct": volatility,
            "ma_20": avg_price_20
        }

# Usage: from modules.pattern_detector import PatternDetector