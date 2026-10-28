import app.drift.psi as psi
import app.drift.kl_divergence as kl
import app.drift.ks_test as ks
import app.drift.severity as sev
import app.drift.runner as rn
import app.drift.preprocessing as pp
import app.drift.schema_drift as sd
import app.drift.null_monitor as nm
import app.experiments.drift_injection as di
import pandas as pd
import numpy as np

print("Imports OK")
np.random.seed(42)
df_baseline = pd.DataFrame({
    'age': np.random.normal(35, 10, 1000),
    'cat': np.random.choice(['A','B','C'], 1000),
})
df_current  = pd.DataFrame({
    'age': np.random.normal(45, 10, 1000),
    'cat': np.random.choice(['A','B','C'], 1000, p=[0.5, 0.3, 0.2]),
})
r = rn.run_drift_detection(df_baseline, df_current)
print(f"Run ID: {r.run_id}")
print(f"Features monitored: {r.features_monitored}, drifted: {r.features_with_drift}")
print(f"Overall severity: {r.overall_severity}")
for fr in r.feature_results:
    print(f"  - {fr.feature}: PSI={fr.psi['psi_score']:.3f}  KL={fr.kl['kl_score']:.3f}  sev={fr.highest_severity}")

injector = di.DriftInjector(seed=42)
res = injector.mean_shift(df_baseline, magnitude=1.0)
print(f"\nDrift injection OK: {res.drift_type} (magnitude={res.magnitude}), features={len(res.affected_features)}")
print("=== Statistical Engine Smoke Test: PASSED ===")
