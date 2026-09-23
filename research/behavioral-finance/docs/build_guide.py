# -*- coding: utf-8 -*-
"""Builds the Behavioral Finance Research Project guide PDF.

A plain-language companion to the code and README/FRAMEWORK/case_studies in
this repo -- explains every concept with an example before using it, narrates
the project's milestones and decisions, and states the real vs. not-yet-
validated results honestly. Regenerate after each milestone that changes the
project's findings (see README.md's own milestone log for what's current).

Usage: pip install reportlab && python docs/build_guide.py
Output: docs/behavioral_finance_guide.pdf
"""
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, NextPageTemplate, FrameBreak
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.pdfgen import canvas as canvas_mod
import os

OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "behavioral_finance_guide.pdf")

PAGE_W, PAGE_H = LETTER
MARGIN = 0.9 * inch

styles = getSampleStyleSheet()

# ---- custom styles ----
styles.add(ParagraphStyle(name="CoverTitle", fontName="Helvetica-Bold", fontSize=27,
                           leading=32, alignment=TA_CENTER, textColor=colors.HexColor("#12233d"),
                           spaceAfter=14))
styles.add(ParagraphStyle(name="CoverSubtitle", fontName="Helvetica", fontSize=14,
                           leading=19, alignment=TA_CENTER, textColor=colors.HexColor("#4a5a72"),
                           spaceAfter=6))
styles.add(ParagraphStyle(name="CoverMeta", fontName="Helvetica", fontSize=10.5,
                           leading=15, alignment=TA_CENTER, textColor=colors.HexColor("#6b7a8f")))

styles.add(ParagraphStyle(name="PartTitle", fontName="Helvetica-Bold", fontSize=20,
                           leading=24, spaceBefore=6, spaceAfter=16,
                           textColor=colors.HexColor("#12233d"),
                           keepWithNext=True))
styles.add(ParagraphStyle(name="H1", fontName="Helvetica-Bold", fontSize=15,
                           leading=19, spaceBefore=18, spaceAfter=8,
                           textColor=colors.HexColor("#173a63"), keepWithNext=True))
styles.add(ParagraphStyle(name="H2", fontName="Helvetica-Bold", fontSize=12.3,
                           leading=16, spaceBefore=12, spaceAfter=6,
                           textColor=colors.HexColor("#2b5282"), keepWithNext=True))
styles.add(ParagraphStyle(name="Body", fontName="Helvetica", fontSize=10.1,
                           leading=14.6, alignment=TA_JUSTIFY, spaceAfter=8,
                           textColor=colors.HexColor("#1c1c1c")))
styles.add(ParagraphStyle(name="BodyItalic", parent=styles["Body"], fontName="Helvetica-Oblique"))
styles.add(ParagraphStyle(name="MyBullet", parent=styles["Body"], leftIndent=16,
                           bulletIndent=4, spaceAfter=5))
styles.add(ParagraphStyle(name="Caption", fontName="Helvetica-Oblique", fontSize=8.7,
                           leading=11.5, textColor=colors.HexColor("#5a6472"), spaceAfter=10))
styles.add(ParagraphStyle(name="TOCHeading", parent=styles["H1"], spaceBefore=0))
styles.add(ParagraphStyle(name="TOC1", fontName="Helvetica-Bold", fontSize=10.5,
                           leading=16, textColor=colors.HexColor("#173a63")))
styles.add(ParagraphStyle(name="TOC2", fontName="Helvetica", fontSize=9.7,
                           leading=14, leftIndent=14, textColor=colors.HexColor("#333")))
styles.add(ParagraphStyle(name="GlossTerm", fontName="Helvetica-Bold", fontSize=10.1,
                           leading=14.6, textColor=colors.HexColor("#173a63"), spaceBefore=6))

TABLE_HEAD_BG = colors.HexColor("#173a63")
TABLE_ROW_BG = colors.HexColor("#eef2f7")
DECISION_BG = colors.HexColor("#fbf3e3")
DECISION_BORDER = colors.HexColor("#c9922c")
FACT_BG = colors.HexColor("#eaf1fb")
FACT_BORDER = colors.HexColor("#3f6ea5")

story = []
toc = TableOfContents()
toc.levelStyles = [styles["TOC1"], styles["TOC2"]]


def h1(text):
    story.append(Paragraph(text, styles["H1"]))


def h2(text):
    story.append(Paragraph(text, styles["H2"]))


def part(text):
    story.append(Paragraph(text, styles["PartTitle"]))


def p(text, style="Body"):
    story.append(Paragraph(text, styles[style]))


def bullets(items):
    for it in items:
        story.append(Paragraph("&bull;&nbsp;&nbsp;" + it, styles["MyBullet"]))


def spacer(h=8):
    story.append(Spacer(1, h))


def box(text, kind="decision", title=None):
    bg = DECISION_BG if kind == "decision" else FACT_BG
    border = DECISION_BORDER if kind == "decision" else FACT_BORDER
    default_title = "DECISION &amp; RATIONALE" if kind == "decision" else "KEY FACT"
    label = title or default_title
    inner_style = ParagraphStyle(name="BoxBody", parent=styles["Body"], spaceAfter=0)
    label_style = ParagraphStyle(name="BoxLabel", fontName="Helvetica-Bold", fontSize=8.6,
                                  leading=11, textColor=border, spaceAfter=4)
    content = [Paragraph(label, label_style), Paragraph(text, inner_style)]
    t = Table([[content]], colWidths=[PAGE_W - 2 * MARGIN])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 1, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(Spacer(1, 4))
    story.append(t)
    story.append(Spacer(1, 8))


def data_table(header, rows, col_widths=None, small=False):
    data = [header] + rows
    t = Table(data, colWidths=col_widths, repeatRows=1)
    fs = 8.3 if small else 9
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEAD_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), fs),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, TABLE_ROW_BG]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c3ccd6")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    t.setStyle(TableStyle(style))
    story.append(t)
    spacer(10)


def toc_entry(text, level, key):
    """No-op: TOC entries are populated automatically by GuideDocTemplate.
    afterFlowable watching for PartTitle/H1 styled paragraphs (see bottom of
    this script). Kept as a call site marker so section boundaries stay
    readable in this script without a second source of truth for headings."""
    return


# ============================================================ COVER PAGE
story.append(Spacer(1, 1.6 * inch))
story.append(Paragraph("Behavioral Finance Research Project", styles["CoverTitle"]))
story.append(Paragraph("Why Markets Aren't Rational, and What You Can Do About It",
                        styles["CoverSubtitle"]))
spacer(28)
story.append(Paragraph(
    "A project guide covering research design, methodology, five real-world case "
    "studies, the psychology behind each one, the milestone-by-milestone decisions "
    "made while building it, the real (not simulated) results obtained, and how "
    "the findings translate into practice.",
    ParagraphStyle(name="CoverDesc", parent=styles["Body"], alignment=TA_CENTER,
                    fontSize=11, leading=16, textColor=colors.HexColor("#33465f"))
))
spacer(60)
story.append(Paragraph("Prepared as a companion guide to the code repository "
                        "<i>research/behavioral-finance/</i>", styles["CoverMeta"]))
story.append(Paragraph("Written in English for readers without a quant-finance background; "
                        "every concept is introduced with a plain-language example before "
                        "it is used.", styles["CoverMeta"]))
story.append(PageBreak())

# ============================================================ TOC PAGE
story.append(Paragraph("Contents", styles["TOCHeading"]))
spacer(6)
story.append(toc)
story.append(PageBreak())

# ============================================================ EXECUTIVE SUMMARY
toc_entry("Executive Summary", 0, "exec")
h1("Executive Summary")
p("Financial theory has long assumed that markets are, to a first approximation, "
  "rational: prices reflect available information, and systematic mispricing should "
  "be rare and quickly corrected by sophisticated investors. This project tests that "
  "assumption from two directions at once, using real code and, wherever technically "
  "possible, real data rather than narrative alone.")
p("<b>Direction one (diagnosis):</b> why do sophisticated, model-driven institutions "
  "sometimes fail catastrophically, precisely because their models assumed rational, "
  "well-behaved markets? Long-Term Capital Management (1998), the &quot;Quant Quake&quot; "
  "(2007), Amaranth Advisors (2006), and the 2008 financial crisis are examined as "
  "cases where a locally reasonable model broke because it could not see how fast "
  "correlation and panic move together once other market participants stop behaving "
  "independently.")
p("<b>Direction two (exploitation):</b> can well-documented behavioral biases &mdash; "
  "anchoring, underreaction, overreaction &mdash; be turned into a measurable, "
  "tradable edge, the way real firms such as Fuller &amp; Thaler Asset Management and "
  "LSV Asset Management have built businesses on doing? This project builds a signal "
  "library and backtest engine, and runs it against a real 21-year daily price "
  "history for 48 India-listed companies (the only market data source technically "
  "reachable from the environment this project was built in &mdash; see Part V for "
  "why that constraint mattered and how it was worked around).")
p("The honest headline result from that empirical run: a blended "
  "&quot;behavioral score&quot; combining three signals looked like a roughly "
  "break-even strategy &mdash; and that blend was hiding two very different stories. "
  "One component signal (anchoring to the 52-week high) lost money persistently and "
  "dramatically; another (short-term reversal) at first looked like a real, positive, "
  "cost-adjusted edge. The project's central methodological lesson &mdash; never trust a "
  "blended score without checking what is inside it &mdash; came directly out of this "
  "finding, not from a textbook. (Chasing <i>why</i> the losing component lost money "
  "turned into the project's longest, most instructive thread &mdash; Part V walks "
  "through five rounds of increasingly rigorous testing. The losing signal's cause "
  "turned out simpler, and more humbling, than any of the behavioral explanations first "
  "considered &mdash; and the same rigor, once finally pointed at the &quot;winning&quot; "
  "signal too, retracted it and surfaced a different, genuine finding instead.)")
p("The guide that follows explains every concept used (behavioral and quantitative) "
  "in plain language with real examples, walks through all five case studies in "
  "detail, narrates the project's milestones and the reasoning behind each decision, "
  "and translates the findings into an investment framework, a risk-management "
  "playbook, and a business idea.")
spacer(4)

# ============================================================ PART I
story.append(NextPageTemplate("normal"))
story.append(PageBreak())
toc_entry("Part I &mdash; Why This Project Exists", 0, "part1")
part("Part I &mdash; Why This Project Exists")

h1("1.1  The theory markets are supposed to follow")
p("The Efficient Market Hypothesis (EMH), the dominant framework in academic finance "
  "since the 1960s-70s, holds that asset prices reflect all available information at "
  "essentially every moment. Its practical implication is stark: if EMH holds strictly, "
  "no strategy should reliably beat a passive index over time, because any predictable "
  "pattern would immediately be traded away by rational, profit-seeking investors the "
  "moment it appeared.")
p("EMH is not a strawman invented for this project to knock down &mdash; it is a "
  "genuinely useful default. Most of the time, for most large, liquid securities, "
  "prices really do incorporate public information quickly. The interesting question "
  "is not &quot;is EMH ever true&quot; (it often is, approximately) but "
  "&quot;when and how does it fail, and can those failures be anticipated, measured, "
  "or profited from?&quot;")

h1("1.2  Two stories that motivate the whole project")
box(
    "In 1998, a hedge fund whose partners included two Nobel-laureate economists "
    "(Myron Scholes and Robert Merton, co-creators of the option-pricing theory "
    "taught in every finance program) lost about 90% of its capital in roughly six "
    "weeks, despite running trades its own models considered close to riskless. "
    "In January 2021, a struggling video-game retailer's stock rose by roughly an "
    "order of magnitude in a few weeks, not because of any change in the company's "
    "prospects, but because a large, loosely coordinated group of retail traders on "
    "a Reddit forum decided to buy it &mdash; and forced some of the most "
    "sophisticated short-selling hedge funds in the world to take large losses "
    "covering their bets. Both episodes are covered in full in Part IV.",
    kind="fact", title="TWO EPISODES THAT FRAME THE PROJECT"
)
p("These two stories point in opposite directions &mdash; one is about a "
  "sophisticated model failing, the other about an unsophisticated crowd winning "
  "&mdash; but they share a single underlying fact: humans, not equations, decide "
  "what a price is. A model can be mathematically elegant and still miss the fact "
  "that, under stress, people (whether panicking institutional traders or excited "
  "retail traders) start behaving in a correlated, non-independent way that no "
  "amount of historical calibration prepared it for.")

h1("1.3  The project's two-track design")
p("Two concrete, falsifiable questions structure everything that follows:")
bullets([
    "<b>Q1 (diagnosis).</b> Can the mechanism by which rational-market risk models "
    "fail under stress be shown mechanically, with real numbers, rather than just "
    "asserted narratively?",
    "<b>Q2 (exploitation).</b> Do specific, named behavioral biases produce a "
    "real, measurable, cost-adjusted return premium when turned into a systematic "
    "trading signal, over a long sample, on real market data?",
])
box(
    "The project could have been written as a pure literature review &mdash; "
    "summarizing what Kahneman, Tversky, Thaler, and others found, and describing "
    "LTCM and GameStop narratively. That would have been faster, but it would not "
    "have produced anything falsifiable: a narrative account can always be told to "
    "confirm whatever conclusion the writer wanted. The decision here was to require "
    "runnable code and, wherever technically possible, real executed numbers for "
    "every claim &mdash; even when (as happened repeatedly, see Part V) the "
    "environment made that harder than expected. A claim in this project is either "
    "backed by a number that was actually computed, or it is explicitly flagged as "
    "not yet validated. Nothing in between.",
)

spacer(6)
# MARKER_END_PART1

# ============================================================ PART II
story.append(PageBreak())
toc_entry("Part II &mdash; Core Behavioral Concepts, Explained Before They're Used", 0, "part2")
part("Part II &mdash; Core Behavioral Concepts, Explained Before They're Used")
p("Every case study and every trading signal in this project rests on one of the "
  "concepts below. Each is introduced with an everyday example first, then the "
  "specific market mechanism it produces, so that later sections can use the term "
  "without re-explaining it.")

h1("2.1  Anchoring")
p("<b>Everyday example:</b> if a car salesperson opens negotiation at $30,000, most "
  "buyers end up settling closer to that number than if the same car had been "
  "opened at $25,000 &mdash; even though the opening number carries no real "
  "information about the car's actual worth. The first number seen becomes a "
  "psychological reference point (an &quot;anchor&quot;) that subsequent judgments "
  "are adjusted from, insufficiently.")
p("<b>Market mechanism:</b> investors use a stock's 52-week high as exactly this "
  "kind of reference point. Even when good news arrives that should push the price "
  "well past the old high, many investors hesitate to buy through a level they've "
  "mentally anchored on as &quot;expensive,&quot; so the price drifts up slowly "
  "instead of jumping &mdash; the mechanism behind the 52-week-high signal used in "
  "this project's Q2 signal library (Part III) and central to the George &amp; "
  "Hwang (2004) academic finding it's based on.")

h1("2.2  Herding (Social Proof)")
p("<b>Everyday example:</b> seeing a long line outside one restaurant and an empty "
  "one next door, most passersby join the line &mdash; not because they have "
  "independently evaluated either restaurant's food, but because a crowd is itself "
  "treated as evidence of quality. This is useful most of the time (crowds often do "
  "know something) and can be badly wrong when the crowd itself started for an "
  "unrelated reason.")
p("<b>Market mechanism:</b> in a crisis, investors and institutions sell what "
  "everyone else is selling, and buy what's flowing toward safety (a "
  "&quot;flight to quality&quot;), regardless of the specific fundamental merits of "
  "what they're selling or buying. This is the central mechanism in the LTCM case "
  "(Part IV): LTCM's own trades were not herding, but the rest of the market's "
  "correlated flight to safety broke the correlation assumptions LTCM's model "
  "depended on.")

h1("2.3  Overconfidence and Illusion of Control")
p("<b>Everyday example:</b> most drivers rate themselves as &quot;above average&quot; "
  "&mdash; a statistical impossibility for a majority to be true, and a "
  "well-replicated psychological finding. A string of good outcomes (safe drives, "
  "in this analogy) is easy to misread as evidence of skill rather than of "
  "favorable conditions that happened to hold.")
p("<b>Market mechanism:</b> a trader with a strong track record under one market "
  "regime can mistake that track record for proof their model handles all "
  "regimes, and size positions accordingly. This is the central mechanism in the "
  "Amaranth Advisors case (Part IV): trader Brian Hunter's prior profitable "
  "natural-gas positions preceded a concentrated bet sized well beyond what the "
  "fund could survive being wrong about.")

h1("2.4  Underreaction and Overreaction")
p("<b>Everyday example:</b> told a piece of surprising news, some people barely "
  "update their prior opinion at all (underreaction &mdash; &quot;I'll believe it "
  "when I see more evidence&quot;), while others swing to the opposite extreme "
  "immediately (overreaction &mdash; &quot;this changes everything&quot;). Both are "
  "documented, opposite failures of the same rational-updating standard (Bayesian "
  "updating: revising a belief by exactly as much as new evidence warrants, no "
  "more, no less).")
p("<b>Market mechanism, underreaction:</b> after a company reports a surprising "
  "earnings beat, its stock price often keeps drifting upward for weeks afterward "
  "instead of jumping immediately to the new fair value &mdash; a well-documented "
  "anomaly called post-earnings-announcement drift (PEAD), because analysts and "
  "investors update their models too slowly. This underreaction is also the "
  "mechanism behind price <i>momentum</i> more generally: information diffuses "
  "slowly, so a trend already underway tends to continue.")
p("<b>Market mechanism, overreaction:</b> a sharp, sudden price move (a panic sale "
  "or a euphoric rally) often partially reverses over the following weeks as the "
  "overreaction unwinds &mdash; the mechanism behind the short-term "
  "<i>reversal</i> signal used in this project, and, as it turned out, the single "
  "signal that actually worked in the real backtest (Part V).")

h1("2.5  Extrapolation Bias")
p("<b>Everyday example:</b> a company that has grown fast for three years straight "
  "is often assumed, informally, to keep growing at a similar pace &mdash; even "
  "though few businesses sustain any given growth rate indefinitely. People "
  "extrapolate recent trends further into the future than the trends themselves "
  "justify.")
p("<b>Market mechanism:</b> investors chase exciting recent growth stories "
  "(&quot;glamour&quot; stocks) and shun boring, currently out-of-favor companies, "
  "bidding growth stocks up beyond what their fundamentals justify and value stocks "
  "down below theirs. Lakonishok, Shleifer &amp; Vishny's 1994 paper (the founding "
  "research behind LSV Asset Management, Part IV) argued this extrapolation bias, "
  "not extra risk, explains much of the historical outperformance of value stocks.")

