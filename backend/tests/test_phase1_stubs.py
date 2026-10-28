"""
Backend test structure.

Run from /backend:
    pytest tests/

Phase 1 test stubs — real assertions added in Phase 18.
"""

import pytest


class TestHealthEndpointStub:
    def test_placeholder_passes(self):
        assert True


class TestStatisticalAlgorithmsStub:
    def test_psi_module_imports(self):
        from app.drift import psi
        assert hasattr(psi, "calculate_psi")

    def test_kl_module_imports(self):
        from app.drift import kl_divergence
        assert hasattr(kl_divergence, "calculate_kl_divergence")

    def test_ks_module_imports(self):
        from app.drift import ks_test
        assert hasattr(ks_test, "run_ks_test")

    def test_severity_imports(self):
        from app.drift import severity
        assert hasattr(severity, "calculate_severity")

    def test_runner_imports(self):
        from app.drift import runner
        assert hasattr(runner, "run_drift_detection")


class TestDriftInjectionStub:
    def test_injector_imports(self):
        from app.experiments.drift_injection import DriftInjector, DRIFT_TYPES
        assert len(DRIFT_TYPES) == 11
        assert DriftInjector(seed=42).seed == 42
