import type { FeatureCollection, LineString, Point } from 'geojson'
import type { AISDataset } from '../types/ais'

/**
 * Convert AIS dataset into a GeoJSON FeatureCollection of vessel trajectories.
 *
 * Each feature is a LineString with properties:
 * - mmsi: Maritime Mobile Service Identity
 * - vesselName: Human-readable name
 * - vesselType: Vessel category (Tanker, Container, etc.)
 * - trajectoryId: Unique identifier for the trajectory
 */
export function buildAISTrajectoryFeatures(
  aisDataset: AISDataset,
): FeatureCollection<LineString> {
  const features = aisDataset.vessels.map((vessel) => ({
    type: 'Feature' as const,
    id: `ais-traj-${vessel.mmsi}`,
    properties: {
      mmsi: vessel.mmsi,
      vesselName: vessel.name,
      vesselType: vessel.type,
      trajectoryId: `traj-${vessel.mmsi}`,
    },
    geometry: vessel.path,
  }))

  return {
    type: 'FeatureCollection',
    features,
  }
}

/**
 * Convert AIS dataset into a GeoJSON FeatureCollection of vessel position markers.
 *
 * Each feature is a Point at the vessel's latest position with properties:
 * - mmsi: Maritime Mobile Service Identity
 * - vesselName: Human-readable name
 * - vesselType: Vessel category
 * - speed: Speed over ground in knots
 * - course: Course over ground in degrees
 * - heading: True heading in degrees
 * - timestamp: ISO-8601 timestamp of latest position
 * - markerId: Unique identifier for the marker
 */
export function buildAISMarkerFeatures(
  aisDataset: AISDataset,
): FeatureCollection<Point> {
  const features = aisDataset.vessels.map((vessel) => {
    const lastPoint = vessel.points[vessel.points.length - 1]

    return {
      type: 'Feature' as const,
      id: `ais-marker-${vessel.mmsi}`,
      properties: {
        mmsi: vessel.mmsi,
        vesselName: vessel.name,
        vesselType: vessel.type,
        speed: lastPoint.speed,
        course: lastPoint.course,
        heading: lastPoint.heading,
        timestamp: lastPoint.timestamp,
        markerId: `marker-${vessel.mmsi}`,
      },
      geometry: {
        type: 'Point' as const,
        coordinates: [vessel.latestPosition.longitude, vessel.latestPosition.latitude],
      },
    }
  })

  return {
    type: 'FeatureCollection',
    features,
  }
}
