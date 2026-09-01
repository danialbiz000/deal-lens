"""finance_engine: pure-Python, deterministic PE screening math.

Zero FastAPI/DB/HTTP dependencies by design (see docs/phase0-vertical-slice-design.md
section 1). This package must remain importable and unit-testable standalone,
and must never import anything nondeterministic (no network, no wall-clock
randomness in the scoring math itself).
"""

from .comps import PeerEvaluation, ValuationResult, compute_valuation, evaluate_peer, select_top_peers
from .constants import FORMULA_VERSION, LBO_FORMULA_VERSION, WEIGHTS
from .ic_gate import BearCaseInput, BearCaseYear, GateResult, evaluate_bear_case_thresholds
from .lbo import LboInputs, LboResult, ScheduleYear, SourcesUses, ValueCreationBridge, run_lbo, run_sensitivity_grid
from .screening import ScoredFactor, ScreeningResult, score_company
from .types import AssumptionInput, CompanySnapshotInput, FactorResult, FinancialPeriodInput

__all__ = [
    "FORMULA_VERSION",
    "LBO_FORMULA_VERSION",
    "WEIGHTS",
    "AssumptionInput",
    "BearCaseInput",
    "BearCaseYear",
    "CompanySnapshotInput",
    "FactorResult",
    "FinancialPeriodInput",
    "GateResult",
    "LboInputs",
    "LboResult",
    "PeerEvaluation",
    "ScheduleYear",
    "ScoredFactor",
    "ScreeningResult",
    "SourcesUses",
    "ValuationResult",
    "ValueCreationBridge",
    "compute_valuation",
    "evaluate_bear_case_thresholds",
    "evaluate_peer",
    "run_lbo",
    "run_sensitivity_grid",
    "score_company",
    "select_top_peers",
]
