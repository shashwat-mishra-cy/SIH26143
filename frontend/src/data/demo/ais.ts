import type { AISDataset, VesselTrajectory, AISTrajectoryPoint } from '../../types/ais'

function buildTrajectory(
  sLat: number,
  sLon: number,
  eLat: number,
  eLon: number,
  sTime: string,
  eTime: string,
): AISTrajectoryPoint[] {
  const start = new Date(sTime)
  const end = new Date(eTime)
  const durationMs = end.getTime() - start.getTime()
  // 10-minute reporting intervals
  const pointCount = Math.max(12, Math.floor(durationMs / (10 * 60 * 1000)) + 1)
  const points: AISTrajectoryPoint[] = []

  for (let i = 0; i < pointCount; i++) {
    const progress = i / (pointCount - 1)
    const lat = sLat + (eLat - sLat) * progress
    const lon = sLon + (eLon - sLon) * progress
    const latVar = Math.sin(progress * Math.PI * 4) * 0.006
    const lonVar = Math.cos(progress * Math.PI * 3) * 0.006
    const timestamp = new Date(start.getTime() + durationMs * progress)

    const dLat = eLat - sLat
    const dLon = eLon - sLon
    const courseRad = Math.atan2(dLon, dLat)
    const courseDeg = ((courseRad * 180) / Math.PI + 360) % 360

    const speedVar = Math.sin(progress * Math.PI * 2) * 2 + 11
    const speed = Math.max(5, Math.min(14, speedVar))
    const headingVar = Math.sin(progress * Math.PI * 5) * 6
    const heading = (courseDeg + headingVar + 360) % 360

    points.push({
      timestamp: timestamp.toISOString(),
      latitude: lat + latVar,
      longitude: lon + lonVar,
      speed: Math.round(speed * 10) / 10,
      course: Math.round(courseDeg),
      heading: Math.round(heading),
    })
  }
  return points
}

function pts2line(points: AISTrajectoryPoint[]): GeoJSON.LineString {
  return { type: 'LineString', coordinates: points.map((p) => [p.longitude, p.latitude]) }
}

function mkVessel(
  mmsi: number,
  name: string,
  type: any,
  sLat: number,
  sLon: number,
  eLat: number,
  eLon: number,
  sTime: string,
  eTime: string,
): VesselTrajectory {
  const points = buildTrajectory(sLat, sLon, eLat, eLon, sTime, eTime)
  return {
    mmsi,
    name,
    type,
    path: pts2line(points),
    points,
    latestPosition: {
      latitude: points[points.length - 1].latitude,
      longitude: points[points.length - 1].longitude,
      timestamp: points[points.length - 1].timestamp,
    },
  }
}

export const DEMO_AIS_DATASET: AISDataset = {
  datasetId: 'AIS-2025-01-01-MUMBAI-01',
  name: 'Historical AIS Traffic — Mumbai/Arabian Sea',
  vesselCount: 8,
  startTime: '2025-01-01T00:00:00Z',
  endTime: '2025-01-01T12:00:00Z',
  vessels: [
    mkVessel(419001234, 'MT OCEAN TRADER', 'Tanker', 18.35, 72.50, 18.52, 72.82, '2025-01-01T00:00:00Z', '2025-01-01T12:00:00Z'),
    mkVessel(563002456, 'CONTAINER EXPRESS', 'Container', 18.25, 72.88, 18.62, 72.60, '2025-01-01T00:00:00Z', '2025-01-01T12:00:00Z'),
    mkVessel(441003789, 'CARGO FRONTIER', 'Cargo', 18.75, 72.95, 18.25, 72.40, '2025-01-01T00:00:00Z', '2025-01-01T12:00:00Z'),
    mkVessel(352004521, 'BULK HORIZON', 'Bulk Carrier', 18.42, 72.58, 18.50, 72.78, '2025-01-01T00:00:00Z', '2025-01-01T12:00:00Z'),
    mkVessel(268005634, 'FISHING VESSEL 001', 'Fishing', 18.65, 72.50, 18.38, 72.85, '2025-01-01T00:00:00Z', '2025-01-01T12:00:00Z'),
    mkVessel(537006847, 'TUG PILOT ASSIST', 'Tug', 18.50, 72.55, 18.48, 72.75, '2025-01-01T00:00:00Z', '2025-01-01T12:00:00Z'),
    mkVessel(636007912, 'CONTAINER STAR', 'Container', 18.80, 72.60, 18.30, 72.90, '2025-01-01T00:00:00Z', '2025-01-01T12:00:00Z'),
    mkVessel(309008765, 'TANKER GUARDIAN', 'Tanker', 18.70, 73.05, 18.68, 73.02, '2025-01-01T00:00:00Z', '2025-01-01T12:00:00Z'),
  ],
  isDemo: true,
  disclaimer: 'Demonstration data — synthetic vessels for UI development. Synchronized with P2 hindcast timeline.',
}
