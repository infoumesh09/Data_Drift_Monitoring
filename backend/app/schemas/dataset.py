from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID


class DatasetBase(BaseModel):
    name: str
    description: Optional[str] = None
    pipeline_id: Optional[UUID] = None
    version: str = "1.0"
    storage_backend: str = "local"
    file_format: str = "csv"
    tags: List[str] = Field(default_factory=list)
    is_baseline: bool = False
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None


class DatasetCreate(DatasetBase):
    pass


class DatasetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_baseline: Optional[bool] = None
    profile: Optional[Dict[str, Any]] = None


class DatasetResponse(DatasetBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    storage_path: Optional[str] = None
    row_count: int = 0
    column_count: int = 0
    size_bytes: int = 0
    checksum: Optional[str] = None
    profile: Dict[str, Any] = Field(default_factory=dict)
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class DatasetProfile(BaseModel):
    dataset_id: Optional[UUID] = None
    name: str
    row_count: int
    column_count: int
    size_bytes: Optional[int] = 0
    file_size_bytes: Optional[int] = 0
    columns: List[Dict[str, Any]] = Field(default_factory=list)
    numerical_stats: Dict[str, Any] = Field(default_factory=dict)
    categorical_stats: Dict[str, Any] = Field(default_factory=dict)
    null_summary: Dict[str, Any] = Field(default_factory=dict)
    duplicate_rows: int = 0
    memory_usage_bytes: int = 0
    inferred_types: Dict[str, str] = Field(default_factory=dict)
