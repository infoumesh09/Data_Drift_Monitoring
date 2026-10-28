from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from ..database.session import Base


class SchemaChange(Base):
    __tablename__ = "schema_changes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False, index=True)
    change_type = Column(String(50), nullable=False, index=True)
    column_name = Column(String(255), nullable=False, index=True)
    before_value = Column(JSONB, nullable=True)
    after_value = Column(JSONB, nullable=True)
    severity = Column(String(20), default="MEDIUM", nullable=False)
    description = Column(Text, nullable=True)
    detected_by = Column(String(50), default="SchemaMonitor")
    baseline_version = Column(String(50), nullable=True)
    current_version = Column(String(50), nullable=True)
    detection_run_id = Column(UUID(as_uuid=True), ForeignKey("detection_runs.id"), nullable=True, index=True)
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    dataset = relationship("Dataset", back_populates="schema_changes")
    detection_run = relationship("DetectionRun", back_populates="schema_changes")

    def __repr__(self):
        return f"<SchemaChange(id={self.id}, type={self.change_type}, column={self.column_name})>"
