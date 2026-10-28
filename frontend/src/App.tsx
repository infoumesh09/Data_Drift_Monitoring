import { Routes, Route, Navigate } from 'react-router-dom'
import AppLayout from './components/layout/AppLayout'
import Overview from './pages/Overview'
import Pipelines from './pages/Pipelines'
import DriftMonitoring from './pages/DriftMonitoring'
import SchemaMonitoring from './pages/SchemaMonitoring'
import Incidents from './pages/Incidents'
import AIDiagnosis from './pages/AIDiagnosis'
import AlgorithmComparison from './pages/AlgorithmComparison'
import Experiments from './pages/Experiments'
import Datasets from './pages/Datasets'
import Settings from './pages/Settings'
import FeatureDrillDown from './pages/FeatureDrillDown'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<AppLayout />}>
        <Route index element={<Navigate to="/overview" replace />} />
        <Route path="overview" element={<Overview />} />
        <Route path="pipelines" element={<Pipelines />} />
        <Route path="drift-monitoring" element={<DriftMonitoring />} />
        <Route path="drift-monitoring/:feature" element={<FeatureDrillDown />} />
        <Route path="schema-monitoring" element={<SchemaMonitoring />} />
        <Route path="incidents" element={<Incidents />} />
        <Route path="ai-diagnosis" element={<AIDiagnosis />} />
        <Route path="algorithm-comparison" element={<AlgorithmComparison />} />
        <Route path="experiments" element={<Experiments />} />
        <Route path="datasets" element={<Datasets />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  )
}
