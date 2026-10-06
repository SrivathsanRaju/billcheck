from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.database import engine, Base
from app.models import db_models  # ensure models are imported
from app.api.routes import router

# ---------------------------------------------------------------------------
# Schema migrations — runs before first request, safe to run on every boot.
# Each statement uses IF NOT EXISTS / DO NOTHING so it's idempotent.
# ---------------------------------------------------------------------------
_MIGRATIONS = [
    # Add actual_weight column for weight-overcharge check (v2)
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS actual_weight FLOAT",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        # Create all tables on startup
        await conn.run_sync(Base.metadata.create_all)
        # Apply incremental column migrations
        for stmt in _MIGRATIONS:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass  # Column likely already exists; swallow and continue
    yield


app = FastAPI(title="BillCheck API", version="2.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": app.version,
        "checks": 7,  # 6 rule checks + duplicate AWB
        "providers_supported": 14,
    }