h1("2.6  Attention and Availability Bias")
p("<b>Everyday example:</b> people tend to overestimate the probability of dying in "
  "a plane crash relative to a car crash, because plane crashes are rare but "
  "vivid and heavily covered by media, so examples come to mind (are "
  "&quot;available&quot;) more easily than the much more common, less-covered car "
  "crash.")
p("<b>Market mechanism:</b> retail investors disproportionately buy stocks that "
  "have recently grabbed their attention &mdash; extreme returns, heavy news or "
  "social-media coverage &mdash; rather than researching broadly across the market "
  "first (Barber &amp; Odean, 2008). This is the central mechanism behind the "
  "GameStop episode (Part IV): a stock became a coordinated retail target largely "
  "because it was already attention-grabbing, not because of a broad, independent "
  "fundamental re-evaluation by thousands of separate investors.")

h1("2.7  Crowding: Herding at Institutional Scale")
p("<b>Everyday example:</b> if every restaurant critic in a city independently "
  "decides &quot;fusion cuisine is the next big trend&quot; and reviews "
  "accordingly, the city can end up with far more fusion restaurants than genuine "
  "demand supports &mdash; not because any critic copied another, but because they "
  "were all reasoning from similar assumptions and similar data.")
p("<b>Market mechanism:</b> many quantitative hedge funds, working independently "
  "with different proprietary signals, can still end up holding very similar "
  "positions if their signals are built on the same underlying academic factors "
  "(value, momentum). Their portfolios look diversified from the inside but are "
  "secretly correlated with each other. This is the central mechanism behind the "
  "2007 &quot;Quant Quake&quot; (Part IV): once one large fund was forced to sell, "
  "the selling pressure looked, to every other similarly-positioned fund's model, "
  "like a signal to sell the same names.")

# MARKER_END_PART2

# ============================================================ PART III
story.append(PageBreak())
toc_entry("Part III &mdash; Quantitative Methodology, Explained", 0, "part3")
part("Part III &mdash; Quantitative Methodology, Explained")

h1("3.1  What is Value-at-Risk, and why does a &quot;calm-regime&quot; model miss the point?")
p("<b>Plain-language definition:</b> Value-at-Risk (VaR) at the 99% confidence level "
  "answers the question &quot;on a bad-but-not-extreme day (one of the worst 1% of "
  "days), roughly how much could this portfolio lose?&quot; It is the financial "
  "-industry equivalent of an insurer asking &quot;how much should we expect to pay "
  "out in a bad year, one we'd expect to see about once every hundred years?&quot;")
p("<b>Why a Gaussian (bell-curve) model of VaR is dangerous:</b> the easiest way to "
  "estimate VaR is to assume returns follow a normal (bell-curve) distribution, "
  "calibrated on however many years of historical data are available, and to "
  "assume the *correlations* between different positions &mdash; how much they tend "
  "to move together &mdash; stay roughly constant. Both assumptions are usually "
  "reasonable in ordinary conditions. Both usually fail together, at the worst "
  "possible time: during a genuine crisis, returns move by more than a bell curve "
  "predicts (&quot;fat tails&quot;), and positions that used to move mostly "
  "independently start moving together (correlations spike toward 1), because "
  "everyone is reacting to the same underlying fear at once.")
box(
    "Two houses on the same street, insured separately against fire. Ordinarily, "
    "one house catching fire tells an insurer almost nothing about whether the "
    "neighboring house will too &mdash; fires are close to independent events, so "
    "insuring both together looks safe. But a wildfire changes that: it can burn "
    "down both houses at once, because now the two risks share a single common "
    "cause. A risk model calibrated only on ordinary house fires will badly "
    "underestimate the insurer's exposure to a wildfire year, not because the "
    "model is bad at estimating ordinary fires, but because it never saw the "
    "correlation-raising event in its calibration data. This is exactly the "
    "mechanism this project's Part III.3 simulation quantifies for a leveraged "
    "trading book.",
    kind="fact", title="ANALOGY: TWO HOUSES AND A WILDFIRE"
)

h2("3.2  The Q1 risk simulation: setup")
p("Rather than simply asserting that Gaussian VaR models understate tail risk, "
  "this project built a Monte Carlo simulation (<i>risk_simulation/"
  "fat_tails_vs_normal.py</i> in the code repository) that computes the "
  "underestimation directly. It models a leveraged, six-asset relative-value "
  "book (weights summing to roughly 9x gross exposure, loosely evocative of the "
  "kind of leveraged spread trades LTCM ran) under two return-generating "
  "processes:")
bullets([
    "<b>The model the risk desk believes:</b> a Gaussian (bell-curve) distribution, "
    "with a modest, constant 0.25 pairwise correlation between assets, calibrated "
    "on &quot;calm regime&quot; data &mdash; exactly the kind of risk model a desk "
    "would build from a few years of ordinary historical returns.",
    "<b>The process that actually generates the data:</b> the same calm regime "
    "most days, but with a small (1%) daily probability of switching into a "
    "&quot;stress regime&quot; where volatility roughly triples and pairwise "
    "correlation jumps to 0.92 &mdash; combined with fat-tailed (Student-t) "
    "shocks in both regimes for realistic extreme-day behavior.",
])
box(
    "This project's sandbox environment had no general internet access when this "
    "simulation was built (see Part V for the full story), which ruled out "
    "downloading real historical crisis data to measure this effect directly. "
    "Rather than skip the question or fake a result, the decision was to build a "
    "Monte Carlo simulation that needs no external data at all &mdash; every "
    "number it reports is a genuine, reproducible output of code that actually "
    "ran, even though the underlying scenario is stylized rather than a literal "
    "reconstruction of any single historical event. The parameters (0.25 to 0.92 "
    "correlation, 3x volatility) were chosen to be qualitatively consistent with "
    "what is publicly known about the LTCM episode's shape, not fit to LTCM's "
    "actual (never fully disclosed) book &mdash; the report is explicit that the "
    "resulting multiple should be read as &quot;this is the order of magnitude of "
    "the effect,&quot; not a precise historical reconstruction.",
)

h2("3.3  The Q1 results (real, executed numbers)")
data_table(
    ["Tail depth", "Gaussian (calm-regime) VaR", "True (simulated) VaR", "True Expected Shortfall (CVaR)"],
    [
        ["99.0%", "7.67% of book", "8.15% of book  (1.06x)", "10.37% of book  (1.35x)"],
        ["99.9%", "10.19% of book", "13.26% of book  (1.30x)", "16.83% of book  (1.65x)"],
    ],
    col_widths=[0.9*inch, 1.8*inch, 1.9*inch, 1.9*inch],
)
p("Worst single day across 500,000 simulated trading days: a loss of 58.9% of the "
  "book &mdash; a scale of move a Gaussian, calm-regime model treats as "
  "essentially impossible, but which falls naturally out of a process that "
  "occasionally lets volatility and correlation rise together. The gap between "
  "the Gaussian model and reality is modest right at the 99% line (that quantile "
  "happens to sit near the boundary between regimes in this parameterization) but "
  "compounds quickly deeper into the tail &mdash; which is itself an important "
  "lesson: a risk model can look adequate at the confidence level a regulator or "
  "risk committee checks routinely, and still be dangerously wrong exactly where "
  "it matters most, a few notches further into the tail.")

h1("3.4  Turning behavioral biases into tradable formulas")
p("Part II described three biases in plain language. Here is how each becomes a "
  "number that can be computed for every stock, every day, and used to rank a "
  "universe of companies:")
data_table(
    ["Signal", "Formula (plain language)", "Bias it targets"],
    [
        ["12-1 month momentum", "Cumulative return over the trailing ~12 months, "
         "excluding the most recent month (to avoid contaminating the signal with "
         "short-term reversal, below)", "Underreaction"],
        ["52-week-high proximity", "Current price divided by the highest price "
         "reached in the trailing 52 weeks (1.0 = at the high)", "Anchoring"],
        ["Short-term reversal", "Negative of the trailing ~1-month return "
         "(a recent loser scores positively, betting on a bounce)", "Overreaction"],
    ],
    col_widths=[1.5*inch, 3.6*inch, 1.5*inch],
)
p("A <b>composite score</b> blends all three by converting each to a "
  "cross-sectional z-score (how many standard deviations a stock is above or "
  "below the average stock, on that signal, on that day) and averaging &mdash; "
  "the intended purpose being a single number that combines all three biases into "
  "one rank. Part V explains why this turned out to be a more dangerous "
  "simplification than it first appears.")

h1("3.5  How the backtest actually works")
p("The methodology follows the standard approach used in the academic momentum "
  "and reversal literature, so results are comparable to published findings "
  "rather than being an artifact of a bespoke design:")
bullets([
    "Once a month, every stock in the universe is ranked by its current signal "
    "score.",
    "The strategy goes equally-weighted <i>long</i> the top group (the best-ranked "
    "names) and equally-weighted <i>short</i> the bottom group (the worst-ranked "
    "names) &mdash; a &quot;long-short&quot; portfolio, so its return reflects the "
    "spread between the best and worst names, not the market's overall direction.",
    "The portfolio is held for one month, then re-ranked and rebalanced.",
])
p("Three metrics summarize the result:")
bullets([
    "<b>Sharpe ratio:</b> average return divided by the volatility (bumpiness) of "
    "that return, annualized. A Sharpe of 1.0 is generally considered good for a "
    "systematic strategy; a Sharpe near 0 means the strategy earned close to "
    "nothing per unit of risk taken; a negative Sharpe means it lost money "
    "relative to its own risk.",
    "<b>Maximum drawdown:</b> the largest peak-to-trough decline the strategy "
    "experienced at any point in the backtest &mdash; a measure of the worst "
    "single stretch an investor in the strategy would have had to sit through.",
    "<b>Turnover and transaction costs:</b> every rebalance that changes which "
    "names are held costs money in practice (bid-ask spread, market impact). The "
    "backtest engine tracks how much of the portfolio changes each month "
    "(turnover) and deducts a simple cost (basis points per unit of turnover) to "
    "report both a &quot;gross&quot; return (before costs) and a &quot;net&quot; "
    "return (after costs) &mdash; because a strategy that looks good gross and "
    "disappears net of realistic costs is a very common way quantitative research "
    "misleads itself.",
])

# MARKER_END_PART3

# ============================================================ PART IV
story.append(PageBreak())
toc_entry("Part IV &mdash; Five Case Studies, in Depth", 0, "part4")
part("Part IV &mdash; Five Case Studies, in Depth")
p("Each case below follows the same structure: what happened, with a timeline; "
  "which behavioral mechanism from Part II explains it, in plain language; and "
  "why the case matters for this project's central question.")

h1("4.1  Long-Term Capital Management (1998)")
h2("What happened")
p("Long-Term Capital Management was a hedge fund founded in 1994 by John "
  "Meriwether, with partners that included Myron Scholes and Robert Merton, who "
  "shared the 1997 Nobel Memorial Prize in Economic Sciences for the "
  "Black-Scholes-Merton option-pricing framework taught in every finance "
  "curriculum. The fund ran highly leveraged convergence/relative-value "
  "arbitrage: betting that prices of closely related securities would converge "
  "toward their historically &quot;fair&quot; relationship. Individual trades had "
  "small expected edges, so the fund used enormous leverage &mdash; over 25:1 on "
  "its balance sheet, with derivative notional exposure exceeding $1 trillion "
  "&mdash; to turn small, statistically reliable-looking edges into a large "
  "return.")
p("From 1994-1997 the fund returned roughly 20-40% annually, a track record that "
  "built exactly the kind of confidence Part II.3 (overconfidence) describes. "
  "Russia's default and rouble devaluation on August 17, 1998 triggered a global "
  "&quot;flight to quality&quot;: investors worldwide fled toward the safest, "
  "most liquid assets (US Treasuries) and away from everything else, regardless "
  "of the specific fundamental link between the assets they were selling. "
  "Spreads LTCM's model treated as largely independent instead moved together, "
  "in the same direction, and kept widening instead of converging. The fund lost "
  "about $1.9 billion in August alone; by September 21, capital had fallen from "
  "roughly $4.7 billion at the start of the year to about $600 million, against "
  "essentially unchanged notional exposure. On September 23, 1998, with the fund "
  "days from a disorderly default that regulators feared could force a fire-sale "
  "across Wall Street, the Federal Reserve Bank of New York organized (but did "
  "not fund) a $3.625 billion recapitalization by 14 banks in exchange for 90% "
  "of the fund's equity.")
h2("The behavioral mechanism, explained")
p("This is a herding case (Part II.2), but with an important twist: the herding "
  "was not LTCM's own. LTCM's individual trades were, in isolation, "
  "defensible. What broke the model was that every other market participant "
  "started behaving in a correlated way at once &mdash; a collective flight to "
  "safety that a &quot;rational agents, independent decisions&quot; model does "
  "not naturally produce. The lesson generalizes: a model of rational markets is "
  "only as good as its assumption that other participants keep behaving "
  "independently under stress, and that is precisely the assumption that breaks "
  "in a genuine crisis &mdash; the exact mechanism quantified in Part III's Q1 "
  "simulation.")
h2("Why it matters here")
p("LTCM is the founding case for this entire project: a fund staffed by the "
  "people who literally wrote the mathematics of modern option pricing still "
  "lost 90% of its capital in six weeks, not because the mathematics was wrong, "
  "but because the mathematics assumed away exactly the kind of correlated human "
  "behavior that shows up under real stress.")

h1("4.2  The &quot;Quant Quake&quot; (August 2007) and Amaranth Advisors (2006)")
h2("What happened &mdash; Quant Quake")
p("Between roughly August 6-9, 2007, a large number of market-neutral "
  "quantitative equity funds &mdash; using different individual signals, run by "
  "different firms, with no apparent common trigger in company fundamentals "
  "&mdash; suffered simultaneous, sharply correlated losses over a few trading "
  "days, followed by a partial rebound once the selling pressure eased. Several "
  "well-known quant strategies lost on the order of 5-10%+ in that single week "
  "&mdash; an extreme move for supposedly market-neutral, low-volatility books. "
  "The standard academic reconstruction (Khandani &amp; Lo, 2007/2011) attributes "
  "this to <b>crowding</b>: many quant managers had, independently, arrived at "
  "similar factor tilts (value, momentum), so their books were far more "
  "correlated with each other than any of them individually realized. When one "
  "or more large funds were forced to deleverage a quant book quickly (for "
  "reasons believed unrelated to those specific positions), the forced selling "
  "looked, to every other similarly-built model, like a signal to sell the same "
  "names.")
h2("What happened &mdash; Amaranth")
p("Amaranth Advisors was a large multi-strategy hedge fund that lost "
  "approximately $6.5 billion in September 2006, almost entirely from "
  "concentrated, highly leveraged natural-gas futures and options positions run "
  "by a single trader, Brian Hunter. Hunter's core position was a calendar "
  "spread &mdash; long winter-month natural-gas futures against short "
  "summer-month contracts, betting the spread would widen &mdash; sized large "
  "enough, relative to actual market open interest, that Amaranth's own trading "
  "could move the market it was betting on. A mild start to the 2006 hurricane "
  "season pushed the spread the wrong way; over roughly a week in mid-September "
  "2006 the fund lost more than half its capital.")
h2("The behavioral mechanisms, explained")
p("Quant Quake is a crowding case (Part II.7): herding among the most "
  "sophisticated participants in the market, the group a naive "
  "efficient-markets story would expect to be immune to it. Amaranth is an "
  "overconfidence case (Part II.3): Hunter's prior profitable natural-gas trades "
  "made a concentrated, survivable-only-if-right position look more justified "
  "than the fund's risk limits should have allowed.")
h2("Why they matter here")
p("Together, these two cases show that neither sophistication (Quant Quake) nor "
  "a genuinely skilled track record (Amaranth) protects against the specific "
  "behavioral failure modes this project studies &mdash; they just change which "
  "failure mode shows up.")

h1("4.3  The 2008 Financial Crisis and the Gaussian Copula")
h2("What happened")
p("The 2007-2008 crisis is usually told as a subprime mortgage story, but the "
  "mechanism that turned a real but containable housing problem into a systemic "
  "banking crisis mirrors this project's Q1 simulation almost exactly. Banks "
  "packaged mortgage pools into collateralized debt obligations (CDOs), tranched "
  "by seniority. A senior tranche's safety depends critically on how correlated "
  "the underlying mortgage defaults are: independent defaults make a senior "
  "tranche very safe; correlated defaults (a national downturn hitting every "
  "region at once) make that protection evaporate. The industry-standard tool "
  "for pricing this correlation risk was the Gaussian copula (David X. Li, 2000), "
  "which reduced the hard problem of modeling thousands of correlated defaults "
  "to a single correlation parameter, estimated from a history drawn almost "
  "entirely from a multi-decade housing boom during which national home prices "
  "had never fallen.")
p("When US home prices began falling nationally in 2006-2007 &mdash; a regime "
  "the calibration window had essentially no examples of &mdash; mortgage "
  "defaults stopped being independent and started moving together, for the same "
  "underlying reason, in every region at once. Senior tranches priced as "
  "extremely safe took losses far larger and faster than the model implied, and "
  "because these instruments were held throughout the banking system, the losses "
  "hit systemically important institutions almost simultaneously (Bear Stearns, "
  "March 2008; Lehman Brothers' bankruptcy, September 15, 2008; AIG's roughly "
  "$182 billion federal rescue, driven largely by credit default swaps written "
  "against these same instruments).")
h2("The behavioral mechanism, explained")
p("This is structurally the identical mistake as a calm-regime Gaussian VaR "
  "model (Part III.1's wildfire analogy): a correlation parameter estimated from "
  "a period that never included the correlation-raising regime, and therefore "
  "blind to how fast that correlation could rise once it arrived. Two "
  "behavioral/institutional layers sit on top of the pure model failure: "
  "<b>herding into a shared industry model</b> (using it was a competitive "
  "necessity even for desks that suspected it understated risk &mdash; a "
  "rational individual response to career/franchise risk producing an "
  "irrational collective outcome), and a <b>correlated trust collapse</b> once "
  "losses started (nobody could tell who was exposed to how much bad paper, so "
  "short-term lenders pulled back from everyone at once &mdash; the same "
  "flight-to-quality mechanism as LTCM, at systemic scale).")
h2("Why it matters here")
p("This is the largest-scale version, in modern financial history, of the "
  "pattern this project's Q1 simulation makes explicit in miniature: a model "
  "that is locally reasonable, calibrated on real data, and wrong specifically "
  "about how correlation behaves in the rare regime that does the damage.")

