import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("FMP_API_KEY", "")

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
