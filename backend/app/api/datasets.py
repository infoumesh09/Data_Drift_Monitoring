from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
import uuid

from ..database.session import get_db
from ..services import datasets as dataset_service
from ..schemas.dataset import DatasetResponse, DatasetUpdate

router = APIRouter(prefix="/datasets", tags=["Datasets"])


@router.get("", response_model=List[DatasetResponse])
def list_datasets(
    pipeline_id: Optional[uuid.UUID] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return dataset_service.list_datasets(db, pipeline_id=pipeline_id, skip=skip, limit=limit)


@router.post("/upload", response_model=Dict[str, Any], status_code=201)
async def upload_dataset(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    pipeline_id: Optional[uuid.UUID] = Form(None),
    description: Optional[str] = Form(None),
    version: str = Form("1.0"),
    is_baseline: bool = Form(False),
    db: Session = Depends(get_db),
):
    dataset, df, error = await dataset_service.upload_dataset(
        db=db,
        file_obj=file.file,
        filename=file.filename or "uploaded_file",
        dataset_name=name,
        pipeline_id=pipeline_id,
        description=description,
        version=version,
        is_baseline=is_baseline,
    )
    if error:
        raise HTTPException(status_code=400, detail=error)
    profile = dataset.profile if dataset else {}
    return {
        "id": str(dataset.id) if dataset else None,
        "name": dataset.name if dataset else None,
        "row_count": len(df) if df is not None else 0,
        "column_count": len(df.columns) if df is not None else 0,
        "columns": profile.get("columns", []) if profile else [],
        "profile": profile,
    }


@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(dataset_id: uuid.UUID, db: Session = Depends(get_db)):
    ds = dataset_service.get_dataset(db, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return ds


@router.patch("/{dataset_id}", response_model=DatasetResponse)
def update_dataset(dataset_id: uuid.UUID, update: DatasetUpdate, db: Session = Depends(get_db)):
    ds = dataset_service.update_dataset(db, dataset_id, update)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return ds


@router.delete("/{dataset_id}", status_code=204)
def delete_dataset(dataset_id: uuid.UUID, db: Session = Depends(get_db)):
    if not dataset_service.delete_dataset(db, dataset_id):
        raise HTTPException(status_code=404, detail="Dataset not found")
    return None
