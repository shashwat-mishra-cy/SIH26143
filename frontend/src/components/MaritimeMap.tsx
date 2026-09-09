import { useMemo, useRef } from 'react'
import Map, { NavigationControl, ScaleControl, AttributionControl, Source, Layer, Marker } from 'react-map-gl/maplibre'
import type { MapRef } from 'react-map-gl/maplibre'
import type { FeatureCollection, LineString, Point } from 'geojson'
import { INITIAL_VIEW_STATE, BASE_MAP_STYLE, BASEMAP_CONFIGS, SEAMARKS_OVERLAY_CONFIG } from '../config/map'
import type { BasemapId } from '../config/map'
import MapLegend from './MapLegend'
import LayerControl from './LayerControl'
import BasemapSelector from './BasemapSelector'
import VesselMarker from './VesselMarker'
import TemporalDragger from './TemporalDragger'
import { SPILL_LABEL } from '../data/demo/satellite'
import { buildHydrodynamicDriftBundle } from '../geo/driftPolygon'
import { reconstructVesselAtTime } from '../geo/temporalInterpolation'
import { P2_DRIFT_TIMEFRAMES } from '../data/pDataAdapters'
import type { SatelliteDetection } from '../types/satellite'
import type { DriftSimulation } from '../types/drift'
import type { AISDataset } from '../types/ais'
import type { AISAssociationResult } from '../analysis/aisAssociationScore'
import type { TimestampProvenance } from '../types/temporal'

interface MaritimeMapProps {
  detection: SatelliteDetection
  driftSimulation: DriftSimulation
  aisDataset: AISDataset
  selectedSpillId: string | null
  selectedSourceRegionId: string | null
  selectedVesselMmsi: number | null
  showSpillLayer: boolean
  showDriftLayer: boolean
  showSourceLayer: boolean
  showAISLayer: boolean
  showLabels: boolean
  showSeamarks: boolean
  activeBasemap: BasemapId
  // Temporal Dragger props
  selectedTimeMs: number
  detectionTimeMs: number
  startTimeMs: number
  isPlaying: boolean
  playbackSpeed: number
  provenance: TimestampProvenance
  onTimeChange: (timeMs: number) => void
  onTogglePlay: () => void
  onSpeedChange: (speed: number) => void
  onResetToDetection: () => void
  onUpdateDetectionTime?: (isoString: string) => void
  // Selection & Layer handlers
  onSpillSelect: (spillId: string | null) => void
  onSourceRegionSelect: (id: string | null) => void
  onVesselSelect: (mmsi: number | null) => void
  onToggleSpillLayer: (v: boolean) => void
  onToggleDriftLayer: (v: boolean) => void
  onToggleSourceLayer: (v: boolean) => void
  onToggleAISLayer: (v: boolean) => void
  onToggleLabels: (v: boolean) => void
  onToggleSeamarks: (v: boolean) => void
  onChangeBasemap: (id: BasemapId) => void
  topAssociatedVessels?: AISAssociationResult[]
}

