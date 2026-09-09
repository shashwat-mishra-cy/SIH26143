import { REGION_LABEL, BASEMAP_CONFIGS } from '../config/map'
import type { BasemapId } from '../config/map'

interface StatusBarProps {
  activeBasemap?: BasemapId
}

/**
 * Bottom status bar — system status, region, basemap provider, and viewport reference.
 */
export default function StatusBar({ activeBasemap = 'satellite' }: StatusBarProps) {
  const currentBasemap = BASEMAP_CONFIGS[activeBasemap]

  return (
    <footer className="status-bar">
      <span className="status-item">
        <span className="status-dot status-dot-green" aria-hidden="true" />
        System Online
      </span>
      <span className="status-item">{REGION_LABEL}</span>
      <span className="status-item">18.52°N 72.85°E</span>
      <span className="status-item">
        <span className="status-basemap-badge">{currentBasemap.icon} {currentBasemap.name}</span>
      </span>
      <span className="status-item">MapLibre GL</span>
      <span className="status-item status-right">SIH26143 · Phase 2</span>
    </footer>
  )
}