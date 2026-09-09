import type { SatelliteDetection } from '../../types/satellite'
import { buildSpillPolygon } from '../../geo/spillPolygon'

/**
 * DEMO satellite detection — SIH26143.
 * Synchronized with P2 OpenDrift hindcast detection timestamp (12:00:00 UTC).
 */
export const DEMO_SATELLITE_DETECTION: SatelliteDetection = {
  spillId: 'SPILL-2025-01-01-MUMBAI-01',
  centroid: {
    latitude: 18.52,
    longitude: 72.85,
  },
  areaKm2: 14.7,
  confidence: 0.91,
  polygon: buildSpillPolygon(
    { latitude: 18.52, longitude: 72.85 },
    6.8, // length km
    2.4, // width km
    32, // orientation degrees clockwise from north
  ),
  timestamp: '2025-01-01T12:00:00Z',
  sensor: 'Sentinel-1 SAR',
  geometry: {
    lengthKm: 6.8,
    widthKm: 2.4,
    orientationDeg: 32,
  },
  isDemo: true,
  disclaimer:
    'Demonstration data — Sentinel-1 SAR detection synchronized with P2 drift hindcast.',
}

/**
 * Short label shown on the map for the detected spill.
 */
export const SPILL_LABEL = 'Suspected oil spill'