"""
Core of the Behavioral Signal & Stress-Risk Analytics toolkit. See
toolkit/__init__.py for the project context and toolkit/README.md for
usage. Every statistical routine here is imported, not reimplemented,
from the investigation script that first built and validated it --
this toolkit's job is to make those routines callable on a signal this
project has never seen, not to re-derive methodology that already
exists and is already trusted.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import numpy as np
import pandas as pd
from scipy import stats

from investigations.crash_stress_test_uncertainty_propagation import (
    COEF_NAMES,
    simulate_episode_with_parameter_uncertainty,
)
from investigations.momentum_crash_severity_stress_test import (
    historical_worst_episode_length,
    simulate_episode,
)
from investigations.momentum_crash_significance import build_regime_dummies, hac_regression
from investigations.momentum_var_cvar_profile import (
    empirical_var_cvar,
    gaussian_var_cvar,
)

DEFAULT_CONFIDENCE_LEVELS = (0.95, 0.99, 0.999)
DEFAULT_N_BOOTSTRAP = 5_000
DEFAULT_SEED = 7
DEFAULT_HAC_LAGS = 21
DEFAULT_DURATION_MULTIPLIERS = (1, 2, 3, 4)
DEFAULT_N_SIMS = 20_000


@dataclass
class CrashInteractionResult:
    label: str
    n_bear_highvol_days: int
    n_total_days: int
    interaction_coef: float
    interaction_p: float
    baseline_coef: float
    baseline_p: float
    era_start: pd.Timestamp
    fit: object  # the underlying statsmodels HAC regression result, for anyone who wants it

    @property
    def significant(self) -> bool:
        return self.interaction_p < 0.05

    def summary(self) -> str:
        verdict = "SIGNIFICANT" if self.significant else "no significant interaction (clean null)"
        return (
            f"{self.label}: Bear+HighVol interaction coef={self.interaction_coef:+.5f}  "
            f"p={self.interaction_p:.4f}  ({self.n_bear_highvol_days}/{self.n_total_days} "
            f"days were Bear+HighVol)  -> {verdict}"
        )


@dataclass
class TailRiskLevel:
    confidence: float
    empirical_var: float
    gaussian_var: float
    empirical_cvar: float
    gaussian_cvar: float
    cvar_ratio: float
    cvar_ratio_ci_lo: float
    cvar_ratio_ci_hi: float
    n_tail_obs: int


@dataclass
class TailRiskReport:
    label: str
    n: int
    mean: float
    std: float
    skew: float
    excess_kurtosis: float
    levels: list[TailRiskLevel] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"{self.label} (n={self.n}, mean={self.mean:+.4%}/day, std={self.std:.4%}/day, "
            f"skew={self.skew:+.2f}, excess kurtosis={self.excess_kurtosis:+.2f})"
        ]
        for lvl in self.levels:
            lines.append(
                f"  {lvl.confidence:.1%}: CVaR ratio (empirical/Gaussian)={lvl.cvar_ratio:.2f}x  "
                f"90% CI=({lvl.cvar_ratio_ci_lo:.2f}x, {lvl.cvar_ratio_ci_hi:.2f}x)  "
                f"(~{lvl.n_tail_obs} raw tail observations)"
            )
        return "\n".join(lines)


@dataclass
class StressRow:
    duration_multiplier: float
    n_days: int
    point_mean: float
    propagated_mean: float
    point_90pct_interval: tuple[float, float]
    propagated_90pct_interval: tuple[float, float]


@dataclass
class StressTable:
    label: str
    worst_historical_episode_days: int
    daily_drift_point: float
    daily_drift_90pct_ci: tuple[float, float]
    rows: list[StressRow] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"{self.label}: worst historical Bear+HighVol episode = "
            f"{self.worst_historical_episode_days} trading days; daily drift in regime = "
            f"{self.daily_drift_point:+.4%} (90% CI {self.daily_drift_90pct_ci[0]:+.4%} to "
            f"{self.daily_drift_90pct_ci[1]:+.4%})"
        ]
        for row in self.rows:
            lines.append(
                f"  {row.duration_multiplier:.1f}x worst ({row.n_days}d): "
                f"point mean={row.point_mean:+.1%}  propagated mean={row.propagated_mean:+.1%}  "
                f"propagated 90% interval=({row.propagated_90pct_interval[0]:+.1%}, "
                f"{row.propagated_90pct_interval[1]:+.1%})"
            )
        return "\n".join(lines)


@dataclass
class SignalRiskReport:
    label: str
    crash_interaction: CrashInteractionResult
    tail_risk: TailRiskReport
    stress: StressTable | None  # None if the interaction wasn't significant enough to stress-test

    def summary(self) -> str:
        parts = [
            f"{'=' * 90}\nSignal risk report: {self.label}\n{'=' * 90}",
            self.crash_interaction.summary(),
            "",
            self.tail_risk.summary(),
        ]
        if self.stress is not None:
            parts += ["", self.stress.summary()]
        else:
            parts += [
                "",
                "No crash-duration stress scenario run: the Bear+HighVol interaction wasn't "
                "significant, so projecting a regime-conditional stress loss from it would "
                "manufacture false precision -- exactly what Milestone 46 found for "
                "low-volatility and MAX, and what Milestone 53 found for turn-of-month.",
            ]
        return "\n".join(parts)


def crash_regime_interaction(
    label: str,
    hedged_returns: pd.Series,
    prices: pd.DataFrame,
    hac_lags: int = DEFAULT_HAC_LAGS,
) -> CrashInteractionResult:
    """Generalizes the Bear+HighVol regime-interaction test run on momentum
    (Milestones 16-18, 20), low-volatility/MAX (Milestone 46), and
    turn-of-month (Milestone 53) to any out-of-sample-hedged daily return
    series. `prices` supplies the look-ahead-free regime dummies (built
    from the same universe the signal trades, or any representative
    market proxy)."""
    regimes = build_regime_dummies(prices)
    era = hedged_returns.dropna()
    era_regimes = regimes.reindex(era.index)
    interaction = era_regimes["high_vol"] * era_regimes["bear"]
    X = pd.DataFrame({
        "high_vol": era_regimes["high_vol"],
        "bear": era_regimes["bear"],
        "high_vol_x_bear": interaction,
    })
    aligned = pd.concat([era.rename("y"), X], axis=1).dropna()
    fit = hac_regression(aligned["y"], aligned[X.columns], lags=hac_lags)
    n_bear_highvol = int(aligned["high_vol_x_bear"].sum())
    return CrashInteractionResult(
        label=label,
        n_bear_highvol_days=n_bear_highvol,
        n_total_days=len(aligned),
        interaction_coef=float(fit.params["high_vol_x_bear"]),
        interaction_p=float(fit.pvalues["high_vol_x_bear"]),
        baseline_coef=float(fit.params["const"]),
        baseline_p=float(fit.pvalues["const"]),
        era_start=aligned.index.min(),
        fit=fit,
    )


def tail_risk_profile(
    label: str,
    returns: pd.Series,
    confidence_levels: tuple[float, ...] = DEFAULT_CONFIDENCE_LEVELS,
    n_bootstrap: int = DEFAULT_N_BOOTSTRAP,
    seed: int = DEFAULT_SEED,
) -> TailRiskReport:
    """Generalizes Milestone 43's VaR/CVaR profile, with Milestone 51's own
    refinement (a bootstrap CI on the CVaR RATIO itself, resampled jointly
    with the Gaussian side from the same draw, not two separate intervals)
    built in from the start rather than added after the fact."""
    values = returns.dropna().values
    rng = np.random.default_rng(seed)
    mean, std = values.mean(), values.std()
    report = TailRiskReport(
        label=label, n=len(values), mean=float(mean), std=float(std),
        skew=float(stats.skew(values)), excess_kurtosis=float(stats.kurtosis(values)),
    )
    for conf in confidence_levels:
        e_var, e_cvar = empirical_var_cvar(values, conf)
        g_var, g_cvar = gaussian_var_cvar(mean, std, conf)
        n_tail = int(np.sum(values <= np.quantile(values, 1.0 - conf)))

        ratios = np.empty(n_bootstrap)
        n = len(values)
        for i in range(n_bootstrap):
            sample = rng.choice(values, size=n, replace=True)
            s_mean, s_std = sample.mean(), sample.std()
            _, se_cvar = empirical_var_cvar(sample, conf)
            _, sg_cvar = gaussian_var_cvar(s_mean, s_std, conf)
            ratios[i] = se_cvar / sg_cvar if sg_cvar != 0 else np.nan

        report.levels.append(TailRiskLevel(
            confidence=conf, empirical_var=e_var, gaussian_var=g_var,
            empirical_cvar=e_cvar, gaussian_cvar=g_cvar,
            cvar_ratio=e_cvar / g_cvar if g_cvar != 0 else float("nan"),
            cvar_ratio_ci_lo=float(np.nanpercentile(ratios, 5)),
            cvar_ratio_ci_hi=float(np.nanpercentile(ratios, 95)),
            n_tail_obs=n_tail,
        ))
    return report


def propagated_crash_stress(
    label: str,
    crash_result: CrashInteractionResult,
    prices: pd.DataFrame,
    duration_multipliers: tuple[float, ...] = DEFAULT_DURATION_MULTIPLIERS,
    n_sims: int = DEFAULT_N_SIMS,
    seed: int = 11,
) -> StressTable:
    """Generalizes Milestone 50's uncertainty-propagated crash-duration
    stress simulation: draws the regression's coefficients from their own
    fitted HAC sampling distribution once per simulated 'world' (not just
    bootstrapping residual noise around a fixed point estimate), for a
    signal whose crash-regime interaction already tested significant.
    Call this only when crash_result.significant is True -- see
    SignalRiskReport.summary() for what this toolkit does instead when
    it isn't."""
    fit = crash_result.fit
    mean_params = fit.params[list(COEF_NAMES)].values
    cov_params = fit.cov_params().loc[list(COEF_NAMES), list(COEF_NAMES)].values
    residuals = fit.resid.values
    daily_drift_point = float(mean_params.sum())
    daily_drift_se = float(np.sqrt(np.ones(4) @ cov_params @ np.ones(4)))

    regimes = build_regime_dummies(prices)
    worst_len = historical_worst_episode_length(regimes, str(crash_result.era_start.date()))

    table = StressTable(
        label=label, worst_historical_episode_days=worst_len,
        daily_drift_point=daily_drift_point,
        daily_drift_90pct_ci=(
            daily_drift_point - 1.645 * daily_drift_se,
            daily_drift_point + 1.645 * daily_drift_se,
        ),
    )
    for mult in duration_multipliers:
        n_days = max(worst_len * int(mult), 1)
        rng_point = np.random.default_rng(seed)
        rng_prop = np.random.default_rng(seed + 1)
        cum_point = simulate_episode(rng_point, daily_drift_point, residuals, n_days, n_sims)
        cum_prop, _ = simulate_episode_with_parameter_uncertainty(
            rng_prop, mean_params, cov_params, residuals, n_days, n_sims,
        )
        table.rows.append(StressRow(
            duration_multiplier=mult, n_days=n_days,
            point_mean=float(cum_point.mean()), propagated_mean=float(cum_prop.mean()),
            point_90pct_interval=(float(np.percentile(cum_point, 5)), float(np.percentile(cum_point, 95))),
            propagated_90pct_interval=(float(np.percentile(cum_prop, 5)), float(np.percentile(cum_prop, 95))),
        ))
    return table


def full_report(
    label: str,
    hedged_returns: pd.Series,
    prices: pd.DataFrame,
    hac_lags: int = DEFAULT_HAC_LAGS,
) -> SignalRiskReport:
    """Runs all three checks in sequence, exactly as every milestone from
    46 onward has applied them: crash-regime interaction first, tail-risk
    profile always (it answers a different question and is never
    conditional on the first result, per Milestone 53's own finding), and
    a propagated stress scenario ONLY if the interaction is significant
    enough to be worth stress-testing in the first place."""
    crash = crash_regime_interaction(label, hedged_returns, prices, hac_lags=hac_lags)
    tail = tail_risk_profile(label, hedged_returns)
    stress = propagated_crash_stress(label, crash, prices) if crash.significant else None
    return SignalRiskReport(label=label, crash_interaction=crash, tail_risk=tail, stress=stress)
