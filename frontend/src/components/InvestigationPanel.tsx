import { useState, useMemo } from 'react'
import type { SatelliteDetection } from '../types/satellite'
import type { DriftSimulation } from '../types/drift'
import type { AISDataset, VesselTrajectory } from '../types/ais'
import type { CandidateFilterStats } from '../analysis/aisCandidateFilter'
import type { AISAssociationResult, AssociationAnalysisResult } from '../analysis/aisAssociationScore'
import type { AISAnomalyResult, AnomalyAnalysisResult } from '../analysis/aisAnomalyAnalysis'
import { formatAcquisitionTime, formatLatitude, formatLongitude } from '../utils/format'
import { reconstructVesselAtTime } from '../geo/temporalInterpolation'
import Top3Display from './Top3Display'
import AssociationScoreBreakdown from './AssociationScoreBreakdown'
import AnomalyEvidenceDisplay from './AnomalyEvidenceDisplay'
import MethodologyDisclaimer from './MethodologyDisclaimer'

interface InvestigationPanelProps {
  detection: SatelliteDetection
  driftSimulation: DriftSimulation
  aisDataset: AISDataset
  selected: boolean
  sourceRegionSelected: boolean
  selectedVessel: VesselTrajectory | undefined
  candidateStats: CandidateFilterStats
  selectedVesselCandidate: AISAssociationResult | undefined
  associationAnalysis: AssociationAnalysisResult
  anomalyAnalysis: AnomalyAnalysisResult
  selectedVesselAnomaly: AISAnomalyResult | undefined
  selectedTimeMs: number
  detectionTimeMs: number
  onVesselSelect?: (mmsi: number | null) => void
}

