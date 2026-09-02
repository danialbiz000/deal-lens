"""FastAPI application entrypoint: app instance, router registration, /health.

Phase 0 is Company -> Financials -> Screening Score
(docs/phase0-vertical-slice-design.md); Phase 2 adds comps + LBO
underwriting (docs/phase2-comps-lbo-design.md) -- both explicitly deferred
any AI/LLM layer, and `packages/finance_engine` still has zero references
to `anthropic`/`claude`/`apps.api.app.ai` anywhere (grep-able, and it's
physically incapable of gaining any: `app/ai/` imports from
`finance_engine`, never the reverse). Phase 4
(docs/phase4-ai-layer-design.md) is the first phase to make real Claude API
calls, and confines every one of them to `app/ai/` -- `POST .../memo` and
`POST .../ic-simulation` are the only two endpoints in the whole codebase
that make outbound network calls to a third-party API. Those two plus
`POST .../ingest` carry rate limits (`app/rate_limit.py`,
docs/phase4-ai-layer-design.md section 12) as cost/abuse control now that a
real API key is configured and the repo is public.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.db import init_db
from app.rate_limit import limiter, rate_limit_exceeded_handler
from app.routers import ai, assumptions, comps, companies, financials, lbo, scenarios, screening


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="DealLens API", version="0.1.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # local-dev-only slice; no auth yet (design doc section 7)
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(companies.router)
app.include_router(financials.router)
app.include_router(assumptions.router)
app.include_router(screening.router)
app.include_router(comps.router)
app.include_router(scenarios.router)
app.include_router(lbo.router)
app.include_router(ai.router)
