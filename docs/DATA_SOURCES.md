# SIH26143 — Data Sources Documentation

## 1. Synthetic Aperture Radar (SAR) Imagery
- **Source:** Copernicus Sentinel-1 (C-band SAR)
- **Mode:** Interferometric Wide (IW) swath mode, Ground Range Detected (GRD) / Single Look Complex (SLC).
- **Purpose:** All-weather, day-and-night sea surface slick detection based on radar backscatter damping.

## 2. Oceanographic & Meteorological Data
- **Wind Vector Data:** ERA5 Reanalysis / GFS surface wind predictions (10m u/v components).
- **Ocean Current Data:** HYCOM / Copernicus Marine Environment Monitoring Service (CMEMS) global ocean current reanalysis/forecasts.
- **Purpose:** Forcing inputs for backward particle drift / hindcast simulations.

## 3. Automatic Identification System (AIS) Data
- **Data Type:** Historical vessel movement logs (MMSI, Timestamp, Latitude, Longitude, Speed Over Ground (SOG), Course Over Ground (COG)).
- **Purpose:** Spatio-temporal correlation with backward drift release windows for candidate vessel attribution.
