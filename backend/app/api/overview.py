from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database.session import get_db
from ..services import overview as overview_service

router = APIRouter(prefix="/overview", tags=["Overview"])


@router.get("")
def get_overview(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Return overview statistics, recent pipelines, real heatmap, and incidents
    calculated from actual PostgreSQL database records.
    """
    stats = overview_service.build_overview_stats(db)
    pipelines = overview_service.list_real_pipelines(db, limit=10)
    heatmap = overview_service.build_real_heatmap(db)
    incidents = overview_service.list_real_incidents(db, limit=5)
    drift_scores = overview_service.list_real_drift_scores(db)

    return {
        "stats": stats,
        "pipelines": pipelines,
        "drift_heatmap": heatmap,
        "incidents": incidents,
        "drift_scores": drift_scores,
    }
