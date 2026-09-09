"""
Main AIS analysis orchestration for backend vessel correlation.

Coordinates:
1. Load and clean AIS data
2. Filter candidates based on investigation context
3. Calculate association scores
4. Analyze behavioral anomalies
5. Build AISResult contract
"""

from datetime import datetime
from shared.schemas.contracts import (
    AISResult,
    VesselCandidate,
    P3Evidence,
    P3Scores,
    VesselTrajectoryPoint,
)
from .candidate_filter import filter_candidate
from .association_score import (
    calculate_association_score,
    rank_candidates,
)
from .anomaly_analysis import analyze_anomalies


def build_vessel_trajectory_points(
    ais_points: list[dict],
) -> list[VesselTrajectoryPoint]:
    """Convert AIS trajectory points to contract format."""
    trajectory = []
    
    for point in ais_points:
        ts = point.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        
        vtp = VesselTrajectoryPoint(
            timestamp=ts,
            latitude=point.get("latitude"),
            longitude=point.get("longitude"),
            speed_kmh=point.get("speed_kmh"),
            heading=point.get("heading"),
            course_over_ground=point.get("course_over_ground"),
        )
        trajectory.append(vtp)
    
    return trajectory


def build_vessel_candidate(
    mmsi: str,
    rank: int,
    association_score_result,
    anomaly_result,
    vessel_trajectory: list[dict],
    vessel_metadata: dict | None = None,
) -> VesselCandidate:
    """Build VesselCandidate from analysis results."""
    if vessel_metadata is None:
        vessel_metadata = {}
    
    # Find closest point to source
    closest_point = None
    min_distance = float("inf")
    
    for point in vessel_trajectory:
        dist = point.get("distance_to_source_km", float("inf"))
        if dist < min_distance:
            min_distance = dist
            closest_point = point
    
    evidence = P3Evidence(
        distance_to_source_km=min_distance if min_distance != float("inf") else None,
        closest_observation_time=closest_point.get("timestamp") if closest_point else None,
        closest_latitude=closest_point.get("latitude") if closest_point else None,
        closest_longitude=closest_point.get("longitude") if closest_point else None,
        closest_speed_kmh=closest_point.get("speed_kmh") if closest_point else None,
        closest_heading=closest_point.get("heading") if closest_point else None,
        trajectory_points=len(vessel_trajectory),
        aligned_points=len(vessel_trajectory),
        alignment_coverage=1.0 if vessel_trajectory else 0.0,
    )
    
    scores = P3Scores(
        temporal_match_score=float(association_score_result.temporal_score) / 100,
        proximity_score=float(association_score_result.proximity_score) / 100,
        trajectory_score=float(association_score_result.trajectory_score) / 100,
        speed_anomaly_score=float(anomaly_result.speed_deviation_score) / 100,
        course_anomaly_score=float(anomaly_result.course_change_score) / 100,
        ais_gap_anomaly_score=float(anomaly_result.ais_gap_score) / 100,
        behaviour_anomaly_score=float(anomaly_result.anomaly_evidence_score) / 100,
    )
    
    candidate = VesselCandidate(
        rank=rank,
        mmsi=mmsi,
        vessel_name=vessel_metadata.get("vessel_name"),
        vessel_type=vessel_metadata.get("vessel_type"),
        imo=vessel_metadata.get("imo"),
        call_sign=vessel_metadata.get("call_sign"),
        association_score=float(association_score_result.association_score) / 100,
        scores=scores,
        evidence=evidence,
        trajectory=build_vessel_trajectory_points(vessel_trajectory),
    )


def analyze_ais(
    vessel_trajectories: dict[str, list[dict]],
    source_region_polygon: dict,
    release_window_start: datetime,
    release_window_end: datetime,
    vessel_metadata: dict[str, dict] | None = None,
    spill_id: str | None = None,
) -> AISResult:
    """
    Execute complete AIS analysis pipeline.
    
    Args:
        vessel_trajectories: Dict of {mmsi: [trajectory_points]}
        source_region_polygon: GeoJSON Polygon of source region
        release_window_start, release_window_end: Release window (UTC)
        vessel_metadata: Optional dict of {mmsi: metadata_dict}
        spill_id: Optional spill identifier for result
    
    Returns:
        AISResult contract with ranked candidates and evidence
    """
    if vessel_metadata is None:
        vessel_metadata = {}
    
    # Phase 1: Candidate filtering
    candidate_filter_results = {}
    
    for mmsi, trajectory in vessel_trajectories.items():
        result = filter_candidate(
            mmsi=mmsi,
            vessel_trajectory=trajectory,
            source_region_polygon=source_region_polygon,
            release_window_start=release_window_start,
            release_window_end=release_window_end,
        )
        candidate_filter_results[mmsi] = result
    
    # Phase 2: Association scoring
    scored_results = {}
    
    for mmsi, filter_result in candidate_filter_results.items():
        trajectory = vessel_trajectories[mmsi]
        
        score_result = calculate_association_score(
            candidate_result=filter_result,
            vessel_trajectory=trajectory,
            source_region_polygon=source_region_polygon,
            release_window_start=release_window_start,
            release_window_end=release_window_end,
        )
        scored_results[mmsi] = score_result
    
    # Phase 3: Ranking
    scored_list = list(scored_results.values())
    ranked_list = rank_candidates(scored_list)
    
    # Phase 4: Anomaly analysis (for all candidates)
    ranked_candidates_with_anomalies = []
    
    for ranked_result in ranked_list:
        mmsi = ranked_result.mmsi
        trajectory = vessel_trajectories[mmsi]
        
        anomaly_result = analyze_anomalies(
            mmsi=mmsi,
            vessel_trajectory=trajectory,
            release_window_start=release_window_start,
            release_window_end=release_window_end,
        )
        
        candidate = build_vessel_candidate(
            mmsi=mmsi,
            rank=ranked_result.rank or 0,
            association_score_result=ranked_result,
            anomaly_result=anomaly_result,
            vessel_trajectory=trajectory,
            vessel_metadata=vessel_metadata.get(mmsi),
        )
        
        ranked_candidates_with_anomalies.append(candidate)
    
    result = AISResult(
        module="P3_AIS_VESSEL_CORRELATION",
        version="1.0",
        status="prototype" if ranked_candidates_with_anomalies else "no_candidates",
        spill_id=spill_id,
        top_vessels=ranked_candidates_with_anomalies,
    )
    
    return result

    
    return candidate
