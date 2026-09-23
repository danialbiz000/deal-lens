from __future__ import annotations

import numpy as np
import pandas as pd

from investigations.short_leg_beta import market_proxy


def test_market_proxy_is_the_cross_sectional_mean_return():
    dates = pd.bdate_range("2020-01-01", periods=5)
    prices = pd.DataFrame(
        {"A": [100, 101, 102, 101, 103], "B": [50, 49, 50, 51, 52]},
        index=dates,
        dtype=float,
    )
    proxy = market_proxy(prices)

    expected_day2 = np.mean([101 / 100 - 1, 49 / 50 - 1])
    assert np.isclose(proxy.iloc[1], expected_day2)
