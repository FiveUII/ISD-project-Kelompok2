"""
FastAPI application entry point.

Configures:
- CORS with explicit allowed origins (never '*' with credentials — STACK.md CORS gotcha)
- All API routers under /api prefix
- Startup hook that seeds library_settings (idempotent)
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.db import async_session_maker
from app.routers import health
from app.seed import seed_library_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan: seed the database on startup.
    seed_library_settings is idempotent — safe to call on every restart.
    """
    async with async_session_maker() as session:
        await seed_library_settings(session)
    yield


app = FastAPI(
    title="Library Management System",
    description="Backend API for the school library management system.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS: explicit origin list — do NOT use ["*"] when credentials may be included.
# See STACK.md 'Docker Compose CORS Gotcha' and PITFALLS C4.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routers under the /api prefix
app.include_router(health.router, prefix="/api")
