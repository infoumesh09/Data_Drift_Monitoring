from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from ..database.session import Base


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    incident_id = Column(String(100), unique=True, nullable=False, index=True)
    pipeline_id = Column(UUID(as_uuid=True), ForeignKey("pipelines.id"), nullable=True, index=True)
    title = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    severity = Column(String(20), default="MEDIUM", nullable=False, index=True)
    status = Column(String(20), default="OPEN", nullable=False, index=True)
    affected_features = Column(JSONB, default=list)
    triggering_metric = Column(String(50), nullable=True)
    triggering_score = Column(Float, nullable=True)
    timeline_events = Column(JSONB, default=list)
    baseline_window = Column(JSONB, default=dict)
    current_window = Column(JSONB, default=dict)
    schema_changes = Column(JSONB, default=list)
    related_incident_ids = Column(JSONB, default=list)
    resolution_notes = Column(Text, nullable=True)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    ai_diagnosis = relationship("AIDiagnosis", back_populates="incident", uselist=False, cascade="all, delete-orphan")
    drift_events = relationship("DriftEvent", back_populates="incident")
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    pipeline = relationship("Pipeline", back_populates="incidents")

    def __repr__(self):
        return f"<Incident(id={self.id}, severity={self.severity}, status={self.status})>"
