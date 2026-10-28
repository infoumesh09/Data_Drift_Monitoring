"""
Comprehensive statistical engine unit test suite.
Validates PSI, KL Divergence, KS Test, Null-Rate Monitor, Schema Comparison,
and Severity Priority Engine against mathematical invariants and edge cases.
"""

import numpy as np
import pandas as pd
import pytest

from app.drift.psi import calculate_psi
from app.drift.kl_divergence import calculate_kl_divergence
from app.drift.ks_test import run_ks_test
from app.drift.null_monitor import monitor_null_rates
from app.drift.severity import calculate_severity
from app.drift.runner import run_drift_detection


# ===========================================================================
# 1. PSI (Population Stability Index) Tests
# ===========================================================================

class TestPSI:
    def test_identical_continuous_distributions(self):
        np.random.seed(42)
        base = pd.Series(np.random.normal(loc=10.0, scale=2.0, size=2000))
        curr = pd.Series(np.random.normal(loc=10.0, scale=2.0, size=2000))
        res = calculate_psi(base, curr, feature="norm_feat", feature_type="numerical")

        assert res.psi_score < 0.05
        assert res.drift_status == "HEALTHY"
        assert res.bins is not None
        assert len(res.bins) > 0

    def test_shifted_continuous_distribution(self):
        np.random.seed(42)
        base = pd.Series(np.random.normal(loc=0.0, scale=1.0, size=2000))
        curr = pd.Series(np.random.normal(loc=1.5, scale=1.0, size=2000))
        res = calculate_psi(base, curr, feature="shifted_feat", feature_type="numerical")

        assert res.psi_score > 0.25
        assert res.drift_status in ["MEDIUM", "HIGH", "CRITICAL"]

    def test_constant_value_continuous(self):
        """Zero variance in baseline should not crash or produce NaN/Inf."""
        base = pd.Series([5.0] * 500)
        curr = pd.Series([5.0] * 500)
        res = calculate_psi(base, curr, feature="const_feat", feature_type="numerical")

        assert res.psi_score == 0.0
        assert not np.isnan(res.psi_score)
        assert not np.isinf(res.psi_score)
        assert res.drift_status == "HEALTHY"

    def test_constant_baseline_different_current(self):
        base = pd.Series([5.0] * 500)
        curr = pd.Series([10.0] * 500)
        res = calculate_psi(base, curr, feature="const_shift", feature_type="numerical")

        assert res.psi_score > 0.25
        assert res.drift_status in ["MEDIUM", "HIGH", "CRITICAL"]

    def test_categorical_with_unseen_classes(self):
        """Unseen class in current should be smoothed by epsilon without dividing by zero."""
        base = pd.Series(["A", "B", "C", "A", "B"] * 200)
        curr = pd.Series(["A", "B", "D", "E"] * 250)
        res = calculate_psi(base, curr, feature="cat_feat", feature_type="categorical")

        assert res.psi_score > 0.0
        assert not np.isnan(res.psi_score)
        assert not np.isinf(res.psi_score)
        assert res.drift_status in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


# ===========================================================================
# 2. KL Divergence Tests
# ===========================================================================

class TestKLDivergence:
    def test_identical_continuous_distributions(self):
        np.random.seed(123)
        base = pd.Series(np.random.exponential(scale=2.0, size=2000))
        curr = pd.Series(np.random.exponential(scale=2.0, size=2000))
        res = calculate_kl_divergence(base, curr, feature="exp_feat", feature_type="numerical")

        assert res.kl_score < 0.1
        assert res.drift_status == "HEALTHY"

    def test_divergent_continuous_distributions(self):
        np.random.seed(123)
        base = pd.Series(np.random.normal(0, 1, 2000))
        curr = pd.Series(np.random.normal(3, 1, 2000))
        res = calculate_kl_divergence(base, curr, feature="div_feat", feature_type="numerical")

        assert res.kl_score > 0.5
        assert res.drift_status in ["MEDIUM", "HIGH", "CRITICAL"]

    def test_categorical_kl(self):
        base = pd.Series(["red", "blue", "green"] * 300)
        curr = pd.Series(["red"] * 800 + ["blue"] * 100)
        res = calculate_kl_divergence(base, curr, feature="color_feat", feature_type="categorical")

        assert res.kl_score > 0.2
        assert not np.isnan(res.kl_score)
        assert not np.isinf(res.kl_score)


# ===========================================================================
# 3. KS Test (Kolmogorov-Smirnov) Tests
# ===========================================================================

class TestKSTest:
    def test_identical_continuous_distributions(self):
        np.random.seed(999)
        base = pd.Series(np.random.normal(50, 10, 1500))
        curr = pd.Series(np.random.normal(50, 10, 1500))
        res = run_ks_test(base, curr, feature="cont_feat", feature_type="numerical")

        assert res.ks_statistic < 0.1
        assert res.p_value > 0.01  # Cannot reject H0
        assert res.statistically_significant is False

    def test_shifted_continuous_distribution(self):
        np.random.seed(999)
        base = pd.Series(np.random.normal(50, 10, 1500))
        curr = pd.Series(np.random.normal(56, 10, 1500))
        res = run_ks_test(base, curr, feature="shift_feat", feature_type="numerical")

        assert res.ks_statistic > 0.15
        assert res.p_value < 0.001
        assert res.statistically_significant is True
        assert res.drift_status in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

    def test_reject_categorical_feature(self):
        base = pd.Series(["Tier1", "Tier2", "Tier3"] * 100)
        curr = pd.Series(["Tier1", "Tier2", "Tier3"] * 100)
        res = run_ks_test(base, curr, feature="tier_feat", feature_type="categorical")

        assert res.ks_statistic == 0.0
        assert res.statistically_significant is False
        assert "not applicable" in res.message.lower()

    def test_constant_value_series(self):
        base = pd.Series([42.0] * 500)
        curr = pd.Series([42.0] * 500)
        res = run_ks_test(base, curr, feature="const_feat", feature_type="numerical")

        assert res.ks_statistic == 0.0
        assert res.statistically_significant is False
        assert res.drift_status == "HEALTHY"


