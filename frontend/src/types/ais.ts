import type { Feature, LineString, Point } from 'geojson'

/**
 * Single timestamped AIS trajectory point.
 */
export interface AISTrajectoryPoint {
  /** ISO-8601 UTC timestamp */
  timestamp: string
  /** Latitude in decimal degrees */
  latitude: number
  /** Longitude in decimal degrees */
  longitude: number
  /** Speed over ground in knots */
  speed: number
  /** Course over ground in degrees (0–360) */
  course: number
  /** True heading in degrees (0–360), may differ from course due to drift */
  heading: number
}

/**
 * Vessel category / type.
 */
export type VesselType =
  | 'Tanker'
  | 'Container'
  | 'Cargo'
  | 'Bulk Carrier'
  | 'Fishing'
  | 'Tug'

/**
 * Historical trajectory of a single vessel.
 */
export interface VesselTrajectory {
  /** Maritime Mobile Service Identity */
  mmsi: number
  /** Vessel name */
  name: string
  /** Vessel type / category */
  type: VesselType
  /** GeoJSON LineString of trajectory points */
  path: LineString
  /** All timestamped trajectory points */
  points: AISTrajectoryPoint[]
  /** Latest position (last point in trajectory) */
  latestPosition: {
    latitude: number
    longitude: number
    timestamp: string
  }
}

/**
 * Complete AIS dataset for demo visualization.
 */
export interface AISDataset {
  /** Dataset identifier */
  datasetId: string
  /** Human-readable name */
  name: string
  /** Number of vessels in dataset */
  vesselCount: number
  /** Investigation period start (ISO-8601 UTC) */
  startTime: string
  /** Investigation period end (ISO-8601 UTC) */
  endTime: string
  /** Array of vessel trajectories */
  vessels: VesselTrajectory[]
  /** True when using demonstration data */
  isDemo: boolean
  /** Human-readable disclaimer for demo data */
  disclaimer: string
}

/**
 * GeoJSON feature for vessel trajectory rendering.
 */
export interface VesselTrajectoryFeature extends Feature {
  id: string
  properties: {
    mmsi: number
    vesselName: string
    vesselType: VesselType
    trajectoryId: string
  }
  geometry: LineString
}

/**
 * GeoJSON feature for vessel marker (latest position).
 */
export interface VesselMarkerFeature extends Feature {
  id: string
  properties: {
    mmsi: number
    vesselName: string
    vesselType: VesselType
    markerId: string
  }
  geometry: Point
}
