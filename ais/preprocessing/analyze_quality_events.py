import polars as pl
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR
    / "output"
    / "quality"
    / "ais_quality_events.parquet"
)


# ============================================================
# LOAD
# ============================================================

print("Loading quality events...")

df = pl.read_parquet(INPUT_FILE)

print(f"Loaded {df.height:,} quality events")


# ============================================================
# 1. EVENT COUNTS BY VESSEL
# ============================================================

print("\n" + "=" * 70)
print("TOP VESSELS BY QUALITY EVENTS")
print("=" * 70)

vessel_counts = (
    df
    .group_by("mmsi")
    .agg(
        pl.len().alias("total_events"),

        pl.col("is_long_gap")
        .sum()
        .alias("long_gaps"),

        pl.col("is_impossible_jump")
        .sum()
        .alias("impossible_jumps"),

        pl.col("is_speed_mismatch")
        .sum()
        .alias("speed_mismatches"),

        pl.max("quality_issue_score")
        .alias("max_quality_score"),
    )
    .sort("total_events", descending=True)
    .head(30)
)

print(vessel_counts)


# ============================================================
# 2. IMPOSSIBLE JUMP DISTRIBUTION
# ============================================================

print("\n" + "=" * 70)
print("IMPOSSIBLE JUMP STATISTICS")
print("=" * 70)

jumps = df.filter(
    pl.col("is_impossible_jump")
)

if jumps.height > 0:

    print(f"Total impossible jumps: {jumps.height:,}")

    print(
        jumps.select(
            [
                pl.col("distance_km")
                .median()
                .alias("median_distance_km"),

                pl.col("distance_km")
                .mean()
                .alias("mean_distance_km"),

                pl.col("distance_km")
                .max()
                .alias("max_distance_km"),

                pl.col("calculated_speed_kmh")
                .median()
                .alias("median_speed_kmh"),

                pl.col("calculated_speed_kmh")
                .max()
                .alias("max_speed_kmh"),

                pl.col("delta_seconds")
                .median()
                .alias("median_gap_seconds"),

                pl.col("delta_seconds")
                .max()
                .alias("max_gap_seconds"),
            ]
        )
    )


# ============================================================
# 3. HOW MANY ARE EXTREME?
# ============================================================

print("\n" + "=" * 70)
print("IMPOSSIBLE JUMP SEVERITY")
print("=" * 70)

severity = (
    jumps
    .select(
        [
            pl.len().alias("total"),

            (
                pl.col("calculated_speed_kmh") > 200
            )
            .sum()
            .alias("speed_over_200"),

            (
                pl.col("calculated_speed_kmh") > 500
            )
            .sum()
            .alias("speed_over_500"),

            (
                pl.col("calculated_speed_kmh") > 1000
            )
            .sum()
            .alias("speed_over_1000"),

            (
                pl.col("calculated_speed_kmh") > 10000
            )
            .sum()
            .alias("speed_over_10000"),

            (
                pl.col("calculated_speed_kmh") > 100000
            )
            .sum()
            .alias("speed_over_100000"),
        ]
    )
)

print(severity)


# ============================================================
# 4. MULTIPLE ISSUES
# ============================================================

print("\n" + "=" * 70)
print("MULTI-ISSUE RECORDS")
print("=" * 70)

multi = (
    df
    .filter(
        (
            pl.col("is_long_gap").cast(pl.Int8)
            +
            pl.col("is_impossible_jump").cast(pl.Int8)
            +
            pl.col("is_speed_mismatch").cast(pl.Int8)
        )
        >= 2
    )
)

print(
    f"Records with 2+ quality indicators: {multi.height:,}"
)


# ============================================================
# 5. TOP EXTREME EVENTS
# ============================================================

print("\n" + "=" * 70)
print("TOP 20 MOST EXTREME EVENTS")
print("=" * 70)

extreme = (
    df
    .filter(
        pl.col("is_impossible_jump")
    )
    .select(
        [
            "mmsi",
            "base_date_time",
            "prev_timestamp",

            "delta_seconds",
            "distance_km",

            "calculated_speed_kmh",
            "sog_kmh",
            "speed_difference_kmh",

            "quality_flag",
            "quality_issue_score",
        ]
    )
    .sort(
        "calculated_speed_kmh",
        descending=True
    )
    .head(20)
)

print(extreme)


# ============================================================
# 6. LONG-GAP SEVERITY
# ============================================================

print("\n" + "=" * 70)
print("LONG GAP SEVERITY")
print("=" * 70)

gaps = df.filter(
    pl.col("is_long_gap")
)

print(
    gaps.select(
        [
            pl.len().alias("total_long_gaps"),

            (
                pl.col("delta_seconds") > 30 * 60
            )
            .sum()
            .alias("over_30_minutes"),

            (
                pl.col("delta_seconds") > 60 * 60
            )
            .sum()
            .alias("over_1_hour"),

            (
                pl.col("delta_seconds") > 3 * 60 * 60
            )
            .sum()
            .alias("over_3_hours"),

            (
                pl.col("delta_seconds") > 6 * 60 * 60
            )
            .sum()
            .alias("over_6_hours"),

            (
                pl.col("delta_seconds") > 12 * 60 * 60
            )
            .sum()
            .alias("over_12_hours"),
        ]
    )
)