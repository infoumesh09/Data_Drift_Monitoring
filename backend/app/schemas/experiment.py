from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID


class ExperimentBase(BaseModel):
    name: str
    description: Optional[str] = None
    experiment_type: str
    config: Dict[str, Any] = Field(default_factory=dict)
    random_seed: int = 42


class ExperimentCreate(ExperimentBase):
    pass


class ExperimentResponse(ExperimentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str = "PENDING"
    created_by: Optional[UUID] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ExperimentResultBase(BaseModel):
    experiment_id: UUID
    dataset_name: Optional[str] = None
    feature_name: Optional[str] = None
    feature_type: Optional[str] = None
    drift_type: Optional[str] = None
    drift_magnitude: Optional[float] = None
    sample_size: Optional[int] = None
    window_size: Optional[int] = None
    psi_score: Optional[float] = None
    kl_score: Optional[float] = None
    ks_statistic: Optional[float] = None
    ks_p_value: Optional[float] = None
    psi_detected: int = 0
    kl_detected: int = 0
    ks_detected: int = 0
    detection_latency_ms: Optional[float] = None
    execution_time_ms: Optional[float] = None
    is_false_positive: int = 0
    is_false_negative: int = 0
    metrics: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExperimentResultCreate(ExperimentResultBase):
    pass


class ExperimentResultResponse(ExperimentResultBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


class RunExperimentRequest(BaseModel):
    experiment_id: Optional[UUID] = None
    dataset_id: Optional[UUID] = None  # If provided, load this dataset; otherwise use synthetic data
    drift_types: List[str] = Field(default_factory=lambda: [
        "no_drift", "small_mean_shift", "medium_mean_shift", "large_mean_shift",
        "variance_shift", "distribution_shift", "categorical_shift",
        "gradual_drift", "sudden_drift", "null_rate_spike", "schema_change"
    ])
    feature_types: List[str] = Field(default_factory=lambda: ["numerical", "categorical"])
    sample_sizes: List[int] = Field(default_factory=lambda: [1000, 5000, 10000])
    magnitudes: List[float] = Field(default_factory=lambda: [0.5, 1.0, 2.0])
    random_seed: int = 42
