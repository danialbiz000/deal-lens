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
box(
    "Section 5.16 asks WHY reversal broke around August 1980, at "
    "explicit request, rather than reporting the date and moving on. "
    "The answer is a major correction, not a refinement: reversal's "
    "entire positive finding, carried since Section 5.10, turns out to "
    "be an artifact of unreliable early data.",
    kind="fact", title="UPDATE FROM SECTION 5.16"
)

h1("5.16  Milestone 15 &mdash; What actually happened in 1980? A major correction")
p("Section 5.15 found a genuine, statistically significant structural "
  "break for reversal around August 1980, but offered no explanation "
  "for the date. At explicit request, this milestone "
  "(<i>investigations/reversal_1980_break_diagnostics.py</i>) "
  "investigates the mechanism directly &mdash; and the result "
  "substantially revises, rather than merely refines, this project's "
  "understanding of reversal's status.")
p("<b>The universe is severely thin in the 1970s-early 1980s &mdash; "
  "2-4 stocks, not a portfolio.</b> From 1972 through 1983, "
  "reversal's decile &quot;long leg&quot; contains only <b>2-4 "
  "stocks</b>, drawn from a total universe of just 9-14 names. The "
  "underlying universe itself is a small, hand-picked subset of "
  "<i>today's</i> largest surviving companies (AAPL, JPM, JNJ, PG, "
  "XOM, KO, PEP, WMT, HD, DIS, CVX, PFE, INTC, VZ, T, MRK, ABT, MCD) "
  "backfilled to their earliest available data &mdash; a textbook "
  "survivorship-biased sample: every name in this era's universe is, "
  "by construction, a company that <i>did</i> go on to become a "
  "mega-cap winner by 2017. Any stock that dipped temporarily in the "
  "1970s-80s was, in hindsight, virtually guaranteed to &quot;bounce "
  "back,&quot; mechanically inflating an apparent reversal effect "
  "that has nothing to do with genuine investor overreaction.")
p("<b>A genuine data-quality defect, not previously flagged, "
  "compounds the problem.</b> Scanning this era for single-day moves "
  "exceeding 50% (the usual fingerprint of an unadjusted stock split) "
  "turns up two real anomalies: <b>WMT</b> drops 52% on 1974-12-06 and "
  "then jumps back +109% twelve days later on 1974-12-18 (a "
  "round-trip, consistent with a split-adjustment error that later "
  "self-corrects in the raw feed), and <b>INTC</b> jumps +101% on "
  "1972-01-27 and a further +51% on 1972-06-22. These are new, "
  "previously undocumented data-quality issues in the US Kaggle "
  "mirror.")
data_table(
    ["Start date", "Reversal ann. ret / p", "Momentum (control) ann. ret / p"],
    [
        ["1972-01-01 (full sample)", "+2.64%/yr, p=.068", "+6.21%/yr, p=.0008"],
        ["1978-01-01", "-0.59%/yr, p=.833", "+6.38%/yr, p=.0014"],
        ["1980-08-29 (break date itself)", "-1.24%/yr, p=.922", "+6.20%/yr, p=.0027"],
        ["1985-01-01", "-1.20%/yr, p=.935", "+5.90%/yr, p=.0056"],
        ["1990-01-01", "-0.73%/yr, p=.896", "+5.47%/yr, p=.0192"],
        ["1995-01-01", "+0.48%/yr, p=.581", "+3.75%/yr, p=.121"],
    ],
    col_widths=[1.9*inch, 2.3*inch, 2.5*inch],
    small=True,
)
p("<b>Reversal's entire positive-alpha claim depends on the "
  "unreliable 1972-1977 window and disappears completely once it is "
  "excluded</b> &mdash; from any start date at or after 1978, "
  "including the Method B break date itself, p ranges 0.54-0.96 and "
  "the point estimate is usually slightly negative. <b>Momentum, run "
  "as a control through the exact same thin, survivorship-biased, "
  "partly data-glitched early universe, is unaffected</b>: it remains "
  "highly significant (p&le;0.02) at every start date through 1990, "
  "fading only toward the already-established, externally-motivated "
  "2008-09 territory from 1995 onward. The same data limitation "
  "affects both signals identically; only reversal's finding "
  "depended on it.")
box(
    "The August 1980 &quot;break&quot; is not evidence of a real 1980 "
    "market event: it is the Quandt-Andrews search correctly detecting "
    "that reversal's entire apparent edge lives inside an unreliable, "
    "thin, survivorship-biased, and partly data-glitched early sample "
    "window, with nothing genuine on either side of any split point "
    "once that window is excluded. <b>The &quot;reversal has genuine "
    "pre-2005 alpha&quot; claim carried since Section 5.10 through "
    "Section 5.15 should be treated as retracted, not merely decayed "
    "or narrowed: reversal shows no reliably demonstrated edge "
    "anywhere in this dataset once the unreliable years are "
    "excluded.</b> Momentum is unaffected by this correction and, if "
    "anything, comes out more strongly validated: the same diagnostic "
    "that broke reversal's finding left momentum's intact.",
    title="RETRACTED, NOT REFINED"
)
box(
    "Section 5.17 asks whether momentum's confirmed 2008-09 break has a "
    "real, named mechanism behind it, not just a date &mdash; and "
    "reuses this project's own crash-risk toolkit, rejected for a "
    "different signal, to test it.",
    kind="fact", title="UPDATE FROM SECTION 5.17"
)

h1("5.17  Milestone 16 &mdash; Does the classic momentum-crash mechanism explain the 2008-09 break?")
p("Sections 5.13-5.14 confirmed momentum's long leg broke sharply "
  "around September 2008 but left the <i>mechanism</i> unexplained "
  "&mdash; Section 5.12 checked a fixed calendar window (March-August "
  "2009) and found it only partially mattered. This milestone "
  "(<i>investigations/momentum_crash_mechanism_2008.py</i>) tests the "
  "actual, named mechanism instead of a calendar window: the classic "
  "Daniel &amp; Moskowitz (2016) momentum-crash trigger (past losers "
  "snapping back hard in a high-volatility market rebound), using the "
  "same look-ahead-free Bear &times; High-Volatility regime-interaction "
  "regression this project built and validated in Sections 5.7-5.8 "
  "&mdash; where it was tested on the 52-week-high signal, full-sample, "
  "and found <i>not</i> significant. Applying the identical regression "
  "to momentum's out-of-sample-hedged long leg, split at the same "
  "literature-motivated 2008-09-01 date used since Section 5.14:")
data_table(
    ["", "Pre-2008-09", "Post-2008-09"],
    [
        ["Bear x High-Vol regime frequency", "6.1% of days", "9.1% of days"],
        ["Bear x High-Vol interaction coef.", "-0.00062/day, p=.424 (n.s.)", "-0.00218/day, p=.0081"],
        ["Baseline (non-crash-regime) alpha", "+0.00038/day, p=.003 (~+9.6%/yr)", "+0.00017/day, p=.203 (n.s.)"],
        ["Implied return, Bear+High-Vol day", "~-11%/yr (n.s.)", "~-37%/yr"],
    ],
    col_widths=[2.2*inch, 2.3*inch, 2.3*inch],
    small=True,
)
p("<b>The crash mechanism was dormant before 2008 and activated "
  "after.</b> Pre-2008-09, the Bear &times; High-Vol interaction is "
  "small and not remotely significant (p=0.42) &mdash; consistent with "
  "Sections 5.7-5.8's original finding that momentum-crash risk wasn't "
  "a real driver of this project's data. Post-2008-09, the identical "
  "interaction term becomes large, negative, and statistically "
  "significant (p=0.008): on the roughly 9% of post-2008 trading days "
  "that are both high-volatility and in a trailing bear-market state, "
  "momentum's long leg loses at an annualized rate around 37%, while "
  "its baseline (non-crash) daily alpha has fallen to statistically "
  "indistinguishable from zero. The combined long-short book shows the "
  "same sign and similar magnitude but weaker significance (p=0.21) "
  "&mdash; consistent with the extra noise from a still-volatile short "
  "leg diluting the signal.")
box(
    "This gives momentum's 2008-09 structural break a genuine causal "
    "mechanism, not just a confirmed date. The classic momentum-crash "
    "dynamic this project rejected in Sections 5.7-5.8 (for the "
    "52-week-high signal, full-sample) and that Section 5.12 found "
    "only partially relevant to a fixed 2009 calendar window, turns "
    "out to be real for momentum specifically &mdash; but <b>conditional "
    "on era: dormant through the pre-crisis decades, then active "
    "since.</b> This is consistent with, and adds mechanistic detail "
    "to, the broader post-2008 quant-crowding story already touched on "
    "in this project's own Quant Quake case study &mdash; a market "
    "where momentum-following capital had scaled up enough by 2008 for "
    "the classic crash dynamic to actually bite.",
    title="A MECHANISM, NOT JUST A DATE"
)
box(
    "Section 5.18 asks whether the same crash mechanism, and a more "
    "rigorous re-test of NSE momentum itself, hold up on the market "
    "this project has tested the most and trusted the least.",
    kind="fact", title="UPDATE FROM SECTION 5.18"
)

h1("5.18  Milestone 17 &mdash; Does the momentum-crash mechanism replicate on NSE?")
p("Section 5.17's finding was established on one market. This "
  "milestone (<i>investigations/momentum_crash_mechanism_nse.py</i>) "
  "tests it on NSE (India) &mdash; a market that lived through the "
  "same 2008 global crisis. Before trusting anything here, the "
  "Section 5.16 lesson applies: NSE momentum's decile long leg holds "
  "6-10 names throughout 2000-2021 (vs. the US mirror's notorious 2-4 "
  "names in the 1970s-80s), a reasonable portfolio size, not the "
  "thin-universe artifact that sank reversal.")
p("<b>A genuine methodological gap, closed first.</b> Section 5.9 "
  "tested NSE momentum's alpha with a single <i>static</i> full-sample "
  "beta regression and found no significant result. That is a "
  "materially cruder test than the rolling, out-of-sample hedge this "
  "project built in Section 5.8 and has used for every US momentum "
  "test since &mdash; but it had never been applied to NSE momentum "
  "before. Doing so now:")
data_table(
    ["", "Long leg, daily", "Long leg, monthly"],
    [
        ["Full sample (2000-2021)", "+3.56%/yr, p=.170 (n.s.)", "+4.55%/yr, p=.168 (n.s.)"],
        ["Pre-2008-09", "-2.82%/yr, p=.744 (n.s.)", "-1.70%/yr, p=.754 (n.s.)"],
        ["Post-2008-09", "+7.66%/yr, p=.044", "+7.94%/yr, p=.073 (marginal)"],
    ],
    col_widths=[2.0*inch, 2.3*inch, 2.3*inch],
    small=True,
)
p("<b>Full-sample, the more rigorous hedge reaffirms Section 5.9's "
  "conclusion</b> &mdash; no significant NSE momentum alpha, daily or "
  "monthly, now on firmer methodological footing. But a "
  "<b>post-2008-specific signal emerges</b> that the cruder full-sample "
  "test could not have seen: daily-frequency alpha is significant "
  "(p=0.044), monthly is marginal (p=0.073). This is genuinely new, "
  "but should be read as &quot;promising, not confirmed&quot; &mdash; "
  "this project's own standard label for exactly this strength of "
  "evidence (Section 5.10) &mdash; and comes with a real caveat: "
  "NSE's universe itself grew from ~30 to 48 names over this window, "
  "so part of the post-2008 improvement in signal strength may reflect "
  "a less thin, better-populated cross-section rather than a genuine "
  "change in the underlying economics.")