h1("4.4  GameStop and the &quot;Meme Stock&quot; Squeeze (January 2021)")
h2("What happened")
p("Through 2020, several large hedge funds, most prominently Melvin Capital, "
  "held large short positions in GameStop (GME), a struggling brick-and-mortar "
  "video-game retailer, on a conventional view that the business was in "
  "structural decline. Starting in mid-to-late January 2021, a large, "
  "coordinated wave of retail buying &mdash; organized largely on the Reddit "
  "forum r/wallstreetbets &mdash; pushed the share price up by roughly an order "
  "of magnitude in a few weeks. Two mechanisms compounded pure buying pressure: "
  "a <b>short squeeze</b> (as the price rose, short sellers faced margin calls "
  "and were forced to buy shares to close losing positions, pushing the price up "
  "further) and a <b>gamma squeeze</b> (heavy buying of short-dated call options "
  "forced the market-makers who sold those calls to buy the underlying stock to "
  "stay hedged, an amplifying loop running through market structure rather than "
  "anyone's fundamental view). Melvin Capital's short position lost the fund a "
  "very large share of its capital in January 2021 and received a $2.75 billion "
  "capital injection from Citadel and Point72 on January 25, 2021. Robinhood and "
  "other brokerages restricted buying of GameStop and similar stocks on January "
  "28, 2021, citing clearinghouse deposit requirements &mdash; a decision that "
  "triggered US congressional hearings in February 2021.")
h2("The behavioral mechanisms, explained")
p("This case runs the <i>opposite</i> direction from the others: retail herding "
  "(Part II.2, at internet speed and scale) overwhelming institutional "
  "positioning, amplified by attention-driven trading (Part II.6 &mdash; "
  "GameStop became a target largely because it was already attention-grabbing, "
  "consistent with Barber &amp; Odean's research on individual investors "
  "disproportionately buying stocks that recently grabbed their attention) and "
  "by the gamified design of mobile-first trading apps.")
h2("Why it matters here")
p("GameStop is included specifically to prevent this project's thesis from "
  "collapsing into &quot;institutions are rational, retail is irrational&quot; "
  "&mdash; a genuinely coordinated crowd can overwhelm sophisticated positioning "
  "just as forcefully as institutional herding overwhelmed LTCM's models, just "
  "pointed in the opposite direction.")

h1("4.5  The Other Side: Funds Built to Exploit These Biases")
p("Every case above is a story about a bias causing a loss. These three firms "
  "are the counter-evidence: specific, named biases treated as a persistent, "
  "exploitable source of return.")
h2("Fuller &amp; Thaler Asset Management")
p("Founded in 1993 by Richard Thaler &mdash; awarded the 2017 Nobel Memorial "
  "Prize in Economic Sciences for work on how limited rationality affects "
  "economic decisions &mdash; together with Russell Fuller. Their signature "
  "mechanism is closely related to Part II.4's underreaction concept: "
  "post-earnings-announcement drift, the well-documented finding that stock "
  "prices keep drifting in the direction of an earnings surprise for weeks "
  "after the announcement, because analysts anchor on their pre-announcement "
  "estimates and update too slowly. Their flagship retail vehicle has long "
  "traded as &quot;Undiscovered Managers Behavioral Value&quot; (ticker UBVLX).")
h2("LSV Asset Management")
p("Founded in 1994 by academic economists Josef Lakonishok, Andrei Shleifer, "
  "and Robert Vishny, whose own research (Lakonishok, Shleifer &amp; Vishny, "
  "<i>Journal of Finance</i> 49(5), 1994, pp. 1541-1578) argued that much of "
  "value stocks' historical outperformance over &quot;glamour&quot; growth "
  "stocks is explained by investors extrapolating recent growth too far into "
  "the future (Part II.5), not by value stocks simply being riskier.")
h2("AQR Capital Management")
p("Founded in 1998 by Cliff Asness, whose University of Chicago PhD "
  "dissertation (under advisors including Eugene Fama, himself closely "
  "associated with the efficient markets hypothesis) was on momentum in stock "
  "returns. AQR treats behavioral anomalies as one input among several "
  "(alongside risk-based explanations), run with heavy quantitative discipline "
  "&mdash; a useful middle case between Fuller &amp; Thaler's purely behavioral "
  "framing and a pure risk-based factor story.")
p("The working assumption behind all three &mdash; and behind this project's "
  "signal library in Part III &mdash; is that specific, named biases produce "
  "persistent, not merely historical, mispricing. Part V.2's empirical result "
  "tests that assumption directly, with a real, non-cherry-picked outcome.")

# MARKER_END_PART4

# ============================================================ PART V
story.append(PageBreak())
toc_entry("Part V &mdash; Project Journal: Milestones, Decisions, Results", 0, "part5")
part("Part V &mdash; Project Journal: Milestones, Decisions, Results")
p("This part narrates the project as it actually happened, in order, including "
  "the constraints that forced decisions and the results that changed the "
  "project's direction. Every decision below is stated together with the "
  "reasoning behind it, per this guide's brief: nothing is presented as "
  "self-evidently correct without the &quot;why.&quot;")

h1("5.1  Scoping the project")
p("The project started from a broad brief: research the role of human "
  "irrationality in markets, with concrete applications to finance and "
  "business. Before writing anything, the scope was narrowed by asking four "
  "questions: what output format was wanted, which behavioral angle to anchor "
  "on, what methodology/evidence to use, and what concrete impact the research "
  "should produce.")
box(
    "The answers chosen were: a <b>quantitative research project with runnable "
    "code</b> (not a pure literature review); anchored on <b>both</b> failed "
    "&quot;rational market&quot; bets (LTCM-style) <b>and</b> behavioral funds "
    "that exploit bias; using <b>public market data plus case-study "
    "comparison</b>; aimed at producing an <b>investment framework, "
    "risk-management lessons, and a business idea</b>. This combination was "
    "chosen specifically because it forces the project to be falsifiable in "
    "both directions at once (Part I.3) rather than only telling the flattering "
    "half of the story (either &quot;markets are irrational, here's how to "
    "profit&quot; or &quot;here's why smart people fail,&quot; without testing "
    "either claim against real numbers).",
)

h1("5.2  Milestone 1 &mdash; Building the pipeline under a hard constraint")
p("The first concrete obstacle appeared immediately: the development "
  "environment's outbound network access is restricted by an egress proxy to a "
  "specific allowlist. Direct testing (curl requests to each host, and reading "
  "the proxy's own status endpoint, which logs connection failures) confirmed "
  "that Yahoo Finance, Stooq, SEC EDGAR, and FRED &mdash; every conventional "
  "free market-data source &mdash; were all blocked with a 403 policy denial.")
box(
    "The tempting shortcut here would have been to generate synthetic "
    "&quot;market-looking&quot; data and present backtest results computed on "
    "it as if they were real findings &mdash; exactly the kind of "
    "model-dressed-as-reality mistake this project's whole thesis warns "
    "against. The decision instead was to build the complete, real pipeline "
    "(data loader, signal library, backtest engine) as production-quality code, "
    "but to sharply separate two categories of claim: results that were "
    "<b>actually computed by running code in this environment</b> (which get "
    "stated as fact) versus code that is <b>complete and believed correct but "
    "not yet exercised on real data</b> (which gets stated as an explicit, "
    "flagged limitation, never as a finding). The one part of the research that "
    "needed no external data at all &mdash; the Q1 tail-risk simulation "
    "(Part III.2-3.3) &mdash; was built first specifically because it could "
    "produce a genuine, real result despite the network constraint.",
)
p("Milestone 1 shipped: the research design document, the full signal and "
  "backtest codebase (validated only against synthetic test fixtures at this "
  "point, with that limitation stated explicitly), the Q1 risk simulation with "
  "its real executed numbers, three initial case studies (LTCM, Quant Quake / "
  "Amaranth, the behavioral funds), and a first version of the practical "
  "framework document.")
box(
    "At the end of milestone 1, a new working practice was established at the "
    "user's request: after every milestone, provide a recap of the reasoning "
    "behind what was built, followed by explicit questions checking whether the "
    "project's focus was still correctly calibrated to what was actually "
    "wanted. This is why milestones 2 and 3 below each open with what the "
    "previous recap's questions surfaced.", kind="fact", title="PROCESS DECISION"
)

h1("5.3  Milestone 2 &mdash; Real data, and a result that changed the project")
p("The milestone-1 recap asked, among other things, how to handle the "
  "no-internet constraint going forward. The chosen answer was to actively "
  "search for a reachable data source rather than accept the limitation as "
  "final.")
box(
    "Rather than assume every external host was blocked, a range of unrelated "
    "hosts was tested directly &mdash; not just financial-data providers but "
    "also generic ones (a plain package index, a generic search engine). This "
    "showed the block was not &quot;no internet at all&quot; but a specific "
    "allowlist: <i>api.github.com</i> and <i>raw.githubusercontent.com</i> were "
    "reachable while general financial-data hosts and even a plain "
    "general-purpose website were not. That distinction mattered: it meant "
    "GitHub-hosted datasets were a real option, not a dead end.",
)
p("A web search for GitHub-hosted multi-ticker daily price datasets surfaced a "
  "real candidate: a community-uploaded CSV of 63 raw ticker symbols covering "
  "NSE (India) large/mid-cap companies from 2000 to 2021. Before using it, the "
  "data was checked for basic quality (no duplicate date/symbol rows, no "
  "zero or negative prices) and then for a subtler issue: several apparent "
  "&quot;different companies&quot; turned out, on inspection of their trading "
  "date ranges, to be the <i>same</i> company under a former ticker symbol.")
box(
    "The evidence for this was date-range contiguity: symbol A's last trading "
    "date and symbol B's first trading date lined up with no overlap and no "
    "gap, for 14 separate symbol pairs (or longer chains) &mdash; the exact "
    "signature of an NSE ticker rename. Each chain was then cross-checked "
    "against publicly known Indian corporate history (for example, "
    "&quot;TELCO&quot; was Tata Motors' ticker before a rename; "
    "&quot;SESAGOA&quot; became &quot;SSLT&quot; then &quot;VEDL&quot; as Sesa "
    "Goa became Sesa Sterlite became Vedanta Ltd) before merging. One pair, "
    "HDFC and HDFCBANK, was deliberately <i>not</i> merged, because the two "
    "were genuinely separate listed companies for the entire sample period "
    "(they only merged in 2023, after the data ends). This is the kind of "
    "judgment call that is easy to get wrong silently in a backtest &mdash; "
    "merging two unrelated companies, or failing to merge one company's own "
    "history &mdash; so it was done from evidence, and locked in afterward "
    "with a dedicated automated test (visible in the code repository's "
    "<i>tests/test_loaders.py</i>) rather than left as a one-off manual step.",
)
p("With 48 clean, continuous company series covering 21 years, the full "
  "signal-and-backtest pipeline was run for the first time on real market "
  "data.")
data_table(
    ["Signal", "Split", "Gross annual return", "Gross Sharpe", "Net Sharpe", "Max drawdown"],
    [
        ["Composite (all 3)", "deciles", "-3.59%", "0.01", "-0.03", "-74.3%"],
        ["Composite (all 3)", "quintiles", "-1.33%", "0.05", "0.00", "-63.2%"],
        ["12-1 momentum only", "quintiles", "-1.73%", "0.04", "0.01", "-60.8%"],
        ["52-week-high only", "quintiles", "-13.71%", "-0.51", "-0.54", "-97.1%"],
        ["Short-term reversal only", "quintiles", "+4.46%", "0.30", "0.22", "-64.1%"],
    ],
    col_widths=[1.5*inch, 0.75*inch, 1.2*inch, 0.85*inch, 0.8*inch, 0.9*inch],
    small=True,
)
p("The composite score alone would have supported a bland, roughly-correct-"
  "sounding conclusion: &quot;no real edge here.&quot; Decomposing it into its "
  "three parts told a much more informative and, in one case, misleading "
  "story: the 52-week-high (anchoring) signal was actively destructive, "
  "losing money persistently and suffering a 97% drawdown, while the "
  "short-term reversal (overreaction) signal <i>looked</i> like a genuine, "
  "positive, cost-adjusted edge. Averaging them together hid both facts "
  "&mdash; and Part V.9 (Milestone 8) later found the reversal side of "
  "that story didn't survive the same scrutiny the losing side got.")
p("A follow-up check tested whether the anchoring signal's damage was simply an "
  "artifact of the 2008 and 2020 crashes (both periods where a "
  "&quot;buy recent winners&quot; strategy is known from the academic "
  "literature to be exposed to sharp reversals &mdash; &quot;momentum crash "
  "risk&quot;). Excluding both crash windows entirely, the strategy's Sharpe "
  "ratio outside them was still -0.46, and its cumulative loss "
  "<i>excluding</i> the crashes (-90%) was actually larger than its loss "
  "<i>during</i> them (-53%) &mdash; ruling out &quot;it only lost money "
  "in the two crashes&quot; as the explanation, and leaving the true cause an "
  "open question flagged honestly rather than resolved with a plausible-"
  "sounding guess. (Part V.4 below picks this exact question back up.)")
box(
    "The milestone-2 recap surfaced this same lesson back to the practice "
    "guiding the project itself: a mediocre-looking blended result should "
    "always be decomposed before being trusted, a rule now stated explicitly "
    "in the practical framework (Part VI.1). The recap also asked whether "
    "tying the eventual business idea to this repository's own existing "
    "software platform (a private-equity deal-screening tool the code "
    "happened to live alongside) was the right framing. The answer was no "
    "&mdash; the business idea was rewritten from scratch as a standalone "
    "analytics service (Part VI.3), decoupled from any specific existing "
    "platform, per that explicit feedback.",
)

h1("5.4  Milestone 3 &mdash; Replication, and a rejected hypothesis")
p("The milestone-2 recap's questions produced three directions: search for a "
  "second, independent market's data to check whether the NSE findings "
  "replicate elsewhere; investigate <i>why</i> the 52-week-high signal lost "
  "money, specifically testing whether it was confounded with a value/growth "
  "effect; and continue expanding the codebase rather than wrapping up. "
  "Producing this guide itself was folded into the same milestone, at the "
  "user's explicit request to run it in parallel with the quantitative work "
  "rather than after it &mdash; which is why an earlier draft of this section "
  "reported milestone 3 as in-progress; both investigations below have since "
  "completed.")
h2("Finding a second market")
p("A GitHub-hosted mirror of the well-known Kaggle &quot;Huge Stock Market "
  "Dataset&quot; (one CSV per US-listed ticker) was located and verified: 30 "
  "US large-cap names, the same tickers as the project's original default "
  "universe, each starting at its own listing date and running through "
  "2017-11-10 (the dataset's last snapshot; this is a historical replication "
  "check, not a live feed).")
data_table(
    ["Signal", "Split", "Gross annual return", "Gross Sharpe", "Net Sharpe", "Max drawdown"],
    [
        ["Composite (all 3)", "quintiles", "+2.99%", "0.25", "0.21", "-79.6%"],
        ["12-1 momentum only", "quintiles", "+5.72%", "0.34", "0.32", "-88.4%"],
        ["52-week-high only", "quintiles", "-13.98%", "-0.29", "-0.32", "-99.9%"],
        ["Short-term reversal only", "quintiles", "-0.68%", "0.13", "0.07", "-83.0%"],
    ],
    col_widths=[1.5*inch, 0.75*inch, 1.2*inch, 0.85*inch, 0.8*inch, 0.9*inch],
    small=True,
)
p("The result was not a clean confirmation of the NSE finding &mdash; it was "
  "more informative than that. <b>Momentum and reversal flipped which one "
  "looked real</b>: reversal was NSE's edge and the US market's near-zero "
  "result; momentum was NSE's near-zero result and the US market's real, "
  "positive, cost-adjusted edge (Sharpe 0.32 net). Only one thing held up "
  "unchanged across both very different markets and eras: <b>the 52-week-high "
  "signal lost money in both.</b> (Part V.9, Milestone 8, later put both "
  "sides of this flip through a beta-adjusted significance test: the US "
  "momentum side held up and then some; the NSE reversal side did not.)")
box(
    "A single-market backtest result is provisional by default. Had this "
    "project stopped after milestone 2 (NSE only), it would have reported "
    "&quot;momentum is dead here, reversal is the real edge&quot; &mdash; the "
    "opposite of what the US data alone would have suggested. Neither market "
    "alone is the right answer; the honest finding is that anomaly presence "
    "is universe-dependent for momentum and reversal, while the "
    "52-week-high signal's damage is not.",
)
h2("Testing the value/growth confound &mdash; and rejecting it")
p("The leading candidate explanation for the 52-week-high signal's losses, "
  "carried over from milestone 2, was that India's two-decade secular bull "
  "market could make &quot;short the names far from their 52-week high&quot; "
  "equivalent to &quot;short cheap, beaten-down names&quot; that then "
  "mean-revert upward &mdash; a value effect masquerading as an anchoring "
  "effect. This was tested directly: a simple price-only value proxy (current "
  "price divided by its own trailing ~3-year average) was built, its "
  "cross-sectional correlation with the raw 52-week-high score was measured, "
  "and the 52-week-high signal was then <b>orthogonalized</b> against it "
  "&mdash; a date-by-date cross-sectional regression that mathematically "
  "removes the shared value component, leaving only the part of the signal "
  "that isn't explained by it.")
data_table(
    ["Market", "Correlation (signal, value proxy)", "Raw signal net Sharpe", "Orthogonalized net Sharpe"],
    [
        ["NSE (India)", "0.63", "-0.54", "-0.73"],
        ["US (Kaggle mirror)", "0.44", "-0.32", "-0.49"],
    ],
    col_widths=[1.6*inch, 2.1*inch, 1.5*inch, 1.7*inch],
)
p("The two signals genuinely are correlated (0.44-0.63) &mdash; a stock near "
  "its 52-week high does tend to look &quot;expensive&quot; on this proxy. "
  "But removing that shared component made performance <b>worse</b>, not "
  "better, in both markets. If the value/growth confound had been the real "
  "explanation, the &quot;purified&quot; signal should have looked neutral "
  "or better once the confounding value component was stripped out; instead "
  "it got more negative. <b>The value/growth confound hypothesis is "
  "rejected.</b>")
box(
    "This is a negative result, and it was reported as one rather than "
    "quietly dropped or reframed as a success. Combined with the milestone-2 "
    "finding that the loss isn't concentrated in the 2008/2020 crash windows "
    "either, two of the three candidate explanations for the 52-week-high "
    "result are now ruled out by direct test, not just by argument. The "
    "remaining candidate &mdash; generic momentum-crash risk, a documented "
    "property of &quot;long recent winners&quot; strategies in general "
    "&mdash; is the best-supported explanation left standing, but it has not "
    "itself been directly tested (that would mean checking whether the "
    "losses cluster specifically in high-volatility periods). The project "
    "states this as narrowed, not solved.",
    kind="fact", title="WHAT THIS DOES AND DOESN'T PROVE"
)

