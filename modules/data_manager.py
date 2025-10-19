# modules/data_manager.py - Historical Data & Support/Resistance Manager

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import pickle
import os
import json

class DataManager:
    """
    Manages historical data cache for 200 stocks
    - Maintains 30+ days of 1-hour candles
    - Calculates support/resistance zones
    - Detects breakout opportunities
    """
    
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = cache_dir
        self.min_candles = 30  # Minimum 30 candles
        os.makedirs(cache_dir, exist_ok=True)
        
    def get_cache_file(self, symbol: str) -> str:
        """Get cache file path for symbol"""
        return os.path.join(self.cache_dir, f"{symbol}_data.pkl")
    
    def load_cached_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Load cached historical data for symbol"""
        cache_file = self.get_cache_file(symbol)
        
        if not os.path.exists(cache_file):
            return None
        
        try:
            # Check if cache is fresh (< 24 hours old)
            cache_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_file))
            if cache_age > timedelta(hours=24):
                print(f"   ⚠️  Cache expired for {symbol}, will refresh")
                return None
            
            with open(cache_file, 'rb') as f:
                df = pickle.load(f)
            
            return df
            
        except Exception as e:
            print(f"   ⚠️  Error loading cache for {symbol}: {e}")
            return None
    
    def save_cached_data(self, symbol: str, df: pd.DataFrame):
        """Save historical data to cache"""
        cache_file = self.get_cache_file(symbol)
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(df, f)
        except Exception as e:
            print(f"   ⚠️  Error saving cache for {symbol}: {e}")
    
    def merge_new_data(self, symbol: str, new_df: pd.DataFrame, 
                       cached_df: Optional[pd.DataFrame]) -> pd.DataFrame:
        """
        Merge new data with cached data
        Keep only most recent 60 candles (enough for 30-day lookback)
        """
        if cached_df is None or cached_df.empty:
            return new_df.tail(60)
        
        # Combine and remove duplicates
        combined = pd.concat([cached_df, new_df])
        combined = combined.drop_duplicates(subset=['Date'], keep='last')
        combined = combined.sort_values('Date').reset_index(drop=True)
        
        # Keep only last 60 candles (more than enough for analysis)
        return combined.tail(60)
    
    def identify_support_resistance(self, df: pd.DataFrame, 
                                    lookback: int = 30) -> Dict:
        """
        Identify horizontal support and resistance levels
        
        Method:
        1. Find significant highs and lows
        2. Cluster nearby levels (within 0.5%)
        3. Rank by number of touches
        4. Return top 3 support and resistance levels
        """
        if len(df) < lookback:
            lookback = len(df)
        
        recent = df.tail(lookback)
        
        # Find swing highs and lows
        highs = []
        lows = []
        
        for i in range(1, len(recent) - 1):
            # Swing high: higher than both neighbors
            if (recent.iloc[i]['High'] > recent.iloc[i-1]['High'] and 
                recent.iloc[i]['High'] > recent.iloc[i+1]['High']):
                highs.append(recent.iloc[i]['High'])
            
            # Swing low: lower than both neighbors
            if (recent.iloc[i]['Low'] < recent.iloc[i-1]['Low'] and 
                recent.iloc[i]['Low'] < recent.iloc[i+1]['Low']):
                lows.append(recent.iloc[i]['Low'])
        
        # Cluster levels within 0.5% of each other
        resistance_zones = self._cluster_levels(highs, threshold=0.005)
        support_zones = self._cluster_levels(lows, threshold=0.005)
        
        # Get current price
        current_price = df.iloc[-1]['Close']
        
        # Filter and rank zones
        resistance_levels = []
        for level, touches in resistance_zones:
            if level > current_price:  # Only levels above current price
                distance_pct = ((level - current_price) / current_price) * 100
                resistance_levels.append({
                    'price': level,
                    'touches': touches,
                    'distance_pct': distance_pct,
                    'type': 'RESISTANCE'
                })
        
        support_levels = []
        for level, touches in support_zones:
            if level < current_price:  # Only levels below current price
                distance_pct = ((current_price - level) / current_price) * 100
                support_levels.append({
                    'price': level,
                    'touches': touches,
                    'distance_pct': distance_pct,
                    'type': 'SUPPORT'
                })
        
        # Sort by touches (more touches = stronger level)
        resistance_levels = sorted(resistance_levels, key=lambda x: (-x['touches'], x['distance_pct']))
        support_levels = sorted(support_levels, key=lambda x: (-x['touches'], x['distance_pct']))
        
        return {
            'resistance': resistance_levels[:3],  # Top 3 resistance
            'support': support_levels[:3],        # Top 3 support
            'current_price': current_price
        }
    
    def _cluster_levels(self, levels: List[float], threshold: float = 0.005) -> List[Tuple[float, int]]:
        """
        Cluster nearby price levels
        threshold: 0.005 = 0.5%
        
        Returns: List of (average_level, touch_count)
        """
        if not levels:
            return []
        
        levels = sorted(levels)
        clusters = []
        current_cluster = [levels[0]]
        
        for level in levels[1:]:
            # If within threshold of cluster average, add to cluster
            cluster_avg = sum(current_cluster) / len(current_cluster)
            if abs(level - cluster_avg) / cluster_avg <= threshold:
                current_cluster.append(level)
            else:
                # Save current cluster and start new one
                clusters.append((
                    sum(current_cluster) / len(current_cluster),
                    len(current_cluster)
                ))
                current_cluster = [level]
        
        # Don't forget last cluster
        if current_cluster:
            clusters.append((
                sum(current_cluster) / len(current_cluster),
                len(current_cluster)
            ))
        
        return clusters
    
    def detect_breakout_potential(self, df: pd.DataFrame, 
                                  support_resistance: Dict) -> Dict:
        """
        Detect if price is near a breakout level
        
        Criteria:
        - Price within 1% of resistance/support
        - Volume increasing
        - Strong directional move
        """
        if len(df) < 5:
            return {'breakout_imminent': False}
        
        current = df.iloc[-1]
        current_price = current['Close']
        
        # Check volume trend (last 5 candles)
        recent_volume = df.tail(5)['Volume'].mean()
        avg_volume = df.tail(20)['Volume'].mean() if len(df) >= 20 else recent_volume
        volume_increasing = recent_volume > avg_volume * 1.2
        
        # Check nearest resistance
        resistance_levels = support_resistance.get('resistance', [])
        support_levels = support_resistance.get('support', [])
        
        breakout_analysis = {
            'breakout_imminent': False,
            'direction': None,
            'target_level': None,
            'distance_pct': None,
            'volume_surge': volume_increasing
        }
        
        # Check for bullish breakout (near resistance)
        if resistance_levels:
            nearest_resistance = resistance_levels[0]
            distance_pct = nearest_resistance['distance_pct']
            
            if distance_pct <= 1.0:  # Within 1% of resistance
                # Check if price is pushing up
                last_3_closes = df.tail(3)['Close'].tolist()
                is_pushing_up = all(last_3_closes[i] <= last_3_closes[i+1] for i in range(len(last_3_closes)-1))
                
                if is_pushing_up and volume_increasing:
                    breakout_analysis.update({
                        'breakout_imminent': True,
                        'direction': 'BULLISH',
                        'target_level': nearest_resistance['price'],
                        'distance_pct': distance_pct,
                        'touches': nearest_resistance['touches']
                    })
        
        # Check for bearish breakdown (near support)
        if support_levels and not breakout_analysis['breakout_imminent']:
            nearest_support = support_levels[0]
            distance_pct = nearest_support['distance_pct']
            
            if distance_pct <= 1.0:  # Within 1% of support
                # Check if price is pushing down
                last_3_closes = df.tail(3)['Close'].tolist()
                is_pushing_down = all(last_3_closes[i] >= last_3_closes[i+1] for i in range(len(last_3_closes)-1))
                
                if is_pushing_down and volume_increasing:
                    breakout_analysis.update({
                        'breakout_imminent': True,
                        'direction': 'BEARISH',
                        'target_level': nearest_support['price'],
                        'distance_pct': distance_pct,
                        'touches': nearest_support['touches']
                    })
        
        return breakout_analysis
    
    def get_enhanced_stock_data(self, symbol: str, new_data: pd.DataFrame) -> Dict:
        """
        Get complete enhanced data for a stock
        
        Returns:
        - Historical data (30+ candles)
        - Support/resistance levels
        - Breakout analysis
        """
        # Load cached data
        cached_df = self.load_cached_data(symbol)
        
        # Merge with new data
        complete_df = self.merge_new_data(symbol, new_data, cached_df)
        
        # Save updated cache
        self.save_cached_data(symbol, complete_df)
        
        # Identify support/resistance
        sr_levels = self.identify_support_resistance(complete_df, lookback=30)
        
        # Detect breakout potential
        breakout = self.detect_breakout_potential(complete_df, sr_levels)
        
        return {
            'symbol': symbol,
            'historical_data': complete_df,
            'candle_count': len(complete_df),
            'support_resistance': sr_levels,
            'breakout_analysis': breakout,
            'latest_candle': complete_df.iloc[-1]
        }


# Usage: from modules.data_manager import DataManager