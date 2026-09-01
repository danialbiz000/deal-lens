"""Deterministic LBO underwriting engine: Sources & Uses, year-by-year
operating case + debt schedule, exit & returns, and a value-creation bridge
that reconciles exactly to MOIC.

Pure Python, zero I/O/DB dependency -- same discipline as screening.py.
Every formula here matches docs/phase2-comps-lbo-design.md section 4-5
verbatim; see that doc for the economic rationale behind each documented
MVP simplification (capex-as-D&A-tax-shield-proxy, flat-% NWC, single
blended debt tranche, no revolver, clean single entry/exit for IRR).
"""

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    EXIT_MULTIPLE_DEPENDENT_THRESHOLD,
    LBO_DEFAULT_CAPEX_PCT_REVENUE,
    LBO_DEFAULT_CASH_SWEEP_PCT,
    LBO_DEFAULT_HOLD_PERIOD_YEARS,
    LBO_DEFAULT_INTEREST_RATE,
    LBO_DEFAULT_LEVERAGE_MULTIPLE,
    LBO_DEFAULT_MANDATORY_AMORT_PCT,
    LBO_DEFAULT_NWC_PCT_REVENUE_CHANGE,
    LBO_DEFAULT_TAX_RATE,
    LBO_DEFAULT_TRANSACTION_FEES_PCT,
    LBO_FORMULA_VERSION,
    SENSITIVITY_DEFAULT_SIZE,
    SENSITIVITY_DEFAULT_STEP,
)
from .factors import clamp


@dataclass(frozen=True)
class LboInputs:
    """Every input the LBO waterfall needs, already resolved by the caller
    (entry_ev from comps.py or an explicit override; the operating deltas
    from a Scenario row; the lbo_* fields from Assumption rows or their
    defaults). Kept flat and explicit rather than reaching back into the DB
    -- inputs_json is a verbatim snapshot of this dataclass.
    """

    entry_ev: float
    entry_ebitda: float
    entry_revenue: float
    revenue_growth_rate: float
    ebitda_margin_delta: float
    exit_multiple_delta: float

    lbo_leverage_multiple: float = LBO_DEFAULT_LEVERAGE_MULTIPLE
    lbo_interest_rate: float = LBO_DEFAULT_INTEREST_RATE
    lbo_cash_sweep_pct: float = LBO_DEFAULT_CASH_SWEEP_PCT
    lbo_mandatory_amort_pct: float = LBO_DEFAULT_MANDATORY_AMORT_PCT
    lbo_tax_rate: float = LBO_DEFAULT_TAX_RATE
    lbo_capex_pct_revenue: float = LBO_DEFAULT_CAPEX_PCT_REVENUE
    lbo_nwc_pct_revenue_change: float = LBO_DEFAULT_NWC_PCT_REVENUE_CHANGE
    lbo_transaction_fees_pct: float = LBO_DEFAULT_TRANSACTION_FEES_PCT
    hold_period_years: int = LBO_DEFAULT_HOLD_PERIOD_YEARS


@dataclass(frozen=True)
class SourcesUses:
    new_debt: float
    sponsor_equity: float
    purchase_ev: float
    fees: float
    reconciles: bool


@dataclass(frozen=True)
class ScheduleYear:
    year: int
    revenue: float
    ebitda: float
    beginning_debt: float
    ending_debt: float
    beginning_cash: float
    ending_cash: float
    margin: Optional[float] = None
    capex: Optional[float] = None
    nwc_investment: Optional[float] = None
    interest: Optional[float] = None
    taxes: Optional[float] = None
    cfads: Optional[float] = None
    mandatory_amort: Optional[float] = None
    sweep: Optional[float] = None


@dataclass(frozen=True)
class ValueCreationBridge:
    entry_equity: float
    ebitda_growth: float
    margin_expansion: float
    debt_paydown: float
    multiple_expansion: float
    transaction_fees: float
    total: float  # reconciles to `moic` within 1e-6 by construction
    exit_multiple_dependent: bool
    value_destructive: bool


