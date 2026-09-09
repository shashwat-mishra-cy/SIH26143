import type { Feature, Polygon, MultiLineString } from 'geojson'

/**
 * Time window for estimated spill release.
 */
export interface TimeWindow {
  /** ISO-8601 UTC start time */
  startTime: string
  /** ISO-8601 UTC end time */
  endTime: string
}

/**
 * Geographic bounds for probable source region.
 */
export interface GeographicBounds {
  minLatitude: number
  maxLatitude: number
  minLongitude: number
  maxLongitude: number
}

/**
 * Backward drift trajectory — a single simulated particle path.
 */
export interface DriftTrajectory {
  id: string
  /** GeoJSON LineString from spill backward to source region */
  path: MultiLineString
}

/**
 * Probable source region from backward drift hindcast.
 */
export interface SourceRegion {
  id: string
  /** Uncertainty polygon of probable source area */
  geometry: Polygon
  /** Geographic bounds of the region */
  bounds: GeographicBounds
  /** Source confidence, 0..1 */
  confidence: number
}

/**
 * Complete backward drift / hindcast simulation result.
 *
 * Represents the conceptual output of an OpenDrift backward simulation:
 * given an observed spill at time T and location L, where did the oil
 * likely originate, and when?
 */
export interface DriftSimulation {
  /** Unique simulation identifier */
  simulationId: string
  /** Associated spill ID */
  spillId: string
  /** Hindcast model name (e.g., OpenDrift) */
  model: string
  /** Simulation mode: 'backward' or 'hindcast' */
  mode: 'backward' | 'hindcast'
  /** Estimated release time window (UTC) */
  estimatedReleaseWindow: TimeWindow
  /** Confidence in source location, 0..1 */
  sourceConfidence: number
  /** Probable source region */
  sourceRegion: SourceRegion
  /** Backward trajectories from spill to source */
  trajectories: DriftTrajectory[]
  /** True when the values are demonstration-only */
  isDemo: boolean
  /** Human-readable disclaimer for demo data */
  disclaimer: string
}

/**
 * GeoJSON feature for trajectory rendering.
 */
export interface TrajectoryFeature extends Feature {
  id: string
  properties: {
    trajectoryId: string
    spillId: string
  }
  geometry: MultiLineString
}

/**
 * GeoJSON feature for source region rendering.
 */
export interface SourceRegionFeature extends Feature {
  id: string
  properties: {
    sourceRegionId: string
    spillId: string
    confidence: number
  }
  geometry: Polygon
}
