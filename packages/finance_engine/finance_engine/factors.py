"""The 4 computable screening factors: growth, margins, cash_conversion,
leverage_capacity.

Each function takes a list of `FinancialPeriodInput` that the caller has
already deduped/selected (see `select_fy_periods` below) and returns a
`FactorResult`. Every function is pure and deterministic -- no I/O, no
wall-clock reads, no randomness -- so they are directly unit-testable.

When a factor cannot be computed (missing data, degenerate inputs), the
function returns the neutral default (50) with a populated `warning` field
rather than raising or silently returning 0 -- callers use the presence of
`warning` to label the factor's `source` as "default" instead of "computed".
"""

from typing import Dict, List, Optional

from .constants import (
    CASH_CONVERSION_CEILING,
    GROWTH_CAGR_CEILING,
    GROWTH_CAGR_FLOOR,
    GROWTH_MIN_FY_PERIODS,
    INTEREST_COVERAGE_CEILING,
    INTEREST_COVERAGE_FLOOR,
    LEVERAGE_RATIO_CEILING,
    MARGIN_CEILING,
    MAX_FY_PERIODS_USED,
    NEUTRAL_DEFAULT_SCORE,
    PREFERRED_SOURCE,
)
from .types import FactorResult, FinancialPeriodInput


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def select_fy_periods(
    periods: List[FinancialPeriodInput], max_periods: int = MAX_FY_PERIODS_USED
) -> List[FinancialPeriodInput]:
    """Pick up to `max_periods` most recent FY periods, one per fiscal year,
    preferring PREFERRED_SOURCE ("SEC_EDGAR") when the same fiscal_year is
    reported by more than one source (design doc section 2.2/3.2).

    Returns periods sorted ascending by fiscal_year (oldest first, most
    recent last) so callers can index [0] for earliest and [-1] for latest.
    """
    fy_periods = [p for p in periods if p.period_type == "FY"]

    by_year: Dict[int, FinancialPeriodInput] = {}
    for p in fy_periods:
        existing = by_year.get(p.fiscal_year)
        if existing is None:
            by_year[p.fiscal_year] = p
        elif existing.source != PREFERRED_SOURCE and p.source == PREFERRED_SOURCE:
            by_year[p.fiscal_year] = p
        # else: keep whichever was selected first -- already preferred, or
        # both non-preferred (order between two non-preferred sources for
        # the same year is not specified by the design doc; first-seen wins).

    selected_years = sorted(by_year.keys())[-max_periods:]
    return [by_year[y] for y in selected_years]


def compute_growth(periods: List[FinancialPeriodInput]) -> FactorResult:
    """Revenue CAGR over the earliest-to-latest selected FY periods.

    Requires >= GROWTH_MIN_FY_PERIODS periods with usable (non-null)
    revenue; otherwise neutral default with a data-quality warning, per
    design doc section 3.2 ("if only 1 exists, factor = None").
    """
    usable = [p for p in periods if p.revenue is not None]

    if len(usable) < GROWTH_MIN_FY_PERIODS:
        return FactorResult(
            normalized_score=NEUTRAL_DEFAULT_SCORE,
            notes=(
                f"fewer than {GROWTH_MIN_FY_PERIODS} FY periods with revenue data "
                f"({len(usable)} available); neutral default (50) used"
            ),
            warning="growth: insufficient data (<2 FY periods), neutral default (50) used",
        )

    earliest, latest = usable[0], usable[-1]
    n_years = latest.fiscal_year - earliest.fiscal_year

    if n_years <= 0 or earliest.revenue is None or earliest.revenue <= 0:
        return FactorResult(
            normalized_score=NEUTRAL_DEFAULT_SCORE,
            notes=(
                "cannot compute CAGR (zero-year span or non-positive earliest "
                "revenue); neutral default (50) used"
            ),
            warning="growth: cannot compute CAGR, neutral default (50) used",
        )

    revenue_cagr = (float(latest.revenue) / float(earliest.revenue)) ** (1.0 / n_years) - 1.0
    score = clamp((revenue_cagr - GROWTH_CAGR_FLOOR) / (GROWTH_CAGR_CEILING - GROWTH_CAGR_FLOOR) * 100, 0, 100)

    return FactorResult(
        normalized_score=score,
        notes=(
            f"revenue CAGR {revenue_cagr:.1%} over {n_years} year(s), "
            f"FY{earliest.fiscal_year}-FY{latest.fiscal_year}"
        ),
    )


