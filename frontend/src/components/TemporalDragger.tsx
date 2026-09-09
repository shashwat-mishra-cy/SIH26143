import { useState, useMemo, useRef } from 'react'
import type { TimestampProvenance } from '../types/temporal'

interface TemporalDraggerProps {
  detectionTimeMs: number
  startTimeMs: number
  selectedTimeMs: number
  isPlaying: boolean
  playbackSpeed: number
  provenance: TimestampProvenance
  onTimeChange: (timeMs: number) => void
  onTogglePlay: () => void
  onSpeedChange: (speed: number) => void
  onResetToDetection: () => void
  onUpdateDetectionTime?: (isoString: string) => void
}

/**
 * Interactive Temporal Reconstruction Dragger (SIH26143).
 * Backward timeline control:
 * - Rightmost position = Spill Detection Time (T = 0)
 * - Dragging right -> left selects earlier historical timestamps
 */
export default function TemporalDragger({
  detectionTimeMs,
  startTimeMs,
  selectedTimeMs,
  isPlaying,
  playbackSpeed,
  provenance,
  onTimeChange,
  onTogglePlay,
  onSpeedChange,
  onResetToDetection,
  onUpdateDetectionTime,
}: TemporalDraggerProps) {
  const [showTimeEditor, setShowTimeEditor] = useState(false)
  const [customTimeInput, setCustomTimeInput] = useState('')
  const [isPointerDragging, setIsPointerDragging] = useState(false)
  const trackRef = useRef<HTMLDivElement>(null)

  const totalDurationMs = Math.max(1, detectionTimeMs - startTimeMs)
  // Value from 0 (earliest) to 1000 (detection time)
  const sliderValue = Math.min(
    1000,
    Math.max(0, Math.round(((selectedTimeMs - startTimeMs) / totalDurationMs) * 1000)),
  )

  const offsetMs = detectionTimeMs - selectedTimeMs
  const offsetHours = Math.floor(offsetMs / (1000 * 60 * 60))
  const offsetMinutes = Math.floor((offsetMs % (1000 * 60 * 60)) / (1000 * 60))
  const offsetSeconds = Math.floor((offsetMs % (1000 * 60)) / 1000)

  const offsetString =
    offsetMs <= 0
      ? 'T = 00:00:00 (Spill Detection)'
      : `T - ${String(offsetHours).padStart(2, '0')}h ${String(offsetMinutes).padStart(2, '0')}m ${String(offsetSeconds).padStart(2, '0')}s`

  const currentUtcString = useMemo(() => {
    try {
      return new Date(selectedTimeMs).toISOString().replace('.000Z', ' UTC').replace('T', ' ')
    } catch {
      return 'Invalid Time'
    }
  }, [selectedTimeMs])

  const detectionUtcString = useMemo(() => {
    try {
      return new Date(detectionTimeMs).toISOString().replace('.000Z', ' UTC').replace('T', ' ')
    } catch {
      return 'Unavailable'
    }
  }, [detectionTimeMs])

  function updateTimeFromClientX(clientX: number) {
    if (!trackRef.current) return
    const rect = trackRef.current.getBoundingClientRect()
    if (rect.width <= 0) return
    const fraction = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width))
    const newTimeMs = Math.round(startTimeMs + fraction * totalDurationMs)
    onTimeChange(newTimeMs)
  }

  function handlePointerDown(e: React.PointerEvent<HTMLDivElement>) {
    if (e.button !== 0) return
    e.stopPropagation()
    e.preventDefault()
    try {
      e.currentTarget.setPointerCapture(e.pointerId)
    } catch {
      // ignore
    }
    setIsPointerDragging(true)
    updateTimeFromClientX(e.clientX)
  }

  function handlePointerMove(e: React.PointerEvent<HTMLDivElement>) {
    if (!isPointerDragging) return
    e.stopPropagation()
    e.preventDefault()
    updateTimeFromClientX(e.clientX)
  }

  function handlePointerUp(e: React.PointerEvent<HTMLDivElement>) {
    if (!isPointerDragging) return
    e.stopPropagation()
    e.preventDefault()
    setIsPointerDragging(false)
    try {
      e.currentTarget.releasePointerCapture(e.pointerId)
    } catch {
      // ignore
    }
  }

  function handleSliderChange(e: React.ChangeEvent<HTMLInputElement>) {
    const val = parseInt(e.target.value, 10)
    const newTimeMs = Math.round(startTimeMs + (val / 1000) * totalDurationMs)
    onTimeChange(newTimeMs)
  }

  function handleStepBackward() {
    // Step 15 minutes backward
    const stepMs = 15 * 60 * 1000
    onTimeChange(Math.max(startTimeMs, selectedTimeMs - stepMs))
  }

  function handleStepForward() {
    // Step 15 minutes forward
    const stepMs = 15 * 60 * 1000
    onTimeChange(Math.min(detectionTimeMs, selectedTimeMs + stepMs))
  }

  function handleSaveObservationTime() {
    if (!customTimeInput.trim()) return
    try {
      const parsed = new Date(customTimeInput).toISOString()
      onUpdateDetectionTime?.(parsed)
      setShowTimeEditor(false)
    } catch {
      alert('Please enter a valid ISO UTC timestamp, e.g. 2025-01-01T12:00:00Z')
    }
  }

  return (
    <div
      className="temporal-dragger-shell"
      aria-label="Interactive Temporal Reconstruction Timeline"
      onMouseDown={(e) => e.stopPropagation()}
      onPointerDown={(e) => e.stopPropagation()}
      onTouchStart={(e) => e.stopPropagation()}
      onDoubleClick={(e) => e.stopPropagation()}
    >
      <div className="dragger-main-row">
        {/* Play / Step Buttons */}
        <div className="dragger-transport-controls">
          <button
            type="button"
            className="dragger-btn step-btn"
            onClick={handleStepBackward}
            title="Step backward 15 minutes"
            aria-label="Step backward 15 minutes"
          >
            ◀ 15m
          </button>

          <button
            type="button"
            className={`dragger-btn play-btn ${isPlaying ? 'playing' : ''}`}
            onClick={onTogglePlay}
            title={isPlaying ? 'Pause temporal reconstruction' : 'Play backward reconstruction'}
            aria-label={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? '⏸ PAUSE' : '▶ PLAY'}
          </button>

          <button
            type="button"
            className="dragger-btn step-btn"
            onClick={handleStepForward}
            title="Step forward 15 minutes"
            aria-label="Step forward 15 minutes"
          >
            15m ▶
          </button>

          <button
            type="button"
            className="dragger-btn reset-btn"
            onClick={onResetToDetection}
            title="Jump to Detection Time (T = 0)"
            aria-label="Reset to detection time"
          >
            ↺ DETECTION
          </button>
        </div>

        {/* Center Timeline Track & Slider */}
        <div className="dragger-track-container">
          <div className="dragger-time-labels">
            <span className="dragger-label-start">
              ← Historical Origin ({new Date(startTimeMs).toISOString().slice(11, 16)} UTC)
            </span>
            <div className="dragger-current-badge">
              <span className="dragger-badge-clock">⏱</span>
              <span className="dragger-badge-utc">{currentUtcString}</span>
              <span className="dragger-badge-offset">{offsetString}</span>
            </div>
            <span className="dragger-label-end">
              Spill Detection ({new Date(detectionTimeMs).toISOString().slice(11, 16)} UTC) →
            </span>
          </div>

          <div
            ref={trackRef}
            className={`dragger-slider-wrapper ${isPointerDragging ? 'active-dragging' : ''}`}
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            onPointerCancel={handlePointerUp}
            onMouseDown={(e) => {
              e.stopPropagation()
              e.preventDefault()
            }}
          >
            <div className="dragger-track-rail" />
            <div
              className="dragger-fill-bar"
              style={{ width: `${sliderValue / 10}%` }}
            />
            <div
              className="dragger-anchor-marker detection-marker"
              title="Spill Detection Point (Rightmost)"
            />
            {/* Custom Interactive Dragger Thumb */}
            <div
              className={`dragger-custom-thumb ${isPointerDragging ? 'dragging' : ''}`}
              style={{ left: `${sliderValue / 10}%` }}
              title="Drag backward or forward in time"
            />
            <input
              type="range"
              min="0"
              max="1000"
              value={sliderValue}
              onChange={handleSliderChange}
              onInput={handleSliderChange}
              className="dragger-range-slider-hidden"
              aria-label="Investigation timeline backward dragger"
              tabIndex={0}
            />
          </div>
        </div>

        {/* Speed & Provenance Controls */}
        <div className="dragger-aux-controls">
          <label className="dragger-speed-select-label" title="Playback speed">
            <span className="speed-icon">⚡</span>
            <select
              value={playbackSpeed}
              onChange={(e) => onSpeedChange(parseFloat(e.target.value))}
              className="dragger-speed-select"
            >
              <option value="1">1x</option>
              <option value="2">2x</option>
              <option value="5">5x</option>
              <option value="10">10x</option>
            </select>
          </label>

          <button
            type="button"
            className="dragger-provenance-pill"
            onClick={() => {
              setCustomTimeInput(new Date(detectionTimeMs).toISOString())
              setShowTimeEditor((prev) => !prev)
            }}
            title="Observation / Acquisition Time Provenance & Settings (Section 7)"
          >
            <span className="provenance-dot" />
            <span className="provenance-text">
              {provenance === 'satellite_metadata'
                ? 'SAR Metadata'
                : provenance === 'user_provided'
                  ? 'User UTC'
                  : 'No Timestamp'}
            </span>
          </button>
        </div>
      </div>

      {/* Observation Time Editor Modal (Section 7 & 8) */}
      {showTimeEditor && (
        <div className="dragger-time-editor-modal">
          <div className="editor-modal-header">
            <h4>Observation / Acquisition Time (UTC)</h4>
            <button
              type="button"
              className="editor-close-btn"
              onClick={() => setShowTimeEditor(false)}
            >
              ✕
            </button>
          </div>
          <p className="editor-modal-desc">
            The timeline depends on a valid observation/acquisition timestamp. Provenance:{' '}
            <strong>
              {provenance === 'satellite_metadata'
                ? 'Satellite SAR Metadata (Sentinel-1)'
                : provenance === 'user_provided'
                  ? 'Manual Investigator Input'
                  : 'Unavailable'}
            </strong>
          </p>
          <div className="editor-input-row">
            <input
              type="text"
              value={customTimeInput}
              onChange={(e) => setCustomTimeInput(e.target.value)}
              placeholder="YYYY-MM-DDTHH:MM:SSZ"
              className="editor-time-input"
            />
            <button
              type="button"
              className="editor-save-btn"
              onClick={handleSaveObservationTime}
            >
              Apply & Synchronize
            </button>
          </div>
          <div className="editor-active-ref">Active Detection Time: {detectionUtcString}</div>
        </div>
      )}
    </div>
  )
}
