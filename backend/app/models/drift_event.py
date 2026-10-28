from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from ..database.session import Base


class DriftEvent(Base):
    __tablename__ = "drift_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    event_id = Column(String(100), unique=True, nullable=False, index=True)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=True, index=True)
    pipeline_id = Column(UUID(as_uuid=True), ForeignKey("pipelines.id"), nullable=True, index=True)
    feature_id = Column(UUID(as_uuid=True), ForeignKey("features.id"), nullable=True, index=True)
    # Renamed from `feature` to avoid conflict with the relationship below
    feature_name = Column(String(255), nullable=False, index=True)
    drift_type = Column(String(50), nullable=False, index=True)
    metric = Column(String(50), nullable=False, index=True)
    score = Column(Float, nullable=False)
    p_value = Column(Float, nullable=True)
    severity = Column(String(20), default="LOW", nullable=False, index=True)
    direction = Column(String(20), nullable=True)
    threshold = Column(Float, nullable=True)
    baseline_window = Column(JSONB, default=dict)
    current_window = Column(JSONB, default=dict)
    baseline_distribution = Column(JSONB, nullable=True)
    current_distribution = Column(JSONB, nullable=True)
    evidence = Column(JSONB, default=dict)
    message = Column(Text, nullable=True)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=True, index=True)
    detection_run_id = Column(UUID(as_uuid=True), ForeignKey("detection_runs.id"), nullable=True, index=True)
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    dataset = relationship("Dataset", back_populates="drift_events")
    detection_run = relationship("DetectionRun", back_populates="drift_events")
    # Renamed from `feature` to avoid shadowing the column
    feature_obj = relationship("Feature", back_populates="drift_events", foreign_keys=[feature_id])
    incident = relationship("Incident", back_populates="drift_events")

    @property
    def feature(self) -> str:
        """Backwards-compat: return the feature name string."""
        return self.feature_name or ""

    @feature.setter
    def feature(self, value: str) -> None:
        self.feature_name = value

    def __repr__(self):
        return f"<DriftEvent(id={self.id}, feature={self.feature_name}, metric={self.metric}, severity={self.severity})>"
