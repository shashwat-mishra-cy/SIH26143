import type { VesselTrajectory } from '../types/ais'
import { haversineDistanceKm } from './aisCandidateFilter'

export const ANOMALY_CONFIG = {
  SPEED_CHANGE_THRESHOLD_KNOTS: 3.0,
  COURSE_CHANGE_THRESHOLD_DEGREES: 15.0,
  AIS_GAP_THRESHOLD_MINUTES: 30,
  MAX_PLAUSIBLE_SPEED_KNOTS: 25,
  SPEED_WEIGHT: 0.25,
  COURSE_WEIGHT: 0.25,
  AIS_GAP_WEIGHT: 0.25,
  TRAJECTORY_WEIGHT: 0.25,
} as const

function circularAngleDifference(angle1: number, angle2: number): number {
  let diff = Math.abs(angle2 - angle1)
  if (diff > 180) diff = 360 - diff
  return diff
}

export function calculateSpeedDeviation(vessel: VesselTrajectory): number {
  if (vessel.points.length < 2) return 0
  let totalDeviation = 0
  let deviationCount = 0
  for (let i = 1; i < vessel.points.length; i++) {
    const speedChange = Math.abs(vessel.points[i].speed - vessel.points[i - 1].speed)
    if (speedChange > ANOMALY_CONFIG.SPEED_CHANGE_THRESHOLD_KNOTS) {
      totalDeviation += Math.min(speedChange, 10)
      deviationCount++
    }
  }
  if (deviationCount === 0) return 0
  const avgDeviation = totalDeviation / deviationCount
  return Math.round(Math.min((avgDeviation / 10) * 100, 100))
}

export function calculateCourseChange(vessel: VesselTrajectory): number {
  if (vessel.points.length < 2) return 0
  let totalCourseChange = 0
  let changeCount = 0
  for (let i = 1; i < vessel.points.length; i++) {
    const courseDiff = circularAngleDifference(vessel.points[i - 1].course, vessel.points[i].course)
    if (courseDiff > ANOMALY_CONFIG.COURSE_CHANGE_THRESHOLD_DEGREES) {
      totalCourseChange += courseDiff
      changeCount++
    }
  }
  if (changeCount === 0) return 0
  const avgCourseChange = totalCourseChange / changeCount
  return Math.round(Math.min((avgCourseChange / 90) * 100, 100))
}

export function calculateAISGaps(vessel: VesselTrajectory): number {
  if (vessel.points.length < 2) return 0
  let gapCount = 0
  let maxGapMinutes = 0
  for (let i = 1; i < vessel.points.length; i++) {
    const gapMs = new Date(vessel.points[i].timestamp).getTime() - new Date(vessel.points[i - 1].timestamp).getTime()
    const gapMinutes = gapMs / (60 * 1000)
    if (gapMinutes > ANOMALY_CONFIG.AIS_GAP_THRESHOLD_MINUTES) {
      gapCount++
      maxGapMinutes = Math.max(maxGapMinutes, gapMinutes)
    }
  }
  if (gapCount === 0) return 0
  return Math.round(Math.min((maxGapMinutes / 120) * 100, 100))
}

export function calculateTrajectoryConsistency(vessel: VesselTrajectory): number {
  if (vessel.points.length < 2) return 0
  let inconsistencyCount = 0
  let maxInconsistency = 0
  for (let i = 1; i < vessel.points.length; i++) {
    const distance = haversineDistanceKm(
      vessel.points[i - 1].latitude,
      vessel.points[i - 1].longitude,
      vessel.points[i].latitude,
      vessel.points[i].longitude
    )
    const timeHours = (new Date(vessel.points[i].timestamp).getTime() - new Date(vessel.points[i - 1].timestamp).getTime()) / (60 * 60 * 1000)
    if (timeHours > 0) {
      const impliedSpeed = distance / timeHours
      if (impliedSpeed > ANOMALY_CONFIG.MAX_PLAUSIBLE_SPEED_KNOTS) {
        inconsistencyCount++
        maxInconsistency = Math.max(maxInconsistency, impliedSpeed - ANOMALY_CONFIG.MAX_PLAUSIBLE_SPEED_KNOTS)
      }
    }
  }
  if (inconsistencyCount === 0) return 0
  return Math.round(Math.min((maxInconsistency / 25) * 100, 100))
}

