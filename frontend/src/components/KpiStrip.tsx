import type { SatelliteDetection } from '../types/satellite'
import type { DriftSimulation } from '../types/drift'
import type { AISDataset } from '../types/ais'
import type { CandidateFilterStats } from '../analysis/aisCandidateFilter'
import type { AssociationAnalysisResult } from '../analysis/aisAssociationScore'

interface KpiStripProps {
  detection: SatelliteDetection
  driftSimulation: DriftSimulation
  aisDataset: AISDataset
  candidateStats: CandidateFilterStats
  associationAnalysis: AssociationAnalysisResult
}

/**
 * Enhanced KPI strip — satellite, drift, and investigation metrics.
 */
export default function KpiStrip({
  detection,
  driftSimulation,
  aisDataset,
  candidateStats,
  associationAnalysis,
}: KpiStripProps) {
  const sourceConfidence = Math.round(driftSimulation.sourceConfidence * 100)
  const topAssociationScore = associationAnalysis.topAssociatedVessels[0]?.associationScore ?? 0

  return (
    <div className="kpi-strip" aria-label="Investigation summary KPIs">
      <div className="kpi-item">
        <span className="kpi-label">Spill Area</span>
        <span className="kpi-value">{detection.areaKm2.toFixed(1)} km²</span>
      </div>

      <div className="kpi-item">
        <span className="kpi-label">Detection Confidence</span>
        <span className="kpi-value">{Math.round(detection.confidence * 100)}%</span>
      </div>

      <div className="kpi-item">
        <span className="kpi-label">Source Confidence</span>
        <span className="kpi-value">{sourceConfidence}%</span>
      </div>

      <div className="kpi-divider" aria-hidden="true" />

      <div className="kpi-item">
        <span className="kpi-label">AIS Vessels</span>
        <span className="kpi-value">{aisDataset.vesselCount}</span>
      </div>

      <div className="kpi-item">
        <span className="kpi-label">Candidates</span>
        <span className="kpi-value">{candidateStats.investigationCandidates}</span>
      </div>

      <div className="kpi-item">
        <span className="kpi-label">Top Association</span>
        <span className="kpi-value">{topAssociationScore}/100</span>
      </div>

      <div className="kpi-divider" aria-hidden="true" />

      <div className="kpi-item kpi-demo-badge">
        <span className="kpi-demo-label">Demo Mode</span>
        <span className="kpi-demo-value">Synthetic Data</span>
      </div>
    </div>
  )
}
