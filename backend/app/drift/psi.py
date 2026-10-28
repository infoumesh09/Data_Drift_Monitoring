"""
Population Stability Index (PSI) Calculator

Formula:
    PSI = Σ ((Actual % - Expected %) * ln(Actual % / Expected %))

Where:
    - Expected (%) is the proportion in the reference (baseline) dataset.
    - Actual (%) is the proportion in the production (current) dataset.

Binning Strategy:
    - Bin edges are calculated strictly from the reference (baseline) distribution
      to preserve the reference framework.
    - Outer bin boundaries are expanded to (-inf, +inf) to properly account for
      new values in current data that fall outside the baseline range.
    - Quantile (equal-frequency) and equal-width binning are supported.
    - Constant distributions and zero-variance features are handled gracefully.

Handling of Zero Proportions:
    - Zero proportions are smoothed with a documented epsilon (default 1e-6)
      to avoid log(0) and division by zero.
"""

from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
import numpy as np
import pandas as pd


@dataclass
class PSIResult:
    feature: str
    feature_type: str
    psi_score: float
    threshold: float
    drift_status: str  # HEALTHY | LOW | MEDIUM | HIGH | CRITICAL
    baseline_distribution: Dict[str, Any] = field(default_factory=dict)
    current_distribution: Dict[str, Any] = field(default_factory=dict)
    bins: Optional[List[str]] = None
    per_bin_psi: Optional[List[float]] = None
    message: str = ""


DEFAULT_PSI_THRESHOLDS = {
    "healthy": 0.10,   # PSI < 0.10: No significant shift
    "low": 0.20,       # 0.10 <= PSI < 0.20: Slight shift
    "medium": 0.25,    # 0.20 <= PSI < 0.25: Moderate shift
    "high": 0.50,      # 0.25 <= PSI < 0.50: Significant shift
    "critical": 0.50,  # PSI >= 0.50: Severe shift requiring intervention
}

EPSILON = 1e-6


def _calculate_psi_components(
    expected_proportions: np.ndarray,
    actual_proportions: np.ndarray,
    epsilon: float = EPSILON,
) -> Tuple[float, List[float]]:
    """
    Calculate PSI score with documented epsilon smoothing for zero-probability bins.
    """
    # Replace zeros with epsilon
    expected = np.where(expected_proportions <= 0, epsilon, expected_proportions).astype(float)
    actual = np.where(actual_proportions <= 0, epsilon, actual_proportions).astype(float)

    # Re-normalize after smoothing
    expected = expected / np.sum(expected)
    actual = actual / np.sum(actual)

    diff = actual - expected
    log_ratio = np.log(actual / expected)
    per_bin = diff * log_ratio

    psi_value = float(np.sum(per_bin))
    # Floating point precision safe clamp
    if np.isnan(psi_value) or psi_value < 0.0:
        psi_value = 0.0

    return round(psi_value, 6), [round(float(v), 6) for v in per_bin.tolist()]


def _bin_numerical(
    baseline_series: pd.Series,
    current_series: pd.Series,
    n_bins: int = 10,
    binning_method: str = "equal_frequency",
) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """
    Bin numerical continuous data using baseline distribution as the reference.
    """
    baseline_clean = baseline_series.dropna().to_numpy(dtype=float)
    current_clean = current_series.dropna().to_numpy(dtype=float)

    # Edge case 1: both datasets empty
    if len(baseline_clean) == 0 and len(current_clean) == 0:
        return np.array([1.0]), np.array([1.0]), ["empty"]

    # Edge case 2: baseline empty but current not empty
    if len(baseline_clean) == 0:
        return np.array([0.0]), np.array([1.0]), ["current_only"]

    # Edge case 3: current empty but baseline not empty
    if len(current_clean) == 0:
        return np.array([1.0]), np.array([0.0]), ["baseline_only"]

    b_min, b_max = float(np.min(baseline_clean)), float(np.max(baseline_clean))

    # Edge case 4: constant value in baseline
    if b_min == b_max:
        # Check if current is also the same constant value
        c_min, c_max = float(np.min(current_clean)), float(np.max(current_clean))
        if c_min == b_min and c_max == b_min:
            return np.array([1.0]), np.array([1.0]), [f"constant_{b_min}"]
        else:
            # Shift away from constant
            bins = np.array([-np.inf, b_min - 1e-5, b_min + 1e-5, np.inf])
    else:
        if binning_method == "equal_frequency" and len(baseline_clean) >= n_bins:
            quantiles = np.linspace(0, 1, n_bins + 1)
            bins = np.quantile(baseline_clean, quantiles)
            bins = np.unique(bins)
            if len(bins) < 2:
                bins = np.linspace(b_min, b_max, n_bins + 1)
        else:
            bins = np.linspace(b_min, b_max, n_bins + 1)

        # Expand outer edges to -inf and +inf so outliers in current are captured
        bins[0] = -np.inf
        bins[-1] = np.inf

    baseline_counts, _ = np.histogram(baseline_clean, bins=bins)
    current_counts, _ = np.histogram(current_clean, bins=bins)

    b_sum = baseline_counts.sum()
    c_sum = current_counts.sum()

    baseline_props = baseline_counts / b_sum if b_sum > 0 else np.zeros_like(baseline_counts, dtype=float)
    current_props = current_counts / c_sum if c_sum > 0 else np.zeros_like(current_counts, dtype=float)

    # Format human readable bin labels
    bin_labels = []
    for i in range(len(bins) - 1):
        left = "-inf" if np.isneginf(bins[i]) else f"{bins[i]:.3g}"
        right = "+inf" if np.isposinf(bins[i + 1]) else f"{bins[i + 1]:.3g}"
        bin_labels.append(f"[{left}, {right})")

    return baseline_props, current_props, bin_labels


