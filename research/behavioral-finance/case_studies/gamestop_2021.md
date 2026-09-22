# Case study: GameStop and the "meme stock" squeeze (January 2021)

## Why this case is different from the others

Every other case in this folder is a story about a sophisticated institution's model
breaking because of correlated behavior *elsewhere* in the market (LTCM, the 2008 crisis)
or its own overconfidence (Amaranth), or sophisticated funds herding into the same factor
bet as each other (Quant Quake). GameStop runs the other direction: a large, coordinated,
retail-driven move that overwhelmed sophisticated institutional positioning, and did so
using tools — options-market mechanics, social-media coordination, gamified trading
apps — that didn't meaningfully exist the last time retail herding moved a market this
much. It belongs in this project because it's strong evidence that "irrational" market
behavior is not only a tail risk that hits leveraged institutions from the outside; it can
also be a coordinated force retail investors generate and that institutions end up on the
wrong side of.

## What happened

Through 2020, several large hedge funds, most prominently Melvin Capital, held large short
positions in GameStop (GME), a struggling brick-and-mortar video-game retailer, on a
conventional fundamentals view that the business was in structural decline. GameStop had
one of the highest short-interest-to-float ratios of any large US-listed stock at the
time — itself a signal, to anyone watching, of just how consensus that bearish view was
among institutional investors.

Starting in mid-to-late January 2021, a large, coordinated wave of retail buying —
organized largely on the Reddit forum r/wallstreetbets and amplified across social media —
pushed GameStop's share price up by roughly an order of magnitude in a few weeks, with the
most extreme single-day moves in the last week of January 2021. Two mechanisms compounded
the pure buying pressure:

- **A short squeeze**: as the price rose, short sellers (Melvin Capital and others) faced
  mounting margin calls and were forced to buy shares to close out losing short positions,
  which pushed the price up further, forcing more covering — a self-reinforcing spiral in
  the opposite direction from the forced-deleveraging spirals in the LTCM and Quant Quake
  cases, but the same underlying mechanic (forced trading by leveraged participants
  amplifying, rather than correcting, a price move).
- **A gamma squeeze**: heavy retail buying of short-dated call options forced the options
  market-makers who sold those calls to buy the underlying stock to stay hedged (delta
  hedging); as the stock rose, the hedging requirement increased further, forcing more
  buying — an amplifying feedback loop that runs through market structure rather than
  through anyone's fundamental view of the company.

Melvin Capital's short position lost the fund a very large share of its capital in January
2021 (widely reported in contemporaneous press as over 50% for the month), and the fund
received a $2.75 billion capital injection from Citadel and Point72 on January 25, 2021 to
shore up its position — a smaller-scale echo of the LTCM bank consortium bailout, except
here the rescued firm was on the losing side of a squeeze driven by dispersed retail
traders rather than a correlated institutional panic. Several retail brokerages, most
visibly Robinhood, restricted buying (not selling) of GameStop and several other
similarly-targeted "meme stocks" on January 28, 2021, citing clearinghouse (NSCC) deposit
requirements driven by the extreme volatility — a decision that triggered public backlash,
allegations of favoring institutional interests, and US congressional hearings in
February 2021.

## The behavioral mechanisms

Several distinct, well-documented behavioral effects compounded here, not just one:

- **Herding / social proof at internet scale.** Retail investors coordinating visibly on a
  public forum is a much faster, more observable version of the herding that happens more
  opaquely among institutions (compare the Quant Quake, where funds herded into similar
  factor exposures without any of them intending to coordinate).
- **Attention-driven trading.** Barber & Odean's research on individual investors
  (notably "All That Glitters: The Effect of Attention and News on the Buying Behavior of
  Individual and Institutional Investors", *Review of Financial Studies*, 2008) documents
  that retail investors disproportionately buy stocks that have recently grabbed their
  attention (extreme returns, heavy news/social coverage) rather than researching broadly
  across the market first — a mechanism directly visible in how GameStop, and a rotating
  cast of other "meme stocks," became targets.
- **Gamification.** Commission-free, mobile-first trading apps (Robinhood chief among them)
  have been widely discussed as encouraging more frequent, more attention- and
  sentiment-driven trading than a traditional brokerage interface, an effect closer to
  consumer app design than to classical market microstructure.
- **A genuine collective-action, not-purely-irrational core.** Unlike a pure panic, part of
  the GameStop move had an internally coherent (if unusual) logic once the squeeze
  mechanics were visible: buying into a stock with extreme short interest and a real
  prospect of forcing short covering is a recognizable, if very high-risk, trading
  strategy, not simple noise. The "irrationality" here is less "investors panicking" and
  more "a large, fast, socially-coordinated repricing that overwhelmed a positioning
  imbalance institutional models hadn't priced as a real risk" — a useful reminder that
  behavioral finance isn't only about mistakes individual investors make, it's also about
  aggregate dynamics that no individual participant's model accounts for.

## Sources / further reading

Congressional testimony and the US House Financial Services Committee hearing "Game
Stopped? Who Wins and Loses When Short Sellers, Social Media, and Retail Investors Collide"
(February 18, 2021) is the primary public record of the Melvin Capital, Citadel/Point72,
and Robinhood details. Brad Barber & Terrance Odean's attention-driven-trading research
(cited above) predates GameStop by over a decade but is the standard academic framework
applied to it after the fact.
