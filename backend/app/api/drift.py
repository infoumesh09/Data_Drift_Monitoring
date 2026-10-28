"""
Drift Detection API

Endpoints:
- POST /drift/detect                 - Execute full drift detection, persist DetectionRun, DriftEvents, SchemaChanges, and auto-generate Incidents.
- GET  /drift/latest                 - Get the most recent detection run with all feature results.
- GET  /drift/runs                   - List historical detection runs.
- GET  /drift/feature-scores         - Return feature scores from the latest detection run (or empty if none).
- GET  /drift/feature/{name}/history - Return longitudinal history and distribution for a specific feature.
- GET  /drift/schema                 - Return real schema comparison from the latest detection run.
- GET  /drift/incidents              - List real incidents from PostgreSQL (never returns mock data).
- GET  /drift/incidents/{id}         - Retrieve a single incident by ID.
- PATCH /drift/incidents/{id}        - Update incident status and resolution notes.
- GET  /drift/events                 - List raw drift events.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
import uuid
from datetime import datetime

from ..database.session import get_db
from ..models.detection_run import DetectionRun
from ..models.drift_event import DriftEvent
from ..models.schema_change import SchemaChange
from ..models.incident import Incident
from ..services import drift_events as drift_service
from ..services import datasets as dataset_service
from ..schemas.drift import DriftDetectionRequest
from ..schemas.incident import IncidentCreate, IncidentUpdate
from ..drift.runner import run_drift_detection, SEVERITY_RANK

router = APIRouter(prefix="/drift", tags=["Drift Detection"])


# ---------------------------------------------------------------------------
# Detection Execution & Persistence
# ---------------------------------------------------------------------------

@router.post("/detect")
async def detect_drift(req: DriftDetectionRequest, db: Session = Depends(get_db)):
    """
    Execute multi-algorithm drift detection between baseline and current datasets,
    persist results to PostgreSQL, and automatically create incidents if significant drift is found.
    """
    baseline_ds = dataset_service.get_dataset(db, req.baseline_dataset_id)
    current_ds = dataset_service.get_dataset(db, req.current_dataset_id)
    if not baseline_ds or not current_ds:
        raise HTTPException(status_code=404, detail="Baseline or current dataset not found in database.")

    baseline_df = dataset_service.load_dataset_dataframe(baseline_ds)
    current_df = dataset_service.load_dataset_dataframe(current_ds)
    if baseline_df is None or current_df is None:
        raise HTTPException(status_code=500, detail="Failed to load dataset files from storage.")

    # Execute statistical engine
    result = run_drift_detection(
        baseline_df,
        current_df,
        features=req.features,
        run_psi=req.run_psi,
        run_kl=req.run_kl,
        run_ks=req.run_ks,
        run_schema=req.run_schema,
        run_null_rate=req.run_null_rate,
        thresholds=req.thresholds,
        dataset_name=current_ds.name,
        baseline_version=baseline_ds.version,
        current_version=current_ds.version,
    )

    # 1. Create DetectionRun record
    det_run = DetectionRun(
        run_id=result.run_id,
        baseline_dataset_id=baseline_ds.id,
        current_dataset_id=current_ds.id,
        pipeline_id=current_ds.pipeline_id or baseline_ds.pipeline_id,
        status="COMPLETED",
        overall_severity=result.overall_severity,
        features_monitored=result.features_monitored,
        features_with_drift=result.features_with_drift,
        baseline_rows=result.baseline_rows,
        baseline_cols=result.baseline_cols,
        current_rows=result.current_rows,
        current_cols=result.current_cols,
        classification=result.classification,
        summary_stats=result.summary_stats,
        schema_drift_summary=result.schema_drift or {},
        null_rate_summary=result.null_rate_summary or {},
        metrics_by_algorithm=result.metrics_by_algorithm,
        created_at=result.detected_at,
    )
    db.add(det_run)
    db.flush()

    # 2. Persist Schema Changes
    if result.schema_drift:
        for cat in ("type_changes", "added_columns", "removed_columns", "null_rate_changes", "cardinality_changes"):
            for sc in result.schema_drift.get(cat, []):
                sch_change = SchemaChange(
                    dataset_id=current_ds.id,
                    detection_run_id=det_run.id,
                    change_type=sc.get("change_type", cat),
                    column_name=sc.get("column_name", ""),
                    before_value=sc.get("before"),
                    after_value=sc.get("after"),
                    severity=sc.get("severity", "MEDIUM"),
                    description=sc.get("description", ""),
                    baseline_version=baseline_ds.version,
                    current_version=current_ds.version,
                    detected_at=result.detected_at,
                )
                db.add(sch_change)

    # 3. Persist Drift Events for each feature
    persisted_events: List[DriftEvent] = []
    high_or_crit_features: List[str] = []

    for fr in result.feature_results:
        metric_name, metric_score, p_val = _extract_primary_metric(fr)
        event_id = f"{result.run_id}-{fr.feature}-{metric_name}"

        evidence: Dict[str, Any] = {}
        if fr.psi:
            evidence["psi_score"] = fr.psi.get("psi_score")
            evidence["psi_status"] = fr.psi.get("drift_status")
        if fr.kl:
            evidence["kl_score"] = fr.kl.get("kl_score")
        if fr.ks:
            evidence["ks_statistic"] = fr.ks.get("ks_statistic")
            evidence["ks_p_value"] = fr.ks.get("p_value")
            evidence["ks_stat_sig"] = fr.ks.get("statistically_significant")
        if fr.null_rate:
            evidence["null_rate_change"] = fr.null_rate.get("absolute_change")
            evidence["current_null_rate"] = fr.null_rate.get("current_null_rate")
        if fr.severity:
            evidence["severity_rule"] = fr.severity.get("primary_rule_id")
            evidence["severity_reasoning"] = fr.severity.get("reasoning")

        event = DriftEvent(
            event_id=event_id,
            dataset_id=current_ds.id,
            detection_run_id=det_run.id,
            pipeline_id=current_ds.pipeline_id or baseline_ds.pipeline_id,
            feature_name=fr.feature,
            drift_type="distribution" if fr.psi or fr.ks else "null_rate",
            metric=metric_name,
            score=metric_score,
            p_value=p_val,
            severity=fr.highest_severity,
            baseline_window={"dataset_id": str(baseline_ds.id), "name": baseline_ds.name, "version": baseline_ds.version},
            current_window={"dataset_id": str(current_ds.id), "name": current_ds.name, "version": current_ds.version},
            baseline_distribution=(fr.psi or {}).get("baseline_distribution"),
            current_distribution=(fr.psi or {}).get("current_distribution"),
            evidence=evidence,
            message=(fr.severity or {}).get("reasoning") or f"Drift evaluated for '{fr.feature}': severity {fr.highest_severity}",
            detected_at=result.detected_at,
        )
        db.add(event)
        persisted_events.append(event)

        if fr.highest_severity in ("HIGH", "CRITICAL"):
            high_or_crit_features.append(fr.feature)

    # 4. Auto-Generate Incident if High or Critical drift occurs
    created_incident = None
    if result.overall_severity in ("HIGH", "CRITICAL") or (result.schema_drift and result.schema_drift.get("overall_severity") in ("HIGH", "CRITICAL")):
        inc_id_str = f"INC-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        primary_feature = high_or_crit_features[0] if high_or_crit_features else (result.feature_results[0].feature if result.feature_results else "schema")
        
        # Determine triggering metric and score
        top_metric = "Multiple"
        top_score = 0.0
        for fr in result.feature_results:
            if fr.feature == primary_feature:
                m_name, m_score, _ = _extract_primary_metric(fr)
                top_metric = m_name
                top_score = m_score
                break

        summary_text = (
            f"Detected {result.overall_severity} drift on dataset '{current_ds.name}' "
            f"({result.features_with_drift}/{result.features_monitored} features affected: {', '.join(high_or_crit_features[:5])})."
        )
        if result.schema_drift and result.schema_drift.get("total_changes", 0) > 0:
            summary_text += f" Schema changes detected: {result.schema_drift.get('total_changes')} changes."

        created_incident = Incident(
            incident_id=inc_id_str,
            pipeline_id=current_ds.pipeline_id or baseline_ds.pipeline_id,
            title=f"{result.overall_severity} Drift Alert: {primary_feature} in {current_ds.name}",
            summary=summary_text,
            severity=result.overall_severity,
            status="OPEN",
            affected_features=high_or_crit_features,
            triggering_metric=top_metric,
            triggering_score=top_score,
            baseline_window={"dataset_id": str(baseline_ds.id), "name": baseline_ds.name, "version": baseline_ds.version},
            current_window={"dataset_id": str(current_ds.id), "name": current_ds.name, "version": current_ds.version},
            schema_changes=result.schema_drift.get("type_changes", []) if result.schema_drift else [],
            created_at=result.detected_at,
        )
        db.add(created_incident)
        db.flush()

        # Link drift events to this incident
        for ev in persisted_events:
            if ev.feature_name in high_or_crit_features:
                ev.incident_id = created_incident.id

    db.commit()
    db.refresh(det_run)

    # Serialize response
    serialized_features = [
        {
            "feature": fr.feature,
            "class": fr.feature_class,
            "psi": fr.psi,
            "kl": fr.kl,
            "ks": fr.ks,
            "null_rate": fr.null_rate,
            "severity": fr.severity,
            "drift_detected": fr.drift_detected,
            "highest_severity": fr.highest_severity,
        }
        for fr in result.feature_results
    ]

    return {
        "run_id": result.run_id,
        "detection_run_id": str(det_run.id),
        "detected_at": result.detected_at.isoformat(),
        "baseline": {
            "dataset_id": str(baseline_ds.id),
            "name": baseline_ds.name,
            "rows": result.baseline_rows,
            "cols": result.baseline_cols,
            "version": baseline_ds.version,
        },
        "current": {
            "dataset_id": str(current_ds.id),
            "name": current_ds.name,
            "rows": result.current_rows,
            "cols": result.current_cols,
            "version": current_ds.version,
        },
        "classification": result.classification,
        "features_monitored": result.features_monitored,
        "features_with_drift": result.features_with_drift,
        "overall_severity": result.overall_severity,
        "feature_results": serialized_features,
        "schema_drift": result.schema_drift,
        "null_rate_summary": result.null_rate_summary,
        "metrics_by_algorithm": result.metrics_by_algorithm,
        "summary_stats": result.summary_stats,
        "incident_generated": {
            "incident_id": created_incident.incident_id,
            "id": str(created_incident.id),
            "severity": created_incident.severity,
            "title": created_incident.title,
        } if created_incident else None,
    }


def _extract_primary_metric(fr) -> tuple:
    """Return (metric_name, score, p_val) representing the highest-impact metric."""
    candidates = []
    if fr.psi:
        candidates.append(("PSI", fr.psi["psi_score"], None, fr.psi["drift_status"]))
    if fr.kl:
        candidates.append(("KL", fr.kl["kl_score"], None, fr.kl["drift_status"]))
    if fr.ks:
        candidates.append(("KS", fr.ks["ks_statistic"], fr.ks.get("p_value"), fr.ks["drift_status"]))
    if fr.null_rate and fr.null_rate.get("severity") != "HEALTHY":
        candidates.append(("Null-Rate", fr.null_rate.get("absolute_change", 0.0), None, fr.null_rate.get("severity", "LOW")))
    if not candidates:
        return "PSI", 0.0, None
    best = max(candidates, key=lambda c: SEVERITY_RANK.get(c[3], 1))
    return best[0], best[1], best[2]


# ---------------------------------------------------------------------------
# Latest Detection Run & Feature Scores
# ---------------------------------------------------------------------------

@router.get("/latest")
def get_latest_run(db: Session = Depends(get_db)):
    """Retrieve the latest detection run from database."""
    run = db.query(DetectionRun).order_by(desc(DetectionRun.created_at)).first()
    if not run:
        return {"has_data": False, "message": "No drift detection runs have been executed yet."}

    events = db.query(DriftEvent).filter(DriftEvent.detection_run_id == run.id).all()
    features = [_serialize_event_to_feature_score(e) for e in events]

    return {
        "has_data": True,
        "run_id": run.run_id,
        "id": str(run.id),
        "created_at": run.created_at.isoformat(),
        "overall_severity": run.overall_severity,
        "features_monitored": run.features_monitored,
        "features_with_drift": run.features_with_drift,
        "baseline_rows": run.baseline_rows,
        "current_rows": run.current_rows,
        "schema_drift": run.schema_drift_summary,
        "null_rate_summary": run.null_rate_summary,
        "summary_stats": run.summary_stats,
        "features": features,
    }


@router.get("/feature-scores")
def get_feature_scores(db: Session = Depends(get_db)):
    """
    Return per-feature drift scores from the latest detection run in PostgreSQL.
    If no detection has been run, returns an empty list (NO MOCK DATA).
    """
    latest_run = db.query(DetectionRun).order_by(desc(DetectionRun.created_at)).first()
    if not latest_run:
        return {
            "has_data": False,
            "run_id": None,
            "features": [],
            "message": "No drift detection runs have been executed yet. Click '+ Run Detection' to start.",
        }

    events = db.query(DriftEvent).filter(DriftEvent.detection_run_id == latest_run.id).all()
    features = [_serialize_event_to_feature_score(e) for e in events]

    return {
        "has_data": True,
        "run_id": latest_run.run_id,
        "created_at": latest_run.created_at.isoformat(),
        "overall_severity": latest_run.overall_severity,
        "features_monitored": latest_run.features_monitored,
        "features_with_drift": latest_run.features_with_drift,
        "features": features,
    }


def _serialize_event_to_feature_score(e: DriftEvent) -> Dict[str, Any]:
    evidence = e.evidence or {}
    return {
        "feature": e.feature_name,
        "type": "numerical" if e.metric in ("KS", "PSI") else "categorical",
        "psi": evidence.get("psi_score", e.score if e.metric == "PSI" else 0.0),
        "kl": evidence.get("kl_score", e.score if e.metric == "KL" else 0.0),
        "ks_stat": evidence.get("ks_statistic", e.score if e.metric == "KS" else 0.0),
        "ks_p": evidence.get("ks_p_value", e.p_value if e.metric == "KS" else 1.0),
        "null_rate": evidence.get("null_rate_change", 0.0),
        "severity": e.severity,
        "drift_type": e.drift_type or "Distribution Drift",
        "message": e.message or "",
        "detected_at": e.detected_at.isoformat() if e.detected_at else None,
    }


# ---------------------------------------------------------------------------
# Feature Drill-Down History & Distribution
# ---------------------------------------------------------------------------

@router.get("/feature/{feature_name}/history")
def get_feature_history(feature_name: str, db: Session = Depends(get_db)):
    """
    Return real historical metric scores and latest distribution for a given feature.
    If no history exists, returns empty data without fabricating fake sine waves.
    """
    events = (
        db.query(DriftEvent)
        .filter(DriftEvent.feature_name == feature_name)
        .order_by(DriftEvent.detected_at.asc())
        .limit(50)
        .all()
    )

    if not events:
        return {
            "has_data": False,
            "feature": feature_name,
            "history": [],
            "distribution": None,
            "message": f"No historical drift records found for feature '{feature_name}'.",
        }

    latest = events[-1]
    history_points = []
    for idx, ev in enumerate(events):
        evidence = ev.evidence or {}
        history_points.append({
            "run": f"R{idx+1}",
            "timestamp": ev.detected_at.isoformat() if ev.detected_at else None,
            "PSI": evidence.get("psi_score", ev.score if ev.metric == "PSI" else 0.0),
            "KL": evidence.get("kl_score", ev.score if ev.metric == "KL" else 0.0),
            "KS": evidence.get("ks_statistic", ev.score if ev.metric == "KS" else 0.0),
            "null_rate": evidence.get("null_rate_change", 0.0),
            "severity": ev.severity,
        })

    # Build distribution comparison from latest event
    base_dist = latest.baseline_distribution or {}
    curr_dist = latest.current_distribution or {}

    bins = base_dist.get("bins") or curr_dist.get("bins") or []
    base_props = base_dist.get("proportions") or []
    curr_props = curr_dist.get("proportions") or []

    chart_data = []
    for i, b in enumerate(bins):
        chart_data.append({
            "bin": str(b),
            "Baseline": round((base_props[i] if i < len(base_props) else 0.0) * 100, 2),
            "Current": round((curr_props[i] if i < len(curr_props) else 0.0) * 100, 2),
        })

    return {
        "has_data": True,
        "feature": feature_name,
        "severity": latest.severity,
        "latest_metrics": {
            "psi": (latest.evidence or {}).get("psi_score", latest.score if latest.metric == "PSI" else 0.0),
            "kl": (latest.evidence or {}).get("kl_score", latest.score if latest.metric == "KL" else 0.0),
            "ks_stat": (latest.evidence or {}).get("ks_statistic", latest.score if latest.metric == "KS" else 0.0),
            "ks_p": (latest.evidence or {}).get("ks_p_value", latest.p_value if latest.metric == "KS" else 1.0),
            "null_rate": (latest.evidence or {}).get("null_rate_change", 0.0),
            "detected_at": latest.detected_at.isoformat() if latest.detected_at else None,
        },
        "history": history_points,
        "distribution_chart": chart_data,
    }


# ---------------------------------------------------------------------------
# Schema Monitoring
# ---------------------------------------------------------------------------

@router.get("/schema")
def get_schema_monitoring(db: Session = Depends(get_db)):
    """
    Return real schema drift comparison from the latest detection run.
    """
    latest_run = db.query(DetectionRun).order_by(desc(DetectionRun.created_at)).first()
    if not latest_run or not latest_run.schema_drift_summary:
        return {
            "has_data": False,
            "total_changes": 0,
            "added_columns": 0,
            "removed_columns": 0,
            "type_changes": 0,
            "null_rate_changes": 0,
            "cardinality_changes": 0,
            "overall_severity": "HEALTHY",
            "before_after": [],
            "change_log": [],
            "message": "No schema comparison data found. Run drift detection to analyze schema changes.",
        }

    schema_data = latest_run.schema_drift_summary
    before_cols = schema_data.get("before_columns", [])
    after_cols = schema_data.get("after_columns", [])

    # Query recent schema change records from DB
    db_changes = (
        db.query(SchemaChange)
        .filter(SchemaChange.detection_run_id == latest_run.id)
        .order_by(desc(SchemaChange.detected_at))
        .all()
    )

    change_log = [
        {
            "change_type": sc.change_type.replace("_", " ").title(),
            "column": sc.column_name,
            "before": str(sc.before_value) if sc.before_value is not None else "—",
            "after": str(sc.after_value) if sc.after_value is not None else "—",
            "severity": sc.severity,
            "detected_by": sc.detected_by,
            "detected_at": sc.detected_at.strftime("%b %d, %I:%M %p") if sc.detected_at else "",
        }
        for sc in db_changes
    ]

    # Build before/after comparison table
    all_col_names = sorted(set(before_cols) | set(after_cols))
    type_change_map = {tc["column_name"]: tc for tc in schema_data.get("type_changes", [])}
    added_set = {ac["column_name"] for ac in schema_data.get("added_columns", [])}
    removed_set = {rc["column_name"] for rc in schema_data.get("removed_columns", [])}

    before_after = []
    for c in all_col_names:
        if c in added_set:
            status = "+ Column (new)"
            b_val = "— (new)"
            a_val = "present"
        elif c in removed_set:
            status = "- Removed Column"
            b_val = "present"
            a_val = "— (removed)"
        elif c in type_change_map:
            tc = type_change_map[c]
            status = "Type Changed"
            b_val = str(tc.get("before", "unknown"))
            a_val = str(tc.get("after", "unknown"))
        else:
            status = "Unchanged"
            b_val = "aligned"
            a_val = "aligned"

        before_after.append({
            "column": c,
            "status": status,
            "before": b_val,
            "after": a_val,
            "null_rate": 0.0,
            "cardinality": 0,
        })

    return {
        "has_data": True,
        "run_id": latest_run.run_id,
        "detected_at": latest_run.created_at.isoformat(),
        "dataset_name": schema_data.get("dataset_name"),
        "baseline_version": schema_data.get("baseline_version"),
        "current_version": schema_data.get("current_version"),
        "total_changes": schema_data.get("total_changes", 0),
        "added_columns": len(schema_data.get("added_columns", [])),
        "removed_columns": len(schema_data.get("removed_columns", [])),
        "type_changes": len(schema_data.get("type_changes", [])),
        "null_rate_changes": len(schema_data.get("null_rate_changes", [])),
        "cardinality_changes": len(schema_data.get("cardinality_changes", [])),
        "overall_severity": schema_data.get("overall_severity", "HEALTHY"),
        "before_after": before_after,
        "change_log": change_log,
    }


# ---------------------------------------------------------------------------
# Incidents (100% Real from PostgreSQL)
# ---------------------------------------------------------------------------

@router.get("/incidents")
def list_incidents(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    Return actual incidents from PostgreSQL. Never substitutes fabricated mock incidents.
    """
    q = db.query(Incident)
    if status and status.lower() != "all":
        q = q.filter(Incident.status == status.upper())
    if severity and severity.lower() != "all":
        q = q.filter(Incident.severity == severity.upper())

    items = q.order_by(desc(Incident.created_at)).offset(skip).limit(limit).all()
    serialized = [drift_service.serialize_incident(i) for i in items]

    return {"items": serialized, "sample": []}