h1("5.5  Milestone 4 &mdash; Testing momentum-crash risk directly")
box(
    "<b>Update (Section 5.6, Milestone 5): the formal statistical test does "
    "NOT confirm the regime-conditioning mechanism this section describes.</b> "
    "This section is kept as written at the time &mdash; the pattern-matching "
    "genuinely looked this compelling &mdash; but Section 5.6 walks it back "
    "with real numbers. Read that section before treating anything below as "
    "confirmed.",
    kind="fact", title="READ THIS FIRST"
)
p("The one remaining candidate explanation from milestone 3 &mdash; generic "
  "momentum-crash risk (Daniel &amp; Moskowitz, &quot;Momentum Crashes,&quot; "
  "2016; see Part II.4 and Part IV.1) &mdash; was tested directly at the "
  "user's request. The theory's specific prediction: a &quot;long recent "
  "winners, short recent losers&quot; strategy is exposed to severe losses "
  "when realized market volatility is elevated and the market has recently "
  "been in a downturn, because the <i>short</i> leg (recent losers, "
  "typically higher-beta) can rebound sharply in a recovery &mdash; and the "
  "damage should concentrate specifically in that short leg, not be spread "
  "evenly across both sides of the trade.")
p("Two things were built to test this properly rather than just plausibly: "
  "two regime indicators from the same price data (a realized-volatility "
  "tercile and a trailing-12-month bull/bear flag, both lagged one day to "
  "avoid look-ahead), and an extension to the backtest engine itself so it "
  "reports the long leg's and short leg's profit-and-loss contributions "
  "<i>separately</i>, not just their combined total &mdash; needed to check "
  "the mechanism, not only the timing.")
data_table(
    ["Evidence", "NSE (India)", "US (Kaggle mirror)"],
    [
        ["Sharpe vs. realized-vol tercile (Low/Mid/High)", "-0.22 / -0.41 / -0.78", "-0.11 / -0.27 / -0.43"],
        ["Sharpe, bull vs. bear trailing-12m state", "-0.27 vs. -1.06", "-0.15 vs. -1.10"],
        ["Worst bucket: bear + high-vol", "-1.07 Sharpe, -38% ann.", "-1.26 Sharpe, -61% ann."],
        ["Return skewness, combined long-short", "-0.66", "-1.32"],
    ],
    col_widths=[2.9*inch, 1.9*inch, 1.9*inch],
    small=True,
)
p("All four signatures point the same way, in both markets. The leg "
  "decomposition confirms the mechanism, not just correlated timing: the "
  "<b>long leg (buying stocks near their 52-week high) is a genuinely "
  "positive, standalone strategy</b> in both markets (Sharpe 0.45-1.03 in "
  "every regime tested on NSE; 0.65-1.20 outside bear markets in the US) "
  "&mdash; the anchoring/underreaction thesis actually works on the long "
  "side. <b>The short leg is the entire problem</b>: negative in every "
  "single regime bucket in both markets, and its losses are specifically "
  "what swells in the bear-plus-high-volatility bucket (NSE: -19% to -49% "
  "annualized from calmest to worst regime; US: -13% to -62%).")
box(
    "This is pattern-matching against a well-documented mechanism using real "
    "data across two independent markets, not a formal significance test "
    "&mdash; no statistical t-tests were run on the regime differences, and "
    "the volatility-tercile cutoffs were computed over each dataset's full "
    "history rather than a rolling window a live system would need. With "
    "that caveat stated plainly, at this point in the project four "
    "independent, mutually consistent signatures looked like about as "
    "strong a case as this kind of historical analysis could make short of "
    "formal statistics &mdash; which is exactly what Section 5.6 adds, and "
    "exactly what changes the conclusion.",
    kind="fact", title="HOW HARD TO LEAN ON THIS, AS UNDERSTOOD AT THE TIME"
)

h1("5.6  Milestone 5 &mdash; Formally testing momentum-crash risk")
p("The user explicitly asked for the pattern-matching in Section 5.5 to "
  "become &quot;a statistical test with proven reliability&quot; before "
  "opening a pull request. Two upgrades were made "
  "(<i>investigations/momentum_crash_significance.py</i>): the volatility "
  "tercile threshold now uses an <b>expanding window</b> (each day's "
  "&quot;high vol&quot; label uses only data through the previous day, "
  "fixing the one look-ahead caveat Section 5.5 flagged), and strategy "
  "returns are regressed on the regime indicators using "
  "<b>Newey-West (HAC) standard errors</b> &mdash; the standard correction "
  "for serial correlation from monthly-rebalanced, overlapping holding "
  "periods, the same style of correction the original Daniel &amp; "
  "Moskowitz paper itself uses. Tests were run at both daily frequency "
  "(HAC lag 21) and monthly frequency (one return per rebalance, HAC lag "
  "6, matching the paper's own testing frequency).")
data_table(
    ["Return series", "Daily: high_vol x bear", "Monthly: bear", "Monthly: vol_rank"],
    [
        ["NSE short leg (theory's predicted locus)", "p=0.57", "p=0.67", "p=0.09 (wrong sign)"],
        ["NSE long leg", "p=0.94", "p=0.0007", "p=0.0046"],
        ["US short leg (theory's predicted locus)", "p=0.65", "p=0.34", "p=0.61"],
        ["US long leg", "p=0.15", "p<0.0001", "p=0.0139"],
    ],
    col_widths=[2.3*inch, 1.5*inch, 1.3*inch, 1.6*inch],
    small=True,
)
p("<b>The specific regime-conditioning mechanism does not survive formal "
  "testing.</b> The short leg &mdash; the one momentum-crash theory "
  "specifically predicts should blow up in high-volatility, bear-market "
  "regimes &mdash; shows no statistically significant regime-conditioning "
  "in either market, at either frequency, in any specification tested. "
  "NSE's short leg even has a wrong-signed coefficient at the 10% level "
  "(losses <i>shrinking</i>, not growing, as volatility rises) &mdash; "
  "evidence against the hypothesis in that specific cut, not for it. The "
  "regime effects that <i>are</i> highly significant (p&lt;0.01, every "
  "specification) show up in the long leg instead &mdash; a far more "
  "mundane explanation (a long-biased position carries positive "
  "market-beta exposure and underperforms generally in bear markets) than "
  "the specific short-squeeze mechanism the hypothesis describes.")
box(
    "What remains statistically ironclad, every specification, both "
    "markets, both frequencies: the long leg's average return is "
    "significantly positive and the short leg's is significantly negative "
    "&mdash; the decomposition itself, not the proposed explanation for "
    "it. With roughly 24 regime-effect coefficients tested across both "
    "frequencies and markets, seeing 2-4 marginally significant results at "
    "the 5-10% level is within what pure chance produces under a true "
    "null &mdash; not meaningfully more than a false-positive rate. As "
    "understood at this point, the long-only recommendation still stood "
    "&mdash; but the project cannot claim to know <i>why</i> the short leg "
    "fails. That remained genuinely open, and Section 5.7 is where it "
    "actually gets resolved, one more check further.",
    title="WHAT SURVIVES AND WHAT DOESN'T, AS UNDERSTOOD AT THIS POINT"
)

h1("5.7  Milestone 6 &mdash; Is it just beta?")
p("Milestone 5 left one basic check untried: does the long leg and the "
  "short leg simply have different, uncontrolled exposure to the market "
  "itself? An equal-weighted decile long-short book makes no attempt to "
  "match the two baskets' market sensitivity. If &quot;losers&quot; (far "
  "from the 52-week high) happen to be higher-beta stocks than "
  "&quot;winners&quot; (near the high), the strategy carries unintended "
  "net market exposure &mdash; and in a market with a strongly positive "
  "average return over the sample (both NSE and the US mirror returned "
  "roughly 19-21% annualized over their windows), that alone would "
  "produce exactly the pattern seen, with no anchoring or crash story "
  "required.")
p("A standard CAPM-style regression was run "
  "(<i>investigations/short_leg_beta.py</i>): leg return = alpha + beta "
  "&times; market return, using the same equal-weighted market proxy and "
  "the same Newey-West correction as Section 5.6, at daily and monthly "
  "frequency, for the long leg, the short leg, and the combined book.")
data_table(
    ["", "NSE daily", "NSE monthly", "US daily", "US monthly"],
    [
        ["Long leg beta (p)", "+0.84 (p<.0001)", "+0.80 (p<.0001)", "+0.82 (p<.0001)", "+0.75 (p<.0001)"],
        ["Short leg beta (p)", "-1.16 (p<.0001)", "-1.19 (p<.0001)", "-1.39 (p<.0001)", "-1.40 (p<.0001)"],
        ["Combined net beta (p)", "-0.32 (p<.0001)", "-0.40 (p=.0007)", "-0.57 (p<.0001)", "-0.70 (p<.0001)"],
        ["Long leg alpha (p)", "p=0.60", "p=0.61", "p=0.76", "p=0.35"],
        ["Short leg alpha (p)", "p=0.15", "p=0.65", "p=0.72", "p=0.95"],
        ["Combined alpha (p)", "p=0.25", "p=0.42", "p=0.69", "p=0.41"],
    ],
    col_widths=[1.7*inch, 1.15*inch, 1.15*inch, 1.15*inch, 1.15*inch],
    small=True,
)
p("<b>This is the answer.</b> All 12 beta coefficients (both legs plus the "
  "combined book, both markets, both frequencies) are highly significant "
  "(p&lt;0.001, all but one below p=0.0001). All 12 alphas are "
  "statistically indistinguishable from zero (p from 0.15 to 0.95). The "
  "&quot;losers&quot; basket consistently carries a larger-magnitude beta "
  "than the &quot;winners&quot; basket &mdash; consistent with the "
  "momentum literature's own description of loser-leg stocks as "
  "higher-beta &mdash; but the consequence here is purely mechanical: "
  "<b>the combined book is not market-neutral. It carries a significant, "
  "unintended net short-beta position (-0.32 to -0.70), and being "
  "structurally short a market that returned ~20% a year is a completely "
  "sufficient explanation for the losses documented in every milestone "
  "above &mdash; no anchoring bias, no crash risk, no value confound "
  "required.</b>")
box(
    "This changes the practical recommendation from Sections 5.5-5.6, not "
    "just adds a footnote. &quot;Trade the signal long-only&quot; rested "
    "on the long leg's raw average return being significantly positive. "
    "That return is real, but this test shows it's consistent with simply "
    "holding an 0.75-0.84-beta long position in a rising market, with "
    "<b>no significant standalone alpha</b> once that exposure is "
    "controlled for. There is currently no evidence, anywhere in this "
    "project, of genuine stock-selection skill in the 52-week-high "
    "signal, in either direction, once market beta is properly accounted "
    "for. The honest recommendation: this signal's long leg is a "
    "reasonable lower-beta way to stay invested, not a demonstrated "
    "behavioral edge. Testing for real, beta-independent skill would "
    "require explicitly beta-neutralizing both legs and re-running this "
    "same regression on the hedged residual &mdash; done next, in "
    "Section 5.8.",
    title="WHAT THIS CHANGES"
)
box(
    "The real methodological lesson: three milestones (2, 3, 5) chased "
    "increasingly sophisticated behavioral and statistical explanations "
    "&mdash; crash windows, a value/growth confound, formal "
    "regime-conditioning significance tests &mdash; before checking the "
    "single most basic hygiene check for any long-short equity backtest: "
    "whether the two legs are beta-matched. They weren't, and that "
    "omission alone explains everything the more exotic hypotheses were "
    "built to explain. Order hypothesis tests from cheapest and most "
    "mechanical to most exotic, not the reverse.",
    kind="fact", title="THE LESSON, AGAIN"
)

h1("5.8  Milestone 7 &mdash; Does real alpha survive an actual beta hedge?")
p("Milestone 6 used one full-sample regression coefficient to estimate "
  "beta and asked whether the leftover average return was significantly "
  "different from zero. That is a legitimate test, but it assumes "
  "constant market exposure across 20+ years, which real betas don't "
  "have. This milestone builds and tests the real thing "
  "(<i>investigations/beta_hedged_backtest.py</i>): at every monthly "
  "rebalance, beta is re-estimated from only the <b>trailing 252 trading "
  "days</b> (roughly one year) of the combined book's own history &mdash; "
  "strictly out-of-sample, never using data from the period being hedged "
  "&mdash; and that beta is used to hedge the <i>next</i> month's daily "
  "returns. This mirrors how a real fund would operationally hedge: "
  "periodic re-estimation applied forward, no look-ahead.")
data_table(
    ["", "NSE (India)", "US (Kaggle mirror)"],
    [
        ["Days covered (needs 252d history)", "5,142", "11,417"],
        ["Rolling hedge beta: mean (std)", "-0.26 (0.31)", "-0.44 (0.50)"],
        ["Correlation of hedged returns w/ market", "-0.07", "-0.02"],
        ["Unhedged ann. return / vol / Sharpe", "-14.3% / 23.9% / -0.53", "-14.7% / 33.5% / -0.30"],
        ["Hedged ann. return / vol / Sharpe", "-7.1% / 22.7% / -0.21", "-7.5% / 31.3% / -0.09"],
        ["Hedged daily return significant?", "p=0.35", "p=0.45"],
        ["Hedged monthly return significant?", "p=0.42", "p=0.17"],
    ],
    col_widths=[2.4*inch, 2.2*inch, 2.2*inch],
    small=True,
)
p("<b>Independent confirmation of Milestone 6, by a stronger method.</b> "
  "The rolling hedge substantially cuts the strategy's correlation with "
  "the market (from strongly negative down to -0.02 to -0.07) and "
  "<b>roughly halves the annualized loss</b> in both markets &mdash; "
  "consistent with a large share of the original loss being mechanical "
  "beta exposure, not something specific to the &quot;losers&quot; "
  "basket. But even after this real, out-of-sample hedge, <b>the "
  "residual return is not statistically distinguishable from zero in "
  "either market, at either frequency</b> (p between 0.17 and 0.45). No "
  "significant alpha, positive or negative, survives once market "
  "exposure is genuinely &mdash; not just statistically &mdash; removed.")
box(
    "Two honest caveats. First, the hedge is imperfect: residual "
    "correlation isn't exactly zero, and the rolling beta itself is "
    "quite unstable over time (its standard deviation is comparable to "
    "or larger than its mean in both markets) &mdash; a real hedging "
    "program would need frequent rebalancing and would incur "
    "transaction costs this script doesn't model. Second, a real, "
    "textbook bug was caught and fixed before any of these numbers were "
    "reported: an early version estimated beta as "
    "<i>np.cov(...) / np.var(...)</i>, but NumPy's <i>cov</i> defaults to "
    "a different degrees-of-freedom convention (ddof=1) than its "
    "<i>var</i> (ddof=0) &mdash; silently inflating every beta estimate "
    "by roughly n/(n-1) (about 0.4% here, immaterial to the conclusion, "
    "but a real bug regardless). Fixed by using an OLS slope instead, "
    "and locked in with a synthetic-fixture test asserting exact beta "
    "recovery on a zero-noise series.",
    kind="fact", title="TWO HONEST CAVEATS"
)

h1("5.9  Milestone 8 &mdash; Does the reversal edge survive a beta check too?")
p("Every beta check so far (Sections 5.7-5.8) was run on the 52-week-high "
  "signal &mdash; the one that <i>lost</i> money. Short-term reversal was "
  "this project's one positive empirical finding (Section 5.3: &quot;the "
  "only signal that actually worked, gross and net of costs,&quot; "
  "Sharpe 0.22 net on NSE), and it was never re-examined for the exact "
  "same uncontrolled-beta artifact that turned out to fully explain the "
  "52-week-high signal's losses. This milestone applies the identical "
  "CAPM-style test (<i>investigations/momentum_reversal_beta.py</i>) to "
  "<b>both</b> remaining signals &mdash; 12-1 momentum and short-term "
  "reversal &mdash; long leg, short leg, and combined book, both markets, "
  "both frequencies: 24 alpha tests in total.")
p("<b>Short-term reversal's &quot;edge&quot; does not survive.</b> Not "
  "one of its 12 alpha tests is significant at conventional levels (all "
  "p&gt;0.10, most p&gt;0.2). The positive Sharpe reported all the way "
  "back in Section 5.3 was &mdash; like the 52-week-high signal's loss "
  "&mdash; a mix of market-beta exposure and noise, not a demonstrated "
  "stock-selection edge. <b>This project's one previously &quot;positive&quot; "
  "empirical result is retracted along with the negative one.</b>")
p("<b>12-1 momentum tells a genuinely different story.</b> On NSE, "
  "momentum shows essentially no significant alpha either (one marginal "
  "hit at the 10% level). But on the <b>US mirror, momentum's long leg "
  "and combined book show real, statistically robust, largely "
  "beta-independent alpha</b>:")
data_table(
    ["", "US long leg", "US combined book"],
    [
        ["Daily alpha (annualized)", "+8.1%/yr, p<.0001", "+12.1%/yr, p=.004"],
        ["Monthly alpha (annualized)", "+9.2%/yr, p<.0001", "+15.3%/yr, p<.0001"],
        ["Beta", "~+1.0 to +1.1", "~-0.05 to -0.24, mostly not significant"],
    ],
    col_widths=[2.3*inch, 2.3*inch, 2.3*inch],
    small=True,
)
p("The combined long-short book's beta is close to zero and, at daily "
  "frequency, not statistically different from zero (p=0.38) &mdash; this "
  "book is close to genuinely market-neutral <b>and</b> has a large, "
  "highly significant positive average return. Unlike the marginal, "
  "scattered hits dismissed as noise in Section 5.6's multiple-testing "
  "discussion, this is a <b>coherent cluster</b>: the same signal, the "
  "same market, the same direction, significant at the 1% level or "
  "better across both frequencies and both the long leg and the combined "
  "book &mdash; a qualitatively different, much less noise-like pattern "
  "than an isolated p&asymp;0.03 hit.")
box(
    "This is the strongest, most credible finding in the entire project "
    "&mdash; but it is one market (the US Kaggle mirror, snapshot ending "
    "2017-11-10), it does not replicate on NSE, and it has not been "
    "checked for the specific decay risk this guide's own limitations "
    "list has flagged since Part III: momentum was published by "
    "Jegadeesh &amp; Titman in 1993, and momentum's premium is well "
    "documented in the literature to have weakened somewhat "
    "post-publication. Whether this specific alpha holds up in a "
    "pre-1994 vs. post-1994 sub-sample split has <b>not yet been "
    "tested</b> &mdash; checked next.",
    title="HOW HARD TO LEAN ON THIS, AS UNDERSTOOD AT THE TIME"
)

