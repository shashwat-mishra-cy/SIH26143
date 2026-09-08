from pathlib import Path
import polars as pl


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

CANDIDATES_FILE = (
    BASE_DIR
    / "output"
    / "candidates"
    / "ais_candidates.parquet"
)

AIS_FILE = (
    BASE_DIR
    / "output"
    / "anomalies"
    / "ais_anomalies.parquet"
)

OUTPUT_DIR = BASE_DIR / "output" / "candidates"
OUTPUT_FILE = OUTPUT_DIR / "candidate_trajectories.parquet"


# ============================================================
# CONFIGURATION
# ============================================================

# Only keep AIS observations inside the candidate's
# relevant source/spill time window.
#
# These are currently the same dummy P2 values used
# elsewhere in the P3 pipeline.
#
# Replace these later with actual P2 output.
SOURCE_TIME_START = "2025-01-01T00:00:00"
SOURCE_TIME_END = "2025-01-01T23:59:59"


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("BUILD CANDIDATE VESSEL TRAJECTORIES")
    print("=" * 70)

    # --------------------------------------------------------
    # 1. Check input files
    # --------------------------------------------------------

    if not CANDIDATES_FILE.exists():
        raise FileNotFoundError(
            f"Candidate file not found:\n{CANDIDATES_FILE}"
        )

    if not AIS_FILE.exists():
        raise FileNotFoundError(
            f"AIS anomaly file not found:\n{AIS_FILE}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------
    # 2. Parse source time window
    # --------------------------------------------------------

    source_start = pl.lit(
        SOURCE_TIME_START.replace("T", " ")
    ).str.to_datetime()

    source_end = pl.lit(
        SOURCE_TIME_END.replace("T", " ")
    ).str.to_datetime()

    # --------------------------------------------------------
    # 3. Load candidate vessels
    # --------------------------------------------------------

    print("\nLoading candidate vessels...")

    candidates = pl.read_parquet(CANDIDATES_FILE)

    if "mmsi" not in candidates.columns:
        raise ValueError(
            "Candidate file does not contain an 'mmsi' column."
        )

    candidate_mmsis = (
        candidates
        .select("mmsi")
        .unique()
        .drop_nulls()
    )

    print(f"Candidate vessels: {candidate_mmsis.height}")

    # --------------------------------------------------------
    # 4. Load AIS data
    # --------------------------------------------------------

    print("\nLoading AIS anomaly data...")

    ais = pl.read_parquet(AIS_FILE)

    print(f"AIS records loaded: {ais.height:,}")

    required_columns = [
        "mmsi",
        "base_date_time",
        "latitude",
        "longitude",
    ]

    missing = [
        col
        for col in required_columns
        if col not in ais.columns
    ]

    if missing:
        raise ValueError(
            f"AIS file is missing required columns: {missing}"
        )

    # --------------------------------------------------------
    # 5. Keep only candidate vessels
    # --------------------------------------------------------

    print("\nFiltering AIS data to candidate vessels...")

    trajectories = ais.join(
        candidate_mmsis,
        on="mmsi",
        how="inner",
    )

    print(
        f"AIS records belonging to candidates: "
        f"{trajectories.height:,}"
    )

    # --------------------------------------------------------
    # 6. Restrict to relevant source time window
    # --------------------------------------------------------

    print("\nApplying source time window...")

    trajectories = trajectories.filter(
        (pl.col("base_date_time") >= source_start)
        & (pl.col("base_date_time") <= source_end)
    )

    print(
        f"Candidate AIS records in time window: "
        f"{trajectories.height:,}"
    )

    # --------------------------------------------------------
    # 7. Select trajectory fields
    # --------------------------------------------------------

    desired_columns = [
        "mmsi",
        "base_date_time",
        "latitude",
        "longitude",

        # Movement information
        "sog_kmh",
        "cog",
        "heading",

        # Vessel information
        "vessel_name",
        "vessel_type",
        "imo",
        "call_sign",

        # Existing trajectory information
        "delta_seconds",
        "distance_km",
        "calculated_speed_kmh",

        # Behaviour information
        "speed_anomaly",
        "acceleration_anomaly",
        "turn_anomaly",
        "behaviour_anomaly_score",
        "has_behaviour_anomaly",

        # Data quality information
        "data_quality_anomaly",
        "quality_flag",
        "quality_issue_score",
    ]

    # Only keep columns that actually exist.
    available_columns = [
        col
        for col in desired_columns
        if col in trajectories.columns
    ]

    trajectories = trajectories.select(available_columns)

    # --------------------------------------------------------
    # 8. Rename timestamp for shared P3/P4 contract
    # --------------------------------------------------------

    trajectories = trajectories.rename(
        {
            "base_date_time": "timestamp"
        }
    )

    # --------------------------------------------------------
    # 9. Sort trajectories
    # --------------------------------------------------------

    print("\nSorting trajectories chronologically...")

    trajectories = trajectories.sort(
        ["mmsi", "timestamp"]
    )

    # --------------------------------------------------------
    # 10. Validate coordinates
    # --------------------------------------------------------

    invalid_coordinates = trajectories.filter(
        (pl.col("latitude") < -90)
        | (pl.col("latitude") > 90)
        | (pl.col("longitude") < -180)
        | (pl.col("longitude") > 180)
    )

    print(
        f"Invalid coordinate records: "
        f"{invalid_coordinates.height:,}"
    )

    if invalid_coordinates.height > 0:
        print("Removing invalid coordinate records...")

        trajectories = trajectories.filter(
            (pl.col("latitude") >= -90)
            & (pl.col("latitude") <= 90)
            & (pl.col("longitude") >= -180)
            & (pl.col("longitude") <= 180)
        )

    # --------------------------------------------------------
    # 11. Remove rows with missing essential trajectory data
    # --------------------------------------------------------

    before = trajectories.height

    trajectories = trajectories.filter(
        pl.col("mmsi").is_not_null()
        & pl.col("timestamp").is_not_null()
        & pl.col("latitude").is_not_null()
        & pl.col("longitude").is_not_null()
    )

    removed = before - trajectories.height

    print(
        f"Removed records with missing trajectory data: "
        f"{removed:,}"
    )

    # --------------------------------------------------------
    # 12. Add explicit UTC timestamp string
    # --------------------------------------------------------

    trajectories = trajectories.with_columns(
        pl.col("timestamp")
        .dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        .alias("timestamp_utc")
    )

    # --------------------------------------------------------
    # 13. Remove duplicate timestamp observations
    # --------------------------------------------------------
    #
    # We keep the first observation for the same vessel/time.
    # This protects P4 and later trajectory calculations
    # from duplicate timestamp points.
    #
    # The original AIS cleaning pipeline already resolved
    # duplicate timestamp groups, but this is an additional
    # safety check for the candidate trajectory output.
    # --------------------------------------------------------

    before = trajectories.height

    trajectories = trajectories.unique(
        subset=["mmsi", "timestamp"],
        keep="first",
        maintain_order=True,
    )

    removed_duplicates = before - trajectories.height

    print(
        f"Duplicate vessel/timestamp records removed: "
        f"{removed_duplicates:,}"
    )

    # Re-sort after duplicate removal.
    trajectories = trajectories.sort(
        ["mmsi", "timestamp"]
    )

    # --------------------------------------------------------
    # 14. Save output
    # --------------------------------------------------------

    print("\nSaving candidate trajectories...")

    trajectories.write_parquet(OUTPUT_FILE)

    print(f"\nOutput saved to:")
    print(OUTPUT_FILE)

    # --------------------------------------------------------
    # 15. Validation summary
    # --------------------------------------------------------

    unique_vessels = trajectories.select(
        pl.col("mmsi").n_unique()
    ).item()

    print("\n" + "=" * 70)
    print("TRAJECTORY VALIDATION")
    print("=" * 70)

    print(
        f"Trajectory records : {trajectories.height:,}"
    )

    print(
        f"Unique vessels     : {unique_vessels:,}"
    )

    if trajectories.height > 0:

        print(
            f"Time range         : "
            f"{trajectories['timestamp'].min()} "
            f"→ "
            f"{trajectories['timestamp'].max()}"
        )

        trajectory_counts = (
            trajectories
            .group_by("mmsi")
            .agg(
                pl.len().alias("trajectory_points")
            )
            .sort(
                "trajectory_points",
                descending=True,
            )
        )

        print("\nTrajectory point statistics:")

        print(
            trajectory_counts
            .select(
                [
                    pl.col("trajectory_points").min().alias("min"),
                    pl.col("trajectory_points").median().alias("median"),
                    pl.col("trajectory_points").mean().alias("mean"),
                    pl.col("trajectory_points").max().alias("max"),
                ]
            )
        )

        print("\nTop 10 candidate trajectories:")

        print(
            trajectory_counts.head(10)
        )

    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()