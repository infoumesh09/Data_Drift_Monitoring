"""
Integration test suite for DriftSense full detection lifecycle.
Tests dataset creation, detection execution, PostgreSQL persistence
(DetectionRun, DriftEvent, SchemaChange, Incident), AI diagnosis hydration,
and experiment evaluation metrics.
"""

import os
import uuid
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal
from app.models.dataset import Dataset
from app.models.detection_run import DetectionRun
from app.models.drift_event import DriftEvent
from app.models.schema_change import SchemaChange
from app.models.incident import Incident
from app.models.experiment import Experiment, ExperimentResult


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def db_session():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def setup_datasets(db_session):
    """Create baseline and drifted dataset files and DB records for testing."""
    os.makedirs("./data_storage/uploads", exist_ok=True)

    # 1. Baseline dataset
    np.random.seed(42)
    n = 1000
    base_df = pd.DataFrame({
        "account_id": [f"ACC_{i:04d}" for i in range(n)],
        "income": np.random.normal(55000, 12000, n),
        "credit_score": np.random.normal(700, 50, n),
        "account_type": np.random.choice(["Checking", "Savings", "Premium"], n, p=[0.5, 0.35, 0.15]),
    })
    base_path = f"./data_storage/uploads/test_baseline_{uuid.uuid4().hex[:6]}.csv"
    base_df.to_csv(base_path, index=False)

    base_id = uuid.uuid4()
    base_ds = Dataset(
        id=base_id,
        name="Test Baseline Dataset",
        version="v1.0",
        storage_path=base_path,
        file_format="csv",
        row_count=n,
        column_count=4,
        is_baseline=True,
    )
    db_session.add(base_ds)

    # 2. Shifted / Drifted dataset (severe income drift + 40% null spike in credit_score)
    curr_df = pd.DataFrame({
        "account_id": [f"ACC_{i:04d}" for i in range(n)],
        "income": np.random.normal(85000, 15000, n),  # severe shift
        "credit_score": [None if i % 2 == 0 else s for i, s in enumerate(np.random.normal(700, 50, n))],  # 50% nulls
        "account_type": np.random.choice(["Checking", "Savings", "Premium"], n, p=[0.2, 0.2, 0.6]),  # categorical shift
        "new_feature": np.random.uniform(0, 1, n),  # schema addition
    })
    curr_path = f"./data_storage/uploads/test_current_{uuid.uuid4().hex[:6]}.csv"
    curr_df.to_csv(curr_path, index=False)

    curr_id = uuid.uuid4()
    curr_ds = Dataset(
        id=curr_id,
        name="Test Current Drifted Dataset",
        version="v1.1",
        storage_path=curr_path,
        file_format="csv",
        row_count=n,
        column_count=5,
        is_baseline=False,
    )
    db_session.add(curr_ds)
    db_session.commit()

    yield base_ds, curr_ds

    # Cleanup files
    for p in (base_path, curr_path):
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass


def test_health_check(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["healthy", "degraded", "ok"]


def test_drift_detection_and_persistence(client, db_session, setup_datasets):
    base_ds, curr_ds = setup_datasets

    # Execute drift detection
    payload = {
        "baseline_dataset_id": str(base_ds.id),
        "current_dataset_id": str(curr_ds.id),
        "run_psi": True,
        "run_kl": True,
        "run_ks": True,
        "run_schema": True,
        "run_null_rate": True,
    }
    res = client.post("/api/v1/drift/detect", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()

    assert "run_id" in data
    run_id = data["run_id"]
    assert data["overall_severity"] in ["HIGH", "CRITICAL"]
    assert data["features_monitored"] >= 3

    # 1. Verify DetectionRun in PostgreSQL
    d_run = db_session.query(DetectionRun).filter(DetectionRun.run_id == run_id).first()
    assert d_run is not None
    assert d_run.baseline_dataset_id == base_ds.id
    assert d_run.current_dataset_id == curr_ds.id
    assert d_run.status == "COMPLETED"
    assert d_run.features_monitored >= 3

    # 2. Verify DriftEvents in PostgreSQL linked to DetectionRun
    events = db_session.query(DriftEvent).filter(DriftEvent.detection_run_id == d_run.id).all()
    assert len(events) >= 1
    for ev in events:
        assert ev.feature_name in ["account_id", "income", "credit_score", "account_type", "new_feature"]
        assert ev.severity in ["HEALTHY", "LOW", "MEDIUM", "HIGH", "CRITICAL"]

    # 3. Verify SchemaChanges in PostgreSQL
    changes = db_session.query(SchemaChange).filter(SchemaChange.detection_run_id == d_run.id).all()
    assert len(changes) >= 1  # "new_feature" was added
    added = [c for c in changes if c.column_name == "new_feature"]
    assert len(added) >= 1

    # 4. Verify Incident automatically generated for HIGH / CRITICAL drift
    incident = db_session.query(Incident).order_by(Incident.created_at.desc()).first()
    assert incident is not None
    assert incident.status == "OPEN"
    assert incident.severity in ["HIGH", "CRITICAL"]
    assert incident.current_window.get("dataset_id") == str(curr_ds.id)

    # 5. Verify GET /api/v1/drift/latest
    latest_res = client.get("/api/v1/drift/latest")
    assert latest_res.status_code == 200
    latest_data = latest_res.json()
    assert latest_data["has_data"] is True
    assert latest_data["run_id"] == run_id

    # 6. Verify GET /api/v1/drift/feature/income/history
    history_res = client.get("/api/v1/drift/feature/income/history")
    assert history_res.status_code == 200
    hist_data = history_res.json()
    assert hist_data["has_data"] is True
    assert hist_data["feature"] == "income"
    assert len(hist_data["history"]) >= 1
    assert len(hist_data["distribution_chart"]) >= 1

    # 7. Verify GET /api/v1/drift/schema
    schema_res = client.get("/api/v1/drift/schema")
    assert schema_res.status_code == 200
    schema_data = schema_res.json()
    assert schema_data["has_data"] is True
    assert schema_data["added_columns"] >= 1

    # 8. Verify AI / Root Cause Analysis using incident ID
    diag_res = client.post("/api/v1/ai/diagnose", json={"incident_id": str(incident.id)})
    assert diag_res.status_code == 200
    diag_data = diag_res.json()
    assert len(diag_data["observed_evidence"]) >= 1
    assert len(diag_data["hypotheses"]) >= 1
    assert len(diag_data["recommendations"]) >= 1
    assert diag_data["confidence"] > 0.0


def test_experiments_run_and_comparison(client, db_session):
    """Test experiment runner and dynamic algorithm comparison calculations."""
    payload = {
        "drift_types": ["mean_shift", "no_drift"],
        "sample_sizes": [500],
        "magnitudes": [0.0, 1.5],
        "random_seed": 42,
    }
    res = client.post("/api/v1/experiments/run", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["total_runs"] >= 2

    # Check database records
    results = db_session.query(ExperimentResult).filter(
        ExperimentResult.experiment_id == data["experiment_id"]
    ).all()
    assert len(results) >= 2
    for r in results:
        assert r.ground_truth_drift in [0, 1]
        assert r.execution_time_ms >= 0

    # Check Algorithm Comparison aggregation
    comp_res = client.get("/api/v1/experiments/algorithm-comparison")
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert comp_data["has_data"] is True
    assert comp_data["total_experiments"] >= 2
    assert len(comp_data["mag_data"]) >= 1
    assert len(comp_data["error_data"]) >= 1
