"""Unit tests for P2 to P3 Handoff Contract (drift/simulation/handoff.py)."""

import json
import unittest
from shapely.geometry import MultiPolygon, Polygon

from drift.simulation.handoff import (
    DetectionInfo,
    DriftSourceResult,
    HDRSupportInfo,
    ModelMetadataInfo,
    SourceSupportInfo,
    SourceTimeInfo,
    create_drift_source_result,
    geometry_to_geojson,
)


class TestDriftHandoffContract(unittest.TestCase):

    def setUp(self):
        self.poly1 = Polygon([(72.0, 18.0), (72.5, 18.0), (72.5, 18.5), (72.0, 18.5), (72.0, 18.0)])
        self.poly2 = Polygon([(73.0, 19.0), (73.2, 19.0), (73.2, 19.2), (73.0, 19.2), (73.0, 19.0)])
        self.mpoly = MultiPolygon([self.poly1, self.poly2])

    def test_a_polygon_handoff_and_serialization(self):
        """Test A: Construct a valid Polygon handoff and verify serialization."""
        result = create_drift_source_result(
            spill_id="SPILL-2025-001",
            detection_timestamp="2025-01-01T12:00:00Z",
            detection_latitude=18.0015,
            detection_longitude=72.4950,
            candidate_source_time="2025-01-01T09:00:00Z",
            source_time_status="candidate_identified",
            hdr_50_geometry=self.poly1,
            hdr_50_area_km2=6.39,
            hdr_90_geometry=self.poly1,
            hdr_90_area_km2=15.02,
            particle_count=500,
            backward_duration_hours=12.0,
            time_step_minutes=10.0,
            horizontal_diffusivity_m2_s=1.0,
        )

        d = result.to_dict()
        self.assertEqual(d["schema_version"], "1.0")
        self.assertEqual(d["spill_id"], "SPILL-2025-001")
        self.assertEqual(d["detection"]["timestamp"], "2025-01-01T12:00:00Z")
        self.assertEqual(d["detection"]["latitude"], 18.0015)
        self.assertEqual(d["detection"]["longitude"], 72.4950)
        self.assertEqual(d["source_time"]["candidate"], "2025-01-01T09:00:00Z")
        self.assertEqual(d["source_time"]["status"], "candidate_identified")
        self.assertEqual(d["source_support"]["hdr_50"]["geometry"]["type"], "Polygon")
        self.assertEqual(d["source_support"]["hdr_50"]["area_km2"], 6.39)
        self.assertEqual(d["model"]["particle_count"], 500)
        self.assertEqual(d["status"], "success")


    def test_b_multipolygon_handoff(self):
        """Test B: Construct a valid MultiPolygon handoff and verify geometry type remains MultiPolygon."""
        result = create_drift_source_result(
            spill_id="SPILL-2025-002",
            detection_timestamp="2025-01-01T12:00:00Z",
            detection_latitude=18.0,
            detection_longitude=72.5,
            candidate_source_time="2025-01-01T08:00:00Z",
            source_time_status="candidate_identified",
            hdr_50_geometry=self.mpoly,
            hdr_50_area_km2=12.5,
            hdr_90_geometry=self.mpoly,
            hdr_90_area_km2=25.0,
            particle_count=500,
            backward_duration_hours=12.0,
            time_step_minutes=10.0,
            horizontal_diffusivity_m2_s=1.0,
        )

        d = result.to_dict()
        self.assertEqual(d["source_support"]["hdr_50"]["geometry"]["type"], "MultiPolygon")
        self.assertEqual(d["source_support"]["hdr_90"]["geometry"]["type"], "MultiPolygon")
        self.assertEqual(len(d["source_support"]["hdr_50"]["geometry"]["coordinates"]), 2)

    def test_c_none_source_time_candidate(self):
        """Test C: Verify that a None source-time candidate is accepted."""
        result = create_drift_source_result(
            spill_id="SPILL-2025-003",
            detection_timestamp="2025-01-01T12:00:00Z",
            detection_latitude=18.0,
            detection_longitude=72.5,
            candidate_source_time=None,
            source_time_status="indeterminate_conflicting_minima",
            hdr_50_geometry=self.poly1,
            hdr_50_area_km2=6.0,
            hdr_90_geometry=self.poly1,
            hdr_90_area_km2=15.0,
            particle_count=500,
            backward_duration_hours=12.0,
            time_step_minutes=10.0,
            horizontal_diffusivity_m2_s=1.0,
        )

        d = result.to_dict()
        self.assertIsNone(d["source_time"]["candidate"])
        self.assertEqual(d["source_time"]["status"], "indeterminate_conflicting_minima")

    def test_d_indeterminate_status_preservation(self):
        """Test D: Verify that indeterminate source status is preserved exactly without alteration."""
        statuses = [
            "indeterminate_flat_signal",
            "indeterminate_boundary_minimum",
            "indeterminate_conflicting_minima",
            "insufficient_temporal_data",
        ]
        for status in statuses:
            result = create_drift_source_result(
                spill_id="SPILL-TEST",
                detection_timestamp="2025-01-01T12:00:00Z",
                detection_latitude=18.0,
                detection_longitude=72.5,
                candidate_source_time=None,
                source_time_status=status,
                hdr_50_geometry=self.poly1,
                hdr_50_area_km2=5.0,
                hdr_90_geometry=self.poly1,
                hdr_90_area_km2=12.0,
                particle_count=100,
                backward_duration_hours=6.0,
                time_step_minutes=10.0,
                horizontal_diffusivity_m2_s=1.0,
            )
            self.assertEqual(result.source_time.status, status)
            self.assertEqual(result.to_dict()["source_time"]["status"], status)

    def test_e_required_field_validation(self):
        """Test E: Verify required-field validation and clear error exceptions."""
        with self.assertRaises(ValueError):
            create_drift_source_result(
                spill_id="",
                detection_timestamp="2025-01-01T12:00:00Z",
                detection_latitude=18.0,
                detection_longitude=72.5,
                source_time_status="candidate_identified",
                hdr_50_geometry=self.poly1,
                hdr_50_area_km2=6.0,
                hdr_90_geometry=self.poly1,
                hdr_90_area_km2=15.0,
                particle_count=500,
                backward_duration_hours=12.0,
                time_step_minutes=10.0,
                horizontal_diffusivity_m2_s=1.0,
            )

        with self.assertRaises(ValueError):
            DetectionInfo(timestamp="2025-01-01", latitude=100.0, longitude=72.0)

        with self.assertRaises(ValueError):
            DetectionInfo(timestamp="2025-01-01", latitude=18.0, longitude=-200.0)

        with self.assertRaises(ValueError):
            ModelMetadataInfo(
                particle_count=0,
                backward_duration_hours=12.0,
                time_step_minutes=10.0,
                horizontal_diffusivity_m2_s=1.0,
            )

        with self.assertRaises(ValueError):
            HDRSupportInfo(geometry=self.poly1, area_km2=-5.0)

        with self.assertRaises(TypeError):
            HDRSupportInfo(geometry="invalid_geometry", area_km2=5.0)


    def test_f_lat_lon_area_serialization(self):
        """Test F: Verify that latitude/longitude and area values are serialized correctly."""
        lat, lon = 18.987654, 72.123456
        area50, area90 = 6.38612, 15.00945

        result = create_drift_source_result(
            spill_id="SPILL-SER-TEST",
            detection_timestamp="2025-01-01T12:00:00Z",
            detection_latitude=lat,
            detection_longitude=lon,
            candidate_source_time="2025-01-01T09:00:00Z",
            source_time_status="candidate_identified",
            hdr_50_geometry=self.poly1,
            hdr_50_area_km2=area50,
            hdr_90_geometry=self.poly1,
            hdr_90_area_km2=area90,
            particle_count=500,
            backward_duration_hours=12.0,
            time_step_minutes=10.0,
            horizontal_diffusivity_m2_s=1.0,
        )

        d = result.to_dict()
        self.assertAlmostEqual(d["detection"]["latitude"], lat, places=6)
        self.assertAlmostEqual(d["detection"]["longitude"], lon, places=6)
        self.assertAlmostEqual(d["source_support"]["hdr_50"]["area_km2"], area50, places=5)
        self.assertAlmostEqual(d["source_support"]["hdr_90"]["area_km2"], area90, places=5)

    def test_g_json_roundtrip_serialization(self):
        """Test G: Verify the final object can round-trip through JSON serialization."""
        original = create_drift_source_result(
            spill_id="SPILL-ROUNDTRIP",
            detection_timestamp="2025-01-01T12:00:00Z",
            detection_latitude=18.0,
            detection_longitude=72.5,
            candidate_source_time="2025-01-01T09:00:00Z",
            source_time_status="candidate_identified",
            hdr_50_geometry=self.poly1,
            hdr_50_area_km2=6.39,
            hdr_90_geometry=self.poly1,
            hdr_90_area_km2=15.02,
            particle_count=500,
            backward_duration_hours=12.0,
            time_step_minutes=10.0,
            horizontal_diffusivity_m2_s=1.0,
        )

        json_str = original.to_json(indent=2)
        self.assertIsInstance(json_str, str)

        parsed_dict = json.loads(json_str)
        reconstructed = DriftSourceResult.from_dict(parsed_dict)

        self.assertEqual(reconstructed.spill_id, original.spill_id)
        self.assertEqual(reconstructed.detection.latitude, original.detection.latitude)
        self.assertEqual(reconstructed.source_time.candidate, original.source_time.candidate)
        self.assertEqual(reconstructed.source_support.hdr_50.area_km2, original.source_support.hdr_50.area_km2)
        self.assertEqual(reconstructed.to_dict(), original.to_dict())


if __name__ == "__main__":
    unittest.main(exit=False)
    print("\n===========================================================")
    print("EXAMPLE SERIALIZED DriftSourceResult JSON HANDOFF CONTRACT:")
    print("===========================================================")
    example_geom_50 = Polygon([(72.48, 17.99), (72.51, 17.99), (72.51, 18.01), (72.48, 18.01), (72.48, 17.99)])
    example_geom_90 = Polygon([(72.45, 17.96), (72.54, 17.96), (72.54, 18.04), (72.45, 18.04), (72.45, 17.96)])
    sample = create_drift_source_result(
        spill_id="SPILL-2025-01-01-001",
        detection_timestamp="2025-01-01T12:00:00Z",
        detection_latitude=18.0015,
        detection_longitude=72.4950,
        candidate_source_time="2025-01-01T09:00:00Z",
        source_time_status="candidate_identified",
        hdr_50_geometry=example_geom_50,
        hdr_50_area_km2=6.39,
        hdr_90_geometry=example_geom_90,
        hdr_90_area_km2=15.02,
        particle_count=500,
        backward_duration_hours=12.0,
        time_step_minutes=10.0,
        horizontal_diffusivity_m2_s=1.0,
    )
    print(sample.to_json(indent=2))