export default function MaritimeMap(p: MaritimeMapProps) {
  const mapRef = useRef<MapRef>(null)
  const basemapConfig = BASEMAP_CONFIGS[p.activeBasemap] ?? BASEMAP_CONFIGS.satellite

  // Rank mapping for top 3 associated vessels
  const rankByMmsi = useMemo(() => {
    const map = new globalThis.Map<number, number>()
    p.topAssociatedVessels?.slice(0, 3).forEach((v, idx) => {
      map.set(v.mmsi, idx + 1)
    })
    return map
  }, [p.topAssociatedVessels])

  // Core Temporal Reconstruction: compute dynamic backward trails and interpolated vessel positions
  const reconstructedVessels = useMemo(() => {
    return p.aisDataset.vessels.map((v) => {
      const rank = rankByMmsi.get(v.mmsi)
      return reconstructVesselAtTime(
        {
          mmsi: v.mmsi,
          name: v.name,
          rank,
          points: v.points,
        },
        p.selectedTimeMs,
        p.detectionTimeMs,
        p.detection.centroid,
      )
    })
  }, [p.aisDataset.vessels, p.selectedTimeMs, p.detectionTimeMs, rankByMmsi, p.detection.centroid])

  // Dynamic GeoJSON for backward trajectory trails (selected_time <= timestamp <= detection_time)
  const dynamicTrajectoryGeoJson: FeatureCollection<LineString> = useMemo(() => {
    return {
      type: 'FeatureCollection',
      features: reconstructedVessels
        .filter((v) => Boolean(v.rank && v.rank >= 1 && v.rank <= 3) && v.trailCoordinates.length >= 2)
        .map((v) => ({
          type: 'Feature' as const,
          id: `trail-${v.mmsi}`,
          properties: {
            mmsi: v.mmsi,
            name: v.name,
            rank: v.rank ?? 0,
            selected: v.mmsi === p.selectedVesselMmsi,
          },
          geometry: {
            type: 'LineString' as const,
            coordinates: v.trailCoordinates,
          },
        })),
    }
  }, [reconstructedVessels, p.selectedVesselMmsi])

  // Dynamic P2 drift particles frame matching the selected time
  const driftParticlesGeoJson: FeatureCollection<Point> = useMemo(() => {
    if (P2_DRIFT_TIMEFRAMES.length === 0) {
      return { type: 'FeatureCollection', features: [] }
    }
    // Find closest frame to selectedTimeMs
    let closest = P2_DRIFT_TIMEFRAMES[0]
    let minDiff = Math.abs(P2_DRIFT_TIMEFRAMES[0].timestampMs - p.selectedTimeMs)
    for (const frame of P2_DRIFT_TIMEFRAMES) {
      const diff = Math.abs(frame.timestampMs - p.selectedTimeMs)
      if (diff < minDiff) {
        minDiff = diff
        closest = frame
      }
    }
    return {
      type: 'FeatureCollection',
      features: closest.particles.map((pt) => ({
        type: 'Feature' as const,
        id: `particle-${pt.id}`,
        properties: { id: pt.id },
        geometry: {
          type: 'Point' as const,
          coordinates: [pt.longitude, pt.latitude],
        },
      })),
    }
  }, [p.selectedTimeMs])

  // Dynamic progress fraction for hydrodynamic drift streamlines (0 at start/origin, 1 at spill detection)
  const driftProgressFraction = useMemo(() => {
    const total = p.detectionTimeMs - p.startTimeMs
    if (total <= 0) return 1.0
    return Math.max(0.08, Math.min(1.0, (p.selectedTimeMs - p.startTimeMs) / total))
  }, [p.selectedTimeMs, p.startTimeMs, p.detectionTimeMs])

  const sourceCentroid = useMemo(
    () => ({
      latitude:
        (p.driftSimulation.sourceRegion.bounds.minLatitude +
          p.driftSimulation.sourceRegion.bounds.maxLatitude) /
        2,
      longitude:
        (p.driftSimulation.sourceRegion.bounds.minLongitude +
          p.driftSimulation.sourceRegion.bounds.maxLongitude) /
        2,
    }),
    [p.driftSimulation.sourceRegion.bounds],
  )

  // Enhanced Hydrodynamic Drift Bundle: curved streamlines, dispersion plume corridor, and flow markers
  const driftBundle = useMemo(() => {
    return buildHydrodynamicDriftBundle(
      p.detection.centroid,
      sourceCentroid,
      driftProgressFraction,
      25,
    )
  }, [p.detection.centroid, sourceCentroid, driftProgressFraction])

  const sf = useMemo(
    () => ({
      type: 'Feature' as const,
      id: p.detection.spillId,
      properties: { spillId: p.detection.spillId },
      geometry: p.detection.polygon,
    }),
    [p.detection],
  )
  const cf = useMemo(
    () => ({
      type: 'Feature' as const,
      id: `${p.detection.spillId}-c`,
      properties: { spillId: p.detection.spillId },
      geometry: {
        type: 'Point' as const,
        coordinates: [p.detection.centroid.longitude, p.detection.centroid.latitude],
      },
    }),
    [p.detection],
  )
  const sr = useMemo(
    () => ({
      type: 'Feature' as const,
      id: p.driftSimulation.sourceRegion.id,
      properties: { sourceRegionId: p.driftSimulation.sourceRegion.id },
      geometry: p.driftSimulation.sourceRegion.geometry,
    }),
    [p.driftSimulation],
  )

  const ss = p.selectedSpillId === p.detection.spillId
  const sr_sel = p.selectedSourceRegionId === p.driftSimulation.sourceRegion.id

  return (
    <div className="map-wrapper">
      <Map
        ref={mapRef}
        mapStyle={BASE_MAP_STYLE}
        initialViewState={INITIAL_VIEW_STATE}
        attributionControl={false}
        reuseMaps
        style={{ width: '100%', height: '100%' }}
      >
        {/* Basemap base raster layer */}
        <Source
          id={`basemap-src-${p.activeBasemap}`}
          key={`basemap-src-${p.activeBasemap}`}
          type="raster"
          tiles={basemapConfig.tiles}
          tileSize={256}
          maxzoom={basemapConfig.maxZoom ?? 19}
        >
          <Layer
            id="basemap-tile-layer"
            type="raster"
            paint={{ 'raster-opacity': 1.0 }}
          />
        </Source>

        {/* Optional reference labels (coasts, cities, bathymetry labels) */}
        {p.showLabels && basemapConfig.referenceTiles && basemapConfig.referenceTiles.length > 0 && (
          <Source
            id={`basemap-ref-${p.activeBasemap}`}
            key={`basemap-ref-${p.activeBasemap}`}
            type="raster"
            tiles={basemapConfig.referenceTiles}
            tileSize={256}
            maxzoom={basemapConfig.maxZoom ?? 19}
          >
            <Layer
              id="basemap-ref-layer"
              type="raster"
              paint={{ 'raster-opacity': 0.85 }}
            />
          </Source>
        )}

        {/* Optional OpenSeaMap seamarks navigation overlay */}
        {p.showSeamarks && (
          <Source
            id="openseamap-seamarks-src"
            type="raster"
            tiles={SEAMARKS_OVERLAY_CONFIG.tiles}
            tileSize={256}
          >
            <Layer
              id="openseamap-seamarks-layer"
              type="raster"
              paint={{ 'raster-opacity': 0.95 }}
            />
          </Source>
        )}

        {/* Navigation, Scale, and Attribution controls */}
        <NavigationControl position="top-right" showCompass showZoom />
        <ScaleControl position="bottom-left" unit="metric" />
        <AttributionControl compact position="bottom-right" />

        {/* 1. 95% Confidence Drift Dispersion Plume Corridor */}
        {p.showDriftLayer && (
          <Source id="drift-envelope-src" type="geojson" data={driftBundle.envelope}>
            <Layer
              id="drift-envelope-fill"
              type="fill"
              paint={{
                'fill-color': 'rgba(192, 132, 252, 0.12)',
              }}
            />
            <Layer
              id="drift-envelope-outline"
              type="line"
              paint={{
                'line-color': 'rgba(232, 121, 249, 0.55)',
                'line-width': 1.4,
                'line-dasharray': [3, 2],
              }}
            />
          </Source>
        )}

        {/* 2. Soft Glowing Halo for Streamlines */}
        {p.showDriftLayer && (
          <Source id="drift-glow-src" type="geojson" data={driftBundle.streamlines}>
            <Layer
              id="drift-streamlines-glow"
              type="line"
              paint={{
                'line-color': '#c084fc',
                'line-width': 4.5,
                'line-opacity': 0.28,
                'line-blur': 2.0,
              }}
            />
          </Source>
        )}

        {/* 3. Core Hydrodynamic Streamlines (Weighted by Gaussian Probability) */}
        {p.showDriftLayer && (
          <Source id="drift-core-src" type="geojson" data={driftBundle.streamlines}>
            <Layer
              id="drift-streamlines-core"
              type="line"
              paint={{
                'line-color': [
                  'case',
                  ['==', ['get', 'isCenterline'], true],
                  '#ffffff',
                  '#f0abfc',
                ],
                'line-width': ['get', 'lineWidth'],
                'line-opacity': [
                  'case',
                  ['==', ['get', 'isCenterline'], true],
                  0.95,
                  ['*', ['get', 'probWeight'], 0.8],
                ],
              }}
            />
          </Source>
        )}

        {/* 4. Directional Flow Pulse Beads along Streamlines */}
        {p.showDriftLayer && (
          <Source id="drift-flow-arrows-src" type="geojson" data={driftBundle.flowArrows}>
            <Layer
              id="drift-flow-beads"
              type="circle"
              paint={{
                'circle-radius': 2.6,
                'circle-color': '#ffffff',
                'circle-stroke-color': '#c084fc',
                'circle-stroke-width': 1.2,
                'circle-opacity': ['get', 'opacity'],
              }}
            />
          </Source>
        )}

        {/* P2 Dynamic Drift Particles Hindcast Cloud */}
        {p.showDriftLayer && (
          <Source id="p2-drift-particles-src" type="geojson" data={driftParticlesGeoJson}>
            <Layer
              id="p2-drift-particles"
              type="circle"
              paint={{
                'circle-radius': 3.2,
                'circle-color': '#e879f9',
                'circle-opacity': 0.75,
                'circle-stroke-color': '#ffffff',
                'circle-stroke-width': 0.6,
              }}
            />
          </Source>
        )}

        {/* Probable Source Region */}
        {p.showSourceLayer && (
          <Source id="sr-src" type="geojson" data={sr}>
            <Layer
              id="source-region-fill"
              type="fill"
              paint={{
                'fill-color': sr_sel ? 'rgba(192, 132, 252, 0.45)' : 'rgba(168, 85, 247, 0.28)',
              }}
            />
            <Layer
              id="source-region-outline"
              type="line"
              paint={{
                'line-color': sr_sel ? '#e9d5ff' : '#c084fc',
                'line-width': sr_sel ? 2.5 : 1.8,
              }}
            />
          </Source>
        )}

        {p.showSourceLayer && (
          <Marker
            longitude={sourceCentroid.longitude}
            latitude={sourceCentroid.latitude}
            anchor="center"
          >
            <div
              className={sr_sel ? 'source-region-label selected' : 'source-region-label'}
              onClick={() => p.onSourceRegionSelect(p.driftSimulation.sourceRegion.id)}
            >
              Probable source
            </div>
          </Marker>
        )}

        {/* Detected Oil Spill Polygon */}
        {p.showSpillLayer && (
          <Source id="sp-src" type="geojson" data={sf}>
            <Layer
              id="spill-fill"
              type="fill"
              paint={{
                'fill-color': ss ? 'rgba(245, 166, 35, 0.65)' : 'rgba(245, 166, 35, 0.42)',
              }}
            />
            <Layer
              id="spill-outline"
              type="line"
              paint={{
                'line-color': ss ? '#ffe082' : '#f59e0b',
                'line-width': ss ? 2.8 : 2.0,
              }}
            />
          </Source>
        )}

        {p.showSpillLayer && (
          <Source id="sc-src" type="geojson" data={cf}>
            <Layer
              id="spill-centroid"
              type="circle"
              paint={{
                'circle-radius': ss ? 5.5 : 4.5,
                'circle-color': '#fbbf24',
                'circle-stroke-color': '#000000',
                'circle-stroke-width': 2,
              }}
            />
          </Source>
        )}

        {p.showSpillLayer && (
          <Marker
            longitude={p.detection.centroid.longitude}
            latitude={p.detection.centroid.latitude}
            anchor="bottom"
          >
            <div
              className={ss ? 'spill-label selected' : 'spill-label'}
              onClick={() => p.onSpillSelect(p.detection.spillId)}
            >
              {SPILL_LABEL}
            </div>
          </Marker>
        )}

        {/* Dynamic Backward Trajectory Trails (Color coded by Rank) */}
        {p.showAISLayer && (
          <Source id="dynamic-ais-trails-src" type="geojson" data={dynamicTrajectoryGeoJson}>
            <Layer
              id="dynamic-ais-trails"
              type="line"
              paint={{
                'line-color': [
                  'case',
                  ['==', ['get', 'selected'], true],
                  '#ffffff', // Selected vessel: glowing white
                  ['==', ['get', 'rank'], 1],
                  '#ff3030', // Rank 1: Red (#ff3030 per spec)
                  ['==', ['get', 'rank'], 2],
                  '#ffd21f', // Rank 2: Yellow (#ffd21f per spec)
                  ['==', ['get', 'rank'], 3],
                  '#28c76f', // Rank 3: Green (#28c76f per spec)
                  '#38bdf8', // Other vessels: cyan
                ],
                'line-width': [
                  'case',
                  ['==', ['get', 'selected'], true],
                  3.2,
                  ['==', ['get', 'rank'], 1],
                  2.6,
                  ['==', ['get', 'rank'], 2],
                  2.2,
                  ['==', ['get', 'rank'], 3],
                  2.0,
                  1.4,
                ],
                'line-opacity': [
                  'case',
                  ['==', ['get', 'selected'], true],
                  1.0,
                  ['==', ['get', 'rank'], 1],
                  0.95,
                  ['==', ['get', 'rank'], 2],
                  0.9,
                  ['==', ['get', 'rank'], 3],
                  0.9,
                  0.65,
                ],
              }}
            />
          </Source>
        )}

        {/* Moving Heading-Rotated Ship Markers (Strict Top 3 Vessels Only) */}
        {p.showAISLayer &&
          reconstructedVessels
            .filter((v) => Boolean(v.rank && v.rank >= 1 && v.rank <= 3))
            .map((v) => (
            <Marker
              key={`vessel-marker-${v.mmsi}`}
              longitude={v.currentPosition.longitude}
              latitude={v.currentPosition.latitude}
              anchor="center"
            >
              <VesselMarker
                name={v.name}
                mmsi={v.mmsi}
                rank={v.rank}
                heading={v.heading}
                speedKmh={v.speedKmh}
                isSelected={v.mmsi === p.selectedVesselMmsi}
                onClick={() => p.onVesselSelect(v.mmsi)}
              />
            </Marker>
          ))}
      </Map>

      {/* Floating Basemap Selector Widget */}
      <BasemapSelector
        activeBasemap={p.activeBasemap}
        onChangeBasemap={p.onChangeBasemap}
      />

      {/* Map Layer Controls */}
      <LayerControl
        showSpillLayer={p.showSpillLayer}
        showDriftLayer={p.showDriftLayer}
        showSourceLayer={p.showSourceLayer}
        showAISLayer={p.showAISLayer}
        showLabels={p.showLabels}
        showSeamarks={p.showSeamarks}
        onToggleSpillLayer={p.onToggleSpillLayer}
        onToggleDriftLayer={p.onToggleDriftLayer}
        onToggleSourceLayer={p.onToggleSourceLayer}
        onToggleAISLayer={p.onToggleAISLayer}
        onToggleLabels={p.onToggleLabels}
        onToggleSeamarks={p.onToggleSeamarks}
      />

      {/* Interactive Temporal Reconstruction Dragger (Docked at Bottom of Map) */}
      <TemporalDragger
        detectionTimeMs={p.detectionTimeMs}
        startTimeMs={p.startTimeMs}
        selectedTimeMs={p.selectedTimeMs}
        isPlaying={p.isPlaying}
        playbackSpeed={p.playbackSpeed}
        provenance={p.provenance}
        onTimeChange={p.onTimeChange}
        onTogglePlay={p.onTogglePlay}
        onSpeedChange={p.onSpeedChange}
        onResetToDetection={p.onResetToDetection}
        onUpdateDetectionTime={p.onUpdateDetectionTime}
      />

      {/* Legend */}
      <MapLegend />
    </div>
  )
}
