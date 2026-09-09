import type { AISAnomalyResult } from '../analysis/aisAnomalyAnalysis'

interface AnomalyEvidenceDisplayProps {
  anomaly: AISAnomalyResult
}

export default function AnomalyEvidenceDisplay({ anomaly }: AnomalyEvidenceDisplayProps) {
  return (
    <div className="anomaly-display">
      <div className="anomaly-title">AIS Behavioral Evidence</div>
      
      <div className="anomaly-score-box">
        <div className="anomaly-main-score">
          <div className="score-value">{anomaly.anomalyEvidenceScore}</div>
          <div className="score-max">/ 100</div>
        </div>
        <div className="score-label">Anomaly Evidence Score</div>
      </div>

      <div className="anomaly-components">
        <div className="component-item">
          <div className="component-label">Speed Deviation</div>
          <div className="component-bar">
            <div className="component-fill" style={{ width: `${anomaly.speedDeviationScore}%` }} />
          </div>
          <div className="component-value">{anomaly.speedDeviationScore}/100</div>
        </div>

        <div className="component-item">
          <div className="component-label">Course Change</div>
          <div className="component-bar">
            <div className="component-fill" style={{ width: `${anomaly.courseChangeScore}%` }} />
          </div>
          <div className="component-value">{anomaly.courseChangeScore}/100</div>
        </div>

        <div className="component-item">
          <div className="component-label">AIS Data Gaps</div>
          <div className="component-bar">
            <div className="component-fill" style={{ width: `${anomaly.aisGapScore}%` }} />
          </div>
          <div className="component-value">{anomaly.aisGapScore}/100</div>
        </div>

        <div className="component-item">
          <div className="component-label">Trajectory Consistency</div>
          <div className="component-bar">
            <div className="component-fill" style={{ width: `${anomaly.trajectoryConsistencyScore}%` }} />
          </div>
          <div className="component-value">{anomaly.trajectoryConsistencyScore}/100</div>
        </div>
      </div>

      {anomaly.evidenceIndicators.length > 0 && (
        <div className="anomaly-indicators">
          <div className="indicators-label">Evidence Indicators:</div>
          <ul className="indicators-list">
            {anomaly.evidenceIndicators.map((indicator: string, idx: number) => (
              <li key={idx} className="indicator-item">
                <span className="indicator-icon">✓</span>
                <span className="indicator-text">{indicator}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="anomaly-note">
        Observational indicators derived from AIS movement history. These indicators do not establish causation.
      </div>
    </div>
  )
}