export default function InvestigationPanel(p: InvestigationPanelProps) {
  const [isDisclaimerExpanded, setIsDisclaimerExpanded] = useState(false)

  const offsetMs = p.detectionTimeMs - p.selectedTimeMs
  const offsetHours = Math.floor(offsetMs / (1000 * 60 * 60))
  const offsetMinutes = Math.floor((offsetMs % (1000 * 60 * 60)) / (1000 * 60))
  const offsetSeconds = Math.floor((offsetMs % (1000 * 60)) / 1000)
  const offsetString =
    offsetMs <= 0
      ? 'T = 00:00:00 (Detection)'
      : `T - ${String(offsetHours).padStart(2, '0')}h ${String(offsetMinutes).padStart(2, '0')}m ${String(offsetSeconds).padStart(2, '0')}s`

  const currentTimeFormatted = useMemo(() => {
    try {
      return new Date(p.selectedTimeMs).toISOString().replace('.000Z', ' UTC').replace('T', ' ')
    } catch {
      return 'Unknown'
    }
  }, [p.selectedTimeMs])

  // Live interpolated positions for Top 3 ranked vessels at selectedTimeMs
  const liveRankedStates = useMemo(() => {
    const topVessels = p.associationAnalysis.topAssociatedVessels.slice(0, 3)
    return topVessels
      .map((assoc, idx) => {
        const vesselData = p.aisDataset.vessels.find((v) => v.mmsi === assoc.mmsi)
        if (!vesselData) return null
        const state = reconstructVesselAtTime(
          {
            mmsi: vesselData.mmsi,
            name: vesselData.name,
            rank: idx + 1,
            points: vesselData.points,
          },
          p.selectedTimeMs,
          p.detectionTimeMs,
          p.detection.centroid,
        )
        return {
          ...assoc,
          state,
        }
      })
      .filter(Boolean)
  }, [
    p.associationAnalysis.topAssociatedVessels,
    p.aisDataset.vessels,
    p.selectedTimeMs,
    p.detectionTimeMs,
    p.detection.centroid,
  ])

  // Minimal & aesthetic temporal reconstruction card
  const reconstructionNotice = (
    <section className="temporal-card">
      <div className="temporal-card-header">
        <div className="temporal-header-left">
          <span className="temporal-pulse-dot" />
          <span className="temporal-title">Temporal Reconstruction (P2 / P3)</span>
        </div>
        <span className={`temporal-offset-badge ${offsetMs <= 0 ? 'at-detection' : ''}`}>
          {offsetString}
        </span>
      </div>

      <div className="temporal-time-strip">
        <span className="time-strip-icon">🕒</span>
        <span className="time-strip-val">{currentTimeFormatted}</span>
      </div>

      <div className="temporal-live-vessels">
        <div className="live-vessels-header">
          <span>Live Proximity at T</span>
          <span className="header-sub">Interpolated</span>
        </div>

        <div className="live-vessel-cards-grid">
          {liveRankedStates.map((item) => {
            if (!item || !item.state) return null
            const rankColors = ['#ef4444', '#f59e0b', '#10b981']
            const rankIdx = item.rank ? item.rank - 1 : 0
            const color = rankColors[rankIdx] ?? '#38bdf8'
            const isSelected = p.selectedVessel?.mmsi === item.mmsi

            return (
              <div
                key={item.mmsi}
                className={`live-vessel-row ${isSelected ? 'selected' : ''}`}
                onClick={() => p.onVesselSelect?.(item.mmsi)}
                style={{ borderLeftColor: color }}
                role="button"
                tabIndex={0}
                title={`Click to focus ${item.vesselName}`}
              >
                <div className="live-vessel-top">
                  <span className="live-rank-pill" style={{ backgroundColor: color }}>
                    #{item.rank ?? rankIdx + 1}
                  </span>
                  <span className="live-vessel-name">{item.vesselName}</span>
                  <span className="live-vessel-speed">{item.state.speedKmh} km/h</span>
                </div>
                <div className="live-vessel-stats">
                  <span>Course: {item.state.heading}°</span>
                  <span>
                    Dist to Spill:{' '}
                    <strong style={{ color: '#fff' }}>
                      {item.state.distanceToSpillKm ?? item.minimumSourceDistanceKm?.toFixed(1) ?? '-'} km
                    </strong>
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Sleek Collapsible Disclosure for Section 10 Notice */}
      <div className="temporal-disclosure">
        <button
          type="button"
          className="temporal-disclosure-toggle"
          onClick={() => setIsDisclaimerExpanded((prev) => !prev)}
        >
          <span>⚖️ Temporal Correlation Notice</span>
          <span className="disclosure-arrow">{isDisclaimerExpanded ? '▲' : '▼'}</span>
        </button>

        {isDisclaimerExpanded && (
          <p className="temporal-disclosure-text">
            &ldquo;Our dashboard provides an interactive temporal reconstruction. Starting from the spill
            detection time, the investigator can move backward through the investigation timeline and
            observe historical positions and movement trails of ranked AIS vessels. This helps visually
            assess spatial-temporal correlation with the reconstructed spill source. The association score
            indicates correlation and does not prove that a vessel caused the spill.&rdquo;
          </p>
        )}
      </div>
    </section>
  )

  // 1. Vessel Selected View
  if (p.selectedVessel && p.selectedVesselCandidate && p.selectedVesselAnomaly) {
    const lpt = p.selectedVessel.points[p.selectedVessel.points.length - 1]
    const isCandidate = p.selectedVesselCandidate.isCandidate

    return (
      <div className="panel">
        <div className="panel-header">
          <div className="panel-header-title">
            <span className="panel-title-text">INVESTIGATION</span>
            <span className="panel-badge-vessel">🚢 Vessel Focus</span>
          </div>
          <button
            type="button"
            className="panel-back-btn"
            onClick={() => p.onVesselSelect?.(null)}
            title="Return to Spill Overview"
          >
            ← Overview
          </button>
        </div>

        <div className="panel-body panel-scrollable">
          {reconstructionNotice}

          {/* Vessel Specification Card */}
          <section className="panel-card">
            <div className="card-section-header">
              <h3 className="section-title">Vessel Telemetry</h3>
              <span className="vessel-rank-highlight">
                Rank #{p.selectedVesselCandidate.rank}
              </span>
            </div>

            <div className="spec-grid">
              <div className="spec-item">
                <span className="spec-label">Vessel Name</span>
                <span className="spec-value highlighted">{p.selectedVessel.name}</span>
              </div>
              <div className="spec-item">
                <span className="spec-label">MMSI</span>
                <span className="spec-value mono">{p.selectedVessel.mmsi}</span>
              </div>
              <div className="spec-item">
                <span className="spec-label">Type</span>
                <span className="spec-value">{p.selectedVessel.type}</span>
              </div>
              <div className="spec-item">
                <span className="spec-label">Speed</span>
                <span className="spec-value mono">{lpt.speed.toFixed(1)} kn</span>
              </div>
              <div className="spec-item">
                <span className="spec-label">Course / Heading</span>
                <span className="spec-value mono">{lpt.course}° / {lpt.heading}°</span>
              </div>
              <div className="spec-item">
                <span className="spec-label">Min Source Dist</span>
                <span className="spec-value mono" style={{ color: '#38bdf8' }}>
                  {p.selectedVesselCandidate.minimumSourceDistanceKm?.toFixed(1) ?? '—'} km
                </span>
              </div>
              <div className="spec-item full-width">
                <span className="spec-label">Position</span>
                <span className="spec-value mono">
                  {formatLatitude(lpt.latitude)} · {formatLongitude(lpt.longitude)}
                </span>
              </div>
            </div>
          </section>

          {/* Association Analysis Breakdown */}
          <section className="panel-card">
            <h3 className="section-title">Association Analysis</h3>
            <AssociationScoreBreakdown
              temporalScore={p.selectedVesselCandidate.temporalScore}
              proximityScore={p.selectedVesselCandidate.proximityScore}
              trajectoryScore={p.selectedVesselCandidate.trajectoryScore}
              totalScore={p.selectedVesselCandidate.associationScore}
            />
          </section>

          {/* Candidate Evidence Checklist */}
          <section className="panel-card">
            <h3 className="section-title">Candidate Evidence Checks</h3>
            <div className="evidence-checklist">
              <div className="checklist-row">
                <span className="check-label">Investigation Candidate</span>
                <span className={`check-badge ${isCandidate ? 'pass' : 'fail'}`}>
                  {isCandidate ? '✓ MATCH' : '✗ NO'}
                </span>
              </div>
              <div className="checklist-row">
                <span className="check-label">Temporal Window Compatibility</span>
                <span className={`check-badge ${p.selectedVesselCandidate.temporalMatch ? 'pass' : 'fail'}`}>
                  {p.selectedVesselCandidate.temporalMatch ? '✓ MATCH' : '✗ NO'}
                </span>
              </div>
              <div className="checklist-row">
                <span className="check-label">Source Proximity Compatibility</span>
                <span className={`check-badge ${p.selectedVesselCandidate.sourceRegionProximityMatch ? 'pass' : 'fail'}`}>
                  {p.selectedVesselCandidate.sourceRegionProximityMatch ? '✓ MATCH' : '✗ NO'}
                </span>
              </div>
              <div className="checklist-row">
                <span className="check-label">Trajectory Intersection</span>
                <span className={`check-badge ${p.selectedVesselCandidate.trajectorySourceIntersection ? 'pass' : 'fail'}`}>
                  {p.selectedVesselCandidate.trajectorySourceIntersection ? '✓ MATCH' : '✗ NO'}
                </span>
              </div>
            </div>
          </section>

          {/* Anomaly Evidence */}
          <section className="panel-card">
            <AnomalyEvidenceDisplay anomaly={p.selectedVesselAnomaly} />
          </section>

          <MethodologyDisclaimer />
        </div>
      </div>
    )
  }

  // 2. Source Region Selected View
  if (p.sourceRegionSelected) {
    const s = p.driftSimulation.sourceRegion
    return (
      <div className="panel">
        <div className="panel-header">
          <div className="panel-header-title">
            <span className="panel-title-text">INVESTIGATION</span>
            <span className="panel-badge-source">Probable Source</span>
          </div>
        </div>
        <div className="panel-body panel-scrollable">
          {reconstructionNotice}

          <section className="panel-card">
            <h3 className="section-title">Inferred Source Region (OpenDrift)</h3>
            <div className="spec-grid">
              <div className="spec-item">
                <span className="spec-label">Lat Range</span>
                <span className="spec-value mono">
                  {formatLatitude(s.bounds.minLatitude)} - {formatLatitude(s.bounds.maxLatitude)}
                </span>
              </div>
              <div className="spec-item">
                <span className="spec-label">Lon Range</span>
                <span className="spec-value mono">
                  {formatLongitude(s.bounds.minLongitude)} - {formatLongitude(s.bounds.maxLongitude)}
                </span>
              </div>
              <div className="spec-item full-width">
                <span className="spec-label">Source Confidence</span>
                <span className="spec-value highlighted" style={{ color: '#34d399' }}>
                  {Math.round(p.driftSimulation.sourceConfidence * 100)}%
                </span>
              </div>
            </div>
          </section>

          <section className="panel-card">
            <Top3Display
              topVessels={p.associationAnalysis.topAssociatedVessels}
              onVesselSelect={p.onVesselSelect}
              selectedMmsi={p.selectedVessel?.mmsi}
            />
          </section>

          <MethodologyDisclaimer />
        </div>
      </div>
    )
  }

  // 3. Default / Satellite Spill Selected View
  const confPercent = Math.round(p.detection.confidence * 100)

  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-header-title">
          <span className="panel-title-text">INVESTIGATION</span>
          <span className="panel-live-tag">● LIVE</span>
        </div>
        <span className="panel-phase-badge">Phase 2 · Attribution</span>
      </div>

      <div className="panel-body panel-scrollable">
        {/* Temporal Reconstruction & Live Proximity */}
        {reconstructionNotice}

        {/* Satellite Detection Card */}
        <section className="panel-card">
          <div className="card-section-header">
            <h3 className="section-title">🛰️ Satellite Detection (P1)</h3>
            <span className="card-pill-ok">Validated</span>
          </div>

          <div className="spec-grid">
            <div className="spec-item">
              <span className="spec-label">Sensor</span>
              <span className="spec-value">{p.detection.sensor}</span>
            </div>
            <div className="spec-item">
              <span className="spec-label">Acquisition Time</span>
              <span className="spec-value mono">{formatAcquisitionTime(p.detection.timestamp)}</span>
            </div>
            <div className="spec-item">
              <span className="spec-label">Observed Area</span>
              <span className="spec-value mono highlighted">{p.detection.areaKm2.toFixed(1)} km²</span>
            </div>
            <div className="spec-item">
              <span className="spec-label">Centroid</span>
              <span className="spec-value mono">
                {p.detection.centroid.latitude.toFixed(2)}°N, {p.detection.centroid.longitude.toFixed(2)}°E
              </span>
            </div>
          </div>

          <div className="confidence-meter-box">
            <div className="meter-header">
              <span className="meter-label">Detection Confidence</span>
              <span className="meter-val" style={{ color: '#34d399' }}>{confPercent}%</span>
            </div>
            <div className="meter-track">
              <div
                className="meter-fill"
                style={{
                  width: `${confPercent}%`,
                  background: 'linear-gradient(90deg, #059669 0%, #34d399 100%)',
                }}
              />
            </div>
          </div>
        </section>

        {/* Backward Drift Card */}
        <section className="panel-card">
          <div className="card-section-header">
            <h3 className="section-title">🌊 Backward Drift (P2 OpenDrift)</h3>
            <span className="card-pill-info">12h Hindcast</span>
          </div>

          <div className="spec-grid">
            <div className="spec-item">
              <span className="spec-label">Hindcast Model</span>
              <span className="spec-value">{p.driftSimulation.model}</span>
            </div>
            <div className="spec-item">
              <span className="spec-label">Release Window</span>
              <span className="spec-value mono">{formatAcquisitionTime(p.driftSimulation.estimatedReleaseWindow.startTime)}</span>
            </div>
            <div className="spec-item full-width">
              <span className="spec-label">Source Probability</span>
              <span className="spec-value highlighted" style={{ color: '#fbbf24' }}>
                {Math.round(p.driftSimulation.sourceConfidence * 100)}%
              </span>
            </div>
          </div>
        </section>

        {/* Top 3 Correlated Vessels Card */}
        <section className="panel-card">
          <Top3Display
            topVessels={p.associationAnalysis.topAssociatedVessels}
            onVesselSelect={p.onVesselSelect}
            selectedMmsi={p.selectedVessel?.mmsi}
          />
        </section>

        {/* AIS Traffic Summary */}
        <section className="panel-card">
          <h3 className="section-title">📊 AIS Traffic Summary</h3>
          <div className="traffic-stats-row">
            <div className="traffic-stat-card">
              <span className="stat-big">{p.candidateStats.totalVessels}</span>
              <span className="stat-sub">Vessels in ROI</span>
            </div>
            <div className="traffic-stat-card">
              <span className="stat-big highlighted" style={{ color: '#fbbf24' }}>
                {p.candidateStats.investigationCandidates}
              </span>
              <span className="stat-sub">Candidates</span>
            </div>
            <div className="traffic-stat-card">
              <span className="stat-big highlighted" style={{ color: '#38bdf8' }}>
                {p.associationAnalysis.topAssociatedVessels.slice(0, 3).length}
              </span>
              <span className="stat-sub">Ranked (Top 3)</span>
            </div>
          </div>
        </section>

        {/* Methodology & Legal Disclaimer Disclosure */}
        <MethodologyDisclaimer />
      </div>
    </div>
  )
}
