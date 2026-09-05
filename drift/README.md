# Drift & Ocean Forcing Module (`/drift`)

## 1. Module Overview
The `drift` module is responsible for environmental forcing data ingestion and OpenDrift-based particle simulation for oil slick transport modeling. Its main purpose in the SIH26143 framework is to receive detected oil spill geometries from the `satellite` module, apply backward hindcast particle tracking against ocean current and surface wind fields, and compute the probable source region and estimated release-time window to pass to the `ais` module for vessel attribution.

## 2. Architecture & Data Flow Pipeline

```text
  [ Satellite Spill Output ]
              │
              ▼
  [ Environmental Forcing Data ]
   (Ocean Currents & Surface Winds)
              │
              ▼
  [ OpenDrift Engine / Simulation ]
              │
              ▼
  [ Backward Hindcast Tracking ]
              │
              ▼
  [ Probable Source Region & Release Window ]
              │
              ▼
    [ Confidence Calculation ]
              │
              ▼
      [ AIS Module Input ]
```

## 3. Conceptual Interfaces

### 3.1 Input Interface (from Satellite Module)
The conceptual interface from the `satellite` module provides detected oil spill geometric and temporal attributes:

- `spill_id`: Unique identifier for the detected oil spill event (string / UUID).
- `timestamp`: Observation acquisition time in UTC (ISO 8601 string or datetime).
- `centroid`: GeoJSON Point or (latitude, longitude) coordinate of the spill centroid.
- `spill_polygon`: GeoJSON Polygon representing the spatial contour of the detected slick.
- `spill_area`: Calculated surface area of the slick (e.g., square kilometers).
- `confidence`: Satellite detection confidence score (float [0.0 - 1.0]).

*Note: Formal schema definitions reside in `shared/schemas/`. The schema is subject to team consensus and final contract agreement.*

### 3.2 Output Interface (to AIS Module)
The conceptual output interface emitted to the `ais` module for spatial-temporal vessel matching:

- `spill_id`: Unique identifier matching the input satellite spill event.
- `probable_source_region`: Spatial probability distribution or GeoJSON polygon bounding box defining the estimated origin zone.
- `estimated_release_window`: Estimated temporal window (start UTC time, end UTC time) during which the release occurred.
- `confidence`: Confidence score associated with the backward hindcast estimation (float [0.0 - 1.0]).

*Note: Final output attributes and data types will align with shared contracts in `shared/schemas/`.*

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
