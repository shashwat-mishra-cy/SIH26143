"""Backend AIS analysis service integration."""

from datetime import datetime
from pathlib import Path

from shared.schemas.contracts import AISResult
from ais.analysis.pipeline import analyze_ais

try:
    import polars as pl
    POLARS_AVAILABLE = True
except ImportError:
    POLARS_AVAILABLE = False


def load_ais_parquet(parquet_path: Path) -> dict[str, list[dict]]:
    """Load cleaned AIS parquet file and reconstruct vessel trajectories."""
    if not POLARS_AVAILABLE:
        raise RuntimeError("Polars not installed. Install with: pip install polars")
    
    if not parquet_path.exists():
        raise RuntimeError(f"AIS data file not found: {parquet_path}")
    
    df = pl.read_parquet(parquet_path)
    trajectories = {}
    
    for mmsi, group in df.group_by("mmsi"):
        mmsi_str = str(mmsi)
        sorted_group = group.sort("base_date_time")
        
        points = []
        for row in sorted_group.iter_rows(named=True):
            point = {
                "timestamp": row.get("base_date_time"),
                "latitude": row.get("latitude"),
                "longitude": row.get("longitude"),
                "speed_kmh": row.get("sog"),
                "heading": row.get("heading"),
                "course_over_ground": row.get("cog"),
                "vessel_type": row.get("vessel_type"),
                "status": row.get("status"),
            }
            points.append(point)
        
        trajectories[mmsi_str] = points
    
    return trajectories


def execute_ais_analysis(
    vessel_trajectories: dict[str, list[dict]],
    source_region_polygon: dict,
    release_window_start: datetime,
    release_window_end: datetime,
    spill_id: str | None = None,
) -> AISResult:
    """Execute complete AIS analysis pipeline."""
    result = analyze_ais(
        vessel_trajectories=vessel_trajectories,
        source_region_polygon=source_region_polygon,
        release_window_start=release_window_start,
        release_window_end=release_window_end,
        spill_id=spill_id,
    )
    
    return result
