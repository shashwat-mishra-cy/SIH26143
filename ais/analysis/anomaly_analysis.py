"""
Behavioral and anomaly analysis for AIS vessel correlation.

Detects behavioral indicators based on available AIS data:
- Speed deviation from vessel mean
- Course changes (angular deviation)
- AIS data gaps (missing observations)
- Trajectory consistency

Configuration (prototype weights):
- Speed weight: 0.25
- Course weight: 0.25
- AIS gap weight: 0.25
- Trajectory weight: 0.25
"""

from datetime import datetime
from typing import NamedTuple
from .geometry import circular_course_difference, haversine_distance_km


class AnomalyIndicator(NamedTuple):
    """Single anomaly indicator."""
    indicator_type: str
    severity: float
    details: dict


class AnomalyAnalysisResult(NamedTuple):
    """Behavioral/anomaly analysis for one vessel."""
    mmsi: str
    speed_deviation_score: int
    course_change_score: int
    ais_gap_score: int
    trajectory_consistency_score: int
    anomaly_evidence_score: int
    anomaly_indicators: list[AnomalyIndicator]


SPEED_WEIGHT = 0.25
COURSE_WEIGHT = 0.25
AIS_GAP_WEIGHT = 0.25
CONSISTENCY_WEIGHT = 0.25


def calculate_speed_statistics(vessel_trajectory: list[dict]) -> dict:
    """Calculate speed mean, stddev, and extremes."""
    speeds = []
    
    for point in vessel_trajectory:
        speed = point.get("speed_kmh")
        if speed is not None and speed >= 0:
            speeds.append(speed)
    
    if not speeds:
        return {"count": 0, "mean": 0, "max": 0, "min": 0}
    
    mean_speed = sum(speeds) / len(speeds)
    
    return {
        "count": len(speeds),
        "mean": mean_speed,
        "max": max(speeds),
        "min": min(speeds),
    }


def calculate_speed_deviation_score(
    vessel_trajectory: list[dict],
    release_window_start: datetime,
    release_window_end: datetime,
) -> tuple[int, list[AnomalyIndicator]]:
    """Calculate speed deviation score (0-100)."""
    stats = calculate_speed_statistics(vessel_trajectory)
    
    if stats["count"] < 2:
        return (0, [])
    
    mean_speed = stats["mean"]
    indicators = []
    
    if mean_speed == 0:
        return (0, [])
    
    deviation_count = 0
    
    for point in vessel_trajectory:
        ts = point.get("timestamp")
        speed = point.get("speed_kmh")
        
        if speed is None or ts is None:
            continue
        
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        
        if not (release_window_start <= ts <= release_window_end):
            continue
        
        deviation_percent = abs(speed - mean_speed) / mean_speed
        
        if deviation_percent > 0.5:
            deviation_count += 1
            if speed > mean_speed * 1.5 and len(indicators) < 5:
                indicators.append(AnomalyIndicator(
                    indicator_type="speed",
                    severity=min((speed - mean_speed) / (mean_speed * 2), 1.0),
                    details={
                        "timestamp": ts.isoformat(),
                        "speed_kmh": speed,
                        "mean_speed_kmh": mean_speed,
                    },
                ))
    
    if deviation_count == 0:
        return (0, [])


def calculate_course_change_score(
    vessel_trajectory: list[dict],
    release_window_start: datetime,
    release_window_end: datetime,
) -> tuple[int, list[AnomalyIndicator]]:
    """Calculate course change score (0-100)."""
    points_in_window = []
    
    for point in vessel_trajectory:
        ts = point.get("timestamp")
        cog = point.get("course_over_ground")
        
        if ts is None or cog is None:
            continue
        
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        
        if release_window_start <= ts <= release_window_end:
            points_in_window.append((ts, cog))
    
    if len(points_in_window) < 2:
        return (0, [])
    
    points_in_window.sort(key=lambda x: x[0])
    
    large_changes = 0
    indicators = []
    
    for i in range(1, len(points_in_window)):
        prev_ts, prev_cog = points_in_window[i - 1]
        curr_ts, curr_cog = points_in_window[i]
        
        angle_diff = circular_course_difference(prev_cog, curr_cog)
        
        if angle_diff > 30 and len(indicators) < 5:
            large_changes += 1
            indicators.append(AnomalyIndicator(
                indicator_type="course",
                severity=min(angle_diff / 180, 1.0),
                details={"timestamp": curr_ts.isoformat(), "angle_change": angle_diff},
            ))
    
    if large_changes == 0:
        return (0, [])
    


