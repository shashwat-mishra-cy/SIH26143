"""P2 -> P3 Pipeline Integration Test for SIH26143 Drift Module.

Executes the full real-forcing backward simulation ensemble and source-estimation workflow,
and constructs the official P2 -> P3 DriftSourceResult handoff contract object.
"""

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict
from shapely.geometry import Polygon

from drift.simulation.backward import (
    group_trajectories_by_timestamp,
    run_polygon_backward_simulation,
)
from drift.simulation.source_support import analyze_source_support
from drift.simulation.source_support_diagnostics import calculate_temporal_diagnostics
from drift.simulation.source_estimation import estimate_source_time
from drift.simulation.handoff import DriftSourceResult, create_drift_source_result


def run_p2_p3_integration():
    print("===========================================================")
    print("P2 -> P3 DRIFT PIPELINE INTEGRATION TEST")
    print("===========================================================")

    # 1. Setup detection parameters
    spill_id = "SPILL-2025-01-01-MUMBAI-01"
    detection_time = datetime(2025, 1, 1, 12, 0, 0)
    detection_ts_str = "2025-01-01T12:00:00Z"

    # Polygon detection footprint (Mumbai offshore region)
    detection_polygon = [
        [72.48, 17.99],
        [72.52, 17.99],
        [72.52, 18.01],
        [72.48, 18.01],
    ]
    detection_lat = 18.0
    detection_lon = 72.5

    duration_hours = 12.0
    number_of_particles = 500
    time_step_minutes = 10.0
    diffusivity = 1.0

    print("Step 1: Running real-forcing backward particle ensemble simulation...")
    print(f"  - Footprint: Bounding box around ({detection_lon}, {detection_lat})")
    print(f"  - Detection Time: {detection_ts_str}")
    print(f"  - Ensemble Particle Count: {number_of_particles}")
    print(f"  - Duration: {duration_hours} hours backward")

    simulation_result = run_polygon_backward_simulation(
        polygon_coordinates=detection_polygon,
        detection_time=detection_time,
        duration_hours=int(duration_hours),
        number_of_particles=number_of_particles,
        time_step_minutes=int(time_step_minutes),
    )

    trajectories = simulation_result["trajectories"]
    grouped_trajectories = group_trajectories_by_timestamp(trajectories)
    print(f"  - Generated backward particle ensemble with {len(trajectories)} trajectories across {len(grouped_trajectories)} timesteps.")

    # 2. Run source-support timeline analysis
    print("\nStep 2: Performing source-support temporal analysis (KDE & HDR)...")
    source_support_results = analyze_source_support(
        trajectories_by_timestamp=grouped_trajectories,
        grid_resolution=100,
        hdr_levels=(0.50, 0.90),
    )

    # 3. Compute temporal diagnostics
    print("Step 3: Calculating temporal diagnostics...")
    diagnostics = calculate_temporal_diagnostics(source_support_results)

    # 4. Estimate source time window
    print("Step 4: Running scientific source-time window estimator...")
    estimation = estimate_source_time(diagnostics)

    candidate_ts = estimation.get("candidate_source_time")
    estimator_status = estimation.get("status")

    print(f"  - Estimator Status: {estimator_status}")
    print(f"  - Candidate Source Timestamp: {candidate_ts}")

    # Select target timestamp's HDR geometry & area
    # If candidate timestamp is identified, use it; otherwise select timestamp with minimum 50% HDR area
    target_ts = candidate_ts
    if target_ts is None:
        valid_supports = [s for s in source_support_results if s.get("status") == "success"]
        if valid_supports:
            best = min(valid_supports, key=lambda s: s["hdr_50_area_m2"])
            target_ts = best["timestamp"]
        else:
            target_ts = detection_ts_str

    support_record = next((s for s in source_support_results if s["timestamp"] == target_ts), source_support_results[0])

    hdr_50_geom = support_record["hdr_50_geometry"]
    hdr_50_area_km2 = float(support_record["hdr_50_area_m2"]) / 1e6

    hdr_90_geom = support_record["hdr_90_geometry"]
    hdr_90_area_km2 = float(support_record["hdr_90_area_m2"]) / 1e6

    # 5. Build DriftSourceResult handoff object
    print("\nStep 5: Constructing P2 -> P3 DriftSourceResult handoff contract...")
    handoff_result = create_drift_source_result(
        spill_id=spill_id,
        detection_timestamp=detection_ts_str,
        detection_latitude=detection_lat,
        detection_longitude=detection_lon,
        candidate_source_time=candidate_ts,
        source_time_status=estimator_status,
        hdr_50_geometry=hdr_50_geom,
        hdr_50_area_km2=hdr_50_area_km2,
        hdr_90_geometry=hdr_90_geom,
        hdr_90_area_km2=hdr_90_area_km2,
        particle_count=number_of_particles,
        backward_duration_hours=duration_hours,
        time_step_minutes=time_step_minutes,
        horizontal_diffusivity_m2_s=diffusivity,
        status="success",
    )

    # 6. Serialize to JSON
    print("Step 6: Serializing DriftSourceResult to JSON string...")
    json_serialized = handoff_result.to_json(indent=2)

    # 7. Write to final artifact JSON file
    project_root = Path(__file__).resolve().parent.parent.parent
    output_path = project_root / "drift" / "data" / f"p2_p3_handoff_{spill_id}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(json_serialized)

    file_size_bytes = output_path.stat().st_size

    # 8. Deserialize JSON file back to verify contract validation
    print("Step 7: Deserializing JSON artifact file back into DriftSourceResult object...")
    with open(output_path, "r", encoding="utf-8") as f:
        loaded_dict = json.load(f)

    reconstructed_result = DriftSourceResult.from_dict(loaded_dict)

    assert reconstructed_result.spill_id == handoff_result.spill_id
    assert reconstructed_result.detection.timestamp == handoff_result.detection.timestamp
    assert reconstructed_result.source_time.status == handoff_result.source_time.status
    assert reconstructed_result.source_time.candidate == handoff_result.source_time.candidate
    assert reconstructed_result.source_support.hdr_50.area_km2 == handoff_result.source_support.hdr_50.area_km2
    assert reconstructed_result.source_support.hdr_90.area_km2 == handoff_result.source_support.hdr_90.area_km2

    print("  -> Contract round-trip validation PASSED successfully.")

    # 9. Print concise summary of actual values
    print("\n===========================================================")
    print("P2 -> P3 INTEGRATION RESULTS SUMMARY")
    print("===========================================================")
    print(f"Spill ID:                 {reconstructed_result.spill_id}")
    print(f"Detection Timestamp:      {reconstructed_result.detection.timestamp}")
    print(f"Detection Coordinates:    ({reconstructed_result.detection.latitude}, {reconstructed_result.detection.longitude})")
    print(f"Candidate Source Time:    {reconstructed_result.source_time.candidate}")
    print(f"Source Estimator Status:  {reconstructed_result.source_time.status}")
    print(f"50% HDR Region Type:      {reconstructed_result.source_support.hdr_50.geometry['type']}")
    print(f"50% HDR Area:             {reconstructed_result.source_support.hdr_50.area_km2:.3f} km²")
    print(f"90% HDR Region Type:      {reconstructed_result.source_support.hdr_90.geometry['type']}")
    print(f"90% HDR Area:             {reconstructed_result.source_support.hdr_90.area_km2:.3f} km²")
    print(f"Ensemble Particle Count:  {reconstructed_result.model.particle_count}")
    print(f"Backward Duration:        {reconstructed_result.model.backward_duration_hours} hours")
    print("===========================================================")
    print("\nP2 -> P3 HANDOFF JSON ARTIFACT CREATED:")
    print(f"  - File Path:          {output_path}")
    print(f"  - File Size:          {file_size_bytes} bytes ({file_size_bytes / 1024:.2f} KB)")
    print(f"  - Geometry Types:     50% HDR: {reconstructed_result.source_support.hdr_50.geometry['type']} | 90% HDR: {reconstructed_result.source_support.hdr_90.geometry['type']}")
    print(f"  - Candidate Time:     {reconstructed_result.source_time.candidate}")
    print(f"  - Estimator Status:   {reconstructed_result.source_time.status}")
    print(f"  - Validation Result:  PASSED (Loaded via DriftSourceResult.from_dict)")
    print("===========================================================")



if __name__ == "__main__":
    run_p2_p3_integration()