def _bin_categorical(
    baseline_series: pd.Series,
    current_series: pd.Series,
    max_categories: int = 50,
) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """
    Bin categorical features using all observed classes across baseline and current.
    Unseen categories in current are grouped into __OTHER__ if exceeding max_categories.
    """
    baseline_clean = baseline_series.fillna("__MISSING__").astype(str)
    current_clean = current_series.fillna("__MISSING__").astype(str)

    b_counts = baseline_clean.value_counts()
    c_counts = current_clean.value_counts()

    all_cats = sorted(set(b_counts.index) | set(c_counts.index))

    if len(all_cats) > max_categories:
        top_cats = sorted(set(b_counts.head(max_categories // 2).index) | set(c_counts.head(max_categories // 2).index))
        top_cats.append("__OTHER__")
        all_cats = top_cats

    b_aligned = b_counts.reindex(all_cats, fill_value=0)
    c_aligned = c_counts.reindex(all_cats, fill_value=0)

    if "__OTHER__" in all_cats:
        b_other = b_counts[~b_counts.index.isin(all_cats)].sum()
        c_other = c_counts[~c_counts.index.isin(all_cats)].sum()
        b_aligned["__OTHER__"] = b_other
        c_aligned["__OTHER__"] = c_other

    b_arr = b_aligned.to_numpy(dtype=float)
    c_arr = c_aligned.to_numpy(dtype=float)

    b_sum = b_arr.sum()
    c_sum = c_arr.sum()

    baseline_props = b_arr / b_sum if b_sum > 0 else np.zeros_like(b_arr)
    current_props = c_arr / c_sum if c_sum > 0 else np.zeros_like(c_arr)

    return baseline_props, current_props, all_cats


def calculate_psi(
    baseline_data: pd.Series,
    current_data: pd.Series,
    feature: str,
    feature_type: str = "numerical",
    n_bins: int = 10,
    binning_method: str = "equal_frequency",
    thresholds: Optional[Dict[str, float]] = None,
    epsilon: float = EPSILON,
) -> PSIResult:
    """
    Compute Population Stability Index for a feature between baseline and current data.
    """
    thresholds = thresholds or DEFAULT_PSI_THRESHOLDS

    if feature_type in ("numerical", "float", "int", "integer"):
        baseline_props, current_props, bins = _bin_numerical(
            baseline_data, current_data, n_bins=n_bins, binning_method=binning_method
        )
        ft = "numerical"
    else:
        baseline_props, current_props, bins = _bin_categorical(baseline_data, current_data)
        ft = "categorical"

    psi_score, per_bin = _calculate_psi_components(baseline_props, current_props, epsilon=epsilon)

    # Assign drift status based on thresholds
    if psi_score < thresholds.get("healthy", 0.10):
        drift_status = "HEALTHY"
    elif psi_score < thresholds.get("low", 0.20):
        drift_status = "LOW"
    elif psi_score < thresholds.get("medium", 0.25):
        drift_status = "MEDIUM"
    elif psi_score < thresholds.get("high", 0.50):
        drift_status = "HIGH"
    else:
        drift_status = "CRITICAL"

    msg = f"PSI={psi_score:.4f} for '{feature}' ({ft}). Status: {drift_status}."

    return PSIResult(
        feature=feature,
        feature_type=ft,
        psi_score=psi_score,
        threshold=thresholds.get("medium", 0.25),
        drift_status=drift_status,
        baseline_distribution={
            "bins": bins,
            "proportions": [round(float(p), 5) for p in baseline_props],
        },
        current_distribution={
            "bins": bins,
            "proportions": [round(float(p), 5) for p in current_props],
        },
        bins=bins,
        per_bin_psi=per_bin,
        message=msg,
    )
