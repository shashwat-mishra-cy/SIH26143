interface LayerControlProps {
  showSpillLayer: boolean
  showDriftLayer: boolean
  showSourceLayer: boolean
  showAISLayer: boolean
  showLabels: boolean
  showSeamarks: boolean
  onToggleSpillLayer: (visible: boolean) => void
  onToggleDriftLayer: (visible: boolean) => void
  onToggleSourceLayer: (visible: boolean) => void
  onToggleAISLayer: (visible: boolean) => void
  onToggleLabels: (visible: boolean) => void
  onToggleSeamarks: (visible: boolean) => void
}

/**
 * Map layer control — toggles intelligence layers and marine cartographic overlays.
 */
export default function LayerControl({
  showSpillLayer,
  showDriftLayer,
  showSourceLayer,
  showAISLayer,
  showLabels,
  showSeamarks,
  onToggleSpillLayer,
  onToggleDriftLayer,
  onToggleSourceLayer,
  onToggleAISLayer,
  onToggleLabels,
  onToggleSeamarks,
}: LayerControlProps) {
  return (
    <div className="layer-control" aria-label="Map layers">
      <div className="layer-control-header">Intelligence Layers</div>
      <label className="layer-control-item">
        <input
          type="checkbox"
          checked={showSpillLayer}
          onChange={(event) => onToggleSpillLayer(event.target.checked)}
        />
        <span className="layer-swatch swatch-spill" aria-hidden="true" />
        <span className="layer-control-label">Detected Oil Spill</span>
      </label>
      <label className="layer-control-item">
        <input
          type="checkbox"
          checked={showDriftLayer}
          onChange={(event) => onToggleDriftLayer(event.target.checked)}
        />
        <span className="layer-swatch swatch-drift" aria-hidden="true" />
        <span className="layer-control-label">Backward Drift</span>
      </label>
      <label className="layer-control-item">
        <input
          type="checkbox"
          checked={showSourceLayer}
          onChange={(event) => onToggleSourceLayer(event.target.checked)}
        />
        <span className="layer-swatch swatch-source" aria-hidden="true" />
        <span className="layer-control-label">Probable Source</span>
      </label>
      <label className="layer-control-item">
        <input
          type="checkbox"
          checked={showAISLayer}
          onChange={(event) => onToggleAISLayer(event.target.checked)}
        />
        <span className="layer-swatch swatch-ais" aria-hidden="true" />
        <span className="layer-control-label">AIS Trajectories</span>
      </label>

      <div className="layer-control-divider" />
      <div className="layer-control-header">Marine Overlays</div>
      <label className="layer-control-item">
        <input
          type="checkbox"
          checked={showLabels}
          onChange={(event) => onToggleLabels(event.target.checked)}
        />
        <span className="layer-swatch swatch-labels" aria-hidden="true" />
        <span className="layer-control-label">Coast & Place Labels</span>
      </label>
      <label className="layer-control-item">
        <input
          type="checkbox"
          checked={showSeamarks}
          onChange={(event) => onToggleSeamarks(event.target.checked)}
        />
        <span className="layer-swatch swatch-seamarks" aria-hidden="true" />
        <span className="layer-control-label">Nautical Seamarks (OpenSeaMap)</span>
      </label>
    </div>
  )
}