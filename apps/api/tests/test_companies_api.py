def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_company(client):
    response = client.post(
        "/companies",
        json={"ticker": "aapl", "name": "Apple Inc.", "cik": "0000320193", "sector": "Technology"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["ticker"] == "AAPL"  # uppercased
    assert body["name"] == "Apple Inc."
    assert body["reporting_currency"] == "USD"
    assert "id" in body and "created_at" in body


def test_create_company_duplicate_ticker_conflicts(client):
    client.post("/companies", json={"ticker": "MSFT", "name": "Microsoft"})
    response = client.post("/companies", json={"ticker": "MSFT", "name": "Microsoft Corp"})
    assert response.status_code == 409


def test_create_company_duplicate_cik_conflicts(client):
    client.post("/companies", json={"ticker": "GOOG", "name": "Alphabet", "cik": "0001652044"})
    response = client.post("/companies", json={"ticker": "GOOGL", "name": "Alphabet Inc", "cik": "0001652044"})
    assert response.status_code == 409


def test_list_companies(client):
    client.post("/companies", json={"ticker": "NVDA", "name": "NVIDIA"})
    client.post("/companies", json={"ticker": "AMD", "name": "AMD"})
    response = client.get("/companies")
    assert response.status_code == 200
    tickers = {c["ticker"] for c in response.json()}
    assert {"NVDA", "AMD"}.issubset(tickers)


def test_get_company_not_found(client):
    response = client.get("/companies/does-not-exist")
    assert response.status_code == 404


def test_get_company_detail_with_no_financials_yet(client):
    created = client.post("/companies", json={"ticker": "TSLA", "name": "Tesla"}).json()
    response = client.get(f"/companies/{created['id']}")
    assert response.status_code == 200
    assert response.json()["latest_financial_period"] is None