h1("5.10  Milestone 9 &mdash; Has US momentum's alpha decayed since publication?")
p("Jegadeesh &amp; Titman published the 12-1 momentum anomaly in the "
  "<i>Journal of Finance</i> in March 1993. A large literature (notably "
  "McLean &amp; Pontiff, &quot;Does Academic Research Destroy Stock "
  "Return Predictability?&quot;, <i>Journal of Finance</i>, 2016) "
  "documents that anomaly returns tend to shrink &mdash; by roughly 26% "
  "after working-paper circulation and ~58% on average after formal "
  "publication &mdash; once traders can crowd into a known effect. This "
  "milestone (<i>investigations/momentum_publication_decay.py</i>) "
  "splits Section 5.9's long leg and combined-book regressions at "
  "<b>1994-01-01</b> (~1 year after publication) and re-runs each half "
  "separately: 251 pre-1994 rebalances vs. 286 post-1994, out of 537 "
  "total.")
data_table(
    ["", "Long leg, pre-1994", "Long leg, post-1994", "Combined, pre-1994", "Combined, post-1994"],
    [
        ["Daily alpha (ann.)", "+9.8%/yr, p=.003", "+6.5%/yr, p=.032", "+16.1%/yr, p=.011", "+8.6%/yr, p=.116 (n.s.)"],
        ["Monthly alpha (ann.)", "+11.4%/yr, p=.0004", "+7.1%/yr, p=.041", "+18.6%/yr, p=.0008", "+13.1%/yr, p=.035"],
    ],
    col_widths=[1.5*inch, 1.4*inch, 1.4*inch, 1.4*inch, 1.4*inch],
    small=True,
)
p("<b>Real, partial decay &mdash; exactly the textbook pattern, not full "
  "disappearance.</b> Every cut shows the alpha shrinking after 1994: "
  "the long leg's daily alpha falls by roughly a third (9.8% to 6.5%/yr) "
  "and its monthly alpha by roughly two-fifths (11.4% to 7.1%/yr); the "
  "combined book decays by 30-47% depending on frequency. That magnitude "
  "lines up closely with McLean &amp; Pontiff's average post-publication "
  "effect across anomalies generally &mdash; this isn't an unusually "
  "large or suspicious decay, it's the expected one. <b>The alpha "
  "survives in three of four cuts</b> (long leg, both frequencies; "
  "combined book, monthly) but <b>loses statistical significance in "
  "one</b> (combined book, daily, p=0.116). The combined book's beta "
  "also drifts from indistinguishable-from-zero pre-1994 (genuinely "
  "market-neutral) to weakly negative post-1994 &mdash; a secondary sign "
  "that the strategy's risk profile itself shifted once the anomaly "
  "became public knowledge.")
box(
    "This project's one durable finding is now stated more precisely: "
    "momentum's long leg (and, less robustly, the market-neutral "
    "combined book) continued to carry statistically significant, "
    "economically smaller alpha through 2017 &mdash; not an un-decayed "
    "anomaly. That is a real, still-standing finding &mdash; three of "
    "four regression cuts remain significant in the post-1994 half "
    "alone, more than 20 years after publication &mdash; but a "
    "meaningfully weaker one than Section 5.9's full-sample numbers "
    "suggested on their own. <b>Size any position on the post-decay "
    "number, not the full-sample one</b> &mdash; the pre-publication half "
    "of the sample describes a market that no longer exists.",
    title="THE HONEST, FINAL-SIZED NUMBER"
)
box(
    "Section 5.11 re-tested this exact post-1994 number with an actual "
    "out-of-sample hedge instead of an in-sample regression, and found it "
    "does not survive. Read the box below as the current, superseding "
    "answer to &quot;is this decayed number real&quot;.",
    kind="fact", title="UPDATE FROM SECTION 5.11"
)

h1("5.11  Milestone 10 &mdash; Does the post-1994 alpha survive an actual out-of-sample hedge?")
p("Section 5.10's decay split is a real improvement over a full-sample "
  "average, but it has the same limitation Section 5.7's beta regression "
  "had before Section 5.8 closed the loop: it fits one beta "
  "<b>in-sample</b>, using the whole post-1994 sub-sample's own data, "
  "then asks whether the average residual differs from zero. A real fund "
  "cannot do that &mdash; it has to estimate beta from only trailing "
  "history and hedge forward. This milestone "
  "(<i>investigations/momentum_hedged_decay_backtest.py</i>) reuses "
  "Section 5.8's rolling, out-of-sample beta hedge (re-estimated every "
  "monthly rebalance from only the preceding 252 trading days, applied "
  "forward, never looking ahead) on the momentum long leg and combined "
  "book, then applies the identical 1994-01-01 split to the resulting "
  "<b>hedged</b> daily return series.")
data_table(
    ["", "Long leg, pre-1994", "Long leg, post-1994", "Combined, pre-1994", "Combined, post-1994"],
    [
        ["Hedged ann. return", "+9.62%/yr", "+3.29%/yr", "+7.93%/yr", "-0.31%/yr"],
        ["Daily alpha (HAC)", "p=.0010", "p=.1485 (n.s.)", "p=.0244", "p=.5900 (n.s.)"],
        ["Monthly alpha (HAC)", "p=.0017", "p=.1886 (n.s.)", "p=.0506 (n.s.)", "p=.5049 (n.s.)"],
    ],
    col_widths=[1.5*inch, 1.4*inch, 1.4*inch, 1.4*inch, 1.4*inch],
    small=True,
)
p("<b>This is a further, sharper correction, not a confirmation of "
  "Section 5.10's &quot;survives in three of four cuts&quot; framing.</b> "
  "Once beta is estimated the way a real fund would have to estimate it "
  "&mdash; from trailing data only, re-hedged every month, never fit on "
  "the same period being tested &mdash; the post-1994 alpha is <b>not "
  "statistically distinguishable from zero in either leg</b>, at either "
  "frequency. The combined book's hedged post-1994 average return is "
  "outright negative. Pre-1994, the same methodology strongly confirms "
  "alpha in both legs (p&le;0.025 in three of four cuts), so the hedge "
  "itself isn't simply too noisy to detect a real effect when one is "
  "present &mdash; it detects it clearly pre-1994 and finds nothing "
  "post-1994. The gap between Section 5.10's &quot;three of four cuts "
  "survive&quot; and this section's &quot;none survive&quot; is entirely "
  "explained by the in-sample vs. out-of-sample distinction: an in-sample "
  "regression can fit the specific quirks of the post-1994 data it's "
  "being tested against, while a rolling hedge estimated only from prior "
  "data cannot.")
box(
    "US 12-1 momentum's alpha was real and strong before 1994 and has "
    "<b>not</b> been demonstrated to survive, in a form an actual fund "
    "could have traded, in the more-than-two-decades since. This "
    "project's single most credible candidate for a genuine, durable "
    "edge does not clear the bar once tested with the same standard of "
    "rigor &mdash; an actual rolling out-of-sample hedge, not a static "
    "or per-era regression coefficient &mdash; that Section 5.8 already "
    "established as this project's own required standard. This doesn't "
    "mean Sections 5.9 and 5.10's findings were wrong for their samples: "
    "the full-sample and pre-1994 alpha are both real and robust. It "
    "means the finding "
    "cannot currently be sized as a forward-looking edge without further "
    "work.",
    title="THE OUT-OF-SAMPLE-CONFIRMED ANSWER, AS FAR AS THIS SECTION TOOK IT"
)
box(
    "Section 5.12 investigated this null result in depth, at explicit "
    "request, rather than stopping here: is it really just the 2009 "
    "momentum crash, or an artifact of the hedge's rolling window? "
    "Neither. Read on for the deeper, still-standing answer.",
    kind="fact", title="UPDATE FROM SECTION 5.12"
)

h1("5.12  Milestone 11 &mdash; Is the post-1994 null result a crash artifact, a hedge artifact, or genuine decay?")
p("Section 5.11 left two objections explicitly untested: is the post-1994 "
  "null result concentrated in a specific regime &mdash; most plausibly "
  "the well-documented 2009 &quot;momentum crash&quot; (Daniel &amp; "
  "Moskowitz, 2016, <i>Review of Financial Studies</i>, where past losers "
  "momentum strategies were underweighting rebounded violently in the "
  "2008-crisis recovery) &mdash; or is it an artifact of the specific "
  "252-trading-day rolling hedge window Sections 5.8 and 5.11 happened to "
  "use? This milestone "
  "(<i>investigations/momentum_decay_regime_analysis.py</i>) runs three "
  "checks on the post-1994 hedged return series to answer both.")
p("<b>Check 1 &mdash; sub-period breakdown.</b> Splitting post-1994 into "
  "five multi-year eras shows a declining trend, not a single bad episode "
  "with a recovery: the long leg's hedged excess return runs +6.5%, "
  "+10.5%, +3.4%, -3.7%, then <b>+0.1%</b> in 2010-2017 &mdash; the most "
  "recent nine years show essentially zero excess return, well after the "
  "2009 crash was over. The combined book shows the same pattern, ending "
  "at <b>-5.1%</b> in 2010-2017.")
p("<b>Check 2 &mdash; explicit crash-window exclusion (March-August "
  "2009).</b> The crash window itself was severe &mdash; the combined "
  "book lost 40.2% cumulatively in those 128 trading days alone. "
  "Excluding it: the long leg's daily alpha p-value improves from 0.149 "
  "to a borderline 0.095 (the crash meaningfully hurt this leg's result), "
  "but the combined book's p-value only improves from 0.590 to 0.334, "
  "nowhere near significance. The crash is a real contributing factor for "
  "the long leg, but does not explain the combined book's null result, "
  "and the continued weakness through 2010-2017 shows the effect is not "
  "fully explained by a single 2009 episode either way.")
p("<b>Check 3 &mdash; hedge rolling-window robustness (126d / 252d / "
  "378d).</b> Re-running the entire hedge with three different lookback "
  "windows: pre-1994 alpha is strongly significant at every window "
  "tested (p&le;0.017, long leg p&le;0.001) and post-1994 alpha is "
  "non-significant at every window tested (p ranges 0.14-0.66 across "
  "both legs and all three windows). The null result is not an artifact "
  "of the specific 252-day window.")
box(
    "This deeper investigation does not reverse Section 5.11's finding "
    "&mdash; if anything it strengthens it. The 2009 momentum crash was "
    "real and severe and meaningfully affected the long leg's result, "
    "but it is not sufficient on its own to explain either leg's "
    "post-1994 null result, and the hedge's design choice is not "
    "driving it either. <b>The era-by-era trend (positive and shrinking "
    "through the 2000s, negative through the crisis, and still flat or "
    "negative for the nine years since) is the signature of genuine, "
    "ongoing decay rather than one bad shock the strategy simply hasn't "
    "yet recovered from.</b> A finding that survives a genuine attempt "
    "to explain it away deserves more confidence, not less.",
    title="THE DEEPER, STILL-STANDING ANSWER"
)
box(
    "Section 5.13 asks whether this whole pattern is unique to momentum, "
    "by applying the same toolkit to the other two US signals. The "
    "answer splits: one signal never had genuine alpha at all; the "
    "other shows the identical decay signature as momentum.",
    kind="fact", title="UPDATE FROM SECTION 5.13"
)

h1("5.13  Milestone 12 &mdash; Is &quot;real pre-1994, decayed since&quot; specific to momentum, or market-wide?")
p("Sections 5.10-5.12 built a specific toolkit &mdash; a rolling, "
  "out-of-sample beta hedge split at 1994-01-01 &mdash; and applied it "
  "only to momentum, because momentum was the one signal with "
  "significant full-sample alpha worth investigating. But the "
  "52-week-high and short-term reversal signals were both declared dead "
  "using a <i>full-sample</i> beta-adjusted regression (Sections "
  "5.7-5.9), which would hide the exact same pattern found for momentum: "
  "real, significant alpha in an early era, averaged down to statistical "
  "noise by a decayed later era. This milestone "
  "(<i>investigations/all_signals_decay_analysis.py</i>) applies the "
  "identical pre/post-1994 hedge to <b>all three</b> US signals &mdash; "
  "not to re-answer an already-settled question (NSE momentum's "
  "full-sample null was already established in Section 5.9, so "
  "re-running the hedge there would add nothing), but to ask a genuinely "
  "new one: is the decay pattern unique to momentum, or a broader "
  "feature of the US market?")
data_table(
    ["Signal / leg", "Pre-1994 ann. ret / p", "Post-1994 ann. ret / p"],
    [
        ["12-1 momentum, long leg", "+9.62%/yr, p=.001", "+3.29%/yr, p=.149"],
        ["12-1 momentum, combined", "+7.93%/yr, p=.024", "-0.31%/yr, p=.590"],
        ["52-week-high, long leg", "-0.21%/yr, p=.704", "-2.06%/yr, p=.468"],
        ["52-week-high, combined", "-8.46%/yr, p=.776", "-6.68%/yr, p=.401"],
        ["Reversal, long leg", "+5.31%/yr, p=.046", "+0.25%/yr, p=.629"],
        ["Reversal, combined", "-0.41%/yr, p=.293", "-0.57%/yr, p=.576"],
    ],
    col_widths=[2.3*inch, 2.4*inch, 2.4*inch],
    small=True,
)
p("<b>Two genuinely different stories, not one.</b> The 52-week-high "
  "signal shows <b>no significant alpha in either era, in any leg</b> "
  "&mdash; confirming Sections 5.7-5.8's conclusion that this signal "
  "never had genuine stock-selection skill in either direction; its "
  "full-sample &quot;loss&quot; was uncontrolled beta from the start, "
  "not a decayed edge. <b>Short-term reversal's long leg tells a "
  "different story: it shows the identical decay pattern as "
  "momentum</b> &mdash; a real, statistically significant pre-1994 "
  "alpha (+5.31%/yr, p=0.046) that decays completely to noise post-1994 "
  "(+0.25%/yr, p=0.629). This was invisible in Section 5.9's full-sample "
  "regression, which averaged the genuine early effect with the decayed "
  "later one and correctly found no full-sample significance &mdash; "
  "but &quot;no full-sample significance&quot; is not the same claim as "
  "&quot;never had a genuine edge,&quot; and this milestone shows "
  "reversal's long leg did.")
box(
    "Section 5.9's headline claim &mdash; that reversal's &quot;edge&quot; "
    "did not survive the same scrutiny applied to the negative one "
    "&mdash; is accurate for the full-sample regression it ran, but "
    "incomplete: reversal's long leg was never pure noise, it was a "
    "real, decayed effect exactly analogous to momentum's, just never "
    "tested with the era-split methodology that only existed starting "
    "at Section 5.10. <b>The &quot;real pre-1994, decayed since&quot; "
    "pattern is not a momentum-specific quirk &mdash; it appears in two "
    "of this project's three signals' long legs (momentum and reversal) "
    "and is absent from the third (52-week-high, which never had genuine "
    "alpha at all)</b>, consistent with a market-wide explanation "
    "&mdash; the same 1990s-2000s scaling-up of quantitative, "
    "cross-sectional equity strategies this project's own case studies "
    "(LTCM, the 2007 Quant Quake) already document as having transformed "
    "US equity markets over exactly this period &mdash; rather than an "
    "idiosyncratic property of momentum alone.",
    title="TWO SIGNALS, ONE SHARED STORY"
)
box(
    "Section 5.14 asks a sharper question: not just whether there was a "
    "decay, but exactly how fast, and when it actually crossed zero "
    "&mdash; quantified directly, instead of assumed from a single "
    "arbitrary cutoff date. The answer reshapes how momentum's story "
    "should be told.",
    kind="fact", title="UPDATE FROM SECTION 5.14"
)

h1("5.14  Milestone 13 &mdash; Quantifying the decay: a continuous rate, not a binary 1994 cut")
p("Every decay test so far (Sections 5.10-5.13) used a single, somewhat "
  "arbitrary binary split &mdash; 1994-01-01, chosen as &quot;~1 year "
  "after Jegadeesh &amp; Titman's 1993 publication.&quot; That answers "
  "&quot;was there a difference before vs. after this one date,&quot; "
  "not &quot;how fast did the edge erode, or when did it actually run "
  "out.&quot; This milestone "
  "(<i>investigations/decay_rate_estimation.py</i>) quantifies the decay "
  "directly: for each signal's out-of-sample-hedged long leg, over the "
  "<i>full</i> sample (no pre/post split), it regresses hedged_return "
  "= alpha + slope &times; (years since hedge coverage began), with HAC "
  "standard errors. <i>Slope</i> is a direct, continuously-estimated "
  "annual decay rate with its own p-value, and (alpha, slope) together "
  "imply a zero-crossing date.")
data_table(
    ["Signal", "alpha (start, ann.)", "slope (change/yr)", "Zero-crossing"],
    [
        ["12-1 momentum, long leg", "+12.65%/yr, p=.008", "-0.23%/yr, p=.152 (n.s.)", "ill-conditioned"],
        ["Reversal, long leg", "+13.46%/yr, p=.014", "-0.41%/yr, p=.026", "2004-11-22"],
    ],
    col_widths=[1.9*inch, 1.7*inch, 2.0*inch, 1.5*inch],
    small=True,
)
p("<b>Momentum's decay is not a smooth line &mdash; it does not even "
  "pass as one.</b> The full-sample linear-trend slope for momentum's "
  "long leg is <i>not</i> statistically significant (p=0.15 daily, "
  "p=0.25 monthly): a single straight line across the whole 1972-2017 "
  "hedged return series is a poor fit, not because the effect didn't "
  "decay, but because it didn't decay <i>smoothly</i>. A 5-year "
  "rolling-window trajectory shows why: annualized hedged returns stay "
  "consistently strong (roughly +4% to +22%/yr, noisy but never close "
  "to zero) all the way from the 1970s through the window ending "
  "January 2008 &mdash; including every year of the supposed "
  "&quot;post-1994 decay&quot; period &mdash; and only then drop "
  "sharply, turning negative for every rolling window from 2009 "
  "onward. <b>Splitting explicitly at September 2008 instead of "
  "January 1994 gives a far cleaner separation</b>: pre-Sept-2008 "
  "long-leg alpha is +8.02%/yr, p=0.0005 (n=8,983 days) vs. "
  "post-Sept-2008 alpha of -0.56%/yr, p=0.998 (n=2,309 days, utterly "
  "indistinguishable from zero) &mdash; a starker divide than the 1994 "
  "split produced (p=0.001 pre-94 vs. p=0.149 post-94). This refines, "
  "rather than contradicts, Sections 5.10-5.12's momentum finding: the "
  "direction was right, but describing it as gradual, publication-"
  "driven decay since 1994 is not well supported by the data's actual "
  "shape. A sudden regime shift around the 2008-09 financial crisis "
  "&mdash; plausibly the same 2009 momentum crash examined directly in "
  "Section 5.12, or the post-crisis scaling-up of quantitative "
  "strategies &mdash; is a better-supported story for <i>when and "
  "how</i> momentum's edge disappeared than slow 1990s crowding.")
