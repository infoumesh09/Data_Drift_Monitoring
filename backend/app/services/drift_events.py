from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import uuid

from ..models.drift_event import DriftEvent
from ..models.incident import Incident
from ..schemas.drift import DriftEventCreate
from ..schemas.incident import IncidentCreate, IncidentUpdate


# ---------------------------------------------------------------------------
# Drift Events
# ---------------------------------------------------------------------------

def create_drift_event(db: Session, data: Dict[str, Any]) -> DriftEvent:
    """Create a DriftEvent from a dict.  Accepts either 'feature' or 'feature_name'."""
    payload = dict(data)
    # Map legacy 'feature' key to the renamed column 'feature_name'
    if "feature" in payload and "feature_name" not in payload:
        payload["feature_name"] = payload.pop("feature")
    elif "feature" in payload:
        payload.pop("feature")  # feature_name already present; discard duplicate
    event = DriftEvent(**payload)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_drift_events(
    db: Session,
    dataset_id: Optional[uuid.UUID] = None,
    pipeline_id: Optional[uuid.UUID] = None,
    feature: Optional[str] = None,
    severity: Optional[str] = None,
    drift_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[DriftEvent]:
    q = db.query(DriftEvent)
    if dataset_id:
        q = q.filter(DriftEvent.dataset_id == dataset_id)
    if pipeline_id:
        q = q.filter(DriftEvent.pipeline_id == pipeline_id)
    if feature:
        q = q.filter(DriftEvent.feature_name == feature)
    if severity:
        q = q.filter(DriftEvent.severity == severity)
    if drift_type:
        q = q.filter(DriftEvent.drift_type == drift_type)
    return q.order_by(DriftEvent.detected_at.desc()).offset(skip).limit(limit).all()


def serialize_drift_event(event: DriftEvent) -> Dict[str, Any]:
    """Convert ORM object to serializable dict."""
    return {
        "id": str(event.id),
        "event_id": event.event_id,
        "dataset_id": str(event.dataset_id) if event.dataset_id else None,
        "pipeline_id": str(event.pipeline_id) if event.pipeline_id else None,
        "feature_id": str(event.feature_id) if event.feature_id else None,
        "feature": event.feature_name,
        "feature_name": event.feature_name,
        "drift_type": event.drift_type,
        "metric": event.metric,
        "score": event.score,
        "p_value": event.p_value,
        "severity": event.severity,
        "direction": event.direction,
        "threshold": event.threshold,
        "baseline_window": event.baseline_window,
        "current_window": event.current_window,
        "baseline_distribution": event.baseline_distribution,
        "current_distribution": event.current_distribution,
        "evidence": event.evidence,
        "message": event.message,
        "incident_id": str(event.incident_id) if event.incident_id else None,
        "detected_at": event.detected_at.isoformat() if event.detected_at else None,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------

def list_incidents(
    db: Session,
    pipeline_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Incident]:
    q = db.query(Incident)
    if pipeline_id:
        q = q.filter(Incident.pipeline_id == pipeline_id)
    if status:
        q = q.filter(Incident.status == status)
    if severity:
        q = q.filter(Incident.severity == severity)
    return q.order_by(Incident.created_at.desc()).offset(skip).limit(limit).all()


def get_incident(db: Session, incident_id: uuid.UUID) -> Optional[Incident]:
    return db.query(Incident).filter(Incident.id == incident_id).first()


def create_incident(db: Session, data: IncidentCreate) -> Incident:
    incident = Incident(**data.model_dump())
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


def update_incident(db: Session, incident_id: uuid.UUID, update: IncidentUpdate) -> Optional[Incident]:
    incident = get_incident(db, incident_id)
    if not incident:
        return None
    for field_name, value in update.model_dump(exclude_unset=True).items():
        setattr(incident, field_name, value)
    if update.status == "RESOLVED" and not incident.resolved_at:
        incident.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(incident)
    return incident


def serialize_incident(incident: Incident) -> Dict[str, Any]:
    """Convert Incident ORM to serializable dict (compatible with frontend IncidentSummary)."""
    features = incident.affected_features or []
    return {
        "id": incident.incident_id or str(incident.id),
        "db_id": str(incident.id),
        "summary": incident.summary or incident.title,
        "severity": incident.severity,
        "feature": features[0] if features else "",
        "status": incident.status,
        "metric": incident.triggering_metric or "",
        "score": incident.triggering_score or 0.0,
        "timestamp": incident.created_at.isoformat() if incident.created_at else datetime.utcnow().isoformat(),
        "drift_type": "",
        "affected_features": features,
        "title": incident.title,
        "pipeline_id": str(incident.pipeline_id) if incident.pipeline_id else None,
        "resolution_notes": incident.resolution_notes,
        "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
    }


# ---------------------------------------------------------------------------
# Aggregate helpers
# ---------------------------------------------------------------------------

def count_incidents(db: Session, status: Optional[str] = None) -> int:
    q = db.query(Incident)
    if status:
        q = q.filter(Incident.status == status)
    return q.count()


def count_drift_events_today(db: Session) -> int:
    today = datetime.utcnow().date()
    return (
        db.query(DriftEvent)
        .filter(DriftEvent.detected_at >= datetime(today.year, today.month, today.day))
        .count()
    )


def count_critical_incidents(db: Session) -> int:
    return db.query(Incident).filter(
        Incident.severity == "CRITICAL", Incident.status != "RESOLVED"
    ).count()
