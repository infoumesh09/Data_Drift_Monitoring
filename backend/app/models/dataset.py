from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from ..database.session import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    pipeline_id = Column(UUID(as_uuid=True), ForeignKey("pipelines.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    version = Column(String(50), default="1.0")
    storage_path = Column(String(1024), nullable=True)
    storage_backend = Column(String(50), default="local")
    file_format = Column(String(20), default="csv")
    row_count = Column(BigInteger, default=0)
    column_count = Column(Integer, default=0)
    size_bytes = Column(BigInteger, default=0)
    checksum = Column(String(64), nullable=True)
    profile = Column(JSONB, default=dict)
    tags = Column(JSONB, default=list)
    is_baseline = Column(Boolean, default=False)
    window_start = Column(DateTime, nullable=True)
    window_end = Column(DateTime, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    pipeline = relationship("Pipeline", back_populates="datasets")
    features = relationship("Feature", back_populates="dataset", cascade="all, delete-orphan")
    schema_changes = relationship("SchemaChange", back_populates="dataset", cascade="all, delete-orphan")
    drift_events = relationship("DriftEvent", back_populates="dataset", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Dataset(id={self.id}, name={self.name}, version={self.version})>"
