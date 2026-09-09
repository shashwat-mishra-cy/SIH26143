import { useState, useRef, useEffect } from 'react'
import type { BasemapId } from '../config/map'
import { BASEMAP_CONFIGS } from '../config/map'

interface BasemapSelectorProps {
  activeBasemap: BasemapId
  onChangeBasemap: (id: BasemapId) => void
}

/**
 * Floating basemap switcher widget.
 * Provides quick toggle between Realistic Satellite Earth, Ocean Bathymetry, Dark Ops, and Chart.
 */
export default function BasemapSelector({ activeBasemap, onChangeBasemap }: BasemapSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  const currentConfig = BASEMAP_CONFIGS[activeBasemap]

  return (
    <div className="basemap-selector-container" ref={dropdownRef} aria-label="Basemap selector">
      <button
        type="button"
        className={`basemap-trigger-btn ${isOpen ? 'active' : ''}`}
        onClick={() => setIsOpen((prev) => !prev)}
        title="Change Earth/Ocean Basemap"
        aria-expanded={isOpen}
      >
        <span className="basemap-trigger-icon" aria-hidden="true">{currentConfig.icon}</span>
        <span className="basemap-trigger-label">{currentConfig.name}</span>
        <span className="basemap-trigger-chevron" aria-hidden="true">{isOpen ? '▲' : '▼'}</span>
      </button>

      {isOpen && (
        <div className="basemap-dropdown-menu" role="menu">
          <div className="basemap-dropdown-header">Realistic Earth & Ocean Basemaps</div>
          {Object.values(BASEMAP_CONFIGS).map((item) => {
            const isSelected = item.id === activeBasemap
            return (
              <button
                key={item.id}
                type="button"
                className={`basemap-option-card ${isSelected ? 'selected' : ''}`}
                onClick={() => {
                  onChangeBasemap(item.id)
                  setIsOpen(false)
                }}
                role="menuitem"
              >
                <div className="basemap-card-header">
                  <span className="basemap-card-icon" aria-hidden="true">{item.icon}</span>
                  <span className="basemap-card-title">{item.name}</span>
                  {isSelected && <span className="basemap-card-badge">ACTIVE</span>}
                </div>
                <div className="basemap-card-desc">{item.subtitle}</div>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
