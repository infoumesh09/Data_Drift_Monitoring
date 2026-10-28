"""
AI Diagnosis API — Rule-based engine (no LLM required)

Provides deterministic, evidence-grounded root-cause analysis for drift incidents.
The engine is purely rule-based and works without any external API key.
LLM integration is a future phase once the statistical engine is validated.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid
from datetime import datetime

from ..database.session import get_db
from ..models.ai_diagnosis import AIDiagnosis
from ..models.incident import Incident
from ..models.drift_event import DriftEvent

router = APIRouter(prefix="/ai", tags=["AI Diagnosis"])

# ---------------------------------------------------------------------------
# Rule-based hypothesis engine
# ---------------------------------------------------------------------------

SEVERITY_RANK = {"CRITICAL": 5, "HIGH": 4, "MEDIUM": 3, "LOW": 2, "HEALTHY": 1, "NONE": 0}


def _build_evidence(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert raw drift metadata into structured observed evidence."""
    evidence = []

    psi = payload.get("psi_score")
    if psi is not None:
        sev = "CRITICAL" if psi >= 0.5 else "HIGH" if psi >= 0.3 else "MEDIUM" if psi >= 0.2 else "LOW"
        evidence.append({
            "metric": "PSI",
            "value": round(psi, 4),
            "severity": sev,
            "text": f"PSI = {psi:.4f} (threshold 0.20 for moderation, 0.25 for significance)",
        })

    kl = payload.get("kl_score")
    if kl is not None:
        sev = "CRITICAL" if kl >= 0.5 else "HIGH" if kl >= 0.3 else "MEDIUM" if kl >= 0.1 else "LOW"
        evidence.append({
            "metric": "KL",
            "value": round(kl, 4),
            "severity": sev,
            "text": f"KL Divergence = {kl:.4f}",
        })

    ks = payload.get("ks_statistic")
    ks_p = payload.get("ks_p_value")
    if ks is not None:
        sig = ks_p is not None and ks_p < 0.05
        sev = "CRITICAL" if ks >= 0.5 else "HIGH" if ks >= 0.3 else "MEDIUM" if ks >= 0.2 else "LOW" if ks >= 0.1 else "HEALTHY"
        evidence.append({
            "metric": "KS",
            "value": round(ks, 4),
            "severity": sev if sig else "HEALTHY",
            "text": (
                f"KS statistic = {ks:.4f}"
                + (f", p = {ks_p:.6g} ({'significant' if sig else 'not significant'})" if ks_p is not None else "")
            ),
        })

    null_change = payload.get("null_rate_change")
    if null_change is not None:
        pct = null_change * 100
        sev = "CRITICAL" if null_change >= 0.25 else "HIGH" if null_change >= 0.10 else "MEDIUM" if null_change >= 0.03 else "LOW"
        evidence.append({
            "metric": "Null Rate",
            "value": round(null_change, 4),
            "severity": sev,
            "text": f"Null-rate change of +{pct:.1f}pp detected",
        })

    schema_sev = payload.get("schema_change_severity")
    if schema_sev and schema_sev != "HEALTHY":
        schema_type = payload.get("schema_change_type", "unknown")
        evidence.append({
            "metric": "Schema",
            "value": schema_sev,
            "severity": schema_sev,
            "text": f"Schema change detected ({schema_type}): severity {schema_sev}",
        })

    baseline_null = payload.get("baseline_null_rate")
    current_null = payload.get("current_null_rate")
    if baseline_null is not None and current_null is not None and abs(current_null - baseline_null) > 0.02:
        delta = current_null - baseline_null
        evidence.append({
            "metric": "Null Rate Trend",
            "value": round(delta, 4),
            "severity": "HIGH" if abs(delta) > 0.10 else "MEDIUM",
            "text": f"Null rate shifted from {baseline_null*100:.1f}% → {current_null*100:.1f}%",
        })

    historical_freq = payload.get("historical_incident_count", 0)
    if historical_freq >= 3:
        evidence.append({
            "metric": "Historical Pattern",
            "value": historical_freq,
            "severity": "MEDIUM",
            "text": f"{historical_freq} related incidents on this pipeline in the past",
        })

    return evidence