def compute_margins(periods: List[FinancialPeriodInput]) -> FactorResult:
    """Average EBITDA margin across available FY periods.

    Periods with revenue <= 0 (or missing revenue/ebitda) are excluded
    rather than divided-by-zero, per design doc section 3.2.
    """
    usable = [
        p
        for p in periods
        if p.revenue is not None and p.revenue > 0 and p.ebitda is not None
    ]

    if not usable:
        return FactorResult(
            normalized_score=NEUTRAL_DEFAULT_SCORE,
            notes="no FY period with positive revenue and EBITDA data; neutral default (50) used",
            warning="margins: insufficient data, neutral default (50) used",
        )

    margins = [float(p.ebitda) / float(p.revenue) for p in usable]  # type: ignore[arg-type]
    avg_margin = sum(margins) / len(margins)
    score = clamp(avg_margin / MARGIN_CEILING * 100, 0, 100)

    return FactorResult(
        normalized_score=score,
        notes=f"avg EBITDA margin {avg_margin:.1%} across {len(usable)} FY period(s)",
    )


def compute_cash_conversion(periods: List[FinancialPeriodInput]) -> FactorResult:
    """Average FCF/EBITDA across available FY periods.

    FCF is always recomputed here (operating_cash_flow - capex), never read
    from a stored field, per design doc section 2.2/3.2. Periods with
    ebitda <= 0 or missing cash-flow inputs are skipped.
    """
    usable = [
        p
        for p in periods
        if p.ebitda is not None
        and p.ebitda > 0
        and p.operating_cash_flow is not None
        and p.capex is not None
    ]

    if not usable:
        return FactorResult(
            normalized_score=NEUTRAL_DEFAULT_SCORE,
            notes=(
                "no FY period with positive EBITDA and complete cash-flow data; "
                "neutral default (50) used"
            ),
            warning="cash_conversion: insufficient data, neutral default (50) used",
        )

    ratios = [
        (float(p.operating_cash_flow) - float(p.capex)) / float(p.ebitda)  # type: ignore[arg-type]
        for p in usable
    ]
    avg_ratio = sum(ratios) / len(ratios)
    score = clamp(avg_ratio / CASH_CONVERSION_CEILING * 100, 0, 100)

    return FactorResult(
        normalized_score=score,
        notes=f"avg FCF/EBITDA {avg_ratio:.1%} across {len(usable)} FY period(s)",
    )


def compute_leverage_capacity(periods: List[FinancialPeriodInput]) -> FactorResult:
    """Point-in-time (latest FY only) 50/50 blend of a net-debt/EBITDA
    sub-score and an interest-coverage sub-score.

    Two independent edge cases per design doc section 3.2, both of which can
    apply at once:
      - ebitda_latest <= 0            -> leverage_score floored at 0, flagged
      - interest_expense null/zero    -> coverage_score set to 100, flagged
    """
    if not periods:
        return FactorResult(
            normalized_score=NEUTRAL_DEFAULT_SCORE,
            notes="no FY period available; neutral default (50) used",
            warning="leverage_capacity: insufficient data, neutral default (50) used",
        )

    latest = periods[-1]

    if latest.total_debt is None or latest.cash_and_equivalents is None or latest.ebitda is None:
        return FactorResult(
            normalized_score=NEUTRAL_DEFAULT_SCORE,
            notes="latest FY period missing debt/cash/EBITDA data; neutral default (50) used",
            warning="leverage_capacity: insufficient data, neutral default (50) used",
        )

    ebitda_latest = float(latest.ebitda)
    net_debt = float(latest.total_debt) - float(latest.cash_and_equivalents)

    warnings: List[str] = []
    notes_parts: List[str] = []

    if ebitda_latest <= 0:
        leverage_score = 0.0
        warnings.append("leverage_capacity: EBITDA <= 0, leverage_score floored at 0")
        notes_parts.append(f"net debt/EBITDA undefined (EBITDA {ebitda_latest:,.0f} <= 0), leverage_score=0")
    else:
        leverage_ratio = net_debt / ebitda_latest
        leverage_score = clamp((1 - leverage_ratio / LEVERAGE_RATIO_CEILING) * 100, 0, 100)
        notes_parts.append(f"net debt/EBITDA {leverage_ratio:.2f}x")

    interest_expense: Optional[float] = (
        float(latest.interest_expense) if latest.interest_expense is not None else None
    )
    if interest_expense is None or interest_expense == 0:
        coverage_score = 100.0
        warnings.append(
            "leverage_capacity: interest_expense null/zero, coverage_score set to 100 (no debt service burden)"
        )
        notes_parts.append("interest coverage n/a (no interest expense), coverage_score=100")
    else:
        interest_coverage = ebitda_latest / interest_expense
        coverage_score = clamp(
            (interest_coverage - INTEREST_COVERAGE_FLOOR)
            / (INTEREST_COVERAGE_CEILING - INTEREST_COVERAGE_FLOOR)
            * 100,
            0,
            100,
        )
        notes_parts.append(f"interest coverage {interest_coverage:.2f}x")

    leverage_capacity_score = (leverage_score + coverage_score) / 2.0

    return FactorResult(
        normalized_score=leverage_capacity_score,
        notes="; ".join(notes_parts),
        warning="; ".join(warnings) if warnings else None,
    )
