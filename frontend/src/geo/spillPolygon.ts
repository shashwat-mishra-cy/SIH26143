import type { Polygon } from 'geojson'

/**
 * Build an irregular, elongated GeoJSON polygon resembling a plausible
 * oil slick centred at `centroid`, sized by `lengthKm` x `widthKm` and
 * oriented `orientationDeg` clockwise from north.
 *
 * The shape is an ellipse perturbed with low-frequency harmonics so it
 * is NOT a perfect circle and looks like a natural dark feature.
 */
export function buildSpillPolygon(
  centroid: { latitude: number; longitude: number },
  lengthKm: number,
  widthKm: number,
  orientationDeg: number,
  segments = 28,
): Polygon {
  const latRad = (centroid.latitude * Math.PI) / 180
  const kmPerDegLat = 111.0
  const kmPerDegLon = 111.0 * Math.cos(latRad)
  const theta = (orientationDeg * Math.PI) / 180

  const halfLen = lengthKm / 2
  const halfWid = widthKm / 2

  const ring: [number, number][] = []

  for (let i = 0; i < segments; i++) {
    const angle = (2 * Math.PI * i) / segments

    // Irregularity: low-frequency perturbation of the radius.
    const irregularity =
      1 +
      0.13 * Math.sin(3 * angle + 0.7) +
      0.09 * Math.cos(5 * angle + 2.1) +
      0.05 * Math.sin(7 * angle + 4.0)

    // Local ellipse coordinates (major axis along x).
    const x = halfLen * Math.cos(angle) * irregularity
    const y = halfWid * Math.sin(angle) * irregularity

    // Rotate so the major axis points along `orientationDeg` (from north).
    const east = x * Math.sin(theta) + y * Math.cos(theta)
    const north = x * Math.cos(theta) - y * Math.sin(theta)

    const latitude = centroid.latitude + north / kmPerDegLat
    const longitude = centroid.longitude + east / kmPerDegLon

    ring.push([round(longitude, 6), round(latitude, 6)])
  }

  // Close the ring.
  ring.push([...ring[0]])

  return {
    type: 'Polygon',
    coordinates: [ring],
  }
}

function round(value: number, digits: number): number {
  const factor = 10 ** digits
  return Math.round(value * factor) / factor
}