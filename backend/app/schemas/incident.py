from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID


class IncidentBase(BaseModel):
    incident_id: str
    pipeline_id: Optional[UUID] = None
    title: str
    summary: Optional[str] = None
    severity: str = "MEDIUM"
    status: str = "OPEN"
    affected_features: List[str] = Field(default_factory=list)
    triggering_metric: Optional[str] = None
    triggering_score: Optional[float] = None
    timeline_events: List[Dict[str, Any]] = Field(default_factory=list)
    baseline_window: Dict[str, Any] = Field(default_factory=dict)
    current_window: Dict[str, Any] = Field(default_factory=dict)
    schema_changes: List[Dict[str, Any]] = Field(default_factory=list)
    related_incident_ids: List[str] = Field(default_factory=list)
    resolution_notes: Optional[str] = None


class IncidentCreate(IncidentBase):
    pass


class IncidentResponse(IncidentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    resolved_by: Optional[UUID] = None
    resolved_at: Optional[datetime] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class IncidentUpdate(BaseModel):
    status: Optional[str] = None
    severity: Optional[str] = None
    summary: Optional[str] = None
    resolution_notes: Optional[str] = None
