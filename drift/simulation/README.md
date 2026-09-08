# Drift Simulation Engine (`drift/simulation`)

## 1. Architecture & OpenDrift Implementation Pipeline
The `drift/simulation` package implements OpenDrift-based Lagrangian particle tracking for backward ocean drift reconstruction. It receives oil spill geometries (Polygon / MultiPolygon) and acquisition timestamps from P1, applies backward particle tracking against ocean current and surface wind fields, and computes spatial and temporal source-support estimates for Person 3's AIS candidate vessel indexing pipeline.

```text
               +----------------------------------+
               |  Satellite Spill Detection Input |
               | (Polygon/MultiPolygon + Timestamp|
               +----------------------------------+
                                │
                                ▼
               +----------------------------------+
               | Environmental Forcing Ingestion  |
               | (Winds: u10, v10 | Currents: u,v)|
               +----------------------------------+
                                │
                                ▼
               +----------------------------------+
               |   OpenDrift Hindcast Simulation  |
               |   - Backward Particle Ensemble   |
               |   - Configurable Random Walk     |
               |   - Wind Leeway + Current Coupling|
               +----------------------------------+
                                │
                                ▼
               +----------------------------------+
               | Spatial KDE & 50% / 90% HDR      |
               | Source-Support Regions           |
               +----------------------------------+
                                │
                                ▼
               +----------------------------------+
               | Temporal Diagnostics & Scientific|
               | Source-Time Window Estimator     |
               +----------------------------------+
                                │
                                ▼
               +----------------------------------+
               | P2 -> P3 DriftSourceResult       |
               | Handoff Contract (handoff.py)    |
               +----------------------------------+
```

## 2. Core Components & Pipeline Implementation

### 2.1 Backward / Hindcast Particle Ensemble Tracking (`backward.py`)
Backward drift operates in reverse time ($t_{obs} \to t_{obs} - \Delta t$). Starting from the satellite-observed spill polygon/centroid and acquisition timestamp, an ensemble of particles (e.g., $N=1000$) is tracked backward along inverted velocity vectors to backtrack where and when the release likely originated.

### 2.2 Particle Trajectories & P4 Visualization Interface
Each particle's trajectory is integrated at 10-minute time steps. P2 emits trajectory data:
- `particle_id`: Unique integer identifier per particle.
- `timestamp`: UTC timestamp for each 10-minute step.
- `latitude` / `longitude`: Coordinates at each step.

P4 (Dashboard) can ingest and downsample these trajectories (e.g. to 30-minute intervals) for UI visualization.

### 2.3 Environmental Forcing & Diffusion
Particles dynamically query ocean currents ($u_{curr}, v_{curr}$) and surface winds ($u_{10}, v_{10}$). Stochastic random-walk diffusion is controlled via configurable horizontal diffusivity $D_x$ (e.g., $1.0\text{ m}^2/\text{s}$).

### 2.4 Spatial KDE & HDR Extraction (`kde.py`, `hdr.py`, `hdr_geometry.py`)
- **Metric Projection (`coordinates.py`):** Converts WGS84 geographic coordinates to Azimuthal Equidistant (AEQD) metric projections centered at the spill centroid for isotropic density estimation.
- **2D Kernel Density Estimation (`kde.py`):** Computes continuous probability densities over spatial grids.
- **50% and 90% Highest Density Regions (`hdr.py`, `hdr_geometry.py`):** Determines strict numerical density thresholds containing 50% and 90% of total particle probability mass, and extracts GeoJSON `Polygon` or `MultiPolygon` boundaries without geometric simplification.

### 2.5 Temporal Source-Support Analysis (`source_support.py`, `source_support_diagnostics.py`)
Analyzes spatial area contraction/expansion dynamics and centroid drift displacements across hindcast timesteps to track origin convergence.

### 2.6 Scientific Source-Time Estimator (`source_estimation.py`)
Evaluates temporal diagnostics to estimate a candidate source time. Returns explicit estimator statuses:
- `candidate_identified`: Evidence supports a distinct temporal area minimum.
- `indeterminate_flat_signal`: HDR area curve lacks a clear minimum (flat signal).
- `indeterminate_boundary_minimum`: Minimum occurs at the edge of the simulation window.
- `indeterminate_conflicting_minima`: Multiple competing minima detected.
- `insufficient_temporal_data`: Insufficient timesteps for temporal analysis.

When status is indeterminate, the source-time candidate timestamp is explicitly set to `null` in the handoff contract.

### 2.7 P2 -> P3 Handoff Contract (`handoff.py`)
Defines the `DriftSourceResult` schema version 1.0 containing source-support geometries (50% and 90% HDR), HDR areas, candidate source-time and estimator status, model parameters, and detection metadata.

## 3. Guiding Rules & Terminology

### 3.1 Satellite Timestamp Rule
- P2 must not invent or assume a satellite timestamp.
- Timestamp must originate from valid satellite metadata or acquisition timestamp.
- If no scientifically valid timestamp is available, time-dependent source reconstruction and temporal AIS correlation are limited/unavailable. P4 should clearly indicate timestamp unavailability.

### 3.2 Scientifically Cautious Terminology
All output contracts and documentation use scientifically cautious terminology:
- Terms used: **"probable source region"**, **"source-support region"**, **"possible backward trajectories"**, **"potential association"**, and **"uncertainty"**.
- P2 outputs represent probabilistic oceanographic drift support and do **NOT** claim an exact source point, exact release time, or proof of vessel causality.
