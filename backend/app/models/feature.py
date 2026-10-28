from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, BigInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from ..database.session import Base


class Feature(Base):
    __tablename__ = "features"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=True)
    data_type = Column(String(50), nullable=False)
    feature_class = Column(String(50), default="unsupported")
    null_count = Column(BigInteger, default=0)
    null_rate = Column(Float, default=0.0)
    cardinality = Column(Integer, default=0)
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    mean_value = Column(Float, nullable=True)
    std_value = Column(Float, nullable=True)
    unique_values = Column(JSONB, default=list)
    value_counts = Column(JSONB, default=dict)
    histogram = Column(JSONB, nullable=True)
    statistics = Column(JSONB, default=dict)
    is_identifier = Column(Integer, default=0)
    position = Column(Integer, default=0)
    monitored = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    dataset = relationship("Dataset", back_populates="features")
    drift_events = relationship("DriftEvent", back_populates="feature_obj", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Feature(id={self.id}, name={self.name}, data_type={self.data_type})>"
