"""
Explainable Severity Engine

Maps individual statistical signals (PSI, KL, KS, Null-Rate, Schema changes)
into an interpretable severity level:
    CRITICAL - Action required immediately (e.g. model predictions corrupted)
    HIGH     - Significant drift detected across multiple metrics or large magnitude
    MEDIUM   - Moderate distribution shift; monitor or schedule retraining
    LOW      - Subtle variation within tolerable boundaries
    HEALTHY  - Normal statistical noise; no actionable shift

Design Principles:
    - Never blindly sum or average raw scores (PSI, KL, KS are on different scales).
    - Map each metric to a normalized severity grade using clear threshold boundaries.
    - Evaluate deterministic rule conditions in priority order with explicit Rule IDs.
    - Keep effect magnitude (PSI / KS D) primary; treat p-value as statistical gatekeeper.
    - Provide transparent explanation: rule ID, triggering metric, score, and threshold.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


SEVERITY_RANK = {"CRITICAL": 5, "HIGH": 4, "MEDIUM": 3, "LOW": 2, "HEALTHY": 1}
REVERSE_RANK = {v: k for k, v in SEVERITY_RANK.items()}


@dataclass
class SeverityEvidence:
    rule_id: str
    metric: str
    observed_value: Any
    threshold: Any
    severity: str
    description: str


@dataclass
class SeverityResult:
    overall_severity: str          # HEALTHY | LOW | MEDIUM | HIGH | CRITICAL
    primary_rule_id: str
    triggering_metric: str
    triggering_score: float
    max_component_severity: str
    num_affected_components: int
    evidence: List[SeverityEvidence] = field(default_factory=list)
    reasoning: str = ""


def calculate_severity(
    psi_score: Optional[float] = None,
    kl_score: Optional[float] = None,
    ks_statistic: Optional[float] = None,
    ks_p_value: Optional[float] = None,
    ks_significance_level: float = 0.05,
    null_rate_abs_change: Optional[float] = None,
    schema_change_severity: Optional[str] = None,
    feature_name: Optional[str] = None,
) -> SeverityResult:
    """
    Evaluate all observed signals for a feature and assign an explainable severity verdict.
    """
    evidence_list: List[SeverityEvidence] = []
    component_sevs: Dict[str, str] = {}

    # 1. Evaluate Schema Change
    if schema_change_severity and schema_change_severity != "HEALTHY":
        component_sevs["schema"] = schema_change_severity
        evidence_list.append(
            SeverityEvidence(
                rule_id="RULE-SCHEMA",
                metric="Schema",
                observed_value=schema_change_severity,
                threshold="HEALTHY",
                severity=schema_change_severity,
                description=f"Schema alteration detected with severity {schema_change_severity}.",
            )
        )

    # 2. Evaluate Null-Rate Change
    if null_rate_abs_change is not None:
        if null_rate_abs_change >= 0.25:
            sev = "CRITICAL"
        elif null_rate_abs_change >= 0.15:
            sev = "HIGH"
        elif null_rate_abs_change >= 0.05:
            sev = "MEDIUM"
        elif null_rate_abs_change >= 0.01:
            sev = "LOW"
        else:
            sev = "HEALTHY"
        component_sevs["null_rate"] = sev
        if sev != "HEALTHY":
            evidence_list.append(
                SeverityEvidence(
                    rule_id="RULE-NULL",
                    metric="Null-Rate",
                    observed_value=round(null_rate_abs_change, 4),
                    threshold=0.05,
                    severity=sev,
                    description=f"Missingness changed by {null_rate_abs_change*100:.2f} percentage points.",
                )
            )

    # 3. Evaluate PSI
    if psi_score is not None:
        if psi_score >= 0.50:
            sev = "CRITICAL"
        elif psi_score >= 0.25:
            sev = "HIGH"
        elif psi_score >= 0.20:
            sev = "MEDIUM"
        elif psi_score >= 0.10:
            sev = "LOW"
        else:
            sev = "HEALTHY"
        component_sevs["psi"] = sev
        if sev != "HEALTHY":
            evidence_list.append(
                SeverityEvidence(
                    rule_id="RULE-PSI",
                    metric="PSI",
                    observed_value=round(psi_score, 4),
                    threshold=0.25,
                    severity=sev,
                    description=f"Population Stability Index = {psi_score:.4f}.",
                )
            )

    # 4. Evaluate KL Divergence
    if kl_score is not None:
        if kl_score >= 1.00:
            sev = "CRITICAL"
        elif kl_score >= 0.50:
            sev = "HIGH"
        elif kl_score >= 0.25:
            sev = "MEDIUM"
        elif kl_score >= 0.10:
            sev = "LOW"
        else:
            sev = "HEALTHY"
        component_sevs["kl"] = sev
        if sev != "HEALTHY":
            evidence_list.append(
                SeverityEvidence(
                    rule_id="RULE-KL",
                    metric="KL",
                    observed_value=round(kl_score, 4),
                    threshold=0.50,
                    severity=sev,
                    description=f"KL divergence = {kl_score:.4f}.",
                )
            )

    # 5. Evaluate KS Test (D-statistic + p-value)
    if ks_statistic is not None:
        ks_sig = (ks_p_value is not None) and (ks_p_value < ks_significance_level)
        if not ks_sig or ks_statistic < 0.10:
            sev = "HEALTHY"
        elif ks_statistic >= 0.50:
            sev = "CRITICAL"
        elif ks_statistic >= 0.30:
            sev = "HIGH"
        elif ks_statistic >= 0.20:
            sev = "MEDIUM"
        else:
            sev = "LOW"
        component_sevs["ks"] = sev
        if sev != "HEALTHY":
            evidence_list.append(
                SeverityEvidence(
                    rule_id="RULE-KS",
                    metric="KS",
                    observed_value=round(ks_statistic, 4),
                    threshold=0.20,
                    severity=sev,
                    description=f"KS statistic D={ks_statistic:.4f} (p={ks_p_value:.3e}, significant).",
                )
            )

    # Count affected non-healthy components
    affected_components = [k for k, v in component_sevs.items() if v != "HEALTHY"]
    num_affected = len(affected_components)

    # Determine highest component severity
    if component_sevs:
        max_sev = max(component_sevs.values(), key=lambda s: SEVERITY_RANK.get(s, 1))
    else:
        max_sev = "HEALTHY"

    # Priority Rule Engine Mapping
    primary_rule_id = "RULE-HEALTHY"
    triggering_metric = "None"
    triggering_score = 0.0
    overall_sev = "HEALTHY"
    reasoning = "All monitored metrics are within acceptable thresholds."

    # Rule 1: Breaking Schema Change -> CRITICAL
    if component_sevs.get("schema") == "CRITICAL":
        overall_sev = "CRITICAL"
        primary_rule_id = "RULE-CRIT-SCHEMA"
        triggering_metric = "Schema"
        triggering_score = 1.0
        reasoning = "Critical schema alteration detected (breaking datatype coercion or column deletion)."

    # Rule 2: Extreme Distribution or Null Shift -> CRITICAL
    elif max_sev == "CRITICAL":
        overall_sev = "CRITICAL"
        if component_sevs.get("null_rate") == "CRITICAL":
            primary_rule_id = "RULE-CRIT-NULL"
            triggering_metric = "Null-Rate"
            triggering_score = null_rate_abs_change or 0.0
            reasoning = f"Severe missingness spike of {triggering_score*100:.1f}pp exceeds critical threshold."
        elif component_sevs.get("psi") == "CRITICAL":
            primary_rule_id = "RULE-CRIT-PSI"
            triggering_metric = "PSI"
            triggering_score = psi_score or 0.0
            reasoning = f"PSI={triggering_score:.4f} exceeds critical stability threshold (0.50)."
        else:
            primary_rule_id = "RULE-CRIT-EXTREME"
            triggering_metric = "KS" if component_sevs.get("ks") == "CRITICAL" else "KL"
            triggering_score = ks_statistic if triggering_metric == "KS" else (kl_score or 0.0)
            reasoning = f"Metric {triggering_metric} reached critical divergence level ({triggering_score:.4f})."

    # Rule 3: Multi-detector consensus High Drift -> HIGH
    elif num_affected >= 2 and any(component_sevs.get(m) in ("HIGH", "MEDIUM") for m in ("psi", "ks", "null_rate")):
        overall_sev = "HIGH"
        primary_rule_id = "RULE-HIGH-CONSENSUS"
        triggering_metric = "Multiple"
        triggering_score = psi_score if psi_score is not None else (ks_statistic or 0.0)
        reasoning = f"Multiple independent detectors ({', '.join(affected_components)}) confirm significant drift."

    # Rule 4: Single detector High Severity -> HIGH
    elif max_sev == "HIGH":
        overall_sev = "HIGH"
        if component_sevs.get("psi") == "HIGH":
            primary_rule_id = "RULE-HIGH-PSI"
            triggering_metric = "PSI"
            triggering_score = psi_score or 0.0
        elif component_sevs.get("ks") == "HIGH":
            primary_rule_id = "RULE-HIGH-KS"
            triggering_metric = "KS"
            triggering_score = ks_statistic or 0.0
        elif component_sevs.get("null_rate") == "HIGH":
            primary_rule_id = "RULE-HIGH-NULL"
            triggering_metric = "Null-Rate"
            triggering_score = null_rate_abs_change or 0.0
        else:
            primary_rule_id = "RULE-HIGH-METRIC"
            triggering_metric = "KL"
            triggering_score = kl_score or 0.0
        reasoning = f"{triggering_metric} reached high severity threshold ({triggering_score:.4f})."

    # Rule 5: Medium Severity -> MEDIUM
    elif max_sev == "MEDIUM":
        overall_sev = "MEDIUM"
        primary_rule_id = "RULE-MED-DRIFT"
        triggering_metric = next((k.upper() for k, v in component_sevs.items() if v == "MEDIUM"), "Drift")
        triggering_score = psi_score or ks_statistic or kl_score or (null_rate_abs_change or 0.0)
        reasoning = f"Moderate distribution movement observed in {triggering_metric}."

    # Rule 6: Low Severity -> LOW
    elif max_sev == "LOW":
        overall_sev = "LOW"
        primary_rule_id = "RULE-LOW-DRIFT"
        triggering_metric = next((k.upper() for k, v in component_sevs.items() if v == "LOW"), "Drift")
        triggering_score = psi_score or ks_statistic or kl_score or (null_rate_abs_change or 0.0)
        reasoning = f"Minor statistical variation detected in {triggering_metric}."

    return SeverityResult(
        overall_severity=overall_sev,
        primary_rule_id=primary_rule_id,
        triggering_metric=triggering_metric,
        triggering_score=round(float(triggering_score), 4),
        max_component_severity=max_sev,
        num_affected_components=num_affected,
        evidence=evidence_list,
        reasoning=reasoning,
    )
