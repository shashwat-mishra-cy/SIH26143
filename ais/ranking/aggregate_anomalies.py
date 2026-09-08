from pathlib import Path
import polars as pl


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR
    / "output"
    / "anomalies"
    / "ais_anomalies.parquet"
)

OUTPUT_DIR = BASE_DIR / "output" / "anomalies"

OUTPUT_FILE = (
    OUTPUT_DIR
    / "vessel_anomaly_profiles.parquet"
)


# ============================================================
# VESSEL-LEVEL AGGREGATION
# ============================================================

def aggregate_vessels(df: pl.DataFrame) -> pl.DataFrame:

    # ---------------------------------------------------------
    # Total records per vessel
    # ---------------------------------------------------------

    profiles = (
        df
        .group_by("mmsi")
        .agg(
            pl.len().alias("total_records"),

            # Vessel metadata
            pl.col("vessel_name")
            .drop_nulls()
            .first()
            .alias("vessel_name"),

            pl.col("vessel_type")
            .drop_nulls()
            .first()
            .alias("vessel_type"),

            pl.col("imo")
            .drop_nulls()
            .first()
            .alias("imo"),

            pl.col("call_sign")
            .drop_nulls()
            .first()
            .alias("call_sign"),

            # -------------------------------------------------
            # Behaviour anomaly counts
            # -------------------------------------------------

            pl.col("has_behaviour_anomaly")
            .sum()
            .alias("behaviour_anomaly_records"),

            pl.col("speed_anomaly")
            .sum()
            .alias("speed_anomaly_count"),

            pl.col("acceleration_anomaly")
            .sum()
            .alias("acceleration_anomaly_count"),

            pl.col("turn_anomaly")
            .sum()
            .alias("turn_anomaly_count"),

            # -------------------------------------------------
            # Behaviour anomaly score
            # -------------------------------------------------

            pl.col("behaviour_anomaly_score")
            .sum()
            .alias("behaviour_anomaly_score_sum"),

            pl.col("behaviour_anomaly_score")
            .max()
            .alias("max_behaviour_anomaly_score"),

            # -------------------------------------------------
            # Data quality
            # -------------------------------------------------

            pl.col("data_quality_anomaly")
            .sum()
            .alias("data_quality_anomaly_count"),

            # -------------------------------------------------
            # Time range
            # -------------------------------------------------

            pl.col("base_date_time")
            .min()
            .alias("trajectory_start"),

            pl.col("base_date_time")
            .max()
            .alias("trajectory_end"),

            # -------------------------------------------------
            # Movement statistics
            # -------------------------------------------------

            pl.col("speed_kmh")
            .median()
            .alias("median_speed_kmh"),

            pl.col("speed_kmh")
            .max()
            .alias("max_speed_kmh"),

            pl.col("rolling_std_speed_10m")
            .median()
            .alias("median_speed_variability"),

            pl.col("stopped_duration_seconds")
            .max()
            .alias("max_stopped_duration_seconds"),
        )
    )

    # ========================================================
    # RATES
    # ========================================================

    profiles = profiles.with_columns(

        # -----------------------------------------------------
        # Behaviour anomaly rate
        # -----------------------------------------------------

        (
            pl.col("behaviour_anomaly_records")
            / pl.col("total_records")
        )
        .alias("behaviour_anomaly_rate"),

        # -----------------------------------------------------
        # Individual anomaly rates
        # -----------------------------------------------------

        (
            pl.col("speed_anomaly_count")
            / pl.col("total_records")
        )
        .alias("speed_anomaly_rate"),

        (
            pl.col("acceleration_anomaly_count")
            / pl.col("total_records")
        )
        .alias("acceleration_anomaly_rate"),

        (
            pl.col("turn_anomaly_count")
            / pl.col("total_records")
        )
        .alias("turn_anomaly_rate"),

        # -----------------------------------------------------
        # Data-quality rate
        # -----------------------------------------------------

        (
            pl.col("data_quality_anomaly_count")
            / pl.col("total_records")
        )
        .alias("data_quality_anomaly_rate"),
    )

    # ========================================================
    # SORT
    # ========================================================

    profiles = profiles.sort(
        "behaviour_anomaly_rate",
        descending=True
    )

    return profiles


# ============================================================
# SUMMARY
# ============================================================

def print_summary(
    df: pl.DataFrame,
    profiles: pl.DataFrame
):

    print("\n" + "=" * 60)
    print("VESSEL ANOMALY PROFILE SUMMARY")
    print("=" * 60)

    print(
        f"\nTotal AIS records: "
        f"{df.height:,}"
    )

    print(
        f"Unique vessels: "
        f"{profiles.height:,}"
    )

    # --------------------------------------------------------
    # Vessels with behavioural anomalies
    # --------------------------------------------------------

    anomalous_vessels = profiles.filter(
        pl.col("behaviour_anomaly_records") > 0
    )

    print(
        f"Vessels with behavioural anomalies: "
        f"{anomalous_vessels.height:,}"
    )

    # --------------------------------------------------------
    # Vessels with data-quality problems
    # --------------------------------------------------------

    quality_vessels = profiles.filter(
        pl.col("data_quality_anomaly_count") > 0
    )

    print(
        f"Vessels with data-quality anomalies: "
        f"{quality_vessels.height:,}"
    )

    # --------------------------------------------------------
    # Top vessels
    # --------------------------------------------------------

    print(
        "\nTop 20 vessels by behavioural anomaly rate:"
    )

    print(
        profiles
        .select([
            "mmsi",
            "vessel_name",
            "vessel_type",
            "total_records",
            "behaviour_anomaly_records",
            "behaviour_anomaly_rate",
            "speed_anomaly_count",
            "acceleration_anomaly_count",
            "turn_anomaly_count",
            "data_quality_anomaly_count",
            "max_behaviour_anomaly_score",
        ])
        .head(20)
    )

    # --------------------------------------------------------
    # Highest absolute anomaly counts
    # --------------------------------------------------------

    print(
        "\nTop 20 vessels by behavioural anomaly count:"
    )

    print(
        profiles
        .sort(
            "behaviour_anomaly_records",
            descending=True
        )
        .select([
            "mmsi",
            "vessel_name",
            "vessel_type",
            "total_records",
            "behaviour_anomaly_records",
            "behaviour_anomaly_rate",
            "behaviour_anomaly_score_sum",
            "data_quality_anomaly_count",
        ])
        .head(20)
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("Loading AIS anomaly dataset...")

    df = pl.read_parquet(INPUT_FILE)

    print(
        f"Input shape: {df.shape}"
    )

    print(
        "\nAggregating anomalies by vessel..."
    )

    profiles = aggregate_vessels(df)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    profiles.write_parquet(
        OUTPUT_FILE
    )

    print(
        "\nVessel anomaly profiles written to:"
    )

    print(OUTPUT_FILE)

    print(
        f"\nOutput shape: {profiles.shape}"
    )

    print_summary(
        df,
        profiles
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()