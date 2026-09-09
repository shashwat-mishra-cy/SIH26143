interface ScoreBarProps {
  label: string
  score: number
  max?: number
}

export function ScoreBar({ label, score, max = 100 }: ScoreBarProps) {
  const percentage = (score / max) * 100
  return (
    <div className="score-bar-container">
      <div className="score-bar-label">{label}</div>
      <div className="score-bar-wrapper">
        <div className="score-bar" style={{ width: `${percentage}%` }} />
      </div>
      <div className="score-bar-value">{score}</div>
    </div>
  )
}

interface AssociationScoreBreakdownProps {
  temporalScore: number
  proximityScore: number
  trajectoryScore: number
  totalScore: number
}

export default function AssociationScoreBreakdown({
  temporalScore,
  proximityScore,
  trajectoryScore,
  totalScore,
}: AssociationScoreBreakdownProps) {
  return (
    <div className="score-breakdown">
      <div className="breakdown-title">Association Score Breakdown</div>
      <div className="breakdown-total">
        <span className="total-label">Total Score</span>
        <span className="total-value">{totalScore} / 100</span>
      </div>
      <div className="breakdown-components">
        <ScoreBar label="Temporal Compatibility" score={temporalScore} />
        <ScoreBar label="Source Proximity" score={proximityScore} />
        <ScoreBar label="Trajectory Compatibility" score={trajectoryScore} />
      </div>
    </div>
  )
}
