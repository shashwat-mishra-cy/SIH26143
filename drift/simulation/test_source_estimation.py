"""Unit test suite for model-supported source-time estimation layer.

Validates clear interior minima, flat signal detection, boundary minima constraints,
conflicting minima handling, insufficient data handling, and irregular timestamp windowing.
"""

from pathlib import Path
import sys

project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from drift.simulation.source_estimation import estimate_source_time


def _make_diag(timestamp: str, a50: float, a90: float) -> dict:
    return {
        "timestamp": timestamp,
        "status": "success",
        "hdr_50_area_m2": a50,
        "hdr_90_area_m2": a90,
    }


def test_clear_interior_minimum() -> None:
    diags = [
        _make_diag("2025-01-01T08:00:00Z", 8000000.0, 18000000.0),
        _make_diag("2025-01-01T08:15:00Z", 6000000.0, 14000000.0),
        _make_diag("2025-01-01T08:30:00Z", 4000000.0, 10000000.0),
        _make_diag("2025-01-01T08:45:00Z", 6500000.0, 15000000.0),
        _make_diag("2025-01-01T09:00:00Z", 8500000.0, 19000000.0),
    ]
    res = estimate_source_time(diags)
    assert res["status"] == "candidate_identified"
    assert res["candidate_source_time"] == "2025-01-01T08:30:00Z"
    assert res["source_time_window_start"] == "2025-01-01T08:15:00Z"
    assert res["source_time_window_end"] == "2025-01-01T08:45:00Z"
    assert res["minimum_50pct_hdr_area_m2"] == 4000000.0
    assert res["minimum_90pct_hdr_area_m2"] == 10000000.0


def test_flat_signal() -> None:
    diags = [
        _make_diag("2025-01-01T08:00:00Z", 5000000.0, 12000000.0),
        _make_diag("2025-01-01T08:15:00Z", 5050000.0, 12100000.0),
        _make_diag("2025-01-01T08:30:00Z", 4980000.0, 11950000.0),
        _make_diag("2025-01-01T08:45:00Z", 5020000.0, 12050000.0),
        _make_diag("2025-01-01T09:00:00Z", 5010000.0, 12020000.0),
    ]
    res = estimate_source_time(diags)
    assert res["status"] == "indeterminate_flat_signal"
    assert res["candidate_source_time"] is None


def test_boundary_minimum() -> None:
    diags = [
        _make_diag("2025-01-01T08:00:00Z", 3000000.0, 8000000.0),
        _make_diag("2025-01-01T08:15:00Z", 4500000.0, 11000000.0),
        _make_diag("2025-01-01T08:30:00Z", 6000000.0, 14000000.0),
        _make_diag("2025-01-01T08:45:00Z", 7500000.0, 17000000.0),
    ]
    res = estimate_source_time(diags)
    assert res["status"] == "indeterminate_boundary_minimum"
    assert res["candidate_source_time"] is None


def test_conflicting_minima() -> None:
    diags = [
        _make_diag("2025-01-01T08:00:00Z", 6000000.0, 18000000.0),
        _make_diag("2025-01-01T08:15:00Z", 3000000.0, 17000000.0),
        _make_diag("2025-01-01T08:30:00Z", 5000000.0, 16000000.0),
        _make_diag("2025-01-01T08:45:00Z", 7000000.0, 15000000.0),
        _make_diag("2025-01-01T09:00:00Z", 8000000.0, 10000000.0),
        _make_diag("2025-01-01T09:15:00Z", 9000000.0, 14000000.0),
    ]
    res = estimate_source_time(diags)
    assert "indeterminate" in res["status"]
    assert res["candidate_source_time"] is None


def test_insufficient_timestamps() -> None:
    diags = [
        _make_diag("2025-01-01T08:00:00Z", 5000000.0, 12000000.0),
        _make_diag("2025-01-01T08:15:00Z", 4000000.0, 10000000.0),
    ]
    res = estimate_source_time(diags)
    assert res["status"] == "insufficient_temporal_data"
    assert res["candidate_source_time"] is None


def test_irregular_timestamp_spacing() -> None:
    diags = [
        _make_diag("2025-01-01T08:00:00Z", 7000000.0, 16000000.0),
        _make_diag("2025-01-01T08:10:00Z", 5000000.0, 12000000.0),
        _make_diag("2025-01-01T08:35:00Z", 3500000.0, 9000000.0),
        _make_diag("2025-01-01T09:15:00Z", 5500000.0, 13000000.0),
        _make_diag("2025-01-01T10:30:00Z", 8000000.0, 18000000.0),
    ]
    res = estimate_source_time(diags)
    assert res["status"] == "candidate_identified"
    assert res["candidate_source_time"] == "2025-01-01T08:35:00Z"
    assert res["source_time_window_start"] == "2025-01-01T08:10:00Z"
    assert res["source_time_window_end"] == "2025-01-01T09:15:00Z"


def main() -> None:
    print("=======================================================================")
    print("RUNNING SOURCE ESTIMATION LAYER TESTS")
    print("=======================================================================")

    test_clear_interior_minimum()
    print("TEST 1 (Clear Interior Minimum):       PASSED")

    test_flat_signal()
    print("TEST 2 (Flat Signal):                  PASSED")

    test_boundary_minimum()
    print("TEST 3 (Boundary Minimum):             PASSED")

    test_conflicting_minima()
    print("TEST 4 (Conflicting Minima):           PASSED")

    test_insufficient_timestamps()
    print("TEST 5 (Insufficient Timestamps):      PASSED")

    test_irregular_timestamp_spacing()
    print("TEST 6 (Irregular Timestamp Spacing):   PASSED")

    print("=======================================================================")
    print("ALL SOURCE ESTIMATION TESTS PASSED SUCCESSFULLY")
    print("=======================================================================\n")


if __name__ == "__main__":
    main()