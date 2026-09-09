import type { DriftSimulation } from '../../types/drift'
import {
  buildSourceRegionPolygon,
  buildBackwardTrajectories,
} from '../../geo/driftPolygon'

/**
 * DEMO backward drift / hindcast simulation — SIH26143 Phase 3.
 *
 * IMPORTANT: These values are demonstration data for UI development.
 * They are NOT real results from an actual OpenDrift simulation and
 * must not be presented as such.
 *
 * The source region is intentionally positioned SOUTHWEST of the observed
 * spill (18.52°N, 72.85°E), representing a plausible backward hindcast
 * in the Arabian Sea.
 */
export const DEMO_DRIFT_SIMULATION: DriftSimulation = {
  simulationId: 'DRIFT-2025-01-01-MUMBAI-01',
  spillId: 'SPILL-2025-01-01-MUMBAI-01',
  model: 'OpenDrift',
  mode: 'backward',
  estimatedReleaseWindow: {
    startTime: '2024-12-31T22:00:00Z',
    endTime: '2025-01-01T02:00:00Z',
  },
  sourceConfidence: 0.78,
  sourceRegion: {
    id: 'SOURCE-2025-01-01-MUMBAI-01',
    geometry: buildSourceRegionPolygon(
      {
        latitude: 18.45,
        longitude: 72.70,
      },
      3.5,
      2.8,
      45,
    ),
    bounds: {
      minLatitude: 18.42,
      maxLatitude: 18.48,
      minLongitude: 72.65,
      maxLongitude: 72.76,
    },
    confidence: 0.78,
  },
  trajectories: Array.from({ length: 12 }, (_, i) => ({
    id: `TRAJ-${i + 1}`,
    path: buildBackwardTrajectories(
      { latitude: 18.52, longitude: 72.85 },
      { latitude: 18.45, longitude: 72.70 },
      1,
    ),
  })),
  isDemo: true,
  disclaimer:
    'Demonstration data — not a real result from an actual OpenDrift simulation.',
}

/**
 * Build all 12 backward trajectories as a single MultiLineString.
 * This is the complete trajectory collection for map rendering.
 */
export const DEMO_BACKWARD_TRAJECTORIES = buildBackwardTrajectories(
  { latitude: 18.52, longitude: 72.85 },
  { latitude: 18.45, longitude: 72.70 },
  12,
)