@dataclass(frozen=True)
class LboResult:
    formula_version: str
    inputs: Dict[str, Any]
    sources_uses: SourcesUses
    schedule: List[ScheduleYear]
    entry_ev: float
    exit_ev: float
    exit_equity_value: float
    moic: float
    irr: float
    entry_leverage: float
    exit_leverage: float
    entry_multiple: float
    exit_multiple: float
    value_creation_bridge: ValueCreationBridge
    warnings: List[str]
    computed_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def run_lbo(inputs: LboInputs) -> LboResult:
    if inputs.entry_ebitda is None or inputs.entry_ebitda <= 0:
        raise ValueError("entry_ebitda must be > 0 to run an LBO")
    if inputs.hold_period_years <= 0:
        raise ValueError("hold_period_years must be > 0")

    warnings: List[str] = []

    entry_multiple = inputs.entry_ev / inputs.entry_ebitda

    # --- 1. Sources & Uses (Year 0) ---
    fees_amount = inputs.entry_ev * inputs.lbo_transaction_fees_pct
    new_debt = inputs.entry_ebitda * inputs.lbo_leverage_multiple
    uses_total = inputs.entry_ev + fees_amount
    sponsor_equity = uses_total - new_debt
    sources_total = new_debt + sponsor_equity
    reconciles = abs(sources_total - uses_total) < 0.01

    sources_uses = SourcesUses(
        new_debt=new_debt, sponsor_equity=sponsor_equity, purchase_ev=inputs.entry_ev, fees=fees_amount,
        reconciles=reconciles,
    )

    # --- 2 & 4. Year-by-year operating case + debt schedule ---
    base_margin = inputs.entry_ebitda / inputs.entry_revenue if inputs.entry_revenue else 0.0

    schedule: List[ScheduleYear] = [
        ScheduleYear(
            year=0,
            revenue=inputs.entry_revenue,
            ebitda=inputs.entry_ebitda,
            beginning_debt=new_debt,
            ending_debt=new_debt,
            beginning_cash=0.0,
            ending_cash=0.0,
        )
    ]

    revenue_prev = inputs.entry_revenue
    debt_prev = new_debt
    cash_prev = 0.0

    for t in range(1, inputs.hold_period_years + 1):
        revenue_t = revenue_prev * (1 + inputs.revenue_growth_rate)
        margin_t = base_margin + inputs.ebitda_margin_delta * (t / inputs.hold_period_years)
        ebitda_t = revenue_t * margin_t
        capex_t = revenue_t * inputs.lbo_capex_pct_revenue
        delta_rev_t = revenue_t - revenue_prev
        nwc_invest_t = delta_rev_t * inputs.lbo_nwc_pct_revenue_change

        interest_t = debt_prev * inputs.lbo_interest_rate
        pretax_income_t = ebitda_t - capex_t - interest_t
        taxes_t = max(0.0, pretax_income_t) * inputs.lbo_tax_rate
        cfads_t = ebitda_t - capex_t - taxes_t - nwc_invest_t

        mandatory_amort_t = min(debt_prev, new_debt * inputs.lbo_mandatory_amort_pct)
        cash_before_sweep_t = cfads_t - interest_t - mandatory_amort_t

        if cash_before_sweep_t > 0:
            sweep_t = clamp(cash_before_sweep_t, 0, debt_prev - mandatory_amort_t) * inputs.lbo_cash_sweep_pct
            unswept_cash_t = cash_before_sweep_t - sweep_t
        else:
            sweep_t = 0.0
            unswept_cash_t = cash_before_sweep_t  # allowed to be negative -- no revolver modeled

        ending_debt_t = debt_prev - mandatory_amort_t - sweep_t
        ending_cash_t = cash_prev + unswept_cash_t

        if ending_cash_t < 0:
            warnings.append(
                f"year {t}: ending cash is negative ({ending_cash_t:,.0f}) -- the case as specified "
                f"would need incremental financing not modeled here (no revolver in this slice)"
            )

        schedule.append(
            ScheduleYear(
                year=t,
                revenue=revenue_t,
                ebitda=ebitda_t,
                margin=margin_t,
                capex=capex_t,
                nwc_investment=nwc_invest_t,
                interest=interest_t,
                taxes=taxes_t,
                cfads=cfads_t,
                mandatory_amort=mandatory_amort_t,
                sweep=sweep_t,
                beginning_debt=debt_prev,
                ending_debt=ending_debt_t,
                beginning_cash=cash_prev,
                ending_cash=ending_cash_t,
            )
        )

        revenue_prev = revenue_t
        debt_prev = ending_debt_t
        cash_prev = ending_cash_t

    # --- 5. Exit & returns ---
    final_year = schedule[-1]
    exit_ebitda = final_year.ebitda
    exit_multiple = entry_multiple + inputs.exit_multiple_delta
    exit_ev = exit_ebitda * exit_multiple
    ending_debt_n = final_year.ending_debt
    ending_cash_n = final_year.ending_cash
    exit_net_debt = ending_debt_n - ending_cash_n
    exit_equity_value = exit_ev - exit_net_debt

    moic = exit_equity_value / sponsor_equity
    irr = moic ** (1.0 / inputs.hold_period_years) - 1.0

    entry_leverage = new_debt / inputs.entry_ebitda
    exit_leverage = ending_debt_n / exit_ebitda if exit_ebitda else 0.0

    # --- Value creation bridge (design doc section 5) ---
    revenue_n = final_year.revenue
    ebitda_at_entry_margin = revenue_n * base_margin

    ebitda_growth = (ebitda_at_entry_margin - inputs.entry_ebitda) * entry_multiple / sponsor_equity
    margin_expansion = (exit_ebitda - ebitda_at_entry_margin) * entry_multiple / sponsor_equity
    debt_paydown = (new_debt - exit_net_debt) / sponsor_equity
    multiple_expansion = exit_ebitda * (exit_multiple - entry_multiple) / sponsor_equity
    transaction_fees_line = -fees_amount / sponsor_equity
    entry_equity_line = 1.00

    total = entry_equity_line + ebitda_growth + margin_expansion + debt_paydown + multiple_expansion + transaction_fees_line

    value_creation_total = moic - 1.00
    if value_creation_total > 0:
        exit_multiple_dependent = (multiple_expansion / value_creation_total) > EXIT_MULTIPLE_DEPENDENT_THRESHOLD
        value_destructive = False
    else:
        exit_multiple_dependent = False
        value_destructive = True

    bridge = ValueCreationBridge(
        entry_equity=entry_equity_line,
        ebitda_growth=ebitda_growth,
        margin_expansion=margin_expansion,
        debt_paydown=debt_paydown,
        multiple_expansion=multiple_expansion,
        transaction_fees=transaction_fees_line,
        total=total,
        exit_multiple_dependent=exit_multiple_dependent,
        value_destructive=value_destructive,
    )

    inputs_snapshot = {
        "entry_ev": inputs.entry_ev,
        "entry_ebitda": inputs.entry_ebitda,
        "entry_revenue": inputs.entry_revenue,
        "entry_multiple": entry_multiple,
        "lbo_leverage_multiple": inputs.lbo_leverage_multiple,
        "lbo_interest_rate": inputs.lbo_interest_rate,
        "lbo_cash_sweep_pct": inputs.lbo_cash_sweep_pct,
        "lbo_mandatory_amort_pct": inputs.lbo_mandatory_amort_pct,
        "lbo_tax_rate": inputs.lbo_tax_rate,
        "lbo_capex_pct_revenue": inputs.lbo_capex_pct_revenue,
        "lbo_nwc_pct_revenue_change": inputs.lbo_nwc_pct_revenue_change,
        "lbo_transaction_fees_pct": inputs.lbo_transaction_fees_pct,
        "hold_period_years": inputs.hold_period_years,
        "revenue_growth_rate": inputs.revenue_growth_rate,
        "ebitda_margin_delta": inputs.ebitda_margin_delta,
        "exit_multiple_delta": inputs.exit_multiple_delta,
    }

    return LboResult(
        formula_version=LBO_FORMULA_VERSION,
        inputs=inputs_snapshot,
        sources_uses=sources_uses,
        schedule=schedule,
        entry_ev=inputs.entry_ev,
        exit_ev=exit_ev,
        exit_equity_value=exit_equity_value,
        moic=moic,
        irr=irr,
        entry_leverage=entry_leverage,
        exit_leverage=exit_leverage,
        entry_multiple=entry_multiple,
        exit_multiple=exit_multiple,
        value_creation_bridge=bridge,
        warnings=warnings,
        computed_at=datetime.now(timezone.utc).isoformat(),
    )


