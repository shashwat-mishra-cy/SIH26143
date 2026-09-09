"""
Unit tests for AIS analysis pipeline.

Tests individual components:
- Geometry (Haversine distance, circular course difference, point-in-polygon)
- Candidate filtering (temporal, spatial, trajectory criteria)
- Association scoring (temporal, proximity, trajectory scores)
- Anomaly analysis (speed, course, gaps, consistency)
"""

import pytest
from datetime import datetime, timezone
from ais.analysis.geometry import (
    haversine_distance_km,
    circular_course_difference,
    point_in_polygon,
    polygon_bounds,
)
from ais.analysis.candidate_filter import (
    has_temporal_overlap,
    minimum_distance_to_source,
    is_within_proximity_threshold,
    filter_candidate,
)
from ais.analysis.association_score import (
    calculate_temporal_score,
    calculate_proximity_score,
    calculate_trajectory_score,
)
from ais.analysis.anomaly_analysis import (
    calculate_speed_statistics,
    analyze_anomalies,
)


@pytest.fixture
def source_polygon():
    """Simple rectangular source region."""
    return {
        "type": "Polygon",
        "coordinates": [[
            [72.5, 18.4],
            [72.9, 18.4],
            [72.9, 18.5],
            [72.5, 18.5],
            [72.5, 18.4],
        ]],
    }


@pytest.fixture
def release_window():
    """Release window: 2025-01-01 10:00 - 14:00 UTC."""
    start = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    end = datetime(2025, 1, 1, 14, 0, 0, tzinfo=timezone.utc)
    return start, end


@pytest.fixture
def vessel_trajectory_candidate():
    """Vessel trajectory overlapping release window and source region."""
    return [
        {
            "timestamp": datetime(2025, 1, 1, 9, 0, 0, tzinfo=timezone.utc),
            "latitude": 18.3,
            "longitude": 72.4,
            "speed_kmh": 10.0,
            "course_over_ground": 45.0,
            "heading": 45.0,
        },
        {
            "timestamp": datetime(2025, 1, 1, 11, 0, 0, tzinfo=timezone.utc),
            "latitude": 18.45,
            "longitude": 72.7,
            "speed_kmh": 12.0,
            "course_over_ground": 50.0,
            "heading": 50.0,
        },
        {
            "timestamp": datetime(2025, 1, 1, 13, 0, 0, tzinfo=timezone.utc),
            "latitude": 18.5,
            "longitude": 72.8,
            "speed_kmh": 11.0,
            "course_over_ground": 55.0,
            "heading": 55.0,
        },
    ]


@pytest.fixture
def vessel_trajectory_non_candidate():
    """Vessel trajectory not overlapping release window or source region."""
    return [
        {
            "timestamp": datetime(2025, 1, 1, 6, 0, 0, tzinfo=timezone.utc),
            "latitude": 19.0,
            "longitude": 73.5,
            "speed_kmh": 10.0,
            "course_over_ground": 45.0,
        },
        {
            "timestamp": datetime(2025, 1, 1, 7, 0, 0, tzinfo=timezone.utc),
            "latitude": 19.1,
            "longitude": 73.6,
            "speed_kmh": 10.0,
            "course_over_ground": 45.0,
        },
    ]


def test_haversine_distance_same_point():
    """Distance from a point to itself should be 0."""
    dist = haversine_distance_km(18.45, 72.7, 18.45, 72.7)
    assert dist < 0.001


def test_haversine_distance_approximate():
    """Test Haversine distance calculation (Delhi to Mumbai ~1450 km)."""
    dist = haversine_distance_km(28.6, 77.2, 19.1, 72.9)
    assert 1400 < dist < 1500


def test_circular_course_difference_same():
    """Course difference from a course to itself should be 0."""
    diff = circular_course_difference(45.0, 45.0)
    assert diff == 0


def test_circular_course_difference_opposite():
    """Course difference of 180 degrees."""
    diff = circular_course_difference(0.0, 180.0)
    assert diff == 180


def test_circular_course_difference_wrap():
    """Test wrap-around (359 to 1 should be 2)."""
    diff = circular_course_difference(359.0, 1.0)
    assert diff == 2


