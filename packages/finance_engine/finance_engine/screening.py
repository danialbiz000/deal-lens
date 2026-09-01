"""score_company: combine the 4 computed factors + 4 Assumption-based
placeholder factors into the final 0-100 screening score.

Formula (design doc section 3.4):
    score = 0.20*business_quality + 0.15*growth + 0.15*margins
          + 0.15*cash_conversion + 0.10*leverage_capacity
          + 0.10*market_structure + 0.10*exit_optionality
          + 0.05*management_execution

This module is the only place that assembles the full 8-factor result; it
performs no I/O and is fully deterministic given its inputs, so calling it
twice with identical periods/assumptions always returns an identical score.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from . import factors as _factors
from .constants import FORMULA_VERSION, NEUTRAL_DEFAULT_SCORE, PLACEHOLDER_FACTOR_NAMES, WEIGHTS
from .types import AssumptionInput, FinancialPeriodInput


@dataclass(frozen=True)
class ScoredFactor:
    name: str
    weight: float
    normalized_score: float
    source: str  # "computed" | "default" | "assumption"
    contribution: float
    notes: str


@dataclass(frozen=True)
class ScreeningResult:
    formula_version: str
    score: float
    factors: List[ScoredFactor]
    warnings: List[str]
    computed_at: str


def _placeholder_factor(
    name: str, assumptions: List[AssumptionInput]
) -> Tuple[ScoredFactor, Optional[str]]:
    assumption_name = PLACEHOLDER_FACTOR_NAMES[name]
    match = next(
        (a for a in assumptions if a.name == assumption_name and a.value_numeric is not None),
        None,
    )
    weight = WEIGHTS[name]

    if match is None:
        value = NEUTRAL_DEFAULT_SCORE
        source = "default"
        notes = "no assumption on file; neutral default (50) used"
        warning: Optional[str] = f"{name}: no assumption on file; neutral default (50) used"
    else:
        value = float(match.value_numeric)  # type: ignore[arg-type]
        source = "assumption"
        notes = f"assumption '{assumption_name}' = {value}"
        warning = None

    scored = ScoredFactor(
        name=name,
        weight=weight,
        normalized_score=value,
        source=source,
        contribution=weight * value,
        notes=notes,
    )
    return scored, warning


def score_company(
    periods: List[FinancialPeriodInput], assumptions: List[AssumptionInput]
) -> ScreeningResult:
    """Compute the full 8-factor screening score.

    `periods` may contain any mix of period_type/source; this function
    selects and dedupes the FY periods it needs internally (see
    `factors.select_fy_periods`). Passing an empty `periods` list is valid
    input as far as this function is concerned -- all 4 computable factors
    will fall back to their neutral defaults with warnings; callers (the API
    layer) decide whether an empty-periods company should instead be a 422.
    """
    warnings: List[str] = []
    result_factors: List[ScoredFactor] = []

    fy_periods = _factors.select_fy_periods(periods)

    computable_results = {
        "growth": _factors.compute_growth(fy_periods),
        "margins": _factors.compute_margins(fy_periods),
        "cash_conversion": _factors.compute_cash_conversion(fy_periods),
        "leverage_capacity": _factors.compute_leverage_capacity(fy_periods),
    }

    for name, factor_result in computable_results.items():
        weight = WEIGHTS[name]
        source = "computed" if factor_result.warning is None else "default"
        result_factors.append(
            ScoredFactor(
                name=name,
                weight=weight,
                normalized_score=factor_result.normalized_score,
                source=source,
                contribution=weight * factor_result.normalized_score,
                notes=factor_result.notes,
            )
        )
        if factor_result.warning:
            warnings.append(factor_result.warning)

    for name in PLACEHOLDER_FACTOR_NAMES:
        scored, warning = _placeholder_factor(name, assumptions)
        result_factors.append(scored)
        if warning:
            warnings.append(warning)

    total_score = sum(f.contribution for f in result_factors)

    return ScreeningResult(
        formula_version=FORMULA_VERSION,
        score=round(total_score, 2),
        factors=result_factors,
        warnings=warnings,
        computed_at=datetime.now(timezone.utc).isoformat(),
    )
