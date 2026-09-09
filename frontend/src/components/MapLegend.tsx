/**
 * Map legend — detected spill, backward drift, probable source region, and AIS trajectories.
 * Updated to match SIH26143 Interactive Dragger specifications (Section 6).
 */
export default function MapLegend() {
  return (
    <div
      className="map-legend"
      aria-label="Map legend"
      onMouseDown={(e) => e.stopPropagation()}
      onPointerDown={(e) => e.stopPropagation()}
    >
      <div className="legend-header">Legend</div>
      <div className="legend-item">
        <span className="legend-swatch swatch-spill" aria-hidden="true" />
        <span className="legend-label">Detected spill</span>
      </div>
      <div className="legend-item">
        <span className="legend-swatch swatch-centroid" aria-hidden="true" />
        <span className="legend-label">Spill centroid</span>
      </div>
      <div className="legend-item">
        <span className="legend-swatch swatch-drift" aria-hidden="true" />
        <span className="legend-label">Backward drift</span>
      </div>
      <div className="legend-item">
        <span className="legend-swatch swatch-source" aria-hidden="true" />
        <span className="legend-label">Probable source region</span>
      </div>
      <div className="legend-item">
        <span className="legend-swatch" style={{ background: '#e879f9' }} aria-hidden="true" />
        <span className="legend-label">P2 Drift particles</span>
      </div>
      <div className="legend-item">
        <span className="legend-swatch swatch-ais" aria-hidden="true" />
        <span className="legend-label">AIS trajectory</span>
      </div>
      <div className="legend-divider" style={{ height: '1px', background: 'var(--border)', margin: '6px 0' }} />
      <div className="legend-item">
        <span className="legend-swatch" style={{ background: '#ff3030' }} aria-hidden="true" />
        <span className="legend-label">#1 Top Rank (Red)</span>
      </div>
      <div className="legend-item">
        <span className="legend-swatch" style={{ background: '#ffd21f' }} aria-hidden="true" />
        <span className="legend-label">#2 Top Rank (Yellow)</span>
      </div>
      <div className="legend-item">
        <span className="legend-swatch" style={{ background: '#28c76f' }} aria-hidden="true" />
        <span className="legend-label">#3 Top Rank (Green)</span>
      </div>
    </div>
  )
}