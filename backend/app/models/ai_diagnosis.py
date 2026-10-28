from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from ..database.session import Base


class AIDiagnosis(Base):
    __tablename__ = "ai_diagnoses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False, unique=True, index=True)
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=True)
    most_probable_cause = Column(Text, nullable=True)
    confidence = Column(Float, default=0.0)
    observed_evidence = Column(JSONB, default=list)
    hypotheses = Column(JSONB, default=list)
    recommendations = Column(JSONB, default=list)
    raw_response = Column(JSONB, nullable=True)
    evidence_summary = Column(Text, nullable=True)
    tools_used = Column(JSONB, default=list)
    agent_trace = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    incident = relationship("Incident", back_populates="ai_diagnosis")

    def __repr__(self):
        return f"<AIDiagnosis(id={self.id}, confidence={self.confidence})>"


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    diagnosis_id = Column(UUID(as_uuid=True), ForeignKey("ai_diagnoses.id"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(20), default="MEDIUM")
    action_type = Column(String(50), nullable=True)
    action_details = Column(JSONB, default=dict)
    status = Column(String(20), default="PENDING")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Recommendation(id={self.id}, priority={self.priority})>"
