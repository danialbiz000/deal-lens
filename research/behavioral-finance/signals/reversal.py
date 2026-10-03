"""Short-term reversal signal."""
from __future__ import annotations

import pandas as pd


def short_term_reversal(prices: pd.DataFrame, lookback: int = 21) -> pd.DataFrame:
    """Jegadeesh (1990) / Lehmann (1990) short-term reversal: trailing ~1-month
    return, NEGATED so that a high signal value means "recent loser." Behavioral
    mechanism: very short-horizon overreaction (panic selling / euphoric buying,
    or liquidity-driven price pressure) partially mean-reverts over the
    following month as the overreaction unwinds. Unlike 12-1 momentum, this is
    the opposite bet: bet against the most recent move, not with it.
    """
    raw_return = prices / prices.shift(lookback) - 1.0
    return -raw_return
