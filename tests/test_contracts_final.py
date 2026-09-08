"""
Validation tests for the finalized shared P1/P2/P3 contracts.

Verifies actual upstream output shapes validate against the Pydantic
models in shared/schemas/contracts.py:

- P2 indeterminate example (nullable candidate, MultiPolygon HDR,
  preserved source_time status, no forced legacy fields)
- P3 single-vessel example (actual P3 field names: speed_kmh,
  course_over_ground, data_quality, top_vessels, no spill_id)
- P3 no_candidates example (empty top_vessels, status no_candidates)
- P1 result with detection_timestamp None and provenance unavailable
- legacy P3 draft payload (vessels,) validates and syncs to top_vessels
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shared.schemas.contracts import (
    AISResult,
    DriftResult,
    SpillResult,
)


def main():
    # 1. P2 indeterminate example -- the supplied upstream shape.
    p2_indeterminate = {
        "schema_version": "1.0",
        "spill_id": "SP001",
        "detection": {
            "timestamp": "2025-01-01T10:30:00Z",
            "latitude": 20.0,
            "longitude": 72.0,
        },
        "source_time": {
            "candidate": None,
            "status": "indeterminate_conflicting_minima",
        },
        "source_support": {
            "hdr_50": {
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": [
                        [
                            [
                                [72.0,  20.0],
                                [72.1,  20.0],
                                [72.1,  20.1],
                                [72.0,  20.1],
                                [72.0,  20.0],
                            ]
                        ]
                    ],
                },
                "area_km2": 12.5,
            },
            "hdr_90": {
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": [
                        [
                            [
                                [72.0,  19.9],
                                [72.2,  19.9],
                                [72.2,20.2],
                                [72.0,20.2],
                                [72.0,19.9],
                            ]
                        ]
                    ],
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
    }

    drift = DriftResult.model_validate(p2_indeterminate)

    assert drift.source_time.candidate is None
    assert drift.source_time.status == "indeterminate_conflicting_minima"
    assert drift.source_support.hdr_50.area_km2 == 12.5
    assert drift.source_support.hdr_90.geometry["type"] == "MultiPolygon"
    assert drift.model.time_step_minutes == 10.0
    assert drift.status == "success"
    assert drift.schema_version == "1.0"
    assert drift.source_origin is None
    assert drift.oil_trajectory == []
    print("PASS 1: P2 indeterminate example validates")

    # 2. P3 example with one vessel.
    p3_one_vessel = {
        "module": "P3_AIS_VESSEL_CORRELATION",
        "version": "1.0",
        "status": "prototype",
        "description": "Vessel correlation prototype output",
        "attribution_note": "Association does not establish legal responsibility",
        "top_vessels": [
            {
                "rank": 1,
                "mmsi": "123456789",
                "vessel_name": "TEST TANKER",
                "vessel_type": 70,
                "imo": "9312345",
                "call_sign": "TCST7",
                "association_score": 0.87,
                "scores": {
                    "spatial": 0.9,
                    "temporal": 0.8,
                    "trajectory": 0.75,
                    "behaviour": 0.6,
                    "data_quality": 0.95,
                },
                "evidence": {
                    "distance_to_source_km": 3.2,
                    "closest_observation_time": "2024-12-31T22:15:00Z",
                    "closest_latitude": 19.98,
                    "closest_longitude": 71.99,
                    "closest_speed_kmh": 14.2,
                    "closest_heading": 245.0,
                    "behaviour_anomaly_records": ["speed_drop_before_release"],
                    "data_quality_anomaly_records": [],
                    "trajectory_points": 42,
                    "aligned_points":  38,
                    "alignment_coverage": 0.9,
                    "mean_oil_distance_km": 2.1,
                    "mean_oil_time_difference_seconds": -180,
                },
                "trajectory": [
                    {
                        "timestamp": "2024-12-31T22:05:00Z",
                        "latitude": 19.95,
                        "longitude": 71.95,
                        "speed_kmh": 14.0,
                        "heading": 247.0,
                        "course_over_ground": 250.0,
                    }
                ],
            }
        ],
    }

    ais_one = AISResult.model_validate(p3_one_vessel)

    assert ais_one.module == "P3_AIS_VESSEL_CORRELATION"
    assert ais_one.status == "prototype"
    assert ais_one.spill_id is None
    assert len(ais_one.top_vessels) == 1
    vessel = ais_one.top_vessels[0]
    assert vessel.vessel_type == 70
    assert vessel.imo == "9312345"
    assert vessel.scores.data_quality == 0.95
    assert vessel.evidence.closest_speed_kmh == 14.2
    assert vessel.evidence.alignment_coverage == 0.9
    assert vessel.evidence.mean_oil_time_difference_seconds == -180
    assert vessel.trajectory[0].speed_kmh == 14.0
    assert vessel.trajectory[0].course_over_ground ==  250.0
    assert ais_one.vessels == ais_one.top_vessels
    print("PASS 2: P3 single-vessel example validates")

    # 3. P3 no_candidates example.
    p3_no_candidates = {
        "module": "P3_AIS_VESSEL_CORRELATION",
        "version": "1.0",
        "status": "no_candidates",
        "description": "No vessels found near the estimated source window",
        "attribution_note": None,
        "top_vessels": [],
    }

    ais_empty = AISResult.model_validate(p3_no_candidates)

    assert ais_empty.status == "no_candidates"
    assert ais_empty.top_vessels == []
    assert ais_empty.vessels == []
    print("PASS 3: P3 no_candidates example validates")

    # 4. P1 result with NO detection timestamp -- provenance unavailable.
    p1_no_timestamp = SpillResult(
        spill_id="SP001",
        detection_timestamp=None,
        timestamp_provenance="unavailable",
        centroid={"latitude": 20.0, "longitude": 72.0},
        geometry={
            "type": "Polygon",
            "coordinates": [
                [
                    [72.0,  20.0],
                    [72.1,  20.0],
                    [72.1,  20.1],
                    [72.0,  20.1],
                    [72.0,  20.0],
                ]
            ],
        },
        spill_area_km2=1.5,
        confidence=0.9,
    )

    assert p1_no_timestamp.detection_timestamp is None
    assert p1_no_timestamp.timestamp_provenance == "unavailable"
    print("PASS 4: P1 timestamp-unavailable result validates")

    # 5. Backward compat -- legacy P3 draft payload (vessels,).
    legacy_p3 = {
        "spill_id": "SP001",
        "vessels": [
            {
                "rank": 1,
                "mmsi": "111222333",
                "vessel_name": "LEGACY VESSEL",
                "association_score": 0.5,
                "scores": {"spatial": 0.6, "temporal":  0.5},
                "evidence": {"distance_to_source_km":  4.0},
                "trajectory": [
                    {
                        "timestamp": "2024-12-31T20:00:00Z",
                        "latitude": 19.5,
                        "longitude": 71.5,
                        "speed_kmh":  12.0,
                    }
                ],
            }
        ],
    }

    legacy_ais = AISResult.model_validate(legacy_p3)

    assert legacy_ais.spill_id == "SP001"
    assert legacy_ais.top_vessels == legacy_ais.vessels
    assert legacy_ais.top_vessels[0].mmsi == "111222333"
    assert legacy_ais.top_vessels[0].trajectory[0].speed_kmh == 12.0
    print("PASS 5: legacy P3 draft payload validates and syncs to top_vessels")

    print("\nALL CONTRACT VALIDATION TESTS PASSED")


if __name__ == "__main__":
    main()