def _rank_hypotheses(evidence: List[Dict[str, Any]], payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Deterministic rule-based hypothesis ranking."""
    hypotheses = []

    has_schema = any(e["metric"] == "Schema" for e in evidence)
    has_null_spike = any(e["metric"] == "Null Rate" and SEVERITY_RANK.get(e["severity"], 0) >= 3 for e in evidence)
    has_dist_drift = any(e["metric"] in ("PSI", "KL") and SEVERITY_RANK.get(e["severity"], 0) >= 3 for e in evidence)
    has_ks_sig = any(e["metric"] == "KS" and e["severity"] != "HEALTHY" for e in evidence)
    has_historical = any(e["metric"] == "Historical Pattern" for e in evidence)

    # Hypothesis 1: Schema / transformation change (if schema change + null spike)
    if has_schema and has_null_spike:
        hypotheses.append({
            "rank": 1,
            "title": "Upstream schema or transformation change",
            "confidence": 0.92,
            "severity": "CRITICAL",
            "reasoning": (
                "Schema change co-occurring with a null-rate spike strongly suggests a breaking "
                "upstream data transformation (e.g., type coercion or column rename). "
                "The data type change likely causes numeric aggregations to return NaN."
            ),
        })
    elif has_schema:
        hypotheses.append({
            "rank": 1,
            "title": "Schema change in upstream pipeline",
            "confidence": 0.80,
            "severity": "HIGH",
            "reasoning": (
                "Schema change detected. Column removal, type change, or rename could be "
                "caused by a deployment or ETL modification upstream."
            ),
        })

    # Hypothesis 2: Data quality / corrupt batch
    if has_null_spike and has_dist_drift:
        conf = 0.70 if not has_schema else 0.55
        hypotheses.append({
            "rank": len(hypotheses) + 1,
            "title": "Corrupt or incomplete upstream batch",
            "confidence": conf,
            "severity": "HIGH",
            "reasoning": (
                "Concurrent distribution drift and null-rate spike is consistent with a "
                "batch processing failure, partial load, or source-side data quality issue."
            ),
        })

    # Hypothesis 3: Seasonal / business behavior change
    if has_dist_drift and not has_schema and not has_null_spike:
        conf = 0.65 if not has_historical else 0.75
        hypotheses.append({
            "rank": len(hypotheses) + 1,
            "title": "Genuine business or behavioral change",
            "confidence": conf,
            "severity": "MEDIUM",
            "reasoning": (
                "Distribution drift without schema or null-rate anomaly suggests the underlying "
                "population has genuinely shifted (seasonal effect, campaign, market change)."
            ),
        })

    # Hypothesis 4: Model / feature engineering change
    if has_ks_sig and has_dist_drift:
        hypotheses.append({
            "rank": len(hypotheses) + 1,
            "title": "Feature engineering or preprocessing change",
            "confidence": 0.45,
            "severity": "MEDIUM",
            "reasoning": (
                "KS test detects a distributional shift in the ECDF shape, which can be caused "
                "by changes in normalization, encoding, or feature computation logic."
            ),
        })

    # Hypothesis 5: Sampling bias
    if has_dist_drift and not has_schema:
        hypotheses.append({
            "rank": len(hypotheses) + 1,
            "title": "Sampling bias or pipeline filtering change",
            "confidence": 0.30,
            "severity": "LOW",
            "reasoning": (
                "A change in upstream filtering, data source routing, or sampling strategy "
                "can shift distributions without any explicit code change."
            ),
        })

    # Default if nothing detected
    if not hypotheses:
        hypotheses.append({
            "rank": 1,
            "title": "Insufficient evidence for specific root cause",
            "confidence": 0.20,
            "severity": "LOW",
            "reasoning": "No dominant drift signal detected. Continue monitoring.",
        })

    # Sort by confidence descending
    hypotheses.sort(key=lambda h: h["confidence"], reverse=True)
    for i, h in enumerate(hypotheses):
        h["rank"] = i + 1

    return hypotheses


def _build_recommendations(hypotheses: List[Dict[str, Any]], evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deterministic recommendations based on hypotheses and evidence."""
    recs = []
    severities = {e["metric"]: e["severity"] for e in evidence}
    top_hyp = hypotheses[0]["title"] if hypotheses else ""

    if "Schema" in severities:
        recs.append({
            "priority": "CRITICAL",
            "title": "Investigate upstream transformation",
            "body": "Review the ETL/ELT deployment deployed nearest to the incident timestamp. Look for type coercions, column renames, or removals.",
        })

    if "Null Rate" in severities and SEVERITY_RANK.get(severities["Null Rate"], 0) >= 3:
        recs.append({
            "priority": "HIGH",
            "title": "Validate the affected batch",
            "body": "Re-run profiling on the affected time window. Quarantine the batch if corruption or high null-rate is confirmed.",
        })
        recs.append({
            "priority": "HIGH",
            "title": "Quarantine affected data in the warehouse",
            "body": "Flag the current dataset version until reprocessed. Prevent downstream models from consuming corrupt data.",
        })

    if "PSI" in severities or "KL" in severities:
        recs.append({
            "priority": "MEDIUM",
            "title": "Reprocess affected data from source",
            "body": "If source data is available, replay records through the corrected pipeline to rebuild a clean current window.",
        })

    if "Historical Pattern" in severities:
        recs.append({
            "priority": "MEDIUM",
            "title": "Review historical incident pattern",
            "body": "This pipeline has repeated drift incidents. Consider adding schema contract tests and automated alerting.",
        })

    recs.append({
        "priority": "LOW",
        "title": "Add schema contract tests",
        "body": "Add data contract assertions to the pipeline to break the build when unexpected type or column changes occur.",
    })

    recs.append({
        "priority": "LOW",
        "title": "Set drift thresholds and alerting",
        "body": "Configure PSI ≥ 0.25 and KL ≥ 0.30 as hard alerts in your monitoring pipeline to catch future incidents earlier.",
    })

    return recs


def _run_diagnosis(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Full rule-based diagnosis — pure Python, no external calls."""
    evidence = _build_evidence(payload)
    hypotheses = _rank_hypotheses(evidence, payload)
    recommendations = _build_recommendations(hypotheses, evidence)

    most_probable = hypotheses[0]["title"] if hypotheses else "Unknown"
    confidence = hypotheses[0]["confidence"] if hypotheses else 0.0

    return {
        "provider": "rule_engine_v1",
        "model": "deterministic_rules",
        "most_probable_cause": most_probable,
        "confidence": confidence,
        "observed_evidence": [
            {"text": e["text"], "severity": e["severity"], "metric": e["metric"]}
            for e in evidence
        ],
        "hypotheses": hypotheses,
        "recommendations": recommendations,
        "evidence_summary": (
            f"{len(evidence)} evidence item(s) analyzed. "
            f"Top hypothesis: '{most_probable}' ({int(confidence * 100)}% confidence)."
        ),
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/status")
def ai_status() -> Dict[str, Any]:
    return {
        "provider": "rule_engine_v1",
        "status": "AVAILABLE",
        "mode": "rule_based",
        "message": (
            "Rule-based AI diagnosis is active. No external API key required. "
            "Diagnosis uses deterministic PSI/KL/KS/null-rate/schema-change rules. "
            "LLM integration (OpenAI, Anthropic, Ollama) is reserved for a future phase."
        ),
        "capabilities": [
            "observed_evidence extraction",
            "hypothesis ranking by confidence",
            "prioritized recommendations",
            "incident DB persistence",
        ],
    }


@router.post("/diagnose")
def diagnose(payload: Dict[str, Any], db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Run rule-based diagnosis on structured drift metadata.

    Expected payload fields (all optional):
      - feature: str
      - psi_score: float
      - kl_score: float
      - ks_statistic: float
      - ks_p_value: float
      - null_rate_change: float          (absolute change, e.g. 0.20)
      - baseline_null_rate: float
      - current_null_rate: float
      - schema_change_severity: str      (CRITICAL | HIGH | MEDIUM | LOW)
      - schema_change_type: str
      - historical_incident_count: int
      - incident_id: str                 (UUID, optional — links to DB incident)
    """
    incident_id_str = payload.get("incident_id")
    incident = None
    if incident_id_str:
        try:
            incident_uuid = uuid.UUID(str(incident_id_str))
            incident = db.query(Incident).filter(Incident.id == incident_uuid).first()
        except (ValueError, AttributeError):
            incident = db.query(Incident).filter(Incident.incident_id == str(incident_id_str)).first()
        if not incident:
            incident = db.query(Incident).filter(Incident.incident_id == str(incident_id_str)).first()

        if incident:
            # Hydrate payload from incident if not explicitly given
            if not payload.get("feature") and incident.affected_features:
                payload["feature"] = incident.affected_features[0]

                # Hydrate from linked drift events
                events = db.query(DriftEvent).filter(DriftEvent.incident_id == incident.id).all()
                for ev in events:
                    ev_data = ev.evidence or {}
                    if "psi_score" not in payload and "psi_score" in ev_data:
                        payload["psi_score"] = ev_data["psi_score"]
                    if "kl_score" not in payload and "kl_score" in ev_data:
                        payload["kl_score"] = ev_data["kl_score"]
                    if "ks_statistic" not in payload and "ks_statistic" in ev_data:
                        payload["ks_statistic"] = ev_data["ks_statistic"]
                    if "ks_p_value" not in payload and "ks_p_value" in ev_data:
                        payload["ks_p_value"] = ev_data["ks_p_value"]
                    if "null_rate_change" not in payload and "null_rate_change" in ev_data:
                        payload["null_rate_change"] = ev_data["null_rate_change"]

                if incident.schema_changes and not payload.get("schema_change_severity"):
                    payload["schema_change_severity"] = incident.severity
                    payload["schema_change_type"] = "Schema alteration"

                # Historical incident count
                hist_count = (
                    db.query(Incident)
                    .filter(Incident.pipeline_id == incident.pipeline_id, Incident.id != incident.id)
                    .count()
                )
                payload["historical_incident_count"] = hist_count

    diagnosis = _run_diagnosis(payload)

    # Persist to DB if incident was found
    if incident:
        existing = db.query(AIDiagnosis).filter(AIDiagnosis.incident_id == incident.id).first()
        if existing:
            db.delete(existing)
            db.flush()

        diag_record = AIDiagnosis(
            incident_id=incident.id,
            provider="rule_engine_v1",
            model="deterministic_expert_rules",
            most_probable_cause=diagnosis["most_probable_cause"],
            confidence=diagnosis["confidence"],
            observed_evidence=diagnosis["observed_evidence"],
            hypotheses=diagnosis["hypotheses"],
            recommendations=diagnosis["recommendations"],
            evidence_summary=diagnosis["evidence_summary"],
            raw_response={"input_payload": payload},
        )
        db.add(diag_record)
        db.commit()
        db.refresh(diag_record)
        diagnosis["db_id"] = str(diag_record.id)

    return diagnosis


@router.get("/diagnoses")
def list_diagnoses(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """List stored AI diagnosis records."""
    rows = db.query(AIDiagnosis).order_by(AIDiagnosis.created_at.desc()).offset(skip).limit(limit).all()
    return {
        "items": [
            {
                "id": str(r.id),
                "incident_id": str(r.incident_id),
                "provider": r.provider,
                "most_probable_cause": r.most_probable_cause,
                "confidence": r.confidence,
                "evidence_summary": r.evidence_summary,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
        "total": db.query(AIDiagnosis).count(),
    }


@router.get("/diagnoses/{diagnosis_id}")
def get_diagnosis(diagnosis_id: uuid.UUID, db: Session = Depends(get_db)) -> Dict[str, Any]:
    diag = db.query(AIDiagnosis).filter(AIDiagnosis.id == diagnosis_id).first()
    if not diag:
        raise HTTPException(status_code=404, detail="Diagnosis not found")
    return {
        "id": str(diag.id),
        "incident_id": str(diag.incident_id),
        "provider": diag.provider,
        "model": diag.model,
        "most_probable_cause": diag.most_probable_cause,
        "confidence": diag.confidence,
        "observed_evidence": diag.observed_evidence,
        "hypotheses": diag.hypotheses,
        "recommendations": diag.recommendations,
        "evidence_summary": diag.evidence_summary,
        "created_at": diag.created_at.isoformat() if diag.created_at else None,
    }
