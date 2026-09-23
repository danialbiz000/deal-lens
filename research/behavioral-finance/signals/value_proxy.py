"""A simple, data-light value/growth proxy, used only for the diagnostic in
investigations/52w_high_value_confound.py -- NOT part of the main signal
library in composite.py, and not claimed to be a rigorous value factor (a real
one needs fundamentals data: book value, earnings, etc., which these price-only
mirrors don't provide).
"""
from __future__ import annotations

import pandas as pd


def price_to_long_run_average(prices: pd.DataFrame, window: int = 750) -> pd.DataFrame:
    """Current price divided by its own trailing ~3-year (750 trading day)
    average. A ratio well below 1 means a stock is trading cheap relative to
    its own recent history (a "value" signature); well above 1 means it's
    trading rich (a "growth"/momentum signature). This is a weak, purely
    time-series proxy for value -- it has no information about earnings,
    book value, or any fundamental -- used here only to test whether the
    52-week-high signal's cross-sectional bets are confounded with this kind
    of cheap/rich distinction, not as a signal in its own right.
    """
    rolling_avg = prices.rolling(window, min_periods=window // 2).mean()
    return prices / rolling_avg