p("<b>The crash-specific mechanism itself does not replicate.</b> "
  "Applying Section 5.17's exact Bear &times; High-Vol regression to "
  "NSE: the interaction term is never significant (p=0.96 full-sample, "
  "p=0.34 pre-2008, p=0.66 post-2008) &mdash; unlike the US, where it "
  "activated sharply post-2008. What NSE <i>does</i> show is a plain, "
  "unconditional <b>Bear</b> effect: the long leg loses significantly "
  "in any trailing bear market (coef=-0.00095/day, p=0.002 full-sample; "
  "p=0.001 post-2008), regardless of whether volatility is "
  "simultaneously high. That is a related but mechanistically "
  "different pattern from the US's specific crash-<i>rebound</i> "
  "dynamic &mdash; NSE momentum looks bear-market-sensitive in "
  "general, not crash-rebound-sensitive in particular.")
box(
    "This is not a repeat of the already-settled &quot;does NSE "
    "momentum work&quot; question &mdash; it is two new, "
    "honestly-qualified findings. The specific momentum-crash "
    "mechanism confirmed for the US in Section 5.17 is not universal; "
    "it does not show up in NSE the same way, even though NSE lived "
    "through the same 2008 crisis. Separately, a more rigorous re-test "
    "surfaced a genuinely new, if still tentative, post-2008 NSE "
    "momentum signal that a cruder test had missed &mdash; evidence "
    "that this project's own methodology upgrades are still capable of "
    "finding things earlier, less careful passes did not, even on a "
    "market already checked multiple times.",
    title="A NEW SIGNAL, AND A MECHANISM THAT DOESN'T TRAVEL"
)
box(
    "Section 5.17's &quot;post-2008&quot; block pools the 2008-09 crisis "
    "with eight subsequent years. Section 5.19 splits it and asks "
    "whether the crash-regime effect actually persisted, or was the "
    "crisis alone.",
    kind="fact", title="UPDATE FROM SECTION 5.19"
)

h1("5.19  Milestone 18 &mdash; Does the 2008-09 crash mechanism persist after the crisis?")
p("Section 5.17 tested the Bear &times; High-Volatility interaction on the "
  "<i>whole</i> post-2008-09 block (Sept 2008 through the end of the US "
  "mirror's coverage in Nov 2017, n=2,309 days) and found it significant "
  "(p=0.008), reading that as the crash mechanism having &quot;activated&quot; "
  "for good after 2008. But that block pools two very different periods: "
  "the acute 2008-09 crisis itself, and eight subsequent years. This "
  "milestone (<i>investigations/momentum_crash_mechanism_persistence.py</i>) "
  "splits the post-2008-09 block at 2009-12-31 and re-runs the identical "
  "regression on each half separately.")
p("The split immediately surfaces a structural fact this project had not "
  "checked before: <b>the US mirror's trailing-12-month market return "
  "never went negative again after September 2009</b>, all the way through "
  "the end of its coverage in November 2017 &mdash; the 2011 European-debt-"
  "crisis selloff and the Aug 2015-Feb 2016 drawdown were sharp but both "
  "recovered within the 252-day lookback before ever registering as a "
  "sustained bear state under this project's own (Section 5.5) definition.")
data_table(
    ["", "Pre-2008-09", "Crisis (2008-09 to 2009-12)", "Post-crisis (2010-01+)"],
    [
        ["Trading days", "8,983", "337", "1,972"],
        ["Bear x High-Vol frequency", "6.1%", "62.3%", "0.0%"],
        ["Interaction coef (long leg)", "-0.00062/day, p=.42 (n.s.)", "+0.00115/day, p=.26 (n.s.)", "cannot be estimated"],
        ["High-Vol alone (crisis)", "-", "-0.00361/day, p<.0001", "-"],
        ["Bear alone (crisis)", "-", "-0.00188/day, p=.036", "-"],
    ],
    col_widths=[1.7*inch, 1.5*inch, 1.85*inch, 1.55*inch],
    small=True,
)
p("<b>Two refinements to Section 5.17's framing, not a retraction of its "
  "core fact.</b> Momentum's long leg still lost heavily during 2008-09 "
  "&mdash; that empirical fact is unchanged and confirmed again here. But "
  "two things Section 5.17's pooled test could not show on its own:")
bullets([
    "<b>There is no evidence of a persisting post-2008 bear-market regime "
    "to test.</b> Because the trailing-return bear flag never fired again "
    "after September 2009, the &quot;post-2008-09&quot; window Section "
    "5.17 tested is, for the interaction term's purposes, entirely carried "
    "by the 16-month crisis sub-window &mdash; the other ~2,000 days "
    "post-crisis contribute zero Bear+High-Vol observations. Framing this "
    "as a standing &quot;post-2008 regime change&quot; was an "
    "overstatement; the honest description is &quot;active during the "
    "2008-09 crisis, untested since, because no comparable bear market "
    "has recurred in this sample.&quot;",
    "<b>Isolated to the crisis window alone, the specific multiplicative "
    "interaction is not what's doing the work.</b> Run on the crisis's "
    "337 days by themselves, the interaction term is <i>not</i> "
    "significant (p=0.26 long leg, p=0.31 combined) &mdash; instead, high "
    "volatility alone (p&lt;0.0001) and the bear-market flag alone "
    "(p=0.036 long leg, p=0.005 combined) each independently explain the "
    "losses. Section 5.17's pooled significance for the interaction "
    "specifically came from contrasting the crisis window against "
    "~2,000 calm, non-bear post-crisis days as an implicit control group "
    "&mdash; a valid test of &quot;did something change after 2008,&quot; "
    "but weaker evidence for &quot;the interaction, specifically, is the "
    "mechanism&quot; than the p=0.008 headline number suggested in "
    "isolation.",
])
p("Neither sub-window shows any hedged-alpha significance in the plain "
  "daily/monthly check either (crisis: p=0.84 daily, n=15 months "
  "insufficient for HAC; post-crisis: p=0.86 daily, p=0.57 monthly) "
  "&mdash; consistent with Section 5.17's original post-2008 "
  "baseline-alpha result (p=0.20, n.s.).")
box(
    "The 2008-09 break is real and tied to volatility and bear-market "
    "state, but this project has no evidence it is a <i>standing</i> "
    "feature of the post-2008 world, because the specific bear-market "
    "condition this project uses to define &quot;crash regime&quot; has "
    "not recurred since 2009 in this sample. A risk model built on "
    "Section 5.17's finding alone would be over-claiming &quot;momentum "
    "has been crash-exposed since 2008&quot;; the accurate claim is "
    "narrower: &quot;momentum was crash-exposed during the one bear "
    "market this sample's post-2008 window actually contains.&quot; "
    "Whether the mechanism would reactivate in a future bear market is a "
    "hypothesis this data cannot confirm or rule out &mdash; there simply "
    "hasn't been one to test against since.",
    title="ONE CRISIS, NOT YET A REGIME"
)
box(
    "Section 5.19's central claim rests on a 252-day bear-market lookback. "
    "Section 5.20 asks whether that claim, and Section 5.17's pattern, "
    "survive other reasonable choices of that window.",
    kind="fact", title="UPDATE FROM SECTION 5.20"
)

h1("5.20  Milestone 19 &mdash; Does the crash-mechanism finding survive different regime-construction choices?")
p("Every crash-regime result since Section 5.6 rests on two parameter "
  "choices baked into <i>build_regime_dummies()</i>: a 21-trading-day "
  "realized-volatility window and a 252-trading-day (~1-year) "
  "trailing-return lookback for the &quot;Bear&quot; flag. Neither had "
  "been stress-tested. This matters more than usual for Section 5.19's "
  "finding specifically, because &quot;no bear market recurred after "
  "2009&quot; is a claim that can only be as robust as the lookback "
  "window that defines &quot;bear market&quot; &mdash; a shorter window "
  "would register the sharp 2011 and 2015-16 drawdowns that a 1-year "
  "lookback smooths away. This milestone "
  "(<i>investigations/momentum_crash_regime_robustness.py</i>) "
  "reimplements the regime construction with configurable windows (the "
  "original function used by every prior milestone is untouched) and "
  "sweeps a 4&times;4 grid: volatility windows of 10, 21, 42, and 63 "
  "trading days, crossed with bear-market lookbacks of 126, 189, 252, "
  "and 378 trading days &mdash; 16 combinations, each checked two ways: "
  "does a Bear regime ever fire after 2010-01-01, and does Section "
  "5.17's &quot;interaction dormant pre-2008-09, significant "
  "post-2008-09&quot; pattern still hold.")
data_table(
    ["", "Bear lookback 126d", "189d", "252d (default)", "378d"],
    [
        ["Bear regime fires post-2010?", "Yes (200 days)", "Yes (47 days)", "No", "No"],
        ["Sec. 5.17 pattern replicates", "1 of 4 vol windows", "2 of 4", "2 of 4 (incl. default)", "3 of 4"],
    ],
    col_widths=[1.75*inch, 1.55*inch, 1.35*inch, 1.75*inch, 1.25*inch],
    small=True,
)
p("<b>Section 5.19's &quot;no bear regime since 2009&quot; is not "
  "robust to the lookback window &mdash; this is a real qualification, "
  "not just a robustness footnote.</b> At the two shorter, equally "
  "standard lookbacks (126 trading days &asymp; 6 months, 189 &asymp; 9 "
  "months), the trailing-return bear flag <i>does</i> fire after 2010 "
  "&mdash; 200 days clustered in 2010-11 and 2015-16, and 47 days in the "
  "same years respectively &mdash; exactly the 2011 European-debt-crisis "
  "selloff and the Aug 2015-Feb 2016 drawdown that Section 5.19 already "
  "named as sharp-but-short episodes the 252-day window happened to "
  "smooth away. Only at lookbacks of 252 days or longer does the &quot;no "
  "recurrence&quot; claim hold. Section 5.19's finding should be read as "
  "conditional on this project's own 1-year convention, not as a "
  "lookback-independent fact about the market.")
p("<b>Section 5.17's interaction pattern itself replicates in 8 of 16 "
  "combinations &mdash; real, but concentrated in a specific part of the "
  "parameter space.</b> It never holds at the shortest volatility window "
  "(10 days, 0 of 4 bear-lookbacks) &mdash; at that window the pre-2008 "
  "era itself becomes significant in one case, breaking the &quot;dormant "
  "before&quot; half of the claim. It rarely holds at the shortest "
  "bear-lookback (126 days, 1 of 4 vol-windows). But it holds reliably "
  "&mdash; 3 of 4 bear-lookbacks &mdash; at this project's own default "
  "21-day volatility window and the adjacent 42-day window, and the "
  "default parameter combination that Sections 5.17-5.19 actually used "
  "sits squarely inside that reliable region, not at an edge case "
  "cherry-picked to produce significance.")
