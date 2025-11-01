"""S/R Engine Package"""

# Import all classes for easy access
from stock_analyzer.sr_engine.swing_detector import SwingDetector
from stock_analyzer.sr_engine.fibonacci_builder import FibonacciBuilder
from stock_analyzer.sr_engine.diagonal_detector import DiagonalDetector
from stock_analyzer.sr_engine.gap_detector import GapDetector
from stock_analyzer.sr_engine.zone_builder import ZoneBuilder
from stock_analyzer.sr_engine.confluence_merger import ConfluenceMerger

__all__ = [
    'SwingDetector',
    'FibonacciBuilder',
    'DiagonalDetector',
    'GapDetector',
    'ZoneBuilder',
    'ConfluenceMerger',
]