p("<b>Reversal's decay is closer to the smooth story the "
  "publication-decay literature predicts.</b> Its full-sample linear "
  "trend <i>is</i> statistically significant (slope -0.41%/yr daily, "
  "p=0.026; -0.39%/yr monthly, p=0.027), with an implied zero-crossing "
  "around November 2004. The rolling trajectory confirms a genuine "
  "decline, though a real one, not a perfectly straight line: annualized "
  "returns fall from a very strong +27%/yr in the late 1970s to negative "
  "territory by the mid-1980s, stay negative through the 1990s, then "
  "show an unexplained recovery bump (+6% to +14%/yr) from 2000-2004 "
  "before declining again through the 2010s. The overall downward trend "
  "is real and significant, but &quot;smooth, monotonic decay&quot; "
  "oversimplifies a pattern that includes a multi-year partial recovery "
  "in the middle.")
box(
    "Quantifying the decay rate, rather than assuming a fixed cutoff, "
    "shows the two signals' declines have genuinely different shapes. "
    "Reversal's long leg decays roughly the way the publication-decay "
    "literature describes &mdash; a real, continuous, statistically "
    "significant downward trend, crossing zero around 2004. Momentum's "
    "long leg does not: it held essentially flat and strong for 35+ "
    "years and then broke sharply around the 2008-09 financial crisis, "
    "a pattern a continuous linear-decay model fits poorly and a "
    "structural-break framing fits well. <b>Treat momentum's weakness "
    "as &quot;broke around 2008-09,&quot; not &quot;has been gradually "
    "decaying since 1994&quot; &mdash; the earlier milestones' binary "
    "split happened to land on the right side of the qualitative story "
    "without correctly identifying its shape or timing.</b>",
    title="RIGHT DIRECTION, WRONG SHAPE"
)
box(
    "Section 5.15 formalizes the &quot;broke around 2008-09&quot; claim "
    "with an actual structural-break test instead of a descriptive "
    "comparison &mdash; and the formal result is more conservative than "
    "this section's own framing suggested.",
    kind="fact", title="UPDATE FROM SECTION 5.15"
)

h1("5.15  Milestone 14 &mdash; A formal structural-break test, not a descriptive comparison")
p("Section 5.14's &quot;split at September 2008 instead of 1994&quot; "
  "comparison was descriptive: the break date was chosen <i>after</i> "
  "looking at momentum's rolling-window trajectory, and testing "
  "&quot;the best of many candidate split dates&quot; is expected to "
  "look impressive even under a null of no true break &mdash; a "
  "comparison, not a test. This milestone "
  "(<i>investigations/structural_break_test.py</i>) runs two properly "
  "specified tests instead.")
p("<b>Method A</b> &mdash; a literature-motivated Chow-style test at a "
  "single, pre-specified date (2008-09-01, motivated externally by "
  "Daniel &amp; Moskowitz's (2016) documented 2009 momentum-crash "
  "episode, not by inspecting this project's own plot). A single "
  "pre-specified date needs no multiple-testing correction.")
p("<b>Method B</b> &mdash; a Quandt-Andrews-style sup-Wald test that "
  "does <i>not</i> assume a break date. It searches every candidate "
  "date in the central 70% of the sample (15% trimmed from each end, "
  "standard Andrews (1993) practice), computes the HAC-robust "
  "level-shift statistic at each one, and takes the maximum &mdash; "
  "both its value and which date it occurs at. Because searching many "
  "candidates inflates the false-positive rate of a naive comparison, "
  "this project's sandboxed environment (which cannot fetch Andrews' "
  "published critical-value tables) instead builds its own empirical "
  "null: fit a no-break model to the real data, block-bootstrap its "
  "residuals (400 draws, 12-month blocks, preserving autocorrelation), "
  "rerun the full candidate search on each synthetic no-break series, "
  "and compare the real maximum statistic to that simulated null "
  "distribution.")
data_table(
    ["", "Momentum", "Reversal"],
    [
        ["Method A: shift at 2008-09, daily", "-9.31%/yr, p=.026", "-4.02%/yr, p=.337"],
        ["Method A: shift at 2008-09, monthly", "-9.10%/yr, p=.052", "-3.90%/yr, p=.316"],
        ["Method B: data-driven break date", "2010-12-31", "1980-08-29"],
        ["Method B: sup|t| (bootstrap p)", "2.771 (p=.138, n.s.)", "3.369 (p=.048)"],
    ],
    col_widths=[2.4*inch, 2.2*inch, 2.2*inch],
    small=True,
)
p("<b>Momentum: the specific 2008 hypothesis holds; an unconstrained "
  "search does not decisively confirm it as the dominant break.</b> "
  "Method A confirms a real, statistically significant level shift "
  "specifically at the literature-motivated date (p=0.026 daily). But "
  "Method B's unconstrained search finds its single best-fitting break "
  "at <b>December 2010, not September 2008</b> &mdash; 27 months later "
  "&mdash; and that best-fit statistic is <i>not</i> significant once "
  "corrected for having searched ~375 candidate dates (bootstrap "
  "p=0.138). This nuances Section 5.14's framing: there is good "
  "evidence of weakening tied specifically to the 2008-09 crisis "
  "window, but the data does not decisively pin down one single, "
  "dominant structural break &mdash; a specific, externally-motivated "
  "hypothesis survives; an unconstrained &quot;find the best break "
  "anywhere&quot; search does not clearly beat noise.")
p("<b>Reversal: no evidence for a 2008-tied break &mdash; but a "
  "genuine, significant break turns up much earlier, around 1980.</b> "
  "Method A finds nothing at 2008 (expected: Section 5.14 already "
  "showed reversal's decline predates the financial crisis by "
  "decades). Method B's unconstrained search finds a significant break "
  "(bootstrap p=0.048) at <b>August 1980</b> &mdash; the early, sharp "
  "decline from the extraordinarily high +27%/yr level of the late "
  "1970s that Section 5.14's rolling trajectory showed, not a smoothly "
  "accumulating multi-decade slope. This further refines Section "
  "5.14's &quot;smooth, statistically significant linear decay&quot; "
  "framing for reversal: part of that significant linear trend is "
  "better described as one sharp early-1980s adjustment than "
  "continuous decay across the whole sample.")
box(
    "Neither signal's decline is best described as either a perfectly "
    "smooth trend or a single obvious break once tested formally and "
    "correctly for multiple-testing bias. Momentum shows a real, "
    "hypothesis-confirmed weakening at the 2008-09 crisis, but not an "
    "unambiguous single structural break when searched for without "
    "that prior. Reversal shows a genuine, statistically significant "
    "break, but decades earlier than any milestone had proposed, "
    "complicating rather than confirming the smooth-decay story. "
    "<b>Both results are more conservative and more precisely "
    "qualified than any earlier milestone's framing</b> &mdash; "
    "consistent with this project's repeated experience that the more "
    "rigorous test usually narrows, rather than confirms, the simpler "
    "story that preceded it.",
    title="THE FORMAL, MORE CONSERVATIVE ANSWER"
)

# MARKER_END_PART5

# ============================================================ PART VI
story.append(PageBreak())
toc_entry("Part VI &mdash; From Research to Practice", 0, "part6")
part("Part VI &mdash; From Research to Practice")

h1("6.1  An investment framework: the Behavioral Mispricing Score")
p("The composite score from Part III.4 is designed to be used as a "
  "<b>tilt or flag layered on top of an existing fundamentals-driven "
  "screen</b>, never as a standalone strategy &mdash; the same pattern every "
  "fund in Part IV.5 actually follows (they all pair behavioral signals with "
  "fundamental discipline, not raw signal-following). A stock that screens well "
  "fundamentally <i>and</i> sits in the top behavioral decile is a stronger "
  "candidate than either signal alone would suggest; a stock flagged as a "
  "behavioral &quot;loser&quot; deserves a second look even when its "
  "fundamentals look fine.")
box(
    "Rule, stated as a direct consequence of Part V.3's finding, not as generic "
    "best practice borrowed from a textbook: <b>never trust a blended score "
    "without checking what each of its components does on its own.</b> The "
    "composite here looked mediocre; decomposing it found one component "
    "actively losing money with a 97% drawdown and another that at first "
    "looked like a genuine, positive, cost-adjusted edge (a claim Part V.9 "
    "later retracted). Any score this project's code produces should be "
    "reported and validated component-by-component before a blended "
    "version of it is trusted for a decision.",
)
p("<b>Decompose the legs before discarding a signal &mdash; still correct, "
  "but the fix isn't &quot;long-only&quot; after all.</b> The long leg's "
  "raw average return is significantly positive, the short leg's "
  "significantly negative, in every specification tested (Part V.6). That "
  "decomposition rule stands. What it was used to conclude did not: Part "
  "V.7 found both legs' significant raw returns are fully explained by "
  "uncontrolled market-beta exposure (long &asymp;+0.8 beta, short "
  "&asymp;-1.2 to -1.4 beta) in markets that rose ~20%/year over the "
  "sample &mdash; once beta is controlled for, <b>alpha is insignificant "
  "in all 12 regressions tested, both legs, both markets, both "
  "frequencies.</b> There is currently no demonstrated stock-selection "
  "skill in this signal, in either direction. <b>Corrected rule:</b> this "
  "signal is not a demonstrated source of alpha as currently built; using "
  "it as a behavioral tilt requires beta-neutralizing both legs first and "
  "re-testing the hedged residual for alpha &mdash; done in Part V.8, "
  "which independently confirmed the same conclusion with an actual "
  "rolling, out-of-sample hedge rather than a single regression "
  "coefficient. And more generally: check for a beta mismatch "
  "between a long-short book's legs before reaching for a behavioral "
  "explanation, not after three rounds of increasingly exotic ones.")
box(
    "Part V.9 applied the same beta check to the other two signals, and "
    "found something important in both directions. Short-term reversal "
    "&mdash; this project's one previously-reported positive finding "
    "&mdash; failed every one of its 12 alpha tests once beta was "
    "controlled for. It had never been re-checked with the standard of "
    "rigor developed for the losing signal; once it finally was, it "
    "didn't hold up either. <b>Rule: a positive finding earns no "
    "exemption from the checks a negative one gets.</b> But 12-1 momentum, "
    "tested the same way, showed something new: on the US mirror, its "
    "long leg and combined book carry large, highly significant alpha "
    "(annualized roughly +8-15%/yr, p&lt;0.01 in every cut), with the "
    "combined book's beta close to zero. This is currently the project's "
    "single most credible candidate for a genuine, demonstrated edge "
    "&mdash; not replicated on NSE, but a coherent, high-significance "
    "cluster rather than the isolated marginal hits this project has "
    "learned to distrust.",
    kind="fact", title="UPDATE FROM PART V.9"
)
box(
    "Part V.10 checked the one thing Part V.9 left open: publication "
    "decay. Real, textbook-consistent decay was found &mdash; alpha down "
    "30-47% post-1994, one cut (combined book, daily) losing "
    "significance entirely &mdash; but not disappearance: three of four "
    "cuts remain significant through 2017 alone. <b>Size any claim about "
    "this finding on the decayed, post-1994 number, not the full-sample "
    "one.</b>",
    kind="fact", title="UPDATE FROM PART V.10"
)
box(
    "Part V.11 re-tested Part V.10's post-1994 number with an actual "
    "rolling, out-of-sample hedge (Part V.8's methodology) instead of an "
    "in-sample regression, and found it does not survive: post-1994 "
    "alpha is not statistically significant in either leg, at either "
    "frequency, once beta is estimated only from trailing data and "
    "re-hedged monthly. Pre-1994 alpha remains strongly confirmed. Treat "
    "this project's momentum finding as real and robust pre-1994, and "
    "not currently demonstrated to be forward-sizeable in the "
    "post-publication era.",
    kind="fact", title="UPDATE FROM PART V.11"
)
box(
    "Part V.12 dug into that null result at explicit request rather than "
    "stopping here: is it really just the 2009 momentum crash, or the "
    "hedge's rolling window? Neither explained it &mdash; a five-era "
    "breakdown showed ongoing decay through 2017, well after 2009, and "
    "the result held across three different hedge windows. This is the "
    "most rigorous read of momentum specifically: genuine, strong "
    "pre-1994 alpha, and genuine, ongoing decay since &mdash; not a "
    "temporary shock the strategy is due to recover from.",
    kind="fact", title="UPDATE FROM PART V.12"
)
box(
    "Part V.13 then asked whether this whole pattern is unique to "
    "momentum. It isn't: short-term reversal's long leg shows the "
    "identical &quot;real pre-1994, decayed since&quot; signature "
    "(p=0.046 pre-1994, p=0.629 post), invisible inside Part V.9's "
    "full-sample null. 52-week-high, by contrast, shows no significant "
    "alpha in either era &mdash; it never had genuine skill at all. "
    "The decay pattern is market-wide, appearing in two of three "
    "signals' long legs, not a momentum idiosyncrasy &mdash; and "
    "Part V.9's reversal retraction should be read as accurate at the "
    "full-sample level but incomplete.",
    kind="fact", title="UPDATE FROM PART V.13"
)
box(
    "Part V.14 then quantified the decay rate directly instead of "
    "trusting the 1994 cutoff, and found the two signals decay in "
    "genuinely different shapes. Reversal's decline is a real, smooth, "
    "statistically significant linear trend (zero-crossing "
    "~November 2004). Momentum's is not smooth at all: alpha stayed "
    "flat and strong through 2008, then broke sharply. Momentum's "
    "weakness is better described as a 2008-09 regime shift than "
    "gradual 1994-onward decay &mdash; the 1994 split was directionally "
    "right but misdescribed the mechanism.",
    kind="fact", title="UPDATE FROM PART V.14"
)
box(
    "Part V.15 then formalized that 2008-09 claim with an actual "
    "structural-break test rather than a descriptive comparison. A "
    "single, literature-motivated Chow test at 2008-09-01 does confirm "
    "a real break in momentum (p=0.026) &mdash; but an unconstrained "
    "search corrected for multiple testing finds its best-fitting "
    "break 27 months later (Dec 2010) and that maximum is not "
    "significant (bootstrap p=0.138). Reversal shows the opposite: "
    "nothing at 2008, but a genuine, significant break (bootstrap "
    "p=0.048) around <b>August 1980</b>, not a smooth 30-year decline. "
    "<b>Both stories are more conservative once tested formally: a "
    "specific, externally-motivated hypothesis can survive even when "
    "an unconstrained search for &quot;the best break anywhere&quot; "
    "does not.</b>",
    kind="fact", title="UPDATE FROM PART V.15"
)

