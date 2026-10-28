"""
Controlled Drift Injection Framework (Research Experiments)

This module implements reproducible drift injection for the 11 required
experiment types. All injected drifts use a fixed random seed so results
are scientifically reproducible.

Implemented:
1.  No drift (baseline control)
2.  Small / Medium / Large mean shift
3.  Variance shift
4.  Distribution shift (distribution family change)
5.  Categorical proportion shift
6.  Gradual drift (linear interpolation across chunks)
7.  Sudden drift (before/after with threshold window)
8.  Null-rate spike
9.  Schema change simulation (dtype coercion + added/removed cols)

Usage:
    from app.experiments.drift_injection import DriftInjector
    injector = DriftInjector(seed=42)
    baseline, current = injector.inject_mean_shift(df, magnitude=1.0)

NOTE: Only deterministic transforms. No fabricated scores — run the
statistical engine on the outputs to produce actual results.
"""

import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any, List, Optional
from dataclasses import dataclass, field
from copy import deepcopy


DRIFT_TYPES = [
    "no_drift",
    "small_mean_shift",
    "medium_mean_shift",
    "large_mean_shift",
    "variance_shift",
    "distribution_shift",
    "categorical_shift",
    "gradual_drift",
    "sudden_drift",
    "null_rate_spike",
    "schema_change",
]


