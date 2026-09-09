import type { Feature, Polygon, Point } from 'geojson'

/**
 * Satellite detection geometry — spill shape metrics.
 */
export interface SpillGeometry {
  /** Approx. length of the slick along its major axis (km). */
  lengthKm: number
  /** Approx. width of the slick along its minor axis (km). */
  widthKm: number
  /** Orientation of the major axis, clockwise from north (degrees). */
  orientationDeg: number
}

/**
 * Conceptual satellite detection output (P1).
 *
 * This is the shape a real satellite pipeline is expected to produce.
 * The demo layer supplies an instance of this contract; later phases
 * can swap the demo source for real API output without rewriting the
 * map component.
 */
export interface SatelliteDetection {
  spillId: string
  centroid: {
    latitude: number
    longitude: number
  }
  /** Detected dark-feature area in square kilometres. */
  areaKm2: number
  /** Detection confidence, 0..1. */
  confidence: number
  /** GeoJSON polygon of the detected dark feature (spill candidate). */
  polygon: Polygon
  /** ISO-8601 acquisition timestamp (UTC). */
  timestamp: string
  /** Sensor name, e.g. Sentinel-1 SAR. */
  sensor: string
  /** Spill geometry metrics. */
  geometry: SpillGeometry
  /** True when the values are demonstration-only, not real measurements. */
  isDemo: boolean
  /** Human-readable disclaimer for demo data. */
  disclaimer: string
}

/**
 * GeoJSON feature carrying a spillId property for map interaction.
 */
export interface SpillFeature extends Feature {
  id: string
  properties: {
    spillId: string
  }
  geometry: Polygon | Point
}