box(
    "Two different answers for two different claims sharing the same "
    "regime-construction code. Section 5.17's qualitative story &mdash; "
    "the crash mechanism was quiet before 2008-09 and active during/after "
    "it &mdash; is reasonably robust to nearby parameter choices, failing "
    "only at unusually short windows this project never actually used. "
    "Section 5.19's stronger, more specific claim &mdash; that <i>no</i> "
    "bear market recurred anywhere in the post-2009 sample &mdash; is "
    "fragile: it depends on choosing a bear-lookback of a year or longer, "
    "and a 6- or 9-month lookback, an equally defensible convention, "
    "tells a different story. The honest combined statement: momentum's "
    "crash-regime exposure is confirmed for the 2008-09 crisis under "
    "every parameter choice tested, and whether it also showed up in 2011 "
    "or 2015-16 is a genuinely open question this project has not yet "
    "run &mdash; the persistence test only ran under the window where no "
    "second bear regime exists to test it against.",
    title="ROBUST PATTERN, FRAGILE ABSENCE-CLAIM"
)
box(
    "Section 5.20 closes that open question directly: re-running the "
    "persistence test under the lookbacks where a real post-2010 bear "
    "regime exists.",
    kind="fact", title="UPDATE FROM SECTION 5.21"
)

h1("5.21  Milestone 20 &mdash; Did the crash mechanism reactivate in 2011 or 2015-16?")
p("Section 5.20 left one question explicitly open: at bear-market "
  "lookbacks of 126 and 189 trading days (~6 and ~9 months), a bear "
  "regime <i>does</i> recur post-2010 &mdash; clustered in 2010-11 (the "
  "European debt-crisis selloff) and 2015-16 (the Aug 2015-Feb 2016 "
  "drawdown) &mdash; giving 148 and 31 Bear+High-Vol days respectively "
  "to actually test the crash mechanism's persistence against, something "
  "Section 5.19's default 252-day lookback could not do at all. This "
  "milestone (<i>investigations/momentum_crash_mechanism_recurrence.py</i>) "
  "closes that thread: re-running the Bear &times; High-Vol interaction "
  "regression on the 2010-onward window, under both alternate lookbacks, "
  "with everything else unchanged.")
data_table(
    ["", "Bear lookback 126d", "Bear lookback 189d"],
    [
        ["Bear+High-Vol days, 2010 onward", "148 (7.5% of era)", "31 (1.6% of era)"],
        ["Interaction coefficient", "-0.00172/day, p=.203 (n.s.)", "-0.00143/day, p=.443 (n.s.)"],
        ["Bear-alone coefficient", "+0.00126/day, p=.226 (n.s.)", "+0.00212/day, p=.023"],
    ],
    col_widths=[2.1*inch, 2.35*inch, 2.35*inch],
    small=True,
)
p("<b>The mechanism did not reactivate, under either alternate lookback "
  "&mdash; and where a coefficient was significant, it pointed the wrong "
  "way for crash risk.</b> At neither window is the Bear &times; "
  "High-Vol interaction anywhere near significant post-2010 (p=0.20, "
  "p=0.44), despite now having real bear-regime days to test it against. "
  "At the 189-day lookback the bear-market main effect <i>is</i> "
  "significant (p=0.023) &mdash; but positive, not negative: momentum's "
  "long leg did somewhat <i>better</i>, not worse, during 2010-onward "
  "trailing-bear periods, the opposite sign from both the crisis-era "
  "coefficient and what the crash-risk mechanism predicts. This is not "
  "the pattern of a dormant mechanism waking back up; it is closer to no "
  "pattern at all.")
box(
    "This strengthens, rather than merely leaves open, Section 5.19's "
    "original framing. The crash mechanism is not just <i>untested</i> "
    "outside the 2008-09 crisis under this project's default parameters "
    "&mdash; now that two alternate, equally standard parameter choices "
    "supply real bear-regime days post-2010, the mechanism is <i>tested "
    "and not found</i> there. The honest, now-complete statement across "
    "Sections 5.17, 5.19, 5.20, and 5.21: the Bear &times; High-Vol "
    "interaction explains momentum's 2008-09 losses specifically, has "
    "not reappeared in either of the two next bear-adjacent episodes "
    "this sample contains under any lookback tested, and a standing "
    "&quot;momentum is crash-exposed&quot; risk rule would have been "
    "wrong to apply in both 2011 and 2015-16. Whether it would "
    "reactivate in a genuinely severe future crisis, as opposed to the "
    "milder episodes of 2011 and 2015-16, remains open &mdash; this "
    "sample simply has not contained one since 2009.",
    title="TESTED AND NOT FOUND, NOT JUST UNTESTED"
)
box(
    "The crash-mechanism chain is now closed. Section 5.22 turns the "
    "same pooled-window lesson back on this project's own other open "
    "finding: the tentative NSE post-2008 momentum signal.",
    kind="fact", title="UPDATE FROM SECTION 5.22"
)

h1("5.22  Milestone 21 &mdash; Does the tentative NSE signal survive its own named caveat?")
p("Section 5.18's tentative post-2008 NSE momentum signal (long leg, "
  "daily p=0.044, monthly p=0.073) shipped with an explicit, unresolved "
  "caveat: NSE's universe grew from ~30 names in 2000 to a full 48 by "
  "late 2010, so part of the apparent post-2008 improvement could "
  "reflect a less thin, better-populated cross-section rather than a "
  "genuine change in the underlying economics. That caveat was named "
  "but never tested &mdash; until now. Checking the NSE mirror's daily "
  "coverage directly finds the universe was still expanding through "
  "2009 (45 of 48 names on average) but has been <b>perfectly fixed at "
  "exactly 48 names, every single day, from 2010-11-04 through the end "
  "of the sample (2021-04-30)</b> &mdash; 10.5 of the ~12.7 years in "
  "Section 5.18's &quot;post-2008&quot; window. That split gives a "
  "clean test: does the signal survive when restricted to only the "
  "years where a growth confound is definitionally impossible, because "
  "the universe never changed size at all?")
data_table(
    ["", "Post-2008 full", "Growing (2008-09 to 2010-11)", "Stable (2010-11+, fixed 48)"],
    [
        ["Days", "3,114", "535", "2,579"],
        ["Daily ann. return / p", "+7.66%/yr, p=.044", "+23.72%/yr, p=.112 (n.s.)", "+4.60%/yr, p=.180 (n.s.)"],
        ["Monthly ann. return / p", "+7.94%/yr, p=.073", "+21.55%/yr, p=.132 (n.s.)", "+4.96%/yr, p=.250 (n.s.)"],
    ],
    col_widths=[1.65*inch, 1.45*inch, 2.15*inch, 1.85*inch],
    small=True,
)
p("<b>Not the confound named, but a different and arguably more serious "
  "problem for the same finding.</b> The growth-confound story predicted "
  "the <i>growing</i> years would show inflated, thin-universe "
  "significance that the <i>stable</i> years would lack &mdash; but the "
  "opposite pattern shows up in the point estimates: the growing "
  "sub-period's annualized return is actually <i>larger</i> (+23.72%/yr "
  "vs. +4.60%/yr), not smaller, so this is not evidence the universe "
  "growth specifically inflated the signal. What it does show is "
  "something this project has now learned to recognize from Sections "
  "5.19-5.21: <b>the full-window significance is a pooling "
  "artifact.</b> Neither natural sub-period &mdash; not the growing "
  "years, not the fully stable, fixed-48-name years &mdash; reaches "
  "significance on its own, at either frequency. The signal exists only "
  "when the two are pooled together.")
box(
    "Section 5.18's own &quot;promising, not confirmed&quot; label "
    "undersold how fragile this finding is. It is not just unconfirmed; "
    "it does not survive being split by the one structural feature "
    "(universe stability) this project already knew was a live concern, "
    "in either direction the split could have gone. Applying the same "
    "lesson Sections 5.19-5.21 learned about the crash mechanism &mdash; "
    "a pooled window's significance can come from combining two periods "
    "rather than a persisting effect in either &mdash; to this project's "
    "own tentative finding rather than only to someone else's: the NSE "
    "post-2008 momentum signal should be read as <i>not currently "
    "demonstrated</i>, not merely as an open, promising thread.",
    title="A NAMED CAVEAT, FINALLY TESTED"
)
box(
    "Both of this project's remaining open threads are now closed. Section "
    "5.23 opens a new one instead: a genuinely independent third market.",
    kind="fact", title="UPDATE FROM SECTION 5.23"
)

h1("5.23  Milestone 22 &mdash; A third, independent market: does momentum replicate on ASX?")
p("NSE and the US Kaggle mirror are this project's only two markets so "
  "far, and both trace back to community re-exports of specific existing "
  "datasets (NSE: one uploader's CSV; US: a well-known Kaggle &quot;Huge "
  "Stock Market Dataset&quot; mirror). Neither is an independent check on "
  "whether momentum is a market-wide phenomenon or an artifact of how "
  "those two particular datasets happen to be built. This milestone looks "
  "for a genuine third source.")
p("<b>Finding one was harder than expected &mdash; worth documenting as "
  "part of the result, not just a footnote.</b> An extensive search for a "
  "European per-company OHLCV mirror (the first choice) found none "
  "reachable from this sandbox: <i>stooq.com</i>, <i>huggingface.co</i>, "
  "<i>github.com</i>'s own HTML pages, and <i>api.github.com</i>'s "
  "general repo-browsing API are all blocked by the network proxy here "
  "&mdash; only <i>raw.githubusercontent.com</i> is allowlisted, and only "
  "for exact, known file paths. Several candidate European-stock "
  "repositories turned out to be pipeline <i>code</i> that fetches from "
  "Yahoo Finance or Kaggle at run time (also blocked), not committed "
  "price data. The source that finally worked is "
  "<i>grantcarthew/data-asx-historical-share-tables</i> &mdash; a GitHub "
  "mirror of the Australian Securities Exchange's own daily S&amp;P/ASX300 "
  "constituent report emails, 2009-10-20 to 2015-12-31. Not European, but "
  "a genuinely independent developed market: different exchange, "
  "different uploader, official ASX report emails rather than a Kaggle "
  "re-export, from both NSE and the US mirror.")
p("<b>Applying this project's current best methodology directly, rather "
  "than its history.</b> Rather than re-running the original crude "
  "full-sample regression Sections 5.7-5.9 started with, this test goes "
  "straight to the out-of-sample rolling hedge and HAC significance check "
  "this project has used for every market since Section 5.11/5.18:")
data_table(
    ["", "Long leg", "Combined long-short"],
    [
        ["Raw ann. return (unhedged)", "+8.29%/yr", "+27.15%/yr"],
        ["Hedged daily ann. return / p", "+11.14%/yr, p=.0085", "+35.45%/yr, p=.0006"],
        ["Hedged monthly ann. return / p", "+9.97%/yr, p=.0141", "+30.97%/yr, p=.0001"],
        ["Mean hedge beta", "+0.83", "-0.42"],
    ],
    col_widths=[2.3*inch, 2.25*inch, 2.25*inch],
    small=True,
)
p("<b>Momentum replicates cleanly on ASX &mdash; the strongest, most "
  "unambiguous result of the three markets tested.</b> Both legs are "
  "significant at both frequencies, on a proper out-of-sample hedge from "
  "day one (this market never went through the &quot;static full-sample "
  "regression first, hedge added later&quot; history NSE and the US "
  "mirror did). The combined book's large magnitude has a plausible, "
  "checked explanation rather than being a red flag on its own: the "
  "short leg's mean beta (-1.26) is far more negative than the long "
  "leg's (+0.83) is positive, consistent with Australia's well-known "
  "2011-2015 mining and resources downturn &mdash; momentum's short leg "
  "would have been loaded with high-beta miners that kept "
  "underperforming through exactly that window, and the rolling beta "
  "estimates themselves are reasonably stable (std 0.39, no extreme "
  "outliers) rather than a symptom of an unstable hedge.")
