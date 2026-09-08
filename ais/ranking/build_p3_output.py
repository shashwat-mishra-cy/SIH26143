from pathlib import Path
import json

import polars as pl


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

SCORES_FILE = (
    BASE_DIR
    / "output"
    / "candidates"
    / "ais_candidate_scores.parquet"
)

TRAJECTORIES_FILE = (
    BASE_DIR
    / "output"
    / "candidates"
    / "candidate_trajectories.parquet"
)

OUTPUT_DIR = (
    BASE_DIR
    / "output"
    / "p3"
)

OUTPUT_JSON = (
    OUTPUT_DIR
    / "p3_vessel_ranking.json"
)

OUTPUT_TRAJECTORY_FILE = (
    OUTPUT_DIR
    / "p3_top3_trajectories.parquet"
)


# ============================================================
# CONFIGURATION
# ============================================================

TOP_N = 3


# ============================================================
# HELPERS
# ============================================================

def require_columns(
    df: pl.DataFrame,
    required: list[str],
    dataset_name: str,
):
    missing = [
        column
        for column in required
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{dataset_name} is missing required columns: {missing}"
        )


def safe_value(value):
    """
    Convert Polars/Python values into JSON-safe values.
    """

    if value is None:
        return None

    # Polars / Python temporal objects
    if hasattr(value, "isoformat"):
        return value.isoformat()

    return value


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("BUILDING FINAL P3 → P4 OUTPUT")
    print("=" * 70)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ========================================================
    # 1. LOAD FINAL SCORES
    # ========================================================

    print("\nLoading final vessel scores...")

    scores = pl.read_parquet(
        SCORES_FILE
    )

    require_columns(
        scores,
        [
            "rank",
            "mmsi",
            "association_score",
            "spatial_score",
            "temporal_score",
            "trajectory_score",
            "behaviour_score",
            "quality_score",
        ],
        "AIS candidate scores",
    )

    print(
        f"Ranked vessels: {scores.height:,}"
    )

    # ========================================================
    # 2. GET TOP 3
    # ========================================================

    top_vessels = (
        scores
        .sort("rank")
        .head(TOP_N)
    )

    print("\nTop vessels selected:")

    print(
        top_vessels.select(
            [
                "rank",
                "mmsi",
                "association_score",
                "spatial_score",
                "temporal_score",
                "trajectory_score",
                "behaviour_score",
                "quality_score",
            ]
        )
    )

    top_mmsis = (
        top_vessels
        .get_column("mmsi")
        .to_list()
    )

    # ========================================================
    # 3. LOAD COMPLETE AIS TRAJECTORIES
    # ========================================================

    print("\nLoading candidate trajectories...")

    trajectories = pl.read_parquet(
        TRAJECTORIES_FILE
    )

    require_columns(
        trajectories,
        [
            "mmsi",
            "timestamp",
            "latitude",
            "longitude",
        ],
        "Candidate trajectories",
    )

    print(
        f"Candidate trajectory records: "
        f"{trajectories.height:,}"
    )

    # ========================================================
    # 4. EXTRACT COMPLETE TOP-3 TRAJECTORIES
    # ========================================================

    print(
        "\nExtracting complete trajectories for Top 3..."
    )

    top3_trajectories = (
        trajectories
        .filter(
            pl.col("mmsi").is_in(top_mmsis)
        )
        .sort(
            [
                "mmsi",
                "timestamp",
            ]
        )
    )

    print(
        f"Top-3 trajectory records: "
        f"{top3_trajectories.height:,}"
    )

    # ========================================================
    # 5. VALIDATE TRAJECTORIES
    # ========================================================

    print("\nValidating Top-3 trajectories...")

    invalid_coordinates = (
        top3_trajectories
        .filter(
            pl.col("latitude").is_null()
            | pl.col("longitude").is_null()
        )
        .height
    )

    duplicate_points = (
        top3_trajectories
        .group_by(
            [
                "mmsi",
                "timestamp",
            ]
        )
        .len()
        .filter(
            pl.col("len") > 1
        )
        .height
    )

    print(
        f"Invalid coordinate records: "
        f"{invalid_coordinates}"
    )

    print(
        f"Duplicate timestamp groups: "
        f"{duplicate_points}"
    )

    if invalid_coordinates > 0:
        raise ValueError(
            "Top-3 trajectories contain invalid coordinates."
        )

    if duplicate_points > 0:
        raise ValueError(
            "Top-3 trajectories contain duplicate "
            "MMSI/timestamp points."
        )

    # ========================================================
    # 6. SAVE TOP-3 TRAJECTORIES
    # ========================================================

    top3_trajectories.write_parquet(
        OUTPUT_TRAJECTORY_FILE
    )

    print(
        f"\nSaved trajectory file:\n"
        f"{OUTPUT_TRAJECTORY_FILE}"
    )

    # ========================================================
    # 7. BUILD JSON OUTPUT
    # ========================================================

    print("\nBuilding dashboard-ready JSON...")

    vessels_output = []

    for vessel_row in top_vessels.iter_rows(
        named=True
    ):

        mmsi = vessel_row["mmsi"]

        vessel_trajectory = (
            top3_trajectories
            .filter(
                pl.col("mmsi") == mmsi
            )
            .sort("timestamp")
        )

        trajectory_points = []

        for point in vessel_trajectory.iter_rows(
            named=True
        ):

            trajectory_point = {
                "timestamp": safe_value(
                    point["timestamp"]
                ),
                "latitude": safe_value(
                    point["latitude"]
                ),
                "longitude": safe_value(
                    point["longitude"]
                ),
            }

            # --------------------------------------------
            # Optional movement fields
            # --------------------------------------------

            if "sog_kmh" in point:
                trajectory_point[
                    "speed_kmh"
                ] = safe_value(
                    point["sog_kmh"]
                )

            elif "speed_kmh" in point:
                trajectory_point[
                    "speed_kmh"
                ] = safe_value(
                    point["speed_kmh"]
                )

            if "heading" in point:
                trajectory_point[
                    "heading"
                ] = safe_value(
                    point["heading"]
                )

            if "cog" in point:
                trajectory_point[
                    "course_over_ground"
                ] = safe_value(
                    point["cog"]
                )

            trajectory_points.append(
                trajectory_point
            )

        # --------------------------------------------
        # Build evidence section
        # --------------------------------------------

        evidence = {}

        evidence_fields = {
            "distance_to_source_km":
                "minimum_distance_to_source_km",

            "closest_observation_time":
                "closest_observation_time",

            "closest_latitude":
                "closest_latitude",

            "closest_longitude":
                "closest_longitude",

            "closest_speed_kmh":
                "closest_speed_kmh",

            "closest_heading":
                "closest_heading",

            "behaviour_anomaly_records":
                "behaviour_anomaly_records",

            "data_quality_anomaly_records":
                "data_quality_anomaly_records",

            "trajectory_points":
                "trajectory_points",

            "aligned_points":
                "aligned_points",

            "alignment_coverage":
                "alignment_coverage",

            "mean_oil_distance_km":
                "mean_oil_distance_km",

            "mean_oil_time_difference_seconds":
                "mean_oil_time_difference_seconds",
        }

        for output_name, source_name in evidence_fields.items():

            if source_name in vessel_row:
                evidence[
                    output_name
                ] = safe_value(
                    vessel_row[source_name]
                )

        # --------------------------------------------
        # Vessel object
        # --------------------------------------------

        vessel = {
            "rank": safe_value(
                vessel_row["rank"]
            ),

            "mmsi": safe_value(
                mmsi
            ),

            "vessel_name": safe_value(
                vessel_row.get(
                    "vessel_name"
                )
            ),

            "vessel_type": safe_value(
                vessel_row.get(
                    "vessel_type"
                )
            ),

            "imo": safe_value(
                vessel_row.get(
                    "imo"
                )
            ),

            "call_sign": safe_value(
                vessel_row.get(
                    "call_sign"
                )
            ),

            # ----------------------------------------
            # Association scores
            # ----------------------------------------

            "association_score": safe_value(
                vessel_row[
                    "association_score"
                ]
            ),

            "scores": {
                "spatial": safe_value(
                    vessel_row[
                        "spatial_score"
                    ]
                ),

                "temporal": safe_value(
                    vessel_row[
                        "temporal_score"
                    ]
                ),

                "trajectory": safe_value(
                    vessel_row[
                        "trajectory_score"
                    ]
                ),

                "behaviour": safe_value(
                    vessel_row[
                        "behaviour_score"
                    ]
                ),

                "data_quality": safe_value(
                    vessel_row[
                        "quality_score"
                    ]
                ),
            },

            # ----------------------------------------
            # Explainable evidence
            # ----------------------------------------

            "evidence": evidence,

            # ----------------------------------------
            # Complete relevant AIS trajectory
            # ----------------------------------------

            "trajectory": trajectory_points,
        }

        vessels_output.append(
            vessel
        )

    # ========================================================
    # 8. FINAL JSON STRUCTURE
    # ========================================================

    result = {
        "module": "P3_AIS_VESSEL_CORRELATION",

        "version": "1.0",

        "status": "prototype",

        "description": (
            "Ranked AIS vessels based on spatial, temporal, "
            "trajectory, behavioural and data-quality evidence."
        ),

        "attribution_note": (
            "Association score indicates relative correlation "
            "with the estimated spill source and does not prove "
            "that a vessel caused the spill."
        ),

        "top_vessels": vessels_output,
    }

    # ========================================================
    # 9. WRITE JSON
    # ========================================================

    with open(
        OUTPUT_JSON,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            result,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print(
        f"\nSaved dashboard JSON:\n"
        f"{OUTPUT_JSON}"
    )

    # ========================================================
    # 10. FINAL SUMMARY
    # ========================================================

    print("\n" + "=" * 70)
    print("P3 OUTPUT PACKAGE COMPLETE")
    print("=" * 70)

    print(
        f"\nTop vessels: {len(vessels_output)}"
    )

    print(
        f"Trajectory records exported: "
        f"{top3_trajectories.height:,}"
    )

    print("\nTop 3:")

    for vessel in vessels_output:

        print(
            f"  #{vessel['rank']} "
            f"{vessel['mmsi']} "
            f"{vessel['vessel_name']} "
            f"→ "
            f"{vessel['association_score']:.4f}"
        )

    print("\nFiles created:")

    print(
        f"  JSON:       {OUTPUT_JSON}"
    )

    print(
        f"  Trajectory: {OUTPUT_TRAJECTORY_FILE}"
    )

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()