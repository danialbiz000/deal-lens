"""
Price-history loaders for the behavioral-finance signal study.

Two source families:

- `load_price_history` / `load_single`: Yahoo Finance (primary) with a Stooq
  fallback, for a US-large-cap default universe. These need general internet
  access, which the sandbox this project was originally built in did NOT
  have (Yahoo, Stooq, SEC EDGAR, and FRED were all blocked by the egress
  proxy) -- run these somewhere with normal network access.

- `load_nse_github_mirror` / `load_us_kaggle_mirror` / `load_asx_github_mirror`:
  real, working alternatives that WERE reachable from that same sandbox,
  because the proxy allowlists `raw.githubusercontent.com` specifically (not
  `github.com`'s own pages, `api.github.com` browsing, Kaggle, Hugging Face,
  or Stooq's static-file host -- all tried and blocked; see Milestone 22's
  writeup in ../README.md "Data provenance: the ASX GitHub mirror" for what
  that search process ruled out before landing on this third source). See
  ../README.md "Important limitation of this environment" for exactly which
  function's output is genuinely validated vs. still unexercised.
"""
from __future__ import annotations

import datetime as dt
import io
import re
import warnings
from concurrent.futures import ThreadPoolExecutor
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


# --- alternative source: a community-uploaded NSE (India) daily OHLCV mirror on
# GitHub, reachable even from network-restricted sandboxes that allowlist GitHub.
# See ../README.md "Data provenance: the NSE GitHub mirror" for what this is and
# is not a substitute for.

_NSE_MIRROR_URL = (
    "https://raw.githubusercontent.com/dheeraj5988/stock_market_dataset/"
    "main/combined_stock_data.csv"
)

# Built by inspecting each raw symbol's min/max trade date in the mirror: these
# pairs have zero date overlap and are contiguous to within a few days, which is
# the signature of an NSE ticker-symbol change (rebrand, corporate action) rather
# than two unrelated companies. Verified against known Indian market corporate
# history (e.g. TELCO -> Tata Motors' old ticker; SESAGOA -> Sesa Sterlite ->
# Vedanta Ltd's successive names). HDFC vs HDFCBANK is deliberately NOT merged:
# those were two separate listed companies for this entire sample (HDFC Ltd only
# merged into HDFC Bank in mid-2023, after this dataset ends).
_NSE_RENAME_CHAINS: list[list[str]] = [
    ["JSWSTL", "JSWSTEEL"],
    ["TISCO", "TATASTEEL"],
    ["TELCO", "TATAMOTORS"],
    ["INFOSYSTCH", "INFY"],
    ["UTIBANK", "AXISBANK"],
    ["HEROHONDA", "HEROMOTOCO"],
    ["HINDALC0", "HINDALCO"],
    ["ZEETELE", "ZEEL"],
    ["HINDLEVER", "HINDUNILVR"],
    ["KOTAKMAH", "KOTAKBANK"],
    ["BHARTI", "BHARTIARTL"],
    ["BAJAUTOFIN", "BAJFINANCE"],
    ["SESAGOA", "SSLT", "VEDL"],
    ["UNIPHOS", "UPL"],
]


def _nse_symbol_merge_map() -> dict[str, str]:
    """Map every raw symbol in a rename chain to the chain's final (most recent)
    name, so the merged series is keyed by the company's current ticker."""
    mapping = {}
    for chain in _NSE_RENAME_CHAINS:
        canonical = chain[-1]
        for symbol in chain:
            mapping[symbol] = canonical
    return mapping


def load_nse_github_mirror(use_cache: bool = True, min_history_days: int = 1000) -> pd.DataFrame:
    """Load the NSE (India) daily-close mirror from GitHub, merge known
    ticker-rename chains into single continuous series, and pivot to a wide
    date x company DataFrame. Drops any resulting series shorter than
    `min_history_days` (mostly renamed-away stub segments that didn't get
    merged, or genuinely short-lived listings) -- see ../README.md for why
    this is still not a survivorship-bias-free universe even after merging.
    """
    cache_file = CACHE_DIR / "nse_github_mirror.parquet"
    if use_cache and cache_file.exists():
        return pd.read_parquet(cache_file)

    resp = requests.get(_NSE_MIRROR_URL, timeout=60)
    resp.raise_for_status()
    raw = pd.read_csv(io.StringIO(resp.text), parse_dates=["Date"])

    merge_map = _nse_symbol_merge_map()
    raw["company"] = raw["Symbol"].map(lambda s: merge_map.get(s, s))

    # a company could in principle have two rows on the same date if a rename
    # chain's endpoints ever overlapped -- they don't here (verified), but
    # guard with a groupby-mean rather than silently picking one arbitrarily
    wide = raw.pivot_table(index="Date", columns="company", values="Close", aggfunc="mean")
    wide = wide.sort_index()

    long_enough = wide.count() >= min_history_days
    wide = wide.loc[:, long_enough]

    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        wide.to_parquet(cache_file)
    return wide