@dataclass
class InjectionResult:
    baseline: pd.DataFrame
    current: pd.DataFrame
    drift_type: str
    magnitude: float
    affected_features: List[str]
    feature_types: Dict[str, str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class DriftInjector:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self._rng = np.random.default_rng(seed)

    def _reset_rng(self):
        self._rng = np.random.default_rng(self.seed)

    def _split(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        df = df.reset_index(drop=True)
        n = len(df)
        if n < 2:
            return df.copy(), df.copy()
        half = n // 2
        return df.iloc[:half].reset_index(drop=True), df.iloc[half:].reset_index(drop=True)

    def _numeric_cols(self, df: pd.DataFrame) -> List[str]:
        return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c])]

    def _categorical_cols(self, df: pd.DataFrame) -> List[str]:
        return [
            c
            for c in df.columns
            if pd.api.types.is_object_dtype(df[c])
            or pd.api.types.is_bool_dtype(df[c])
            or pd.api.types.is_categorical_dtype(df[c])
            or pd.api.types.is_string_dtype(df[c])
        ]

    def no_drift(self, df: pd.DataFrame) -> InjectionResult:
        self._reset_rng()
        base, curr = self._split(df)
        return InjectionResult(
            baseline=base,
            current=curr,
            drift_type="no_drift",
            magnitude=0.0,
            affected_features=[],
            feature_types={},
            metadata={"description": "Control group: identical distribution"},
        )

    def mean_shift(self, df: pd.DataFrame, magnitude: float = 1.0, cols: Optional[List[str]] = None) -> InjectionResult:
        self._reset_rng()
        base, curr = self._split(df)
        cols = cols or self._numeric_cols(curr)
        for c in cols:
            std = float(base[c].std(skipna=True)) or 1.0
            curr[c] = curr[c] + magnitude * std
        return InjectionResult(
            baseline=base,
            current=curr,
            drift_type="mean_shift",
            magnitude=magnitude,
            affected_features=cols,
            feature_types={c: "numerical" for c in cols},
            metadata={"shift_formula": "x_current = x_baseline + magnitude * std_baseline"},
        )

    def variance_shift(self, df: pd.DataFrame, factor: float = 2.0, cols: Optional[List[str]] = None) -> InjectionResult:
        self._reset_rng()
        base, curr = self._split(df)
        cols = cols or self._numeric_cols(curr)
        for c in cols:
            mean = float(base[c].mean(skipna=True) or 0.0)
            curr[c] = (curr[c] - mean) * factor + mean
        return InjectionResult(
            baseline=base,
            current=curr,
            drift_type="variance_shift",
            magnitude=factor,
            affected_features=cols,
            feature_types={c: "numerical" for c in cols},
            metadata={"formula": "x_current = (x - μ)·factor + μ"},
        )

    def distribution_shift(self, df: pd.DataFrame, cols: Optional[List[str]] = None) -> InjectionResult:
        self._reset_rng()
        base, curr = self._split(df)
        cols = cols or self._numeric_cols(curr)
        for c in cols:
            series = base[c].dropna()
            if len(series) < 5:
                continue
            loc = float(series.min())
            scale = float(series.max() - loc) or 1.0
            n = len(curr[c])
            new_vals = self._rng.exponential(scale=scale / 3.0, size=n) + loc
            mask = curr[c].notna()
            curr.loc[mask, c] = new_vals[mask.values if hasattr(mask, "values") else mask][:int(mask.sum())]
        return InjectionResult(
            baseline=base,
            current=curr,
            drift_type="distribution_shift",
            magnitude=1.0,
            affected_features=cols,
            feature_types={c: "numerical" for c in cols},
            metadata={"target_distribution": "Exponential shift applied to current values"},
        )

    def categorical_shift(self, df: pd.DataFrame, magnitude: float = 0.5, cols: Optional[List[str]] = None) -> InjectionResult:
        self._reset_rng()
        base, curr = self._split(df)
        cols = cols or self._categorical_cols(curr)
        for c in cols:
            series = base[c].astype(str)
            if series.nunique(dropna=True) < 2:
                continue
            counts = series.value_counts()
            cats = list(counts.index)
            top_cat = cats[0]
            n = len(curr)
            if n == 0:
                continue
            top_prop = min(0.99, 0.5 + magnitude * 0.45)
            weights = np.array([top_prop if i == 0 else (1 - top_prop) / max(1, len(cats) - 1) for i in range(len(cats))])
            weights = weights / weights.sum()
            new_values = self._rng.choice(cats, size=n, p=weights)
            curr[c] = pd.Series(new_values, index=curr.index).where(curr[c].notna(), curr[c])
        return InjectionResult(
            baseline=base,
            current=curr,
            drift_type="categorical_shift",
            magnitude=magnitude,
            affected_features=cols,
            feature_types={c: "categorical" for c in cols},
            metadata={"description": "Top category proportion boosted"},
        )

    def gradual_drift(self, df: pd.DataFrame, magnitude: float = 1.0, cols: Optional[List[str]] = None) -> InjectionResult:
        self._reset_rng()
        base, curr = self._split(df)
        cols = cols or self._numeric_cols(curr)
        n = len(curr)
        for c in cols:
            std = float(base[c].std(skipna=True)) or 1.0
            ramp = np.linspace(0, 1, n)
            shift = ramp * magnitude * std
            curr[c] = curr[c].astype(float) + shift
        return InjectionResult(
            baseline=base,
            current=curr,
            drift_type="gradual_drift",
            magnitude=magnitude,
            affected_features=cols,
            feature_types={c: "numerical" for c in cols},
            metadata={"ramp": "linear from 0 to magnitude·σ across current window"},
        )

    def sudden_drift(self, df: pd.DataFrame, magnitude: float = 1.0, split_frac: float = 0.5, cols: Optional[List[str]] = None) -> InjectionResult:
        self._reset_rng()
        base, curr = self._split(df)
        cols = cols or self._numeric_cols(curr)
        n = len(curr)
        split_idx = int(n * split_frac)
        for c in cols:
            std = float(base[c].std(skipna=True)) or 1.0
            shifted = curr[c].astype(float).copy()
            shifted.iloc[split_idx:] = shifted.iloc[split_idx:] + magnitude * std
            curr[c] = shifted
        return InjectionResult(
            baseline=base,
            current=curr,
            drift_type="sudden_drift",
            magnitude=magnitude,
            affected_features=cols,
            feature_types={c: "numerical" for c in cols},
            metadata={"split_point": f"row {split_idx} of {n}", "split_frac": split_frac},
        )

    def null_rate_spike(self, df: pd.DataFrame, target_rate: float = 0.30, cols: Optional[List[str]] = None) -> InjectionResult:
        self._reset_rng()
        base, curr = self._split(df)
        cols = cols or list(curr.columns)
        for c in cols:
            n = len(curr)
            if n == 0:
                continue
            mask = self._rng.random(n) < target_rate
            curr.loc[mask, c] = np.nan
        return InjectionResult(
            baseline=base,
            current=curr,
            drift_type="null_rate_spike",
            magnitude=target_rate,
            affected_features=cols,
            feature_types={c: "mixed" for c in cols},
            metadata={"target_null_rate": target_rate},
        )

    def schema_change(self, df: pd.DataFrame, add_col: bool = True, remove_col: bool = True, change_dtype: bool = True) -> InjectionResult:
        self._reset_rng()
        base, curr = self._split(df)
        affected = []

        if remove_col and len(base.columns) > 3:
            col = base.columns[-2]
            if col in curr.columns:
                curr = curr.drop(columns=[col])
                affected.append(f"-removed:{col}")

        if add_col:
            new_col_name = "injected_promo_code"
            new_vals = self._rng.choice(["A", "B", "C", None], size=len(curr))
            curr[new_col_name] = new_vals
            affected.append(f"+added:{new_col_name}")

        if change_dtype:
            numeric_cols = self._numeric_cols(curr)
            if numeric_cols:
                target = numeric_cols[-1]
                curr[target] = curr[target].astype(str)
                affected.append(f"dtype_changed:{target} (numeric→string)")

        return InjectionResult(
            baseline=base,
            current=curr,
            drift_type="schema_change",
            magnitude=1.0,
            affected_features=affected,
            feature_types={a.split(":")[-1]: "schema" for a in affected},
            metadata={"operations": affected},
        )

    def run_by_name(self, drift_type: str, df: pd.DataFrame, magnitude: float = 1.0) -> InjectionResult:
        mapping = {
            "no_drift": lambda: self.no_drift(df),
            "small_mean_shift": lambda: self.mean_shift(df, magnitude=0.25),
            "medium_mean_shift": lambda: self.mean_shift(df, magnitude=0.75),
            "large_mean_shift": lambda: self.mean_shift(df, magnitude=1.5),
            "variance_shift": lambda: self.variance_shift(df, factor=magnitude if magnitude > 0 else 2.0),
            "distribution_shift": lambda: self.distribution_shift(df),
            "categorical_shift": lambda: self.categorical_shift(df, magnitude=magnitude if magnitude > 0 else 0.5),
            "gradual_drift": lambda: self.gradual_drift(df, magnitude=magnitude if magnitude > 0 else 1.0),
            "sudden_drift": lambda: self.sudden_drift(df, magnitude=magnitude if magnitude > 0 else 1.0),
            "null_rate_spike": lambda: self.null_rate_spike(df, target_rate=magnitude if 0 < magnitude < 1 else 0.30),
            "schema_change": lambda: self.schema_change(df),
        }
        fn = mapping.get(drift_type)
        if not fn:
            raise ValueError(f"Unknown drift_type {drift_type}. Available: {sorted(mapping.keys())}")
        return fn()
