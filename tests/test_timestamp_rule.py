"""
Backend tests for the P1 timestamp rule.

Covers:
- spill stored without a timestamp -> "unavailable" (never generated)
- user-supplied timestamp -> stored with provenance "user"
- naive inputs treated as UTC
- invalid timestamps rejected by pydantic validation

No external test dependencies required.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from datetime import datetime, timezone

from pydantic import ValidationError

from shared.schemas.contracts import SpillResult
from backend.app import (
    TimestampUpdate,
    create_spill,
    get_analysis,
    get_connection,
    set_spill_timestamp,
)

SPILL_ID = "TEST_TIMESTAMP_RULE"


def cleanup():
    conn = get_connection()
    for table in ("ais_results", "drift_results", "spills"):
        conn.execute(
            f"DELETE FROM {table} WHERE spill_id = ?",
            (SPILL_ID,),
        )
    conn.commit()
    conn.close()


def make_spill():
    return SpillResult(
        spill_id=SPILL_ID,
        detection_timestamp=None,
        timestamp_provenance="unavailable",
        centroid={"latitude": 20.0, "longitude": 72.0},
        geometry={
            "type": "Polygon",
            "coordinates": [
                [
                    [72.0, 20.0],
                    [72.1, 20.0],
                    [72.1, 20.1],
                    [72.0, 20.1],
                    [72.0, 20.0],
                ]
            ],
        },
        spill_area_km2=1.5,
        confidence=0.9,
    )


def parse_utc(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
        timezone.utc
    )


def main():
    cleanup()

    # 1. Store a spill WITHOUT any timestamp.
    create_spill(make_spill())

    analysis = get_analysis(SPILL_ID)
    assert analysis["spill"]["detection_timestamp"] is None, analysis
    assert analysis["spill"]["timestamp_provenance"] == "unavailable", analysis
    print("PASS: spill stored without a timestamp -> unavailable")

    # 2. User supplies a timestamp -> stored with provenance "user".
    set_spill_timestamp(
        SPILL_ID,
        TimestampUpdate(detection_timestamp="2025-01-01T10:30:00Z"),
    )

    analysis = get_analysis(SPILL_ID)
    stored = analysis["spill"]["detection_timestamp"]
    assert stored is not None, analysis
    assert parse_utc(stored) == datetime(
        2025, 1, 1, 10, 30, tzinfo=timezone.utc
    ), stored
    assert analysis["spill"]["timestamp_provenance"] == "user", analysis
    print(f"PASS: user timestamp stored with provenance 'user': {stored}")

    # 3. Naive timestamp input is treated as UTC.
    set_spill_timestamp(
        SPILL_ID,
        TimestampUpdate(detection_timestamp="2025-01-02T08:00:00"),
    )
    analysis = get_analysis(SPILL_ID)
    assert parse_utc(analysis["spill"]["detection_timestamp"]) == datetime(
        2025, 1, 2, 8, 0, tzinfo=timezone.utc
    ), analysis["spill"]["detection_timestamp"]
    print("PASS: naive timestamp treated as UTC")

    # 4. Invalid timestamps rejected by pydantic validation.
    try:
        TimestampUpdate(detection_timestamp="not-a-timestamp")
    except ValidationError:
        print("PASS: invalid timestamp rejected")
    else:
        raise AssertionError("invalid timestamp should be rejected")

    # 5. No timestamp supplied -> nothing generated.
    create_spill(make_spill())
    analysis = get_analysis(SPILL_ID)
    assert analysis["spill"]["detection_timestamp"] is None, analysis
    assert analysis["spill"]["timestamp_provenance"] == "unavailable", analysis
    print("PASS: no timestamp is ever generated when none is supplied")

    print("\nALL TIMESTAMP RULE TESTS PASSED")

    cleanup()


if __name__ == "__main__":
    main()