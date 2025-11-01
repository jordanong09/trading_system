"""
Market Sentiment Layer (v5.0)

Provides market context for trading decisions:
    - Volatility Index: Internal SPY/QQQ ATR-based calculation
    - SPY/QQQ Analyzer: Market regime detection
    - Sentiment Engine: Combined sentiment with weighted multiplier

Usage:
    from stock_analyzer.market import get_composite_sentiment
    sentiment = get_composite_sentiment(data_fetcher)
"""

from stock_analyzer.market.volatility_index import VolatilityIndex
from stock_analyzer.market.spy_qqq_analyzer import SPYQQQAnalyzer
from stock_analyzer.market.sentiment_engine import SentimentEngine, get_composite_sentiment

__all__ = [
    'VolatilityIndex',
    'SPYQQQAnalyzer',
    'SentimentEngine',
    'get_composite_sentiment',
]