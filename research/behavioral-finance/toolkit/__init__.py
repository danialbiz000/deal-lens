"""
Behavioral Signal & Stress-Risk Analytics toolkit.

The statistical core of this project's 53 research milestones, extracted
from signal-specific investigation scripts into a signal-agnostic library.
Point it at any out-of-sample-hedged daily return series and a price panel
for regime construction, and it runs the same three checks this project
built and repeatedly refined on its own three signals (momentum,
turn-of-month, and in passing low-volatility/MAX):

1. crash_regime_interaction -- does this signal's return carry the
   Bear+HighVol crash-regime interaction momentum showed (Milestones
   16-18, 20, 46-48)?
2. tail_risk_profile -- does the empirical distribution understate tail
   risk relative to a Gaussian fit, the way Q1's simulation warned
   (Milestone 43), including a bootstrap CI on the CVaR ratio ITSELF, not
   just each side separately (the refinement Milestone 51 found necessary)?
3. propagated_crash_stress -- if the signal shows a crash-regime
   interaction, what does a stress scenario look like once the fitted
   coefficient's own estimation uncertainty is propagated through, not
   just residual noise (the discipline Milestone 50 built)?

See toolkit/README.md for the full API and toolkit/demo_52w_high_asx.py
for a worked example on a signal this project had never run the combined
pipeline against before.
"""
from .report import (
    CrashInteractionResult,
    SignalRiskReport,
    StressTable,
    TailRiskReport,
    crash_regime_interaction,
    full_report,
    propagated_crash_stress,
    tail_risk_profile,
)

__all__ = [
    "CrashInteractionResult",
    "TailRiskReport",
    "StressTable",
    "SignalRiskReport",
    "crash_regime_interaction",
    "tail_risk_profile",
    "propagated_crash_stress",
    "full_report",
]