# --- second alternative source: a GitHub mirror of the well-known Kaggle "Huge
# Stock Market Dataset" (Boris Marjanovic), one CSV per US ticker, used here as
# an independent-market replication check for the NSE result above. See
# ../README.md "Data provenance: the US Kaggle mirror" for what this is and
# is not a substitute for.

_US_MIRROR_BASE = "https://raw.githubusercontent.com/scienclick/stocks/master/data/Stocks/"

# The same 30-ticker universe as DEFAULT_UNIVERSE above, so the two markets are
# as comparable as possible. This dataset's last snapshot is 2017-11-10, and it
# predates Facebook's 2021 rename to Meta, so "fb" stands in for "meta" here --
# documented, not silently substituted.
US_MIRROR_UNIVERSE = [t.lower() if t != "META" else "fb" for t in DEFAULT_UNIVERSE]


def _fetch_us_mirror_ticker(ticker: str) -> pd.Series | None:
    url = f"{_US_MIRROR_BASE}{ticker.lower()}.us.txt"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text), parse_dates=["Date"], index_col="Date")
        if df.empty or "Close" not in df.columns:
            return None
        return df["Close"].rename(ticker.upper() if ticker != "fb" else "META")
    except Exception:
        return None


def load_us_kaggle_mirror(
    tickers: list[str] | None = None, use_cache: bool = True
) -> pd.DataFrame:
    """Load the US Kaggle-mirror daily-close history for `tickers` (default:
    US_MIRROR_UNIVERSE) and pivot to a wide date x company DataFrame. Data
    runs from each company's IPO/listing date (or dataset start) through
    2017-11-10 -- this is a historical replication check, not a live feed.
    """
    cache_file = CACHE_DIR / "us_kaggle_mirror.parquet"
    if use_cache and cache_file.exists():
        return pd.read_parquet(cache_file)

    tickers = tickers or US_MIRROR_UNIVERSE
    closes = {}
    for t in tickers:
        series = _fetch_us_mirror_ticker(t)
        if series is None:
            print(f"[loaders] skipping {t}: not found in US Kaggle mirror")
            continue
        closes[series.name] = series
    if not closes:
        raise RuntimeError("No tickers could be loaded from the US Kaggle mirror.")

    wide = pd.DataFrame(closes).sort_index()
    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        wide.to_parquet(cache_file)
    return wide


# --- third alternative source: the Australian Securities Exchange (ASX), via a
# community-maintained GitHub mirror of ASX's own daily S&P/ASX300 report emails
# -- a genuinely independent developed market, not a Kaggle re-export like the
# two sources above. See ../README.md "Data provenance: the ASX GitHub mirror"
# for what this is and is not a substitute for, and why Milestone 22 searched
# for (and could not reach) a European mirror first.

_ASX_REPO_BASE = (
    "https://raw.githubusercontent.com/grantcarthew/data-asx-historical-share-tables/"
    "master/csv/Daily/S%26P-ASX300/"
)
_ASX_DATES_FILE = Path(__file__).parent / "resources" / "asx300_dates.txt"

# One CSV per report; the filename date is the day the report was PROCESSED
# (usually the next morning), not the trading date inside the file, and the
# offset between the two isn't constant (weekends/public holidays shift it) --
# see _parse_asx_daily_csv, which reads the real trading date out of the
# file's own header text rather than trusting the filename.
_ASX_DATE_RE_SLASH = re.compile(r"(\d{1,2}/\d{1,2}/\d{4})")
_ASX_DATE_RE_LONG = re.compile(r"([A-Za-z]+day,\s*[A-Za-z]+\s+\d{1,2},\s*\d{4})")


def _asx_report_dates() -> list[str]:
    """The list of report-filename dates this loader knows to fetch, derived
    once by listing grantcarthew/data-asx-historical-share-tables's
    csv/Daily/S&P-ASX300/ directory (that listing isn't itself re-fetchable
    through this sandbox's GitHub proxy, which only serves known raw file
    paths, not directory browsing -- so the list is captured here instead)."""
    return _ASX_DATES_FILE.read_text().split()


