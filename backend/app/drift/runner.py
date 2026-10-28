"""
Unified Drift Detection Runner

Orchestrates multi-algorithm drift detection (PSI, KL, KS, Schema Drift, Null-Rate)
on a reference baseline vs. current production DataFrame pair.
Includes Benjamini-Hochberg False Discovery Rate (FDR) multiple-testing correction
for the KS test p-values.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import numpy as np
import pandas as pd

from .psi import calculate_psi
from .kl_divergence import calculate_kl_divergence
from .ks_test import run_ks_test
from .schema_drift import detect_schema_drift
from .null_monitor import monitor_null_rates
from .severity import calculate_severity, SEVERITY_RANK
from .preprocessing import (
    classify_dataframe,
    FEATURE_CLASS_NUMERICAL,
    FEATURE_CLASS_CATEGORICAL,
    FEATURE_CLASS_UNSUPPORTED,
)


@dataclass
class FeatureDriftResult:
    feature: str
    feature_class: str
    psi: Optional[Dict[str, Any]] = None
    kl: Optional[Dict[str, Any]] = None
    ks: Optional[Dict[str, Any]] = None
    null_rate: Optional[Dict[str, Any]] = None
    severity: Optional[Dict[str, Any]] = None
    drift_detected: bool = False
    highest_severity: str = "HEALTHY"


@dataclass
class DriftRunResult:
    run_id: str
    detected_at: datetime
    baseline_rows: int
    baseline_cols: int
    current_rows: int
    current_cols: int
    classification: Dict[str, str] = field(default_factory=dict)
    feature_results: List[FeatureDriftResult] = field(default_factory=list)
    schema_drift: Optional[Dict[str, Any]] = None
    null_rate_summary: Optional[Dict[str, Any]] = None
    features_monitored: int = 0
    features_with_drift: int = 0
    overall_severity: str = "HEALTHY"
    metrics_by_algorithm: Dict[str, Any] = field(default_factory=dict)
    summary_stats: Dict[str, Any] = field(default_factory=dict)


def _apply_fdr_correction(p_values: List[float]) -> List[float]:
    """
    Benjamini-Hochberg (FDR) multiple-testing adjustment.
    """
    m = len(p_values)
    if m <= 1:
        return p_values

    # Pair with original index and sort by p-value ascending
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    adjusted = [0.0] * m

    # Step-up procedure: p_adj(i) = min(1, p(i) * m / rank)
    cum_min = 1.0
    for rank in range(m, 0, -1):
        idx, p = indexed[rank - 1]
        val = min(1.0, (p * m) / rank)
        cum_min = min(cum_min, val)
        adjusted[idx] = round(cum_min, 8)

    return adjusted


def run_drift_detection(
    baseline_df: pd.DataFrame,
    current_df: pd.DataFrame,
    features: Optional[List[str]] = None,
    run_psi: bool = True,
    run_kl: bool = True,
    run_ks: bool = True,
    run_schema: bool = True,
    run_null_rate: bool = True,
    thresholds: Optional[Dict[str, Any]] = None,
    dataset_name: Optional[str] = None,
    baseline_version: Optional[str] = None,
    current_version: Optional[str] = None,
) -> DriftRunResult:
    """
    Run complete, multi-algorithm drift analysis on baseline and current dataframes.
    """
    thresholds = thresholds or {}
    run_id = "DRUN-" + datetime.utcnow().strftime("%Y%m%d-") + uuid.uuid4().hex[:8].upper()

    # Determine schema & column types
    combined_sample = pd.concat([baseline_df.head(500), current_df.head(500)])
    classification = classify_dataframe(combined_sample)

    if features is None:
        common_cols = [c for c in baseline_df.columns if c in current_df.columns]
    else:
        common_cols = [c for c in features if c in baseline_df.columns and c in current_df.columns]

    # Filter to supported feature types (numerical and categorical)
    monitored_cols = [
        c for c in common_cols
        if classification.get(c) in (FEATURE_CLASS_NUMERICAL, FEATURE_CLASS_CATEGORICAL)
    ]

    result = DriftRunResult(
        run_id=run_id,
        detected_at=datetime.utcnow(),
        baseline_rows=len(baseline_df),
        baseline_cols=len(baseline_df.columns),
        current_rows=len(current_df),
        current_cols=len(current_df.columns),
        classification=classification,
        features_monitored=len(monitored_cols),
    )

    # 1. Run Schema Drift
    if run_schema:
        schema_res = detect_schema_drift(
            baseline_df, current_df, dataset_name, baseline_version, current_version
        )
        result.schema_drift = {
            "dataset_name": schema_res.dataset_name,
            "baseline_version": schema_res.baseline_version,
            "current_version": schema_res.current_version,
            "added_columns": [
                {
                    "column_name": d.column_name,
                    "change_type": d.change_type,
                    "before": d.before_value,
                    "after": d.after_value,
                    "severity": d.severity,
                    "description": d.description,
                }
                for d in schema_res.added_columns
            ],
            "removed_columns": [
                {
                    "column_name": d.column_name,
                    "change_type": d.change_type,
                    "before": d.before_value,
                    "after": d.after_value,
                    "severity": d.severity,
                    "description": d.description,
                }
                for d in schema_res.removed_columns
            ],
            "type_changes": [
                {
                    "column_name": d.column_name,
                    "change_type": d.change_type,
                    "before": d.before_value,
                    "after": d.after_value,
                    "severity": d.severity,
                    "description": d.description,
                }
                for d in schema_res.type_changes
            ],
            "null_rate_changes": [
                {
                    "column_name": d.column_name,
                    "change_type": d.change_type,
                    "before": d.before_value,
                    "after": d.after_value,
                    "severity": d.severity,
                    "description": d.description,
                }
                for d in schema_res.null_rate_changes
            ],
            "cardinality_changes": [
                {
                    "column_name": d.column_name,
                    "change_type": d.change_type,
                    "before": d.before_value,
                    "after": d.after_value,
                    "severity": d.severity,
                    "description": d.description,
                }
                for d in schema_res.cardinality_changes
            ],
            "total_changes": schema_res.total_changes,
            "overall_severity": schema_res.overall_severity,
            "before_columns": sorted(schema_res.before_schema.keys()),
            "after_columns": sorted(schema_res.after_schema.keys()),
            "detected_at": schema_res.detected_at.isoformat(),
        }

    # 2. Run Null-Rate Monitoring
    null_summary_map: Dict[str, Any] = {}
    if run_null_rate:
        null_res = monitor_null_rates(
            baseline_df, current_df, features=monitored_cols, thresholds=thresholds.get("null_rate")
        )
        for nr in null_res.results:
            null_summary_map[nr.feature] = {
                "baseline_null_rate": nr.baseline_null_rate,
                "current_null_rate": nr.current_null_rate,
                "delta_null_rate": nr.delta_null_rate,
                "absolute_change": nr.absolute_change,
                "relative_change": nr.relative_change,
                "severity": nr.severity,
                "drift_detected": nr.drift_detected,
                "baseline_null_count": nr.baseline_null_count,
                "current_null_count": nr.current_null_count,
                "baseline_total": nr.baseline_total,
                "current_total": nr.current_total,
                "direction": nr.direction,
                "message": nr.message,
            }
        result.null_rate_summary = {
            "overall_severity": null_res.overall_severity,
            "features_with_drift": null_res.features_with_drift,
            "total_features": null_res.total_features,
            "detected_at": null_res.detected_at.isoformat(),
        }

    # 3. Calculate per-feature drift metrics
    algorithm_metrics = {
        "psi": {"total": 0, "drift": 0},
        "kl": {"total": 0, "drift": 0},
        "ks": {"total": 0, "drift": 0},
    }

    # Collect KS p-values for FDR adjustment
    numeric_ks_results: Dict[str, Any] = {}
    ks_raw_pvals: List[float] = []
    ks_features: List[str] = []

    for col in monitored_cols:
        fc = classification.get(col, FEATURE_CLASS_UNSUPPORTED)
        is_numeric = fc == FEATURE_CLASS_NUMERICAL

        if run_ks and is_numeric:
            ks_res = run_ks_test(
                baseline_df[col],
                current_df[col],
                feature=col,
                feature_type=fc,
                significance_level=thresholds.get("ks_significance", 0.05),
                config=thresholds.get("ks"),
            )
            numeric_ks_results[col] = ks_res
            ks_raw_pvals.append(ks_res.p_value)
            ks_features.append(col)

    # Apply FDR correction across KS tests
    if ks_raw_pvals:
        adj_pvals = _apply_fdr_correction(ks_raw_pvals)
        for col, adj_p in zip(ks_features, adj_pvals):
            numeric_ks_results[col].adjusted_p_value = adj_p
            # Check significance with adjusted p-value
            alpha = numeric_ks_results[col].significance_level
            numeric_ks_results[col].statistically_significant = bool(adj_p < alpha)

    # Iterate through all monitored features
    for col in monitored_cols:
        fc = classification.get(col, FEATURE_CLASS_UNSUPPORTED)
        is_numeric = fc == FEATURE_CLASS_NUMERICAL
        is_categorical = fc == FEATURE_CLASS_CATEGORICAL

        fr = FeatureDriftResult(feature=col, feature_class=fc)

        # PSI
        if run_psi and (is_numeric or is_categorical):
            psi_res = calculate_psi(
                baseline_df[col],
                current_df[col],
                feature=col,
                feature_type=fc,
                thresholds=thresholds.get("psi"),
            )
            fr.psi = {
                "psi_score": psi_res.psi_score,
                "threshold": psi_res.threshold,
                "drift_status": psi_res.drift_status,
                "feature_type": psi_res.feature_type,
                "baseline_distribution": psi_res.baseline_distribution,
                "current_distribution": psi_res.current_distribution,
                "bins": psi_res.bins,
                "per_bin_psi": psi_res.per_bin_psi,
                "message": psi_res.message,
            }
            algorithm_metrics["psi"]["total"] += 1
            if psi_res.drift_status != "HEALTHY":
                algorithm_metrics["psi"]["drift"] += 1

        # KL
        if run_kl and (is_numeric or is_categorical):
            kl_res = calculate_kl_divergence(
                baseline_df[col],
                current_df[col],
                feature=col,
                feature_type=fc,
                thresholds=thresholds.get("kl"),
            )
            fr.kl = {
                "kl_score": kl_res.kl_score,
                "threshold": kl_res.threshold,
                "drift_status": kl_res.drift_status,
                "feature_type": kl_res.feature_type,
                "direction": kl_res.direction,
                "baseline_distribution": kl_res.baseline_distribution,
                "current_distribution": kl_res.current_distribution,
                "message": kl_res.message,
            }
            algorithm_metrics["kl"]["total"] += 1
            if kl_res.drift_status != "HEALTHY":
                algorithm_metrics["kl"]["drift"] += 1

        # KS
        if run_ks and is_numeric and col in numeric_ks_results:
            ks_res = numeric_ks_results[col]
            fr.ks = {
                "ks_statistic": ks_res.ks_statistic,
                "p_value": ks_res.p_value,
                "adjusted_p_value": ks_res.adjusted_p_value,
                "significance_level": ks_res.significance_level,
                "statistically_significant": ks_res.statistically_significant,
                "drift_status": ks_res.drift_status,
                "severity_threshold": ks_res.severity_threshold,
                "baseline_n": ks_res.baseline_n,
                "current_n": ks_res.current_n,
                "baseline_ecdf": ks_res.baseline_ecdf,
                "current_ecdf": ks_res.current_ecdf,
                "message": ks_res.message,
            }
            algorithm_metrics["ks"]["total"] += 1
            if ks_res.drift_status != "HEALTHY":
                algorithm_metrics["ks"]["drift"] += 1

        # Null rate
        nr_info = null_summary_map.get(col)
        if nr_info is not None:
            fr.null_rate = nr_info

        # Schema changes affecting this specific feature
        schema_component_sev = "HEALTHY"
        if result.schema_drift:
            col_changes = [
                *[c for c in result.schema_drift["type_changes"] if c["column_name"] == col],
                *[c for c in result.schema_drift["null_rate_changes"] if c["column_name"] == col],
                *[c for c in result.schema_drift["cardinality_changes"] if c["column_name"] == col],
            ]
            if col_changes:
                schema_component_sev = max(
                    (c["severity"] for c in col_changes),
                    key=lambda s: SEVERITY_RANK.get(s, 1),
                )

        # Calculate explainable severity
        sev_res = calculate_severity(
            psi_score=fr.psi["psi_score"] if fr.psi else None,
            kl_score=fr.kl["kl_score"] if fr.kl else None,
            ks_statistic=fr.ks["ks_statistic"] if fr.ks else None,
            ks_p_value=fr.ks["p_value"] if fr.ks else None,
            null_rate_abs_change=fr.null_rate["absolute_change"] if fr.null_rate else None,
            schema_change_severity=None if schema_component_sev == "HEALTHY" else schema_component_sev,
            feature_name=col,
        )

        fr.severity = {
            "overall_severity": sev_res.overall_severity,
            "primary_rule_id": sev_res.primary_rule_id,
            "triggering_metric": sev_res.triggering_metric,
            "triggering_score": sev_res.triggering_score,
            "max_component_severity": sev_res.max_component_severity,
            "num_affected_components": sev_res.num_affected_components,
            "reasoning": sev_res.reasoning,
            "evidence": [
                {
                    "rule_id": e.rule_id,
                    "metric": e.metric,
                    "observed_value": e.observed_value,
                    "threshold": e.threshold,
                    "severity": e.severity,
                    "description": e.description,
                }
                for e in sev_res.evidence
            ],
        }

        fr.highest_severity = sev_res.overall_severity
        fr.drift_detected = sev_res.overall_severity != "HEALTHY"
        if fr.drift_detected:
            result.features_with_drift += 1

        result.feature_results.append(fr)

    # Overall run severity
    feature_sevs = [fr.highest_severity for fr in result.feature_results] if result.feature_results else ["HEALTHY"]
    overall_feat_sev = max(feature_sevs, key=lambda s: SEVERITY_RANK.get(s, 1))

    schema_sev = result.schema_drift["overall_severity"] if result.schema_drift else "HEALTHY"
    null_sev = result.null_rate_summary["overall_severity"] if result.null_rate_summary else "HEALTHY"

    result.overall_severity = max(
        [overall_feat_sev, schema_sev, null_sev],
        key=lambda s: SEVERITY_RANK.get(s, 1),
    )

    result.metrics_by_algorithm = algorithm_metrics
    result.summary_stats = {
        "severity_counts": _severity_counts(result.feature_results),
        "algorithm_agreement": _compute_agreement(result.feature_results),
    }

    return result


def _severity_counts(feature_results: List[FeatureDriftResult]) -> Dict[str, int]:
    counts = {k: 0 for k in SEVERITY_RANK}
    for fr in feature_results:
        counts[fr.highest_severity] = counts.get(fr.highest_severity, 0) + 1
    return counts


def _compute_agreement(feature_results: List[FeatureDriftResult]) -> Dict[str, Any]:
    if not feature_results:
        return {"all_agree": 0, "psi_kl_agree": 0, "psi_ks_agree": 0, "kl_ks_agree": 0, "total": 0}

    total = 0
    all3 = 0
    pk = 0
    pks = 0
    kks = 0

    for fr in feature_results:
        if fr.psi is None and fr.kl is None and fr.ks is None:
            continue
        total += 1
        psi_heal = (fr.psi is None) or fr.psi["drift_status"] == "HEALTHY"
        kl_heal = (fr.kl is None) or fr.kl["drift_status"] == "HEALTHY"
        ks_heal = (fr.ks is None) or fr.ks["drift_status"] == "HEALTHY"

        if fr.psi is not None and fr.kl is not None and psi_heal == kl_heal:
            pk += 1
        if fr.psi is not None and fr.ks is not None and psi_heal == ks_heal:
            pks += 1
        if fr.kl is not None and fr.ks is not None and kl_heal == ks_heal:
            kks += 1

        present = [x for x in [fr.psi, fr.kl, fr.ks] if x is not None]
        heal_flags = [(x["drift_status"] == "HEALTHY") for x in present]
        if len(set(heal_flags)) <= 1:
            all3 += 1

    return {
        "total_with_multiple_algorithms": total,
        "all_agree": all3,
        "psi_kl_agree": pk,
        "psi_ks_agree": pks,
        "kl_ks_agree": kks,
    }
