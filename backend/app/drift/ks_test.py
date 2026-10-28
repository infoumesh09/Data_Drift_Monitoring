"""
Two-Sample Kolmogorov-Smirnov (KS) Test

Non-parametric test for comparing continuous distributions by measuring the
maximum vertical distance (D-statistic) between their empirical cumulative
distribution functions (ECDFs):
    D = sup_x |F_1(x) - F_2(x)|

CRITICAL STATISTICAL PRINCIPLE:
    Statistical significance (p-value < alpha) and practical drift severity
    (D-statistic magnitude) are strictly separated.
    - With large sample sizes (e.g., N > 10,000), even minuscule, practically
      irrelevant differences yield p < 0.0001.
    - Conversely, small samples may fail to achieve p < 0.05 even with noticeable drift.
    Therefore:
      Drift is flagged only when BOTH statistical significance (p < alpha)
      AND practical magnitude (D >= threshold) are satisfied.

Scope:
    - Applicable exclusively to numerical / continuous features.
    - Categorical features are explicitly rejected with a clear status message.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from scipy import stats as scipy_stats


@dataclass
class KSTestResult:
    feature: str
    feature_type: str
    ks_statistic: float            # Effect size (D in [0, 1])
    p_value: float                 # Statistical significance
    adjusted_p_value: Optional[float] = None  # Benjamini-Hochberg FDR corrected
    significance_level: float = 0.05
    statistically_significant: bool = False
    drift_status: str = "HEALTHY"  # HEALTHY | LOW | MEDIUM | HIGH | CRITICAL
    severity_threshold: float = 0.20
    baseline_n: int = 0
    current_n: int = 0
    baseline_ecdf: Dict[str, Any] = field(default_factory=dict)
    current_ecdf: Dict[str, Any] = field(default_factory=dict)
    message: str = ""


DEFAULT_KS_CONFIG = {
    "significance_level": 0.05,
    "healthy": 0.10,    # D < 0.10: Minimal difference
    "low": 0.20,        # 0.10 <= D < 0.20: Slight shift
    "medium": 0.30,     # 0.20 <= D < 0.30: Moderate shift
    "high": 0.50,       # 0.30 <= D < 0.50: Substantial shift
    "critical": 0.50,   # D >= 0.50: Severe divergence
}


def _compute_ecdf_summary(data: np.ndarray, n_points: int = 20) -> Dict[str, Any]:
    """Sample points along the ECDF for visualization."""
    if len(data) == 0:
        return {"quantiles": [], "values": []}
    percentiles = np.linspace(0, 100, n_points)
    values = np.percentile(data, percentiles)
    return {
        "quantiles": [round(float(q / 100.0), 3) for q in percentiles],
        "values": [round(float(v), 4) for v in values],
    }


def run_ks_test(
    baseline_data: pd.Series,
    current_data: pd.Series,
    feature: str,
    feature_type: str = "numerical",
    significance_level: float = 0.05,
    config: Optional[Dict[str, float]] = None,
) -> KSTestResult:
    """
    Execute two-sample Kolmogorov-Smirnov test.
    """
    cfg = config or DEFAULT_KS_CONFIG
    alpha = significance_level or cfg.get("significance_level", 0.05)

    # Validate feature type
    if feature_type not in ("numerical", "float", "int", "integer"):
        return KSTestResult(
            feature=feature,
            feature_type=feature_type,
            ks_statistic=0.0,
            p_value=1.0,
            significance_level=alpha,
            statistically_significant=False,
            drift_status="HEALTHY",
            message=f"KS test not applicable to non-numerical feature '{feature}' (type={feature_type}). Use PSI or Categorical divergence instead.",
        )

    b_clean = baseline_data.dropna().to_numpy(dtype=float)
    c_clean = current_data.dropna().to_numpy(dtype=float)

    b_n = len(b_clean)
    c_n = len(c_clean)

    # Edge cases: Insufficient data
    if b_n < 2 or c_n < 2:
        return KSTestResult(
            feature=feature,
            feature_type="numerical",
            ks_statistic=0.0,
            p_value=1.0,
            significance_level=alpha,
            statistically_significant=False,
            drift_status="HEALTHY",
            baseline_n=b_n,
            current_n=c_n,
            message=f"Insufficient observations for KS test (baseline n={b_n}, current n={c_n}, minimum required 2).",
        )

    # Constant distributions
    if np.min(b_clean) == np.max(b_clean) and np.min(c_clean) == np.max(c_clean):
        if np.min(b_clean) == np.min(c_clean):
            return KSTestResult(
                feature=feature,
                feature_type="numerical",
                ks_statistic=0.0,
                p_value=1.0,
                significance_level=alpha,
                statistically_significant=False,
                drift_status="HEALTHY",
                baseline_n=b_n,
                current_n=c_n,
                message="Both baseline and current are identical constant distributions.",
            )
        else:
            return KSTestResult(
                feature=feature,
                feature_type="numerical",
                ks_statistic=1.0,
                p_value=0.0,
                significance_level=alpha,
                statistically_significant=True,
                drift_status="CRITICAL",
                baseline_n=b_n,
                current_n=c_n,
                message="Constant value shifted completely between baseline and current.",
            )

    # Run two-sample KS test from SciPy
    res = scipy_stats.ks_2samp(b_clean, c_clean)
    ks_stat = float(res.statistic)
    p_val = float(res.pvalue)

    if np.isnan(ks_stat):
        ks_stat = 0.0
    if np.isnan(p_val):
        p_val = 1.0

    stat_sig = bool(p_val < alpha)

    # Assign severity by D-statistic magnitude, contingent on statistical significance
    if not stat_sig or ks_stat < cfg.get("healthy", 0.10):
        drift_status = "HEALTHY"
    elif ks_stat < cfg.get("low", 0.20):
        drift_status = "LOW"
    elif ks_stat < cfg.get("medium", 0.30):
        drift_status = "MEDIUM"
    elif ks_stat < cfg.get("high", 0.50):
        drift_status = "HIGH"
    else:
        drift_status = "CRITICAL"

    msg = (
        f"KS D={ks_stat:.4f}, p={p_val:.4e} (alpha={alpha}). "
        f"{'Statistically significant' if stat_sig else 'Not significant'}. "
        f"Status: {drift_status}."
    )

    return KSTestResult(
        feature=feature,
        feature_type="numerical",
        ks_statistic=round(ks_stat, 6),
        p_value=round(p_val, 8),
        significance_level=alpha,
        statistically_significant=stat_sig,
        drift_status=drift_status,
        severity_threshold=cfg.get("medium", 0.20),
        baseline_n=b_n,
        current_n=c_n,
        baseline_ecdf=_compute_ecdf_summary(b_clean),
        current_ecdf=_compute_ecdf_summary(c_clean),
        message=msg,
    )
