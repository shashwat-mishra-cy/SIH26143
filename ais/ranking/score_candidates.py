from pathlib import Path
from datetime import datetime

import polars as pl


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

CANDIDATES_FILE = (
    BASE_DIR / "output" / "candidates" / "ais_candidates.parquet"
)

TRAJECTORIES_FILE = (
    BASE_DIR / "output" / "candidates" / "candidate_trajectories.parquet"
)

TRAJECTORY_SCORES_FILE = (
    BASE_DIR / "output" / "candidates" / "trajectory_alignment_scores.parquet"
)

OUTPUT_DIR = BASE_DIR / "output" / "candidates"

OUTPUT_FILE = (
    OUTPUT_DIR / "ais_candidate_scores.parquet"
)


# ============================================================
# DUMMY P2 SOURCE WINDOW
#
# Replace these later with the real P2 output.
# All timestamps are UTC.
# ============================================================

SOURCE_TIME_START = "2025-01-01T00:00:00Z"
SOURCE_TIME_END = "2025-01-01T23:59:59Z"


# ============================================================
# SCORING WEIGHTS
#
# Total = 1.00
# ============================================================

SPATIAL_WEIGHT = 0.35
TEMPORAL_WEIGHT = 0.25
TRAJECTORY_WEIGHT = 0.20
BEHAVIOUR_WEIGHT = 0.10
DATA_QUALITY_WEIGHT = 0.10


# ============================================================
# SPATIAL PARAMETERS
# ============================================================

# Candidate generation currently uses a 50 km source radius.
# A vessel at 0 km gets spatial score 1.
# A vessel at 50 km gets spatial score 0.
SOURCE_RADIUS_KM = 50.0


# ============================================================
# HELPERS
# ============================================================

def parse_utc_naive(timestamp_string: str) -> datetime:
    """
    Parse an ISO-8601 UTC timestamp and convert it to a
    timezone-naive datetime.

    The current AIS parquet files contain timezone-naive
    Polars Datetime values, so this keeps both sides compatible.
    """

    return datetime.fromisoformat(
        timestamp_string.replace("Z", "")
    )


def require_columns(
    df: pl.DataFrame,
    required_columns: list[str],
    dataset_name: str,
) -> None:
    """
    Verify that required columns exist.
    """

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{dataset_name} is missing required columns: {missing}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("FINAL AIS CANDIDATE ASSOCIATION SCORING")
    print("=" * 70)

    # --------------------------------------------------------
    # Parse source time window
    # --------------------------------------------------------

    source_start = parse_utc_naive(SOURCE_TIME_START)
    source_end = parse_utc_naive(SOURCE_TIME_END)

    if source_end <= source_start:
        raise ValueError(
            "SOURCE_TIME_END must be later than SOURCE_TIME_START."
        )

    source_duration_seconds = (
        source_end - source_start
    ).total_seconds()

    print("\nSource time window:")
    print(f"  {SOURCE_TIME_START}")
    print(f"  → {SOURCE_TIME_END}")

    # --------------------------------------------------------
    # Validate weights
    # --------------------------------------------------------

    total_weight = (
        SPATIAL_WEIGHT
        + TEMPORAL_WEIGHT
        + TRAJECTORY_WEIGHT
        + BEHAVIOUR_WEIGHT
        + DATA_QUALITY_WEIGHT
    )

    if abs(total_weight - 1.0) > 1e-9:
        raise ValueError(
            f"Scoring weights must sum to 1.0. "
            f"Current sum = {total_weight}"
        )

    # --------------------------------------------------------
    # Check files
    # --------------------------------------------------------

    for file_path in [
        CANDIDATES_FILE,
        TRAJECTORIES_FILE,
        TRAJECTORY_SCORES_FILE,
    ]:
        if not file_path.exists():
            raise FileNotFoundError(
                f"Required file not found:\n{file_path}"
            )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ========================================================
    # 1. LOAD VESSEL-LEVEL CANDIDATES
    # ========================================================

    print("\nLoading vessel-level candidate dataset...")

    candidates = pl.read_parquet(
        CANDIDATES_FILE
    )

    require_columns(
        candidates,
        [
            "mmsi",
            "minimum_distance_to_source_km",
            "first_observation",
            "last_observation",
        ],
        "Candidate dataset",
    )

    print(
        f"Candidate vessels: {candidates.height:,}"
    )

    # --------------------------------------------------------
    # Make sure one row exists per MMSI
    # --------------------------------------------------------

    duplicate_mmsis = (
        candidates
        .group_by("mmsi")
        .len()
        .filter(pl.col("len") > 1)
    )

    if duplicate_mmsis.height > 0:
        raise ValueError(
            "Candidate dataset contains duplicate MMSI rows."
        )

    # ========================================================
    # 2. LOAD COMPLETE CANDIDATE TRAJECTORIES
    # ========================================================
    #
    # This is important:
    #
    # ais_candidates.parquet
    #     = vessel-level candidate summary
    #
    # candidate_trajectories.parquet
    #     = complete relevant AIS trajectory for those vessels
    #
    # Therefore behaviour and data-quality statistics are
    # calculated from candidate_trajectories.parquet.
    # ========================================================

    print("\nLoading complete candidate trajectories...")

    trajectories = pl.read_parquet(
    TRAJECTORIES_FILE
    )

    require_columns(
    trajectories,
    [
        "mmsi",
        "timestamp",
        "has_behaviour_anomaly",
        "data_quality_anomaly",
    ],
    "Candidate trajectory dataset",
    )

