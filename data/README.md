# SIH26143 Data Directory Guidelines

## Storage Guidelines
1. **Git Hygiene:** Do NOT commit raw or large binary data files to the repository.
2. **Local Storage:** Store raw dataset files locally under `data/raw/` and intermediate outputs under `data/processed/`. Both are excluded via `.gitignore`.
3. **Data Handling:** Access data via configured path variables rather than relative hardcoded paths.

## Directory Structure
- `data/raw/satellite/`: Raw Sentinel-1 SAFE packages or GeoTIFFs.
- `data/raw/ocean/`: NetCDF files containing wind and current vector data.
- `data/raw/ais/`: Raw AIS CSV or JSON logs.
- `data/processed/`: Processed segmentation masks, slick GeoJSON polygons, and drift grids.
