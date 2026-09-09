import type { AISDataset, VesselTrajectory } from '../types/ais'

/**
 * Configurable thresholds for candidate filtering.
 */
export const CANDIDATE_FILTER_CONFIG = {
  /** Maximum distance in km from vessel trajectory to source region to be considered "proximate" */
  SOURCE_PROXIMITY_THRESHOLD_KM: 15,
  /** Release window start (ISO-8601 UTC) */
  RELEASE_WINDOW_START: '2024-12-31T22:00:00Z',
  /** Release window end (ISO-8601 UTC) */
  RELEASE_WINDOW_END: '2025-01-01T02:00:00Z',
} as const

/**
 * Bounds of the probable source region (from OpenDrift hindcast).
 */
export const SOURCE_REGION_BOUNDS = {
  minLatitude: 18.42,
  maxLatitude: 18.48,
  minLongitude: 72.65,
  maxLongitude: 72.76,
} as const

/**
 * Center of the probable source region.
 */
export const SOURCE_REGION_CENTER = {
  latitude: 18.45,
  longitude: 72.70,
} as const

/**
 * Calculate distance between two geographic points using Haversine formula (km).
 */
export function haversineDistanceKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371
  const dLat = ((lat2 - lat1) * Math.PI) / 180
  const dLon = ((lon2 - lon1) * Math.PI) / 180
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) + Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) * Math.sin(dLon / 2)
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  return R * c
}

/**
 * Check if timestamp is in release window.
 */
export function isTimestampInReleaseWindow(timestamp: string): boolean {
  const ts = new Date(timestamp).getTime()
  const windowStart = new Date(CANDIDATE_FILTER_CONFIG.RELEASE_WINDOW_START).getTime()
  const windowEnd = new Date(CANDIDATE_FILTER_CONFIG.RELEASE_WINDOW_END).getTime()
  return ts >= windowStart && ts <= windowEnd
}

/**
 * Check if point is in source region bounds.
 */
function isPointInSourceBounds(lat: number, lon: number): boolean {
  return lat >= SOURCE_REGION_BOUNDS.minLatitude && lat <= SOURCE_REGION_BOUNDS.maxLatitude && lon >= SOURCE_REGION_BOUNDS.minLongitude && lon <= SOURCE_REGION_BOUNDS.maxLongitude
}

/**
 * Check if vessel has AIS points during release window.
 */
export function filterByReleaseWindow(vessel: VesselTrajectory): boolean {
  return vessel.points.some((point) => isTimestampInReleaseWindow(point.timestamp))
}

/**
 * Calculate minimum distance from vessel trajectory to source region center (km).
 */
export function calculateMinimumSourceDistance(vessel: VesselTrajectory): number {
  let minDistance = Infinity
  for (const point of vessel.points) {
    const distance = haversineDistanceKm(point.latitude, point.longitude, SOURCE_REGION_CENTER.latitude, SOURCE_REGION_CENTER.longitude)
    minDistance = Math.min(minDistance, distance)
  }
  return minDistance === Infinity ? -1 : minDistance
}

/**
 * Check if vessel trajectory is within proximity threshold of source region.
 */
export function filterBySourceProximity(vessel: VesselTrajectory): boolean {
  const minDistance = calculateMinimumSourceDistance(vessel)
  return minDistance >= 0 && minDistance <= CANDIDATE_FILTER_CONFIG.SOURCE_PROXIMITY_THRESHOLD_KM
}

/**
 * Check if vessel trajectory passes through source region during release window.
 */
export function checkTrajectorySourceIntersection(vessel: VesselTrajectory): boolean {
  for (const point of vessel.points) {
    if (isPointInSourceBounds(point.latitude, point.longitude) && isTimestampInReleaseWindow(point.timestamp)) {
      return true
    }
  }
  return false
}

/**
 * Candidate filter result for a single vessel.
 */
export interface AIScandidateFilterResult {
  mmsi: number
  vesselName: string
  vesselType: string
  temporalMatch: boolean
  minimumSourceDistanceKm: number
  sourceRegionProximityMatch: boolean
  trajectorySourceIntersection: boolean
  isCandidate: boolean
}

/**
 * Filter a single vessel and return candidate analysis.
 */
export function analyzeVessel(vessel: VesselTrajectory): AIScandidateFilterResult {
  const temporalMatch = filterByReleaseWindow(vessel)
  const minimumSourceDistanceKm = calculateMinimumSourceDistance(vessel)
  const sourceRegionProximityMatch = filterBySourceProximity(vessel)
  const trajectorySourceIntersection = checkTrajectorySourceIntersection(vessel)
  const isCandidate = temporalMatch || sourceRegionProximityMatch || trajectorySourceIntersection
  return { mmsi: vessel.mmsi, vesselName: vessel.name, vesselType: vessel.type, temporalMatch, minimumSourceDistanceKm, sourceRegionProximityMatch, trajectorySourceIntersection, isCandidate }
}

/**
 * Build investigation candidates from complete AIS dataset.
 */
export function buildAISCandidates(aisDataset: AISDataset): AIScandidateFilterResult[] {
  return aisDataset.vessels.map((vessel) => analyzeVessel(vessel))
}

/**
 * Candidate filter statistics.
 */
export interface CandidateFilterStats {
  totalVessels: number
  temporalMatches: number
  proximityMatches: number
  intersectionMatches: number
  investigationCandidates: number
}

/**
 * Calculate statistics about candidate filtering results.
 */
export function calculateCandidateStats(results: AIScandidateFilterResult[]): CandidateFilterStats {
  return { totalVessels: results.length, temporalMatches: results.filter((r) => r.temporalMatch).length, proximityMatches: results.filter((r) => r.sourceRegionProximityMatch).length, intersectionMatches: results.filter((r) => r.trajectorySourceIntersection).length, investigationCandidates: results.filter((r) => r.isCandidate).length }
}