# The candidate trajectory builder stores the AIS timestamp
# under the column name "timestamp".
# Rename it internally so the rest of this scoring script
# can consistently use "base_date_time".
    trajectories = trajectories.rename(
    {
        "timestamp": "base_date_time"
    }
    )

    print(
    f"Candidate trajectory records: "
    f"{trajectories.height:,}"
)
    # --------------------------------------------------------
    # Ensure trajectories are restricted to the requested
    # source time window.
    #
    # The current dummy trajectory file already uses this
    # window, but this makes the script safe when P2 provides
    # a narrower real window later.
    # --------------------------------------------------------

    trajectories = trajectories.filter(
        (
            pl.col("base_date_time") >= pl.lit(source_start)
        )
        & (
            pl.col("base_date_time") <= pl.lit(source_end)
        )
    )

    print(
        f"Trajectory records in source window: "
        f"{trajectories.height:,}"
    )

    # ========================================================
    # 3. CALCULATE BEHAVIOUR + DATA QUALITY STATISTICS
    # ========================================================

    print("\nCalculating vessel behaviour statistics...")

    trajectory_stats = (
        trajectories
        .group_by("mmsi")
        .agg(
            [
                pl.len().alias(
                    "trajectory_records"
                ),

                pl.col(
                    "has_behaviour_anomaly"
                )
                .cast(pl.Int64)
                .sum()
                .alias(
                    "behaviour_anomaly_records"
                ),

                pl.col(
                    "data_quality_anomaly"
                )
                .cast(pl.Int64)
                .sum()
                .alias(
                    "data_quality_anomaly_records"
                ),

                pl.col(
                    "base_date_time"
                )
                .min()
                .alias(
                    "trajectory_first_observation"
                ),

                pl.col(
                    "base_date_time"
                )
                .max()
                .alias(
                    "trajectory_last_observation"
                ),
            ]
        )
    )

    # --------------------------------------------------------
    # Convert counts into rates.
    #
    # Behaviour score is NOT treated as proof of suspicious
    # activity. It is only a supporting signal.
    # --------------------------------------------------------

    trajectory_stats = trajectory_stats.with_columns(
        [
            (
                pl.col(
                    "behaviour_anomaly_records"
                )
                / pl.col("trajectory_records")
            )
            .clip(
                lower_bound=0.0,
                upper_bound=1.0,
            )
            .alias(
                "behaviour_anomaly_rate"
            ),

            (
                1.0
                - (
                    pl.col(
                        "data_quality_anomaly_records"
                    )
                    / pl.col(
                        "trajectory_records"
                    )
                )
            )
            .clip(
                lower_bound=0.0,
                upper_bound=1.0,
            )
            .alias(
                "data_quality_score"
            ),
        ]
    )

    # ========================================================
    # 4. VALIDATE ANOMALY STATISTICS
    # ========================================================

    behaviour_summary = (
        trajectory_stats
        .select(
            [
                pl.col(
                    "behaviour_anomaly_rate"
                ).min().alias("min"),

                pl.col(
                    "behaviour_anomaly_rate"
                ).median().alias("median"),

                pl.col(
                    "behaviour_anomaly_rate"
                ).mean().alias("mean"),

                pl.col(
                    "behaviour_anomaly_rate"
                ).max().alias("max"),
            ]
        )
    )

    quality_summary = (
        trajectory_stats
        .select(
            [
                pl.col(
                    "data_quality_score"
                ).min().alias("min"),

                pl.col(
                    "data_quality_score"
                ).median().alias("median"),

                pl.col(
                    "data_quality_score"
                ).mean().alias("mean"),

                pl.col(
                    "data_quality_score"
                ).max().alias("max"),
            ]
        )
    )

    print("\nBehaviour anomaly rate:")
    print(
        behaviour_summary
    )

    print("\nData quality score:")
    print(
        quality_summary
    )

    # ========================================================
    # 5. LOAD TRAJECTORY ALIGNMENT SCORES
    # ========================================================

    print(
        "\nLoading trajectory alignment scores..."
    )

    trajectory_scores = pl.read_parquet(
        TRAJECTORY_SCORES_FILE
    )

    require_columns(
        trajectory_scores,
        [
            "mmsi",
            "trajectory_score",
        ],
        "Trajectory alignment dataset",
    )

    print(
        f"Trajectory score records: "
        f"{trajectory_scores.height:,}"
    )

    # --------------------------------------------------------
    # Keep one score per MMSI.
    # --------------------------------------------------------

    trajectory_scores = (
        trajectory_scores
        .select(
            [
                "mmsi",
                "trajectory_score",

                # Keep useful evidence fields if they exist.
                *[
                    column
                    for column in [
                        "spatial_alignment_score",
                        "temporal_alignment_score",
                        "direction_alignment_score",
                        "coverage_score",
                        "alignment_coverage",
                        "sample_confidence",
                        "trajectory_points",
                        "aligned_points",
                        "minimum_oil_distance_km",
                        "mean_oil_distance_km",
                        "mean_oil_time_difference_seconds",
                    ]
                    if column
                    in trajectory_scores.columns
                ],
            ]
        )
        .unique(
            subset=["mmsi"],
            keep="first",
        )
    )

    # ========================================================
    # 6. JOIN EVERYTHING
    # ========================================================

    print("\nCombining candidate evidence...")

    df = (
        candidates
        .join(
            trajectory_stats,
            on="mmsi",
            how="left",
        )
        .join(
            trajectory_scores,
            on="mmsi",
            how="left",
        )
    )

    # --------------------------------------------------------
    # Candidates should all have trajectory statistics.
    # --------------------------------------------------------

    missing_trajectory_stats = (
        df
        .filter(
            pl.col(
                "trajectory_records"
            ).is_null()
        )
        .height
    )

    if missing_trajectory_stats > 0:
        print(
            "\nWARNING:"
            f" {missing_trajectory_stats} candidates "
            "have no trajectory records in the source window."
        )

    # --------------------------------------------------------
    # Missing trajectory scores are allowed.
    #
    # This can happen when P2 trajectory alignment cannot
    # establish a meaningful comparison.
    #
    # Use neutral 0.0 here rather than inventing a positive
    # trajectory relationship.
    # --------------------------------------------------------

    df = df.with_columns(
        pl.col(
            "trajectory_score"
        )
        .fill_null(0.0)
        .clip(
            lower_bound=0.0,
            upper_bound=1.0,
        )
        .alias(
            "trajectory_score"
        )
    )

    # ========================================================
    # 7. SPATIAL SCORE
    # ========================================================
    #
    # Based on minimum AIS distance to the estimated source.
    #
    # 0 km   → 1.0
    # 25 km  → 0.5
    # 50 km  → 0.0
    #
    # This is candidate ranking evidence, not proof of source.
    # ========================================================

    df = df.with_columns(
        (
            1.0
            - (
                pl.col(
                    "minimum_distance_to_source_km"
                )
                / SOURCE_RADIUS_KM
            )
        )
        .clip(
            lower_bound=0.0,
            upper_bound=1.0,
        )
        .alias(
            "spatial_score"
        )
    )

    # ========================================================
    # 8. TEMPORAL SCORE
    # ========================================================
    #
    # Measures how much of the vessel's AIS history overlaps
    # the source time window.
    #
    # Full overlap → 1.0
    # No overlap   → 0.0
    # ========================================================

    overlap_start = pl.max_horizontal(
        pl.col(
            "first_observation"
        ),
        pl.lit(source_start),
    )

    overlap_end = pl.min_horizontal(
        pl.col(
            "last_observation"
        ),
        pl.lit(source_end),
    )

    overlap_seconds = (
        overlap_end
        - overlap_start
    ).dt.total_seconds()

    df = df.with_columns(
        (
            (
                overlap_seconds
                / source_duration_seconds
            )
            .clip(
                lower_bound=0.0,
                upper_bound=1.0,
            )
        )
        .alias(
            "temporal_score"
        )
    )

    # ========================================================
    # 9. BEHAVIOUR SCORE
    # ========================================================
    #
    # Behaviour anomaly rate is used as a supporting signal.
    #
    # IMPORTANT:
    # This does NOT mean:
    #
    # "more anomalies = vessel caused spill"
    #
    # It only contributes 10% of the overall score.
    # ========================================================

    df = df.with_columns(
        pl.col(
            "behaviour_anomaly_rate"
        )
        .fill_null(0.0)
        .clip(
            lower_bound=0.0,
            upper_bound=1.0,
        )
        .alias(
            "behaviour_score"
        )
    )

    # ========================================================
    # 10. DATA QUALITY SCORE
    # ========================================================
    #
    # High-quality trajectory:
    #     score closer to 1
    #
    # Poor-quality trajectory:
    #     score closer to 0
    #
    # Data quality is a trustworthiness signal, NOT a
    # behavioural suspicion signal.
    # ========================================================

    df = df.with_columns(
        pl.col(
            "data_quality_score"
        )
        .fill_null(0.0)
        .clip(
            lower_bound=0.0,
            upper_bound=1.0,
        )
        .alias(
            "quality_score"
        )
    )

    # ========================================================
    # 11. FINAL ASSOCIATION SCORE
    # ========================================================
    #
    # Weighted combination:
    #
    # 35% spatial
    # 25% temporal
    # 20% trajectory
    # 10% behaviour
    # 10% data quality
    #
    # This is an association/ranking score.
    # It is NOT a probability that the vessel caused the spill.
    # ========================================================

    df = df.with_columns(
        (
            (
                pl.col(
                    "spatial_score"
                )
                * SPATIAL_WEIGHT
            )
            + (
                pl.col(
                    "temporal_score"
                )
                * TEMPORAL_WEIGHT
            )
            + (
                pl.col(
                    "trajectory_score"
                )
                * TRAJECTORY_WEIGHT
            )
            + (
                pl.col(
                    "behaviour_score"
                )
                * BEHAVIOUR_WEIGHT
            )
            + (
                pl.col(
                    "quality_score"
                )
                * DATA_QUALITY_WEIGHT
            )
        )
        .clip(
            lower_bound=0.0,
            upper_bound=1.0,
        )
        .alias(
            "association_score"
        )
    )

    # ========================================================
    # 12. ADD EXPLAINABLE EVIDENCE
    # ========================================================

    df = df.with_columns(
        [
            (
                pl.col(
                    "association_score"
                )
                * 100.0
            )
            .round(2)
            .alias(
                "association_score_percent"
            ),

            (
                pl.col(
                    "minimum_distance_to_source_km"
                )
                <= 10.0
            )
            .alias(
                "very_close_to_source"
            ),

            (
                pl.col(
                    "temporal_score"
                )
                >= 0.5
            )
            .alias(
                "strong_temporal_overlap"
            ),

            (
                pl.col(
                    "trajectory_score"
                )
                >= 0.5
            )
            .alias(
                "strong_trajectory_alignment"
            ),

            (
                pl.col(
                    "behaviour_anomaly_records"
                )
                > 0
            )
            .alias(
                "has_behaviour_evidence"
            ),

            (
                pl.col(
                    "data_quality_anomaly_records"
                )
                > 0
            )
            .alias(
                "has_data_quality_issues"
            ),
        ]
    )

    # ========================================================
    # 13. RANK VESSELS
    # ========================================================

    df = (
        df
        .sort(
            [
                "association_score",
                "minimum_distance_to_source_km",
            ],
            descending=[
                True,
                False,
            ],
        )
        .with_row_index(
            name="rank",
            offset=1,
        )
    )

    # ========================================================
    # 14. SELECT / ORDER OUTPUT COLUMNS
    # ========================================================

    preferred_columns = [
        # Ranking
        "rank",
        "mmsi",
        "vessel_name",
        "vessel_type",
        "imo",
        "call_sign",

        # Final score
        "association_score",
        "association_score_percent",

        # Component scores
        "spatial_score",
        "temporal_score",
        "trajectory_score",
        "behaviour_score",
        "quality_score",

        # Spatial evidence
        "minimum_distance_to_source_km",
        "closest_observation_time",
        "closest_latitude",
        "closest_longitude",
        "closest_speed_kmh",
        "closest_heading",

        # Temporal evidence
        "first_observation",
        "last_observation",
        "trajectory_first_observation",
        "trajectory_last_observation",

        # Trajectory evidence
        "trajectory_records",
        "trajectory_points",
        "aligned_points",
        "alignment_coverage",
        "sample_confidence",
        "minimum_oil_distance_km",
        "mean_oil_distance_km",
        "mean_oil_time_difference_seconds",

        # Behaviour evidence
        "behaviour_anomaly_records",
        "behaviour_anomaly_rate",

        # Data quality evidence
        "data_quality_anomaly_records",
        "data_quality_score",

        # Explainability flags
        "very_close_to_source",
        "strong_temporal_overlap",
        "strong_trajectory_alignment",
        "has_behaviour_evidence",
        "has_data_quality_issues",
    ]

    # Keep only columns that actually exist.
    output_columns = [
        column
        for column in preferred_columns
        if column in df.columns
    ]

    df = df.select(
        output_columns
    )

    # ========================================================
    # 15. SAVE
    # ========================================================

    df.write_parquet(
        OUTPUT_FILE
    )

    # ========================================================
    # 16. FINAL SUMMARY
    # ========================================================

    print("\n" + "=" * 70)
    print("FINAL SCORING COMPLETE")
    print("=" * 70)

    print(
        f"\nOutput file:\n{OUTPUT_FILE}"
    )

    print(
        f"\nRanked vessels: {df.height:,}"
    )

    score_summary = (
        df
        .select(
            [
                pl.col(
                    "association_score"
                ).min().alias("min"),

                pl.col(
                    "association_score"
                ).mean().alias("mean"),

                pl.col(
                    "association_score"
                ).median().alias("median"),

                pl.col(
                    "association_score"
                ).max().alias("max"),
            ]
        )
    )

    print("\nAssociation score summary:")
    print(
        score_summary
    )

    # ========================================================
    # TOP 10
    # ========================================================

    print("\nTOP 10 CANDIDATE VESSELS")
    print("-" * 70)

    top_columns = [
        column
        for column in [
            "rank",
            "mmsi",
            "vessel_name",
            "vessel_type",
            "association_score",
            "spatial_score",
            "temporal_score",
            "trajectory_score",
            "behaviour_score",
            "quality_score",
            "minimum_distance_to_source_km",
            "behaviour_anomaly_records",
            "data_quality_anomaly_records",
        ]
        if column in df.columns
    ]

    print(
        df
        .head(10)
        .select(top_columns)
    )

    # ========================================================
    # TOP 3
    # ========================================================

    print("\nTOP 3 FOR DASHBOARD")
    print("-" * 70)

    print(
        df
        .head(3)
        .select(top_columns)
    )

    print("\n" + "=" * 70)
    print(
        "IMPORTANT: association_score is a ranking signal, "
        "not proof of responsibility."
    )
    print(
        "Use dashboard wording such as "
        "'Potentially associated vessel'."
    )
    print("=" * 70)


if __name__ == "__main__":
    main()