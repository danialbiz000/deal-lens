# Case studies: funds built explicitly around behavioral biases

The other side of this research question: firms that treat the "irrational" side of the
market not as noise to be modeled away, but as the actual source of their edge.

## Fuller & Thaler Asset Management

Founded in 1993 by Richard Thaler — a founding figure of behavioral economics, awarded the
2017 Nobel Memorial Prize in Economic Sciences for work on how limited rationality,
social preferences, and lack of self-control affect economic decisions — together with
Russell Fuller. The firm's stated investment philosophy is built directly on Kahneman &
Tversky-style behavioral finance: markets are inefficient specifically *because* investors
are human, and those inefficiencies are systematic enough to be identified and exploited
rather than being pure noise.

**The specific mechanism they've built a business on** is closely related to this
project's `signals/reversal.py` and `signals/momentum.py`: systematic **under-reaction to
earnings surprises**. The academic finding (post-earnings-announcement drift, or "PEAD",
first documented by Ball & Brown in 1968 and refined by many since) is that stock prices
keep drifting in the direction of an earnings surprise for weeks to months after the
announcement, rather than jumping immediately to the new fair value — consistent with
analysts and investors anchoring on their pre-announcement estimates and updating too
slowly. Fuller & Thaler's flagship retail vehicle, the fund long known as "Undiscovered
Managers Behavioral Value" (ticker UBVLX; the strategy has also traded under other fund
wrappers over the years as sub-advisory relationships changed), is built around
systematically buying into that underreaction.

## LSV Asset Management

Founded in 1994 by three academic economists — Josef Lakonishok, Andrei Shleifer, and
Robert Vishny — whose own published research (Lakonishok, Shleifer & Vishny,
"Contrarian Investment, Extrapolation, and Risk", *Journal of Finance* 49(5), 1994,
pp. 1541-1578) argued that
much of the historical outperformance of value stocks over "glamour" (growth) stocks is
best explained by investors systematically **extrapolating recent growth too far into the
future** — chasing exciting recent growth stories and shunning boring, currently
out-of-favor companies — rather than by value stocks simply being riskier, as a strict
risk-based efficient-markets account would require. LSV built a long-running institutional
asset management business directly implementing that thesis: systematic, quantitative
value and contrarian strategies, explicitly informed by the behavioral-extrapolation
explanation for the value premium rather than a pure risk-compensation story.

## AQR Capital Management

Founded in 1998 by Cliff Asness together with several colleagues from Goldman Sachs
Asset Management's quantitative research group. Asness's University of Chicago PhD
dissertation, completed under advisors including Eugene Fama, was on momentum in stock
returns — a notable detail given Fama is himself closely associated with the efficient
markets hypothesis that momentum's persistence is often read as challenging. AQR is not a
"pure" behavioral shop the way Fuller & Thaler is —
it explicitly frames some of its factor premia (value, quality) as at least partly
risk-based — but its research and public writing repeatedly draw on behavioral
explanations for specific factors, most clearly **momentum**, where the standard academic
account (including papers co-authored by AQR-affiliated researchers) attributes much of
the effect to gradual, biased information diffusion and investor underreaction — the same
mechanism this project's `signals/momentum.py` targets — rather than to a coherent
risk-based story. AQR is useful in this project as the "moderate" case: a firm that treats
behavioral anomalies as one input among several (alongside risk-based and structural
explanations), run with heavy quantitative discipline and explicit awareness of factor
crowding risk (the same crowding dynamic behind the 2007 Quant Quake above) — a useful
contrast to Fuller & Thaler's more purely behavioral framing.

## The common thread, and why it matters for `../FRAMEWORK.md`

All three firms bet that specific, *named* cognitive biases (anchoring, extrapolation
bias, underreaction) produce **persistent, not merely historical**, mispricing —
persistent enough to build a decades-long business on, net of costs and net of the fact
that the anomaly is now public knowledge (a real risk: see `../README.md`,
"Explicit limitations", on performance decay after publication). That is the working
assumption behind the composite score in `../signals/composite.py` and the investment
framework in `../FRAMEWORK.md`: not "markets are irrational" as a vague slogan, but
specific, citable biases, each with a specific, testable, and falsifiable market
signature.

## Sources / further reading

Josef Lakonishok, Andrei Shleifer & Robert Vishny, "Contrarian Investment, Extrapolation,
and Risk", *Journal of Financial Economics* / *Journal of Finance*, 1994. Richard Thaler,
*Misbehaving: The Making of Behavioral Economics* (2015), covers the intellectual history
connecting Kahneman-Tversky psychology to Thaler's later asset-management work. Firm
websites (fullerthaler.com, lsvasset.com, aqr.com) describe current strategy framing in
their own words.