box(
    "A genuine limitation, stated plainly: this is the shortest history "
    "of the three markets. Six years (1,501 trading days) is enough for "
    "a full-sample significance test but not for the era-splitting, "
    "structural-break, or persistence checks this project ran "
    "extensively on the US mirror's 47-year history &mdash; there is no "
    "&quot;pre-publication vs. post-publication&quot; split possible "
    "here, and no way yet to check whether ASX momentum's edge is stable "
    "across sub-periods the way Sections 5.10-5.15 checked for the US. "
    "That is future work, not a result claimed here.",
    title="CLEANEST RESULT, SHORTEST HISTORY"
)
box(
    "Section 5.23 tested only momentum on ASX. Section 5.24 completes the "
    "picture: do 52-week-high and reversal replicate too?",
    kind="fact", title="UPDATE FROM SECTION 5.24"
)

h1("5.24  Milestone 23 &mdash; Completing the ASX picture: do 52-week-high and reversal replicate too?")
p("Section 5.23 tested only momentum on ASX. NSE and the US mirror were "
  "both tested on all three signals from the first pass (Section 5.4) "
  "&mdash; ASX had an incomplete picture by comparison. This milestone "
  "runs 52-week-high and short-term reversal on ASX with the identical "
  "out-of-sample hedge + HAC methodology, closing that gap.")
data_table(
    ["", "Long leg (daily / monthly)", "Combined (daily / monthly)"],
    [
        ["52-week-high", "+7.00%/yr, p=.099 / +8.41%/yr, p=.0091", "+24.52%/yr, p=.0126 / +23.80%/yr, p=.0023"],
        ["Short-term reversal", "-4.04%/yr, p=.491 / -3.40%/yr, p=.529", "-3.14%/yr, p=.818 / -2.49%/yr, p=.719"],
    ],
    col_widths=[1.5*inch, 2.75*inch, 2.75*inch],
    small=True,
)
p("<b>Reversal replicates the established pattern: no edge, anywhere.</b> "
  "Consistent with Section 5.16's full retraction on NSE and the US "
  "mirror, reversal shows nothing on ASX either &mdash; not close to "
  "significant at either frequency, either leg. A third market, the "
  "identical null. This is a confirming result, not a new one, and needs "
  "no further qualification.")
p("<b>52-week-high does not &mdash; and this is a genuine update to a "
  "conclusion this project called &quot;resolved&quot; three signals "
  "ago.</b> Sections 5.7-5.8 found 52-week-high's apparent edge on NSE "
  "and the US mirror was <i>entirely</i> a construction flaw: an "
  "uncontrolled long/short beta mismatch, with <b>zero</b> significant "
  "alpha in 12 of 12 hedged regressions across both markets and both "
  "frequencies. On ASX, the hedged combined book is significant at both "
  "frequencies (p=0.0126 daily, p=0.0023 monthly), and even the long leg "
  "alone clears significance monthly (p=0.0091). This is not the same "
  "failure mode Sections 5.7-5.8 found &mdash; the alpha survives the "
  "hedge here, rather than vanishing once beta is controlled for.")
p("<b>But this likely isn't a second, independent anomaly &mdash; it's "
  "the same mechanism as momentum's ASX result, viewed through a highly "
  "correlated signal.</b> 52-week-high and 12-1 momentum are both "
  "trend-following constructions (recent winners vs. losers), and on "
  "ASX their leg returns are correlated at <b>0.76 (long leg) and 0.82 "
  "(combined book)</b> &mdash; they are substantially picking the same "
  "names. The short leg's mean beta (-1.36) is close to momentum's own "
  "short-leg beta (-1.26) from Section 5.23, consistent with both "
  "signals' short sides being loaded with the same high-beta mining and "
  "resources stocks that underperformed through 2011-2015. The honest "
  "reading: ASX's 2011-2015 divergence was severe and persistent enough "
  "that <i>any</i> reasonable trend-following construction would have "
  "captured it, not that 52-week-high anchoring specifically is a real, "
  "independent behavioral edge on this market.")
