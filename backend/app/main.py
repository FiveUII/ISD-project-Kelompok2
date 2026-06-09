"""
FastAPI application entry point.

Configures:
- CORS with explicit allowed origins (never '*' with credentials — STACK.md CORS gotcha)
- All API routers under /api prefix
- Startup hook that seeds library_settings and admin superuser (both idempotent)
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.db import async_session_maker
import asyncio
import logging

from app.routers import health
from app.routers import auth
from app.routers import admin
from app.routers import books
from app.routers import loans
from app.routers import fines
from app.scheduler import configure_scheduler
from app.services.notification_service import run_notification_job
from app.seed import seed_library_settings, seed_admin_superuser

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan: seed the database on startup, then start the APScheduler.

    Seeds are idempotent — safe to call on every restart.
    The scheduler fires once immediately at startup (via ensure_future) and then
    every 24 hours via the interval trigger.
    """
    async with async_session_maker() as session:
        await seed_library_settings(session)
        await seed_admin_superuser(session)
        await session.commit()

    # Start APScheduler for daily email notifications
    _scheduler = configure_scheduler()
    _scheduler.start()
    logger.info("Scheduler started")

    # Fire the notification job once immediately at startup
    asyncio.ensure_future(run_notification_job())

    yield

    # Clean shutdown — do not wait for running jobs
    _scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")


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
app.include_router(auth.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(books.student_router, prefix="/api")
app.include_router(books.librarian_router, prefix="/api")
app.include_router(books.copies_router, prefix="/api")
app.include_router(loans.loans_router, prefix="/api")
app.include_router(loans.student_loans_router, prefix="/api")
app.include_router(fines.fines_router, prefix="/api")
