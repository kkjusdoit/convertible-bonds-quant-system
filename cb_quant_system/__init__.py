"""
可转债量化选债系统
Convertible Bond Quantitative Selection System

A Python-based quantitative selection system for Chinese convertible bonds.
"""

__version__ = "1.0.0"
__author__ = "Quantitative Developer"

from .data_fetcher import get_cb_data, fetch_cb_basic_data
from .calculator import (
    calculate_all_indicators,
    calculate_composite_score,
    calculate_convert_value,
    calculate_premium_rate,
    calculate_double_low
)
from .strategy import (
    filter_by_basic_criteria,
    filter_by_risk,
    strategy_low_premium,
    strategy_double_low,
    strategy_high_ytm,
    strategy_composite_score,
    strategy_value_hunting,
    run_all_strategies
)

__all__ = [
    'get_cb_data',
    'fetch_cb_basic_data',
    'calculate_all_indicators',
    'calculate_composite_score',
    'calculate_convert_value',
    'calculate_premium_rate',
    'calculate_double_low',
    'filter_by_basic_criteria',
    'filter_by_risk',
    'strategy_low_premium',
    'strategy_double_low',
    'strategy_high_ytm',
    'strategy_composite_score',
    'strategy_value_hunting',
    'run_all_strategies',
]