box(
    "Momentum remains this project's one demonstrably robust, "
    "independently-replicated finding across all three markets. "
    "52-week-high's ASX result should be read as an open, "
    "mechanism-ambiguous finding &mdash; real and hedge-robust, but not "
    "yet shown to be <i>more</i> than momentum wearing a different "
    "construction &mdash; not folded in alongside momentum as a second "
    "confirmed ASX edge. The natural next check (momentum as an explicit "
    "control in the same regression) has not yet been run.",
    title="ONE MECHANISM, TWO CONSTRUCTIONS"
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
    "momentum. At the time, it looked like it wasn't: short-term "
    "reversal's long leg showed the identical &quot;real pre-1994, "
    "decayed since&quot; signature (p=0.046 pre-1994, p=0.629 post), "
    "invisible inside Part V.9's full-sample null. 52-week-high, by "
    "contrast, showed no significant alpha in either era &mdash; it "
    "never had genuine skill at all. <i>(Part V.16 later retracted "
    "reversal's side of this finding entirely &mdash; see below.)</i>",
    kind="fact", title="UPDATE FROM PART V.13"
)
box(
    "Part V.14 then quantified the decay rate directly instead of "
    "trusting the 1994 cutoff, and found the two signals decay in "
    "genuinely different shapes &mdash; at the time. Reversal's "
    "decline looked like a real, smooth, statistically significant "
    "linear trend (zero-crossing ~November 2004). Momentum's was not "
    "smooth at all: alpha stayed flat and strong through 2008, then "
    "broke sharply, better described as a 2008-09 regime shift than "
    "gradual 1994-onward decay. <i>(Reversal's side of this was later "
    "retracted; momentum's was not &mdash; see Part V.16.)</i>",
    kind="fact", title="UPDATE FROM PART V.14"
)
box(
    "Part V.15 then formalized the 2008-09 claim with an actual "
    "structural-break test rather than a descriptive comparison. A "
    "single, literature-motivated Chow test at 2008-09-01 does confirm "
    "a real break in momentum (p=0.026) &mdash; but an unconstrained "
    "search corrected for multiple testing finds its best-fitting "
    "break 27 months later (Dec 2010) and that maximum is not "
    "significant (bootstrap p=0.138). Reversal appeared to show the "
    "opposite: nothing at 2008, but a genuine, significant break "
    "(bootstrap p=0.048) around <b>August 1980</b>. <i>(Part V.16 "
    "investigated that August 1980 date directly and found it was not "
    "a real market event &mdash; see below.)</i>",
    kind="fact", title="UPDATE FROM PART V.15"
)
box(
    "Part V.16 investigated the mechanism behind that August 1980 date "
    "at explicit request, rather than reporting it and moving on. It "
    "found reversal's decile long leg was only 2-4 stocks from 1972-83, "
    "drawn from a tiny, survivorship-biased universe, plus two "
    "previously undocumented data anomalies (WMT, INTC). <b>Reversal's "
    "entire positive-alpha claim &mdash; carried since Part V.10 "
    "&mdash; evaporates completely (p=0.54-0.96) once the unreliable "
    "1972-1977 window is excluded, including from the exact date this "
    "section's own break search identified.</b> Momentum, tested as a "
    "control on the identical data, was unaffected (p&le;0.02 "
    "throughout). Treat every reversal claim in this Part VI as "
    "retracted; momentum's claims stand.",
    kind="fact", title="UPDATE FROM PART V.16"
)
box(
    "Part V.17 then gave momentum's 2008-09 break a real mechanism: "
    "reapplying this project's own Bear &times; High-Vol momentum-crash "
    "regression (Part V.7-5.8, rejected for the 52-week-high signal) to "
    "momentum's hedged long leg, split at 2008-09-01. The interaction "
    "term is insignificant pre-2008 (p=0.42) but large, negative, and "
    "significant post-2008 (p=0.008): on Bear+High-Vol days, the long "
    "leg loses at roughly a 37% annualized rate post-2008, versus an "
    "insignificant ~11% pre-2008. <b>The classic momentum-crash "
    "mechanism was dormant before 2008 and activated after &mdash; a "
    "genuine causal story, not just a confirmed date.</b> <i>(Part "
    "V.19 later refined &mdash; did not retract &mdash; the &quot;activated "
    "after&quot; framing: see below.)</i>",
    kind="fact", title="UPDATE FROM PART V.17"
)
box(
    "Part V.18 then tested the same crash mechanism on NSE, and in the "
    "process exposed a gap in this project's own earlier NSE test. "
    "Part V.9's &quot;no significant NSE momentum alpha&quot; used a "
    "static regression, never the rolling out-of-sample hedge used for "
    "every US test since Part V.8. Applying that hedge to NSE for the "
    "first time reaffirms no significant full-sample alpha, but finds "
    "a tentative, &quot;promising not confirmed&quot; post-2008 signal "
    "(daily p=0.044) the cruder test missed. The Bear &times; High-Vol "
    "crash mechanism itself, however, does <b>not</b> replicate on "
    "NSE (p=0.96) &mdash; NSE shows a plain Bear effect instead, not "
    "the specific crash-rebound dynamic found for the US. <i>(Part V.22 "
    "later found this tentative NSE signal does not survive its own "
    "named universe-growth caveat &mdash; see below.)</i>",
    kind="fact", title="UPDATE FROM PART V.18"
)
box(
    "Part V.19 then split Part V.17's &quot;post-2008&quot; block at "
    "2009-12-31 and found the trailing-12-month market return never went "
    "negative again after September 2009 through the end of the US "
    "sample &mdash; so the interaction term's pooled significance was "
    "carried entirely by the 337-day crisis window, and cannot even be "
    "tested against the ~2,000 days since (zero Bear+High-Vol "
    "observations there). Worse for the &quot;interaction&quot; framing "
    "specifically: run on the crisis window alone, the multiplicative "
    "term itself is not significant (p=0.26) &mdash; high volatility and "
    "bear-state each mattered independently instead. <b>The 2008-09 "
    "break is real; &quot;activated since 2008&quot; is not demonstrated "
    "&mdash; it is confirmed for the one crisis this sample's post-2008 "
    "window actually contains, and untested since, because no comparable "
    "bear market has recurred.</b> <i>(Part V.20 found this &quot;no "
    "comparable bear market&quot; claim itself depends on the 252-day "
    "lookback used to define &quot;bear market&quot; &mdash; see "
    "below.)</i>",
    kind="fact", title="UPDATE FROM PART V.19"
)
box(
    "Part V.20 swept the two parameters every regime-based finding since "
    "Part V.6 has used &mdash; the volatility window and the bear-market "
    "lookback &mdash; across a 4&times;4 grid. Part V.17's pattern "
    "(dormant pre-2008, active post) replicated in 8 of 16 combinations, "
    "reliably near this project's own defaults but not at the shortest "
    "windows tested. Part V.19's stronger claim &mdash; that no bear "
    "market recurred after 2009 &mdash; did <b>not</b> survive shorter, "
    "equally standard bear-lookbacks: at 126 or 189 trading days instead "
    "of 252, a bear regime fires post-2010, clustered in 2010-11 and "
    "2015-16. Two different robustness verdicts for two different claims "
    "built on the same code. <i>(Part V.21 then ran the persistence test "
    "this made possible &mdash; see below.)</i>",
    kind="fact", title="UPDATE FROM PART V.20"
)
box(
    "Part V.21 re-ran the crash-mechanism interaction on the 2010-onward "
    "window under both alternate bear-lookbacks Part V.20 identified. It "
    "did not reactivate at either (p=0.20, p=0.44), and at the 189-day "
    "lookback the bear-market main effect was significant but "
    "<b>positive</b> &mdash; the opposite sign from crash risk. This "
    "strengthens, not just leaves open, Part V.19's &quot;confirmed for "
    "one crisis&quot; framing: the mechanism is now tested and not found "
    "outside 2008-09, in the two next bear-adjacent episodes this sample "
    "contains, not merely untested.",
    kind="fact", title="UPDATE FROM PART V.21"
)
box(
    "Part V.22 turned the pooled-window lesson from Parts V.19-21 back "
    "on this project's own remaining open finding: Part V.18's tentative "
    "NSE signal. Splitting at the date NSE's universe became permanently "
    "fixed at 48 names, neither the growing sub-period nor the fully "
    "stable sub-period is significant alone (p=0.11, p=0.18) &mdash; "
    "only the pooled full window is. Not the growth confound named, but "
    "the same pooling problem diagnosed in the crash mechanism, applied "
    "to this project's own house-favored open thread.",
    kind="fact", title="UPDATE FROM PART V.22"
)
box(
    "Part V.23 found and validated a genuinely independent third market "
    "(ASX Australia) after ruling out every reachable European source, "
    "and applied this project's current best methodology &mdash; the "
    "out-of-sample hedge, not the crude full-sample regression this "
    "project itself started with &mdash; from the very first test. "
    "Momentum's long leg came back significant at both daily (p=0.0085) "
    "and monthly (p=0.0141) frequency, the cleanest result of the three "
    "markets tested, on this project's shortest sample (six years).",
    kind="fact", title="UPDATE FROM PART V.23"
)
box(
    "Part V.24 completed the ASX picture. Reversal replicated its "
    "established null cleanly. 52-week-high did not: significant hedged "
    "alpha at both frequencies, reopening a question Parts V.7-8 had "
    "called resolved. But its ASX leg returns correlate 0.76-0.82 with "
    "momentum's own, and its short-leg beta (-1.36) nearly matches "
    "momentum's (-1.26) &mdash; the two signals are substantially "
    "picking the same names. Read as one mechanism (ASX's 2011-2015 "
    "mining divergence) viewed through two correlated constructions, not "
    "two independent confirmed anomalies.",
    kind="fact", title="UPDATE FROM PART V.24"
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
    "from a signal that was simply never real. <i>(This specific "
    "reversal example was itself later retracted by Part V.16 &mdash; "
    "see below &mdash; but the underlying rule, that a full-sample null "
    "deserves a second look with an era-split toolkit, still stands.)</i>",
    "<b>A binary before/after split can get the direction right while "
    "getting the mechanism wrong &mdash; quantify the trend continuously "
    "before naming a cause.</b> Part V.14 fit a continuous linear decay "
    "rate to momentum's and reversal's hedged long legs instead of "
    "trusting the 1994 publication-date cutoff. Reversal's decay "
    "appeared, at the time, to be genuinely smooth and statistically "
    "significant, consistent with the publication-decay story &mdash; "
    "later shown by Part V.16 to be an artifact, not a real trend. "
    "Momentum's trend was not significant, because the real pattern is "
    "a sharp break around the 2008-09 financial crisis, not a gradual "
    "erosion starting in 1994 &mdash; and that finding held up. Once a "
    "binary split finds a real effect, don't stop there &mdash; fit a "
    "continuous trend and inspect a rolling, non-parametric trajectory "
    "to check whether the story you're about to tell actually matches "
    "the shape of the data, or just happens to fall on the correct "
    "side of an arbitrary cutoff.",
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
    "<b>When a signal's finding depends on data density you haven't "
    "checked, check it before trusting the finding.</b> Part V.16 "
    "traced reversal's August 1980 &quot;break&quot; to its source: a "
    "decile portfolio of only 2-4 stocks, drawn from a 9-14-name "
    "universe of today's mega-cap survivors backfilled to the 1970s "
    "&mdash; plus two previously undocumented data anomalies (an "
    "apparent unadjusted-split round-trip in WMT, two large jumps in "
    "INTC). Reversal's entire positive-alpha claim depended on this "
    "unreliable window and vanished completely once it was excluded, "
    "at every later start date tested. Momentum, run through the "
    "identical thin data as a control, was unaffected. A decile "
    "portfolio with 2-4 names is not a diversified strategy, it is a "
    "handful of individual stock bets, and &quot;statistically "
    "significant&quot; on such a sample tells you about those "
    "specific stocks' survivorship, not about a market-wide "
    "behavioral effect. Check minimum portfolio size and data density "
    "for every sub-period a significance claim rests on, not just the "
    "full sample's average.",
    "<b>A structural break confirmed by a date is still an unexplained "
    "fact until tested against a named mechanism.</b> Part V.17 applied "
    "this project's own Bear &times; High-Volatility momentum-crash "
    "regression (Parts V.7-8, rejected for the 52-week-high signal, "
    "full-sample) to momentum's hedged long leg, split at the same "
    "2008-09-01 date. The interaction term is insignificant pre-2008 "
    "(p=0.42) but large, negative, and significant post-2008 (p=0.008) "
    "&mdash; the classic momentum-crash mechanism was dormant through "
    "the pre-crisis decades and activated since. A mechanism this "
    "project rejected for one signal, in one era, can still be real "
    "for a different signal in a different era &mdash; don't let an "
    "earlier rejection close off re-testing the same hypothesis "
    "somewhere new; a confirmed break date is a fact, not yet an "
    "explanation.",
    "<b>&quot;Already checked&quot; and &quot;checked with your "
    "current best method&quot; are not the same claim.</b> Part V.9's "
    "NSE momentum test used a static full-sample regression. Applying "
    "the rolling out-of-sample hedge this project built in Part V.8 to "
    "NSE momentum for the first time reaffirmed no significant "
    "full-sample alpha, but surfaced a tentative post-2008 signal "
    "(daily p=0.044, monthly p=0.073) the cruder test lacked the power "
    "to see &mdash; while the Bear &times; High-Volatility crash "
    "mechanism confirmed for US momentum (Part V.17) turned out not to "
    "replicate on NSE at all. A rejected finding on an already-tested "
    "market is worth re-checking with each new methodology upgrade "
    "this project builds, not just applying new methods to new "
    "markets &mdash; the earlier rejection may have been correct for "
    "the test it used and still be missing something a better test "
    "would find; and a confirmed mechanism on one market is a "
    "hypothesis, not a law, everywhere else.",
    "<b>A pooled multi-year regression's significant coefficient can be "
    "one crisis acting as its own control group, not a persisting "
    "regime.</b> Part V.19 split Part V.17's &quot;post-2008&quot; test "
    "window at end-2009 and found the US mirror's trailing-12-month "
    "market return never went negative again after September 2009 "
    "through the end of the sample &mdash; so the interaction term found "
    "significant across the whole post-2008 block had zero Bear+High-Vol "
    "observations to draw on outside the 337-day crisis itself. Run on "
    "the crisis window alone, the multiplicative interaction specifically "
    "was not significant (p=0.26); volatility and bear-state each "
    "mattered on their own instead. Before reading a coefficient "
    "significant across a multi-year window as evidence of a standing "
    "regime, split the window and check whether the conditioning regime "
    "actually recurs throughout it &mdash; a test that silently rests on "
    "one sub-period contrasted against a calm remainder is a test of "
    "&quot;did something happen once,&quot; not &quot;is this now a "
    "permanent feature.&quot;",
    "<b>A qualitative pattern and the specific quantitative claim built on "
    "top of it can have very different robustness, and a binary &quot;did "
    "X ever happen&quot; claim is only as robust as its own "
    "definition.</b> Part V.20 swept the two regime-construction "
    "parameters every crash-regime finding since Part V.6 has used "
    "&mdash; a 4&times;4 grid of volatility windows and bear-market "
    "lookbacks. Part V.17's &quot;dormant pre-2008, active post-2008&quot; "
    "pattern replicated in 8 of 16 nearby parameter combinations, "
    "reliably near this project's own defaults. But Part V.19's specific "
    "&quot;no bear market recurred after 2009&quot; claim did not survive "
    "shorter, equally standard bear-lookbacks (126 or 189 trading days "
    "instead of 252) &mdash; a bear regime fires post-2010 under those "
    "conventions. Test the pattern and the specific claim separately, "
    "since they can have different robustness; and when a finding rests "
    "on whether some condition ever occurred, stress-test the "
    "condition's own definition, not just the finding built on top of "
    "it &mdash; the definition is often the more arbitrary choice.",
    "<b>&quot;Untested&quot; and &quot;tested and not found&quot; are "
    "different claims, and closing a robustness thread means running the "
    "test it made possible, not just noting that it's now possible.</b> "
    "Part V.21 re-ran the crash-mechanism persistence test under the two "
    "bear-lookbacks Part V.20 found actually see a post-2010 bear "
    "regime. The interaction did not reactivate at either window "
    "(p=0.20, p=0.44), and at the 189-day lookback the bear-market main "
    "effect was significant but positive &mdash; the opposite sign from "
    "crash risk. When a robustness check reveals that a previously "
    "untestable question has become testable, run the test rather than "
    "leaving it flagged as an open thread &mdash; a mechanism that fails "
    "to reactivate when given a real chance to is materially stronger "
    "evidence than a mechanism that was simply never checked.",
    "<b>A named caveat is a promise to test it, and a lesson learned "
    "from one correction applies to your own other findings, not just "
    "the one that taught it.</b> Part V.22 tested the growth-confound "
    "caveat Part V.18 attached to the tentative NSE momentum signal, "
    "splitting at the exact date NSE's universe became permanently "
    "fixed at 48 names. The growing sub-period showed a larger point "
    "estimate, not a smaller, thin-universe-inflated one, so the named "
    "confound wasn't confirmed &mdash; but neither sub-period reached "
    "significance alone, only the pooled full window, the identical "
    "pooled-window pattern Parts V.19-21 had just diagnosed in the "
    "crash mechanism. Apply a methodology lesson learned from one "
    "finding to every other finding built the same way, including your "
    "own project's most-favored remaining result &mdash; a named but "
    "untested caveat is unfinished work, not a disclosed limitation.",
    "<b>A sandbox's specific network allowlist is itself a research "
    "constraint worth documenting, and a genuinely independent third "
    "market is worth the search effort even when the first choice "
    "isn't reachable.</b> Part V.23 spent real effort ruling out Stooq, "
    "Hugging Face, <i>github.com</i>'s own pages, and general "
    "<i>api.github.com</i> browsing before finding "
    "<i>raw.githubusercontent.com</i> could serve a real, committed ASX "
    "dataset once the exact file paths were known. Momentum replicated "
    "cleanly there (p=0.0085 daily, p=0.0141 monthly), the strongest of "
    "the three markets, on a sample too short (six years) for the "
    "era-stability checks run on the US mirror. Document a data "
    "search's dead ends, not just its destination &mdash; the next "
    "milestone benefits from knowing which doors were tried and found "
    "locked; and label a new result by what it has and hasn't yet been "
    "checked against, not by how clean it looks on first pass.",
    "<b>A correlated pair of signals confirming together is not two "
    "confirmations &mdash; check whether a new result is independent of "
    "an already-established one before counting it separately.</b> Part "
    "V.24 completed the ASX picture: reversal replicated its established "
    "null cleanly, but 52-week-high showed significant hedged alpha "
    "where Parts V.7-8 had found zero alpha in 12 of 12 regressions on "
    "the other two markets. Checking the correlation between "
    "52-week-high's and momentum's ASX leg returns (0.76 long leg, 0.82 "
    "combined) and their near-identical short-leg betas (-1.36 vs. "
    "-1.26) showed the two signals were substantially picking the same "
    "names. Before treating a new significant result as a second, "
    "independent finding, check its correlation with an already-"
    "confirmed one built from related inputs &mdash; a shared "
    "underlying driver can make one real economic effect look like two "
    "separate discoveries.",
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
  "(Parts V.10-11's check), and a minimum-data-density flag on any "
  "period where a decile portfolio would hold fewer than roughly 10 "
  "names (Part V.16, which found a &quot;genuine&quot; edge that was "
  "actually 2-4 survivor-biased stocks) &mdash; differentiators most "
  "factor-data vendors don't surface at all) and a <b>risk side</b> (the regime-switching "
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
    "<b>Short-term reversal's positive result is retracted, fully, at "
    "every level this project checked (Parts V.9, then V.13, then "
    "V.16 &mdash; a claim that briefly looked rehabilitated before "
    "being retracted again, more thoroughly).</b> Part V.9's "
    "full-sample CAPM beta check found none of reversal's 12 alpha "
    "tests significant. Part V.13 then found this incomplete: "
    "reversal's long leg carried a real-looking, significant pre-1994 "
    "alpha (p=0.046) hidden inside that full-sample average. But Part "
    "V.16 traced that apparent pre-1994 alpha to its source and found "
    "it depends entirely on a severely thin (2-4 stock), "
    "survivorship-biased, partly data-glitched 1972-1977 sample window "
    "&mdash; it vanishes completely (p=0.54-0.96, often slightly "
    "negative) from any start date at or after 1978, including the "
    "exact date Part V.15's own structural-break search identified as "
    "reversal's &quot;true&quot; break (1980-08-29, p=0.922). "
    "Momentum, tested through the identical unreliable early data as a "
    "control, was unaffected (p&le;0.02 at every comparable start "
    "date). <b>Reversal shows no reliably demonstrated edge anywhere "
    "in this dataset, in any leg, at any point in the sample, once "
    "properly checked.</b>",
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
    "with a market-wide explanation rather than a momentum idiosyncrasy. "
    "<i>(Since retracted for reversal &mdash; Part V.16 traced this "
    "&quot;pattern&quot; to a thin, survivorship-biased early sample; "
    "momentum's finding is unaffected.)</i>",
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
    "slow, 1990s publication-driven crowding. <i>(Since retracted for "
    "reversal &mdash; Part V.16 found this &quot;smooth trend&quot; was "
    "itself an artifact of unreliable early data; momentum's finding is "
    "unaffected.)</i>",
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
    "framing. <i>(Since retracted for reversal &mdash; Part V.16 found "
    "this August 1980 &quot;break&quot; is a thin-universe and "
    "data-quality artifact, not a real 1980 market event; momentum's "
    "finding is unaffected.)</i>",
    "<b>What actually happened in 1980? Not a market event &mdash; a "
    "thin, survivorship-biased universe plus a data-quality defect "
    "(Part V.16).</b> Investigating the mechanism behind Part V.15's "
    "August 1980 reversal break at explicit request, rather than "
    "reporting the date and moving on, found reversal's decile long "
    "leg was only 2-4 stocks from 1972-1983, drawn from a 9-14-name "
    "universe of today's mega-cap survivors backfilled to their "
    "earliest available data, plus two previously undocumented data "
    "anomalies (WMT round-trips -52%/+109% across two weeks in "
    "December 1974; INTC jumps +101% and +51% in 1972, both consistent "
    "with split-adjustment errors). Re-testing reversal's long-leg "
    "significance from a range of start dates shows its entire "
    "positive-alpha claim (already only marginal at full sample, "
    "p=0.068) depends completely on the unreliable 1972-1977 window: "
    "from any later start, including the exact date Part V.15's own "
    "search identified, alpha is never significant (p=0.54 to 0.96, "
    "usually slightly negative). Momentum, run through the identical "
    "thin, biased, partly-glitched early data as a control, was "
    "unaffected (p&le;0.02 at every comparable start date). "
    "<b>Short-term reversal's apparent pre-2005 alpha is retracted "
    "outright, not narrowed: this project has found no reliably "
    "demonstrated reversal edge anywhere in this dataset, in any leg, "
    "at any point in the sample.</b>",
    "<b>Momentum's 2008-09 break now has a concrete causal mechanism, "
    "not just a confirmed date (Part V.17).</b> Applying this "
    "project's own look-ahead-free Bear &times; High-Volatility "
    "momentum-crash regression (Parts V.7-8, where it was rejected for "
    "the 52-week-high signal, full-sample) to momentum's hedged long "
    "leg, split at 2008-09-01: the interaction term is small and "
    "insignificant pre-2008 (p=0.42) but large, negative, and "
    "significant post-2008 (coef=-0.00218/day, p=0.008) &mdash; on the "
    "~9% of post-2008 trading days that are both high-volatility and "
    "trailing-bear, the long leg loses at an annualized rate around "
    "37%. The classic momentum-crash mechanism this project rejected "
    "for the original signal turns out to be real for momentum "
    "specifically, but conditional on era: dormant through the "
    "pre-crisis decades, active since. <i>(Refined, not retracted, by "
    "Part V.19: the &quot;active since&quot; framing overstates what was "
    "tested &mdash; see below.)</i>",
    "<b>The momentum-crash mechanism does not replicate on NSE "
    "&mdash; but a more rigorous re-test finds a tentative NSE "
    "momentum signal a cruder test had missed (Part V.18).</b> Part "
    "V.9's &quot;no significant NSE momentum alpha&quot; used a "
    "static full-sample regression; applying the project's own "
    "rolling out-of-sample hedge (used for every US momentum test "
    "since Part V.8) to NSE momentum for the first time reaffirms no "
    "significant alpha full-sample (daily p=0.170, monthly p=0.168), "
    "but surfaces a new, &quot;promising, not confirmed&quot; "
    "post-2008 signal (daily p=0.044, monthly p=0.073, marginal) "
    "&mdash; with the real caveat that NSE's universe itself grew "
    "from ~30 to 48 names over this window, so part of the "
    "improvement may reflect a less thin cross-section rather than a "
    "genuine regime change. <i>(Downgraded by Part V.22: testing this "
    "exact caveat found neither sub-period significant alone &mdash; "
    "see below.)</i> Separately, Part V.17's exact Bear "
    "&times; High-Vol interaction is never significant on NSE (p=0.96 "
    "full-sample) &mdash; the specific crash-<i>rebound</i> mechanism "
    "found for US momentum does not generalize. NSE does show a "
    "plain, unconditional Bear effect instead (loses significantly in "
    "any trailing bear market, p=0.002 full-sample) &mdash; a related "
    "but mechanistically different, more generic bear-market "
    "sensitivity.",
    "<b>Milestone 16's &quot;post-2008 crash regime&quot; is really "
    "&quot;the one crisis in the post-2008 window,&quot; not a standing "
    "feature &mdash; and in isolation, the interaction term itself is "
    "not what's significant (Part V.19).</b> Splitting the post-2008-09 "
    "block at 2009-12-31: the US mirror's trailing-12-month market "
    "return never went negative again after September 2009, through the "
    "end of its coverage (Nov 2017) &mdash; the 2011 and 2015-16 "
    "selloffs both recovered before the 252-day lookback registered them "
    "as sustained bear states. That means Part V.17's &quot;post-2008&quot; "
    "test is entirely carried, for the interaction term, by the 337-day "
    "2008-09 crisis window; the other ~2,000 post-crisis days contribute "
    "zero Bear+High-Vol observations, so the interaction cannot even be "
    "estimated there (rank-deficient regression). Worse for the "
    "&quot;interaction&quot; framing specifically: run on the crisis "
    "window alone, the multiplicative term itself is <i>not</i> "
    "significant (p=0.26 long leg, p=0.31 combined) &mdash; high "
    "volatility alone (p&lt;0.0001) and the bear flag alone (p=0.036-"
    "0.005) do the work instead. Read Part V.17's finding as: real for "
    "the 2008-09 crisis specifically, evidence for volatility and "
    "bear-state each mattering independently more than for their "
    "interaction being the mechanism, and untested &mdash; not "
    "disconfirmed &mdash; as a standing post-2008 regime, since no "
    "comparable bear market has recurred in this sample to test "
    "against. <i>(Part V.20 found this &quot;no comparable bear "
    "market&quot; claim itself depends on the 252-day lookback used to "
    "define &quot;bear market&quot; &mdash; see below.)</i>",
    "<b>The crash-mechanism pattern replicates across most, but not "
    "all, nearby regime-construction choices &mdash; and the specific "
    "claim that no bear market recurred after 2009 does not (Part "
    "V.20).</b> Sweeping a 4&times;4 grid of volatility windows "
    "(10/21/42/63 days) and bear-market lookbacks (126/189/252/378 "
    "days): Part V.17's pattern holds in 8 of 16 combinations, reliably "
    "(3 of 4 lookbacks) at this project's own default 21-day volatility "
    "window and the adjacent 42-day window, but never at the shortest "
    "10-day window and rarely at the shortest 126-day bear-lookback. "
    "The default combination Parts V.17-19 actually used sits inside "
    "the reliable region, not at a cherry-picked edge case. But the "
    "bear-regime-frequency finding underlying Part V.19 is fragile: a "
    "bear regime fires post-2010 at both shorter lookbacks tested (126 "
    "and 189 days, clustered in 2010-11 and 2015-16) and never at the "
    "two longer ones (252, the default, and 378) &mdash; so whether the "
    "crash mechanism has a second data point to test persistence "
    "against depends on which standard convention is chosen, and that "
    "persistence test has not yet been re-run under the windows where a "
    "second bear regime actually exists. <i>(Closed by Part V.21: "
    "re-run under both alternate lookbacks, the mechanism did not "
    "reactivate &mdash; see below.)</i>",
    "<b>The crash mechanism did not reactivate in 2011 or 2015-16, even "
    "once real bear-regime days exist to test it against (Part "
    "V.21).</b> Re-running the Bear &times; High-Vol interaction on the "
    "2010-onward window under the two lookbacks (126 and 189 days) where "
    "a bear regime actually recurs: the interaction is not significant "
    "at either window (p=0.203 at 126 days, p=0.443 at 189 days), "
    "despite 148 and 31 Bear+High-Vol days respectively to test it "
    "against. At the 189-day lookback the bear-market main effect "
    "<i>is</i> significant (p=0.023) but positive &mdash; momentum's "
    "long leg did somewhat better, not worse, during those trailing-bear "
    "periods, the opposite sign from both the 2008-09 crisis coefficient "
    "and what the crash-risk mechanism predicts. This strengthens, "
    "rather than merely leaves open, Part V.19's &quot;confirmed for one "
    "crisis&quot; framing: the mechanism is now tested and not found "
    "outside 2008-09, not just untested. Whether it would reactivate in "
    "a genuinely severe future crisis, as opposed to the milder 2011 and "
    "2015-16 episodes, remains open &mdash; this sample has not "
    "contained one since 2009.",
    "<b>The tentative NSE post-2008 momentum signal (Part V.18) does not "
    "survive splitting by universe stability &mdash; its own named "
    "caveat, finally tested (Part V.22).</b> NSE's universe grew from "
    "~30 names in 2000 to a fixed 48 by 2010-11-04, then stayed at "
    "exactly 48 names every day through the end of the sample. "
    "Splitting Part V.18's post-2008 window at that date: the growing "
    "sub-period (2008-09 to 2010-11, n=535 days) shows a <i>larger</i> "
    "point estimate (+23.72%/yr) than the full window but is not "
    "significant (p=0.112) on its own; the fully stable, fixed-48-name "
    "sub-period (2010-11 onward, n=2,579 days) shows a smaller point "
    "estimate (+4.60%/yr) and is also not significant (p=0.180). "
    "Neither direction of the growth-confound concern is confirmed "
    "&mdash; the growing years are not where the significance is "
    "concentrated &mdash; but a different, arguably more serious "
    "problem is: the full-window significance (p=0.044) exists only "
    "when the two sub-periods are pooled, echoing the exact "
    "pooled-window lesson Parts V.19-21 learned about the crash "
    "mechanism, applied here to this project's own remaining open "
    "finding. The NSE post-2008 signal should now be read as not "
    "currently demonstrated, not merely as an unconfirmed but promising "
    "thread.",
    "<b>Momentum replicates on a third, independent market (ASX "
    "Australia), the cleanest result of the three tested &mdash; but on "
    "this project's shortest history, and finding the market at all "
    "took real effort (Part V.23).</b> A thorough search for a European "
    "per-company OHLCV mirror found none reachable from this sandbox: "
    "<i>stooq.com</i>, <i>huggingface.co</i>, <i>github.com</i>'s own "
    "HTML pages, and general <i>api.github.com</i> repo browsing are "
    "all blocked, and several candidate repositories turned out to be "
    "fetch-at-runtime pipeline code (also blocked), not committed data. "
    "<i>grantcarthew/data-asx-historical-share-tables</i> &mdash; a "
    "mirror of ASX's own daily S&amp;P/ASX300 report emails, 2009-10-20 "
    "to 2015-12-31 &mdash; was the source that worked. Applying this "
    "project's out-of-sample hedge and HAC significance test directly "
    "(not the cruder full-sample regression Parts V.7-9 started with): "
    "long-leg alpha +11.14%/yr daily (p=0.0085) and +9.97%/yr monthly "
    "(p=0.0141); the combined book shows an even larger, still-"
    "significant effect (p&lt;0.001 both frequencies), plausibly tied "
    "to Australia's 2011-2015 mining-sector downturn loading the short "
    "leg with high-beta losers (mean short-leg beta -1.26 vs. the long "
    "leg's +0.83) rather than being a hedge-instability artifact "
    "(rolling beta std 0.39, no extreme outliers). This is a real "
    "limitation, not just a caveat: six years is enough for a "
    "full-sample significance test but not for the era-splits, "
    "structural-break tests, or persistence checks Parts V.10-15 ran on "
    "the US mirror's 47-year history &mdash; ASX momentum has not yet "
    "been checked for stability across sub-periods the way every other "
    "surviving finding in this project has.",
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
    "currently built. <i>(Reopened, not overturned, by Part V.24: ASX "
    "shows significant hedged 52-week-high alpha, but it correlates "
    "0.76-0.82 with momentum's own ASX result &mdash; likely the same "
    "mechanism, not new independent skill. See below.)</i>",
    "<b>52-week-high shows significant hedged alpha on ASX &mdash; "
    "reopening, not confirming, a question Parts V.7-8 called resolved "
    "&mdash; but it is highly correlated with momentum's own ASX result, "
    "not clearly a second independent edge (Part V.24).</b> On ASX, the "
    "hedged combined book is significant at both frequencies (p=0.0126 "
    "daily, p=0.0023 monthly) &mdash; the alpha survives the hedge this "
    "time, a different failure mode than before. But 52-week-high's and "
    "momentum's ASX leg returns correlate at 0.76 (long leg) and 0.82 "
    "(combined book), and the short leg's mean beta (-1.36) closely "
    "matches momentum's own (-1.26) &mdash; both signals are "
    "substantially picking the same names, consistent with both simply "
    "capturing Australia's 2011-2015 mining-sector divergence rather "
    "than 52-week-high anchoring being an independent behavioral edge on "
    "this market. Reversal, tested alongside it, shows nothing "
    "(p=0.49-0.82 across all four cuts) &mdash; a clean confirmation of "
    "its established null. Treat 52-week-high's ASX result as open and "
    "mechanism-ambiguous, not as a second confirmed ASX anomaly alongside "
    "momentum &mdash; the natural next check (momentum as an explicit "
    "control in the same regression) has not yet been run.",
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
  "break of its own, decades earlier than anyone had looked. Part V.16 "
  "then did what none of the previous checks had: it asked "
  "<i>why</i> that August 1980 date, rather than reporting it as a fact "
  "and moving on. The answer was not a market event. It was a decile "
  "portfolio of two to four stocks, drawn from a universe of today's "
  "mega-cap survivors backfilled to the 1970s, compounded by two "
  "previously undiscovered data anomalies. Reversal's entire "
  "positive-alpha claim &mdash; the one this project had been "
  "calling &quot;genuine&quot; since Part V.10, narrowing and "
  "re-narrowing it seven separate times without ever asking whether it "
  "was real &mdash; evaporated the moment the unreliable years were "
  "excluded, at every start date tested, including the exact date its "
  "own break search had identified. Momentum, run through the identical "
  "unreliable data as a control, was untouched. Part V.17 then closed "
  "the loop this project opened in Part V.5-6 and never fully resolved: "
  "does the classic momentum-crash mechanism, rejected there for a "
  "different signal on the full sample, actually explain why momentum "
  "broke in 2008-09? Reapplying that same rejected regression to "
  "momentum's own hedged long leg, split at the same break date, found "
  "the answer was conditional: dormant pre-2008 (statistically "
  "indistinguishable from the earlier full-sample rejection), then "
  "sharply, significantly active since. The one surviving finding in "
  "this entire guide now has not just a confirmed break date, but a "
  "named, tested reason for it. Part V.18 then took that reason abroad, "
  "to the one market this project had visited more than any other and "
  "trusted least: does the same crash mechanism show up on NSE, which "
  "lived through the same 2008 crisis? It doesn't &mdash; the specific "
  "Bear-plus-High-Vol interaction never clears significance there. But "
  "testing it required re-running NSE momentum through this project's "
  "own best hedge methodology for the first time, not the cruder "
  "regression Part V.9 had used, and that re-run found something new: "
  "a tentative signal since 2008 the earlier test had lacked the power "
  "to see. Even a market this project believed it had already closed "
  "the book on had more to say once asked with a better instrument. "
  "Part V.19 then turned that same instinct back on Part V.17's own "
  "result: was the crash mechanism's &quot;post-2008&quot; significance "
  "a standing regime, or one crisis pooled with eight quiet years? "
  "Splitting the window apart found the market's own trailing-bear "
  "indicator had not fired once since September 2009 &mdash; the "
  "significance Part V.17 reported had nowhere else to come from but "
  "the crisis itself, and, isolated there, even the specific "
  "interaction term stopped being what carried it. Part V.20 then asked "
  "the question Part V.19 itself invited but didn't ask: was that "
  "&quot;never fired again&quot; finding a fact about the market, or "
  "about the one-year window chosen to measure it? Sweeping nearby "
  "windows found both answers at once &mdash; the crash-mechanism "
  "pattern held up under most choices tested, but the specific claim "
  "that no bear market recurred did not, vanishing the moment a shorter, "
  "equally ordinary lookback was used instead. Part V.22 then closed the "
  "loop on this project's own last untested claim, aiming the same "
  "instrument at itself one more time: the tentative NSE signal Part "
  "V.18 had flagged, not as a finding, but as a &quot;promising, not "
  "confirmed&quot; result with a named caveat nobody had gone back to "
  "test. Splitting NSE's universe at the exact date it stopped growing "
  "found the caveat as named wasn't the problem &mdash; but the same "
  "pooled-window pattern this project had just learned to distrust in "
  "the crash mechanism was. Part V.23 then asked a question no "
  "correction could answer: not what was wrong with a finding already in "
  "hand, but whether either of this project's two markets was itself "
  "representative of anything beyond its own dataset. Finding a third, "
  "independent one took longer than running the actual test once it was "
  "found.")
