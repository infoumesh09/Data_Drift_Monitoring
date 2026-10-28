from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from ..database.session import Base


class DetectionRun(Base):
    __tablename__ = "detection_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    run_id = Column(String(100), unique=True, nullable=False, index=True)
    baseline_dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=True, index=True)
    current_dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=True, index=True)
    pipeline_id = Column(UUID(as_uuid=True), ForeignKey("pipelines.id"), nullable=True, index=True)
    status = Column(String(50), default="COMPLETED", nullable=False, index=True)
    overall_severity = Column(String(20), default="HEALTHY", nullable=False, index=True)
    features_monitored = Column(Integer, default=0)
    features_with_drift = Column(Integer, default=0)
    baseline_rows = Column(Integer, default=0)
    baseline_cols = Column(Integer, default=0)
    current_rows = Column(Integer, default=0)
    current_cols = Column(Integer, default=0)
    classification = Column(JSONB, default=dict)
    summary_stats = Column(JSONB, default=dict)
    schema_drift_summary = Column(JSONB, default=dict)
    null_rate_summary = Column(JSONB, default=dict)
    metrics_by_algorithm = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    baseline_dataset = relationship("Dataset", foreign_keys=[baseline_dataset_id])
    current_dataset = relationship("Dataset", foreign_keys=[current_dataset_id])
    pipeline = relationship("Pipeline", foreign_keys=[pipeline_id])
    drift_events = relationship("DriftEvent", back_populates="detection_run", cascade="all, delete-orphan")
    schema_changes = relationship("SchemaChange", back_populates="detection_run", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<DetectionRun(run_id={self.run_id}, severity={self.overall_severity}, drift_features={self.features_with_drift})>"