def test_point_in_polygon_inside():
    """Point inside polygon should return True."""
    polygon = {
        "type": "Polygon",
        "coordinates": [[
            [0, 0], [10, 0], [10, 10], [0, 10], [0, 0],
        ]],
    }
    assert point_in_polygon(5.0, 5.0, polygon) is True


def test_point_in_polygon_outside():
    """Point outside polygon should return False."""
    polygon = {
        "type": "Polygon",
        "coordinates": [[
            [0, 0], [10, 0], [10, 10], [0, 10], [0, 0],
        ]],
    }
    assert point_in_polygon(15.0, 15.0, polygon) is False


def test_temporal_overlap_yes(vessel_trajectory_candidate, release_window):
    """Vessel with points in release window."""
    start, end = release_window
    overlap = has_temporal_overlap(vessel_trajectory_candidate, start, end)
    assert overlap is True


def test_temporal_overlap_no(vessel_trajectory_non_candidate, release_window):
    """Vessel with no points in release window."""
    start, end = release_window
    overlap = has_temporal_overlap(vessel_trajectory_non_candidate, start, end)
    assert overlap is False


def test_minimum_distance_to_source(vessel_trajectory_candidate):
    """Calculate minimum distance to source center."""
    dist = minimum_distance_to_source(
        vessel_trajectory_candidate,
        18.45,
        72.7,
    )
    assert dist >= 0
    assert dist < 1


def test_proximity_within_threshold():
    """Distance within threshold."""
    assert is_within_proximity_threshold(10.0, 15.0) is True


def test_proximity_outside_threshold():
    """Distance outside threshold."""
    assert is_within_proximity_threshold(20.0, 15.0) is False


def test_filter_candidate_yes(
    vessel_trajectory_candidate,
    source_polygon,
    release_window,
):
    """Vessel should be classified as candidate."""
    start, end = release_window
    result = filter_candidate(
        mmsi="123456789",
        vessel_trajectory=vessel_trajectory_candidate,
        source_region_polygon=source_polygon,
        release_window_start=start,
        release_window_end=end,
    )
    assert result.is_candidate is True


def test_filter_candidate_no(
    vessel_trajectory_non_candidate,
    source_polygon,
    release_window,
):
    """Vessel should not be classified as candidate."""
    start, end = release_window
    result = filter_candidate(
        mmsi="987654321",
        vessel_trajectory=vessel_trajectory_non_candidate,
        source_region_polygon=source_polygon,
        release_window_start=start,
        release_window_end=end,
    )
    assert result.is_candidate is False


def test_temporal_score_with_coverage(vessel_trajectory_candidate, release_window):
    """Temporal score when trajectory covers release window."""
    start, end = release_window
    score = calculate_temporal_score(vessel_trajectory_candidate, start, end)
    assert 0 <= score <= 100
    assert score > 0


def test_proximity_score_close():
    """Proximity score for close distance."""
    score = calculate_proximity_score(5.0, 15.0)
    assert score > 50


def test_proximity_score_far():
    """Proximity score for far distance."""
    score = calculate_proximity_score(20.0, 15.0)
    assert score == 0


def test_speed_statistics(vessel_trajectory_candidate):
    """Calculate speed statistics."""
    stats = calculate_speed_statistics(vessel_trajectory_candidate)
    assert stats["count"] == 3
    assert stats["mean"] > 0
    assert stats["max"] >= stats["mean"]
    assert stats["min"] <= stats["mean"]


def test_analyze_anomalies(vessel_trajectory_candidate, release_window):
    """Complete anomaly analysis."""
    start, end = release_window
    result = analyze_anomalies(
        mmsi="123456789",
        vessel_trajectory=vessel_trajectory_candidate,
        release_window_start=start,
        release_window_end=end,
    )
    assert result.mmsi == "123456789"
    assert 0 <= result.anomaly_evidence_score <= 100
    assert isinstance(result.anomaly_indicators, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



def test_polygon_bounds(source_polygon):
    """Extract bounds from polygon."""
    bounds = polygon_bounds(source_polygon)
    assert bounds is not None
    assert bounds["minLatitude"] == 18.4
    assert bounds["maxLatitude"] == 18.5
