"""
Milestone 32 (line K): does momentum's one demonstrated edge carry hidden
sector concentration risk? Every "ticker concentration" check this project
has run (Milestones 26-27) asks whether a handful of individual NAMES
secretly drive a result. This asks the one level up: whether a handful of
SECTORS do -- a real risk-management question a momentum book's manager
would need answered before sizing it, distinct from whether the return
itself is statistically genuine.

Only the US mirror's fixed 30-ticker universe can be checked this way. GICS
sector assignments for all 30 names are well-established public knowledge
(no lookup needed) and are hardcoded below. ASX's momentum result cannot be
checked the same way: its universe is 209 tickers pulled from S&P/ASX300
constituent reports, and this project has no reliable sector-classification
source for them -- the sandbox's network allowlist (raw.githubusercontent.com
only, exact known paths) has no company-classification API reachable, and
hand-classifying 209 unfamiliar ASX codes from memory would risk silently
wrong labels, which this project's honesty standard treats as worse than
just not running the check. Flagged as an explicit limitation, not silently
skipped.

For the US mirror: at every rebalance, tally how many names in the long
(winner) and short (loser) legs come from each sector, compare to that
sector's share of the full 30-name universe, and check whether the pre-2008
long leg -- the specific window carrying the one demonstrated edge -- shows
persistent sector concentration relative to a proportional expectation.

Run: python investigations/momentum_sector_concentration.py
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import pandas as pd

from data.loaders import load_us_kaggle_mirror
from signals.momentum import momentum_12_1

N_DECILES = 5

# GICS-style sector assignment for the US mirror's fixed 30-ticker universe
# (data/loaders.py DEFAULT_UNIVERSE). Public, static company classifications
# -- not something this project needs a data source to look up.
SECTOR = {
    "AAPL": "Technology", "MSFT": "Technology", "NVDA": "Technology",
    "CSCO": "Technology", "INTC": "Technology", "CRM": "Technology",
    "GOOGL": "Communication Services", "META": "Communication Services",
    "DIS": "Communication Services", "VZ": "Communication Services", "T": "Communication Services",
    "JPM": "Financials", "BAC": "Financials", "V": "Financials", "MA": "Financials",
    "JNJ": "Health Care", "UNH": "Health Care", "PFE": "Health Care",
    "MRK": "Health Care", "ABT": "Health Care",
    "PG": "Consumer Staples", "KO": "Consumer Staples", "PEP": "Consumer Staples", "WMT": "Consumer Staples",
    "AMZN": "Consumer Discretionary", "HD": "Consumer Discretionary",
    "NKE": "Consumer Discretionary", "MCD": "Consumer Discretionary",
    "XOM": "Energy", "CVX": "Energy",
}
# load_us_kaggle_mirror() fetches using the lower-cased/fb-renamed tickers
# (US_MIRROR_UNIVERSE) but renames columns back to the original uppercase
# tickers before returning, so the DataFrame's own columns match SECTOR's
# keys directly.
SECTOR_BY_LOADER_TICKER = SECTOR

UNIVERSE_SECTOR_COUNTS = Counter(SECTOR.values())
PRE_2008_WINDOW = ("1970-01-01", "2008-08-31")


def month_end_dates(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(sorted(index.to_series().groupby([index.year, index.month]).max().values))


def leg_membership(scores: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    reb_dates = month_end_dates(prices.index)
    rows = []
    for d in reb_dates:
        if d not in scores.index:
            continue
        cross_section = scores.loc[d].dropna()
        if len(cross_section) == 0:
            continue
        ranked = cross_section.rank(pct=True)
        long_names = ranked[ranked >= 1.0 - 1.0 / N_DECILES].index.tolist()
        short_names = ranked[ranked <= 1.0 / N_DECILES].index.tolist()
        rows.append((d, long_names, short_names))
    return pd.DataFrame(rows, columns=["date", "long_names", "short_names"]).set_index("date")


def sector_tally(names_series: pd.Series) -> Counter:
    counts = Counter()
    for names in names_series:
        for n in names:
            sector = SECTOR_BY_LOADER_TICKER.get(n, "UNKNOWN")
            counts[sector] += 1
    return counts


def print_sector_breakdown(label: str, counts: Counter, n_total: int) -> None:
    print(f"\n  {label} (n={n_total} name-months):")
    universe_total = sum(UNIVERSE_SECTOR_COUNTS.values())
    for sector, n in counts.most_common():
        actual_share = n / n_total
        universe_share = UNIVERSE_SECTOR_COUNTS.get(sector, 0) / universe_total
        flag = " <-- overrepresented" if actual_share > universe_share * 1.5 else ""
        print(f"    {sector:24s}: {n:4d} ({actual_share:.1%} of leg-months, "
              f"vs {universe_share:.1%} of universe){flag}")


def main() -> None:
    prices = load_us_kaggle_mirror()
    signal = momentum_12_1(prices)
    membership = leg_membership(signal, prices)

    print("Full sample (1970-2017):")
    full_long = sector_tally(membership["long_names"])
    full_short = sector_tally(membership["short_names"])
    print_sector_breakdown("Long leg (winners)", full_long, sum(full_long.values()))
    print_sector_breakdown("Short leg (losers)", full_short, sum(full_short.values()))

    print(f"\n{'=' * 90}\nPre-2008-09 window only ({PRE_2008_WINDOW[0]} to {PRE_2008_WINDOW[1]}) "
          "-- the specific window carrying momentum's demonstrated edge\n" + "=" * 90)
    pre = membership.loc[PRE_2008_WINDOW[0]:PRE_2008_WINDOW[1]]
    pre_long = sector_tally(pre["long_names"])
    pre_short = sector_tally(pre["short_names"])
    print_sector_breakdown("Long leg (winners)", pre_long, sum(pre_long.values()))
    print_sector_breakdown("Short leg (losers)", pre_short, sum(pre_short.values()))

    print("\nUniverse sector composition (30 names):")
    universe_total = sum(UNIVERSE_SECTOR_COUNTS.values())
    for sector, n in UNIVERSE_SECTOR_COUNTS.most_common():
        print(f"    {sector:24s}: {n} names ({n / universe_total:.1%})")

    print("\nNOTE: ASX's momentum result (also independently confirmed, Milestone 22) cannot be")
    print("checked this way -- no reliable sector-classification source for its 209-ticker")
    print("universe is reachable from this sandbox. Explicit limitation, not silently skipped.")


if __name__ == "__main__":
    print("Does momentum's US long/short legs carry hidden sector concentration,")
    print("beyond what the universe's own sector composition would predict?")
    main()
