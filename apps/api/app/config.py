"""Environment/settings via pydantic-settings.

Reads from a `.env` file at the apps/api working directory (see
.env.example at the repo root, which documents every variable used here).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./deal_lens.db"

    # SEC EDGAR requires a descriptive User-Agent identifying the app/contact
    # per SEC's fair-access policy (design doc section 5). Requests without
    # one are throttled/blocked.
    edgar_user_agent: str = "DealLens Portfolio Project (replace-with-your-email@example.com)"

    # Financial Modeling Prep free-tier API key (design doc section 5:
    # chosen over Alpha Vantage for this slice's supplementary source).
    fmp_api_key: str = ""

    # Phase 4 (docs/phase4-ai-layer-design.md section 2): never hardcoded.
    # Only apps/api/app/ai/ reads these -- packages/finance_engine has zero
    # knowledge this layer exists. Blank by default; the default pytest run
    # never needs a real key (ClaudeClient is injectable and faked in tests).
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"

    # Rate limiting (docs/phase4-ai-layer-design.md section 12) -- cost
    # control on the two paid-Claude-API endpoints, good-citizenship
    # throttling on ingest. Values use the `limits` package's own string
    # syntax (e.g. "5/hour;20/day"), enforced in-memory via slowapi --
    # correct for this single-instance FastAPI + SQLite app, no distributed
    # store anywhere in scope. RATE_LIMIT_ENABLED=false is the test default
    # (set in tests/conftest.py) so the existing suite's many repeated
    # calls to these endpoints don't start failing with 429s.
    rate_limit_enabled: bool = True
    rate_limit_ai_per_ip: str = "10/minute"
    rate_limit_ai_per_company: str = "5/hour;20/day"
    rate_limit_ingest_per_ip: str = "20/minute"
    rate_limit_ingest_per_company: str = "10/hour"
    # Document extraction (POST /companies/{id}/documents/extract) sends a
    # whole PDF to Claude -- far more tokens per call than memo/ic-simulation
    # -- so it gets its own, stricter per-company budget while still sharing
    # the combined ai_per_ip abuse backstop with those two endpoints.
    rate_limit_extraction_per_company: str = "5/hour;15/day"

    request_timeout_seconds: float = 30.0


settings = Settings()
