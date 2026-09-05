# Environmental Forcing Data Interface (`drift/data`)

## 1. Overview
The `drift/data` package defines the interface requirements and data access layer for environmental forcing fields used in oil spill drift modeling. Drift simulations rely on surface wind vectors and ocean surface current vectors to advect and disperse oil particles over time.

## 2. Environmental Forcing Attributes

The expected interface for environmental forcing data covers both atmospheric and oceanographic components:

| Parameter Field | Data Category | Interface Specification & Requirements |
| :--- | :--- | :--- |
| **Wind Fields** | Atmospheric | Eastward ($u_{10}$) and Northward ($v_{10}$) surface wind velocity components measured at 10 meters above sea level. |
| **Ocean Surface Current Fields** | Oceanographic | Eastward ($u_{curr}$) and Northward ($v_{curr}$) surface ocean current velocity components at surface layer (0m depth). |
| **Timestamps** | Temporal | UTC timestamps corresponding to continuous time steps across the simulation window (ISO 8601 / datetime index). |
| **Latitude/Longitude Coordinates** | Spatial | Geodetic coordinates (WGS84, EPSG:4326) specifying grid node locations for vector field evaluation. |
| **Units** | Measurement | Velocity components in meters per second ($\text{m/s}$ or $\text{m s}^{-1}$); coordinates in decimal degrees ($^\circ\text{N}, ^\circ\text{E}$). |
| **Spatial Resolution** | Grid Resolution | Resolution of forcing grids (e.g., $0.25^\circ \times 0.25^\circ$ or $1/12^\circ \times 1/12^\circ$). |
| **Temporal Resolution** | Frequency | Time step resolution of forcing datasets (e.g., 1-hour, 3-hour, or 6-hour interval updates). |

## 3. Candidate Data Sources

The following datasets are listed as candidate/example sources in technical planning and require evaluation prior to live integration:

- **Surface Wind Fields:** Candidate source ERA5 Reanalysis (ECMWF) or Global Forecast System (GFS).
- **Ocean Current Fields:** Candidate source HYCOM (Hybrid Coordinate Ocean Model) or CMEMS (Copernicus Marine Environment Monitoring Service).

*Note: These sources represent potential candidates under consideration. Exact dataset availability, spatial coverage, API access key requirements, and final spatial/temporal resolutions will be verified and documented once data pipelines are finalized.*

## 4. Input Requirements for Drift Simulation Engine

To perform particle advection, the forcing data loader must expose:
1. Interpolation functions in spatial coordinates $(x, y, z)$ and temporal coordinate $t$.
2. Boundary spatial coverage extending beyond the estimated spill trajectory path.
3. Temporal coverage spanning from the observed spill detection time back to the maximum candidate release search window.
