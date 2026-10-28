"""
Overview Service — Genuine Database-Driven Observability Metrics

Calculates dashboard metrics, health score, recent incidents, real heatmap,
and monitored pipelines directly from PostgreSQL records.
Never fabricates mock data or presents synthetic sine waves as real live metrics.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from ..models.pipeline import Pipeline
from ..models.incident import Incident
from ..models.drift_event import DriftEvent
from ..models.detection_run import DetectionRun
from ..models.feature import Feature


def build_overview_stats(db: Session) -> Dict[str, Any]:
    """Calculate actual pipeline and drift statistics from database records."""
    active_pipelines = db.query(Pipeline).filter(Pipeline.is_active == True).count()
    healthy_pipelines = (
        db.query(Pipeline)
        .filter(Pipeline.is_active == True)
        .filter(Pipeline.health_score >= 70)
        .count()
    )

    active_incidents = (
        db.query(Incident)
        .filter(Incident.status.in_(["OPEN", "IN_PROGRESS"]))
        .count()
    )
    critical_incidents = (
        db.query(Incident)
        .filter(Incident.status.in_(["OPEN", "IN_PROGRESS"]))
        .filter(Incident.severity == "CRITICAL")
        .count()
    )

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    drift_events_today = (
        db.query(DriftEvent)
        .filter(DriftEvent.detected_at >= today_start)
        .count()
    )

    # Monitored features from latest detection run or features table
    latest_run = db.query(DetectionRun).order_by(desc(DetectionRun.created_at)).first()
    if latest_run and latest_run.features_monitored:
        monitored_features = latest_run.features_monitored
    else:
        monitored_features = db.query(Feature).count()

    # Calculate Data Health Score
    has_data = (active_pipelines > 0) or (latest_run is not None)
    if not has_data:
        data_health_score = 100
    else:
        # Penalize for active unresolved incidents
        penalty = (critical_incidents * 30) + ((active_incidents - critical_incidents) * 15)
        # If active pipelines have individual health scores, incorporate them
        pipe_scores = [p.health_score for p in db.query(Pipeline).filter(Pipeline.is_active == True).all() if p.health_score is not None]
        if pipe_scores:
            base_score = sum(pipe_scores) / len(pipe_scores)
            data_health_score = max(0, min(100, int(round(base_score - (penalty * 0.5)))))
        else:
            data_health_score = max(0, min(100, 100 - penalty))

    return {
        "has_data": has_data,
        "data_health_score": data_health_score,
        "active_pipelines": active_pipelines,
        "healthy_pipelines": healthy_pipelines,
        "active_incidents": active_incidents,
        "critical_incidents": critical_incidents,
        "monitored_features": monitored_features,
        "drift_events_today": drift_events_today,
    }


def build_real_heatmap(db: Session) -> Dict[str, Any]:
    """
    Construct drift severity heatmap from real DriftEvent records in the last 24h.
    If no events exist, returns an empty structure with has_data=False.
    """
    since = datetime.utcnow() - timedelta(hours=24)
    events = (
        db.query(DriftEvent)
        .filter(DriftEvent.detected_at >= since)
        .order_by(DriftEvent.detected_at.asc())
        .all()
    )

    if not events:
        return {"has_data": False, "time_windows": [], "rows": []}

    # Generate 2-hour window buckets
    windows = [f"{h:02d}:00" for h in range(0, 24, 2)]
    feature_events: Dict[str, Dict[str, str]] = {}

    for ev in events:
        feat = ev.feature_name
        if feat not in feature_events:
            feature_events[feat] = {w: "HEALTHY" for w in windows}

        hour = ev.detected_at.hour
        bucket_idx = (hour // 2) * 2
        bucket_str = f"{bucket_idx:02d}:00"
        # Overwrite with highest severity in bucket
        current_sev = feature_events[feat].get(bucket_str, "HEALTHY")
        from ..drift.runner import SEVERITY_RANK
        if SEVERITY_RANK.get(ev.severity, 1) > SEVERITY_RANK.get(current_sev, 1):
            feature_events[feat][bucket_str] = ev.severity

    rows = []
    for feat, cell_map in feature_events.items():
        rows.append({
            "feature": feat,
            "cells": [cell_map[w] for w in windows],
        })

    return {
        "has_data": True,
        "time_windows": windows,
        "rows": rows,
    }


def list_real_pipelines(db: Session, limit: int = 10) -> List[Dict[str, Any]]:
    """Fetch real pipelines from database. Returns empty list if none exist."""
    pipes = db.query(Pipeline).order_by(desc(Pipeline.created_at)).limit(limit).all()
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "source": p.source_type or "Configured Source",
            "destination": p.destination_type or "Warehouse",
            "last_successful_run": p.last_run_at.isoformat() if p.last_run_at else None,
            "status": "Healthy" if (p.health_score or 100) >= 70 else "Warning",
            "mcfe_count": p.monitored_features_count or 0,
            "project": p.project or "default",
        }
        for p in pipes
    ]


def list_real_incidents(db: Session, limit: int = 5) -> List[Dict[str, Any]]:
    """Fetch recent incidents from database."""
    items = db.query(Incident).order_by(desc(Incident.created_at)).limit(limit).all()
    from .drift_events import serialize_incident
    return [serialize_incident(i) for i in items]


def list_real_drift_scores(db: Session) -> List[Dict[str, Any]]:
    """Fetch feature scores from the latest detection run."""
    latest_run = db.query(DetectionRun).order_by(desc(DetectionRun.created_at)).first()
    if not latest_run:
        return []

    events = db.query(DriftEvent).filter(DriftEvent.detection_run_id == latest_run.id).all()
    scores = []
    for e in events:
        ev = e.evidence or {}
        scores.append({
            "feature": e.feature_name,
            "type": "numerical" if e.metric in ("KS", "PSI") else "categorical",
            "psi": ev.get("psi_score", e.score if e.metric == "PSI" else 0.0),
            "kl": ev.get("kl_score", e.score if e.metric == "KL" else 0.0),
            "ks_stat": ev.get("ks_statistic", e.score if e.metric == "KS" else 0.0),
            "ks_p": ev.get("ks_p_value", e.p_value if e.metric == "KS" else 1.0),
            "null_rate": ev.get("null_rate_change", 0.0),
            "severity": e.severity,
            "drift_type": e.drift_type or "Distribution Drift",
        })
    return scores