function getSpeedIndicator(score: number): string {
  if (score === 0) return 'No significant speed deviation detected'
  if (score < 30) return 'Minor speed variation detected'
  if (score < 60) return 'Moderate speed change observed'
  return 'Significant speed change observed'
}

function getCourseIndicator(score: number): string {
  if (score === 0) return 'No significant course change detected'
  if (score < 30) return 'Minor course variation detected'
  if (score < 60) return 'Moderate course change observed'
  return 'Significant course change observed'
}

function getAISGapIndicator(score: number): string {
  if (score === 0) return 'No significant AIS data gap detected'
  if (score < 50) return 'Minor AIS data gap detected'
  return 'Significant AIS data gap detected'
}

function getTrajectoryIndicator(score: number): string {
  if (score === 0) return 'Trajectory appears continuous'
  if (score < 30) return 'Minor trajectory discontinuity detected'
  if (score < 60) return 'Moderate trajectory inconsistency detected'
  return 'Significant trajectory discontinuity detected'
}

export interface AISAnomalyResult {
  mmsi: number
  vesselName: string
  speedDeviationScore: number
  courseChangeScore: number
  aisGapScore: number
  trajectoryConsistencyScore: number
  anomalyEvidenceScore: number
  evidenceIndicators: string[]
}

export function analyzeVesselBehavior(vessel: VesselTrajectory): AISAnomalyResult {
  const speedDeviationScore = calculateSpeedDeviation(vessel)
  const courseChangeScore = calculateCourseChange(vessel)
  const aisGapScore = calculateAISGaps(vessel)
  const trajectoryConsistencyScore = calculateTrajectoryConsistency(vessel)
  const anomalyEvidenceScore =
    speedDeviationScore * ANOMALY_CONFIG.SPEED_WEIGHT +
    courseChangeScore * ANOMALY_CONFIG.COURSE_WEIGHT +
    aisGapScore * ANOMALY_CONFIG.AIS_GAP_WEIGHT +
    trajectoryConsistencyScore * ANOMALY_CONFIG.TRAJECTORY_WEIGHT
  const evidenceIndicators = [
    getSpeedIndicator(speedDeviationScore),
    getCourseIndicator(courseChangeScore),
    getAISGapIndicator(aisGapScore),
    getTrajectoryIndicator(trajectoryConsistencyScore),
  ]
  return {
    mmsi: vessel.mmsi,
    vesselName: vessel.name,
    speedDeviationScore: Math.round(speedDeviationScore),
    courseChangeScore: Math.round(courseChangeScore),
    aisGapScore: Math.round(aisGapScore),
    trajectoryConsistencyScore: Math.round(trajectoryConsistencyScore),
    anomalyEvidenceScore: Math.round(anomalyEvidenceScore),
    evidenceIndicators,
  }
}

export interface AnomalyAnalysisResult {
  allResults: AISAnomalyResult[]
  vesselCount: number
  vesselsWithIndicators: number
}

export function buildAnomalyAnalysis(vessels: VesselTrajectory[]): AnomalyAnalysisResult {
  const allResults = vessels.map((vessel) => analyzeVesselBehavior(vessel))
  const vesselsWithIndicators = allResults.filter(
    (r) =>
      r.speedDeviationScore > 0 ||
      r.courseChangeScore > 0 ||
      r.aisGapScore > 0 ||
      r.trajectoryConsistencyScore > 0
  ).length
  return {
    allResults,
    vesselCount: vessels.length,
    vesselsWithIndicators,
  }
}
