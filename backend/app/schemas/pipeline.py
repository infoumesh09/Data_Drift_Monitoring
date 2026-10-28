from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID


class PipelineBase(BaseModel):
    name: str
    description: Optional[str] = None
    source_type: str = "csv"
    source_config: Dict[str, Any] = Field(default_factory=dict)
    destination_type: Optional[str] = None
    destination_config: Optional[Dict[str, Any]] = None
    schedule: Optional[str] = None
    status: str = "active"
    tags: List[str] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)


class PipelineCreate(PipelineBase):
    pass


class PipelineUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class PipelineResponse(PipelineBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: Optional[UUID] = None
    last_successful_run: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    health_score: int = 100
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class PipelineSummary(BaseModel):
    id: UUID
    name: str
    status: str
    health_score: int
    last_successful_run: Optional[datetime] = None
