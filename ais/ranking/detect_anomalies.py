from pathlib import Path
import polars as pl


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR
    / "output"
    / "features"
    / "ais_features.parquet"
)

OUTPUT_DIR = BASE_DIR / "output" / "anomalies"
OUTPUT_FILE = OUTPUT_DIR / "ais_anomalies.parquet"


# ============================================================
# INITIAL ANOMALY THRESHOLDS
# ============================================================
#
# These are first-pass engineering thresholds.
# They are NOT final scientific thresholds.
#
# We will inspect the resulting distributions and refine
# these values before building the final vessel ranking system.
# ============================================================

SPEED_CHANGE_THRESHOLD_KMH = 10.0

ACCELERATION_THRESHOLD_KMH_S = 0.10

TURN_RATE_THRESHOLD_DEG_S = 0.50


# ============================================================
# ANOMALY DETECTION
# ============================================================

def detect_anomalies(df: pl.DataFrame) -> pl.DataFrame:

    # ========================================================
    # 1. SUDDEN SPEED CHANGE
    # ========================================================
    #
    # Detect unusually large changes in AIS-reported speed.
    #
    # We use speed_change_abs_kmh rather than coordinate-derived
    # speed because coordinate-derived speed can be corrupted
    # by GPS/AIS position jumps.
    # ========================================================

    df = df.with_columns(
        (
            pl.col("speed_change_abs_kmh")
            >= SPEED_CHANGE_THRESHOLD_KMH
        )
        .fill_null(False)
        .alias("speed_anomaly")
    )

    # ========================================================
    # 2. HIGH ACCELERATION / DECELERATION
    # ========================================================

    df = df.with_columns(
        (
            pl.col("acceleration_kmh_s")
            .abs()
            >= ACCELERATION_THRESHOLD_KMH_S
        )
        .fill_null(False)
        .alias("acceleration_anomaly")
    )

    # ========================================================
    # 3. SHARP TURNING
    # ========================================================
    #
    # Uses AIS heading-derived turn rate.
    #
    # Quality flags remain separate, so a corrupted heading
    # record does not automatically become a trusted behavioural
    # anomaly.
    # ========================================================

    df = df.with_columns(
        (
            pl.col("turn_rate_deg_s")
            .abs()
            >= TURN_RATE_THRESHOLD_DEG_S
        )
        .fill_null(False)
        .alias("turn_anomaly")
    )

    # ========================================================
    # 4. DATA QUALITY ANOMALY
    # ========================================================
    #
    # This is deliberately separate from behavioural anomaly.
    #
    # A bad AIS position should reduce confidence in an
    # observation, not make the vessel look suspicious.
    # ========================================================

    df = df.with_columns(
        (
            pl.col("is_impossible_jump").fill_null(False)
            | pl.col("is_speed_mismatch").fill_null(False)
        )
        .alias("data_quality_anomaly")
    )

    # ========================================================
    # BEHAVIOURAL ANOMALY SCORE
    # ========================================================
    #
    # Score:
    #
    #   speed anomaly       = 1
    #   acceleration        = 1
    #   turning             = 1
    #
    # Maximum = 3
    #
    # Data quality is NOT included.
    # Stationary duration is NOT included.
    # ========================================================

    df = df.with_columns(
        (
            pl.col("speed_anomaly").cast(pl.Int8)
            + pl.col("acceleration_anomaly").cast(pl.Int8)
            + pl.col("turn_anomaly").cast(pl.Int8)
        )
        .alias("behaviour_anomaly_score")
    )

    # ========================================================
    # 5. ANY BEHAVIOURAL ANOMALY?
    # ========================================================

    df = df.with_columns(
        (
            pl.col("behaviour_anomaly_score") > 0
        )
        .alias("has_behaviour_anomaly")
    )

    # ========================================================
    # 6. HUMAN-READABLE ANOMALY REASONS
    # ========================================================
    #
    # Example:
    #
    #   speed
    #   acceleration
    #   turn
    #   speed;acceleration
    #   turn;data_quality
    #
    # Empty string means no detected anomaly.
    # ========================================================

    df = df.with_columns(
        pl.concat_str(
            [
                pl.when(pl.col("speed_anomaly"))
                .then(pl.lit("speed;"))
                .otherwise(pl.lit("")),

                pl.when(pl.col("acceleration_anomaly"))
                .then(pl.lit("acceleration;"))
                .otherwise(pl.lit("")),

                pl.when(pl.col("turn_anomaly"))
                .then(pl.lit("turn;"))
                .otherwise(pl.lit("")),

                pl.when(pl.col("data_quality_anomaly"))
                .then(pl.lit("data_quality;"))
                .otherwise(pl.lit("")),
            ]
        )
        .str.strip_chars(";")
        .alias("anomaly_reasons")
    )

    return df


# ============================================================
# SUMMARY
# ============================================================

def print_summary(df: pl.DataFrame):

    print("\n" + "=" * 60)
    print("ANOMALY DETECTION SUMMARY")
    print("=" * 60)

    total = df.height

    print(f"\nTotal AIS records: {total:,}")

    # --------------------------------------------------------
    # Individual anomaly counts
    # --------------------------------------------------------

    print("\nAnomaly indicators:")

    anomaly_columns = [
        "speed_anomaly",
        "acceleration_anomaly",
        "turn_anomaly",
        "data_quality_anomaly",
    ]

    for column in anomaly_columns:

        count = df.filter(
            pl.col(column)
        ).height

        percentage = (
            count / total * 100
            if total > 0
            else 0
        )

        print(
            f"  {column}: "
            f"{count:,} "
            f"({percentage:.2f}%)"
        )

    # --------------------------------------------------------
    # Behaviour anomaly score distribution
    # --------------------------------------------------------

    print("\nBehaviour anomaly score distribution:")

    score_distribution = (
        df
        .group_by("behaviour_anomaly_score")
        .agg(
            pl.len().alias("records")
        )
        .sort("behaviour_anomaly_score")
    )

    print(score_distribution)

    # --------------------------------------------------------
    # Top anomaly reasons
    # --------------------------------------------------------

    print("\nTop anomaly reasons:")

    reasons = (
        df
        .filter(
            pl.col("anomaly_reasons") != ""
        )
        .group_by("anomaly_reasons")
        .agg(
            pl.len().alias("records")
        )
        .sort(
            "records",
            descending=True
        )
        .head(15)
    )

    print(reasons)

    # --------------------------------------------------------
    # Behavioural anomaly total
    # --------------------------------------------------------

    behavioural_records = df.filter(
        pl.col("has_behaviour_anomaly")
    ).height

    behavioural_percentage = (
        behavioural_records / total * 100
        if total > 0
        else 0
    )

    print(
        f"\nTotal records with behavioural anomalies: "
        f"{behavioural_records:,} "
        f"({behavioural_percentage:.2f}%)"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("Loading feature dataset...")

    df = pl.read_parquet(INPUT_FILE)

    print(f"Input shape: {df.shape}")

    print("\nDetecting behavioural anomalies...")

    df = detect_anomalies(df)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    df.write_parquet(OUTPUT_FILE)

    print("\nAnomaly dataset written to:")
    print(OUTPUT_FILE)

    print(f"\nOutput shape: {df.shape}")

    print_summary(df)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()