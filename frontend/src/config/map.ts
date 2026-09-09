import type { ViewState } from 'react-map-gl/maplibre'
import type { StyleSpecification } from 'maplibre-gl'

/**
 * Initial map viewport — Mumbai / Arabian Sea.
 */
export const INITIAL_VIEW_STATE: ViewState = {
  latitude: 18.52,
  longitude: 72.85,
  zoom: 7,
  bearing: 0,
  pitch: 0,
  padding: { top: 0, bottom: 0, left: 0, right: 0 },
}

export type BasemapId = 'satellite' | 'ocean' | 'dark' | 'streets'

export interface BasemapConfig {
  id: BasemapId
  name: string
  subtitle: string
  icon: string
  tiles: string[]
  referenceTiles?: string[]
  attribution: string
  maxZoom?: number
}

/**
 * Real, authentic GIS basemaps without API key watermarks.
 * Esri World Imagery provides genuine photorealistic satellite Earth & ocean imagery.
 * Esri World Ocean Base provides specialized oceanographic bathymetry & marine topography.
 */
export const BASEMAP_CONFIGS: Record<BasemapId, BasemapConfig> = {
  satellite: {
    id: 'satellite',
    name: 'Satellite Earth',
    subtitle: 'Photorealistic satellite Earth & ocean',
    icon: '🛰️',
    tiles: [
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    ],
    referenceTiles: [
      'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
    ],
    attribution:
      '&copy; <a href="https://www.esri.com/">Esri</a>, Maxar, Earthstar Geographics, USDA, USGS, AeroGRID, IGN, and the GIS User Community',
    maxZoom: 19,
  },
  ocean: {
    id: 'ocean',
    name: 'Ocean Bathymetry',
    subtitle: 'Marine depth contours & undersea relief',
    icon: '🌊',
    tiles: [
      'https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}',
    ],
    referenceTiles: [
      'https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Reference/MapServer/tile/{z}/{y}/{x}',
    ],
    attribution:
      '&copy; <a href="https://www.esri.com/">Esri</a>, GEBCO, NOAA, National Geographic, DeLorme, HERE, Geonames.org, and other contributors',
    maxZoom: 13,
  },
  dark: {
    id: 'dark',
    name: 'Dark Maritime',
    subtitle: 'High-contrast nocturnal canvas (watermark-free)',
    icon: '🎯',
    tiles: [
      'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
    ],
    referenceTiles: [
      'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}',
    ],
    attribution:
      '&copy; <a href="https://www.esri.com/">Esri</a>, HERE, Garmin, &copy; OpenStreetMap contributors',
    maxZoom: 16,
  },
  streets: {
    id: 'streets',
    name: 'Navigation Chart',
    subtitle: 'OpenStreetMap standard coastal navigation',
    icon: '🗺️',
    tiles: [
      'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    ],
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
  },
}

/**
 * OpenSeaMap maritime navigation overlay (seamarks, buoys, lighthouses, shipping channels).
 */
export const SEAMARKS_OVERLAY_CONFIG = {
  tiles: ['https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png'],
  attribution:
    '&copy; <a href="http://www.openseamap.org">OpenSeaMap</a> contributors',
}

/**
 * Clean base style specification for MapLibre GL.
 * Raster layers are mounted dynamically inside the Map container.
 */
export const BASE_MAP_STYLE: StyleSpecification = {
  version: 8,
  sources: {},
  layers: [
    {
      id: 'background',
      type: 'background',
      paint: {
        'background-color': '#060c14',
      },
    },
  ],
}

/**
 * Backwards compatibility default style.
 */
export const MAP_STYLE = BASE_MAP_STYLE

/**
 * Region label shown in the status bar.
 */
export const REGION_LABEL = 'MUMBAI / ARABIAN SEA'