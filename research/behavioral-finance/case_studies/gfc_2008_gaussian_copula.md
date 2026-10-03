# Case study: the 2008 financial crisis and the Gaussian copula

## What happened

The 2007-2008 global financial crisis is usually told as a story about subprime mortgages,
but the mechanism that turned a real-but-containable housing problem into a systemic
banking crisis was a **pricing model failure that mirrors this project's Q1 risk
simulation almost exactly**: a correlation assumption, calibrated on a short and unusually
benign historical window, that broke catastrophically once the underlying risk stopped
behaving independently.

Wall Street banks packaged large pools of individual mortgages into mortgage-backed
securities and then into collateralized debt obligations (CDOs), tranched by seniority.
The value of a senior (AAA-rated) tranche depends critically on how correlated the
underlying mortgage defaults are with each other: if defaults are close to independent
(a homeowner in Ohio defaulting tells you little about one in Nevada), a senior tranche is
very safe, because it would take an enormous number of simultaneous, unrelated defaults to
exhaust the more junior tranches protecting it. If defaults are highly correlated (a
national housing downturn hits every region at once), that protection evaporates.

**The model used to price this correlation risk across the industry was the Gaussian
copula**, popularized by David X. Li in a widely-cited 2000 paper ("On Default Correlation:
A Copula Function Approach"). It let banks reduce the hard problem of modeling correlated
default risk across thousands of individual mortgages to a single correlation parameter,
estimated from a short history of historical default and credit-spread data — a history
drawn almost entirely from a multi-decade US housing boom during which nationwide home
prices had never fallen. The model was not "wrong" mathematically; it was, structurally,
exactly the same mistake as a calm-regime-calibrated Gaussian VaR model in this project's
`risk_simulation/fat_tails_vs_normal.py`: it estimated a correlation parameter from a
period in which the correlation-raising regime (a national price decline) had never
occurred, and therefore could not have seen how fast that correlation could rise once it
did.

When US home prices began falling nationally in 2006-2007 — a regime the calibration
window had essentially no examples of — mortgage defaults stopped being (relatively)
independent events and started moving together, for the same underlying reason (falling
prices push more borrowers underwater and into default simultaneously, in every region at
once). Senior tranches that the Gaussian copula had priced as extremely safe took losses
far larger and far faster than the model implied, and because these instruments were held,
directly or via derivatives referencing them, throughout the banking system, the losses
were not contained to specialist mortgage investors — they hit the balance sheets of
systemically important banks and insurers (Bear Stearns, March 2008; Lehman Brothers,
September 15, 2008 bankruptcy; AIG's ~$182 billion federal rescue, driven largely by credit
default swaps written against these same instruments) more or less simultaneously.

## The behavioral and institutional layer on top of the model failure

The Gaussian copula's correlation-blindness explains the mechanical trigger, but two
behavioral/institutional dynamics explain why so much of the system was exposed to it at
once:

- **Herding into a model everyone knew was imperfect.** Li's own paper and subsequent
  commentary noted the model's limitations; widespread industry adoption happened anyway,
  in large part because it was tractable, produced a single clean number rating agencies
  and risk desks could all agree on, and — critically — using it let banks originate and
  sell more structured product, generating fees, as long as competitors were using the same
  approach. Deviating from the consensus model was a career and franchise risk even for
  desks that suspected it understated tail risk — a rational *individual* response
  (career/business risk) to an *irrational collective* outcome (everyone underpricing the
  same tail).
- **A run dynamic once trust broke.** Once senior-tranche losses started, nobody could
  reliably tell which institutions were exposed to how much bad paper (opacity plus
  correlated exposure), so short-term lenders and counterparties pulled back from
  *everyone*, not just the actually-insolvent — a rational individual response to
  uncertainty that collectively froze interbank lending (most visibly around the Reserve
  Primary Fund "breaking the buck" and the broader money-market panic in September 2008).
  This is the same flight-to-quality/correlated-withdrawal mechanism as LTCM in 1998
  (`ltcm_1998.md`), at a much larger, systemic scale.

## Why this belongs alongside LTCM and Amaranth in this project

All three cases share the same underlying structure this project's Q1 simulation makes
explicit: a model that is locally reasonable, calibrated on real historical data, and
wrong specifically about how correlation behaves in the regime that matters most — the one
that shows up rarely in the calibration window but does the damage. The 2008 crisis is the
largest-scale version of that pattern in modern financial history, and the one with the
most direct mechanical parallel to `risk_simulation/fat_tails_vs_normal.py`: a single
correlation parameter, fit on calm data, silently wrong about the tail.

## Sources / further reading

David X. Li, "On Default Correlation: A Copula Function Approach", *Journal of Fixed
Income*, 2000. Felix Salmon, "Recipe for Disaster: The Formula That Killed Wall Street",
*Wired*, February 2009, is the standard accessible account connecting the model
specifically to the crisis. Michael Lewis, *The Big Short* (2010), covers the broader
institutional and behavioral dynamics of the housing-bubble years.
