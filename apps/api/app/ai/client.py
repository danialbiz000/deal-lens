"""Single choke point for the Anthropic SDK (design doc section 2).

Nothing else in the codebase touches `anthropic` directly. `ClaudeClient`
is a `Protocol`, so the default test suite substitutes a `FakeClaudeClient`
with zero mocking gymnastics, zero network calls, and zero API key
required -- matching the FMP-key-optional pattern already used for Phase
2's market-data tests.

Uses Claude's forced-JSON-schema structured output for every call in this
phase (memo sections, each of the 5 IC roles) -- never free-text parsing of
prose into structured fields. This is a reliability choice: brittle
regex-parsing of LLM prose is exactly the kind of hidden nondeterminism
this project has avoided everywhere else.
"""

import json
from typing import Any, Dict, Protocol, runtime_checkable

from app.config import settings


@runtime_checkable
class ClaudeClient(Protocol):
    """The only interface the rest of the AI layer is allowed to depend on."""

    model_name: str

    def complete_structured(self, system: str, user: str, json_schema: Dict[str, Any]) -> Dict[str, Any]: ...


class ClaudeApiError(RuntimeError):
    """Raised when the Claude API errors or times out.

    Routers catch this and return 503 with a clear message -- never a raw
    stack trace (design doc section 8): the two memo/ic-simulation POST
    endpoints are the only ones in the whole codebase that make outbound
    network calls to a third-party API.
    """


class AnthropicClaudeClient:
    """Real implementation, backed by the Anthropic SDK.

    Reads ANTHROPIC_API_KEY from the environment (never hardcoded) and the
    model id from ANTHROPIC_MODEL (default claude-sonnet-4-5) -- overridable
    without a code change so the model can be bumped later without touching
    any prompt logic.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None, max_tokens: int = 8000):
        import anthropic  # imported lazily -- only required when this class is actually instantiated

        self._anthropic = anthropic
        resolved_key = api_key or settings.anthropic_api_key
        self._client = anthropic.Anthropic(api_key=resolved_key) if resolved_key else anthropic.Anthropic()
        self.model_name = model or settings.anthropic_model
        self._max_tokens = max_tokens

    def complete_structured(self, system: str, user: str, json_schema: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = self._client.messages.create(
                model=self.model_name,
                max_tokens=self._max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_config={"format": {"type": "json_schema", "schema": json_schema}},
            )
        except self._anthropic.APIConnectionError as exc:
            raise ClaudeApiError(f"Claude API: network error: {exc}") from exc
        except self._anthropic.RateLimitError as exc:
            raise ClaudeApiError(f"Claude API: rate limited: {exc}") from exc
        except self._anthropic.APIStatusError as exc:
            raise ClaudeApiError(f"Claude API: request failed ({exc.status_code}): {exc.message}") from exc

        try:
            text = next(block.text for block in response.content if block.type == "text")
            return json.loads(text)
        except (StopIteration, json.JSONDecodeError) as exc:
            raise ClaudeApiError(f"Claude API: response did not contain valid structured JSON: {exc}") from exc


def get_claude_client() -> ClaudeClient:
    """FastAPI dependency factory -- overridden with a fake in tests via
    `app.dependency_overrides`, the same pattern as `get_db`.
    """
    return AnthropicClaudeClient()
