"""Diagnostic temporal-analysis module for backward drift source-support regions.

Computes trajectory-wide temporal evolution metrics (area changes, centroid displacements,
and relative area expansion/contraction) across chronological source-support timestamps.
Strictly a diagnostic layer — performs no source-time selection, scoring, or causal ranking.
"""

import math
from typing import Any, Dict, List
from drift.simulation.coordinates import project_latlon_to_xy


def calculate_temporal_diagnostics(
    source_support_results: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Compute temporal diagnostic metrics across chronological source-support results.

    Args:
        source_support_results: List of dictionaries output by analyze_source_support().

    Returns:
        List of dictionaries containing per-timestamp metric values and consecutive temporal changes.
    """
    sorted_inputs = sorted(
        source_support_results, key=lambda x: str(x.get("timestamp", ""))
    )

    diagnostics: List[Dict[str, Any]] = []
    prev_valid: Dict[str, Any] = None

    for item in sorted_inputs:
        status = item.get("status", "success")
        timestamp = str(item.get("timestamp", ""))

        if status != "success":
            diagnostics.append(
                {
                    "timestamp": timestamp,
                    "status": status,
                    "particle_count": item.get("particle_count", 0),
                    "hdr_50_area_m2": None,
                    "hdr_90_area_m2": None,
                    "hdr_50_area_km2": None,
                    "hdr_90_area_km2": None,
                    "kde_max_density": None,
                    "hdr_50_centroid_lat": None,
                    "hdr_50_centroid_lon": None,
                    "hdr_90_centroid_lat": None,
                    "hdr_90_centroid_lon": None,
                    "hdr_50_component_count": None,
                    "hdr_90_component_count": None,
                    "hdr_50_area_change_m2": None,
                    "hdr_90_area_change_m2": None,
                    "hdr_50_centroid_displacement_m": None,
                    "hdr_90_centroid_displacement_m": None,
                    "hdr_50_area_relative_change": None,
                    "hdr_90_area_relative_change": None,
                }
            )
            continue

        a50_m2 = float(item["hdr_50_area_m2"])
        a90_m2 = float(item["hdr_90_area_m2"])
        a50_km2 = a50_m2 / 1e6
        a90_km2 = a90_m2 / 1e6

        kde_max = float(item["kde_max_density"])

        if "hdr_50_centroid" in item and item["hdr_50_centroid"] is not None:
            c50_lon, c50_lat = float(item["hdr_50_centroid"][0]), float(item["hdr_50_centroid"][1])
        else:
            c50_lon = float(item.get("hdr_50_centroid_lon", 0.0))
            c50_lat = float(item.get("hdr_50_centroid_lat", 0.0))

        if "hdr_90_centroid" in item and item["hdr_90_centroid"] is not None:
            c90_lon, c90_lat = float(item["hdr_90_centroid"][0]), float(item["hdr_90_centroid"][1])
        else:
            c90_lon = float(item.get("hdr_90_centroid_lon", 0.0))
            c90_lat = float(item.get("hdr_90_centroid_lat", 0.0))

        comp50 = int(item["hdr_50_component_count"])
        comp90 = int(item["hdr_90_component_count"])

        if prev_valid is None:
            a50_change = 0.0
            a90_change = 0.0
            disp50 = 0.0
            disp90 = 0.0
            rel50 = 0.0
            rel90 = 0.0
        else:
            prev_a50 = prev_valid["hdr_50_area_m2"]
            prev_a90 = prev_valid["hdr_90_area_m2"]

            a50_change = a50_m2 - prev_a50
            a90_change = a90_m2 - prev_a90

            rel50 = (a50_change / prev_a50) if prev_a50 > 0 else 0.0
            rel90 = (a90_change / prev_a90) if prev_a90 > 0 else 0.0

            x50, y50 = project_latlon_to_xy(
                c50_lon,
                c50_lat,
                prev_valid["hdr_50_centroid_lon"],
                prev_valid["hdr_50_centroid_lat"],
            )
            disp50 = float(math.hypot(x50, y50))

            x90, y90 = project_latlon_to_xy(
                c90_lon,
                c90_lat,
                prev_valid["hdr_90_centroid_lon"],
                prev_valid["hdr_90_centroid_lat"],
            )
            disp90 = float(math.hypot(x90, y90))

        diag_entry = {
            "timestamp": timestamp,
            "status": "success",
            "particle_count": item.get("particle_count", 0),
            "hdr_50_area_m2": a50_m2,
            "hdr_90_area_m2": a90_m2,
            "hdr_50_area_km2": a50_km2,
            "hdr_90_area_km2": a90_km2,
            "kde_max_density": kde_max,
            "hdr_50_centroid_lat": c50_lat,
            "hdr_50_centroid_lon": c50_lon,
            "hdr_90_centroid_lat": c90_lat,
            "hdr_90_centroid_lon": c90_lon,
            "hdr_50_component_count": comp50,
            "hdr_90_component_count": comp90,
            "hdr_50_area_change_m2": a50_change,
            "hdr_90_area_change_m2": a90_change,
            "hdr_50_centroid_displacement_m": disp50,
            "hdr_90_centroid_displacement_m": disp90,
            "hdr_50_area_relative_change": rel50,
            "hdr_90_area_relative_change": rel90,
        }

        diagnostics.append(diag_entry)
        prev_valid = diag_entry

    return diagnostics
