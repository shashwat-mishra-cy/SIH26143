"""Association scoring for AIS vessel correlation."""

from datetime import datetime
from typing import NamedTuple
from .geometry import haversine_distance_km, point_in_polygon
from .candidate_filter import CandidateFilterResult


class AssociationScoreResult(NamedTuple):
    """Association score result for one vessel."""
    mmsi: str
    is_candidate: bool
    temporal_score: int
    proximity_score: int
    trajectory_score: int
    association_score: int
    rank: int | None


TEMPORAL_WEIGHT = 0.30
PROXIMITY_WEIGHT = 0.40
TRAJECTORY_WEIGHT = 0.30


def calculate_temporal_score(
    vessel_trajectory: list[dict],
    release_window_start: datetime,
    release_window_end: datetime,
) -> int:
    """Calculate temporal compatibility score (0-100)."""
    window_duration_ms = (release_window_end - release_window_start).total_seconds() * 1000
    
    overlap_start_ms = None
    overlap_end_ms = None
    
    for point in vessel_trajectory:
        ts = point.get("timestamp")
        if ts is None:
            continue
        
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        
        if release_window_start <= ts <= release_window_end:
            ts_ms = (ts - release_window_start).total_seconds() * 1000
            
            if overlap_start_ms is None:
                overlap_start_ms = ts_ms
            overlap_end_ms = ts_ms
    
    if overlap_start_ms is None or overlap_end_ms is None:
        return 0
    
    overlap_duration_ms = overlap_end_ms - overlap_start_ms
    temporal_coverage = min(overlap_duration_ms / window_duration_ms, 1.0)
    
    return int(temporal_coverage * 100)


def calculate_proximity_score(
    minimum_distance_km: float,
    max_distance_km: float = 15.0,
) -> int:
    """Calculate source proximity score (0-100)."""
    if minimum_distance_km < 0:
        return 0
    
    if minimum_distance_km >= max_distance_km:
        return 0


def calculate_trajectory_score(
    vessel_trajectory: list[dict],
    source_region_polygon: dict,
    release_window_start: datetime,
    release_window_end: datetime,
) -> int:
    """Calculate trajectory compatibility score (0-100)."""
    closest_approach_km = float("inf")
    
    for point in vessel_trajectory:
        lat = point.get("latitude")
        lon = point.get("longitude")
        ts = point.get("timestamp")
        
        if lat is None or lon is None or ts is None:
            continue
        
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        
        if not (release_window_start <= ts <= release_window_end):
            continue
        
        if point_in_polygon(lat, lon, source_region_polygon):
            return 100
        
        if source_region_polygon.get("type") == "Polygon":
            coords = source_region_polygon.get("coordinates", [[]])
            if coords and coords[0]:
                ring = coords[0]
                lons = [pt[0] for pt in ring]
                lats = [pt[1] for pt in ring]
                if lons and lats:
                    center_lat = (min(lats) + max(lats)) / 2
                    center_lon = (min(lons) + max(lons)) / 2
                    
                    distance = haversine_distance_km(lat, lon, center_lat, center_lon)
                    closest_approach_km = min(closest_approach_km, distance)
    
    if closest_approach_km == float("inf"):
        return 0
    
    if closest_approach_km <= 5:
        return 75
    elif closest_approach_km <= 10:
        return 50
    elif closest_approach_km <= 15:
        return 25
    


def calculate_association_score(
    candidate_result: CandidateFilterResult,
    vessel_trajectory: list[dict],
    source_region_polygon: dict,
    release_window_start: datetime,
    release_window_end: datetime,
) -> AssociationScoreResult:
    """Calculate association score for a single vessel."""
    if not candidate_result.is_candidate:
        return AssociationScoreResult(
            mmsi=candidate_result.mmsi,
            is_candidate=False,
            temporal_score=0,
            proximity_score=0,
            trajectory_score=0,
            association_score=0,
            rank=None,
        )
    
    temporal_score = calculate_temporal_score(
        vessel_trajectory,
        release_window_start,
        release_window_end,
    )
    
    proximity_score = calculate_proximity_score(candidate_result.minimum_source_distance_km)
    
    trajectory_score = calculate_trajectory_score(
        vessel_trajectory,
        source_region_polygon,
        release_window_start,
        release_window_end,
    )
    
    association_score = int(
        temporal_score * TEMPORAL_WEIGHT +
        proximity_score * PROXIMITY_WEIGHT +
        trajectory_score * TRAJECTORY_WEIGHT
    )
    
    return AssociationScoreResult(
        mmsi=candidate_result.mmsi,
        is_candidate=True,
        temporal_score=temporal_score,
        proximity_score=proximity_score,
        trajectory_score=trajectory_score,
        association_score=association_score,
        rank=None,
    )


def rank_candidates(
    scored_results: list[AssociationScoreResult],
) -> list[AssociationScoreResult]:
    """Rank candidates deterministically by score, distance, MMSI."""
    candidates_only = [r for r in scored_results if r.is_candidate]
    
    sorted_candidates = sorted(
        candidates_only,
        key=lambda r: (-r.association_score, r.mmsi),
    )
    
    ranked = []
    for rank, result in enumerate(sorted_candidates, start=1):
        ranked_result = AssociationScoreResult(
            mmsi=result.mmsi,
            is_candidate=result.is_candidate,
            temporal_score=result.temporal_score,
            proximity_score=result.proximity_score,
            trajectory_score=result.trajectory_score,
            association_score=result.association_score,
            rank=rank,
        )
        ranked.append(ranked_result)
    
    return ranked

    return 0

    
    proximity_score = ((max_distance_km - minimum_distance_km) / max_distance_km) * 100
    return int(proximity_score)
