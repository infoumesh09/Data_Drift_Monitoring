from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict, model_validator
from uuid import UUID


class DriftEventBase(BaseModel):
    event_id: str
    dataset_id: Optional[UUID] = None
    pipeline_id: Optional[UUID] = None
    feature_id: Optional[UUID] = None
    # Accept both 'feature' and 'feature_name'; store as feature_name
    feature_name: Optional[str] = None
    feature: Optional[str] = None
    drift_type: str
    metric: str
    score: float
    p_value: Optional[float] = None
    severity: str = "LOW"
    direction: Optional[str] = None
    threshold: Optional[float] = None
    baseline_window: Dict[str, Any] = Field(default_factory=dict)
    current_window: Dict[str, Any] = Field(default_factory=dict)
    baseline_distribution: Optional[Dict[str, Any]] = None
    current_distribution: Optional[Dict[str, Any]] = None
    evidence: Dict[str, Any] = Field(default_factory=dict)
    message: Optional[str] = None
    incident_id: Optional[UUID] = None

    @model_validator(mode="after")
    def sync_feature_fields(self) -> "DriftEventBase":
        if self.feature and not self.feature_name:
            self.feature_name = self.feature
        elif self.feature_name and not self.feature:
            self.feature = self.feature_name
        return self

    @property
    def resolved_feature(self) -> str:
        return self.feature_name or self.feature or ""


class DriftEventCreate(DriftEventBase):
    pass


class DriftEventResponse(DriftEventBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    detected_at: datetime
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def map_feature_name_from_orm(cls, values):
        """Support ORM objects that expose feature_name as the column."""
        if hasattr(values, "feature_name"):
            # It's an ORM object — extract into a dict-like structure
            fn = values.feature_name
            if fn is not None:
                try:
                    values.__dict__["feature"] = fn
                except Exception:
                    pass
        return values


class DriftDetectionRequest(BaseModel):
    baseline_dataset_id: UUID
    current_dataset_id: UUID
    features: Optional[List[str]] = None
    run_psi: bool = True
    run_kl: bool = True
    run_ks: bool = True
    run_schema: bool = True
    run_null_rate: bool = True
    thresholds: Optional[Dict[str, Any]] = None
