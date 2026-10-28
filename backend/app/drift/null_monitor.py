"""
Null-Rate Monitor

Tracks missing-value anomalies between baseline and current windows.

Metrics calculated per feature:
    - baseline_null_rate: count(nulls_baseline) / count(total_baseline)
    - current_null_rate: count(nulls_current) / count(total_current)
    - delta_null_rate: current_null_rate - baseline_null_rate (signed percentage-point change)
    - absolute_change: |delta_null_rate| (magnitude in percentage points)
    - relative_change: (current_null_rate - baseline_null_rate) / baseline_null_rate
      (relative change in missingness, if baseline > 0)
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd


@dataclass
class NullRateFeatureResult:
    feature: str
    baseline_null_rate: float
    current_null_rate: float
    delta_null_rate: float      # Signed difference (current - baseline)
    absolute_change: float      # Magnitude |current - baseline|
    relative_change: float      # Relative multiplier
    threshold: float
    severity: str               # HEALTHY | LOW | MEDIUM | HIGH | CRITICAL
    drift_detected: bool
    baseline_null_count: int = 0
    current_null_count: int = 0
    baseline_total: int = 0
    current_total: int = 0
    direction: str = "UNCHANGED" # INCREASED | DECREASED | UNCHANGED
    message: str = ""


@dataclass
class NullRateMonitorResult:
    results: List[NullRateFeatureResult] = field(default_factory=list)
    overall_severity: str = "HEALTHY"
    features_with_drift: int = 0
    total_features: int = 0
    detected_at: datetime = field(default_factory=datetime.utcnow)


DEFAULT_NULL_RATE_THRESHOLDS = {
    "healthy": 0.01,           # < 1 percentage point change
    "low": 0.03,               # 1-3 percentage points change
    "medium": 0.05,            # 3-5 percentage points change
    "high": 0.15,              # 5-15 percentage points change
    "critical": 0.25,          # >= 25 percentage points change OR current null rate >= 50%
    "relative_spike_ratio": 5.0, # 5x increase in null rate
}

SEVERITY_ORDER = {"CRITICAL": 5, "HIGH": 4, "MEDIUM": 3, "LOW": 2, "HEALTHY": 1}


def _classify_null_severity(
    current_rate: float,
    abs_change: float,
    rel_change: float,
    thresholds: Dict[str, float],
) -> str:
    """Classify null rate severity based on shift between baseline and current."""
    if abs_change < thresholds.get("healthy", 0.01):
        return "HEALTHY"
    if abs_change >= thresholds.get("critical", 0.25) or (current_rate >= 0.50 and abs_change >= 0.10):
        return "CRITICAL"
    if abs_change >= thresholds.get("high", 0.15) or (current_rate >= 0.25 and rel_change >= thresholds.get("relative_spike_ratio", 5.0)):
        return "HIGH"
    if abs_change >= thresholds.get("medium", 0.05) or (current_rate >= 0.10 and rel_change >= 2.0):
        return "MEDIUM"
    if abs_change >= thresholds.get("low", 0.03):
        return "LOW"
    return "HEALTHY"


def monitor_null_rates(
    baseline_df: pd.DataFrame,
    current_df: pd.DataFrame,
    features: Optional[List[str]] = None,
    thresholds: Optional[Dict[str, float]] = None,
) -> NullRateMonitorResult:
    """
    Evaluate null rate shifts across all features.
    """
    thresholds = thresholds or DEFAULT_NULL_RATE_THRESHOLDS

    if features is None:
        cols = sorted(set(baseline_df.columns) & set(current_df.columns))
    else:
        cols = [c for c in features if c in baseline_df.columns and c in current_df.columns]

    result = NullRateMonitorResult(total_features=len(cols))
    highest_sev = "HEALTHY"

    for col in cols:
        b_series = baseline_df[col]
        c_series = current_df[col]

        b_total = len(b_series)
        c_total = len(c_series)

        b_null = int(b_series.isna().sum())
        c_null = int(c_series.isna().sum())

        b_rate = float(b_null / b_total) if b_total > 0 else 0.0
        c_rate = float(c_null / c_total) if c_total > 0 else 0.0

        delta_rate = round(c_rate - b_rate, 6)
        abs_change = round(abs(delta_rate), 6)

        if b_rate > 0:
            rel_change = round((c_rate - b_rate) / b_rate, 4)
        elif c_rate > 0:
            rel_change = 999.0  # Spike from 0 to positive
        else:
            rel_change = 0.0

        if delta_rate > 0.0001:
            direction = "INCREASED"
        elif delta_rate < -0.0001:
            direction = "DECREASED"
        else:
            direction = "UNCHANGED"

        severity = _classify_null_severity(c_rate, abs_change, rel_change, thresholds)
        drift = severity != "HEALTHY"

        if drift:
            result.features_with_drift += 1

        if SEVERITY_ORDER.get(severity, 1) > SEVERITY_ORDER.get(highest_sev, 1):
            highest_sev = severity

        sign_str = f"+{delta_rate*100:.2f}pp" if delta_rate >= 0 else f"{delta_rate*100:.2f}pp"
        msg = f"Null rate: baseline {b_rate*100:.2f}% -> current {c_rate*100:.2f}% ({sign_str}). Severity: {severity}."

        result.results.append(
            NullRateFeatureResult(
                feature=col,
                baseline_null_rate=round(b_rate, 6),
                current_null_rate=round(c_rate, 6),
                delta_null_rate=delta_rate,
                absolute_change=abs_change,
                relative_change=rel_change,
                threshold=thresholds.get("low", 0.03),
                severity=severity,
                drift_detected=drift,
                baseline_null_count=b_null,
                current_null_count=c_null,
                baseline_total=b_total,
                current_total=c_total,
                direction=direction,
                message=msg,
            )
        )

    result.overall_severity = highest_sev
    return result
