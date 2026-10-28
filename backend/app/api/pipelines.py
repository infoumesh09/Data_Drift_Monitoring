from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import uuid

from ..database.session import get_db
from ..services import pipelines as pipeline_service
from ..services import overview as overview_service
from ..schemas.pipeline import PipelineCreate, PipelineResponse, PipelineUpdate, PipelineSummary

router = APIRouter(prefix="/pipelines", tags=["Pipelines"])


@router.get("", response_model=List[PipelineResponse])
def list_pipelines(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return pipeline_service.list_pipelines(db, skip=skip, limit=limit, status=status)


@router.post("", response_model=PipelineResponse, status_code=201)
def create_pipeline(data: PipelineCreate, db: Session = Depends(get_db)):
    return pipeline_service.create_pipeline(db, data)


@router.get("/{pipeline_id}", response_model=PipelineResponse)
def get_pipeline(pipeline_id: uuid.UUID, db: Session = Depends(get_db)):
    p = pipeline_service.get_pipeline(db, pipeline_id)
    if not p:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return p


@router.patch("/{pipeline_id}", response_model=PipelineResponse)
def update_pipeline(pipeline_id: uuid.UUID, update: PipelineUpdate, db: Session = Depends(get_db)):
    p = pipeline_service.update_pipeline(db, pipeline_id, update)
    if not p:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return p


@router.delete("/{pipeline_id}", status_code=204)
def delete_pipeline(pipeline_id: uuid.UUID, db: Session = Depends(get_db)):
    if not pipeline_service.delete_pipeline(db, pipeline_id):
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return None
