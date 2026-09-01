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

    request_timeout_seconds: float = 30.0


settings = Settings()
