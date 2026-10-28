"""
Dataset Service layer

Dataset ingestion, metadata storage, and CSV parsing utilities.
"""

import os
import io
import uuid
import hashlib
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any, BinaryIO
from pathlib import Path
from sqlalchemy.orm import Session
import pandas as pd

from ..database.session import get_db
from ..models.dataset import Dataset
from ..models.feature import Feature as FeatureModel
from ..schemas.dataset import DatasetCreate, DatasetUpdate, DatasetProfile, DatasetResponse
from ..services.storage import get_storage_backend
from ..drift.preprocessing import profile_dataframe, classify_dataframe


ALLOWED_EXTENSIONS = {".csv", ".tsv", ".xlsx", ".xls", ".parquet"}


def _validate_filename(filename: str) -> Tuple[bool, str]:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Unsupported extension {ext}. Allowed: {sorted(ALLOWED_EXTENSIONS)}"
    return True, ext


def _infer_reader(ext: str):
    if ext == ".csv":
        return lambda f: pd.read_csv(f, low_memory=False)
    if ext == ".tsv":
        return lambda f: pd.read_csv(f, sep="\t", low_memory=False)
    if ext in (".xlsx", ".xls"):
        return lambda f: pd.read_excel(f)
    if ext == ".parquet":
        return lambda f: pd.read_parquet(f)
    raise ValueError(f"No reader for {ext}")


def _checksum_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def upload_dataset(
    db: Session,
    file_obj: BinaryIO,
    filename: str,
    dataset_name: Optional[str] = None,
    pipeline_id: Optional[uuid.UUID] = None,
    description: Optional[str] = None,
    is_baseline: bool = False,
    version: str = "1.0",
    created_by: Optional[uuid.UUID] = None,
    tags: Optional[List[str]] = None,
):
    valid, ext = _validate_filename(filename)
    if not valid:
        return None, None, ext

    file_bytes = file_obj.read() if hasattr(file_obj, "read") else file_obj
    if isinstance(file_bytes, bytes):
        reader_input = io.BytesIO(file_bytes)
    else:
        reader_input = file_obj
        file_bytes = file_bytes if isinstance(file_bytes, (bytes, bytearray)) else b""

    if not file_bytes or len(file_bytes) == 0:
        return None, None, "Uploaded file is empty (0 bytes)."

    # Max size 250 MB
    if len(file_bytes) > 250 * 1024 * 1024:
        return None, None, "File exceeds maximum permitted size of 250 MB."

    try:
        reader = _infer_reader(ext)
        df = reader(reader_input)
    except Exception as e:
        return None, None, f"Failed to parse {ext} file: {str(e)}"

    if df is None or len(df) == 0:
        return None, None, "Dataset contains no data rows."
    if len(df.columns) == 0:
        return None, None, "Dataset contains no columns."

    checksum = _checksum_bytes(file_bytes) if file_bytes else ""

    storage = get_storage_backend()
    storage_key = f"datasets/{uuid.uuid4().hex}{ext}"
    storage.save(storage_key, file_bytes if isinstance(file_bytes, (bytes, bytearray)) else io.BytesIO(file_bytes))

    profile = profile_dataframe(df)
    classification = classify_dataframe(df)

    name = dataset_name or Path(filename).stem

    dataset = Dataset(
        pipeline_id=pipeline_id,
        name=name,
        description=description,
        version=version,
        storage_path=storage_key,
        storage_backend="local",
        file_format=ext.lstrip("."),
        row_count=len(df),
        column_count=len(df.columns),
        size_bytes=len(file_bytes) if isinstance(file_bytes, (bytes, bytearray)) else profile.get("size_bytes", 0),
        checksum=checksum,
        profile=profile,
        tags=tags or [],
        is_baseline=is_baseline,
        created_by=created_by,
    )
    db.add(dataset)
    db.flush()

    for col_info in profile["columns"]:
        col = col_info["name"]
        feat = FeatureModel(
            dataset_id=dataset.id,
            name=col,
            display_name=col,
            data_type=col_info.get("dtype", "object"),
            feature_class=classification.get(col, "unsupported"),
            null_count=col_info.get("null_count", 0),
            null_rate=col_info.get("null_rate", 0.0),
            cardinality=col_info.get("cardinality", 0),
            min_value=col_info.get("min"),
            max_value=col_info.get("max"),
            mean_value=col_info.get("mean"),
            std_value=col_info.get("std"),
            unique_values=col_info.get("top_values", {}),
            value_counts=col_info.get("top_values", {}),
            statistics={k: col_info.get(k) for k in ("min", "max", "mean", "median", "std", "q1", "q3") if k in col_info},
            is_identifier=1 if classification.get(col) == "identifier" else 0,
            position=list(df.columns).index(col) if col in df.columns else 0,
            monitored=0 if classification.get(col) in ("identifier", "datetime", "unsupported") else 1,
        )
        db.add(feat)

    db.commit()
    db.refresh(dataset)
    return dataset, df, None


def load_dataset_dataframe(dataset: Dataset) -> Optional[pd.DataFrame]:
    raw_path = dataset.storage_path or ""
    if os.path.exists(raw_path):
        path = raw_path
    else:
        try:
            storage = get_storage_backend()
            path = storage.get_path(raw_path)
        except Exception:
            path = None

    if not path or not os.path.exists(path):
        return None
    ext = Path(path).suffix.lower()
    try:
        reader = _infer_reader(ext)
        return reader(path)
    except Exception:
        return None


def list_datasets(db: Session, pipeline_id: Optional[uuid.UUID] = None, skip: int = 0, limit: int = 100) -> List[Dataset]:
    q = db.query(Dataset)
    if pipeline_id:
        q = q.filter(Dataset.pipeline_id == pipeline_id)
    return q.order_by(Dataset.created_at.desc()).offset(skip).limit(limit).all()


def get_dataset(db: Session, dataset_id: uuid.UUID) -> Optional[Dataset]:
    return db.query(Dataset).filter(Dataset.id == dataset_id).first()


def update_dataset(db: Session, dataset_id: uuid.UUID, update: DatasetUpdate) -> Optional[Dataset]:
    ds = get_dataset(db, dataset_id)
    if not ds:
        return None
    for field_name, value in update.model_dump(exclude_unset=True).items():
        setattr(ds, field_name, value)
    db.commit()
    db.refresh(ds)
    return ds


def delete_dataset(db: Session, dataset_id: uuid.UUID) -> bool:
    ds = get_dataset(db, dataset_id)
    if not ds:
        return False
    storage = get_storage_backend()
    if ds.storage_path:
        storage.delete(ds.storage_path)
    db.delete(ds)
    db.commit()
    return True