p("The practical output (Part VI) turns that into three concrete artifacts: an "
  "investment framework that explicitly forbids trusting a blend without "
  "decomposing it; a risk-management playbook built directly from a "
  "real simulated result, not a generic checklist; and a business idea whose "
  "differentiation <i>is</i> the decomposition discipline the research itself "
  "needed. Milestones 3 through 23 then ran the India findings through "
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
  "concealing a genuine break of its own decades before 2008 &mdash; a "
  "break that Part V.16 then traced to its actual cause and found was "
  "never a market phenomenon at all, retracting reversal's status as a "
  "second surviving finding entirely &mdash; while Part V.17, applying "
  "the same instinct to the finding that survived, gave momentum's own "
  "2008-09 break a mechanism it had lacked since Part V.13 first "
  "described its shape. Part V.18 carried that mechanism to NSE and "
  "found it didn't travel &mdash; but the trip wasn't wasted: testing "
  "it exposed that NSE momentum itself had only ever been checked with "
  "this project's cruder, pre-Part-V.8 method, and the better one found "
  "a signal since 2008 that the earlier pass had missed entirely. Part "
  "V.19 then asked one question of Part V.17's own mechanism that no "
  "earlier milestone had: not whether it was real, but whether it was "
  "still happening, and found the &quot;post-2008&quot; window it was "
  "tested against had, itself, only one crisis in it to be significant "
  "about. Part V.20 then did to Part V.19 what Part V.19 had just done "
  "to Part V.17: checked whether its own headline finding depended on "
  "one arbitrary-looking choice. It found two different answers hiding "
  "in the same code &mdash; the crash-mechanism pattern survived most "
  "reasonable variations of that choice, but the specific claim that no "
  "bear market had recurred did not. Part V.21 then finished what Part "
  "V.20 had only made possible: it actually ran the persistence test "
  "under the windows where a second bear market exists, instead of "
  "leaving that as a flagged possibility, and found the mechanism stayed "
  "quiet &mdash; not because there was nothing to test it against this "
  "time, but because it was tested and simply didn't show up, with the "
  "one coefficient that did clear significance pointing the wrong way "
  "for crash risk entirely. Part V.22 then took the same instrument this "
  "project had just used on its own crash-mechanism finding and pointed "
  "it at the one other open thread still standing: the tentative NSE "
  "signal. It found the same failure mode again, in a completely "
  "different corner of the project &mdash; a real, named caveat that "
  "turned out not to be the actual problem, sitting next to a pooled-"
  "window artifact nobody had thought to check until the crash mechanism "
  "taught this project what to look for. Part V.23 then stepped back from "
  "correcting existing findings entirely and asked the question this "
  "project's own two-market design had left unasked since Part V.3: is "
  "either market representative of anything, or just of itself? Answering "
  "it took more effort than any single statistical test in this guide "
  "&mdash; most of the obvious candidate sources turned out to be "
  "unreachable, blocked, or not actually data at all &mdash; but the one "
  "source that worked gave momentum's long leg its cleanest replication "
  "yet.")