def run_sensitivity_grid(
    base_inputs: LboInputs,
    step: float = SENSITIVITY_DEFAULT_STEP,
    size: int = SENSITIVITY_DEFAULT_SIZE,
) -> Dict[str, Any]:
    """Entry x exit multiple IRR/MOIC grid (design doc section 6).

    Recomputes the FULL LBO per cell via `run_lbo` -- no separate/duplicated
    sensitivity formula. `base_entry_multiple`/`base_exit_multiple` are
    derived from `base_inputs` itself so the grid is always centered on the
    actual base-case run.
    """
    if base_inputs.entry_ebitda <= 0:
        raise ValueError("entry_ebitda must be > 0 to build a sensitivity grid")

    base_entry_multiple = base_inputs.entry_ev / base_inputs.entry_ebitda
    base_exit_multiple = base_entry_multiple + base_inputs.exit_multiple_delta

    offset = (size - 1) / 2.0
    entry_multiples = [base_entry_multiple + (i - offset) * step for i in range(size)]
    exit_multiples = [base_exit_multiple + (j - offset) * step for j in range(size)]

    irr_grid: List[List[float]] = []
    moic_grid: List[List[float]] = []

    for entry_mult in entry_multiples:
        irr_row: List[float] = []
        moic_row: List[float] = []
        new_entry_ev = base_inputs.entry_ebitda * entry_mult
        for exit_mult in exit_multiples:
            cell_inputs = replace(
                base_inputs,
                entry_ev=new_entry_ev,
                exit_multiple_delta=exit_mult - entry_mult,  # so entry_multiple + delta == exit_mult exactly
            )
            result = run_lbo(cell_inputs)
            irr_row.append(result.irr)
            moic_row.append(result.moic)
        irr_grid.append(irr_row)
        moic_grid.append(moic_row)

    return {
        "entry_multiples": entry_multiples,
        "exit_multiples": exit_multiples,
        "irr_grid": irr_grid,
        "moic_grid": moic_grid,
    }