def calculate_ais_gap_score(
    vessel_trajectory: list[dict],
    release_window_start: datetime,
    release_window_end: datetime,
) -> tuple[int, list[AnomalyIndicator]]:
    """Calculate AIS data gap score (0-100)."""
    points_in_window = []
    
    for point in vessel_trajectory:
        ts = point.get("timestamp")
        if ts is None:
            continue
        
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        
        if release_window_start <= ts <= release_window_end:
            points_in_window.append(ts)
    
    if len(points_in_window) < 2:
        return (0, [])
    
    points_in_window.sort()
    gaps = []
    indicators = []
    
    for i in range(1, len(points_in_window)):
        gap_seconds = (points_in_window[i] - points_in_window[i - 1]).total_seconds()
        gaps.append(gap_seconds)
        
        if gap_seconds > 3600 and len(indicators) < 5:
            indicators.append(AnomalyIndicator(
                indicator_type="gap",
                severity=min(gap_seconds / 10800, 1.0),
                details={
                    "gap_start": points_in_window[i - 1].isoformat(),
                    "gap_end": points_in_window[i].isoformat(),
                    "gap_seconds": gap_seconds,
                },
            ))
    
    if not gaps:
        return (0, [])
    
    mean_gap = sum(gaps) / len(gaps)
    large_gaps = sum(1 for g in gaps if g > mean_gap * 2)
    
    if large_gaps == 0:
        return (0, [])
    
    gap_ratio = large_gaps / len(gaps)
    score = int(gap_ratio * 100)
    
    return (score, indicators)


def calculate_trajectory_consistency_score(
    vessel_trajectory: list[dict],
    release_window_start: datetime,
    release_window_end: datetime,
) -> tuple[int, list[AnomalyIndicator]]:
    """Calculate trajectory consistency score (0-100)."""
    points_in_window = []
    
    for point in vessel_trajectory:
        ts = point.get("timestamp")
        lat = point.get("latitude")
        lon = point.get("longitude")
        
        if ts is None or lat is None or lon is None:
            continue
        
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        
        if release_window_start <= ts <= release_window_end:
            points_in_window.append((ts, lat, lon))
    
    if len(points_in_window) < 3:
        return (0, [])
    
    points_in_window.sort(key=lambda x: x[0])
    indicators = []
    inconsistencies = 0
    
    for i in range(1, len(points_in_window) - 1):
        prev_ts, prev_lat, prev_lon = points_in_window[i - 1]
        curr_ts, curr_lat, curr_lon = points_in_window[i]
        next_ts, next_lat, next_lon = points_in_window[i + 1]
        
        prev_dist = haversine_distance_km(prev_lat, prev_lon, curr_lat, curr_lon)
        next_dist = haversine_distance_km(curr_lat, curr_lon, next_lat, next_lon)
        
        prev_time_s = (curr_ts - prev_ts).total_seconds()
        next_time_s = (next_ts - curr_ts).total_seconds()
        
        if prev_time_s > 0 and next_time_s > 0:
            prev_speed = (prev_dist / prev_time_s) * 3600
            next_speed = (next_dist / next_time_s) * 3600
            speed_diff = abs(prev_speed - next_speed)
            
            if speed_diff > 20 and len(indicators) < 5:
                inconsistencies += 1
                indicators.append(AnomalyIndicator(
                    indicator_type="consistency",
                    severity=min(speed_diff / 50, 1.0),
                    details={"timestamp": curr_ts.isoformat(), "speed_change": speed_diff},
                ))
    
    if inconsistencies == 0:
        return (0, [])
    
    consistency_ratio = inconsistencies / max(len(points_in_window) - 2, 1)
    score = int(consistency_ratio * 100)
    
    return (score, indicators)


def analyze_anomalies(
    mmsi: str,
    vessel_trajectory: list[dict],
    release_window_start: datetime,
    release_window_end: datetime,
) -> AnomalyAnalysisResult:
    """Perform complete behavioral/anomaly analysis for a vessel."""
    speed_score, speed_indicators = calculate_speed_deviation_score(
        vessel_trajectory,
        release_window_start,
        release_window_end,
    )
    
    course_score, course_indicators = calculate_course_change_score(
        vessel_trajectory,
        release_window_start,
        release_window_end,
    )
    
    gap_score, gap_indicators = calculate_ais_gap_score(
        vessel_trajectory,
        release_window_start,
        release_window_end,
    )
    
    consistency_score, consistency_indicators = calculate_trajectory_consistency_score(
        vessel_trajectory,
        release_window_start,
        release_window_end,
    )
    
    anomaly_evidence_score = int(
        speed_score * SPEED_WEIGHT +
        course_score * COURSE_WEIGHT +
        gap_score * AIS_GAP_WEIGHT +
        consistency_score * CONSISTENCY_WEIGHT
    )
    
    all_indicators = (
        speed_indicators +
        course_indicators +
        gap_indicators +
        consistency_indicators
    )
    
    return AnomalyAnalysisResult(
        mmsi=mmsi,
        speed_deviation_score=speed_score,
        course_change_score=course_score,
        ais_gap_score=gap_score,
        trajectory_consistency_score=consistency_score,
        anomaly_evidence_score=anomaly_evidence_score,
        anomaly_indicators=all_indicators,
    )


    change_ratio = large_changes / (len(points_in_window) - 1)
    score = int(change_ratio * 100)
    
    return (score, indicators)

    
    deviation_ratio = deviation_count / stats["count"]
    score = int(deviation_ratio * 100)
    
    return (score, indicators)
