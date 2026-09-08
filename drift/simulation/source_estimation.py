"""Model-supported source-time window estimation from temporal source-support diagnostics.

Identifies model-supported candidate source-time windows based on spatial density
concentration signals (local minima in 50% and 90% Highest Density Region areas).
Returns explicitly indeterminate results when signals are flat, boundary-constrained, or conflicting.
"""

from typing import Any, Dict, List


def estimate_source_time(
    diagnostics: List[Dict[str, Any]],
    relative_flatness_threshold: float = 0.05,
) -> Dict[str, Any]:
    """Estimate model-supported candidate source time window from temporal diagnostics.

    Args:
        diagnostics: List of dictionaries output by calculate_temporal_diagnostics().
        relative_flatness_threshold: Fractional threshold (default 0.05 = 5%) below which
            total HDR area variation across the analysis period is deemed flat.

    Returns:
        Dictionary containing status, candidate source time, source time window bounds,
        and supporting metadata.
    """
    valid_items = [
        d for d in sorted(diagnostics, key=lambda x: str(x.get("timestamp", "")))
        if d.get("status") == "success"
        and d.get("hdr_50_area_m2") is not None
        and d.get("hdr_90_area_m2") is not None
    ]

    n_valid = len(valid_items)
    if n_valid < 3:
        return {
            "status": "insufficient_temporal_data",
            "candidate_source_time": None,
            "source_time_window_start": None,
            "source_time_window_end": None,
            "reason": f"Fewer than 3 valid timestamps available for interior minimum analysis (got {n_valid}).",
            "minimum_50pct_hdr_area_m2": None,
            "minimum_90pct_hdr_area_m2": None,
            "supporting_timestamps": [],
        }

    timestamps = [d["timestamp"] for d in valid_items]
    a50 = [float(d["hdr_50_area_m2"]) for d in valid_items]
    a90 = [float(d["hdr_90_area_m2"]) for d in valid_items]

    min_a50, max_a50 = min(a50), max(a50)
    min_a90, max_a90 = min(a90), max(a90)

    rel_var_50 = (max_a50 - min_a50) / min_a50 if min_a50 > 0 else 0.0
    rel_var_90 = (max_a90 - min_a90) / min_a90 if min_a90 > 0 else 0.0

    if rel_var_50 <= relative_flatness_threshold and rel_var_90 <= relative_flatness_threshold:
        return {
            "status": "indeterminate_flat_signal",
            "candidate_source_time": None,
            "source_time_window_start": None,
            "source_time_window_end": None,
            "reason": (
                f"HDR areas are approximately flat over the analyzed period "
                f"(50% var {rel_var_50:.2%}, 90% var {rel_var_90:.2%} <= threshold {relative_flatness_threshold:.2%})."
            ),
            "minimum_50pct_hdr_area_m2": min_a50,
            "minimum_90pct_hdr_area_m2": min_a90,
            "supporting_timestamps": timestamps,
        }

    def _find_interior_minima(arr: List[float]) -> List[int]:
        minima = []
        for i in range(1, len(arr) - 1):
            if arr[i] < arr[i - 1] and arr[i] < arr[i + 1]:
                minima.append(i)
        return minima

    minima_50 = _find_interior_minima(a50)
    minima_90 = _find_interior_minima(a90)

    global_min_50_idx = a50.index(min_a50)
    global_min_90_idx = a90.index(min_a90)

    if not minima_50 or not minima_90:
        if global_min_50_idx in (0, n_valid - 1) or global_min_90_idx in (0, n_valid - 1):
            return {
                "status": "indeterminate_boundary_minimum",
                "candidate_source_time": None,
                "source_time_window_start": None,
                "source_time_window_end": None,
                "reason": (
                    "HDR area minimum occurs at analysis boundary (first or last timestamp); "
                    "backtrack window is insufficient to bound source release time."
                ),
                "minimum_50pct_hdr_area_m2": min_a50,
                "minimum_90pct_hdr_area_m2": min_a90,
                "supporting_timestamps": timestamps,
            }

    idx_50 = min(minima_50, key=lambda idx: (a50[idx], abs(idx - global_min_50_idx)))
    idx_90 = min(minima_90, key=lambda idx: (a90[idx], abs(idx - global_min_90_idx)))

    if abs(idx_50 - idx_90) > 1:
        return {
            "status": "indeterminate_conflicting_minima",
            "candidate_source_time": None,
            "source_time_window_start": None,
            "source_time_window_end": None,
            "reason": (
                f"Local minima for 50% HDR ({timestamps[idx_50]}) and 90% HDR ({timestamps[idx_90]}) "
                "occur at distant non-adjacent timestamps."
            ),
            "minimum_50pct_hdr_area_m2": a50[idx_50],
            "minimum_90pct_hdr_area_m2": a90[idx_90],
            "supporting_timestamps": [timestamps[idx_50], timestamps[idx_90]],
        }

    cand_idx = idx_50 if a50[idx_50] <= a50[idx_90] else idx_90
    if idx_50 == idx_90:
        cand_idx = idx_50

    start_idx = min(idx_50, idx_90) - 1
    end_idx = max(idx_50, idx_90) + 1

    return {
        "status": "candidate_identified",
        "candidate_source_time": timestamps[cand_idx],
        "source_time_window_start": timestamps[start_idx],
        "source_time_window_end": timestamps[end_idx],
        "reason": (
            "Model-supported candidate source-time window identified from aligned 50% and 90% HDR "
            "spatial concentration minima."
        ),
        "minimum_50pct_hdr_area_m2": a50[idx_50],
        "minimum_90pct_hdr_area_m2": a90[idx_90],
        "supporting_timestamps": timestamps[start_idx : end_idx + 1],
    }
