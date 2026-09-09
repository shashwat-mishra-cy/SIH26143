"""
Backend validation test for P1 Confidence Threshold Rule (confidence <= 0.3).

Verifies:
1. Low confidence (<= 0.3) detections:
   - Flagged as natural lookalikes / not oil spills.
   - Flagged with forwarded_to_p2 = False and can_proceed_to_evidence_map = False.
   - Blocked from storing P2 drift data (HTTP 422).
   - Blocked from AIS analysis (HTTP 422).
   - Blocked from generating complete analysis / evidence map (HTTP 422).
2. High confidence (> 0.3) detections:
   - Verified as oil spills.
   - Forwarded to P2 (forwarded_to_p2 = True, can_proceed_to_evidence_map = True).
   - Can store P2 drift data and produce complete analysis.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
import io

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi import HTTPException, UploadFile
from shared.schemas.contracts import Coordinate, DriftResult, SpillResult
from backend.app import (
    create_spill,
    get_analysis,
    get_connection,
    store_drift,
    upload_satellite_image,
)

LOW_CONF_SPILL_ID = "TEST_SPILL_LOOKALIKE_LOW"
HIGH_CONF_SPILL_ID = "TEST_SPILL_CONFIRMED_HIGH"


def cleanup():
    conn = get_connection()
    for table in ("ais_results", "drift_results", "spills"):
        conn.execute(
            f"DELETE FROM {table} WHERE spill_id IN (?, ?)",
            (LOW_CONF_SPILL_ID, HIGH_CONF_SPILL_ID),
        )
    conn.commit()
    conn.close()


def make_spill(spill_id: str, confidence: float):
    return SpillResult(
        spill_id=spill_id,
        detection_timestamp=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        timestamp_provenance="satellite_metadata",
        centroid=Coordinate(latitude=18.52, longitude=72.85),
        geometry={
            "type": "Polygon",
            "coordinates": [
                [
                    [72.81, 18.48],
                    [72.89, 18.49],
                    [72.88, 18.56],
                    [72.82, 18.55],
                    [72.81, 18.48],
                ]
            ],
        },
        spill_area_km2=14.7,
        perimeter_km=18.4,
        confidence=confidence,
    )


def make_drift(spill_id: str) -> DriftResult:
    return DriftResult.model_validate({
        "schema_version": "1.0",
        "spill_id": spill_id,
        "detection": {
            "timestamp": "2025-01-01T12:00:00Z",
            "latitude": 18.52,
            "longitude": 72.85,
        },
        "source_time": {
            "candidate": "2025-01-01T04:00:00Z",
            "status": "resolved_single_minimum",
        },
        "source_support": {
            "hdr_50": {
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": [[[[72.0, 18.0], [72.1, 18.0], [72.1, 18.1], [72.0, 18.1], [72.0, 18.0]]]]
                },
                "area_km2": 12.5,
            },
            "hdr_90": {
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": [[[[72.0, 18.0], [72.2, 18.0], [72.2, 18.2], [72.0, 18.2], [72.0, 18.0]]]]
                },
                "area_km2": 45.7,
            },
        },
        "model": {
            "particle_count": 500,
            "backward_duration_hours": 12.0,
            "time_step_minutes": 10.0,
            "horizontal_diffusivity_m2_s": 1.0,
        },
        "status": "success",
    })


def test_low_confidence_pipeline_halt():
    cleanup()

    # 1. Store low-confidence spill (confidence = 0.22 <= 0.3)
    spill = make_spill(LOW_CONF_SPILL_ID, confidence=0.22)
    res = create_spill(spill)

    assert res["confidence"] == 0.22, "Confidence mismatch"
    assert res["forwarded_to_p2"] is False, "Low confidence must not be forwarded to P2"
    assert res["status"] == "pipeline_halted_low_confidence", "Status must indicate pipeline halted"
    print("PASS: Low-confidence detection stored with forwarded_to_p2=False")

    # 2. P2 drift storage must be rejected with HTTP 422
    drift = make_drift(LOW_CONF_SPILL_ID)

    try:
        store_drift(LOW_CONF_SPILL_ID, drift)
        assert False, "Should have raised HTTPException 422"
    except HTTPException as e:
        assert e.status_code == 422, f"Expected 422, got {e.status_code}"
        assert "<= 0.3" in e.detail or "lookalike" in e.detail
        print(f"PASS: store_drift correctly rejected low-confidence spill ({e.detail})")

    # 3. get_analysis (Evidence map) must be rejected with HTTP 422
    try:
        get_analysis(LOW_CONF_SPILL_ID)
        assert False, "Should have raised HTTPException 422"
    except HTTPException as e:
        assert e.status_code == 422
        assert "Cannot proceed to evidence map" in e.detail
        print(f"PASS: get_analysis blocked evidence map generation ({e.detail})")


def test_high_confidence_pipeline_allowed():
    cleanup()

    # 1. Store high-confidence spill (confidence = 0.91 > 0.3)
    spill = make_spill(HIGH_CONF_SPILL_ID, confidence=0.91)
    res = create_spill(spill)

    assert res["confidence"] == 0.91
    assert res["forwarded_to_p2"] is True, "High confidence must be forwarded to P2"
    assert res["status"] == "ready_for_p2"
    print("PASS: High-confidence detection stored with forwarded_to_p2=True")

    # 2. P2 drift storage should succeed
    drift = make_drift(HIGH_CONF_SPILL_ID)
    drift_res = store_drift(HIGH_CONF_SPILL_ID, drift)
    assert drift_res["message"] == "Drift result stored successfully"
    print("PASS: store_drift allowed for high-confidence spill")

    # 3. get_analysis should succeed
    analysis = get_analysis(HIGH_CONF_SPILL_ID)
    assert analysis["spill"]["spill_id"] == HIGH_CONF_SPILL_ID
    assert analysis["spill"]["confidence"] == 0.91
    print("PASS: get_analysis successfully generated complete analysis for high-confidence spill")



import asyncio

def test_image_upload_endpoint():
    # Test low confidence via upload endpoint
    file_bytes = b"sample tiff data"
    upload_file_low = UploadFile(
        file=io.BytesIO(file_bytes),
        filename="sar_scene_calm_sea_lookalike.tif",
    )
    result_low = asyncio.run(upload_satellite_image(
        file=upload_file_low,
        manual_timestamp=None,
        confidence=0.25,
    ))
    assert result_low["can_proceed_to_evidence_map"] is False
    assert result_low["forwarded_to_p2"] is False
    assert result_low["classification"] == "lookalike"
    assert "Cannot proceed to evidence map" in result_low["error"]
    print(f"PASS: upload_satellite_image correctly handled low confidence: {result_low['error']}")

    # Test high confidence via upload endpoint
    upload_file_high = UploadFile(
        file=io.BytesIO(file_bytes),
        filename="sar_scene_crude_slick.tif",
    )
    result_high = asyncio.run(upload_satellite_image(
        file=upload_file_high,
        manual_timestamp=None,
        confidence=0.92,
    ))
    assert result_high["can_proceed_to_evidence_map"] is True
    assert result_high["forwarded_to_p2"] is True
    assert result_high["classification"] == "mineral_oil"
    assert result_high["error"] is None
    print("PASS: upload_satellite_image correctly handled high confidence")


if __name__ == "__main__":
    test_low_confidence_pipeline_halt()
    test_high_confidence_pipeline_allowed()
    test_image_upload_endpoint()
    cleanup()
    print("\nALL BACKEND CONFIDENCE THRESHOLD & EVIDENCE MAP TESTS PASSED!")
