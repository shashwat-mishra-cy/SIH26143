import { useEffect } from 'react'
import type { MapRef } from 'react-map-gl/maplibre'
import type { FeatureCollection, LineString, Point } from 'geojson'
import type { AISAssociationResult } from '../analysis/aisAssociationScore'

interface AISSelectionProps {
  mapRef: React.RefObject<MapRef>
  selectedVesselMmsi: number | null
  aisTrajectoryFeatures: FeatureCollection<LineString>
  aisMarkerFeatures: FeatureCollection<Point>
  topAssociatedVessels?: AISAssociationResult[]
}

/**
 * Hook to manage AIS vessel selection and ranking state via MapLibre feature-state.
 * - Highlights selected vessel (highest priority)
 * - Highlights Top 1, 2, 3 ranked vessels
 * - Other vessels remain subdued
 */
export function useAISSelection({
  mapRef,
  selectedVesselMmsi,
  aisTrajectoryFeatures,
  aisMarkerFeatures,
  topAssociatedVessels = [],
}: AISSelectionProps) {
  useEffect(() => {
    const map = mapRef.current
    if (!map) return

    // Build map of MMSI to rank (1, 2, 3)
    const rankByMmsi = new Map<number, number>()
    topAssociatedVessels.slice(0, 3).forEach((vessel, idx) => {
      rankByMmsi.set(vessel.mmsi, idx + 1)
    })

    // Reset all features
    aisTrajectoryFeatures.features.forEach((feat) => {
      const mmsi = feat.properties?.mmsi as number
      const rank = rankByMmsi.get(mmsi) ?? 0
      map.setFeatureState({ source: 'ais-trajectories-source', id: feat.id }, { selected: false, rank })
    })
    aisMarkerFeatures.features.forEach((feat) => {
      const mmsi = feat.properties?.mmsi as number
      const rank = rankByMmsi.get(mmsi) ?? 0
      map.setFeatureState({ source: 'ais-markers-source', id: feat.id }, { selected: false, rank })
    })

    // Highlight selected vessel (selection takes precedence over rank)
    if (selectedVesselMmsi !== null) {
      map.setFeatureState({ source: 'ais-trajectories-source', id: `ais-traj-${selectedVesselMmsi}` }, { selected: true })
      map.setFeatureState({ source: 'ais-markers-source', id: `ais-marker-${selectedVesselMmsi}` }, { selected: true })
    }
  }, [selectedVesselMmsi, aisTrajectoryFeatures, aisMarkerFeatures, topAssociatedVessels, mapRef])
}

/**
 * Click handler helper for layer-priority feature selection.
 */
export function createMapClickHandler(
  mapRef: React.RefObject<MapRef>,
  layerIds: { spill: string[]; source: string[]; ais: string[] },
  callbacks: {
    onAISSelect: (mmsi: number | null) => void
    onSourceSelect: (id: string | null) => void
    onSpillSelect: (id: string | null) => void
  },
) {
  return (event: any) => {
    const map = mapRef.current
    if (!map || !event.point) return

    // Priority 1: AIS
    const aisFeatures = map.queryRenderedFeatures(event.point as [number, number], { layers: layerIds.ais })
    if (aisFeatures.length > 0 && aisFeatures[0].properties?.mmsi !== undefined) {
      callbacks.onAISSelect(aisFeatures[0].properties.mmsi)
      callbacks.onSourceSelect(null)
      callbacks.onSpillSelect(null)
      return
    }

    // Priority 2: Source
    const srcFeatures = map.queryRenderedFeatures(event.point as [number, number], { layers: layerIds.source })
    if (srcFeatures.length > 0 && srcFeatures[0].properties?.sourceRegionId !== undefined) {
      callbacks.onSourceSelect(srcFeatures[0].properties.sourceRegionId)
      callbacks.onSpillSelect(null)
      callbacks.onAISSelect(null)
      return
    }

    // Priority 3: Spill
    const spillFeatures = map.queryRenderedFeatures(event.point as [number, number], { layers: layerIds.spill })
    if (spillFeatures.length > 0 && spillFeatures[0].properties?.spillId !== undefined) {
      callbacks.onSpillSelect(spillFeatures[0].properties.spillId)
      callbacks.onSourceSelect(null)
      callbacks.onAISSelect(null)
      return
    }

    // Deselect all
    callbacks.onAISSelect(null)
    callbacks.onSourceSelect(null)
    callbacks.onSpillSelect(null)
  }
}
