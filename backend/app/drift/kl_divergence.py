"""
Kullback-Leibler (KL) Divergence Calculator

Direction:
    D_KL(Baseline || Current) = Σ P(x) * ln(P(x) / Q(x))

    Where P is the reference (baseline) probability distribution and Q is the
    production (current) probability distribution.
    Measures informational divergence when Q is used to approximate P.

Properties & Handling:
    - Binning strictly mirrors the reference distribution for numerical data.
    - Epsilon smoothing prevents division by zero when Q(x) = 0.
    - If P(x) = 0, the term limits to 0 since lim_{p->0} p * ln(p / q) = 0.
    - Score is non-negative (clamped to >= 0 to avoid float precision negatives).
    - Thresholds:
        KL < 0.10: HEALTHY (no significant shift)
        0.10 <= KL < 0.25: LOW
        0.25 <= KL < 0.50: MEDIUM
        0.50 <= KL < 1.00: HIGH
        KL >= 1.00: CRITICAL (major informational divergence)
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from .psi import _bin_numerical, _bin_categorical, EPSILON


@dataclass
class KLResult:
    feature: str
    feature_type: str
    kl_score: float
    threshold: float
    drift_status: str  # HEALTHY | LOW | MEDIUM | HIGH | CRITICAL
    direction: str = "KL(Baseline || Current)"
    baseline_distribution: Dict[str, Any] = field(default_factory=dict)
    current_distribution: Dict[str, Any] = field(default_factory=dict)
    message: str = ""


DEFAULT_KL_THRESHOLDS = {
    "healthy": 0.10,
    "low": 0.25,
    "medium": 0.50,
    "high": 1.00,
    "critical": 1.00,
}


def _compute_kl_divergence(
    p_probs: np.ndarray,
    q_probs: np.ndarray,
    epsilon: float = EPSILON,
) -> float:
    """
    Compute D_KL(P || Q) = Σ P(x) * ln(P(x) / Q(x)).
    P is baseline, Q is current.
    """
    # Smooth zero probabilities with epsilon
    p_smooth = np.where(p_probs <= 0, epsilon, p_probs).astype(float)
    q_smooth = np.where(q_probs <= 0, epsilon, q_probs).astype(float)

    p_norm = p_smooth / np.sum(p_smooth)
    q_norm = q_smooth / np.sum(q_smooth)

    # Where p was originally 0, contribution to KL is 0
    ratio = p_norm / q_norm
    term = np.where(p_probs <= 0, 0.0, p_norm * np.log(ratio))

    kl_val = float(np.sum(term))
    if np.isnan(kl_val) or kl_val < 0.0:
        kl_val = 0.0

    return round(kl_val, 6)


def calculate_kl_divergence(
    baseline_data: pd.Series,
    current_data: pd.Series,
    feature: str,
    feature_type: str = "numerical",
    n_bins: int = 10,
    thresholds: Optional[Dict[str, float]] = None,
    epsilon: float = EPSILON,
) -> KLResult:
    """
    Calculate KL Divergence D_KL(Baseline || Current) for continuous or categorical features.
    """
    thresholds = thresholds or DEFAULT_KL_THRESHOLDS

    if feature_type in ("numerical", "float", "int", "integer"):
        p_props, q_props, bins = _bin_numerical(baseline_data, current_data, n_bins=n_bins)
        ft = "numerical"
    else:
        p_props, q_props, bins = _bin_categorical(baseline_data, current_data)
        ft = "categorical"

    kl_score = _compute_kl_divergence(p_props, q_props, epsilon=epsilon)

    if kl_score < thresholds.get("healthy", 0.10):
        drift_status = "HEALTHY"
    elif kl_score < thresholds.get("low", 0.25):
        drift_status = "LOW"
    elif kl_score < thresholds.get("medium", 0.50):
        drift_status = "MEDIUM"
    elif kl_score < thresholds.get("high", 1.00):
        drift_status = "HIGH"
    else:
        drift_status = "CRITICAL"

    msg = f"KL(Baseline||Current)={kl_score:.4f} for '{feature}' ({ft}). Status: {drift_status}."

    return KLResult(
        feature=feature,
        feature_type=ft,
        kl_score=kl_score,
        threshold=thresholds.get("medium", 0.50),
        drift_status=drift_status,
        direction="KL(Baseline || Current)",
        baseline_distribution={
            "bins": bins,
            "proportions": [round(float(p), 5) for p in p_props],
        },
        current_distribution={
            "bins": bins,
            "proportions": [round(float(q), 5) for q in q_props],
        },
        message=msg,
    )
