import type { InterpolatedVesselState } from '../types/temporal'

/**
 * Compute shortest-arc circular angle interpolation between two compass headings.
 */
export function interpolateHeading(h1: number, h2: number, fraction: number): number {
  const diff = ((h2 - h1 + 180) % 360 + 360) % 360 - 180
  return ((h1 + diff * fraction) % 360 + 360) % 360
}

/**
 * Haversine formula to compute great-circle distance between two coordinates in km.
 */
export function haversineDistanceKm(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number,
): number {
  const R = 6371
  const dLat = ((lat2 - lat1) * Math.PI) / 180
  const dLon = ((lon2 - lon1) * Math.PI) / 180
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2)
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  return Math.round(R * c * 10) / 10
}

export interface TrajectoryPointInput {
  timestamp: string
  latitude: number
  longitude: number
  heading?: number | null
  course?: number | null
  course_over_ground?: number | null
  speed?: number | null
  speed_kmh?: number | null
}

export interface VesselInput {
  mmsi: number | string
  name: string
  rank?: number
  points: TrajectoryPointInput[]
}

/**
 * Core temporal reconstruction logic (Section 4 & 5 of Interactive Dragger spec):
 * - Interpolates vessel position and heading between actual AIS observations.
 * - Filters trajectory points to satisfy: selected_time <= timestamp <= detection_time
 * - Inserts the exact interpolated position at selected_time as the head of the trail.
 */
export function reconstructVesselAtTime(
  vessel: VesselInput,
  selectedTimeMs: number,
  detectionTimeMs: number,
  targetCentroid?: { latitude: number; longitude: number },
): InterpolatedVesselState {
  const mmsiNum = typeof vessel.mmsi === 'string' ? parseInt(vessel.mmsi, 10) || 0 : vessel.mmsi
  const pts = vessel.points
  if (!pts || pts.length === 0) {
    return {
      mmsi: mmsiNum,
      name: vessel.name,
      rank: vessel.rank,
      currentPosition: { latitude: 0, longitude: 0 },
      heading: 0,
      course: 0,
      speedKmh: 0,
      trailCoordinates: [],
    }
  }

  // Pre-parse timestamps
  const ptsWithMs = pts.map((p) => {
    const timeMs = new Date(p.timestamp).getTime()
    const rawCourse = p.course ?? p.course_over_ground ?? 0
    const rawHeading = p.heading !== null && p.heading !== undefined ? p.heading : rawCourse
    const rawSpeed = p.speed_kmh ?? (p.speed ? p.speed * 1.852 : 0)
    return {
      ...p,
      timeMs,
      heading: rawHeading,
      course: rawCourse,
      speedKmh: Math.round(rawSpeed * 10) / 10,
    }
  })

  // Sort chronologically
  ptsWithMs.sort((a, b) => a.timeMs - b.timeMs)

  let interpLat: number
  let interpLon: number
  let interpHeading: number
  let interpCourse: number
  let interpSpeed: number

  if (selectedTimeMs <= ptsWithMs[0].timeMs) {
    // Before or at first point
    const first = ptsWithMs[0]
    interpLat = first.latitude
    interpLon = first.longitude
    interpHeading = first.heading
    interpCourse = first.course
    interpSpeed = first.speedKmh
  } else if (selectedTimeMs >= ptsWithMs[ptsWithMs.length - 1].timeMs) {
    // At or after last point
    const last = ptsWithMs[ptsWithMs.length - 1]
    interpLat = last.latitude
    interpLon = last.longitude
    interpHeading = last.heading
    interpCourse = last.course
    interpSpeed = last.speedKmh
  } else {
    // Find surrounding points Pi and Pi+1
    let idx = 0
    for (let i = 0; i < ptsWithMs.length - 1; i++) {
      if (ptsWithMs[i].timeMs <= selectedTimeMs && selectedTimeMs <= ptsWithMs[i + 1].timeMs) {
        idx = i
        break
      }
    }
    const p1 = ptsWithMs[idx]
    const p2 = ptsWithMs[idx + 1]
    const span = p2.timeMs - p1.timeMs
    const fraction = span > 0 ? (selectedTimeMs - p1.timeMs) / span : 0

    interpLat = p1.latitude + (p2.latitude - p1.latitude) * fraction
    interpLon = p1.longitude + (p2.longitude - p1.longitude) * fraction
    interpHeading = interpolateHeading(p1.heading, p2.heading, fraction)
    interpCourse = interpolateHeading(p1.course, p2.course, fraction)
    interpSpeed = Math.round((p1.speedKmh + (p2.speedKmh - p1.speedKmh) * fraction) * 10) / 10
  }

  // Build backward trail logic (Section 5):
  // Points satisfying selected_time <= timestamp <= detection_time
  const trailPoints = ptsWithMs.filter(
    (p) => p.timeMs >= selectedTimeMs && p.timeMs <= detectionTimeMs,
  )

  // Construct coordinates array: starts at interpolated point, follows along historical observations
  const trailCoordinates: [number, number][] = [[interpLon, interpLat]]
  for (const pt of trailPoints) {
    // Avoid duplicate point if very close to interpolated point
    if (
      Math.abs(pt.longitude - interpLon) > 0.00005 ||
      Math.abs(pt.latitude - interpLat) > 0.00005
    ) {
      trailCoordinates.push([pt.longitude, pt.latitude])
    }
  }

  const distanceToSpillKm = targetCentroid
    ? haversineDistanceKm(interpLat, interpLon, targetCentroid.latitude, targetCentroid.longitude)
    : undefined

  return {
    mmsi: mmsiNum,
    name: vessel.name,
    rank: vessel.rank,
    currentPosition: {
      latitude: interpLat,
      longitude: interpLon,
    },
    heading: Math.round(interpHeading),
    course: Math.round(interpCourse),
    speedKmh: interpSpeed,
    trailCoordinates,
    distanceToSpillKm,
  }
}
