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
    # Add these 8 methods to your PatternDetector class in pattern_detector.py

    def detect_shooting_star(self, df: pd.DataFrame) -> List[Dict]:
        detections = []
        wick_ratio = self.config.get('SHOOTING_STAR_WICK_RATIO', 2.0)
    
        for i in range(len(df)):
            candle = df.iloc[i]
        
        # Calculate body and wicks
            body = abs(candle["Close"] - candle["Open"])
            upper_wick = candle["High"] - max(candle["Open"], candle["Close"])
            lower_wick = min(candle["Open"], candle["Close"]) - candle["Low"]
        
        # Skip if no body (doji)
            if body == 0 or body < 0.0001:
                continue
        
        # Shooting Star criteria
            is_shooting_star = (
                upper_wick > wick_ratio * body and     # Long upper wick
                lower_wick < 0.5 * body and            # Small/no lower wick
                upper_wick > 0.6 * (candle["High"] - candle["Low"])  # Upper wick dominates
            )
        
            if is_shooting_star:
                detections.append({
                    "date": candle["Date"],
                    "price": candle["Close"],
                    "volume": candle["Volume"],
                    "pattern": "SHOOTING_STAR",
                    "bias": "BEARISH",
                    "historical_completion_rate": 0.59
                })
    
        return detections


    def detect_morning_star(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect Morning Star pattern (3-candle bullish reversal)
        
        Historical completion rate: 65%
        
        Criteria:
        - Day 1: Long bearish candle
        - Day 2: Small body (doji/spinning top), gaps down
        - Day 3: Long bullish candle, closes above Day 1 midpoint
        """
        detections = []
        
        for i in range(2, len(df)):
            day1 = df.iloc[i-2]
            day2 = df.iloc[i-1]
            day3 = df.iloc[i]
            
            # Day 1: Long bearish
            day1_body = abs(day1["Close"] - day1["Open"])
            day1_bearish = day1["Close"] < day1["Open"]
            day1_range = day1["High"] - day1["Low"]
            day1_long = day1_body > 0.6 * day1_range if day1_range > 0 else False
            
            # Day 2: Small body (doji or spinning top)
            day2_body = abs(day2["Close"] - day2["Open"])
            day2_range = day2["High"] - day2["Low"]
            day2_small = day2_body < 0.3 * day1_body if day1_body > 0 else False
            
            # Day 2 gaps down (opens below Day 1 close)
            day2_gaps_down = day2["Open"] < day1["Close"]
            
            # Day 3: Long bullish
            day3_body = abs(day3["Close"] - day3["Open"])
            day3_bullish = day3["Close"] > day3["Open"]
            day3_range = day3["High"] - day3["Low"]
            day3_long = day3_body > 0.6 * day3_range if day3_range > 0 else False
            
            # Day 3 closes above Day 1 midpoint
            day1_midpoint = (day1["Open"] + day1["Close"]) / 2
            day3_closes_above_midpoint = day3["Close"] > day1_midpoint
            
            # Morning Star pattern
            is_morning_star = (
                day1_bearish and day1_long and
                day2_small and day2_gaps_down and
                day3_bullish and day3_long and
                day3_closes_above_midpoint
            )
            
            if is_morning_star:
                detections.append({
                    "date": day3["Date"],
                    "price": day3["Close"],
                    "volume": day3["Volume"],
                    "pattern": "MORNING_STAR",
                    "bias": "BULLISH",
                    "historical_completion_rate": 0.65
                })
        
        return detections


    def detect_evening_star(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect Evening Star pattern (3-candle bearish reversal)
        
        Historical completion rate: 69%
        
        Criteria:
        - Day 1: Long bullish candle
        - Day 2: Small body (doji/spinning top), gaps up
        - Day 3: Long bearish candle, closes below Day 1 midpoint
        """
        detections = []
        
        for i in range(2, len(df)):
            day1 = df.iloc[i-2]
            day2 = df.iloc[i-1]
            day3 = df.iloc[i]
            
            # Day 1: Long bullish
            day1_body = abs(day1["Close"] - day1["Open"])
            day1_bullish = day1["Close"] > day1["Open"]
            day1_range = day1["High"] - day1["Low"]
            day1_long = day1_body > 0.6 * day1_range if day1_range > 0 else False
            
            # Day 2: Small body (doji or spinning top)
            day2_body = abs(day2["Close"] - day2["Open"])
            day2_small = day2_body < 0.3 * day1_body if day1_body > 0 else False
            
            # Day 2 gaps up (opens above Day 1 close)
            day2_gaps_up = day2["Open"] > day1["Close"]
            
            # Day 3: Long bearish
            day3_body = abs(day3["Close"] - day3["Open"])
            day3_bearish = day3["Close"] < day3["Open"]
            day3_range = day3["High"] - day3["Low"]
            day3_long = day3_body > 0.6 * day3_range if day3_range > 0 else False
            
            # Day 3 closes below Day 1 midpoint
            day1_midpoint = (day1["Open"] + day1["Close"]) / 2
            day3_closes_below_midpoint = day3["Close"] < day1_midpoint
            
            # Evening Star pattern
            is_evening_star = (
                day1_bullish and day1_long and
                day2_small and day2_gaps_up and
                day3_bearish and day3_long and
                day3_closes_below_midpoint
            )
            
            if is_evening_star:
                detections.append({
                    "date": day3["Date"],
                    "price": day3["Close"],
                    "volume": day3["Volume"],
                    "pattern": "EVENING_STAR",
                    "bias": "BEARISH",
                    "historical_completion_rate": 0.69
                })
        
        return detections


    def detect_three_white_soldiers(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect Three White Soldiers pattern (3-candle strong bullish)
        
        Historical completion rate: 82% (HIGHEST)
        
        Criteria:
        - 3 consecutive bullish candles
        - Each closes higher than previous
        - Each opens within previous body
        - Bodies roughly equal size (±20%)
        - Minimal upper wicks (< 25% of body)
        """
        detections = []
        
        for i in range(2, len(df)):
            day1 = df.iloc[i-2]
            day2 = df.iloc[i-1]
            day3 = df.iloc[i]
            
            # All three bullish
            all_bullish = (
                day1["Close"] > day1["Open"] and
                day2["Close"] > day2["Open"] and
                day3["Close"] > day3["Open"]
            )
            
            if not all_bullish:
                continue
            
            # Each closes higher
            closes_higher = (
                day2["Close"] > day1["Close"] and
                day3["Close"] > day2["Close"]
            )
            
            # Each opens within previous body
            day2_opens_in_day1 = day1["Open"] < day2["Open"] < day1["Close"]
            day3_opens_in_day2 = day2["Open"] < day3["Open"] < day2["Close"]
            opens_within = day2_opens_in_day1 and day3_opens_in_day2
            
            # Bodies roughly equal (±20%)
            body1 = day1["Close"] - day1["Open"]
            body2 = day2["Close"] - day2["Open"]
            body3 = day3["Close"] - day3["Open"]
            
            avg_body = (body1 + body2 + body3) / 3
            bodies_equal = (
                abs(body1 - avg_body) < 0.2 * avg_body and
                abs(body2 - avg_body) < 0.2 * avg_body and
                abs(body3 - avg_body) < 0.2 * avg_body
            )
            
            # Minimal upper wicks
            wick1 = day1["High"] - day1["Close"]
            wick2 = day2["High"] - day2["Close"]
            wick3 = day3["High"] - day3["Close"]
            
            minimal_wicks = (
                wick1 < 0.25 * body1 and
                wick2 < 0.25 * body2 and
                wick3 < 0.25 * body3
            )
            
            # Three White Soldiers pattern
            is_three_soldiers = (
                all_bullish and
                closes_higher and
                opens_within and
                bodies_equal and
                minimal_wicks
            )
            
            if is_three_soldiers:
                detections.append({
                    "date": day3["Date"],
                    "price": day3["Close"],
                    "volume": day3["Volume"],
                    "pattern": "THREE_WHITE_SOLDIERS",
                    "bias": "BULLISH",
                    "historical_completion_rate": 0.82
                })
        
        return detections


    def detect_three_black_crows(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect Three Black Crows pattern (3-candle strong bearish)
        
        Historical completion rate: 78% (VERY STRONG)
        
        Criteria:
        - 3 consecutive bearish candles
        - Each closes lower than previous
        - Each opens within previous body
        - Bodies roughly equal size (±20%)
        - Minimal lower wicks (< 25% of body)
        """
        detections = []
        
        for i in range(2, len(df)):
            day1 = df.iloc[i-2]
            day2 = df.iloc[i-1]
            day3 = df.iloc[i]
            
            # All three bearish
            all_bearish = (
                day1["Close"] < day1["Open"] and
                day2["Close"] < day2["Open"] and
                day3["Close"] < day3["Open"]
            )
            
            if not all_bearish:
                continue
            
            # Each closes lower
            closes_lower = (
                day2["Close"] < day1["Close"] and
                day3["Close"] < day2["Close"]
            )
            
            # Each opens within previous body
            day2_opens_in_day1 = day1["Close"] < day2["Open"] < day1["Open"]
            day3_opens_in_day2 = day2["Close"] < day3["Open"] < day2["Open"]
            opens_within = day2_opens_in_day1 and day3_opens_in_day2
            
            # Bodies roughly equal (±20%)
            body1 = day1["Open"] - day1["Close"]
            body2 = day2["Open"] - day2["Close"]
            body3 = day3["Open"] - day3["Close"]
            
            avg_body = (body1 + body2 + body3) / 3
            bodies_equal = (
                abs(body1 - avg_body) < 0.2 * avg_body and
                abs(body2 - avg_body) < 0.2 * avg_body and
                abs(body3 - avg_body) < 0.2 * avg_body
            )
            
            # Minimal lower wicks
            wick1 = day1["Close"] - day1["Low"]
            wick2 = day2["Close"] - day2["Low"]
            wick3 = day3["Close"] - day3["Low"]
            
            minimal_wicks = (
                wick1 < 0.25 * body1 and
                wick2 < 0.25 * body2 and
                wick3 < 0.25 * body3
            )
            
            # Three Black Crows pattern
            is_three_crows = (
                all_bearish and
                closes_lower and
                opens_within and
                bodies_equal and
                minimal_wicks
            )
            
            if is_three_crows:
                detections.append({
                    "date": day3["Date"],
                    "price": day3["Close"],
                    "volume": day3["Volume"],
                    "pattern": "THREE_BLACK_CROWS",
                    "bias": "BEARISH",
                    "historical_completion_rate": 0.78
                })
        
        return detections


    def detect_bullish_abandoned_baby(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect Bullish Abandoned Baby pattern (3-candle rare bullish reversal)
        
        Historical completion rate: 66% (RARE but powerful)
        
        Criteria:
        - Day 1: Long bearish candle
        - Day 2: Doji gaps down (island formation, no overlap with Day 1)
        - Day 3: Long bullish candle gaps up (no overlap with Day 2)
        - Day 2 is "abandoned" between gaps
        """
        detections = []
        
        for i in range(2, len(df)):
            day1 = df.iloc[i-2]
            day2 = df.iloc[i-1]
            day3 = df.iloc[i]
            
            # Day 1: Long bearish
            day1_body = abs(day1["Close"] - day1["Open"])
            day1_bearish = day1["Close"] < day1["Open"]
            day1_range = day1["High"] - day1["Low"]
            day1_long = day1_body > 0.6 * day1_range if day1_range > 0 else False
            
            # Day 2: Doji (very small body)
            day2_body = abs(day2["Close"] - day2["Open"])
            day2_range = day2["High"] - day2["Low"]
            day2_doji = day2_body < 0.1 * day2_range if day2_range > 0 else False
            
            # Day 2 gaps down - NO OVERLAP with Day 1
            day2_gaps_down = day2["High"] < day1["Low"]
            
            # Day 3: Long bullish
            day3_body = abs(day3["Close"] - day3["Open"])
            day3_bullish = day3["Close"] > day3["Open"]
            day3_range = day3["High"] - day3["Low"]
            day3_long = day3_body > 0.6 * day3_range if day3_range > 0 else False
            
            # Day 3 gaps up - NO OVERLAP with Day 2
            day3_gaps_up = day3["Low"] > day2["High"]
            
            # Bullish Abandoned Baby pattern
            is_abandoned_baby = (
                day1_bearish and day1_long and
                day2_doji and day2_gaps_down and
                day3_bullish and day3_long and day3_gaps_up
            )
            
            if is_abandoned_baby:
                detections.append({
                    "date": day3["Date"],
                    "price": day3["Close"],
                    "volume": day3["Volume"],
                    "pattern": "BULLISH_ABANDONED_BABY",
                    "bias": "BULLISH",
                    "historical_completion_rate": 0.66,
                    "note": "RARE_STRONG_SIGNAL"
                })
        
        return detections


    def detect_bearish_abandoned_baby(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect Bearish Abandoned Baby pattern (3-candle rare bearish reversal)
        
        Historical completion rate: 78% (RARE but VERY STRONG)
        
        Criteria:
        - Day 1: Long bullish candle
        - Day 2: Doji gaps up (island formation, no overlap with Day 1)
        - Day 3: Long bearish candle gaps down (no overlap with Day 2)
        - Day 2 is "abandoned" between gaps
        """
        detections = []
        
        for i in range(2, len(df)):
            day1 = df.iloc[i-2]
            day2 = df.iloc[i-1]
            day3 = df.iloc[i]
            
            # Day 1: Long bullish
            day1_body = abs(day1["Close"] - day1["Open"])
            day1_bullish = day1["Close"] > day1["Open"]
            day1_range = day1["High"] - day1["Low"]
            day1_long = day1_body > 0.6 * day1_range if day1_range > 0 else False
            
            # Day 2: Doji (very small body)
            day2_body = abs(day2["Close"] - day2["Open"])
            day2_range = day2["High"] - day2["Low"]
            day2_doji = day2_body < 0.1 * day2_range if day2_range > 0 else False
            
            # Day 2 gaps up - NO OVERLAP with Day 1
            day2_gaps_up = day2["Low"] > day1["High"]
            
            # Day 3: Long bearish
            day3_body = abs(day3["Close"] - day3["Open"])
            day3_bearish = day3["Close"] < day3["Open"]
            day3_range = day3["High"] - day3["Low"]
            day3_long = day3_body > 0.6 * day3_range if day3_range > 0 else False
            
            # Day 3 gaps down - NO OVERLAP with Day 2
            day3_gaps_down = day3["High"] < day2["Low"]
            
            # Bearish Abandoned Baby pattern
            is_abandoned_baby = (
                day1_bullish and day1_long and
                day2_doji and day2_gaps_up and
                day3_bearish and day3_long and day3_gaps_down
            )
            
            if is_abandoned_baby:
                detections.append({
                    "date": day3["Date"],
                    "price": day3["Close"],
                    "volume": day3["Volume"],
                    "pattern": "BEARISH_ABANDONED_BABY",
                    "bias": "BEARISH",
                    "historical_completion_rate": 0.78,
                    "note": "RARE_STRONG_SIGNAL"
                })
        
        return detections


    def detect_bearish_breakdown(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect Bearish Breakdown pattern (momentum bearish)
        
        Criteria:
        - Close below 20-day support level
        - Volume > 1.5× average (20-day)
        - Bearish candle
        """
        detections = []
        lookback = self.config.get('BREAKDOWN_LOOKBACK', 20)
        vol_mult = self.config.get('VOLUME_SURGE_MULTIPLIER', 1.5)
        
        for i in range(lookback, len(df)):
            recent = df.iloc[i-lookback:i]
            current = df.iloc[i]
            
            # Calculate 20-day support (lowest low)
            support = recent["Low"].min()
            
            # Calculate average volume
            avg_volume = recent["Volume"].mean()
            
            # Bearish Breakdown criteria
            is_breakdown = (
                current["Close"] < support and                    # Break below support
                current["Volume"] > avg_volume * vol_mult and     # Volume surge
                current["Close"] < current["Open"]                # Bearish candle
            )
            
            if is_breakdown:
                detections.append({
                    "date": current["Date"],
                    "price": current["Close"],
                    "volume": current["Volume"],
                    "pattern": "BEARISH_BREAKDOWN",
                    "bias": "BEARISH",
                    "support_level": support,
                    "volume_ratio": current["Volume"] / avg_volume
                })
        
        return detections

# Usage: from modules.pattern_detector import PatternDetector