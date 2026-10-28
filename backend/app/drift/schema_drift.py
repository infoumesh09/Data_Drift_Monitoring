"""
Schema Drift Detector

Detects changes between a baseline schema and a current schema, including:
- Added columns
- Removed columns
- Datatype changes
- Null-rate changes
- Cardinality changes
"""

import pandas as pd
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ColumnSchemaDiff:
    column_name: str
    change_type: str
    before_value: Any = None
    after_value: Any = None
    severity: str = "MEDIUM"
    description: str = ""


@dataclass
class SchemaDriftResult:
    dataset_name: Optional[str] = None
    baseline_version: Optional[str] = None
    current_version: Optional[str] = None
    added_columns: List[ColumnSchemaDiff] = field(default_factory=list)
    removed_columns: List[ColumnSchemaDiff] = field(default_factory=list)
    type_changes: List[ColumnSchemaDiff] = field(default_factory=list)
    null_rate_changes: List[ColumnSchemaDiff] = field(default_factory=list)
    cardinality_changes: List[ColumnSchemaDiff] = field(default_factory=list)
    before_schema: Dict[str, Any] = field(default_factory=dict)
    after_schema: Dict[str, Any] = field(default_factory=dict)
    total_changes: int = 0
    overall_severity: str = "HEALTHY"
    detected_at: datetime = field(default_factory=datetime.utcnow)


def _infer_schema(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    schema = {}
    total_rows = len(df)
    for col in df.columns:
        series = df[col]
        null_count = int(series.isna().sum())
        null_rate = float(null_count / total_rows) if total_rows > 0 else 0.0
        try:
            cardinality = int(series.nunique(dropna=True))
        except Exception:
            cardinality = 0
        schema[col] = {
            "name": col,
            "dtype": str(series.dtype),
            "null_count": null_count,
            "null_rate": null_rate,
            "cardinality": cardinality,
            "position": list(df.columns).index(col),
        }
    return schema


def _null_rate_severity(before: float, after: float) -> str:
    abs_change = abs(after - before)
    if after > 0.30 or abs_change > 0.25:
        return "CRITICAL"
    if after > 0.15 or abs_change > 0.10:
        return "HIGH"
    if after > 0.05 or abs_change > 0.03:
        return "MEDIUM"
    if after > 0.01 or abs_change > 0.005:
        return "LOW"
    return "HEALTHY"


def detect_schema_drift(
    baseline_df: pd.DataFrame,
    current_df: pd.DataFrame,
    dataset_name: Optional[str] = None,
    baseline_version: Optional[str] = None,
    current_version: Optional[str] = None,
) -> SchemaDriftResult:
    baseline_schema = _infer_schema(baseline_df)
    current_schema = _infer_schema(current_df)

    result = SchemaDriftResult(
        dataset_name=dataset_name,
        baseline_version=baseline_version,
        current_version=current_version,
        before_schema=baseline_schema,
        after_schema=current_schema,
    )

    baseline_cols = set(baseline_schema.keys())
    current_cols = set(current_schema.keys())

    added = current_cols - baseline_cols
    removed = baseline_cols - current_cols
    common = baseline_cols & current_cols

    for col in added:
        cs = current_schema[col]
        result.added_columns.append(ColumnSchemaDiff(
            column_name=col,
            change_type="added_column",
            before_value=None,
            after_value={"dtype": cs["dtype"], "null_rate": cs["null_rate"], "cardinality": cs["cardinality"]},
            severity="HIGH" if cs["null_rate"] > 0.5 else "MEDIUM",
            description=f"Column '{col}' added with type {cs['dtype']}",
        ))

    for col in removed:
        bs = baseline_schema[col]
        result.removed_columns.append(ColumnSchemaDiff(
            column_name=col,
            change_type="removed_column",
            before_value={"dtype": bs["dtype"], "null_rate": bs["null_rate"], "cardinality": bs["cardinality"]},
            after_value=None,
            severity="HIGH",
            description=f"Column '{col}' removed (was {bs['dtype']})",
        ))

    for col in common:
        bs = baseline_schema[col]
        cs = current_schema[col]

        if bs["dtype"] != cs["dtype"]:
            critical_types = {"int64", "float64", "int32", "float32"}
            is_critical = (bs["dtype"] in critical_types) != (cs["dtype"] in critical_types)
            result.type_changes.append(ColumnSchemaDiff(
                column_name=col,
                change_type="type_changed",
                before_value=bs["dtype"],
                after_value=cs["dtype"],
                severity="CRITICAL" if is_critical else "HIGH",
                description=f"Datatype changed from {bs['dtype']} to {cs['dtype']}",
            ))

        null_sev = _null_rate_severity(bs["null_rate"], cs["null_rate"])
        if null_sev != "HEALTHY":
            result.null_rate_changes.append(ColumnSchemaDiff(
                column_name=col,
                change_type="null_rate_changed",
                before_value=round(bs["null_rate"], 4),
                after_value=round(cs["null_rate"], 4),
                severity=null_sev,
                description=(
                    f"Null rate changed from {bs['null_rate']*100:.2f}% to "
                    f"{cs['null_rate']*100:.2f}%"
                ),
            ))

        card_before = bs["cardinality"]
        card_after = cs["cardinality"]
        if card_before > 0:
            card_ratio = card_after / card_before if card_before > 0 else 0.0
        else:
            card_ratio = float("inf") if card_after > 0 else 1.0
        if card_ratio < 0.5 or card_ratio > 2.0:
            if card_ratio < 0.3 or card_ratio > 3.0:
                card_sev = "HIGH"
            else:
                card_sev = "MEDIUM"
            result.cardinality_changes.append(ColumnSchemaDiff(
                column_name=col,
                change_type="cardinality_changed",
                before_value=card_before,
                after_value=card_after,
                severity=card_sev,
                description=f"Cardinality changed from {card_before} to {card_after}",
            ))

    result.total_changes = (
        len(result.added_columns)
        + len(result.removed_columns)
        + len(result.type_changes)
        + len(result.null_rate_changes)
        + len(result.cardinality_changes)
    )

    all_sevs = [
        *(d.severity for d in result.added_columns),
        *(d.severity for d in result.removed_columns),
        *(d.severity for d in result.type_changes),
        *(d.severity for d in result.null_rate_changes),
        *(d.severity for d in result.cardinality_changes),
    ]
    severity_rank = {"CRITICAL": 5, "HIGH": 4, "MEDIUM": 3, "LOW": 2, "HEALTHY": 1}
    if all_sevs:
        result.overall_severity = max(all_sevs, key=lambda s: severity_rank.get(s, 1))
    else:
        result.overall_severity = "HEALTHY"

    return result
