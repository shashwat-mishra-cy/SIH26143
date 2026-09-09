import { useState, useMemo, useEffect } from 'react'
import TopNavbar from './components/TopNavbar'
import MaritimeMap from './components/MaritimeMap'
import InvestigationPanel from './components/InvestigationPanel'
import DraggablePanel from './components/DraggablePanel'
import StatusBar from './components/StatusBar'
import KpiStrip from './components/KpiStrip'
import SatelliteUploadModal from './components/SatelliteUploadModal'
import { DEMO_SATELLITE_DETECTION } from './data/demo/satellite'
import { DEMO_DRIFT_SIMULATION } from './data/demo/drift'
import { DEMO_AIS_DATASET } from './data/demo/ais'
import { buildAISCandidates, calculateCandidateStats } from './analysis/aisCandidateFilter'
import { buildAssociationAnalysis } from './analysis/aisAssociationScore'
import { buildAnomalyAnalysis } from './analysis/aisAnomalyAnalysis'
import type { BasemapId } from './config/map'
import type { SatelliteDetection } from './types/satellite'
import type { TimestampProvenance } from './types/temporal'

export default function App() {
  const [currentDetection, setCurrentDetection] = useState<SatelliteDetection>(DEMO_SATELLITE_DETECTION)
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [selectedSpillId, setSelectedSpillId] = useState<string | null>(DEMO_SATELLITE_DETECTION.spillId)
  const [selectedSourceRegionId, setSelectedSourceRegionId] = useState<string | null>(null)
  const [selectedVesselMmsi, setSelectedVesselMmsi] = useState<number | null>(null)
  const [showSpillLayer, setShowSpillLayer] = useState(true)
  const [showDriftLayer, setShowDriftLayer] = useState(true)
  const [showSourceLayer, setShowSourceLayer] = useState(true)
  const [showAISLayer, setShowAISLayer] = useState(true)
  const [showLabels, setShowLabels] = useState(true)
  const [showSeamarks, setShowSeamarks] = useState(false)
  const [activeBasemap, setActiveBasemap] = useState<BasemapId>('satellite')

  // Interactive Temporal Reconstruction (Dragger) State
  const initialDetectionTimeMs = useMemo(
    () => new Date(DEMO_SATELLITE_DETECTION.timestamp).getTime(),
    [],
  )
  const [detectionTimeMs, setDetectionTimeMs] = useState(initialDetectionTimeMs)
  const [startTimeMs, setStartTimeMs] = useState(initialDetectionTimeMs - 12 * 60 * 60 * 1000)
  // Rightmost anchor = detection time (T = 0)
  const [selectedTimeMs, setSelectedTimeMs] = useState(initialDetectionTimeMs)
  const [isPlaying, setIsPlaying] = useState(false)
  const [playbackSpeed, setPlaybackSpeed] = useState(1)
  const [provenance, setProvenance] = useState<TimestampProvenance>('satellite_metadata')

  // Backward playback animation loop
  useEffect(() => {
    if (!isPlaying) return
    const intervalMs = 120
    const timer = setInterval(() => {
      setSelectedTimeMs((prev) => {
        // Step backward by (1 minute * playbackSpeed)
        const step = 60 * 1000 * playbackSpeed
        const next = prev - step
        if (next <= startTimeMs) {
          setIsPlaying(false)
          return startTimeMs
        }
        return next
      })
    }, intervalMs)
    return () => clearInterval(timer)
  }, [isPlaying, playbackSpeed, startTimeMs])

  function handleResetToDetection() {
    setIsPlaying(false)
    setSelectedTimeMs(detectionTimeMs)
  }

  function handleUpdateDetectionTime(isoString: string) {
    try {
      const ms = new Date(isoString).getTime()
      if (isNaN(ms)) return
      setDetectionTimeMs(ms)
      setStartTimeMs(ms - 12 * 60 * 60 * 1000)
      setSelectedTimeMs(ms)
      setProvenance('user_provided')
      setIsPlaying(false)
    } catch {
      // ignore
    }
  }

  function handleLoadUploadedDetection(newDetection: SatelliteDetection, newProvenance: TimestampProvenance) {
    setCurrentDetection(newDetection)
    setSelectedSpillId(newDetection.spillId)
    try {
      const ms = new Date(newDetection.timestamp).getTime()
      if (!isNaN(ms)) {
        setDetectionTimeMs(ms)
        setStartTimeMs(ms - 12 * 60 * 60 * 1000)
        setSelectedTimeMs(ms)
        setProvenance(newProvenance)
        setIsPlaying(false)
      }
    } catch {
      // ignore
    }
  }

  const selectedVessel = selectedVesselMmsi
    ? DEMO_AIS_DATASET.vessels.find((v) => v.mmsi === selectedVesselMmsi)
    : undefined
  const candidateResults = useMemo(() => buildAISCandidates(DEMO_AIS_DATASET), [])
  const candidateStats = useMemo(() => calculateCandidateStats(candidateResults), [candidateResults])
  const associationAnalysis = useMemo(
    () => buildAssociationAnalysis(DEMO_AIS_DATASET.vessels, candidateResults),
    [candidateResults],
  )
  const associationByMmsi = useMemo(
    () => new Map(associationAnalysis.allResults.map((a) => [a.mmsi, a])),
    [associationAnalysis],
  )
  const anomalyAnalysis = useMemo(() => buildAnomalyAnalysis(DEMO_AIS_DATASET.vessels), [])
  const anomalyByMmsi = useMemo(
    () => new Map(anomalyAnalysis.allResults.map((a) => [a.mmsi, a])),
    [anomalyAnalysis],
  )

  return (
    <div className="app-shell">
      <TopNavbar onOpenUpload={() => setIsUploadModalOpen(true)} />
      <KpiStrip
        detection={currentDetection}
        driftSimulation={DEMO_DRIFT_SIMULATION}
        aisDataset={DEMO_AIS_DATASET}
        candidateStats={candidateStats}
        associationAnalysis={associationAnalysis}
      />
      <main className="main-area">
        <section className="map-container" aria-label="Geographic map">
          <MaritimeMap
            detection={currentDetection}
            driftSimulation={DEMO_DRIFT_SIMULATION}
            aisDataset={DEMO_AIS_DATASET}
            selectedSpillId={selectedSpillId}
            selectedSourceRegionId={selectedSourceRegionId}
            selectedVesselMmsi={selectedVesselMmsi}
            showSpillLayer={showSpillLayer}
            showDriftLayer={showDriftLayer}
            showSourceLayer={showSourceLayer}
            showAISLayer={showAISLayer}
            showLabels={showLabels}
            showSeamarks={showSeamarks}
            activeBasemap={activeBasemap}
            // Temporal reconstruction props
            selectedTimeMs={selectedTimeMs}
            detectionTimeMs={detectionTimeMs}
            startTimeMs={startTimeMs}
            isPlaying={isPlaying}
            playbackSpeed={playbackSpeed}
            provenance={provenance}
            onTimeChange={setSelectedTimeMs}
            onTogglePlay={() => setIsPlaying((prev) => !prev)}
            onSpeedChange={setPlaybackSpeed}
            onResetToDetection={handleResetToDetection}
            onUpdateDetectionTime={handleUpdateDetectionTime}
            // Selection handlers
            onSpillSelect={setSelectedSpillId}
            onSourceRegionSelect={setSelectedSourceRegionId}
            onVesselSelect={setSelectedVesselMmsi}
            onToggleSpillLayer={setShowSpillLayer}
            onToggleDriftLayer={setShowDriftLayer}
            onToggleSourceLayer={setShowSourceLayer}
            onToggleAISLayer={setShowAISLayer}
            onToggleLabels={setShowLabels}
            onToggleSeamarks={setShowSeamarks}
            onChangeBasemap={setActiveBasemap}
            topAssociatedVessels={associationAnalysis.topAssociatedVessels}
          />
        </section>
        <DraggablePanel initialWidth={380} minWidth={330} maxWidth={650}>
          <aside className="investigation-panel" aria-label="Investigation panel">
            <InvestigationPanel
              detection={currentDetection}
              driftSimulation={DEMO_DRIFT_SIMULATION}
              aisDataset={DEMO_AIS_DATASET}
              selected={selectedSpillId === currentDetection.spillId}
              sourceRegionSelected={selectedSourceRegionId === DEMO_DRIFT_SIMULATION.sourceRegion.id}
              selectedVessel={selectedVessel}
              candidateStats={candidateStats}
              selectedVesselCandidate={selectedVesselMmsi ? associationByMmsi.get(selectedVesselMmsi) : undefined}
              associationAnalysis={associationAnalysis}
              anomalyAnalysis={anomalyAnalysis}
              selectedVesselAnomaly={selectedVesselMmsi ? anomalyByMmsi.get(selectedVesselMmsi) : undefined}
              selectedTimeMs={selectedTimeMs}
              detectionTimeMs={detectionTimeMs}
              onVesselSelect={setSelectedVesselMmsi}
            />
          </aside>
        </DraggablePanel>
      </main>
      <StatusBar activeBasemap={activeBasemap} />

      {/* Module P1 Satellite Ingestion & ML Detection Modal */}
      <SatelliteUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onLoadDetection={handleLoadUploadedDetection}
      />
    </div>
  )
}
