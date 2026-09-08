from pathlib import Path
import polars as pl


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR
    / "output"
    / "quality"
    / "ais_quality_flagged.parquet"
)

OUTPUT_DIR = BASE_DIR / "output" / "features"
OUTPUT_FILE = OUTPUT_DIR / "ais_features.parquet"


# ============================================================
# FEATURE ENGINEERING
# ============================================================

def add_features(df: pl.DataFrame) -> pl.DataFrame:

    # ---------------------------------------------------------
    # Sort chronologically for every vessel
    # ---------------------------------------------------------

    df = df.sort(["mmsi", "base_date_time"])

    # =========================================================
    # BASIC MOVEMENT FEATURES
    # =========================================================

    # ---------------------------------------------------------
    # 1. Primary operational speed
    # ---------------------------------------------------------

    df = df.with_columns(
        pl.col("sog_kmh").alias("speed_kmh")
    )

    # ---------------------------------------------------------
    # 2. Speed change
    # ---------------------------------------------------------

    df = df.with_columns(
        (
            pl.col("speed_kmh")
            - pl.col("speed_kmh").shift(1).over("mmsi")
        ).alias("speed_change_kmh")
    )

    # ---------------------------------------------------------
    # 3. Acceleration / deceleration
    # ---------------------------------------------------------

    df = df.with_columns(
        pl.when(
            (pl.col("delta_seconds") > 0)
            & pl.col("speed_change_kmh").is_not_null()
        )
        .then(
            pl.col("speed_change_kmh")
            / pl.col("delta_seconds")
        )
        .otherwise(None)
        .alias("acceleration_kmh_s")
    )

    # ---------------------------------------------------------
    # 4. Previous heading
    # ---------------------------------------------------------

    df = df.with_columns(
        pl.col("heading")
        .shift(1)
        .over("mmsi")
        .alias("previous_heading")
    )

    # ---------------------------------------------------------
    # 5. Circular heading change
    # ---------------------------------------------------------

    df = df.with_columns(
        (
            (
                pl.col("heading")
                - pl.col("previous_heading")
                + 180
            )
            % 360
            - 180
        ).alias("heading_change_deg")
    )

    # ---------------------------------------------------------
    # 6. Turn rate
    # ---------------------------------------------------------

    df = df.with_columns(
        pl.when(
            (pl.col("delta_seconds") > 0)
            & pl.col("heading_change_deg").is_not_null()
        )
        .then(
            pl.col("heading_change_deg")
            / pl.col("delta_seconds")
        )
        .otherwise(None)
        .alias("turn_rate_deg_s")
    )

    # ---------------------------------------------------------
    # 7. Absolute speed change
    # ---------------------------------------------------------

    df = df.with_columns(
        pl.col("speed_change_kmh")
        .abs()
        .alias("speed_change_abs_kmh")
    )

    # =========================================================
    # STATIONARY / MOVEMENT SEGMENTS
    # =========================================================

    # ---------------------------------------------------------
    # 8. Movement-state changes
    # ---------------------------------------------------------

    df = df.with_columns(
        (
            pl.col("movement_state")
            != pl.col("movement_state")
            .shift(1)
            .over("mmsi")
        )
        .fill_null(True)
        .alias("movement_state_changed")
    )

    # ---------------------------------------------------------
    # 9. Movement segment
    # ---------------------------------------------------------

    df = df.with_columns(
        pl.col("movement_state_changed")
        .cast(pl.Int64)
        .cum_sum()
        .over("mmsi")
        .alias("movement_segment")
    )

    # ---------------------------------------------------------
    # 10. Current stationary duration
    # ---------------------------------------------------------

    df = df.with_columns(
        pl.when(
            pl.col("movement_state") == "stationary"
        )
        .then(
            pl.col("delta_seconds")
            .fill_null(0)
            .cum_sum()
            .over(["mmsi", "movement_segment"])
        )
        .otherwise(0)
        .alias("stopped_duration_seconds")
    )

    # =========================================================
    # QUALITY-AWARE FEATURES
    # =========================================================

    # A record is considered behaviourally trustworthy when
    # it is not marked as a major trajectory/data-quality issue.
    #
    # We DO NOT delete bad records.
    # We simply prevent them from influencing rolling
    # behavioural statistics.
    # =========================================================

    # ---------------------------------------------------------
    # 11. Speed quality validity
    # ---------------------------------------------------------

    df = df.with_columns(
        (
            ~pl.col("is_impossible_jump").fill_null(False)
            & ~pl.col("is_speed_mismatch").fill_null(False)
        )
        .alias("speed_quality_valid")
    )

    # ---------------------------------------------------------
    # 12. Acceleration quality validity
    # ---------------------------------------------------------

    df = df.with_columns(
        (
            ~pl.col("is_impossible_jump").fill_null(False)
            & ~pl.col("is_speed_mismatch").fill_null(False)
        )
        .alias("acceleration_quality_valid")
    )

    # ---------------------------------------------------------
    # 13. Heading quality validity
    # ---------------------------------------------------------

    df = df.with_columns(
        (
            ~pl.col("is_impossible_jump").fill_null(False)
        )
        .alias("heading_quality_valid")
    )

    # ---------------------------------------------------------
    # Quality-filtered behavioural signals
    # ---------------------------------------------------------

    df = df.with_columns(

        pl.when(pl.col("speed_quality_valid"))
        .then(pl.col("speed_kmh"))
        .otherwise(None)
        .alias("trusted_speed_kmh"),

        pl.when(pl.col("acceleration_quality_valid"))
        .then(pl.col("acceleration_kmh_s"))
        .otherwise(None)
        .alias("trusted_acceleration_kmh_s"),

        pl.when(pl.col("heading_quality_valid"))
        .then(pl.col("turn_rate_deg_s"))
        .otherwise(None)
        .alias("trusted_turn_rate_deg_s"),

        pl.when(pl.col("speed_quality_valid"))
        .then(pl.col("speed_change_abs_kmh"))
        .otherwise(None)
        .alias("trusted_speed_change_abs_kmh"),
    )

    # =========================================================
    # TIME-AWARE ROLLING FEATURES
    # =========================================================

    # ---------------------------------------------------------
    # 14. Rolling mean trusted speed
    # ---------------------------------------------------------

    df = df.with_columns(
        pl.col("trusted_speed_kmh")
        .rolling_mean_by(
            by="base_date_time",
            window_size="10m",
            min_samples=2,
        )
        .over("mmsi")
        .alias("rolling_mean_speed_10m")
    )

    # ---------------------------------------------------------
    # 15. Rolling speed variability
    # ---------------------------------------------------------

    df = df.with_columns(
        pl.col("trusted_speed_kmh")
        .rolling_std_by(
            by="base_date_time",
            window_size="10m",
            min_samples=2,
        )
        .over("mmsi")
        .alias("rolling_std_speed_10m")
    )

    # ---------------------------------------------------------
    # 16. Rolling mean acceleration
    # ---------------------------------------------------------

    df = df.with_columns(
        pl.col("trusted_acceleration_kmh_s")
        .rolling_mean_by(
            by="base_date_time",
            window_size="10m",
            min_samples=2,
        )
        .over("mmsi")
        .alias("rolling_mean_acceleration_10m")
    )

    # ---------------------------------------------------------
    # 17. Rolling mean turn rate
    # ---------------------------------------------------------

    df = df.with_columns(
        pl.col("trusted_turn_rate_deg_s")
        .abs()
        .rolling_mean_by(
            by="base_date_time",
            window_size="10m",
            min_samples=2,
        )
        .over("mmsi")
        .alias("rolling_mean_turn_rate_10m")
    )

    # ---------------------------------------------------------
    # 18. Rolling mean speed change
    # ---------------------------------------------------------

    df = df.with_columns(
        pl.col("trusted_speed_change_abs_kmh")
        .rolling_mean_by(
            by="base_date_time",
            window_size="10m",
            min_samples=2,
        )
        .over("mmsi")
        .alias("rolling_mean_speed_change_10m")
    )

    return df


