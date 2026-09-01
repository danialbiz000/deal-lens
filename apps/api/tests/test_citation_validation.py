"""Unit tests for citation_validation.py -- pure Python, no LLM, no DB.

Per docs/phase4-ai-layer-design.md section 9/10's acceptance checklist:
correctly extracts valid citations, correctly flags a constructed invalid
citation, and demonstrates both a flagged and unflagged case for the
uncited-number heuristic. Also covers the mismatched_citations category
added after adversarial testing found that "path exists" and "number
appears somewhere in the bundle" checked independently let a fabricated
number paired with a real-but-unrelated citation pass completely clean.
"""

from app.ai.citation_validation import validate_citations

BUNDLE = {
    "company": {"ticker": "ACME", "sector": "Technology"},
    "screening": {"score": 62.4, "factors": {"growth": {"normalized_score": 71.2}}},
    "valuation": {"entry_ev": 1000000.0, "ev_ebitda": {"median": 12.4}},
    "lbo": {"bear": {"irr": 0.062, "moic": 1.1}},
}


def test_valid_citation_resolves_and_is_not_flagged():
    text = "The screening score is 62.4 [[source: screening.score]]."
    report = validate_citations(text, BUNDLE)
    assert report.total_citations == 1
    assert report.invalid_citations == []


def test_nested_valid_citation_resolves():
    text = "Growth scored 71.2 [[source: screening.factors.growth.normalized_score]]."
    report = validate_citations(text, BUNDLE)
    assert report.invalid_citations == []
    assert report.status == "ok"


def test_invalid_citation_flagged_as_hard_signal():
    text = "Revenue grew 20% [[source: financials.revenue_growth]]."  # path doesn't exist in bundle
    report = validate_citations(text, BUNDLE)
    assert report.total_citations == 1
    assert report.invalid_citations == ["financials.revenue_growth"]
    assert report.status == "warnings"


def test_uncited_number_is_flagged():
    text = "Margins could expand by roughly 8% next year."  # 8% appears nowhere in the bundle, no citation nearby
    report = validate_citations(text, BUNDLE)
    assert any("8" in n for n in report.uncited_numbers)
    assert report.status == "warnings"


def test_number_near_citation_tag_is_not_flagged_as_uncited():
    text = "Bear-case IRR is 6.2% [[source: lbo.bear.irr]], a genuine downside case."
    report = validate_citations(text, BUNDLE)
    assert report.uncited_numbers == []
    assert report.invalid_citations == []
    assert report.status == "ok"


def test_number_matching_a_bundle_value_elsewhere_is_not_flagged():
    # No citation tag adjacent, but 12.4 does appear in the bundle's own values.
    text = "Peers trade around 12.4 times EBITDA in this sector."
    report = validate_citations(text, BUNDLE)
    assert report.uncited_numbers == []


def test_no_citations_no_numbers_is_clean():
    report = validate_citations("This company operates in a fragmented but growing market.", BUNDLE)
    assert report.total_citations == 0
    assert report.invalid_citations == []
    assert report.uncited_numbers == []
    assert report.status == "ok"


def test_multiple_citations_counted_correctly():
    text = (
        "Score is 62.4 [[source: screening.score]] and entry EV is "
        "1000000.0 [[source: valuation.entry_ev]]."
    )
    report = validate_citations(text, BUNDLE)
    assert report.total_citations == 2
    assert report.invalid_citations == []


def test_bool_values_in_bundle_are_not_treated_as_numeric_matches():
    # `False` formats as "0" via Python's int-subclass behavior -- without
    # explicitly excluding bool, an unrelated "0" in prose would spuriously
    # match this flag and escape the uncited-number heuristic entirely.
    bundle_with_bool = {"flag": {"exit_multiple_dependent": False}}
    report = validate_citations("There were 0 material red flags this quarter.", bundle_with_bool)
    assert any("0" in n for n in report.uncited_numbers)


# --- mismatched_citations: number claimed by a specific citation must match
# THAT citation's own resolved value, not just appear somewhere in the bundle ---


def test_fabricated_number_on_real_unrelated_path_is_caught():
    """THE adversarial case found in testing: a real, resolvable citation
    path paired with a number that has nothing to do with that path's
    actual value must no longer pass as clean.
    """
    text = "MOIC is 999.0x [[source: screening.score]]."
    report = validate_citations(text, BUNDLE)
    assert report.invalid_citations == []  # the path IS real
    assert report.uncited_numbers == []  # not "uncited" either -- it has a tag right next to it
    assert len(report.mismatched_citations) == 1
    assert "screening.score" in report.mismatched_citations[0]
    assert report.status == "warnings"


