from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID


class FeatureBase(BaseModel):
    dataset_id: UUID
    name: str
    display_name: Optional[str] = None
    data_type: str
    feature_class: str = "unsupported"
    null_count: int = 0
    null_rate: float = 0.0
    cardinality: int = 0
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    mean_value: Optional[float] = None
    std_value: Optional[float] = None
    unique_values: List[Any] = Field(default_factory=list)
    value_counts: Dict[str, int] = Field(default_factory=dict)
    histogram: Optional[Dict[str, Any]] = None
    statistics: Dict[str, Any] = Field(default_factory=dict)
    is_identifier: int = 0
    position: int = 0
    monitored: int = 1


class FeatureCreate(FeatureBase):
    pass


class FeatureResponse(FeatureBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
