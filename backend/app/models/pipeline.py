from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from ..database.session import Base


class Pipeline(Base):
    __tablename__ = "pipelines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    source_type = Column(String(100), nullable=False)
    source_config = Column(JSONB, nullable=True)
    destination_type = Column(String(100), nullable=True)
    destination_config = Column(JSONB, nullable=True)
    schedule = Column(String(100), nullable=True)
    status = Column(String(50), default="active", nullable=False)
    last_successful_run = Column(DateTime, nullable=True)
    last_run_at = Column(DateTime, nullable=True)
    health_score = Column(Integer, default=100)
    tags = Column(JSONB, default=list)
    config = Column(JSONB, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    datasets = relationship("Dataset", back_populates="pipeline", cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="pipeline", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Pipeline(id={self.id}, name={self.name}, status={self.status})>"
