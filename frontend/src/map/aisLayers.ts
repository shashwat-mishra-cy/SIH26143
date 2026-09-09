import type { LayerProps } from 'react-map-gl/maplibre'

/**
 * MapLibre layer definition for AIS vessel trajectories.
 *
 * Uses feature-state expressions to highlight:
 * - selected vessel (highest priority)
 * - Top 3 ranked associations (rank: 1, 2, 3)
 * - other vessels (subdued)
 */
export const AIS_TRAJECTORY_LAYER: LayerProps = {
  id: 'ais-trajectories',
  type: 'line',
  source: 'ais-trajectories-source',
  paint: {
    'line-color': [
      'case',
      ['==', ['feature-state', 'selected'], true],
      '#0055aa', // selected: darker blue
      ['==', ['feature-state', 'rank'], 1],
      '#ff9500', // Top 1: warm gold/amber
      ['==', ['feature-state', 'rank'], 2],
      '#0088cc', // Top 2: bright cyan
      ['==', ['feature-state', 'rank'], 3],
      '#22cc44', // Top 3: vibrant green
      '#4499dd', // other: subdued blue
    ],
    'line-width': [
      'case',
      ['==', ['feature-state', 'selected'], true],
      2.5, // selected: thicker
      ['==', ['feature-state', 'rank'], 1],
      2.2, // Top 1: prominent
      ['==', ['feature-state', 'rank'], 2],
      1.8, // Top 2: medium
      ['==', ['feature-state', 'rank'], 3],
      1.8, // Top 3: medium
      1.2, // other: thin
    ],
    'line-opacity': [
      'case',
      ['==', ['feature-state', 'selected'], true],
      1.0, // selected: fully opaque
      ['==', ['feature-state', 'rank'], 1],
      0.9, // Top 1: very opaque
      ['==', ['feature-state', 'rank'], 2],
      0.85, // Top 2: opaque
      ['==', ['feature-state', 'rank'], 3],
      0.85, // Top 3: opaque
      0.55, // other: semi-transparent
    ],
  },
}

/**
 * MapLibre layer definition for AIS vessel position markers.
 *
 * Uses feature-state expressions to highlight:
 * - selected vessel (highest priority)
 * - Top 3 ranked associations (rank: 1, 2, 3)
 * - other vessels (subdued)
 */
export const AIS_MARKER_LAYER: LayerProps = {
  id: 'ais-vessel-markers',
  type: 'circle',
  source: 'ais-markers-source',
  paint: {
    'circle-radius': [
      'case',
      ['==', ['feature-state', 'selected'], true],
      6.5, // selected: larger
      ['==', ['feature-state', 'rank'], 1],
      5.5, // Top 1: prominent
      ['==', ['feature-state', 'rank'], 2],
      4.8, // Top 2: medium
      ['==', ['feature-state', 'rank'], 3],
      4.8, // Top 3: medium
      3.5, // other: small
    ],
    'circle-color': [
      'case',
      ['==', ['feature-state', 'selected'], true],
      '#0055aa', // selected: darker blue
      ['==', ['feature-state', 'rank'], 1],
      '#ff9500', // Top 1: warm gold/amber
      ['==', ['feature-state', 'rank'], 2],
      '#0088cc', // Top 2: bright cyan
      ['==', ['feature-state', 'rank'], 3],
      '#22cc44', // Top 3: vibrant green
      '#4499dd', // other: subdued blue
    ],
    'circle-stroke-color': '#ffffff',
    'circle-stroke-width': [
      'case',
      ['==', ['feature-state', 'selected'], true],
      2.2, // selected: thicker outline
      ['==', ['feature-state', 'rank'], 1],
      1.8, // Top 1: prominent outline
      ['==', ['feature-state', 'rank'], 2],
      1.5, // Top 2: medium outline
      ['==', ['feature-state', 'rank'], 3],
      1.5, // Top 3: medium outline
      1.0, // other: thin outline
    ],
    'circle-opacity': 0.85,
  },
}
