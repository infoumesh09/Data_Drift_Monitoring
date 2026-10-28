"""
Feature Classification and Preprocessing Utilities

Classifies columns into:
- numerical (int, float)
- categorical (object, category, bool, string with low cardinality)
- datetime (datetime64, object convertible to datetime)
- identifier (high cardinality string like IDs)
- unsupported (mixed types, unparseable objects)

Also provides common preprocessing helpers.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple


FEATURE_CLASS_NUMERICAL = "numerical"
FEATURE_CLASS_CATEGORICAL = "categorical"
FEATURE_CLASS_DATETIME = "datetime"
FEATURE_CLASS_IDENTIFIER = "identifier"
FEATURE_CLASS_UNSUPPORTED = "unsupported"


def _is_likely_identifier(series: pd.Series, cardinality: int, row_count: int) -> bool:
    if row_count == 0:
        return False
    col_name = str(series.name).lower()
    id_keywords = ("id", "uuid", "guid", "key", "code", "serial", "hash", "pk", "sk", "_id")
    if any(k in col_name for k in id_keywords):
        if cardinality >= int(row_count * 0.8):
            return True
    if cardinality == row_count and row_count >= 50:
        if pd.api.types.is_string_dtype(series) or pd.api.types.is_integer_dtype(series):
            return True
    return False


def _is_datetime_like(series: pd.Series) -> bool:
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    if pd.api.types.is_numeric_dtype(series):
        return False
    if not pd.api.types.is_object_dtype(series) and not pd.api.types.is_string_dtype(series):
        return False
    sample = series.dropna().astype(str).head(50)
    if len(sample) == 0:
        return False
    try:
        parsed = pd.to_datetime(sample, errors="coerce", utc=False)
        return parsed.notna().sum() / len(sample) >= 0.8
    except Exception:
        return False


def classify_feature(series: pd.Series, row_count: Optional[int] = None) -> str:
    row_count = row_count if row_count is not None else len(series)
    non_null = series.dropna()
    if len(non_null) == 0:
        return FEATURE_CLASS_UNSUPPORTED

    try:
        cardinality = int(series.nunique(dropna=True))
    except Exception:
        cardinality = 0

    if pd.api.types.is_numeric_dtype(series):
        if pd.api.types.is_bool_dtype(series):
            return FEATURE_CLASS_CATEGORICAL
        if cardinality <= 2 and row_count >= 10:
            return FEATURE_CLASS_CATEGORICAL
        if _is_likely_identifier(series, cardinality, row_count):
            return FEATURE_CLASS_IDENTIFIER
        return FEATURE_CLASS_NUMERICAL

    if pd.api.types.is_datetime64_any_dtype(series) or pd.api.types.is_timedelta64_dtype(series):
        return FEATURE_CLASS_DATETIME

    if _is_datetime_like(series):
        return FEATURE_CLASS_DATETIME

    if pd.api.types.is_categorical_dtype(series):
        return FEATURE_CLASS_CATEGORICAL

    if pd.api.types.is_bool_dtype(series):
        return FEATURE_CLASS_CATEGORICAL

    if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
        if _is_likely_identifier(series, cardinality, row_count):
            return FEATURE_CLASS_IDENTIFIER
        return FEATURE_CLASS_CATEGORICAL

    return FEATURE_CLASS_UNSUPPORTED


def classify_dataframe(df: pd.DataFrame) -> Dict[str, str]:
    classification = {}
    row_count = len(df)
    for col in df.columns:
        try:
            classification[col] = classify_feature(df[col], row_count)
        except Exception:
            classification[col] = FEATURE_CLASS_UNSUPPORTED
    return classification


def profile_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    row_count = len(df)
    col_count = len(df.columns)
    total_cells = row_count * col_count
    total_nulls = int(df.isna().sum().sum())

    profile: Dict[str, Any] = {
        "row_count": row_count,
        "column_count": col_count,
        "total_cells": total_cells,
        "total_null_cells": total_nulls,
        "overall_null_rate": float(total_nulls / total_cells) if total_cells > 0 else 0.0,
        "duplicate_rows": int(df.duplicated().sum()),
        "columns": [],
        "classification": classify_dataframe(df),
    }

    for col in df.columns:
        series = df[col]
        col_info: Dict[str, Any] = {
            "name": col,
            "dtype": str(series.dtype),
            "feature_class": profile["classification"].get(col, FEATURE_CLASS_UNSUPPORTED),
            "non_null_count": int(series.notna().sum()),
            "null_count": int(series.isna().sum()),
            "null_rate": float(series.isna().sum() / row_count) if row_count > 0 else 0.0,
        }
        try:
            col_info["cardinality"] = int(series.nunique(dropna=True))
        except Exception:
            col_info["cardinality"] = 0

        fc = col_info["feature_class"]
        if fc == FEATURE_CLASS_NUMERICAL:
            clean = series.dropna()
            if len(clean) > 0:
                col_info.update({
                    "min": float(clean.min()),
                    "max": float(clean.max()),
                    "mean": float(clean.mean()),
                    "median": float(clean.median()),
                    "std": float(clean.std()) if len(clean) > 1 else 0.0,
                    "q1": float(clean.quantile(0.25)),
                    "q3": float(clean.quantile(0.75)),
                })
        elif fc == FEATURE_CLASS_CATEGORICAL:
            vc = series.astype(str).value_counts().head(20)
            col_info["top_values"] = {str(k): int(v) for k, v in vc.items()}

        profile["columns"].append(col_info)

    profile["memory_usage_bytes"] = int(df.memory_usage(deep=True).sum())
    profile["size_bytes"] = profile["memory_usage_bytes"]

    return profile
