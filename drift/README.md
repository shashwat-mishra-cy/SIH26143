# Drift & Ocean Forcing Module (`/drift`)

## 1. Module Overview
The `drift` module (P2) is responsible for environmental forcing data ingestion and OpenDrift-based particle ensemble simulation for backward ocean drift modeling. Its main purpose in the SIH26143 framework is to receive detected oil spill geometries (Polygon or MultiPolygon) and acquisition timestamps from the `satellite` module (P1), apply backward hindcast particle tracking against ocean current and surface wind fields with configurable horizontal diffusion, perform 2D Kernel Density Estimation (KDE) and 50% / 90% Highest Density Region (HDR) spatial analysis, and compute probable source-support regions and candidate release-time estimates to pass to Person 3's `ais` module for candidate vessel attribution.

## 2. Architecture & Data Flow Pipeline

```text
  [ Satellite Spill Output (P1: Polygon / MultiPolygon + Acquisition Timestamp) ]
                                      │
                                      ▼
                        [ Environmental Forcing Data ]
               (Ocean Currents: u_curr, v_curr | Surface Winds: u10, v10)
                                      │
                                      ▼
                   [ OpenDrift Particle Ensemble Hindcast ]
                   - Backward Stochastic Particle Tracking
                   - Configurable Horizontal Diffusion (e.g. 1.0 m²/s)
                   - 10-Minute Resolution Trajectories (P4 Dashboard Input)
                                      │
                                      ▼
                   [ Spatial KDE & 50% / 90% HDR Extraction ]
                 (Preserving Exact Polygon / MultiPolygon Boundaries)
                                      │
                                      ▼
                   [ Temporal Source-Support Diagnostics ]
                 (50% / 90% HDR Area Dynamics & Centroid Displacements)
                                      │
                                      ▼
                   [ Scientific Source-Time Window Estimator ]
            (Explicit Indeterminate Statuses & Candidate Source Time)
                                      │
                                      ▼
               [ P2 -> P3 DriftSourceResult Handoff Contract ]
                           (drift/simulation/handoff.py)
```

## 3. Interfaces & Contracts

### 3.1 Input Interface (from Satellite Module - P1)
The interface from the `satellite` module provides detected oil spill geometric and acquisition attributes:

- `spill_id`: Unique identifier for the detected oil spill event (string / UUID).
- `timestamp`: Observation acquisition time in UTC from satellite metadata.
- `centroid`: GeoJSON Point or (latitude, longitude) coordinate of the spill centroid.
- `spill_polygon`: GeoJSON Polygon or MultiPolygon representing the spatial contour of the detected slick.
- `spill_area`: Calculated surface area of the slick (square kilometers).
- `confidence`: Satellite detection confidence score (float [0.0 - 1.0]).

*Timestamp Rule:* P2 must not invent or assume a satellite timestamp. The timestamp must originate from valid satellite metadata or a user-provided observation timestamp. If no valid timestamp is available, time-dependent source reconstruction and temporal AIS correlation are limited/unavailable, and P4 should clearly indicate timestamp unavailability on the dashboard.

### 3.2 Output Handoff Interface (to AIS Module - P3)
Implemented and validated in `drift/simulation/handoff.py` (`DriftSourceResult` schema version 1.0):

- `schema_version`: `"1.0"`
- `spill_id`: Unique identifier matching the input satellite spill event.
- `detection`: Detection timestamp, latitude, and longitude.
- `source_time`: Candidate source-time timestamp (`null` when status is indeterminate) and scientific estimator status (`candidate_identified`, `indeterminate_flat_signal`, `indeterminate_boundary_minimum`, `indeterminate_conflicting_minima`, `insufficient_temporal_data`).
- `source_support`: GeoJSON 50% and 90% HDR source-support geometries (Polygon or MultiPolygon preserved without simplification) and corresponding areas in $\text{km}^2$.
- `model`: Ensemble particle count, backward duration in hours, time step in minutes, and horizontal diffusivity in $\text{m}^2/\text{s}$.
- `status`: Execution status (e.g. `"success"`).

*Note on Shared Schemas:* The validated P2->P3 handoff is implemented in `drift/simulation/handoff.py`. Before introducing a project-wide shared schema (e.g. `shared/schemas/contracts.py`), the team should agree on the final P1->P2->P3 contract.

## 4. Submodules & Package Layout

```text
drift/
├── README.md                 # Module documentation and data flow overview
├── __init__.py               # Package initialization
├── data/
│   ├── README.md             # Forcing data specifications and interface documentation
│   ├── __init__.py           # Subpackage initialization
│   └── environment.py        # Environmental data loader and adapter stubs
└── simulation/
    ├── README.md             # OpenDrift simulation pipeline architecture
    ├── __init__.py           # Subpackage initialization
    ├── forward.py            # Forward drift simulation stubs
    ├── backward.py           # Backward hindcast drift simulation stubs
    └── source_estimation.py  # Probable source region & release window estimation stubs
```

## 5. Module Independence & Testing Strategy
- The `drift` module is designed to operate independently using abstract data loaders and mock spill inputs.
- Data ingestion and simulation components depend on stub interfaces, ensuring unit tests and integration harnesses can execute without live oceanographic data feeds or external web service calls.
