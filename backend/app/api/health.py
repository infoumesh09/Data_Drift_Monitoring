from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..database.session import get_db
from ..schemas.common import HealthResponse
from ..config import get_settings

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
@router.get("/status", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    settings = get_settings()
    database_info = {"status": "unknown"}
    try:
        result = db.execute(text("SELECT 1")).scalar()
        database_info = {
            "status": "connected" if result == 1 else "error",
            "reachable": result == 1,
        }
    except Exception as exc:
        database_info = {"status": "disconnected", "error": str(exc)}

    return HealthResponse(
        status="ok" if database_info.get("status") == "connected" else "degraded",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.BACKEND_ENV,
        timestamp=datetime.utcnow(),
        database=database_info,
    )
