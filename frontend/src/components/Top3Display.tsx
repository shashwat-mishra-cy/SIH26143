import type { AISAssociationResult } from '../analysis/aisAssociationScore'

interface Top3DisplayProps {
  topVessels: AISAssociationResult[]
  onVesselSelect?: (mmsi: number) => void
  selectedMmsi?: number | null
}

const RANK_ACCENTS = [
  { color: '#ef4444', glow: 'rgba(239, 68, 68, 0.25)', label: 'Primary Suspect' },
  { color: '#f59e0b', glow: 'rgba(245, 158, 11, 0.25)', label: 'Secondary Suspect' },
  { color: '#10b981', glow: 'rgba(16, 185, 129, 0.25)', label: 'Tertiary Suspect' },
]

export default function Top3Display({ topVessels, onVesselSelect, selectedMmsi }: Top3DisplayProps) {
  return (
    <div className="top3-display">
      <div className="top3-header-row">
        <span className="top3-title">🚢 Top Correlated Vessels (P3)</span>
        <span className="top3-badge">Top 3 Only</span>
      </div>

      <div className="top3-list">
        {topVessels.length > 0 ? (
          topVessels.slice(0, 3).map((vessel, idx) => {
            const accent = RANK_ACCENTS[idx] ?? RANK_ACCENTS[0]
            const isSelected = selectedMmsi === vessel.mmsi
            const score = vessel.associationScore
            const dist = vessel.minimumSourceDistanceKm !== undefined
              ? `${vessel.minimumSourceDistanceKm.toFixed(1)} km`
              : '—'

            return (
              <div
                key={vessel.mmsi}
                className={`top3-card ${isSelected ? 'selected' : ''}`}
                onClick={() => onVesselSelect?.(vessel.mmsi)}
                style={{
                  borderLeftColor: accent.color,
                  boxShadow: isSelected ? `0 0 14px ${accent.glow}` : undefined,
                }}
                role="button"
                tabIndex={0}
                title={`Click to inspect correlation details for ${vessel.vesselName}`}
              >
                <div className="top3-card-top">
                  <div className="top3-rank-group">
                    <span
                      className="top3-rank-pill"
                      style={{ backgroundColor: accent.color }}
                    >
                      #{idx + 1}
                    </span>
                    <span className="top3-vessel-name">{vessel.vesselName}</span>
                  </div>

                  <div className="top3-score-pill">
                    <span className="score-num" style={{ color: accent.color }}>
                      {score}
                    </span>
                    <span className="score-max">/100</span>
                  </div>
                </div>

                {/* Score Progress Bar */}
                <div className="top3-bar-track">
                  <div
                    className="top3-bar-fill"
                    style={{
                      width: `${Math.min(100, Math.max(0, score))}%`,
                      background: `linear-gradient(90deg, ${accent.color}88, ${accent.color})`,
                    }}
                  />
                </div>

                <div className="top3-card-bottom">
                  <span className="top3-dist">
                    📍 Min Dist: <strong>{dist}</strong>
                  </span>
                  <span className="top3-mmsi">MMSI: {vessel.mmsi}</span>
                </div>
              </div>
            )
          })
        ) : (
          <div className="top3-empty">No vessels correlated within release window</div>
        )}
      </div>
    </div>
  )
}