# ===========================================================================
# 4. Null-Rate Monitor Tests
# ===========================================================================

class TestNullMonitor:
    def test_stable_null_rate(self):
        base = pd.DataFrame({"feat": [1.0, 2.0, None, 4.0, 5.0] * 200})  # 20% null
        curr = pd.DataFrame({"feat": [1.0, 2.0, None, 4.0, 5.0] * 200})  # 20% null
        res = monitor_null_rates(base, curr)

        feat_res = res.results[0]
        assert feat_res.baseline_null_rate == 0.2
        assert feat_res.current_null_rate == 0.2
        assert feat_res.absolute_change == 0.0
        assert feat_res.severity == "HEALTHY"
        assert feat_res.drift_detected is False

    def test_severe_null_spike(self):
        base = pd.DataFrame({"feat": [1.0, 2.0, 3.0, 4.0, 5.0] * 200})    # 0% null
        curr = pd.DataFrame({"feat": [None, None, None, 4.0, 5.0] * 200})  # 60% null
        res = monitor_null_rates(base, curr)

        feat_res = res.results[0]
        assert feat_res.baseline_null_rate == 0.0
        assert feat_res.current_null_rate == 0.6
        assert feat_res.delta_null_rate == 0.6
        assert feat_res.severity == "CRITICAL"
        assert feat_res.drift_detected is True


# ===========================================================================
# 5. Severity Engine Priority Rules Tests
# ===========================================================================

class TestSeverityEngine:
    def test_critical_schema_removal_rule(self):
        res = calculate_severity(
            psi_score=0.01,
            kl_score=0.01,
            ks_p_value=0.5,
            null_rate_abs_change=0.0,
            schema_change_severity="CRITICAL",
        )
        assert res.overall_severity == "CRITICAL"
        assert "RULE-CRIT-SCHEMA" in res.primary_rule_id

    def test_critical_null_spike_rule(self):
        res = calculate_severity(
            psi_score=0.05,
            kl_score=0.02,
            ks_p_value=0.3,
            null_rate_abs_change=0.35,  # 35% spike
        )
        assert res.overall_severity == "CRITICAL"
        assert "RULE-CRIT-NULL" in res.primary_rule_id

    def test_high_psi_rule(self):
        res_single = calculate_severity(
            psi_score=0.35,
            kl_score=0.01,
            null_rate_abs_change=0.005,
        )
        assert res_single.overall_severity == "HIGH"
        assert "RULE-HIGH-PSI" in res_single.primary_rule_id

        res_consensus = calculate_severity(
            psi_score=0.35,
            kl_score=0.30,
            null_rate_abs_change=0.005,
        )
        assert res_consensus.overall_severity == "HIGH"
        assert "RULE-HIGH-CONSENSUS" in res_consensus.primary_rule_id

        res_crit = calculate_severity(
            psi_score=0.55,
            kl_score=0.01,
            null_rate_abs_change=0.005,
        )
        assert res_crit.overall_severity == "CRITICAL"
        assert "RULE-CRIT-PSI" in res_crit.primary_rule_id

    def test_healthy_consensus_rule(self):
        res = calculate_severity(
            psi_score=0.02,
            kl_score=0.01,
            ks_p_value=0.6,
            null_rate_abs_change=0.005,
        )
        assert res.overall_severity == "HEALTHY"
        assert "RULE-HEALTHY" in res.primary_rule_id


# ===========================================================================
# 6. Detection Runner & Benjamini-Hochberg Correction Tests
# ===========================================================================

class TestRunnerFDR:
    def test_fdr_correction_multi_feature(self):
        np.random.seed(42)
        n = 1000
        # 4 continuous features, 1 shifted, 3 identical
        base_df = pd.DataFrame({
            "feat_1": np.random.normal(0, 1, n),
            "feat_2": np.random.normal(10, 2, n),
            "feat_3": np.random.normal(100, 15, n),
            "feat_shifted": np.random.normal(5, 1, n),
        })
        curr_df = pd.DataFrame({
            "feat_1": np.random.normal(0, 1, n),
            "feat_2": np.random.normal(10, 2, n),
            "feat_3": np.random.normal(100, 15, n),
            "feat_shifted": np.random.normal(8, 1, n),  # shifted
        })

        summary = run_drift_detection(base_df, curr_df)
        assert summary.overall_severity in ["MEDIUM", "HIGH", "CRITICAL"]
        assert summary.features_monitored == 4
        assert summary.features_with_drift >= 1

        # Check feat_shifted was caught
        shifted_res = next(f for f in summary.feature_results if f.feature == "feat_shifted")
        assert shifted_res.drift_detected is True
        assert shifted_res.psi["psi_score"] > 0.25
        assert shifted_res.ks["statistically_significant"] is True
        assert "adjusted_p_value" in shifted_res.ks
