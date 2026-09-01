"""Deterministic bear-case threshold gate for the IC simulator (Phase 4).

This module's placement here -- inside `packages/finance_engine`, not
`apps/api/app/ai/` -- IS the guardrail, not just a convention
(docs/phase4-ai-layer-design.md section 1): this file has zero AI/HTTP
dependency and is physically incapable of importing anything from
`apps/api/app/ai/`. The AI layer calls into this module; it never calls
back. Spec rule enforced here, verbatim: "Do not permit a positive
recommendation if critical assumptions fail the bear case thresholds."

Deliberately decoupled from `finance_engine.lbo.LboResult`: this module
takes a minimal, self-contained `BearCaseInput` rather than importing the
full LBO dataclass, so it has no dependency surface on the LBO engine's
internals either -- only the 4 numbers/rows this specific policy check
needs.
"""

from dataclasses import dataclass
from typing import List, Optional

BEAR_IRR_FLOOR = 0.08  # typical PE hurdle rate
BEAR_MOIC_FLOOR = 1.0  # capital loss below this
BEAR_EXIT_LEVERAGE_CEILING = 6.0  # still overlevered at exit -> refinancing risk


@dataclass(frozen=True)
class BearCaseYear:
    year: int
    ebitda: float
    interest: Optional[float]  # None for year 0 (no debt service yet)


@dataclass(frozen=True)
class BearCaseInput:
    irr: float
    moic: float
    exit_leverage: float
    schedule: List[BearCaseYear]


@dataclass(frozen=True)
class GateResult:
    passes: bool
    failures: List[str]


def evaluate_bear_case_thresholds(bear_case: BearCaseInput) -> GateResult:
    """Check the bear case against 4 named thresholds. Returns every
    failure found (not just the first) so an override reason can name all
    of them, not just one.
    """
    failures: List[str] = []

    if bear_case.irr < BEAR_IRR_FLOOR:
        failures.append(f"bear IRR {bear_case.irr:.1%} below floor {BEAR_IRR_FLOOR:.0%}")

    if bear_case.moic < BEAR_MOIC_FLOOR:
        failures.append(f"bear MOIC {bear_case.moic:.2f}x below {BEAR_MOIC_FLOOR:.1f}x (capital loss)")

    if bear_case.exit_leverage > BEAR_EXIT_LEVERAGE_CEILING:
        failures.append(
            f"bear exit leverage {bear_case.exit_leverage:.1f}x exceeds {BEAR_EXIT_LEVERAGE_CEILING:.1f}x"
        )

    for year_row in bear_case.schedule:
        if year_row.interest is None:
            continue  # year 0: no debt service yet, nothing to check
        if year_row.ebitda <= year_row.interest:
            failures.append(f"year {year_row.year}: EBITDA does not cover interest (coverage < 1.0x)")

    return GateResult(passes=(len(failures) == 0), failures=failures)
