"""Full tornado sensitivity (design doc section 11, v1.0): independently
perturb each of the spec's 6 variables -- growth, margin, entry multiple,
leverage, interest rate, exit multiple -- low/high around the base case,
holding every other variable fixed, and re-run the full deterministic
`run_lbo` waterfall for each side. Never a separate/duplicated sensitivity
formula, exactly like the existing entry x exit 2D grid in lbo.py.

Kept in its own module (not lbo.py) purely to keep lbo.py itself under this
project's file-size convention -- this is presentation/orchestration on top
of run_lbo, not new financial math.
"""

from dataclasses import asdict, dataclass, replace
from typing import Any, Dict, List, Optional

from .constants import TORNADO_DEFAULT_DELTAS, TORNADO_VARIABLE_FLOORS, TORNADO_VARIABLE_LABELS
from .lbo import LboInputs, _resolve_tranches, run_lbo


@dataclass(frozen=True)
class TornadoVariableResult:
    variable: str
    label: str
    base_value: float
    low_value: float
    high_value: float
    base_irr: float
    low_irr: float
    high_irr: float
    base_moic: float
    low_moic: float
    high_moic: float
    spread: float  # abs(high_irr - low_irr) -- sorts the tornado, widest first


def _tornado_base_value(inputs: LboInputs, variable: str) -> float:
    if variable == "revenue_growth_rate":
        return inputs.revenue_growth_rate
    if variable == "ebitda_margin_delta":
        return inputs.ebitda_margin_delta
    if variable == "entry_multiple":
        return inputs.entry_ev / inputs.entry_ebitda
    if variable == "exit_multiple":
        return inputs.entry_ev / inputs.entry_ebitda + inputs.exit_multiple_delta
    if variable == "leverage":
        return sum(tr.leverage_multiple for tr in _resolve_tranches(inputs))
    if variable == "interest_rate":
        # With multiple tranches there's no single "the" rate -- report the
        # highest-priority tranche's rate as the representative value, since
        # that's the one most PE conversations mean by "the base rate" when
        # a deal has senior + subordinated debt at different spreads.
        tranches = sorted(_resolve_tranches(inputs), key=lambda tr: tr.priority)
        return tranches[0].interest_rate if tranches else inputs.lbo_interest_rate
    raise ValueError(f"unknown tornado variable: {variable}")


def _apply_tornado_variable(inputs: LboInputs, variable: str, target_value: float) -> LboInputs:
    if variable == "revenue_growth_rate":
        return replace(inputs, revenue_growth_rate=target_value)
    if variable == "ebitda_margin_delta":
        return replace(inputs, ebitda_margin_delta=target_value)
    if variable == "entry_multiple":
        # Hold the absolute EXIT multiple fixed while entry moves -- isolates
        # "what if I pay more/less to get in", the standard PE framing,
        # rather than letting exit drift by the same amount as entry.
        original_entry_multiple = inputs.entry_ev / inputs.entry_ebitda
        original_exit_multiple = original_entry_multiple + inputs.exit_multiple_delta
        return replace(
            inputs,
            entry_ev=inputs.entry_ebitda * target_value,
            exit_multiple_delta=original_exit_multiple - target_value,
        )
    if variable == "exit_multiple":
        entry_multiple = inputs.entry_ev / inputs.entry_ebitda
        return replace(inputs, exit_multiple_delta=target_value - entry_multiple)
    if variable == "leverage":
        # Scale every tranche's leverage_multiple proportionally so the
        # relative tranche mix (e.g. 70% senior / 30% mezz) is preserved --
        # a leverage sensitivity should mean "more/less debt at the same
        # capital-structure shape", not "change only the senior tranche".
        tranches = _resolve_tranches(inputs)
        current_total = sum(tr.leverage_multiple for tr in tranches)
        scale = (target_value / current_total) if current_total > 0 else 1.0
        scaled = tuple(replace(tr, leverage_multiple=tr.leverage_multiple * scale) for tr in tranches)
        return replace(inputs, debt_tranches=scaled, lbo_leverage_multiple=target_value)
    if variable == "interest_rate":
        # Shift every tranche's rate by the same absolute delta, preserving
        # each tranche's own credit spread relative to the others -- a rate
        # sensitivity models a broad rate-environment move, not a change to
        # one tranche's spread specifically.
        base_value = _tornado_base_value(inputs, variable)
        delta = target_value - base_value
        tranches = _resolve_tranches(inputs)
        shifted = tuple(replace(tr, interest_rate=max(0.0, tr.interest_rate + delta)) for tr in tranches)
        return replace(inputs, debt_tranches=shifted, lbo_interest_rate=max(0.0, inputs.lbo_interest_rate + delta))
    raise ValueError(f"unknown tornado variable: {variable}")


def run_tornado_analysis(base_inputs: LboInputs, deltas: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """Runs all 6 variables (or a caller-selected subset via `deltas`'
    keys) low/high around `base_inputs`, sorted widest-IRR-spread first --
    the conventional tornado-chart ordering.
    """
    resolved_deltas = {**TORNADO_DEFAULT_DELTAS, **(deltas or {})}
    base_result = run_lbo(base_inputs)

    results: List[TornadoVariableResult] = []
    for variable, delta in resolved_deltas.items():
        base_value = _tornado_base_value(base_inputs, variable)
        floor = TORNADO_VARIABLE_FLOORS.get(variable, float("-inf"))
        low_value = max(floor, base_value - delta)
        high_value = max(floor, base_value + delta)

        low_result = run_lbo(_apply_tornado_variable(base_inputs, variable, low_value))
        high_result = run_lbo(_apply_tornado_variable(base_inputs, variable, high_value))

        results.append(
            TornadoVariableResult(
                variable=variable,
                label=TORNADO_VARIABLE_LABELS.get(variable, variable),
                base_value=base_value,
                low_value=low_value,
                high_value=high_value,
                base_irr=base_result.irr,
                low_irr=low_result.irr,
                high_irr=high_result.irr,
                base_moic=base_result.moic,
                low_moic=low_result.moic,
                high_moic=high_result.moic,
                spread=abs(high_result.irr - low_result.irr),
            )
        )

    results.sort(key=lambda r: r.spread, reverse=True)
    return {"variables": [asdict(r) for r in results]}
