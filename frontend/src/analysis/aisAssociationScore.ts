import type { VesselTrajectory } from '../types/ais'
import type { AIScandidateFilterResult } from './aisCandidateFilter'
import {
  CANDIDATE_FILTER_CONFIG,
  SOURCE_REGION_CENTER,
  SOURCE_REGION_BOUNDS,
  haversineDistanceKm,
  isTimestampInReleaseWindow,
} from './aisCandidateFilter'

/**
 * Configuration for association/correlation scoring.
 * Demonstration weights for the prototype — NOT official NTRO weights.
 */
export const ASSOCIATION_SCORE_CONFIG = {
  TEMPORAL_WEIGHT: 0.30,
  PROXIMITY_WEIGHT: 0.40,
  TRAJECTORY_WEIGHT: 0.30,
  PROXIMITY_MAX_DISTANCE_KM: 15,
} as const

/**
 * Calculate temporal compatibility score (0-100).
 */
export function calculateTemporalScore(vessel: VesselTrajectory): number {
  const windowStart = new Date(CANDIDATE_FILTER_CONFIG.RELEASE_WINDOW_START).getTime()
  const windowEnd = new Date(CANDIDATE_FILTER_CONFIG.RELEASE_WINDOW_END).getTime()
  const windowDuration = windowEnd - windowStart
  let overlapStart = windowEnd
  let overlapEnd = windowStart
  for (const point of vessel.points) {
    const pointTime = new Date(point.timestamp).getTime()
    if (pointTime >= windowStart && pointTime <= windowEnd) {
      overlapStart = Math.min(overlapStart, pointTime)
      overlapEnd = Math.max(overlapEnd, pointTime)
    }
  }
  if (overlapStart > overlapEnd) return 0
  const overlapDuration = overlapEnd - overlapStart
  const temporalCoverage = Math.min(overlapDuration / windowDuration, 1.0)
  return Math.round(temporalCoverage * 100)
}

/**
 * Calculate source proximity score (0-100).
 */
export function calculateProximityScore(minDistanceKm: number): number {
  if (minDistanceKm < 0) return 0
  const maxDistance = ASSOCIATION_SCORE_CONFIG.PROXIMITY_MAX_DISTANCE_KM
  if (minDistanceKm >= maxDistance) return 0
  const proximityScore = ((maxDistance - minDistanceKm) / maxDistance) * 100
  return Math.round(proximityScore)
}

/**
 * Check if point is in source region bounds.
 */
function isPointInSourceBounds(lat: number, lon: number): boolean {
  return (
    lat >= SOURCE_REGION_BOUNDS.minLatitude &&
    lat <= SOURCE_REGION_BOUNDS.maxLatitude &&
    lon >= SOURCE_REGION_BOUNDS.minLongitude &&
    lon <= SOURCE_REGION_BOUNDS.maxLongitude
  )
}

/**
 * Calculate trajectory compatibility score (0-100).
 */
export function calculateTrajectoryScore(vessel: VesselTrajectory): number {
  let closestApproachDuringWindow = Infinity
  for (const point of vessel.points) {
    if (isTimestampInReleaseWindow(point.timestamp)) {
      if (isPointInSourceBounds(point.latitude, point.longitude)) {
        return 100
      }
      const distance = haversineDistanceKm(
        point.latitude,
        point.longitude,
        SOURCE_REGION_CENTER.latitude,
        SOURCE_REGION_CENTER.longitude,
      )
      closestApproachDuringWindow = Math.min(closestApproachDuringWindow, distance)
    }
  }
  if (closestApproachDuringWindow < Infinity) {
    if (closestApproachDuringWindow <= 5) return 75
    if (closestApproachDuringWindow <= 10) return 50
    if (closestApproachDuringWindow <= 15) return 25
  }
  return 0
}

/**
 * Association score result for a single vessel.
 */
export interface AISAssociationResult extends AIScandidateFilterResult {
  temporalScore: number
  proximityScore: number
  trajectoryScore: number
  associationScore: number
  rank?: number
}

/**
 * Calculate association score for a single vessel.
 */
export function calculateAssociationScore(
  vessel: VesselTrajectory,
  candidateResult: AIScandidateFilterResult,
): AISAssociationResult {
  if (!candidateResult.isCandidate) {
    return {
      ...candidateResult,
      temporalScore: 0,
      proximityScore: 0,
      trajectoryScore: 0,
      associationScore: 0,
    }
  }
  const temporalScore = calculateTemporalScore(vessel)
  const proximityScore = calculateProximityScore(candidateResult.minimumSourceDistanceKm)
  const trajectoryScore = calculateTrajectoryScore(vessel)
  const associationScore = temporalScore * ASSOCIATION_SCORE_CONFIG.TEMPORAL_WEIGHT + proximityScore * ASSOCIATION_SCORE_CONFIG.PROXIMITY_WEIGHT + trajectoryScore * ASSOCIATION_SCORE_CONFIG.TRAJECTORY_WEIGHT
  return { ...candidateResult, temporalScore, proximityScore, trajectoryScore, associationScore: Math.round(associationScore) }
}

/**
 * Rank association results deterministically.
 */
export function rankAssociationResults(results: AISAssociationResult[]): AISAssociationResult[] {
  const rankedResults = results
    .filter((r) => r.isCandidate)
    .sort((a, b) => {
      if (b.associationScore !== a.associationScore) return b.associationScore - a.associationScore
      if (a.minimumSourceDistanceKm !== b.minimumSourceDistanceKm) return a.minimumSourceDistanceKm - b.minimumSourceDistanceKm
      return a.mmsi - b.mmsi
    })
    .map((result, index) => ({
      ...result,
      rank: index + 1,
    }))
  return rankedResults
}

/**
 * Build association scores for all vessels.
 */
export interface AssociationAnalysisResult {
  allResults: AISAssociationResult[]
  rankedCandidates: AISAssociationResult[]
  topAssociatedVessels: AISAssociationResult[]
}

export function buildAssociationAnalysis(
  vessels: VesselTrajectory[],
  candidateResults: AIScandidateFilterResult[],
): AssociationAnalysisResult {
  const allResults = vessels.map((vessel) => {
    const candidate = candidateResults.find((c) => c.mmsi === vessel.mmsi)!
    return calculateAssociationScore(vessel, candidate)
  })
  const rankedCandidates = rankAssociationResults(allResults)
  const topAssociatedVessels = rankedCandidates.slice(0, 3)
  return { allResults, rankedCandidates, topAssociatedVessels }
}