def test_correctly_cited_number_is_not_mismatched():
    text = "The screening score is 62.4 [[source: screening.score]]."
    report = validate_citations(text, BUNDLE)
    assert report.mismatched_citations == []
    assert report.status == "ok"


def test_percent_formatting_variance_within_tolerance_not_flagged():
    # 62.4 stated informally as "62%" -- close enough (within tolerance) to
    # the raw value 62.4 that this must not be treated as fabricated.
    text = "The screening score is roughly 62% [[source: screening.score]]."
    report = validate_citations(text, BUNDLE)
    assert report.mismatched_citations == []


def test_fraction_vs_percent_formatting_variance_not_flagged():
    # lbo.bear.irr is stored as a 0-1 fraction (0.062); stating it as "6.2%"
    # is the normal, correctly-cited way to express it, not a mismatch.
    text = "Bear-case IRR is 6.2% [[source: lbo.bear.irr]]."
    report = validate_citations(text, BUNDLE)
    assert report.mismatched_citations == []


def test_currency_scale_suffix_formatting_variance_not_flagged():
    bundle_with_large_value = {"valuation": {"entry_ev": 1_200_000_000.0}}
    text = "Entry EV is approximately $1.2bn [[source: valuation.entry_ev]]."
    report = validate_citations(text, bundle_with_large_value)
    assert report.mismatched_citations == []
    assert report.status == "ok"


def test_genuinely_wrong_number_with_currency_suffix_is_flagged():
    bundle_with_large_value = {"valuation": {"entry_ev": 1_200_000_000.0}}
    text = "Entry EV is approximately $5.0bn [[source: valuation.entry_ev]]."
    report = validate_citations(text, bundle_with_large_value)
    assert len(report.mismatched_citations) == 1


def test_citation_to_non_numeric_value_is_never_treated_as_a_mismatch():
    # A number happening to sit near a citation to a *string* field (e.g.
    # sector) has nothing numeric to compare against -- must not crash or
    # be flagged as a fabricated numeric claim.
    text = "This is a Technology company [[source: company.sector]], now in its 5th year."
    report = validate_citations(text, BUNDLE)
    assert report.mismatched_citations == []
    assert report.invalid_citations == []


def test_mismatch_does_not_double_count_same_citation():
    text = "MOIC is 999.0x, repeated: 999.0x [[source: screening.score]]."
    report = validate_citations(text, BUNDLE)
    # Only the token actually within the adjacency window of the tag is
    # "claimed" by it and checked -- at most one entry per citation tag.
    assert len(report.mismatched_citations) <= 1


# --- additional adversarial cases (independently verified in review) ---


def test_reversed_order_number_after_tag_still_caught():
    # The design doc's canonical phrasing puts the number before the tag,
    # but the adjacency check must not depend on word order -- a fabricated
    # number stated right after the tag, close enough to still plausibly be
    # "about" that citation, must be caught just the same. (The adjacency
    # window is deliberately tight -- see CITATION_ADJACENCY_WINDOW -- so
    # this only holds for phrasing that keeps the number genuinely close,
    # not an unrelated number several clauses later.)
    text = "[[source: screening.score]] states 999.0."
    report = validate_citations(text, BUNDLE)
    assert len(report.mismatched_citations) == 1
    assert "screening.score" in report.mismatched_citations[0]


def test_two_correct_adjacent_citations_no_cross_contamination():
    text = (
        "Score is 62.4 [[source: screening.score]] and growth is 71.2 "
        "[[source: screening.factors.growth.normalized_score]]."
    )
    report = validate_citations(text, BUNDLE)
    assert report.mismatched_citations == []
    assert report.status == "ok"


def test_two_adjacent_citations_only_second_wrong_is_correctly_attributed():
    text = (
        "Score is 62.4 [[source: screening.score]] and growth is 999.0 "
        "[[source: screening.factors.growth.normalized_score]]."
    )
    report = validate_citations(text, BUNDLE)
    assert len(report.mismatched_citations) == 1
    assert "screening.factors.growth.normalized_score" in report.mismatched_citations[0]
    assert "screening.score" not in report.mismatched_citations[0]


def test_sign_flip_is_caught_not_treated_as_a_rounding_variance():
    # lbo.bear.irr is a positive 0.062 -- a claimed *negative* value is a
    # different claim entirely, not formatting noise, and must be flagged.
    text = "Bear-case IRR is -6.2% [[source: lbo.bear.irr]]."
    report = validate_citations(text, BUNDLE)
    assert len(report.mismatched_citations) == 1
    assert "lbo.bear.irr" in report.mismatched_citations[0]
