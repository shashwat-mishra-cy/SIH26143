/**
 * Temporal reconstruction types for SIH26143 Interactive Dragger feature.
 */

export type TimestampProvenance = 'satellite_metadata' | 'user_provided' | 'unavailable'

export interface TimelineRange {
  /** Earliest historical observation time (ms) */
  startTimeMs: number
  /** Detection / observation time (ms) — rightmost slider position */
  detectionTimeMs: number
  /** Current selected inspection time (ms) */
  selectedTimeMs: number
  /** Default step in minutes (e.g. 10 or 15) */
  stepMinutes: number
}

export interface InterpolatedPoint {
  latitude: number
  longitude: number
  heading: number
  course: number
  speedKmh: number
  timestamp: string
}

export interface InterpolatedVesselState {
  mmsi: number
  name: string
  rank?: number
  currentPosition: {
    latitude: number
    longitude: number
  }
  heading: number
  course: number
  speedKmh: number
  /** Dynamic backward trail: coordinates from selectedTime up to detectionTime */
  trailCoordinates: [number, number][]
  distanceToSpillKm?: number
  distanceToSourceKm?: number
}

export interface DriftParticle {
  id: number
  latitude: number
  longitude: number
}

export interface DriftTimeFrame {
  timestamp: string
  timestampMs: number
  particles: DriftParticle[]
}