def _parse_asx_daily_csv(text: str) -> tuple[pd.Timestamp, pd.Series] | None:
    """Parse one ASX daily report CSV's text into (trading_date, close_prices
    indexed by ASX code). Returns None if the file has no recognizable date or
    header (a handful of report emails in this mirror are malformed/empty)."""
    lines = text.splitlines(keepends=True)
    date = None
    for line in lines[:4]:
        m = _ASX_DATE_RE_SLASH.search(line)
        if m:
            date = pd.Timestamp(dt.datetime.strptime(m.group(1), "%d/%m/%Y"))
            break
        m = _ASX_DATE_RE_LONG.search(line)
        if m:
            date = pd.Timestamp(dt.datetime.strptime(m.group(1), "%A, %B %d, %Y"))
            break
    if date is None:
        return None

    header_idx = next((i for i, l in enumerate(lines) if l.startswith("52 Week High")), None)
    if header_idx is None:
        return None

    with warnings.catch_warnings():
        # data rows carry two trailing empty fields the header row doesn't --
        # harmless (index_col=False already prevents pandas mis-parsing the
        # first column as an index because of it), just noisy.
        warnings.simplefilter("ignore", category=pd.errors.ParserWarning)
        df = pd.read_csv(
            io.StringIO(text), skiprows=header_idx, thousands=",",
            on_bad_lines="skip", index_col=False,
        )
    df.columns = [c.strip() for c in df.columns]
    if "ASX Code" not in df.columns or "Last Sale" not in df.columns:
        return None
    sub = df[["ASX Code", "Last Sale"]].dropna(subset=["ASX Code"])
    prices = pd.to_numeric(sub["Last Sale"], errors="coerce")
    prices.index = sub["ASX Code"].astype(str)
    prices = prices[~prices.index.duplicated(keep="first")]
    return date, prices


def _fetch_asx_daily(report_date: str) -> tuple[pd.Timestamp, pd.Series] | None:
    url = _ASX_REPO_BASE + requests.utils.quote(f"Daily - S&P-ASX300 - {report_date}.csv")
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return _parse_asx_daily_csv(resp.text)
    except Exception:
        return None


def load_asx_github_mirror(
    use_cache: bool = True, max_workers: int = 20, min_history_days: int = 1000
) -> pd.DataFrame:
    """Load the ASX (Australia) S&P/ASX300 daily-report mirror from GitHub,
    parse each day's report, and pivot to a wide date x ASX-code DataFrame of
    closing ("Last Sale") prices. Covers 2009-10-20 through 2015-12-31 (this
    mirror's full range), ~296-300 constituents on every trading day -- a
    materially more stable universe size than the NSE mirror's early years
    (see Milestone 15), though shorter in span than either the NSE or US
    mirrors. Fetches ~1,600 individual daily reports in parallel (one HTTP
    request per trading day, since this source has no combined file); cached
    to parquet afterward so repeated runs don't re-fetch.

    Raw parsing yields several hundred extra, mostly near-empty "codes" beyond
    the ~300 genuine constituents -- deferred-settlement trading variants
    (suffixes like DA/DC/R that ASX uses temporarily during capital raisings,
    not separate companies) and a handful of malformed report rows. Dropping
    any code with fewer than `min_history_days` observations (same threshold
    and same Milestone-15 motivation as `load_nse_github_mirror`) removes
    essentially all of them and leaves ~200 persistent constituents.
    """
    cache_file = CACHE_DIR / "asx_github_mirror.parquet"
    if use_cache and cache_file.exists():
        return pd.read_parquet(cache_file)

    report_dates = _asx_report_dates()
    rows: dict[pd.Timestamp, pd.Series] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for result in pool.map(_fetch_asx_daily, report_dates):
            if result is None:
                continue
            date, prices = result
            rows[date] = prices

    if not rows:
        raise RuntimeError("No ASX daily reports could be fetched or parsed.")

    wide = pd.DataFrame(rows).T.sort_index()
    wide.index.name = "Date"

    long_enough = wide.count() >= min_history_days
    wide = wide.loc[:, long_enough]

    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        wide.to_parquet(cache_file)
    return wide


if __name__ == "__main__":
    prices = load_nse_github_mirror()
    print(prices.tail())
    print(f"NSE mirror: {prices.shape[1]} companies, {prices.shape[0]} trading days "
          f"({prices.index.min().date()} to {prices.index.max().date()}).")

    us_prices = load_us_kaggle_mirror()
    print(us_prices.tail())
    print(f"US mirror: {us_prices.shape[1]} companies, {us_prices.shape[0]} trading days "
          f"({us_prices.index.min().date()} to {us_prices.index.max().date()}).")
