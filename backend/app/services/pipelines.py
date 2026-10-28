from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
import uuid

from ..models.pipeline import Pipeline
from ..schemas.pipeline import PipelineCreate, PipelineUpdate


def create_pipeline(db: Session, data: PipelineCreate, owner_id: Optional[uuid.UUID] = None) -> Pipeline:
    pipe = Pipeline(
        **data.model_dump(),
        owner_id=owner_id,
    )
    db.add(pipe)
    db.commit()
    db.refresh(pipe)
    return pipe


def list_pipelines(db: Session, skip: int = 0, limit: int = 100, status: Optional[str] = None) -> List[Pipeline]:
    q = db.query(Pipeline).filter(Pipeline.is_active == True)
    if status:
        q = q.filter(Pipeline.status == status)
    return q.order_by(Pipeline.created_at.desc()).offset(skip).limit(limit).all()


def get_pipeline(db: Session, pipeline_id: uuid.UUID) -> Optional[Pipeline]:
    return db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()


def update_pipeline(db: Session, pipeline_id: uuid.UUID, update: PipelineUpdate) -> Optional[Pipeline]:
    pipe = get_pipeline(db, pipeline_id)
    if not pipe:
        return None
    for field_name, value in update.model_dump(exclude_unset=True).items():
        setattr(pipe, field_name, value)
    pipe.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(pipe)
    return pipe


def delete_pipeline(db: Session, pipeline_id: uuid.UUID) -> bool:
    pipe = get_pipeline(db, pipeline_id)
    if not pipe:
        return False
    pipe.is_active = False
    pipe.updated_at = datetime.utcnow()
    db.commit()
    return True


def count_pipelines(db: Session) -> int:
    return db.query(Pipeline).filter(Pipeline.is_active == True).count()