@router.get("/incidents/{incident_id}")
def get_incident(incident_id: uuid.UUID, db: Session = Depends(get_db)):
    incident = drift_service.get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found in database.")
    res = drift_service.serialize_incident(incident)
    if incident.ai_diagnosis:
        diag = incident.ai_diagnosis
        res["ai_diagnosis"] = {
            "id": str(diag.id),
            "provider": diag.provider,
            "model": diag.model,
            "most_probable_cause": diag.most_probable_cause,
            "confidence": diag.confidence,
            "observed_evidence": diag.observed_evidence,
            "hypotheses": diag.hypotheses,
            "recommendations": diag.recommendations,
            "created_at": diag.created_at.isoformat() if diag.created_at else None,
        }
    return res


@router.patch("/incidents/{incident_id}")
def update_incident(incident_id: uuid.UUID, update: IncidentUpdate, db: Session = Depends(get_db)):
    allowed_statuses = {"OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"}
    if update.status and update.status.upper() not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{update.status}'. Allowed transitions: {sorted(allowed_statuses)}",
        )
    incident = drift_service.update_incident(db, incident_id, update)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found in database.")
    return drift_service.serialize_incident(incident)


@router.get("/events")
def list_events(
    dataset_id: Optional[uuid.UUID] = None,
    pipeline_id: Optional[uuid.UUID] = None,
    feature: Optional[str] = None,
    severity: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    events = drift_service.list_drift_events(
        db,
        dataset_id=dataset_id,
        pipeline_id=pipeline_id,
        feature=feature,
        severity=severity,
        skip=skip,
        limit=limit,
    )
    return [drift_service.serialize_drift_event(e) for e in events]
