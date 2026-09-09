interface VesselMarkerProps {
  name: string
  mmsi: number
  rank?: number
  heading: number
  speedKmh: number
  isSelected?: boolean
  onClick?: () => void
}

/**
 * Directional vessel marker that rotates according to interpolated heading.
 * Color-coded according to association rank:
 * - Rank 1: Red (#ff3030)
 * - Rank 2: Yellow (#ffd21f)
 * - Rank 3: Green (#28c76f)
 * - Other: Cyan (#38bdf8)
 */
export default function VesselMarker({
  name,
  mmsi,
  rank,
  heading,
  speedKmh,
  isSelected,
  onClick,
}: VesselMarkerProps) {
  let rankColor = '#38bdf8'
  let rankBorder = 'rgba(56, 189, 248, 0.4)'
  let rankBadge = ''

  if (rank === 1) {
    rankColor = '#ff3030'
    rankBorder = 'rgba(255, 48, 48, 0.6)'
    rankBadge = '#1'
  } else if (rank === 2) {
    rankColor = '#ffd21f'
    rankBorder = 'rgba(255, 210, 31, 0.6)'
    rankBadge = '#2'
  } else if (rank === 3) {
    rankColor = '#28c76f'
    rankBorder = 'rgba(40, 199, 111, 0.6)'
    rankBadge = '#3'
  }

  return (
    <div
      className={`vessel-temporal-marker ${isSelected ? 'selected' : ''}`}
      onClick={(e) => {
        e.stopPropagation()
        onClick?.()
      }}
      title={`${name} (MMSI: ${mmsi}) — Heading: ${heading}° · Speed: ${speedKmh} km/h`}
      role="button"
      tabIndex={0}
    >
      {/* Rotated vessel hull icon */}
      <div
        className="vessel-heading-rotator"
        style={{ transform: `rotate(${heading}deg)` }}
        aria-hidden="true"
      >
        <svg
          viewBox="0 0 24 32"
          width="20"
          height="28"
          className="vessel-hull-svg"
          style={{ filter: isSelected ? 'drop-shadow(0 0 6px #fff)' : `drop-shadow(0 0 4px ${rankColor})` }}
        >
          {/* Arrow / Vessel hull polygon pointing straight UP (0 deg) */}
          <path
            d="M 12,2 L 21,24 L 12,19 L 3,24 Z"
            fill={rankColor}
            stroke="#ffffff"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
          {/* Forward direction beam */}
          <line
            x1="12"
            y1="2"
            x2="12"
            y2="10"
            stroke="#ffffff"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>
      </div>

      {/* Floating label pill */}
      <div className="vessel-marker-label" style={{ borderColor: rankBorder }}>
        {rankBadge && <span className="vessel-rank-badge" style={{ backgroundColor: rankColor }}>{rankBadge}</span>}
        <span className="vessel-name-text">{name}</span>
        <span className="vessel-speed-text">{speedKmh} km/h</span>
      </div>
    </div>
  )
}