# ============================================================
# MAIN
# ============================================================

def main():

    print("Loading AIS quality dataset...")

    df = pl.read_parquet(INPUT_FILE)

    print(f"Input shape: {df.shape}")

    print("\nEngineering AIS movement features...")

    df = add_features(df)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    df.write_parquet(OUTPUT_FILE)

    print("\nFeature dataset written to:")
    print(OUTPUT_FILE)

    print(f"\nOutput shape: {df.shape}")

    print("\nFeature columns:")

    feature_columns = [
        "speed_kmh",
        "speed_change_kmh",
        "acceleration_kmh_s",
        "previous_heading",
        "heading_change_deg",
        "turn_rate_deg_s",
        "speed_change_abs_kmh",
        "movement_state_changed",
        "movement_segment",
        "stopped_duration_seconds",
        "speed_quality_valid",
        "acceleration_quality_valid",
        "heading_quality_valid",
        "trusted_speed_kmh",
        "trusted_acceleration_kmh_s",
        "trusted_turn_rate_deg_s",
        "trusted_speed_change_abs_kmh",
        "rolling_mean_speed_10m",
        "rolling_std_speed_10m",
        "rolling_mean_acceleration_10m",
        "rolling_mean_turn_rate_10m",
        "rolling_mean_speed_change_10m",
    ]

    for column in feature_columns:
        print(f"  - {column}")


if __name__ == "__main__":
    main()