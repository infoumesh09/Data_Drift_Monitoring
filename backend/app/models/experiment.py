from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, BigInteger, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from ..database.session import Base


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    experiment_type = Column(String(100), nullable=False)
    config = Column(JSONB, default=dict)
    random_seed = Column(Integer, default=42)
    status = Column(String(20), default="PENDING", nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    results = relationship("ExperimentResult", back_populates="experiment", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Experiment(id={self.id}, name={self.name}, type={self.experiment_type})>"


class ExperimentResult(Base):
    __tablename__ = "experiment_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    experiment_id = Column(UUID(as_uuid=True), ForeignKey("experiments.id"), nullable=False, index=True)
    dataset_name = Column(String(255), nullable=True)
    feature_name = Column(String(255), nullable=True)
    feature_type = Column(String(50), nullable=True)
    drift_type = Column(String(50), nullable=True, index=True)
    drift_magnitude = Column(Float, nullable=True)
    sample_size = Column(BigInteger, nullable=True)
    window_size = Column(BigInteger, nullable=True)
    psi_score = Column(Float, nullable=True)
    kl_score = Column(Float, nullable=True)
    ks_statistic = Column(Float, nullable=True)
    ks_p_value = Column(Float, nullable=True)
    psi_detected = Column(Integer, default=0)
    kl_detected = Column(Integer, default=0)
    ks_detected = Column(Integer, default=0)
    detection_latency_ms = Column(Float, nullable=True)
    execution_time_ms = Column(Float, nullable=True)
    ground_truth_drift = Column(Integer, default=0)
    is_false_positive = Column(Integer, default=0)
    is_false_negative = Column(Integer, default=0)
    metrics = Column(JSONB, default=dict)
    run_metadata = Column('metadata', JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    experiment = relationship("Experiment", back_populates="results")

    def __repr__(self):
        return f"<ExperimentResult(id={self.id}, drift_type={self.drift_type})>"
