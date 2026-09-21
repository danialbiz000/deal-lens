"""
Price-history loaders for the behavioral-finance signal study.

NOTE: this module needs outbound internet access to Yahoo Finance (primary) or
Stooq (fallback). It was written and unit-tested in a sandbox with no general
internet access, so it has never been exercised against a live provider from
this repo's CI/session — run it yourself somewhere with normal network access
before trusting anything downstream of it. See ../README.md, "Important
limitation of this environment."
"""
from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import requests

CACHE_DIR = Path(__file__).parent / "cache"

# A fixed, liquid large-cap universe used as the default sample. This is a
# convenience default, NOT a survivorship-bias-free universe -- see
# ../README.md "Explicit limitations" before using results from this list in
# any paper or pitch.
DEFAULT_UNIVERSE = [
    "AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "JPM", "JNJ", "PG", "XOM",
    "KO", "PEP", "WMT", "HD", "DIS", "BAC", "V", "MA", "UNH", "CVX",
    "PFE", "CSCO", "INTC", "VZ", "T", "MRK", "ABT", "CRM", "NKE", "MCD",
]


def _cache_path(ticker: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{ticker}.parquet"


def _fetch_yfinance(ticker: str, period: str) -> pd.DataFrame | None:
    try:
        import yfinance as yf

        df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
        if df is None or df.empty:
            return None
        df = df[["Close", "Volume"]].rename(columns={"Close": "close", "Volume": "volume"})
        return df
    except Exception:
        return None


def _fetch_stooq(ticker: str) -> pd.DataFrame | None:
    """Fallback source: Stooq's free CSV endpoint. Full history only (no `period`)."""
    url = f"https://stooq.com/q/d/l/?s={ticker.lower()}.us&i=d"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text), parse_dates=["Date"], index_col="Date")
        if df.empty or "Close" not in df.columns:
            return None
        df = df.rename(columns={"Close": "close", "Volume": "volume"})[["close", "volume"]]
        return df.sort_index()
    except Exception:
        return None


def load_single(ticker: str, period: str = "10y", use_cache: bool = True) -> pd.DataFrame:
    """Load one ticker's daily close/volume history, trying Yahoo then Stooq, with a
    local parquet cache so repeated runs don't re-hit the network."""
    cache_file = _cache_path(ticker)
    if use_cache and cache_file.exists():
        return pd.read_parquet(cache_file)

    df = _fetch_yfinance(ticker, period)
    if df is None:
        df = _fetch_stooq(ticker)
    if df is None:
        raise RuntimeError(
            f"Could not fetch price history for {ticker} from Yahoo Finance or Stooq. "
            "Check network access -- see README.md 'Important limitation of this environment'."
        )

    if use_cache:
        df.to_parquet(cache_file)
    return df


def load_price_history(
    tickers: list[str] | None = None,
    period: str = "10y",
    use_cache: bool = True,
) -> pd.DataFrame:
    """Load a wide DataFrame of adjusted close prices, columns = tickers, for the
    default (or given) universe. Tickers that fail to fetch are dropped with a
    warning rather than aborting the whole run."""
    tickers = tickers or DEFAULT_UNIVERSE
    closes = {}
    for t in tickers:
        try:
            closes[t] = load_single(t, period=period, use_cache=use_cache)["close"]
        except Exception as exc:  # noqa: BLE001 -- intentionally broad, this is I/O
            print(f"[loaders] skipping {t}: {exc}")
    if not closes:
        raise RuntimeError("No tickers could be loaded -- check network access.")
    return pd.DataFrame(closes).sort_index().dropna(how="all")


if __name__ == "__main__":
    prices = load_price_history(period="1y")
    print(prices.tail())
    print(f"Loaded {prices.shape[1]} tickers, {prices.shape[0]} trading days.")
