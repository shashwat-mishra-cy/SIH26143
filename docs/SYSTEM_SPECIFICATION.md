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
- **Simulation (`drift/simulation`):** Backward particle tracking / hindcast simulation modeling slick movement back in time.
- **Data (`drift/data`):** Forcing data management for sea surface currents (HYCOM/CMEMS), winds (ERA5/GFS), and wave conditions.

### 2.3 AIS Processing & Vessel Ranking (`/ais`)
- **Preprocessing (`ais/preprocessing`):** Ingestion, cleaning, deduplication, and spatial indexing of historical AIS vessel trajectory logs.
- **Ranking (`ais/ranking`):** Spatial-temporal correlation between vessel trajectories and estimated drift release regions/time windows to rank candidate vessels.

### 2.4 Backend (`/backend`)
- Service layer orchestrating pipeline steps (Satellite -> Drift -> AIS -> Report), handling async task execution, and providing REST API endpoints.

### 2.5 Dashboard (`/dashboard`)
- Interactive web UI displaying SAR imagery overlays, extracted spill geometries, drift trajectories, candidate vessel paths, and attribution scores.

### 2.6 Shared Schemas (`/shared/schemas`)
- Standardized Pydantic models defining JSON interface contracts between all system modules.

### 2.7 Integration (`/integration/mock_data`)
- Test harnesses and mock data instances for end-to-end verification without live data pipelines.
