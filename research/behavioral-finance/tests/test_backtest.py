from __future__ import annotations

from backtest.engine import run_decile_backtest
from backtest.metrics import annualized_return, sharpe_ratio


def test_decile_backtest_recovers_known_signal(signal_predicts_return_prices):
    """On data constructed so the score PERFECTLY ranks forward returns
    (see conftest.py), the long-short decile backtest must produce a clearly
    positive gross return and Sharpe ratio -- this is the "does the engine
    actually do what it claims" sanity check, independent of whether any real
    market anomaly exists."""
    prices, scores = signal_predicts_return_prices
    result = run_decile_backtest(prices, scores, n_deciles=10, cost_bps=0.0)

    assert len(result.daily_returns_gross.dropna()) > 0
    assert annualized_return(result.daily_returns_gross) > 0
    assert sharpe_ratio(result.daily_returns_gross) > 1.0


def test_transaction_costs_reduce_net_vs_gross_return(signal_predicts_return_prices):
    prices, scores = signal_predicts_return_prices
    result = run_decile_backtest(prices, scores, n_deciles=10, cost_bps=50.0)

    gross_total = (1 + result.daily_returns_gross.fillna(0)).prod()
    net_total = (1 + result.daily_returns_net.fillna(0)).prod()
    assert net_total < gross_total
    # this fixture's score is constant through time, so decile membership
    # (and therefore turnover) is only nonzero at the very first rebalance --
    # that's still enough to prove costs are being deducted at all
    assert result.turnover_by_month.iloc[0] > 0
    assert (result.turnover_by_month >= 0).all()


def test_insufficient_universe_produces_no_trades(random_walk_prices):
    """min_names_per_side * n_deciles=10 needs 30 names for 3-per-side; the
    fixture only has 20 tickers, so the engine should skip every rebalance
    rather than error or silently trade an under-sized decile."""
    from signals.composite import composite_score

    scores = composite_score(random_walk_prices)
    result = run_decile_backtest(random_walk_prices, scores, n_deciles=10, min_names_per_side=3)

    assert result.turnover_by_month.empty
    assert (result.daily_returns_gross.fillna(0) == 0).all()