h1("6.2  A risk-management playbook, from the Q1 simulation")
bullets([
    "<b>Never calibrate tail risk on a calm-regime correlation matrix alone.</b> "
    "The Part III simulation shows a Gaussian VaR model calibrated on "
    "&quot;normal&quot; data understates the true 99.9% tail loss by roughly "
    "1.3x, purely because it cannot see correlations rising toward 1 under "
    "stress. Any leveraged strategy needs a stress-regime correlation scenario "
    "as a second, explicit check, not just a historical-calibration number.",
    "<b>Leverage does not just scale losses &mdash; it changes which losses are "
    "survivable.</b> LTCM's underlying spread moves were not physically "
    "unprecedented; 25:1+ leverage turned a bad quarter into insolvency. "
    "Position and leverage limits should be set against the stress-regime tail "
    "estimate, not the calm-regime one.",
    "<b>Crowding is a correlation risk invisible from inside your own "
    "portfolio.</b> The 2007 Quant Quake shows a well-diversified-looking book "
    "can be secretly correlated with every other fund running a similar "
    "signal. A practical mitigant: track how crowded a factor appears to be "
    "(e.g., the realized correlation of a strategy's returns to a public "
    "factor index) and de-risk when it's high, independent of the strategy's "
    "own apparent confidence.",
    "<b>A winning streak is not evidence against tail risk.</b> Amaranth's "
    "Brian Hunter had a strong record before the 2006 blowup; recent success "
    "under one regime is weak evidence a concentrated position is safe under a "
    "different one. Concentration limits need an explicit override that "
    "doesn't relax just because a book has been working.",
    "<b>Treat &quot;the model says it's fine&quot; as a hypothesis, not a "
    "fact</b> &mdash; especially near known regime-change triggers (sovereign "
    "defaults, liquidity crunches, crowded-factor unwinds). This is the "
    "project's central thesis applied reflexively to its own tooling, not just "
    "to the markets it studies.",
    "<b>The Q1 mechanism and the Q2 investigation asked the same question "
    "&mdash; Q1 answered it with a simulation, Q2's real data gave a more "
    "honest, weaker answer.</b> Part III's simulation showed, stylized, that "
    "tail risk compounds when volatility and correlation rise together. Part "
    "V.5's momentum-crash-risk investigation set out to find the same "
    "signature in a real backtest, and a first descriptive pass looked like "
    "it had. Formal significance testing (Part V.6) did not confirm it. Any "
    "short position built on a behavioral signal should still be "
    "regime-tested before being sized &mdash; that precaution doesn't depend "
    "on this specific mechanism being confirmed &mdash; but &quot;regime-"
    "tested&quot; has to mean the HAC-regression version, not the "
    "regime-bucket version, given what happened here when the two "
    "disagreed.",
    "<b>A compelling descriptive pattern is a hypothesis, not a finding "
    "&mdash; this project produced its own cautionary tale.</b> Part V.5's "
    "regime-bucket comparison looked like a clean, four-signature "
    "confirmation of momentum-crash risk. Formal HAC-regression testing at "
    "daily and monthly frequency (Part V.6) found none of the "
    "regime-conditioning coefficients significant in the leg the theory "
    "actually predicts, in either market. Both analyses used the same "
    "underlying data; only the statistical rigor differed. Never size a "
    "position, write a risk limit, or make a claim based on a descriptive "
    "regime split alone &mdash; run the regression with proper standard "
    "errors first, and expect a real chance the compelling-looking pattern "
    "won't survive it.",
    "<b>The cheapest test is the one to run first, and this project ran it "
    "last.</b> Three escalating hypotheses (crash-window concentration, a "
    "value/growth confound, formal momentum-crash regime-conditioning) "
    "were tested across three milestones before Part V.7 finally ran a "
    "plain CAPM beta regression &mdash; the single cheapest, most standard "
    "check for any long-short book &mdash; and found the entire answer in "
    "it: an uncontrolled beta mismatch between the legs, fully explaining "
    "every prior milestone's numbers, no behavioral story needed. Order "
    "hypothesis tests from cheapest and most mechanical to most exotic, "
    "not the reverse; a beta regression takes minutes and rules out the "
    "most common cause of surprising long-short performance before any "
    "more elaborate explanation is worth reaching for.",
    "<b>A risk process that only re-tests its losers eventually trusts a "
    "winner it never should have.</b> Every rigor upgrade through Part "
    "V.8 was applied to the signal that was losing money. The one signal "
    "reported as a genuine edge (reversal) rode on its original, less "
    "rigorous validation for six milestones before anyone checked it the "
    "same way. Part V.9 finally did, and it didn't hold up. Schedule "
    "periodic re-validation of every &quot;confirmed&quot; edge under "
    "your <i>current</i> standard of rigor, not just the standard at the "
    "time it was confirmed &mdash; a standard that improves over a "
    "book's life should apply retroactively, especially to positions "
    "still being sized on the old conclusion.",
    "<b>Size a position on the decayed number, not the full-sample "
    "number &mdash; and check that decayed number was itself estimated "
    "out-of-sample.</b> Part V.10 split the one surviving edge (US "
    "momentum) at its 1993 publication date and found real decay: alpha "
    "down 30-47% post-1994, one cut losing significance outright. That "
    "was already a large correction &mdash; but it was still an "
    "in-sample estimate. Part V.11 re-tested the same period with an "
    "actual rolling, out-of-sample hedge and found the post-1994 alpha "
    "does not survive at all, in either leg. The full-sample average was "
    "never the honest number to size against once a signal is old enough "
    "to have a publication date, and an in-sample per-era regression "
    "isn't the final word either &mdash; only a hedge that could "
    "actually have been traded forward tells you what capital entering "
    "today can expect.",
    "<b>Before accepting a null result, rule out the obvious &quot;maybe "
    "it's just one bad episode&quot; and &quot;maybe it's a methodology "
    "artifact&quot; objections &mdash; and if it survives both, treat "
    "that as the null result getting stronger, not weaker.</b> Part V.12 "
    "tested whether Part V.11's post-1994 null result was really just "
    "the 2009 momentum crash, and whether it depended on the specific "
    "hedge window chosen. Neither objection explained it: the era-by-era "
    "trend showed ongoing decay through 2017, well after 2009, and the "
    "result was identical across three different hedge windows. A "
    "finding that survives a genuine attempt to explain it away deserves "
    "more confidence, not less &mdash; the temptation after an "
    "unwelcome result is to look for the one adjustment that makes it go "
    "away; running that check honestly, and reporting it even when it "
    "doesn't help, is what separates a stress-test from a fishing "
    "expedition.",
    "<b>A full-sample &quot;no significant alpha&quot; verdict does not "
    "mean a signal was never real &mdash; check whether it's actually "
    "two eras averaging to zero before writing it off entirely.</b> Part "
    "V.9 declared short-term reversal fully retracted based on a "
    "full-sample regression, the technically correct read of that "
    "specific test. Part V.13 applied the era-split toolkit built for "
    "momentum and found reversal's long leg had been genuinely, "
    "significantly positive pre-1994 and decayed to noise since &mdash; "
    "the same pattern as momentum, hidden inside a full-sample average "
    "that happened to net out near zero. Retest every full-sample null "
    "result from before your era-split toolkit existed with that "
    "toolkit, not just your full-sample findings &mdash; a &quot;no "
    "effect on average&quot; verdict can quietly contain a real, "
    "decayed effect that a single-number summary cannot distinguish "
    "from a signal that was simply never real.",
    "<b>A binary before/after split can get the direction right while "
    "getting the mechanism wrong &mdash; quantify the trend continuously "
    "before naming a cause.</b> Part V.14 fit a continuous linear decay "
    "rate to momentum's and reversal's hedged long legs instead of "
    "trusting the 1994 publication-date cutoff. Reversal's decay turned "
    "out to be genuinely smooth and statistically significant, "
    "consistent with the publication-decay story. Momentum's did not: "
    "its linear trend was not significant, because the real pattern is "
    "a sharp break around the 2008-09 financial crisis, not a gradual "
    "erosion starting in 1994. Once a binary split finds a real effect, "
    "don't stop there &mdash; fit a continuous trend and inspect a "
    "rolling, non-parametric trajectory to check whether the story "
    "you're about to tell actually matches the shape of the data, or "
    "just happens to fall on the correct side of an arbitrary cutoff.",
    "<b>Even a data-driven, non-arbitrary date can still be the wrong "
    "test &mdash; correct for the search itself before trusting "
    "it.</b> Part V.14 picked September 2008 by eyeballing a rolling "
    "trajectory, which is a comparison, not a test: it doesn't say "
    "whether that split is meaningfully better than what chance alone "
    "would produce from searching many candidate dates. Part V.15 ran "
    "the actual test two ways: a single pre-registered date (motivated "
    "by an external, published crash episode, not this project's own "
    "plot) confirmed momentum's break; an unconstrained search over "
    "~375 candidate dates, corrected via bootstrap for having searched "
    "that many, did not decisively confirm any single dominant break "
    "(its own best-fit date, December 2010, wasn't even the one the "
    "earlier milestone had proposed). A hypothesis motivated by an "
    "external, independent source can be tested directly and cheaply; "
    "a hypothesis motivated by your own data requires a "
    "multiple-testing-corrected test before it earns the same "
    "confidence &mdash; and expect the corrected version to be "
    "measurably more conservative.",
])

h1("6.3  A standalone business idea: decomposed behavioral signal analytics")
p("Off-the-shelf factor data (momentum, value, quality) is typically sold by "
  "large vendors as pre-blended, black-box composites, priced for institutions "
  "with large budgets. Smaller systematic funds, family offices, independent "
  "RIAs, and research desks either cannot afford that tier, or cannot see "
  "<i>inside</i> the composite to know which component is actually carrying "
  "the edge on their specific universe &mdash; exactly the failure mode this "
  "project hit directly on the NSE data (Part V.3), and hit again when its "
  "own first-reported positive finding (reversal) failed a beta check the "
  "project hadn't yet thought to run (Part V.9). Decomposed, beta-adjusted "
  "validation is what surfaced the project's one genuine finding (US "
  "momentum) instead of its retracted one.")
box(
    "This idea was originally framed as an extension of the specific software "
    "platform this research happened to be built alongside. That framing was "
    "dropped after explicit feedback that the business idea should stand on "
    "its own, independent of any particular existing product. The pitch below "
    "reflects that: a standalone service, differentiated on the same "
    "transparency principle (decomposed, auditable signals; never a "
    "pre-blended black box) that Part V.3's finding demonstrated the value of "
    "directly.",
)
p("<b>The product:</b> a subscription analytics service with two parts &mdash; "
  "a <b>signal side</b> (the momentum / 52-week-high / reversal library, run "
  "per client against <i>their</i> universe, reported as separate, "
  "individually-backtested components, never pre-blended, each with its own "
  "beta-regression alpha/beta breakdown so a client can see whether "
  "performance is genuine stock-selection skill or just uncontrolled market "
  "exposure &mdash; Part V.7's finding made this check a required feature, "
  "not an optional one &mdash; and, for any signal drawn from published "
  "academic research, a pre/post-publication decay split re-confirmed "
  "with an actual out-of-sample hedge, not just an in-sample regression "
  "(Parts V.10-11's check), a second differentiator most factor-data "
  "vendors don't surface at all) and a <b>risk side</b> (the regime-switching "
  "stress-VaR methodology from Part III, run against a client's actual "
  "position correlations and leverage, reporting calm-regime vs. "
  "stress-regime tail loss side by side).")
p("<b>Target customer:</b> small-to-mid systematic equity funds, family "
  "offices, and independent RIAs priced out of institutional factor-data tiers "
  "but sophisticated enough to want decomposed, re-validated signals rather "
  "than a black box; secondarily, finance graduate programs and CFA/PE prep "
  "courses, as a teaching tool for the exact &quot;don't trust the "
  "blend&quot; lesson this project surfaced.")
p("<b>Revenue model:</b> a per-seat analytics subscription, tiered by number "
  "of tracked universes/portfolios &mdash; the same go-to-market as existing "
  "quant factor-data vendors, priced and scoped for the segment those vendors "
  "serve poorly, differentiated specifically on transparency: every number "
  "traces to runnable code and a stated backtest window, not a proprietary "
  "methodology.")
p("<b>Moat:</b> not the signals themselves (all public, published research) "
  "&mdash; the moat is the discipline of per-client, per-universe decomposed "
  "validation instead of a generic pre-blended score, which is exactly what a "
  "larger vendor selling a standardized product across all clients "
  "structurally cannot do cheaply.")

# MARKER_END_PART6

# ============================================================ PART VII
story.append(PageBreak())
toc_entry("Part VII &mdash; Limitations and Honesty Statement", 0, "part7")
part("Part VII &mdash; Limitations and Honesty Statement")
p("Stated together in one place because a project whose entire thesis is "
  "&quot;don't trust a model's output just because it looks rigorous&quot; "
  "owes the same discipline to its own outputs.")
bullets([
    "<b>Survivorship bias.</b> Both the NSE mirror and the US mirror located in "
    "milestone 3 use a present-day-chosen company list, not point-in-time "
    "index membership. A rigorous version needs a survivorship-bias-free "
    "universe (e.g., CRSP, or a maintained point-in-time constituents file).",
    "<b>Data provenance.</b> Both the NSE and US mirrors are personal, "
    "community-uploaded GitHub repositories, not official exchange or "
    "licensed vendor feeds. Results from them are a genuine methodology "
    "demonstration on real prices, not investment-grade research, until "
    "cross-checked against an official source.",
    "<b>Momentum and reversal did not replicate consistently</b> across the "
    "two markets tested (Part V.4) &mdash; treat either result, in isolation, "
    "as provisional rather than a confirmed anomaly. Only the 52-week-high "
    "signal's loss held up in both.",
    "<b>Short-term reversal's positive result is retracted at the "
    "full-sample level (Part V.9) &mdash; but its long leg specifically "
    "is a decayed, not a never-real, effect (Part V.13).</b> The same "
    "CAPM beta check that debunked the 52-week-high signal, applied to "
    "reversal for the first time, found none of its 12 full-sample "
    "alpha tests significant. That verdict is accurate but incomplete: "
    "Part V.13 later found reversal's long leg carries real, significant "
    "pre-1994 alpha (p=0.046) that decays fully to noise post-1994 "
    "(p=0.629) &mdash; the identical pattern found for momentum, "
    "invisible in a single full-sample average. Its short leg and "
    "combined book remain non-significant in every era tested.",
    "<b>US 12-1 momentum's post-1994 alpha does not survive an actual "
    "out-of-sample hedge, and the deeper investigation confirms genuine "
    "decay rather than a crash or methodology artifact (Parts V.10-12, "
    "superseding an earlier, more optimistic in-sample reading).</b> An "
    "in-sample pre/post-1994 split (Part V.10) found real decay but "
    "apparent survival in three of four cuts. Re-testing the same "
    "post-1994 period with a rolling, out-of-sample beta hedge found no "
    "statistically significant alpha in either leg, at either frequency "
    "(Part V.11); the hedged combined book's post-1994 average return is "
    "outright negative. Part V.12 then tested whether that null result "
    "was just the 2009 momentum crash or a hedge-window artifact: an "
    "era-by-era breakdown showed ongoing decay through 2017 (well past "
    "2009), excluding the crash window left the combined book's result "
    "essentially unchanged, and the null result held across three "
    "different hedge windows. Pre-1994 alpha remains real and robust "
    "under every test. This project's momentum finding should be read "
    "as strong and genuine before 1994, and as genuine, ongoing decay "
    "&mdash; not a temporary shock &mdash; since.",
    "<b>&quot;Real pre-1994, decayed since&quot; is not momentum-specific "
    "(Part V.13).</b> Applying the identical pre/post-1994 out-of-sample "
    "hedge to all three US signals found two distinct stories: "
    "52-week-high shows no significant alpha in either era, in any leg "
    "(it never had genuine stock-selection skill); reversal's long leg "
    "shows the identical decay signature as momentum's. The pattern "
    "appears in two of three signals' long legs, not one, consistent "
    "with a market-wide explanation rather than a momentum idiosyncrasy.",
    "<b>The 1994 cutoff was directionally right for momentum but "
    "misdescribes its shape and timing (Part V.14).</b> A continuous "
    "linear-trend regression on momentum's hedged long leg gives a "
    "slope that is not statistically significant (p=0.15) &mdash; the "
    "effect did not decay smoothly. A rolling 5-year trajectory shows "
    "momentum's alpha stayed consistently strong (+4% to +22%/yr) from "
    "the 1970s through the window ending January 2008, then broke "
    "sharply negative from 2009 on. Splitting at September 2008 gives a "
    "far cleaner divide (pre: +8.02%/yr, p=0.0005; post: -0.56%/yr, "
    "p=0.998) than 1994 ever produced. Reversal's decay, by contrast, "
    "<i>is</i> well-described by a smooth linear trend (slope "
    "-0.41%/yr, p=0.026, zero-crossing ~November 2004). Momentum's "
    "weakness is better attributed to a 2008-09 regime shift than to "
    "slow, 1990s publication-driven crowding.",
    "<b>A formal structural-break test qualifies both of Part V.14's "
    "stories further (Part V.15).</b> A Chow-style test at the single, "
    "literature-motivated date (2008-09-01, from Daniel &amp; Moskowitz "
    "2016) confirms a real level shift in momentum (p=0.026 daily) "
    "&mdash; but an unconstrained Quandt-Andrews sup-Wald search "
    "(which does not assume any break date) finds its single "
    "best-fitting break 27 months later, at December 2010, and that "
    "unconstrained maximum is not statistically significant once "
    "corrected for the multiple-testing problem of searching ~375 "
    "candidate dates (400-draw block-bootstrap p=0.138). Reversal shows "
    "the opposite: no break near 2008 (p=0.34), but a genuine, "
    "significant break (bootstrap p=0.048) around <b>August 1980</b> "
    "&mdash; the sharp early decline from reversal's extraordinarily "
    "high late-1970s level, not a smoothly accumulating multi-decade "
    "slope as the linear-trend regression alone suggested. Treat both "
    "signals' &quot;when did it break&quot; story as more conservative "
    "and more precisely qualified than Part V.14's descriptive "
    "framing.",
    "<b>The 52-week-high result's cause: resolved, and it's the boring "
    "answer.</b> Two behavioral/statistical explanations were ruled out by "
    "direct test: crash-window concentration (Part V.4) and a value/growth "
    "confound (Part V.5), neither surviving in either market; formally-"
    "tested momentum-crash risk (Part V.6) then walked back Part V.5's "
    "descriptive-looking confirmation too. The actual explanation (Part "
    "V.7) is a construction flaw, not a market phenomenon: the legs have "
    "significantly different, uncontrolled market-beta exposure (long "
    "&asymp;+0.8, short &asymp;-1.2 to -1.4), leaving the book net "
    "short-beta (-0.32 to -0.70, p&lt;0.001 every cut) in markets that "
    "returned ~20%/year. Once beta is controlled for, alpha is "
    "insignificant in all 12 regressions tested. There is no demonstrated "
    "stock-selection skill in this signal, in either direction, as "
    "currently built.",
    "<b>Transaction costs are a simple linear model</b>, not a real "
    "market-impact model; a strategy sized for real capital would need a "
    "proper implementation-shortfall estimate.",
    "<b>No out-of-sample / walk-forward validation is wired up by default.</b> "
    "A real deployment should split into a strict in-sample fit period and "
    "out-of-sample test period, and check for performance decay after each "
    "anomaly's academic publication date &mdash; a well-documented risk for "
    "momentum and reversal specifically.",
    "<b>The Q1 simulation's parameters are illustrative</b>, calibrated "
    "loosely to the LTCM episode's qualitative shape (correlations that were "
    "low/moderate in normal times moving toward 1 in crisis), not fit to "
    "LTCM's actual, never fully disclosed book. Its reported multiple should "
    "be read as an order of magnitude, not a precise historical "
    "reconstruction.",
    "<b>The beta-hedge test (Part V.8) is itself imperfect, by design and "
    "by honest admission.</b> The rolling hedge leaves a small residual "
    "correlation with the market (-0.02 to -0.07, not exactly zero), the "
    "estimated beta is quite unstable across time in both markets (its "
    "standard deviation rivals its mean), and no hedging transaction "
    "costs are modeled. None of that changes the direction of the "
    "finding (still no significant residual alpha), but a live "
    "implementation would need a more robust hedging scheme and would "
    "bear real costs this analysis doesn't capture.",
])

# ============================================================ CONCLUSIONS
story.append(PageBreak())
toc_entry("Conclusions", 0, "concl")
part("Conclusions")
p("The Efficient Market Hypothesis is a useful default, not a law of nature. "
  "This project's five case studies show it failing in genuinely different "
  "ways &mdash; a Nobel-laureate-staffed fund undone by other investors' "
  "correlated panic; sophisticated quant funds undone by their own hidden "
  "crowding; an entire industry's risk model undone by a correlation "
  "assumption nobody's calibration data ever tested; a struggling retailer's "
  "stock undone (in the institutional short-sellers' favor, this time) by "
  "coordinated retail attention &mdash; which is itself evidence against any "
  "single, tidy story of &quot;why markets are irrational.&quot; There isn't "
  "one mechanism; there are several, each traceable to a specific, "
  "well-documented piece of human psychology.")
