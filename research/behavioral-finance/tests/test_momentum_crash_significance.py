from __future__ import annotations

import numpy as np
import pandas as pd

from investigations.momentum_crash_significance import monthly_returns_at_rebalances


def test_monthly_returns_at_rebalances_compounds_correctly():
    dates = pd.bdate_range("2020-01-01", periods=40)
    daily = pd.Series(0.0, index=dates)
    # two known holding periods with hand-checkable compounding
    daily.iloc[1:11] = 0.01   # +1% for 10 days -> (1.01**10 - 1)
    daily.iloc[11:21] = -0.005  # -0.5% for 10 days -> (0.995**10 - 1)

    reb_dates = pd.DatetimeIndex([dates[0], dates[10], dates[20], dates[30]])
    monthly = monthly_returns_at_rebalances(daily, reb_dates)

    assert len(monthly) == 3
    assert np.isclose(monthly.iloc[0], 1.01 ** 10 - 1, atol=1e-9)
    assert np.isclose(monthly.iloc[1], 0.995 ** 10 - 1, atol=1e-9)
    assert np.isclose(monthly.iloc[2], 0.0)  # flat period, no return
