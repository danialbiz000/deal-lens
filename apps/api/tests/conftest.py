import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("FMP_API_KEY", "")
# Design doc section 12.6: the in-memory limiter's state persists for the
# test process's lifetime, and the existing suites call these endpoints
# many times across many tests -- without this default, the full suite
# would start failing with 429s partway through. Only the dedicated
# tests in test_rate_limit.py explicitly flip this on.
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.ai.client import get_claude_client  # noqa: E402
from app.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

# A dedicated in-memory engine for tests, isolated from whatever
# DATABASE_URL a developer's local .env points at. StaticPool keeps the
# same in-memory DB alive across connections within a test.
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def _fresh_schema():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


class FakeClaudeClient:
    """Zero-network stand-in for ClaudeClient (design doc section 9) --
    returns a queue of canned structured responses in call order, and
    records every call for assertions (e.g. that the IC roles really run
    sequentially and each sees the prior transcript).
    """

    def __init__(self, responses, model_name: str = "fake-claude-test"):
        self._responses = list(responses)
        self.model_name = model_name
        self.calls = []

    def complete_structured(self, system: str, user: str, json_schema: dict) -> dict:
        self.calls.append({"system": system, "user": user, "json_schema": json_schema})
        if not self._responses:
            raise AssertionError("FakeClaudeClient ran out of canned responses")
        return self._responses.pop(0)

    def complete_structured_from_document(
        self, system: str, user: str, json_schema: dict, document_base64: str, media_type: str = "application/pdf"
    ) -> dict:
        self.calls.append(
            {
                "system": system,
                "user": user,
                "json_schema": json_schema,
                "document_base64": document_base64,
                "media_type": media_type,
            }
        )
        if not self._responses:
            raise AssertionError("FakeClaudeClient ran out of canned responses")
        return self._responses.pop(0)


@pytest.fixture
def fake_claude_client():
    """Returns a factory `set_responses(list_of_dicts) -> FakeClaudeClient`
    that also wires the fake up as the `get_claude_client` dependency
    override for the duration of the test.
    """
    created = []

    def _factory(responses):
        fake = FakeClaudeClient(responses)
        created.append(fake)
        app.dependency_overrides[get_claude_client] = lambda: fake
        return fake

    yield _factory
    app.dependency_overrides.pop(get_claude_client, None)


@pytest.fixture
def rate_limiting_enabled():
    """Enables the real slowapi limiter for one test, with a clean
    in-memory counter state, then restores the disabled default (design
    doc section 12.6). Only test_rate_limit.py's dedicated tests use this.
    """
    from app.rate_limit import limiter

    limiter.reset()
    limiter.enabled = True
    try:
        yield limiter
    finally:
        limiter.enabled = False
        limiter.reset()


@pytest.fixture
def override_setting():
    """Returns `set(name, value)` to temporarily override a `settings`
    attribute for one test -- works because rate-limit values are read
    live via zero-arg lambdas in the route decorators, not resolved once
    at import time (see app/rate_limit.py's module docstring).
    """
    from app.config import settings

    originals: dict = {}

    def _set(name: str, value):
        if name not in originals:
            originals[name] = getattr(settings, name)
        setattr(settings, name, value)

    yield _set

    for name, value in originals.items():
        setattr(settings, name, value)
