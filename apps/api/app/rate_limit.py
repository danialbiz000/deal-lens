"""Rate limiting for the two paid-Claude-API endpoints and the ingest
endpoint (docs/phase4-ai-layer-design.md section 12 -- added post-review
for cost control once a real ANTHROPIC_API_KEY was configured and the repo
went public).

In-memory limiting via slowapi (wraps the `limits` package) is the right
call here, not a distributed store: this is a single-instance FastAPI app
backed by SQLite, with no multi-process/multi-node deployment anywhere in
scope. Two independent, stacked dimensions on the AI endpoints:
  - per-company (the real cost control): keyed on the {company_id} path
    param, not caller identity -- a per-IP limit alone doesn't stop one
    company's memo/IC-simulation from being regenerated endlessly by
    different callers. Deliberately separate per endpoint (design doc
    section 12.2: "per company, per endpoint") -- memo and ic-simulation
    each get their own per-company budget for the same company.
  - per-IP (abuse/blast-radius backstop): keyed on remote address,
    independent of which company is targeted, and -- per design doc
    section 12.2 -- COMBINED across both AI endpoints into one shared
    counter, unlike the per-company dimension.

Two distinct slowapi mechanisms are needed to get both of the above right,
and mixing them up produces two different silent-failure bugs (both found
by testing the actual cross-request behavior, not by reading the docs and
assuming):
  - `key_style="endpoint"` on the Limiter (not the slowapi default,
    "url"): the default folds the raw request path into the storage key,
    which for /companies/{company_id}/memo differs per company -- that
    silently scopes a same-route limit to one company at a time even when
    its key_func has nothing to do with company_id. Without this, the
    per-IP limit on /ingest (a single route, plain `.limit()`, no
    explicit `scope=`) would leak per-company through the URL.
  - `shared_limit(..., scope="ai_per_ip")` instead of a plain `.limit()`
    call, on BOTH /memo and /ic-simulation's per-IP decorator: `scope=`
    overrides slowapi's per-endpoint differentiation entirely
    (`limit_scope = lim.scope or endpoint` in slowapi's own
    `__evaluate_limits`), which `key_style` alone cannot do --
    `key_style="endpoint"` still differentiates `create_memo` from
    `create_ic_simulation` as two separate buckets (different function
    names), so it does NOT combine them. Passing the identical literal
    `scope=` string on both routes' per-IP decorators is what makes them
    share one real counter. The per-company decorators never set `scope`,
    so they're untouched by this and keep their correct
    per-company-per-endpoint behavior.

Limit VALUES are passed to `@limiter.limit(...)`/`@limiter.shared_limit(...)`
as zero-arg lambdas reading live `settings` attributes, not resolved once
at decoration time -- this is what lets dedicated rate-limit tests override
a limit at runtime (monkeypatch `settings.rate_limit_ai_per_company`, no
re-import needed) and is a first-class supported pattern
(`limit_value: Union[str, Callable]`).
"""

from typing import Optional

from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from app.config import settings

SCOPE_AI_PER_IP = "ai_per_ip"
SCOPE_AI_PER_COMPANY = "ai_per_company"
SCOPE_EXTRACTION_PER_COMPANY = "extraction_per_company"
SCOPE_INGEST_PER_IP = "ingest_per_ip"
SCOPE_INGEST_PER_COMPANY = "ingest_per_company"

_SCOPE_DESCRIPTIONS = {
    SCOPE_AI_PER_IP: "across all companies from this address",
    SCOPE_AI_PER_COMPANY: "for this company",
    SCOPE_EXTRACTION_PER_COMPANY: "for this company",
    SCOPE_INGEST_PER_IP: "from this address",
    SCOPE_INGEST_PER_COMPANY: "for this company",
}


def company_id_key(request: Request) -> str:
    """Key function for the per-company dimension. Every rate-limited route
    here uses `company_id` as its path parameter name."""
    return request.path_params.get("company_id", "unknown")


# key_style="endpoint" is deliberate, not the slowapi default ("url"): the
# default folds the raw request path into the storage key, which for
# /companies/{company_id}/memo means a DIFFERENT path per company -- that
# would silently scope the per-IP limit to one company too (defeating the
# whole point of a limit meant to combine usage "across all companies from
# this address"). Keying on the endpoint function name instead makes the
# per-IP counter genuinely shared across every company hitting the same
# route, while the per-company `key_func=company_id_key` limit still gets
# its own separate per-company bucket via the key FUNCTION, not the URL.
limiter = Limiter(key_func=get_remote_address, enabled=settings.rate_limit_enabled, key_style="endpoint")


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Custom handler producing the exact JSON shape from design doc
    section 12.4 -- `error_message` on each `.limit()`/`.shared_limit()`
    call carries the scope tag through to `exc.detail` (this is our own
    reporting tag, unrelated to slowapi's own `scope=` mechanism used for
    combining the per-IP AI limit across routes), and
    `exc.limit.limit.get_expiry()` gives the exact window length (in
    seconds) of the specific sub-limit that fired, used as a conservative
    `retry_after_seconds` upper bound.
    """
    scope = exc.detail if exc.detail in _SCOPE_DESCRIPTIONS else "unknown"
    limit_item = exc.limit.limit if exc.limit is not None else None
    limit_str = str(limit_item) if limit_item is not None else "rate limit"
    retry_after_seconds: Optional[int] = limit_item.get_expiry() if limit_item is not None else None

    description = _SCOPE_DESCRIPTIONS.get(scope)
    qualifier = f" {description}" if description else ""
    message = f"Rate limit exceeded: {limit_str}{qualifier}. Try again later."

    body = {
        "error": "rate_limit_exceeded",
        "scope": scope,
        "message": message,
        "retry_after_seconds": retry_after_seconds,
    }
    response = JSONResponse(status_code=429, content=body)
    if retry_after_seconds is not None:
        response.headers["Retry-After"] = str(retry_after_seconds)
    return response