p("The fix that survived all of that scrutiny is more modest, and "
  "narrower, than any earlier draft of this conclusion claimed: there "
  "is no demonstrated, beta-independent stock-selection skill in the "
  "52-week-high signal, in either direction, as currently built, at any "
  "point in the sample &mdash; and, as of Part V.16, the same is now "
  "true of short-term reversal, at every level this project checked. "
  "Momentum's long leg is the sole survivor: a real, largely "
  "beta-independent edge that held, essentially undiminished, all the "
  "way to the 2008-09 financial crisis, confirmed by a test built "
  "specifically around that crisis date, though a fully unconstrained "
  "search for the single best break in the series does not confirm "
  "that date as uniquely special, landing instead 27 months later "
  "without clearing significance. Reversal looked, for six milestones, "
  "like it might be a second such survivor &mdash; first retracted "
  "outright (Part V.9), then partially rehabilitated as a genuine, "
  "decayed effect (Part V.13), then given its own precise decline date "
  "(Part V.14), then its own formally-tested structural break (Part "
  "V.15) &mdash; before Part V.16 finally asked the one question none "
  "of those milestones had: was any of it real to begin with? It "
  "wasn't. A decile portfolio of two to four stocks, pulled from a "
  "universe of companies guaranteed by construction to have survived "
  "and thrived, is not evidence of a behavioral anomaly; it is a "
  "handful of individual stock histories dressed up as a diversified "
  "backtest. Momentum's own history in that same unreliable data was "
  "checked as a control and came through clean. Every one of those "
  "findings was reached not by anyone's original hypothesis about which "
  "signal should work, but by finally applying the project's own "
  "hard-won standard of rigor evenly: to a winner as well as a loser, to "
  "a signal's own more recent, more comfortable-looking result as well "
  "as its oldest one, to a signal already written off instead of "
  "assuming a full-sample null closed the question for good, to the "
  "project's own explanatory story once a result was found instead of "
  "assuming the first plausible mechanism was the right one, and "
  "finally to the data itself, checking whether a headline number "
  "rested on a real market or on three stocks and a backfilled ticker "
  "list. That is the project working as intended, "
  "including on itself: not every finding needs to be confirmed to be "
  "useful, a compelling pattern &mdash; positive or negative &mdash; is a "
  "hypothesis until it survives testing at every level of rigor "
  "available, and the single most important thread running through this "
  "entire guide is a project that kept correcting or deepening its own "
  "most recent, best-supported-looking result, twenty times in a row "
  "&mdash; six outright retractions or downward revisions, one nuanced "
  "check (Part V.10) that briefly looked like a stopping point before "
  "Part V.11 showed it wasn't, an eighth check (Part V.12) built "
  "specifically to try to explain the seventh correction away that "
  "couldn't, and a ninth (Part V.13) that went looking for the same "
  "pattern somewhere the project had stopped looking, and found it "
  "&mdash; then, rather than resting on that broader finding, ran a "
  "tenth check (Part V.14) against its own explanation for the ninth, "
  "discovered that even &quot;two signals, one shared story&quot; was "
  "itself an oversimplification, ran an eleventh check (Part V.15) "
  "against its own <i>informal</i> version of that discovery and found "
  "the formal, multiple-testing-corrected test was more conservative "
  "than the eyeballed comparison that had motivated it, on both "
  "signals, in different directions, ran a twelfth check (Part V.16) "
  "that did what none of the previous eleven had: it asked whether the "
  "underlying data could even support the question being asked of it, "
  "and found that for reversal, across every one of those eleven "
  "checks, it could not, ran a thirteenth check (Part V.17) that, for "
  "the first time, wasn't a correction at all: it took the one result "
  "still standing and asked not whether it was real, but why, "
  "reapplying a mechanism this project had itself rejected elsewhere "
  "and finding it fit, conditional on era, exactly where the break had "
  "been &mdash; ran a fourteenth check (Part V.18) that "
  "took that same mechanism somewhere it had never been asked before, "
  "found it didn't belong there, and, checking why, found that even the "
  "project's own earlier verdict on that market had been reached with a "
  "tool it had since outgrown, ran a fifteenth check (Part "
  "V.19) that turned the same &quot;is it still true&quot; question "
  "back on the mechanism itself: split apart, the &quot;post-2008&quot; "
  "window the mechanism was confirmed against turned out to contain "
  "exactly one crisis and no second bear market to test persistence "
  "against, and the specific interaction term stopped being what "
  "carried the result once that one crisis was looked at on its own, "
  "ran a sixteenth check (Part V.20) that questioned the "
  "fifteenth's own instrument: was &quot;no second bear market&quot; a "
  "fact about the market, or about the one specific window chosen to "
  "look for one, and found it was partly the latter &mdash; the "
  "pattern survived nearby choices, the absence-claim did not, ran a "
  "seventeenth check (Part V.21) that did not just note "
  "the sixteenth check's opening but walked through it: reran the "
  "mechanism against the two windows that now had a real second bear "
  "market to test against, and found silence &mdash; not the absence of "
  "a test this time, but a test that came back negative, with the one "
  "significant coefficient it produced running in the wrong direction "
  "for crash risk altogether, and finally ran an eighteenth check (Part "
  "V.22) that took the exact instrument the seventeenth had just used "
  "&mdash; splitting a pooled window to see if a finding survived on "
  "either side of the split &mdash; and pointed it at a completely "
  "different result: this project's own tentative NSE signal, the one "
  "open thread Part V.18 had left standing with a named but never-tested "
  "caveat. The caveat, tested, wasn't the problem; the exact same pooling "
  "artifact the seventeenth check had just diagnosed elsewhere was, "
  "ran a nineteenth check (Part V.23) that wasn't aimed at any "
  "existing finding at all: it asked whether this project's entire "
  "two-market design was itself sound, went looking for an independent "
  "third market to find out, and found that the search itself &mdash; "
  "ruling out one blocked or empty source after another &mdash; took "
  "longer than the test that followed once a real one turned up, and "
  "finally ran a twentieth check (Part V.24) that finished what the "
  "nineteenth had left half-open: a third market tested on one signal "
  "only. The second and third signals, run on it, gave two different "
  "answers &mdash; one a clean confirmation, one a result that looked "
  "new until the nineteenth check's own lesson (check what a finding "
  "correlates with before counting it twice) was turned on it. "
  "Not finding an escape hatch, finding the "
  "same shape twice in independent places, discovering the two "
  "places didn't actually share a shape after all, discovering that "
  "even that discovery needed a proper test before it could be "
  "trusted, discovering that the entire multi-milestone "
  "argument about reversal had been conducted on three stocks, "
  "discovering a real reason behind the one number that survived all of "
  "it, and finally discovering that a market believed fully closed still "
  "had something left to find, are all findings: the project never "
  "found a result, an explanation, or even a way of testing an "
  "explanation, durable enough to stop re-checking. What survives is "
  "smaller and more precisely qualified "
  "than any single milestone first suggested: momentum's long leg, "
  "real and strong pre-2008-09, confirmed weakened specifically at "
  "that literature-motivated date though not provably the site of the "
  "single largest break in the series, and now understood to have "
  "broken because the classic momentum-crash mechanism &mdash; dormant "
  "for over three decades &mdash; activated during the 2008-09 crisis, "
  "is this project's "
  "one remaining, seventeen-times-checked finding, confirmed to be a "
  "US-specific mechanism after failing to replicate on NSE, confirmed on "
  "the fifteenth check for that one crisis specifically rather than for "
  "a standing post-2008 regime, confirmed on the sixteenth to be "
  "reasonably robust to nearby modeling choices while the specific claim "
  "that no second bear market has occurred since was not, and, on the "
  "seventeenth, put to the one test that claim's own qualification made "
  "possible: run against the two windows where a second bear market "
  "genuinely exists, and it did not reactivate in either. Short-term "
  "reversal is "
  "not a second one: every version of its apparent edge &mdash; the "
  "original NSE Sharpe ratio, the full-sample beta-adjusted alpha, "
  "the pre-1994 era split, the continuous decay trend, the formal "
  "structural break &mdash; traces back to the same unreliable "
  "1972-1977 window and disappears the moment that window is excluded. "
  "One signal decays on its own schedule and by its own mechanism, "
  "sized more cautiously than the milestone that first found it would "
  "have suggested; the other was never there to begin with, once "
  "checked against data good enough to ask the question. Two threads "
  "that looked open as recently as Part V.20 are open no longer. "
  "Whether the momentum-crash mechanism reactivated in 2011 or 2015-16, "
  "episodes this project's own default bear-market definition was too "
  "conservative to register as bear markets at all, but that two other, "
  "equally standard definitions do register: Part V.21 ran the "
  "persistence test against both of those definitions and the mechanism "
  "did not reactivate in either, with the one coefficient that did clear "
  "significance running the wrong direction for crash risk. And whether "
  "the tentative, &quot;promising not confirmed&quot; post-2008 NSE "
  "momentum signal &mdash; found only because this project finally ran "
  "its own best method against a market it thought it had already closed "
  "the book on &mdash; was real: Part V.22 tested the one named caveat "
  "attached to it and found a different, more fundamental problem "
  "instead, the identical pooled-window artifact Part V.21 had just "
  "taught this project to look for. And one question this project had "
  "never actually asked, because it had never had the means to: whether "
  "momentum's edge was a property of stock markets generally or of the "
  "two specific, re-exported datasets this project happened to have "
  "access to. Part V.23 went looking for a third, independent source "
  "after ruling out an entire continent's worth of blocked or empty "
  "candidates, found one in Australia's own exchange, and momentum came "
  "back significant at both daily and monthly frequency &mdash; the "
  "cleanest replication in the whole guide, on the one market tested "
  "with this project's best method from the very first pass rather than "
  "arriving at it after several corrections. Part V.24 then finished "
  "what Part V.23 had left half-done: NSE and the US mirror were both "
  "tested on all three signals from the start, ASX had only been tested "
  "on one. Reversal, run on ASX, changed nothing &mdash; the same null "
  "as everywhere else. 52-week-high did: significant hedged alpha, "
  "reopening a question Parts V.7-8 had called resolved &mdash; until "
  "checking its correlation with momentum's own ASX result (0.76-0.82) "
  "showed the two signals were picking substantially the same stocks, "
  "the same lesson Part V.23 itself had just taught this project applied "
  "to a market it had barely finished exploring. Four settled conclusions "
  "now, not three: a real, if narrower, US-specific finding for "
  "momentum, now independently replicated on a third market; two "
  "retractions, reversal's and the NSE signal's, reached for different "
  "reasons but by the same refusal to let a promising number stand "
  "without being taken apart; and a genuinely new confirmation, arrived "
  "at not by re-examining an old result but by questioning whether this "
  "project's entire evidentiary base was wide enough to trust in the "
  "first place. What remains open is not a specific "
  "finding but three honest limits of the data itself: whether the crash "
  "mechanism would reactivate in a genuinely severe future crisis, as "
  "opposed to the milder episodes this sample happens to contain, is a "
  "question no amount of further re-testing of this history can answer "
  "&mdash; the most recent decade, for momentum, to size nothing against "
  "&mdash; whether ASX momentum's own edge is stable across "
  "sub-periods the way the US finding eventually was shown to be, a "
  "check this project's newest market hasn't had enough history yet to "
  "run, and whether ASX 52-week-high carries any skill beyond what its "
  "correlation with momentum already explains, a check that needs "
  "momentum held constant as an explicit control rather than compared "
  "after the fact. All three are what a research process built to "
  "distrust its own best-looking result eventually converges on.")

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

