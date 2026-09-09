import type { SatelliteDetection } from '../types/satellite'
import type { DriftSimulation } from '../types/drift'

interface InvestigationWorkflowProps {
  detection: SatelliteDetection
  driftSimulation: DriftSimulation
}

export default function InvestigationWorkflow({ detection, driftSimulation }: InvestigationWorkflowProps) {
  const sourceConfidence = Math.round(driftSimulation.sourceConfidence * 100)

  return (
    <div className="investigation-workflow">
      <h3 className="workflow-title">Investigation Evidence Chain</h3>
      <div className="workflow-steps">
        <div className="workflow-step">
          <div className="step-number">01</div>
          <div className="step-content">
            <div className="step-label">SATELLITE DETECTION</div>
            <div className="step-detail">{detection.sensor}</div>
            <div className="step-detail">{detection.areaKm2.toFixed(1)} km²</div>
          </div>
        </div>

        <div className="workflow-arrow">↓</div>

        <div className="workflow-step">
          <div className="step-number">02</div>
          <div className="step-content">
            <div className="step-label">BACKWARD DRIFT</div>
            <div className="step-detail">{driftSimulation.model}</div>
            <div className="step-detail">Hindcast: 7 hours</div>
          </div>
        </div>

        <div className="workflow-arrow">↓</div>

        <div className="workflow-step">
          <div className="step-number">03</div>
          <div className="step-content">
            <div className="step-label">PROBABLE SOURCE</div>
            <div className="step-detail">18.45°N · 72.70°E</div>
            <div className="step-detail">Confidence: {sourceConfidence}%</div>
          </div>
        </div>

        <div className="workflow-arrow">↓</div>

        <div className="workflow-step">
          <div className="step-number">04</div>
          <div className="step-content">
            <div className="step-label">AIS CORRELATION</div>
            <div className="step-detail">8 vessels analyzed</div>
            <div className="step-detail">Top 3 ranked</div>
          </div>
        </div>
      </div>
    </div>
  )
}

