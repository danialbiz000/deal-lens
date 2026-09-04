"""POST /companies/{id}/documents/extract -- AI-assisted extraction of
candidate financial periods from an uploaded PDF (design doc section 8's
deferred "document parser", now built). Extraction never writes to the
database; every candidate here is shaped so it can be posted straight to
the already-tested POST /companies/{id}/financials endpoint once a human
reviewer confirms it.
"""

import pytest

from app.ai.prompts.financial_extraction import JSON_SCHEMA


def _count_union_typed_params(node):
    """Recursively count schema properties whose "type" is a list (e.g.
    ["number", "null"]) -- Anthropic's real structured-output API rejects a
    schema with more than 16 of these ("too many parameters with union
    types ... this causes exponential compilation cost"), discovered the
    hard way against the live API when the first draft of this schema paired
    11 nullable numeric fields with 11 nullable citation-string fields (22
    total). The fake test client never enforces this, so only a schema-tree
    walk (or a live call) can catch it reappearing.
    """
    count = 0
    if isinstance(node, dict):
        if isinstance(node.get("type"), list):
            count += 1
        for v in node.values():
            count += _count_union_typed_params(v)
    elif isinstance(node, list):
        for item in node:
            count += _count_union_typed_params(item)
    return count


def test_extraction_schema_stays_under_anthropic_union_type_limit():
    count = _count_union_typed_params(JSON_SCHEMA)
    assert count <= 16, (
        f"JSON_SCHEMA has {count} union/nullable-typed parameters, over Anthropic's "
        "structured-output limit of 16 -- the real API returns a 400 for this"
    )


def _create_company(client, ticker="DOCCO"):
    return client.post(
        "/companies", json={"ticker": ticker, "name": f"{ticker} Inc.", "sector": "Industrials"},
    ).json()


def _minimal_pdf_bytes() -> bytes:
    # A syntactically minimal (if not renderable) PDF -- the fake client
    # never actually parses this, so only its bytes/content-type matter here.
    return b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>"


def _canned_extraction_response(with_period=True):
    if not with_period:
        return {"periods": [], "notes": "no periods found"}
    return {
        "periods": [
            {
                "fiscal_year": 2024,
                "period_end_date": "2024-12-31",
                "period_type": "FY",
                "currency": "USD",
                "revenue": 42_000_000.0,
                "gross_profit": None,
                "ebitda": 8_400_000.0,
                "ebit": None,
                "net_income": None,
                "operating_cash_flow": None,
                "capex": 1_200_000.0,
                "total_debt": None,
                "cash_and_equivalents": None,
                "interest_expense": None,
                "shares_outstanding": None,
                # The wire format Claude actually returns (see the NOTE in
                # financial_extraction.JSON_SCHEMA) -- a variable-length list,
                # not a fixed nullable-per-field object. extraction.py
                # converts this to a {field: quote} dict before it reaches
                # the router/schema/UI.
                "citations": [
                    {"field": "revenue", "quote": "p.3: 'Total net sales of $42.0 million'"},
                    {"field": "ebitda", "quote": "p.4: 'Adjusted EBITDA of $8.4 million'"},
                    {"field": "capex", "quote": "p.5: 'capital expenditures of $1.2 million'"},
                ],
            }
        ],
        "notes": "Figures were reported in millions and converted to full units.",
    }


def test_extraction_returns_candidate_periods_with_citations(client, db_session, fake_claude_client):
    company = _create_company(client)
    fake_claude_client([_canned_extraction_response()])

    response = client.post(
        f"/companies/{company['id']}/documents/extract",
        files={"file": ("statement.pdf", _minimal_pdf_bytes(), "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["periods"]) == 1
    period = body["periods"][0]
    assert period["revenue"] == pytest.approx(42_000_000.0)
    assert period["citations"]["revenue"] == "p.3: 'Total net sales of $42.0 million'"
    assert period["citations"]["gross_profit"] is None
    assert "millions" in body["notes"]


def test_extraction_candidate_can_be_posted_straight_to_manual_financials(client, db_session, fake_claude_client):
    # Proves the shape compatibility the whole design leans on: the review
    # UI should be able to take a candidate, let the analyst edit it, and
    # POST it verbatim (plus a source_ref) to the existing manual endpoint.
    company = _create_company(client)
    fake_claude_client([_canned_extraction_response()])

    extracted = client.post(
        f"/companies/{company['id']}/documents/extract",
        files={"file": ("statement.pdf", _minimal_pdf_bytes(), "application/pdf")},
    ).json()
    candidate = extracted["periods"][0]
    candidate.pop("citations")
    candidate["source_ref"] = "extracted from statement.pdf"

    response = client.post(f"/companies/{company['id']}/financials", json=candidate)
    assert response.status_code == 201
    assert response.json()["source"] == "MANUAL"
    assert response.json()["revenue"] == pytest.approx(42_000_000.0)


def test_extraction_company_not_found_returns_404(client, db_session, fake_claude_client):
    response = client.post(
        "/companies/does-not-exist/documents/extract",
        files={"file": ("statement.pdf", _minimal_pdf_bytes(), "application/pdf")},
    )
    assert response.status_code == 404


def test_extraction_rejects_non_pdf_content_type(client, db_session):
    company = _create_company(client)
    response = client.post(
        f"/companies/{company['id']}/documents/extract",
        files={"file": ("statement.txt", b"hello world", "text/plain")},
    )
    assert response.status_code == 422


def test_extraction_rejects_empty_file(client, db_session):
    company = _create_company(client)
    response = client.post(
        f"/companies/{company['id']}/documents/extract",
        files={"file": ("statement.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 422


def test_extraction_no_periods_found_returns_503(client, db_session, fake_claude_client):
    # A ClaudeApiError from the orchestration layer (design doc section 8:
    # a contract violation is treated the same as an API failure) surfaces
    # as 503, never a 500 or a silently empty 200.
    company = _create_company(client)
    fake_claude_client([_canned_extraction_response(with_period=False)])

    response = client.post(
        f"/companies/{company['id']}/documents/extract",
        files={"file": ("statement.pdf", _minimal_pdf_bytes(), "application/pdf")},
    )
    assert response.status_code == 503


def test_extraction_document_reaches_fake_client_as_base64(client, db_session, fake_claude_client):
    company = _create_company(client)
    fake = fake_claude_client([_canned_extraction_response()])

    client.post(
        f"/companies/{company['id']}/documents/extract",
        files={"file": ("statement.pdf", _minimal_pdf_bytes(), "application/pdf")},
    )

    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["media_type"] == "application/pdf"
    import base64

    assert base64.b64decode(call["document_base64"]) == _minimal_pdf_bytes()