p("The project's real empirical result (Part V.3) delivered a finding more "
  "useful than a simple confirmation of either extreme view would have been: "
  "not &quot;markets are irrational, biases always pay,&quot; and not "
  "&quot;the anomalies are all arbitraged away, don't bother.&quot; Instead: "
  "one specific, named bias (anchoring, via the 52-week-high signal) actively "
  "lost money on this universe, while a different one (overreaction, via "
  "short-term reversal) at first looked like a real, cost-adjusted edge "
  "&mdash; and the two were invisible from inside a single blended "
  "composite. That is, in miniature, the entire project's argument: rigor "
  "means checking the specific mechanism, not trusting the "
  "reassuring-looking aggregate. It took until Part V.9 for the project to "
  "apply that same rigor to its own positive-looking half of the story, "
  "and when it did, the &quot;edge&quot; didn't survive either &mdash; but "
  "a different signal, US 12-1 momentum, did, and Part V.10 went one step "
  "further than any earlier milestone: instead of asking whether the "
  "finding was real, it asked how much of it a trader could still expect "
  "to capture today, and found a genuinely mixed, honest answer at "
  "first &mdash; real decay, not disappearance. Part V.11 pushed the same "
  "question one step further still, replacing an in-sample estimate with "
  "an actual out-of-sample hedge, and the honest answer got more sobering: "
  "no statistically significant post-1994 alpha survives in either leg. "
  "Even this project's own most reassuring recent finding kept shrinking "
  "every time it was checked with a sharper tool. Part V.12 then did "
  "something different from every check before it: instead of applying a "
  "sharper tool and finding the result shrink again, it tried directly to "
  "explain the shrinkage away &mdash; as a single crash episode, or as an "
  "artifact of one modeling choice &mdash; and failed on both counts. The "
  "result held. Part V.13 then went back to the signal Part V.9 had "
  "seemed to retract outright &mdash; short-term reversal &mdash; and "
  "applied the same era-split toolkit rather than trusting the earlier "
  "full-sample verdict, and found reversal's long leg had been telling "
  "the truth about being &quot;a real, cost-adjusted edge&quot; all "
  "along, just not for the era that mattered by the time anyone checked: "
  "genuine pre-1994, decayed since, the same shape as momentum's story "
  "&mdash; or so it seemed. Part V.14 finally asked the question every "
  "prior milestone had assumed the answer to without checking: was "
  "&quot;the same shape&quot; actually true? It wasn't. Quantified as a "
  "continuous trend instead of a binary 1994 split, reversal's decline "
  "turned out to be genuinely smooth, but momentum's did not &mdash; "
  "momentum held flat and strong for 35 years and then broke sharply "
  "around the 2008-09 crisis, a shape a decay curve fits badly and a "
  "regime shift fits well &mdash; or so a descriptive comparison "
  "suggested. Part V.15 finally asked whether that comparison would "
  "survive being turned into an actual test, corrected for the fact "
  "that the best of many candidate break dates always looks impressive. "
  "It survived only partly: the externally-motivated 2008-09 hypothesis "
  "for momentum held up, but an unconstrained search for the single "
  "best break in the whole series landed 27 months later and wasn't "
  "significant once that search was accounted for &mdash; and reversal's "
  "&quot;smooth&quot; decline turned out to hide a real, significant "
  "break of its own, decades earlier than anyone had looked.")
p("The practical output (Part VI) turns that into three concrete artifacts: an "
  "investment framework that explicitly forbids trusting a blend without "
  "decomposing it; a risk-management playbook built directly from a "
  "real simulated result, not a generic checklist; and a business idea whose "
  "differentiation <i>is</i> the decomposition discipline the research itself "
  "needed. Milestones 3 through 14 then ran the India findings through "
  "increasingly rigorous versions of the same skepticism the project "
  "applies to everything else, and at every step a stronger method found "
  "something the weaker one had missed or overclaimed: momentum and "
  "reversal turned out to be universe-dependent, not general truths; a "
  "value/growth confound was tested and rejected; a formally-compelling-"
  "looking momentum-crash mechanism was tested and rejected too, once "
  "proper statistical significance testing replaced descriptive pattern-"
  "matching; the actual explanation for the losing signal, when it finally "
  "arrived, was the most basic and least glamorous of all the candidates "
  "tested &mdash; an uncontrolled beta mismatch, checked last instead of "
  "first, then confirmed a second way with an actual hedged strategy; and "
  "then, applying that same beta check to the signal the project had been "
  "treating as a validated success, the success turned out not to be one "
  "&mdash; while a signal nobody had flagged as special (US momentum) "
  "turned out to hold real, statistically robust alpha once someone "
  "finally looked properly &mdash; alpha that Part V.10 then showed had "
  "partially decayed since its 1993 publication, that Part V.11 then "
  "showed does not clear this project's own bar for a forward-sizeable "
  "edge once tested with an actual out-of-sample hedge, that Part V.12 "
  "then confirmed is genuine, ongoing decay rather than an artifact of "
  "the 2009 crash or the hedge's own design, that Part V.13 then showed "
  "is not even unique to momentum &mdash; the identical shape turned up "
  "in a signal this project had already, separately, declared dead "
  "&mdash; and that Part V.14 then showed isn't quite the shape anyone "
  "had assumed either: reversal decays the way the textbook predicts, "
  "but momentum's own decline is better described as a sudden 2008-09 "
  "break than the same slow crowding story &mdash; a claim Part V.15 "
  "then formalized and found to be simultaneously more and less true "
  "than Part V.14 suggested: real for the specific, literature-"
  "motivated date, not decisively confirmed as the single best break "
  "once the search itself was accounted for, and, for reversal, "
  "concealing a genuine break of its own decades before 2008.")
p("The fix that survived all of that scrutiny is more modest, and the "
  "project's real positive finding is broader and more precisely dated "
  "than any earlier draft of this conclusion claimed: there is no "
  "demonstrated, beta-independent stock-selection skill in the "
  "52-week-high signal, in either direction, as currently built, at any "
  "point in the sample. Momentum's long leg and short-term reversal's "
  "long leg, by contrast, both show robust, largely beta-independent "
  "edges &mdash; on the US mirror specifically, but not on the same "
  "clock, and not with the same confidence about exactly when or how "
  "each one gave out. Momentum held, essentially undiminished, all the "
  "way to the 2008-09 financial crisis, and a test built specifically "
  "around that crisis date confirms a real break there &mdash; but a "
  "fully unconstrained search for the single best break in the series "
  "does not confirm that date as uniquely special, landing instead 27 "
  "months later without clearing significance. Reversal's decline, "
  "read as a smooth multi-decade trend, is real and significant, but a "
  "formal search finds a genuine break hiding inside that trend near "
  "1980, decades before the mid-2000s point where the trend line "
  "happens to cross zero. Neither date, nor even &quot;a single clean "
  "break exists&quot;, should be read as the &quot;true&quot; story in "
  "some deeper sense &mdash; they are this project's best current, "
  "appropriately hedged point estimates, arrived at only by measuring "
  "the decay directly and then testing that measurement itself, instead "
  "of assuming a shared timeline for two different signals or trusting "
  "the first framing that fit. Every one of those "
  "findings was reached not by anyone's original hypothesis about which "
  "signal should work, but by finally applying the project's own "
  "hard-won standard of rigor evenly: to a winner as well as a loser, to "
  "a signal's own more recent, more comfortable-looking result as well "
  "as its oldest one, to a signal already written off instead of "
  "assuming a full-sample null closed the question for good, and "
  "finally to the project's own explanatory story once a result was "
  "found, instead of assuming the first plausible mechanism was the "
  "right one. That is the project working as intended, "
  "including on itself: not every finding needs to be confirmed to be "
  "useful, a compelling pattern &mdash; positive or negative &mdash; is a "
  "hypothesis until it survives testing at every level of rigor "
  "available, and the single most important thread running through this "
  "entire guide is a project that kept correcting its own most recent, "
  "best-supported-looking result, eleven times in a row &mdash; six "
  "outright retractions or downward revisions, one nuanced check "
  "(Part V.10) that briefly looked like a stopping point before Part "
  "V.11 showed it wasn't, an eighth check (Part V.12) built specifically "
  "to try to explain the seventh correction away that couldn't, and a "
  "ninth (Part V.13) that went looking for the same pattern somewhere "
  "the project had stopped looking, and found it &mdash; then, rather "
  "than resting on that broader finding, ran a tenth check (Part V.14) "
  "against its own explanation for the ninth, discovered that even "
  "&quot;two signals, one shared story&quot; was itself an "
  "oversimplification, and finally ran an eleventh check (Part V.15) "
  "against its own <i>informal</i> version of that discovery &mdash; "
  "and found the formal, multiple-testing-corrected test was more "
  "conservative than the eyeballed comparison that had motivated it, "
  "on both signals, in different directions. Not finding an escape "
  "hatch, finding the same shape twice in independent places, "
  "discovering the two places didn't actually share a shape after all, "
  "and then discovering that even that discovery needed a proper test "
  "before it could be trusted, are all findings: the project never "
  "found a result, an explanation, or even a way of testing an "
  "explanation, durable enough to stop re-checking. What survives is "
  "smaller and more precisely qualified than any single milestone first "
  "suggested: momentum's alpha, real and strong pre-2008-09 and "
  "confirmed weakened specifically at that literature-motivated date, "
  "though not provably the site of the single largest break in the "
  "series; reversal's alpha, real pre-roughly-2005 on a declining trend "
  "that itself conceals a sharper, independently significant break "
  "decades earlier, near 1980. Both are long-leg-only, both decay on "
  "their own schedule and by their own mechanism, and both are now "
  "sized more cautiously than the milestone that first found them would "
  "have suggested &mdash; alongside one honest, thoroughly-stress-tested "
  "absence, the most recent decade, across signals, to size nothing "
  "against.")

# ============================================================ GLOSSARY
story.append(PageBreak())
toc_entry("Glossary", 0, "gloss")
part("Glossary")
glossary = [
    ("Alpha", "The part of a strategy's average return left over after "
     "accounting for its market exposure (beta) -- the piece that would "
     "represent genuine stock-selection skill, if it's significantly "
     "different from zero. This guide's Part V.7 finds none in the "
     "52-week-high signal, either leg, once beta is controlled for."),
    ("Anchoring", "Relying too heavily on an initial reference point (e.g. a "
     "52-week high, an opening price) when making subsequent judgments."),
    ("Beta", "How much a position tends to move for a given move in the "
     "overall market -- a beta of 1 means it moves with the market on "
     "average, above 1 means it amplifies market moves, negative means it "
     "moves opposite the market. A long-short book with unequal long and "
     "short beta carries unintended net market exposure."),
    ("Composite score", "A single number blending several individual signals "
     "into one rank; this project's central finding is that a composite can "
     "hide a component that is actively harmful."),
    ("Correlation regime shift", "A change in how much different assets move "
     "together &mdash; typically a jump from low/moderate to near-1 "
     "correlation during a market crisis."),
    ("Crowding", "Many independent, sophisticated participants arriving at "
     "similar positions without coordinating, producing hidden correlation "
     "across supposedly diversified portfolios."),
    ("Decile / quintile backtest", "A methodology that ranks a universe by a "
     "signal, then goes long the best-ranked group and short the worst-ranked "
     "group, to isolate the return spread the signal actually predicts."),
    ("Efficient Market Hypothesis (EMH)", "The theory that asset prices "
     "reflect all available information, implying no strategy should "
     "reliably beat a passive index."),
    ("Extrapolation bias", "Assuming a recent trend (e.g. fast earnings "
     "growth) will continue further into the future than it typically does."),
    ("Fat tails", "A return distribution with more extreme outcomes than a "
     "normal (bell-curve) distribution predicts."),
    ("Herding", "Following the crowd's behavior rather than independently "
     "evaluating a decision &mdash; useful most of the time, dangerous when "
     "the crowd itself started moving for an unrelated reason."),
    ("Leverage", "Borrowed capital or notional derivative exposure used to "
     "scale a position beyond what the investor's own capital would allow; "
     "it magnifies both gains and losses."),
    ("Maximum drawdown", "The largest peak-to-trough decline a strategy "
     "experiences at any point in a backtest."),
    ("Momentum", "The tendency of a security's recent trend to continue, "
     "typically attributed to underreaction."),
    ("Momentum crash risk", "The tendency of a \"long recent winners, short "
     "recent losers\" strategy to suffer severe losses when the short leg's "
     "high-beta losers rebound sharply, typically during high-volatility, "
     "post-downturn market recoveries."),
    ("Overconfidence", "Overestimating the reliability of one's own "
     "judgment or model, often reinforced by a recent string of favorable "
     "outcomes."),
    ("Post-earnings-announcement drift (PEAD)", "The tendency of a stock "
     "price to keep drifting in the direction of an earnings surprise for "
     "weeks after the announcement, rather than repricing immediately."),
    ("Newey-West (HAC) standard errors", "A correction to a regression's "
     "standard errors that accounts for serial correlation in the data "
     "(e.g. from overlapping monthly holding periods); without it, "
     "significance tests on this kind of strategy-return data can look "
     "more confident than the data actually supports."),
    ("p-value", "The probability of seeing a result at least this extreme "
     "if there were truly no effect. Conventionally, p<0.05 is called "
     "\"statistically significant\" -- but with many tests run at once, "
     "some will cross that bar by chance alone (see this guide's own "
     "Milestone 5 for a worked example)."),
    ("Reversal", "The tendency of a very recent, sharp price move to "
     "partially revert, typically attributed to overreaction."),
    ("Sharpe ratio", "Average return divided by return volatility, "
     "annualized; a standard measure of risk-adjusted performance."),
    ("Survivorship bias", "The distortion introduced by only including, in a "
     "historical study, entities that are still around today (e.g. still-"
     "listed companies), which tends to overstate historical performance."),
    ("Value-at-Risk (VaR)", "An estimate of how much a portfolio could lose "
     "over a given horizon at a given confidence level (e.g. the worst-case "
     "loss on all but the worst 1% of days)."),
]
for term, definition in glossary:
    story.append(Paragraph(term, styles["GlossTerm"]))
    story.append(Paragraph(definition, styles["Body"]))

# ============================================================ SOURCES
story.append(PageBreak())
toc_entry("Sources and Further Reading", 0, "sources")
part("Sources and Further Reading")
sources = [
    "Roger Lowenstein, <i>When Genius Failed: The Rise and Fall of "
    "Long-Term Capital Management</i> (2000).",
    "President's Working Group on Financial Markets, report on hedge fund "
    "leverage and LTCM (April 1999).",
    "Amir Khandani &amp; Andrew Lo, &quot;What Happened To The Quants In "
    "August 2007?&quot;, <i>Journal of Investment Management</i>, 2011 "
    "(working paper 2007).",
    "Contemporaneous financial press coverage of Amaranth Advisors' "
    "September 2006 collapse (e.g. <i>Wall Street Journal</i>, "
    "September-October 2006).",
    "David X. Li, &quot;On Default Correlation: A Copula Function "
    "Approach&quot;, <i>Journal of Fixed Income</i>, 2000.",
    "Felix Salmon, &quot;Recipe for Disaster: The Formula That Killed Wall "
    "Street&quot;, <i>Wired</i>, February 2009.",
    "Michael Lewis, <i>The Big Short</i> (2010).",
    "US House Financial Services Committee hearing, &quot;Game Stopped? Who "
    "Wins and Loses When Short Sellers, Social Media, and Retail Investors "
    "Collide&quot; (February 18, 2021).",
    "Brad Barber &amp; Terrance Odean, &quot;All That Glitters: The Effect "
    "of Attention and News on the Buying Behavior of Individual and "
    "Institutional Investors&quot;, <i>Review of Financial Studies</i>, "
    "2008.",
    "Narasimhan Jegadeesh &amp; Sheridan Titman, &quot;Returns to Buying "
    "Winners and Selling Losers: Implications for Stock Market "
    "Efficiency&quot;, <i>Journal of Finance</i>, 1993.",
    "William George &amp; Chuan-Yang Hwang, &quot;The 52-Week High and "
    "Momentum Investing&quot;, <i>Journal of Finance</i>, 2004.",
    "Narasimhan Jegadeesh, &quot;Evidence of Predictable Behavior of "
    "Security Returns&quot;, <i>Journal of Finance</i>, 1990.",
    "Josef Lakonishok, Andrei Shleifer &amp; Robert Vishny, &quot;Contrarian "
    "Investment, Extrapolation, and Risk&quot;, <i>Journal of Finance</i> "
    "49(5), 1994, pp. 1541-1578.",
    "Richard Thaler, <i>Misbehaving: The Making of Behavioral "
    "Economics</i> (2015).",
    "Kent Daniel &amp; Tobias Moskowitz, &quot;Momentum Crashes&quot;, "
    "<i>Journal of Financial Economics</i>, 2016.",
    "Werner De Bondt &amp; Richard Thaler, &quot;Does the Stock Market "
    "Overreact?&quot;, <i>Journal of Finance</i>, 1985.",
    "Whitney Newey &amp; Kenneth West, &quot;A Simple, Positive "
    "Semi-Definite, Heteroskedasticity and Autocorrelation Consistent "
    "Covariance Matrix&quot;, <i>Econometrica</i>, 1987 -- the standard "
    "reference for the HAC standard errors used in Part V.6.",
]
for s in sources:
    story.append(Paragraph("&bull;&nbsp;&nbsp;" + s, styles["MyBullet"]))

p("All code, full case-study write-ups, and the underlying data-loading and "
  "backtest engine referenced throughout this guide live in the project's "
  "code repository, folder <i>research/behavioral-finance/</i>, which remains "
  "the definitive, most up-to-date source as milestone 3 and beyond continue.",
  style="BodyItalic")

# MARKER_END_ALL_CONTENT

# ============================================================ DOCUMENT BUILD


class GuideDocTemplate(BaseDocTemplate):
    """Populates the TOC automatically from PartTitle (level 0) and H1
    (level 1) styled paragraphs as the document is laid out, and draws a
    running header/footer (skipped on the cover page)."""

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            style_name = getattr(flowable.style, "name", "")
            if style_name == "PartTitle":
                self.notify("TOCEntry", (0, flowable.getPlainText(), self.page))
            elif style_name == "H1":
                self.notify("TOCEntry", (1, flowable.getPlainText(), self.page))


def _draw_page_furniture(canvas_obj, doc_obj):
    canvas_obj.saveState()
    page_num = canvas_obj.getPageNumber()
    if page_num > 1:
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.setFillColor(colors.HexColor("#8a94a3"))
        canvas_obj.drawString(MARGIN, PAGE_H - 0.55 * inch, "Behavioral Finance Research Project")
        canvas_obj.drawRightString(PAGE_W - MARGIN, PAGE_H - 0.55 * inch, "Project Guide")
        canvas_obj.setStrokeColor(colors.HexColor("#c3ccd6"))
        canvas_obj.line(MARGIN, PAGE_H - 0.62 * inch, PAGE_W - MARGIN, PAGE_H - 0.62 * inch)
        canvas_obj.setFont("Helvetica", 8.5)
        canvas_obj.setFillColor(colors.HexColor("#5a6472"))
        canvas_obj.drawCentredString(PAGE_W / 2, 0.5 * inch, str(page_num))
    canvas_obj.restoreState()


frame = Frame(MARGIN, MARGIN, PAGE_W - 2 * MARGIN, PAGE_H - 2 * MARGIN, id="normal_frame")

doc = GuideDocTemplate(
    OUT_PATH,
    pagesize=LETTER,
    leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN, bottomMargin=MARGIN,
    title="Behavioral Finance Research Project - Guide",
    author="Behavioral Finance Research Project",
)
doc.addPageTemplates([PageTemplate(id="normal", frames=[frame], onPage=_draw_page_furniture)])
doc.multiBuild(story)

print(f"PDF built: {OUT_PATH}")

