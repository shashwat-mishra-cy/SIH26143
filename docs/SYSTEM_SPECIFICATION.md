# SIH26143 — System Architecture & Specification

## 1. Overview
The SIH26143 system automates the process of oil spill detection from SAR satellite imagery, backward ocean drift simulation for origin estimation, and candidate vessel attribution through historical AIS tracking correlation.

## 2. Module Specifications

### 2.1 Satellite Processing (`/satellite`)
- **Preprocessing (`satellite/preprocessing`):** Radiometric calibration, speckle reduction, terrain correction, thermal noise removal.
- **Model (`satellite/model`):** Deep learning segmentation models (e.g., U-Net, DeepLabV3+) trained on SAR oil spill datasets.
- **Training (`satellite/training`):** Model training pipelines, loss functions, hyperparameter optimization, and validation metrics.
- **Inference (`satellite/inference`):** Batch/real-time inference pipelines producing segmentation masks from SAR input scenes.
- **Geometry (`satellite/geometry`):** Vectorization of oil slicks, area calculation, centroid determination, and GeoJSON polygon generation.

### 2.2 Drift Simulation (`/drift`)
- **Simulation (`drift/simulation`):** OpenDrift-based backward particle tracking ensemble modeling probable source-support regions back in time.
  - **Input:**
    - Spill GeoJSON Polygon or MultiPolygon geometry (from Satellite module P1).
    - Spill centroid/location.
    - Observation/detection acquisition timestamp (when scientifically valid and available from satellite metadata).
    - Environmental forcing data (ocean surface currents and surface winds).
  - **Processing:**
    - Backward OpenDrift particle ensemble tracking (stochastic random-walk diffusion).
    - Surface wind forcing ($u_{10}, v_{10}$) and ocean-current forcing ($u_{curr}, v_{curr}$) coupling.
    - Configurable horizontal diffusion (e.g. $1.0\text{ m}^2/\text{s}$).
    - 2D Kernel Density Estimation (KDE) spatial density calculation on metric projections.
    - 50% and 90% Highest Density Region (HDR) source-support extraction.
    - Temporal source-support diagnostic analysis across hindcast timesteps.
    - Source-time estimation with explicit uncertainty and indeterminate state handling (`candidate_identified`, `indeterminate_flat_signal`, `indeterminate_boundary_minimum`, `indeterminate_conflicting_minima`, `insufficient_temporal_data`).
  - **Output:**
    - Backward particle trajectories (particle ID, timestamp, latitude, longitude at 10-minute resolution) for P4 dashboard rendering (which P4 can downsample to e.g. 30-minute intervals).
    - 50% HDR source-support region (GeoJSON Polygon or MultiPolygon preserving multi-component boundaries without simplification).
    - 90% HDR source-support region (GeoJSON Polygon or MultiPolygon preserving multi-component boundaries without simplification).
    - HDR spatial areas ($\text{km}^2$).
    - Candidate source-time estimate when supported (set to `null` when estimator status is indeterminate).
    - Source estimator status and supporting diagnostics.
    - Structured P2 -> P3 `DriftSourceResult` handoff contract (implemented in `drift/simulation/handoff.py`).
  - **Timestamp Rule:**
    - P2 must not invent or assume a satellite timestamp. The timestamp must originate from valid satellite metadata or acquisition timestamp.
    - If no scientifically valid timestamp is available, time-dependent source reconstruction and temporal AIS correlation are limited/unavailable, and P4 should clearly indicate timestamp unavailability.
  - **Terminology & Scientific Integrity:**
    - Uses scientifically cautious terminology: "probable source region", "source-support region", "possible backward trajectories", "potential association", and "uncertainty".
    - Outputs represent physical model support and do NOT claim an exact source point, exact release time, or proof of vessel causality.
- **Data (`drift/data`):** Forcing data management for sea surface currents (HYCOM/CMEMS), winds (ERA5/GFS), and wave conditions.

### 2.3 AIS Processing & Vessel Ranking (`/ais`)
- **Preprocessing (`ais/preprocessing`):** Ingestion, cleaning, deduplication, and spatial indexing of historical AIS vessel trajectory logs.
- **Ranking (`ais/ranking`):** Spatial-temporal correlation between vessel trajectories and estimated drift release regions/time windows to rank candidate vessels.

### 2.4 Backend (`/backend`)
- Service layer orchestrating pipeline steps (Satellite -> Drift -> AIS -> Report), handling async task execution, and providing REST API endpoints.

### 2.5 Dashboard (`/dashboard`)
- Interactive web UI displaying SAR imagery overlays, extracted spill geometries, drift trajectories, candidate vessel paths, and attribution scores.

### 2.6 Shared Schemas (`/shared/schemas`)
- Standardized models defining JSON interface contracts between system modules.
  * *P2 -> P3 Handoff Contract:* Currently implemented and validated in `drift/simulation/handoff.py` (`DriftSourceResult`). Project-wide shared schemas in `shared/schemas/` will be aligned once the team agrees on final inter-module contracts.

### 2.7 Integration (`/integration/mock_data`)
- Test harnesses and mock data instances for end-to-end verification without live data pipelines.
