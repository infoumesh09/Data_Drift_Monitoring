"""
DriftSense — FastAPI Entrypoint

Run:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from .config import get_settings
from .api.router import api_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from .database.session import init_db, engine
        from sqlalchemy import text
        init_db()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
    except Exception as exc:
        print(f"[startup] database init skipped (ok for dev without postgres): {exc}")
    yield
    print("[shutdown] DriftSense backend shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Autonomous Data Pipeline Health Monitoring: Statistical Drift Detection with Agentic AI-Driven Diagnosis",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(api_router)


@app.get("/", tags=["Root"])
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.BACKEND_ENV,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/api/v1/health",
        "api_prefix": "/api/v1",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=settings.BACKEND_ENV == "development",
    )
