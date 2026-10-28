from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    environment: str
    timestamp: datetime
    database: Optional[Dict[str, Any]] = None


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int


class CommonDriftEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    dataset_id: Optional[UUID] = None
    pipeline_id: Optional[UUID] = None
    feature: str
    drift_type: str
    metric: str
    score: float
    p_value: Optional[float] = None
    severity: str
    direction: Optional[str] = None
    threshold: Optional[float] = None
    baseline_window: Dict[str, Any] = Field(default_factory=dict)
    current_window: Dict[str, Any] = Field(default_factory=dict)
    baseline_distribution: Optional[Dict[str, Any]] = None
    current_distribution: Optional[Dict[str, Any]] = None
    evidence: Dict[str, Any] = Field(default_factory=dict)
    message: Optional[str] = None
    detected_at: datetime = Field(default_factory=datetime.utcnow)


class SeverityThresholds(BaseModel):
    psi_healthy: float = 0.1
    psi_low: float = 0.2
    psi_medium: float = 0.3
    psi_high: float = 0.5

    kl_healthy: float = 0.05
    kl_low: float = 0.1
    kl_medium: float = 0.3
    kl_high: float = 0.5

    ks_significance: float = 0.05

    null_rate_healthy: float = 0.01
    null_rate_warning: float = 0.05
    null_rate_high: float = 0.15
    null_rate_critical: float = 0.30


class WindowConfig(BaseModel):
    baseline_start: Optional[datetime] = None
    baseline_end: Optional[datetime] = None
    current_start: Optional[datetime] = None
    current_end: Optional[datetime] = None
    window_size: Optional[int] = None
    dataset_version: Optional[str] = None
