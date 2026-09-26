"""Composite behavioral mispricing score: cross-sectional z-score blend of the
three individual signals, equal-weighted by default. See ../FRAMEWORK.md for
how this is meant to be used and its stated limitations.
"""
from __future__ import annotations

import pandas as pd

from .momentum import high_52w_proximity, momentum_12_1
from .reversal import short_term_reversal


def _cross_sectional_zscore(df: pd.DataFrame) -> pd.DataFrame:
    mean = df.mean(axis=1)
    std = df.std(axis=1)
    return df.sub(mean, axis=0).div(std, axis=0)


def composite_score(
    prices: pd.DataFrame,
    weights: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Equal-weighted (by default) composite of the three signals above, each
    cross-sectionally z-scored before combining so no single signal's scale
    dominates. Returns a DataFrame aligned with `prices` (date x ticker),
    NaN wherever any component signal isn't yet defined (e.g. within the
    first 252 trading days of history).
    """
    weights = weights or {"momentum": 1.0, "high_52w": 1.0, "reversal": 1.0}

    components = {
        "momentum": momentum_12_1(prices),
        "high_52w": high_52w_proximity(prices),
        "reversal": short_term_reversal(prices),
    }

    z_scored = {name: _cross_sectional_zscore(df) for name, df in components.items()}

    total_weight = sum(weights.values())
    score = sum(z_scored[name] * w for name, w in weights.items()) / total_weight
    return score
